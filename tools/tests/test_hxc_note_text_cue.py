"""Structural and runtime-boundary tests for bounded HXC note-text cues."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
STATIC_TEXT = Path(
    "/run/media/cammie/External Storage/FNF-Example-Mods/"
    "v-slice/Vs Tricky/scripts/modules/StaticTextHandler.hxc"
)


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


SYNTHETIC = r'''
class UnrelatedLabelModule extends Module {
    var cueKeys = ["one-song", "second-song"];
    var odds = [12, 37];
    var visible = false;
    var startedAt = 0;
    var label;
    var resetAllowed = true;

    function onNoteHit(hit) {
        if (hit.judgement == "perfect") {
            if (FlxG.random.bool(odds[cueKeys.indexOf(PlayState.instance.currentChart.song.id)]) && !visible)
                showLabel(getCopy(), null, null);
        }
    }

    function onUpdate(frame) {
        if (visible && startedAt + 4 < Conductor.instance.currentStep) {
            if (resetAllowed) {
                if (label != null && PlayState.instance.members.indexOf(label) != -1)
                    PlayState.instance.remove(label);
                PlayState.instance.currentStage.refresh();
                visible = false;
            }
        }
    }

    function showLabel(copies:Array<String>, setX:Float, setY:Float):Void {
        startedAt = Conductor.instance.currentStep;
        visible = true;
        if (copies.length > 0) {
            var selected = copies[FlxG.random.int(0, copies.length - 1)];
            var stage = PlayState.instance.currentStage;
            label = new FlxText(setX != null ? setX : stage.getDad().x + FlxG.random.float(18, 74),
                setY != null ? setY : stage.getDad().y + FlxG.random.float(90, 190));
            label.setFormat(Paths.font("font/impact.ttf"), 42, 0xFF123456);
            label.bold = true;
            label.zIndex = 814;
            label.text = selected;
            PlayState.instance.add(label);
            PlayState.instance.currentStage.refresh();
        }
    }

    function getCopy():Array<String> {
        switch (cueKeys.indexOf(PlayState.instance.currentChart.song.id)) {
            case 0: ["FIRST", "OTHER"];
            case 1: [];
        }
    }
}
'''

SYNTHETIC_MISS = SYNTHETIC.replace(
    'var startedAt = 0;',
    'var missCopies = ["MISS ONE", "MISS TWO"];\n    var startedAt = 0;',
).replace(
    '    function onUpdate(frame) {',
    '''    function onNoteMiss(missed) {
        if (FlxG.random.bool(PlayState.instance.currentChart.song.id == "second-song" ? 17 : 0) && !visible)
            showLabel(missCopies, null, null);
    }

    function onUpdate(frame) {''',
)


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain is not mounted")
class HxcNoteTextCueTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(prefix="hxc-note-text-") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            env = os.environ.copy()
            for name in (
                "DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "XAUTHORITY", "XDG_RUNTIME_DIR"
            ):
                env.pop(name, None)
            return subprocess.run(
                [
                    str(HAXE), "-cp", str(ROOT / "source"),
                    "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                    "-cp", folder, "-main", "Main", "--interp",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_renamed_module_extracts_data_and_runs_only_the_owner_abi(self):
        main = f'''import hscript.Interp;
import hscript.Parser;
class PlayState {{
  public static var instance:PlayState;
  public var mountedRoot:String = "";
  public var mountedSpec:Dynamic;
  public var handle:Dynamic = {{token: "module-local"}};
  public var hits:Int = 0;
  public var resets:Int = 0;
  public var clears:Int = 0;
  public var receivedEvent:Dynamic;
  public function new() {{}}
  public function hxcMountNoteTextCue(root:String, spec:Dynamic):Dynamic {{
    mountedRoot = root; mountedSpec = spec; return handle;
  }}
  public function hxcTriggerNoteTextCue(value:Dynamic, event:Dynamic):Bool {{
    if (value != handle) return false; hits++; receivedEvent = event; return true;
  }}
  public function hxcResetNoteTextCue(value:Dynamic):Bool {{ if (value != handle) return false; resets++; return true; }}
  public function hxcClearNoteTextCue(value:Dynamic):Bool {{ if (value != handle) return false; clears++; return true; }}
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(SYNTHETIC)}, "some/other/module/UnrelatedLabelModule.hxc");
    if (result.kind != "module" || result.noteTextSpec == null || !result.moduleSafe
      || !result.moduleInitializationSafe) fail("renamed shape did not become a safe data adapter");
    var spec:Dynamic = result.noteTextSpec;
    if (spec.rules.length != 2 || spec.rules[0].songId != "one-song"
      || spec.rules[0].chancePercent != 12 || spec.rules[1].chancePercent != 37)
      fail("connected song/chance tables lost their order");
    if (spec.rules[0].lines.length != 2 || spec.rules[1].lines.length != 0
      || spec.lifetimeSteps != 4 || spec.expireStrictlyAfter != true
      || spec.anchor != "opponent" || spec.font != "font/impact.ttf"
      || spec.fontSize != 42 || spec.color != 0xFF123456 || spec.zIndex != 814)
      fail("style/lifetime data missing");
    if (HxcNoteTextSpec.isExpired(10, 14, spec) != false
      || HxcNoteTextSpec.isExpired(10, 15, spec) != true)
      fail("strict expiry must keep the cue through start + lifetime and clear on the next step");
    if (!HxcNoteTextSpec.appliesToSong("one-song", spec)
      || HxcNoteTextSpec.appliesToSong("One-Song", spec)
      || HxcNoteTextSpec.appliesToSong("missing", spec))
      fail("song membership must use exact identifier equality");
    var caseSensitive = HxcNoteTextSpec.fromDynamic({{rules: [{{songId: "One-Song",
      chancePercent: 1, lines: ["line"]}}], triggerJudgement: "perfect", perfectOnly: true,
      onceAtATime: true, lifetimeSteps: 3, expireStrictlyAfter: true, anchor: "opponent",
      xOffsetMin: 1, xOffsetMax: 2, yOffsetMin: 3, yOffsetMax: 4,
      font: "font.ttf", fontSize: 16, color: 0, bold: true, zIndex: 1}});
    if (caseSensitive == null || caseSensitive.rules[0].songId != "One-Song")
      fail("song identifiers were normalized instead of preserved exactly");
    var overlay = {{image: "images/effects/static.png", frameWidth: 320, frameHeight: 180,
      frames: [0, 1, 2], fps: 24, loop: true, scaleX: 8, scaleY: 8, camera: "hud",
      idleAlpha: 0, hitAlpha: 0.5, flickerMin: 0.1, flickerMax: 0.5,
      sound: "sounds/staticSound.ogg"}};
    var emptyLines = HxcNoteTextSpec.fromDynamic({{rules: [
      {{songId: "visible", chancePercent: 1, lines: ["line"]}},
      {{songId: "empty-lines", chancePercent: 1, lines: []}}],
      triggerJudgement: "perfect", perfectOnly: true, onceAtATime: true,
      lifetimeSteps: 3, expireStrictlyAfter: true, anchor: "opponent",
      xOffsetMin: 1, xOffsetMax: 2, yOffsetMin: 3, yOffsetMax: 4,
      font: "font.ttf", fontSize: 16, color: 0, bold: true, zIndex: 1,
      staticOverlay: overlay}});
    if (emptyLines == null || emptyLines.staticOverlay == null
      || !HxcNoteTextSpec.appliesToSong("empty-lines", emptyLines)
      || HxcNoteTextSpec.appliesToSong("EMPTY-LINES", emptyLines))
      fail("empty-line cue must still select its exact song and static overlay");
    overlay.image = "images/../outside.png";
    var traversal = HxcNoteTextSpec.fromDynamic({{rules: emptyLines.rules,
      triggerJudgement: "perfect", perfectOnly: true, onceAtATime: true,
      lifetimeSteps: 3, expireStrictlyAfter: true, anchor: "opponent",
      xOffsetMin: 1, xOffsetMax: 2, yOffsetMin: 3, yOffsetMax: 4,
      font: "font.ttf", fontSize: 16, color: 0, bold: true, zIndex: 1,
      staticOverlay: overlay}});
    if (traversal != null) fail("traversing static-overlay image path accepted");
    if (result.generatedHscript.indexOf("new FlxText") >= 0
      || result.generatedHscript.indexOf("FlxG.random") >= 0
      || result.generatedHscript.indexOf("getCopy") >= 0
      || result.generatedHscript.indexOf("showLabel") >= 0
      || result.generatedHscript.indexOf("staticSpr") >= 0)
      fail("foreign graph leaked into generated HScript: " + result.generatedHscript);
    for (name in ["mountNoteTextCue", "triggerNoteTextCue", "resetNoteTextCue", "clearNoteTextCue"])
      if (result.generatedHscript.indexOf(name) < 0) fail("missing owner ABI " + name);
    new Parser().parseString(result.generatedHscript);

    PlayState.instance = new PlayState();
    var interp = new Interp();
    interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    interp.variables.set("PlayState", PlayState);
    interp.variables.set("hxcAssetRoot", "assets/imported_mods/fixture");
    interp.execute(new Parser().parseString(result.generatedHscript));
    Reflect.callMethod(null, interp.variables.get("songLoaded"), [null]);
    if (PlayState.instance.mountedRoot != "assets/imported_mods/fixture"
      || PlayState.instance.mountedSpec == null) fail("module did not mount through the owner");
    var event = {{judgement: "perfect"}};
    Reflect.callMethod(null, interp.variables.get("noteHit"), [event]);
    if (PlayState.instance.hits != 1 || PlayState.instance.receivedEvent != event)
      fail("shared HXC note payload was not forwarded");
    Reflect.callMethod(null, interp.variables.get("songRetry"), [null]);
    if (PlayState.instance.resets != 1) fail("retry did not reset the cue");
    Reflect.callMethod(null, interp.variables.get("destroy"), []);
    if (PlayState.instance.clears != 1) fail("destroy did not clear the cue");

    var invalid = HxcNoteTextSpec.fromDynamic({{rules: spec.rules, triggerJudgement: "perfect",
      perfectOnly: true, onceAtATime: true, lifetimeSteps: 4, expireStrictlyAfter: false,
      anchor: "opponent", xOffsetMin: 18, xOffsetMax: 74, yOffsetMin: 90, yOffsetMax: 190,
      font: "font/impact.ttf", fontSize: 42, color: 0xFF123456, bold: true, zIndex: 814}});
    if (invalid != null) fail("non-strict expiry spec accepted");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_static_text_module_is_read_only_and_preserves_strict_expiry(self):
        if not STATIC_TEXT.is_file():
            self.skipTest("Vs Tricky StaticTextHandler donor is not mounted")
        before = STATIC_TEXT.read_bytes()
        source = STATIC_TEXT.read_text(errors="ignore")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "mounted/donor/StaticTextHandler.hxc");
    if (result.noteTextSpec == null || !result.moduleSafe || !result.moduleInitializationSafe)
      fail("mounted text spec missing: " + result.moduleSafetyReasons.join(","));
    if (!result.payloadSafe) fail("bounded text callbacks retained a donor payload gap");
    for (finding in result.diagnostics)
      if (finding.code == "unsupported-hxc-payload")
        fail("bounded text callbacks emitted an obsolete payload warning");
    var spec:Dynamic = result.noteTextSpec;
    if (spec.rules.length != 4 || spec.rules[0].chancePercent != 2
      || spec.rules[1].chancePercent != 20 || spec.rules[2].chancePercent != 45
      || spec.rules[3].chancePercent != 60 || spec.rules[2].lines.length != 0
      || spec.rules[3].lines.length != 9) fail("mounted literal tables changed");
    if (spec.lifetimeSteps != 3 || spec.expireStrictlyAfter != true
      || spec.xOffsetMin != 40 || spec.xOffsetMax != 120
      || spec.yOffsetMin != 200 || spec.yOffsetMax != 300
      || spec.font != "impact.ttf" || spec.fontSize != 128
      || spec.color != 0xFFFF0000 || spec.zIndex != 3502)
      fail("mounted style or strict lifetime changed");
    if (spec.missRules == null || spec.missRules.length != 1
      || spec.missRules[0].songId != "madness"
      || spec.missRules[0].chancePercent != 10
      || spec.missRules[0].lines.length != 12
      || spec.missRules[0].lines[0] != "TERRIBLE")
      fail("bounded miss text branch was not extracted");
    var overlay:Dynamic = spec.staticOverlay;
    if (overlay == null || overlay.image != "images/bgs/TrickyStatic.png"
      || overlay.frameWidth != 320 || overlay.frameHeight != 180
      || overlay.frames.length != 3 || overlay.frames[0] != 0 || overlay.frames[2] != 2
      || overlay.fps != 24 || !overlay.loop || overlay.scaleX != 8 || overlay.scaleY != 8
      || overlay.camera != "hud" || overlay.idleAlpha != 0 || overlay.hitAlpha != 0.5
      || overlay.flickerMin != 0.1 || overlay.flickerMax != 0.5
      || overlay.sound != "sounds/staticSound.ogg")
      fail("mounted static overlay descriptor incomplete");
    if (!HxcNoteTextSpec.appliesToSong("hellclown", spec)
      || HxcNoteTextSpec.appliesToSong("Hellclown", spec))
      fail("empty-line static-overlay song must be matched exactly");
    if (HxcNoteTextSpec.isExpired(100, 103, spec)
      || !HxcNoteTextSpec.isExpired(100, 104, spec))
      fail("donor expiry boundary must leave start + 3 visible and clear at start + 4");
    if (result.generatedHscript.indexOf("triggerMissNoteTextCue") < 0
      || result.generatedHscript.indexOf("new FlxText") >= 0
      || result.generatedHscript.indexOf("FunkinSound") >= 0
      || result.generatedHscript.indexOf("staticSpr") >= 0)
      fail("unsupported donor effects leaked into generated HScript");
    if (result.generatedHscript.indexOf("staticOverlay: {{image: \\\"images/bgs/TrickyStatic.png\\\"") < 0
      || result.generatedHscript.indexOf("sound: \\\"sounds/staticSound.ogg\\\"") < 0
      || result.generatedHscript.indexOf("camera: \\\"hud\\\"") < 0)
      fail("static overlay data was not emitted as a literal descriptor");
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(STATIC_TEXT.read_bytes(), before, "mounted donor changed")

    def test_renamed_miss_rule_uses_owner_callback_and_rejects_unbounded_variants(self):
        main = f'''import hscript.Interp;
import hscript.Parser;
class PlayState {{
  public static var instance:PlayState;
  public var handle:Dynamic = {{token: 1}};
  public var misses:Int = 0;
  public var received:Dynamic;
  public function new() {{}}
  public function hxcMountNoteTextCue(root:String, spec:Dynamic):Dynamic return handle;
  public function hxcTriggerNoteTextCue(value:Dynamic, event:Dynamic):Bool return false;
  public function hxcTriggerMissNoteTextCue(value:Dynamic, event:Dynamic):Bool {{
    if (value != handle) return false;
    misses++; received = event; return true;
  }}
  public function hxcResetNoteTextCue(value:Dynamic):Bool return true;
  public function hxcClearNoteTextCue(value:Dynamic):Bool return true;
}}
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    var source = {hx_string(SYNTHETIC_MISS)};
    var result = HxcCompat.analyze(source, "unrelated/label.hxc");
    if (result.noteTextSpec == null || result.noteTextSpec.missRules == null
      || result.noteTextSpec.missRules.length != 1
      || result.noteTextSpec.missRules[0].songId != "second-song"
      || result.noteTextSpec.missRules[0].chancePercent != 17
      || result.noteTextSpec.missRules[0].lines[1] != "MISS TWO")
      fail("renamed miss branch was not extracted");
    if (!HxcNoteTextSpec.appliesToSong("second-song", result.noteTextSpec))
      fail("miss song must be within mountable song scope");
    var duplicate:Dynamic = Reflect.copy(result.noteTextSpec);
    duplicate.missRules = [result.noteTextSpec.missRules[0], result.noteTextSpec.missRules[0]];
    if (HxcNoteTextSpec.fromDynamic(duplicate) != null)
      fail("duplicate miss entries were accepted");
    var foreign:Dynamic = Reflect.copy(result.noteTextSpec);
    foreign.missRules = [{{songId: "outside", chancePercent: 17, lines: ["MISS"]}}];
    if (HxcNoteTextSpec.fromDynamic(foreign) != null)
      fail("miss entry outside mounted hit song scope was accepted");
    if (result.generatedHscript.indexOf("triggerMissNoteTextCue") < 0
      || result.generatedHscript.indexOf("new FlxText") >= 0)
      fail("miss route did not stay behind owner ABI");
    PlayState.instance = new PlayState();
    var interp = new Interp();
    interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    interp.variables.set("PlayState", PlayState);
    interp.variables.set("hxcAssetRoot", "assets/imported_mods/fixture");
    interp.execute(new Parser().parseString(result.generatedHscript));
    Reflect.callMethod(null, interp.variables.get("songLoaded"), [null]);
    var event = {{judgement: "miss"}};
    Reflect.callMethod(null, interp.variables.get("noteMiss"), [event]);
    if (PlayState.instance.misses != 1 || PlayState.instance.received != event)
      fail("miss payload was not passed to owner");
    var unsafeSource = StringTools.replace(source,
      'PlayState.instance.currentChart.song.id == "second-song" ? 17 : 0',
      'PlayState.instance.currentChart.song.id == "second-song" ? unknownChance : 0');
    var unsafe = HxcCompat.analyze(unsafeSource, "unrelated/label.hxc");
    if (unsafe.noteTextSpec == null || unsafe.noteTextSpec.missRules != null
      || unsafe.generatedHscript.indexOf("triggerMissNoteTextCue") >= 0)
      fail("dynamic chance escaped bounded miss detection");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_owner_pins_strict_step_boundary_and_teardown_cleanup(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        runtime = (ROOT / "source/HxcCompatRuntime.hx").read_text()
        expiry_start = play_state.index("function hxcExpireNoteTextCues()")
        expiry_end = play_state.index("function hxcClearAllNoteTextCues()", expiry_start)
        expiry = play_state[expiry_start:expiry_end]
        self.assertIn("HxcNoteTextSpec.isExpired(cue.startStep, curStep, cue.spec)", expiry)
        self.assertIn("HxcNoteTextSpec.appliesToSong(songId, spec)", play_state)
        trigger_start = play_state.index("function hxcTriggerNoteTextCue(")
        trigger_end = play_state.index("function hxcResetNoteTextCue(", trigger_start)
        trigger = play_state[trigger_start:trigger_end]
        text_block_start = trigger.index("if (lines.length > 0)")
        text_block_open = trigger.index("{", text_block_start)
        depth = 1
        cursor = text_block_open + 1
        while cursor < len(trigger) and depth > 0:
            if trigger[cursor] == "{":
                depth += 1
            elif trigger[cursor] == "}":
                depth -= 1
            cursor += 1
        text_block = trigger[text_block_open:cursor]
        self.assertNotIn("overlay.alpha = overlaySpec.hitAlpha", text_block)
        self.assertNotIn("FlxG.sound.play", text_block)
        self.assertLess(text_block_start, trigger.index("handle.active = true"))
        self.assertIn("overlay.alpha = overlaySpec.hitAlpha", trigger)
        self.assertIn("hxcClearAllNoteTextCues();", play_state)
        self.assertIn("Reflect.callMethod(state, method, [handle, event])", runtime)
        self.assertIn("HxcNoteTextSpec.fromDynamic(spec)", runtime)


if __name__ == "__main__":
    unittest.main()
