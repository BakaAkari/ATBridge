# ATBridge Fab ZIP 导入操作符
"""
Fab 资产 ZIP 包导入操作符

解压并导入从 Fab 商城下载的 ZIP 资产包。
"""
import bpy
import os
import json
import zipfile
import tempfile
import shutil

from ..state.bridge_state import BridgeState
from ..utils.translation import message_text, get_text
from ..core.import_manager import ImportManager
from ..utils.logger import ATBridgeLogger as log
from ..utils.zip_safety import validate_zip, extract_checked
from ..utils.fab_files import downloads_directory, read_asset_metadata
from ..core.fab_package import analyse


class ATB_OT_import_zip(bpy.types.Operator):
    """导入 Fab 资产 ZIP 文件"""
    
    bl_idname = "atb.import_zip"
    bl_label = "Import Asset ZIP"
    bl_description = "Choose a Fab asset ZIP to import"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")  # type: ignore
    filter_glob: bpy.props.StringProperty(default='*.zip', options={'HIDDEN'})
    
    cache_directory: bpy.props.StringProperty(subtype="DIR_PATH", options={'HIDDEN'})

    def execute(self, context):
        """执行操作符"""
        log.info(f"开始导入 Fab 资产: {self.filepath}")
        from ..ui.fab_panel import record_import
        before = set(context.scene.objects)
        
        # 验证文件
        if not self.filepath.lower().endswith('.zip'):
            log.report_error(self, Exception("无效文件"), get_text("请选择 .zip 文件!"))
            record_import(self.filepath, False, '请选择 .zip 文件')
            return {'CANCELLED'}
        
        context.window_manager.progress_begin(0, 3)
        if context.window:
            context.window.cursor_set('WAIT')
        try:
            if not os.path.isfile(self.filepath):
                raise ValueError('ZIP 文件不存在，请重新选择')
            # 获取解压路径
            fab_path = self._get_fab_assets_path(context)
            os.makedirs(fab_path, exist_ok=True)
            
            # 解压并解析
            asset_data = self._extract_and_parse(fab_path)
            context.window_manager.progress_update(1)
            if not asset_data:
                return {'CANCELLED'}
            
            # 导入资产
            manager = ImportManager()
            success = manager.process_dataset(json.dumps([asset_data]))
            context.window_manager.progress_update(3)
            
            if success:
                added = [obj for obj in context.scene.objects if obj not in before]
                record_import(self.filepath, True,
                              '已导入：%s · 新增 %d 个对象' % (asset_data.get('name', '资产'), len(added)), added)
                log.report_info(self, get_text("成功导入 Fab 资产: ") + asset_data.get("name", "Unknown"))
                return {'FINISHED'}
            else:
                record_import(self.filepath, False, '导入未完成，请检查资产格式和 ATBridge 日志后重试。')
                return {'CANCELLED'}
                
        except Exception as e:
            record_import(self.filepath, False, '导入失败：' + str(e))
            log.report_error(self, e, message_text("导入失败：" + str(e), context))
            return {'CANCELLED'}
        finally:
            context.window_manager.progress_end()
            if context.window:
                context.window.cursor_set('DEFAULT')
    
    def _extract_and_parse(self, fab_path: str) -> dict:
        """解压并解析 ZIP 文件"""
        with zipfile.ZipFile(self.filepath, 'r') as zip_ref:
            validate_zip(zip_ref)
            asset_json = read_asset_metadata(zip_ref)
            # Each import owns its extraction folder; same-named ZIPs cannot mix files.
            target_dir = tempfile.mkdtemp(prefix='fab-', dir=fab_path)
            try:
                extract_checked(zip_ref, target_dir)
                asset_data = self._build_bridge_asset(asset_json, target_dir)
            except Exception:
                shutil.rmtree(target_dir)
                raise
            log.info(f"解压完成: {target_dir}")
        
        # 构建 Megascans 兼容数据
        return asset_data
    
    def _build_bridge_asset(self, asset_json: dict, target_dir: str) -> dict:
        """Analyse the extracted package and build the import description."""
        all_files = [os.path.join(root, f) for root, _, files in os.walk(target_dir) for f in files]
        pkg = analyse(asset_json, all_files)
        if pkg.package_format == 'unsupported':
            raise ValueError('模型格式不支持或缺失，请下载 FBX、OBJ 或 glTF 资产包')
        if pkg.package_format in ('fbx', 'obj') and not (pkg.models or pkg.variants):
            raise ValueError('没有找到可导入的模型文件')
        if pkg.package_format == 'textures' and not pkg.textures:
            raise ValueError('资产包中没有可识别的贴图')
        mesh_list = [{'format': pkg.package_format, 'path': p} for p in pkg.models]
        return {
            'type': pkg.kind,
            'id': pkg.asset_id,
            'name': pkg.name,
            'components': [{'type': t, 'format': os.path.splitext(p)[1][1:].lower(), 'path': p}
                           for t, p in pkg.textures.items()],
            'meshList': mesh_list,
            'variants': [{'name': v.name, 'lods': {str(k): p for k, p in v.lods.items()}} for v in pkg.variants],
            'gltf': pkg.gltf,
            'physicalSize': list(pkg.physical_size) if pkg.physical_size else None,
            'displacementHeight': pkg.displacement_height,
            'resolution': pkg.resolution,
            'categories': asset_json.get('categories', []),
            'tags': asset_json.get('tags', []),
            'category': asset_json.get('category', ''),
            'pbrWorkflow': asset_json.get('pbrWorkflow', 'metalness'),
            'applyToSelection': True,
        }

    def _get_fab_assets_path(self, context) -> str:
        """获取 Fab 资产路径"""
        if self.cache_directory:
            return bpy.path.abspath(self.cache_directory)
        try:
            from ..preferences import get_addon_preferences
            prefs = get_addon_preferences(context)
            if prefs and prefs.fab_assets_path:
                return bpy.path.abspath(prefs.fab_assets_path)
        except Exception:
            pass
        return bpy.utils.user_resource('DATAFILES', path='ATBridge/assets', create=True)
    
    def invoke(self, context, event):
        """调用操作符"""
        if not self.filepath:
            from ..preferences import get_addon_preferences
            prefs = get_addon_preferences(context)
            folder = bpy.path.abspath(prefs.fab_downloads_path) if prefs else str(downloads_directory())
            self.filepath = os.path.join(folder, '')
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
