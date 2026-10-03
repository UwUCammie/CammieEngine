"""Offscreen probes for the smoke-only native visual binding snapshots."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class RuntimeSmokeVisualsTest(unittest.TestCase):
    def test_actual_graphic_and_registered_animation_state_are_reported(self):
        main = r'''
class FakeAnimation {
  public var name:String;
  public var frames:Array<Int>;
  public var looped:Bool;
  public var frameRate:Float;
  public var curFrame:Int = 2;
  public var finished:Bool = false;
  public function new(name:String, frames:Array<Int>, looped:Bool) {
    this.name = name; this.frames = frames; this.looped = looped; frameRate = 24;
  }
}
class FakeController {
  public var curAnim:FakeAnimation;
  var entries:Map<String, FakeAnimation> = new Map();
  public function new() {
    entries.set("Scroll", new FakeAnimation("Scroll", [0, 1, 2], true));
    entries.set("danceLeft", new FakeAnimation("danceLeft", [7, 8], false));
    entries.set("danceRight", new FakeAnimation("danceRight", [9, 10, 11], true));
    entries.set("singLEFT", new FakeAnimation("singLEFT", [12], false));
    curAnim = entries.get("danceRight");
  }
  public function getByName(name:String):FakeAnimation return entries.get(name);
  public function getNameList():Array<String> return ["singLEFT", "danceRight", "Scroll", "danceLeft"];
}
class FakePoint {
  public static var released:Int = 0;
  public var x:Float;
  public var y:Float;
  public function new(x:Float, y:Float) { this.x = x; this.y = y; }
  public function put():Void released++;
}
class FakeSprite {
  public var animation = new FakeController();
  public var graphic = {key: "selected-root/NOTE_death.png"};
  public var frames = {frames: [0, 1, 2, 3]};
  public var blend = 0;
  public var shader = {fragmentPath:"owned/shaders/fog.frag"};
  public var sourceKind = "danger";
  public var coolId = "vslice:danger:0";
  public var trueNoteData = 40;
  public var noteData = 0;
  public var customNotePath = "selected-root/NOTE_death";
  public var isPixel = false;
  public var x = 300.0;
  public var y = 200.0;
  public var width = 444.5;
	public var height = 630.0;
	public var scrollFactor = {x:1.0, y:1.0};
	public var camera = {width:1280, height:720, zoom:1.0, scroll:{x:0.0, y:0.0}};
  public var frameWidth = 500.0;
  public var frameHeight = 600.0;
  public var isSustainNote = true;
  public var frame = {offset: {x: 4.0, y: 9.0}};
  public var origin = {x: 317.5, y: 45.0};
  public var scale = {x: 0.7, y: 1.05};
  public var offset = {x: 261.5, y: 90.0};
  public var playerOffsetX = 2;
  public var playerOffsetY = -5;
  public var requestedCharacter = "actor";
  public var resolvedCharacter = "actor";
  public var imageFile = "selected-root/actor";
  public var isPlayer = true;
  public var flipX = false;
  public var flipY = false;
  public var stageBaseFlipX = false;
  public function new() {}
  public function getCurrentAnimationOffset(index:Int):Float return index == 0 ? 3 : -4;
  public function hxcBaseScreenPosition(_result:Dynamic, _camera:Dynamic):FakePoint
    return new FakePoint(290, 205);
  public function getScreenPosition(_result:Dynamic, _camera:Dynamic):FakePoint
    return new FakePoint(280, 210);
}
class Main {
  static function fail(message:String):Void throw message;
  static function main() {
    var sprite = new FakeSprite();
    var note:Dynamic = RuntimeSmokeVisuals.note(sprite, 112);
    if (note.sourceKind != "danger" || note.customNotePath != "selected-root/NOTE_death"
      || note.graphicKey != "selected-root/NOTE_death.png"
      || note.atlasFrames != 4 || note.scrollFrames != 3
      || note.currentAnimation != "danceRight" || note.currentFrame != 2
      || note.isSustainNote != true || note.width != 444.5 || note.frameWidth != 500
      || note.originX != 317.5 || note.scaleX != 0.7 || note.scaleY != 1.05
      || Math.abs(note.renderCenterX - 308.75) > 0.00001
      || Math.abs(note.centerErrorX - (-47.25)) > 0.00001 || note.offsetY != 90)
      fail("note snapshot did not read actual native binding");
    var actor:Dynamic = RuntimeSmokeVisuals.character("girlfriend", sprite);
	var stage:Dynamic = RuntimeSmokeVisuals.stage({members:[sprite]});
	var prop:Dynamic = stage.members[0];
	if (stage.memberCount != 1 || prop.width != 444.5 || prop.height != 630
	  || prop.scaleX != 0.7 || prop.offsetX != 261.5 || prop.scrollFactorX != 1
	  || prop.cameraWidth != 1280 || prop.cameraHeight != 720
	  || prop.cameraZoom != 1 || prop.cameraScrollX != 0 || prop.cameraScrollY != 0
      || prop.blend != 0 || prop.shader != "owned/shaders/fog.frag")
	  fail("stage overlay geometry or camera routing snapshot missing");
    if (actor.role != "girlfriend" || actor.graphicKey != "selected-root/NOTE_death.png"
      || actor.isPlayer != true || actor.flipX != false || actor.stageBaseFlipX != false
      || actor.currentAnimation != "danceRight" || actor.currentLength != 3
      || actor.currentLooped != true || actor.currentFinished != false
      || actor.dance.length != 2)
      fail("character snapshot missed current or registered animation state");
    if (actor.dance[0].name != "danceLeft" || actor.dance[0].frames != 2
      || actor.dance[0].looped != false
      || actor.dance[1].name != "danceRight" || actor.dance[1].frames != 3
      || actor.dance[1].looped != true)
      fail("registered dance animation lengths or loop flags");
    var geometry:Dynamic = actor.geometry;
    if (geometry.x != 300 || geometry.y != 200 || geometry.scaleY != 1.05
      || geometry.frameWidth != 500 || geometry.frameHeight != 600
      || geometry.frameTrimX != 4 || geometry.frameTrimY != 9
      || geometry.animationOffsetX != 3 || geometry.animationOffsetY != -4
      || geometry.globalOffsetX != 2 || geometry.globalOffsetY != -5
      || geometry.baseScreenX != 290 || geometry.baseScreenY != 205
      || geometry.screenX != 280 || geometry.screenY != 210
      || geometry.drawX != 18.5 || geometry.drawY != 120
      || FakePoint.released != 2)
      fail("character geometry or pooled point release missing");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_smoke_hooks_are_one_shot_and_gated(self):
        harness = (ROOT / "source/RuntimeSmokeHarness.hx").read_text()
        state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("if (!enabled() || finished || note == null || !note.dontEdit", harness)
        self.assertIn("visualNoteKinds.exists(key)", harness)
        self.assertIn("emit('custom_note_visual', RuntimeSmokeVisuals.note(note, Note.swagWidth))", harness)
        self.assertIn("emit('character_visual', RuntimeSmokeVisuals.character('girlfriend'", harness)
        self.assertIn("geometry: RuntimeSmokeVisuals.characterGeometry(actor)", harness)
        self.assertIn("RuntimeSmokeHarness.markCustomNoteVisual(swagNote)", state)
        self.assertIn("liveVisualNoteKinds.exists(key)", harness)
        self.assertIn("emit('live_custom_note_visual', snapshot)", harness)
        self.assertIn("Math.abs(note.y - receptor.y) > Note.swagWidth * 4", harness)
        self.assertIn("RuntimeSmokeHarness.markLiveCustomNoteVisual(daNote,", state)


if __name__ == "__main__":
    unittest.main()
