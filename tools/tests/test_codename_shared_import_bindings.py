"""Exercise source-facing Codename bindings without starting the game."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class CodenameSharedImportBindingsTest(unittest.TestCase):
    def test_discord_util_offline_user_and_flixel_text_format_imports(self):
        source = (ROOT / "source/CodenameImportBindings.hx").read_text()
        self.assertIn("bindings.set('funkin.backend.utils.DiscordUtil', discordUtilConstants());", source)
        self.assertIn("bindings.set('flixel.text.FlxTextFormat', FlxTextFormat);", source)
        self.assertIn("bindings.set('flixel.text.FlxText.FlxTextFormat', FlxTextFormat);", source)
        self.assertIn("import flixel.text.FlxText.FlxTextFormat;", source)
        discord_method = extract_method(source, "public static function discordUtilConstants")

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            text_module = base / "flixel/text/FlxText.hx"
            text_module.parent.mkdir(parents=True)
            text_module.write_text("""package flixel.text;
class FlxText {
 public static function formatType():Dynamic return FlxTextFormat;
}
class FlxTextFormat {
 public var color:Int;
 public function new(color:Int) this.color=color;
}
""")
            (base / "Main.hx").write_text(f'''import flixel.text.FlxText;
import hscript.Interp;
class CodenameImportBindings {{
 {discord_method}
}}
class Main {{
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {{
  var allowed:Map<String,Dynamic>=new Map();
  var discord=CodenameImportBindings.discordUtilConstants();
  var formatType=FlxText.formatType();
  allowed.set("funkin.backend.utils.DiscordUtil", discord);
  allowed.set("flixel.text.FlxTextFormat", formatType);
  var parsed=CodenameScriptParser.prepare(
   'import funkin.backend.utils.DiscordUtil; import flixel.text.FlxTextFormat; '
   + 'function getUsername() {{ var username="BOYFRIEND"; '
   + 'if (DiscordUtil.user.globalName != null) username=DiscordUtil.user.globalName; return username; }} '
   + 'function getFormatColor() return new FlxTextFormat(77).color;', allowed);
  check(parsed.program!=null && parsed.diagnostics.length==0,
   parsed.diagnostics.length==0 ? "imports produced no program" : parsed.diagnostics[0].message);
  var interp=new Interp();
  interp.variables.set("DiscordUtil", discord);
  interp.variables.set("FlxTextFormat", formatType);
  interp.execute(parsed.program);
  var getUsername:Dynamic=interp.variables.get("getUsername");
  var getFormatColor:Dynamic=interp.variables.get("getFormatColor");
  check(getUsername()!=null && getUsername()=="BOYFRIEND",
   "Discord globalName absence did not preserve the script's authored fallback");
  check(getFormatColor()==77, "flattened FlxTextFormat import lost its constructor");
 }}
}}''')
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(base), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
