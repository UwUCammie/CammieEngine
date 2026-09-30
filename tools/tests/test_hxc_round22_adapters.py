"""Mounted HXC regressions for the data-only character/shader adapters."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
HAXE = ROOT / ".tools/haxe/haxe"


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


class HxcRound22AdapterTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            command = [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder,
                       "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                       "-main", "Main", "--interp"]
            return subprocess.run(command, cwd=ROOT, capture_output=True,
                                  text=True, timeout=300)

    def test_mounted_character_info_preserves_sparrow_metadata(self):
        path = DONOR / "whitty/data/characters/Whitty.hxc"
        if not path.is_file():
            self.skipTest("Whitty HXC donor is not mounted")
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze(sys.io.File.getContent({hx_string(str(path))}), {hx_string(str(path))});
    if (result.kind != "character" || result.characterDefinition == null)
      fail("Whitty character metadata was not recognized");
    if (result.generatedHscript.indexOf("characters/WhittySprites") < 0
      || result.generatedHscript.indexOf("[150, 420]") < 0
      || result.generatedHscript.indexOf("Sing Up") < 0)
      fail("Whitty metadata was not emitted: " + result.generatedHscript);
    if (hasCode(result, "unsupported-hxc-api")) fail("setSparrow metadata was rejected");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_mounted_whitty_sparrow_definitions_use_the_metadata_route(self):
        paths = sorted((DONOR / "whitty/data/characters").glob("*.hxc"))
        paths = [path for path in paths if "setSparrow" in path.read_text(errors="ignore")]
        if not paths:
            self.skipTest("Whitty Sparrow character definitions are not mounted")
        encoded = ",\n".join(hx_string(str(path)) for path in paths)
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var paths = [{encoded}];
    if (paths.length != 10) fail("unexpected Whitty Sparrow corpus: " + paths.length);
    for (path in paths) {{
      var result = HxcCompat.analyze(sys.io.File.getContent(path), path);
      if (result.kind != "character" || result.characterDefinition == null)
        fail("missing CharacterInfo definition: " + path);
      for (finding in (cast result.diagnostics:Array<Dynamic>))
        if (finding.code == "unsupported-hxc-api")
          fail("metadata helper rejected: " + path + " :: " + finding.message);
    }}
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rabbit_mixed_module_uses_store_gate_and_native_shader_owner(self):
        path = DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/songs/rabbit-hole.hxc"
        if not path.is_file():
            self.skipTest("Rabbit Hole HXC donor is not mounted")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze(sys.io.File.getContent({hx_string(str(path))}), {hx_string(str(path))});
    if (result.kind != "song-script" || result.className != "RabbitHole") fail("Rabbit class selection");
    if (result.companionClassNames == null || result.companionClassNames.indexOf("RabbitHoleOptions") < 0)
      fail("RabbitHoleOptions companion was not registered");
    if (result.runtimeShaderDescriptor == null) fail("Rabbit shader descriptor missing");
    if (result.runtimeShaderDescriptor == null) fail("Rabbit descriptor null");
    if (result.runtimeShaderDescriptor.shaderField == null
      || result.runtimeShaderDescriptor.shaderField == "")
      fail("Rabbit shader field missing: " + result.runtimeShaderDescriptor.shaderName);
    if (result.runtimeShaderDescriptor.gate == null)
      fail("Rabbit shader gate missing");
    var generated = result.generatedHscript;
    if (generated.indexOf("rabbit_hole_settings") < 0
      || generated.indexOf("HxcCompatRuntime.applyShaderDescriptor") < 0
      || generated.indexOf("hxcGetModule") >= 0
      || generated.indexOf("game.HxcCompatRuntime") >= 0)
      fail("Rabbit gate did not use the isolated store: " + generated);
    new Parser().parseString(generated);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_markov_shader_uses_opaque_uniform_and_pulse_adapters(self):
        path = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/markov-lyrics.hxc"
        if not path.is_file():
            self.skipTest("Markov HXC donor is not mounted")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze(sys.io.File.getContent({hx_string(str(path))}), {hx_string(str(path))});
    var descriptor:Dynamic = result.runtimeShaderDescriptor;
    if (descriptor == null || descriptor.shaderName != "StaticShader") fail("StaticShader descriptor missing");
    if (descriptor.uniforms.indexOf("iTime") < 0 || descriptor.uniforms.indexOf("alpha") < 0)
      fail("StaticShader uniforms missing");
    var generated = result.generatedHscript;
    if (generated.indexOf("createShaderHandle") < 0
      || generated.indexOf("setShaderUniform") < 0
      || generated.indexOf("pulseShader") < 0
      || generated.indexOf("new FlxRuntimeShader") >= 0
      || generated.indexOf("new ShaderFilter") >= 0)
      fail("Markov shader graph was not lowered: " + generated);
    new Parser().parseString(generated);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_standalone_vignette_shader_is_data_only_noop(self):
        path = DONOR / "v-slice/Wacky World UPDATE [V-Slice]/shaders/hxc files/vignette.hxc"
        if not path.is_file():
            self.skipTest("Vignette HXC donor is not mounted")
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze(sys.io.File.getContent({hx_string(str(path))}), {hx_string(str(path))});
    if (result.kind != "shader" || result.shaderDefinition == null)
      fail("Vignette shader declaration was not recognized");
    var generated = result.generatedHscript == null ? "" : StringTools.trim(result.generatedHscript);
    if (generated != "" && generated != "// HXC compatibility adapter; donor source is never executed directly.")
      fail("standalone shader emitted executable donor code: " + result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shader_contract_rejects_unscoped_roots_and_uses_store_gate(self):
        main = '''
class FakeShaderState {
  public var called:Bool = false;
  public var root:String = "";
  public function new() {}
  public function hxcApplyRuntimeShaderDescriptor(descriptor:Dynamic, assetRoot:String):Bool {
    called = true;
    root = assetRoot;
    return true;
  }
  public function hxcClearRuntimeShaderBindings():Void {}
}
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var state = new FakeShaderState();
    HxcCompatRuntime.bindActiveState(state);
    var store:Dynamic = HxcCompatRuntime.openStore("shader-gate");
    store.modOptions.set("rabbit_hole_settings", {shadersEnabled: false});
    var descriptor:Dynamic = {shaderName: "bloom", cameras: ["camGame"],
      gate: {bucket: "rabbit_hole_settings", field: "shadersEnabled", defaultValue: false}};
    if (HxcCompatRuntime.applyShaderDescriptor(state, descriptor, store, "assets/imported_mods/x"))
      fail("disabled shader gate applied");
    store.modOptions.set("rabbit_hole_settings", {shadersEnabled: true});
    if (!HxcCompatRuntime.applyShaderDescriptor(state, descriptor, store, "assets/imported_mods/x")
      || !state.called || state.root != "assets/imported_mods/x")
      fail("enabled shader gate did not reach exact root");
    HxcCompatRuntime.clearActiveState(state);
  }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shader_pulse_runtime_forwards_ease_and_uniform(self):
        main = '''
class PulseState {
  public var called:Bool = false;
  public var fromValue:Float = 0;
  public var toValue:Float = 0;
  public var tweenDuration:Float = 0;
  public var holdDuration:Float = 0;
  public var ease:Dynamic;
  public var uniform:String = "";
  public function new() {}
  public function hxcPulseRuntimeShader(handle:Dynamic, from:Float, to:Float,
    tweenDuration:Float, holdDuration:Float, ?ease:Dynamic, ?uniform:String):Bool {
    called = handle != null;
    fromValue = from;
    toValue = to;
    this.tweenDuration = tweenDuration;
    this.holdDuration = holdDuration;
    this.ease = ease;
    this.uniform = uniform;
    return called;
  }
}
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var state = new PulseState();
    var handle = {};
    var customEase = function(value:Float):Float return value * value;
    HxcCompatRuntime.bindActiveState(state);
    if (!HxcCompatRuntime.pulseShader(handle, 0, 1, 0.25, 0.4, customEase, "opacity"))
      fail("pulse call was not forwarded");
    if (!state.called || state.fromValue != 0 || state.toValue != 1
      || state.tweenDuration != 0.25 || state.holdDuration != 0.4
      || state.ease != customEase || state.uniform != "opacity")
      fail("pulse adapter dropped source parameters");
    HxcCompatRuntime.clearActiveState(state);
  }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_shader_owner_rejects_empty_or_foreign_asset_roots(self):
        """Keep the native boundary from falling through to cwd/native assets."""
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("public function hxcCreateRuntimeShaderHandle")
        end = source.index("\n\t/** Append/remove only this binding's exact filter identity. */", start)
        owner = source[start:end]
        self.assertIn("root == '' || root.startsWith('/')", owner)
        self.assertIn("root.indexOf(':') >= 0", owner)
        self.assertIn("root.indexOf('..') >= 0", owner)
        self.assertIn("root == CompatScriptManifest.ROOT_PREFIX", owner)
        self.assertIn("ShaderPaths.resolve(Std.string(shaderName), [root], false)", owner)
        self.assertIn("Reflect.field(descriptor, 'cameraRefs')", owner)
        self.assertIn("Reflect.field(descriptor, 'deferCameraBinding') != true", owner)
        camera_start = source.index("function hxcRuntimeShaderCamera")
        camera_end = source.index("\n\tfunction hxcSetRuntimeShaderCamera", camera_start)
        camera_owner = source[camera_start:camera_end]
        self.assertIn("Std.isOfType(name, FlxCamera)", camera_owner)
        self.assertIn("FlxG.cameras.list.indexOf(camera) < 0", camera_owner)
        cleanup_start = source.index("function hxcSetRuntimeShaderCamera", camera_start)
        cleanup_end = source.index("function hxcCancelRuntimeShaderMotion", cleanup_start)
        binding_owner = source[cleanup_start:cleanup_end]
        self.assertIn("candidate.camera == target.camera", binding_owner)
        self.assertIn("else if (previous != null)", binding_owner)
