"""Exercise Psych getTextString behavior through the real Lua translator."""
from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


FIXTURE = r'''import hscript.Parser;

class FlxText {
  public var text:String;
  public function new(text:String) this.text = text;
}

class PsychGetTextStringFixture {
  var objects:Map<String, Dynamic> = new Map();
  public function new() {}
  function compatFindObject(name:Dynamic):Dynamic return objects.get(Std.string(name));

__GETTER__

  static function check(value:Bool, message:String):Void if (!value) throw message;

  static function main():Void {
    var fixture = new PsychGetTextStringFixture();
    fixture.objects.set('running', new FlxText('true'));
    fixture.objects.set('other', new FlxText('loading'));
    fixture.objects.set('unicode', new FlxText('字幕 🐈'));
    fixture.objects.set('empty', new FlxText(''));
    fixture.objects.set('sprite', {text:'not a FlxText'});

    check(fixture.compatGetTextString('unicode') == '字幕 🐈',
      'Unicode text was changed');
    check(fixture.compatGetTextString('empty') == '',
      'empty text must stay an empty string');
    check(fixture.compatGetTextString('sprite') == null,
      'non-text object must return nil');
    check(fixture.compatGetTextString('missing') == null,
      'missing optional text tag must return nil');

    var source = 'function shouldRun(tag)\n'
      + '  if getTextString(tag) ~= "true" then\n'
      + '    return true\n'
      + '  else\n'
      + '    return false\n'
      + '  end\n'
      + 'end\n'
      + 'function textFor(tag)\n'
      + '  return getTextString(tag)\n'
      + 'end\n';
    var translated = LuaCompat.translate(source, 'BAMBOO-DREAMS.lua');
    if (!translated.supported) throw translated.diagnostics.join(' | ');

    var interp = new LuaCompatInterp();
    interp.variables.set('getTextString', fixture.compatGetTextString);
    interp.execute(new Parser().parseString(translated.hscript));
    var shouldRun:Dynamic = interp.variables.get('shouldRun');
    var textFor:Dynamic = interp.variables.get('textFor');
    check(Reflect.callMethod(null, shouldRun, ['missing']) == true,
      'nil ~= "true" should enter the optional-tag branch');
    check(Reflect.callMethod(null, shouldRun, ['running']) == false,
      'the exact text "true" should block the branch');
    check(Reflect.callMethod(null, shouldRun, ['other']) == true,
      'other text should pass the not-equal comparison');
    check(Reflect.callMethod(null, textFor, ['unicode']) == '字幕 🐈',
      'translated Lua did not preserve Unicode text');
    check(Reflect.callMethod(null, textFor, ['empty']) == '',
      'translated Lua did not preserve empty text');
    check(Reflect.callMethod(null, textFor, ['sprite']) == null,
      'translated Lua returned text from a non-text object');
    Sys.println('ok');
  }
}
'''


class PsychGetTextStringTest(unittest.TestCase):
    def test_native_getter_and_lua_optional_tag_comparison(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        getter = extract_method(play_state, "function compatGetTextString(")
        fixture = FIXTURE.replace("__GETTER__", getter)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "PsychGetTextStringFixture.hx").write_text(
                fixture, encoding="utf-8", newline="\n"
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(HAXESCRIPT), "-main", "PsychGetTextStringFixture", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_shared_binding_and_importer_allowlist(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("interp.variables.set('getTextString', compatGetTextString);", play_state)

        engine = (ROOT / "source/EngineCompat.hx").read_text(encoding="utf-8")
        known_functions = extract_method(engine, "public static function knownScriptFunction(").lower()
        self.assertIn("'gettextstring'", known_functions)


if __name__ == "__main__":
    unittest.main()
