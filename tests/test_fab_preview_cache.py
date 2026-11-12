"""Managed Fab product-image cache regressions; no Blender needed."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

# Load the pure utils module through a package parent so nothing from the
# Blender-dependent addon package root is imported.
utils_dir = Path(__file__).resolve().parents[1] / 'utils'
package = types.ModuleType('atbridge_test_utils')
package.__path__ = [str(utils_dir)]
sys.modules[package.__name__] = package
spec = importlib.util.spec_from_file_location(
    'atbridge_test_utils.fab_preview_cache', utils_dir / 'fab_preview_cache.py')
fab_preview_cache = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fab_preview_cache
spec.loader.exec_module(fab_preview_cache)

IMAGE_NAME = hashlib.sha256(b'fab product image').hexdigest() + '.png'
IMAGE_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x00' * 57
LISTING_UUID = '3f2b8c64-9a1d-4e7f-b2c3-5d6e7f8a9b0c'
LISTING_URL = 'https://www.fab.com/listings/' + LISTING_UUID


class FabPreviewCacheTest(unittest.TestCase):
    def asset_key(self, asset_id):
        return hashlib.sha256(asset_id.encode('utf-8')).hexdigest()

    def payload(self, asset_id, **overrides):
        data = {'schema': 1, 'asset_id': asset_id, 'image': IMAGE_NAME,
                'listing_url': LISTING_URL, 'title': 'Weathered Rock'}
        data.update(overrides)
        return data

    def write_cache(self, root, asset_id, payload=None, image_size=None):
        root = Path(root)
        (root / 'images').mkdir(parents=True, exist_ok=True)
        (root / 'assets').mkdir(parents=True, exist_ok=True)
        image = root / 'images' / IMAGE_NAME
        image.write_bytes(IMAGE_BYTES if image_size is None else b'\x00' * image_size)
        record = root / 'assets' / (self.asset_key(asset_id) + '.json')
        record.write_text(json.dumps(payload or self.payload(asset_id)), encoding='utf-8')
        return record, image

    def test_valid_record_returns_expected_fields(self):
        for host in ('www.fab.com', 'fab.com'):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as root:
                asset_id = 'asset-01'
                record, image = self.write_cache(root, asset_id, payload=self.payload(
                    asset_id, listing_url='https://%s/listings/%s' % (host, LISTING_UUID)))
                result = fab_preview_cache.cached_product_image(asset_id, directory=root)
                self.assertEqual(Path(result['preview']), image.resolve())
                self.assertEqual(Path(result['preview']).read_bytes(), IMAGE_BYTES)
                self.assertEqual(result['preview_label'], 'Fab 商品图')
                self.assertEqual(result['listing_url'], 'https://%s/listings/%s' % (host, LISTING_UUID))
                self.assertEqual(result['title'], 'Weathered Rock')
                self.assertEqual(result['preview_token'], '%s|%s|%s' % (
                    IMAGE_NAME, image.stat().st_mtime_ns, record.stat().st_mtime_ns))

    def test_record_with_bom_and_unicode_title_round_trips(self):
        with tempfile.TemporaryDirectory() as root:
            asset_id = 'asset-01'
            title = '风化岩石 — 4K'
            (Path(root) / 'images').mkdir(parents=True)
            (Path(root) / 'assets').mkdir(parents=True)
            (Path(root) / 'images' / IMAGE_NAME).write_bytes(IMAGE_BYTES)
            record = Path(root) / 'assets' / (self.asset_key(asset_id) + '.json')
            record.write_text(json.dumps(self.payload(asset_id, title=title)), encoding='utf-8-sig')
            result = fab_preview_cache.cached_product_image(asset_id, directory=root)
            self.assertEqual(result['title'], title)

    def test_title_is_normalized(self):
        missing = self.payload('asset-01')
        missing.pop('title')
        cases = {
            'missing-title': (missing, '', 0),
            'non-string-title': (self.payload('asset-01', title=None), '', 0),
            'exactly-300': (self.payload('asset-01', title='r' * 300), 'r' * 300, 300),
            'over-300': (self.payload('asset-01', title='r' * 305), 'r' * 300, 300),
        }
        for name, (payload, expected_title, expected_length) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                self.write_cache(root, 'asset-01', payload=payload)
                result = fab_preview_cache.cached_product_image('asset-01', directory=root)
                self.assertEqual(result['title'], expected_title)
                self.assertEqual(len(result['title']), expected_length)

    def test_default_root_is_localappdata_atbridge_cache_fab(self):
        with tempfile.TemporaryDirectory() as base:
            with patch.dict(os.environ, {'LOCALAPPDATA': base}):
                self.assertEqual(fab_preview_cache.preview_cache_directory(),
                                 Path(base) / 'ATBridge' / 'Cache' / 'Fab')
            env = os.environ.copy()
            env.pop('LOCALAPPDATA', None)
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(fab_preview_cache.preview_cache_directory(),
                                 Path.home() / '.cache' / 'ATBridge' / 'Cache' / 'Fab')

    def test_call_without_directory_uses_default_root(self):
        asset_id = 'default-root-asset'
        with tempfile.TemporaryDirectory() as base:
            self.write_cache(Path(base) / 'ATBridge' / 'Cache' / 'Fab', asset_id)
            with patch.dict(os.environ, {'LOCALAPPDATA': base}):
                result = fab_preview_cache.cached_product_image(asset_id)
            self.assertEqual(result['listing_url'], LISTING_URL)

    def test_invalid_asset_id_inputs_return_empty(self):
        for asset_id in (None, 7, ''):
            with self.subTest(asset_id=asset_id), tempfile.TemporaryDirectory() as root:
                self.assertEqual(fab_preview_cache.cached_product_image(asset_id, directory=root), {})

    def test_asset_id_over_256_chars_is_rejected_even_when_record_exists(self):
        asset_id = 'x' * 257
        with tempfile.TemporaryDirectory() as root:
            self.write_cache(root, asset_id)
            self.assertEqual(fab_preview_cache.cached_product_image(asset_id, directory=root), {})

    def test_asset_id_of_exactly_256_chars_is_accepted(self):
        asset_id = 'x' * 256
        with tempfile.TemporaryDirectory() as root:
            self.write_cache(root, asset_id)
            result = fab_preview_cache.cached_product_image(asset_id, directory=root)
            self.assertEqual(result['listing_url'], LISTING_URL)

    def test_missing_or_corrupt_records_return_empty(self):
        cases = {
            'no-record-file': None,
            'broken-json': '{not valid json',
            'json-array': '[]',
            'json-string': '"asset-01"',
            'wrong-schema': json.dumps({'schema': 2, 'asset_id': 'asset-01', 'image': IMAGE_NAME,
                                        'listing_url': LISTING_URL}),
            'asset-id-mismatch': json.dumps({'schema': 1, 'asset_id': 'other', 'image': IMAGE_NAME,
                                             'listing_url': LISTING_URL}),
            'invalid-utf8': None,
        }
        for name, raw in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                (root / 'images').mkdir(parents=True)
                (root / 'assets').mkdir(parents=True)
                (root / 'images' / IMAGE_NAME).write_bytes(IMAGE_BYTES)
                record = root / 'assets' / (self.asset_key('asset-01') + '.json')
                if name == 'no-record-file':
                    pass
                elif name == 'invalid-utf8':
                    record.write_bytes(b'\x80\x81\x82')
                else:
                    record.write_text(raw, encoding='utf-8')
                self.assertEqual(fab_preview_cache.cached_product_image('asset-01', directory=root), {})

    def test_record_path_as_directory_returns_empty(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / 'images').mkdir(parents=True)
            (root / 'images' / IMAGE_NAME).write_bytes(IMAGE_BYTES)
            (root / 'assets' / (self.asset_key('asset-01') + '.json')).mkdir(parents=True)
            self.assertEqual(fab_preview_cache.cached_product_image('asset-01', directory=root), {})

    def test_record_size_cap_boundary(self):
        asset_id = 'asset-01'
        payload = self.payload(asset_id)
        payload['pad'] = 'x' * 20000
        overshoot = len(json.dumps(payload)) - 16384
        for pad_chars, accepted in (((20000 - overshoot), True), ((20000 - overshoot + 1), False)):
            with self.subTest(record_bytes=16384 + (0 if accepted else 1)), \
                    tempfile.TemporaryDirectory() as root:
                payload = self.payload(asset_id)
                payload['pad'] = 'x' * pad_chars
                self.write_cache(root, asset_id, payload=payload)
                result = fab_preview_cache.cached_product_image(asset_id, directory=root)
                if accepted:
                    self.assertEqual(result['listing_url'], LISTING_URL)
                else:
                    self.assertEqual(result, {})

    def test_invalid_image_names_are_rejected(self):
        hex_part = IMAGE_NAME.split('.')[0]
        names = {
            'missing-image-key': None,
            'non-string-image': 7,
            'uppercase-hex': hex_part.upper() + '.png',
            'too-short': hex_part[:63] + '.png',
            'too-long': hex_part + 'a' + '.png',
            'traversal': '../evil.png',
            'not-hex': 'rock.png',
            'empty-stem': '.png',
            'wrong-extension': hex_part + '.jpg',
        }
        for name, image in names.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                payload = self.payload('asset-01')
                if image is None:
                    payload.pop('image')
                else:
                    payload['image'] = image
                self.write_cache(root, 'asset-01', payload=payload)
                self.assertEqual(fab_preview_cache.cached_product_image('asset-01', directory=root), {})

    def test_unsupported_listing_urls_are_rejected(self):
        urls = {
            'missing-listing-url': None,
            'empty-url': '',
            'http-scheme': 'http://www.fab.com/listings/' + LISTING_UUID,
            'ftp-scheme': 'ftp://www.fab.com/listings/' + LISTING_UUID,
            'foreign-host': 'https://evil.com/listings/' + LISTING_UUID,
            'host-suffix-lookalike': 'https://www.fab.com.evil.com/listings/' + LISTING_UUID,
            'wrong-path': 'https://www.fab.com/products/' + LISTING_UUID,
            'short-uuid': 'https://www.fab.com/listings/' + LISTING_UUID[:-1],
            'trailing-segment': 'https://www.fab.com/listings/' + LISTING_UUID + '/extra',
            'non-443-port': 'https://www.fab.com:8443/listings/' + LISTING_UUID,
            'userinfo': 'https://user@www.fab.com/listings/' + LISTING_UUID,
            'misplaced-dashes': 'https://www.fab.com/listings/ffffffff-ffffffff-ffff-ffff-ffffffffffff',
            'invalid-ipv6-url': 'https://[::1',
            'numeric-url': 7,
            'object-url': {},
            'array-url': [],
        }
        for name, listing_url in urls.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                payload = self.payload('asset-01')
                if listing_url is None:
                    payload.pop('listing_url')
                else:
                    payload['listing_url'] = listing_url
                self.write_cache(root, 'asset-01', payload=payload)
                self.assertEqual(fab_preview_cache.cached_product_image('asset-01', directory=root), {})

    def test_image_size_bounds(self):
        with tempfile.TemporaryDirectory() as root:
            names = {'0' * 64 + '.png': 0, '1' * 64 + '.png': 8 * 1024 ** 2,
                     '2' * 64 + '.png': 8 * 1024 ** 2 + 1}
            for filename, size in names.items():
                (Path(root) / 'images').mkdir(parents=True, exist_ok=True)
                (Path(root) / 'images' / filename).write_bytes(b'\x00' * size)
            for filename, accepted in (('0' * 64 + '.png', False), ('1' * 64 + '.png', True),
                                       ('2' * 64 + '.png', False)):
                with self.subTest(image=filename, accepted=accepted):
                    payload = self.payload('asset-01')
                    payload['image'] = filename
                    self.write_cache(root, 'asset-01', payload=payload)
                    result = fab_preview_cache.cached_product_image('asset-01', directory=root)
                    if accepted:
                        self.assertTrue(result['preview'])
                    else:
                        self.assertEqual(result, {})

    def test_symlink_to_image_outside_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            outside_image = Path(outside) / 'outside.png'
            outside_image.write_bytes(IMAGE_BYTES)
            link = Path(root) / 'images' / IMAGE_NAME
            link.parent.mkdir(parents=True)
            (Path(root) / 'assets').mkdir()
            try:
                link.symlink_to(outside_image)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f'symlinks unavailable: {error}')
            (Path(root) / 'assets' / (self.asset_key('asset-01') + '.json')).write_text(
                json.dumps(self.payload('asset-01')), encoding='utf-8')
            self.assertEqual(fab_preview_cache.cached_product_image('asset-01', directory=root), {})

    def test_symlinked_cache_locations_are_rejected(self):
        for location in ('junction-root', 'root', 'assets-directory', 'images-directory', 'record-file'):
            with self.subTest(location=location), \
                    tempfile.TemporaryDirectory() as holder, tempfile.TemporaryDirectory() as external:
                holder = Path(holder)
                external = Path(external)
                root = holder / 'cache'
                self.write_cache(root, 'asset-01')
                record = root / 'assets' / (self.asset_key('asset-01') + '.json')
                try:
                    if location == 'root':
                        directory = holder / 'link-root'
                        directory.symlink_to(root, target_is_directory=True)
                    elif location == 'assets-directory':
                        (external / 'record.json').write_text(record.read_text(encoding='utf-8'))
                        record.unlink()
                        (root / 'assets').symlink_to(external, target_is_directory=True)
                        directory = root
                    elif location == 'images-directory':
                        (external / IMAGE_NAME).write_bytes(IMAGE_BYTES)
                        (root / 'images' / IMAGE_NAME).unlink()
                        (root / 'images').symlink_to(external, target_is_directory=True)
                        directory = root
                    elif location == 'record-file':
                        outside_record = external / 'record.json'
                        outside_record.write_text(record.read_text(encoding='utf-8'))
                        record.unlink()
                        record.symlink_to(outside_record)
                        directory = root
                    else:
                        directory = holder / 'junction-root'
                        completed = subprocess.run(
                            ['cmd', '/c', 'mklink', '/J', str(directory), str(root)],
                            capture_output=True, text=True)
                        if completed.returncode != 0:
                            self.skipTest(f'junctions unavailable: {completed.stderr.strip()}')
                except (OSError, NotImplementedError) as error:
                    self.skipTest(f'symlinks unavailable: {error}')
                self.assertEqual(fab_preview_cache.cached_product_image('asset-01', directory=directory), {})

    def test_symlink_to_image_inside_root_still_resolves(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            real_image = root / 'images' / ('f' * 63 + 'e.png')
            real_image.parent.mkdir(parents=True)
            real_image.write_bytes(IMAGE_BYTES)
            link = root / 'images' / IMAGE_NAME
            try:
                link.symlink_to(real_image)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f'symlinks unavailable: {error}')
            (root / 'assets').mkdir()
            (root / 'assets' / (self.asset_key('asset-01') + '.json')).write_text(
                json.dumps(self.payload('asset-01')), encoding='utf-8')
            result = fab_preview_cache.cached_product_image('asset-01', directory=root)
            self.assertEqual(Path(result['preview']), real_image.resolve())

    def test_preview_token_tracks_image_and_record_updates(self):
        asset_id = 'asset-01'
        with tempfile.TemporaryDirectory() as root:
            record, image = self.write_cache(root, asset_id)
            record_mtime_ns = record.stat().st_mtime_ns
            original = fab_preview_cache.cached_product_image(asset_id, directory=root)
            self.assertEqual(original['preview_token'], '%s|%s|%s' % (
                IMAGE_NAME, image.stat().st_mtime_ns, record_mtime_ns))

            hour = 3600 * 10 ** 9
            now_ns = time.time_ns()
            os.utime(image, ns=(now_ns - hour, now_ns - hour))
            after_image_update = fab_preview_cache.cached_product_image(asset_id, directory=root)
            self.assertNotEqual(after_image_update['preview_token'], original['preview_token'])

            os.utime(record, ns=(now_ns - 2 * hour, now_ns - 2 * hour))
            after_record_update = fab_preview_cache.cached_product_image(asset_id, directory=root)
            self.assertNotEqual(after_record_update['preview_token'], after_image_update['preview_token'])
            self.assertEqual(after_record_update['preview_token'], '%s|%s|%s' % (
                IMAGE_NAME, image.stat().st_mtime_ns, record.stat().st_mtime_ns))
            self.assertEqual(after_record_update['listing_url'], LISTING_URL)

    def test_image_older_than_90_days_is_rejected(self):
        asset_id = 'asset-01'
        day = 86400 * 10 ** 9
        with tempfile.TemporaryDirectory() as root:
            self.write_cache(root, asset_id)
            image = Path(root) / 'images' / IMAGE_NAME
            now_ns = time.time_ns()
            os.utime(image, ns=(now_ns - 89 * day, now_ns - 89 * day))
            result = fab_preview_cache.cached_product_image(asset_id, directory=root)
            self.assertTrue(result['preview'])
            os.utime(image, ns=(now_ns - 91 * day, now_ns - 91 * day))
            self.assertEqual(fab_preview_cache.cached_product_image(asset_id, directory=root), {})


if __name__ == '__main__':
    unittest.main()
