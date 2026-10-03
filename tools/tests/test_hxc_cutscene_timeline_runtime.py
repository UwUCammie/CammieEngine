"""Native, data-only consumer coverage for bounded FPS Plus cutscenes."""
from haxe_test_support import HAXE_COMMAND

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


class HxcCutsceneTimelineRuntimeTest(unittest.TestCase):
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

    def test_playstate_routes_accepted_hxc_data_before_hscript(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("var timelineCompat = HxcCompat.analyze(FNFAssets.getText(scriptPath), scriptPath);", play_state)
        self.assertIn("startHxcCutsceneTimeline(timelineCompat.cutsceneTimeline, scriptPath);", play_state)
        self.assertIn("hxcCutsceneTimelineRuntime.advance(elapsed);", play_state)
        self.assertIn("hxcCutsceneTimelineRuntime.cancel(false);", play_state)
        self.assertIn("runtime.onHandoff = function()", play_state)
        native_gate = play_state.index("var timelineCompat = HxcCompat.analyze(FNFAssets.getText(scriptPath), scriptPath);")
        generated_hscript = play_state.index("var converted = getCompatibleHscript(scriptPath);", native_gate)
        self.assertLess(native_gate, generated_hscript)

    def test_equal_timestamps_missing_assets_and_cancel_are_deterministic(self):
        main = r'''import HxcCutsceneTimeline.HxcCutsceneAction;
import HxcCutsceneTimeline.HxcCutsceneTimelineData;
import HxcCutsceneTimelineRuntime;
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var timeline:HxcCutsceneTimelineData = {
      version: 1, sourceClass: "Synthetic", sourcePath: "data/cutscenes/Synthetic.hxc",
      dialoguePath: "data/songs/{song}/dialogue.json", dialogueColor: 0,
      initialActions: [{kind: "captureDefaultZoom", target: "originalZoom"}],
      events: [
        {at: {kind: "seconds", value: 0, source: "0"}, callback: "first",
          actions: [{kind: "spriteDefine", sprite: "missing", asset: "images/missing"}]},
        {at: {kind: "seconds", value: 0, source: "0"}, callback: "second",
          actions: [{kind: "visibility", actor: "dad", value: 0}]}
      ],
      dialogueEnd: [{kind: "handoff"}],
      dialogueEndDelay: {kind: "seconds", value: 0.5, source: "0.5"},
      assets: [{kind: "sparrow", key: "images/missing"}], diagnostics: []
    };
    var log:Array<String> = [];
    var rt = new HxcCutsceneTimelineRuntime(timeline, 500);
    rt.assetAvailable = function(asset) return false;
    rt.onAction = function(action) { log.push(action.kind); return true; };
    rt.onCleanup = function() log.push("cleanup");
    rt.onHandoff = function() log.push("countdown");
    if (!rt.start() || log.join(",") != "captureDefaultZoom") fail("initial dispatch");
    rt.advance(0);
    if (log.join(",") != "captureDefaultZoom,visibility") fail("equal timestamp order: " + log.join(","));
    var missing = false;
    for (entry in rt.diagnostics)
      if (entry.code == "missing-hxc-cutscene-asset") missing = true;
    if (!missing) fail("missing manifest asset was not diagnosed");
    rt.notifyDialogueEnd();
    rt.advance(0.49);
    if (log.join(",") != "captureDefaultZoom,visibility") fail("dialogue fired early");
    rt.advance(0.01);
    if (log.join(",") != "captureDefaultZoom,visibility,handoff,cleanup,countdown") fail("handoff order: " + log.join(","));
    rt.cancel();
    if (log.join(",") != "captureDefaultZoom,visibility,handoff,cleanup,countdown") fail("cancel was not idempotent");
    Sys.println("OK");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_bounded_time_and_unsupported_action_fail_to_countdown(self):
        main = r'''import HxcCutsceneTimeline.HxcCutsceneTimelineData;
import HxcCutsceneTimelineRuntime;
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var timeline:HxcCutsceneTimelineData = {
      version: 1, sourceClass: "Bad", sourcePath: "bad.hxc", dialoguePath: "", dialogueColor: 0,
      initialActions: [{kind: "futureDonorObjectGraph"}], events: [], dialogueEnd: [],
      dialogueEndDelay: {kind: "donor-expression", value: 1, source: "foo()"},
      assets: [], diagnostics: []
    };
    var handoffs = 0;
    var cleanup = 0;
    var rt = new HxcCutsceneTimelineRuntime(timeline, 500);
    rt.onHandoff = function() handoffs++;
    rt.onCleanup = function() cleanup++;
    if (rt.start()) fail("unsupported data started");
    if (handoffs != 1 || cleanup != 1) fail("unsafe fallback did not hand off exactly once");
    var foundAction = false;
    var foundTime = false;
    for (entry in rt.diagnostics) {
      if (entry.code == "unsupported-hxc-cutscene-runtime-action") foundAction = true;
      if (entry.code == "unsupported-hxc-cutscene-time") foundTime = true;
    }
    if (!foundAction || !foundTime) fail("unsupported constructs were not diagnosed");
    Sys.println("OK");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_mounted_ballistic_and_lofight_cross_data_runtime_boundary(self):
        missing = [path for path in CUTSCENES.values() if not path.is_file()]
        if missing:
            # The FPS Plus donor (whitty) is no longer part of the mounted
            # donor library; the runtime contract stays covered by the
            # synthetic fixtures above.
            self.skipTest(f"mounted FPS Plus cutscene fixtures are unavailable: {missing[0]}")
        calls = "\n".join(
            f'    run({hx_string(name)}, {hx_string(str(path))});'
            for name, path in CUTSCENES.items()
        )
        main = f'''import HxcCutsceneTimelineRuntime;
class Main {{
  static function fail(value:String):Void throw value;
  static function run(name:String, path:String):Void {{
    var result = HxcCompat.analyze(sys.io.File.getContent(path), path);
    if (result.cutsceneTimeline == null) fail(name + " was not accepted at extraction boundary");
    var timeline = result.cutsceneTimeline;
    var actions = 0;
    for (action in timeline.initialActions)
      if (!HxcCutsceneTimelineRuntime.supportsAction(action.kind)) fail(name + " initial action unsupported: " + action.kind);
    for (event in timeline.events)
      for (action in event.actions)
        if (!HxcCutsceneTimelineRuntime.supportsAction(action.kind)) fail(name + " event action unsupported: " + action.kind);
    for (action in timeline.dialogueEnd)
      if (!HxcCutsceneTimelineRuntime.supportsAction(action.kind)) fail(name + " completion action unsupported: " + action.kind);
    var rt = new HxcCutsceneTimelineRuntime(timeline, 500);
    rt.assetAvailable = function(_) return true;
    rt.onAction = function(action) {{ actions++; return true; }};
    var handoffs = 0;
    rt.onHandoff = function() handoffs++;
    rt.onCleanup = function() {{}};
    if (!rt.start()) fail(name + " did not start");
    rt.advance(20);
    rt.notifyDialogueEnd();
    rt.advance(0.5);
    var expected = timeline.initialActions.length + timeline.dialogueEnd.length;
    for (event in timeline.events) expected += event.actions.length;
    if (actions != expected) fail(name + " action count " + actions + " != " + expected);
    if (handoffs != 1) fail(name + " countdown handoff count " + handoffs);
    if (rt.state != HxcCutsceneTimelineRuntime.STATE_FINISHED) fail(name + " did not finish");
    Sys.println("RUNTIME|" + name + "|" + timeline.events.length + "|" + actions);
  }}
  static function main() {{
{calls}
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        self.assertIn("RUNTIME|BallisticIntro|11|44", output)
        self.assertIn("RUNTIME|LoFightIntro|6|30", output)
        self.assertIn("RUNTIME|OverheadIntro|1|9", output)


if __name__ == "__main__":
    unittest.main()
