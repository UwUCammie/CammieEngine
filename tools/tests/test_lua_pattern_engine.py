from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"


def run_fixture(test, name, fixture):
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        (Path(folder) / (name + ".hx")).write_text(fixture, newline='\n')
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HAXESCRIPT),
             "-main", name, "--interp"],
            cwd=ROOT, capture_output=True, text=True, timeout=300)
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    test.assertIn("ok", result.stdout)


class LuaPatternEngineTest(unittest.TestCase):
    def test_find_match_gmatch_and_gsub_follow_lua_pattern_rules(self):
        fixture = r'''
class LuaPatternEngineTest {
 static function show(value:Dynamic):String return value == null ? 'nil' : Std.string(value);
 static function same(label:String, got:Dynamic, want:String) {
  if (show(got) != want) throw label + ': got ' + show(got) + ' want ' + want;
 }
 static function fails(label:String, run:Void->Void) {
  var threw = false;
  try run() catch (_:Dynamic) threw = true;
  if (!threw) throw label + ' should be rejected';
 }
 static function main() {
  // find: positions are one based and inclusive, captures follow them
  same('digits', LuaPattern.find('abc123', '%d+'), '[4,6]');
  same('plain text', LuaPattern.find('hello world', 'wor'), '[7,9]');
  same('find captures', LuaPattern.find('key = value', '(%w+)%s*=%s*(%w+)'), '[1,11,key,value]');
  same('no match', LuaPattern.find('abc', '%d'), 'nil');
  same('init', LuaPattern.find('a.b.c', '.', 3, true), '[4,4]');
  same('negative init', LuaPattern.find('abcabc', 'b', -3), '[5,5]');
  same('plain flag keeps magic literal', LuaPattern.find('a+b', '+', 1, true), '[2,2]');
  same('empty pattern', LuaPattern.find('abc', ''), '[1,0]');
  same('anchored start', LuaPattern.find('aab', '^a+'), '[1,2]');
  same('anchored miss', LuaPattern.find('baa', '^a'), 'nil');
  same('end anchor', LuaPattern.find('hello.lua', '%.lua$$'), '[6,9]');
  same('dollar in the middle is literal', LuaPattern.find('a$$b', 'a$$b'), '[1,3]');

  // classes, complements and sets
  same('alpha', LuaPattern.match('  word9', '%a+'), '[word]');
  same('alnum', LuaPattern.match('  word9!', '%w+'), '[word9]');
  same('space', LuaPattern.match('a \t\nb', '%s+'), '[ \t\n]');
  same('punct', LuaPattern.match('ab,;cd', '%p+'), '[,;]');
  same('lower upper', LuaPattern.match('abCDef', '%l+%u+'), '[abCD]');
  same('hex', LuaPattern.match('0xFFzz', '0x%x+'), '[0xFF]');
  same('control', LuaPattern.find('a\tb', '%c'), '[2,2]');
  same('complement', LuaPattern.match('abc123', '%D+'), '[abc]');
  same('escaped magic', LuaPattern.match('1+1=2', '%d%+%d'), '[1+1]');
  same('set range', LuaPattern.match('x=42;', '[0-9]+'), '[42]');
  same('negated set', LuaPattern.match('one,two', '[^,]+'), '[one]');
  same('set with class', LuaPattern.match('a_b-c d', '[%w_]+'), '[a_b]');
  same('set with closing bracket first', LuaPattern.match('a]b', '[]]'), '[]]');
  same('dot', LuaPattern.match('a\nb', 'a.b'), '[a\nb]');

  // quantifiers
  same('greedy star', LuaPattern.match('<a><b>', '<.*>'), '[<a><b>]');
  same('lazy dash', LuaPattern.match('<a><b>', '<.->'), '[<a>]');
  same('optional', LuaPattern.match('color colour', 'colou?r'), '[color]');
  same('optional present', LuaPattern.match('colour', 'colou?r'), '[colour]');
  same('plus needs one', LuaPattern.match('abc', '%d+'), 'nil');
  same('star may be empty', LuaPattern.find('abc', '%d*'), '[1,0]');

  // captures
  same('two captures', LuaPattern.match('hello world', '(%w+) (%w+)'), '[hello,world]');
  same('nested captures', LuaPattern.match('abc', '((a)(b))c'), '[ab,a,b]');
  same('position capture', LuaPattern.match('hello', '()ll()'), '[3,5]');
  if (!Std.isOfType(LuaPattern.match('hello', '()ll()')[0], Int)) throw 'position captures are numbers';
  same('empty capture', LuaPattern.match('abc', 'a()'), '[2]');
  same('back reference', LuaPattern.match('say "hi" now', '(["\'])(.-)%1'), '[",hi]');
  same('back reference miss', LuaPattern.match('"hi\'', '(["\'])(.-)%1'), 'nil');
  same('match init', LuaPattern.match('a1b2', '%d', 3), '[2]');
  same('trim idiom', LuaPattern.match('   padded text  ', '^%s*(.-)%s*$$'), '[padded text]');

  // balanced and frontier
  same('balanced', LuaPattern.match('f(a(b)c) + g(d)', '%b()'), '[(a(b)c)]');
  same('balanced unclosed', LuaPattern.match('f(a(b', '%b()'), 'nil');
  same('balanced custom pair', LuaPattern.match('x = [a[b]] y', '%b[]'), '[[a[b]]]');
  same('frontier', LuaPattern.find('THE (quick) fox', '%f[%a]%a+%f[%A]'), '[1,3]');
  same('frontier word start', LuaPattern.gsub('hello world', '%f[%w]%w+', 'X'), '[X X,2]');

  // the comma and whitespace separated value lists event scripts split
  same('value list', LuaPattern.match('1.5, 20,ease', '([^,]+),%s*([^,]+),?%s*([^,]*)'), '[1.5,20,ease]');
  same('value list without third', LuaPattern.match('4,8', '([^,]+),%s*([^,]+),?%s*([^,]*)'), '[4,8,]');
  same('sign and name pairs', LuaPattern.gmatch('+x-y', '(%p)(%w+)'), '[[+,x],[-,y]]');
  same('split on commas and spaces', LuaPattern.gmatch('a, b ,c', '([^,%s]+)'), '[[a],[b],[c]]');
  same('gmatch skips empty fields', LuaPattern.gmatch('a,b,,c', '([^,]+)'), '[[a],[b],[c]]');
  same('gmatch whole match', LuaPattern.gmatch('one two', '%a+'), '[[one],[two]]');
  same('gmatch key value', LuaPattern.gmatch('a=1, b=2', '(%w+)=(%w+)'), '[[a,1],[b,2]]');
  same('gmatch empty matches', LuaPattern.gmatch('ab', 'x*').length, '3');

  // gsub
  same('swap captures', LuaPattern.gsub('john smith', '(%w+) (%w+)', '%2 %1'), '[smith john,1]');
  same('whole match', LuaPattern.gsub('abc', '%w', '%0%0'), '[aabbcc,3]');
  same('first capture without captures', LuaPattern.gsub('abc', '%w', '<%1>'), '[<a><b><c>,3]');
  same('limit', LuaPattern.gsub('a.b.c', '%.', '', 1), '[ab.c,1]');
  same('zero limit', LuaPattern.gsub('aaa', 'a', 'b', 0), '[aaa,0]');
  same('whitespace runs', LuaPattern.gsub('a  b   c', '%s+', ' '), '[a b c,2]');
  same('non alphanumerics', LuaPattern.gsub('A-Song 1!', '[^%a%d]', '_'), '[A_Song_1_,3]');
  same('anchored once', LuaPattern.gsub('aaa', '^a', 'b'), '[baa,1]');
  same('empty matches', LuaPattern.gsub('abc', '', '-'), '[-a-b-c-,4]');
  same('escaped percent', LuaPattern.gsub('50', '%d+', '%0%%'), '[50%,1]');
  same('lone trailing percent is not an error', LuaPattern.gsub('50', '%d+', '%0%'), '[50,1]');
  same('function replacement',
   LuaPattern.gsub('a1b22', '%d+', function(digits:String):Dynamic return '<' + digits.length + '>'), '[a<1>b<2>,2]');
  same('function gets every capture',
   LuaPattern.gsub('x=1', '(%w+)=(%w+)', function(key:String, value:String):Dynamic return value + '=' + key), '[1=x,1]');
  same('nil keeps the match',
   LuaPattern.gsub('abc', '%w', function(letter:String):Dynamic return letter == 'b' ? null : letter.toUpperCase()), '[AbC,3]');
  same('false keeps the match', LuaPattern.gsub('abc', 'b', function(letter:String):Dynamic return false), '[abc,1]');
  same('table replacement', LuaPattern.gsub('$$name is $$age', '%$$(%w+)', {name: 'Sam', age: 7}), '[Sam is 7,2]');
  var marker:Dynamic = {};
  same('table lookup hook', LuaPattern.gsub('a b', '%w', marker, null,
   function(table:Dynamic, key:Dynamic):Dynamic return table == marker && key == 'a' ? 'found' : null), '[found b,2]');

  // broken patterns are errors, not silent misses
  fails('unfinished set', function() LuaPattern.find('abc', '[a'));
  fails('trailing escape', function() LuaPattern.find('abc', 'a%'));
  fails('unfinished capture', function() LuaPattern.match('abc', '(a'));
  fails('stray close', function() LuaPattern.match('abc', 'a)'));
  fails('bad back reference', function() LuaPattern.match('abc', '%1'));
  fails('frontier without set', function() LuaPattern.match('abc', '%fa'));
  fails('replacement capture out of range', function() LuaPattern.gsub('abc', '(a)', '%2'));
  if (!LuaPattern.isPlain('abc def') || LuaPattern.isPlain('a.b')) throw 'plain text detection';
  Sys.println('ok');
 }
}
'''
        run_fixture(self, "LuaPatternEngineTest", fixture)

    def test_engine_string_helpers_use_the_pattern_engine(self):
        fixture = r'''
class LuaPatternHelperTest {
 static function same(label:String, got:Dynamic, want:String) {
  var text = got == null ? 'nil' : Std.string(got);
  if (text != want) throw label + ': got ' + text + ' want ' + want;
 }
 static function main() {
  same('find pattern', EngineCompat.luaStringFind('abc123', '%d+'), '4');
  same('find literal', EngineCompat.luaStringFind('a song 1', 'song'), '3');
  same('find miss', EngineCompat.luaStringFind('a song 1', 'absent'), 'nil');
  same('find plain', EngineCompat.luaStringFind('a.b', '.', 1, true), '2');
  same('find nil subject', EngineCompat.luaStringFind(null, 'a'), 'nil');
  same('match capture', EngineCompat.luaStringMatch('speed=2.5', '=(.+)'), '2.5');
  same('match whole', EngineCompat.luaStringMatch('abc123', '%a+'), 'abc');
  same('match miss', EngineCompat.luaStringMatch('abc', '%d'), 'nil');
  same('gsub captures', EngineCompat.luaStringGsub('john smith', '(%w+) (%w+)', '%2 %1'), 'smith john');
  same('gsub digits', EngineCompat.luaStringGsub('a1b2', '%d', ''), 'ab');
  same('gsub limit', EngineCompat.luaStringGsub('a.b.c', '%.', '', 1), 'ab.c');
  same('gsub function', EngineCompat.luaStringGsub('abc', '%w', function(c:String):Dynamic return c.toUpperCase()), 'ABC');
  same('gmatch first captures', EngineCompat.luaStringGmatch('a,b,,c', '([^,]+)'), '[a,b,c]');
  same('gmatch words', EngineCompat.luaStringGmatch('one two', '%a+'), '[one,two]');
  same('gmatch several captures', EngineCompat.luaStringGmatch('a=1,b=2', '(%w+)=(%w+)'), '[[a,1],[b,2]]');
  same('gmatch all', EngineCompat.luaStringGmatchAll('+x-y', '(%p)(%w+)'), '[[+,x],[-,y]]');
  same('rep', EngineCompat.luaStringRep('ab', 3), 'ababab');
  same('rep zero', EngineCompat.luaStringRep('ab', 0), '');
  same('reverse', EngineCompat.luaStringReverse('abc'), 'cba');
  same('byte', EngineCompat.luaStringByte('ABC', 2), '66');
  same('byte default', EngineCompat.luaStringByte('ABC'), '65');
  same('byte past end', EngineCompat.luaStringByte('ABC', 9), 'nil');
  same('char', EngineCompat.luaStringChar(72, 105), 'Hi');
  same('sub', EngineCompat.luaStringSub('hello', 2, 4), 'ell');
  same('sub negative', EngineCompat.luaStringSub('hello', -3), 'llo');
  same('sub from zero', EngineCompat.luaStringSub('hello', 0, 2), 'he');

  // string.format flags and conversions
  same('left justify', EngineCompat.luaStringFormat('[%-5d]', 42), '[42   ]');
  same('right justify', EngineCompat.luaStringFormat('[%5d]', 42), '[   42]');
  same('zero pad', EngineCompat.luaStringFormat('%05d', -42), '-0042');
  same('plus sign', EngineCompat.luaStringFormat('%+d %+d', 5, -5), '+5 -5');
  same('character', EngineCompat.luaStringFormat('%c%c', 72, 105), 'Hi');
  same('float default precision', EngineCompat.luaStringFormat('%f', 1.5), '1.500000');
  same('float precision', EngineCompat.luaStringFormat('%.2f', 3.14159), '3.14');
  same('float rounds to integer', EngineCompat.luaStringFormat('%.0f', 2.6), '3');
  same('float width', EngineCompat.luaStringFormat('%8.3f|', 3.14159), '   3.142|');
  same('negative float', EngineCompat.luaStringFormat('%.1f', -0.26), '-0.3');
  same('hex', EngineCompat.luaStringFormat('%x %X %#x', 255, 255, 255), 'ff FF 0xff');
  same('octal', EngineCompat.luaStringFormat('%o', 8), '10');
  same('string width', EngineCompat.luaStringFormat('[%-6s][%6s]', 'ab', 'cd'), '[ab    ][    cd]');
  same('string precision', EngineCompat.luaStringFormat('%.2s', 'abcdef'), 'ab');
  same('exponent', EngineCompat.luaStringFormat('%.2e', 12345.678), '1.23e+04');
  same('general', EngineCompat.luaStringFormat('%g %g %g', 0.5, 100, 1e20), '0.5 100 1e+20');
  same('quoted', EngineCompat.luaStringFormat('%q', 'a"b'), '"a\\"b"');
  // 1.25 is exactly half way, so like C it rounds to the even digit.
  same('existing mix', EngineCompat.luaStringFormat('%02X:%02d:%.1f:%s:%%', 15, 3, 1.25, 'ok'), '0F:03:1.2:ok:%');
  same('big integer', EngineCompat.luaStringFormat('%d', 12345678901.0), '12345678901');
  same('integer truncates', EngineCompat.luaStringFormat('%d', 3.99), '3');
  same('long precision keeps the fraction', EngineCompat.luaStringFormat('%.15f', 12.5), '12.500000000000000');
  same('long precision rounds the last digit', EngineCompat.luaStringFormat('%.8f', 123456789.99999998), '123456789.99999999');
  same('padded negative float', EngineCompat.luaStringFormat('[%8.2f][%-8.2f][%08.2f]', -3.14159, -3.14159, -3.14159),
   '[   -3.14][-3.14   ][-0003.14]');
  same('general picks its style', EngineCompat.luaStringFormat('%g %g %g %g', 0.0001, 0.00001, 1234567, 2.50),
   '0.0001 1e-05 1.23457e+06 2.5');
  Sys.println('ok');
 }
}
'''
        run_fixture(self, "LuaPatternHelperTest", fixture)


if __name__ == "__main__":
    unittest.main()
