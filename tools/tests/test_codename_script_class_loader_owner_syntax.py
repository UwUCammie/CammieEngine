"""Focused owner-class module loading and safe syntax normalization."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def haxe_fixture_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


def haxe_fixture_command(base, *arguments, with_flixel=False):
    command = [
        str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
        "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
        "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
    ]
    if with_flixel:
        command.extend([
            "-lib", "openfl", "-lib", "lime", "-lib", "flixel",
            "-D", "FLX_STANDARD_ASSETS_DIRECTORY", "-D", "FLX_DEFAULT_SOUND_EXT=ogg",
            "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
        ])
    command.extend(arguments)
    return command


def write_loader_interp_stub(base):
    (base / "CodenameScriptInterp.hx").write_text('''class CodenameScriptInterp {
	public var variables:Map<String,Dynamic>=new Map();
	public function new() {}
	public function bindScriptClassScope(_scope:hscript.ScriptClassScope):Void {}
}''', encoding="utf-8")


class CodenameScriptClassLoaderSyntaxTest(unittest.TestCase):
    def test_owner_import_stringtools_lowers_typed_case_chain(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            write_loader_interp_stub(base)
            owner = base / "owner"
            (owner / "source/demo").mkdir(parents=True)
            (owner / "source/import.hx").write_text(
                "#if !macro\nusing StringTools;\n#end\n", encoding="utf-8")
            (owner / "source/demo/Mall.hx").write_text('''package demo;
class Mall {
 public function new() {}
 public function eventCalled(value1:String):String return value1.toLowerCase().trim();
}''', encoding="utf-8")
            (owner / "source/demo/BadUsing.hx").write_text('''package demo;
class BadUsing {
 public function new() {}
 public function read(value:Dynamic):String return value.trim();
}''', encoding="utf-8")
            (owner / "source/demo/NativeContains.hx").write_text('''package demo;
class NativeContains {
 public function new() {}
 public function hasEntry():Bool {
  var noteTypes:Array<String> = ["special"];
  return noteTypes.contains("special");
 }
}''', encoding="utf-8")
            (base / "Main.hx").write_text(r'''class Main {
 static function main():Void {
  var root=Sys.args()[0];
  var loaded=CodenameScriptClassLoader.load(root,["demo.Mall"],new Map(),new Map());
  if(loaded.diagnostics.length!=0) throw loaded.diagnostics;
  var mall=loaded.scope.createInstance("demo.Mall",[]);
  if(mall.callFunction("eventCalled",["  GF  "])!="gf")
   throw "owner-wide StringTools case chain did not execute";
  loaded.scope.release();
  var dynamicOwner=CodenameScriptClassLoader.load(root,
   ["demo.BadUsing","demo.NativeContains"],new Map(),new Map());
  if(dynamicOwner.diagnostics.length!=0) throw dynamicOwner.diagnostics;
  var dynamicText=dynamicOwner.scope.createInstance("demo.BadUsing",[]);
  if(dynamicText.callFunction("read",["  source  "])!="source")
   throw "runtime String extension did not execute";
  var arrayUser=dynamicOwner.scope.createInstance("demo.NativeContains",[]);
  if(Std.string(arrayUser.callFunction("hasEntry",[]))!="true")
   throw "Array.contains was wrongly rewritten as StringTools.contains";
  dynamicOwner.scope.release();
 }
}''', encoding="utf-8")
            result = subprocess.run(
                haxe_fixture_command(base, "--run", "Main", str(owner)),
                cwd=ROOT, env=haxe_fixture_env(), text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_declared_uninitialized_class_fields_have_haxe_defaults(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            write_loader_interp_stub(base)
            owner = base / "owner"
            module = owner / "source/demo/FieldActor.hx"
            module.parent.mkdir(parents=True)
            module.write_text('''package demo;
class FieldActor {
 public var snd(default, set):Dynamic;
 public var enabled:Bool;
 public var count:Int;
 public var volume:Float;
 public function new() {}
 function set_snd(changed:Dynamic):Dynamic { snd = changed; return snd; }
 public function assign(changed:Dynamic):Void { snd = changed; }
 public function defaults():Array<Dynamic> { return [snd, enabled, count, volume]; }
 public function readSnd():Dynamic { return snd; }
}''', encoding="utf-8")
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.FieldActor'],new Map(),new Map());
  if(loaded.diagnostics.length!=0) throw loaded.diagnostics;
  var actor=loaded.scope.createInstance('demo.FieldActor',[]);
  var values:Array<Dynamic>=actor.callFunction('defaults',[]);
  if(values[0]!=null || values[1]!=false || values[2]!=0 || values[3]!=0)
   throw 'class field defaults were lost: '+values;
  actor.callFunction('assign',['music']);
  var read:Dynamic=actor.callFunction('readSnd',[]);
  if(read!='music') throw 'declared field write failed after construction';
  loaded.scope.release();
 }
}''', encoding="utf-8")
            result = subprocess.run(
                haxe_fixture_command(base, "--run", "Main", str(owner)),
                cwd=ROOT, env=haxe_fixture_env(), text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_stage_shader_filter_binding_uses_owner_proxy_compat(self):
        stage_bindings = (ROOT / "source/PsychCompiledStageBindings.hx").read_text(encoding="utf-8")
        self.assertIn("PsychShaderFilterCompat", stage_bindings)
        self.assertIn("bind(bindings, 'ShaderFilter', PsychShaderFilterCompat);", stage_bindings)
        self.assertIn(
            "bind(bindings, 'openfl.filters.ShaderFilter', PsychShaderFilterCompat);",
            stage_bindings,
        )
        shader_filter_compat = (ROOT / "source/PsychShaderFilterCompat.hx").read_text(encoding="utf-8")
        self.assertIn("class PsychShaderFilterCompat extends ShaderFilter", shader_filter_compat)
        self.assertIn("super(cast unwrapShader(shader));", shader_filter_compat)

        shader_filter = (
            ROOT / ".haxelib/openfl/9,5,2/src/openfl/filters/ShaderFilter.hx"
        ).read_text(encoding="utf-8")
        flx_assets = (
            ROOT / ".haxelib/flixel/6,1,2/flixel/system/FlxAssets.hx"
        ).read_text(encoding="utf-8")
        flx_graphics_shader = (
            ROOT / ".haxelib/flixel/6,1,2/flixel/graphics/tile/FlxGraphicsShader.hx"
        ).read_text(encoding="utf-8")
        graphics_shader = (
            ROOT / ".haxelib/openfl/9,5,2/src/openfl/display/GraphicsShader.hx"
        ).read_text(encoding="utf-8")
        self.assertIn("public function new(shader:Shader)", shader_filter)
        self.assertIn("typedef FlxShader = #if nme Dynamic #else flixel.graphics.tile.FlxGraphicsShader #end;", flx_assets)
        self.assertIn("class FlxGraphicsShader extends GraphicsShader", flx_graphics_shader)
        self.assertIn("class GraphicsShader extends Shader", graphics_shader)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            write_loader_interp_stub(base)
            owner = base / "owner"
            stage = owner / "source/demo/ShaderFilterStage.hx"
            stage.parent.mkdir(parents=True)
            stage.write_text('''package demo;
import openfl.filters.ShaderFilter;
class ShaderFilterStage {
	public function new() {}
	public function wrap(shader:Dynamic):Dynamic { return new ShaderFilter(shader); }
}''', encoding="utf-8")
            filter_module = base / "openfl/filters/ShaderFilter.hx"
            filter_module.parent.mkdir(parents=True)
            filter_module.write_text('''package openfl.filters;
class ShaderFilter {
	public var shader:Dynamic;
	public function new(shader:Dynamic) { this.shader = shader; }
}''', encoding="utf-8")
            (base / "Main.hx").write_text(r'''import hscript.AbstractScriptClass;
import openfl.filters.ShaderFilter;
class Main {
 public static var cwd:String;
 static function main():Void {
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set("openfl.filters.ShaderFilter",ShaderFilter);
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],["demo.ShaderFilterStage"],bindings,new Map());
  if(loaded.diagnostics.length!=0) throw "native ShaderFilter import did not bind: "+loaded.diagnostics;
  var stage=loaded.scope.createInstance("ShaderFilterStage",[]);
  var shader={tag:"rain-shader"};
  var filter=stage.callFunction("wrap",[shader]);
  if(filter==null || !Std.isOfType(filter,ShaderFilter) || Reflect.field(filter,"shader")!=shader)
   throw "the bound ShaderFilter constructor did not retain its shader";
  loaded.scope.release();
 }
}''', encoding="utf-8")
            result = subprocess.run(
                haxe_fixture_command(base, "--run", "Main", str(owner)),
                cwd=ROOT, env=haxe_fixture_env(), text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_payload_free_enum_state_machine_normalizes_safely(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            write_loader_interp_stub(base)
            owner = base / "owner"
            modules = {
                "source/demo/StageEnum.hx": '''package demo;
enum NeneState {
	STATE_DEFAULT;
	STATE_PRE_RAISE;
	STATE_RAISE;
	STATE_READY;
	STATE_LOWER;
}
class StageEnum {
	var current:NeneState = STATE_DEFAULT;
	public function new() {}
	public function advance():String {
		switch (current) {
		case STATE_DEFAULT: current = NeneState.STATE_PRE_RAISE;
		case STATE_PRE_RAISE: current = STATE_RAISE;
		case STATE_RAISE, STATE_LOWER: current = NeneState.STATE_READY;
		case STATE_READY: current = STATE_LOWER;
		case _: current = STATE_DEFAULT;
		}
		return Std.string(current);
	}
}''',
                "source/demo/PayloadEnum.hx": '''package demo;
enum Result { OK; ERROR(String); }
class PayloadEnum {}''',
            }
            for relative, content in modules.items():
                path = owner / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            (base / "Main.hx").write_text(r'''import hscript.AbstractScriptClass;
class Main {
 public static var cwd:String;
 static function main():Void {
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],["demo.StageEnum"],new Map(),new Map());
  if(loaded.diagnostics.length!=0) throw "payload-free state enum did not load: "+loaded.diagnostics;
  var stage=loaded.scope.createInstance("StageEnum",[]);
  if(stage==null || stage.callFunction("advance",[])!="STATE_PRE_RAISE")
   throw "enum initial constructor or qualified transition changed";
  if(stage.callFunction("advance",[])!="STATE_RAISE")
   throw "unqualified enum switch case or transition changed";
  if(stage.callFunction("advance",[])!="STATE_READY")
   throw "comma-separated enum switch cases were not preserved";
  if(stage.callFunction("advance",[])!="STATE_LOWER"
   || stage.callFunction("advance",[])!="STATE_READY")
   throw "the second enum constructor in a multi-case branch was not preserved";
  loaded.scope.release();

  var payload=CodenameScriptClassLoader.load(Sys.args()[0],["demo.PayloadEnum"],new Map(),new Map());
  if(payload.diagnostics.length!=1 || payload.diagnostics[0].indexOf("enum constructor payloads are not supported: Result.ERROR")<0)
   throw "payload enum was not rejected with a bounded diagnostic: "+payload.diagnostics;
  payload.scope.release();
 }
}''', encoding="utf-8")
            result = subprocess.run(
                haxe_fixture_command(base, "--run", "Main", str(owner)),
                cwd=ROOT, env=haxe_fixture_env(), text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_wildcards_aliases_final_and_narrow_stringtools_using(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            write_loader_interp_stub(base)
            owner = base / "owner"
            modules = {
                "source/demo/Main.hx": '''package demo;
import demo.parts.*;
class Main {
	public function new() {}
	public function run():String {
		var first = new Widget();
		var second = new Other();
		return first.value() + ":" + second.value();
	}
}''',
                "source/demo/parts/Widget.hx": '''package demo.parts;
class Widget {
	public function new() {}
	public function value():String { return "widget"; }
}''',
                "source/demo/parts/Other.hx": '''package demo.parts;
import demo.parts.Widget as WidgetAlias;
class Other extends WidgetAlias {
	public function new() { super(); }
	override public function value():String { return "other"; }
}''',
                "source/demo/parts/Unused.hx": '''package demo.parts;
enum Unused { NEVER_LOAD_THIS; }
''',
                "source/demo/parts/Constants.hx": '''package demo.parts;
class Constants {
	public final value:Int = 40;
	public function new() {}
	public function read():Int {
		final local:Int = 2;
		return value + local;
	}
}''',
                "source/demo/parts/Strings.hx": '''package demo.parts;
using StringTools;
class Strings {
	public function new() {}
	public function normalize(value:String):String { return value.trim().toLowerCase(); }
}''',
                "source/demo/parts/NativeAlias.hx": '''package demo.parts;
import demo.NativeValue as Token;
class NativeAlias {
	public function new() {}
	public function read():String { return Token.tag(); }
}''',
                "source/demo/parts/GenericOwner.hx": '''package demo.parts;
class GenericOwner {
	public function new() {}
	public function value():String { return "owner-generic"; }
}''',
                "source/demo/parts/GenericUser.hx": '''package demo.parts;
import demo.parts.GenericOwner;
class GenericUser {
	public function new() {}
	public function ownerValue():String {
		var owner = new GenericOwner<String>();
		return owner.value();
	}
	public function mapValue():String {
		var values = new Map<String, Array<Dynamic>>();
		values.set("entry", [17]);
		return Std.string(values.get("entry")[0]);
	}
	public function intMapValue():String {
		var values = new Map<Int, String>();
		values.set(17, "int-map");
		return values.get(17);
	}
	public function nativeMapValue():String {
		var values = new haxe.ds.StringMap<String, Dynamic>();
		values.set("entry", "native-generic");
		return values.get("entry");
	}
}''',
                "source/demo/parts/BadGeneric.hx": '''package demo.parts;
class BadGeneric {
	public function run():Dynamic return new MissingType<String>();
}''',
                "source/demo/parts/MalformedGeneric.hx": '''package demo.parts;
class MalformedGeneric {
	public function run():Dynamic return new haxe.ds.StringMap<String, Array<Dynamic>();
}''',
                "source/demo/parts/AmbiguousGeneric.hx": '''package demo.parts;
import demo.parts.left.Same;
import demo.parts.right.Same;
class AmbiguousGeneric {
	public function run():Dynamic return new Same<String>();
}''',
                "source/demo/parts/UnsupportedMapKey.hx": '''package demo.parts;
class UnsupportedMapKey {
	public function run():Dynamic return new Map<Dynamic, String>();
}''',
                "source/demo/parts/UnusedExternalImport.hx": '''package demo.parts;
import openfl.utils.AssetType;
class UnusedExternalImport {
	public function value():String {
		// AssetType in a comment is not an import use.
		var AssetTypeMode:String = "unused";
		return AssetTypeMode + ":AssetType";
	}
}''',
                "source/demo/parts/UsedExternalEnumImport.hx": '''package demo.parts;
import openfl.utils.AssetType;
class UsedExternalEnumImport {
	public var kind:AssetType;
	public function new() {}
}''',
                "source/demo/parts/OwnerImportKeeper.hx": '''package demo.parts;
import demo.parts.Widget;
class OwnerImportKeeper {
	public function new() {}
}''',
                "source/demo/parts/PsychSongSyntax.hx": '''package demo.parts;
import haxe.Json;
class PsychSongSyntax {
	public function new() {}
	public function convert(sectionsData:Array<Dynamic>):String {
		if (sectionsData == null) { return "none"; }
		var result:String = "";
		for (section in sectionsData) {
			var beats:Null<Float> = cast section.sectionBeats;
			if (beats == null) { beats = 4; }
			result += Std.string(beats);
		}
		return result;
	}
	public function parseJSON(rawData:String):String {
		var songJson:Dynamic = cast Json.parse(rawData);
		return songJson.song;
	}
	public function memberCast(value:Dynamic):Dynamic { return value.cast(); }
	public function castText():String {
		// cast (comment, Type) stays inert.
		return "cast (string, Type)";
	}
}''',
                "source/demo/parts/OptionsUse.hx": '''package demo.parts;
class OptionsUse {
	public function new() {}
	public function read():Dynamic { return Options.gameplayShaders && Options.lowMemoryMode; }
}''',
                "source/demo/parts/OptionsPointer.hx": '''package demo.parts;
class OptionsPointer {
	public var rows:Array<Dynamic> = [{label:"VRAM Only", pointer:"gpuOnlyBitmaps"}];
}''',
                "source/demo/parts/OptionsTextOnly.hx": '''package demo.parts;
class OptionsTextOnly {
	// Options.gpuOnlyBitmaps and pointer: "gpuOnlyBitmaps" are not executable references.
	public var note:String = "Options.gpuOnlyBitmaps pointer: \\\"gpuOnlyBitmaps\\\"";
}''',
                "source/demo/parts/TypedCast.hx": '''package demo.parts;
class TypedCast {
	public function read(value:Dynamic):Dynamic return cast(value, String);
}''',
                "source/demo/parts/ParenthesizedCast.hx": '''package demo.parts;
class ParenthesizedCast {
	public function read(value:Dynamic):Dynamic return cast (value);
}''',
                "source/demo/parts/MissingCastOperand.hx": '''package demo.parts;
class MissingCastOperand {
	public function read():Dynamic return cast;
}''',
                "source/demo/parts/BadFinal.hx": '''package demo.parts;
class BadFinal {
	public function read():Int {
		final value:Int = 1;
		value = 2;
		return value;
	}
}''',
                "source/demo/parts/BadUsing.hx": '''package demo.parts;
using StringTools;
class BadUsing {
	public function read(value:Dynamic):String return value.trim();
}''',
                "source/demo/parts/ShadowAlias.hx": '''package demo.parts;
import demo.parts.Widget as WidgetAlias;
class ShadowAlias {
	public function read(WidgetAlias:String):String return WidgetAlias;
}''',
            }
            for relative, content in modules.items():
                path = owner / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            (base / "Main.hx").write_text(r'''import haxe.Json;
import hscript.AbstractScriptClass;
class Main {
 public static var cwd:String;
 static function main():Void {
  var root=Sys.args()[0];
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set("demo.NativeValue",{tag:function() return "native-alias"});
  bindings.set("haxe.Json",{parse:function(value:String):Dynamic return Json.parse(value)});
  var loaded=CodenameScriptClassLoader.load(root,
   ["demo.Main","demo.parts.Constants","demo.parts.Strings","demo.parts.NativeAlias","demo.parts.GenericUser",
    "demo.parts.OptionsUse","demo.parts.OptionsPointer","demo.parts.OptionsTextOnly"],
   bindings,new Map());
  if(loaded.diagnostics.length!=0) throw "unexpected loader diagnostics: "+loaded.diagnostics;
  if(loaded.sourceUseDiagnostics.length!=1
   || loaded.sourceUseDiagnostics[0].indexOf("source/demo/parts/OptionsPointer.hx:3:")<0
   || loaded.sourceUseDiagnostics[0].indexOf("Options.gpuOnlyBitmaps literal Options pointer")<0)
   throw "unsupported VRAM-only pointer was not bounded and owner-relative: "+loaded.sourceUseDiagnostics;
  var main=loaded.scope.createInstance("Main",[]);
  if(main==null || main.callFunction("run",[])!="widget:other")
   throw "wildcard expansion or source-class alias failed";
  var constants=loaded.scope.createInstance("Constants",[]);
  if(constants==null || Std.string(constants.callFunction("read",[]))!="42")
   throw "initialized final field/local normalization failed";
  var strings=loaded.scope.createInstance("Strings",[]);
  if(strings==null || strings.callFunction("normalize",["  Hi There  "])!="hi there")
   throw "typed StringTools using normalization failed";
  var nativeAlias=loaded.scope.createInstance("NativeAlias",[]);
  if(nativeAlias==null || nativeAlias.callFunction("read",[])!="native-alias")
   throw "owner-bound import alias failed";
  var generic=loaded.scope.createInstance("GenericUser",[]);
  if(generic==null || generic.callFunction("ownerValue",[])!="owner-generic")
   throw "known owner generic constructor was not erased safely";
  if(generic.callFunction("mapValue",[])!="17")
   throw "String-key Haxe Map did not keep its runtime implementation";
  if(generic.callFunction("intMapValue",[])!="int-map")
   throw "Int-key Haxe Map did not keep its runtime implementation";
  if(generic.callFunction("nativeMapValue",[])!="native-generic")
   throw "known native generic constructor was not erased safely";
  loaded.scope.release();

  var badFinal=CodenameScriptClassLoader.load(root,["demo.parts.BadFinal"],new Map(),new Map());
  if(badFinal.diagnostics.length!=1 || badFinal.diagnostics[0].indexOf("final variable value is reassigned")<0)
   throw "final reassignment was silently normalized: "+badFinal.diagnostics;
  badFinal.scope.release();
  var badUsing=CodenameScriptClassLoader.load(root,["demo.parts.BadUsing"],new Map(),new Map());
  if(badUsing.diagnostics.length!=1 || badUsing.diagnostics[0].indexOf("no statically proven String receiver")<0)
   throw "dynamic using receiver was silently normalized: "+badUsing.diagnostics;
  badUsing.scope.release();
  var shadow=CodenameScriptClassLoader.load(root,["demo.parts.ShadowAlias"],new Map(),new Map());
  if(shadow.diagnostics.length!=1 || shadow.diagnostics[0].indexOf("shadows a module declaration")<0)
   throw "shadowing class alias was silently rewritten: "+shadow.diagnostics;
  shadow.scope.release();
  var badGeneric=CodenameScriptClassLoader.load(root,["demo.parts.BadGeneric"],new Map(),new Map());
  if(badGeneric.diagnostics.length!=1 || badGeneric.diagnostics[0].indexOf("not a known owner or native class")<0)
   throw "unknown generic constructor was silently erased: "+badGeneric.diagnostics;
  badGeneric.scope.release();
  var malformed=CodenameScriptClassLoader.load(root,["demo.parts.MalformedGeneric"],new Map(),new Map());
  if(malformed.diagnostics.length!=1 || malformed.diagnostics[0].indexOf("malformed explicit constructor type parameters")<0)
   throw "unbalanced generic constructor was not rejected explicitly: "+malformed.diagnostics;
  malformed.scope.release();
  var ambiguous=CodenameScriptClassLoader.load(root,["demo.parts.AmbiguousGeneric"],new Map(),new Map());
  if(ambiguous.diagnostics.length!=1 || ambiguous.diagnostics[0].indexOf("ambiguous generic constructor type Same")<0)
   throw "ambiguous generic constructor was guessed: "+ambiguous.diagnostics;
  ambiguous.scope.release();
  var unsupportedMap=CodenameScriptClassLoader.load(root,["demo.parts.UnsupportedMapKey"],new Map(),new Map());
  if(unsupportedMap.diagnostics.length!=1 || unsupportedMap.diagnostics[0].indexOf("has no proven runtime map implementation")<0)
   throw "unsupported Map specialization was silently erased: "+unsupportedMap.diagnostics;
  unsupportedMap.scope.release();

  var unusedExternal=CodenameScriptClassLoader.load(root,["demo.parts.UnusedExternalImport"],new Map(),new Map());
  if(unusedExternal.diagnostics.length!=0)
   throw "unreferenced external import was not pruned: "+unusedExternal.diagnostics;
  var unusedInstance=unusedExternal.scope.createInstance("UnusedExternalImport",[]);
  if(unusedInstance==null || unusedInstance.callFunction("value",[])!="unused:AssetType")
   throw "token-aware unused import normalization changed the module body";
  unusedExternal.scope.release();

  var usedEnum=CodenameScriptClassLoader.load(root,["demo.parts.UsedExternalEnumImport"],new Map(),new Map());
  var expectedEnumDiagnostic="source/demo/parts/UsedExternalEnumImport.hx: no explicit owner binding or source module for import openfl.utils.AssetType";
  if(usedEnum.diagnostics.length!=1 || usedEnum.diagnostics[0]!=expectedEnumDiagnostic)
   throw "a used, unsupported enum abstract lost its exact import diagnostic: "+usedEnum.diagnostics;
  usedEnum.scope.release();

  var ownerImport=CodenameScriptClassLoader.load(root,["demo.parts.OwnerImportKeeper"],new Map(),new Map());
  if(ownerImport.diagnostics.length!=0 || ownerImport.scope.findDescriptor("demo.parts.Widget")==null)
   throw "an unreferenced owner import was pruned from the descriptor graph: "+ownerImport.diagnostics;
  ownerImport.scope.release();

  var psychSong=CodenameScriptClassLoader.load(root,["demo.parts.PsychSongSyntax"],bindings,new Map());
  if(psychSong.diagnostics.length!=0)
   throw "Psych Song untyped casts did not parse: "+psychSong.diagnostics;
  var psych=psychSong.scope.createInstance("PsychSongSyntax",[]);
  if(psych==null || psych.callFunction("convert",[[{sectionBeats:null},{sectionBeats:2.5}]])!="42.5")
   throw "untyped cast erasure changed the Psych section-loop result";
  if(psych.callFunction("parseJSON",['{"song":"chart"}'])!="chart")
   throw "untyped cast erasure changed the Psych Json.parse result";
  if(psych.callFunction("castText",[])!="cast (string, Type)")
   throw "cast text in comments or strings was normalized as code";
  var castReceiver:Dynamic={};
  Reflect.setField(castReceiver,"cast",function() return "member-call");
  if(psych.callFunction("memberCast",[castReceiver])!="member-call")
   throw "member access named cast was normalized as a prefix cast";
  psychSong.scope.release();

  var typedCast=CodenameScriptClassLoader.load(root,["demo.parts.TypedCast"],new Map(),new Map());
  if(typedCast.diagnostics.length!=1 || typedCast.diagnostics[0].indexOf("typed or parenthesized cast syntax is unsupported")<0)
   throw "typed cast syntax was silently erased: "+typedCast.diagnostics;
  typedCast.scope.release();
  var parenthesizedCast=CodenameScriptClassLoader.load(root,["demo.parts.ParenthesizedCast"],new Map(),new Map());
  if(parenthesizedCast.diagnostics.length!=1 || parenthesizedCast.diagnostics[0].indexOf("typed or parenthesized cast syntax is unsupported")<0)
   throw "ambiguous parenthesized cast syntax was silently erased: "+parenthesizedCast.diagnostics;
  parenthesizedCast.scope.release();
  var missingCast=CodenameScriptClassLoader.load(root,["demo.parts.MissingCastOperand"],new Map(),new Map());
  if(missingCast.diagnostics.length!=1 || missingCast.diagnostics[0].indexOf("untyped cast has no expression operand")<0)
   throw "untyped cast without an operand was silently erased: "+missingCast.diagnostics;
  missingCast.scope.release();
 }
}''', encoding="utf-8")
            result = subprocess.run(
                haxe_fixture_command(base, "--run", "Main", str(owner)),
                cwd=ROOT, env=haxe_fixture_env(), text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_flxsprite_animation_name_is_a_proven_stringtools_receiver(self):
        flixel = ROOT / ".haxelib/flixel/6,1,2/flixel"
        sprite_source = (flixel / "FlxSprite.hx").read_text(encoding="utf-8")
        controller_source = (flixel / "animation/FlxAnimationController.hx").read_text(encoding="utf-8")
        animation_source = (flixel / "animation/FlxAnimation.hx").read_text(encoding="utf-8")
        base_animation_source = (flixel / "animation/FlxBaseAnimation.hx").read_text(encoding="utf-8")
        self.assertIn("public var animation:FlxAnimationController;", sprite_source)
        self.assertIn("public var curAnim(get, set):FlxAnimation;", controller_source)
        self.assertIn("class FlxAnimation extends FlxBaseAnimation", animation_source)
        self.assertIn("public var name:String;", base_animation_source)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            write_loader_interp_stub(base)
            owner = base / "owner"
            modules = {
                "source/demo/NativeSpriteNote.hx": '''package demo;
import flixel.FlxSprite;
using StringTools;
class NativeSpriteNote extends FlxSprite {
	public function new() { super(); }
	public function hasEnd():Bool { return animation.curAnim.name.endsWith("end"); }
}''',
                # Psych's Note relies on the host's unqualified FlxSprite symbol.
                # Exercise that statically supplied native binding without invoking
                # superclass construction in this parsing-only case.
                "source/demo/ImplicitSpriteNote.hx": '''package demo;
using StringTools;
class ImplicitSpriteNote extends FlxSprite {
	public function hasEnd():Bool { return animation.curAnim.name.endsWith("end"); }
}''',
                "source/demo/OtherProperty.hx": '''package demo;
import flixel.FlxSprite;
using StringTools;
class OtherProperty extends FlxSprite {
	public function hasEnd():Bool { return animation.curAnim.frameRate.endsWith("end"); }
}''',
                "source/demo/ShadowedAnimation.hx": '''package demo;
import flixel.FlxSprite;
using StringTools;
class ShadowedAnimation extends FlxSprite {
	public function hasEnd(animation:Dynamic):Bool { return animation.curAnim.name.endsWith("end"); }
}''',
                "source/demo/NotSprite.hx": '''package demo;
using StringTools;
class NotSprite {
	public function hasEnd():Bool { return animation.curAnim.name.endsWith("end"); }
}''',
            }
            for relative, content in modules.items():
                path = owner / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            flx_sprite = base / "flixel/FlxSprite.hx"
            flx_sprite.parent.mkdir(parents=True)
            flx_sprite.write_text('''package flixel;
class FlxSprite {
	public var animation:Dynamic;
	public function new() { animation = {curAnim:{name:"danceend", frameRate:24}}; }
}''', encoding="utf-8")
            (base / "Main.hx").write_text(r'''import flixel.FlxSprite;
class Main {
 public static var cwd:String;
 static function main():Void {
  var root=Sys.args()[0];
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set("flixel.FlxSprite",FlxSprite);
  bindings.set("FlxSprite",FlxSprite);
  var loaded=CodenameScriptClassLoader.load(root,
   ["demo.NativeSpriteNote","demo.ImplicitSpriteNote"],bindings,new Map());
  if(loaded.diagnostics.length!=0) throw "native FlxSprite String receiver failed to normalize: "+loaded.diagnostics;
  if(loaded.scope.findDescriptor("demo.ImplicitSpriteNote")==null)
   throw "unqualified native FlxSprite binding did not prove animation.curAnim.name";
  var note=loaded.scope.createInstance("demo.NativeSpriteNote",[]);
  if(note==null || note.callFunction("hasEnd",[])!=true)
   throw "StringTools.endsWith lowering changed the native FlxSprite receiver result";
  loaded.scope.release();

  for(module in ["demo.OtherProperty","demo.ShadowedAnimation","demo.NotSprite"]) {
   var rejected=CodenameScriptClassLoader.load(root,[module],bindings,new Map());
   if(rejected.diagnostics.length!=1
    || rejected.diagnostics[0].indexOf("no statically proven String receiver")<0)
    throw "unsafe native animation StringTools receiver was accepted for "+module+": "+rejected.diagnostics;
   rejected.scope.release();
  }
  var fakeBindings:Map<String,Dynamic>=new Map();
  var fakeSprite={};
  fakeBindings.set("flixel.FlxSprite",fakeSprite);
  fakeBindings.set("FlxSprite",fakeSprite);
  var fake=CodenameScriptClassLoader.load(root,["demo.NativeSpriteNote"],fakeBindings,new Map());
  if(fake.diagnostics.length!=1
   || fake.diagnostics[0].indexOf("no statically proven String receiver")<0)
   throw "a non-native FlxSprite binding was treated as a typed String receiver: "+fake.diagnostics;
  fake.scope.release();
 }
}''', encoding="utf-8")
            result = subprocess.run(
                haxe_fixture_command(base, "--run", "Main", str(owner)),
                cwd=ROOT, env=haxe_fixture_env(), text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_flixel_class_bindings_and_native_use(self):
        bindings_source = (ROOT / "source/CodenameImportBindings.hx").read_text(encoding="utf-8")
        self.assertIn("import flixel.animation.FlxAnimationController;", bindings_source)
        self.assertIn(
            "bindings.set('flixel.animation.FlxAnimationController', FlxAnimationController);",
            bindings_source,
        )
        self.assertIn("import flixel.util.FlxSort;", bindings_source)
        self.assertIn("bindings.set('flixel.util.FlxSort', FlxSort);", bindings_source)
        self.assertIn("import flixel.util.FlxDestroyUtil;", bindings_source)
        self.assertIn("bindings.set('flixel.util.FlxDestroyUtil', FlxDestroyUtil);", bindings_source)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            write_loader_interp_stub(base)
            owner = base / "owner"
            controller = owner / "source/demo/PsychAnimationController.hx"
            controller.parent.mkdir(parents=True)
            controller.write_text('''package demo;
import flixel.animation.FlxAnimationController;
class PsychAnimationController extends FlxAnimationController {
	public function new() {}
}''', encoding="utf-8")
            sort_user = owner / "source/demo/SortUser.hx"
            sort_user.write_text('''package demo;
import flixel.util.FlxDestroyUtil;
import flixel.util.FlxSort;
class SortUser {
	public function new() {}
	public function compare():Int {
		FlxDestroyUtil.destroy(null);
		return FlxSort.byValues(-1, 1, 2);
	}
}''', encoding="utf-8")
            (base / "Main.hx").write_text(r'''import flixel.animation.FlxAnimationController;
import flixel.util.FlxDestroyUtil;
import flixel.util.FlxSort;
class Main {
 public static var cwd:String;
 static function main():Void {
  var nativeClass=Type.resolveClass("flixel.animation.FlxAnimationController");
  if(nativeClass==null || nativeClass!=FlxAnimationController)
   throw "pinned Flixel class did not resolve at runtime";
  var sortClass=Type.resolveClass("flixel.util.FlxSort");
  if(sortClass==null || sortClass!=FlxSort)
   throw "pinned FlxSort class did not resolve at runtime";
  var destroyClass=Type.resolveClass("flixel.util.FlxDestroyUtil");
  if(destroyClass==null || destroyClass!=FlxDestroyUtil)
   throw "pinned FlxDestroyUtil class did not resolve at runtime";
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set("flixel.animation.FlxAnimationController",nativeClass);
  bindings.set("flixel.util.FlxSort",sortClass);
  bindings.set("flixel.util.FlxDestroyUtil",destroyClass);
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],
   ["demo.PsychAnimationController","demo.SortUser"],bindings,new Map());
  if(loaded.diagnostics.length!=0)
   throw "explicit Flixel class imports failed: "+loaded.diagnostics;
  if(loaded.scope.findDescriptor("demo.PsychAnimationController")==null)
   throw "owner class extending the bound native class was not registered";
  if(loaded.scope.findBinding("flixel.animation.FlxAnimationController")!=nativeClass)
   throw "the owner class scope lost the explicitly bound native class";
  if(loaded.scope.findBinding("flixel.util.FlxSort")!=sortClass)
   throw "the owner class scope lost the explicitly bound FlxSort class";
  if(loaded.scope.findBinding("flixel.util.FlxDestroyUtil")!=destroyClass)
   throw "the owner class scope lost the explicitly bound FlxDestroyUtil class";
  var sorter=loaded.scope.createInstance("demo.SortUser",[]);
  if(sorter==null || sorter.callFunction("compare",[])!=-1)
   throw "owner HScript could not use the explicitly bound FlxSort class";
  loaded.scope.release();
 }
}''', encoding="utf-8")
            result = subprocess.run(
                haxe_fixture_command(base, "--run", "Main", str(owner), with_flixel=True),
                cwd=ROOT, env=haxe_fixture_env(), text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
