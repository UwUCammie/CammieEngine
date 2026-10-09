"""Psych notes follow receptor geometry and clip sustains like the pinned donor."""
from pathlib import Path
from haxe_test_support import FixturePath as Path, HAXE_COMMAND
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def extract_method(source, marker):
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychNoteFollowTest(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "source/Note.hx").read_text()
        self.follow = extract_method(self.source, "public function applyPsychReceptorFollow(")
        self.clip = extract_method(self.source, "public function applyPsychReceptorClip(")
        self.set_speed = extract_method(self.source, "function set_multSpeed(")
        self.resize = extract_method(self.source, "public function resizeByRatio(")

    def run_haxe(self, body):
        fixture = f'''using StringTools;
class Conductor {{ public static var songPosition:Float = 1000; }}
class FlxPoint {{
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0) {{ this.x=x; this.y=y; }}
}}
class FlxRect {{
 public var x:Float; public var y:Float; public var width:Float; public var height:Float;
 public function new(x:Float,y:Float,width:Float,height:Float) {{
  this.x=x; this.y=y; this.width=width; this.height=height;
 }}
}}
class AnimFrame {{ public var name:String; public function new(name:String) this.name=name; }}
class Anim {{ public var curAnim:AnimFrame; public function new(name:String='hold') curAnim=new AnimFrame(name); }}
class Note {{
 public static var swagWidth:Float = 35;
 public var nightmareVisionLegacyGeometry=false; public var noteData=0; public var baseScaleY=1.;
 public var sourceTimingMode:Int = 1;
 public var codenameInputLine:Dynamic = null;
 public var copyX:Bool = true; public var copyY:Bool = true; public var copyAngle:Bool = true;
 public var offsetX:Float = 0; public var offsetY:Float = 0; public var offsetAngle:Float = 0;
 public var multSpeed(default,set):Float = 1;
 public var correctionOffset:Float = 0; public var distance:Float = 0;
 public var strumTime:Float = 800;
 public var isSustainNote:Bool = false;
 public var x:Float = 0; public var y:Float = 0; public var angle:Float = 0;
 public var frameHeight:Float = 40; public var width:Float = 120; public var height:Float = 100;
 public var frameWidth:Float = 120; public var scale:FlxPoint = new FlxPoint(2, 2);
 public var offset:FlxPoint = new FlxPoint(0, 3);
 public var animation:Anim = new Anim();
 public var hitboxUpdates:Int = 0;
 public function updateHitbox():Void hitboxUpdates++;
 public var mustPress:Bool = true; public var ignoreNote:Bool = false;
 public var wasGoodHit:Bool = true; public var prevNote:Note = null;
 public var canBeHit:Bool = true; public var noSustainClip:Bool = false;
 public var clipRect:FlxRect = null;
 public function new() prevNote=this;
 {self.set_speed}
 {self.resize}
 {self.follow}
 {self.clip}
}}
class Main {{
 static function check(value:Bool,message:String):Void if (!value) throw message;
 static function close(actual:Float,expected:Float,message:String):Void {{
  if (Math.abs(actual-expected)>0.0001) throw message+': '+actual+' expected '+expected;
 }}
 static function main():Void {{
  {body}
 }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_donor_fields_and_sustain_constructor_defaults(self):
        for declaration in (
            "@:keep public var copyX:Bool = true;",
            "@:keep public var copyY:Bool = true;",
            "@:keep public var copyAngle:Bool = true;",
            "@:keep public var offsetX:Float = 0;",
            "@:keep public var offsetY:Float = 0;",
            "@:keep public var offsetAngle:Float = 0;",
            "@:keep public var multSpeed(default, set):Float = 1.0;",
            "@:keep public var correctionOffset:Float = 0;",
            "@:keep public var distance:Float = 0;",
        ):
            self.assertIn(declaration, self.source)
        constructor = extract_method(self.source, "public function new(strumTime:Float")
        self.assertIn('if ((sourceTimingMode == 1 && codenameInputLine == null) || nightmareVisionLegacyGeometry)', constructor)
        self.assertIn('copyAngle = false;', constructor)
        finalizer = extract_method(self.source, 'public function finalizePsychSustainSegment(')
        self.assertIn('offsetX += (startWidth - width) / 2;', finalizer)
        self.assertIn('if (pixelStage) offsetX += 30;', finalizer)

    def test_follow_formula_copy_flags_speed_and_mode_guards(self):
        self.run_haxe(f'''
  Conductor.songPosition = 1000;
  var note = new Note();
  note.offsetX = 5; note.offsetY = 7; note.offsetAngle = 3; note.multSpeed = 2;
  note.applyPsychReceptorFollow(100, 300, 90, 15, false, 1.5, false, 6);
  close(note.x, 105, 'Psych travel changed receptor-relative X');
  close(note.y, 37, 'Psych travel used the wrong scroll direction or speed');
  close(note.distance, -270, 'source distance field does not expose signed travel');
  close(note.angle, 18, 'Psych angle omitted direction, receptor angle, or offset');

  note.x = 14; note.y = 25; note.angle = 36;
  note.copyX = false; note.copyY = false; note.copyAngle = false;
  note.applyPsychReceptorFollow(700, 800, 0, 90, true, 4, false, 6);
  close(note.x, 14, 'copyX=false overwrote a script-owned X');
  close(note.y, 25, 'copyY=false overwrote a script-owned Y');
  close(note.angle, 36, 'copyAngle=false overwrote a script-owned angle');

  note.copyX = true; note.copyY = false; note.copyAngle = true;
  note.applyPsychReceptorFollow(20, 30, 180, 12, true, 1, false, 6);
  close(note.x, -155, 'independent copyX did not update');
  close(note.y, 25, 'copyY=false was not independent');
  close(note.angle, 105, 'independent copyAngle did not update');

  note.x = 41; note.y = 42; note.angle = 43; note.sourceTimingMode = 0;
  note.applyPsychReceptorFollow(1, 2, 90, 3, true, 1, false, 6);
  close(note.x, 41, 'base note was modified');
  close(note.y, 42, 'base note was modified');
  close(note.angle, 43, 'base note was modified');
  note.sourceTimingMode = 2;
  note.applyPsychReceptorFollow(1, 2, 90, 3, true, 1, false, 6);
  close(note.x, 41, 'Nightmare Vision note was modified');

  note.sourceTimingMode = 1; note.codenameInputLine = {{}};
  note.applyPsychReceptorFollow(1, 2, 90, 3, true, 1, false, 6);
  close(note.x, 41, 'Codename-owned note was modified');
''')

    def test_mult_speed_and_downscroll_sustain_trim(self):
        self.run_haxe(f'''
  var sustain = new Note();
  sustain.isSustainNote = true;
  sustain.scale.y = 1;
  sustain.multSpeed = 2;
  close(sustain.scale.y, 2, 'multSpeed did not resize active sustain');
  close(sustain.hitboxUpdates, 1, 'multSpeed did not refresh sustain hitbox');
  sustain.multSpeed = 0.5;
  close(sustain.scale.y, 0.5, 'multSpeed resize ratio compounded incorrectly');
  sustain.animation.curAnim.name = 'holdend';
  sustain.multSpeed = 1;
  close(sustain.scale.y, 0.5, 'multSpeed rescaled sustain end');

  Conductor.songPosition = 500;
  sustain.strumTime = 500; sustain.multSpeed = 1; sustain.scale.y = 1.5;
  sustain.frameHeight = 40; sustain.offsetY = 2; sustain.correctionOffset = 5;
  sustain.offsetX = 30; sustain.copyAngle = false;
  sustain.applyPsychReceptorFollow(10, 300, 90, 0, true, 1, true, 6);
  close(sustain.x, 10 + 30, 'pixel sustain X offset was lost');
  close(sustain.y, 300 + 2 + 5 - 6 * 9.5 - (40 * 1.5 - 17.5),
    'downscroll pixel sustain trim or source correction offset is wrong');

  sustain.copyY = false; sustain.y = 77;
  sustain.applyPsychReceptorFollow(10, 300, 90, 0, true, 1, true, 6);
  close(sustain.y, 77, 'copyY=false did not preserve sustain placement');
''')

    def test_sustain_clip_matches_donor_and_obeys_route_guards(self):
        self.run_haxe(f'''
  var note = new Note();
  note.isSustainNote = true; note.wasGoodHit = true; note.y = 320;
  note.height = 100; note.width = 120; note.frameHeight = 100; note.frameWidth = 120;
  note.scale.x = 2; note.scale.y = 2; note.offset.y = 3; note.offsetY = 2;
  note.applyPsychReceptorClip(317.5, false);
  check(note.clipRect != null, 'eligible sustain did not receive source clip rect');
  close(note.clipRect.y, 8.5, 'upscroll sustain clip starts at wrong local Y');
  close(note.clipRect.width, 60, 'upscroll sustain clip uses wrong local width');
  close(note.clipRect.height, 41.5, 'upscroll sustain clip has wrong height');

  note.clipRect = null; note.y = 320;
  note.applyPsychReceptorClip(317.5, true);
  close(note.clipRect.y, 91.5, 'downscroll sustain clip starts at wrong frame row');
  close(note.clipRect.width, 120, 'downscroll sustain clip uses wrong frame width');
  close(note.clipRect.height, 8.5, 'downscroll sustain clip has wrong height');

  note.clipRect = new FlxRect(1, 2, 3, 4); note.noSustainClip = true;
  note.applyPsychReceptorClip(317.5, true);
  check(note.clipRect == null, 'noSustainClip left a stale crop');
  note.noSustainClip = false; note.sourceTimingMode = 0;
  note.applyPsychReceptorClip(317.5, true);
  check(note.clipRect == null, 'base mode received Psych sustain clipping');
  note.sourceTimingMode = 2;
  note.applyPsychReceptorClip(317.5, true);
  check(note.clipRect == null, 'Nightmare Vision mode received Psych sustain clipping');

  note.sourceTimingMode = 1; note.ignoreNote = true; note.mustPress = false;
  note.applyPsychReceptorClip(317.5, false);
  check(note.clipRect == null, 'ignored opponent sustain was source clipped');
  note.mustPress = true; note.codenameInputLine = {{}};
  note.applyPsychReceptorClip(317.5, false);
  check(note.clipRect == null, 'Codename sustain was source clipped');
''')

    def test_source_geometry_matches_pinned_psych_contract(self):
        donor = Path(
            r"C:\Users\uwucammie\Documents\coding\FNF\fnf_sources\FNF-PsychEngine"
            r"\source\objects\Note.hx"
        ).read_text()
        donor_play = Path(
            r"C:\Users\uwucammie\Documents\coding\FNF\fnf_sources\FNF-PsychEngine"
            r"\source\states\PlayState.hx"
        ).read_text()
        self.assertIn(
            "distance = (0.45 * (Conductor.songPosition - strumTime) * songSpeed * multSpeed);",
            donor,
        )
        self.assertIn("daNote.followStrumNote(strum, fakeCrochet, songSpeed / playbackRate);", donor_play)
        for fragment in (
            "angle = strumDirection - 90 + strumAngle + offsetAngle;",
            "x = strumX + offsetX + Math.cos(angleDir) * distance;",
            "y = strumY + offsetY + correctionOffset + Math.sin(angleDir) * distance;",
            "sustainNote.correctionOffset = swagNote.height / 2;",
            "sustainNote.correctionOffset = 0;",
        ):
            self.assertIn(fragment, donor if "sustainNote." not in fragment else donor_play)


if __name__ == "__main__":
    unittest.main()