"""Exercise Codename's optional stage camera axes during load and replacement."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_difficulty_visual_fallback import extract_method

ROOT = Path(__file__).resolve().parents[2]


class CodenameStageStartCameraTest(unittest.TestCase):
    def test_stage_load_and_swap_apply_selected_camera_axes(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        method = extract_method(source, "function applyCodenameStageStartCamera(")
        opening = source[source.index("var beforeStageCameraX ="):source.index("//add(curStage);")]
        swap = source[source.index("public function swapStage("):source.index("var startTimer:FlxTimer;", source.index("public function swapStage("))]
        self.assertLess(opening.index("setAllHaxeVar('stage', curStage);"),
                        opening.index("applyCodenameStageStartCamera();"))
        self.assertLess(opening.index("applyCodenameStageStartCamera();"),
                        opening.index("initializeCodenameActors();"))
        self.assertLess(swap.index("setAllHaxeVar('stage', curStage);"),
                        swap.index("applyCodenameStageStartCamera();"))
        self.assertLess(swap.index("applyCodenameStageStartCamera();"),
                        swap.index("reapplyCodenameActors();"))
        fixture = '''import CodenameStagePlacement.CodenameStagePlacementData;
class Camera { public var x:Float; public var y:Float;
 public function new(x:Float,y:Float) { this.x=x;this.y=y; } }
class Stage { public var placement:CodenameStagePlacementData;
 public function new(value:CodenameStagePlacementData) placement=value;
 public function getCodenamePlacement():CodenameStagePlacementData return placement; }
class Main {
 var curStage:Stage;
 var camFollow:Camera = new Camera(11,22);
 public function new() {}
''' + method + '''
 function run() {
  curStage=new Stage(CodenameStagePlacement.parse('<stage startCamPosX="0"/>'));
  applyCodenameStageStartCamera();
  if(camFollow.x!=0 || camFollow.y!=22) throw 'opening X and absent Y';
  curStage=new Stage(CodenameStagePlacement.parse('<stage startCamPosY="275"/>'));
  applyCodenameStageStartCamera();
  if(camFollow.x!=0 || camFollow.y!=275) throw 'replacement Y and absent X';
  curStage=new Stage(CodenameStagePlacement.parse('<stage startCamPosX="900"/>',true));
  applyCodenameStageStartCamera();
  if(camFollow.x!=900 || camFollow.y!=275) throw 'stage script suppressed independent camera axis';
  curStage=null; applyCodenameStageStartCamera();
  camFollow=null; applyCodenameStageStartCamera();
 }
 static function main() new Main().run();
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", folder, "--run", "Main"], cwd=ROOT, text=True,
                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
