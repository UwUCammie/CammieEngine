"""Exercise standard Flixel imports used by owner-scoped Codename scripts."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CodenameHl17SharedImportsTest(unittest.TestCase):
    def test_hl17_window_framework_imports_remain_explicitly_unsupported(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text('''import hscript.Interp;
class HLTypeText {}
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var allowed:Map<String, Dynamic> = new Map();
  allowed.set("HLTypeText", HLTypeText);
  var parsed = CodenameScriptParser.prepare(
   'import HLCreditsWindow; import HLOptionsWindow; '
   + 'import HLSelectWindow; import HLTypeText; function create() {}', allowed,
   'data/states/HL17MainMenu.hx');
  check(parsed.program == null, "unavailable HLUI classes must not produce an executable HScript program");
  var names = ['HLCreditsWindow', 'HLOptionsWindow', 'HLSelectWindow'];
  check(parsed.diagnostics.length == names.length,
   "expected one unsupported-import diagnostic for each unavailable class: " + parsed.diagnostics.length);
  for (i in 0...names.length) {
   var diagnostic = parsed.diagnostics[i];
   check(diagnostic.code == 'unsupported-import'
    && diagnostic.message.indexOf('No explicit binding for import ' + names[i] + '.') >= 0,
    "missing explicit unsupported diagnostic for " + names[i] + ": " + diagnostic.message);
  }
  check(parsed.imports.indexOf('HLTypeText') >= 0,
   "supported HL17 typewriter import was not retained");
  var bindingSource = sys.io.File.getContent('source/CodenameImportBindings.hx');
  check(bindingSource.indexOf("bindings.set('HLTypeText', CodenameHLTypeTextCompat);") >= 0,
   "shared owner-scoped HLTypeText import binding is missing");
  var interpSource = sys.io.File.getContent('source/CodenameScriptInterp.hx');
  check(interpSource.indexOf("if (name == 'HLTypeText')") >= 0
   && interpSource.indexOf('CodenameHLTypeTextCompat.fromArgs(args, paths)') >= 0,
   "HLTypeText constructor does not receive selected-owner asset paths");
 }
}
''')
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(base), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_math_and_flxrect_imports_are_parser_checked_and_callable(self):
        source = (ROOT / "source/CodenameImportBindings.hx").read_text()
        self.assertIn("import flixel.math.FlxRect;", source)
        self.assertIn("bindings.set('Math', Math);", source)
        self.assertIn("bindings.set('Reflect', Reflect);", source)
        self.assertIn("bindings.set('flixel.math.FlxRect', FlxRect);", source)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            rect = base / "flixel/math/FlxRect.hx"
            rect.parent.mkdir(parents=True)
            rect.write_text("""package flixel.math;
class FlxRect {
 public var x:Float; public var y:Float; public var width:Float; public var height:Float;
 public function new(x:Float=0, y:Float=0, width:Float=0, height:Float=0) {
  this.x=x; this.y=y; this.width=width; this.height=height;
 }
}
""")
            (base / "Main.hx").write_text('''import flixel.math.FlxRect;
import hscript.Interp;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var allowed:Map<String, Dynamic> = new Map();
  allowed.set("Math", Math);
  allowed.set("Reflect", Reflect);
  allowed.set("flixel.math.FlxRect", FlxRect);
  var parsed = CodenameScriptParser.prepare(
   'import Math; import Reflect; import flixel.math.FlxRect; '
   + 'var bar = new FlxRect(0, 120, 100, 100); '
   + 'var menu = {alpha: 0}; Reflect.setField(menu, "alpha", 0.75); '
   + 'function values() return [Math.abs(-7), Math.round(health / 2 * 100), '
   + 'bar.y, bar.width, bar.height, Reflect.getProperty(menu, "alpha")]; '
   + 'var health = 1.76;', allowed);
  check(parsed.program != null && parsed.diagnostics.length == 0,
   parsed.diagnostics.length == 0 ? "no program" : parsed.diagnostics[0].message);
  var interp = new Interp();
  interp.variables.set("Math", Math);
  interp.variables.set("Reflect", Reflect);
  interp.variables.set("FlxRect", FlxRect);
  interp.execute(parsed.program);
  var values:Dynamic = interp.variables.get("values");
  var actual:Array<Dynamic> = values();
  check(actual[0] == 7 && actual[1] == 88 && actual[2] == 120
   && actual[3] == 100 && actual[4] == 100 && actual[5] == 0.75,
   "Math, Reflect or FlxRect import semantics changed: " + actual);
 }
}
''')
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(base), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pasted_global_imports_are_shared_and_sys_is_narrowly_bound(self):
        names = [
            "Type", "haxe.Timer", "openfl.display.FPS", "openfl.text.TextField",
            "openfl.text.TextFormat", "openfl.display.Sprite",
            "funkin.backend.utils.MemoryUtil", "funkin.backend.system.Main",
            "funkin.backend.system.framerate.Framerate", "Math", "flixel.math.FlxRect",
        ]
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text()
        host = (ROOT / "source/CodenameModBindings.hx").read_text()
        for name in names:
            self.assertIn(f"bindings.set('{name}',", bindings)
        self.assertIn("CodenameImportBindings.addShared(result, interp, paths);", host)
        self.assertIn("bindings.set('Sys', CodenameSysCompat.facade());", bindings,
                      "HL17's Sys.exit needs the host-safe return-to-menu facade")
        self.assertNotIn("bindings.set('Sys', Sys);", bindings,
                         "native Sys must never be exposed to imported scripts")
        sys_compat = (ROOT / "source/CodenameSysCompat.hx").read_text()
        self.assertIn("CodenameModRuntime.exitToNativeMenu();", sys_compat)
        self.assertNotIn("sys.io.Process", sys_compat)
        self.assertIn("CodenameModRuntime.isActiveOwner(ownerRoot)", sys_compat)
        self.assertIn("if (processExit != null) processExit(code); else exitProcess(code);", sys_compat)
        self.assertIn("Sys.exit(code);", sys_compat,
                      "only active imported-state hosts may reach native process exit")

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            quoted = ", ".join(f'"{name}"' for name in names)
            (base / "Main.hx").write_text(f'''class Main {{
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {{
  var names = [{quoted}];
  var allowed:Map<String, Dynamic> = new Map();
  for (name in names) allowed.set(name, {{}});
  var imports = CodenameScriptParser.prepare(
   'import Type; import haxe.Timer; import openfl.display.FPS; '
   + 'import openfl.text.TextField; import openfl.text.TextFormat; '
   + 'import openfl.display.Sprite; import funkin.backend.utils.MemoryUtil; '
   + 'import funkin.backend.system.Main; '
   + 'import funkin.backend.system.framerate.Framerate; '
   + 'import Math; import flixel.math.FlxRect; function create() {{}}', allowed);
  check(imports.program != null && imports.diagnostics.length == 0,
   imports.diagnostics.length == 0 ? "global imports produced no program" : imports.diagnostics[0].message);
  var unsafe = CodenameScriptParser.prepare('import Sys; function terminate() Sys.exit(0);', allowed);
  check(unsafe.program == null && unsafe.diagnostics.length == 1
   && unsafe.diagnostics[0].code == 'unsupported-import'
   && unsafe.diagnostics[0].message.indexOf('Sys') >= 0,
   "Sys import must be explicitly rejected");
 }}
}}''')
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(base), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
