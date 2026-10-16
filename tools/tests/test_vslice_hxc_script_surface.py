"""V-Slice script surface a stage, character and module of one mod rely on together.

Each probe is a shape the Tricky "Expurgation" scripts use and that was lowered
wrongly or left unplanned:

* `getProp(name)?.field = value` was left as an assignment to a lazy read.
* A character's actor-field pass rewrote a property name inside a quoted string
  (`["visible"]`), so a prop could never be hidden again.
* A private `FlxTimerManager` field lost its constructor.
* `FunkinSprite.create`, `createTextureAtlas` and `loadTextureAtlas` art was
  never planned for import, and the constructor chain had no atlas lowering.
* A prop's `isAnimationFinished`/`playAnimation` had no answer on a flixel or
  Animate sprite.
"""
import json
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

STAGE = r'''import funkin.play.stage.Stage;

class PropStage extends Stage {
    function new() { super('prop-stage'); }
    override function onCreate(event:ScriptEvent) {
        super.onCreate(event);
        for (i in ["handz", "skeleton"]) {
            var rim = new DropShadowShader();
            getNamedProp(i)?.shader = rim;
        }
        getNamedProp("skeleton")?.visible = false;
        getNamedProp("a")?.getChild("b")?.alpha = 0.5;
    }
}
'''

CHARACTER = r'''import flixel.util.FlxTimerManager;

class ClownCharacter extends MultiAnimateAtlasCharacter {
    function new() { super('clown'); }
    var timerMan:FlxTimerManager = new FlxTimerManager();
    function onCreate(event:ScriptEvent) {
        super.onCreate(event);
        currentStage.add(this);
        currentStage.refresh();
    }
    function playAnimation(name:String = false, restart:Bool = false, ignoreOther:Bool = false) {
        var stage = PlayState.instance.currentStage;
        switch (name) {
            case "singDOWN":
                stage.getNamedProp("handz")?.visible = true;
                stage.getNamedProp("handz")?.animation.play("down", true);
            default:
                stage.getNamedProp("handz")?.visible = false;
        }
        super.playAnimation(name, restart, ignoreOther);
    }
    function onUpdate(event:UpdateScriptEvent) {
        timerMan?.update(event?.elapsed ?? 0);
    }
}
'''

MODULE = r'''import flixel.util.FlxTimerManager;

class ClockModule extends Module {
    var timerMan:FlxTimerManager = new FlxTimerManager();
    var tweenMan:FlxTweenManager = new FlxTweenManager();
    var gremlin:FunkinSprite;
    function new() { super('ClockModule'); }
    function onSongLoaded(event:ScriptEvent) {
        gremlin = new FunkinSprite(0, 0).loadTextureAtlas("props/gremlin", "shared");
        var glow = FunkinSprite.create(0, 0, 'hud/glow');
        var atlas = FunkinSprite.createTextureAtlas(0, 0, 'props/signpost', 'shared');
        var viaPaths = Paths.getAnimateAtlas('props/viaPaths');
    }
    function onUpdate(event:UpdateScriptEvent) {
        timerMan.update(event.elapsed);
    }
}
'''

MAIN = '''import hscript.Parser;
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var stage = HxcCompat.analyze(%(stage)s, "scripts/stages/prop-stage.hxc");
    var stageText = stage.generatedHscript;
    if (stageText.indexOf("?.") >= 0 || stageText.indexOf("hxcOptionalField(function() { return getNamedProp(i); }, \\"shader\\") =") >= 0)
      fail("optional write on a call receiver stayed an assignment to a read: " + stageText);
    if (stageText.indexOf("hxcOptionalSet(getNamedProp(i), [\\"shader\\"], rim, \\"=\\")") < 0)
      fail("call receiver write was not lowered to the optional setter: " + stageText);
    if (stageText.indexOf("hxcOptionalSet(getNamedProp(\\"skeleton\\"), [\\"visible\\"], false, \\"=\\")") < 0)
      fail("literal-argument receiver write was not lowered: " + stageText);
    if (stageText.indexOf("hxcOptionalSet(hxcOptionalCall(getNamedProp(\\"a\\"), \\"getChild\\", [\\"b\\"]), [\\"alpha\\"], 0.5, \\"=\\")") < 0)
      fail("nested optional receiver write was not lowered: " + stageText);
    try { new Parser().parseString(stageText); }
    catch (error:Dynamic) fail("stage HScript does not parse: " + Std.string(error) + "\\n" + stageText);

    var character = HxcCompat.analyze(%(character)s, "scripts/characters/clown.hxc").generatedHscript;
    if (character.indexOf("\\"hxcCharacter()") >= 0)
      fail("actor field rewrite reached inside a string literal: " + character);
    if (character.indexOf("hxcOptionalSet(stage.getNamedProp(\\"handz\\"), [\\"visible\\"], false, \\"=\\")") < 0)
      fail("character prop write lost its property name: " + character);
    if (character.indexOf("PlayState.instance.curStage.add(") < 0 || character.indexOf("PlayState.instance.curStage.refresh()") < 0)
      fail("bare BaseCharacter.currentStage was not routed to the live stage: " + character);
    if (character.indexOf("var timerMan = new FlxTimerManager();") < 0)
      fail("character timer clock lost its constructor: " + character);
    try { new Parser().parseString(character); }
    catch (error:Dynamic) fail("character HScript does not parse: " + Std.string(error) + "\\n" + character);

    var module = HxcCompat.analyze(%(module)s, "scripts/modules/clock.hxc").generatedHscript;
    if (module.indexOf("var timerMan = new FlxTimerManager();") < 0)
      fail("module timer clock lost its constructor: " + module);
    if (module.indexOf("HxcCompatRuntime.createFunkinSpriteTextureAtlas(hxcAssetRoot, 0, 0, \\"props/gremlin\\", \\"shared\\")") < 0)
      fail("constructor chain loadTextureAtlas was not lowered to the Animate factory: " + module);
    if (module.indexOf(".loadTextureAtlas(") >= 0)
      fail("loadTextureAtlas call stayed on the placeholder sprite: " + module);

    var seen = new Map<String, Bool>();
    for (reference in HxcAssetPlanner.literalReferences(%(module)s))
      seen.set(reference.kind + ":" + reference.key, true);
    for (expected in ["frames:props/gremlin", "image:hud/glow", "frames:props/signpost", "frames:props/viaPaths"])
      if (!seen.exists(expected)) fail("asset plan misses " + expected + " in " + Std.string([for (key in seen.keys()) key]));
    Sys.println("surface-ok");
  }
}
'''


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class VSliceHxcScriptSurfaceTest(unittest.TestCase):
    def test_script_shapes_lower_and_plan_assets(self):
        main = MAIN % {
            'stage': json.dumps(STAGE),
            'character': json.dumps(CHARACTER),
            'module': json.dumps(MODULE),
        }
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(main, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=900)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn('surface-ok', result.stdout)

    def test_prop_animation_fallback_is_bound_to_the_optional_call(self):
        runtime = (ROOT / 'source/HxcCompatRuntime.hx').read_text()
        for method in ('isAnimationFinished', 'getCurrentAnimation', 'hasAnimation', 'playAnimation'):
            self.assertRegex(runtime, r"case '%s':" % method)
        play_state = (ROOT / 'source/PlayState.hx').read_text()
        self.assertRegex(play_state,
            r'function hxcOptionalCall\([^)]*\)[^{]*\{[^}]*?return HxcCompatRuntime\.spriteAnimationCall\(receiver, method, args\);',
            'an optional call on a sprite with no such method must fall back to the prop animation helpers')

    def test_is_in_countdown_starts_the_silent_lead_in(self):
        """A script that cancels the countdown and sets `isInCountdown = true`
        gets V-Slice's lead-in clock without the 3-2-1-Go."""
        play_state = (ROOT / 'source/PlayState.hx').read_text()
        setter = re.search(r'function set_isInCountdown\(value:Bool\):Bool \{(.*?)\n\t\}', play_state, re.S)
        self.assertIsNotNone(setter, 'isInCountdown setter is missing')
        self.assertIn('requestSilentPreRoll()', setter.group(1))
        request = re.search(r'function requestSilentPreRoll\(\):Void \{(.*?)\n\t\}', play_state, re.S)
        self.assertIsNotNone(request, 'silent pre-roll request is missing')
        body = request.group(1)
        # Already running or stopped by the script: nothing to start.
        self.assertRegex(body, r'if \(startedCountdown \|\| hxcCountdownStopRequested\)\s*return;')
        # A request made inside the countdownStart callback is read afterwards,
        # a later one (a script timer) restarts the countdown silently.
        self.assertIn('hxcScriptCountdownRequested = true;', body)
        self.assertIn('hxcSilentPreRoll = true;', body)
        self.assertIn('startCountdown();', body)
        # The restart does not announce the cancelled start a second time.
        self.assertRegex(play_state, r"if \(!silentPreRoll\)\s*callAllHScript\('countdownStart'")
        # A same-callback request continues instead of waiting for a script restart.
        self.assertRegex(play_state,
            r'if \(hxcScriptCountdownRequested && !hxcCountdownStopRequested\) \{[^}]*silentPreRoll = true;')
        # The clock still dances the cast but shows no countdown.
        self.assertRegex(play_state, r'if \(silentPreRoll\) \{\s*swagCounter \+= 1;\s*return;\s*\}')

    def test_finished_tap_confirm_settles_on_v_slice_receptors(self):
        """V-Slice drops a receptor back to static shortly after a tap's confirm
        animation ends, even with the key still down, and shows the held key's
        press pose; Psych keeps the glow lit until release. A sustain keeps its
        confirm while the hold lasts."""
        strumline = (ROOT / 'source/Strumline.hx').read_text()
        self.assertRegex(strumline, r'V_SLICE_CONFIRM_HOLD_TIME:Float = 0\.15;')
        settle = re.search(r'function settleFinishedConfirm\(elapsed:Float\):Void \{(.*?)\n\t\}', strumline, re.S)
        self.assertIsNotNone(settle, 'settleFinishedConfirm is missing')
        body = settle.group(1)
        self.assertIn("current.name != 'confirm' && current.name != 'confirmHold'", body)
        self.assertIn('!current.finished', body)
        self.assertIn('confirmFromSustain', body)
        self.assertIn("playAnim('static', true);", body)
        self.assertRegex(strumline, r'public var settlesConfirm\(get, never\):Bool;\s*function get_settlesConfirm\(\):Bool\s*return usesVSliceGeometry;')
        # A confirm requested without the sustain flag never inherits the old one.
        self.assertRegex(strumline,
            r"if \(anim == 'confirm' \|\| anim == 'confirmHold'\) \{\s*confirmationGeneration\+\+;\s*confirmFromSustain = false;")
        play_state = (ROOT / 'source/PlayState.hx').read_text()
        self.assertRegex(play_state,
            r"else if \(sourceLine == null && spr\.settlesConfirm && holdArray\[spr\.ID\] && strumAnimationName == 'static'\)\s*spr\.playAnim\('pressed'\);")
        self.assertRegex(strumline, r'public function endSustainConfirm\(\):Void\s*confirmFromSustain = false;')
        self.assertRegex(play_state,
            r'spr\.settlesConfirm && spr\.holdsSustainConfirm\s*&& !laneHasLiveSustain\(spr\.ID, playerOne\)\)\s*spr\.endSustainConfirm\(\);')
        live = extract_method(play_state, 'function laneHasLiveSustain(')
        for part in ('piece.isSustainNote', 'piece.noteData == lane', 'piece.mustPress == playerOne',
                     '!piece.wasGoodHit', '!piece.tooLate'):
            self.assertIn(part, live)
        confirm = extract_method(strumline, 'public function playConfirm(hold:Bool = false')
        fixture = """class Anim { public var name:String; public var finished:Bool = false; public function new(name:String) this.name = name; }
class Controller {
	public var curAnim:Anim;
	public function new() {}
	public function exists(name:String):Bool return name != 'noHold';
}
class Strum {
	public var animation:Controller = new Controller();
	var confirmFinishedTime:Float = 0;
	var confirmFromSustain:Bool = false;
	public static inline var V_SLICE_CONFIRM_HOLD_TIME:Float = 0.15;
	public var log:Array<String> = [];
	public function new() animation.curAnim = new Anim('static');
	public function playAnim(anim:String, force:Bool = false):Void {
		log.push(anim);
		animation.curAnim = new Anim(anim);
		if (anim == 'confirm' || anim == 'confirmHold') confirmFromSustain = false;
	}
	function settleFinishedConfirm(elapsed:Float):Void {
""" + body + """
	}
	""" + confirm + """
	public function tick(elapsed:Float, finish:Bool):Void {
		if (finish) animation.curAnim.finished = true;
		settleFinishedConfirm(elapsed);
	}
	public function current():String return animation.curAnim.name;
}
class Main {
	static function fail(message:String):Void throw message;
	static function main():Void {
		var tap = new Strum();
		tap.playConfirm(false);
		tap.tick(0.05, false);
		tap.tick(0.05, true);
		tap.tick(0.05, true);
		if (tap.current() != 'confirm') fail('a tap confirm settled before its hold time');
		tap.tick(0.06, true);
		if (tap.current() != 'static') fail('a finished tap confirm stayed lit with the key down');
		var hold = new Strum();
		hold.playConfirm(true);
		hold.tick(0.05, true);
		hold.tick(1.0, true);
		if (hold.current() != 'confirmHold') fail('a sustain confirm settled while the hold lasts');
		hold.playConfirm(false);
		hold.tick(0.05, true);
		hold.tick(0.2, true);
		if (hold.current() != 'static') fail('a tap after a sustain did not settle');
		var plain = new Strum();
		plain.playConfirm(true);
		plain.tick(0.5, false);
		if (plain.current() != 'confirmHold') fail('an unfinished confirm settled');
	}
}
"""
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        update = re.search(r'override public function update\(elapsed:Float\):Void \{\r?\n\t\tsuper\.update\(elapsed\);\r?\n\t\tif \(nightmareVisionOffsets(.*?)\n\t\}',
            strumline, re.S)
        self.assertIsNotNone(update, 'receptor update is missing')
        self.assertRegex(update.group(1), r'if \(usesVSliceGeometry\) \{[^}]*settleFinishedConfirm\(elapsed\);')

    def test_hidden_v_slice_strumline_hides_its_notes(self):
        """V-Slice scripts hide a line with `opponentStrumline.visible = false`, and
        the notes of that line are part of the strumline group there."""
        play_state = (ROOT / 'source/PlayState.hx').read_text()
        self.assertRegex(play_state,
            r'var daNoteStrums = getNoteStrumline\(daNote\);\s*if \(daNoteStrums == null\) return;[^}]*?'
            r'if \(hxcCompatScriptsLoaded && !daNoteStrums\.visible\)\s*daNote\.visible = false;')

    def test_script_clock_is_native_class(self):
        catalog = (ROOT / 'source/ScriptNativeClasses.hx').read_text()
        self.assertRegex(catalog, r"entry\('FlxTimerManager', 'flixel\.util\.FlxTimerManager'")


if __name__ == '__main__':
    unittest.main()
