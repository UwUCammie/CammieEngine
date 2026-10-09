"""Historical speed transaction against the pinned source, including reentry."""
from pathlib import Path
import re, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'

class HistoricalScrollStorageTest(unittest.TestCase):
 def test_speed_transaction_matches_pinned_source(self):
  donor=subprocess.run(['git','-C',str(ROOT.parent/'fnf_sources/NightmareVision'),'show',REV+':source/meta/states/PlayState.hx'],capture_output=True,text=True,check=True).stdout
  reference=extract_method(donor,'function set_songSpeed(').replace('set_songSpeed','referenceSpeed').replace('songSpeed','daScrollSpeed')
  play=(ROOT/'source/PlayState.hx').read_text()
  actual='\n'.join(extract_method(play,m) for m in ['function set_scrollSpeed(', 'function resizePsychSustains(', 'function refreshNightmareVisionNoteKillOffset('])
  flixel=(ROOT/'.haxelib/flixel/6,1,2/flixel/group/FlxGroup.hx').read_text()
  iterator=flixel[flixel.index('class FlxTypedGroupIterator<T>'):]
  host=r'''class Conductor {public static var stepCrochet=400.;}
class Group {
 public var members:Array<Note>=[]; public function new(){}
 public function iterator():FlxTypedGroupIterator<Note> return new FlxTypedGroupIterator(members);
}
class Note {
 public var scale=1.;public var id:Int;var s:PlayState;
 public function new(s:PlayState,id:Int){this.s=s;this.id=id;}
 public function resizeByRatio(r:Float):Void {
  s.events.push(id+':'+r+':'+s.daScrollSpeed+':'+s.noteKillOffset);scale*=r;
  if(id!=0||s.mutated)return;s.mutated=true;
  switch(s.mode){
   case 1:s.assign(7.);
   case 2:throw 'resize';
   case 3:s.notes.members.push(s.third);
   case 4:s.notes.members[2]=s.third;
   case 5:s.notes.members=[s.third];
   case 6:s.unspawnNotes=[s.third,s.first];
   case 7:s.daScrollSpeed=19.;
   case 8:s.unspawnNotes.push(s.third);
   case 9:s.notes.members.splice(1,1);
   default:
  }
 }
}
class PlayState {
 public var daScrollSpeed=2.;public var effectiveScrollSpeed(get,never):Float;function get_effectiveScrollSpeed():Float return 99.;
 public var songSpeed(get,never):Float;function get_songSpeed():Float return daScrollSpeed;
 public var nightmareVisionScripts:Dynamic={};public var nightmareVisionLegacyFieldCameras=true;
 public var generatedMusic=true;public var noteKillOffset=123.;public var playbackRate=3.;
 public var notes=new Group();public var unspawnNotes:Array<Note>=[];
 public var first:Note;public var second:Note;public var third:Note;
 public var events:Array<String>=[];public var mode:Int;public var actual:Bool;public var mutated=false;
 public function new(actual:Bool,mode:Int,generated:Bool,old:Float){this.actual=actual;this.mode=mode;generatedMusic=generated;daScrollSpeed=old;
  first=new Note(this,0);second=new Note(this,1);third=new Note(this,2);
  notes.members=[first,null,second];unspawnNotes=[first,second];
  if(mode==10)unspawnNotes.insert(1,null);
  if(mode==11){notes.members=[];unspawnNotes=[];}
 }
 function sourceNoteTimingMode():Int return 0;function isPsychReceptorNote(n:Note):Bool return false;
 public function assign(v:Float):Float return actual?set_scrollSpeed(v):referenceSpeed(v);
 public function run(v:Float):String {var result='ok';try result+=':'+assign(v) catch(e:Dynamic) result='throw';
  var snapshot:Array<Dynamic>=[result,daScrollSpeed,noteKillOffset,first.scale,second.scale,third.scale,events.join('|')];return snapshot.join(';');}
 __METHODS__
}
class Main {static function main(){var count=0;
 for(mode in 0...12)for(generated in [false,true])for(old in [0.,-2.,2.,Math.POSITIVE_INFINITY,Math.NaN])for(value in [0.,-3.,2.,4.,Math.POSITIVE_INFINITY,Math.NEGATIVE_INFINITY,Math.NaN]){
  var a=new PlayState(true,mode,generated,old).run(value);var b=new PlayState(false,mode,generated,old).run(value);
  if(a!=b)throw mode+':'+generated+':'+old+':'+value+'\n'+a+'\n'+b;count++;
 }trace(count+' historical speed transactions');}}
'''.replace('__METHODS__',actual+'\n'+reference)+'\n'+iterator
  self.run_haxe(host)
 def test_position_aliases_share_baselines_without_moving_groups(self):
  play=(ROOT/'source/PlayState.hx').read_text()
  fields=[]
  for prefix,point in [('BF','boyfriendPosition'),('DAD','dadPosition'),('GF','gfPosition')]:
   for axis in 'xy':
    key=prefix+'_'+axis.upper()
    fields.append(f'public var {key}(get,set):Float;')
    for op in ['get','set']:
     fields.append(re.search(r'function '+op+'_'+key+r'\([^\n]+',play).group(0))
  host=r'''class Point {public var x:Float;public var y:Float;public function new(x:Float,y:Float){this.x=x;this.y=y;}}
class Main {
 public var boyfriendPosition=new Point(770,100);public var dadPosition=new Point(100,100);public var gfPosition=new Point(400,130);
 __FIELDS__
 public function new(){}
 static function main(){var a=new Main();var b=new Main();
  for(key in ['BF_X','BF_Y','DAD_X','DAD_Y','GF_X','GF_Y']){
   var before:Float=Reflect.getProperty(a,key);Reflect.setProperty(a,key,before+17);
   if(Reflect.getProperty(a,key)!=before+17||Reflect.getProperty(b,key)!=before)throw key;
  }
  if(a.gfPosition.x!=417||a.gfPosition.y!=147||a.dadPosition.x!=117||a.boyfriendPosition.y!=117)throw 'shared baseline';
  a.gfPosition.x=999;if(a.GF_X!=999)throw 'live baseline';
 }}'''.replace('__FIELDS__','\n'.join(fields))
  self.run_haxe(host)
 def run_haxe(self,host):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);(work/'Main.hx').write_text(host)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
