# ATBridge 材质节点排布
"""
Lays out ATBridge-built material nodes in readable columns:

    UV mapping | image textures | converters | Principled BSDF | Material Output

Each texture channel (color, metallic, roughness, ...) gets a labelled frame; converters
line up with the texture they consume, and rows are stacked from estimated node heights so
nothing overlaps. Node.dimensions is zero until the editor draws, so heights are estimated
per node type and kept slightly generous.
"""
from typing import Dict, List, Optional

import bpy

# Estimated drawn heights (node editor units) for nodes as ATBridge configures them.
_HEIGHT = {
    'ShaderNodeTexImage': 270,
    'ShaderNodeMix': 200,
    'ShaderNodeNormalMap': 150,
    'ShaderNodeBump': 190,
    'ShaderNodeInvert': 120,
    'ShaderNodeSeparateColor': 150,
    'ShaderNodeDisplacement': 190,
    'ShaderNodeValue': 90,
    'ShaderNodeMapping': 380,
    'ShaderNodeTexCoord': 250,
    'NodeReroute': 20,
    'ShaderNodeBsdfPrincipled': 660,
    'ShaderNodeOutputMaterial': 120,
}
COLUMN_GAP = 80
ROW_GAP = 30
FRAME_GAP = 70        # space between channel frames (includes the frame label)
FRAME_TAG = 'atb_channel'   # channel of a node ATBridge created
ROLE_TAG = 'atb_role'       # stable role, used to carry user links over on rebuild
OWNED_TAG = 'atb_owned'     # shader/output created by ATBridge (safe to reposition)


def node_height(node) -> float:
    return _HEIGHT.get(node.bl_idname, 200)


def node_width(node) -> float:
    # Reroutes report a width but draw as a small dot.
    return 16 if node.bl_idname == 'NodeReroute' else node.width


def node_rect(node):
    """(left, top, right, bottom) in absolute editor coordinates, using estimated size."""
    x, y = absolute_location(node)
    return x, y, x + node_width(node), y - node_height(node)


def absolute_location(node):
    loc = getattr(node, 'location_absolute', None)
    if loc is not None:
        return loc.x, loc.y
    x, y = node.location.x, node.location.y
    parent = node.parent
    while parent is not None:
        x += parent.location.x
        y += parent.location.y
        parent = parent.parent
    return x, y


def _place(node, x: float, y: float) -> None:
    # Position before parenting: assigning .parent keeps the absolute position on every
    # Blender version (relative storage before 4.4, absolute afterwards).
    node.parent = None
    node.location = (x, y)


def _frame(tree, label: str, color, nodes: List) -> bpy.types.Node:
    frame = tree.nodes.new('NodeFrame')
    frame.label = label
    frame.label_size = 16
    frame.shrink = True
    frame.use_custom_color = True
    frame.color = color
    frame[FRAME_TAG] = 'frame'
    frame.location = (0, 0)
    for node in nodes:
        node.parent = frame
    return frame


def _hide_unused_outputs(node) -> None:
    if node.bl_idname in ('ShaderNodeBsdfPrincipled', 'ShaderNodeOutputMaterial', 'NodeFrame', 'NodeReroute'):
        return
    for socket in node.outputs:
        if socket.enabled and not socket.is_linked:
            socket.hide = True


# Muted, dark frame colors so they read in both light and dark editor themes.
CHANNEL_COLORS = {
    'mapping': (0.16, 0.16, 0.18),
    'color': (0.24, 0.18, 0.14),
    'metallic': (0.17, 0.19, 0.22),
    'roughness': (0.18, 0.18, 0.18),
    'opacity': (0.14, 0.18, 0.22),
    'transmission': (0.14, 0.20, 0.20),
    'translucency': (0.15, 0.21, 0.15),
    'normal': (0.17, 0.16, 0.24),
    'displacement': (0.21, 0.16, 0.20),
}


def layout_material(tree, bsdf, output, channels: List[Dict], mapping: Optional[List] = None,
                    labels: Optional[Dict[str, str]] = None, move_shader: bool = True,
                    move_output: bool = True) -> None:
    """
    channels: ordered list of {'key', 'textures': [nodes], 'converters': [nodes], 'to_output': bool}
    mapping:  nodes of the UV mapping setup (tex coord, value, mapping, reroute), left-most column.
    """
    labels = labels or {}
    tex_w = max([n.width for c in channels for n in c['textures']] or [240])
    conv_w = max([n.width for c in channels for n in c['converters']] or [160])

    # Columns (x of each column's left edge), right to left from the BSDF. A user's own shader
    # and output keep their position and frame; ATBridge's nodes are anchored to them instead.
    if move_shader:
        bsdf_x, top = 0.0, 0.0
        _place(bsdf, bsdf_x, top)
    else:
        bsdf_x, top = absolute_location(bsdf)
    if move_output:
        _place(output, bsdf_x + bsdf.width + COLUMN_GAP, top)
    conv_x = bsdf_x - COLUMN_GAP - conv_w
    tex_x = conv_x - COLUMN_GAP - tex_w

    y = top
    for channel in channels:
        textures, converters = channel['textures'], channel['converters']
        if not textures and not converters:
            continue
        band_top = y
        ty = band_top
        for node in textures:
            _place(node, tex_x, ty)
            ty -= node_height(node) + ROW_GAP
        cy = band_top
        for node in converters:
            _place(node, conv_x, cy)
            cy -= node_height(node) + ROW_GAP
        y = min(ty, cy) + ROW_GAP - FRAME_GAP
        members = textures + converters
        _frame(tree, labels.get(channel['key'], channel['key'].title()),
               CHANNEL_COLORS.get(channel['key'], (0.18, 0.18, 0.18)), members)
        for node in textures + converters:
            _hide_unused_outputs(node)

    if mapping:
        # Texture Coordinate and the tiling value feed Mapping; the reroute fans out to textures.
        coords = [n for n in mapping if n.bl_idname == 'ShaderNodeTexCoord']
        values = [n for n in mapping if n.bl_idname == 'ShaderNodeValue']
        maps = [n for n in mapping if n.bl_idname == 'ShaderNodeMapping']
        reroutes = [n for n in mapping if n.bl_idname == 'NodeReroute']
        map_x = tex_x - COLUMN_GAP * 2 - 180
        src_x = map_x - COLUMN_GAP - 160
        sy = top
        for node in coords + values:
            _place(node, src_x, sy)
            sy -= node_height(node) + ROW_GAP
        for node in maps:
            _place(node, map_x, top)
        for node in reroutes:
            _place(node, tex_x - COLUMN_GAP / 2 - 8, top - 40)
        _frame(tree, labels.get('mapping', 'UV Mapping'), CHANNEL_COLORS['mapping'], coords + values + maps)

    # New nodes are created selected; leave the editor without a surprise selection.
    for node in tree.nodes:
        node.select = False
