"""Source field spawn ordering with pinned Flixel group add/recycle semantics."""
import subprocess
import os
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]

class SustainSplashFieldTest(unittest.TestCase):
 def test_spawn_recycle_publication_direction_miss_release_and_group_pointer_identity(self):
  ps=(ROOT/'source/PlayState.hx').read_text(encoding='utf-8')
  body='\n'.join(method(ps,m).replace('function ','public function ',1) for m in ['function spawnNightmareVisionSustainSplash(', 'function hideNightmareVisionSustainSplashes(', 'function releaseNightmareVisionSustainSplashes(', 'function initializeNightmareVisionFieldSplashes(', 'function destroyNightmareVisionFieldSplashes('])
  donor=(ROOT.parent/'fnf_sources/NightmareVision/source/funkin/objects/note/PlayField.hx').read_text(encoding='utf-8')
  import re
  reference=re.sub(r'\bSustainSplash\b','NightmareVisionSustainSplash',method(donor,'public function spawnSusSplash('))
  group=(ROOT/'.haxelib/flixel/6,1,2/flixel/group/FlxGroup.hx').read_text(encoding='utf-8')
  methods='\n'.join(method(group,m) for m in ['public function add(', 'public function recycle(', 'public function getFirstAvailable(', 'public function getFirstNull(', 'override public function destroy('])
  tap_update=method((ROOT/'source/NoteSplash.hx').read_text(encoding='utf-8'),'override public function update(')
  files={
   'flixel/group/FlxGroup.hx':'''package flixel.group;
import FlxBasic;
import flixel.util.FlxDestroyUtil;
class FlxG {public static var log={warn:(s:String)->{}};}
class FlxTypedGroup<T:FlxBasic> extends FlxBasic {
 public var members:Array<T>=[];public var length:Int=0;public var maxSize:Int=0;var _marker:Int=0;var _memberAdded:flixel.util.IFlxDestroyable;var _memberRemoved:flixel.util.IFlxDestroyable;public var onAdded:T->Void;
 public function new(){super();} function onMemberAdd(o:T):Void if(onAdded!=null)onAdded(o);
 __GROUP__
}'''.replace('__GROUP__',methods),
   'flixel/util/IFlxDestroyable.hx':'package flixel.util; interface IFlxDestroyable {public function destroy():Void;}',
   'flixel/util/FlxDestroyUtil.hx':'package flixel.util; class FlxDestroyUtil {'+'\n'.join(method((ROOT/'.haxelib/flixel/6,1,2/flixel/util/FlxDestroyUtil.hx').read_text(encoding='utf-8'),m) for m in ['public static function destroy<','public static function destroyArray<'])+'}',
   'NightmareVisionNoteSplash.hx': 'class NightmareVisionNoteSplash extends NoteSplash {public var player:Int;public function new(x=0,y=0,data=0,player=0,?owner:Dynamic){super(x,y,data);this.player=player;} }',
   'NoteSplash.hx':'''class NoteSplash extends FlxBasic {public var nightmareVisionSkin:Dynamic;public var animation=new TapAnimation();public function new(x=0,y=0,d=0,t='normal',skip=false){super();} __UPDATE__} class TapAnimation {public var curAnim:Null<{finished:Bool}>;public function new(){}public function play(n:String,f:Bool):Void curAnim={finished:false};}'''.replace('__UPDATE__',tap_update),
   'FlxBasic.hx':'''class FlxBasic implements flixel.util.IFlxDestroyable {public var cameras:Array<Dynamic>;public var destroys:Int=0;public function destroy():Void destroys++;public var exists:Bool=true;public var alive:Bool=true;public var alpha:Float=1;public var visible:Bool=true;public var revives:Int=0;public function new(){} public function update(elapsed:Float):Void {} public function revive():Void{exists=alive=true;revives++;}public function kill():Void{exists=alive=false;} }''',
   'Strumline.hx':'''class Strumline{} class StrumNote {public var ID:Int;public function new(i:Int)ID=i;}''',
   'Note.hx':'''class Note {var rgbValue:Dynamic;public var noteData:Int=5;public var tail:Array<Note>=[];public var playField:NightmareVisionPlayFieldView;public var sustainLength:Float=750;public var rgbGraphics(get,never):Dynamic;function get_rgbGraphics():Dynamic return rgbValue;public var sustainSplash:Dynamic;public function new(){rgbValue='note-rgb-view';} }''',
   'NightmareVisionSustainSplash.hx':'''import Strumline.StrumNote;class NightmareVisionSustainSplash extends FlxBasic {public var ctorArgs:Array<Int>;public var data:Int=0;public var completed:Bool=false;public var usedStrum:StrumNote;public var usedField:Dynamic;public var usedTime:Float;public var usedGraphics:Dynamic;public var isPlayer:Bool;public function new(x=0,y=0,data=0,player=0,?owner:Dynamic){super();ctorArgs=[x,y,data,player];} public function setupSplash(s:StrumNote,n:Note,t:Float,p:Bool,g:Dynamic,f:Dynamic):Void {usedStrum=s;usedField=f;usedTime=t;usedGraphics=g;isPlayer=p;data=n.noteData;} }''',
   'NightmareVisionPlayFieldView.hx':'''class NightmareVisionPlayFieldView {public var grpSusSplashes:Dynamic;public var grpNoteSplashes:Dynamic;public var splashLayer:Dynamic;public var ownedSplashLayer:Dynamic;public var displayedSplashLayer:Dynamic;public var _skin:Dynamic={sustainSplashes:true,applySplash:function(s:Dynamic,d:Int):Bool return true};public var members(get,never):Array<Strumline.StrumNote>;var receptors:Array<Strumline.StrumNote>;function get_members():Array<Strumline.StrumNote> return receptors;public var player:Int=2;public function new(){receptors=[for(i in 0...6)new Strumline.StrumNote(i)];grpSusSplashes=new flixel.group.FlxGroup.FlxTypedGroup<NightmareVisionSustainSplash>();}}''',
   'ClientPrefs.hx':'class ClientPrefs {public static var noteSplashType:String="Both";}',
   'Conductor.hx':'class Conductor {public static var stepCrotchet:Float=125;}',
   'PlayState.hx':'''class PlayState {public static var instance={scripts:{call:function(name:String,args:Array<Dynamic>):Void Main.callback(name,args)}};}''',
   'Host.hx':'''import flixel.group.FlxGroup.FlxTypedGroup;class Host {public var camHUD:Dynamic={};public var members:Array<Dynamic>=[];function remove(o:Dynamic,splice:Bool):Dynamic {members.remove(o);return o;}public var nightmareVisionPrefs={view:{noteSplashType:'Both'}};public var nightmareVisionConductor={stepCrotchet:125.0};public function new(){}function nightmareVisionSustainSplashOwner():Dynamic return null;function callNightmareVision(name:String,args:Array<Dynamic>):Void Main.callback(name,args);__BODY__}'''.replace('__BODY__',body),
   'Donor.hx':'import Strumline.StrumNote; class Donor extends NightmareVisionPlayFieldView {public function new(){super();}'+reference+'}',
   'Main.hx':r'''import flixel.group.FlxGroup.FlxTypedGroup;
class Main {
 static var traceEvents:Array<String>=[];
 public static function callback(name:String,args:Array<Dynamic>):Void {var splash:NightmareVisionSustainSplash=cast args[0];var note:Note=cast args[1];ok(name=='onSpawnSustainSplash'&&note.sustainSplash==null,'callback before head pointer publication');ok((cast splash.usedField.grpSusSplashes:FlxTypedGroup<NightmareVisionSustainSplash>).members.indexOf(splash)>=0,'callback after membership');traceEvents.push('callback:'+splash.data);}
 static function ok(v:Bool,m:String):Void if(!v)throw m;
 static function scenario(donor:Bool):String {
  var f=new Donor();var h=new Host();var group:FlxTypedGroup<NightmareVisionSustainSplash>=cast f.grpSusSplashes;traceEvents=[];group.onAdded=s->traceEvents.push('added:'+s.data);var n=new Note();n.playField=new NightmareVisionPlayFieldView();n.tail=[new Note()];
  var s:NightmareVisionSustainSplash=donor?f.spawnSusSplash(n,true):h.spawnNightmareVisionSustainSplash(f,n,true);
  ok(s==n.sustainSplash&&s.usedStrum==n.playField.members[5]&&s.usedField==f&&s.data==5&&s.usedTime==0.90625&&s.isPlayer,'source field selection/wider data/unused-time argument');
  ok(s.usedGraphics==n.rgbGraphics&&s.usedGraphics=='note-rgb-view','sustain splash receives Note getter RGB view');
  s.completed=true;s.kill();n.sustainSplash=null;var reused:NightmareVisionSustainSplash=donor?f.spawnSusSplash(n,false):h.spawnNightmareVisionSustainSplash(f,n,false);ok(reused==s&&s.completed&&s.exists&&s.alive&&s.revives==1&&group.length==1,'actual recycle keeps completed state/revives/no duplicateadd');
  n.tail=[];ok((donor?f.spawnSusSplash(n):h.spawnNightmareVisionSustainSplash(f,n))==null,'empty tail gate');n.tail=[new Note()];f._skin.sustainSplashes=false;ok((donor?f.spawnSusSplash(n):h.spawnNightmareVisionSustainSplash(f,n))==null,'skin gate');f._skin.sustainSplashes=true;n.playField.members[5]=null;ok((donor?f.spawnSusSplash(n):h.spawnNightmareVisionSustainSplash(f,n))==null,'null receptor gate');
  return traceEvents.join(',');
 }
 static function main(){ok(scenario(true)==scenario(false),'donor publication trace');var h=new Host();var f=new NightmareVisionPlayFieldView();var g:FlxTypedGroup<NightmareVisionSustainSplash>=cast f.grpSusSplashes;var a=new NightmareVisionSustainSplash();a.data=5;var b=new NightmareVisionSustainSplash();b.data=4;var c=new NightmareVisionSustainSplash();c.data=5;c.completed=true;g.add(a);g.add(b);g.add(c);h.hideNightmareVisionSustainSplashes(f,5);ok(!a.visible&&a.alpha==0&&a.alive&&!c.visible&&b.visible,'miss hides matching without kill');h.releaseNightmareVisionSustainSplashes(f,5);ok(!a.alive&&b.alive&&c.alive,'release completed gate');
  var seeded=new NightmareVisionPlayFieldView();h.initializeNightmareVisionFieldSplashes(seeded);var seededLayer:FlxTypedGroup<FlxBasic>=cast seeded.splashLayer;var seededSus:FlxTypedGroup<NightmareVisionSustainSplash>=cast seeded.grpSusSplashes;var seededTap:FlxTypedGroup<NightmareVisionNoteSplash>=cast seeded.grpNoteSplashes;
  ok(seededLayer.members[0]==seededSus&&seededLayer.members[1]==seededTap&&seededSus.length==1&&seededTap.length==1&&seededSus.members[0].alpha==0&&seededTap.members[0].alpha==0&&seededTap.members[0].player==seeded.player&&seeded.player==2&&seededSus.members[0].ctorArgs.join(',')=='0,0,0,0','source seeded constructor/layer order');
  var tapSeed=seededTap.members[0];tapSeed.update(0.016);ok(tapSeed.animation.curAnim==null&&tapSeed.alive&&tapSeed.exists&&tapSeed.alpha==0,'source no-animation seed survives actual update');var ordinaryTap=seededTap.recycle(NightmareVisionNoteSplash,()->new NightmareVisionNoteSplash());ok(ordinaryTap!=tapSeed&&ordinaryTap.alpha==1&&seededTap.length==2,'inert invisible seed cannot be recycled into invisible ordinary tap');ordinaryTap.animation.play('note0-0',true);ordinaryTap.update(0.016);ok(ordinaryTap.alive,'ordinary tap remains visible through live animation');ordinaryTap.animation.curAnim.finished=true;ordinaryTap.update(0.016);ok(!ordinaryTap.exists&&!ordinaryTap.alive,'actual finished tap retirement preserved');
  h.initializeNightmareVisionFieldSplashes(seeded);ok(seeded.splashLayer==seededLayer,'repeated binding does not reconstruct groups');seeded.displayedSplashLayer=seededLayer;h.members.push(seededLayer);var retainedSus=seededSus.members[0];var retainedTap=seededTap.members[0];h.destroyNightmareVisionFieldSplashes(seeded);ok(h.members.length==0&&retainedSus.destroys==1&&retainedTap.destroys==1&&seededLayer.destroys==1&&seeded.grpSusSplashes==null,'one owner teardown/removed display');h.destroyNightmareVisionFieldSplashes(seeded);ok(retainedSus.destroys==1,'repeated teardown safe');
  var borrowed=new FlxTypedGroup<FlxBasic>();var otherField=new NightmareVisionPlayFieldView();h.initializeNightmareVisionFieldSplashes(otherField);otherField.displayedSplashLayer=borrowed;h.members.push(borrowed);h.destroyNightmareVisionFieldSplashes(otherField);ok(borrowed.destroys==0&&h.members.indexOf(borrowed)>=0,'borrowed layer is not owned/destroyed or detached by this field');
  var layer=new FlxTypedGroup<FlxBasic>();layer.add(g);var taps=new FlxTypedGroup<FlxBasic>();layer.add(taps);f.splashLayer=layer;f.grpSusSplashes=new FlxTypedGroup<NightmareVisionSustainSplash>();ok(layer.members[0]==g&&layer.members[1]==taps,'public group replacement does not rewrite children');f.splashLayer=new FlxTypedGroup<FlxBasic>();ok(layer.members[0]==g&&f.splashLayer!=layer,'public layer pointer does not rewrite captured container');
 }
}'''}
  files['NightmareVisionLegacyNoteSplash.hx']='class NightmareVisionLegacyNoteSplash extends NightmareVisionNoteSplash {public function new(x=0,y=0,n=0,?owner:Dynamic){super(x,y,n,0,owner);}}'
  files['Host.hx']=files['Host.hx'].replace('class Host {', 'class Host {public var nightmareVisionLegacyFieldCameras=false;')
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   work=Path(tmp)
   for name,s in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',tmp,'--run','Main'],capture_output=True,text=True,timeout=35,cwd=ROOT)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   env=os.environ.copy();env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['NEKOPATH']=str(ROOT/'.tools/neko');env['PATH']=str(ROOT/'.tools/haxe')+os.pathsep+str(ROOT/'.tools/neko')+os.pathsep+env.get('PATH','')
   cpp=work/'cpp'
   result=subprocess.run([*HAXE_COMMAND,'-cp',tmp,'-main','Main','-cpp',str(cpp),'-D','no-compilation'],capture_output=True,text=True,timeout=35,cwd=ROOT,env=env)
   self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-4000:])
   generated=(cpp/'src/Host.cpp').read_text(encoding='utf-8')
   start=generated.index('Host_obj::spawnNightmareVisionSustainSplash(')
   spawn=generated[start:generated.index('HX_DEFINE_DYNAMIC_FUNC3',start)]
   self.assertIn('noteField->get_members()',spawn)
   self.assertNotIn('__Field(HX_("members"',spawn)
   self.assertIn('get_rgbGraphics()',spawn)
   self.assertNotIn('__Field(HX_("rgbGraphics"',spawn)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)

 def test_live_skin_scale_uses_source_float_on_static_cpp_target(self):
  ps=(ROOT/'source/PlayState.hx').read_text(encoding='utf-8')
  change=method(ps,'function nightmareVisionChangeFieldSkin(')
  body=method(change,'if (field.grpSusSplashes != null)')
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   work=Path(tmp)
   files={
    'Main.hx': 'import flixel.group.FlxGroup.FlxTypedGroup; class Skin {public var susSplashScale:Float=2;public var inEngineColoring=true;public function new(){}} class Field {public var grpSusSplashes:Dynamic;public function new(){}} class Main {static function change(field:Field,skin:Skin):Void '+body+' static function main(){var f=new Field();var s=new NightmareVisionSustainSplash();var g=new FlxTypedGroup<NightmareVisionSustainSplash>();g.members=[s];f.grpSusSplashes=g;change(f,new Skin());if(s.scale.x!=2||s.baseScale.x!=2||!s.rgbGraphics.enabled)throw "live skin scale";}}',
    'NightmareVisionSustainSplash.hx':'class Point {public var x:Float=1;public var y:Float=1;public function new(){}public function set(a:Float,b:Float){x=a;y=b;}public function copyFrom(p:Point){x=p.x;y=p.y;}} class NightmareVisionSustainSplash {public var alive=true;public var scale=new Point();public var baseScale=new Point();public var rgbGraphics={enabled:false};public function new(){}}',
    'flixel/group/FlxGroup.hx':'package flixel.group;class FlxTypedGroup<T> {public var members:Array<T>=[];public function new(){}}'}
   for name,content in files.items():
    path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf-8')
   env=os.environ.copy();env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['NEKOPATH']=str(ROOT/'.tools/neko');env['PATH']=str(ROOT/'.tools/haxe')+os.pathsep+str(ROOT/'.tools/neko')+os.pathsep+env.get('PATH','')
   for target in [['--interp'],['-cpp',str(work/'cpp'),'-D','no-compilation']]:
    result=subprocess.run([*HAXE_COMMAND,'-cp',tmp,'-main','Main',*target],cwd=ROOT,env=env,capture_output=True,text=True,timeout=35)
    self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-4000:])

 def test_owner_skin_registry_matches_pinned_source_id_and_fallback_rules(self):
  source=(ROOT.parent/'fnf_sources/NightmareVision/source/funkin/utils/NoteUtil.hx').read_text(encoding='utf-8')
  resolver=method(source,'public static function getSkinFromID(')
  fixture=r'''import NightmareVisionNoteSkin as NoteSkin;
class DonorResolver {public static var noteskins:Array<NoteSkin>=[];__RESOLVER__}
class Main {static function ok(v:Bool,m:String):Void if(!v)throw m;static function main(){
 var r=new NightmareVisionNoteSkinRegistry(()->new NoteSkin('default',4,0));
 var first=new NoteSkin('a',6,9);var second=new NoteSkin('b',3,25);r.noteskins=[first,second];DonorResolver.noteskins=r.noteskins;
 for(id in [0,1,2,9,25,99])ok(r.getSkinFromID(id)==DonorResolver.getSkinFromID(id),'skin.ID lookup/first fallback independent of array index');
 var replacement=new NoteSkin('changed',5,40);r.noteskins[0]=replacement;ok(r.getSkinFromID(9)==replacement&&r.getSkinFromID(25)==second,'source live change/player-slot mutation');
 r.noteskins=[second];DonorResolver.noteskins=r.noteskins;ok(r.getSkinFromID(25)==second&&r.getSkinFromID(0)==DonorResolver.getSkinFromID(0),'public array replacement/current lookup');
 r.noteskins=[];DonorResolver.noteskins=[];var fallback=r.getSkinFromID(8);var donor=DonorResolver.getSkinFromID(8);ok(fallback.name==donor.name&&fallback.keys==4&&fallback.ID==0&&r.getSkinFromID(8)!=fallback,'empty fallback fresh source default');
 r.noteskins=[null,second];DonorResolver.noteskins=r.noteskins;var hostFailed=false;var donorFailed=false;try r.getSkinFromID(25)catch(_:Dynamic)hostFailed=true;try DonorResolver.getSkinFromID(25)catch(_:Dynamic)donorFailed=true;ok(hostFailed&&donorFailed,'source null list entry remains invalid');
 r.noteskins=[second];var held=r.noteskins;r.destroy();ok(held.length==0,'owner registry teardown releases array references');
 }}'''.replace('__RESOLVER__',resolver)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   work=Path(tmp)
   (work/'Main.hx').write_text(fixture,encoding='utf-8')
   (work/'NightmareVisionNoteSkin.hx').write_text('class NightmareVisionNoteSkin {public var name:String;public var keys:Int;public var ID:Int;public function new(n:String,k:Int,id:Int){name=n;keys=k;ID=id;}}',encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',tmp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  ps=(ROOT/'source/PlayState.hx').read_text(encoding='utf-8')
  constructor=method(ps,'public function createNightmareVisionSourceField(')
  injected=constructor[constructor.index('if (spec.skinInput != null)'):constructor.index('} else')]
  self.assertNotIn('noteskins.push',injected)
  self.assertIn('noteskins.push(skin)',constructor)
  self.assertIn('noteskins.push(field._skin)',method(ps,'function createNightmareVisionDefaultField('))
  self.assertIn('noteskins[field.player] = skin',method(ps,'function nightmareVisionChangeFieldSkin('))
  self.assertIn('nightmareVisionSourceSkinRegistry().getSkinFromID',method(ps,'function nightmareVisionSustainSplashOwner('))
