"""Exercise owner-scoped HScript video completion with a synthetic event."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class CodenameVideoEndCallbackTest(unittest.TestCase):
    def test_hscript_end_callback_restores_hidden_game_camera(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(r'''import hscript.Interp;

class FakeSignal {
 public var callback:Dynamic;
 public var addCalls:Int = 0;
 public function new() {}
 public function add(listener:Dynamic):Void { callback = listener; addCalls++; }
 public function dispatch():Void if (callback != null) Reflect.callMethod(null, callback, []);
}
class FakeVideoBitmap {
 public var onEndReached:FakeSignal = new FakeSignal();
 public function new() {}
}
class FakeVideoSprite {
 public var bitmap:FakeVideoBitmap = new FakeVideoBitmap();
 public var cameras:Array<Dynamic> = [];
 public var visible:Bool = true;
 public var destroyed:Bool = false;
 public var playing:Bool = false;
 public var loadedPath:String = '';
 public function new() {}
 public function load(path:String):Bool { loadedPath = path; return true; }
 public function play():Void playing = true;
 public function destroy():Void destroyed = true;
}
class FakeCamera {
 public var visible:Bool = true;
 public function new() {}
 public function flash(_color:Int, _duration:Float):Void {}
}
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var source = 'var intro;\n'
   + 'function getIntro() return intro;\n'
   + 'function create() { intro = new FlxVideoSprite(); '
   + 'intro.load(Assets.getPath(Paths.video("intro"))); }\n'
   + 'function postCreate() { FlxG.camera.visible = false; camHUD.alpha = 0.001; }\n'
   + 'function onSongStart() { intro.play(); intro.cameras = [camHuggy]; '
   + 'intro.bitmap.onEndReached.add(() -> { intro.visible = false; intro.destroy(); '
   + 'if (Options.flashingMenu) camHuggy.flash(0xFFFFFFFF, 2); '
   + 'FlxG.camera.visible = true; }); }';
  var allowed:Map<String, Dynamic> = new Map();
  var prepared = CodenameScriptParser.prepare(source, allowed, 'generic-video-callback');
  check(prepared.program != null && prepared.diagnostics.length == 0,
   prepared.diagnostics.length == 0 ? 'no HScript program' : prepared.diagnostics[0].message);

  var gameCamera = new FakeCamera();
  var overlayCamera = new FakeCamera();
  var hud:Dynamic = {alpha: 1.0};
  var interp = new Interp();
  interp.variables.set('FlxVideoSprite', FakeVideoSprite);
  interp.variables.set('FlxG', {camera:gameCamera});
  interp.variables.set('camHUD', hud);
  interp.variables.set('camHuggy', overlayCamera);
  interp.variables.set('Options', {flashingMenu:false});
  interp.variables.set('Paths', {video:function(key:String):String return 'selected-owner/videos/' + key + '.mp4'});
  interp.variables.set('Assets', {getPath:function(path:String):String return path});
  interp.execute(prepared.program);

  var create:Dynamic = interp.variables.get('create');
  var postCreate:Dynamic = interp.variables.get('postCreate');
  var onSongStart:Dynamic = interp.variables.get('onSongStart');
  create();
  postCreate();
  onSongStart();
  var getIntro:Dynamic = interp.variables.get('getIntro');
  var intro:FakeVideoSprite = cast getIntro();
  check(intro != null && intro.loadedPath == 'selected-owner/videos/intro.mp4' && intro.playing,
   'video must load through the selected owner and start before completion');
  check(!gameCamera.visible && hud.alpha == 0.001 && intro.bitmap.onEndReached.addCalls == 1,
   'pre-end state must keep the gameplay camera hidden and register one completion listener');

  hud.alpha = 1;
  check(!gameCamera.visible && hud.alpha == 1,
   'HUD can become visible before the intro video finishes');
  intro.bitmap.onEndReached.dispatch();
  check(gameCamera.visible && !intro.visible && intro.destroyed,
   'video completion callback must hide and destroy the intro before restoring gameplay camera');
 }
}''')
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib" / "hscript" / "2,5,0"),
                 "-cp", str(ROOT / ".haxelib" / "hscript-ex" / "git" / "src"),
                 "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
