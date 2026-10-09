"""Execute NMV note-skin animation selection for suffixed and native names."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class NightmareVisionNoteAnimationMappingTest(unittest.TestCase):
    def test_direction_suffixes_select_lane_art_and_bare_names_still_work(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/NightmareVisionNoteSkin.hx").read_text()
        lane_index_start = source.index("static function laneIndex(")
        lane_index_end = source.index(";", lane_index_start) + 1
        methods = "\n".join((
            source[lane_index_start:lane_index_end],
            *(extract_method(source, marker) for marker in (
                "static function laneItems(",
                "static function noteAnimationKind(",
                "static function prefixExists(",
                "function diagnose(",
                "public function boolField(",
                "public function numberField(",
                "static function runtimeFieldName(",
                "function refreshRGB(",
                "public function applyNote(",
                "static function numberValue(",
            )),
        ))
        fixture = r'''
class FakeFrame { public var name:String; public function new(name:String) this.name=name; }
class FlxAtlasFrames { public var frames:Array<FakeFrame>; public function new(names:Array<String>) frames=[for(name in names)new FakeFrame(name)]; }
class NightmareVisionPaths { public var root:String="owner"; public function new() {} }
class PsychRGBPalette { public function new() {} public function copyValues(_other:PsychRGBPalette):Void {} }
class NightmareVisionRGBGraphics {
 public var enabled:Bool=false;
 public var palette:PsychRGBPalette;
 public function new(palette:PsychRGBPalette) this.palette=palette;
 public function apply(note:Note):Void {}
}
class FakeAnim {
 public var name:String;
 public function new(name:String) this.name=name;
}
class FakeAnimation {
 public var owner:Note;
 public var curAnim:FakeAnim;
 public var prefixes:Map<String,String>=new Map();
 public function new(owner:Note) this.owner=owner;
 public function addByPrefix(name:String,prefix:String,fps:Int,looping:Bool):Void {
  if(owner.frames==null)return;
  for(frame in owner.frames.frames) if(StringTools.startsWith(frame.name,prefix)) {
   prefixes.set(name,prefix);return;
  }
 }
 public function exists(name:String):Bool return prefixes.exists(name);
 public function play(name:String,restart:Bool=false):Void curAnim=exists(name)?new FakeAnim(name):null;
}
class FakeScale { public var x:Float=1; public var y:Float=1; public function new() {} public function set(x:Float,y:Float):Void {this.x=x;this.y=y;} }
class Note {
 public var nightmareVisionLegacyGeometry=false; public var nightmareVisionSustainInitialized=false; public var nightmareVisionSustainInitialWidth=0.;
 public var isSustainNote:Bool;
 public var animation:FakeAnimation;
 public var scale:FakeScale=new FakeScale();
 public var baseScale:FakeScale=new FakeScale();
 var storedFrames:FlxAtlasFrames;
 public var frames(get,set):FlxAtlasFrames;
 public var width:Float=100; public var height:Float=100;
 public var antialiasing:Bool=true; public var normalSize:Float=1; public var alpha:Float=1;
 public var nightmareVisionRGB:NightmareVisionRGBGraphics;
 public function new(sustain:Bool) { isSustainNote=sustain; animation=new FakeAnimation(this); animation.curAnim=new FakeAnim("PsychDefault"); }
 function get_frames():FlxAtlasFrames return storedFrames;
 function set_frames(value:FlxAtlasFrames):FlxAtlasFrames {
  storedFrames=value;
  if(animation!=null){animation.prefixes=new Map();animation.curAnim=null;}
  return value;
 }
 public function setGraphicSize(width:Int,height:Int=-1):Void this.width=width;
 public function resetPsychVisualOffset():Void {}
 public function updateHitbox():Void {}
 public function centerOffsets():Void {}
 public function centerOrigin():Void {}
}
class NightmareVisionNoteSkin {
 static function applyLegacyNoteAtlas(note:Note,frames:FlxAtlasFrames,aa:Bool):Void throw "historical branch entered in modern metadata test";
 public var data:Dynamic;
 public var paths:NightmareVisionPaths=new NightmareVisionPaths();
 public var name:String="ourple";
 public var reported:Map<String,Bool>=new Map();
 public var noteFrames:FlxAtlasFrames;
 public var noteAnims:Array<Array<Dynamic>>;
 public var noteTexture:String="";
 public var noteScale:Float=0.7;
 public var antialiasing:Bool=true;
 public var inEngineColoring:Bool=true;
 public function new(data:Dynamic) {
  this.data=data; noteAnims=cast Reflect.field(data,"noteAnimations");
  if(Reflect.field(data,"noteScale")!=null) noteScale=Reflect.field(data,"noteScale");
  if(Reflect.field(data,"antialiasing")!=null) antialiasing=Reflect.field(data,"antialiasing");
 }
 public function palette(lane:Int):PsychRGBPalette return new PsychRGBPalette();
 function refreshNoteFrames():FlxAtlasFrames return noteFrames;
''' + methods + r'''
}
class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var names=["purple","blue","green","red"];
  var rows:Array<Dynamic>=[];
  var sheetNames:Array<String>=[];
  for(i in 0...4) {
   rows.push([
    {anim:"scroll"+i,xmlName:names[i]},
    {anim:"hold"+i,xmlName:names[i]+" hold piece"},
    {anim:"holdend"+i,xmlName:i==0?"pruple end hold":names[i]+" hold end"}
   ]);
   sheetNames.push(names[i]+"0000");
   sheetNames.push(names[i]+" hold piece0000");
   sheetNames.push((i==0?"pruple end hold":names[i]+" hold end")+"0000");
  }
  var atlas=new FlxAtlasFrames(sheetNames);
  var skin=new NightmareVisionNoteSkin({noteAnimations:rows,noteScale:1,antialiasing:false,inGameColoring:false});
  for(lane in 0...4) {
   var head=new Note(false);
   check(skin.applyNote(head,lane,atlas),"suffixed scroll metadata rejected for lane "+lane);
   check(head.frames==atlas && head.animation.curAnim.name=="Scroll",
    "head did not select its custom atlas/Scroll animation for lane "+lane);
   check(head.animation.prefixes.get("Scroll")==names[lane]+"0",
    "head used another direction's frames for lane "+lane);

   var sustain=new Note(true);
   check(skin.applyNote(sustain,lane,atlas),"suffixed hold metadata rejected for lane "+lane);
   check(sustain.frames==atlas && sustain.animation.curAnim.name=="holdend",
    "sustain did not select its custom atlas/end animation for lane "+lane);
   check(sustain.animation.prefixes.get("hold")==names[lane]+" hold piece0"
    && sustain.animation.prefixes.get("holdend")==((lane==0?"pruple end hold":names[lane]+" hold end")+"0"),
    "sustain used another direction's frames for lane "+lane);
  }
  var wrapped=new Note(false);
  check(skin.applyNote(wrapped,5,atlas)
   && wrapped.animation.prefixes.get("Scroll")=="blue0",
   "lane-table wrapping did not keep its metadata direction suffix aligned");

  var bare=new NightmareVisionNoteSkin({noteAnimations:[[
   {anim:"scroll",xmlName:"legacy"},
   {anim:"hold",xmlName:"legacy hold"},
   {anim:"holdend",xmlName:"legacy end"}
  ]],noteScale:1,antialiasing:true,inGameColoring:false});
  var bareAtlas=new FlxAtlasFrames(["legacy0000","legacy hold0000","legacy end0000"]);
  check(bare.applyNote(new Note(false),3,bareAtlas),"bare native scroll name stopped working");
  check(bare.applyNote(new Note(true),3,bareAtlas),"bare native hold names stopped working");

  // Explicit note-type reloads follow source Note.reloadNote: a resolved
  // owner atlas replaces the current frames even when it only contains tap
  // art or a single authored special-note frame. Initial skin validation
  // remains strict so a missing default atlas still uses the native fallback.
  var iceAtlas=new FlxAtlasFrames(["blue0000","purple0000","red0000","green0000"]);
  var iceHead=new Note(false);
  check(skin.applyNote(iceHead,1,iceAtlas),"tap-only owner atlas reload was rejected");
  check(iceHead.frames==iceAtlas && iceHead.animation.curAnim!=null
   && iceHead.animation.curAnim.name=="Scroll",
   "Try Harder tap atlas did not replace the regular skin art");
  var iceSustain=new Note(true);
  check(skin.applyNote(iceSustain,1,iceAtlas),"owner atlas without hold frames was rejected");
  check(iceSustain.frames==iceAtlas && !iceSustain.animation.exists("hold")
   && !iceSustain.animation.exists("holdend"),
   "partial sustain atlas fell back to the unrelated regular note sheet");
  var accelerantAtlas=new FlxAtlasFrames(["BulletNote0000"]);
  var accelerant=new Note(false);
  check(skin.applyNote(accelerant,0,accelerantAtlas),"single-frame special atlas reload was rejected");
  check(accelerant.frames==accelerantAtlas && !accelerant.animation.exists("Scroll"),
   "Accelerant atlas was replaced by the default directional sheet after its custom prefix was absent");

  var mismatched=new NightmareVisionNoteSkin({noteAnimations:[[],[
   {anim:"scroll0",xmlName:"wrong"}
  ]],noteScale:1});
  var fallbackFrames=new FlxAtlasFrames(["psych-default0000"]);
  var fallback=new Note(false);
  fallback.frames=fallbackFrames;
  check(!mismatched.applyNote(fallback,1,atlas),"wrong direction suffix unexpectedly matched");
  check(fallback.frames==fallbackFrames,"failed source metadata replaced the Psych fallback frames");
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="nmv-note-animation-", dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
