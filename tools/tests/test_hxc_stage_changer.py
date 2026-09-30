"""A complete donor StageRegistry replacement reaches the native stage lifecycle."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR_SCRIPT = (Path("/run/media/cammie/External Storage/FNF-Example-Mods") /
                "v-slice/Wacky World UPDATE [V-Slice]/scripts/modules/SC_StageChanger.hxc")


class HxcStageChangerTest(unittest.TestCase):
    def test_complete_replacement_and_transitive_partial_gate(self):
        (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
        replacement = r'''
  function replaceScene(stageKey:String):Void {
    PlayState.instance.remove(PlayState.instance.currentStage);
    PlayState.instance.currentStage.kill();
    for (piece in PlayState.instance.currentStage.group) {
      piece?.kill();
      PlayState.instance.currentStage.group.remove(piece);
    }
    PlayState.instance.currentStage = StageRegistry.instance.fetchEntry(stageKey);
    if (PlayState.instance.currentStage != null) {
      var folder = PlayState.instance.currentStage?._data?.directory ?? "shared";
      Paths.setCurrentLevel(folder);
      PlayState.instance.currentStage.revive();
      PlayState.instance.resetCameraZoom();
      PlayState.instance.currentStage.buildStage();
      PlayState.instance.currentStage.resetStage();
      PlayState.instance.add(PlayState.instance.currentStage);
    }
  }
'''
        donor = ("class DifferentModule extends Module {\n" + replacement +
                 '  function restoreScene() { replaceScene("alternateStage"); }\n' +
                 "  override function onCountdownStart(event:CountdownScriptEvent):Void { restoreScene(); }\n}\n")
        unsafe = donor.replace("PlayState.instance.currentStage.kill();",
                               'PlayState.instance.currentStage.kill(); trace("extra donor side effect");')
        main = '''import hscript.Parser;
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main() {
  var good=HxcCompat.analyze(sys.io.File.getContent(Sys.args()[0]),"synthetic/scripts/modules/other.hxc");
  check(good.moduleSafe,"complete replacement rejected: "+good.moduleSafetyReasons.join(","));
  check(good.generatedHscript.indexOf("function replaceScene")>=0,"renamed helper missing");
  check(good.generatedHscript.indexOf("PlayState.instance.swapStage(stageKey);")>=0,"native stage lifecycle missing");
  check(good.generatedHscript.indexOf("StageRegistry")<0,"donor stage graph leaked");
  new Parser().parseString(good.generatedHscript);
  var bad=HxcCompat.analyze(sys.io.File.getContent(Sys.args()[1]),"synthetic/scripts/modules/other.hxc");
  check(!bad.moduleSafe,"partial replacement passed safety gate");
  var transitive=false;
  for (reason in bad.moduleSafetyReasons)
   if (reason.indexOf("unsafe helper dependency")>=0) transitive=true;
  check(transitive,"unsafe helper chain was not diagnosed: "+bad.moduleSafetyReasons.join(","));
  check(bad.generatedHscript.indexOf("function countdownStart")<0,"unsafe lifecycle emitted");
  if (Sys.args().length>2) {
   var actual=HxcCompat.analyze(sys.io.File.getContent(Sys.args()[2]),Sys.args()[2]);
   check(actual.moduleSafe,"actual donor stage changer rejected: "+actual.moduleSafetyReasons.join(","));
   check(actual.generatedHscript.indexOf("PlayState.instance.swapStage(id);")>=0,"actual loadStage did not lower");
   check(actual.generatedHscript.indexOf("function countdownStart")>=0,"actual countdown callback absent");
  }
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="hxc-stage-changer-", dir=ROOT / "tmp") as folder:
            fixture = Path(folder)
            (fixture / "Main.hx").write_text(main)
            (fixture / "good.hxc").write_text(donor)
            (fixture / "bad.hxc").write_text(unsafe)
            command = [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                       "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", folder,
                       "--run", "Main", str(fixture / "good.hxc"), str(fixture / "bad.hxc")]
            if DONOR_SCRIPT.is_file():
                command.append(str(DONOR_SCRIPT))
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=45,
                                    env={**os.environ, "TMPDIR": str(ROOT / "tmp")})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
