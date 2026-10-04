"""Owner-local source-compatible Nightmare Vision Mods and Difficulty APIs."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"
DONOR = ROOT.parent / "fnf_sources/NightmareVision/source/funkin"


class NightmareVisionSourceApiContextsTest(unittest.TestCase):
    def run_haxe(self, body, fixture_files=None):
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
            write_flixel_point_stub(work)
            for relative, content in (fixture_files or {}).items():
                path = work / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_discord_presence_keeps_source_argument_order_and_defaults(self):
        self.run_haxe(r'''
var calls:Array<Array<Dynamic>> = [];
var client = new NightmareVisionDiscordClient(function(details, state, small, timestamp, end, large)
  calls.push([details, state, small, timestamp, end, large]));
var interp = new NightmareVisionScriptInterp();
interp.variables.set('DiscordClient', client);
interp.bindImport('funkin.api.DiscordClient', client);
interp.execute(new Parser().parseString(
  'import funkin.api.DiscordClient;\n'
  + 'DiscordClient.changePresence("Playing", "Composer", "small", true, 1234, "cover");\n'
  + 'DiscordClient.changePresence();\n'
  + 'if (DiscordClient.username != "Unknown") throw "fabricated Discord identity";'));
eq(calls.length, 2, 'presence callback count');
eq(calls[0][0], 'Playing', 'details');
eq(calls[0][1], 'Composer', 'state');
eq(calls[0][2], 'small', 'small image key');
eq(calls[0][3], true, 'timestamp switch');
eq(calls[0][4], 1234, 'end timestamp');
eq(calls[0][5], 'cover', 'large image key');
eq(calls[1][0], 'In the Menus', 'default details');
eq(calls[1][5], 'icon', 'default large image key');
''')

    def test_chart_api_loads_owned_source_charts_without_changing_source_file(self):
        self.run_haxe(r'''
var owner = 'assets/imported_mods/selected';
var json = '{"song":{"player3":"gf","notes":[{"mustHitSection":false,"sectionNotes":[[100,0,0], [200,-1,"Camera", "x", "y"]]}]}}';
var readCount = 0;
var chart = new NightmareVisionChartApi(function(path:String):String {
  if (path != owner + '/songs/tutorial/data/gf.json') return null;
  readCount++;
  return json;
}, function(song:String, difficulty:Int):String
  return owner + '/songs/' + song + '/charts/' + (difficulty == 2 ? 'hard' : 'normal') + '.json');
var interp = new NightmareVisionScriptInterp();
interp.bindImport('funkin.data.Chart', chart);
interp.variables.set('Paths', {json:function(name:String):String return owner + '/songs/' + name + '.json'});
interp.execute(new Parser().parseString(
  'import funkin.data.Chart;\n'
  + 'var crowd = Chart.fromPath(Paths.json("tutorial/data/gf"));\n'
  + 'if (crowd.gfVersion != "gf") throw "GF conversion missing";\n'
  + 'if (crowd.notes[0].sectionNotes[0][1] != 4) throw "legacy lane swap missing";'));
eq(readCount, 1, 'owned chart read');
var loaded = chart.fromPath(owner + '/songs/tutorial/data/gf.json');
eq(loaded.events.length, 1, 'legacy event extraction');
eq(loaded.notes[0].sectionNotes.length, 1, 'event removed from note rows');
eq(loaded.notes[0].sectionBeats, 4, 'default section beats');
eq(loaded.arrowSkins.length, 2, 'source arrow skins');
eq(json.indexOf('"player3"') >= 0, true, 'source text was not changed');
var rejected = false;
try chart.fromPath('assets/imported_mods/other/songs/tutorial/data/gf.json') catch (error:Dynamic)
  rejected = Std.string(error).indexOf('couldnt find chart') >= 0;
check(rejected, 'another owner chart was accepted');
''')

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
  unsupported = Std.string(error).indexOf('[nightmare-vision-mods-scope]') >= 0;
check(unsupported, 'another owner mod list was accepted');
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

    def test_mods_method_surface_matches_donor_and_methods_are_implemented(self):
        if not (DONOR / "Mods.hx").is_file():
            self.skipTest("supplied Nightmare Vision Mods source unavailable")
        donor = (DONOR / "Mods.hx").read_text(encoding="utf-8")
        declared = set(re.findall(r"public static (?:inline )?function\s+(\w+)\s*\(", donor))
        adapter = (ROOT / "source/NightmareVisionModsContext.hx").read_text(encoding="utf-8")
        source_surface = re.search(r"sourceApiMethods\(\).*?return \[(.*?)\];", adapter, re.S)
        unsupported_surface = re.search(r"unsupportedSourceApiMethods\(\).*?return \[\];", adapter, re.S)
        self.assertIsNotNone(source_surface)
        self.assertIsNotNone(unsupported_surface)
        exposed = set(re.findall(r"'([A-Za-z_]\w*)'", source_surface.group(1)))
        self.assertEqual(exposed, declared, "adapter inventory does not match source Mods methods")

        self.assertIn("public function getModDirectories()", adapter)
        self.assertNotIn("return cast unsupported(", adapter)
        self.assertNotIn("return unsupported(", adapter)

    def test_mods_files_and_pack_apis_are_owner_scoped(self):
        self.run_haxe(r'''
var mods = new NightmareVisionModsContext('assets/imported_mods/owner-a', 'owner-a');
eq(mods.getModDirectories().join(','), 'owner-a', 'selected owner directory');
eq(mods.pushGlobalMods().join(','), 'owner-a', 'selected owner global flag');
eq(mods.getPack().name, 'Owner Display', 'owner metadata read');
eq(mods.getPack('other-owner'), null, 'foreign pack metadata read');
eq(mods.getModName(''), 'Owner Display', 'meta display name');
eq(mods.getModIcon(''), 'icons/icon', 'meta icon key');
check(mods.getModFont('').indexOf('assets/imported_mods/owner-a/fonts/owner-font.ttf') >= 0,
  'owner font path resolution');
var matches = mods.directoriesWithFile('assets/data', 'values.txt');
eq(matches.length, 2, 'core/owner text matches (' + matches.join(',') + ')');
check(matches[0].indexOf('__nmv_core/data/values.txt') >= 0, 'core precedence');
check(matches[1].indexOf('owner-a/values.txt') >= 0, 'owner match');
eq(mods.mergeAllTextsNamed('values.txt', 'assets/data').join(','), 'core,same,owner',
  'core-first text merge with duplicate removal');
var withDuplicates = mods.mergeAllTextsNamed('values.txt', 'assets/data', true);
eq(withDuplicates.join(','), 'core,same,owner,same', 'duplicate-preserving merge');
var parsed = mods.parseList();
eq(parsed.enabled.join(','), 'owner-a', 'owner-local list enabled');
eq(mods.getListAsArray()[0].folder, 'owner-a', 'owner-local list row');
mods.applyModConfig();
eq(mods.currentModConfig.name, 'Owner Display', 'owner config applied locally');
mods.loadTopMod();
''', {
            'assets/imported_mods/owner-a/meta.json': '{"name":"Owner Display","global":true,"iconFile":"icons/icon","defaultFont":"owner-font"}',
            'assets/imported_mods/owner-a/fonts/owner-font.ttf': 'font',
            'assets/imported_mods/owner-a/values.txt': 'owner\nsame\n',
            'assets/imported_mods/owner-a/__nmv_core/data/values.txt': 'core\nsame\n',
        })


if __name__ == "__main__":
    unittest.main()
