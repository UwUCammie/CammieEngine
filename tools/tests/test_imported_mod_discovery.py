"""Imported Mods groups owners by package and follows owner-local menu routes."""
from haxe_test_support import HAXE_COMMAND
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class ImportedModDiscoveryTest(unittest.TestCase):
    def test_package_projection_entrypoint_and_owner_scoped_state_resolution(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owners = {
                "dsides": base / "assets/imported_mods/dsides",
                "ambiguous": base / "assets/imported_mods/ambiguous",
                "psych": base / "assets/imported_mods/psych",
            }
            for root in owners.values():
                root.mkdir(parents=True)
            dsides_states = {
                "data/states/Dsides/TitleState.hx": "FlxG.switchState(new MainMenuState());",
                "data/states/Dsides/MainMenuState.hx": "FlxG.switchState(new FreeplayState());",
                "data/states/Dsides/FreeplayState.hx": "function create() {}",
            }
            for relative, content in dsides_states.items():
                path = owners["dsides"] / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')
            ambiguous_states = {
                "data/states/Entry/TitleState.hx": "FlxG.switchState(new MainMenuState());",
                "data/states/One/MainMenuState.hx": "function create() {}",
                "data/states/Two/MainMenuState.hx": "function create() {}",
            }
            for relative, content in ambiguous_states.items():
                path = owners["ambiguous"] / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')

            def receipt(folder, owner, engine, title, name_source):
                song_folder = base / "assets/data" / folder
                song_folder.mkdir(parents=True)
                (song_folder / "importProvenance.json").write_text(json.dumps({
                    "version": 1,
                    "sourceEngine": engine,
                    "sourceOwner": f"assets/imported_mods/{owner}",
                    "destinationFolder": folder,
                    "sourceFolder": folder,
                    "modName": title,
                    "nameSource": name_source,
                }), newline='\n')

            receipt("song-a", "dsides", "Codename Engine", "D-Sides", "metadata")
            receipt("song-b", "dsides", "Codename Engine", "Outer Archive Name", "inferred")
            receipt("song-c", "psych", "Psych Engine", "D-Sides", "user")
            receipt("song-d", "ambiguous", "Codename Engine", "Ambiguous Pack", "metadata")
            catalog = {"version": 1, "entries": [
                {"root": "assets/imported_mods/dsides", "label": "Outer · Codename Engine",
                 "states": list(dsides_states)},
                {"root": "assets/imported_mods/ambiguous", "label": "Ambiguous Pack · Codename Engine",
                 "states": list(ambiguous_states)},
            ]}
            (base / "catalog.json").write_text(json.dumps(catalog), newline='\n')
            (base / "Main.hx").write_text(r'''
class Main {
 static function main():Void {
  var result = ImportedModDiscovery.discover("assets/data", sys.io.File.getContent("catalog.json"));
  if (!result.valid || result.packages.length != 3) throw "package projection lost an owner";
  var dsides = null;
  var psych = null;
  var ambiguous = null;
  for (entry in result.packages) {
   if (entry.root == "assets/imported_mods/dsides") dsides = entry;
   if (entry.root == "assets/imported_mods/psych") psych = entry;
   if (entry.root == "assets/imported_mods/ambiguous") ambiguous = entry;
  }
  if (dsides == null || dsides.title != "D-Sides" || dsides.engine != "Codename Engine"
      || dsides.songCount != 2 || dsides.launchState != "data/states/Dsides/TitleState.hx")
   throw "authored title route or provenance title was not selected";
  if (psych == null || psych.title != "D-Sides" || psych.engine != "Psych Engine"
      || psych.launchState != "" || psych.songCount != 1)
   throw "non-Codename owner did not retain a native Freeplay fallback";
  if (ambiguous == null || ambiguous.launchState != "")
   throw "ambiguous authored transition was exposed as a launch route";

  var paths = ["data/states/Dsides/TitleState.hx",
   "data/states/Dsides/MainMenuState.hx", "data/states/Other/MainMenuState.hx"];
  var sibling = CodenameModStateResolver.resolve(paths, "MainMenuState",
   "data/states/Dsides/TitleState.hx");
  if (sibling.path != "data/states/Dsides/MainMenuState.hx" || sibling.ambiguous)
   throw "same-folder owner state was not preferred";
  var explicit = CodenameModStateResolver.resolve(paths,
   "data/states/Other/MainMenuState.hx", "data/states/Dsides/TitleState.hx");
  if (explicit.path != "data/states/Other/MainMenuState.hx" || explicit.ambiguous)
   throw "explicit owner-relative state path was not honored";
  var qualified = CodenameModStateResolver.resolve(paths, "Other.MainMenuState",
   "data/states/Dsides/TitleState.hx");
  if (qualified.path != "data/states/Other/MainMenuState.hx" || qualified.ambiguous)
   throw "qualified owner namespace was not honored";
  var missingNamespace = CodenameModStateResolver.resolve(paths, "Missing.MainMenuState",
   "data/states/Dsides/TitleState.hx");
  if (missingNamespace.path != "" || missingNamespace.ambiguous)
   throw "missing qualified namespace fell back to a same-named sibling";
  var ambiguousRoute = CodenameModStateResolver.resolve(paths, "MainMenuState",
   "data/states/Nowhere/TitleState.hx");
  if (!ambiguousRoute.ambiguous || ambiguousRoute.path != "")
   throw "owner-wide duplicate silently chose one state";
  var missing = CodenameModStateResolver.resolve(paths, "CreditsState",
   "data/states/Dsides/TitleState.hx");
  if (missing.ambiguous || missing.path != "") throw "missing owner state was not left for native fallback";

  var fallbackOwner = ImportedModDiscovery.ownerForSong("song-a", "assets/data");
  if (fallbackOwner != "assets/imported_mods/dsides")
   throw "chart provenance owner fallback failed";
 }
}''', newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main"],
                cwd=base, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

    def test_codename_constructor_routing_uses_callback_source_and_stays_owner_scoped(self):
        interp = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        runtime = (ROOT / "source/CodenameModRuntime.hx").read_text()
        menu = (ROOT / "source/CodenameImportedModsState.hx").read_text()
        self.assertIn("ownerStateFactory(name)", interp)
        self.assertIn("__compatDiagnosticSource", (ROOT / "source/CodenameModBindings.hx").read_text())
        self.assertIn("CodenameModStateResolver.resolve(activeStatePaths, name, sourcePath)", runtime)
        self.assertIn("Ambiguous state constructor", runtime)
        self.assertIn("item.title", menu)
        self.assertIn("'(' + item.engine + ')'", menu)
        self.assertNotIn("item.relativePath", menu)
        self.assertIn("ImportedModDiscovery.discover('assets/data', catalog)", menu)


if __name__ == "__main__":
    unittest.main()
