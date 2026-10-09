"""Actual source tap-spawn and caller contracts over pinned Flixel recycle."""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]

class NoteSplashFieldTest(unittest.TestCase):
 def test_source_spawn_and_rating_caller_with_real_getter_and_pool(self):
  ps=(ROOT/'source/PlayState.hx').read_text(encoding='utf-8')
  spawn=method(ps,'function spawnNightmareVisionNoteSplash(').replace('function ','public function ',1)
  caller=method(ps,'function prepareNightmareVisionHitSplash(').replace('function ','public function ',1)
  field_spawn=method((ROOT/'source/NightmareVisionPlayFieldView.hx').read_text(encoding='utf-8'),'public function spawnSplash(')
  donor=(ROOT.parent/'fnf_sources/NightmareVision/source/funkin/objects/note/PlayField.hx').read_text(encoding='utf-8')
  reference=re.sub(r'\bNoteSplash\b','NightmareVisionNoteSplash',method(donor,'public function spawnSplash('))
  group=(ROOT/'.haxelib/flixel/6,1,2/flixel/group/FlxGroup.hx').read_text(encoding='utf-8')
  groupmethods='\n'.join(method(group,m) for m in ['public function add(','public function recycle(','public function getFirstAvailable(','public function getFirstNull('])
  files={
   'flixel/group/FlxGroup.hx':'''package flixel.group;import FlxBasic;class FlxG {public static var log={warn:(s:String)->{}};}class FlxTypedGroup<T:FlxBasic> {public var members:Array<T>=[];public var length:Int=0;public var maxSize:Int=0;var _marker=0;public var onAdded:T->Void;function onMemberAdd(o:T):Void if(onAdded!=null)onAdded(o);public function new(){} __METHODS__}'''.replace('__METHODS__',groupmethods),
   'FlxBasic.hx':'class FlxBasic {public var alive=true;public var exists=true;public var alpha:Float=1;public var revives=0;public function new(){}public function kill(){alive=exists=false;}public function revive(){alive=exists=true;revives++;}}',
   'Strumline.hx':'class Strumline{}class StrumNote {public var ID:Int;public function new(i:Int)ID=i;}',
   'NightmareVisionNoteSkin.hx':'class NightmareVisionNoteSkin {public var splashesEnabled=true;public var splashTexture="skin";public function new(){}}',
   'NightmareVisionPlayFieldView.hx':'''class NightmareVisionPlayFieldView {public var members(get,never):Array<Strumline.StrumNote>;var bank:Array<Strumline.StrumNote>;function get_members()return bank;public var grpNoteSplashes:Dynamic=new flixel.group.FlxGroup.FlxTypedGroup<NightmareVisionNoteSplash>();public var noteSplashes=true;public var trackNoteSplashes=true;public var playerControls=false;public var _skin:NightmareVisionNoteSkin=new NightmareVisionNoteSkin();public var host:Host;public var nativeHooks:{spawnSplash:(NightmareVisionPlayFieldView,Dynamic)->Dynamic};function missingHook(name:String):Void throw name;public function new(){bank=[for(i in 0...6)new Strumline.StrumNote(i)];}__FIELD_SPAWN__}'''.replace('__FIELD_SPAWN__',field_spawn),
   'Note.hx':'class Note {public var noteSplashTexture="skin";public var noteType="";public var isQuant=false;public var noteData=5;public var playField:NightmareVisionPlayFieldView;public var hitCausesMiss=false;public var isSustainNote=false;public var noteSplashDisabled=false;public var rgbGraphics:Dynamic={};public var noteSplash:Dynamic;public var ratingMod:Float=.25;public function new(){playField=new NightmareVisionPlayFieldView();}}',
   'NightmareVisionNoteSplash.hx':'''class NightmareVisionNoteSplash extends FlxBasic {public var data=0;public var usedField:NightmareVisionPlayFieldView;public var usedStrum:Strumline.StrumNote;public var texture:String;public var graphics:Dynamic;public function new(x=0,y=0,d=0,p=0,?owner:Dynamic){super();data=d;}public function setupLegacyNoteSplash(s:Strumline.StrumNote,n:Note,t:String,f:NightmareVisionPlayFieldView)setupNoteSplash(s,n,t,n.rgbGraphics,f);public function setupNoteSplash(s:Strumline.StrumNote,n:Note,t:String,g:Dynamic,f:NightmareVisionPlayFieldView){data=n.noteData;usedStrum=s;usedField=f;texture=t;graphics=g;}}''',
   'ClientPrefs.hx':'class ClientPrefs {public static var noteSplashType="Both";}',
   'PlayState.hx':'class PlayState {public static var instance={scripts:{call:(name:String,args:Array<Dynamic>)->Main.callback(name,args)}};}',
   'Donor.hx':'import Strumline.StrumNote;class Donor extends NightmareVisionPlayFieldView {public function new(){super();}'+reference.replace('public function spawnSplash','public function donorSpawnSplash')+'}',
   'Host.hx':'import flixel.group.FlxGroup.FlxTypedGroup;class Host {public var nightmareVisionLegacyFieldCameras=false;public var nightmareVisionPrefs={view:{noteSplashType:"Both"}};public function new(){}function nightmareVisionSustainSplashOwner():Dynamic return null;function callNightmareVision(name:String,args:Array<Dynamic>):Void Main.callback(name,args);'+spawn+caller+'}',
   'Main.hx':r'''import flixel.group.FlxGroup.FlxTypedGroup;class Main {static var events:Array<String>=[];static function ok(v:Bool,m:String):Void if(!v)throw m;public static function callback(name:String,args:Array<Dynamic>):Void{var s:NightmareVisionNoteSplash=cast args[0];var n:Note=cast args[1];ok(name=='onSpawnNoteSplash'&&n.noteSplash==null,'callback before pointer');var group:FlxTypedGroup<NightmareVisionNoteSplash>=cast s.usedField.grpNoteSplashes;ok(group.members.indexOf(s)>=0,'callback after membership');events.push('callback:'+s.data);}static function scenario(donor:Bool):String {var h=new Host();var f=new Donor();f.host=h;f.nativeHooks={spawnSplash:h.spawnNightmareVisionNoteSplash};var n=new Note();var group:FlxTypedGroup<NightmareVisionNoteSplash>=cast f.grpNoteSplashes;events=[];group.onAdded=s->events.push('added:'+s.data);var s:NightmareVisionNoteSplash=donor?f.donorSpawnSplash(n):cast h.spawnNightmareVisionNoteSplash(f,n);ok(s==n.noteSplash&&s.usedStrum==n.playField.members[5]&&s.usedField==f&&s.texture=='skin'&&s.graphics==n.rgbGraphics,'source own bank/widerdata/field texture/RGB');ok(n.ratingMod<1,'public spawn permits low rating');s.alpha=.37;s.kill();n.noteSplash=null;var recycled:NightmareVisionNoteSplash=donor?f.donorSpawnSplash(n):cast h.spawnNightmareVisionNoteSplash(f,n);ok(recycled==s&&s.alpha==.37&&s.revives==1&&group.length==1,'real recycle preserves alpha/revives/no doubleadd');return events.join(',');}static function main(){ok(scenario(true)==scenario(false),'donor spawn publication trace');for(donor in [true,false]){var h=new Host();var f=new Donor();f.host=h;f.nativeHooks={spawnSplash:h.spawnNightmareVisionNoteSplash};var n=new Note();for(pref in ['Both','Note Splashes','Hold Covers','None']){ClientPrefs.noteSplashType=pref;h.nightmareVisionPrefs.view.noteSplashType=pref;for(gate in 0...6){n.hitCausesMiss=gate==1;n.isSustainNote=gate==2;n.noteSplashDisabled=gate==3;f.noteSplashes=gate!=4;f._skin.splashesEnabled=gate!=5;n.noteSplash=null;var result=donor?f.donorSpawnSplash(n):h.spawnNightmareVisionNoteSplash(f,n);ok((result!=null)==((pref=='Both'||pref=='Note Splashes')&&gate==0),'exact spawn gates');}}ClientPrefs.noteSplashType='Both';h.nightmareVisionPrefs.view.noteSplashType='Both';ok((donor?f.donorSpawnSplash(null):h.spawnNightmareVisionNoteSplash(f,null))==null,'null note shortcircuit');n.hitCausesMiss=false;n.isSustainNote=false;n.noteSplashDisabled=false;f.noteSplashes=true;f._skin.splashesEnabled=true;n.playField.members[5]=null;ok((donor?f.donorSpawnSplash(n):h.spawnNightmareVisionNoteSplash(f,n))==null,'null receptor gate');n.playField=new NightmareVisionPlayFieldView();f._skin=null;var failed=false;try {if(donor)f.donorSpawnSplash(n);else h.spawnNightmareVisionNoteSplash(f,n);}catch(_:Dynamic)failed=true;ok(failed,'null skin source coalesce gate then texture failure');}var h=new Host();var f=new NightmareVisionPlayFieldView();f.host=h;f.nativeHooks={spawnSplash:h.spawnNightmareVisionNoteSplash};var n=new Note();f.playerControls=true;n.noteSplash=null;h.prepareNightmareVisionHitSplash(n,f,0);ok(n.noteSplash==null,'player low rating caller gate');n.ratingMod=1;h.prepareNightmareVisionHitSplash(n,f,0);ok(n.noteSplash!=null,'player perfect rating caller');n.noteSplash=null;f.playerControls=false;n.ratingMod=-1;h.prepareNightmareVisionHitSplash(n,f,0);ok(n.noteSplash!=null,'opponent rating independent caller');}}'''}
  files['NightmareVisionLegacyNoteSplash.hx']='class NightmareVisionLegacyNoteSplash extends NightmareVisionNoteSplash {public function new(x=0,y=0,n=0,?owner:Dynamic){super(x,y,n,0,owner);}}'
  files['NightmareVisionLegacyNoteSkin.hx']='class NightmareVisionLegacyNoteSkin {public static function splash(s:Dynamic,k:Int,p:Dynamic,l:Int,n:Dynamic):Dynamic throw "historical skin called in modern field test";}'
  files['Host.hx']=files['Host.hx'].replace('public var nightmareVisionLegacyFieldCameras=false;', 'public var nightmareVisionLegacyFieldCameras=false;public var noteskinScript:Dynamic;function nightmareVisionKeyCount():Int return 4;') if 'Host.hx' in files else ''
  if 'Strumline.hx' in files:files['Strumline.hx']=files['Strumline.hx'].replace('public var ID:Int;', 'public var x=0.;public var y=0.;public var ID:Int;')
  if 'Note.hx' in files:files['Note.hx']=files['Note.hx'].replace('public var noteSplashTexture=', 'public var mustPress=false;public var noteSplashTexture=')
  files['NightmareVisionNoteSplash.hx']=files['NightmareVisionNoteSplash.hx'].replace('public function setupLegacyNoteSplash', 'public function setupLegacyCoordinates(x:Float,y:Float,n:Int,t:String,h:Float,s:Float,b:Float,f:NightmareVisionPlayFieldView):Void throw "historical setup called in modern field test";public function setupLegacyNoteSplash')
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   work=Path(tmp)
   for name,content in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf-8')
   env=os.environ.copy();env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['NEKOPATH']=str(ROOT/'.tools/neko');env['PATH']=str(ROOT/'.tools/haxe')+os.pathsep+str(ROOT/'.tools/neko')+os.pathsep+env.get('PATH','')
   for target in [['--interp'],['-cpp',str(work/'cpp'),'-D','no-compilation']]:
    result=subprocess.run([*HAXE_COMMAND,'-cp',tmp,'-main','Main',*target],cwd=ROOT,env=env,capture_output=True,text=True,timeout=35)
    self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-4000:])
   generated=(work/'cpp/src/Host.cpp').read_text(encoding='utf-8');start=generated.index('Host_obj::spawnNightmareVisionNoteSplash(');body=generated[start:generated.index('HX_DEFINE_DYNAMIC_FUNC2',start)];self.assertIn('noteField->get_members()',body);self.assertNotIn('__Field(HX_("members"',body)

 def test_actual_iris_import_constructor_binding_uses_current_owner(self):
  ps=(ROOT/'source/PlayState.hx').read_text(encoding='utf-8')
  start=ps.index("interp.variables.set('NoteSplash', NightmareVisionNoteSplash)")
  end=ps.index("interp.variables.set('SustainSplash'",start)
  binding=ps[start:end]
  files={
   'NightmareVisionNoteSplash.hx': 'class NightmareVisionNoteSplash {public var x:Float;public var y:Float;public var data:Int;public var player:Int;public var owner:Dynamic;public function new(x:Float=0,y:Float=0,data:Int=0,player:Int=0,?owner:Dynamic){if(owner==null)throw "missing owner";this.x=x;this.y=y;this.data=data;this.player=player;this.owner=owner;}}',
   'Main.hx': 'class Host {public var nightmareVisionLegacyFieldCameras=false;public var selected:Dynamic={id:"a"};public function new(){}function nightmareVisionSustainSplashOwner():Dynamic return selected;public function install(interp:NightmareVisionScriptInterp){'+binding+'}} class Main {static function check(v:Bool,m:String):Void if(!v)throw m;static function main(){var host=new Host();var interp=new NightmareVisionScriptInterp();var parser=new NightmareVisionScriptParser();host.install(interp);check(interp.variables.get("NoteSplash")==interp.importBindings.get("funkin.objects.note.NoteSplash"),"import identity");interp.execute(parser.parseString("import funkin.objects.note.NoteSplash; bare = new NoteSplash(); explicit = new funkin.objects.note.NoteSplash(12, 34, 5, 2);"));var bare:NightmareVisionNoteSplash=cast interp.variables.get("bare");var explicit:NightmareVisionNoteSplash=cast interp.variables.get("explicit");check(bare.x==0&&bare.y==0&&bare.data==0&&bare.player==0&&bare.owner==host.selected,"source default constructor owner");check(explicit.x==12&&explicit.y==34&&explicit.data==5&&explicit.player==2&&explicit.owner==host.selected,"qualified constructor args");host.selected={id:"b"};interp.execute(parser.parseString("current = new NoteSplash(1, 2);"));var current:NightmareVisionNoteSplash=cast interp.variables.get("current");check(current.owner==host.selected&&current.owner!=bare.owner&&current.data==0&&current.player==0,"factory current owner/defaults");interp.release();}}'}
  from test_nightmare_vision_note_skin_runtime import STUBS
  files={**STUBS,**files}
  files['NightmareVisionLegacyNoteSplash.hx']='class NightmareVisionLegacyNoteSplash extends NightmareVisionNoteSplash {public function new(x:Float=0,y:Float=0,n:Int=0,?owner:Dynamic){super(x,y,n,0,owner);}}'
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   work=Path(tmp)
   for name,content in files.items():
    path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',tmp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=35)
   self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-5000:])

 def test_live_skin_updates_alive_current_group_scale_without_reload(self):
  ps=(ROOT/'source/PlayState.hx').read_text(encoding='utf-8')
  body=method(method(ps,'function nightmareVisionChangeFieldSkin('),'if (field.grpNoteSplashes != null)')
  files={
   'Main.hx':'import flixel.group.FlxGroup.FlxTypedGroup;class Skin {public var splashScale:Float=3;public var inEngineColoring=false;public function new(){}}class Field {public var grpNoteSplashes:Dynamic;public function new(){}}class Main {static function change(field:Field,skin:Skin):Void '+body+' static function main(){var f=new Field();var a=new NightmareVisionNoteSplash();var dead=new NightmareVisionNoteSplash();dead.alive=false;var g=new FlxTypedGroup<NightmareVisionNoteSplash>();g.members=[a,null,dead];f.grpNoteSplashes=g;change(f,new Skin());if(a.scale.x!=3||a.baseScale.x!=3||a.rgbGraphics.enabled||a.alpha!=.4||a.skin!="old"||a.texture!="cached"||dead.scale.x!=1)throw "source live skin mutation";}}',
   'NightmareVisionNoteSplash.hx':'class Point {public var x:Float=1;public var y:Float=1;public function new(){}public function set(x:Float,y:Float){this.x=x;this.y=y;}public function copyFrom(p:Point){x=p.x;y=p.y;}}class NightmareVisionNoteSplash {public var alive=true;public var scale=new Point();public var baseScale=new Point();public var rgbGraphics={enabled:true};public var alpha:Float=.4;public var skin="old";public var texture="cached";public function new(){}}',
   'flixel/group/FlxGroup.hx':'package flixel.group;class FlxTypedGroup<T> {public var members:Array<T>=[];public function new(){}}'}
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   work=Path(tmp)
   for name,content in files.items():
    path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf-8')
   env=os.environ.copy();env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['NEKOPATH']=str(ROOT/'.tools/neko');env['PATH']=str(ROOT/'.tools/haxe')+os.pathsep+str(ROOT/'.tools/neko')+os.pathsep+env.get('PATH','')
   for target in [['--interp'],['-cpp',str(work/'cpp'),'-D','no-compilation']]:
    result=subprocess.run([*HAXE_COMMAND,'-cp',tmp,'-main','Main',*target],cwd=ROOT,env=env,capture_output=True,text=True,timeout=35)
    self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-4000:])
