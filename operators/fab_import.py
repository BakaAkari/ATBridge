# ATBridge Fab ZIP 导入操作符
"""
Fab 资产 ZIP 包导入操作符

解压并导入从 Fab 商城下载的 ZIP 资产包。
"""
import bpy
import os
import json
import zipfile

from ..state.bridge_state import BridgeState
from ..core.import_manager import ImportManager
from ..utils.logger import ATBridgeLogger as log


class ATB_OT_import_zip(bpy.types.Operator):
    """导入 Fab 资产 ZIP 文件"""
    
    bl_idname = "atb.import_zip"
    bl_label = "Import Fab Asset"
    bl_description = "选择 Fab 资产 ZIP 文件进行导入"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")  # type: ignore
    
    # 贴图类型标准化映射
    BASECOLOR_NAMES = ["basecolor", "albedo", "diffuse", "col", "color"]
    
    def execute(self, context):
        """执行操作符"""
        log.info(f"开始导入 Fab 资产: {self.filepath}")
        
        # 验证文件
        if not self.filepath.lower().endswith('.zip'):
            log.report_error(self, Exception("无效文件"), "请选择 .zip 文件!")
            return {'CANCELLED'}
        
        try:
            # 获取解压路径
            fab_path = self._get_fab_assets_path(context)
            if not fab_path or not os.path.isdir(fab_path):
                log.report_error(self, Exception("路径未设置"), 
                               "请在插件首选项中设置有效的 Fab Assets Path")
                return {'CANCELLED'}
            
            # 解压并解析
            asset_data = self._extract_and_parse(fab_path)
            if not asset_data:
                return {'CANCELLED'}
            
            # 导入资产
            manager = ImportManager()
            success = manager.process_dataset(json.dumps([asset_data]))
            
            if success:
                log.report_info(self, f"成功导入 Fab 资产: {asset_data.get('name', 'Unknown')}")
                return {'FINISHED'}
            else:
                return {'CANCELLED'}
                
        except Exception as e:
            log.report_error(self, e, f"导入失败: {e}")
            return {'CANCELLED'}
    
    def _extract_and_parse(self, fab_path: str) -> dict:
        """解压并解析 ZIP 文件"""
        with zipfile.ZipFile(self.filepath, 'r') as zip_ref:
            # 查找 JSON 文件
            json_files = [f for f in zip_ref.namelist() if f.lower().endswith('.json')]
            if not json_files:
                log.report_error(self, Exception("无 JSON"), "ZIP 中找不到 .json 文件!")
                return None
            
            # 解析 JSON
            with zip_ref.open(json_files[0]) as json_file:
                asset_json = json.load(json_file)
            
            asset_id = asset_json.get('id')
            if not asset_id:
                log.report_error(self, Exception("无 ID"), "JSON 中找不到 'id' 字段!")
                return None
            
            # 验证文件名
            zip_filename = os.path.basename(self.filepath)
            if asset_id not in zip_filename:
                log.report_error(self, Exception("ID 不匹配"), 
                               f"ZIP 文件名不包含资产 ID: {asset_id}")
                return None
            
            # 创建目标目录并解压
            target_dir = os.path.join(fab_path, os.path.splitext(zip_filename)[0])
            os.makedirs(target_dir, exist_ok=True)
            zip_ref.extractall(target_dir)
            log.info(f"解压完成: {target_dir}")
        
        # 构建 Megascans 兼容数据
        return self._build_bridge_asset(asset_json, target_dir)
    
    def _build_bridge_asset(self, asset_json: dict, target_dir: str) -> dict:
        """构建 Megascans 兼容的资产数据结构"""
        asset_id = asset_json['id']
        
        # 收集所有文件
        all_files = []
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                all_files.append(os.path.join(root, file))
        
        # 解析贴图
        components = []
        for m in asset_json.get('maps', []):
            if 'uri' not in m:
                continue
            
            # 智能查找文件
            map_name = m.get('name', m.get('type', 'unknown'))
            found_path = self._smart_find_file(all_files, asset_id, map_name)
            if not found_path:
                continue
            
            # 标准化类型
            map_type = m.get('type', map_name).lower()
            if map_type in self.BASECOLOR_NAMES:
                map_type = 'albedo'
            
            # 确定格式
            if 'format' in m:
                fmt = m['format']
            elif 'mimeType' in m:
                fmt = m['mimeType'].split('/')[-1]
            else:
                ext = os.path.splitext(m['uri'])[1].lower()
                fmt = ext[1:] if ext.startswith('.') else ext
            
            components.append({
                'type': map_type,
                'format': fmt,
                'path': found_path,
            })
        
        # 解析模型
        mesh_list = []
        for m in asset_json.get('models', []):
            if 'uri' not in m:
                continue
            
            uri_lower = m['uri'].lower()
            if uri_lower.endswith('.fbx'):
                mesh_format = 'fbx'
            elif uri_lower.endswith('.obj'):
                mesh_format = 'obj'
            elif uri_lower.endswith('.abc'):
                mesh_format = 'abc'
            else:
                continue
            
            found_path = self._smart_find_model(all_files, asset_id, mesh_format)
            if found_path:
                mesh_list.append({
                    'format': mesh_format,
                    'path': found_path,
                })
        
        # 安全获取资产名称
        asset_name = (asset_json.get('name') or 
                     asset_json.get('displayName') or 
                     asset_json.get('title') or 
                     asset_id)
        
        # 构建最终数据
        return {
            'type': asset_json.get('categories', ['3d'])[0].lower(),
            'id': asset_id,
            'name': asset_name,
            'components': components,
            'meshList': mesh_list,
            'categories': asset_json.get('categories', ['3d']),
            'tags': asset_json.get('tags', []),
            'category': asset_json.get('category', ''),
            'activeLOD': asset_json.get('activeLOD', ''),
            'minLOD': asset_json.get('minLOD', ''),
            'pbrWorkflow': asset_json.get('pbrWorkflow', 'metalness'),
            'applyToSelection': True,
        }
    
    def _smart_find_file(self, all_files: list, asset_id: str, map_name: str) -> str:
        """智能查找贴图文件"""
        asset_id_lower = asset_id.lower()
        map_name_lower = map_name.lower()
        
        candidates = []
        for f in all_files:
            fname = os.path.basename(f).lower()
            if asset_id_lower in fname and map_name_lower in fname:
                candidates.append(f)
        
        return sorted(candidates, key=len)[0] if candidates else None
    
    def _smart_find_model(self, all_files: list, asset_id: str, mesh_format: str) -> str:
        """智能查找模型文件"""
        asset_id_lower = asset_id.lower()
        ext = '.' + mesh_format.lower()
        
        candidates = []
        for f in all_files:
            fname = os.path.basename(f).lower()
            if asset_id_lower in fname and fname.endswith(ext):
                candidates.append(f)
        
        return sorted(candidates, key=len)[0] if candidates else None
    
    def _get_fab_assets_path(self, context) -> str:
        """获取 Fab 资产路径"""
        try:
            from ..preferences import get_addon_preferences
            prefs = get_addon_preferences(context)
            if prefs:
                return prefs.fab_assets_path
        except Exception:
            pass
        return ''
    
    def invoke(self, context, event):
        """调用操作符"""
        fab_path = self._get_fab_assets_path(context)
        if not fab_path or not os.path.isdir(fab_path):
            log.report_error(self, Exception("路径未设置"),
                           "请先在插件首选项中设置 Fab Assets Path")
            return {'CANCELLED'}
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
