"""Historical public splash gates and mutable global pool against pinned source."""
from pathlib import Path
import re, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class HistoricalPublicSplashTest(unittest.TestCase):
 def test_pinned_public_calls_and_real_flixel_recycle(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir(): self.skipTest('pinned source unavailable')
  source=subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
  direct=method(source,'public function spawnNoteSplash(')
  # The engine never copies donor song-name exceptions. Compare the general path.
  direct=re.sub(r'var lazerSplash:Bool = [^;]+;', 'var lazerSplash:Bool = false;', direct)
  exception=method(direct,'if (lazerSplash)')
  direct=direct.replace(exception,'').replace('var splash:NoteSplash = grpNoteSplashes.recycle', 'var splash:NoteSplash = cast grpNoteSplashes.recycle')
  onnote=method(source,'function spawnNoteSplashOnNote(').replace('function ','public function ',1)
  group=(ROOT/'.haxelib/flixel/6,1,2/flixel/group/FlxGroup.hx').read_text()
  groupmethods='\n'.join(method(group,m) for m in ['public function add(','public function recycle(','public function getFirstAvailable(','public function getFirstNull('])
  files={
   'FlxBasic.hx':"class FlxBasic {public var alive=true;public var exists=true;public var revives=0;public function new(){}public function kill(){alive=exists=false;}public function revive(){alive=exists=true;revives++;}}",
   'flixel/group/FlxGroup.hx':"package flixel.group;import FlxBasic;class FlxG {public static var log={warn:(s:String)->{}};}class FlxTypedGroup<T:FlxBasic> {public var members:Array<T>=[];public var length=0;public var maxSize=0;var _marker=0;function onMemberAdd(o:T):Void {}public function new(){}"+groupmethods+"}",
   'flixel/math/FlxPoint.hx':"package flixel.math;class FlxPoint {public var x:Float;public var y:Float;public function new(x=0.,y=0.){this.x=x;this.y=y;}}",
   'nightmarevision/modchart/NightmareVisionModchartVector.hx':"package nightmarevision.modchart;class NightmareVisionModchartVector {public var x=0.;public var y=0.;public function new(){}public function setTo(x:Float,y:Float,z:Float){this.x=x;this.y=y;}}",
   'Strumline.hx':"class Strumline{}class StrumNote {public var x=100.;public var y=200.;public function new(){}}",
   'NightmareVisionLegacyNoteSplash.hx':"class NightmareVisionLegacyNoteSplash extends NightmareVisionNoteSplash {public function new(){super();}}",
   'NightmareVisionPlayFieldView.hx':"class NightmareVisionPlayFieldView {public var members(get,never):Array<Strumline.StrumNote>;var bank=[new Strumline.StrumNote()];public var scale=2.;function get_members()return bank;public function new(){}}",
   'Note.hx':"class Note {public var noteData=0;public var mustPress=false;public var isSustainNote=false;public var hitCausesMiss=false;public var noteSplashDisabled=false;public var noteSplashHue=.1;public var noteSplashSat=.2;public var noteSplashBrt=.3;public var playField:NightmareVisionPlayFieldView=new NightmareVisionPlayFieldView();public function new(){}}",
   'NightmareVisionNoteSplash.hx':"class NightmareVisionNoteSplash extends FlxBasic {public var args:Array<Dynamic>;public function new(){super();}public function setupLegacyCoordinates(x:Float,y:Float,d:Int,t:String,h:Float,s:Float,b:Float,f:Dynamic){args=[x,y,d,t,h,s,b,f.scale];}public function setupNoteSplash(x:Float,y:Float,d:Int,t:String,h:Float,s:Float,b:Float,f:Dynamic){setupLegacyCoordinates(x,y,d,t,h,s,b,f);}}",
   'NightmareVisionScriptModule.hx':"class NightmareVisionScriptModule {public var fn:String->Array<Dynamic>->Dynamic;public function new(f)fn=f;public function callValue(n:String,a:Array<Dynamic>):Dynamic return fn(n,a);public function call(n:String,a:Array<Dynamic>):Dynamic return fn(n,a);public function parsingFailed()return false;public function destroy():Void {}}",
   'Donor.hx':"import flixel.math.FlxPoint;import flixel.group.FlxGroup.FlxTypedGroup;import Strumline.StrumNote;typedef NoteSplash=NightmareVisionLegacyNoteSplash;class Donor {public var ClientPrefs:Dynamic;public var SONG:Dynamic={keys:4,song:'generic'};public var noteskinScript:NightmareVisionScriptModule;public var grpNoteSplashes=new FlxTypedGroup<NightmareVisionNoteSplash>();public var notify:Array<Dynamic>->Dynamic;public function new(){}function callOnHScripts(n:String,a:Array<Dynamic>):Dynamic return notify(a);"+direct+onnote+"}",
   'Main.hx':r"""import flixel.group.FlxGroup.FlxTypedGroup;
class Main {
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function scenario(host:Bool,mode:Int):String {
  var donor=new Donor();var prefs:Dynamic={noteSplashes:mode!=1,noteSkin:mode==2?'Quants':'Vanilla',arrowHSV:[[90.,20.,30.],[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]};donor.ClientPrefs=prefs;
  var events:Array<String>=[];if(mode==5){var foreign=new NightmareVisionNoteSplash();foreign.kill();donor.grpNoteSplashes.add(foreign);}var original=donor.grpNoteSplashes;var replacement=new FlxTypedGroup<NightmareVisionNoteSplash>();
  var module=new NightmareVisionScriptModule(function(n,a):Dynamic {events.push(n);if(n=='noteSplash'){a[0][0].x=11;a[0][0].y=13;if(mode==3)donor.grpNoteSplashes=replacement;return 'custom';}return true;});donor.noteskinScript=module;
  donor.notify=function(a):Dynamic {var s:NightmareVisionNoteSplash=cast a[0];check(donor.grpNoteSplashes.members.indexOf(s)>=0,'membership before callback');events.push('spawn:'+s.args.join('|')+':'+a[3]+':'+a[4]);s.kill();return 2;};
  var note=new Note();note.mustPress=mode%2==0;note.hitCausesMiss=true;note.noteSplashDisabled=true;note.isSustainNote=true;
  var spawn=function(x:Float,y:Float,d:Int,n:Note):Void {if(host)NightmareVisionLegacySplashRuntime.spawn(x,y,d,n,module,4,prefs,function()return donor.grpNoteSplashes,function()return new NightmareVisionLegacyNoteSplash(),donor.notify);else donor.spawnNoteSplash(x,y,d,n);};
  var onNote=function(n:Note):Void {if(host)NightmareVisionLegacySplashRuntime.onNote(n,prefs,spawn);else donor.spawnNoteSplashOnNote(n);};
  onNote(null);if(mode==4)note.playField.members[0]=null;
  onNote(note);spawn(7,9,0,note);spawn(8,10,0,note);
  check(donor.grpNoteSplashes.length==(mode==5?2:1),'shared pool reuses only historical source class and does not double-add');
  if(mode==5)check(donor.grpNoteSplashes.members[0].revives==0,'foreign source class remains unrecycled');
  check(original==donor.grpNoteSplashes || (mode==3&&original.length==0&&replacement==donor.grpNoteSplashes),'hook group reassignment before recycle');
  events.push('revives:'+donor.grpNoteSplashes.members[0].revives);
  return events.join(',');
 }
 static function main(){for(i in 0...6){var expected=scenario(false,i),actual=scenario(true,i);check(actual==expected,'source scenario '+i+'\n'+actual+'\nEXPECTED '+expected);}}
}
"""
  }
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
   work=FixturePath(d)
   for name,text in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
   r=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=40)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
