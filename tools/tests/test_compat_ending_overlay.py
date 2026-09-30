"""A fallback ending must cover reordered gameplay cameras without destroying them."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.tests.test_codename_note_core import method

ROOT = Path(__file__).resolve().parents[2]


class CompatEndingOverlayTest(unittest.TestCase):
    def test_promotes_only_overlay_preserving_camera_selection_and_defaults(self):
        production = method((ROOT / 'source/PlayState.hx').read_text(), 'promoteCompatEndingOverlay')
        fixture = r'''
class Camera {public var destroyed=false;public function new() {}}
class Frontend {
 public var list:Array<Camera>=[];public var defaults:Array<Camera>=[];
 public var edits=0;
 public function new() {}
 public function add(camera:Camera,isDefault:Bool):Void {
  edits++;list.push(camera);if(isDefault)defaults.push(camera);FlxG.camera=camera;
 }
 public function remove(camera:Camera,destroy:Bool):Void {
  edits++;list.remove(camera);defaults.remove(camera);camera.destroyed=destroy;
 }
}
class FlxG {public static var cameras=new Frontend();public static var camera:Camera;}
class RuntimeSmokeHarness {
 public static function enabled():Bool return false;
 public static function markStep(value:String):Void {}
}
class Main {
 var camOther=new Camera();
 var defaultPsychGlobalScopes:Array<String>=[];
 var hscriptStates:Map<String,{variables:Map<String,Dynamic>}>=[];
 var songScore=0;var misses=0;var combo=0;var accuracy:Float=0;var storyDifficultyText='hard';
 public function new() {}
''' + production + r'''
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 function run():Void {
  var game=new Camera(),hud=new Camera(),source=new Camera();
  FlxG.cameras.list=[game,camOther,source,hud];
  FlxG.cameras.defaults=[game,source];FlxG.camera=source;
  promoteCompatEndingOverlay();
  check(FlxG.cameras.list[0]==game&&FlxG.cameras.list[1]==source
   &&FlxG.cameras.list[2]==hud&&FlxG.cameras.list[3]==camOther,'scene order changed');
  check(!camOther.destroyed&&FlxG.camera==source,'destroyed or changed main');
  check(FlxG.cameras.defaults.length==2&&!FlxG.cameras.defaults.contains(camOther),'defaults changed');
  var edits=FlxG.cameras.edits;promoteCompatEndingOverlay();
  check(FlxG.cameras.edits==edits,'already top camera was detached again');
  FlxG.cameras.list=[game,camOther,hud];FlxG.cameras.defaults=[game,camOther];
  promoteCompatEndingOverlay();
  check(FlxG.cameras.defaults.contains(camOther),'existing default target lost');
  FlxG.cameras.list=[game,hud];FlxG.cameras.defaults=[game];
  promoteCompatEndingOverlay();check(FlxG.cameras.list[2]==camOther,'detached overlay not restored');
 }
 static function main():Void new Main().run();
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            path = Path(folder)
            (path / 'Main.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(path), '--run', 'Main'],
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


    def test_fallback_results_observe_source_scoring_and_can_write_presentation(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        helpers = method(source, 'compatSetResultsProperty') + method(source, 'compatPropertySeparator')
        fixture = r"""
class Main {
 var combo=27;var writes:Array<String>=[];
 public function new() {}
 function compatSetProperty(path:Dynamic,value:Dynamic):Void {
  writes.push(path);if(path=='combo')combo=value;
 }
""" + helpers + r"""
 function run():Void {
  for(path in ['combo','songScore','songMisses','misses','sicks','ratingPercent','accuracy'])
   compatSetResultsProperty(path,0);
  if(combo!=27||writes.length!=0)throw 'fallback presentation changed source scoring';
  compatSetResultsProperty('scoreTxt.text','source results');
  compatSetResultsProperty('overlay.alpha',1);
  if(writes.join(',')!='scoreTxt.text,overlay.alpha')throw 'presentation properties blocked';
  compatSetProperty('combo',0);
  if(combo!=0)throw 'selected script lost writable API';
 }
 static function main():Void new Main().run();
}"""
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            path = Path(folder)
            (path / 'Main.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                                     '-cp', str(path), '--run', 'Main'],
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
