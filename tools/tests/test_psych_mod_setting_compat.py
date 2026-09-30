from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
TJSON = ROOT / ".haxelib/tjson/1,4,0"


class PsychModSettingCompatTest(unittest.TestCase):
    def test_playstate_binds_settings_to_the_current_lua_script_and_psych_owner(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        seed = play[play.index("function seedEngineCompat("):play.index(
            "function getCompatScriptManifest(", play.index("function seedEngineCompat(")
        )]
        self.assertIn("PsychModSettingCompat.create(origin", seed)
        self.assertIn("psychScriptOwner, function(message:String)", seed)
        self.assertIn("__compatDiagnosticSource", seed)
        self.assertIn("ownerForScript(origin, extraPsychOwnerRoot)", seed)
        self.assertIn("seedEngineCompat(interp, extraPsychOwnerRoot);", play)
        self.assertIn("?extraPsychOwnerRoot:String", play)
        owner_resolver = play[play.index("function compatPsychOwnerForScript("):play.index(
            "function preparePsychNoteDefinitions(", play.index("function compatPsychOwnerForScript(")
        )]
        self.assertIn("entry.engine == ImportEngine.PSYCH", owner_resolver)
        self.assertIn("PsychModSettingCompat.ownerForScriptRoots(scriptOrigin, candidates)", owner_resolver)

    def test_settings_defaults_are_owner_scoped_and_tolerant_parse_is_diagnosed(self):
        fixture = r'''
import sys.FileSystem;
import sys.io.File;

class PsychModSettingCompatTest {
 static function fail(message:String):Void throw message;
 static function main() {
  var owner = "OWNER_ROOT";
  var globalOwner = "GLOBAL_ROOT";
  FileSystem.createDirectory(owner);
  FileSystem.createDirectory(owner + '/scripts');
  FileSystem.createDirectory(owner + '/data');
  File.saveContent(owner + '/scripts/results.lua', '-- fixture');
  FileSystem.createDirectory(globalOwner);
  FileSystem.createDirectory(globalOwner + '/scripts');
  File.saveContent(globalOwner + '/scripts/results.lua', '-- global fixture');
  File.saveContent(owner + '/pack.json', '{"name":"Fixture Pack"}');
  // TJSON can recover this donor-style omitted comma; strict JSON rejects it.
  File.saveContent(owner + '/data/settings.json',
   '[{"save":"choice","value":"Default" "options":["Default"]},'
   + '{"save":"enabled","value":true},{"save":"amount","value":17}]');
  var messages:Array<String> = [];
  var provider:Dynamic = PsychModSettingCompat.create(owner + '/scripts/results.lua', owner,
   function(message:String) messages.push(message));
  if (Reflect.callMethod(null, provider, ['choice', 'Fixture Pack']) != 'Default')
   fail('string default should be returned');
  if (Reflect.callMethod(null, provider, ['enabled']) != true
   || Reflect.callMethod(null, provider, ['amount', 'Fixture Pack']) != 17)
   fail('boolean and numeric defaults should preserve type');
  if (Reflect.callMethod(null, provider, ['choice', 'Another Pack']) != null)
   fail('a caller cannot query another package name');
  if (messages.length != 1 || messages[0].indexOf('malformed') < 0)
   fail('tolerant parse must produce one malformed JSON diagnostic: ' + messages);
  FileSystem.deleteFile(owner + '/pack.json');
  var olderImportedRoot:Dynamic = PsychModSettingCompat.create(owner + '/scripts/results.lua', owner);
  if (Reflect.callMethod(null, olderImportedRoot, ['choice', 'Fixture Pack']) != 'Default')
   fail('legacy imported roots without pack.json remain scoped to their script owner');
  var foreign = PsychModSettingCompat.create('assets/imported_mods/other/scripts/script.lua', owner);
  if (Reflect.callMethod(null, foreign, ['choice', 'Fixture Pack']) != null)
   fail('script outside selected owner must not read settings');
  var traversal = PsychModSettingCompat.create(owner + '/../other/script.lua', owner);
  if (Reflect.callMethod(null, traversal, ['choice', 'Fixture Pack']) != null)
   fail('traversal origin must not read settings');
  var resolvedGlobal = PsychModSettingCompat.ownerForScriptRoots(
   globalOwner + '/scripts/results.lua', [owner, globalOwner]);
  if (resolvedGlobal != globalOwner)
   fail('a globally loaded Psych script must resolve its own root, not the song root');
  var absoluteGlobal = FileSystem.fullPath(globalOwner + '/scripts/results.lua');
  if (PsychModSettingCompat.ownerForScript(absoluteGlobal, globalOwner) != globalOwner)
   fail('absolute installed script path must retain its validated owner');
  if (PsychModSettingCompat.ownerForScript(absoluteGlobal, owner) != null)
   fail('absolute script path cannot claim a sibling owner');
  var unresolvedGlobal = PsychModSettingCompat.ownerForScriptRoots(
   'assets/imported_mods/unlisted/scripts/results.lua', [owner, globalOwner]);
  if (unresolvedGlobal != null)
   fail('unlisted scripts cannot claim an imported owner');
  Sys.println('ok');
 }
}
'''
        imported_root = ROOT / "assets/imported_mods"
        imported_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="psych-settings-test-", dir=imported_root) as owner_path:
            owner_dir = Path(owner_path)
            owner = (owner_dir / "song-owner").relative_to(ROOT).as_posix()
            global_owner = (owner_dir / "global-owner").relative_to(ROOT).as_posix()
            with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
                (Path(folder) / "PsychModSettingCompatTest.hx").write_text(
                    fixture.replace("OWNER_ROOT", owner).replace("GLOBAL_ROOT", global_owner))
                result = subprocess.run(
                    [str(HAXE), "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(TJSON),
                     "-main", "PsychModSettingCompatTest", "--interp"],
                    cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
