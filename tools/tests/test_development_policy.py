"""Development version synchronization and engine-owned punctuation policy."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERSIONS = load_tool('development_version')
TEXT_POLICY = load_tool('text_policy')
API_DOCS = load_tool('normalize_api_docs')


class DevelopmentPolicyTest(unittest.TestCase):
    def test_next_patch_is_based_on_published_build_not_current_edit_count(self):
        self.assertEqual(VERSIONS.next_patch_version('v0.0.13'), '0.0.14')
        self.assertEqual(VERSIONS.next_patch_version('v1.2.99-beta.2'), '1.2.100')
        with self.assertRaises(ValueError):
            VERSIONS.next_patch_version('latest')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project = root / 'Project.xml'
            version = root / 'VERSION'
            project.write_bytes(b'<?xml version="1.0"?>\r\n<project><app version="0.0.13"/></project>\r\n')
            version.write_bytes(b'0.0.13\r\n')
            branding = root / 'source' / 'EngineBranding.hx'
            branding.parent.mkdir()
            branding.write_text("class EngineBranding {static var FALLBACK_VERSION:String = '0.0.13';}", encoding='utf-8')
            readme = root / 'README.md'
            guide = root / 'USER-README.txt'
            readme.write_bytes(b'# CammieEngine v0.0.13\r\n\r\nKeep this guide text.\r\n')
            guide.write_bytes(b'CammieEngine v0.0.13 - alpha player guide\r\n')
            with self.assertRaises(ValueError):
                VERSIONS.configure_development_version(root, 'v0.0.13')
            VERSIONS.configure_development_version(root, 'v0.0.13', apply=True)
            first_project = project.read_bytes()
            first_version = version.read_bytes()
            self.assertIn(b'<?xml version="1.0"?>', first_project)
            self.assertIn(b'<app version="0.0.14"', first_project)
            self.assertEqual(first_version, b'0.0.14\r\n')
            self.assertIn("FALLBACK_VERSION:String = '0.0.14'", branding.read_text())
            self.assertEqual(readme.read_bytes(), b'# CammieEngine v0.0.14\r\n\r\nKeep this guide text.\r\n')
            self.assertEqual(guide.read_bytes(), b'CammieEngine v0.0.14 - alpha player guide\r\n')
            VERSIONS.configure_development_version(root, 'v0.0.13', apply=True)
            self.assertEqual(project.read_bytes(), first_project)
            self.assertEqual(version.read_bytes(), first_version)
            self.assertEqual(readme.read_bytes(), b'# CammieEngine v0.0.14\r\n\r\nKeep this guide text.\r\n')
            VERSIONS.configure_development_version(root, 'v0.0.14', apply=True)
            self.assertEqual(version.read_text().strip(), '0.0.15')

    def test_no_disallowed_punctuation_in_engine_owned_text(self):
        self.assertEqual(list(TEXT_POLICY.punctuation_violations(ROOT)), [])

    def test_generated_api_postprocessor_preserves_other_bytes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            nested = root / 'thirdparty'
            nested.mkdir()
            punctuation = chr(0x2014).encode('utf-8')
            original = b'\xef\xbb\xbf<p>caf\xc3\xa9 ' + punctuation + b' text</p>\r\n' + punctuation + b'\n'
            html = nested / 'Type.HTML'
            html.write_bytes(original)
            retained = root / 'asset.bin'
            retained.write_bytes(punctuation)
            script = root / 'script.js'
            script.write_bytes(punctuation)
            self.assertEqual(API_DOCS.normalize_api_docs(root), (1, 2))
            self.assertEqual(html.read_bytes(), original.replace(punctuation, b'-'))
            self.assertEqual(retained.read_bytes(), punctuation)
            self.assertEqual(script.read_bytes(), punctuation)
            self.assertEqual(API_DOCS.normalize_api_docs(root), (0, 0))
        with self.assertRaises(ValueError):
            API_DOCS.normalize_api_docs(root)
        batch = (ROOT / 'builddocs.bat').read_bytes()
        self.assertIn(b'python tools/normalize_api_docs.py --docs docs', batch)
        self.assertEqual(batch.count(b'\n'), batch.count(b'\r\n'))
        self.assertLess(batch.index(b'haxelib run dox'), batch.index(b'python tools/normalize_api_docs.py'))

    def test_retained_sources_vendor_and_generated_builds_are_outside_text_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in ('README.md', 'source/Engine.hx', 'tools/reports/audit.md', 'tools/vendor/vendor.py',
                             'assets/imported_mods/source.md', 'docs/generated.md', 'export/generated.hx'):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(chr(0x2014), encoding="utf-8")
            self.assertCountEqual(list(TEXT_POLICY.punctuation_violations(root)),
                                  ['README.md:1', 'source/Engine.hx:1', 'tools/reports/audit.md:1'])


if __name__ == '__main__':
    unittest.main()
