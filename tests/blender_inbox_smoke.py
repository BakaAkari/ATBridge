"""Blender background smoke for Fab inbox state, feedback and legacy visibility."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import zipfile

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
assert addon_utils.enable(ROOT.name, default_set=True, persistent=False)
from ATBridge.preferences import get_addon_preferences
from ATBridge.ui import fab_panel

try:
    with tempfile.TemporaryDirectory(prefix='atbridge-inbox-smoke-') as directory:
        root = Path(directory)
        prefs = get_addon_preferences(bpy.context)
        assert prefs is not None
        prefs.fab_downloads_path = str(root / 'downloads')
        Path(prefs.fab_downloads_path).mkdir(parents=True)

        state = bpy.context.window_manager.atb_fab_local

        def visible_names():
            flags, _ = fab_panel.ATB_UL_fab_local.filter_items(
                SimpleNamespace(bitflag_filter_item=1), bpy.context, state, 'files')
            return [state.files[i].name for i, flag in enumerate(flags) if flag]

        # Selecting an older item survives a scan that inserts a newer download.
        older = str(root / 'older.zip')
        newer = str(root / 'newer.zip')
        old_info = {'title': 'Older asset', 'detail': 'FBX', 'error': '', 'preview': ''}
        new_info = {'title': 'Newest asset', 'detail': 'OBJ', 'error': '', 'preview': ''}
        fab_panel._apply(state, [(older, 3, 'older-key', old_info),
                                 (str(root / 'other.zip'), 3, 'other-key', old_info)])
        state.index = 1
        selected_path = state.files[state.index].path
        fab_panel._apply(state, [(newer, 3, 'newer-key', new_info),
                                 (older, 3, 'older-key', old_info),
                                 (str(root / 'other.zip'), 3, 'other-key', old_info)])
        assert state.files[state.index].path == selected_path, 'Selection changed when newest item was inserted'

        # A malformed ZIP remains visible with an error instead of looking importable.
        invalid_zip = Path(prefs.fab_downloads_path) / 'broken.zip'
        invalid_zip.write_bytes(b'not a zip archive')
        assert bpy.ops.atb.fab_local(action='refresh') == {'FINISHED'}
        invalid_items = [item for item in state.files if item.path == str(invalid_zip)]
        assert len(invalid_items) == 1 and invalid_items[0].error, 'Invalid ZIP was not marked with an error'
        assert invalid_items[0].name not in visible_names(), 'Unsupported ZIP should be hidden by default'
        state.show_unsupported = True
        assert invalid_items[0].name in visible_names(), 'Show unsupported toggle did not reveal the invalid ZIP'
        state.show_unsupported = False

        # record_import immediately updates status, the row, and isolated history.
        imported_zip = root / 'recorded.zip'
        with zipfile.ZipFile(imported_zip, 'w') as archive:
            archive.writestr('asset.json', json.dumps({'id': 'recorded', 'models': [{'uri': 'asset.fbx'}], 'maps': []}))
        config_dir = root / 'config'
        config_dir.mkdir()
        history_path = config_dir / 'imports.json'
        original_history_path = fab_panel._history_path
        original_history = dict(fab_panel._history)
        fab_panel._history_path = lambda: history_path
        fab_panel._history.clear()
        try:
            # Add a history target row so direct feedback can update its imported marker.
            fab_panel._apply(state, [(str(imported_zip), imported_zip.stat().st_size,
                                      fab_panel._key(imported_zip), old_info)])
            bpy.ops.mesh.primitive_cube_add()
            obj = bpy.context.object
            fab_panel.record_import(str(imported_zip), True, '导入成功', [obj])
            assert state.status == '导入成功' and not state.failed and state.result_count == 1
            assert state.files[0].imported, 'Successful direct feedback did not mark the inbox row imported'
            history = json.loads(history_path.read_text(encoding='utf-8'))
            assert fab_panel._key(imported_zip) in history, 'Successful direct feedback was not persisted to history'

            # Locate follows the imported object through a rename, using its RNA identity.
            original_name = 'Tracked Asset After Rename'
            obj.name = original_name
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.mesh.primitive_cube_add()
            decoy = bpy.context.object
            bpy.ops.object.select_all(action='DESELECT')
            assert bpy.ops.atb.fab_local(action='locate') == {'FINISHED'}
            assert obj.select_get() and bpy.context.view_layer.objects.active == obj
            assert not decoy.select_get(), 'Locate selected a different object after the tracked object was renamed'

            # A replacement with the same name must not be mistaken for the deleted object.
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.mesh.primitive_cube_add()
            replacement = bpy.context.object
            replacement.name = original_name
            bpy.ops.object.select_all(action='DESELECT')
            try:
                locate_result = bpy.ops.atb.fab_local(action='locate')
            except RuntimeError as error:
                # Background Blender raises when the operator reports an error.
                assert fab_panel.message_text('上次导入的对象已不在当前场景中') in str(error), str(error)
                locate_result = {'CANCELLED'}
            assert locate_result == {'CANCELLED'}, 'Locate should fail when the imported object was deleted'
            assert not replacement.select_get(), 'Locate selected a same-named replacement object'

            fab_panel.record_import(str(imported_zip), False, '导入失败：fixture')
            assert state.status == '导入失败：fixture' and state.failed, 'Failed direct feedback was not shown'
        finally:
            fab_panel._history_path = original_history_path
            fab_panel._history.clear()
            fab_panel._history.update(original_history)

        # Legacy UI is removed, not merely hidden behind a preference.
        assert not hasattr(bpy.types, 'ATB_PT_companion')
        assert not hasattr(bpy.types.WindowManager, 'atb_companion')
        assert 'fab_show_legacy' not in prefs.bl_rna.properties

        # The running browser keeps the directory captured at launch. Once it exits,
        # the inbox follows the current preference again.
        launch_folder = root / 'browser-start-folder'
        preference_after_exit = root / 'preference-after-exit'
        launch_folder.mkdir()
        preference_after_exit.mkdir()
        prefs.fab_downloads_path = str(launch_folder)
        executable = root / 'fake-browser.exe'
        executable.write_bytes(b'fixture')

        class FakeBrowser:
            running = True

            def poll(self):
                return None if self.running else 0

        fake_browser = FakeBrowser()
        original_browser = fab_panel._browser
        original_browser_folder = fab_panel._browser_folder
        original_executable = fab_panel._browser_executable
        original_popen = fab_panel.subprocess.Popen
        launched = {}

        def fake_popen(args, **kwargs):
            launched['args'] = args
            launched['kwargs'] = kwargs
            return fake_browser

        fab_panel._browser = None
        fab_panel._browser_folder = None
        fab_panel._browser_executable = lambda: executable
        fab_panel.subprocess.Popen = fake_popen
        try:
            assert bpy.ops.atb.fab_local(action='browser') == {'FINISHED'}
            assert launched['args'][-2:] == ['--downloads', str(launch_folder)]
            assert fab_panel._download_folder(bpy.context) == launch_folder
            prefs.fab_downloads_path = str(preference_after_exit)
            assert fab_panel._download_folder(bpy.context) == launch_folder, \
                'Running browser directory changed with the preference'
            fake_browser.running = False
            assert fab_panel._download_folder(bpy.context) == preference_after_exit, \
                'Inbox did not return to the preference directory after browser exit'
        finally:
            fab_panel._browser = original_browser
            fab_panel._browser_folder = original_browser_folder
            fab_panel._browser_executable = original_executable
            fab_panel.subprocess.Popen = original_popen

        # UIList filtering matches either the metadata title or original filename.
        fab_panel._apply(state, [(str(root / 'weathered-rock.zip'), 1, 'search-key',
                                  {'title': 'Weathered Rock', 'detail': 'FBX', 'error': '', 'preview': ''}),
                                 (str(root / 'metal.zip'), 1, 'metal-key',
                                  {'title': 'Metal Panel', 'detail': 'OBJ', 'error': '', 'preview': ''})])
        state.query = 'weathered'
        visible = visible_names()
        assert visible == ['weathered-rock.zip'], f'Search filtering returned unexpected rows: {visible}'

        print('PASS: selection preservation, invalid ZIP error, direct import feedback/history, legacy UI removal, and inbox search')
finally:
    addon_utils.disable(ROOT.name, default_set=False)
