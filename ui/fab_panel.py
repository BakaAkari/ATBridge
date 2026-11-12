"""Fab inbox: filesystem work is isolated from Blender's UI thread."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import subprocess
import sys
import textwrap
import webbrowser
import tempfile
import shutil
import bpy
import bpy.utils.previews
from ..preferences import get_addon_preferences
from ..utils.translation import get_text as tr, message_text, get_language
from ..utils.fab_files import downloads_directory, recent_zip_files, describe_zip
from ..utils.fab_preview_cache import cached_product_image, preview_cache_directory

_executor = None
_future = None
_cache = {}
_history = {}
_failures = {}
_browser = None
_browser_folder = None
_last_objects = []
_preview_dir = None
_previews = None


def _download_folder(context):
    if _browser is not None and _browser.poll() is None and _browser_folder:
        return Path(_browser_folder)
    prefs = get_addon_preferences(context)
    return Path(bpy.path.abspath(prefs.fab_downloads_path)) if prefs else downloads_directory()


def _browser_executable():
    addon = Path(__file__).resolve().parents[1]
    # Release packages ship the browser inside the add-on; source checkouts use dist/ builds.
    bundled = addon / 'bin' / 'fab-browser' / 'ATBridge.FabBrowser.exe'
    if bundled.is_file():
        return bundled
    root = addon / 'dist' / 'fab-browser'
    marker = root / 'current.txt'
    if marker.is_file():
        candidate = (root / marker.read_text().strip() / 'ATBridge.FabBrowser.exe').resolve()
        if root.resolve() not in candidate.parents:
            raise ValueError('独立窗口构建路径无效，请重新构建')
        return candidate
    return root / 'ATBridge.FabBrowser.exe'


def _history_path():
    return Path(bpy.utils.user_resource('CONFIG', path='ATBridge', create=True)) / 'imports.json'


def _key(path):
    p = Path(path)
    s = p.stat()
    return '%s|%s|%s' % (p.resolve(), s.st_size, s.st_mtime_ns)


def _scan(folder):
    rows = []
    for path, stamp, size in recent_zip_files(folder):
        key = '%s|%s|%s' % (path, size, stamp)
        info = _cache.get(key)
        if info is None:
            info = describe_zip(path, _preview_dir)
            _cache[key] = info
        display = dict(info)
        if not info.get('error'):
            cached = cached_product_image(info.get('asset_id'))
            if cached:
                display.update({k: v for k, v in cached.items() if v})
        rows.append((str(path), size, key, display))
    live = {row[2] for row in rows}
    for key in list(_cache):
        if key not in live:
            old = _cache.pop(key)
            if old.get('preview'):
                try:
                    Path(old['preview']).unlink(missing_ok=True)
                except OSError:
                    pass
    return rows


def _apply(state, rows):
    selected = state.files[state.index].path if 0 <= state.index < len(state.files) else ''
    signature = json.dumps(rows, ensure_ascii=False)
    if state.signature == signature:
        return
    state.signature = signature
    if _previews is not None:
        live = {row[3].get('preview_token', row[2]) for row in rows}
        for key in list(_previews):
            if key not in live:
                del _previews[key]
    state.files.clear()
    for path, size, key, info in rows:
        item = state.files.add()
        item.name = Path(path).name
        item.path, item.key = path, key
        item.title, item.detail, item.error = info['title'], info['detail'], info['error']
        item.preview_label = info.get('preview_label', '')
        if _previews is not None and info.get('preview'):
            try:
                preview_key = info.get('preview_token', key)
                if preview_key not in _previews:
                    _previews.load(preview_key, info['preview'], 'IMAGE')
                item.preview_icon = _previews[preview_key].icon_id
            except Exception:
                pass
        item.size_label = '%.1f MiB' % (size / 1024 ** 2)
        item.imported = key in _history
        item.last_error = _failures.get(path, '')
    state.index = next((i for i, row in enumerate(state.files) if row.path == selected),
                       next((i for i, row in enumerate(state.files) if not row.error), 0))


def _redraw():
    for wm in bpy.data.window_managers:
        for win in wm.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()


def _pump():
    global _future
    if _executor is None:
        return None
    state = bpy.context.window_manager.atb_fab_local
    folder = str(_download_folder(bpy.context))
    if _future is not None and _future[0].done():
        job, source = _future
        _future = None
        if source == folder:
            try:
                _apply(state, job.result())
                state.scan_error = ''
            except Exception as error:
                state.scan_error = str(error)
        else:
            pass
    if _future is None and state.auto_scan:
        _future = (_executor.submit(_scan, folder), folder)
    _redraw()
    return 2.0


def _request_scan(context):
    global _future
    if _executor is not None:
        folder = str(_download_folder(context))
        _future = (_executor.submit(_scan, folder), folder)


def record_import(path, success, message, objects=()):
    """All import entry points publish the same outcome on Blender's main thread."""
    global _last_objects
    state = bpy.context.window_manager.atb_fab_local
    state.status = message
    state.failed = not success
    if success:
        _failures.pop(str(path), None)
    else:
        _failures[str(path)] = message
    for item in state.files:
        if item.path == str(path):
            item.last_error = '' if success else message
    if success:
        _last_objects = list(objects)
        state.result_count = len(_last_objects)
        try:
            key = _key(path)
            _history[key] = True
            # Bound local history; it records a prior import, never asserts scene membership.
            while len(_history) > 200:
                del _history[next(iter(_history))]
            target = _history_path()
            temp = target.with_suffix('.tmp')
            temp.write_text(json.dumps(_history), encoding='utf-8')
            temp.replace(target)
            for item in state.files:
                if item.key == key:
                    item.imported = True
        except OSError:
            state.status += '（导入记录未保存）'
    _redraw()


class ATB_FabLocalFile(bpy.types.PropertyGroup):
    path: bpy.props.StringProperty()
    key: bpy.props.StringProperty()
    title: bpy.props.StringProperty()
    detail: bpy.props.StringProperty()
    error: bpy.props.StringProperty()
    last_error: bpy.props.StringProperty()
    imported: bpy.props.BoolProperty()
    size_label: bpy.props.StringProperty()
    preview_icon: bpy.props.IntProperty()
    preview_label: bpy.props.StringProperty()


class ATB_FabLocalState(bpy.types.PropertyGroup):
    files: bpy.props.CollectionProperty(type=ATB_FabLocalFile)
    index: bpy.props.IntProperty(default=0)
    signature: bpy.props.StringProperty()
    status: bpy.props.StringProperty(default='')
    scan_error: bpy.props.StringProperty()
    failed: bpy.props.BoolProperty()
    result_count: bpy.props.IntProperty()
    auto_scan: bpy.props.BoolProperty(name='Auto-detect downloads', default=True)
    settings: bpy.props.BoolProperty(name='Settings and other options', default=False)
    query: bpy.props.StringProperty(name='Search assets', options={'TEXTEDIT_UPDATE'})
    show_unsupported: bpy.props.BoolProperty(name='Show unsupported ZIPs', default=False)


class ATB_OT_fab_local(bpy.types.Operator):
    bl_idname = 'atb.fab_local'
    bl_label = 'Fab Assets'
    action: bpy.props.StringProperty()

    def execute(self, context):
        global _browser, _browser_folder
        state = context.window_manager.atb_fab_local
        try:
            if self.action == 'website':
                webbrowser.open('https://www.fab.com/sellers/Quixel')
            elif self.action == 'browser':
                # One browser launched per Blender session; repeated clicks focus it.
                if _browser is not None and _browser.poll() is None:
                    import ctypes
                    user32 = ctypes.windll.user32
                    callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                    def focus(hwnd, unused):
                        pid = ctypes.c_ulong()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        if pid.value == _browser.pid and user32.IsWindowVisible(hwnd):
                            user32.ShowWindow(hwnd, 9)
                            user32.SetForegroundWindow(hwnd)
                            return False
                        return True
                    user32.EnumWindows(callback(focus), 0)
                else:
                    executable = _browser_executable()
                    if sys.platform != 'win32' or not executable.is_file():
                        raise ValueError('独立窗口不可用；请在其他入口使用普通浏览器。')
                    destination = str(_download_folder(context))
                    _browser = subprocess.Popen([str(executable), '--blender-pid', str(os.getpid()),
                                                 '--language', get_language(context),
                                                 '--downloads', destination],
                                                cwd=str(executable.parent), close_fds=True)
                    _browser_folder = destination
            elif self.action == 'folder':
                bpy.ops.wm.path_open(filepath=str(_download_folder(context)))
            elif self.action == 'preview_cache':
                folder = preview_cache_directory()
                folder.mkdir(parents=True, exist_ok=True)
                bpy.ops.wm.path_open(filepath=str(folder))
            elif self.action == 'reveal':
                item = state.files[state.index]
                subprocess.Popen(['explorer.exe', '/select,', str(Path(item.path))])
            elif self.action == 'refresh':
                # Explicit refresh also supports background scripts; never overlap cache mutation.
                if bpy.app.background and (_future is None or _future[0].done()):
                    _apply(state, _scan(_download_folder(context)))
                    state.scan_error = ''
                elif _future is None:
                    _request_scan(context)
            elif self.action == 'import':
                if not 0 <= state.index < len(state.files):
                    raise ValueError('请选择一个资产')
                item = state.files[state.index]
                if item.error:
                    raise ValueError(item.error)
                return bpy.ops.atb.import_zip(filepath=item.path)
            elif self.action == 'locate':
                objects = []
                for obj in _last_objects:
                    try:
                        if context.scene.objects.get(obj.name) == obj and context.view_layer.objects.get(obj.name) == obj:
                            objects.append(obj)
                    except ReferenceError:
                        pass
                if not objects:
                    raise ValueError('上次导入的对象已不在当前场景中')
                bpy.ops.object.select_all(action='DESELECT')
                for obj in objects:
                    obj.select_set(True)
                context.view_layer.objects.active = objects[0]
                if context.area and context.area.type == 'VIEW_3D':
                    bpy.ops.view3d.view_selected(use_all_regions=False)
            return {'FINISHED'}
        except Exception as error:
            state.status, state.failed = str(error), True
            self.report({'ERROR'}, message_text(str(error), context))
            return {'CANCELLED'}


class ATB_UL_fab_local(bpy.types.UIList):
    def filter_items(self, context, data, propname):
        query = data.query.casefold().strip()
        return ([self.bitflag_filter_item if (data.show_unsupported or not x.error)
                 and (not query or query in (x.title + x.name).casefold()) else 0
                 for x in getattr(data, propname)], [])

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        row.label(text=item.title or item.name,
                  icon='ERROR' if item.error or item.last_error else ('CHECKMARK' if item.imported else 'PACKAGE'), translate=False)


class ATB_PT_fab_local(bpy.types.Panel):
    bl_label = 'Fab Assets'
    bl_idname = 'ATB_PT_fab_local'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ATBridge'
    bl_order = -1

    def draw(self, context):
        layout = self.layout
        state = context.window_manager.atb_fab_local
        width = max(18, int(context.region.width / 8))
        def lines(parent, text):
            for line in textwrap.wrap(text, width=width, break_long_words=True):
                parent.label(text=line, translate=False)
        def button(parent, action, text, icon='NONE'):
            parent.operator('atb.fab_local', text=text, icon=icon, translate=False).action = action

        row = layout.row()
        row.scale_y = 1.4
        button(row, 'browser' if sys.platform == 'win32' else 'website', tr('浏览 Fab 资产'), 'WORLD')
        layout.label(text=tr('下载完成后自动出现在下方'), icon='INFO')
        if hasattr(bpy.types, 'ATB_OT_dev_reload'):
            layout.operator('atb.dev_reload', text=tr('重载插件 · 开发模式'), icon='FILE_REFRESH')
        layout.separator()
        row = layout.row()
        supported = sum(not x.error for x in state.files)
        row.label(text=tr('最近资产 · %d') % supported)
        button(row, 'refresh', '', 'FILE_REFRESH')
        if state.scan_error:
            box = layout.box()
            box.alert = True
            lines(box, message_text(state.scan_error, context))
            box.prop(state, 'settings', text=tr('打开设置'))
        elif not supported and not state.show_unsupported:
            box = layout.box()
            box.label(text=tr('等待你的第一个资产'), icon='PACKAGE')
            lines(box, tr('在 Fab 下载 Megascans ZIP，或选择电脑上的资产包。'))
        if state.files and (supported or state.show_unsupported):
            layout.prop(state, 'query', text='', icon='VIEWZOOM')
            layout.template_list('ATB_UL_fab_local', '', state, 'files', state, 'index', rows=5)
            if (0 <= state.index < len(state.files)
                    and (state.show_unsupported or not state.files[state.index].error)
                    and (not state.query.strip() or state.query.casefold().strip() in
                         (state.files[state.index].title + state.files[state.index].name).casefold())):
                item = state.files[state.index]
                box = layout.box()
                lines(box, item.title)
                if item.preview_icon:
                    box.template_icon(icon_value=item.preview_icon, scale=6)
                    lines(box, message_text(item.preview_label, context))
                elif not item.error:
                    lines(box, tr('暂无商品图；在新版独立窗口浏览对应商品页可补齐。'))
                box.label(text=message_text(item.detail, context) + ' · ' + item.size_label)
                if item.error:
                    box.alert = True
                    lines(box, message_text(item.error, context))
                    lines(box, tr('请在 Fab 选择含 Megascans 元数据的模型或材质 ZIP。'))
                else:
                    if item.last_error:
                        lines(box, message_text(item.last_error, context))
                    box.label(text=tr('曾导入过 · 再次导入会创建副本') if item.imported else tr('元数据已识别 · 可尝试导入'),
                              icon='CHECKMARK' if item.imported else 'IMPORT')
                    row = box.row()
                    row.scale_y = 1.3
                    button(row, 'import', tr('重试导入') if item.last_error else (tr('再次导入副本') if item.imported else tr('导入到场景')), 'IMPORT')
                button(box, 'reveal', tr('在文件夹中显示'), 'FILE_FOLDER')
        layout.operator('atb.import_zip', text=tr('从电脑选择 ZIP…'), icon='FILEBROWSER')
        if state.status:
            box = layout.box()
            box.alert = state.failed
            lines(box, message_text(state.status, context))
            if not state.failed and state.result_count:
                button(box, 'locate', tr('选中并查看导入对象'), 'VIEWZOOM')
        layout.separator()
        layout.prop(state, 'settings', icon='TRIA_DOWN' if state.settings else 'TRIA_RIGHT', emboss=False)
        if state.settings:
            box = layout.box()
            box.prop(state, 'auto_scan')
            box.prop(state, 'show_unsupported')
            prefs = get_addon_preferences(context)
            if prefs:
                folder_row = box.column()
                running = _browser is not None and _browser.poll() is None
                folder_row.enabled = not running
                folder_row.prop(prefs, 'fab_downloads_path', text=tr('下载目录'))
                if running:
                    lines(box, tr('关闭独立窗口后可修改下载目录。当前接收：') + str(_download_folder(context)))
                box.prop(prefs, 'fab_assets_path', text=tr('解压缓存'))
            button(box, 'website', tr('用普通浏览器打开 Fab'), 'URL')
            button(box, 'folder', tr('打开下载目录'), 'FILE_FOLDER')
            button(box, 'preview_cache', tr('打开商品图缓存'), 'IMAGE_DATA')
            lines(box, tr('商品图独立存于 LocalAppData/ATBridge/Cache/Fab；90 天过期，上限 256 MiB。'))
            lines(box, tr('仅显示最近 20 个 ZIP。缓存留空即可；材质引用缓存文件，请勿随意删除。'))


_CLASSES = (ATB_FabLocalFile, ATB_FabLocalState, ATB_OT_fab_local, ATB_UL_fab_local, ATB_PT_fab_local)


def register():
    global _executor, _history, _preview_dir, _previews
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.atb_fab_local = bpy.props.PointerProperty(type=ATB_FabLocalState)
    try:
        data = json.loads(_history_path().read_text(encoding='utf-8'))
        _history = data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        _history = {}
    _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ATBridge-inbox')
    _preview_dir = tempfile.mkdtemp(prefix='atbridge-previews-')
    _previews = bpy.utils.previews.new()
    if not bpy.app.background:
        bpy.app.timers.register(_pump, first_interval=0.5, persistent=True)


def shutdown():
    global _executor, _future, _previews, _preview_dir
    if bpy.app.timers.is_registered(_pump):
        bpy.app.timers.unregister(_pump)
    if _executor:
        _executor.shutdown(wait=True, cancel_futures=True)
    _executor, _future = None, None
    _cache.clear()
    _failures.clear()
    _last_objects.clear()
    if _previews is not None:
        bpy.utils.previews.remove(_previews)
        _previews = None
    if _preview_dir:
        shutil.rmtree(_preview_dir, ignore_errors=True)
        _preview_dir = None


def unregister():
    shutdown()
    if hasattr(bpy.types.WindowManager, 'atb_fab_local'):
        del bpy.types.WindowManager.atb_fab_local
    for cls in reversed(_CLASSES):
        if cls.is_registered:
            bpy.utils.unregister_class(cls)
