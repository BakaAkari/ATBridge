"""File discovery and renamed/multi-JSON package regressions; no Blender needed."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
import zipfile
from unittest.mock import patch

# Give fab_files a package parent so its relative zip_safety import is exercised
# without importing the Blender-dependent addon package.
utils_dir = Path(__file__).resolve().parents[1] / 'utils'
package = types.ModuleType('atbridge_test_utils')
package.__path__ = [str(utils_dir)]
sys.modules[package.__name__] = package
spec = importlib.util.spec_from_file_location('atbridge_test_utils.fab_files', utils_dir / 'fab_files.py')
fab_files = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fab_files
spec.loader.exec_module(fab_files)


class FabFilesTest(unittest.TestCase):
    def archive(self, files):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return zipfile.ZipFile(buffer)

    def write_asset_zip(self, directory, filename, metadata, members=None):
        path = Path(directory) / filename
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('asset.json', json.dumps(metadata))
            for name, data in (members or {}).items():
                archive.writestr(name, data)
        return path

    def test_metadata_ignores_unrelated_json_and_zip_name(self):
        with self.archive({'first.json': '{}', 'asset.json': json.dumps(
                {'id': 'rock', 'models': [{'uri': 'rock.fbx'}]})}) as archive:
            self.assertEqual(fab_files.read_asset_metadata(archive)['id'], 'rock')

    def test_ambiguous_and_unsupported_metadata_rejected(self):
        with self.archive({'one.json': '{"id":"a","models":[{"uri":"a.fbx"}]}',
                           'two.json': '{"id":"b","models":[{"uri":"b.fbx"}]}'}) as archive:
            with self.assertRaisesRegex(ValueError, '多个资产'):
                fab_files.read_asset_metadata(archive)
        with self.archive({'not_asset.json': '{"id":"config"}'}) as archive:
            with self.assertRaisesRegex(ValueError, '没有可识别'):
                fab_files.read_asset_metadata(archive)

    def test_invalid_json_and_malformed_metadata_are_not_selected(self):
        with self.archive({'broken.json': '{not valid json',
                           'array.json': '[{"id":"rock","models":[{}]}]',
                           'blank_id.json': '{"id":"  ","models":[{}]}',
                           'wrong_collections.json': '{"id":"rock","models":{},"maps":[]}'}) as archive:
            with self.assertRaisesRegex(ValueError, '没有可识别'):
                fab_files.read_asset_metadata(archive)

    def test_metadata_rejects_non_object_entries_and_invalid_uris(self):
        for metadata in (
                '{"id":"rock","models":[null]}',
                '{"id":"rock","models":[{"uri":7}]}',
                '{"id":"rock","maps":[{"uri":"  "}]}'):
            with self.subTest(metadata=metadata), self.archive({'asset.json': metadata}) as archive:
                with self.assertRaisesRegex(ValueError, '没有可识别'):
                    fab_files.read_asset_metadata(archive)

    def test_invalid_json_does_not_hide_valid_asset_metadata(self):
        with self.archive({'broken.json': '{not valid json',
                           'asset.json': '{"id":"rock","models":[{"uri":"rock.fbx"}]}'}) as archive:
            self.assertEqual(fab_files.read_asset_metadata(archive)['id'], 'rock')

    def test_describe_zip_uses_metadata_name_not_archive_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'renamed download (1).zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('asset.json', json.dumps({
                    'id': 'rock-01', 'name': 'Weathered Rock',
                    'models': [{'uri': 'rock.fbx'}], 'maps': []}))
                archive.writestr('rock.fbx', b'fbx')
            result = fab_files.describe_zip(path)
            self.assertEqual(result['title'], 'Weathered Rock')
            self.assertEqual(result['detail'], '3D 资产 · FBX')
            self.assertEqual(result['asset_id'], 'rock-01')
            self.assertEqual(result['error'], '')

    def test_describe_zip_reports_unsupported_model_formats_including_abc(self):
        # Only an unsupported model format is shipped.
        for name, extra in (('abc', {'rock.abc': b'abc'}), ('usdz', {'rock.usdz': b'usdz'})):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / f'unsupported-{name}.zip'
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr('asset.json', json.dumps({
                        'id': 'rock-01', 'name': 'Rock',
                        'models': [{'uri': 'rock.fbx'}], 'maps': []}))
                    for member, data in extra.items():
                        archive.writestr(member, data)
                result = fab_files.describe_zip(path)
                self.assertIn('不支持', result['error'])
                self.assertEqual(result['asset_id'], '')

    def test_describe_zip_accepts_gltf_and_reports_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fern_ue_low.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('fern.json', json.dumps({
                    'id': 'fern01', 'semanticTags': {'asset_type': '3D plant', 'name': 'Fern'},
                    'models': [{'uri': 'fern_LOD0.fbx'}], 'maps': [{'uri': 'fern_1K_Albedo.jpg'}]}))
                archive.writestr('fern_tier_3.gltf', b'{}')
                archive.writestr('Textures/T_fern01_1K_B.jpg', b'jpg')
            result = fab_files.describe_zip(path)
            self.assertEqual(result['error'], '')
            self.assertEqual(result['detail'], '植物 · GLTF · 1K')

    def test_describe_zip_quality_hint(self):
        cases = [('rock_low.zip', 'rock.fbx', '1K', 'Low 品质'),
                 ('rock_medium.zip', 'rock.fbx', '2K', 'Medium 品质'),
                 ('rock_high.zip', 'rock.fbx', '1K', ''),
                 ('rock_raw.zip', 'rock.fbx', '8K', ''),
                 ('rock_1k.zip', None, '1K', '只有 1K'),
                 ('rock_2k.zip', None, '2K', '只有 2K'),
                 ('rock_4k.zip', None, '4K', '')]
        for name, model, res, expected in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / name
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr('rock.json', json.dumps({
                        'id': 'rock01', 'semanticTags': {'asset_type': '3D asset' if model else 'surface'},
                        'models': [{'uri': 'rock.fbx'}] if model else [],
                        'maps': [{'uri': f'rock_{res}_Albedo.jpg'}]}))
                    if model:
                        archive.writestr(model, b'fbx')
                    archive.writestr(f'rock_{res}_Albedo.jpg', b'jpg')
                hint = fab_files.describe_zip(path)['quality_hint']
                if expected:
                    self.assertIn(expected, hint)
                else:
                    self.assertEqual(hint, '')

    def test_quality_hints_have_english_text(self):
        spec = importlib.util.spec_from_file_location('atbridge_hint_locale', utils_dir / 'localization.py')
        locale = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(locale)
        translate_message = locale.translate_message
        for message in ('这是 Low 品质下载，模型已精简、贴图分辨率较低；渲染建议在 Fab 改下 High 或 Raw',
                        '贴图最高只有 1K，近景渲染建议在 Fab 改下 4K 或 8K'):
            english = translate_message(message, 'en_US')
            self.assertNotEqual(english, message)
            self.assertTrue('Low' in english or '1K' in english)

    def test_describe_zip_falls_back_to_humanized_zip_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Weathered_Rock_1K.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('asset.json', json.dumps({
                    'id': 'rock', 'models': [{'uri': 'rock.fbx'}], 'maps': []}))
            result = fab_files.describe_zip(path)
            self.assertEqual(result['title'], 'Weathered')
            self.assertEqual(result['asset_id'], 'rock')

    def test_describe_zip_rejects_unsafe_archive_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'unsafe.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('asset.json', json.dumps({
                    'id': 'rock-01', 'models': [{'uri': 'rock.fbx'}], 'maps': []}))
                archive.writestr('../outside.txt', 'unsafe')
            result = fab_files.describe_zip(path)
            self.assertIn('Unsafe ZIP entry', result['error'])
            self.assertEqual(result['asset_id'], '')

    def test_describe_zip_accepts_metadata_preview_larger_than_one_mib(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preview_directory = root / 'previews'
            preview_directory.mkdir()
            payload = b'x' * (1024 ** 2 + 17)
            path = self.write_asset_zip(root, 'asset.zip', {
                'id': 'asset-01', 'models': [{'uri': 'asset.fbx'}], 'maps': [],
                'previews': {'images': [{'uri': 'id.png'}]},
            }, {'id.png': payload})

            result = fab_files.describe_zip(path, preview_directory)

            self.assertEqual(result['error'], '')
            self.assertTrue(result['preview'])
            self.assertEqual(Path(result['preview']).read_bytes(), payload)
            self.assertEqual(result['preview_label'], '模型缩略图')

    def test_describe_zip_does_not_use_basecolor_when_preview_reference_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_asset_zip(Path(directory), 'asset.zip', {
                'id': 'asset-01', 'models': [{'uri': 'asset.fbx'}], 'maps': [],
                'previews': {'images': [{'uri': 'preview/missing.png'}]},
            }, {'Textures/asset_basecolor.jpg': b'material texture'})

            result = fab_files.describe_zip(path, Path(directory) / 'previews')

            self.assertEqual(result['error'], '')
            self.assertEqual(result['preview'], '')
            self.assertIn('缺少可用缩略图', result['preview_label'])

    def test_describe_zip_ignores_malformed_preview_metadata(self):
        malformed = (
            {'images': {'uri': 'id.png'}},
            {'images': [None, 'id.png', {'uri': 12}, {'path': 'id.png'}]},
            ['not', 'an', 'object'],
        )
        for previews in malformed:
            with self.subTest(previews=previews), tempfile.TemporaryDirectory() as directory:
                path = self.write_asset_zip(Path(directory), 'asset.zip', {
                    'id': 'asset-01', 'models': [{'uri': 'asset.fbx'}], 'maps': [],
                    'previews': previews,
                }, {'id.png': b'valid image member'})

                result = fab_files.describe_zip(path, Path(directory) / 'previews')

                self.assertEqual(result['error'], '')
                self.assertEqual(result['preview'], '')
                self.assertEqual(result['preview_label'], '资产包未包含模型缩略图')

    def test_describe_zip_does_not_fetch_external_preview_uris(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_asset_zip(Path(directory), 'asset.zip', {
                'id': 'asset-01', 'models': [{'uri': 'asset.fbx'}], 'maps': [],
                'previews': {'images': [{'uri': 'https://example.invalid/previews/id.png'}]},
            }, {'Textures/asset_basecolor.jpg': b'material texture'})
            with patch('urllib.request.urlopen', side_effect=AssertionError('external preview fetched')) as urlopen:
                result = fab_files.describe_zip(path, Path(directory) / 'previews')

            self.assertEqual(result['error'], '')
            self.assertEqual(result['preview'], '')
            urlopen.assert_not_called()

    def test_describe_zip_skips_preview_over_eight_mib_without_rejecting_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oversized = b'x' * (8 * 1024 ** 2 + 1)
            path = self.write_asset_zip(root, 'asset.zip', {
                'id': 'asset-01', 'models': [{'uri': 'asset.fbx'}], 'maps': [],
                'previews': {'images': [{'uri': 'id.png'}]},
            }, {'id.png': oversized})

            result = fab_files.describe_zip(path, root / 'previews')

            self.assertEqual(result['error'], '')
            self.assertEqual(result['asset_id'], 'asset-01')
            self.assertEqual(result['preview'], '')
            self.assertIn('缺少可用缩略图', result['preview_label'])

    def test_aggregate_metadata_size_is_capped_without_large_zip_payloads(self):
        class Entry:
            def __init__(self, name):
                self.filename = name
                self.file_size = 8 * 1024 ** 2

        class FakeArchive:
            def infolist(self):
                return [Entry(f'{index}.json') for index in range(5)]

            def read(self, entry):
                return b'{}'

        with self.assertRaisesRegex(ValueError, 'JSON 元数据过大'):
            fab_files.read_asset_metadata(FakeArchive())

    def test_recent_list_ignores_partial_and_unrelated_subfolders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'renamed (1).ZIP').write_bytes(b'zip')
            (root / 'still.zip.partial').write_bytes(b'incomplete')
            (root / 'empty.zip').touch()
            native = root / 'ATBridge' / 'job'
            native.mkdir(parents=True)
            (native / 'rock.zip').write_bytes(b'zip')
            unrelated = root / 'other'
            unrelated.mkdir()
            (unrelated / 'not-for-atbridge.zip').write_bytes(b'zip')
            paths = {path.name for path, _, _ in fab_files.recent_zip_files(root)}
            self.assertEqual(paths, {'renamed (1).ZIP', 'rock.zip'})

    def test_recent_list_is_bounded_and_respects_limit_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, timestamp in [('older.zip', 100), ('newest.zip', 300), ('middle.zip', 200)]:
                path = root / name
                path.write_bytes(b'zip')
                os.utime(path, ns=(timestamp * 1_000_000_000, timestamp * 1_000_000_000))
            supported = root / 'ATBridge' / 'job'
            supported.mkdir(parents=True)
            nested = supported / 'deeper'
            nested.mkdir()
            (nested / 'too-deep.zip').write_bytes(b'zip')

            found = fab_files.recent_zip_files(root, limit=2)
            self.assertEqual([path.name for path, _, _ in found], ['newest.zip', 'middle.zip'])
            self.assertEqual([size for _, _, size in found], [3, 3])

    def test_recent_list_ignores_symlinks_resolving_outside_selected_folder(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            external_zip = Path(outside) / 'external.zip'
            external_zip.write_bytes(b'zip')
            link = root / 'external.zip'
            try:
                link.symlink_to(external_zip)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f'symlinks unavailable: {error}')

            self.assertEqual(fab_files.recent_zip_files(root), [])


if __name__ == '__main__':
    unittest.main()
