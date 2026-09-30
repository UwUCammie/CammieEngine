"""Owner-local source-compatible Nightmare Vision Mods and Difficulty APIs."""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"
DONOR = ROOT.parent / "FNF-Example-Mods/misc/nightmare_vision_source_code/source/funkin"


class NightmareVisionSourceApiContextsTest(unittest.TestCase):
    def run_haxe(self, body):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''
import crowplexus.hscript.Parser;

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected ' + Std.string(expected) + ', got ' + Std.string(actual));
 static function main() {
''' + body + r'''
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mods_context_import_is_owner_local_and_rejects_switching(self):
        self.run_haxe(r'''
var first = new NightmareVisionModsContext('assets/imported_mods/owner-a', 'new-dsides');
var second = new NightmareVisionModsContext('assets/imported_mods/owner-b', 'other-mod');
var interp = new NightmareVisionScriptInterp();
interp.bindImport('funkin.Mods', first);
interp.execute(new Parser().parseString(
  'import funkin.Mods;\n'
  + 'if (Mods.currentModDirectory != "new-dsides") throw "wrong initial source directory";\n'
  + 'Mods.currentModDirectory = "new-dsides";\n'
  + 'Mods.globalMods.push("owner-local-global");\n'
  + 'Mods.ignoreModFolders.push("owner-local-ignore");'));
eq(first.currentModDirectory, 'new-dsides', 'same owner directory assignment changed the mounted owner');
eq(second.currentModDirectory, 'other-mod', 'directory selection leaked to another owner');
eq(second.globalMods.length, 0, 'global mod array leaked between owners');
eq(second.ignoreModFolders.indexOf('owner-local-ignore'), -1, 'ignore folder array leaked between owners');
check(first.canReuseFor('assets\\imported_mods\\owner-a'), 'same normalized owner was not reusable');
check(!first.canReuseFor(second.ownerRoot), 'context accepted a different owner');
var switched = false;
try first.currentModDirectory = 'old-dsides' catch (error:Dynamic)
  switched = Std.string(error).indexOf('[nightmare-vision-mods-unsupported] funkin.Mods.currentModDirectory') >= 0;
check(switched, 'directory setter pretended to switch while the owner paths stayed mounted');
eq(first.currentModDirectory, 'new-dsides', 'failed selection changed the visible mounted owner');
var unsupported = false;
try first.updateModList('owner-b') catch (error:Dynamic)
  unsupported = Std.string(error).indexOf('[nightmare-vision-mods-unsupported] funkin.Mods.updateModList') >= 0;
check(unsupported, 'global Mods mutation silently succeeded');
''')

    def test_source_directory_comes_from_retained_provenance(self):
        self.run_haxe(r'''
var diagnostics:Array<String> = [];
var current = NightmareVisionModsContext.sourceDirectoryFromProvenance({
  sourceModDirectory:'new-dsides', nameSource:'metadata', modName:'D-Sides Redux'
}, function(message:String):Void diagnostics.push(message));
eq(current, 'new-dsides', 'retained source mod directory was ignored');
var legacy = NightmareVisionModsContext.sourceDirectoryFromProvenance({
  nameSource:'inferred', modName:'legacy-source-pack'
}, function(message:String):Void diagnostics.push(message));
eq(legacy, 'legacy-source-pack', 'inferred legacy directory was not recovered');
var missing = NightmareVisionModsContext.sourceDirectoryFromProvenance({
  nameSource:'metadata', modName:'A Display Name'
}, function(message:String):Void diagnostics.push(message));
eq(missing, null, 'display name was mistaken for a source folder');
check(diagnostics.length == 1 && diagnostics[0].indexOf('refresh the import') >= 0,
  'missing retained directory was not diagnosed');
var context = new NightmareVisionModsContext('assets/imported_mods/missing-owner', missing);
var accessFailed = false;
try context.currentModDirectory catch (error:Dynamic)
  accessFailed = Std.string(error).indexOf('[nightmare-vision-mods-context-missing]') >= 0;
check(accessFailed, 'missing owner metadata silently exposed an empty directory');
''')

    def test_difficulty_adapter_matches_source_selection_and_isolates_owners(self):
        self.run_haxe(r'''
var diagnostics:Array<String> = [];
var first = new NightmareVisionDifficultyAdapter('assets/imported_mods/owner-a',
  ['Easy', 'Normal', 'Hard', 'Encore'], 3, function(message:String):Void diagnostics.push(message));
var second = new NightmareVisionDifficultyAdapter('assets/imported_mods/owner-b');
var interp = new NightmareVisionScriptInterp();
interp.bindImport('funkin.backend.Difficulty', first);
interp.execute(new Parser().parseString(
  'import funkin.backend.Difficulty;\n'
  + 'if (Difficulty.getCurrentDifficultyString() != "Encore") throw "current chart difficulty was lost";\n'
  + 'Difficulty.difficulties[3] = "Extra Hard!";\n'
  + 'if (Difficulty.getDifficultyFilePath() != "extra-hard!") throw "source punctuation was not preserved";\n'
  + 'Difficulty.defaultDifficulty = "Fallback";'));
eq(first.getCurrentDifficultyString(), 'Extra Hard!', 'script difficulty list write was not reflected');
eq(first.getDifficultyFilePath(), 'extra-hard!', 'current file path suffix');
eq(first.defaultDifficulty, 'Fallback', 'source defaultDifficulty was not mutable');
eq(second.getCurrentDifficultyString(), 'Normal', 'default source selection');
eq(second.defaultDifficulty, 'Normal', 'default value leaked between owners');
eq(second.difficulties[3], null, 'source difficulty list leaked between owners');
first.selectDifficulty(80);
eq(first.getCurrentDifficultyString(), 'Fallback', 'invalid current index did not use source fallback');
eq(first.getDifficultyFilePath(), 'fallback', 'invalid file index did not use sanitized source fallback');
check(diagnostics.length == 1 && diagnostics[0].indexOf('difficulty index 80') >= 0,
  'invalid file index was not diagnosed');
first.reset();
eq(first.difficulties.join(','), 'Easy,Normal,Hard', 'reset did not restore source defaults');
eq(second.difficulties.join(','), 'Easy,Normal,Hard', 'reset crossed owner contexts');
check(!first.canReuseFor(second.ownerRoot), 'difficulty adapter accepted another owner');
''')

    def test_mods_method_surface_matches_donor_and_unsupported_calls_are_explicit(self):
        if not (DONOR / "Mods.hx").is_file():
            self.skipTest("supplied Nightmare Vision Mods source unavailable")
        donor = (DONOR / "Mods.hx").read_text(encoding="utf-8")
        declared = set(re.findall(r"public static (?:inline )?function\s+(\w+)\s*\(", donor))
        adapter = (ROOT / "source/NightmareVisionModsContext.hx").read_text(encoding="utf-8")
        source_surface = re.search(r"sourceApiMethods\(\).*?return \[(.*?)\];", adapter, re.S)
        unsupported_surface = re.search(r"unsupportedSourceApiMethods\(\).*?return sourceApiMethods\(\)\.copy\(\);", adapter, re.S)
        self.assertIsNotNone(source_surface)
        self.assertIsNotNone(unsupported_surface)
        exposed = set(re.findall(r"'([A-Za-z_]\w*)'", source_surface.group(1)))
        self.assertEqual(exposed, declared, "adapter inventory does not match source Mods methods")

        self.run_haxe(r'''
var mods = new NightmareVisionModsContext('assets/imported_mods/owner');
var failures = 0;
for (name in NightmareVisionModsContext.unsupportedSourceApiMethods()) {
  var method = Reflect.field(mods, name);
  check(method != null && Reflect.isFunction(method), 'missing source method ' + name);
  try Reflect.callMethod(mods, method, []) catch (error:Dynamic) {
    if (Std.string(error).indexOf('[nightmare-vision-mods-unsupported] funkin.Mods.' + name) >= 0)
      failures++;
    else throw error;
  }
}
eq(failures, NightmareVisionModsContext.sourceApiMethods().length,
  'unsupported Mods calls were swallowed or lacked a diagnostic');
''')


if __name__ == "__main__":
    unittest.main()
