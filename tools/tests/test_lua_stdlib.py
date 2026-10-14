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


class LuaStdlibTest(unittest.TestCase):
    def test_library_tables_and_base_functions_work_in_a_lua_scope(self):
        fixture = r'''
class LuaStdlibTest {
 static var interp:LuaCompatInterp;
 static function show(value:Dynamic):String return value == null ? 'nil' : Std.string(value);
 static function same(name:String, want:String) {
  var got = show(interp.variables.get(name));
  if (got != want) throw name + ': got ' + got + ' want ' + want;
 }
 static function main() {
  interp = new LuaCompatInterp();
  var printed:Array<String> = [];
  interp.variables.set("debugPrint", function(text:Dynamic, ?color:Dynamic) printed.push(Std.string(text)));
  // Every result of a call, joined, so the script can look at more than the first one.
  interp.variables.set("all", interp.registerMultiValueFunction(Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
   var items:Array<String> = [];
   for (value in args)
    for (item in LuaValues.list(value))
     items.push(show(item));
   return args.length == 0 ? "nil" : items.join(",");
  })));
  interp.variables.set("second", interp.registerMultiValueFunction(Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic
   return LuaValues.list(LuaValues.of(args))[1])));
  LuaStdlib.install(interp);
  var script = "
   math.remap = function(v, a, b) { return a + v * (b - a); };
   remapped = math.remap(0.5, 0, 10);
   var floor = math.floor;
   aliased = floor(2.5);

   var t = [3, 1, 2];
   table.sort(t);
   sorted = table.concat(t, ',');
   removedLast = table.remove(t);
   afterRemoveLast = table.concat(t, ',');
   var words = ['pear', 'apple', 'fig', 'kiwi'];
   table.sort(words, function(a, b) { return a > b; });
   sortedDescending = table.concat(words, ' ');
   removedFirst = table.remove(words, 1);
   afterRemoveFirst = table.concat(words, ' ');
   removedFromEmpty = table.remove([]);
   table.insert(words, 'plum');
   table.insert(words, 1, 'lime');
   afterInsert = table.concat(words, ' ');
   concatRange = table.concat(['a', 'b', 'c', 'd'], '-', 2, 3);
   concatNumbers = table.concat([1, 2, 3]);
   tableLength = table.getn(words);
   unpacked = all(unpack([1, 2, 3]));
   unpackedRange = all(table.unpack(['a', 'b', 'c'], 2));
   selectCount = select('#', 'a', 'b', 'c');
   selectRest = all(select(2, 'a', 'b', 'c'));
   selectLast = all(select(-1, 'a', 'b', 'c'));

   pcallOk = all(pcall(function(a) { return a + 1; }, 4));
   pcallError = all(pcall(function() { error('boom'); }));
   pcallNil = all(pcall(null));
   var thrownTable = {code: 7};
   pcallTable = rawequal(second(pcall(function() { error(thrownTable); })), thrownTable);
   firstOnly = pcall(function() { return 9; });
   pcallAssert = all(pcall(function() { assert(false, 'nope'); }));
   pcallAssertDefault = all(pcall(function() { assert(null); }));
   assertPasses = all(assert(5, 'unused'));
   pcallArithmetic = all(pcall(function() { var missing = null; return missing + 1; }));
   function keepsLocals() {
    var keep = 7;
    pcall(function() { var inner = 1; error('boom'); });
    return keep;
   }
   localsAfterError = keepsLocals();

   maxOfThree = math.max(1, 5, 3);
   minOfThree = math.min(4, 2, 8);
   hugeIsBig = math.huge > 1000000000;
   floored = math.floor(3.7);
   ceiled = math.ceil(3.2);
   flooredNegative = math.floor(-0.5);
   absolute = math.abs(-4);
   modf = all(math.modf(3.25));
   fmod = math.fmod(7, 3);
   power = math.pow(2, 5);
   squareRoot = math.sqrt(16);
   degrees = math.floor(math.deg(math.pi) + 0.5);
   arcTangent = math.atan2(0, 1);
   logTen = math.floor(math.log10(1000) + 0.5);
   var roll = math.random();
   randomFloat = roll >= 0 && roll < 1;
   var die = math.random(3);
   randomOne = die >= 1 && die <= 3 && die == math.floor(die);
   var ranged = math.random(5, 6);
   randomTwo = ranged == 5 || ranged == 6;
   math.randomseed(42);

   repeated = string.rep('ab', 3);
   byteOfA = string.byte('A');
   bytes = all(string.byte('ABC', 1, 3));
   fromCodes = string.char(72, 105);
   reversed = string.reverse('abc');
   length = string.len('hello');
   upper = string.upper('abc');
   lower = string.lower('ABC');
   sub = string.sub('hello', 2, -2);
   found = all(string.find('abc123', '%d+'));
   foundCaptures = all(string.find('key=value', '(%w+)=(%w+)'));
   notFound = string.find('abc', '%d');
   foundPlain = all(string.find('a b', ' ', 0, true));
   matched = all(string.match('1.5, 20', '([^,]+),%s*([^,]+)'));
   matchedOne = string.match('speed=2', '=(%d+)');
   swapped = all(string.gsub('john smith', '(%w+) (%w+)', '%2 %1'));
   gsubFunction = all(string.gsub('a1b22', '%d+', function(digits) { return '<' + string.len(digits) + '>'; }));
   gsubTable = all(string.gsub('hi NAME', '%u+', {NAME: 'Sam'}));
   var step = string.gmatch('+x-y', '(%p)(%w+)');
   gmatchFirst = all(step());
   gmatchSecond = all(step());
   gmatchDone = step();
   scopedFind = all(luaStringFind('abc123', '%d+'));
   scopedMatch = all(luaStringMatch('4,8', '(%d),(%d)'));
   scopedGsub = all(luaStringGsub('a.b', '%.', '-'));
   scopedSingle = luaStringFind('abc123', '%d+');
   scopedFormat = luaStringFormat('%d%d%d%d%d%d%d%d%d', 1, 2, 3, 4, 5, 6, 7, 8, 9);
   nestedResults = string.upper(string.gsub('abc', 'b', 'x'));
   formatted = string.format('%5.1f|%-3d|%s', 2.25, 7, 'x');
   formattedMany = string.format('%d%d%d%d%d%d%d%d%d%d', 1, 2, 3, 4, 5, 6, 7, 8, 9, 0);

   dateIsText = type(os.date()) == 'string';
   yearDigits = string.len(os.date('%Y'));
   fixedDate = os.date('!%Y-%m-%d %H:%M:%S', 86400);
   recentDate = os.date('!%Y-%m-%d', 1700000000);
   fixedParts = os.date('!%A %B %j %p %I', 86400);
   var fields = os.date('*t');
   dateTable = type(fields) == 'table' && fields.year >= 2024 && fields.month >= 1 && fields.month <= 12;
   timeIsNumber = type(os.time()) == 'number' && os.time() > 1700000000;
   timeFromFields = os.time({year: 2020, month: 1, day: 2, hour: 0}) - os.time({year: 2020, month: 1, day: 1, hour: 0});
   clockIsNumber = type(os.clock()) == 'number';
   difference = os.difftime(10, 4);
   unsafeOs = all(os.execute) + ',' + all(os.remove) + ',' + all(os.getenv) + ',' + all(os.exit);

   typeOfFunction = type(function() { return 1; });
   typeOfLibrary = type(math) + ',' + type(math.floor) + ',' + type(pcall);
   typeOfValues = type(null) + ',' + type(1) + ',' + type('x') + ',' + type(true) + ',' + type([1]) + ',' + type({a: 1});

   nextEmpty = next([]);
   nextFirst = all(next([10, 20]));
   nextSecond = all(next([10, 20], 1));
   nextEnd = next([10, 20], 2);
   nextField = all(next({a: 1}));
   var walked = {a: 1};
   var walkedKey = next(walked);
   walked.a = null;
   nextAfterClearing = all(pcall(next, walked, walkedKey));
   nextOnNothing = all(pcall(next, null));
   var raw = {a: 1};
   rawset(raw, 'b', 2);
   rawRead = all(rawget(raw, 'a')) + ',' + all(rawget(raw, 'b')) + ',' + all(rawget(raw, 'c'));
   var list = [];
   rawset(list, 1, 'first');
   rawList = rawget(list, 1);
   rawSame = rawequal(raw, raw);
   rawDifferent = rawequal(raw, {a: 1});

   stringified = tostring(null) + ',' + tostring(12) + ',' + tostring(true) + ',' + tostring('s');
   converted = all(tonumber('0x10')) + ',' + all(tonumber('z')) + ',' + all(tonumber('ff', 16)) + ',' + all(tonumber(' 8 '));
   print('a', 1, null);
  ";
  interp.execute(new hscript.Parser().parseString(script));

  same("remapped", "5");
  same("aliased", "2");
  same("sorted", "1,2,3");
  same("removedLast", "3");
  same("afterRemoveLast", "1,2");
  same("sortedDescending", "pear kiwi fig apple");
  same("removedFirst", "pear");
  same("afterRemoveFirst", "kiwi fig apple");
  same("removedFromEmpty", "nil");
  same("afterInsert", "lime kiwi fig apple plum");
  same("concatRange", "b-c");
  same("concatNumbers", "123");
  same("tableLength", "5");
  same("unpacked", "1,2,3");
  same("unpackedRange", "b,c");
  same("selectCount", "3");
  same("selectRest", "b,c");
  same("selectLast", "c");

  same("pcallOk", "true,5");
  same("pcallError", "false,boom");
  same("pcallNil", "false,attempt to call a nil value");
  same("pcallTable", "true");
  same("firstOnly", "true");
  same("pcallAssert", "false,nope");
  same("pcallAssertDefault", "false,assertion failed!");
  same("assertPasses", "5,unused");
  if (show(interp.variables.get("pcallArithmetic")).indexOf("false,") != 0
   || show(interp.variables.get("pcallArithmetic")).indexOf("nil") < 0)
   throw "pcall must report an interpreter error: " + show(interp.variables.get("pcallArithmetic"));
  same("localsAfterError", "7");

  same("maxOfThree", "5");
  same("minOfThree", "2");
  same("hugeIsBig", "true");
  same("floored", "3");
  if (!Std.isOfType(interp.variables.get("floored"), Int)) throw "math.floor gives a whole number";
  same("ceiled", "4");
  same("flooredNegative", "-1");
  same("absolute", "4");
  same("modf", "3,0.25");
  same("fmod", "1");
  same("power", "32");
  same("squareRoot", "4");
  same("degrees", "180");
  same("arcTangent", "0");
  same("logTen", "3");
  same("randomFloat", "true");
  same("randomOne", "true");
  same("randomTwo", "true");

  same("repeated", "ababab");
  same("byteOfA", "65");
  same("bytes", "65,66,67");
  same("fromCodes", "Hi");
  same("reversed", "cba");
  same("length", "5");
  same("upper", "ABC");
  same("lower", "abc");
  same("sub", "ell");
  same("found", "4,6");
  same("foundCaptures", "1,9,key,value");
  same("notFound", "nil");
  same("foundPlain", "2,2");
  same("matched", "1.5,20");
  same("matchedOne", "2");
  same("swapped", "smith john,1");
  same("gsubFunction", "a<1>b<2>,2");
  same("gsubTable", "hi Sam,1");
  same("gmatchFirst", "+,x");
  same("gmatchSecond", "-,y");
  same("gmatchDone", "nil");
  same("scopedFind", "4,6");
  same("scopedMatch", "4,8");
  same("scopedGsub", "a-b,1");
  same("scopedSingle", "4");
  same("scopedFormat", "123456789");
  same("nestedResults", "AXC");
  // 2.25 is exactly half way: C and real Lua round it to the even 2.2.
  same("formatted", "  2.2|7  |x");
  same("formattedMany", "1234567890");

  same("dateIsText", "true");
  same("yearDigits", "4");
  same("fixedDate", "1970-01-02 00:00:00");
  same("recentDate", "2023-11-14");
  same("fixedParts", "Friday January 002 AM 12");
  same("dateTable", "true");
  same("timeIsNumber", "true");
  same("timeFromFields", "86400");
  same("clockIsNumber", "true");
  same("difference", "6");
  same("unsafeOs", "nil,nil,nil,nil");
  for (name in ["io", "require", "dofile", "loadstring", "load", "loadfile", "debug", "package"])
   if (interp.variables.get(name) != null) throw name + " must not be exposed";

  same("typeOfFunction", "function");
  same("typeOfLibrary", "table,function,function");
  same("typeOfValues", "nil,number,string,boolean,table,table");

  same("nextEmpty", "nil");
  same("nextFirst", "1,10");
  same("nextSecond", "2,20");
  same("nextEnd", "nil");
  same("nextField", "a,1");
  same("nextAfterClearing", "true,nil");
  same("nextOnNothing", "true,nil");
  same("rawRead", "1,2,nil");
  same("rawList", "first");
  same("rawSame", "true");
  same("rawDifferent", "false");

  same("stringified", "nil,12,true,s");
  same("converted", "16,nil,255,8");
  if (printed.length != 1 || printed[0] != "a\t1\tnil") throw "print goes to the script log: " + printed;

  // math.random hands off to the engine's seeded source when the scope has one.
  var asked:Array<String> = [];
  interp.variables.set("luaMathRandom", function(?first:Null<Int>, ?second:Null<Int>):Dynamic {
   asked.push(first + ":" + second);
   return 4;
  });
  interp.execute(new hscript.Parser().parseString("engineRoll = math.random(2, 6); math.random(); math.random(9);"));
  same("engineRoll", "4");
  if (asked.join(" ") != "2:6 null:null 9:null") throw "engine random arguments: " + asked;

  // Installing again keeps what the script added and what it replaced.
  var ownPrint:Dynamic = function(value:Dynamic) return "mine";
  interp.variables.set("print", ownPrint);
  LuaStdlib.install(interp);
  if (interp.variables.get("print") != ownPrint) throw "a script's own global survives a second install";
  interp.execute(new hscript.Parser().parseString("again = math.remap(1, 0, 4) + math.max(1, 2);"));
  same("again", "6");

  // Method calls on a string value look the name up in the string library.
  if (show(LuaStdlib.stringMethod("abc", "upper", [])) != "ABC") throw "string method";
  if (LuaValues.list(LuaStdlib.stringMethod("a,b", "match", ["(%w+),(%w+)"])).join("|") != "a|b") throw "string method results";
  if (show(LuaStdlib.stringMethod("x1", "gsub", ["%d", "2"])) != "x2, 1") throw "string method gsub";
  var rejected = false;
  try LuaStdlib.stringMethod("abc", "execute", []) catch (_:Dynamic) rejected = true;
  if (!rejected) throw "unknown string method must fail";

  // A plain script interpreter is not a Lua scope and gets none of this.
  var native = new hscript.Interp();
  for (name in ["pcall", "string", "table", "os", "math", "unpack", "next", "select"])
   if (native.variables.exists(name)) throw "native interpreter received " + name;
  Sys.println("ok");
 }
}
'''
        run_fixture(self, "LuaStdlibTest", fixture)

    def test_type_reports_functions_and_random_helper_covers_each_form(self):
        fixture = r'''
class LuaStdlibHelpersTest {
 static function main() {
  if (EngineCompat.luaType(function() return 1) != "function") throw "function type";
  if (EngineCompat.luaType(Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic return null)) != "function")
   throw "variadic function type";
  if (EngineCompat.luaType({a: 1}) != "table" || EngineCompat.luaType([1]) != "table") throw "table type";
  if (EngineCompat.luaType(new haxe.ds.StringMap<Int>()) != "userdata") throw "engine object type";
  if (EngineCompat.luaType(1.5) != "number" || EngineCompat.luaType("s") != "string"
   || EngineCompat.luaType(false) != "boolean" || EngineCompat.luaType(null) != "nil") throw "value types";
  for (attempt in 0...200) {
   var unit:Float = LuaStdlib.random();
   if (unit < 0 || unit >= 1) throw "random() range";
   var single:Int = LuaStdlib.random(4);
   if (single < 1 || single > 4) throw "random(m) range";
   var ranged:Int = LuaStdlib.random(-2, 2);
   if (ranged < -2 || ranged > 2) throw "random(m, n) range";
  }
  if (LuaStdlib.extreme([3, 9.5, 2], true) != 9.5 || LuaStdlib.extreme([3, 9.5, 2], false) != 2) throw "extreme";
  if (!Std.isOfType(LuaStdlib.extreme([3, 1], true), Int)) throw "max keeps whole numbers whole";
  var list:Array<Dynamic> = ["b", "c", "a"];
  LuaStdlib.sort(list);
  if (list.join("") != "abc") throw "sort on an engine array";
  if (LuaStdlib.remove(list, 1) != "a" || LuaStdlib.remove(list) != "c" || list.join("") != "b") throw "remove on an engine array";
  if (LuaStdlib.concat(["x", 1, "y"], "/") != "x/1/y") throw "concat on an engine array";
  var mixed = false;
  try LuaStdlib.sort([1, "a"]) catch (_:Dynamic) mixed = true;
  if (!mixed) throw "sorting mixed types is an error, as in Lua";
  Sys.println("ok");
 }
}
'''
        run_fixture(self, "LuaStdlibHelpersTest", fixture)


if __name__ == "__main__":
    unittest.main()
