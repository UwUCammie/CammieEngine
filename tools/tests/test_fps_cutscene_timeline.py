"""Bounded, data-only extraction coverage for the mounted FPS Plus cutscenes."""
from haxe_test_support import HAXE_COMMAND

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods/whitty")
CUTSCENES = {
    name: DONOR / "data/cutscenes" / f"{name}.hxc"
    for name in ("BallisticIntro", "LoFightIntro", "OverheadIntro")
}


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


class FpsCutsceneTimelineTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        build_tmp = ROOT / "tmp"
        build_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build_tmp) as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source, newline='\n')
            command = [
                *HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                "-main", "Main", "--interp",
            ]
            environment = os.environ.copy()
            environment["TMPDIR"] = str(build_tmp)
            return subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_renamed_constructor_shape_is_lowered_without_execution(self):
        donor = r'''
class RenamedIntro extends ScriptedCutscene {
    var originalZoom:Float;
    var dialogueBox:DialogueBox;

    function new(args:Array<Dynamic>) {
        super(args);
        var dialogue = Json.parse(Utils.getText(Paths.json("dialogue", "data/songs/" + PlayState.SONG.song.toLowerCase())));
        var dialogueBgColor = 0xFFB3DFD8;
        dialogueBox = new DialogueBox(dialogue, dialogueBgColor);
        dialogueBox.onDialogueEnd.add(function(d) {
            new FlxTimer().start(0.5, function(tmr:FlxTimer) {
                next();
                playstate.camChangeZoom(originalZoom, (Conductor.crochet / 1000) * 5, FlxEase.quadInOut);
                focusCameraBasedOnFirstSection();
                playstate.camGame.filters.remove(fadeInShaderFilter);
            });
        });
        dialogueBox.cameras = [playstate.camHUD];
        addGeneric(dialogueBox);
        originalZoom = playstate.defaultCamZoom;
        playstate.camMove(10, 20, null);
        addEvent(0, first);
        addEvent(0, second);
        addEvent(Conductor.crochet / 1000 * 2, third);
    }

    function first() { startDialogue(); }
    function second() { playstate.camChangeZoom(1.5, 0.4, FlxEase.quadInOut); }
    function third() { FlxG.sound.play(Paths.sound("beep")); }
}
'''
        main = f'''import HxcCutsceneTimeline.HxcCutsceneTimelineData;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "assets/data/cutscenes/renamed/RenamedIntro.hxc");
    if (result.kind != "cutscene" || result.cutsceneTimeline == null)
      fail("renamed cutscene was not accepted");
    var timeline:HxcCutsceneTimelineData = result.cutsceneTimeline;
    if (timeline.sourceClass != "RenamedIntro" || timeline.sourcePath != "data/cutscenes/renamed/RenamedIntro.hxc")
      fail("manifest/class provenance was not normalized: " + timeline.sourcePath);
    if (timeline.dialoguePath != "data/songs/{{song}}/dialogue.json" || timeline.initialActions.length != 3)
      fail("dialogue/initial action schema mismatch");
    if (timeline.events.length != 3 || timeline.events[0].callback != "first"
      || timeline.events[1].callback != "second" || timeline.events[2].callback != "third")
      fail("event order was not retained");
    if (timeline.events[0].at.source != "0" || timeline.events[1].at.source != "0"
      || timeline.events[2].at.kind != "crochet-multiplier" || timeline.events[2].at.value != 2)
      fail("literal/symbolic timestamp lowering mismatch");
    if (timeline.events[0].actions[0].kind != "dialogueStart"
      || timeline.events[1].actions[0].kind != "cameraZoom"
      || timeline.events[2].actions[0].kind != "soundPlay")
      fail("action lowering mismatch");
    if (timeline.dialogueEnd.length != 4 || timeline.assets.length != 1
      || timeline.assets[0].key != "sounds/beep")
      fail("completion/assets schema mismatch");
    Sys.println("OK");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_unsafe_dynamic_path_is_diagnosed_and_not_partially_emitted(self):
        donor = r'''
class UnsafeRenamed extends ScriptedCutscene {
    var dialogueBox:DialogueBox;

    function new(args:Array<Dynamic>) {
        super(args);
        var dialogue = Json.parse(Utils.getText(Paths.json("dialogue", "data/songs/" + PlayState.SONG.song.toLowerCase())));
        var dialogueBgColor = 0xFFB3DFD8;
        dialogueBox = new DialogueBox(dialogue, dialogueBgColor);
        dialogueBox.onDialogueEnd.add(function(d) {
            new FlxTimer().start(0.5, function(tmr:FlxTimer) { next(); });
        });
        addEvent(0, playUnsafe);
    }

    function playUnsafe() {
        FlxG.sound.play(Paths.sound(dynamicName));
    }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "assets/data/cutscenes/unsafe.hxc");
    var dynamicPath = false;
    for (finding in result.diagnostics)
      if (finding.code == "unsupported-hxc-cutscene-dynamic-path") dynamicPath = true;
    if (result.cutsceneTimeline != null || !dynamicPath)
      fail("unsafe dynamic path was accepted or silently dropped");
    Sys.println("OK");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_mounted_cutscenes_extract_exactly_and_leave_donors_unchanged(self):
        missing = [path for path in CUTSCENES.values() if not path.is_file()]
        if missing:
            # The FPS Plus donor (whitty) is no longer part of the mounted
            # donor library; the extraction contract stays covered by the
            # synthetic fixtures above.
            self.skipTest(f"mounted FPS Plus cutscene fixtures are unavailable: {missing[0]}")
        before = {
            name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
            for name, path in CUTSCENES.items()
        }
        calls = "\n".join(
            f'    emit("{name}", {hx_string(str(path))});'
            for name, path in CUTSCENES.items()
        )
        main = f'''import HxcCutsceneTimeline.HxcCutsceneTimelineData;
class Main {{
  static function actions(timeline:HxcCutsceneTimelineData):Int {{
    var total = timeline.initialActions.length + timeline.dialogueEnd.length;
    for (event in timeline.events) total += event.actions.length;
    return total;
  }}
  static function emit(name:String, path:String):Void {{
    var result = HxcCompat.analyze(sys.io.File.getContent(path), path);
    var timeline = result.cutsceneTimeline;
    Sys.println("RESULT|" + name + "|" + result.kind + "|"
      + (timeline == null ? "null" : Std.string(timeline.events.length)) + "|"
      + (timeline == null ? "null" : Std.string(actions(timeline))) + "|"
      + (timeline == null ? "" : timeline.sourcePath));
    if (timeline != null) {{
      var events:Array<String> = [];
      var actionKinds:Array<String> = [];
      var assets:Array<String> = [];
      for (event in timeline.events) {{
        var kinds:Array<String> = [];
        for (action in event.actions) {{
          kinds.push(action.kind);
          actionKinds.push(event.callback + "=" + action.kind);
        }}
        events.push(event.callback + ":" + event.at.source + ":" + event.actions.length + ":" + kinds.join(","));
      }}
      for (asset in timeline.assets) assets.push(asset.kind + ":" + asset.key);
      var initialKinds:Array<String> = [];
      for (action in timeline.initialActions) initialKinds.push(action.kind);
      var endKinds:Array<String> = [];
      for (action in timeline.dialogueEnd) endKinds.push(action.kind);
      Sys.println("INITIAL|" + name + "|" + initialKinds.join(","));
      Sys.println("END|" + name + "|" + endKinds.join(","));
      Sys.println("EVENTS|" + name + "|" + events.join(";"));
      Sys.println("ACTIONS|" + name + "|" + actionKinds.join(","));
      Sys.println("ASSETS|" + name + "|" + assets.join(","));
    }}
    var codes:Array<String> = [];
    for (finding in result.diagnostics)
      codes.push(finding.code + ":" + finding.severity);
    Sys.println("CODES|" + name + "|" + codes.join(","));
  }}
  static function main() {{
    if (ImportDiagnostic.label("[hxc-cutscene-adapter-engine-owned] inherited") != "[INFO]"
      || ImportDiagnostic.label("[hxc-cutscene-adapter-no-op] skipped") != "[INFO]")
      throw "accepted cutscene adapter findings were not classified as informational";
{calls}
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        rows = {}
        for line in output.splitlines():
            if line.startswith("RESULT|"):
                _, name, kind, events, actions, source = line.split("|", 5)
                rows[name] = {
                    "kind": kind,
                    "events": events,
                    "actions": actions,
                    "source": source,
                }
        self.assertEqual(set(rows), set(CUTSCENES))
        self.assertEqual(rows["BallisticIntro"], {
            "kind": "cutscene", "events": "11", "actions": "44",
            "source": "data/cutscenes/BallisticIntro.hxc",
        })
        self.assertEqual(rows["LoFightIntro"], {
            "kind": "cutscene", "events": "6", "actions": "30",
            "source": "data/cutscenes/LoFightIntro.hxc",
        })
        self.assertEqual(rows["OverheadIntro"]["kind"], "cutscene")
        self.assertEqual(rows["OverheadIntro"]["events"], "1")
        self.assertEqual(rows["OverheadIntro"]["actions"], "9")
        self.assertEqual(rows["OverheadIntro"]["source"], "data/cutscenes/OverheadIntro.hxc")
        self.assertIn("INITIAL|BallisticIntro|dialogueConfig,spriteDefine,spriteDefine,captureDefaultZoom,cameraMove,cameraZoom", output)
        self.assertIn("INITIAL|LoFightIntro|dialogueConfig,spriteDefine,captureDefaultZoom,cameraMove,cameraZoom", output)
        self.assertIn("INITIAL|OverheadIntro|dialogueConfig,captureDefaultZoom", output)
        self.assertIn("END|BallisticIntro|handoff,cameraZoom,focusFirstSection,removeOwnedFilter,musicFadeOut", output)
        self.assertIn("END|LoFightIntro|handoff,musicFadeOut,cameraZoom,focusFirstSection,removeOwnedFilter,musicFadeOut", output)
        self.assertIn("END|OverheadIntro|handoff,musicFadeOutSkipped,cameraZoom,focusFirstSection,removeOwnedFilter,musicFadeOut", output)
        self.assertIn(
            "EVENTS|BallisticIntro|intro:0:8:spriteAdd,spriteAdd,spriteAnimation,spriteAnimation,visibility,soundPlay,cameraZoom,visibility;"
            "mbreak:2.166666666666667:3:soundPlay,cameraZoom,cameraShake;"
            "yyy:3.333333333333333:1:cameraMove;"
            "mslam:3.583333333333333:2:soundPlay,cameraMove;"
            "mthrow:3.625:1:soundPlay;"
            "rumble:5.125:2:soundPlay,cameraMove;"
            "solja:5.333333333333333:3:soundPlay,spriteAnimation,cameraShake;"
            "twt:6.458333333333333:1:cameraZoom;"
            "toe:6.583333333333333:3:soundPlay,cameraShake,cameraZoom;"
            "flash:8.583333333333333:1:cameraFade;"
            "stop:10:8:cameraFade,visibility,visibility,visibility,visibility,spriteRemove,spriteRemove,dialogueStart",
            output,
        )
        self.assertIn(
            "EVENTS|LoFightIntro|intro:0:8:spriteAdd,spriteAnimation,visibility,musicPlay,musicFadeIn,cameraZoom,cameraMove,visibility;"
            "rip:1.416666666666667:1:soundPlay;"
            "fire:1.708333333333333:1:soundPlay;"
            "bfBeep:6.125:2:actorAnimation,soundPlay;"
            "focus:6.25:2:cameraZoom,cameraMove;"
            "stop:9.333333333333333:5:visibility,visibility,visibility,spriteRemove,dialogueStart",
            output,
        )
        self.assertIn("ASSETS|LoFightIntro|sparrow:images/alley/cutscene/whittyCutscene,music:music/city,sound:sounds/rip,sound:sounds/fire,sound:sounds/beepboop", output)
        self.assertIn(
            "CODES|OverheadIntro|hxc-cutscene-adapter-engine-owned:info,hxc-cutscene-adapter-no-op:info,hxc-cutscene-adapter-engine-owned:info",
            output,
        )
        after = {
            name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
            for name, path in CUTSCENES.items()
        }
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
