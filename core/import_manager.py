# ATBridge 导入管理器
"""
资产导入流程管理模块

整合解析、导入、材质构建等流程，替代原有的 MS_Init_ImportProcess 类。
"""
import re

import bpy
from typing import List, Optional, Tuple

from .asset_parser import AssetParser, AssetData, MeshInfo
from .geometry_importer import GeometryImporter
from .material_builder import MaterialBuilder
from .node_factory import NodeFactory
from ..config import BridgeConfig
from ..utils.logger import ATBridgeLogger as log


class ImportManager:
    """资产导入管理器"""
    
    def __init__(self):
        """初始化导入管理器"""
        self.alembic_paths: List[List[str]] = []
        self.alembic_materials: List[bpy.types.Material] = []
    
    def process_dataset(self, json_data) -> bool:
        """
        处理完整的资产数据集
        
        Args:
            json_data: Megascans JSON 格式字符串或 bytes
        
        Returns:
            成功导入返回 True
        """
        try:
            # 处理 bytes 输入
            if isinstance(json_data, bytes):
                json_str = json_data.decode('utf-8')
            else:
                json_str = json_data
            
            # 解析资产
            assets = AssetParser.parse_json(json_str)
            if not assets:
                log.warning("没有解析到任何资产")
                return False
            
            # 逐个导入
            for asset in assets:
                self._import_single_asset(asset)
            
            log.info(f"成功导入 {len(assets)} 个资产")
            return True
            
        except Exception as e:
            log.error("资产导入失败", e)
            return False
    
    # Texture-only packages: material only, shown on the selection or a plane of real size.
    TEXTURE_KINDS = ('surface', 'decal', 'atlas', 'imperfection')

    def _import_single_asset(self, asset: AssetData) -> None:
        """
        导入单个资产

        Args:
            asset: 解析后的资产数据
        """
        log.info(f"正在导入: {asset.name} (类型: {asset.type})")
        selected = [o for o in bpy.context.selected_objects if o.type == 'MESH']

        if asset.type == 'brush':
            self._import_brush(asset)
            return
        if asset.gltf:
            self._import_gltf(asset, selected)
            return

        # 导入几何体（记录导入前已有的材质和图像，便于清理 FBX/OBJ 自带的数据）
        materials_before = {m.as_pointer() for m in bpy.data.materials}
        images_before = {i.as_pointer() for i in bpy.data.images}
        meshes_before = {m.as_pointer() for m in bpy.data.meshes}
        if asset.variants:
            objects, abc_paths = self._import_variants(asset), []
        else:
            objects, abc_paths = GeometryImporter.import_meshes(asset.meshes)

        if (asset.meshes or asset.variants) and not objects and not abc_paths:
            raise ValueError('No model objects were imported')

        # 构建材质
        builder = MaterialBuilder(asset)
        material = builder.build()

        replace_all = True
        if asset.type in self.TEXTURE_KINDS and not objects:
            objects, replace_all = (selected, False) if selected else ([self._create_plane(asset)], True)
        # 赋予材质
        self._apply_material(objects, material, asset.type, replace_all)
        self._remove_import_leftovers(materials_before, images_before, material, meshes_before)

        # 处理特殊资产类型
        if asset.is_scatter and len(objects) > 1:
            self._setup_parent(asset, objects, 'Scatter')
        elif asset.type == BridgeConfig.ASSET_TYPE_3DPLANT and len(objects) > 1:
            self._setup_parent(asset, objects, 'Plant')

        # 记录 Alembic 数据（延迟导入）
        if abc_paths:
            self.alembic_paths.append(abc_paths)
            self.alembic_materials.append(material)

        log.info(f"导入完成: {asset.name}")

    def _import_variants(self, asset: AssetData) -> List[bpy.types.Object]:
        """Plants: import the most detailed LOD of every variant and line them up along X."""
        objects: List[bpy.types.Object] = []
        x = 0.0
        cursor = bpy.context.scene.cursor.location.copy()
        for variant in asset.variants:
            lods = {int(k): v for k, v in variant['lods'].items()}
            path = lods[min(lods)]
            fmt = 'obj' if path.lower().endswith('.obj') else 'fbx'
            imported, _ = GeometryImporter.import_meshes([MeshInfo(format=fmt, path=path)])
            meshes = [o for o in imported if o.type == 'MESH']
            if not meshes:
                continue
            width = max(max(o.dimensions.x for o in meshes), 0.1)
            for obj in imported:
                if obj.parent is None:
                    obj.location = (cursor.x + x + width / 2, cursor.y, cursor.z)
            for obj in meshes:
                obj.name = f"{asset.name}_{variant['name']}"
            x += width * 1.2
            objects.extend(imported)
        return objects

    def _create_plane(self, asset: AssetData) -> bpy.types.Object:
        """A plane of the scanned size, so a texture-only asset is visible right away."""
        size = asset.physical_size or (1.0, 1.0)
        mesh = bpy.data.meshes.new(asset.name)
        hx, hy = size[0] / 2, size[1] / 2
        mesh.from_pydata([(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0)], [], [(0, 1, 2, 3)])
        uv = mesh.uv_layers.new(name='UVMap')
        for loop, co in zip(mesh.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            uv.data[loop.index].uv = co
        mesh.update()
        obj = bpy.data.objects.new(asset.name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.location = bpy.context.scene.cursor.location
        for other in bpy.context.selected_objects:
            other.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        return obj

    def _import_gltf(self, asset: AssetData, selected) -> None:
        """glTF packages carry their own material setup (UE-packed ORM/B-O maps); Blender's importer handles it."""
        materials_before = {m.as_pointer() for m in bpy.data.materials}
        images_before = {i.as_pointer() for i in bpy.data.images}
        meshes_before = {m.as_pointer() for m in bpy.data.meshes}
        objects = GeometryImporter.import_gltf(asset.gltf)
        # Plant glTFs hold every variant with all LODs (the last LOD is a billboard): keep the most
        # detailed LOD of each variant, like the FBX path, and line the variants up.
        lod = lambda o: int(m.group(1)) if (m := re.search(r'_LOD(\d+)(?:\.\d{3})?$', o.name)) else 0
        drop = [o for o in objects if o.type == 'MESH' and lod(o) > 0]
        for obj in drop:
            bpy.data.objects.remove(obj)
        objects = [o for o in objects if o not in drop]
        meshes = [o for o in objects if o.type == 'MESH']
        if not meshes:
            raise ValueError('glTF 文件中没有模型')
        if asset.type == BridgeConfig.ASSET_TYPE_3DPLANT and len(meshes) > 1:
            x, cursor = 0.0, bpy.context.scene.cursor.location
            for obj in sorted(meshes, key=lambda o: o.name):
                width = max(obj.dimensions.x, 0.1)
                obj.location = (cursor.x + x + width / 2, cursor.y, cursor.z)
                x += width * 1.2
        materials = {slot.material for o in meshes for slot in o.material_slots if slot.material}
        self._remove_import_leftovers(materials_before, images_before, None, meshes_before)
        for i, mat in enumerate(sorted(materials, key=lambda m: m.name)):
            mat.name = asset.material_name if len(materials) == 1 else f"{asset.material_name}_{i + 1}"
        if asset.type in self.TEXTURE_KINDS and selected and len(materials) == 1:
            # The glTF holds a preview plane; apply its material to the user's selection instead.
            mat = next(iter(materials))
            for obj in objects:
                bpy.data.objects.remove(obj)
            self._apply_material(selected, mat, asset.type, replace_all=False)
            self._remove_import_leftovers(materials_before, images_before, mat, meshes_before)
            return
        roots = [o for o in objects if o.parent is None]
        if len(roots) > 1:
            self._setup_parent(asset, roots, 'glTF')

    def _import_brush(self, asset: AssetData) -> None:
        """Brush packages are alpha stamps: load them as an image texture and a texture-paint brush.
        Only datablocks ATBridge created for this asset id are reused; same-named user data is left alone."""
        path = asset.get_texture_path('brush')
        if not path:
            raise ValueError('笔刷资产中没有可用的笔刷贴图')
        image = NodeFactory.load_image(path, BridgeConfig.COLORSPACE_NON_COLOR)
        tag = 'atb_asset'
        texture = next((t for t in bpy.data.textures if t.get(tag) == asset.id), None)
        if texture is None:
            texture = bpy.data.textures.new(asset.name, 'IMAGE')
            texture[tag] = asset.id
        texture.image = image
        try:
            brush = next((b for b in bpy.data.brushes if b.get(tag) == asset.id), None)
            if brush is None:
                brush = bpy.data.brushes.new(asset.name, mode='TEXTURE_PAINT')
                brush[tag] = asset.id
            brush.texture = texture
        except (TypeError, RuntimeError, AttributeError) as error:
            log.warning(f"无法创建纹理绘制笔刷，已保留图像纹理: {error}")
        log.info(f"笔刷已导入为图像纹理: {texture.name}")

    def _apply_material(self, objects: List[bpy.types.Object],
                       material: bpy.types.Material,
                       asset_type: str, replace_all: bool = True) -> None:
        """
        为对象应用材质
        
        Args:
            objects: 对象列表
            material: 材质
            asset_type: 资产类型
        """
        for obj in objects:
            if obj.type != 'MESH':
                continue
            if replace_all and obj.material_slots:
                # Imported models: Megascans assets use one material; replace every slot the file created.
                for slot in obj.material_slots:
                    slot.material = material
            else:
                # The user's own objects: only the active slot changes.
                obj.active_material = material
    
    @staticmethod
    def _remove_import_leftovers(materials_before, images_before, keep, meshes_before=None) -> None:
        """Delete meshes/materials/images that this import created and nothing uses any more
        (meshes first: an orphan mesh would otherwise keep its material and images alive)."""
        if meshes_before is not None:
            for mesh in [m for m in bpy.data.meshes if m.as_pointer() not in meshes_before]:
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
        for mat in [m for m in bpy.data.materials if m.as_pointer() not in materials_before]:
            if mat != keep and mat.users == 0:
                log.debug(f"移除模型文件自带的未使用材质: {mat.name}")
                bpy.data.materials.remove(mat)
        for img in [i for i in bpy.data.images if i.as_pointer() not in images_before]:
            if img.users == 0:
                bpy.data.images.remove(img)

    def _setup_parent(self, asset: AssetData,
                     objects: List[bpy.types.Object],
                     parent_type: str) -> None:
        """
        创建空对象作为父级
        
        Args:
            asset: 资产数据
            objects: 子对象列表
            parent_type: 父对象类型描述
        """
        bpy.ops.object.empty_add(type='ARROWS')
        parent = bpy.context.active_object
        bpy.context.view_layer.update()   # fresh matrix_world for the moved objects and the new empty
        parent.name = f"{asset.id}_{asset.name}"
        
        for obj in objects:
            world = obj.matrix_world.copy()
            obj.parent = parent
            obj.matrix_world = world   # objects are already placed in world space
        
        log.debug(f"创建 {parent_type} 父对象: {parent.name}")
    
    def get_alembic_data(self) -> Tuple[List[List[str]], List[bpy.types.Material]]:
        """
        获取待导入的 Alembic 数据
        
        Returns:
            (alembic_paths, materials) 元组
        """
        return self.alembic_paths, self.alembic_materials
    
    def has_pending_alembic(self) -> bool:
        """检查是否有待导入的 Alembic"""
        return len(self.alembic_paths) > 0
