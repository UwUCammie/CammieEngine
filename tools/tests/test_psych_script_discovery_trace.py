"""The opt-in Psych chart trace identifies a failing mounted chart row."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
TRACE_ENV = "DISAPPOINTINGPLUS_PSYCH_DISCOVERY_TRACE"


class PsychScriptDiscoveryTraceTest(unittest.TestCase):
    def test_chart_section_and_row_provenance_is_opt_in(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            owner = work / "owner"
            owner.mkdir()
            (owner / "custom_events").mkdir()
            (owner / "custom_events/Cheer.lua").write_text("-- custom event")
            (owner / "custom_notetypes").mkdir()
            (owner / "custom_notetypes/hurt.lua").write_text("-- custom note type")
            (work / "Main.hx").write_text('''class Main {
 static function main():Void {
  var eventRow:Array<Dynamic> = [100, -1, "Cheer", null];
  var noteRow:Array<Dynamic> = [200, 0, "ignored", "hurt"];
  var chart:Dynamic = {song:{song:"demo", events:[], notes:[
   {sectionNotes:[eventRow, noteRow]}, {sectionNotes:[]}
  ]}};
  var plan = PsychScriptDiscovery.discover(Sys.args()[0], "demo", chart, null,
   "mounted/psych/data/demo/demo-hard.json");
  if (plan.scripts.length != 2
   || plan.scripts[0].scope != PsychScriptDiscovery.CUSTOM_EVENT
   || plan.scripts[0].name != "Cheer"
   || plan.scripts[1].scope != PsychScriptDiscovery.CUSTOM_NOTE_TYPE
   || plan.scripts[1].name != "hurt")
   throw haxe.Json.stringify(plan.scripts);
 }
}''')

            command = [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(work),
                       "--run", "Main", str(owner)]
            env = os.environ.copy()
            env.pop(TRACE_ENV, None)
            quiet = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                   capture_output=True, timeout=60)
            self.assertEqual(quiet.returncode, 0, quiet.stdout + quiet.stderr)
            self.assertNotIn("PSYCH_SCRIPT_DISCOVERY|", quiet.stderr)

            env[TRACE_ENV] = "1"
            traced = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                    capture_output=True, timeout=60)
            self.assertEqual(traced.returncode, 0, traced.stdout + traced.stderr)
            output = traced.stderr
            self.assertIn("phase=chart|chart=mounted/psych/data/demo/demo-hard.json", output)
            self.assertIn("phase=section|section=1|row=-1|detail=begin", output)
            self.assertIn("phase=row|section=0|row=0|detail=before-typecheck", output)
            self.assertIn("phase=row|section=0|row=1|detail=before-typecheck", output)
            # A chart identity is written once, not for every note/index access.
            self.assertEqual(output.count("chart=mounted/psych/data/demo/demo-hard.json"), 1)
            self.assertEqual(output.count("phase=row|"), 2)
            self.assertLess(len(output), 1000)


if __name__ == "__main__":
    unittest.main()
