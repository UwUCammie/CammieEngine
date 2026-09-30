"""Bounded Haxe surface normalization shared by Codename script families."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR_PACK = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "codename/D-Sides REDUX Codename Engine (Cancelled)/mods/D-Sides REDUX/data/events/Change Character.pack"
)
DONOR_STAGE = DONOR_PACK.parents[1] / "stages/stageD.hx"
DONOR_LYRICS = DONOR_PACK.parents[1] / "scripts/Lyrics.hx"
DONOR_COMPOSER_INTRO = DONOR_PACK.parents[2] / "songs/composerIntro.hx"
DONOR_HL17 = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "codename/hl17_v3/mods/HL17/source/HLTypeText.hx"
)


class CodenameScriptParserTest(unittest.TestCase):
    def test_dollar_escape_and_nested_interpolation_keep_haxe_meaning(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text(r'''
import hscript.Interp;
class Main {
 static function main():Void {
  var source = "var name='fixture'; var n=4; "
   + "var label='$$name|$name|${n + 1}|$${n}'; "
   + "var nested='outer:${'inner:$name'}'; "
   + "var quoted=\"$name|${n}\"; // '$ignored'\n"
   + "var suffix='$$'; function values() return [label,nested,quoted,suffix];";
  var prepared=CodenameScriptParser.prepare(source,new Map(),"dollar-escape");
  if (prepared.program==null || CodenameScriptParser.hasFatalDiagnostics(prepared))
   throw Std.string(prepared.diagnostics);
  var interp=new Interp();
  interp.execute(prepared.program);
  var actual:Array<String> = Reflect.callMethod(null,interp.variables.get('values'),[]);
  var expected=["$name|fixture|5|${n}", 'outer:inner:fixture', "$name|${n}", '$'];
  for (index in 0...expected.length) if (actual[index]!=expected[index])
   throw index+': '+actual[index];
 }
}''')
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                 "--main", "Main", "--interp"], cwd=ROOT,
                text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_final_local_declaration_parses_without_changing_text_literals(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''import hscript.Interp;
class Main {
 static function main():Void {
  var source="function read() { final value:Int = 7; return value; }\\n"
   +"var text = 'final value:Int = 9'; // final ignored:Int = 2\\n";
  var prepared=CodenameScriptParser.prepare(source,new Map(),"final-local");
  if(prepared.program==null || CodenameScriptParser.hasFatalDiagnostics(prepared))
   throw "final local did not parse: "+[for(d in prepared.diagnostics) d.message].join(";");
  if(prepared.source.indexOf("var   value:Int = 7")<0
   || prepared.source.indexOf("'final value:Int = 9'")<0
   || prepared.source.indexOf("// final ignored:Int = 2")<0)
   throw "final normalization touched a non-declaration: "+prepared.source;
  var interpreter=new Interp();
  interpreter.execute(prepared.program);
  var read:Dynamic=interpreter.variables.get("read");
  if(read()==7) return;
  throw "final local initializer changed behavior";
 }
}''', encoding="utf-8")
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                                "--run", "Main"], cwd=ROOT,
                               text=True, capture_output=True, timeout=30)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_braced_haxe_interpolation_evaluates_expressions_and_rejects_open_braces(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text(r'''import hscript.Interp;
class Main {
 static function main():Void {
  var prepared=CodenameScriptParser.prepare("var label='combo${game.combo}';",new Map(),"braced-interpolation");
  if(prepared.program==null || CodenameScriptParser.hasFatalDiagnostics(prepared))
   throw "braced property interpolation did not parse: "+[for(item in prepared.diagnostics) item.message].join(";");
  var interp=new Interp();
  interp.variables.set("game",{combo:42});
  var label=interp.execute(prepared.program);
  if(label!="combo42")
   throw "braced property interpolation changed string conversion: "+label+" source="+prepared.source;

  var nested=CodenameScriptParser.prepare("var label='sum=${game.combo + 1}';",new Map(),"balanced-interpolation");
  if(nested.program==null || CodenameScriptParser.hasFatalDiagnostics(nested))
   throw "balanced Haxe expression interpolation did not parse: "+[for(item in nested.diagnostics) item.message].join(";");
  label=interp.execute(nested.program);
  if(label!="sum=43")
   throw "braced expression interpolation changed arithmetic or string conversion: "+label;

  var malformed=CodenameScriptParser.prepare("var label='combo${game.combo';",new Map(),"malformed-interpolation");
  var rejected=false;
  for(item in malformed.diagnostics) if(item.code=="unsupported-haxe-surface"
   && item.message.indexOf("Haxe interpolation expression")>=0) rejected=true;
  if(malformed.program!=null || !rejected)
   throw "unterminated braced interpolation was not reported explicitly: "+[for(item in malformed.diagnostics) item.message].join(";");
 }
}''', encoding="utf-8")
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                                "--run", "Main"], cwd=ROOT,
                               text=True, capture_output=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_hl17_shader_and_low_memory_options_are_supported_but_vram_is_not(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text(r'''class Main {
 static function main():Void {
  var stage=CodenameScriptParser.prepare(
   'if (Options.lowMemoryMode) return;\n', new Map(), "data/stages/17.hx");
  var song=CodenameScriptParser.prepare(
   'if (Options.gameplayShaders) enableShader();\n', new Map(),
   "songs/linkinteen-parks/scripts/script.hx");
  var vram=CodenameScriptParser.prepare('var row = {pointer:"gpuOnlyBitmaps"};',
   new Map(), "source/HLOptionsWindow.hx");
  var quiet=CodenameScriptParser.prepare(
   '// Options.gpuOnlyBitmaps\nvar text = "Options.lowMemoryMode";\n'
    +'/* Options.gameplayShaders */\n', new Map(), "stages/quiet.hx");
  if (stage.sourceUseDiagnostics.length!=0 || song.sourceUseDiagnostics.length!=0)
   throw "supported HL17 Options reads still report as unsupported: "+stage.sourceUseDiagnostics+song.sourceUseDiagnostics;
  if (vram.sourceUseDiagnostics.length!=1
   || vram.sourceUseDiagnostics[0].indexOf("source/HLOptionsWindow.hx:1:")<0
   || vram.sourceUseDiagnostics[0].indexOf("Options.gpuOnlyBitmaps literal Options pointer")<0)
   throw "unsupported VRAM-only pointer was not reported with owner-relative path: "+vram.sourceUseDiagnostics;
  if (quiet.sourceUseDiagnostics.length!=0)
   throw "comments or ordinary string literals were reported as source uses: "+quiet.sourceUseDiagnostics;
  if (vram.sourceUseDiagnostics[0].indexOf("static source evidence")<0
   || vram.sourceUseDiagnostics[0].indexOf("not an observed runtime read")<0)
   throw "static evidence was mislabeled as an observed runtime read";
 }
}''')
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                                "--run", "Main"],
                               cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    @unittest.skipUnless(DONOR_COMPOSER_INTRO.is_file() and DONOR_HL17.is_file(),
                         "mounted Codename class sources unavailable")
    def test_unused_mounted_enum_recovers_while_used_enum_and_class_remain_fatal(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''import sys.io.File;
import hscript.ParserEx;
import hscript.Interp;
class Main {
 static function main():Void {
  var composer=File.getContent(Sys.args()[0]);
  var imports:Map<String,Dynamic>=new Map();
  imports.set("flixel.text.FlxTextAlign",{});
  imports.set("flixel.text.FlxTextBorderStyle",{});
  var prepared=CodenameScriptParser.prepare(composer,imports,"composerIntro");
  if(prepared.program==null || CodenameScriptParser.hasFatalDiagnostics(prepared))
    throw "unused mounted enum blocked surrounding script: "+[for(item in prepared.diagnostics) item.message].join(";");
  var enumDiagnostic=false;
  for(item in prepared.diagnostics) if(item.code=="unused-enum-elided" && item.recoverable==true
    && item.line==4 && item.message.indexOf("ComposerData")>=0
    && item.message.indexOf("no identifier references")>=0) enumDiagnostic=true;
  if(!enumDiagnostic) throw "missing recoverable line-mapped enum diagnostic: "+[for(item in prepared.diagnostics) item.message].join(";");
  var interp=new Interp();
  interp.variables.set("SONG",{meta:{name:"fixture-unmapped"}});
  interp.execute(prepared.program);
  var getStartStep:Dynamic=interp.variables.get("getStartStep");
  if(getStartStep==null || getStartStep()!=0)
    throw "surrounding mounted script was not executable after enum removal";
  var moduleParserRejected=false;
  try new ParserEx().parseModule(composer,"composerIntro") catch(error:Dynamic) {
   moduleParserRejected=Std.string(error)=="EUnexpected(enum)";
  }
  if(!moduleParserRejected) throw "hscript-ex unexpectedly accepted the donor enum module";

  var referenced=CodenameScriptParser.prepare("enum Mode { START, END }\\nvar selected=Mode.START;",
    new Map(),"referenced-enum");
  if(referenced.program!=null) throw "referenced enum unexpectedly produced a program";
  var referencedDiagnostic=false;
  for(item in referenced.diagnostics) if(item.code=="class-declaration" && item.recoverable!=true
    && item.line==1 && item.message.indexOf("enum Mode")>=0) referencedDiagnostic=true;
  if(!referencedDiagnostic) throw "referenced enum was not reported as unsupported";

  var constructorUse=CodenameScriptParser.prepare("enum Choice { START, END }\\nvar selected=START;",
    new Map(),"unqualified-enum-constructor");
  if(constructorUse.program!=null || !CodenameScriptParser.hasFatalDiagnostics(constructorUse))
    throw "unqualified enum constructor reference was incorrectly elided";
  var interpolationUse=CodenameScriptParser.prepare("enum Marker { BEGIN, END }\\nvar label='$Marker';",
    new Map(),"interpolated-enum-reference");
  if(interpolationUse.program!=null || !CodenameScriptParser.hasFatalDiagnostics(interpolationUse))
    throw "Haxe single-quoted interpolation reference was incorrectly elided";
  var expressionInterpolationUse=CodenameScriptParser.prepare("enum Marker { BEGIN, END }\\nvar label='${Std.string(Marker)}';",
    new Map(),"expression-interpolated-enum-reference");
  if(expressionInterpolationUse.program!=null || !CodenameScriptParser.hasFatalDiagnostics(expressionInterpolationUse))
    throw "braced Haxe interpolation reference was incorrectly elided";

  var textOnly=CodenameScriptParser.prepare("enum Marker { BEGIN, END }\\n// Marker\\nvar label='Marker';\\nfunction readLabel() return label;",
    new Map(),"enum-text-reference");
  if(textOnly.program==null || textOnly.diagnostics.length!=1
    || textOnly.diagnostics[0].code!="unused-enum-elided" || !textOnly.diagnostics[0].recoverable)
    throw "comment/string text was incorrectly counted as a type reference";
  var nested=CodenameScriptParser.prepare("function scope() {\\n enum Nested { A, B }\\n return true;\\n}",
    new Map(),"nested-enum");
  if(nested.program!=null || !CodenameScriptParser.hasFatalDiagnostics(nested))
    throw "nested enum was incorrectly elided";

  var mapping=CodenameScriptParser.prepare("enum Safe { A, B }\\n\\nclass StillUnsupported {}",
    new Map(),"enum-line-mapping");
  var classLine=false;
  for(item in mapping.diagnostics) if(item.code=="class-declaration" && item.line==3) classLine=true;
  if(!classLine) throw "enum removal shifted the following declaration line";

  var hl=CodenameScriptParser.prepare(File.getContent(Sys.args()[1]),new Map(),"HLTypeText");
  if(hl.program!=null || !CodenameScriptParser.hasFatalDiagnostics(hl)) throw "unsupported class unexpectedly produced a program";
  var classDiagnostic=false;
  for(item in hl.diagnostics) if(item.code=="class-declaration"
    && item.message.indexOf("class HLTypeText")>=0
    && item.message.indexOf("owner-scoped module loader")>=0) classDiagnostic=true;
  if(!classDiagnostic) throw "missing named class diagnostic: "+[for(item in hl.diagnostics) item.message].join(";");
 }
}''')
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                                "--run", "Main", str(DONOR_COMPOSER_INTRO), str(DONOR_HL17)],
                               cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_global_and_state_bindings_expose_map_compat_alias(self):
        source = (ROOT / "source/CodenameModBindings.hx").read_text()
        self.assertIn("result.set('CodenameMapCompat', CodenameMapCompat);", source)

    def test_top_level_static_map_declarations_execute_with_class_keys(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''
import hscript.Interp;
import hscript.Expr;
class TitleState {}
class MainMenuState {}
class Main {
 static function main():Void {
  var source='static var routes:Map<Dynamic, String> = [\\n'
    +'  TitleState => "ImportedMain",\\n'
    +'  MainMenuState => "ImportedMain",\\n'
    +'];\\nfunction route(value) return routes.get(value);\\nfunction routeCount() return routes.keys().length;';
  var prepared=CodenameScriptParser.prepare(source,new Map());
  if(prepared.program==null || prepared.diagnostics.length!=0)
    throw prepared.diagnostics.length==0 ? "no program" : prepared.diagnostics[0].message;
  var interp=new Interp();
  interp.variables.set("CodenameMapCompat",CodenameMapCompat);
  interp.variables.set("TitleState",TitleState);
  interp.variables.set("MainMenuState",MainMenuState);
  interp.execute(prepared.program);
  var route:Dynamic=interp.variables.get("route");
  var routeCount:Dynamic=interp.variables.get("routeCount");
  if(route==null || routeCount==null || routeCount()!=2
    || route(TitleState)!="ImportedMain"
    || route(MainMenuState)!="ImportedMain") throw "class-key map values";
  if(prepared.source.indexOf("static")>=0) throw "top-level static was not normalized";

  var accessSource='public var dadbattle_chorus:Bool = false;\\n'
    +'private static function chorusEnabled() return dadbattle_chorus;';
  var accessPrepared=CodenameScriptParser.prepare(accessSource,new Map());
  if(accessPrepared.program==null || accessPrepared.diagnostics.length!=0)
    throw accessPrepared.diagnostics.length==0 ? "no access-modifier program" : accessPrepared.diagnostics[0].message;
  if(accessPrepared.source.indexOf("public")>=0 || accessPrepared.source.indexOf("private")>=0
    || accessPrepared.source.indexOf("static")>=0)
    throw "top-level access modifiers were not normalized";
  var accessInterp=new Interp();
  accessInterp.execute(accessPrepared.program);
  var chorusEnabled:Dynamic=accessInterp.variables.get("chorusEnabled");
  if(chorusEnabled==null || chorusEnabled()!=false) throw "access-modifier declarations did not execute";

  var forwardSource='function readCurrentState() { return currentState; } '
    +'function advanceCurrentState() { currentState++; } '
    +'var currentState:Int = 7;';
  var forwardPrepared=CodenameScriptParser.prepare(forwardSource,new Map());
  if(forwardPrepared.program==null || forwardPrepared.diagnostics.length!=0)
    throw forwardPrepared.diagnostics.length==0 ? "no forward-field program" : forwardPrepared.diagnostics[0].message;
  var forwardInterp=new Interp();
  forwardInterp.execute(forwardPrepared.program);
  var readCurrentState:Dynamic=forwardInterp.variables.get("readCurrentState");
  var advanceCurrentState:Dynamic=forwardInterp.variables.get("advanceCurrentState");
  if(readCurrentState==null || advanceCurrentState==null || readCurrentState()!=7)
    throw "function declared before top-level field could not read it";
  advanceCurrentState();
  if(readCurrentState()!=8) throw "forward top-level field was not mutable from closure";

  var defaultSource='function sample() return [camFollowPos - 625, count + 1, enabled]; '
    +'var camFollowPos:Float; var count:Int; var enabled:Bool;';
  var defaultPrepared=CodenameScriptParser.prepare(defaultSource,new Map());
  if(defaultPrepared.program==null || defaultPrepared.diagnostics.length!=0)
    throw defaultPrepared.diagnostics.length==0 ? "no primitive-default program" : defaultPrepared.diagnostics[0].message;
  var defaultInterp=new Interp();
  defaultInterp.execute(defaultPrepared.program);
  var sample:Dynamic=defaultInterp.variables.get('sample');
  var defaults:Array<Dynamic>=sample();
  if(defaults[0]!=-625 || defaults[1]!=1 || defaults[2]!=false)
    throw 'typed top-level fields did not receive Haxe primitive defaults: '+defaults;

  var optionalSource='import funkin.game.Character; '
    +'var charactersMap:Map<String, Character> = [boyfriend.curCharacter => boyfriend, dad.curCharacter => dad]; '
    +'function precacheCharacter(character:Character, newName:String, index:Int, ?offset) { '
    +'offset ??= {x:0, y:0}; var replacement = new Character(character.x, character.y, newName, character.isPlayer); '
    +'replacement.cameraOffset.x += stage?.characterPoses["dad"]?.camxoffset; return replacement; }';
  var optionalImports:Map<String,Dynamic>=new Map();
  optionalImports.set("funkin.game.Character", {});
  var optionalPrepared=CodenameScriptParser.prepare(optionalSource,optionalImports,"fixture",true);
  if(optionalPrepared.program==null || optionalPrepared.diagnostics.length!=0)
    throw optionalPrepared.diagnostics.length==0 ? "no optional-argument program" : optionalPrepared.diagnostics[0].message;
  var optionalFlag=Std.string(optionalPrepared.program).indexOf("opt: true")>=0;
  if(!optionalFlag || optionalPrepared.source.indexOf("?offset")<0
    || optionalPrepared.source.indexOf("offset == null ?")<0
    || optionalPrepared.source.indexOf("offset ??=")>=0)
    throw "optional parameter and fallback assignment were not preserved";
  if(optionalPrepared.normalizationTrace.length<4
    || optionalPrepared.normalizationTrace[0].indexOf("activeCoalesceAssign=1")<0
    || optionalPrepared.normalizationTrace[0].indexOf("rawCodes=")<0
    || optionalPrepared.normalizationTrace[0].indexOf("maskCodes=")<0
    || optionalPrepared.normalizationTrace[0].indexOf("63,63,61")<0
    || optionalPrepared.normalizationTrace[0].indexOf("tokenLength=3")<0
    || optionalPrepared.normalizationTrace[0].indexOf("tokenCodes=63,63,61")<0
    || optionalPrepared.normalizationTrace[0].indexOf("sliceEqual=true")<0
    || optionalPrepared.normalizationTrace[3].indexOf("activeCoalesceAssign=0")<0)
    throw "normalization stage trace did not confirm ??= lowering";

  var defaultSource='var defaultObserved=-1; '
    +'function changeItem(h:Int = 0) { defaultObserved = h; } '
    +'function updateWithDefault(base:Int = 4, value:Int = base + 3) { defaultObserved = value; } '
    +'changeItem(); if (defaultObserved != 0) throw "zero-argument default"; '
    +'changeItem(3); if (defaultObserved != 3) throw "explicit argument"; '
    +'updateWithDefault(); if (defaultObserved != 7) throw "dependent defaults";';
  var defaultPrepared=CodenameScriptParser.prepare(defaultSource,new Map());
  if(defaultPrepared.program==null || defaultPrepared.diagnostics.length!=0)
    throw defaultPrepared.diagnostics.length==0 ? "no default-argument program" : defaultPrepared.diagnostics[0].message;
  if(defaultPrepared.source.indexOf("function changeItem(?h:Int)")<0
    || defaultPrepared.source.indexOf("if (h == null) h = (0);")<0)
    throw "Haxe default argument was not lowered to optional parameter semantics";
  var defaultInterp=new Interp();
  defaultInterp.execute(defaultPrepared.program);

  var nullSafetySource='var maybe:Dynamic=null; '
    +'var safeRead=maybe?.child.value; '
    +'var safeWrite=maybe?.child.value=1; '
    +'var called=0; maybe?.touch(called++); '
    +'var target={child:{value:2}}; '
    +'var chained=target?.child.value; target?.child.value += 3; '
    +'var stage={characterPoses:[{camxoffset:4}]}; '
    +'var nested=stage?.characterPoses[0]?.camxoffset; '
    +'var slots=[{value:4}]; slots[0]?.value=9; '
    +'var coalesced:Dynamic=null; coalesced ??= {value:11}; '
    +'var record={value:null}; record.value ??= 12; '
    +'var indexed=[null]; indexed[0] ??= {value:13}; '
    +'var defaulted=maybe?.child.value ?? 17; var unchanged=stage?.characterPoses[0]?.camxoffset ?? 19; '
    +'function readNullSafety() return [safeRead,safeWrite,called,chained,target.child.value,nested,slots[0].value,coalesced.value,record.value,indexed[0].value,defaulted,unchanged];';
  var nullSafetyPrepared=CodenameScriptParser.prepare(nullSafetySource,new Map());
  if(nullSafetyPrepared.program==null || nullSafetyPrepared.diagnostics.length!=0)
    throw nullSafetyPrepared.diagnostics.length==0 ? "no null-safety program" : nullSafetyPrepared.diagnostics[0].message;
  var nullSafetyInterp=new Interp();
  nullSafetyInterp.execute(nullSafetyPrepared.program);
  var readNullSafety:Dynamic=nullSafetyInterp.variables.get('readNullSafety');
  var values:Array<Dynamic>=readNullSafety();
  if(values[0]!=null || values[1]!=null || values[2]!=0)
    throw "null-safe read or call did not short-circuit";
  if(values[3]!=2 || values[4]!=5 || values[5]!=4 || values[6]!=9)
    throw "null-safe chained read or assignment";
  if(values[7]!=11 || values[8]!=12 || values[9]!=13 || values[10]!=17 || values[11]!=4)
    throw "null-coalescing assignment";
 }
}''')
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                                "--run", "Main"], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    @unittest.skipUnless(DONOR_PACK.is_file(), "mounted Codename event pack unavailable")
    def test_mounted_change_character_pack_payload_parses_with_runtime_imports(self):
        """Parse the exact packed source payload; do not normalize donor bytes."""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''import sys.io.File;
class Main {
 static function main():Void {
  var decoded = CodenameEventPack.decode(File.getContent(Sys.args()[0]), "Change Character");
  if (decoded.pack == null) throw "donor pack failed to decode: " + decoded.error;
  var imports:Map<String, Dynamic> = new Map();
  imports.set("funkin.game.Character", {});
  imports.set("CodenameMapCompat", {});
  var parsed = CodenameScriptParser.prepare(decoded.pack.script, imports, "mounted-change-character", true);
  if (parsed.program == null || parsed.diagnostics.length != 0) {
   var diagnostics = [for (item in parsed.diagnostics) item.code + ":" + item.message];
   throw "mounted event payload did not parse: " + diagnostics.join(";");
  }
  if (parsed.source.indexOf("?offset") < 0 || parsed.source.indexOf("offset == null ?") < 0
    || parsed.source.indexOf("offset ??=") >= 0)
   throw "optional argument/null-coalescing normalization missing";
  if (parsed.normalizationTrace.length < 4
    || parsed.normalizationTrace[0].indexOf("activeCoalesceAssign=1") < 0
    || parsed.normalizationTrace[0].indexOf("rawCodes=") < 0
    || parsed.normalizationTrace[0].indexOf("maskCodes=") < 0
    || parsed.normalizationTrace[3].indexOf("activeCoalesceAssign=0") < 0)
   throw "mounted source retained active ??= after its normalization stage";
 }
}''')
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                                "--run", "Main", str(DONOR_PACK)], cwd=ROOT,
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    @unittest.skipUnless(DONOR_STAGE.is_file(), "mounted Codename stage unavailable")
    def test_mounted_top_level_public_stage_fields_parse(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''import sys.io.File;
class Main {
 static function main():Void {
  var imports:Map<String,Dynamic> = new Map();
  imports.set("openfl.display.BlendMode", {});
  var prepared = CodenameScriptParser.prepare(File.getContent(Sys.args()[0]), imports,
    "mounted-stageD");
  if (prepared.program == null || prepared.diagnostics.length != 0)
   throw prepared.diagnostics.length == 0 ? "stageD program absent" : prepared.diagnostics[0].message;
  if (prepared.source.indexOf("public var dadbattle_chorus") >= 0
    || prepared.source.indexOf("public var darkLights") >= 0)
   throw "top-level public fields survived lowering";
 }
}''')
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                                "--run", "Main", str(DONOR_STAGE)], cwd=ROOT,
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    @unittest.skipUnless(DONOR_LYRICS.is_file(), "mounted Codename lyrics script unavailable")
    def test_mounted_lyrics_path_uses_haxe_single_quote_interpolation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''import sys.io.File;
import hscript.Interp;
class Main {
 static function main():Void {
  var imports:Map<String,Dynamic> = new Map();
  imports.set("haxe.Json", {});
  imports.set("flixel.text.FlxTextAlign", {});
  imports.set("flixel.text.FlxTextBorderStyle", {});
  var source = File.getContent(Sys.args()[0]);
  var prepared = CodenameScriptParser.prepare(source, imports, "mounted-lyrics");
  if (prepared.program == null || prepared.diagnostics.length != 0)
   throw prepared.diagnostics.length == 0 ? "lyrics program absent" : prepared.diagnostics[0].message;
  var interp = new Interp();
  interp.variables.set("PlayState", {SONG:{meta:{name:"tutorial"}}});
  interp.variables.set("Paths", {getPath:function(value:String):String {
   if (value != "songs/tutorial/lyrics.json") throw "Haxe interpolation remained literal: " + value;
   return value;
  }});
  interp.variables.set("Assets", {getText:function(value:String):String {
   if (value != "songs/tutorial/lyrics.json") throw "wrong owner path: " + value;
   return "{\\\"stuff\\\":[]}";
  }});
  interp.variables.set("Json", {parse:function(value:String):Dynamic return haxe.Json.parse(value)});
  interp.variables.set("json", null);
  interp.execute(prepared.program);
 }
}''')
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                                "--run", "Main", str(DONOR_LYRICS)], cwd=ROOT,
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
