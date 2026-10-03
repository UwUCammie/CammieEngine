"""Codename indexed `for` loops retain array and map key/value semantics."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR_DEBUG = (Path('/run/media/cammie/External Storage/FNF-Example-Mods')
               / 'codename/D-Sides REDUX Codename Engine (Cancelled)'
               / 'mods/D-Sides REDUX/songs/Debug.hx')


class CodenameIndexedLoopTest(unittest.TestCase):
    @unittest.skipUnless(DONOR_DEBUG.is_file(), 'mounted Codename source unavailable')
    def test_mounted_nested_map_loop_parses_with_explicit_editor_binding(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            base = Path(directory)
            (base / 'PlayState.hx').write_text('''class PlayState {
 public static var instance:PlayState;
 public static var SONG:Dynamic;
 public function new() {}
 public function codenameCharterIdentity():Dynamic return null;
}''', newline='\n')
            (base / 'ChartingState.hx').write_text('''class ChartingState {
 public function new() {}
 public function create():Void {}
 public function destroy():Void {}
}''', newline='\n')
            (base / 'Conductor.hx').write_text('''class Conductor { public static var songPosition:Float=0; }''', newline='\n')
            flxg = base / 'flixel/FlxG.hx'
            flxg.parent.mkdir(parents=True)
            flxg.write_text('''package flixel; class FlxG { public static var state:Dynamic; }''', newline='\n')
            (base / 'Main.hx').write_text('''import sys.io.File;
class Main {
 static function main():Void {
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set('funkin.editors.charter.Charter',CodenameCharterAdapter);
  var prepared=CodenameScriptParser.prepare(File.getContent(Sys.args()[0]),bindings);
  if(prepared.program==null || prepared.diagnostics.length!=0)
   throw prepared.diagnostics.length==0 ? 'no program' : prepared.diagnostics[0].message;
  if(prepared.source.indexOf('CodenameKeyValueIterator.entries(strumLineCache)')<0)
   throw 'source map iteration was not preserved';
 }
}
''', newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                 '-cp', str(base), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                 '-cp', str(ROOT / '.haxelib/hscript-ex/git/src'), '--run',
                 'Main', str(DONOR_DEBUG)], cwd=ROOT, text=True,
                capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

    def test_nested_indexed_loops_execute_array_and_map_pairs(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            base = Path(directory)
            (base / 'Main.hx').write_text('''import hscript.Interp;
class Main {
 static function run(source:String, map:CodenameMapCompat):String {
  var parsed=CodenameScriptParser.prepare(source,new Map());
  if(parsed.program==null || parsed.diagnostics.length!=0)
   throw parsed.diagnostics.length==0 ? 'no program' : parsed.diagnostics[0].message;
  var interp=new Interp();
  interp.variables.set('CodenameKeyValueIterator',CodenameKeyValueIterator.facade());
  interp.variables.set('map',map);
  interp.execute(parsed.program);
  return interp.variables.get('result')();
 }
 static function main():Void {
  var rows=[[2,3],[4]];
  var map=CodenameMapCompat.fromPairs([
   {key:7,value:[8,9]}, {key:3,value:[6]}]);
  var array=run('var rows=[[2,3],[4]]; var output=""; '
   +'for (i => row in rows) for (j in 0...row.length) {'
   +' output += i+":"+j+"="+row[j]+";"; } function result() return output;',map);
  if(array!='0:0=2;0:1=3;1:0=4;') throw 'array pairs: '+array;
  var mapped=run('var output=""; for (key => row in map) '
   +'for (j in 0...row.length) { output += key+":"+row[j]+";"; } '
   +'function result() return output;',map);
  if(mapped!='7:8;7:9;3:6;') throw 'map pairs: '+mapped;
  var native:Map<Int,Array<Int>>=[];
  native.set(12,[5]);
  var nativePairs=CodenameKeyValueIterator.entries(native);
  if(nativePairs.length!=1 || nativePairs[0].key!=12 || nativePairs[0].value[0]!=5)
   throw 'native map pairs';
  var rejected=CodenameScriptParser.prepare(
   'for (i => row in rows) output += row;',new Map());
  if(rejected.program!=null || rejected.diagnostics.length==0
   || rejected.diagnostics[0].code!='unsupported-haxe-surface')
   throw 'unbraced expression was silently accepted';
 }
}
''', newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                 '-cp', str(base), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                 '-cp', str(ROOT / '.haxelib/hscript-ex/git/src'), '--run', 'Main'],
                cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == '__main__':
    unittest.main()
