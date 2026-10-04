"""Psych empty presses dispatch a lane callback without inventing a Note."""
from pathlib import Path
from haxe_test_support import FixturePath as Path, HAXE_COMMAND
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PsychMissPressCallbacksTest(unittest.TestCase):
    def test_ghost_press_route_and_note_miss_remain_distinct(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as scratch:
            (Path(scratch) / 'Main.hx').write_text(r'''
class Main {
 static function main():Void {
  for (direction in 0...4) {
   var input:Array<Dynamic>=[null,true,direction,null];
   var args=EngineCompat.psychMissPressArguments('noteMiss',input);
   if(args==null || args.length!=1 || args[0]!=direction) throw 'missing lane press';
   if(input.length!=4 || input[0]!=null) throw 'caller payload mutated';
  }
  if(EngineCompat.psychMissPressArguments('onNoteMiss',[null,false,2])[0]!=2)
   throw 'alias/second input lane lost';
  var note:Dynamic={noteData:3,isSustainNote:false,coolId:'Hurt Note',ID:7};
  if(EngineCompat.psychMissPressArguments('noteMiss',[note,true,3])!=null)
   throw 'live note routed as empty press';
  var invalid:Array<Array<Dynamic>>=[null,[],[null],[null,true],[null,true,'3'],[null,'player',3]];
  for(args in invalid)
   if(EngineCompat.psychMissPressArguments('noteMiss',args)!=null)
    throw 'unsupported payload routed';
  if(EngineCompat.psychMissPressArguments('goodNoteHit',[null,true,3])!=null)
   throw 'unrelated callback routed';
  if(EngineCompat.canonicalCallback('onNoteMissPress')!='noteMissPress') throw 'missing alias';
  var names=EngineCompat.callbackNames('noteMissPress');
  if(names.join(',')!='noteMissPress,onNoteMissPress') throw 'wrong callback candidates';
  var press=EngineCompat.callbackArguments('noteMissPress','noteMissPress',[2]);
  if(press.length!=1 || press[0]!=2) throw 'press received note ABI';
  var ordinary=EngineCompat.callbackArguments('noteMiss','noteMiss',[note,true,3],false,[note]);
  if(ordinary.length!=4 || ordinary[0]!=0 || ordinary[1]!=3 || ordinary[2]!='Hurt Note')
   throw 'live note ABI regressed';
 }
}
''', encoding='utf-8', newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT / 'source'),'-cp',scratch,'--run','Main'],
                                  cwd=ROOT,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        source=(ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        start=source.index('function callHscript(')
        stop=source.index('// Psych removes a Lua script',start)
        route=source[start:stop]
        self.assertIn('Std.isOfType(interp, LuaCompatInterp)',route)
        self.assertIn("interp.variables.get('__psychPlainHscript') == true",route)
        self.assertIn('EngineCompat.psychMissPressArguments(func_name, args)',route)
        self.assertIn("func_name = 'noteMissPress';",route)


if __name__=='__main__':
    unittest.main()
