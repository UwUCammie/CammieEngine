"""Every name the source script preset hands out is seeded here too, or listed as not ported yet."""
import re
import subprocess
import tempfile
import unittest

from base_helper_fixtures import extract_block
from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT.parent / 'fnf_sources/NightmareVision/source/funkin/scripts/FunkinScript.hx'

# Names with no engine equivalent yet. They stay unknown identifiers so a
# script fails where it uses them instead of meeting a wrong stand-in. When one
# gets ported, take it off this list.
KNOWN_MISSING = {
    'Dynamic',  # a type, not a value hxcpp can hand to a script
    'Defines',
    'FlxRuntimeShader',
    'FlxAnimateFrames',
    'FlxSpriteElement',
    'StageData',
    'FunkinSound',
    'Note',  # the engine note has different fields; a wrong alias is worse than none
    'StrumNote',
    'BackgroundDancer',
    'BackgroundGirls',
    'CutsceneHandler',
    'DialogueBox',
}

SORT_MAIN = r'''class Main {
 static function check(v:Bool, s:String):Void if (!v) throw s;
 static function main():Void {
  var low={zIndex:1, strumTime:300.0}; var high={zIndex:5, strumTime:100.0};
  var up=flixel.util.FlxSort.ASCENDING;
  check(NightmareVisionSortUtil.sortByZ(up, low, high) < 0, 'lower zIndex sorts first ascending');
  check(NightmareVisionSortUtil.sortByZ(-up, low, high) > 0, 'order flips the z comparison');
  check(NightmareVisionSortUtil.sortByZ(up, null, high) == 0, 'null members compare equal');
  check(NightmareVisionSortUtil.sortByStrumTime(low, high) > 0, 'strum time sorts ascending');
  check(NightmareVisionSortUtil.laserSort(2, 1) > 0, 'laserSort compares floats ascending');
  var items:Array<Dynamic>=[high, low];
  items.sort(function(a, b) return NightmareVisionSortUtil.sortByZ(up, a, b));
  check(items[0] == low, 'sortByZ works as an Array.sort comparator');
 }
}
'''


def reference_preset_names(text):
    body = text[text.index('function preset('):]
    return list(dict.fromkeys(re.findall(r"""\bset\(\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]""", body)))


class NightmareVisionPresetParityTest(unittest.TestCase):
    def test_reference_preset_names_are_seeded_or_known_missing(self):
        if not REFERENCE.exists():
            self.skipTest('reference sources are not checked out next to the repo')
        names = reference_preset_names(REFERENCE.read_text(encoding='utf-8'))
        self.assertGreater(len(names), 50)
        source = ROOT / 'source'
        play = (source / 'PlayState.hx').read_text(encoding='utf-8')
        blob = '\n'.join(
            [path.read_text(encoding='utf-8') for path in sorted(source.glob('NightmareVision*.hx'))]
            + [(source / 'ScriptNativeClasses.hx').read_text(encoding='utf-8'),
               extract_block(play, 'public static function seedNightmareVisionCommon('),
               extract_block(play, 'function seedNightmareVision(interp:'),
               # Gameplay HUD classes are bound by their own helpers in PlayState.
               extract_block(play, 'function bindSourceBarClass('),
               extract_block(play, 'function bindSourceHealthIconClass(')])
        missing = [name for name in names
                   if name not in KNOWN_MISSING and not re.search(r"""['"]%s['"]""" % re.escape(name), blob)]
        self.assertEqual(missing, [], 'source preset names with no binding and no known-missing entry')
        stale = sorted(name for name in KNOWN_MISSING
                       if name in names and re.search(r"""variables\.set\(\s*'%s'|entry\('%s'""" % (name, name), blob))
        self.assertEqual(stale, [], 'known-missing names that are now bound should leave the list')

    def test_new_preset_classes_are_bound(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        preset = extract_block(play, 'public static function seedNightmareVisionCommon(')
        self.assertIn("interp.variables.set('SortUtil', NightmareVisionSortUtil);", preset)
        self.assertIn("interp.bindImport('funkin.utils.SortUtil', NightmareVisionSortUtil);", preset)
        self.assertIn('NightmareVisionVideoSprite.instancesFor(videoOwner)', preset)

    def test_sort_util_comparators(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            (work / 'flixel/util').mkdir(parents=True)
            (work / 'flixel/util/FlxSort.hx').write_text('''package flixel.util;
class FlxSort {
 public static inline var ASCENDING:Int=-1;
 public static function byValues(order:Int, a:Float, b:Float):Int return a < b ? order : a > b ? -order : 0;
}''', encoding='utf-8')
            (work / 'HxcCompatRuntime.hx').write_text('''class HxcCompatRuntime {
 public static function getZIndex(target:Dynamic):Dynamic return Reflect.field(target, 'zIndex');
}''', encoding='utf-8')
            (work / 'NightmareVisionSortUtil.hx').write_text(
                (ROOT / 'source/NightmareVisionSortUtil.hx').read_text(encoding='utf-8'), encoding='utf-8')
            (work / 'Main.hx').write_text(SORT_MAIN, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '--main', 'Main', '--interp'],
                                    cwd=work, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
