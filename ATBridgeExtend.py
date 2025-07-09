import bpy
import os
import zipfile
from bpy.utils import register_class, unregister_class
from bpy.types import AddonPreferences

# 插件首选项
class AT_AddonPreferences(AddonPreferences):
    bl_idname = "ATBridge"

    fab_assets_path: bpy.props.StringProperty(
        name="Fab Assets Path",
        description="Specify the path to the Fab Assets",
        subtype='DIR_PATH',
        default="D:/FabAssets"
    ) # type: ignore

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "fab_assets_path")

# ZIP导入操作符
class ATB_OT_import_zip(bpy.types.Operator):
    bl_idname = "atb.import_zip"
    bl_label = "Import Fab Asset"
    bl_description = "Select Fab Assets ZIP file to import assets"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH") # type: ignore

    def execute(self, context):
        if not self.filepath.lower().endswith('.zip'):
            self.report({'ERROR'}, "Please select a .zip file!")
            return {'CANCELLED'}
        try:
            with zipfile.ZipFile(self.filepath, 'r') as zip_ref:
                json_files = [f for f in zip_ref.namelist() if f.lower().endswith('.json')]
                if not json_files:
                    self.report({'ERROR'}, "No .json file found in the ZIP file!")
                    return {'CANCELLED'}
                with zip_ref.open(json_files[0]) as json_file:
                    import json
                    try:
                        json_data = json.load(json_file)
                    except Exception as e:
                        self.report({'ERROR'}, f"Failed to parse JSON file: {e}")
                        return {'CANCELLED'}
                    asset_id = json_data.get('id')
                    if not asset_id:
                        self.report({'ERROR'}, "No 'id' field found in the JSON file!")
                        return {'CANCELLED'}
                    zip_filename = os.path.basename(self.filepath)
                    if asset_id not in zip_filename:
                        self.report({'ERROR'}, f"id '{asset_id}' not found in the ZIP file name!")
                        return {'CANCELLED'}
                    fab_assets_path = None
                    prefs = context.preferences.addons.get("ATBridge")
                    if prefs is not None:
                        fab_assets_path = prefs.preferences.fab_assets_path
                    if not fab_assets_path:
                        self.report({'ERROR'}, "Fab Assets Path not found, cannot unzip!")
                        return {'CANCELLED'}
                    target_dir = os.path.join(fab_assets_path, os.path.splitext(zip_filename)[0])
                    os.makedirs(target_dir, exist_ok=True)
                    zip_ref.extractall(target_dir)
                    json_files = [f for f in os.listdir(target_dir) if f.lower().endswith('.json')]
                    if not json_files:
                        self.report({'ERROR'}, "No .json file found in the unzipped directory, cannot import automatically!")
                        return {'CANCELLED'}
                    json_path = os.path.join(target_dir, json_files[0])
                    try:
                        import json
                        with open(json_path, 'r', encoding='utf-8') as f:
                            asset = json.load(f)
                        all_files = []
                        for root, dirs, files in os.walk(target_dir):
                            for file in files:
                                all_files.append(os.path.join(root, file))
                        def smart_find_file(asset_id, map_name, exts=None):
                            asset_id = asset_id.lower()
                            map_name = map_name.lower()
                            candidates = []
                            for f in all_files:
                                fname = os.path.basename(f).lower()
                                if asset_id in fname and map_name in fname:
                                    if exts:
                                        if any(fname.endswith(ext.lower()) for ext in exts):
                                            candidates.append(f)
                                    else:
                                        candidates.append(f)
                            if candidates:
                                return sorted(candidates, key=len)[0]
                            return None
                        def smart_find_model(asset_id, mesh_format):
                            asset_id = asset_id.lower()
                            mesh_format = mesh_format.lower()
                            candidates = []
                            for f in all_files:
                                fname = os.path.basename(f).lower()
                                if asset_id in fname and fname.endswith('.' + mesh_format):
                                    candidates.append(f)
                            if candidates:
                                return sorted(candidates, key=len)[0]
                            return None
                        BASECOLOR_NAMES = ["basecolor", "albedo", "diffuse", "col", "color"]
                        components = []
                        for m in asset.get('maps', []):
                            if 'uri' not in m:
                                continue
                            comp = dict(m)
                            comp['path'] = smart_find_file(asset['id'], m.get('name', m.get('type', 'unknown')))
                            # 统一basecolor同义词为albedo
                            map_type = m.get('type', m.get('name', 'unknown')).lower()
                            if map_type in BASECOLOR_NAMES:
                                comp['type'] = 'albedo'
                            else:
                                comp['type'] = map_type
                            # 自动补充format字段
                            if 'format' not in comp:
                                if 'mimeType' in comp:
                                    comp['format'] = comp['mimeType'].split('/')[-1]
                                else:
                                    ext = os.path.splitext(m['uri'])[1].lower()
                                    comp['format'] = ext[1:] if ext.startswith('.') else ext
                            components.append(comp)
                        meshList = []
                        for m in asset.get('models', []):
                            if 'uri' not in m:
                                continue
                            if not m['uri'].lower().endswith(('.fbx', '.obj', '.abc')):
                                continue
                            mesh_format = 'fbx' if m['uri'].lower().endswith('.fbx') else (
                                'obj' if m['uri'].lower().endswith('.obj') else (
                                    'abc' if m['uri'].lower().endswith('.abc') else 'unknown'
                                )
                            )
                            found_path = smart_find_model(asset['id'], mesh_format)
                            if not found_path:
                                continue
                            mesh = dict(m)
                            mesh['path'] = found_path
                            mesh['format'] = mesh_format
                            meshList.append(mesh)
                        bridge_asset = {
                            "type": asset.get("categories", ["3d"])[0].lower(),
                            "id": asset["id"],
                            "name": asset["name"],
                            "components": components,
                            "meshList": meshList,
                            "categories": asset.get("categories", ["3d"]),
                            "tags": asset.get("tags", []),
                            "category": asset.get("category", ""),
                            "activeLOD": asset.get("activeLOD", ""),
                            "minLOD": asset.get("minLOD", ""),
                            "pbrWorkflow": asset.get("pbrWorkflow", "specular"),
                            "scatter": asset.get("scatter", False),
                        }
                        json_str = json.dumps([bridge_asset], ensure_ascii=False)
                        from .ATBridge import BridgeState, MS_Init_ImportProcess
                        BridgeState.set_Megascans_DataSet(json_str)
                        MS_Init_ImportProcess()
                    except Exception as e:
                        self.report({'ERROR'}, f"Automatic import failed: {e}")
                        return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to read ZIP file: {e}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Selected file: {self.filepath}")
        # 这里可以添加后续的zip处理逻辑
        return {'FINISHED'}

    def invoke(self, context, event):
        # 检查首选项中是否设置了Fab Assets Path
        prefs = context.preferences.addons.get("ATBridge")
        fab_assets_path = None
        if prefs is not None:
            fab_assets_path = prefs.preferences.fab_assets_path
        if not fab_assets_path:
            self.report({'ERROR'}, "Please set the Fab Assets Path in the plugin preferences!")
            return {'CANCELLED'}
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# 注册所有类
classes = (
    AT_AddonPreferences,
    ATB_OT_import_zip,
)

def register():
    global classes
    for cls in classes:
        register_class(cls)

def unregister():
    global classes
    for cls in classes:
        unregister_class(cls)

if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register() 