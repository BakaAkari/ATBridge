"""Import every real Fab sample package and check the result per asset kind.

Samples are real Fab downloads (not redistributable, so not in the repo). Put each ZIP in
<samples>/sample-<key>/*.zip; <samples> defaults to ~/Downloads/ATBridge, override with
ATB_FAB_SAMPLES. Missing samples are skipped and listed.

Run: blender -b --factory-startup --python-exit-code 1 --python tests/blender_fab_samples_smoke.py
"""
from pathlib import Path
import importlib
import os
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
addon = importlib.import_module(ROOT.name)
addon.register()
bpy.context.preferences.use_preferences_save = False

SAMPLES = Path(os.environ.get('ATB_FAB_SAMPLES', Path.home() / 'Downloads' / 'ATBridge'))

# key: (expected mesh objects, materials, texture labels that must be linked to these BSDF inputs)
LINKED = {'Base Color': 'Base Color', 'Roughness': 'Roughness', 'Normal': 'Normal', 'Opacity': 'Alpha',
          'Translucency': 'Subsurface Weight', 'Fuzz': 'Sheen Weight', 'Transmission': 'Transmission Weight'}
EXPECT = {
    'jerrycan-fbx':       dict(meshes=1, materials=1, linked=['Base Color', 'Roughness', 'Normal']),
    'dead-tree':          dict(meshes=1, materials=1, linked=['Base Color', 'Roughness', 'Normal']),
    'lady-fern-fbx':      dict(meshes=9, materials=1, linked=['Base Color', 'Opacity', 'Translucency', 'Normal'], plant=True),
    'grass-clumps':       dict(meshes=3, materials=1, linked=['Base Color', 'Opacity', 'Translucency', 'Normal'], plant=True),
    'rock-cliff-texture': dict(meshes=1, materials=1, linked=['Base Color', 'Roughness', 'Normal'], plane=(1.0, 1.0), disp=0.151),
    'herringbone':        dict(meshes=1, materials=1, linked=['Base Color', 'Roughness', 'Normal'], plane=(2.0, 2.0)),
    'plush-carpet':       dict(meshes=1, materials=1, linked=['Base Color', 'Fuzz', 'Transmission'], plane=(0.25, 0.25)),
    'graffiti-texture':   dict(meshes=1, materials=1, linked=['Base Color', 'Opacity'], plane=(4.0, 2.0)),
    'oak-leaves':         dict(meshes=1, materials=1, linked=['Base Color', 'Opacity', 'Translucency'], plane=(0.41, 0.41)),
    'scratched-metal':    dict(meshes=1, materials=1, linked=['Roughness'], plane=(0.7, 0.7), mask=True),
    'coffee-stain':       dict(meshes=0, materials=0, brush=True),
    'jerrycan-gltf':      dict(meshes=1, materials=1, gltf=True),
    'lady-fern-gltf':     dict(meshes=9, materials=1, gltf=True, plant=True),
    'rock-cliff-gltf':    dict(meshes=1, materials=1, gltf=True),
    'graffiti-gltf':      dict(meshes=1, materials=1, gltf=True),
}


def reset():
    for collection in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.images,
                       bpy.data.textures, bpy.data.brushes):
        for item in list(collection):
            if collection is bpy.data.brushes and not item.texture:
                continue
            collection.remove(item)


def bsdf_of(mat):
    return next(n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')


def feeds(socket, label):
    """True when an image node labelled `label` reaches `socket` through any converters."""
    pending = [l.from_node for l in socket.links]
    while pending:
        node = pending.pop()
        if node.bl_idname == 'ShaderNodeTexImage' and node.label == label:
            return True
        pending.extend(l.from_node for s in node.inputs for l in s.links)
    return False


checked, missing = [], []
for key, expect in EXPECT.items():
    zips = sorted((SAMPLES / f'sample-{key}').glob('*.zip'))
    if not zips:
        missing.append(key)
        continue
    reset()
    result = bpy.ops.atb.import_zip(filepath=str(zips[0]))
    assert result == {'FINISHED'}, f'{key}: import {result}'
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    mats = {s.material for o in meshes for s in o.material_slots if s.material}
    assert len(meshes) == expect['meshes'], f'{key}: {len(meshes)} meshes, expected {expect["meshes"]}'
    assert len(mats) == expect['materials'], f'{key}: {len(mats)} materials {[m.name for m in mats]}'
    for mat in mats:
        bsdf = bsdf_of(mat)
        surface = next(n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output).inputs['Surface']
        foliage = any(n.bl_idname == 'ShaderNodeBsdfTranslucent' for n in mat.node_tree.nodes)
        for label in expect.get('linked', []):
            # Foliage: translucency and the opacity cut-out are mixed at shader level, after the BSDF.
            socket = surface if foliage and label in ('Translucency', 'Opacity') else bsdf.inputs[LINKED[label]]
            assert feeds(socket, label), f'{key}: {label} not linked to {socket.name}'
        if 'Translucency' in expect.get('linked', []):
            assert foliage, f'{key}: translucency without a Translucent BSDF'
        if 'Opacity' in expect.get('linked', []) and hasattr(mat, 'surface_render_method'):
            assert mat.surface_render_method == 'DITHERED', f'{key}: opacity without dithered render method'
        if expect.get('mask'):
            assert any(n.label == 'Mask' for n in mat.node_tree.nodes), f'{key}: mask map missing'
        if expect.get('disp') is not None:
            scale = next(n for n in mat.node_tree.nodes if n.get('atb_role') == 'disp_scale')
            assert abs(scale.outputs[0].default_value - expect['disp']) < 1e-6, f'{key}: displacement scale'
    if expect.get('plane'):
        dx, dy = expect['plane']
        dims = meshes[0].dimensions
        assert abs(dims.x - dx) < 1e-4 and abs(dims.y - dy) < 1e-4, f'{key}: plane {tuple(dims)} != {expect["plane"]}'
    if expect.get('plant'):
        spans = sorted((o.matrix_world.translation.x - o.dimensions.x / 2, o.matrix_world.translation.x + o.dimensions.x / 2)
                       for o in meshes)
        assert all(a[1] <= b[0] + 1e-4 for a, b in zip(spans, spans[1:])), f'{key}: plant variants overlap'
        assert len({o.parent for o in meshes}) == 1 and meshes[0].parent is not None, f'{key}: variants not grouped'
    if expect.get('brush'):
        tex = next((t for t in bpy.data.textures if t.type == 'IMAGE' and t.image), None)
        assert tex and '4K' in tex.image.name, f'{key}: brush texture missing or not capped at 4K'
    checked.append(key)

# A texture-only asset with a selection goes onto the selection's active slot, no plane is added.
key = 'rock-cliff-texture'
zips = sorted((SAMPLES / f'sample-{key}').glob('*.zip'))
if zips:
    reset()
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    keep = bpy.data.materials.new('UserKeep')
    cube.data.materials.append(bpy.data.materials.new('UserActive'))
    cube.data.materials.append(keep)
    cube.active_material_index = 0
    assert bpy.ops.atb.import_zip(filepath=str(zips[0])) == {'FINISHED'}
    assert [o for o in bpy.data.objects if o.type == 'MESH'] == [cube], 'a plane was added despite a selection'
    assert cube.material_slots[0].material.name.startswith('Rock_Cliff') and cube.material_slots[1].material == keep, \
        'selection: only the active slot may change'
    checked.append('selection')

def sample(key):
    zips = sorted((SAMPLES / f'sample-{key}').glob('*.zip'))
    return str(zips[0]) if zips else None


# Plants at a non-zero cursor with a name collision: world positions start at the cursor,
# LOD filtering survives Blender's ".001" suffix, no orphan meshes or billboard material remain.
z = sample('lady-fern-gltf')
if z:
    reset()
    blocker = bpy.data.objects.new('SM_wdvlditia_VarA_LOD1', bpy.data.meshes.new('blocker'))
    bpy.context.collection.objects.link(blocker)
    bpy.context.scene.cursor.location = (10, 20, 3)
    meshes_before = set(bpy.data.meshes)
    assert bpy.ops.atb.import_zip(filepath=z) == {'FINISHED'}
    plants = [o for o in bpy.data.objects if o.type == 'MESH' and o != blocker]
    assert len(plants) == 9, f'glTF plant with name collision: {len(plants)} meshes'
    xs = sorted(o.matrix_world.translation.x for o in plants)
    assert 10 <= xs[0] < 12 and all(abs(o.matrix_world.translation.y - 20) < 1e-3 and abs(o.matrix_world.translation.z - 3) < 1e-3
                                    for o in plants), f'plants not placed at the cursor: {xs[0]}'
    orphans = [m.name for m in bpy.data.meshes if m not in meshes_before and m.users == 0]
    assert not orphans, f'orphan meshes left: {orphans[:3]}'
    assert not any('Billboard' in m.name for m in bpy.data.materials), 'billboard material left behind'
    bpy.context.scene.cursor.location = (0, 0, 0)
    checked.append('plant-cursor-collision-orphans')

# Brush import leaves a user's same-named texture/brush and shared image untouched.
z = sample('coffee-stain')
if z:
    reset()
    import zipfile, tempfile
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(z) as zf:
        member = next(n for n in zf.namelist() if n.endswith('4K_Brush.jpg'))
        shared = Path(zf.extract(member, tmp))
    user_img = bpy.data.images.load(str(shared))
    user_img.colorspace_settings.name = 'sRGB'
    user_tex = bpy.data.textures.new('Coffee Stain', 'IMAGE')
    other_img = bpy.data.images.new('other', 4, 4)
    user_tex.image = other_img
    assert bpy.ops.atb.import_zip(filepath=z) == {'FINISHED'}
    assert user_img.colorspace_settings.name == 'sRGB', 'user image color space changed'
    assert user_tex.image == other_img, 'same-named user texture was overwritten'
    assert any(t.get('atb_asset') == 'sb4jej0p' for t in bpy.data.textures), 'ATBridge brush texture missing'
    checked.append('brush-user-data')

# Foliage shader stack on a reused material: splice where the shader went (a user's own mix),
# keep the user's output where it is, and avoid stacking new nodes on top of it.
z = sample('oak-leaves')
if z:
    reset()
    mat = bpy.data.materials.new('Oak_Leaves_sedlecvh2')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    out = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    bsdf.location, out.location = (0, 0), (320, 0)
    user_mix = nt.nodes.new('ShaderNodeMixShader')
    user_mix.location = (320, -400)
    emission = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(bsdf.outputs['BSDF'], user_mix.inputs[1])
    nt.links.new(emission.outputs['Emission'], user_mix.inputs[2])
    nt.links.new(user_mix.outputs['Shader'], out.inputs['Surface'])
    bpy.ops.mesh.primitive_plane_add()
    assert bpy.ops.atb.import_zip(filepath=z) == {'FINISHED'}
    assert out.inputs['Surface'].links[0].from_node == user_mix, 'user output chain bypassed'
    assert user_mix.inputs[1].links[0].from_node.get('atb_role') == 'mix_cutout', 'stack not spliced into the user chain'
    assert tuple(out.location) == (320, 0), 'user output moved'
    from ATBridge.core.node_layout import node_rect
    for n in nt.nodes:
        if n.get('atb_channel') == 'shader':
            for user in (out, user_mix):
                a, b = node_rect(n), node_rect(user)
                assert a[2] <= b[0] or b[2] <= a[0] or a[3] >= b[1] or b[3] >= a[1], f'{n.name} overlaps {user.name}'
    # Rebuilt from a package without translucency: the user chain gets the shader back.
    from ATBridge.core.asset_parser import AssetData, TextureInfo
    from ATBridge.core.material_builder import MaterialBuilder
    albedo = next(n for n in nt.nodes if n.get('atb_role') == 'tex:albedo').image.filepath
    plain = AssetData(id='sedlecvh2', name='Oak_Leaves', type='atlas', path=None,
                      textures=[TextureInfo('jpg', 'albedo', bpy.path.abspath(albedo))], texture_types=['albedo'])
    assert MaterialBuilder(plain).build() == mat
    assert user_mix.inputs[1].links[0].from_node == bsdf, 'shader not restored after the stack was dropped'
    assert not any(n.get('atb_channel') == 'shader' for n in nt.nodes), 'old shader stack kept'
    checked.append('foliage-user-chain')

    # Partial stack changes: whatever the old stack fed takes this build's final stack output.
    paths = {}

    def tex(kind):
        return TextureInfo('jpg', kind, paths[kind])
    reset()
    assert bpy.ops.atb.import_zip(filepath=z) == {'FINISHED'}
    full = next(m for m in bpy.data.materials if m.name.startswith('Oak_Leaves'))
    for n in full.node_tree.nodes:
        role = n.get('atb_role', '')
        if role.startswith('tex:') and n.image:
            paths[role[4:]] = bpy.path.abspath(n.image.filepath)
    nt = full.node_tree
    out = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    surface_from = lambda: out.inputs['Surface'].links[0].from_node.get('atb_role')

    def rebuild(kinds):
        asset = AssetData(id='sedlecvh2', name='Oak_Leaves', type='atlas', path=None,
                          textures=[tex(k) for k in kinds], texture_types=list(kinds))
        assert MaterialBuilder(asset).build() == full

    rebuild(['albedo', 'translucency'])
    assert surface_from() == 'mix_translucency', f'opacity removed: surface fed by {surface_from()}'
    rebuild(['albedo', 'translucency', 'opacity'])
    assert surface_from() == 'mix_cutout', f'opacity added: surface fed by {surface_from()}'

    # First stack insertion keeps the mute state of the shader's original link.
    rebuild(['albedo'])
    link = out.inputs['Surface'].links[0]
    link.is_muted = True
    rebuild(['albedo', 'translucency'])
    link = out.inputs['Surface'].links[0]
    assert link.from_node.get('atb_role') == 'mix_translucency' and link.is_muted, 'muted output link not kept'

    # A user node referencing an intermediate stack node keeps that role after a rebuild.
    rebuild(['albedo', 'translucency', 'opacity'])
    fade = nt.nodes.new('ShaderNodeMixShader')
    role = lambda r: next(n for n in nt.nodes if n.get('atb_role') == r)
    nt.links.new(role('transparent_bsdf').outputs[0], fade.inputs[1])
    nt.links.new(role('mix_cutout').outputs[0], fade.inputs[2])
    nt.links.new(fade.outputs[0], out.inputs['Surface'])
    rebuild(['albedo', 'translucency', 'opacity'])
    sources = [fade.inputs[i].links[0].from_node.get('atb_role') for i in (1, 2)]
    assert sources == ['transparent_bsdf', 'mix_cutout'], f'intermediate stack reference lost: {sources}'
    checked.append('stack-shape-changes')

# A glTF texture applied to a selection leaves no preview plane mesh behind.
z = sample('rock-cliff-gltf')
if z:
    reset()
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    meshes_before = set(bpy.data.meshes)
    assert bpy.ops.atb.import_zip(filepath=z) == {'FINISHED'}
    assert [o for o in bpy.data.objects if o.type == 'MESH'] == [cube], 'glTF preview object kept'
    orphans = [m.name for m in bpy.data.meshes if m not in meshes_before]
    assert not orphans, f'glTF selection left meshes: {orphans}'
    checked.append('gltf-selection-orphans')

print(f'PASS: {len(checked)} Fab sample checks ({", ".join(checked)})'
      + (f'; skipped missing samples: {", ".join(missing)}' if missing else '')
      + f' (Blender {bpy.app.version_string})')
