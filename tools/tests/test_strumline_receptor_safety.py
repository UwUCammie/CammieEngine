"""Pin the receptor-safety contract between imported donor scripts and Strumline.

Imported V-Slice scripts attach effect sprites to the strumline container
(``strumline.add(splash)``) and kill notes the stream no longer owns
(``strumline.killNote(note)``).  In the donor engine the receptors live in
their own subgroup, so those calls can never pollute receptor iteration; this
fork's Strumline *is* the receptor group, so the native gameplay loops rely on
the routing/guard contract pinned here.
"""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def run_interp(main_source: str, extra_classpaths=None, classpath_first=False):
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        temp = Path(folder)
        (temp / "Main.hx").write_text(main_source, newline='\n')
        command = [*HAXE_COMMAND]
        paths = [str(ROOT / "source"), str(temp)]
        if classpath_first:
            paths = [str(temp), str(ROOT / "source")]
        if extra_classpaths:
            paths.extend(str(path) for path in extra_classpaths)
        for path in paths:
            command.extend(["-cp", path])
        command.extend(["-main", "Main", "--interp"])
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)


class StrumlineReceptorSafetyTest(unittest.TestCase):
    def setUp(self):
        self.strumline = (ROOT / "source/Strumline.hx").read_text()
        self.play_state = (ROOT / "source/PlayState.hx").read_text()

    def strumline_routing_fixture(self):
        """Extract the routing + guarded-iteration members into a stub family."""
        source = self.strumline
        routing = source[source.index("\toverride public function add(sprite:StrumNote):StrumNote"):
                         source.index("\tpublic function forEachReceptor(")]
        iteration = source[source.index("\tpublic function forEachReceptor("):
                           source.index("\t/** Attached effects update with the line")]
        return '''class Pt {public var x:Float=1.;public var y:Float=1.;public function new(x:Float=1.,y:Float=1.){this.x=x;this.y=y;}public function copyFrom(o:Pt){x=o.x;y=o.y;}}
class FlxBasic {
 public var ID:Int;public var exists=true;public var alive=true;public var active=true;public var visible=true;
 public function new(){}public function kill(){alive=false;exists=false;}
}
class FlxSprite extends FlxBasic {
 public var x:Float=0.;public var y:Float=0.;public var alpha:Float=1.;
 public var scrollFactor:Pt=new Pt();public var cameras:Dynamic=null;
 public function new(){super();}
}
class FlxTypedGroup<T> {
 public var members:Array<T>=[];public var destroyed=false;
 public function new(){}
 public function add(s:T):T{members.push(s);return s;}
 public function remove(s:T,splice:Bool=false):T{var i=members.indexOf(s);if(i>=0){if(splice)members.splice(i,1);else members[i]=null;}return s;}
 public function clear(){members=[];}
 public function destroy(){destroyed=true;members=[];}
}
class StrumNote extends FlxSprite {public var animation:Dynamic={};public function new(){super();}}
class FakeSplash extends FlxSprite {public function new(){super();}}
class LineBase extends FlxSprite {
 public var members:Array<StrumNote>=[];
 public function add(sprite:StrumNote):StrumNote{members.push(sprite);return sprite;}
 public function insert(position:Int,sprite:StrumNote):StrumNote{members.insert(position,sprite);return sprite;}
 public function remove(sprite:StrumNote,splice:Bool=false):StrumNote{var i=members.indexOf(sprite);if(i>=0){if(splice)members.splice(i,1);else members[i]=null;}return sprite;}
 public function new(){super();}
}
class Line extends LineBase {
 public var attachedEffects(default, null):FlxTypedGroup<FlxSprite>;
''' + routing + iteration + '''}
class Main {
 static function fail(value:String):Void throw value;
 static function main() {
  var line = new Line();
  var receptors:Array<StrumNote> = [];
  for (i in 0...4) { var r = new StrumNote(); receptors.push(r); line.add(r); }
  if (line.members.length != 4) fail("receptor add must land in the receptor members");

  // Donor strumline.add(effect): routed beside the receptors, never into them.
  var splash = new FakeSplash();
  splash.scrollFactor.x = 9;
  line.add(cast splash);
  if (line.members.length != 4) fail("effect sprite entered the receptor members");
  if (line.attachedEffects == null || line.attachedEffects.members.length != 1)
    fail("effect sprite was not routed to the attached effects layer");
  if (splash.scrollFactor.x != line.scrollFactor.x)
    fail("routed effect must inherit the strumline scroll factor");
  if (line.attachedEffects.members[0] != splash)
    fail("attached layer lost the routed effect");

  // Iteration visits only live receptors; foreign members are named, never passed.
  var visited:Int = 0;
  line.forEachReceptor(function(spr:StrumNote) { visited++; });
  if (visited != 4) fail("live receptors must all be visited");

  receptors[2].kill();
  receptors[3].animation = null;
  visited = 0;
  line.forEachReceptor(function(spr:StrumNote) { visited++; });
  if (visited != 2) fail("killed or unanimated receptors must not be visited");

  // Effects can leave again through the same routing.
  line.remove(cast splash);
  if (line.attachedEffects.members.indexOf(splash) >= 0) fail("routed effect removal failed");

  // A null add (typed signature rejected a foreign object) must not punch a
  // null hole into the receptor members.
  line.add(null);
  if (line.members.length != 4) fail("null add must not grow the receptor members");
 }
}
'''

    def test_foreign_effect_adds_are_routed_beside_the_receptors(self):
        result = run_interp(self.strumline_routing_fixture())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_kill_note_keeps_donor_hide_and_kill_semantics(self):
        source = self.strumline
        kill = source[source.index("\tpublic function killNote(note:Dynamic):Void"):
                      source.index("\t/**\n\t * Adjust only receptor spacing")]
        fixture = '''class Pt {public var x:Float=1;public var y:Float=1;public function copyFrom(o:Pt){}}
class FlxBasic {
 public var exists=true;public var alive=true;public var active=true;public var visible=true;
 public function new(){}public function kill(){alive=false;exists=false;}
}
class Line {
 public function new(){}
''' + kill + '''
}
class FakeNote extends FlxBasic {public function new(){super();}}
class Main {
 static function fail(value:String):Void throw value;
 static function main() {
  var line = new Line();
  var note = new FakeNote();
  line.killNote({nativeNote: note});
  if (note.visible) fail("donor killNote must hide the note");
  if (note.alive || note.exists) fail("donor killNote must kill the note so group iteration skips it");
  line.killNote(null);
  line.killNote({});
  line.killNote({nativeNote: null});
 }
}
'''
        result = run_interp(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_receptor_loops_use_the_guarded_iteration(self):
        play = self.play_state
        self.assertIn("strums.forEachReceptor(function(spr:Strumline.StrumNote)", play)
        self.assertIn("enemyStrums.forEachReceptor(function(spr:Strumline.StrumNote)", play)
        self.assertIn("playerStrums.forEachReceptor(function(spr:Strumline.StrumNote)", play)
        self.assertGreaterEqual(play.count("forEachReceptor(function(spr:Strumline.StrumNote)"), 4)
        # Donor killNote parity stays hide + kill, and the hit path reaps the
        # killed note out of the iterating group.
        strumline = self.strumline
        kill = strumline[strumline.index("\tpublic function killNote(note:Dynamic):Void"):]
        kill = kill[kill.index("{") + 1:kill.index("}", kill.index("{") + 1)]
        self.assertIn("visible = false", kill)
        self.assertIn("kill()", kill)
        self.assertIn("if (!note.alive) {", play)
        reap = play[play.index("if (!note.alive) {"):]
        self.assertIn("notes.remove(note, true)", reap)

    def translate_character_body(self, body: str, method_name: str, argument: str) -> str:
        """Run the private character-callback lowering through reflection.

        ``analyze`` is only the read-only diagnostic surface and does not
        generate for these donors, so the test pins the translator itself.
        """
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            generated_path = temp / "generated.txt"
            main = '''import hscript.Parser;
class Main {
 static function fail(value:String):Void throw value;
 static function main() {
  if (HxcCompat.analyze == null) fail("HxcCompat is not compiled in");
  var translate = Reflect.field(HxcCompat, "translateCharacterBody");
  if (translate == null) fail("translateCharacterBody is missing");
  var body:String = Reflect.callMethod(HxcCompat, translate,
    [''' + self.hx_multiline(body) + ''', "''' + method_name + '''", ["''' + argument + '''"]]);
  var parser = new hscript.Parser();
  parser.parseString("function probe(''' + argument + ''') {" + body + "\\n}");
  sys.io.File.saveContent("''' + str(generated_path).replace("\\", "/").replace("'", "\\'") + '''", body);
 }
}
'''
            (temp / "Main.hx").write_text(main, newline='\n')
            # The temp classpath must come last: duplicate module names resolve
            # to the last classpath, so this shadows source/Main.hx.
            command = [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                       "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                       "-cp", str(temp), "-main", "Main", "--interp"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return generated_path.read_text()

    @staticmethod
    def hx_multiline(text: str) -> str:
        return "'" + text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"

    def test_character_super_note_miss_is_lowered_not_dropped(self):
        body = self.translate_character_body(
            '\n'
            '  if (event.note.noteData.kind != "trickyhell" && event.note.noteData.kind != "trickydeath")\n'
            '   super.onNoteMiss(event);\n',
            'onNoteMiss', 'event')
        self.assertIn("HxcCompatRuntime.characterDefaultNoteMiss(hxcCharacter(), event)", body)
        self.assertNotIn("super.onNoteMiss", body)

    def test_dropped_statement_leaves_parseable_empty_branch(self):
        # An unsupported super call is stripped; the guarded branch must still
        # parse instead of failing the whole file with EUnexpected(}).  The
        # repaired body keeps an explicit empty block as the branch body.
        for method_name in ('onUpdate', 'onNoteMiss'):
            body = self.translate_character_body(
                '\n'
                '  if (event != null)\n'
                '   super.actuallyDance(event);\n',
                method_name, 'event')
            self.assertNotIn("super.actuallyDance", body)
            self.assertIn("if (event != null)", body)
            self.assertTrue(body.rstrip().endswith("{}"),
                            "dangling branch must end with an empty block: " + repr(body))

    def test_character_default_note_miss_bridge_plays_the_miss_sing(self):
        runtime = (ROOT / "source/HxcCompatRuntime.hx").read_text()
        bridge = runtime[runtime.index("\tpublic static function characterDefaultNoteMiss("):
                         runtime.index("\tpublic static function dance(")]
        field_helper = runtime[runtime.index("\tstatic function runtimeField("):
                               runtime.index("\tstatic function runtimeIntValue(")]
        int_helper = runtime[runtime.index("\tstatic function runtimeIntValue("):
                             runtime.index("\tstatic function runtimeFloatValue(")]
        fixture = '''class Bridge {
''' + bridge + field_helper + int_helper + '''
}
class Main {
 static function fail(value:String):Void throw value;
 static function main() {
  var calls:Array<Array<Dynamic>> = [];
  var character = {playSingAnimation: function(direction:Int, miss:Bool, suffix:String) {
   calls.push([direction, miss, suffix]);
  }};
  var event = {note: {noteData: {getDirection: function() return 2}}};
  Bridge.characterDefaultNoteMiss(character, event);
  if (calls.length != 1) fail("miss sing must play once");
  if (calls[0][0] != 2 || calls[0][1] != true || calls[0][2] != "")
    fail("wrong miss sing: " + calls[0]);

  // Ghost misses carry no note: the bridge must stay a no-op.
  Bridge.characterDefaultNoteMiss(character, {note: null});
  if (calls.length != 1) fail("ghost miss must not animate");

  // Sustain segments resolve direction from the native note payload.
  Bridge.characterDefaultNoteMiss(character, {note: null, nativeNote: {noteData: {data: 0}}});
  if (calls.length != 2 || calls[1][0] != 0 || calls[1][1] != true)
    fail("native note fallback failed: " + calls);
 }
}
'''
        result = run_interp(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
