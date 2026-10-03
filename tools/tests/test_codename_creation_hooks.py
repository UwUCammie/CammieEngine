"""Exercise Codename note/receptor creation mutations and frame ownership."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def method(source: str, name: str) -> str:
    match = re.search(r"(?:override public |public )?function " + re.escape(name) + r"\(", source)
    if match is None:
        raise AssertionError(name)
    start = match.start()
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unclosed method {name}")


class CodenameCreationHooksTest(unittest.TestCase):
    def test_mutable_events_install_atlas_metadata_and_frame_offsets(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        note_source = (ROOT / "source/Note.hx").read_text()
        strum_source = (ROOT / "source/Strumline.hx").read_text()
        self.assertIn("@:keep public var frameOffset(get, set):FlxPoint;", note_source)
        self.assertIn("@:keep public var splash:String = 'default';", note_source)
        self.assertIn("codenameFrameOffsetOwned", note_source)
        self.assertIn("noteTypeID = PlayState.instance.codenameNoteTypeIndex(sourceKind)", note_source)
        self.assertIn("new StrumNote(Note.swagWidth * i, 0, i, type, currentKey, this)", strum_source)
        self.assertIn("&& (codenameOwnerActive", note_source)
        self.assertIn("codenameDefaultNoteAtlasFrames()", note_source)
        self.assertLess(note_source.index("prepareCodenameNoteCreation(this)"),
                        note_source.index("var initialCodenameScale"))
        self.assertIn("&& (codenameOwnerActive", strum_source)
        self.assertIn("codenameDefaultNoteAtlasFrames()", strum_source)
        state_source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("codenameDefaultNoteAtlasResolved.exists(root)", state_source)
        self.assertIn("codenameDefaultNoteAtlasResolved.set(root, true)", state_source)

        note_hook = note_source.index("dispatchCodenameCreationCallback('onNoteCreation'")
        note_atlas = note_source.index("new CodenamePaths(PlayState.instance.codenameCreationOwnerRoot())", note_hook)
        note_apply = note_source.index("CodenameCreationVisual.applyNoteAtlas", note_atlas)
        note_post = note_source.index("dispatchCodenameCreationCallback('onPostNoteCreation'", note_apply)
        self.assertLess(note_hook, note_atlas)
        self.assertLess(note_atlas, note_apply)
        self.assertLess(note_apply, note_post)
        self.assertIn("if (codenameVisualWasCancelled)", note_source[note_apply:note_post])
        parent_line = strum_source.index("this.parentLine = parentLine;")
        strum_hook = strum_source.index("dispatchCodenameCreationCallback('onStrumCreation'")
        strum_atlas = strum_source.index(".getFrames(selectedAtlasPath)", strum_hook)
        self.assertLess(parent_line, strum_hook)
        self.assertLess(strum_hook, strum_atlas)

        helper = (ROOT / "source/CodenameCreationVisual.hx").read_text()
        event = (ROOT / "source/CodenameNoteCreationEvent.hx").read_text()
        get_offset = method(note_source, "get_frameOffset")
        set_offset = method(note_source, "set_frameOffset")
        destroy = method(note_source, "destroy")

        stubs = {
            "animate/FlxAnimateFrames.hx": r'''package animate;
class FlxAnimateFrames extends flixel.graphics.frames.FlxFramesCollection {
 public function new(key:String,prefixes:Array<String>,trimData:String) super(key,prefixes,trimData);
}''',
            "flixel/graphics/frames/FlxFramesCollection.hx": r'''package flixel.graphics.frames;
class FlxFramesCollection {
 public var key:String;
 public var prefixes:Array<String>;
 public var trimData:String;
 public function new(key:String,prefixes:Array<String>,trimData:String) {
  this.key=key;this.prefixes=prefixes;this.trimData=trimData;
 }
}''',
            "flixel/math/FlxPoint.hx": r'''package flixel.math;
class FlxPoint {
 public static var gets=0;public static var puts=0;
 public var x:Float=0;public var y:Float=0;
 public function new(x:Float=0,y:Float=0) {this.x=x;this.y=y;}
 public static function get():FlxPoint {gets++;return new FlxPoint();}
 public function put():FlxPoint {puts++;return this;}
 public function set(x:Float=0,y:Float=0):FlxPoint {this.x=x;this.y=y;return this;}
}''',
            "flixel/math/FlxMatrix.hx": r'''package flixel.math;
class FlxMatrix {
 public var tx:Float=0;public var ty:Float=0;
 public function new() {}
 public function translate(x:Float,y:Float):FlxMatrix {tx+=x;ty+=y;return this;}
}''',
            "flixel/FlxSprite.hx": r'''package flixel;
import flixel.graphics.frames.FlxFramesCollection;
import flixel.math.FlxPoint;
class FlxSprite {
 public var frames:FlxFramesCollection;
 public var animation:FakeAnimation;
 public var scale:FlxPoint;
 public var width:Float=64;public var height:Float=32;
 public var antialiasing:Bool=true;public var updates=0;public var sizedTo:Float=0;
 public function new() {scale=new FlxPoint(1,1);animation=new FakeAnimation(this);}
 public function setGraphicSize(value:Int):Void {sizedTo=value;width=value;}
 public function updateHitbox():Void {updates++;width=64*scale.x;height=32*scale.y;}
 public function destroy():Void {}
}
class FakeAnimation {
 var owner:FlxSprite;var names:Map<String,String>=new Map();
 public function new(owner:FlxSprite) this.owner=owner;
 public function destroyAnimations():Void names=new Map();
 public function addByPrefix(name:String,prefix:String,frameRate:Float=24,loop:Bool=true):Void {
  if(owner.frames!=null&&owner.frames.prefixes.indexOf(prefix)>=0) names.set(name,prefix);
 }
 public function exists(name:String):Bool return names.exists(name);
 public function prefix(name:String):String return names.get(name);
 public function play(name:String,force:Bool=false):Void {}
}''',
            "Note.hx": r'''import flixel.math.FlxPoint;
class Note extends flixel.FlxSprite {
 public var codenameFrameOffset:FlxPoint=null;public var codenameFrameOffsetOwned:Bool=false;
 public var nightmareVisionTypeRuntime:Dynamic=null;public var nightmareVisionRenderer:Dynamic=null;
 public var nightmareVisionTailState:Dynamic=null;public var nightmareVisionRGB:Dynamic=null;
 public var nightmareVisionBaseScalePoint:FlxPoint=null;
 public var frameOffset(get,set):FlxPoint;
''',
            "CodenameGameEvent.hx": (ROOT / "source/CodenameGameEvent.hx").read_text(),
            "Main.hx": r'''import flixel.FlxSprite;
import flixel.graphics.frames.FlxFramesCollection;
import flixel.math.FlxMatrix;
import flixel.math.FlxPoint;
class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var noteFrames=new FlxFramesCollection('selected-owner-opponent',
   ['purple0','purple hold piece','pruple end hold'],'rotated=70;trimmed=87');
  var note=new FlxSprite();
  check(CodenameCreationVisual.applyNoteAtlas(note,noteFrames,'purple','',true,.75),
   'Sparrow note atlas was rejected');
  check(note.frames==noteFrames,'resolver frames identity lost trim/rotation metadata');
  check(note.frames.trimData=='rotated=70;trimmed=87','atlas metadata changed');
  check(note.animation.prefix('Scroll')=='purple0'&&note.animation.prefix('scroll')=='purple0',
   'tap prefix missing');
  check(note.animation.prefix('hold')=='purple hold piece','sustain prefix missing');
  check(note.animation.prefix('holdend')=='pruple end hold','upstream purple typo fallback order');
  check(note.scale.x==.75&&note.scale.y==.75&&note.width==48&&note.updates==1,
   'note scale was not applied before hitbox measurement');

  var receptorFrames=new FlxFramesCollection('selected-owner-receptors',
   ['arrowLEFT','left press','left confirm'],'rotation-and-trim-preserved');
  var receptor=new FlxSprite();
  check(CodenameCreationVisual.applyStrumAtlas(receptor,receptorFrames,'left',.5),
   'Sparrow receptor atlas was rejected');
  check(receptor.frames==receptorFrames,'receptor frames metadata identity lost');
  check(receptor.animation.prefix('static')=='arrowLEFT'
   &&receptor.animation.prefix('pressed')=='left press'
   &&receptor.animation.prefix('confirm')=='left confirm','mutable receptor prefix was ignored');

  var matrix=new FlxMatrix();
  CodenameCreationVisual.applyFrameOffset(matrix,25,-4);
  check(matrix.tx==-25&&matrix.ty==4,'frameOffset did not change the sprite transform');

  var eventNote=new Note();
  var event=new CodenameNoteCreationEvent(eventNote,2,'custom',3,4,true,
   'game/notes/default','',.7);
  event.noteSprite='hud/oppNOTE';event.noteScale=.9;event.cancel();
  check(event.note==eventNote&&event.noteSprite=='hud/oppNOTE'&&event.noteScale==.9
   &&event.cancelled&&!event.stopsPropagation(),'creation event mutations/cancel were lost');

  var defaultAtlas='game/notes/default';
  check(CodenameCreationVisual.selectedAtlasPath(true,defaultAtlas,false)==defaultAtlas,
   'Codename default atlas sentinel was skipped');
  check(CodenameCreationVisual.selectedAtlasPath(true,'hud/custom',false)=='hud/custom',
   'callback atlas replacement was not preserved');
  check(CodenameCreationVisual.selectedAtlasPath(false,defaultAtlas,false)==null,
   'ownerless native receptor selected a Codename atlas');
  check(CodenameCreationVisual.selectedAtlasPath(true,defaultAtlas,true)==null,
   'cancelled creation still selected an atlas');

  var animateFrames=new animate.FlxAnimateFrames('selected-owner-animate',
   ['arrowLEFT','left press','left confirm'],'timeline=true');
  var animateNote=new FlxSprite();
  check(!CodenameCreationVisual.applyNoteAtlas(animateNote,animateFrames,'purple','',false,.7,
   'owner-a','game/notes/animated'), 'FlxSprite note accepted Animate timeline frames');
  check(animateNote.frames==null&&animateNote.updates==0,
   'unsupported Animate atlas partially changed note state');
  var animateReceptor=new FlxSprite();
  check(!CodenameCreationVisual.applyStrumAtlas(animateReceptor,animateFrames,'left',.7,true,
   'owner-a','game/notes/animated'), 'FlxSprite receptor accepted Animate timeline frames');
  check(animateReceptor.frames==null&&animateReceptor.updates==0,
   'unsupported Animate atlas partially changed receptor state');

  var pooled=new Note();
  var internal=pooled.frameOffset;
  check(internal!=null&&FlxPoint.gets==1&&pooled.codenameFrameOffsetOwned,
   'lazy point getter did not allocate one owned point');
  var external=new FlxPoint(25,0);
  pooled.frameOffset=external;
  check(pooled.frameOffset==external&&FlxPoint.puts==1&&!pooled.codenameFrameOffsetOwned,
   'writable field did not replace/return its internally owned point');
  pooled.destroy();
  check(FlxPoint.puts==1,'destroy returned the script-owned FlxPoint to the pool');
  var borrowed=new Note();var assigned=new FlxPoint(5,6);borrowed.frameOffset=assigned;
  borrowed.destroy();
  check(FlxPoint.puts==1,'destroy returned an assigned borrowed point');
  Sys.println('creation hooks ok');
 }
}''',
        }
        probe = stubs["Note.hx"] + "\n" + get_offset + "\n" + set_offset + "\n" + destroy + "\n}\n"
        stubs["Note.hx"] = probe
        state_source = (ROOT / "source/PlayState.hx").read_text()
        stubs["TypeTable.hx"] = ('class TypeTable { public var codenameSelectedNoteTypes:Array<Dynamic> '
                                 '= ["unused", "later", "firstEncounter", "later"]; public function new() {} '
                                 + method(state_source, "codenameNoteTypeIndex") + '}')
        stubs["Main.hx"] = stubs["Main.hx"].replace("Sys.println('creation hooks ok');", """
  var types = new TypeTable();
  check(types.codenameNoteTypeIndex('firstEncounter') == 3, 'source table order lost');
  check(types.codenameNoteTypeIndex('later') == 2, 'first duplicate source type lost');
  check(types.codenameNoteTypeIndex(null) == 0 && types.codenameNoteTypeIndex('') == 0,
   'implicit default type ID changed');
  Sys.println('creation hooks ok');
""")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            temp = Path(directory)
            for name, body in stubs.items():
                file = temp / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(body, newline='\n')
            (temp / "CodenameCreationVisual.hx").write_text(helper, newline='\n')
            (temp / "CodenameNoteCreationEvent.hx").write_text(event, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(temp), "-main", "Main", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("creation hooks ok", result.stdout)
        self.assertEqual(result.stdout.count("[codename-atlas-unsupported]"), 1,
                         result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
