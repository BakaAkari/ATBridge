# ATBridge 材质构建器
"""
材质节点图构建模块

负责根据资产数据创建完整的 PBR 材质节点图。节点按通道登记，
全部创建完成后交给 node_layout 统一排布。
"""
import os

import bpy
from typing import Dict, List, Optional

from .asset_parser import AssetData
from .node_factory import NodeFactory
from .node_layout import FRAME_TAG, OWNED_TAG, ROLE_TAG, layout_material
from ..compat.blender_compat import BlenderCompat
from ..config import BridgeConfig
from ..utils.logger import ATBridgeLogger as log
from ..utils.translation import get_text

# Channel order follows the Principled BSDF input order, top to bottom.
CHANNEL_ORDER = ['color', 'metallic', 'roughness', 'opacity', 'transmission', 'translucency', 'sheen',
                 'normal', 'displacement', 'mask']
CHANNEL_LABELS = {
    'mapping': 'UV Mapping', 'color': 'Base Color', 'metallic': 'Metallic', 'roughness': 'Roughness',
    'opacity': 'Opacity', 'transmission': 'Transmission', 'normal': 'Normal', 'displacement': 'Displacement',
    'translucency': 'Translucency', 'sheen': 'Sheen', 'mask': 'Mask',
}
# Node labels shown on image nodes instead of long file names.
TEXTURE_LABELS = {
    'albedo': 'Base Color', 'ao': 'Ambient Occlusion', 'metalness': 'Metallic', 'roughness': 'Roughness',
    'gloss': 'Gloss', 'opacity': 'Opacity', 'transmission': 'Transmission', 'normal': 'Normal',
    'bump': 'Bump', 'displacement': 'Displacement', 'translucency': 'Translucency', 'fuzz': 'Fuzz', 'mask': 'Mask',
}


class MaterialBuilder:
    """材质构建器"""

    def __init__(self, asset: AssetData):
        """
        初始化材质构建器

        Args:
            asset: 解析后的资产数据
        """
        self.asset = asset
        self.mat: Optional[bpy.types.Material] = None
        self.factory: Optional[NodeFactory] = None
        self.bsdf_node: Optional[bpy.types.Node] = None
        self.output_node: Optional[bpy.types.Node] = None
        self.reroute: Optional[bpy.types.Node] = None
        self.mapping_nodes: List[bpy.types.Node] = []
        self.channels: Dict[str, Dict[str, List]] = {}
        self.tex_count = 0
        self.owns_shader = True
        self.owns_output = True
        self.post_columns: List[List[bpy.types.Node]] = []
        self.stack_output = None

    def build(self) -> bpy.types.Material:
        """
        构建完整材质

        Returns:
            创建的材质
        """
        log.info(f"构建材质: {self.asset.material_name}")

        self._check_texture_files()
        existing = bpy.data.materials.get(self.asset.material_name)
        images_before = {i.as_pointer() for i in bpy.data.images}
        snapshot = self._snapshot(existing) if existing else None
        # Rebuild transactionally: the previous ATBridge nodes stay in place while the new ones
        # are built, and are only swapped out once everything succeeded. On failure the material
        # (nodes, links incl. mute state, render settings, names) is restored exactly.
        previous, kept = [], []
        try:
            self._create_material()
            tree = self.mat.node_tree
            previous = [n for n in tree.nodes if FRAME_TAG in n and n not in (self.bsdf_node, self.output_node)]
            for node in previous:
                node.name = '_atb_old_' + node.name
            self._setup_mapping()
            self._setup_textures()
            kept = self._carry_over_user_links(previous, snapshot)
        except Exception:
            if existing is not None:
                self._restore(snapshot)
            elif self.mat is not None:
                bpy.data.materials.remove(self.mat)
                self.mat = None
            for img in [i for i in bpy.data.images if i.as_pointer() not in images_before]:
                if img.users == 0:
                    bpy.data.images.remove(img)
            raise
        tree = self.mat.node_tree
        for node in previous:
            if node not in kept:
                tree.nodes.remove(node)
        self._layout()

        log.debug(f"材质构建完成, 贴图节点数: {self.tex_count}")
        return self.mat

    def _create_material(self) -> None:
        """创建或获取材质"""
        name = self.asset.material_name
        existing = bpy.data.materials.get(name)
        self.mat = existing or bpy.data.materials.new(name)
        self.mat.use_nodes = True
        pre_existing = {n.as_pointer() for n in self.mat.node_tree.nodes}

        self.factory = NodeFactory(self.mat.node_tree)
        # Default node names are translated when Blender translates new data names.
        # Node identifiers remain stable across interface languages and user renames.
        nodes = self.mat.node_tree.nodes
        self.output_node = next((node for node in nodes if node.bl_idname == 'ShaderNodeOutputMaterial'
                                 and node.is_active_output), None)
        if self.output_node is None:
            self.output_node = next((node for node in nodes if node.bl_idname == 'ShaderNodeOutputMaterial'), None)
        if self.output_node is None:
            self.output_node = nodes.new('ShaderNodeOutputMaterial')
        # Prefer the shader that actually feeds the active output. A material may
        # retain disconnected old Principled nodes that must not receive new maps.
        pending = [link.from_node for link in self.output_node.inputs['Surface'].links]
        visited = set()
        self.bsdf_node = None
        while pending:
            node = pending.pop(0)
            if node.as_pointer() in visited:
                continue
            visited.add(node.as_pointer())
            if node.bl_idname == 'ShaderNodeBsdfPrincipled':
                self.bsdf_node = node
                break
            pending.extend(link.from_node for socket in node.inputs for link in socket.links)
        if self.bsdf_node is None:
            named = nodes.get('Principled BSDF')
            if named and named.bl_idname == 'ShaderNodeBsdfPrincipled':
                self.bsdf_node = named
            else:
                shaders = [node for node in nodes if node.bl_idname == 'ShaderNodeBsdfPrincipled']
                self.bsdf_node = shaders[0] if len(shaders) == 1 else nodes.new('ShaderNodeBsdfPrincipled')
        if not self.output_node.inputs['Surface'].is_linked:
            self.mat.node_tree.links.new(self.bsdf_node.outputs['BSDF'], self.output_node.inputs['Surface'])
        # ATBridge only repositions the shader/output it created itself; a user's own nodes keep
        # their place and frame, and ATBridge's nodes are laid out around them.
        for node in (self.bsdf_node, self.output_node):
            if existing is None or node.as_pointer() not in pre_existing:
                node[OWNED_TAG] = True
        self.owns_shader = bool(self.bsdf_node.get(OWNED_TAG))
        self.owns_output = bool(self.output_node.get(OWNED_TAG))

    def _check_texture_files(self) -> None:
        """Fail before touching the material when a texture file is missing."""
        missing = [t.path for t in self.asset.textures if t.path and not os.path.isfile(t.path)]
        if missing:
            raise FileNotFoundError(f"贴图文件不存在: {missing[0]}")

    # Material settings ATBridge may change while building.
    _MATERIAL_PROPS = ('blend_method', 'surface_render_method', 'displacement_method', 'shadow_method')

    @classmethod
    def _snapshot(cls, mat):
        # Blender 4.2 keeps the node tree when use_nodes is off; snapshot it regardless.
        tree = mat.node_tree
        return {
            'mat': mat,
            'use_nodes': mat.use_nodes,
            'props': {k: getattr(mat, k) for k in cls._MATERIAL_PROPS if hasattr(mat, k)},
            'nodes': {n.as_pointer() for n in tree.nodes} if tree else set(),
            'names': [(n, n.name) for n in tree.nodes] if tree else [],
            'owned': {n.as_pointer() for n in tree.nodes if n.get(OWNED_TAG)} if tree else set(),
            'links': [(l.from_socket, l.to_socket, l.is_muted) for l in tree.links] if tree else [],
        }

    @staticmethod
    def _restore(snap) -> None:
        mat = snap['mat']
        tree = mat.node_tree
        for node in [n for n in tree.nodes if n.as_pointer() not in snap['nodes']]:
            tree.nodes.remove(node)
        for link in list(tree.links):
            tree.links.remove(link)
        for from_socket, to_socket, muted in snap['links']:
            tree.links.new(from_socket, to_socket).is_muted = muted
        for node, name in snap['names']:
            node.name = name
            if node.as_pointer() not in snap['owned'] and OWNED_TAG in node:
                del node[OWNED_TAG]
        for key, value in snap['props'].items():
            try:
                setattr(mat, key, value)
            except (AttributeError, TypeError):
                pass
        mat.use_nodes = snap['use_nodes']

    def _carry_over_user_links(self, previous, snapshot):
        """
        Links from old ATBridge nodes into nodes ATBridge does not rebuild (the user's own nodes
        and BSDF/Output inputs the new build left alone) move to the new node with the same role.
        When the new asset has no such role any more, the old node and its old upstream nodes are
        kept and handed over to the user instead of being deleted. Returns the kept nodes.
        """
        tree = self.mat.node_tree
        old_ptrs = {n.as_pointer() for n in previous}
        original = {n.as_pointer(): name for n, name in (snapshot['names'] if snapshot else [])}
        new_by_role = {n[ROLE_TAG]: n for n in tree.nodes if ROLE_TAG in n and n.as_pointer() not in old_ptrs}
        keep = []
        old_shader = [n for n in previous if n.get(FRAME_TAG) == 'shader']
        old_finals = [n for n in old_shader
                      if not any(l.to_node in old_shader for s in n.outputs for l in s.links)]
        for old in previous:
            new = new_by_role.get(old.get(ROLE_TAG))
            for socket in old.outputs:
                for link in list(socket.links):
                    if link.to_node.as_pointer() in old_ptrs:
                        continue  # wiring between old ATBridge nodes is rebuilt, not copied
                    if old.get(FRAME_TAG) == 'shader' and old in old_finals:
                        # What the old stack's last node fed now takes this build's final shader output: the
                        # new stack's last node, or the Principled BSDF when the asset has no stack any more.
                        # Intermediate stack nodes migrate by role like any other node.
                        final = getattr(self, 'stack_output', None) or self.bsdf_node.outputs['BSDF']
                        tree.links.new(final, link.to_socket).is_muted = link.is_muted
                        continue
                    match = next((s for s in new.outputs if s.identifier == socket.identifier), None) if new else None
                    if match is None:
                        if old not in keep:
                            keep.append(old)
                        continue
                    muted = link.is_muted
                    tree.links.new(match, link.to_socket).is_muted = muted
        # Keep whatever old ATBridge nodes still feed a kept node.
        pending = list(keep)
        while pending:
            node = pending.pop()
            for socket in node.inputs:
                for link in socket.links:
                    up = link.from_node
                    if up.as_pointer() in old_ptrs and up not in keep:
                        keep.append(up)
                        pending.append(up)
        for node in keep:
            for tag in (FRAME_TAG, ROLE_TAG):
                if tag in node:
                    del node[tag]
            node.name = original.get(node.as_pointer(), node.name.replace('_atb_old_', '', 1))
            log.info(f"保留仍被用户节点使用的旧节点: {node.name}")
        return keep

    # ------------------------------------------------------------------ registration

    def _register(self, channel: str, node, converter: bool = False, role: str = None):
        """Record a created node under its channel; layout happens once everything exists."""
        if node is None:
            return None
        node[FRAME_TAG] = channel
        node[ROLE_TAG] = role or channel
        entry = self.channels.setdefault(channel, {'textures': [], 'converters': []})
        entry['converters' if converter else 'textures'].append(node)
        return node

    def _layout(self) -> None:
        channels = [{'key': key, 'to_output': key == 'displacement', **self.channels[key]}
                    for key in CHANNEL_ORDER if key in self.channels]
        labels = {key: get_text(text) for key, text in CHANNEL_LABELS.items()}
        layout_material(self.mat.node_tree, self.bsdf_node, self.output_node, channels,
                        self.mapping_nodes or None, labels,
                        move_shader=self.owns_shader, move_output=self.owns_output,
                        post_columns=self.post_columns)

    # ------------------------------------------------------------------ channels

    def _setup_mapping(self) -> None:
        """设置 UV Mapping（非 3D/3DPlant 资产）"""
        if self.asset.type not in [BridgeConfig.ASSET_TYPE_3D,
                                   BridgeConfig.ASSET_TYPE_3DPLANT]:
            mapping, tex_coord, scale, self.reroute = self.factory.create_mapping_setup((0, 0))
            self.mapping_nodes = [tex_coord, scale, mapping, self.reroute]
            for node, role in zip(self.mapping_nodes, ('map_coord', 'map_scale', 'mapping', 'map_reroute')):
                node[FRAME_TAG] = 'mapping'
                node[ROLE_TAG] = role

    def _setup_textures(self) -> None:
        """设置所有贴图"""
        if self.asset.has_texture('albedo'):
            self._setup_albedo_ao()

        if self.asset.has_texture('metalness'):
            self._create_connected_texture('metalness', 'metallic', 'Metallic',
                                           BridgeConfig.COLORSPACE_NON_COLOR)

        if self.asset.has_texture('roughness'):
            self._create_connected_texture('roughness', 'roughness', 'Roughness',
                                           BridgeConfig.COLORSPACE_NON_COLOR)
        elif self.asset.has_texture('gloss'):
            self._setup_gloss()

        if self.asset.has_texture('opacity'):
            self._setup_opacity()
            self.mat.blend_method = BlenderCompat.get_blend_method_hashed()
            if hasattr(self.mat, 'surface_render_method'):   # EEVEE Next (4.2+)
                self.mat.surface_render_method = 'DITHERED'

        if self.asset.has_texture('transmission'):
            self._create_connected_texture('transmission', 'transmission', 'Transmission Weight',
                                           BridgeConfig.COLORSPACE_NON_COLOR)

        if self.asset.has_texture('translucency'):
            self._setup_translucency()

        if self.asset.has_texture('fuzz'):
            # Fabric fuzz drives the sheen layer.
            self._create_connected_texture('fuzz', 'sheen', 'Sheen Weight',
                                           BridgeConfig.COLORSPACE_NON_COLOR)

        if self.asset.has_texture('mask'):
            # Imperfection masks are for layering; keep the map ready but unconnected.
            node = self._register('mask', self._create_texture_node('mask', BridgeConfig.COLORSPACE_NON_COLOR),
                                  role='tex:mask')
            if node:
                node.name = 'Mask Tex Node'
                self.tex_count += 1

        if self.asset.has_texture('normal'):
            self._setup_normal()
        elif self.asset.has_texture('bump'):
            self._setup_bump()

        if self.asset.has_texture('displacement'):
            self._setup_displacement()

        self._setup_shader_stack()

    def _setup_albedo_ao(self) -> None:
        """设置 Albedo (+ AO 混合)"""
        color_node = self._register('color', self._create_texture_node('albedo', BridgeConfig.COLORSPACE_SRGB), role='tex:albedo')
        color_node.name = "Color Tex Node"
        self.tex_count += 1
        if self.asset.has_texture('ao'):
            ao_node = self._register('color', self._create_texture_node('ao', BridgeConfig.COLORSPACE_NON_COLOR), role='tex:ao')
            ao_node.name = "AO Tex Node"
            mix_node = self._register('color', self.factory.create_mix_node((0, 0), 'MULTIPLY'), converter=True, role='mix_ao')
            mix_node.label = 'Base Color × AO'
            inputs = BlenderCompat.get_mix_node_inputs()
            self.factory.link(color_node.outputs['Color'], mix_node.inputs[inputs['a']])
            self.factory.link(ao_node.outputs['Color'], mix_node.inputs[inputs['b']])
            self._connect_to_bsdf(mix_node.outputs[2], 'Base Color')
            self.tex_count += 1
        else:
            self._connect_to_bsdf(color_node.outputs['Color'], 'Base Color')

    def _setup_opacity(self) -> None:
        """Opacity masks may live in the red channel only (plant atlases ship red-on-black),
        so read R instead of letting Blender convert the color by luminance (~21% for pure red)."""
        tex = self._register('opacity', self._create_texture_node('opacity', BridgeConfig.COLORSPACE_NON_COLOR),
                             role='tex:opacity')
        tex.name = 'Opacity Tex Node'
        sep = self._register('opacity', self.factory.create_separate_color_node((0, 0)), converter=True,
                             role='opacity_red')
        sep.label = 'Opacity (R)'
        self.factory.link(tex.outputs['Color'], sep.inputs[0])
        self._connect_to_bsdf(sep.outputs[0], 'Alpha')
        self.tex_count += 1

    def _setup_translucency(self) -> None:
        """Foliage: the translucency map is the color of light passing through the leaf."""
        tex = self._register('translucency', self._create_texture_node('translucency', BridgeConfig.COLORSPACE_SRGB),
                             role='tex:translucency')
        tex.name = 'Translucency Tex Node'
        bsdf = self._register('translucency', self.factory.create_node('ShaderNodeBsdfTranslucent', (0, 0)),
                              converter=True, role='translucent_bsdf')
        amount = self._register('translucency', self.factory.create_value_node((0, 0), 0.4, 'Translucency Amount'),
                                converter=True, role='translucency_amount')
        amount.label = 'Translucency Amount'
        self.factory.link(tex.outputs['Color'], bsdf.inputs['Color'])
        self.translucent_bsdf, self.translucency_amount = bsdf, amount
        self.tex_count += 1

    def _setup_shader_stack(self) -> None:
        """Principled → (mix with Translucent) → (cut out by opacity) → Output, when the asset needs it."""
        if not getattr(self, 'translucent_bsdf', None):
            return
        tree = self.mat.node_tree

        def shader_node(kind, role):
            node = self.factory.create_node(kind, (0, 0))
            node[FRAME_TAG] = 'shader'
            node[ROLE_TAG] = role
            return node

        # Where the shader's output goes now (the Output, or a user's own mix/add chain);
        # ATBridge's previous stack nodes are excluded — their downstream links are migrated.
        targets = [(l.to_socket, l.is_muted) for l in self.bsdf_node.outputs['BSDF'].links if FRAME_TAG not in l.to_node]
        mix = shader_node('ShaderNodeMixShader', 'mix_translucency')
        mix.label = 'Translucency'
        self.factory.link(self.translucency_amount.outputs[0], mix.inputs['Fac'])
        self.factory.link(self.bsdf_node.outputs['BSDF'], mix.inputs[1])
        self.factory.link(self.translucent_bsdf.outputs['BSDF'], mix.inputs[2])
        self.post_columns = [[mix]]
        result = mix
        opacity = next((n for n in self.channels.get('opacity', {}).get('converters', [])
                        if n.get(ROLE_TAG) == 'opacity_red'), None)
        if opacity is not None:
            # The Translucent BSDF ignores Principled alpha, so the cut-out moves to the shader level.
            alpha = self.bsdf_node.inputs[BlenderCompat.get_bsdf_input_name('Alpha')]
            for link in list(alpha.links):
                tree.links.remove(link)
            transparent = shader_node('ShaderNodeBsdfTransparent', 'transparent_bsdf')
            cut = shader_node('ShaderNodeMixShader', 'mix_cutout')
            cut.label = 'Opacity Cut-out'
            self.factory.link(opacity.outputs[0], cut.inputs['Fac'])
            self.factory.link(transparent.outputs['BSDF'], cut.inputs[1])
            self.factory.link(mix.outputs['Shader'], cut.inputs[2])
            self.post_columns = [[mix, transparent], [cut]]
            result = cut
        self.stack_output = result.outputs['Shader']
        for socket, muted in targets:
            self.mat.node_tree.links.new(self.stack_output, socket).is_muted = muted   # replaces the shader's own link
        if not targets and not self.output_node.inputs['Surface'].is_linked:
            self.factory.link(result.outputs['Shader'], self.output_node.inputs['Surface'])

    def _setup_gloss(self) -> None:
        """设置 Gloss 贴图（反转为 Roughness）"""
        gloss_node = self._register('roughness', self._create_texture_node('gloss', BridgeConfig.COLORSPACE_NON_COLOR), role='tex:gloss')
        gloss_node.name = "Gloss Tex Node"
        invert_node = self._register('roughness', self.factory.create_invert_node((0, 0)), converter=True, role='invert_gloss')
        invert_node.label = 'Gloss → Roughness'
        self.factory.link(gloss_node.outputs['Color'], invert_node.inputs[1])
        self._connect_to_bsdf(invert_node.outputs[0], 'Roughness')
        self.tex_count += 1

    def _setup_normal(self) -> None:
        """设置法线贴图"""
        tex_node = self._register('normal', self._create_texture_node('normal', BridgeConfig.COLORSPACE_NON_COLOR), role='tex:normal')
        tex_node.name = "Normal Tex Node"
        normal_node = self._register('normal', self.factory.create_normal_map_node((0, 0)), converter=True, role='normal_map')
        self.factory.link(tex_node.outputs['Color'], normal_node.inputs['Color'])
        self._connect_to_bsdf(normal_node.outputs['Normal'], 'Normal')
        self.tex_count += 1

    def _setup_bump(self) -> None:
        """设置凹凸贴图"""
        tex_node = self._register('normal', self._create_texture_node('bump', BridgeConfig.COLORSPACE_NON_COLOR), role='tex:bump')
        tex_node.name = "Bump Tex Node"
        bump_node = self._register('normal', self.factory.create_bump_node((0, 0)), converter=True, role='bump')
        self.factory.link(tex_node.outputs['Color'], bump_node.inputs[2])
        self._connect_to_bsdf(bump_node.outputs['Normal'], 'Normal')
        self.tex_count += 1

    def _setup_displacement(self) -> None:
        """设置置换贴图"""
        tex_node = self._register('displacement', self._create_texture_node('displacement', BridgeConfig.COLORSPACE_NON_COLOR), role='tex:displacement')
        tex_node.name = "Displacement Tex Node"
        sep_node = self._register('displacement', self.factory.create_separate_color_node((0, 0)), converter=True, role='disp_separate')
        strength_node = self._register('displacement', self.factory.create_value_node(
            (0, 0), self.asset.displacement_height or BridgeConfig.DISPLACEMENT_SCALE, 'Bump Strength'),
            converter=True, role='disp_scale')
        strength_node.label = 'Displacement Scale'
        disp_node = self._register('displacement', self.factory.create_displacement_node((0, 0)), converter=True, role='displacement')
        self.factory.link(tex_node.outputs['Color'], sep_node.inputs[0])
        self.factory.link(sep_node.outputs[0], disp_node.inputs[0])
        self.factory.link(strength_node.outputs[0], disp_node.inputs['Scale'])
        self.factory.link(disp_node.outputs[0], self.output_node.inputs[2])
        self.mat.displacement_method = BlenderCompat.get_displacement_method()
        self.tex_count += 1

    # ------------------------------------------------------------------ helpers

    def _create_texture_node(self, tex_type: str, colorspace: str) -> Optional[bpy.types.Node]:
        """创建贴图节点并连接到 Mapping"""
        path = self.asset.get_texture_path(tex_type)
        if not path:
            log.warning(f"找不到贴图: {tex_type}")
            return None
        projection = 'FLAT' if self.asset.type == BridgeConfig.ASSET_TYPE_SURFACE else None
        node = self.factory.create_texture_node(path, (0, 0), colorspace, projection)
        node.label = TEXTURE_LABELS.get(tex_type, tex_type.title())
        if self.reroute:
            self.factory.link(self.reroute.outputs[0], node.inputs['Vector'])
        return node

    def _create_connected_texture(self, tex_type: str, channel: str, bsdf_input: str,
                                  colorspace: str) -> Optional[bpy.types.Node]:
        """创建贴图并直接连接到 BSDF"""
        node = self._register(channel, self._create_texture_node(tex_type, colorspace), role=f'tex:{tex_type}')
        if node:
            node.name = f"{tex_type.title()} Tex Node"
            self._connect_to_bsdf(node.outputs['Color'], bsdf_input)
            self.tex_count += 1
        return node

    def _connect_to_bsdf(self, from_socket, input_name: str) -> None:
        """连接到 BSDF 节点"""
        bsdf_input = BlenderCompat.get_bsdf_input_name(input_name)
        if bsdf_input in self.bsdf_node.inputs:
            self.factory.link(from_socket, self.bsdf_node.inputs[bsdf_input])
        else:
            log.warning(f"BSDF 节点没有输入: {bsdf_input}")
