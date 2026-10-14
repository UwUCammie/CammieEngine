from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class LuaToNumberTest(unittest.TestCase):
    def test_tonumber_is_nil_for_non_numbers_and_reads_hex_and_bases(self):
        fixture = r'''
class LuaToNumberTest {
 static function same(label:String, got:Dynamic, want:String) {
  var text = got == null ? 'nil' : Std.string(got);
  if (text != want) throw label + ': got ' + text + ' want ' + want;
 }
 static function main() {
  same('nil', EngineCompat.luaNumber(null), 'nil');
  same('empty', EngineCompat.luaNumber(''), 'nil');
  same('blank', EngineCompat.luaNumber('   '), 'nil');
  same('word', EngineCompat.luaNumber('abc'), 'nil');
  same('trailing junk', EngineCompat.luaNumber('12abc'), 'nil');
  same('two numbers', EngineCompat.luaNumber('1 2'), 'nil');
  same('lone sign', EngineCompat.luaNumber('-'), 'nil');
  same('lone dot', EngineCompat.luaNumber('.'), 'nil');
  same('lone exponent', EngineCompat.luaNumber('1e'), 'nil');
  same('boolean', EngineCompat.luaNumber(true), 'nil');
  same('table', EngineCompat.luaNumber([1]), 'nil');
  same('object', EngineCompat.luaNumber({a: 1}), 'nil');
  same('padded', EngineCompat.luaNumber(' 5 '), '5');
  same('integer text', EngineCompat.luaNumber('12'), '12');
  same('decimal', EngineCompat.luaNumber('1.5'), '1.5');
  same('leading dot', EngineCompat.luaNumber('.5'), '0.5');
  same('trailing dot', EngineCompat.luaNumber('5.'), '5');
  same('negative', EngineCompat.luaNumber('-2.25'), '-2.25');
  same('plus sign', EngineCompat.luaNumber('+3'), '3');
  same('exponent', EngineCompat.luaNumber('1e2'), '100');
  same('negative exponent', EngineCompat.luaNumber('25E-1'), '2.5');
  same('hex', EngineCompat.luaNumber('0x1F'), '31');
  same('hex upper prefix', EngineCompat.luaNumber('0X10'), '16');
  same('negative hex', EngineCompat.luaNumber('-0xa'), '-10');
  same('bad hex', EngineCompat.luaNumber('0xZZ'), 'nil');
  same('number passes through', EngineCompat.luaNumber(7), '7');
  if (!Std.isOfType(EngineCompat.luaNumber(7), Int)) throw 'a whole number stays whole';
  same('float passes through', EngineCompat.luaNumber(7.5), '7.5');
  same('base 16', EngineCompat.luaNumber('ff', 16), '255');
  same('base 16 with prefix', EngineCompat.luaNumber('0xFF', 16), '255');
  same('base 2', EngineCompat.luaNumber('1010', 2), '10');
  same('base 36', EngineCompat.luaNumber('z', 36), '35');
  same('base 8 rejects 8', EngineCompat.luaNumber('8', 8), 'nil');
  same('base on a number', EngineCompat.luaNumber(11, 2), '3');
  same('base 10 is the default path', EngineCompat.luaNumber('1.5', 10), '1.5');
  same('negative in a base', EngineCompat.luaNumber('-11', 2), '-3');
  same('base 16 past 32 bits', EngineCompat.luaNumber('ffffffff', 16), '4294967295');
  same('hex past 32 bits', EngineCompat.luaNumber('0xFFFFFFFF'), '4294967295');
  same('hex with no digits', EngineCompat.luaNumber('0x'), 'nil');
  var badBase = false;
  try EngineCompat.luaNumber('1', 99) catch (_:Dynamic) badBase = true;
  if (!badBase) throw 'a base outside 2..36 is an error';

  // The everyday idiom: a missing or junk value falls back to the default.
  var converted = LuaCompat.translate(
   "function onCreate()\n"
   + " local missing\n"
   + " fromNil = tonumber(missing) or 1\n"
   + " fromText = tonumber('x') or 3\n"
   + " fromHex = tonumber('0x10') or 0\n"
   + " fromNumber = tonumber('4') or 9\n"
   + " if tonumber('nope') then taken = true else taken = false end\n"
   + "end\n", 'tonumber.lua');
  if (!converted.supported) throw converted.diagnostics.join(' | ');
  var interp = new LuaCompatInterp();
  interp.variables.set('luaNumber', EngineCompat.luaNumber);
  interp.execute(new hscript.Parser().parseString(converted.hscript));
  Reflect.callMethod(null, interp.variables.get('onCreate'), []);
  same('nil falls back', interp.variables.get('fromNil'), '1');
  same('text falls back', interp.variables.get('fromText'), '3');
  same('hex is read', interp.variables.get('fromHex'), '16');
  same('number text is read', interp.variables.get('fromNumber'), '4');
  same('junk is falsy', interp.variables.get('taken'), 'false');
  Sys.println('ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "LuaToNumberTest.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HAXESCRIPT),
                 "-main", "LuaToNumberTest", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
