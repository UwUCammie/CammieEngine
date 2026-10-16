"""The song importer lives on the main menu as an Import entry under Options."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class MainMenuImportEntryTest(unittest.TestCase):
    def compile(self, code):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'Main.hx').write_text(code, encoding='utf-8')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work), '-main', 'Main', '--interp'],
                cwd=work, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_layout_keeps_every_row_reachable_in_the_freeplay_list(self):
        self.compile(r"""class Main {
 static function ok(v:Bool, m:String):Void if (!v) throw m;
 static function main() {
  // The default menu (story mode, freeplay, options, import) and the donate and
  // costume rows on top of it must all be drawn wherever the selection is.
  ok(MainMenuLayout.capacity(720) >= 6, 'six rows must fit at 720');
  for (count in [4, 5, 6]) for (selected in 0...count) {
   for (i in 0...count) ok(MainMenuLayout.shown(i, selected, count, 720), 'row ' + i + ' of ' + count + ' is hidden');
   for (i in 1...count) ok(MainMenuLayout.rowTop(i, selected, count, 720) > MainMenuLayout.rowTop(i - 1, selected, count, 720), 'rows ordered');
  }
  // A longer menu scrolls to keep the chosen row on screen.
  for (selected in 0...9) ok(MainMenuLayout.shown(selected, selected, 9, 720), 'the chosen row of nine is hidden');
 }
}""")

    def test_main_menu_lists_import_under_options_and_opens_the_importer(self):
        menu = (ROOT / 'source/MainMenuState.hx').read_text(encoding='utf-8')
        declaration = re.search(r"var optionShit:Array<String> = \['story mode', 'freeplay', 'donate', 'options'#if sys, 'import'#end\];", menu)
        self.assertIsNotNone(declaration, 'import must directly follow options')
        self.assertIn("case 'import':", menu)
        self.assertIn('LoadingState.loadAndSwitchState(new ImportSettingsState());', menu)
        # Same card as every other row: selected card, flicker confirm.
        self.assertIn('new MenuCard(rowLabel(optionShit[i])', menu)
        self.assertIn("case 'import': 'Import';", menu)
        # The imported costume button is re-laid out with the shared layout helper.
        costume = menu[menu.index('public function hxcAddCostumeMenuItem'):]
        self.assertIn('layoutMenuItems(true);', costume[:costume.index('function changeItem')])
        self.assertNotIn('100 + (menuItems.length * 160)', menu)

    def test_import_is_no_longer_an_options_entry_and_returns_to_the_main_menu(self):
        options = (ROOT / 'source/SaveDataState.hx').read_text(encoding='utf-8')
        self.assertNotIn('Import Settings...', options)
        self.assertNotIn('importSettings', options)
        self.assertNotIn('ImportSettingsState', options)
        screen = (ROOT / 'source/ImportSettingsState.hx').read_text(encoding='utf-8')
        self.assertNotIn('new SaveDataState()', screen)
        self.assertEqual(screen.count('new MainMenuState()'), 2)

    def test_native_probe_covers_open_and_return_with_import_selected(self):
        probe = (ROOT / 'source/RuntimeMainMenuImportProbe.hx').read_text(encoding='utf-8')
        self.assertIn("simulateKey('escape')", probe)
        self.assertIn('MainMenuState.curSelected == importIndex', probe)
        self.assertIn("capturePending = 'returned'", probe)
        harness = (ROOT / 'source/RuntimeSmokeHarness.hx').read_text(encoding='utf-8')
        self.assertIn('RuntimeMainMenuImportProbe.enabled()', harness)

    def test_imported_menu_specs_keep_their_own_route_vocabulary(self):
        spec = (ROOT / 'source/HxcMenuSpec.hx').read_text(encoding='utf-8')
        self.assertNotIn("'import'", spec)
        menu = (ROOT / 'source/MainMenuState.hx').read_text(encoding='utf-8')
        # An imported spec replaces the native rows wholesale (menuItems hidden),
        # so the native Import row never merges into or breaks it.
        self.assertIn('menuItems.visible = false;', menu)
        self.assertIn('menuItems.visible = hxcOverlayMenuVisible;', menu)


if __name__ == '__main__':
    unittest.main()
