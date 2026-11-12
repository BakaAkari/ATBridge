"""Same-process development reload regression."""
from pathlib import Path
import importlib.util
import sys
import os
import builtins
import bpy
import addon_utils
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
bpy.context.preferences.use_preferences_save = False
assert addon_utils.enable(ROOT.name, default_set=True)
spec = importlib.util.spec_from_file_location('_atbridge_dev_reload', ROOT / 'scripts/dev_reload.py')
host = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = host
spec.loader.exec_module(host)
host.install()
objects = list(bpy.context.scene.objects)
pointers = [obj.as_pointer() for obj in objects]
selected_pointers = [obj.as_pointer() for obj in bpy.context.selected_objects]
selected = bpy.context.view_layer.objects.active
prefs = bpy.context.preferences.addons[ROOT.name].preferences
prefs.fab_downloads_path = str(ROOT)
prefs.fab_assets_path = str(ROOT / 'test-assets-cache')
old_module = sys.modules[ROOT.name + '.ui.fab_panel']
old_module._last_objects = [selected]
pid = os.getpid()

def assert_live_state(expected_module=None):
    assert os.getpid() == pid
    assert [obj.as_pointer() for obj in bpy.context.scene.objects] == pointers
    assert [obj.as_pointer() for obj in bpy.context.selected_objects] == selected_pointers
    assert bpy.context.view_layer.objects.active == selected
    current_prefs = bpy.context.preferences.addons[ROOT.name].preferences
    assert current_prefs.fab_downloads_path == str(ROOT)
    assert current_prefs.fab_assets_path == str(ROOT / 'test-assets-cache')
    if expected_module is not None:
        assert sys.modules[ROOT.name] is expected_module
    assert hasattr(bpy.types, 'ATB_PT_fab_local')

for i in range(3):
    host.reload_now()
    assert_live_state()
    fresh = sys.modules[ROOT.name + '.ui.fab_panel']
    assert fresh is not old_module
    assert fresh._last_objects == [selected]
    assert hasattr(bpy.types, 'ATB_OT_dev_reload')
    assert len([h for h in bpy.app.handlers.load_post if h.__module__ == ROOT.name]) == 1
    old_module = fresh
# Registration failure after some classes exist restores the prior usable module set.
real_enable = addon_utils.enable
previous = sys.modules[ROOT.name]
def fail_halfway(name, **kwargs):
    import importlib
    partial = importlib.import_module(name)
    partial.properties.register()
    partial.preferences.register()
    partial.ui.fab_panel.register()
    return None
addon_utils.enable = fail_halfway
try:
    try:
        host.reload_now()
        raise AssertionError('Expected registration failure')
    except RuntimeError as error:
        assert '已恢复先前版本' in str(error)
    assert sys.modules[ROOT.name] is previous
    assert_live_state(previous)
finally:
    addon_utils.enable = real_enable
host.reload_now()

# Syntax preflight failure must leave the currently registered version untouched.
preflight_module = sys.modules[ROOT.name]
real_compile = builtins.compile
def fail_preflight(source, filename, mode, *args, **kwargs):
    if Path(filename).resolve() == (ROOT / '__init__.py').resolve():
        raise SyntaxError('injected preflight syntax failure')
    return real_compile(source, filename, mode, *args, **kwargs)
builtins.compile = fail_preflight
try:
    try:
        host.reload_now()
        raise AssertionError('Expected syntax preflight failure')
    except SyntaxError as error:
        assert 'injected preflight' in str(error)
    assert_live_state(preflight_module)
finally:
    builtins.compile = real_compile

# Inject one real Blender class-registration failure late in a fresh registration.
# The failed registration must roll back to the old module, then a later reload works.
previous = sys.modules[ROOT.name]
real_register_class = bpy.utils.register_class
registered_before_failure = []
failure_injected = False
def fail_late_once(cls):
    global failure_injected
    if not failure_injected and cls.__name__ == 'ATB_PT_fab_local':
        failure_injected = True
        raise RuntimeError('injected late register_class failure')
    result = real_register_class(cls)
    registered_before_failure.append(cls.__name__)
    return result
bpy.utils.register_class = fail_late_once
try:
    try:
        host.reload_now()
        raise AssertionError('Expected one-shot register_class failure')
    except RuntimeError as error:
        assert '已恢复先前版本' in str(error), str(error)
    assert failure_injected, 'The intended late register_class failure was not triggered'
    assert 'ATB_FabLocalFile' in registered_before_failure, 'Failure was not late in addon registration'
    assert sys.modules[ROOT.name] is previous
    assert_live_state(previous)
    host.reload_now()
    assert sys.modules[ROOT.name] is not previous
    assert_live_state()
finally:
    bpy.utils.register_class = real_register_class

# A broken old-version unregister is reported, cleaned up, and rolled back. Its
# executor is explicitly shut down before the old modules are re-registered.
previous = sys.modules[ROOT.name]
old_panel = sys.modules[ROOT.name + '.ui.fab_panel']
original_unregister = old_panel.unregister
old_executor = old_panel._executor
handler_counts = {
    attr: len(value) for attr in dir(bpy.app.handlers)
    if isinstance((value := getattr(bpy.app.handlers, attr)), list)
}
timer_was_registered = bpy.app.timers.is_registered(old_panel._pump)
unregister_failed = False
def fail_unregister_once():
    global unregister_failed
    if not unregister_failed:
        unregister_failed = True
        raise RuntimeError('injected old panel unregister failure')
    return original_unregister()
old_panel.unregister = fail_unregister_once
try:
    try:
        host.reload_now()
        raise AssertionError('Expected old unregister failure')
    except RuntimeError as error:
        assert '旧版本卸载失败' in str(error), str(error)
    assert unregister_failed, 'Old fab_panel.unregister was not called'
    assert old_executor._shutdown, 'Old Fab inbox executor was not shut down'
    assert sys.modules[ROOT.name] is previous
    assert_live_state(previous)
    current_handler_counts = {
        attr: len(value) for attr in dir(bpy.app.handlers)
        if isinstance((value := getattr(bpy.app.handlers, attr)), list)
    }
    assert current_handler_counts == handler_counts, \
        f'Handler callback counts changed across failed unload: {handler_counts} -> {current_handler_counts}'
    assert bpy.app.timers.is_registered(old_panel._pump) == timer_was_registered
finally:
    old_panel.unregister = original_unregister

host.reload_now()
assert_live_state()
addon_utils.disable(ROOT.name, default_set=True)
print('PASS: 3 reload cycles, syntax preflight, late registration rollback/recovery, old unregister failure cleanup/recovery; scene identities/selection/preferences retained')
