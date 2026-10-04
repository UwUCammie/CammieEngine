"""Keep Psych's game.vocals native while NV receives its source audio view."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


MAIN = r'''package;
class NightmareVisionPlayableSongView {
 public var marker:String='nightmare-audio-view';
 public function new() {}
}
class NativeSound { public var marker:String='native-vocals'; public function new() {} }
interface NightmareVisionPlayableSongOwner {
 public function nightmareVisionAudioView():NightmareVisionPlayableSongView;
}
class FakeGame implements NightmareVisionPlayableSongOwner {
 public var vocals:NativeSound=new NativeSound();
 public var audio:NativeSound=new NativeSound();
 public var view:NightmareVisionPlayableSongView=new NightmareVisionPlayableSongView();
 public var viewRequests:Int=0;
 public function new() {}
 public function nightmareVisionAudioView():NightmareVisionPlayableSongView {
  viewRequests++;
  return view;
 }
}
class FakeAnimation {
 public var onFrameChange:Dynamic=null;
 public var onFinish:Dynamic=null;
 public var onLoop:Dynamic=null;
 public function new() {}
}
class Character { public var animation:FakeAnimation=new FakeAnimation(); }
class PsychBaseStageActorGroupCompat {}
class HxcCompatRuntime { public static function getZIndex(_object:Dynamic):Dynamic return 0; }
class NightmareVisionFlxGView { public function getField(_field:String):Dynamic return null; }
class NightmareVisionSaveData { public function getField(_field:String):Dynamic return null; }
class NightmareVisionSaveFacade {}
class BaseInterp {
 public function new() {}
 public function get(object:Dynamic,field:String):Dynamic return Reflect.getProperty(object,field);
}
class ProbeInterp extends BaseInterp {
 public var ownerPaths:Dynamic;
 public var parent:Dynamic=null;
 public function new(?paths:Dynamic) { super(); ownerPaths=paths; }
 function usesClassParent(_object:Dynamic,_field:String,_write:Bool):Bool return false;
 GET_METHOD
}
class NightmareVisionPsychAudioGetterMain {
 static function check(ok:Bool,message:String):Void if (!ok) throw message;
 static function main():Void {
  var game=new FakeGame();
  var psych=new ProbeInterp();
  check(psych.get(game,'vocals')==game.vocals && psych.get(game,'audio')==game.audio,
   'Psych interpreter must read PlayState native audio properties');
  check(game.viewRequests==0,'Psych audio read must not request the Nightmare Vision view');

  var nightmare=new ProbeInterp({root:'selected-owner'});
  check(nightmare.get(game,'vocals')==game.view && nightmare.get(game,'audio')==game.view,
   "Nightmare Vision aliases must return the owner's PlayableSong view");
  check(game.viewRequests==2,'Nightmare Vision interpreter should request its view for both aliases');
 }
}'''


class NightmareVisionPsychAudioGetterTest(unittest.TestCase):
    def test_actual_getter_scopes_audio_alias_to_owner_paths_interpreters(self):
        source = (ROOT / "source/NightmareVisionScriptInterp.hx").read_text(encoding="utf-8")
        getter = extract_method(source, "override function get(object:Dynamic, field:String):Dynamic")
        self.assertIn("ownerPaths != null && (field == 'audio' || field == 'vocals')", getter)
        fixture = MAIN.replace("GET_METHOD", getter)
        with tempfile.TemporaryDirectory(prefix="psych-audio-getter-", dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            (work / "NightmareVisionPsychAudioGetterMain.hx").write_text(
                fixture, encoding="utf-8", newline="\n"
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-D", "flixel", "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "NightmareVisionPsychAudioGetterMain", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
