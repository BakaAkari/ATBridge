"""Material layout: channel frames, column order, no overlaps, idempotent rebuild, FBX leftovers removed.

Run: blender -b --factory-startup --python-exit-code 1 --python tests/blender_material_layout_smoke.py
"""
from pathlib import Path
import sys
import tempfile

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from ATBridge.core.asset_parser import AssetData, MeshInfo, TextureInfo
from ATBridge.core.import_manager import ImportManager
from ATBridge.core.material_builder import MaterialBuilder
from ATBridge.core.node_layout import FRAME_TAG, node_rect

bpy.context.preferences.use_preferences_save = False
tmp = Path(tempfile.mkdtemp(prefix='atb-layout-'))


def make_image(name):
    img = bpy.data.images.new(name, 4, 4)
    path = tmp / f'{name}.png'
    img.filepath_raw = str(path)
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return str(path)


def asset(asset_id, asset_type, maps, meshes=()):
    tex = [TextureInfo(format='png', type=t, path=make_image(f'{asset_id}_{t}')) for t in maps]
    return AssetData(id=asset_id, name=asset_id.title(), type=asset_type, path=None, textures=tex,
                     texture_types=[t.type for t in tex], meshes=list(meshes))


def check_layout(mat, expect_frames):
    nodes = [n for n in mat.node_tree.nodes if n.bl_idname != 'NodeFrame']
    rects = {n.name: node_rect(n) for n in nodes}
    names = list(rects)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            l1, t1, r1, b1 = rects[a]
            l2, t2, r2, b2 = rects[b]
            assert r1 <= l2 or r2 <= l1 or b1 >= t2 or b2 >= t1, f'{mat.name}: {a} overlaps {b}'
    frames = [n for n in mat.node_tree.nodes if n.bl_idname == 'NodeFrame']
    assert sorted(f.label for f in frames) == sorted(expect_frames), [f.label for f in frames]
    textures = [n for n in nodes if n.bl_idname == 'ShaderNodeTexImage']
    assert textures and all(n.parent is not None for n in textures), 'texture outside a frame'
    assert all(n.label for n in textures), 'texture without a channel label'
    bsdf = next(n for n in nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    out = next(n for n in nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    tex_right = max(rects[n.name][2] for n in textures)
    conv = [n for n in nodes if n.get(FRAME_TAG) and n.bl_idname not in ('ShaderNodeTexImage', 'NodeReroute', 'ShaderNodeDisplacement')
            and n.get(FRAME_TAG) != 'mapping']
    assert all(rects[n.name][0] >= tex_right for n in conv), 'converter left of textures'
    assert all(rects[n.name][2] <= rects[bsdf.name][0] for n in conv), 'converter overlaps BSDF column'
    assert rects[bsdf.name][2] <= rects[out.name][0], 'output not right of BSDF'
    for n in textures:
        assert all(s.is_linked or s.hide for s in n.outputs if s.enabled), f'{n.label}: unused output not hidden'
    return len(mat.node_tree.nodes), len(mat.node_tree.links)


# 1. 3D asset with AO, metallic, normal and displacement.
a3d = asset('fixture3d', '3d', ['albedo', 'ao', 'metalness', 'roughness', 'normal', 'displacement'])
m3d = MaterialBuilder(a3d).build()
first = check_layout(m3d, ['Base Color', 'Metallic', 'Roughness', 'Normal', 'Displacement'])
images = len(bpy.data.images)
again = MaterialBuilder(a3d).build()
assert again == m3d and check_layout(m3d, ['Base Color', 'Metallic', 'Roughness', 'Normal', 'Displacement']) == first, 'rebuild duplicated nodes'
assert len(bpy.data.images) == images, 'rebuild reloaded images'

# 2. Surface: UV mapping column, gloss inversion, opacity, transmission, bump fallback.
asurf = asset('fixturesurf', 'surface', ['albedo', 'gloss', 'opacity', 'transmission', 'bump', 'displacement'])
msurf = MaterialBuilder(asurf).build()
check_layout(msurf, ['UV Mapping', 'Base Color', 'Roughness', 'Opacity', 'Transmission', 'Normal', 'Displacement'])

# 3. FBX with its own material: every slot gets the ATBridge material, the file's material is removed.
bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.active_object
own = bpy.data.materials.new('FixtureOwnMaterial')
cube.data.materials.append(own)
cube.data.materials.append(bpy.data.materials.new('FixtureSecondSlot'))
fbx = tmp / 'fixture.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True)
bpy.data.objects.remove(cube)
for m in [m for m in bpy.data.materials if m.name.startswith(('FixtureOwnMaterial', 'FixtureSecondSlot'))]:
    bpy.data.materials.remove(m)
afbx = asset('fixturefbx', '3d', ['albedo', 'roughness', 'normal'], [MeshInfo(format='fbx', path=str(fbx))])
existing = set(bpy.context.scene.objects)
ImportManager()._import_single_asset(afbx)
imported = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o not in existing]
assert imported, 'FBX not imported'
target = bpy.data.materials[afbx.material_name]
assert all(slot.material == target for o in imported for slot in o.material_slots), 'a slot kept the file material'
leftover = [m.name for m in bpy.data.materials if m.name.startswith(('FixtureOwnMaterial', 'FixtureSecondSlot'))]
assert not leftover, f'file materials left behind: {leftover}'

# 4. A user's image with the same file keeps its color space; ATBridge loads its own copy.
user_mat = bpy.data.materials.new('UserShared')
user_mat.use_nodes = True
shared_path = make_image('shared_roughness')
user_tex = user_mat.node_tree.nodes.new('ShaderNodeTexImage')
user_tex.image = bpy.data.images.load(shared_path)
user_tex.image.colorspace_settings.name = 'sRGB'
ashared = AssetData(id='fixtureshared', name='Shared', type='3d', path=None,
                    textures=[TextureInfo(format='png', type='roughness', path=shared_path)], texture_types=['roughness'])
mshared = MaterialBuilder(ashared).build()
assert user_tex.image.colorspace_settings.name == 'sRGB', 'user image color space changed'
ours = next(n for n in mshared.node_tree.nodes if n.bl_idname == 'ShaderNodeTexImage')
assert ours.image != user_tex.image and ours.image.colorspace_settings.name == 'Non-Color'

# 5. Rebuild keeps links from ATBridge nodes into the user's own branch.
tree = m3d.node_tree
color = next(n for n in tree.nodes if n.get('atb_role') == 'tex:albedo')
curves = tree.nodes.new('ShaderNodeRGBCurve')
user_bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
tree.links.new(color.outputs['Color'], curves.inputs['Color'])
tree.links.new(curves.outputs['Color'], user_bsdf.inputs['Emission Color'])
MaterialBuilder(a3d).build()
color_new = next(n for n in tree.nodes if n.get('atb_role') == 'tex:albedo')
assert curves.inputs['Color'].is_linked and curves.inputs['Color'].links[0].from_node == color_new, 'user branch lost its input'
assert user_bsdf.inputs['Emission Color'].links[0].from_node == curves

# 6. A failed rebuild (missing texture file) leaves the material in use untouched.
state = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in tree.links)
count = len(tree.nodes)
broken = AssetData(id=a3d.id, name=a3d.name, type='3d', path=None,
                   textures=[TextureInfo(format='png', type='albedo', path=str(tmp / 'missing.png'))], texture_types=['albedo'])
try:
    MaterialBuilder(broken).build()
    raise AssertionError('missing texture did not fail')
except FileNotFoundError:
    pass
assert len(tree.nodes) == count and sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier)
                                           for l in tree.links) == state, 'failed rebuild changed the material'

# 7. A user's own shader inside a user frame keeps its frame and position; displacement stays left of it.
umat = bpy.data.materials.new(asurf.material_name.replace('fixturesurf', 'fixtureuser'))
umat.use_nodes = True
ut = umat.node_tree
for n in list(ut.nodes):
    if n.bl_idname == 'ShaderNodeBsdfPrincipled':
        ut.nodes.remove(n)
user_frame = ut.nodes.new('NodeFrame')
shader = ut.nodes.new('ShaderNodeBsdfPrincipled')
shader.location = (1400, 300)
shader.parent = user_frame
out = next(n for n in ut.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
ut.links.new(shader.outputs['BSDF'], out.inputs['Surface'])
before_abs = node_rect(shader)[:2]
auser = AssetData(id='fixtureuser', name=asurf.name, type='3d', path=None, textures=a3d.textures,
                  texture_types=a3d.texture_types)
assert auser.material_name == umat.name
b = MaterialBuilder(auser)
b.build()
assert b.bsdf_node == shader and shader.parent == user_frame, 'user shader moved out of its frame'
assert tuple(round(v) for v in node_rect(shader)[:2]) == tuple(round(v) for v in before_abs), 'user shader moved'
disp = next(n for n in ut.nodes if n.get('atb_role') == 'displacement')
assert disp.parent is not None and node_rect(disp)[2] <= node_rect(shader)[0], 'displacement not framed left of the shader'

# 8. Mix output (identifier differs from name) and muted links migrate; a dropped channel keeps
#    the old node the user still depends on; mid-build failure restores everything incl. names.
amix = asset('fixturemix', '3d', ['albedo', 'ao', 'roughness'])
mmix = MaterialBuilder(amix).build()
mt = mmix.node_tree
mix = next(n for n in mt.nodes if n.get('atb_role') == 'mix_ao')
rough = next(n for n in mt.nodes if n.get('atb_role') == 'tex:roughness')
rer = mt.nodes.new('NodeReroute')
mt.links.new(mix.outputs[2], rer.inputs[0]).is_muted = True
math = mt.nodes.new('ShaderNodeMath')
mt.links.new(rough.outputs['Color'], math.inputs[0])
MaterialBuilder(amix).build()
assert rer.inputs[0].is_linked and rer.inputs[0].links[0].from_node.get('atb_role') == 'mix_ao', 'mix output not migrated'
assert rer.inputs[0].links[0].is_muted, 'muted state lost'
only_color = AssetData(id=amix.id, name=amix.name, type='3d', path=None, textures=amix.textures[:1], texture_types=['albedo'])
MaterialBuilder(only_color).build()
assert math.inputs[0].is_linked, 'user dependency on a dropped channel was cut'
assert math.inputs[0].links[0].from_node.get('atb_role') is None, 'kept node still marked as ATBridge-owned'

long_name = 'A' * 63
color_node = next(n for n in mt.nodes if n.get('atb_role') == 'tex:albedo')
color_node.name = long_name
mmix.blend_method = 'BLEND'
props = {k: getattr(mmix, k) for k in ('blend_method', 'displacement_method') if hasattr(mmix, k)}
snapshot_links = sorted((l.from_node.as_pointer(), l.from_socket.identifier, l.to_node.as_pointer(), l.to_socket.identifier, l.is_muted)
                        for l in mt.links)
nodes_before = {n.as_pointer() for n in mt.nodes}


class FailingBuilder(MaterialBuilder):
    def _setup_textures(self):
        super()._setup_textures()
        raise RuntimeError('simulated failure after textures were loaded')


racy = AssetData(id=amix.id, name=amix.name, type='3d', path=None,
                 textures=amix.textures + [TextureInfo(format='png', type='opacity', path=make_image('fixturemix_opacity'))],
                 texture_types=amix.texture_types + ['opacity'])
try:
    FailingBuilder(racy).build()
    raise AssertionError('simulated failure was swallowed')
except RuntimeError:
    pass
assert {n.as_pointer() for n in mt.nodes} == nodes_before, 'rollback left or removed nodes'
assert sorted((l.from_node.as_pointer(), l.from_socket.identifier, l.to_node.as_pointer(), l.to_socket.identifier, l.is_muted)
              for l in mt.links) == snapshot_links, 'rollback changed links'
assert color_node.name == long_name, 'rollback truncated a node name'
assert {k: getattr(mmix, k) for k in props} == props, 'rollback left material settings changed'

print(f'PASS: channel frames, column order, no overlaps, labels, hidden unused outputs, idempotent rebuild, '
      f'mix/muted link migration, dropped-channel dependency kept, mid-build rollback, '
      f'FBX slots replaced and leftovers removed, shared image color space kept, user links carried over, '
      f'failed rebuild rolled back, user shader/frame untouched (Blender {bpy.app.version_string})')

# 9. Existing node tree with use_nodes off (kept by Blender 4.2): a failed rebuild must not delete it.
off = bpy.data.materials.new(AssetData(id='fixtureoff', name='Off', type='3d', path=None).material_name)
off.use_nodes = True
curves_off = off.node_tree.nodes.new('ShaderNodeRGBCurve')
off_nodes = {n.as_pointer() for n in off.node_tree.nodes}
off_links = len(off.node_tree.links)
off.use_nodes = False
aoff = AssetData(id='fixtureoff', name='Off', type='3d', path=None, textures=amix.textures[:1], texture_types=['albedo'])
try:
    FailingBuilder(aoff).build()
    raise AssertionError('simulated failure was swallowed')
except RuntimeError:
    pass
assert {n.as_pointer() for n in off.node_tree.nodes} == off_nodes and len(off.node_tree.links) == off_links, \
    'rollback deleted a node tree that had use_nodes off'
print('PASS: rollback keeps node trees of materials with use_nodes off')
