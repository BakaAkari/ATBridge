"""Minimal Blender controls. All bpy operations stay on the main thread."""
from pathlib import Path
import bpy
import webbrowser
from .distribution import store_url
from .bridge import Bridge
from ..preferences import get_addon_preferences

_service = None
_job_id = None
_seen = None
_status = 'Stopped'
_results = []
_files = []
_listing = ''
_cursor = ''
_query = ''
_ready = ''


class ATB_CompanionRow(bpy.types.PropertyGroup):
    uid: bpy.props.StringProperty()
    name: bpy.props.StringProperty()
    size: bpy.props.IntProperty()


class ATB_CompanionState(bpy.types.PropertyGroup):
    query: bpy.props.StringProperty(name='Search', default='Nordic Forest Cluster Rock Small')
    downloads: bpy.props.StringProperty(name='Browser download folder', subtype='DIR_PATH',
                                       default=str(Path.home() / 'Downloads'))
    results: bpy.props.CollectionProperty(type=ATB_CompanionRow)
    result_index: bpy.props.IntProperty(default=0)
    files: bpy.props.CollectionProperty(type=ATB_CompanionRow)
    file_index: bpy.props.IntProperty(default=0)


def _redraw():
    for wm in bpy.data.window_managers:
        for window in wm.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()


def _pump():
    global _seen, _status, _results, _files, _cursor, _ready
    if not _service:
        return None
    if _job_id:
        job = _service.snapshot(_job_id)
        state = job['status']
        if state != _seen:
            _seen = state
            _status = state
            if state == 'done':
                data = job['data']
                if job['action'] == 'search':
                    _results, _cursor = data['items'], data['cursor']
                    for wm in bpy.data.window_managers:
                        props = wm.atb_companion
                        props.results.clear()
                        props.result_index = 0
                        for item in _results:
                            row = props.results.add()
                            row.uid, row.name = item['uid'], item['title']
                elif job['action'] == 'files':
                    _files = data['files']
                    for wm in bpy.data.window_managers:
                        props = wm.atb_companion
                        props.files.clear()
                        props.file_index = 0
                        for item in _files:
                            row = props.files.add()
                            row.uid, row.name, row.size = item['uid'], item['name'], item['size']
                    if not _files:
                        _status = 'No supported FBX ZIP (prototype limit: 1 GiB)'
                else:
                    _ready = data['path']
                    _status = 'Ready to import: ' + Path(_ready).name
            elif state == 'error':
                _status = job['error'] + ' — reconnect/login if needed, then retry manually'
    _redraw()
    return 0.5


def shutdown():
    global _service, _job_id, _seen, _status, _ready, _files, _results, _listing, _cursor
    if _service:
        _service.stop()
        _service = None
    if bpy.app.timers.is_registered(_pump):
        bpy.app.timers.unregister(_pump)
    _job_id = _seen = None
    _ready = _listing = _cursor = ''
    _files, _results = [], []
    _status = 'Stopped'


class ATB_OT_companion(bpy.types.Operator):
    bl_idname = 'atb.companion'
    bl_label = 'Fab Companion'
    action: bpy.props.StringProperty()
    request_id: bpy.props.StringProperty()

    def execute(self, context):
        global _service, _job_id, _status, _seen, _listing, _query, _cursor, _ready, _files
        props = context.window_manager.atb_companion
        try:
            if self.action == 'guide':
                webbrowser.open((Path(__file__).parent / 'install.html').as_uri())
            elif self.action == 'store':
                url = store_url()
                if not url:
                    raise ValueError('Chrome 商店尚未上架，请使用测试版安装指南')
                webbrowser.open(url)
            elif self.action == 'folder':
                bpy.ops.wm.path_open(filepath=str(Path(__file__).parent / 'extension'))
            elif self.action == 'pair':
                if not _service:
                    raise ValueError('请先启动连接')
                _service.open_pairing()
                _status = '配对已开启 2 分钟：在 Chrome 扩展中点击请求连接'
            elif self.action in {'approve', 'deny'}:
                _service.decide_pairing(self.request_id, self.action == 'approve')
                _status = '已允许，等待 Chrome 完成连接' if self.action == 'approve' else '已拒绝配对'
            elif self.action == 'start':
                if _service:
                    return {'CANCELLED'}
                prefs = get_addon_preferences(context)
                cache = (Path(bpy.path.abspath(prefs.fab_assets_path)) if prefs and prefs.fab_assets_path
                         else Path(bpy.utils.user_resource('DATAFILES', path='ATBridge', create=True)))
                downloads = Path(bpy.path.abspath(props.downloads)).expanduser().resolve()
                if not downloads.is_dir():
                    raise ValueError('Browser download folder does not exist')
                service = Bridge(downloads, cache / 'companion-inbox')
                service.start()
                service.open_pairing()
                _service = service
                _status = 'Waiting for browser companion'
                props.results.clear()
                props.files.clear()
                bpy.app.timers.register(_pump, persistent=True)
            elif self.action == 'stop':
                shutdown()
            elif self.action == 'copy':
                context.window_manager.clipboard = _service.token
                self.report({'INFO'}, 'Pairing code copied; paste in the extension page')
            elif self.action == 'cancel':
                _service.cancel()
            elif self.action == 'import':
                if not _ready or not Path(_ready).is_file():
                    raise ValueError('No verified download ready')
                result = bpy.ops.atb.import_zip(filepath=_ready, cache_directory=str(Path(_ready).parent))
                if 'FINISHED' not in result:
                    raise ValueError('Import failed; see ATBridge log')
                _status = 'Imported: ' + Path(_ready).name
                _ready = ''
            else:
                if not _service:
                    raise ValueError('Start companion first')
                if _job_id and _service.snapshot(_job_id)['status'] in {'queued', 'running', 'transferring'}:
                    raise ValueError('Wait or cancel the current request')
                params = {}
                action = self.action
                if action in {'search', 'next'}:
                    query = props.query.strip() if action == 'search' else _query
                    if not query or len(query) > 200:
                        raise ValueError('Enter a search query (up to 200 characters)')
                    params = {'query': query, 'cursor': _cursor if action == 'next' else ''}
                    _query = query
                    action = 'search'
                    _listing = ''
                    _files = []
                    props.files.clear()
                elif action == 'files':
                    if not 0 <= props.result_index < len(props.results):
                        raise ValueError('Select an asset')
                    _listing = props.results[props.result_index].uid
                    params = {'listing': _listing}
                    _files = []
                    props.files.clear()
                elif action == 'download':
                    if not _listing or not 0 <= props.file_index < len(_files):
                        raise ValueError('Fetch and select an FBX ZIP first')
                    file = _files[props.file_index]
                    params = {'listing': _listing, 'file': file['uid'], 'name': file['name'], 'size': file['size']}
                else:
                    raise ValueError('Unknown action')
                _job_id = _service.submit(action, **params)
                if action == 'download':
                    _ready = ''
                _seen = None
                _status = 'Queued: ' + action
            _redraw()
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class ATB_UL_companion(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.name)


class ATB_PT_companion(bpy.types.Panel):
    bl_label = 'Fab Companion (Prototype)'
    bl_idname = 'ATB_PT_companion'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ATBridge'

    def draw(self, context):
        layout = self.layout
        props = context.window_manager.atb_companion
        def button(parent, action, text):
            parent.operator('atb.companion', text=text).action = action
        setup = layout.box()
        setup.label(text='首次使用：安装 Chrome 扩展')
        if store_url():
            button(setup, 'store', '前往 Chrome 商店安装')
        else:
            setup.label(text='测试版：尚未上架 Chrome 商店')
            button(setup, 'folder', '打开扩展文件夹')
        button(setup, 'guide', '查看安装与连接指南')
        if not _service:
            layout.prop(props, 'downloads')
            button(layout, 'start', '连接 Fab / 开启配对')
        else:
            row = layout.row()
            button(row, 'copy', 'Copy pairing code')
            button(row, 'stop', 'Stop')
            pair = _service.pairing_snapshot()
            box = layout.box()
            if pair['state'] == 'pending':
                box.label(text='Chrome 确认码：' + pair['code'])
                box.label(text='仅在浏览器显示相同码时允许')
                box.label(text='扩展 ID：' + pair['origin'].split('://')[1])
                row = box.row()
                for action, title in [('approve', '允许连接'), ('deny', '拒绝')]:
                    op = row.operator('atb.companion', text=title)
                    op.action, op.request_id = action, pair['id']
            elif pair['state'] == 'waiting':
                box.label(text='2 分钟内在 Chrome 扩展点击请求连接')
            elif _service.origin:
                box.label(text='浏览器已配对；保持扩展页面打开')
            else:
                box.label(text='未连接 / 配对窗口已关闭')
            button(box, 'pair', '重新配对（取消当前任务）')
            layout.label(text='Keep extension connection page open')
            layout.prop(props, 'query')
            row = layout.row()
            button(row, 'search', 'Search')
            if _cursor:
                button(row, 'next', 'Next page')
            button(row, 'cancel', 'Cancel')
            layout.template_list('ATB_UL_companion', 'results', props, 'results', props, 'result_index', rows=4)
            button(layout, 'files', 'Check ownership / FBX files')
            layout.template_list('ATB_UL_companion', 'files', props, 'files', props, 'file_index', rows=3)
            if 0 <= props.file_index < len(props.files):
                layout.label(text='Size: %.2f MiB' % (props.files[props.file_index].size / 1024 ** 2))
            button(layout, 'download', 'Download selected ZIP')
        for line in [_status[i:i+60] for i in range(0, len(_status), 60)]:
            layout.label(text=line)
        if _ready:
            button(layout, 'import', 'Import downloaded asset')


_CLASSES = (ATB_CompanionRow, ATB_CompanionState, ATB_OT_companion, ATB_UL_companion, ATB_PT_companion)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.atb_companion = bpy.props.PointerProperty(type=ATB_CompanionState)


def unregister():
    shutdown()
    del bpy.types.WindowManager.atb_companion
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
