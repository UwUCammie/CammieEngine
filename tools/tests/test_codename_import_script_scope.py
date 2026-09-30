"""Imported Codename HScript must retain the caller's classless field scope."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameImportScriptScopeTest(unittest.TestCase):
    def test_inline_import_retains_fields_and_later_callbacks(self):
        source = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        signature = "public function executeImportedScript(program:Expr):Dynamic {"
        start = source.index(signature)
        opening = source.index("{", start)
        depth = 1
        end = opening + 1
        while depth:
            depth += (source[end] == "{") - (source[end] == "}")
            end += 1
        method = source[start:end]
        play = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("interp.executeImportedScript(prepared.program)", play)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text(
                "import hscript.Interp;\nimport hscript.Expr;\n"
                "import hscript.ParserEx;\n"
                "class ScopedInterp extends Interp {\n" + method + "\n}\n"
                "class Main { static function main() {\n"
                " var parser = new ParserEx(); parser.allowTypes = true;\n"
                " var imported = parser.parseString('var data = 7; function importedValue() return data;');\n"
                " var parent = parser.parseString('var rainbow:Bool = false; importScript(); '\n"
                "  + 'function update() return rainbow; function importedCheck() return importedValue();');\n"
                " var interp = new ScopedInterp();\n"
                " interp.variables.set('importScript', function() interp.executeImportedScript(imported));\n"
                " interp.execute(parent);\n"
                " var update:Dynamic = interp.variables.get('update');\n"
                " var check:Dynamic = interp.variables.get('importedCheck');\n"
                " if (update == null || update() != false || check == null || check() != 7)\n"
                "  throw 'nested import lost caller or imported fields';\n"
                "}}\n"
            )
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "-cp", str(base), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
