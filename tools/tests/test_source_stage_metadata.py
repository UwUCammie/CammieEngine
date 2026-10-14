"""Stage file fields shared by Psych and Nightmare Vision: one parser, one apply path."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method

ROOT = Path(__file__).resolve().parents[2]

PARSE_MAIN = r'''
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function same(a:Null<Array<Float>>, b:Null<Array<Float>>):Bool
  return a == null ? b == null : b != null && a[0] == b[0] && a[1] == b[1];
 static function main():Void {
  var template = SourceStageMetadata.parse({defaultZoom:0.8, boyfriend:[500, 100], girlfriend:[0, 100],
   opponent:[-500, 100], camera_speed:1});

  // Psych keeps the engine's own position for anything missing or broken.
  var broken:Dynamic = {boyfriend:(['x', 3]:Array<Dynamic>), opponent:[7], defaultZoom:-1, camera_speed:'fast'};
  var psych = SourceStageMetadata.parse(broken);
  check(psych.boyfriend == null && psych.opponent == null && psych.girlfriend == null, 'Psych invented a point');
  check(psych.defaultZoom == null && psych.cameraSpeed == null, 'bad numbers must be ignored');
  // NV falls back to its template instead.
  var nv = SourceStageMetadata.parse(broken, template);
  check(same(nv.boyfriend, [500, 100]) && same(nv.opponent, [-500, 100]) && same(nv.girlfriend, [0, 100]), 'NV template points');
  check(nv.defaultZoom == 0.8 && nv.cameraSpeed == 1, 'NV template numbers');
  nv.boyfriend[0] = 1;
  check(template.boyfriend[0] == 500, 'fallback points must be copies');

  for (zoom in ([0, Math.NaN, Math.POSITIVE_INFINITY, 'nope']:Array<Dynamic>))
   check(SourceStageMetadata.parse({defaultZoom:zoom}).defaultZoom == null, 'zoom ' + zoom + ' was accepted');
  check(SourceStageMetadata.parse({defaultZoom:'0.75'}).defaultZoom == 0.75, 'numeric text zoom');
  check(SourceStageMetadata.parse({camera_speed:0}).cameraSpeed == 0, 'a 0 camera speed locks the camera and is valid');

  var empty = SourceStageMetadata.parse({});
  check(same(empty.cameraBoyfriend, [0, 0]) && same(empty.cameraOpponent, [0, 0]) && same(empty.cameraGirlfriend, [0, 0]), 'camera offsets default to 0,0');
  check(!empty.hideGirlfriend && empty.stageUI == null && empty.objects == null && empty.preload == null, 'empty file has no opinions');

  check(SourceStageMetadata.parse({hide_girlfriend:true}).hideGirlfriend, 'hide_girlfriend');
  check(SourceStageMetadata.parse({isPixelStage:true}).stageUI == 'pixel', 'isPixelStage is the old spelling of pixel');
  check(SourceStageMetadata.parse({isPixelStage:false}).stageUI == null, 'isPixelStage false leaves the chart UI alone');
  check(SourceStageMetadata.parse({stageUI:' custom-pixel ', isPixelStage:false}).stageUI == 'custom-pixel', 'stageUI wins');
  check(SourceStageMetadata.parse({stageUI:'', isPixelStage:true}).stageUI == 'pixel', 'empty stageUI falls through');
  check(SourceStageMetadata.parse({objects:[]}).objects == null, 'an empty objects list builds nothing');
  check(SourceStageMetadata.parse({objects:[{type:'square'}]}).objects.length == 1, 'objects kept');

  // A complete file reads the same through both engines.
  var full:Dynamic = {directory:'week1', defaultZoom:0.9, boyfriend:[770, 100], girlfriend:[400, 130], opponent:[100, 100],
   hide_girlfriend:false, camera_boyfriend:[1, 2], camera_opponent:[3, 4], camera_girlfriend:[5, 6], camera_speed:1.5, stageUI:'pixel'};
  var a = SourceStageMetadata.parse(full);
  var b = SourceStageMetadata.parse(full, template);
  check(same(a.boyfriend, b.boyfriend) && same(a.opponent, b.opponent) && same(a.girlfriend, b.girlfriend)
   && same(a.cameraBoyfriend, b.cameraBoyfriend) && same(a.cameraOpponent, b.cameraOpponent) && same(a.cameraGirlfriend, b.cameraGirlfriend)
   && a.defaultZoom == b.defaultZoom && a.cameraSpeed == b.cameraSpeed && a.stageUI == b.stageUI
   && a.directory == b.directory && a.hideGirlfriend == b.hideGirlfriend, 'profiles disagree on a complete file');
 }
}
'''

APPLY_MAIN = r'''
class Info { public var x:Float = 0; public var y:Float = 0; public function new() {} }
class Stage {
 public var defaultZoom:Float = 1.05; public var bf = new Info(); public var dad = new Info(); public var gf = new Info();
 public function new() {}
 public function getInfo(role:String):Info return role == 'bf' ? bf : role == 'gf' ? gf : dad;
}
class Point { public var x:Float; public var y:Float; public function new(x:Float, y:Float) {this.x = x; this.y = y;} public function set(x:Float, y:Float) {this.x = x; this.y = y;} }
class NightmareVisionStageData {
 public static function getTemplateStageFile():Dynamic return {defaultZoom:0.8, boyfriend:[500, 100], girlfriend:[0, 100], opponent:[-500, 100], camera_speed:1};
}
class Host {
 public var curStage = new Stage(); public var defaultCamZoom:Float = 1.05; public var cameraSpeed:Float = 1;
 public static var stageUI:String = 'normal'; public var snapped:Array<Float> = []; public var pixelUI:Bool = false;
 static function stageUIIsPixel(value:String):Bool return value != null && (value == 'pixel' || StringTools.endsWith(value, '-pixel'));
 public var boyfriendPosition = new Point(770, 100); public var dadPosition = new Point(100, 100); public var gfPosition = new Point(400, 130);
 public var psychStageCameraBoyfriend:Array<Float> = [9, 9]; public var psychStageCameraOpponent:Array<Float> = [9, 9]; public var psychStageCameraGirlfriend:Array<Float> = [9, 9];
 public function new() {}
 function setGameCameraZoom(value:Float):Void snapped.push(value);
 __METHODS__
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var psych = new Host();
  psych.applySourceStageMetadata(SourceStageMetadata.parse({defaultZoom:0.7, camera_speed:2.5, stageUI:'pixel', boyfriend:[10, 20],
   camera_opponent:[3, 4]}), SourceStageMetadata.PSYCH);
  check(psych.cameraSpeed == 2.5, 'camera_speed did not reach cameraSpeed');
  // Notes and receptors were built from the chart's UI before the stage file
  // is read, so a late pixel flip would mix the two looks.
  check(stageUI == 'normal', 'a stage file flipped pixel mode after the notes were built');
  var pixelChart = new Host();
  pixelChart.pixelUI = true;
  pixelChart.applySourceStageMetadata(SourceStageMetadata.parse({stageUI:'custom-pixel'}), SourceStageMetadata.PSYCH);
  check(stageUI == 'custom-pixel', 'a stage UI name that agrees on pixel mode is kept for scripts');
  pixelChart.applySourceStageMetadata(SourceStageMetadata.parse({stageUI:'normal'}), SourceStageMetadata.PSYCH);
  check(stageUI == 'custom-pixel', 'a stage file turned pixel mode off after the notes were built');
  stageUI = 'normal';
  var named = new Host();
  named.applySourceStageMetadata(SourceStageMetadata.parse({stageUI:'custom'}), SourceStageMetadata.PSYCH);
  check(stageUI == 'custom', 'a non-pixel stage UI name is kept for scripts');
  check(psych.defaultCamZoom == 0.7 && psych.curStage.defaultZoom == 0.7 && psych.snapped.join(',') == '0.7', 'zoom snap');
  check(psych.curStage.bf.x == 10 && psych.curStage.bf.y == 20 && psych.curStage.dad.x == 0, 'anchors');
  check(psych.boyfriendPosition.x == 770, 'Psych has no role-group positions to move');
  check(psych.psychStageCameraOpponent[0] == 3 && psych.psychStageCameraBoyfriend[0] == 0, 'camera offsets replaced as a set');

  // A file that says nothing about speed, UI or zoom leaves them alone.
  stageUI = 'normal';
  var quiet = new Host();
  quiet.cameraSpeed = 3;
  quiet.applySourceStageMetadata(SourceStageMetadata.parse({isPixelStage:false}), SourceStageMetadata.PSYCH);
  check(quiet.cameraSpeed == 3 && stageUI == 'normal' && quiet.defaultCamZoom == 1.05 && quiet.snapped.length == 0, 'absent fields changed state');

  var nv = new Host();
  nv.applySourceStageMetadata(nv.nightmareVisionStageMetadata({camera_speed:2, stageUI:'pixel'}), SourceStageMetadata.NIGHTMARE_VISION_CREATE);
  check(nv.cameraSpeed == 2 && stageUI == 'normal', 'NV reads camera_speed but has no stage UI');
  check(nv.boyfriendPosition.x == 500 && nv.dadPosition.x == -500 && nv.gfPosition.x == 0 && nv.curStage.gf.y == 100, 'NV template positions');
  check(nv.defaultCamZoom == 0.8 && nv.snapped.join(',') == '0.8', 'NV create snaps to the stage zoom');

  var swap = new Host();
  swap.cameraSpeed = 4;
  swap.applySourceStageMetadata(swap.nightmareVisionStageMetadata({defaultZoom:1.2, camera_speed:2, boyfriend:[1, 2]}), SourceStageMetadata.NIGHTMARE_VISION_SWAP);
  check(swap.cameraSpeed == 4 && swap.snapped.length == 0 && swap.defaultCamZoom == 1.2, 'NV swap keeps speed and eases the zoom');
  check(swap.boyfriendPosition.x == 1 && swap.boyfriendPosition.y == 2, 'NV swap moves the role groups');
 }
}
'''


class SourceStageMetadataTest(unittest.TestCase):
    def run_fixture(self, main: str, main_class: str):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = FixturePath(folder)
            (work / (main_class + '.hx')).write_text(main, newline='\n')
            (work / 'SourceStageMetadata.hx').write_text(
                (ROOT / 'source/SourceStageMetadata.hx').read_text(encoding='utf-8'), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', main_class, '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_parser_validates_once_and_falls_back_per_engine(self):
        self.run_fixture(PARSE_MAIN, 'Main')

    def test_shared_apply_honours_each_engine_profile(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        methods = '\n'.join(extract_method(play, '\tfunction ' + name) for name in (
            'applySourceStageMetadata(', 'nightmareVisionStageMetadata(', 'rememberStageAnchor(', 'applyStageCameraOffsets('))
        methods = methods.replace('\tfunction ', '\tpublic function ')
        self.run_fixture(APPLY_MAIN.replace('__METHODS__', methods), 'Host')

    def test_psych_and_both_nightmare_vision_entry_points_use_the_shared_apply(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        psych = extract_method(play, 'function applyPsychStageJson(')
        self.assertIn('SourceStageMetadata.parse(data)', psych)
        self.assertIn('applySourceStageMetadata(meta, SourceStageMetadata.PSYCH);', psych)
        self.assertNotIn("Reflect.field(data, 'defaultZoom')", psych)
        nv_init = extract_method(play, 'function initializeNightmareVisionScripts(')
        self.assertIn('SourceStageMetadata.NIGHTMARE_VISION_CREATE', nv_init)
        self.assertNotIn('data.defaultZoom', nv_init)
        swap = extract_method(play, 'function swapNightmareVisionStage(')
        self.assertIn('SourceStageMetadata.NIGHTMARE_VISION_SWAP', swap)
        self.assertNotIn('boyfriendPosition.set(data.boyfriend', swap)
        groups = extract_method(play, 'function initializeNightmareVisionCharacterGroups(')
        self.assertNotIn('data.boyfriend[0]', groups)


if __name__ == '__main__':
    unittest.main()
