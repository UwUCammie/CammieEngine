"""Mounted regressions for complete HXC stage countdown shader callbacks."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DONOR = (Path("/run/media/cammie/External Storage/FNF-Example-Mods") /
         "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE")
HAXE = ROOT / ".tools/haxe/haxe"
CLUBROOM = DONOR / "scripts/stages/clubroomfestival.hxc"
EVIL_STAGES = [
    DONOR / "scripts/stages/evilClubroom.hxc",
    DONOR / "scripts/stages/evilClubroomSayo.hxc",
]


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


class HxcStageRuntimeShaderBridgeTest(unittest.TestCase):
    def run_fixture(self, source: str, *args: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(prefix="hxc-stage-shader-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            command = [str(HAXE), "-cp", str(ROOT / "source"),
                       "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", folder,
                       "--run", "Main", *args]
            return subprocess.run(command, cwd=ROOT, capture_output=True,
                                  text=True, timeout=120)

    def test_clubroom_countdown_keeps_shader_shadows_and_character_layout(self):
        if not CLUBROOM.is_file():
            self.skipTest("DDTO++ ClubroomFestival HXC donor is not mounted")
        main = f'''import hscript.Interp;
import hscript.Parser;
class FakeCompatRuntime {{
  public static var calls:Array<String> = [];
  public static function createShaderHandle(state:Dynamic, descriptor:Dynamic, root:String):String {{
    if (descriptor.shaderName != "BloomShader" || root != "assets/imported_mods/ddto")
      throw "wrong shader descriptor or root";
    calls.push("create");
    return "opaque-shader";
  }}
  public static function setShaderUniform(handle:Dynamic, name:Dynamic, value:Dynamic):Bool {{
    calls.push("uniform:" + name + "=" + value);
    return true;
  }}
  public static function bindShaderFilter(state:Dynamic, handle:Dynamic,
      camera:Dynamic, enabled:Dynamic):Bool {{
    calls.push("filter:" + camera + "=" + enabled);
    return true;
  }}
  public static function assignFilters(target:Dynamic, value:Dynamic):Dynamic return value;
}}
class Main {{
  static function fail(message:String):Void throw message;
  static function check(value:Bool, message:String):Void if (!value) fail(message);
  static function prop():Dynamic {{
    var result:Dynamic = {{alpha: 1.0, color: 0, x: 0.0, y: 0.0}};
    Reflect.setField(result, "setPosition", function(x:Dynamic, y:Dynamic) {{
      Reflect.setField(result, "x", x);
      Reflect.setField(result, "y", y);
    }});
    return result;
  }}
  static function main() {{
    var path = Sys.args()[0];
    var result = HxcCompat.analyze(sys.io.File.getContent(path), path);
    check(result.kind == "stage", "stage classification");
    check(result.runtimeShaderDescriptor != null
      && result.runtimeShaderDescriptor.shaderName == "BloomShader"
      && result.runtimeShaderDescriptor.cameras.indexOf("camGame") >= 0,
      "bounded stage shader descriptor missing");
    var countdown:Dynamic = null;
    for (callback in result.callbackAdapters)
      if (callback.sourceName == "onCountdownStart") countdown = callback;
    check(countdown != null && countdown.safe, "full countdown callback remained unsafe");
    check(countdown.body.indexOf("setShaderUniform(__hxcShaderHandle, \\\"funrange\\\", 0.1)") >= 0
      && countdown.body.indexOf("bindShaderFilter(PlayState.instance, __hxcShaderHandle, \\\"camGame\\\", true)") >= 0
      && countdown.body.indexOf("refreshShadows()") >= 0
      && countdown.body.indexOf("setDokiPosition(\\n") >= 0,
      "shader bridge dropped or reordered callback behavior: " + countdown.body);
    for (finding in result.diagnostics)
      if (finding.code == "unsupported-hxc-callback-body"
        && finding.message.indexOf("onCountdownStart") >= 0)
        fail("countdown callback still has a strict diagnostic: " + finding.message);
    check(result.generatedHscript.indexOf("if (__hxcShaderHandle == null)") >= 0,
      "stage shader was not deferred to countdown");
    check(result.generatedHscript.indexOf("function refreshShadows") >= 0
      && result.generatedHscript.indexOf("function setDokiPosition") >= 0,
      "source helper bodies were not emitted");

    var interp = new Interp();
    interp.variables.set("HxcCompatRuntime", FakeCompatRuntime);
    interp.execute(new Parser().parseString(result.generatedHscript));
    var sayori = prop();
    var natsuki = prop();
    var monika = prop();
    var yuri = prop();
    var protag = prop();
    var boyfriend = prop();
    var girlfriend = prop();
    var opponent = prop();
    interp.variables.set("sayori", sayori);
    interp.variables.set("natsuki", natsuki);
    interp.variables.set("monika", monika);
    interp.variables.set("yuri", yuri);
    interp.variables.set("protag", protag);
    interp.variables.set("getBoyfriend", function() return boyfriend);
    interp.variables.set("getGirlfriend", function() return girlfriend);
    interp.variables.set("getOpponent", function() return opponent);
    interp.variables.set("hxcAssetRoot", "assets/imported_mods/ddto");
    interp.variables.set("SONG", {{player2: "natsuki"}});
    interp.variables.set("PlayState", {{instance: {{camGame: {{}}}}}});
    FakeCompatRuntime.calls = [];
    Reflect.callMethod(null, interp.variables.get("countdownStart"), [null]);
    check(FakeCompatRuntime.calls.indexOf("create") == 0, "shader handle did not initialize at countdown");
    var expectedUniforms = ["uniform:funrange=0.1", "uniform:funsteps=0.005",
      "uniform:funthreshhold=0.8", "uniform:funbrightness=7"];
    for (index in 0...expectedUniforms.length)
      if (FakeCompatRuntime.calls[index + 1] != expectedUniforms[index])
        fail("uniform write/order mismatch: " + FakeCompatRuntime.calls);
    check(FakeCompatRuntime.calls.indexOf("filter:camGame=true") >= 0,
      "camGame filter was not attached");
    check(boyfriend.color == 0x828282 && girlfriend.color == 0x828282
      && opponent.color == 0x828282 && sayori.color == 0x828282
      && natsuki.color == 0x828282 && monika.color == 0x828282
      && yuri.color == 0x828282 && protag.color == 0x828282,
      "refreshShadows did not color every actor and background character");
    check(natsuki.alpha == 0 && sayori.alpha == 1 && monika.alpha == 1
      && yuri.alpha == 1 && protag.alpha == 1,
      "Natsuki character placement alpha was not preserved");
    check(sayori.x == -49 && sayori.y == 247 && yuri.x == 1044 && yuri.y == 178
      && protag.x == 379 && protag.y == 152 && monika.x == 1207 && monika.y == 173,
      "Natsuki character placement coordinates were not preserved");
  }}
}}'''
        result = self.run_fixture(main, str(CLUBROOM))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_dynamic_stage_cameras_keep_source_backed_shader_guards(self):
        paths = [path for path in EVIL_STAGES if path.is_file()]
        if not paths:
            self.skipTest("DDTO++ dynamic-camera stage HXC donors are not mounted")
        encoded = ",\n".join(hx_string(str(path)) for path in paths)
        main = f'''import hscript.Parser;
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    for (path in [{encoded}]) {{
      var result = HxcCompat.analyze(sys.io.File.getContent(path), path);
      var descriptor:Dynamic = result.runtimeShaderDescriptor;
      if (descriptor == null || descriptor.dynamicCameraField != "camBG"
        || descriptor.preferenceGuard == null || descriptor.preferenceGuard.sourceBacked != true
        || descriptor.preferenceGuard.field != "bloom")
        fail("source-backed dynamic camera/preference proof missing: " + path);
      var found = false;
      for (callback in result.callbackAdapters)
        if (callback.sourceName == "onCountdownStart" && callback.safe) found = true;
      if (!found) fail("complete dynamic-camera countdown remained unsafe: " + path);
      var generated = result.generatedHscript;
      if (generated.indexOf("cameraRefs: [camBG]") < 0
        || generated.indexOf("preferenceEnabled(save, \\\"bloom\\\")") < 0
        || generated.indexOf("bindShaderFilter(PlayState.instance, __hxcShaderHandle, camBG, true)") < 0
        || generated.indexOf("new FlxRuntimeShader") >= 0
        || generated.indexOf("new ShaderFilter") >= 0)
        fail("dynamic camera or preference escaped its bridge: " + generated);
      for (finding in result.diagnostics)
        if ((finding.code == "unsupported-hxc-callback-body"
            || finding.code == "unsupported-hxc-shader-callback")
          && finding.message.indexOf("onCountdownStart") >= 0)
          fail("countdown retained a strict diagnostic: " + finding.message);
      new Parser().parseString(generated);
    }}
  }}
}}'''
        result = self.run_fixture(main, *[str(path) for path in paths])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_dynamic_camera_adapter_requires_source_proofs_and_preserves_preference(self):
        donor = r'''class ArbitraryOverlay extends Stage {
  var overlayCamera:FunkinCamera;
  var settings:Dynamic;
  var colorShader = new FlxRuntimeShader(Assets.getText(Paths.frag("Noise")));
  var overlayFilter = new ShaderFilter(colorShader);
  function new() { super(); settings = AnyPreferences.getSettingsSave(); }
  public function onCountdownStart(event:Dynamic):Void {
    colorShader.setFloat("strength", 0.25);
    if (settings.enabled) { overlayCamera.filters = [overlayFilter]; }
  }
  override function buildStage() {
    super.buildStage();
    overlayCamera = new FunkinCamera("overlayCamera");
    FlxG.cameras.insert(overlayCamera,
      FlxG.cameras.list.indexOf(PlayState.instance.camGame), false);
  }
}'''
        nonliteral_camera = donor.replace(
            'new FunkinCamera("overlayCamera")',
            'new FunkinCamera(cameraName)',
        )
        unregistered_camera = donor.replace(
            'FlxG.cameras.insert(overlayCamera,\n      FlxG.cameras.list.indexOf(PlayState.instance.camGame), false);',
            'FlxG.cameras.add(PlayState.instance.camGame, false);',
        )
        unbacked_preference = donor.replace(
            'settings = AnyPreferences.getSettingsSave();',
            'settings = {};',
        )
        dynamic_uniform = donor.replace(
            'colorShader.setFloat("strength", 0.25);',
            'colorShader.setFloat("strength", settings.strength);',
        )
        dynamic_fragment = donor.replace(
            'Paths.frag("Noise")',
            'Paths.frag(settings.shaderName)',
        )
        extra_side_effect = donor.replace(
            'if (settings.enabled) { overlayCamera.filters = [overlayFilter]; }',
            'if (settings.enabled) { overlayCamera.filters = [overlayFilter]; }\n'
            '    FlxG.camera.filters = [];',
        )
        encoded_donors = [
            hx_string(donor), hx_string(nonliteral_camera),
            hx_string(unregistered_camera), hx_string(unbacked_preference),
            hx_string(dynamic_uniform), hx_string(dynamic_fragment),
            hx_string(extra_side_effect),
        ]
        main = f'''import hscript.Interp;
import hscript.Parser;
class FakeCompatRuntime {{
  public static var cameras:Array<Dynamic> = [];
  public static var calls:Array<String> = [];
  public static var save:Dynamic;
  public static function openStore(_namespace:String):Dynamic
    return {{getSave: function() return save}};
  public static function createFunkinCamera(_owner:Dynamic, name:Dynamic):Dynamic
    return {{name: name, filters: [], filtersEnabled: true}};
  public static function createShaderHandle(_state:Dynamic, descriptor:Dynamic, _root:String):String {{
    if (descriptor.deferCameraBinding != true || descriptor.cameraRefs.length != 1
      || descriptor.cameraRefs[0] == null || cameras.indexOf(descriptor.cameraRefs[0]) < 0)
      throw "unregistered camera crossed the descriptor boundary";
    calls.push("create");
    return "opaque";
  }}
  public static function setShaderUniform(_handle:Dynamic, name:Dynamic, value:Dynamic):Bool {{
    calls.push("uniform:" + name + "=" + value);
    return true;
  }}
  public static function preferenceEnabled(preferences:Dynamic, field:Dynamic):Bool {{
    var value = Reflect.field(preferences, Std.string(field));
    return value != null && Type.typeof(value) == TBool && (cast value:Bool);
  }}
  public static function bindShaderFilter(_state:Dynamic, _handle:Dynamic,
      camera:Dynamic, enabled:Dynamic):Bool {{
    calls.push("bind:" + (cameras.indexOf(camera) >= 0) + ":" + enabled);
    return true;
  }}
}}
class Main {{
  static function fail(message:String):Void throw message;
  static function check(value:Bool, message:String):Void if (!value) fail(message);
  static function safeCountdown(result:Dynamic):Bool {{
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onCountdownStart") return callback.safe;
    return false;
  }}
  static function main() {{
    check(HxcCompatRuntime.preferenceEnabled({{enabled: true}}, "enabled")
      && !HxcCompatRuntime.preferenceEnabled({{enabled: "true"}}, "enabled")
      && !HxcCompatRuntime.preferenceEnabled({{enabled: false}}, "enabled"),
      "native preference reader did not enforce a strict bool");
    var inputs = [{", ".join(encoded_donors)}];
    var accepted = HxcCompat.analyze(inputs[0], "assets/scripts/stages/renamed-overlay.hxc");
    check(accepted.runtimeShaderDescriptor != null
      && accepted.runtimeShaderDescriptor.dynamicCameraField == "overlayCamera"
      && accepted.runtimeShaderDescriptor.preferenceGuard.sourceBacked == true,
      "renamed source-proven camera/preferences were not recognized");
    check(safeCountdown(accepted), "complete generic countdown was not accepted");
    check(accepted.generatedHscript.indexOf("cameraRefs: [overlayCamera]") >= 0
      && accepted.generatedHscript.indexOf("preferenceEnabled(settings, \\\"enabled\\\")") >= 0
      && accepted.generatedHscript.indexOf("new FlxRuntimeShader") < 0
      && accepted.generatedHscript.indexOf("new ShaderFilter") < 0,
      "generated adapter did not retain the bounded data and preference guard");
    new Parser().parseString(accepted.generatedHscript);

    var gameCamera:Dynamic = {{name: "game", filters: [], filtersEnabled: true}};
    var cameraList:Array<Dynamic> = [gameCamera];
    FakeCompatRuntime.cameras = cameraList;
    FakeCompatRuntime.calls = [];
    FakeCompatRuntime.save = {{enabled: false}};
    var camerasView:Dynamic = {{list: cameraList}};
    Reflect.setField(camerasView, "insert", function(camera:Dynamic, index:Int, _makeDefault:Bool) {{
      cameraList.insert(index, camera);
      return camera;
    }});
    var interp = new Interp();
    interp.variables.set("HxcCompatRuntime", FakeCompatRuntime);
    interp.variables.set("FlxG", {{cameras: camerasView}});
    interp.variables.set("PlayState", {{instance: {{camGame: gameCamera}}}});
    interp.variables.set("hxcAssetRoot", "assets/imported_mods/renamed");
    interp.execute(new Parser().parseString(accepted.generatedHscript));
    Reflect.callMethod(null, interp.variables.get("start"), []);
    check(cameraList.length == 2 && cameraList[0] != gameCamera,
      "source-proven stage camera was not constructed and registered: "
        + Std.string(cameraList) + " / " + cameraList.length);
    Reflect.callMethod(null, interp.variables.get("countdownStart"), [null]);
    check(FakeCompatRuntime.calls.indexOf("create") == 0
      && FakeCompatRuntime.calls.indexOf("bind:true:true") < 0,
      "disabled preference attached the dynamic camera filter");
    FakeCompatRuntime.save.enabled = true;
    Reflect.callMethod(null, interp.variables.get("countdownStart"), [null]);
    check(FakeCompatRuntime.calls.indexOf("bind:true:true") >= 0,
      "enabled preference did not attach to the registered camera: "
        + FakeCompatRuntime.calls.join("|"));
    FakeCompatRuntime.save.enabled = "true";
    Reflect.callMethod(null, interp.variables.get("countdownStart"), [null]);
    check(FakeCompatRuntime.calls.length == 5,
      "non-bool preference value enabled the filter: " + FakeCompatRuntime.calls.join("|"));

    for (index in 1...inputs.length) {{
      var rejected = HxcCompat.analyze(inputs[index], "assets/scripts/stages/renamed-overlay.hxc");
      check(!safeCountdown(rejected), "unsupported camera/shader side effect was accepted: " + index);
    }}
    var unbacked = HxcCompat.analyze(inputs[3], "assets/scripts/stages/renamed-overlay.hxc");
    check(unbacked.runtimeShaderDescriptor != null
      && unbacked.runtimeShaderDescriptor.preferenceGuard.sourceBacked != true,
      "unbacked preference was not retained as a failed proof");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
