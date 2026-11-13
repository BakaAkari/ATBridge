"""Material node identity must survive translated and user-edited names."""
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from ATBridge.core.asset_parser import AssetData
from ATBridge.core.material_builder import MaterialBuilder, CHANNEL_LABELS
from ATBridge.core.node_layout import FRAME_TAG

bpy.context.preferences.use_preferences_save = False
bpy.context.preferences.view.language = 'zh_HANS'
bpy.context.preferences.view.use_translate_interface = True
bpy.context.preferences.view.use_translate_new_dataname = True
asset = AssetData(id='locale-fixture', name='Locale', type='3d', path=None)
builder = MaterialBuilder(asset)
material = builder.build()
assert builder.bsdf_node.bl_idname == 'ShaderNodeBsdfPrincipled'
assert builder.bsdf_node.name != 'Principled BSDF'
assert builder.output_node.bl_idname == 'ShaderNodeOutputMaterial'
assert builder.output_node.inputs['Surface'].is_linked
builder.bsdf_node.name = 'User renamed shader'
builder.output_node.name = 'User renamed output'
shader_pointer = builder.bsdf_node.as_pointer()
another = MaterialBuilder(asset)
assert another.build() == material
assert another.bsdf_node.as_pointer() == shader_pointer
assert sum(n.bl_idname == 'ShaderNodeBsdfPrincipled' for n in material.node_tree.nodes) == 1
parked = another.bsdf_node
parked.name = 'Parked shader'
value = material.node_tree.nodes.new('ShaderNodeValue')
material.node_tree.links.new(value.outputs[0], parked.inputs['Roughness'])
active_shader = material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
active_shader.name = 'Principled BSDF'
material.node_tree.links.new(active_shader.outputs['BSDF'], another.output_node.inputs['Surface'])
active = MaterialBuilder(asset)
active.build()
assert active.bsdf_node == active_shader, 'Selected an unused shader instead of the rendered branch'
assert parked.inputs['Roughness'].links[0].from_node == value, 'Changed an inactive branch'
material.node_tree.nodes.clear()
recovered = MaterialBuilder(asset)
recovered.build()
assert recovered.bsdf_node and recovered.output_node.inputs['Surface'].is_linked

# Persisted frame captions must stay English even when new Blender data names are Chinese.
surface = AssetData(id='locale-frames', name='Locale Frames', type='surface', path=None)
captions = []
for language in ('zh_HANS', 'en_US'):
    bpy.context.preferences.view.language = language
    framed = MaterialBuilder(surface).build()
    frames = [n for n in framed.node_tree.nodes if n.bl_idname == 'NodeFrame' and FRAME_TAG in n]
    assert frames, 'Surface mapping frame missing'
    assert [n.label for n in frames] == [CHANNEL_LABELS['mapping']], 'Persisted frame label was translated'
    captions.append([n.label for n in frames])
assert captions[0] == captions[1], 'Frame captions changed with UI language'
print('PASS: Chinese/renamed nodes, stable reuse, active shader selection, inactive branch preservation and missing-node recovery')
