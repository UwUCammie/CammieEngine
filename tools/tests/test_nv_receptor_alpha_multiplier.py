"""Extract and exercise the source-only StrumNote alpha multiplier contract."""

from __future__ import annotations

import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unterminated Haxe method: {marker}")


class NvReceptorAlphaMultiplierTest(unittest.TestCase):
    def test_source_alpha_target_and_multiplier_do_not_compound(self):
        source = (ROOT / "source/Strumline.hx").read_text(encoding="utf-8")
        setters = "\n".join(
            extract_method(source, marker)
            for marker in (
                "function set_nightmareVisionSource(",
                "function set_alphaMult(",
                "override function set_alpha(",
            )
        )
        fixture = r'''
class FlxSpriteMock {
 public var alpha(default, set):Float = 1;
 public function new() {}
 public function set_alpha(value:Float):Float {
  alpha = Math.max(0, Math.min(1, value));
  return alpha;
 }
}
class SourceStrumNote extends FlxSpriteMock {
 public var nightmareVisionSource(default, set):Bool = false;
 public var targetAlpha:Float = 1;
 public var alphaMult(default, set):Float = 1;
 __SETTERS__
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function near(actual:Float, expected:Float, message:String):Void
  check(Math.abs(actual - expected) < 0.00001, message + ': ' + actual);
 static function main():Void {
  var native = new SourceStrumNote();
  native.alpha = 0.6;
  near(native.alpha, 0.6, 'native alpha write');
  native.alphaMult = 0.25;
  near(native.alpha, 0.6, 'multiplier must not change Psych/native alpha');
  native.alpha = 0.3;
  near(native.alpha, 0.3, 'native alpha remains direct');

  var source = new SourceStrumNote();
  source.alpha = 0.8;
  source.alphaMult = 0.5;
  near(source.alpha, 0.8, 'multiplier is inert before source ownership');
  source.nightmareVisionSource = true;
  near(source.targetAlpha, 0.8, 'source activation retains the existing alpha target');
  near(source.alpha, 0.4, 'source activation applies the multiplier');

  source.alpha = 0.6;
  near(source.targetAlpha, 0.6, 'ordinary alpha writes update the independent target');
  near(source.alpha, 0.3, 'alpha write combines with multiplier');
  source.alphaMult = 0.2;
  near(source.alpha, 0.12, 'multiplier update reapplies from target');
  source.alphaMult = 0.4;
  near(source.alpha, 0.24, 'repeated multiplier writes never compound');
  source.alpha = 0;
  source.alphaMult = 0.8;
  near(source.alpha, 0, 'fade target stays zero as field alpha changes');
  source.alpha = 0.25;
  near(source.alpha, 0.2, 'new tween alpha target uses current multiplier');
 }
}
'''.replace("__SETTERS__", setters)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
