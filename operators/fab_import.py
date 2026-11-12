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


class ATB_OT_import_zip(bpy.types.Operator):
    """导入 Fab 资产 ZIP 文件"""
    
    bl_idname = "atb.import_zip"
    bl_label = "Import Asset ZIP"
    bl_description = "Choose a Fab asset ZIP to import"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")  # type: ignore
    filter_glob: bpy.props.StringProperty(default='*.zip', options={'HIDDEN'})
    
    cache_directory: bpy.props.StringProperty(subtype="DIR_PATH", options={'HIDDEN'})

    # 贴图类型标准化映射
    BASECOLOR_NAMES = ["basecolor", "albedo", "diffuse", "col", "color"]
    
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
        """构建 Megascans 兼容的资产数据结构"""
        asset_id = asset_json['id']
        
        # 收集所有文件
        all_files = []
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                all_files.append(os.path.join(root, file))
        
        # 解析贴图
        components = []
        seen_components = set()
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
            
            component_key = (map_type, os.path.realpath(found_path))
            if component_key in seen_components:
                continue
            seen_components.add(component_key)
            components.append({
                'type': map_type,
                'format': fmt,
                'path': found_path,
            })
        
        # 解析模型
        mesh_list = []
        seen_meshes = set()
        for m in asset_json.get('models', []):
            if 'uri' not in m:
                continue
            
            uri_lower = m['uri'].lower()
            if uri_lower.endswith('.fbx'):
                mesh_format = 'fbx'
            elif uri_lower.endswith('.obj'):
                mesh_format = 'obj'
            else:
                continue
            
            found_path = self._smart_find_model(all_files, asset_id, mesh_format, m['uri'])
            mesh_key = os.path.realpath(found_path) if found_path else None
            if found_path and mesh_key not in seen_meshes:
                seen_meshes.add(mesh_key)
                mesh_list.append({
                    'format': mesh_format,
                    'path': found_path,
                })
        
        if asset_json.get('models') and not mesh_list:
            raise ValueError('没有找到可明确匹配的 FBX / OBJ 模型；请下载对应格式的单一精度资产包')

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
    
    def _smart_find_model(self, all_files: list, asset_id: str, mesh_format: str, uri: str = "") -> str:
        """智能查找模型文件"""
        asset_id_lower = asset_id.lower()
        ext = '.' + mesh_format.lower()
        
        candidates = []
        for f in all_files:
            fname = os.path.basename(f).lower()
            if asset_id_lower in fname and fname.endswith(ext):
                candidates.append(f)
        
        exact = [f for f in candidates if f.replace(os.sep, '/').endswith('/' + uri)]
        if len(exact) == 1:
            return exact[0]
        named = [f for f in candidates if os.path.basename(f).lower() == os.path.basename(uri).lower()]
        if len(named) == 1:
            return named[0]
        if len(candidates) > 1:
            raise ValueError('Multiple models match metadata; select a single-quality package')
        return candidates[0] if candidates else None
    
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
