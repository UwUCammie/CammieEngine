"""Configured global sound shortcuts must not enter menu search."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

class MenuSearchShortcutsTest(unittest.TestCase):
    def test_configured_shortcuts_and_modifiers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "flixel/input/keyboard").mkdir(parents=True)
            (root / "flixel/input/keyboard/FlxKey.hx").write_text("package flixel.input.keyboard; typedef FlxKey = Int;")
            (root / "flixel/FlxG.hx").write_text("package flixel; class FlxG { public static var keys = {pressed:{CONTROL:false, ALT:false}}; public static var sound = {muteKeys:[48], volumeUpKeys:[187], volumeDownKeys:[189]}; }")
            (root / "MenuSearchInput.hx").write_text((ROOT / "source/MenuSearchInput.hx").read_text())
            (root / "Main.hx").write_text("""
class Main {
 static function check(value:Bool):Void if (!value) throw 'shortcut ownership';
 static function main() {
  check(MenuSearchInput.reserved(48));
  check(MenuSearchInput.reserved(187)); check(MenuSearchInput.reserved(189));
  check(!MenuSearchInput.reserved(65)); check(!MenuSearchInput.reserved(57));
  flixel.FlxG.sound.muteKeys=[77,96];
  check(MenuSearchInput.reserved(77)); check(MenuSearchInput.reserved(96));
  check(!MenuSearchInput.reserved(48));
  flixel.FlxG.sound.volumeUpKeys=null; flixel.FlxG.sound.volumeDownKeys=[];
  check(!MenuSearchInput.reserved(189));
  flixel.FlxG.keys.pressed.CONTROL=true; check(MenuSearchInput.reserved(65));
  flixel.FlxG.keys.pressed.CONTROL=false; flixel.FlxG.keys.pressed.ALT=true;
  check(MenuSearchInput.reserved(8));
 }
}
""")
            result=subprocess.run([*HAXE_COMMAND, '-cp', str(root), '-main', 'Main', '--interp'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ('CategoryState',):
            source=(ROOT / ('source/'+name+'.hx')).read_text()
            self.assertIn('MenuSearchInput.reserved(searchKey) ? -1 : searchKey', source)
            self.assertIn('!MenuSearchInput.reserved(FlxKey.BACKSPACE)', source)

    def test_freeplay_uses_native_focused_text_input(self):
        source=(ROOT/'source/FreeplayState.hx').read_text()
        self.assertIn('var searchFocused:Bool = false',source)
        self.assertIn('FlxG.keys.justReleased.CONTROL && !searchControlUsed',source)
        self.assertIn('searchInput.startFocus()',source)
        self.assertIn('searchInput.endFocus()',source)
        self.assertIn('searchInput.onTextChange.add',source)
        self.assertIn('if (searchFocused || focusChanged)',source)
        self.assertNotIn('String.fromCharCode(key -',source)
