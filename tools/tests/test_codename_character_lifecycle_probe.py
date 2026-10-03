"""Offline checks for the disposable native character lifecycle probe."""
from haxe_test_support import HAXE_COMMAND

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "codename_character_lifecycle_probe", ROOT / "tmp/codename-character-lifecycle/run_probe.py")
if not Path(SPEC.origin).is_file():
    raise unittest.SkipTest("private lifecycle probe fixture is unavailable")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def records():
    result = [{"event": "startup", "runToken": "one", "playstateVisits": 2}]
    expected = [(0, 0, probe.RIVAL), (0, 1, probe.RIVAL), (1, 0, probe.RIVAL),
                (2, 0, probe.HERO), (3, 0, probe.COMPANION)]
    for visit in (1, 2):
        result.extend({"event": event, "visit": visit, "runToken": "one"}
                      for event in ("playstate_start", "playstate_ready"))
        result.append({"event": "codename_actor_snapshot", "visit": visit,
                       "runToken": "one", "owned": 2, "borrowed": 3,
                       "actors": [{"lineIndex": line, "occurrenceIndex": occurrence,
                                   "authoredId": name, "token": visit * 10 + i,
                                   "displayIndex": i}
                                  for i, (line, occurrence, name) in enumerate(expected)]})
        if visit == 1:
            result.extend({"event": event, "visit": visit, "runToken": "one"}
                          for event in ("playstate_reload_begin", "codename_actor_teardown"))
            result.append({"event": "playstate_destroyed", "visit": 1,
                           "runToken": "one", "owned": 2, "borrowed": 3,
                           "destroyCalls": 2, "remainingBindings": 0, "cleanupErrors": []})
    result.append({"event": "success", "runToken": "one"})
    return result


class LifecycleProbeTests(unittest.TestCase):
    def test_synthetic_hscript_sources_parse_with_production_parser(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text('''class Main {
 static function main():Void {
  for (source in SOURCES) {
   var parsed=CodenameScriptParser.prepare(source,new Map());
   if(parsed.program==null || parsed.diagnostics.length>0)
    throw Std.string(parsed.diagnostics);
  }
 }
 static var SOURCES:Array<String> = '''
                + json.dumps([probe.CHARACTER_SCRIPT, probe.SONG_SCRIPT]) + ';\n}\n', newline='\n')
            command = [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                       "-cp", str(folder), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                       "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_expected_two_visit_evidence(self):
        log = ("CHAR_LIFECYCLE_OK|five-instances|mutable-xml|ordered-nodes|callbacks|cancellation\n" * 2
               + "CHAR_DESTROY_OK|ProbeRival|1|1\n" * 3
               + "CHAR_DESTROY_OK|ProbeHero|1|1\n"
               + "CHAR_DESTROY_OK|ProbeCompanion|1|1\n")
        probe.assert_lifecycle(records(), 42, log)

    def test_reused_actor_and_missing_destroy_are_rejected(self):
        log = ("CHAR_LIFECYCLE_OK|five-instances|mutable-xml|ordered-nodes|callbacks|cancellation\n" * 2
               + "CHAR_DESTROY_OK|ProbeRival|1|1\n" * 3
               + "CHAR_DESTROY_OK|ProbeHero|1|1\n"
               + "CHAR_DESTROY_OK|ProbeCompanion|1|1\n")
        reused = records()
        second = next(row for row in reused if row["event"] == "codename_actor_snapshot" and row["visit"] == 2)
        second["actors"][0]["token"] = 10
        with self.assertRaisesRegex(RuntimeError, "reused first-visit actors"):
            probe.assert_lifecycle(reused, 42, log)
        with self.assertRaisesRegex(RuntimeError, "destroy exactly once"):
            probe.assert_lifecycle(records(), 42, log.replace("CHAR_DESTROY_OK|ProbeHero|1|1\n", ""))

    def test_fixture_declares_instance_local_callbacks(self):
        script = probe.CHARACTER_SCRIPT
        for callback in ("create", "onCharacterXMLParsed", "onCharacterNodeParsed",
                         "postCreate", "update", "beatHit", "stepHit", "onDance",
                         "onPlayAnim", "destroy"):
            self.assertIn(f"function {callback}(", script)
        self.assertIn('event.xml.nodes.anim[1].att.x = "13"', script)
        self.assertIn('event.cancel()', script)


if __name__ == "__main__":
    unittest.main()
