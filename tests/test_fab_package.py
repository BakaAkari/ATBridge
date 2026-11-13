"""Pure-Python checks for core/fab_package.py (no Blender)."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('atb_fab_package', Path(__file__).resolve().parents[1] / 'core' / 'fab_package.py')
fp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fp)


def meta(asset_type, **extra):
    return {'id': 'abc123', 'semanticTags': {'asset_type': asset_type, 'name': 'Asset'}, **extra}


class FabPackageTest(unittest.TestCase):
    def test_generic_map_beats_lod_specific_in_any_order(self):
        files = ['/p/Asset_LOD0.fbx', '/p/Asset_4K_Normal_LOD2.png', '/p/Asset_4K_Normal.png']
        for order in (files, list(reversed(files))):
            pkg = fp.analyse(meta('3D asset'), order)
            self.assertEqual(Path(pkg.textures['normal']).name, 'Asset_4K_Normal.png')

    def test_model_asset_without_importable_model_is_unsupported(self):
        pkg = fp.analyse(meta('3D asset'), ['/p/Asset.abc', '/p/Asset_1K_Albedo.png'])
        self.assertEqual(pkg.package_format, 'unsupported')

    def test_texture_kinds_stay_texture_only(self):
        pkg = fp.analyse(meta('surface'), ['/p/Asset_2K_BaseColor.jpg'])
        self.assertEqual(pkg.package_format, 'textures')

    def test_plant_variants_and_billboard_maps(self):
        files = ['/p/P_x_VarA_LOD0.fbx', '/p/P_x_VarA_LOD1.fbx', '/p/P_x_VarB_LOD0.fbx',
                 '/p/P_1K_Opacity.jpg', '/p/P_1K_Billboard_Opacity.jpg']
        pkg = fp.analyse(meta('3D plant'), files)
        self.assertEqual([v.name for v in pkg.variants], ['VarA', 'VarB'])
        self.assertEqual(Path(pkg.textures['opacity']).name, 'P_1K_Opacity.jpg')

    def test_multi_resolution_package_caps_at_4k(self):
        files = [f'/p/B_{k}K_Brush.jpg' for k in (1, 2, 4, 8)]
        pkg = fp.analyse(meta('brush'), files)
        self.assertEqual(pkg.resolution, 4)
        self.assertEqual(Path(pkg.textures['brush']).name, 'B_4K_Brush.jpg')

    def test_scan_area_and_height(self):
        m = meta('decal', meta=[{'key': 'scanArea', 'value': '4x2 m'}, {'key': 'height', 'value': '0.151 m'}])
        pkg = fp.analyse(m, ['/p/D_1K_BaseColor.jpg'])
        self.assertEqual(pkg.physical_size, (4.0, 2.0))
        self.assertAlmostEqual(pkg.displacement_height, 0.151)


if __name__ == '__main__':
    unittest.main()
