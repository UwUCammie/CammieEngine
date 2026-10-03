"""Read-only Psych/Kade script-scope discovery coverage."""
from haxe_test_support import HAXE_COMMAND

import hashlib
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONORS = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


MAIN = r'''import haxe.Json;
import sys.io.File;

class Main {
  static function main() {
    var args = Sys.args();
    var planNumber = 0;
    var index = 0;
    while (index + 2 < args.length) {
      var root = args[index++];
      var chartPath = args[index++];
      var song = args[index++];
      var chart:Dynamic = chartPath == "" ? null : Json.parse(File.getContent(chartPath));
      var plan = PsychScriptDiscovery.discover(root, song, chart);
      Sys.println('PLAN|' + planNumber + '|' + plan.song + '|' + plan.stage);
      for (entry in plan.scripts)
        Sys.println('ENTRY|' + planNumber + '|' + entry.scope + '|' + entry.name + '|' + entry.path);
      planNumber++;
    }
  }
}
'''


COMPANION_MAIN = r'''import haxe.Json;
import sys.io.File;

class Main {
  static function main() {
    var args = Sys.args();
    var root = args[0];
    var chart:Dynamic = Json.parse(File.getContent(args[1]));
    var companion:Dynamic = Json.parse(File.getContent(args[2]));
    var plan = PsychScriptDiscovery.discover(root, "testsong", chart, companion);
    for (entry in plan.scripts)
      Sys.println('ENTRY|' + entry.scope + '|' + entry.name + '|' + entry.path);
  }
}
'''


class PsychScriptDiscoveryTest(unittest.TestCase):
    def run_plans(self, plans):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            shutil.copy(ROOT / "source/PsychScriptDiscovery.hx", temp / "PsychScriptDiscovery.hx")
            (temp / "Main.hx").write_text(MAIN, newline='\n')
            args = []
            for root, chart, song in plans:
                args.extend([str(root), str(chart) if chart else "", song])
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main", *args],
                cwd=folder,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        parsed = {}
        for line in result.stdout.splitlines():
            if line.startswith("PLAN|"):
                _, number, song, stage = line.split("|", 3)
                parsed[int(number)] = {"song": song, "stage": stage, "entries": []}
            elif line.startswith("ENTRY|"):
                _, number, scope, name, path = line.split("|", 4)
                parsed[int(number)]["entries"].append({"scope": scope, "name": name, "path": path})
        return parsed

    @staticmethod
    def entry_names(plan, scope):
        return [Path(entry["path"]).name.lower() for entry in plan["entries"] if entry["scope"] == scope]

    def run_companion_plan(self, root, chart, companion):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            shutil.copy(ROOT / "source/PsychScriptDiscovery.hx", temp / "PsychScriptDiscovery.hx")
            (temp / "Main.hx").write_text(COMPANION_MAIN, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main", str(root), str(chart), str(companion)],
                cwd=folder,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.splitlines()

    def test_symlink_mount_retains_runtime_address_and_canonical_deduplication(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder)
            donor = root / "donor"
            scripts = donor / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "global.lua").write_text("function onCreate() end", newline='\n')
            stages = donor / "stages"
            stages.mkdir()
            (stages / "scene.lua").write_text("function onCreate() end", newline='\n')
            # Same real files under two content roots must still run once.
            (donor / "shared").symlink_to(donor, target_is_directory=True)
            runtime = root / "runtime"
            runtime.mkdir()
            mount = runtime / "assets"
            mount.symlink_to(donor, target_is_directory=True)
            chart = root / "chart.json"
            chart.write_text(json.dumps({"song": {"song": "probe", "stage": "scene"}}), newline='\n')
            plan = self.run_plans([(mount, chart, "probe")])[0]
            self.assertEqual(len(plan["entries"]), 2)
            self.assertEqual({entry["scope"] for entry in plan["entries"]}, {"global", "stage"})
            for entry in plan["entries"]:
                path = Path(entry["path"])
                self.assertTrue(path.is_relative_to(runtime), entry)
                self.assertEqual(path.read_text(), "function onCreate() end")
                self.assertTrue(path.resolve().is_relative_to(donor))

    def test_case_insensitive_scopes_direct_references_and_unused_directories(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder) / "donor"
            files = {
                "DATA/TestSong/Script.LUA": "-- song script",
                "DATA/TestSong/helper.hscript": "// song helper",
                "DATA/TestSong/disabled/ghost.lua": "-- not referenced",
                "SCRIPTS/Global.LUA": "-- global",
                "SCRIPTS/disabled/ghost.lua": "-- not referenced",
                "STAGES/MixedStage.LuA": "-- stage",
                "STAGES/Unused/ghost.lua": "-- not referenced",
                "CUSTOM_EVENTS/MixedEvent.lua": "-- event",
                "CUSTOM_EVENTS/Unused/Ghost.lua": "-- not referenced",
                "CUSTOM_EVENTS/Unused/DirectEvent.lua": "-- direct reference",
                "CUSTOM_EVENTS/Used/DeepEvent.hscript": "// direct reference",
                "CUSTOM_NOTETYPES/Poison.lua": "-- note type",
                "CUSTOM_NOTETYPES/Unused/Ghost.lua": "-- not referenced",
                "CUSTOM_NOTETYPES/Unused/DirectType.lua": "-- direct reference",
            }
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')
            chart = root / "chart.json"
            chart.write_text(json.dumps({
                "song": {
                    "song": "testsong",
                    "stage": "mixedstage",
                    "events": [[0, [
                        ["mixedevent", "", ""],
                        ["used/deepevent", "", ""],
                        ["unused/DirectEvent", "", ""],
                        ["missing-event", "", ""],
                    ]]],
                    "notes": [{"sectionNotes": [
                        [0, 0, 0, "Poison"],
                        [10, 1, 0, "unused/DirectType"],
                    ]}],
                },
            }), newline='\n')
            before = {
                relative: hashlib.sha256((root / relative).read_bytes()).digest()
                for relative in files
            }
            plans = self.run_plans([(root, chart, "TESTSONG"), (root, chart, "TESTSONG")])
            self.assertEqual(plans[0], plans[1], "discovery order is not deterministic")
            plan = plans[0]
            self.assertEqual(plan["song"], "TESTSONG")
            self.assertEqual(plan["stage"], "mixedstage")
            self.assertEqual(self.entry_names(plan, "global"), ["global.lua"])
            self.assertEqual(set(self.entry_names(plan, "song")), {"script.lua", "helper.hscript"})
            self.assertEqual(self.entry_names(plan, "stage"), ["mixedstage.lua"])
            self.assertEqual(set(self.entry_names(plan, "custom_event")),
                             {"mixedevent.lua", "deepevent.hscript", "directevent.lua"})
            self.assertEqual(set(self.entry_names(plan, "custom_notetype")),
                             {"poison.lua", "directtype.lua"})
            all_paths = "\n".join(entry["path"].lower() for entry in plan["entries"])
            self.assertNotIn("ghost.lua", all_paths)
            after = {
                relative: hashlib.sha256((root / relative).read_bytes()).digest()
                for relative in files
            }
            self.assertEqual(before, after, "discovery modified donor files")

    def test_psych_songdata_layout_discovers_song_local_scripts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder) / "donor"
            song = root / "assets/data/songData/TestSong"
            song.mkdir(parents=True)
            script = song / "script.lua"
            script.write_text("function onCreate() end", newline='\n')
            chart = root / "chart.json"
            chart.write_text(json.dumps({
                "song": {"song": "testsong", "stage": "stage", "notes": []},
            }), newline='\n')

            plan = self.run_plans([(root, chart, "TestSong")])[0]

            song_entries = [entry for entry in plan["entries"] if entry["scope"] == "song"]
            self.assertEqual([Path(entry["path"]).name.lower() for entry in song_entries], ["script.lua"])
            self.assertEqual(Path(song_entries[0]["path"]), script)
            self.assertEqual(script.read_text(), "function onCreate() end")

    @unittest.skipUnless(
        (DONORS / "psych/PERFEXION Demo1").is_dir(),
        "the external example-mod fixture is not mounted",
    )
    def test_perfexion_psych_donor_selects_global_song_stage_and_events(self):
        root = DONORS / "psych/PERFEXION Demo1"
        chart = root / "data/Resonance/resonance-hard.json"
        plan = self.run_plans([(root, chart, "Resonance")])[0]
        self.assertEqual(plan["stage"].lower(), "haven")
        self.assertIn("intro.lua", self.entry_names(plan, "global"))
        song_scripts = self.entry_names(plan, "song")
        self.assertIn("modchart.lua", song_scripts)
        self.assertGreater(len(song_scripts), 3)
        self.assertIn("haven.lua", self.entry_names(plan, "stage"))
        event_scripts = self.entry_names(plan, "custom_event")
        self.assertIn("cam boom speed.lua", event_scripts)
        self.assertIn("flash.lua", event_scripts)
        paths = "\n".join(entry["path"].lower() for entry in plan["entries"])
        self.assertNotIn("/all scripts/reverse glitch.lua", paths)
        self.assertFalse(any("/unused/" in entry["path"].lower() for entry in plan["entries"]))

    def test_external_event_sidecar_selects_only_referenced_custom_event(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder) / "donor"
            event = root / "CUSTOM_EVENTS/SideOnly.lua"
            event.parent.mkdir(parents=True)
            event.write_text("function onEvent(name, value1, value2) end", newline='\n')
            unused = root / "CUSTOM_EVENTS/Unused.lua"
            unused.write_text("function onEvent(name, value1, value2) end", newline='\n')
            chart = root / "chart.json"
            chart.write_text(json.dumps({"song": {"song": "testsong", "stage": "stage"}}), newline='\n')
            companion = root / "events.json"
            companion.write_text(json.dumps({"events": [[0, [["SideOnly", "", ""]]]]}), newline='\n')
            lines = self.run_companion_plan(root, chart, companion)
            paths = "\n".join(lines).lower()
            self.assertIn("sideonly.lua", paths)
            self.assertNotIn("unused.lua", paths)

    def test_modern_psych_compact_event_records_select_custom_event_script(self):
        """The compact Psych `e` field is a custom-event reference too."""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder) / "donor"
            event = root / "custom_events/FocusCamera.lua"
            event.parent.mkdir(parents=True)
            event.write_text("function onEvent(name, value1, value2) end", newline='\n')
            unused = root / "custom_events/Unused.lua"
            unused.write_text("function onEvent(name, value1, value2) end", newline='\n')
            chart = root / "chart.json"
            chart.write_text(json.dumps({
                "song": {
                    "song": "testsong",
                    "stage": "stage",
                    "events": [
                        {"t": 12.5, "e": "FocusCamera", "v": ["1", "2"]},
                        {"t": 24, "e": "MissingEvent", "v": []},
                    ],
                },
            }), newline='\n')
            companion = root / "events.json"
            companion.write_text("{}", newline='\n')
            lines = self.run_companion_plan(root, chart, companion)
            paths = "\n".join(lines).lower()
            self.assertIn("focuscamera.lua", paths)
            self.assertNotIn("unused.lua", paths)

    @unittest.skipUnless(
        (DONORS / "hellbeats_kade_engine/HellBeats Kade Engine").is_dir(),
        "the external example-mod fixture is not mounted",
    )
    def test_kade_assets_root_selects_song_modchart_case_insensitively(self):
        root = DONORS / "hellbeats_kade_engine/HellBeats Kade Engine"
        chart = root / "assets/data/tutorial/tutorial.json"
        plan = self.run_plans([(root, chart, "tutorial")])[0]
        self.assertIn("modchart.lua", self.entry_names(plan, "song"))
        self.assertFalse(any(entry["scope"] == "stage" for entry in plan["entries"]))


if __name__ == "__main__":
    unittest.main()
