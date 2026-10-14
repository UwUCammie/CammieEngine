"""Per-frame and per-hit HUD work: same answers, less garbage.

The score line, presence strings, camera nudges, sustain clip rects and the
Nightmare Vision note snapshot are all rebuilt every frame or every hit. These
fixtures run the actual helpers next to the code they replaced and check the
results match, and that the cached paths still notice every input change.
"""
from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE, HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    """Extract one Haxe method, ignoring braces in comments and strings."""
    start = source.index(marker)
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
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"Unclosed Haxe method: {marker}")


# The Wife3 table GenerateLetterRank used before it became an if-chain.
OLD_WIFE = [
    (lambda a: a >= 99.9935, " AAAAA"), (lambda a: a >= 99.980, " AAAA:"),
    (lambda a: a >= 99.970, " AAAA."), (lambda a: a >= 99.955, " AAAA"),
    (lambda a: a >= 99.90, " AAA:"), (lambda a: a >= 99.80, " AAA."),
    (lambda a: a >= 99.70, " AAA"), (lambda a: a >= 99, " AA:"),
    (lambda a: a >= 96.50, " AA."), (lambda a: a >= 93, " AA"),
    (lambda a: a >= 90, " A:"), (lambda a: a >= 85, " A."),
    (lambda a: a >= 80, " A"), (lambda a: a >= 70, " B"),
    (lambda a: a >= 60, " C"), (lambda a: a < 60, " D"),
]


def old_letter_rank(accuracy: float, botplay: bool, fc_label: str) -> str:
    ranking = fc_label
    for test, letter in OLD_WIFE:
        if test(accuracy):
            ranking += letter
            break
    if accuracy == 0:
        ranking = "N/A"
    elif botplay:
        ranking = "BotPlay"
    return ranking


class HudFrameAllocationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")

    def run_haxe(self, files: dict[str, str], extra_cp: list[str] | None = None) -> str:
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp", prefix="hud-frame-") as directory:
            work = Path(directory)
            for name, text in files.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8", newline="\n")
            command = [*HAXE_COMMAND, "-cp", str(work)]
            for path in extra_cp or []:
                command += ["-cp", path]
            result = subprocess.run(command + ["--main", "Main", "--interp"], cwd=work,
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

    def test_letter_rank_matches_the_old_table_and_cached_score_line_tracks_inputs(self):
        accuracies = [0, 100, 99.9935, 99.9934, 99.98, 99.975, 99.97, 99.96, 99.955, 99.95,
                      99.9, 99.85, 99.8, 99.75, 99.7, 99.5, 99, 98, 96.5, 96.49, 93, 92.9,
                      90, 89.99, 85, 84, 80, 79.5, 70, 69.9, 60, 59.99, 30, 0.01, -5]
        cases = []
        for accuracy in accuracies:
            for botplay in (False, True):
                cases.append((accuracy, botplay))
        lines = []
        for accuracy, botplay in cases:
            lines.append(f"  rank({accuracy!r}, {str(botplay).lower()});")
        main = r'''
class Main {
 static function rank(accuracy:Float, botplay:Bool):Void {
  flixel.FlxG.save.data.botplay = botplay;
  Sys.println(Std.string(accuracy) + "|" + botplay + "|" + Ratings.GenerateLetterRank(accuracy));
 }
 static function check(v:Bool, s:String):Void if (!v) throw s;
 static function same(label:String):Void {
  var cached = Ratings.CalculateRankingCached(PlayState.songScore, PlayState.songScoreDef, PlayState.nps, PlayState.accuracy);
  var fresh = Ratings.CalculateRanking(PlayState.songScore, PlayState.songScoreDef, PlayState.nps, PlayState.accuracy);
  check(cached == fresh, label + ': cached "' + cached + '" fresh "' + fresh + '"');
 }
 static function main() {
__RANKS__
  flixel.FlxG.save.data.botplay = false;
  Sys.println("NAN|" + Ratings.GenerateLetterRank(Math.NaN));
  flixel.FlxG.save.data.npsDisplay = false;
  same('first line');
  same('unchanged');
  PlayState.songScore = 350; same('score');
  PlayState.songScoreDef = 12; same('score def');
  Conductor.safeFrames = 8; same('safe frames');
  PlayState.accuracy = 97.25; same('accuracy');
  PlayState.misses = 1; same('misses');
  PlayState.misses = 0; PlayState.goods = 2; same('goods change the full combo label');
  PlayState.bads = 1; same('bads');
  PlayState.shits = 1; same('shits');
  flixel.FlxG.save.data.npsDisplay = true; same('nps display on');
  PlayState.nps = 7; same('nps');
  flixel.FlxG.save.data.botplay = true; same('botplay on');
  flixel.FlxG.save.data.botplay = null; same('botplay unset');
  PlayState.accuracy = Math.NaN; same('nan accuracy');
  same('nan accuracy again');
 }
}
'''.replace("__RANKS__", "\n".join(lines))
        stubs = {
            "Main.hx": main,
            "Ratings.hx": (ROOT / "source/Ratings.hx").read_text(encoding="utf-8"),
            # Only truncateFloat: the rest of HelperFunctions reaches into PlayState.
            "HelperFunctions.hx": "class HelperFunctions {\n" + extract_method(
                (ROOT / "source/HelperFunctions.hx").read_text(encoding="utf-8"),
                "public static function truncateFloat(") + "\n}\n",
            "flixel/FlxG.hx": "package flixel;\nclass FlxG { public static var save:Dynamic = {data:{}}; }\n",
            "Highscore.hx": "enum abstract FCLevel(Int) from Int to Int { var None; var Clear; var Sdcb; var Bad; var Good; var Sick; }\nclass Highscore {}\n",
            "PlayState.hx": "class PlayState {\n public static var misses:Int=0; public static var goods:Int=0; public static var bads:Int=0;\n public static var shits:Int=0; public static var songScore:Int=0; public static var songScoreDef:Int=0;\n public static var nps:Int=0; public static var accuracy:Float=100;\n}\n",
            "Conductor.hx": "class Conductor { public static var safeFrames:Int=10; public static var safeZoneOffset:Float=166; }\n",
            "ModifierState.hx": "class ModifierState { public static var namedModifiers:Dynamic={demo:{value:false}}; }\n",
            "OptionsHandler.hx": "class OptionsHandler { public static var options:Dynamic={ignoreVile:false}; }\n",
            "Judge.hx": "class Judge { public static var sickJudge:Float=45; public static var goodJudge:Float=90; public static var badJudge:Float=135; public static var shitJudge:Float=166; public static var wayoffJudge:Float=203; }\n",
        }
        output = self.run_haxe(stubs).splitlines()
        # With every count at zero the full combo label is (MFC).
        for (accuracy, botplay), line in zip(cases, output):
            expected = old_letter_rank(float(accuracy), botplay, "(MFC)")
            self.assertEqual(line.split("|", 2)[2], expected, f"accuracy {accuracy} botplay {botplay}")
        self.assertEqual(output[len(cases)], "NAN|" + old_letter_rank(math.nan, False, "(MFC)"))
        ratings = (ROOT / "source/Ratings.hx").read_text(encoding="utf-8")
        self.assertNotIn("wifeConditions", ratings)
        hud = self.play[self.play.index("\t\tif (disableScoreChange == false && !sourceScoreDisplayOwned())"):]
        self.assertTrue(hud.startswith("\t\tif (disableScoreChange == false && !sourceScoreDisplayOwned())\n"
                                       "\t\t\tscoreTxt.text = Ratings.CalculateRankingCached(songScore, songScoreDef, nps, accuracy);"))

    def test_smoke_gates_resolve_once_on_an_ordinary_launch(self):
        harness = (ROOT / "source/RuntimeSmokeHarness.hx").read_text(encoding="utf-8")
        config = extract_method(harness, "public static function config():Null<RuntimeSmokeOptions> {")
        self.assertTrue(config.split("\n", 3)[1].strip() == "if (configResolved)"
                        and config.split("\n", 3)[2].strip() == "return parsed;", config[:200])
        self.assertIn("parsed = null;\n\t\t\tconfigResolved = true;\n\t\t\treturn null;", config)
        self.assertIn("parsed = result;\n\t\tconfigResolved = true;\n\t\treturn parsed;", config)
        self.assertEqual(harness.count("configResolved = true;"), 2)

        menu = (ROOT / "source/ImportedMenuSmokeHarness.hx").read_text(encoding="utf-8")
        enabled = extract_method(menu, "public static function enabled():Bool {")
        main = r'''
class Gate {
 static var enabledResolved:Bool = false;
 static var enabledValue:Bool = false;
 __ENABLED__
}
class Main {
 static function main() {
  Sys.putEnv('CAMMIE_MENU_SMOKE_PLAN', 'tmp/plan.json');
  if (!Gate.enabled()) throw 'first read sees the plan';
  Sys.putEnv('CAMMIE_MENU_SMOKE_PLAN', '');
  if (!Gate.enabled()) throw 'answer is fixed for the run';
 }
}
'''.replace("__ENABLED__", enabled)
        self.run_haxe({"Main.hx": main})

    def test_health_format_presence_strings_and_camera_nudges(self):
        methods = "\n".join(extract_method(self.play, marker) for marker in (
            "\tfunction applyHealthTxtFormat(",
            "\tfunction presenceIconRpc(",
            "\tfunction presencePlayingAs(",
            "\tfunction writeCharacterCamNudge(",
            "\tstatic function animationHeadIs(",
        ))
        main = r'''
enum FlxTextBorderStyle { NONE; OUTLINE; SHADOW; }
enum abstract FlxTextAlign(String) { var LEFT = 'left'; var RIGHT = 'right'; }
abstract FlxColor(Int) from Int to Int {
 public static inline var RED:FlxColor = 0xFFFF0000;
 public static inline var WHITE:FlxColor = 0xFFFFFFFF;
 public static inline var BLACK:FlxColor = 0xFF000000;
}
class Text {
 public var font:String = null; public var embedded:Bool = false; public var color:FlxColor = 0;
 public var size:Int = 8; public var alignment:FlxTextAlign = LEFT; public var borderStyle:FlxTextBorderStyle = NONE;
 public var borderColor:FlxColor = 0; public var borderSize:Float = 0; public var borderQuality:Float = 0;
 public var formats:Int = 0;
 public function new() {}
 public function setFormat(font:String, size:Int, color:FlxColor, alignment:FlxTextAlign, style:FlxTextBorderStyle, borderColor:FlxColor):Void {
  formats++;
  // FlxText stores the font's own name, not the asset path.
  this.font = 'VCR OSD Mono'; embedded = true; this.size = size; this.color = color; this.alignment = alignment;
  borderStyle = style; this.borderColor = borderColor; borderSize = 1; borderQuality = 1;
 }
}
class Character {
 public var camOffsets:Map<String, Array<Dynamic>> = new Map();
 public var anim:String = '';
 public function new() {}
}
class Main {
 var healthTxt = new Text();
 var healthTxtFormatFont:String = null;
 var iconRpcResolved:Bool = false;
 var iconRpcBase:String = null;
 var iconRpcSuffix:String = null;
 var iconRpcValue:String = null;
 var playingAsRpcIcon:String = null;
 var playingAsRpcState:String = null;
 var playingAsRpcValue:String = null;
 public function new() {}
 static function characterAnimationName(c:Character):String return c.anim;
__METHODS__
 static function check(v:Bool, s:String):Void if (!v) throw s;
 static function oldNudge(c:Character, offset:Float, authored:Bool):Array<Float> {
  var cam:Array<Float>;
  if (c.camOffsets.exists(c.anim)) { var d = c.camOffsets.get(c.anim); cam = [d[0], d[1]]; }
  else switch (c.anim.split('-')[0]) {
   case 'singLEFT': cam = [-offset, 0];
   case 'singRIGHT': cam = [offset, 0];
   case 'singUP': cam = [0, -offset];
   case 'singDOWN': cam = [0, offset];
   default: cam = [0, 0];
  }
  return authored ? [0, 0] : cam;
 }
 static function main() {
  var game = new Main();
  var text = game.healthTxt;
  game.applyHealthTxtFormat(FlxColor.WHITE);
  check(text.formats == 1 && text.color == FlxColor.WHITE, 'first frame applies the format');
  for (_ in 0...5) game.applyHealthTxtFormat(FlxColor.WHITE);
  check(text.formats == 1, 'unchanged frames leave the text alone');
  game.applyHealthTxtFormat(FlxColor.RED);
  check(text.formats == 2 && text.color == FlxColor.RED, 'low health colour applied');
  game.applyHealthTxtFormat(FlxColor.RED);
  check(text.formats == 2, 'low health held');
  text.size = 32; game.applyHealthTxtFormat(FlxColor.RED);
  check(text.formats == 3 && text.size == 20, 'a script size change is put back as before');
  text.font = 'Other'; game.applyHealthTxtFormat(FlxColor.RED);
  check(text.formats == 4 && text.font == 'VCR OSD Mono', 'font put back');
  text.alignment = LEFT; game.applyHealthTxtFormat(FlxColor.RED);
  check(text.formats == 5, 'alignment put back');
  text.borderStyle = SHADOW; game.applyHealthTxtFormat(FlxColor.RED);
  check(text.formats == 6, 'border style put back');
  text.borderColor = FlxColor.WHITE; game.applyHealthTxtFormat(FlxColor.RED);
  check(text.formats == 7, 'border colour put back');
  text.borderSize = 3; game.applyHealthTxtFormat(FlxColor.RED);
  check(text.formats == 8, 'border size put back');
  text.color = FlxColor.WHITE; game.applyHealthTxtFormat(FlxColor.RED);
  check(text.formats == 9 && text.color == FlxColor.RED, 'colour put back');

  // The presence strings equal the old concatenations, null names included.
  for (base in ['bf', 'pico', null, 'bf']) for (suffix in ['', '-dead', '-dazed', '']) {
   var expected = suffix == '' ? base : base + suffix;
   check(game.presenceIconRpc(base, suffix) == expected, 'icon rpc ' + base + suffix);
  }
  check(game.presenceIconRpc(null, '') == null, 'a missing icon stays missing');
  for (icon in ['bf', 'dad', null]) for (state in ['Playing', 'Dying', 'Being Poisoned'])
   check(game.presencePlayingAs(icon, state) == "Playing as " + icon + " | " + state, 'playing as ' + icon + state);

  // Camera nudges equal the old split('-') switch for every name shape.
  var actor = new Character();
  actor.camOffsets.set('singUP-alt', [7, -9]);
  var target:Array<Float> = [123, 456];
  for (anim in ['singLEFT', 'singLEFT-alt', 'singLEFTmiss', 'singLEFT-', 'singRIGHT', 'singUP', 'singUP-alt',
   'singUP-alt-2', 'singDOWN', 'singDOWN-miss', 'idle', '', '-singLEFT', 'singleft', 'sing'])
   for (authored in [false, true]) {
    actor.anim = anim;
    game.writeCharacterCamNudge(actor, target, 25.5, authored);
    var expected = oldNudge(actor, 25.5, authored);
    check(target.length == 2 && target[0] == expected[0] && target[1] == expected[1],
     'nudge for "' + anim + '" authored=' + authored + ' got ' + target + ' expected ' + expected);
   }
 }
}
'''.replace("__METHODS__", methods)
        self.run_haxe({"Main.hx": main})

        update = self.play[self.play.index("\toverride public function update("):]
        update = update[:update.index("\n\t}\n")]
        self.assertNotIn("healthTxt.setFormat(", update)
        self.assertIn("applyHealthTxtFormat(properHealth < 20 && !duoMode ? FlxColor.RED : FlxColor.WHITE);", update)
        self.assertIn("if (healthTxt.text != healthLabel)\n\t\t\thealthTxt.text = healthLabel;", update)
        self.assertIn("if (accuracyTxt.text != accuracyLabel)\n\t\t\t\taccuracyTxt.text = accuracyLabel;", update)
        self.assertNotIn('iconRPC = player', update)
        self.assertNotIn("dadcam = [", update)
        self.assertNotIn("bfcam = [", update)
        self.assertNotIn(".split('-')", update)
        self.assertNotIn('playingAsRpc = "Playing as', update)

    def test_sustain_clip_reuses_the_note_rect_with_the_same_geometry(self):
        start = self.play.index("\t\t\t\t\t\t\tvar swagRect = daNote.clipRect;")
        down = self.play[start:self.play.index("daNote.clipRect = swagRect;", start)]
        second = self.play.index("\t\t\t\t\t\t\tvar swagRect = daNote.clipRect;", start + 10)
        up = self.play[second:self.play.index("daNote.clipRect = swagRect;", second)]
        self.assertNotIn("new FlxRect(0, 0, daNote", self.play)
        main = r'''
class FlxRect {
 public var x:Float; public var y:Float; public var width:Float; public var height:Float;
 public function new(x:Float = 0, y:Float = 0, width:Float = 0, height:Float = 0) {
  this.x = x; this.y = y; this.width = width; this.height = height;
 }
}
class Note {
 public static var swagWidth:Float = 112 * 0.7;
 public var frameWidth:Int = 52; public var frameHeight:Int = 44;
 public var width:Float = 36.4; public var height:Float = 61.6; public var y:Float = 410.25;
 public var noteData:Int = 2; public var scale = {x: 0.7, y: 1.4};
 public var clipRect:FlxRect = null;
 public function new() {}
}
class Main {
 static function down(daNote:Note, daNoteStrums:Dynamic):FlxRect {
__DOWN__
  daNote.clipRect = swagRect;
  return swagRect;
 }
 static function up(daNote:Note, daNoteStrums:Dynamic):FlxRect {
__UP__
  daNote.clipRect = swagRect;
  return swagRect;
 }
 static function same(a:FlxRect, b:FlxRect, label:String):Void
  if (a.x != b.x || a.y != b.y || a.width != b.width || a.height != b.height)
   throw label + ' got ' + [a.x, a.y, a.width, a.height] + ' expected ' + [b.x, b.y, b.width, b.height];
 static function main() {
  var strums = {members: [{y: 50.0}, {y: 50.0}, {y: 57.5}, {y: 50.0}]};
  for (fresh in [true, false]) {
   var note = new Note();
   // A reused rect starts with stale values from an earlier frame.
   if (!fresh) note.clipRect = new FlxRect(-9, 99, 1, 2);
   var reused = note.clipRect;
   var oldDown = new FlxRect(0, 0, note.frameWidth * 2, note.frameHeight * 2);
   oldDown.height = (strums.members[Math.floor(Math.abs(note.noteData))].y + Note.swagWidth / 2 - note.y) / note.scale.y;
   oldDown.y = note.frameHeight - oldDown.height;
   var got = down(note, strums);
   same(got, oldDown, 'downscroll fresh=' + fresh);
   if (!fresh && got != reused) throw 'downscroll keeps the note rect';
   var oldUp = new FlxRect(0, 0, note.width / note.scale.x, note.height / note.scale.y);
   oldUp.y = (strums.members[Math.floor(Math.abs(note.noteData))].y + Note.swagWidth / 2 - note.y) / note.scale.y;
   oldUp.height -= oldUp.y;
   note.y = 12.75;
   oldUp = new FlxRect(0, 0, note.width / note.scale.x, note.height / note.scale.y);
   oldUp.y = (strums.members[Math.floor(Math.abs(note.noteData))].y + Note.swagWidth / 2 - note.y) / note.scale.y;
   oldUp.height -= oldUp.y;
   var gotUp = up(note, strums);
   same(gotUp, oldUp, 'upscroll fresh=' + fresh);
   if (gotUp != got) throw 'upscroll keeps the same note rect';
  }
 }
}
'''.replace("__DOWN__", down).replace("__UP__", up)
        self.run_haxe({"Main.hx": main})

    def test_nightmare_vision_snapshot_keeps_pass_order_and_nesting(self):
        take = extract_method(self.play, "\tfunction takeNightmareVisionNoteSnapshot(")
        release = extract_method(self.play, "\tfunction releaseNightmareVisionNoteSnapshot(")
        holds = extract_method(self.play, "\tfunction processNightmareVisionHolds(")
        autos = extract_method(self.play, "\tfunction processNightmareVisionAutoHits(")
        self.assertNotIn("notes.members.copy()", holds)
        self.assertNotIn("notes.members.copy()", autos)
        self.assertIn("releaseNightmareVisionNoteSnapshot(snapshot);\n\t}", holds)
        self.assertIn("var held = nightmareVisionHeldScratch;", holds)
        main = r'''
class Note { public var id:Int; public function new(id:Int) this.id = id; }
class Group { public var members:Array<Note> = []; public function new() {} }
class Main {
 var notes = new Group();
 var nightmareVisionNoteSnapshot:Array<Note> = [];
 var nightmareVisionNoteSnapshotBusy:Bool = false;
 public function new() {}
__TAKE__
__RELEASE__
 static function check(v:Bool, s:String):Void if (!v) throw s;
 static function main() {
  var game = new Main();
  for (id in 0...5) game.notes.members.push(new Note(id));
  var seen:Array<Int> = [];
  var snapshot = game.takeNightmareVisionNoteSnapshot();
  for (note in snapshot) {
   seen.push(note.id);
   // A hit removes notes from the group mid-pass; the pass still sees them.
   if (note.id == 1) { game.notes.members.remove(note); game.notes.members.remove(game.notes.members[2]); }
   if (note.id == 2) {
    var nested = game.takeNightmareVisionNoteSnapshot();
    check(nested != snapshot && nested.length == 3, 'a nested pass gets its own copy');
    game.releaseNightmareVisionNoteSnapshot(nested);
    check(game.nightmareVisionNoteSnapshotBusy, 'releasing the nested copy keeps the outer snapshot');
   }
  }
  check(seen.join(',') == '0,1,2,3,4', 'pass order ' + seen);
  game.releaseNightmareVisionNoteSnapshot(snapshot);
  check(!game.nightmareVisionNoteSnapshotBusy && snapshot.length == 0, 'released snapshot holds no notes');
  var again = game.takeNightmareVisionNoteSnapshot();
  check(again == snapshot && again.length == 3 && again[1].id == 2, 'next pass reuses the array with current members');
  game.releaseNightmareVisionNoteSnapshot(again);
 }
}
'''.replace("__TAKE__", take).replace("__RELEASE__", release)
        self.run_haxe({"Main.hx": main})

    def test_key_shit_sustain_passes_judge_timing_last(self):
        key_shit = extract_method(self.play, "\tprivate function keyShit(")
        self.assertNotIn("var daRating = Ratings.CalculateRating(", key_shit)
        self.assertIn("if (daNote.isSustainNote && !daNote.isLiftNote && coolShouldPress && daNote.canBeHit", key_shit)
        self.assertIn("if (daNote.isLiftNote && daNote.isSustainNote && coolShouldPress && daNote.canBeHit", key_shit)
        self.assertIn("&& Ratings.CalculateRating(Math.abs(daNote.strumTime - Conductor.songPosition)) == 'sick') {", key_shit)

    def test_nightmare_vision_renderer_is_looked_up_once_per_field(self):
        update = self.play[self.play.index("\toverride public function update("):]
        self.assertNotIn("nightmareVisionRenderer(field.ID, field).update", update[:update.index("\n\t}\n")])
        self.assertEqual(update[:update.index("\n\t}\n")].count(
            "if (renderer == null) renderer = nightmareVisionRenderer(field.ID, field);"), 3)


if __name__ == "__main__":
    unittest.main()
