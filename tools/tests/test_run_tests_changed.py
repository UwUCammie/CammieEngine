"""Everyday runs pick only the test modules that cover what changed."""
from pathlib import Path
import tempfile, unittest
from haxe_test_support import TEST_TMP
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import run_tests


class ChangedSelectionTest(unittest.TestCase):
    def test_changed_files_select_the_modules_that_name_them(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            folder = Path(temp)
            texts = {
                'test_star.py': "source = read('source/FreeplayStarTrail.hx')",
                'test_menu.py': "LibraryMenuLayout.rowsTop(true)",
                'test_build.py': "self.assertIn('patch_flixel_finish_guard.py', run_bat)\nopen('run.bat')",
                'test_other.py': "nothing relevant here",
                'test_edited.py': "also nothing relevant",
            }
            modules = []
            for name, text in sorted(texts.items()):
                (folder / name).write_text(text, encoding='utf-8'); modules.append(folder / name)
            def picked(*paths): return [m.name for m in run_tests.modules_for_changes(list(paths), modules)]
            self.assertEqual(picked('source/FreeplayStarTrail.hx'), ['test_star.py'])
            self.assertEqual(picked('source/LibraryMenuLayout.hx', 'source/FreeplayStarTrail.hx'), ['test_menu.py', 'test_star.py'])
            self.assertEqual(picked('tools/patch_flixel_finish_guard.py'), ['test_build.py'])
            self.assertEqual(picked('run.bat'), ['test_build.py'])
            # A changed test module runs even when nothing else names it.
            self.assertEqual(picked('tools/tests/test_edited.py'), ['test_edited.py'])
            self.assertEqual(picked('source/Unmentioned.hx'), [])
            self.assertEqual(picked(), [])

    def test_runner_offers_the_option_and_keeps_the_full_run_as_default(self):
        source = (ROOT / 'tools/run_tests.py').read_text(encoding='utf-8')
        self.assertIn('"--changed", action="store_true"', source)
        self.assertIn('if args.changed:', source)


if __name__ == '__main__':
    unittest.main()
