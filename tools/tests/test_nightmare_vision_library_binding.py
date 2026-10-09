"""Legacy class binding uses shared resolution without leaking between owners."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionLibraryBindingTest(unittest.TestCase):
    def test_exact_class_binding_owner_isolation_missing_class_and_teardown(self):
        fixture = r'''
class HudHost {
 public var nightmareVisionLegacyHudControls = new NightmareVisionLegacyHudControls();
 public function new() {}
 public function seed(interp:NightmareVisionScriptInterp):Void {
  BIND_LEGACY_HUD
 }
}
class FixtureClass { public static var marker = 42; }
enum FixtureEnum { Value; }
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main() {
  check(FixtureClass.marker == 42 && FixtureEnum.Value != null, "link fixture types");
  check(haxe.crypto.Md5.encode("test") != null, "link native class");
  var errors:Array<String> = [];
  var report = function(name:String, phase:String, error:Dynamic):Void {
   errors.push(name + "#" + phase + ":" + Std.string(error));
  };
  var a = NightmareVisionScriptModule.fromSource("owner-a", '
   addHaxeLibrary("Md5", "haxe.crypto");
   digest = Md5.encode("test");
   addHaxeLibrary("FixtureClass");
   marker = FixtureClass.marker;
   MissingClass = "stale";
   addHaxeLibrary("MissingClass", "missing.package");
   missingIsNull = MissingClass == null;
   addHaxeLibrary("FixtureEnum");
   enumBinding = FixtureEnum;
   function nextCallback() return marker;
  ', null, null, function(interp) {
   interp.variables.set("Md5", "unrelated short-name seed");
   interp.bindImport("haxe.crypto.Md5", {encode:function(text:String) return "owner:" + text});
  }, report);
  check(a.initialized && a.callValue("nextCallback") == 42, "missing class aborted module/callback");
  check(a.get("digest") == "owner:test", "exact owner binding lost to a same-name seed or native class");
  check(a.get("missingIsNull") && a.get("enumBinding") == Type.resolveClass("FixtureEnum"), "legacy Type.resolveClass/null behavior changed");
  check(errors.length == (Type.resolveClass("FixtureEnum") == null ? 2 : 1) && errors[0].indexOf("owner-a#addHaxeLibrary:Unresolved source class: missing.package.MissingClass") == 0,
   "missing class diagnostics lack owner, phase or qualified name: " + errors);
  var b = NightmareVisionScriptModule.fromSource("owner-b", '
   addHaxeLibrary("Md5", "haxe.crypto"); digest = Md5.encode("test");
  ', null, null, null, report);
  check(b.get("digest") == "098f6bcd4621d373cade4e832627b4f6", "class binding leaked between owners");
  // Psych and language imports retain the same owner-first resolver.
  var bridge = new SourceIrisBridge(null);
  bridge.evaluator.bindImport("fixture.Scoped", {marker:71});
  check(Reflect.field(bridge.bindLibrary("Scoped", "fixture.Scoped"), "marker") == 71, "Psych did not use shared owner resolution");
  var failed = false;
  try bridge.bindLibrary("Missing", "missing.package.Missing") catch (_:Dynamic) failed = true;
  check(failed, "Psych strict failure contract changed");
  var scope = b.interp.sourceClassScope();
  scope.bindRuntimeClass("fixture.Scoped", FixtureClass);
  check(b.interp.resolveSourceImport("fixture.Scoped", true) == FixtureClass, "owner runtime class missed");
  NightmareVisionScriptInterp.validateCameraArray(null);
  NightmareVisionScriptInterp.validateCameraArray([]);
  NightmareVisionScriptInterp.validateCameraArray([{}, {}]);
  for (invalid in [[null], [{}, null]]) {
   failed = false;
   try NightmareVisionScriptInterp.validateCameraArray(invalid) catch (error:Dynamic)
    failed = Std.string(error).indexOf("source-camera-assignment") >= 0;
   check(failed, "uninitialized source camera accepted");
  }
  var cameras:Array<Dynamic> = [];
  var manager:Dynamic={add:function(camera:Dynamic, target:Bool):Dynamic {
   cameras.push(camera); return camera;
  }};
  var cameraErrors = 0;
  b.interp.sourceError = function(error:Dynamic, pos:haxe.PosInfos):Void cameraErrors++;
  var add = b.interp.sourceCameraMutation(manager, "add");
  for (camera in [null, {id:1}, null, {id:2}]) Reflect.callMethod(null, add, [camera, false]);
  check(cameras.length == 2 && cameraErrors == 2,
   "camera restoration must continue past rejected null entries without calling native add");
  check(Reflect.field(Reflect.callMethod(null, add, [{id:3}, true]), "id") == 3,
   "valid camera return or arguments changed");
  var host = new HudHost();
  var hud:Dynamic={showRating:true,showCombo:true,showRatingNum:true};
  var controlsModule = NightmareVisionScriptModule.fromSource("hud-owner", '
   game.showRating = false; showCombo = false;
   function restore() { showRating = true; game.showCombo = true; }
  ', host, null, host.seed, report);
  host.nightmareVisionLegacyHudControls.bind(hud);
  check(controlsModule.initialized && !hud.showRating && !hud.showRatingNum,
   "actual gameplay binding lost qualified/bare writes before HUD attachment");
  controlsModule.callValue("restore");
  check(hud.showRating && hud.showRatingNum && hud.showCombo, "live script controls did not restore HUD");
  controlsModule.destroy(); host.nightmareVisionLegacyHudControls.release();
  var retained = a.interp;
  var callback = a.get("addHaxeLibrary");
  a.destroy();
  Reflect.callMethod(null, callback, ["Md5", "haxe.crypto"]);
  check(!retained.variables.keys().hasNext() && !retained.importBindings.keys().hasNext(), "released helper rebound or retained state");
  check(b.get("Md5") == haxe.crypto.Md5, "other owner damaged by teardown");
  b.destroy(); bridge.release();
 }
}
'''
        gameplay = (ROOT / "source/PlayState.hx").read_text()
        bindings = gameplay.split("\t\tinterp.variables.set('game', this);\n", 1)[1].split("\t\tbindSourceBarClass(interp, true);", 1)[0]
        fixture = fixture.replace("BIND_LEGACY_HUD", "interp.variables.set('game', this);\n" + bindings)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / "Main.hx").write_text(fixture, newline="\n")
            (work / "HxcCompatRuntime.hx").write_text("""class HxcCompatRuntime {
 public static function getZIndex(_target:Dynamic):Dynamic return 0;
 public static function setZIndex(_target:Dynamic, value:Dynamic, ?_op:String='='):Dynamic return value;
}""", newline="\n")
            for defines in ([], ["-D", "hscriptPos"]):
                with self.subTest(defines=defines):
                    result = subprocess.run(
                        [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                         "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                         "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", str(work)]
                        + defines + ["--main", "Main", "--interp"], cwd=work,
                        capture_output=True, text=True, timeout=45)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
