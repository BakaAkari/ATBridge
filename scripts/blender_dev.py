"""Enable this checkout in a disposable Blender session without installing it."""
from pathlib import Path
import sys
import importlib.util

import addon_utils
import bpy


ROOT = Path(__file__).resolve().parents[1]
# Keep this session from automatically saving its temporary preferences.
bpy.context.preferences.use_preferences_save = False
bpy.context.preferences.view.show_splash = False
sys.path.insert(0, str(ROOT.parent))
addon = addon_utils.enable(ROOT.name, default_set=True, persistent=False)
if addon is None:
    raise RuntimeError("Could not enable ATBridge from " + str(ROOT))
if Path(addon.__file__).resolve() != ROOT / "__init__.py":
    raise RuntimeError("Blender loaded another ATBridge installation: " + addon.__file__)

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.show_region_ui = True

print("[ATBridge DEV] Source: " + str(ROOT))
print("[ATBridge DEV] Open ATBridge > Fab 资产 in the sidebar. Downloads appear automatically.")
spec = importlib.util.spec_from_file_location('_atbridge_dev_reload', ROOT / 'scripts' / 'dev_reload.py')
host = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = host
spec.loader.exec_module(host)
host.install()
print("[ATBridge DEV] Use Reload Plugin or F3 > ATBridge 重载插件 after Python changes.")
