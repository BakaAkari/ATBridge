"""Development-only reload host, intentionally outside the ATBridge package."""
import importlib
import importlib.util
from pathlib import Path
import sys
import threading
import traceback
import bpy
import addon_utils

ROOT = Path(__file__).resolve().parents[1]
HOST = '_atbridge_dev_reload'
_pending = False


def _cleanup_partial(name):
    """Best-effort unwind of a register() that stopped halfway through."""
    current = {k: v for k, v in tuple(sys.modules.items()) if k == name or k.startswith(name + '.')}
    panel = current.get(name + '.ui.fab_panel')
    if panel and hasattr(panel, 'shutdown'):
        # A broken unregister must not leave a timer or worker using old RNA types.
        panel.shutdown()
        if hasattr(bpy.types.WindowManager, 'atb_fab_local'):
            del bpy.types.WindowManager.atb_fab_local
    for key in sorted(current, key=lambda x: x.count('.'), reverse=True):
        module = current[key]
        cleanup = getattr(module, 'unregister', None)
        if cleanup and getattr(cleanup, '__module__', '') == key:
            try:
                cleanup()
            except Exception:
                pass
        for cls in reversed(getattr(module, '_CLASSES', getattr(module, 'classes', ()))):
            if isinstance(cls, type) and getattr(cls, 'is_registered', False):
                try:
                    bpy.utils.unregister_class(cls)
                except Exception:
                    pass
    for attr in dir(bpy.app.handlers):
        handlers = getattr(bpy.app.handlers, attr)
        if isinstance(handlers, list):
            for handler in list(handlers):
                module = getattr(handler, '__module__', '')
                if module == name or module.startswith(name + '.'):
                    handlers.remove(handler)
    for key in current:
        sys.modules.pop(key, None)


def reload_now():
    name = ROOT.name
    old = sys.modules.get(name)
    if old is None or Path(old.__file__).resolve() != ROOT / '__init__.py':
        raise RuntimeError('当前启用的 ATBridge 不是此源码目录')
    props = getattr(bpy.context.window_manager, 'atb_props', None)
    if props and props.running_physics_calculation:
        raise RuntimeError('请先结束物理模拟，再重载插件')
    if any(t.__class__.__name__ == 'QuixelSocketServer' and t.is_alive() for t in threading.enumerate()):
        raise RuntimeError('LiveLink 服务运行中，暂不能安全重载全部模块')

    modules = {k: v for k, v in tuple(sys.modules.items()) if k == name or k.startswith(name + '.')}
    # Fail before unregistering anything when edited source has a syntax error.
    for module in modules.values():
        source = getattr(module, '__file__', None)
        if source and source.endswith('.py') and Path(source).is_file():
            compile(Path(source).read_bytes(), source, 'exec')
    prefs = bpy.context.preferences.addons.get(name)
    saved = {}
    if prefs:
        for prop in prefs.preferences.bl_rna.properties:
            if prop.identifier != 'rna_type' and not prop.is_readonly and prop.type in {'STRING', 'BOOLEAN', 'INT', 'FLOAT', 'ENUM'}:
                saved[prop.identifier] = getattr(prefs.preferences, prop.identifier)
    old_panel = modules.get(name + '.ui.fab_panel')
    runtime = {key: getattr(old_panel, key, None) for key in ('_browser', '_browser_folder', '_last_objects')}
    if runtime['_last_objects'] is not None:
        runtime['_last_objects'] = list(runtime['_last_objects'])
    frame_module = modules.get(name + '.tools.frame_operators')
    frame_callback = getattr(frame_module, 'stop_playback', None)
    looping = frame_callback in bpy.app.handlers.frame_change_pre
    if looping:
        bpy.app.handlers.frame_change_pre.remove(frame_callback)

    errors = []
    addon_utils.disable(name, default_set=False, handle_error=lambda error: errors.append(str(error)))
    registration_error = None
    if errors:
        _cleanup_partial(name)
        sys.modules.update(modules)
        old.register()
        old.__addon_enabled__ = True
        registration_error = '旧版本卸载失败，已恢复先前版本；本次未加载新代码。\n' + '\n'.join(errors)
    else:
        for key, module in modules.items():
            cached = getattr(module, '__cached__', None)
            if cached and ROOT in Path(cached).resolve().parents:
                Path(cached).unlink(missing_ok=True)
            sys.modules.pop(key, None)
        importlib.invalidate_caches()
        fresh = addon_utils.enable(name, default_set=False, persistent=False,
                                   handle_error=lambda error: errors.append(str(error)))
        if fresh is None:
            _cleanup_partial(name)
            sys.modules.update(modules)
            old.register()
            old.__addon_enabled__ = True
            registration_error = '新代码注册失败，已恢复先前版本；修复代码后可再次重载。\n' + '\n'.join(errors)
    prefs = bpy.context.preferences.addons.get(name)
    if prefs:
        for key, value in saved.items():
            if key in prefs.preferences.bl_rna.properties:
                setattr(prefs.preferences, key, value)
    panel = sys.modules[name + '.ui.fab_panel']
    for key, value in runtime.items():
        if value is not None:
            setattr(panel, key, value)
    if looping:
        bpy.app.handlers.frame_change_pre.append(sys.modules[name + '.tools.frame_operators'].stop_playback)
    state = bpy.context.window_manager.atb_fab_local
    state.status = registration_error or '插件已重载 · 当前场景保持不变'
    state.failed = bool(registration_error)
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
    if registration_error:
        raise RuntimeError(registration_error)
    print('[ATBridge DEV] Reloaded source in existing Blender process')


def _deferred():
    global _pending
    _pending = False
    try:
        reload_now()
    except Exception as error:
        traceback.print_exc()
        state = getattr(bpy.context.window_manager, 'atb_fab_local', None)
        if state:
            state.status, state.failed = str(error), True
    return None


class ATB_OT_dev_reload(bpy.types.Operator):
    bl_idname = 'atb.dev_reload'
    bl_label = 'ATBridge Reload Add-on'
    bl_description = 'Reload source in this Blender session without changing the scene. An open native browser keeps its current version.'

    def execute(self, context):
        global _pending
        if not _pending:
            _pending = True
            bpy.app.timers.register(_deferred, first_interval=0.2)
        translator = sys.modules.get(ROOT.name + '.utils.translation')
        text = translator.get_text('正在重载 ATBridge…', context) if translator else 'Reloading ATBridge…'
        self.report({'INFO'}, text)
        return {'FINISHED'}


def install():
    existing = getattr(bpy.types, 'ATB_OT_dev_reload', None)
    if existing:
        return
    bpy.utils.register_class(ATB_OT_dev_reload)


if __name__ == '__main__':
    # Can be executed once from an already-open Blender Python console.
    host = sys.modules.get(HOST)
    if host is not None and bpy.app.timers.is_registered(host._deferred):
        bpy.app.timers.unregister(host._deferred)
    existing = getattr(bpy.types, 'ATB_OT_dev_reload', None)
    if existing:
        bpy.utils.unregister_class(existing)
    spec = importlib.util.spec_from_file_location(HOST, __file__)
    host = importlib.util.module_from_spec(spec)
    sys.modules[HOST] = host
    spec.loader.exec_module(host)
    host.install()
    bpy.ops.atb.dev_reload()
