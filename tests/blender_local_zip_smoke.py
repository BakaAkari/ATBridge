"""Blender smoke: no extraction-path setup, renamed ZIP, recent download import."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
assert addon_utils.enable(ROOT.name, default_set=True, persistent=False)
from ATBridge.preferences import get_addon_preferences

try:
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    assert len(args) <= 1, 'Usage: blender ... -- [real-user-owned.zip]'
    real_zip = Path(args[0]).expanduser().resolve() if args else None
    if real_zip is not None:
        assert real_zip.is_file(), f'ZIP file does not exist: {real_zip}'

    with tempfile.TemporaryDirectory(prefix='atbridge-local-') as directory:
        root = Path(directory)
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        if real_zip is not None:
            source_before = real_zip.read_bytes()
            source_stat = real_zip.stat()
            result = bpy.ops.atb.import_zip(filepath=str(real_zip), cache_directory=str(root / 'cache'))
            assert result == {'FINISHED'}, f'Real ZIP import failed: {result}'
            meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
            assert meshes, 'Real ZIP import produced no mesh objects'
            vertices = sum(len(obj.data.vertices) for obj in meshes)
            polygons = sum(len(obj.data.polygons) for obj in meshes)
            material_images = set()
            for obj in meshes:
                for slot in obj.material_slots:
                    material = slot.material
                    if material and material.use_nodes and material.node_tree:
                        material_images.update(node.image for node in material.node_tree.nodes
                            if node.type == 'TEX_IMAGE' and node.image is not None)
            image_details = []
            for image in sorted(material_images, key=lambda item: item.name):
                dimensions = tuple(image.size)
                pixels = image.pixels
                assert dimensions[0] > 0 and dimensions[1] > 0 and len(pixels) > 0, \
                    f'Material image has no pixel data: {image.name}'
                image_details.append(f'{image.name}={dimensions[0]}x{dimensions[1]}')
            source_after = real_zip.stat()
            assert real_zip.read_bytes() == source_before, 'Import modified the source ZIP bytes'
            assert source_after.st_size == source_stat.st_size and source_after.st_mtime_ns == source_stat.st_mtime_ns, \
                'Import changed the source ZIP metadata'
            digest = hashlib.sha256(source_before).hexdigest()
            print(f'PASS: real ZIP imported from disposable cache; meshes={len(meshes)}, vertices={vertices}, '
                f'polygons={polygons}, material images={len(image_details)} [{", ".join(image_details)}], '
                f'source sha256={digest}')
        else:
            bpy.ops.mesh.primitive_cube_add()
            fbx = root / 'fixture.fbx'
            bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True)
            archive = root / 'renamed by user (1).ZIP'
            with zipfile.ZipFile(archive, 'w') as output:
                output.write(fbx, fbx.name)
                output.writestr('unrelated.json', '{}')
                output.writestr('fixture.json', json.dumps({'id': 'fixture', 'name': 'Fixture',
                    'categories': ['3d'], 'models': [{'uri': fbx.name}], 'maps': []}))
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
            prefs = get_addon_preferences(bpy.context)
            prefs.fab_downloads_path = str(root)
            # Keep add-on history (CONFIG) separate from extracted assets (DATAFILES).
            original_resource = bpy.utils.user_resource
            def isolated_user_resource(resource_type, path=None, create=False):
                base = root / ('config' if resource_type == 'CONFIG' else 'datafiles')
                target = base / path if path else base
                target.mkdir(parents=True, exist_ok=True)
                return str(target)
            bpy.utils.user_resource = isolated_user_resource
            prefs.fab_assets_path = ''
            try:
                assert bpy.ops.atb.fab_local(action='refresh') == {'FINISHED'}
                state = bpy.context.window_manager.atb_fab_local
                assert len(state.files) == 1 and state.files[0].name == archive.name
                assert bpy.ops.atb.fab_local(action='import') == {'FINISHED'}
                assert len([obj for obj in bpy.context.scene.objects if obj.type == 'MESH']) == 1
                assert (root / 'datafiles' / 'ATBridge' / 'assets').is_dir()
                # Same-named imports use independent caches, without leftover models or textures.
                assert bpy.ops.atb.fab_local(action='import') == {'FINISHED'}
                assert len(list((root / 'datafiles' / 'ATBridge' / 'assets').iterdir())) == 2
            finally:
                bpy.utils.user_resource = original_resource
            print('PASS: renamed uppercase ZIP, unrelated JSON ignored, default cache, recent list and actual import, independent extraction folders')
finally:
    addon_utils.disable(ROOT.name, default_set=False)
