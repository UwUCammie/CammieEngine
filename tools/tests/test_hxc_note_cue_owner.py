"""Execute the native text-cue owner with separate hit and miss rule sets."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NoteCueOwnerTest(unittest.TestCase):
    def test_hit_and_miss_use_separate_rules_and_share_active_owner(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\tpublic function hxcTriggerNoteTextCue(")
        end = source.index("\n\t/** Remove the active display object", start)
        methods = source[start:end]
        fixture = r'''
class FlxText {
 public var bold:Bool; public var text:String;
 public function new(x:Float, y:Float, width:Float, text:String, size:Int) { this.text = text; }
 public function setFormat(font:String, size:Int, color:Int):Void {}
}
class FlxSprite { public var alpha:Float = 0; public function new() {} }
class RandomStub {
 public function new() {}
 public function bool(chance:Float):Bool return chance > 0;
 public function int(min:Int, max:Int):Int return min;
 public function float(min:Float, max:Float):Float return min;
}
class SoundStub { public function new() {} public function play(sound:Dynamic):Void {} }
class FlxG {
 public static var random = new RandomStub(); public static var sound = new SoundStub();
}
class FNFAssets { public static function getSound(path:String):Dynamic return path; }
class HxcStateAssetScope {
 public static function scopedAssetPath(root:String, path:String):String return root + '/' + path;
}
class HxcCompatRuntime { public static function setZIndex(text:Dynamic, z:Int):Void {} }
class RuntimeSmokeHarness {
 public static var marks:Array<String> = [];
 public static function markStep(value:String):Void marks.push(value);
}
class CueOwnerFixture {
 var SONG:Dynamic = {song:'fixture'};
 var dad:Dynamic = {x:10.0, y:20.0};
 var hxcNoteTextCues:Array<Dynamic> = [];
 var curStep:Int = 20;
 var rendered:Array<FlxText> = [];
 function new() {}
 function add(text:FlxText):Void rendered.push(text);
 function refresh():Void {}
 function hxcNoteTextFont(root:String, font:String):String return font;
''' + methods + r'''
 static function main() {
  var owner = new CueOwnerFixture();
  var spec:Dynamic = {
   triggerJudgement:'perfect', rules:[{songId:'fixture',chancePercent:100,lines:['HIT']}],
   missRules:[{songId:'fixture',chancePercent:100,lines:['MISS']}],
   xOffsetMin:0, xOffsetMax:0, yOffsetMin:0, yOffsetMax:0,
   font:'test.ttf', fontSize:20, color:0, bold:false, zIndex:1
  };
  var cue:Dynamic = {root:'fixture-root',spec:spec,active:false,startStep:-1,overlay:null,text:null};
  owner.hxcNoteTextCues.push(cue);
  if (owner.hxcTriggerNoteTextCue(cue, {judgement:'bad'})) throw 'bad hit triggered cue';
  if (owner.hxcTriggerNoteTextCue(cue, {judgement:'sick'})) throw 'scored player sick triggered bot perfect cue';
  if (!owner.hxcTriggerNoteTextCue(cue, {judgement:'perfect'})
   || owner.rendered[0].text != 'HIT' || cue.startStep != 20) throw 'hit rules failed';
  if (owner.hxcTriggerNoteTextCue(cue, {judgement:'perfect'}) || owner.rendered.length != 1)
   throw 'active cue must not stack a second text or static trigger';
  if (owner.hxcTriggerMissNoteTextCue(cue, {})) throw 'miss bypassed active owner';
  cue.active = false;
  if (!owner.hxcTriggerMissNoteTextCue(cue, {}) || owner.rendered[1].text != 'MISS')
   throw 'miss required hit judgement or used hit lines';
  if (RuntimeSmokeHarness.marks.indexOf('hxc-note-miss-text-cue-active') < 0)
   throw 'miss route not observable';
  cue.active = false; spec.missRules[0].chancePercent = 0;
  if (owner.hxcTriggerMissNoteTextCue(cue, {})) throw 'zero chance ignored';
  spec.missRules[0].chancePercent = 100; owner.SONG.song = 'other';
  if (owner.hxcTriggerMissNoteTextCue(cue, {})) throw 'miss escaped song rules';
  owner.SONG.song = 'fixture'; spec.missRules = null;
  if (owner.hxcTriggerMissNoteTextCue(cue, {})) throw 'missing miss rules borrowed hit rules';
  owner.hxcNoteTextCues = [];
  if (owner.hxcTriggerNoteTextCue(cue, {judgement:'perfect'})) throw 'foreign handle accepted';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "CueOwnerFixture.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "CueOwnerFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
