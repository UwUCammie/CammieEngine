"""Keep Nightmare Vision raw Lime/OpenFL Assets imports owner scoped."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


class NightmareVisionAssetsBindingsTest(unittest.TestCase):
    def test_bare_qualified_and_reflection_routes_share_interpreter_owner(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() or not (IRIS / "crowplexus/hscript/Interp.hx").is_file():
            self.skipTest("portable Haxe or pinned hscript-iris 1.1.3 is unavailable")

        files = {
            "fixture/Assets.hx": r'''package fixture;
class Assets {}''',
            "SourceOwnerAssetContext.hx": r'''package;
class SourceOwnerAssetContext {
 public var ownerRoot(default,null):String;
 public function new(ownerRoot:String) this.ownerRoot=ownerRoot;
 public static function nightmareVisionAssets(ownerRoot:String):SourceOwnerAssetContext
  return new SourceOwnerAssetContext(ownerRoot);
}''',
            "PsychOwnerLimeAssets.hx": r'''package;
class PsychOwnerLimeAssets {
 public static var created:Array<Dynamic>=[];
 public static function createForContext(context:SourceOwnerAssetContext):Dynamic {
  var proxy:Dynamic={owner:context.ownerRoot,kind:"lime"};
  Reflect.setField(proxy,"getText",function(id:String):String return "lime:"+context.ownerRoot+":"+id);
  created.push(proxy);return proxy;
 }
}''',
            "PsychOwnerOpenFlAssets.hx": r'''package;
class PsychOwnerOpenFlAssets {
 public static var created:Array<Dynamic>=[];
 public static function createForContext(context:SourceOwnerAssetContext):Dynamic {
  var proxy:Dynamic={owner:context.ownerRoot,kind:"openfl"};
  Reflect.setField(proxy,"getText",function(id:String):String return "openfl:"+context.ownerRoot+":"+id);
  created.push(proxy);return proxy;
 }
}''',
            "NightmareVisionPaths.hx": r'''package;
class NightmareVisionPaths { public var root:String;public function new(root:String)this.root=root; }''',
            "HxcCompatRuntime.hx": r'''package;
class HxcCompatRuntime {
 public static function getZIndex(object:Dynamic):Dynamic return 0;
 public static function setZIndex(object:Dynamic,value:Dynamic):Dynamic return value;
}''',
            "flixel/math/FlxPoint.hx": r'''package flixel.math;
class FlxPoint {
 public var x:Float;public var y:Float;
 public function new(x:Float=0,y:Float=0){this.x=x;this.y=y;}
 public static function weak(x:Float=0,y:Float=0):FlxPoint return new FlxPoint(x,y);
 public function set(x:Float=0,y:Float=0):FlxPoint {this.x=x;this.y=y;return this;}
 public function copyFrom(point:FlxPoint):FlxPoint return set(point.x,point.y);
}
class FlxCallbackPoint extends FlxPoint {
 final callback:FlxPoint->Void;
 public function new(setXCallback:FlxPoint->Void,?setYCallback:FlxPoint->Void,?setXYCallback:FlxPoint->Void){super();callback=setXYCallback!=null?setXYCallback:setXCallback;}
 override public function set(x:Float=0,y:Float=0):FlxCallbackPoint {super.set(x,y);if(callback!=null)callback(this);return this;}
}''',
            "NvAssetsBindingsFixture.hx": r'''package;
import fixture.Assets as FixtureAssets;
class NvAssetsBindingsFixture {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function run(interp:NightmareVisionScriptInterp,parser:NightmareVisionScriptParser,source:String):Void
  interp.execute(parser.parseString(source,"nv-assets-bindings"));
 static function main():Void {
  var ownerA=new NightmareVisionScriptInterp();
  var ownerB=new NightmareVisionScriptInterp();
  var ownerOpenFl=new NightmareVisionScriptInterp();
  var expectedFixtureType:Dynamic=FixtureAssets;
  ownerA.variables.set("Type",Type);
  ownerB.variables.set("Type",Type);
  ownerOpenFl.variables.set("Type",Type);
  NightmareVisionAssetsBindings.install(ownerA,new NightmareVisionPaths("owner-A"));
  NightmareVisionAssetsBindings.install(ownerB,new NightmareVisionPaths("owner-B"));
  NightmareVisionAssetsBindings.install(ownerOpenFl,new NightmareVisionPaths("owner-A"));
  var limeA=ownerA.variables.get("Assets");
  var openA=ownerA.variables.get("OpenFlAssets");
  var limeB=ownerB.variables.get("Assets");
  var openB=ownerB.variables.get("OpenFlAssets");
  check(limeA!=limeB&&openA!=openB,"owner interpreters shared a raw Assets proxy");
  check(ownerA.importBindings.get("lime.utils.Assets")==limeA
   &&ownerA.importBindings.get("openfl.utils.Assets")==openA
   &&ownerA.importBindings.get("openfl.Assets")==openA,
   "qualified import bindings differ from bare owner aliases");
  var scopeA=ownerA.sourceClassScope();
  scopeA.bindRuntimeClass("fixture.ScopeType",NvAssetsBindingsFixture);
  check(scopeA.resolveClass("lime.utils.Assets")==limeA
   &&scopeA.resolveClass("openfl.utils.Assets")==openA
   &&scopeA.resolveClass("openfl.Assets")==openA,
   "Type.resolveClass scope did not return the interpreter proxies");
  check(ownerA.getOrImportClass("lime.utils.Assets")==limeA
   &&ownerA.getOrImportClass("openfl.utils.Assets")==openA
   &&ownerA.getOrImportClass("openfl.Assets")==openA,
   "Iris qualified import lookup did not return the interpreter proxies");
  check(ownerA.getOrImportClass("fixture.ScopeType")==NvAssetsBindingsFixture,
   "Iris import lookup skipped a class held only by the shared source class scope");

  var parser=new NightmareVisionScriptParser();
  run(ownerA,parser,"bareLime=Assets.getText('core-id'); bareOpen=OpenFlAssets.getText('package-id'); ");
  run(ownerA,parser,"import lime.utils.Assets as ScopedLime; importedLime=ScopedLime.getText('core-id'); ");
  run(ownerOpenFl,parser,"import openfl.utils.Assets as ScopedOpenFl; importedOpen=ScopedOpenFl.getText('package-id'); ");
  run(ownerOpenFl,parser,"import openfl.Assets as LegacyOpenFl; importedLegacyOpen=LegacyOpenFl.getText('legacy-id'); ");
  run(ownerA,parser,"import fixture.ScopeType as ScopedFixtureType; importedFixtureType=ScopedFixtureType; ");
  run(ownerA,parser,"import fixture.Assets as FixtureAssetsAlias; importedFixtureAssets=FixtureAssetsAlias; ");
  run(ownerA,parser,"postAliasBare=Assets.getText('core-after-import'); postAliasOpen=OpenFlAssets.getText('open-after-import'); ");
  run(ownerOpenFl,parser,"resolvedOpen=Type.resolveClass('openfl.utils.Assets'); ");
  run(ownerOpenFl,parser,"resolvedLegacyOpen=Type.resolveClass('openfl.Assets'); ");
  run(ownerA,parser,"resolvedLime=Type.resolveClass('lime.utils.Assets'); ");
  check(ownerA.variables.get("bareLime")=="lime:owner-A:core-id"
   &&ownerA.variables.get("bareOpen")=="openfl:owner-A:package-id",
   "bare source globals did not call the selected owner");
  check(ownerA.variables.get("importedLime")=="lime:owner-A:core-id"
   &&ownerOpenFl.variables.get("importedOpen")=="openfl:owner-A:package-id"
   &&ownerOpenFl.variables.get("importedLegacyOpen")=="openfl:owner-A:legacy-id",
   "qualified source imports escaped their selected owner");
  check(ownerA.variables.get("importedFixtureType")==NvAssetsBindingsFixture,
   "explicit alias lookup skipped the shared source class scope");
  check(ownerA.variables.get("importedFixtureAssets")==expectedFixtureType,
   "same-leaf explicit alias changed the resolved native class token");
  check(ownerA.variables.get("postAliasBare")=="lime:owner-A:core-after-import"
   &&ownerA.variables.get("postAliasOpen")=="openfl:owner-A:open-after-import",
   "import aliases shadowed the source preset's bare Assets/OpenFlAssets globals");
  check(ownerA.variables.get("resolvedLime")==limeA
   &&ownerOpenFl.variables.get("resolvedOpen")==ownerOpenFl.variables.get("OpenFlAssets")
   &&ownerOpenFl.variables.get("resolvedLegacyOpen")==ownerOpenFl.variables.get("OpenFlAssets"),
   "source Type.resolveClass did not return the same raw proxies");
  run(ownerB,parser,"value=Assets.getText('core-id');");
  check(ownerB.variables.get("value")=="lime:owner-B:core-id",
   "second interpreter read the first owner's raw asset scope");
  ownerA.release();ownerB.release();ownerOpenFl.release();
 }
}''',
        }

        with tempfile.TemporaryDirectory(prefix="nv-assets-bindings-", dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            for name, content in files.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            env = os.environ.copy()
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS),
                 "-cp", scratch, "--run", "NvAssetsBindingsFixture"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_source_interpreter_entry_paths_install_the_raw_asset_scope(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = source.index("public static function seedNightmareVisionCommon(")
        end = source.index("\n\tpublic static function ", start + 1)
        common = source[start:end]
        self.assertIn("NightmareVisionAssetsBindings.install(interp, paths);", common)
        self.assertLess(common.index("NightmareVisionAssetsBindings.install"), common.index("NightmareVisionScriptBindings.install"))
        self.assertIn("seedNightmareVisionCommon(interp, paths, prefs, plugins, mods, difficulty", source)
        self.assertIn("seedNightmareVisionCommon(nightmareVisionStageConstructionInterp", source)
        self.assertIn("configure:function(child) configureNightmareVisionStandalone(child, paths, prefs, plugins, mods, difficulty)", common)
        session = (ROOT / "source/NightmareVisionStateSession.hx").read_text(encoding="utf-8")
        self.assertIn("PlayState.seedNightmareVisionCommon(interp, paths, prefs, runtime, mods, difficulty, null, entry);", session)
        self.assertIn("PlayState.seedNightmareVisionCommon(child, paths, prefs, plugins, mods, difficulty, null, entry);", session)
        self.assertIn("interp.bindImport('lime.utils.Assets', limeAssets)",
                     (ROOT / "source/NightmareVisionAssetsBindings.hx").read_text(encoding="utf-8"))
        bindings = (ROOT / "source/NightmareVisionAssetsBindings.hx").read_text(encoding="utf-8")
        self.assertIn("interp.bindImport('openfl.Assets', openFlAssets)", bindings)
        self.assertIn("classScope.bindRuntimeClass('openfl.utils.Assets', openFlAssets)",
                     bindings)
        self.assertIn("classScope.bindRuntimeClass('openfl.Assets', openFlAssets)", bindings)


if __name__ == "__main__":
    unittest.main()
