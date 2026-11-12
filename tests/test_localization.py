"""Catalog regressions without Blender, the UI, or the network."""
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('atbridge_locale_test', ROOT / 'utils' / 'localization.py')
locale = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locale)


class LocalizationTest(unittest.TestCase):
    def test_locale_fallback(self):
        for code in ('zh_CN', 'zh-Hans', 'zh_HANT', 'ZH-tw'):
            self.assertEqual(locale.normalize_language(code), 'zh_CN')
        for code in ('en_US', 'en-GB', 'fr_FR', 'de-DE', 'ja_JP', 'not-a-locale'):
            self.assertEqual(locale.normalize_language(code), 'en_US')
        self.assertEqual(locale.normalize_language('DEFAULT', 'zh-Hans'), 'zh_CN')
        self.assertEqual(locale.normalize_language('auto', 'fr-FR'), 'en_US')

    def test_status_parameters_preserve_user_data(self):
        message = '已导入：Asset · 石头 %s {0} · 新增 3 个对象'
        self.assertEqual(locale.translate_message(message, 'en_US'),
                         'Imported: Asset · 石头 %s {0} · 3 objects added')
        self.assertEqual(locale.translate_message(message, 'zh_CN'), message)
        self.assertEqual(locale.translate_message(message + '（导入记录未保存）', 'en_US'),
                         'Imported: Asset · 石头 %s {0} · 3 objects added (import history could not be saved)')

    def test_unknown_native_details_and_paths_preserved(self):
        path = 'C:/资产/下载/Stone %s {0}.zip'
        self.assertEqual(locale.translate_message(path, 'en_US'), path)
        self.assertEqual(locale.translate_message('导入失败：Native error: ' + path, 'en_US'),
                         'Import failed: Native error: ' + path)
        self.assertEqual(locale.translate_message('材质资产 · 4K', 'en_US'), 'Material asset · 4K')

    def test_all_format_placeholders_retained(self):
        for key, value in locale.ENGLISH.items():
            with self.subTest(key=key):
                self.assertEqual(re.findall(r'%[sd]', key), re.findall(r'%[sd]', value))
                self.assertEqual(sorted(re.findall(r'\{\d+(?::[^}]+)?\}', key)),
                                 sorted(re.findall(r'\{\d+(?::[^}]+)?\}', value)))

    def test_native_literal_catalog_coverage(self):
        for path in (ROOT / 'browser').glob('*.cs'):
            for match in re.finditer(r'L\.(?:T|F)\("((?:\\.|[^"\\])*)"', path.read_text(encoding='utf-8')):
                key = json.loads('"' + match[1] + '"')
                with self.subTest(file=path.name, key=key):
                    self.assertIn(key, locale.ENGLISH)

    def test_catalog_is_main_assembly_resource(self):
        # *.en.json would otherwise become a satellite and break L.Load on first use.
        import xml.etree.ElementTree as ET
        project = ET.parse(ROOT / 'browser' / 'ATBridge.FabBrowser.csproj')
        resource = next(item for item in project.iter('EmbeddedResource')
                        if item.get('LogicalName') == 'ATBridge.Fab.en.json')
        self.assertEqual(resource.get('WithCulture'), 'false')


if __name__ == '__main__':
    unittest.main()
