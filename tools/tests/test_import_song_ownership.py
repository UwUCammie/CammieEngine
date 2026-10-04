"""A non-overwriting import must not retarget another donor's scripts."""
from haxe_test_support import HAXE_COMMAND
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]

class ImportSongOwnershipTest(unittest.TestCase):
    def test_base_song_registry_covers_tracked_charts(self):
        tracked = subprocess.run(["git", "ls-files", "assets/data/*/*.json"], cwd=ROOT,
                                 capture_output=True, text=True, check=True).stdout.splitlines()
        folders = {Path(path).parent.name for path in tracked}
        registered = set(json.loads((ROOT / "assets/data/baseSongKeys.json").read_text()))
        self.assertEqual(registered, folders)

    def test_matching_foreign_and_previously_mixed_owners(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import sys.io.File;
import sys.FileSystem;
class Main {
 static function main() {
  FileSystem.createDirectory("song");
  var a = "donor-one"; var b = "donor-two";
  if (ImportSongOwnership.conflict("song", a, "Psych Engine") == null) throw "unknown owner overwritten";
  FileSystem.createDirectory("assets"); FileSystem.createDirectory("assets/data");
  if (ImportSongOwnership.conflict("assets/data/new-song", a, "Psych Engine") == null)
    throw "missing base ownership registry did not fail closed";
  var manifest = CompatScriptManifest.create(a, "Psych Engine");
  var encoded = CompatScriptManifest.stringify(manifest);
  File.saveContent("song/compatScripts.json", encoded);
  if (ImportSongOwnership.conflict("song", a, "Psych Engine") != null) throw "same owner";
  if (ImportSongOwnership.conflict("song", b, "Psych Engine") == null) throw "same engine different donor";
  if (ImportSongOwnership.conflict("song", a, "FPS Plus") == null) throw "different engine";
  if (File.getContent("song/compatScripts.json") != encoded) throw "guard mutated manifest";
  var foreign = CompatScriptManifest.create(b, "Psych Engine");
  manifest.roots.push(foreign.roots[0]); manifest.selectedRoot = foreign.selectedRoot;
  File.saveContent("song/compatScripts.json", CompatScriptManifest.stringify(manifest));
  if (ImportSongOwnership.conflict("song", b, "Psych Engine") == null) throw "mixed old import allowed";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mixed_selected_owner_repairs_visuals_without_duplicate_chart(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  FileSystem.createDirectory("assets"); FileSystem.createDirectory("assets/data");
  File.saveContent("assets/data/baseSongKeys.json", '["monster"]');
  var current = "/donors/current"; var old = "/donors/old";
  var folder = "assets/data/overlap";
  FileSystem.createDirectory(folder);
  var manifest = CompatScriptManifest.create(old, "V-Slice");
  var currentManifest = CompatScriptManifest.create(current, "V-Slice");
  manifest.roots.push(currentManifest.roots[0]);
  manifest.selectedRoot = currentManifest.selectedRoot;
  File.saveContent(folder + "/compatScripts.json", CompatScriptManifest.stringify(manifest));
  if (ImportSongOwnership.conflict(folder, current, "V-Slice") == null)
    throw "mixed chart ownership was accepted for chart writes";
  var repair = ImportSongOwnership.planDestination(folder, "overlap", current, "V-Slice");
  if (Reflect.field(repair, "error") != null || Reflect.field(repair, "qualified") == true
      || Reflect.field(repair, "visualOnly") != true)
    throw "selected owner did not receive a visual-only repair";
  var other = ImportSongOwnership.planDestination(folder, "overlap", old, "V-Slice");
  if (Reflect.field(other, "visualOnly") == true || Reflect.field(other, "qualified") != true)
    throw "unselected owner incorrectly claimed the chart";
  FileSystem.createDirectory("assets/data/monster");
  File.saveContent("assets/data/monster/compatScripts.json", CompatScriptManifest.stringify(manifest));
  var base = ImportSongOwnership.planDestination("assets/data/monster", "monster", current, "V-Slice");
  if (Reflect.field(base, "visualOnly") == true || Reflect.field(base, "qualified") != true)
    throw "base-song guard was bypassed";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                                     "-cp", tmp, "--run", "Main"], cwd=tmp,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        batch = module[module.index("static public function importSongsFromPath("):]
        batch = batch[:batch.index("\n\t#else")]
        self.assertLess(batch.index("Reflect.field(destinationPlan, 'visualOnly') == true"),
                        batch.index("if (ownershipError != null)"))
        self.assertIn("mergeConvertedVisuals(songData)", batch)

    def test_incomplete_import_provenance_allows_only_same_owner_to_resume(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  var a = "donor-one"; var b = "donor-two";
  FileSystem.createDirectory("assets"); FileSystem.createDirectory("assets/data");
  File.saveContent("assets/data/baseSongKeys.json", '["monster"]');
  var folder = "assets/data/monster--codename-owner";
  FileSystem.createDirectory(folder);
  var record = ImportSongOwnership.provenance("monster", a, "Codename Engine",
    "monster--codename-owner", "Monster · Mod");
  File.saveContent(folder + "/importProvenance.json", Json.stringify(record));
  if (ImportSongOwnership.conflict(folder, a, "Codename Engine") != null)
    throw "same owner could not finish incomplete import";
  if (ImportSongOwnership.conflict(folder, b, "Codename Engine") == null)
    throw "different donor claimed incomplete import";
  if (ImportSongOwnership.conflict(folder, a, "Psych Engine") == null)
    throw "different engine claimed incomplete import";
  if (ImportSongOwnership.conflict("assets/data/monster", a, "Codename Engine") == null)
    throw "base song was not reserved";
  Reflect.setField(record, "destinationFolder", "another-folder");
  File.saveContent(folder + "/importProvenance.json", Json.stringify(record));
  if (ImportSongOwnership.conflict(folder, a, "Codename Engine") == null)
    throw "wrong destination claimed incomplete import";
  File.saveContent(folder + "/importProvenance.json", "not json");
  if (ImportSongOwnership.conflict(folder, a, "Codename Engine") == null)
    throw "malformed provenance claimed incomplete import";
  File.saveContent(folder + "/importProvenance.json", Json.stringify(ImportSongOwnership.provenance(
    "monster", a, "Codename Engine", "monster--codename-owner", "Monster · Mod")));
  File.saveContent(folder + "/compatScripts.json", "corrupt");
  if (ImportSongOwnership.conflict(folder, a, "Codename Engine") == null)
    throw "valid provenance bypassed corrupt completed ownership";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_collision_gets_stable_owner_key_and_destination_only_provenance(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  var original = "improbable-outset";
  var currentRoot = "/donors/vs-tricky";
  var nextRoot = "/donors/d-sides";
  FileSystem.createDirectory("assets");
  FileSystem.createDirectory("assets/data");
  File.saveContent("assets/data/baseSongKeys.json", '["fresh", "monster", "tutorial"]');
  FileSystem.createDirectory("assets/data/" + original);
  File.saveContent("assets/data/" + original + "/compatScripts.json",
    CompatScriptManifest.stringify(CompatScriptManifest.create(currentRoot, "V-Slice")));
  var plan = ImportSongOwnership.planDestination("assets/data/" + original,
    original, nextRoot, "Codename");
  if (Reflect.field(plan, "error") != null) throw "qualified collision was rejected";
  if (Reflect.field(plan, "qualified") != true) throw "foreign owner was not qualified";
  var destination:String = Reflect.field(plan, "folder");
  if (destination != ImportSongOwnership.ownerQualifiedFolder(original, nextRoot, "Codename"))
    throw "destination is not deterministic";
  if (destination == original || ImportSongOwnership.conflict("assets/data/" + destination,
    nextRoot, "Codename") != null) throw "qualified destination is not owner-safe";
  var sameOwnerPlan = ImportSongOwnership.planDestination("assets/data/" + destination,
    destination, nextRoot, "Codename");
  if (Reflect.field(sameOwnerPlan, "qualified") == true
    || Reflect.field(sameOwnerPlan, "folder") != destination)
    throw "existing owner-qualified destination was not stable";
  var provenance = Json.stringify(ImportSongOwnership.provenance(original, nextRoot,
    "Codename", destination, "Improbable Outset · D-Sides · Codename"));
  if (provenance.indexOf(nextRoot) >= 0 || provenance.indexOf(currentRoot) >= 0)
    throw "persisted provenance contains a donor filesystem path";
  if (provenance.indexOf(destination) < 0 || provenance.indexOf("improbable-outset") < 0)
    throw "persisted provenance lost source or destination identity";
  FileSystem.createDirectory("assets/data/monster");
  File.saveContent("assets/data/monster/compatScripts.json",
    CompatScriptManifest.stringify(CompatScriptManifest.create(nextRoot, "Codename")));
  var basePlan = ImportSongOwnership.planDestination("assets/data/monster", "monster", nextRoot, "Codename");
  if (Reflect.field(basePlan, "qualified") != true || Reflect.field(basePlan, "error") != null)
    throw "a prior bad import manifest cannot claim a base song";
  for (engine in ["Psych Engine", "V-Slice", "Modding Plus", "ModdingPoop",
    "Nightmare Vision", "Codename Engine"]) {
    var isolated = ImportSongOwnership.planDestination("assets/data/monster", "monster",
      "/renamed/source/" + engine, engine);
    if (Reflect.field(isolated, "qualified") != true || Reflect.field(isolated, "error") != null)
      throw "base protection depends on engine: " + engine;
  }
  for (baseKey in ["fresh", "monster", "tutorial"]) {
    var nmv = ImportSongOwnership.planDestination("assets/data/" + baseKey, baseKey,
      "/donors/nightmare-vision", "Nightmare Vision");
    var nmvFolder:String = Reflect.field(nmv, "folder");
    if (Reflect.field(nmv, "qualified") != true || Reflect.field(nmv, "error") != null
        || !StringTools.startsWith(nmvFolder, baseKey + "--nightmare-vision-"))
      throw "NMV base collision was not isolated: " + baseKey;
  }
  var engineMonster = ImportSongOwnership.ownerQualifiedFolder("monster",
    "/donors/nmv-executable", "Nightmare Vision");
  var packMonster = ImportSongOwnership.ownerQualifiedFolder("monster",
    "/donors/nmv-executable/content/dsides-pack", "Nightmare Vision");
  if (engineMonster == packMonster)
    throw "Nested content pack reused the executable's owner-qualified song key";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pristine_collision_destination_records_owner_before_manifest_guard(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  var original = "collision-track";
  var currentRoot = "/donors/base-song-owner";
  var nextRoot = "/donors/renamed-mod-folder";
  FileSystem.createDirectory("assets");
  FileSystem.createDirectory("assets/data");
  File.saveContent("assets/data/baseSongKeys.json", '["collision-track"]');
  FileSystem.createDirectory("assets/data/collision-track");
  File.saveContent("assets/data/collision-track/compatScripts.json",
    CompatScriptManifest.stringify(CompatScriptManifest.create(currentRoot, "V-Slice")));

  var plan = ImportSongOwnership.planDestination("assets/data/collision-track", original,
    nextRoot, "Codename Engine");
  if (Reflect.field(plan, "error") != null || Reflect.field(plan, "qualified") != true)
    throw "base-song collision was not assigned an owner-qualified destination";
  var destination:String = Reflect.field(plan, "folder");
  var folder = "assets/data/" + destination;
  if (FileSystem.exists(folder)) throw "fixture destination must start pristine";
  if (ImportSongOwnership.conflict(folder, nextRoot, "Codename Engine") != null)
    throw "nonexistent destination should be writable";

  // importSong creates the directory and writes its chart before the batch
  // writer adds either ownership marker.
  FileSystem.createDirectory(folder);
  File.saveContent(folder + "/" + destination + ".json", '{"song":{}}');
  if (ImportSongOwnership.conflict(folder, nextRoot, "Codename Engine") == null)
    throw "chart-only folder incorrectly passed the manifest ownership guard";

  File.saveContent(folder + "/importProvenance.json", Json.stringify(
    ImportSongOwnership.provenance(original, nextRoot, "Codename Engine",
      destination, "Collision Track · Renamed Mod · Codename Engine")));
  if (ImportSongOwnership.conflict(folder, nextRoot, "Codename Engine") != null)
    throw "fresh collision owner could not pass the manifest guard after provenance";
  File.saveContent(folder + "/compatScripts.json",
    CompatScriptManifest.stringify(CompatScriptManifest.create(nextRoot, "Codename Engine")));
  if (ImportSongOwnership.conflict(folder, nextRoot, "Codename Engine") != null)
    throw "completed owner-qualified destination lost its ownership";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        manifest_loop = module[module.index("// Every accepted imported song gets a destination-only manifest."):]
        manifest_loop = manifest_loop[:manifest_loop.index("// Registry-backed visual validation")]
        self.assertLess(manifest_loop.index("writeImportProvenance(importedSong)"),
                        manifest_loop.index("writeCompatScriptManifest(importedSong)"))

    def test_batch_planner_installs_destination_before_chart_and_registry_writes(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        batch = module[module.index("static public function importSongsFromPath("):]
        batch = batch[:batch.index("\n\t#else")]
        self.assertLess(batch.index("ImportSongOwnership.planDestination("), batch.index("importSong(songData)"))
        self.assertIn("Reflect.setField(songData, 'destinationFolder', ownerFolder)", batch)
        self.assertIn("Reflect.setField(songData, 'display', currentDisplay + ' · ' + ownerLabel)", batch)
        self.assertIn("importedRegistryNames.set(storageKey, true)", batch)
        self.assertIn("writeImportProvenance(importedSong)", batch)

    def test_mod_label_uses_metadata_or_single_codename_mod_directory(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  FileSystem.createDirectory("renamed-download");
  File.saveContent("renamed-download/pack.json", '{"name":"Actual Psych Mod"}');
  if (ImportSongOwnership.modDisplayName("renamed-download") != "Actual Psych Mod")
    throw "Psych metadata name";
  if (!ImportSongOwnership.displayNameInfo("renamed-download").authored)
    throw "Psych metadata is authored";
  FileSystem.createDirectory("source-checkout-with-random-folder");
  File.saveContent("source-checkout-with-random-folder/Project.xml",
    '<project><app title="Friday Night Funkin: Source Engine" /></project>');
  var projectTitle = ImportSongOwnership.displayNameInfo("source-checkout-with-random-folder");
  if (!projectTitle.authored || projectTitle.name != "Friday Night Funkin: Source Engine")
    throw "source project title metadata";
  if (ImportSongOwnership.displayWithEngine("Friday Night Funkin: Psych Engine", "Psych Engine")
    != "Friday Night Funkin: Psych Engine")
    throw "redundant engine suffix";
  if (ImportSongOwnership.displayWithEngine("AntiPsych Engine", "Psych Engine")
    != "AntiPsych Engine · Psych Engine")
    throw "unrelated title suffix";
  FileSystem.createDirectory("outer-name");
  FileSystem.createDirectory("outer-name/mods");
  FileSystem.createDirectory("outer-name/mods/D-Sides REDUX");
  File.saveContent("outer-name/Project.xml", '<project><app title="Host Engine" /></project>');
  if (ImportSongOwnership.modDisplayName("outer-name") != "D-Sides REDUX")
    throw "Codename inner mod name";
  if (ImportSongOwnership.displayNameInfo("outer-name").authored)
    throw "directory fallback is not authored";
  FileSystem.createDirectory("changed-folder");
  File.saveContent("changed-folder/_polymod_meta.json", '{"title":"Wacky World"}');
  if (ImportSongOwnership.modDisplayName("changed-folder") != "Wacky World")
    throw "Polymod title";
  FileSystem.createDirectory("nested-psych");
  FileSystem.createDirectory("nested-psych/mods");
  File.saveContent("nested-psych/mods/pack.json", '{"name":"Bruce Update"}');
  if (ImportSongOwnership.modDisplayName("nested-psych") != "Bruce Update")
    throw "nested Psych pack name";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_package_id_reuses_existing_owner_after_source_root_moves(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  var engine = "Psych Engine";
  var oldRoot = Sys.getCwd() + "/first-extraction-name";
  var newRoot = Sys.getCwd() + "/renamed-and-moved-folder";
  FileSystem.createDirectory("assets"); FileSystem.createDirectory("assets/data");
  File.saveContent("assets/data/baseSongKeys.json", '[]');
  FileSystem.createDirectory(oldRoot); FileSystem.createDirectory(newRoot);
  File.saveContent(oldRoot + "/pack.json", '{"id":"org.example.shared","name":"Stable Package"}');
  File.saveContent(newRoot + "/pack.json", '{"id":"org.example.shared","name":"Stable Package"}');
  var namespace = CompatScriptManifest.namespaceFor(oldRoot, engine);
  var destination = "assets/data/stable-song";
  FileSystem.createDirectory(destination);
  File.saveContent(destination + "/compatScripts.json",
    CompatScriptManifest.stringify(CompatScriptManifest.create(oldRoot, engine)));
  var receipt = ImportSongOwnership.provenance("authored-folder", oldRoot, engine,
    "stable-song", "Stable Song · Stable Package", "Stable Package", "metadata");
  var encoded = Json.stringify(receipt);
  if (encoded.indexOf(oldRoot) >= 0) throw "receipt stored the donor path";
  if (Reflect.field(receipt, "sourceIdentity") != "psych engine|id|org.example.shared")
    throw "receipt omitted the authored package identity";
  File.saveContent(destination + "/importProvenance.json", encoded);
  ImportSongOwnership.invalidateOwnerIdentityIndex();
  if (CompatScriptManifest.namespaceFor(newRoot, engine) != namespace)
    throw "moved package was assigned a new compatibility namespace";
  if (ImportSongOwnership.conflict(destination, newRoot, engine) != null)
    throw "moved package could not refresh its existing chart owner";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unnamed_package_uses_user_label_as_movable_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  var engine = "Codename Engine";
  var oldRoot = Path.normalize(Sys.getCwd() + "/old-package-folder");
  var newRoot = Path.normalize(Sys.getCwd() + "/new-package-folder");
  FileSystem.createDirectory("assets"); FileSystem.createDirectory("assets/data");
  File.saveContent("assets/data/baseSongKeys.json", '[]');
  FileSystem.createDirectory(oldRoot); FileSystem.createDirectory(newRoot);
  for (root in [oldRoot, newRoot]) {
   FileSystem.createDirectory(root + "/data/user-named-song");
   FileSystem.createDirectory(root + "/songs/user-named-song");
   File.saveContent(root + "/data/user-named-song/user-named-song.json", '{"song":{"notes":[]}}');
   File.saveContent(root + "/songs/user-named-song/Inst.ogg", "same audio manifest");
  }
  var oldChart = oldRoot + "/data/user-named-song/user-named-song.json";
  var newChart = newRoot + "/data/user-named-song/user-named-song.json";
  var oldSongs:Array<Dynamic> = [{sourceRoot:oldRoot, sourceFolder:"user-named-song",
    diffFiles:[oldChart], importSourceInfo:{song:oldRoot + "/songs/user-named-song"}}];
  var oldNames:Map<String, String> = new Map();
  oldNames.set(oldRoot, "My Named Package");
  ImportSongOwnership.setIdentityOverrides(oldNames);
  ImportSongOwnership.setSourceFingerprintHints(oldSongs);
  var destination = "assets/data/user-named-song";
  FileSystem.createDirectory(destination);
  var receipt = ImportSongOwnership.provenance("song", oldRoot, engine,
    "user-named-song", "Song · My Named Package", "My Named Package", "user");
  var expectedNamespace = CompatScriptManifest.namespaceFor(oldRoot, engine);
  File.saveContent(destination + "/importProvenance.json", Json.stringify(receipt));
  ImportSongOwnership.clearIdentityOverrides();
  ImportSongOwnership.invalidateOwnerIdentityIndex();
  var newNames:Map<String, String> = new Map();
  newNames.set(newRoot, "My Named Package");
  ImportSongOwnership.setIdentityOverrides(newNames);
  var newSongs:Array<Dynamic> = [{sourceRoot:newRoot, sourceFolder:"user-named-song",
    diffFiles:[newChart], importSourceInfo:{song:newRoot + "/songs/user-named-song"}}];
  ImportSongOwnership.setSourceFingerprintHints(newSongs);
  if (CompatScriptManifest.namespaceFor(newRoot, engine) != expectedNamespace)
    throw "user label did not reconnect a renamed package root";
  ImportSongOwnership.clearIdentityOverrides();
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_import_without_fingerprint_does_not_claim_moved_owner(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  var engine = "Psych Engine";
  var root = Sys.getCwd() + "/renamed-legacy-package";
  var owner = "assets/imported_mods/psych-engine-legacy-package-1234567890";
  FileSystem.createDirectory("assets"); FileSystem.createDirectory("assets/data");
  File.saveContent("assets/data/baseSongKeys.json", '[]');
  FileSystem.createDirectory(root); FileSystem.createDirectory("assets/data/legacy-song");
  File.saveContent(root + "/pack.json", '{"name":"Legacy Package"}');
  File.saveContent("assets/data/legacy-song/compatScripts.json",
    '{"version":1,"roots":[{"engine":"Psych Engine","path":"' + owner
      + '"}],"selectedRoot":"' + owner + '"}');
  File.saveContent("assets/data/legacy-song/importProvenance.json",
    '{"version":1,"sourceFolder":"legacy-song","sourceEngine":"Psych Engine",'
      + '"sourceOwner":"' + owner + '","destinationFolder":"legacy-song",'
      + '"display":"Legacy Song · Legacy Package","modName":"Legacy Package",'
      + '"nameSource":"metadata"}');
  ImportSongOwnership.invalidateOwnerIdentityIndex();
  var originalManifest = File.getContent("assets/data/legacy-song/compatScripts.json");
  if (CompatScriptManifest.namespaceFor(root, engine) == "psych-engine-legacy-package-1234567890")
    throw "legacy display label alone claimed a moved owner";
  if (ImportSongOwnership.conflict("assets/data/legacy-song", root, engine) == null)
    throw "legacy owner conflict was not rejected";
  if (File.getContent("assets/data/legacy-song/compatScripts.json") != originalManifest)
    throw "failed legacy claim mutated the existing owner manifest";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_project_title_reconnects_and_duplicate_title_owners_fail_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  var engine = "Psych Engine";
  var oldRoot = Sys.getCwd() + "/old-project-folder";
  var newRoot = Sys.getCwd() + "/renamed-project-folder";
  FileSystem.createDirectory("assets"); FileSystem.createDirectory("assets/data");
  File.saveContent("assets/data/baseSongKeys.json", '[]');
  FileSystem.createDirectory(oldRoot); FileSystem.createDirectory(newRoot);
  var project = '<project><app title="Unique Authored Package Title" /></project>';
  File.saveContent(oldRoot + "/Project.xml", project);
  File.saveContent(newRoot + "/Project.xml", project);
  var identity = ImportSongOwnership.stableIdentity(oldRoot, engine);
  if (identity != "psych engine|package-title|unique authored package title")
    throw "authored project title was not selected as package identity";
  FileSystem.createDirectory("assets/data/project-song");
  for (root in [oldRoot, newRoot]) {
   FileSystem.createDirectory(root + "/data/project-song");
   FileSystem.createDirectory(root + "/songs/project-song");
   File.saveContent(root + "/data/project-song/project-song.json", '{"song":{"notes":[]}}');
   File.saveContent(root + "/songs/project-song/Inst.ogg", "same audio manifest");
  }
  var oldChart = oldRoot + "/data/project-song/project-song.json";
  var newChart = newRoot + "/data/project-song/project-song.json";
  var oldSongs:Array<Dynamic> = [{sourceRoot:oldRoot, sourceFolder:"project-song",
    diffFiles:[oldChart], importSourceInfo:{song:oldRoot + "/songs/project-song"}}];
  ImportSongOwnership.setSourceFingerprintHints(oldSongs);
  var oldRecord = ImportSongOwnership.provenance("project-song", oldRoot, engine,
    "project-song", "Project Song · Unique Authored Package Title",
    "Unique Authored Package Title", "metadata");
  var fingerprint = Reflect.field(oldRecord, "sourceFingerprint");
  if (fingerprint == null || fingerprint == "") throw "source chart/audio fingerprint was not recorded";
  var ownerParts = Std.string(Reflect.field(oldRecord, "sourceOwner")).split("/");
  var expectedNamespace = ownerParts[ownerParts.length - 1];
  File.saveContent("assets/data/project-song/importProvenance.json", Json.stringify(oldRecord));
  ImportSongOwnership.invalidateOwnerIdentityIndex();
  var newSongs:Array<Dynamic> = [{sourceRoot:newRoot, sourceFolder:"project-song",
    diffFiles:[newChart], importSourceInfo:{song:newRoot + "/songs/project-song"}}];
  ImportSongOwnership.setSourceFingerprintHints(newSongs);
  var movedNamespace = CompatScriptManifest.namespaceFor(newRoot, engine);
  if (movedNamespace != expectedNamespace)
    throw "unique project title did not reconnect: " + movedNamespace + " != " + expectedNamespace;

  var otherOwner = "assets/imported_mods/psych-other-owner-1234567890";
  FileSystem.createDirectory("assets/data/other-project-song");
  var otherRecord:Dynamic = {version:1, sourceEngine:engine, sourceOwner:otherOwner,
    destinationFolder:"other-project-song", sourceIdentity:identity,
    sourceFingerprint:fingerprint, modName:"Unique Authored Package Title"};
  File.saveContent("assets/data/other-project-song/importProvenance.json", Json.stringify(otherRecord));
  ImportSongOwnership.invalidateOwnerIdentityIndex();
  var ambiguous = CompatScriptManifest.namespaceFor(newRoot, engine);
  if (ambiguous == expectedNamespace || ambiguous == "psych-other-owner-1234567890")
    throw "duplicate title chose one existing owner instead of failing closed";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_second_package_with_same_title_gets_separate_owner_by_chart_audio_fingerprint(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  var engine = "Psych Engine";
  var firstRoot = Sys.getCwd() + "/first-same-title-package";
  var secondRoot = Sys.getCwd() + "/second-same-title-package";
  for (root in [firstRoot, secondRoot]) {
   FileSystem.createDirectory(root);
   FileSystem.createDirectory(root + "/data/shared-song");
   FileSystem.createDirectory(root + "/songs/shared-song");
   File.saveContent(root + "/pack.json", '{"name":"Shared Title"}');
  }
  File.saveContent(firstRoot + "/data/shared-song/shared-song.json", '{"song":{"notes":[1]}}');
  File.saveContent(secondRoot + "/data/shared-song/shared-song.json", '{"song":{"notes":[2]}}');
  File.saveContent(firstRoot + "/songs/shared-song/Inst.ogg", "first audio");
  File.saveContent(secondRoot + "/songs/shared-song/Inst.ogg", "second audio is distinct");

  FileSystem.createDirectory("assets"); FileSystem.createDirectory("assets/data");
  File.saveContent("assets/data/baseSongKeys.json", '[]');
  var existing = "assets/data/shared-song";
  FileSystem.createDirectory(existing);
  File.saveContent(existing + "/shared-song.json", '{"song":{"notes":[1]}}');
  var firstSong:Array<Dynamic> = [{sourceRoot:firstRoot, sourceFolder:"shared-song",
    diffFiles:[firstRoot + "/data/shared-song/shared-song.json"],
    importSourceInfo:{song:firstRoot + "/songs/shared-song"}}];
  ImportSongOwnership.setSourceFingerprintHints(firstSong);
  var firstReceipt = ImportSongOwnership.provenance("shared-song", firstRoot, engine,
    "shared-song", "Shared Song · Shared Title", "Shared Title", "metadata");
  var firstIdentity = Std.string(Reflect.field(firstReceipt, "sourceIdentity"));
  var firstFingerprint = Std.string(Reflect.field(firstReceipt, "sourceFingerprint"));
  if (firstIdentity != "psych engine|package-name|shared title" || firstFingerprint == "")
    throw "first package receipt lacks its label fingerprint";
  File.saveContent(existing + "/importProvenance.json", Json.stringify(firstReceipt));
  File.saveContent(existing + "/compatScripts.json",
    CompatScriptManifest.stringify(CompatScriptManifest.create(firstRoot, engine)));
  var manifestBefore = File.getContent(existing + "/compatScripts.json");
  var chartBefore = File.getContent(existing + "/shared-song.json");
  ImportSongOwnership.invalidateOwnerIdentityIndex();

  var secondSong:Array<Dynamic> = [{sourceRoot:secondRoot, sourceFolder:"shared-song",
    diffFiles:[secondRoot + "/data/shared-song/shared-song.json"],
    importSourceInfo:{song:secondRoot + "/songs/shared-song"}}];
  ImportSongOwnership.setSourceFingerprintHints(secondSong);
  var secondFingerprint = Std.string(Reflect.field(ImportSongOwnership.provenance("shared-song",
    secondRoot, engine, "shared-song", "Shared Song · Shared Title", "Shared Title", "metadata"),
    "sourceFingerprint"));
  if (secondFingerprint == firstFingerprint) throw "different package fixture has the same fingerprint";
  var plan = ImportSongOwnership.planDestination(existing, "shared-song", secondRoot, engine);
  if (Reflect.field(plan, "error") != null || Reflect.field(plan, "qualified") != true)
    throw "second same-title package was not isolated: " + Std.string(Reflect.field(plan, "error"));
  var destination:String = Reflect.field(plan, "folder");
  if (destination == "shared-song") throw "second package retained the first owner's chart key";
  if (ImportSongOwnership.conflict(existing, secondRoot, engine) == null)
    throw "second package was treated as the first package's owner";
  if (File.getContent(existing + "/compatScripts.json") != manifestBefore
    || File.getContent(existing + "/shared-song.json") != chartBefore)
    throw "collision planning modified the first package's imported files";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generic_pack_template_uses_parent_folder_and_keeps_package_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            fixture = Path(tmp) / "Main.hx"
            fixture.write_text(r'''import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  FileSystem.createDirectory("SEGATENDO COLLECTION");
  FileSystem.createDirectory("SEGATENDO COLLECTION/mods");
  File.saveContent("SEGATENDO COLLECTION/mods/pack.json",
    '{"name":"Name","description":"Description"}');
  var template = ImportSongOwnership.displayNameInfo("SEGATENDO COLLECTION/mods");
  if (template.name != "SEGATENDO COLLECTION" || template.authored || !template.template)
    throw "generic Psych package template did not use its parent directory label";
  var originalRoot = ImportSongOwnership.displayNameInfo("SEGATENDO COLLECTION");
  if (originalRoot.name != "SEGATENDO COLLECTION" || originalRoot.authored || !originalRoot.template)
    throw "generic Psych package template changed the selected parent folder fallback";
  if (ImportSongOwnership.stableIdentity("SEGATENDO COLLECTION/mods", "Psych Engine")
    != "psych engine|package-name|name")
    throw "template recognition changed stable source identity";
  FileSystem.createDirectory("legitimate-name");
  File.saveContent("legitimate-name/pack.json",
    '{"name":"Name","description":"A real package named Name"}');
  var legitimate = ImportSongOwnership.displayNameInfo("legitimate-name");
  if (legitimate.name != "Name" || !legitimate.authored || legitimate.template)
    throw "legitimate package title Name was treated as a template";
 }
}''', encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"],
                cwd=tmp, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_package_display_refresh_preserves_owner_and_user_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            fixture = Path(tmp) / "Main.hx"
            fixture.write_text(r'''class Main {
 static function main() {
  var owner = "assets/imported_mods/psych-engine-mods-51a38873d6";
  var record:Dynamic = {
    version:1, sourceEngine:"Psych Engine", sourceOwner:owner,
    destinationFolder:"segatendo-song", display:"Authored Song Title",
    sourceFolder:"segatendo-song", sourceIdentity:"psych engine|package-name|name",
    sourceFingerprint:"retained-fingerprint", modName:"Name", nameSource:"metadata",
    extension:{keep:true}
  };
  if (!ImportSongOwnership.refreshDisplayMetadata(record, "Psych Engine", owner,
    "segatendo-song", "SEGATENDO COLLECTION", "inferred"))
    throw "retained package display metadata was not refreshed";
  if (record.modName != "SEGATENDO COLLECTION" || record.nameSource != "inferred")
    throw "new package fallback was not saved";
  if (record.sourceIdentity != "psych engine|package-name|name"
    || record.sourceFingerprint != "retained-fingerprint" || record.sourceOwner != owner
    || record.destinationFolder != "segatendo-song" || record.display != "Authored Song Title"
    || record.sourceFolder != "segatendo-song" || record.extension.keep != true)
    throw "display refresh changed source, owner, score, or extension identity";

  var userRecord:Dynamic = {
    version:1, sourceEngine:"Psych Engine", sourceOwner:owner,
    destinationFolder:"segatendo-song", modName:"My Label", nameSource:"user"
  };
  if (ImportSongOwnership.refreshDisplayMetadata(userRecord, "Psych Engine", owner,
    "segatendo-song", "SEGATENDO COLLECTION", "inferred")
    || userRecord.modName != "My Label")
    throw "retained-source refresh replaced an explicit user label";
  var wrongOwner = owner + "-other";
  if (ImportSongOwnership.refreshDisplayMetadata(record, "Psych Engine", wrongOwner,
    "segatendo-song", "Wrong Owner", "inferred")
    || record.modName != "SEGATENDO COLLECTION")
    throw "display refresh modified a receipt owned by another source";
 }
}''', encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"],
                cwd=tmp, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ambiguous_package_identity_does_not_merge_existing_owners(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            path = Path(tmp)
            (path / "Main.hx").write_text('''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  var engine = "Psych Engine";
  var root = Sys.getCwd() + "/renamed-package";
  FileSystem.createDirectory("assets"); FileSystem.createDirectory("assets/data");
  File.saveContent("assets/data/baseSongKeys.json", '[]');
  FileSystem.createDirectory(root);
  File.saveContent(root + "/pack.json", '{"id":"org.example.duplicate","name":"Duplicate Title"}');
  for (index in 1...3) {
   var folder = "assets/data/song-" + index;
   FileSystem.createDirectory(folder);
   var owner = "assets/imported_mods/owner-" + index + "-1234567890";
   var record:Dynamic = {version:1, sourceEngine:engine, sourceOwner:owner,
     destinationFolder:"song-" + index,
     sourceIdentity:"psych engine|id|org.example.duplicate"};
   File.saveContent(folder + "/importProvenance.json", Json.stringify(record));
  }
  ImportSongOwnership.invalidateOwnerIdentityIndex();
  var next = CompatScriptManifest.namespaceFor(root, engine);
  if (next == "owner-1-1234567890" || next == "owner-2-1234567890")
    throw "ambiguous identity selected a foreign imported namespace";
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", tmp, "--run", "Main"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
