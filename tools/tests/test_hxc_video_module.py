"""Focused coverage for the complete HXC video-module native boundary."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path(
    "/run/media/cammie/External Storage/FNF-Example-Mods/v-slice/"
    "Wacky World UPDATE [V-Slice]/scripts/modules/PVE_VideoModule.hxc"
)
HAXE = ROOT / ".tools/haxe/haxe"


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


class HxcVideoModuleTest(unittest.TestCase):
    def run_fixture(self, source: str, extra_cp=None):
        with tempfile.TemporaryDirectory() as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            command = [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder]
            for classpath in extra_cp or []:
                command.extend(["-cp", str(classpath)])
            command.extend(["-main", "Main", "--interp"])
            return subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True, timeout=300
            )

    def test_complete_video_module_is_structural_and_partial_copy_stays_unsupported(self):
        if not DONOR.exists():
            self.skipTest("mounted Wacky World V-Slice fixture is unavailable")
        source = DONOR.read_text(errors="ignore")
        renamed = source.replace("PVE_VideoModule", "RenamedVideoBoundary")
        renamed = renamed.replace("PVE_ConfigData", "OtherVideoConfig")
        renamed = renamed.replace("PVE_VideoData", "OtherVideoEntry")
        renamed = renamed.replace("super('RenamedVideoBoundary')", "super('OtherRegistryKey')")
        partial = source.replace(
            "Math.abs(videoError) > VIDEO_RESYNC_THRESHOLD",
            "Math.abs(videoError) > VIDEO_RESYNC_THRESHOLD + 1",
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var full = HxcCompat.analyze({hx_string(source)}, "scripts/modules/foreign-path.hxc");
    var renamed = HxcCompat.analyze({hx_string(renamed)}, "scripts/modules/renamed-path.hxc");
    for (result in [full, renamed]) {{
      if (result.kind != "module" || !result.moduleSafe || !result.moduleInitializationSafe
        || result.videoModuleAdapter != true || hasCode(result, "unsupported-hxc-module-body")
        || hasCode(result, "unsupported-hxc-callback-body"))
        fail("complete structural video module was rejected: adapter=" + result.videoModuleAdapter
          + " module=" + result.moduleSafe + " init=" + result.moduleInitializationSafe
          + " reasons=" + result.moduleSafetyReasons.join(","));
      var callbacks = (cast result.callbackAdapters:Array<Dynamic>);
      if (callbacks.length != 9) fail("native lifecycle callback count " + callbacks.length);
      for (callback in callbacks)
        if (!callback.safe) fail("unsafe generated native lifecycle callback " + callback.sourceName);
      var helpers = (cast result.helperAdapters:Array<Dynamic>);
      if (helpers.length != 4) fail("native video helper count " + helpers.length);
      for (helper in helpers)
        if (!helper.safe) fail("unsafe generated native video helper " + helper.sourceName);
      if (result.generatedHscript.indexOf("HxcCompatRuntime.createVideoModule") < 0
        || result.generatedHscript.indexOf("function focusGained") < 0
        || result.generatedHscript.indexOf("function countdownStart") < 0
        || result.generatedHscript.indexOf("function destroy") < 0
        || result.generatedHscript.indexOf("FlxTypedGroup") >= 0)
        fail("native module boundary is incomplete or leaked donor state: " + result.generatedHscript);
      var adapter = false;
      for (finding in result.diagnostics)
        if (finding.code == "hxc-video-module-adapter") adapter = true;
      if (!adapter) fail("video semantics diagnostic missing");
      new Parser().parseString(result.generatedHscript);
    }}
    var incomplete = HxcCompat.analyze({hx_string(partial)}, "scripts/modules/renamed-path.hxc");
    if (incomplete.videoModuleAdapter == true || incomplete.moduleSafe
      || !hasCode(incomplete, "unsupported-hxc-module-body"))
      fail("partial video semantics were incorrectly covered");
    new Parser().parseString(incomplete.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_video_module_runtime_bridge_calls_only_the_owned_host(self):
        main = '''
class FakeVideoHost {
  public var calls:Array<Dynamic> = [];
  public function new() {}
  function record(values:Array<Dynamic>):Void calls.push(values);
  public function getDefaultConfig():Dynamic { record(["defaults"]); return {videoType: 1}; }
  public function createVideo(path:Dynamic, config:Dynamic):Dynamic { record(["create", path, config]); return path; }
  public function checkResync(video:Dynamic, instant:Bool, resume:Bool):Void record(["resync", video, instant, resume]);
  public function clearVideoSprites():Void record(["clear"]);
  public function destroy():Void record(["destroy"]);
  public function update(event:Dynamic):Void record(["update", event]);
}
class FakeVideoState {
  public var host:FakeVideoHost = new FakeVideoHost();
  public var root:String = "";
  public function new() {}
  public function hxcCreateVideoModule(assetRoot:String):Dynamic { root = assetRoot; return host; }
}
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var state = new FakeVideoState();
    var host = HxcCompatRuntime.createVideoModule(state, "selected-root");
    if (state.root != "selected-root" || host != state.host) fail("owner creation");
    var defaults = HxcCompatRuntime.videoModuleDefaults(state, host);
    if (defaults.videoType != 1) fail("defaults boundary");
    if (HxcCompatRuntime.videoModuleCreateVideo(state, host, "safe-path", {mute: true}) != "safe-path")
      fail("video return value");
    HxcCompatRuntime.videoModuleCheckResync(state, host, "sprite", "true", false);
    HxcCompatRuntime.videoModuleUpdate(state, host, "frame");
    HxcCompatRuntime.videoModuleClear(state, host);
    HxcCompatRuntime.videoModuleDestroy(state, host);
    if (state.host.calls.length != 6) fail("host dispatch count " + Std.string(state.host.calls.length));
    var resync = state.host.calls[2];
    if (Std.string(resync[0]) != "resync" || Std.string(resync[2]) != "true"
      || Std.string(resync[3]) != "false") fail("boolean defaults");
    if (Std.string(state.host.calls[3][1]) != "frame"
      || Std.string(state.host.calls[4][0]) != "clear"
      || Std.string(state.host.calls[5][0]) != "destroy") fail("lifecycle dispatch order");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generated_video_module_initializer_receives_owner_asset_root(self):
        if not DONOR.exists():
            self.skipTest("mounted Wacky World V-Slice fixture is unavailable")
        main = f'''import hscript.Interp;
import hscript.ParserEx;
class Main {{
  static function main() {{
    var result = HxcCompat.analyze({hx_string(DONOR.read_text(errors="ignore"))}, "scripts/modules/source.hxc");
    if (result.videoModuleAdapter != true) throw "video adapter missing";
    var root = "assets/imported_mods/selected-owner";
    var state:Dynamic = {{received: ""}};
    Reflect.setField(state, "hxcCreateVideoModule", function(received:String):Dynamic {{
      if (received != root) throw "wrong owner root";
      Reflect.setField(state, "received", received);
      return {{}};
    }});
    var interp = new Interp();
    interp.variables.set("PlayState", {{instance: state}});
    interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    interp.variables.set("hxcAssetRoot", root);
    interp.execute(new ParserEx().parseString(result.generatedHscript));
    if (Reflect.field(state, "received") != root)
      throw "module initializer did not retain its native host";
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0", ROOT / ".haxelib/hscript-ex/git/src"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_video_host_teardown_does_not_touch_outgoing_hud_camera(self):
        source = (ROOT / "source/HxcVideoModuleHost.hx").read_text()
        start = source.index("public function destroy():Void {")
        opening = source.index("{", start)
        depth = 0
        end = opening
        while end < len(source):
            if source[end] == "{":
                depth += 1
            elif source[end] == "}":
                depth -= 1
                if depth == 0:
                    break
            end += 1
        self.assertLess(end, len(source), "video host destroy method is not closed")
        body = source[opening + 1:end]
        self.assertIn("if (disposed)", body)
        self.assertIn("clearVideoSprites();", body)
        self.assertIn("state = null;", body)
        self.assertNotIn("camHUD", body,
                         "the outgoing PlayState camera is unsafe to mutate during teardown")


if __name__ == "__main__":
    unittest.main()
