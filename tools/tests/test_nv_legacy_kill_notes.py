"""Pinned KillNotes live traversal, retirement order and replacement identity."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
HOST=r'''
class Host {
 public var notes:Group;public var unspawnNotes:Array<Note>=[];public var eventNotes(get,set):Array<Dynamic>;
 public var registry=new NightmareVisionLegacyScriptRegistry();public var modchartObjects:Map<String,Dynamic>=[];
 public var log:Array<String>=[];public var mode:Int;public var previous:Group;
 public function new(mode:Int){this.mode=mode;notes=new Group(this);for(id in 1...4)add(id);unspawnNotes=[new Note(90,this)];registry.eventNotes=[{event:'pending'}];if(mode==7)notes.members.insert(0,null);}
 function get_eventNotes():Array<Dynamic>return registry.eventNotes;
 function set_eventNotes(v:Array<Dynamic>):Array<Dynamic>return registry.eventNotes=v;
 function legacyScriptRegistry()return registry;
 public function add(id:Int){var n=new Note(id,this);notes.members.push(n);modchartObjects.set('note'+id,n);}
 function nightmareVisionRemoveFieldNoteMembership(n:Note,hostAlreadyRemoved:Bool=false):Void {n.member=false;}
 __RETIRE__
 __ACTUAL__
 __REFERENCE__
 public function bind(i:NightmareVisionScriptInterp){
  i.variables.set('game',this);i.variables.set('PlayState',Host);i.variables.set('Reflect',i.sourceClassScope().reflectFacade());
  NightmareVisionLegacyRegistryBindings.install(i,this,Host,registry);
  NightmareVisionLegacyEventBindings.install(i,this,Host,{KillNotes:killHistoricalNightmareNotes});
 }
}
class Group {
 public var members:Array<Note>=[];public var length(get,never):Int;var host:Host;
 public function new(h:Host)host=h;function get_length():Int return members.length;
 public function remove(n:Note,splice:Bool){host.log.push('remove:'+n.ID+':'+splice);members.remove(n);return n;}
}
class Note {
 public var active=true;public var visible=true;public var alive=true;public var exists=true;public var destroyed=false;public var member=true;
 public var ID:Int;var host:Host;
 public function new(id:Int,h:Host){ID=id;host=h;}
 public function kill(){
  host.log.push('kill:'+ID+':'+active+':'+visible+':'+host.modchartObjects.exists('note'+ID)+':'+host.notes.length);
  active=false;alive=false;exists=false;
  if(ID==1)switch(host.mode){case 1:host.add(100);case 3:host.notes.members.pop();case 5:host.notes.members.reverse();default:}
 }
 public function destroy(){
  destroyed=true;host.log.push('destroy:'+ID+':'+host.notes.length+':'+host.unspawnNotes.length+':'+host.eventNotes.length);
  if(ID==1)switch(host.mode){case 2:host.add(100);case 4:host.previous=host.notes;host.notes=new Group(host);host.add(100);case 6:host.unspawnNotes=[new Note(91,host)];host.eventNotes=[{},{}];default:}
 }
}
@:access(Host) class Main {
 static function check(b:Bool,m:String){if(!b)throw m;}
 static function inspect(h:Host,oldNotes:Array<Note>,oldEvents:Array<Dynamic>,failed:Bool):String {
  var keys=[for(k in h.modchartObjects.keys())k];keys.sort(Reflect.compare);
  if(!failed){check(h.notes.length==0&&h.unspawnNotes.length==0&&h.eventNotes.length==0,'queues empty');check(h.unspawnNotes!=oldNotes&&h.eventNotes!=oldEvents,'fresh array identity');}
  check(oldNotes.length==1&&!oldNotes[0].destroyed&&oldEvents.length==1,'pending records are abandoned without destruction or old-array mutation');
  return h.log.join('|')+'#'+keys.join(',')+'#'+failed;
 }
 static function main(){
 for(mode in 0...8)for(form in ['KillNotes();','game.KillNotes();','PlayState.KillNotes();','Reflect.callMethod(game,Reflect.field(game,"KillNotes"),[]);']) {
  var source=new Host(mode);var oldNotes=source.unspawnNotes;var oldEvents=source.eventNotes;var failed=false;
  try source.referenceKill() catch(_:Dynamic)failed=true;
  var expected=inspect(source,oldNotes,oldEvents,failed);
  var actual=new Host(mode);oldNotes=actual.unspawnNotes;oldEvents=actual.eventNotes;failed=false;
  var i=new NightmareVisionScriptInterp(actual);actual.bind(i);
  i.variables.set('oldNotes',oldNotes);i.variables.set('oldEvents',oldEvents);
  try i.execute(new NightmareVisionScriptParser().parseString(form)) catch(_:Dynamic)failed=true;
  check(inspect(actual,oldNotes,oldEvents,failed)==expected,'source retirement '+mode+' '+form);
  if(!failed)i.execute(new NightmareVisionScriptParser().parseString('if(unspawnNotes==oldNotes||eventNotes==oldEvents||game.unspawnNotes.length!=0||PlayState.eventNotes.length!=0)throw "live array aliases";'));
  i.release();
 }
 var h=new Host(0);var original:Array<Dynamic>=[{strumTime:0.,event:'first'},{strumTime:0.,event:'second'}];h.eventNotes=original;var fired=0;
 NightmareVisionLegacyEventQueue.drain(function()return h.eventNotes,function()return 1.,function(e){fired++;h.killHistoricalNightmareNotes();});
 check(fired==1&&h.eventNotes.length==0&&original.length==2,'cleanup during an event retires the live queue without mutating the old reference');
 trace('32 pinned KillNotes cases verified');
 }
}
'''
class LegacyKillNotesTest(unittest.TestCase):
 def test_live_cleanup_and_public_bindings_match_source(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned historical source unavailable')
  source=subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
  reference=extract_method(source,'function KillNotes(').replace('function KillNotes','public function referenceKill')
  play=(ROOT/'source/PlayState.hx').read_text()
  actual=extract_method(play,'function killHistoricalNightmareNotes(')
  retire=extract_method(play,'function retireNightmareVisionLegacyNote(')
  text=HOST.replace('__REFERENCE__',reference).replace('__ACTUAL__',actual).replace('__RETIRE__',retire)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);write_flixel_point_stub(work);(work/'Main.hx').write_text(text)
   (work/'Note.hx').write_text('typedef Note=Main.Note;')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
