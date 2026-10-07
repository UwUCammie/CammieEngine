"""Actual typed Stage and source base behavior against complete immutable donor bodies."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from nv_stage_fixture_support import nv_stage_fixture_files
ROOT=Path(__file__).resolve().parents[2]
MAIN=r'''
import flixel.FlxSprite;
class Main {
 static function ok(b:Bool,s:String):Void if(!b)throw s;
 static function stage(host:Bool,io:StageIO):Dynamic {StageIO.current=io;return host?new NightmareVisionStage("custom",io.owner()):new DonorStage("custom");}
 static function snapshot(g:Dynamic,io:StageIO):String {var values:Array<Dynamic>=[];for(c in (cast g.members:Array<FlxSprite>)){var item:Array<Dynamic>=[c.width,c.height,c.alpha,c.angle,c.color,c.blend,c.flipX,c.flipY,c.scale.x,c.scale.y,c.x,c.y,c.scrollFactor.x,c.zIndex,c.antialiasing,c.animation.curAnim==null?"":c.animation.curAnim.name];values.push(item);}return haxe.Json.stringify({values:values,warn:io.warn,registered:g.objects.keys().hasNext(),boppers:g.boppers.length});}
 static function run(host:Bool):String {var io=new StageIO();io.data.stageObjects=[{id:"obj",asset:"alphabet",alpha:.4,angle:15,flipX:true,flipY:false,blend:" ADD ",colour:"0x8ABBCCDD",position:[10,20],scale:[.5],scrollFactor:[.2],zIndex:7,antialiasing:true,animations:[{anim:"idle",name:"A bold",fps:24,loop:true,offsets:[3,4]}]},{id:"GF",highQuality:true,dance_every:0},{id:"obj",customInstance:"Plain",advancedCalls:[{method:"missing"},{method:"tick",args:[]}],setProperties:[{property:"bad",value:1},{property:"alpha",value:.7}]}];
  var g=stage(host,io);g.buildStage();var first=snapshot(g,io);ok(g.members.length==3&&g.objects.get("obj")==g.members[0]&&!g.objects.exists("GF")&&g.boppers.length==0,"source member/map/reserved/boppers behavior");g.buildStage();ok(g.members.length==6&&g.objects.get("obj")==g.members[0],"repeated build no clearing");return first+snapshot(g,io);}
 static function scripts(host:Bool,code:String):String {var io=new StageIO();io.data.stageObjects=[{id:"obj",alpha:.4}];io.source=code;io.scriptFiles.set("stages/custom",true);var g=stage(host,io);g.buildStage();var group=new NightmareVisionScriptGroup();var result=g.runScript(group);ok(group.members.length==0,"Stage loader doesn't register before onLoad");if(result){ok(io.shared==group.sharedFields&&g.script==io.loaded,"real module/shared map identity");ok(io.loaded.get("stage")==g&&Reflect.isFunction(io.loaded.get("add"))&&io.loaded.get("obj")==g.objects.get("obj"),"postexecute module source bindings");group.addScript(g.script);ok(group.members[0]==g.script,"caller registers same module after runScript");}else ok(g.script==null&&io.loaded.released,"failed real module destroyed/null");return haxe.Json.stringify({result:result,calls:io.calls,warn:io.warn});}
 static function main(){ok(run(false)==run(true),"complete Stage builder source order");
  for(code in ["io.tick(); function onLoad(){io.tick();}","throw 'top failure';","function broken( {"])ok(scripts(false,code)==scripts(true,code),"real module source execution/onLoad/failure phase");
  var staleIO=new StageIO();staleIO.data.stageObjects=[{asset:"atlas"}];var retained:NightmareVisionStage=cast stage(true,staleIO);staleIO.active=false;var beforeIO=staleIO.calls.length;var rejected=false;try retained.buildStage()catch(e:Dynamic)rejected=e=="captured stage lease released";ok(rejected&&staleIO.calls.length==beforeIO&&retained.members.length==0,"retained unmounted Stage rejects before provider capture/atlas IO");
  var io=new StageIO();var a:NightmareVisionStage=cast stage(true,io);var b=new NightmareVisionStage("other",io.owner());var child=new FlxSprite();a.add(child);ok(child.container==a&&a.members[0]==child,"actual native container identity");b.add(child);ok(child.container==b&&a.members[0]==null&&b.members[0]==child,"actual native container transfer removes prior owner");b.destroy();ok(child.destroyed==1&&child.container==null,"native child teardown once");
 }
}
'''
LEAF=r'''
import flixel.FlxSprite;import flixel.math.FlxPoint;
class Main {
 static function ok(b:Bool,s:String):Void if(!b)throw s;
 static function state(s:Dynamic):String {var p:flixel.FlxSprite=cast s;var pos=p.getScreenPosition();return haxe.Json.stringify({x:pos.x,y:pos.y,offsetX:s.animOffset.x,offsetY:s.animOffset.y,scale:p.scale.x,frames:p.frames.frames.length,anim:s.getAnimName(),flip:p.flipX,base:s.baseScale.x});}
 static function run(host:Bool,animated:Bool):String {
  var io=new StageIO();io.animated=animated;io.gpu=animated;
  var b:Dynamic=host?new NightmareVisionBopper(10,20,2,io.paths):new DonorBopper(10,20,2);
  ok(Reflect.getProperty(b,"animateAtlas")==null&&b.canDance&&b.alternatingDance==null,"source Bopper defaults");
  b.loadAtlas(" atlas ");b.addAnimByPrefix("idle","A bold",17,true,false,false);b.addAnimByIndices("chosen","A bold",[0,1],23,false,true,false);b.addOffset("idle",7,9);b.playAnim("idle",true);b.spriteOffset.set(2,3);b.scale.set(2,3);b.angle=35;b.skew.set(12,17);var out=[state(b)];
  if(animated)ok(io.frames.parent.bitmap.disposed==1&&!io.frames.parent.persist&&!io.tracked.exists(io.frames.parent.key)&&!io.paths.tempAtlasFramesCache.exists(haxe.io.Path.withoutExtension(io.frames.parent.key)),"source Animate GPU/cache/persist effects");
  ok(animated?(Reflect.getProperty(b,"animateAtlas")==b):Reflect.getProperty(b,"animateAtlas")==null,"source animateAtlas only library host="+host+" animated="+animated+" library="+Std.isOfType(b.library,animate.FlxAnimateFrames));
  if(animated){var nativeAnim:IconAnimation=b.animation;var library:animate.FlxAnimateFrames=cast b.library;library.addedCollections.push({dictionary:["extra"=>true]});b.addAnimByPrefix("labels","label",24,true);b.addAnimByPrefix("symbols","symbol",24,true);b.addAnimByPrefix("merged","extra",24,true);b.addAnimByIndices("labelI","label",[1,0],12,false);b.addAnimByIndices("symbolI","symbol",[1],12,false);ok(nativeAnim.methodCalls.join("|")=="prefix:label|symbol:symbol|symbol:extra|label-indices:label:1,0|symbol-indices:symbol:1","full source label/symbol/merged/indices dispatch");}
  var seen=0;var nativeSprite:animate.FlxAnimate=cast b;ok(b.onAnimationFinish!=nativeSprite.animation.onFinish,"independent forwarded signal");b.onAnimationFinish.add(function(n){seen++;});nativeSprite.animation.onFinish.dispatch("idle");ok(seen==1,"native finish forwarding");
  b.correctFlippedOffsets=true;b.flipX=true;b.setOffsets("idle");out.push(state(b));
  b.playAnim("idle-missing-suffix",true);ok(b.getAnimName()=="idle","source recursive suffix correction");b.addAnimByPrefix("danceLeft","A bold");b.addAnimByPrefix("danceRight","A bold");b.alternatingDance=null;b.dance();ok(b.getAnimName()=="danceRight","source first alternating dance");b.dance();ok(b.getAnimName()=="danceLeft","source next alternating dance");
  b.canDance=false;var last=b.getAnimName();b.dance();ok(b.getAnimName()==last,"source dance suppression");b.canDance=true;b.alternatingDance=false;b.onBeatHit(2);ok(b.getAnimName()=="idle","beat guard and native animation");
  var clone:Dynamic=b.clone();ok(clone.frames==b.frames&&clone.animOffsets.get("idle")==b.animOffsets.get("idle"),"source clone borrows frames/offset arrays");ok(clone.scale.x==b.scale.x&&clone.baseScale.x==b.baseScale.x&&clone.spriteOffset.x==b.spriteOffset.x&&clone.animOffset.x==0,"source clone copies only specified fields");out.push(state(clone));
  io.empty=true;var before=nativeSprite.frames;b.loadAtlas("none");ok(nativeSprite.frames==before,"no found atlas retains prior frames");
  var base=b.baseScale,point=b.spriteOffset,anim=b.animOffset;b.destroy();ok(base.puts==0&&point.puts==1&&anim.puts==1,"source baseScale cleanup omission retained; owned offsets returned");return out.join("|");
 }
 static function main(){for(animated in [false,true])ok(run(false,animated)==run(true,animated),"full source base/Bopper comparisons "+animated);
  var io=new StageIO();var b=new NightmareVisionBopper(0,0,0,io.paths);b.onBeatHit(0);b.loadAtlas("atlas");b.addAnimByPrefix("idle","A bold");b.playAnim("idle");b.onBeatHit(0);ok(b.getAnimName()=="idle","source eval zero modulo retains animation; CPP preserves native hx::Mod error");
  var provider:NightmareVisionSpriteOwner=cast Reflect.field(b,"__nightmareVisionSpriteOwner");provider.release();NightmareVisionSpriteRegistry.enterSession("different-primary");ok(NightmareVisionSpriteRegistry.peek(io.paths.root)==null,"primaryexit removed registry cell");var borrowed=b.clone();ok(NightmareVisionSpriteRegistry.peek(io.paths.root)==null,"clone never reconstructs old owner registry");var before=io.calls.length;var stale=false;try b.loadAtlas("after-release")catch(e:Dynamic)stale=Std.string(e).indexOf("released")>=0;ok(stale&&io.calls.length==before,"released owner check before any atlas/metadata IO");var cloneStale=false;try borrowed.loadAtlas("cloned-after-release")catch(e:Dynamic)cloneStale=Std.string(e).indexOf("released")>=0;ok(cloneStale&&io.calls.length==before,"clone borrows released provider; no registry recapture/IO");
 }
}
'''
EDGE=r'''
import flixel.FlxBasic;import flixel.group.FlxContainer.FlxTypedContainer;
class Main {
 static function ok(b:Bool,s:String):Void if(!b)throw s;
 static function stage(host:Bool,io:StageIO):Dynamic {StageIO.current=io;return host?new NightmareVisionStage("custom",io.owner()):new DonorStage("custom");}
 static function run(host:Bool):String {
  var io=new StageIO();io.data.stageObjects=[{id:"advanced",customInstance:"Plain",advancedCalls:[{method:"explode"}],setProperties:[{property:"alpha",value:.8}]}];var g=stage(host,io);var registered:Map<String,flixel.FlxSprite>=cast g.objects;var error:Dynamic=null;try g.buildStage()catch(e:Dynamic)error=e;ok(error=="advanced failure"&&g.objects.exists("advanced")&&g.members.length==0&&registered.get("advanced").alpha==1,"advanced throw retains registration but never properties/add");
  io.data.stageObjects=[{id:"first",customInstance:"Plain"}];var parent:FlxTypedContainer<FlxBasic>=cast g;var called=0;parent.added=function(c){called++;ok(registered.get(called==1?"first":"live")==c,"map precedes actual memberAdded");if(called==1)io.data.stageObjects.push({id:"live",alpha:.25});};g.buildStage();ok(called==2&&g.members.length==2&&g.objects.exists("live"),"actual member callback append joins source live array iteration");
  io.source="function onLoad(){io.tick();}";io.scriptFiles.set("data/stages/custom/script",true);var group=new NightmareVisionScriptGroup();ok(g.runScript(group),"successful source script");var old=g.script;io.scriptFiles.clear();ok(g.runScript(group)&&g.script==old&&!old.released,"no path found retains old script/true source return");io.scriptFiles.set("data/stages/custom/script",true);io.source="function onLoad(){io.tick();}";g.runScript(group);ok(g.script!=old&&!old.released,"replace reference does not destroy previous module");
  var data=g.stageData;g.curStage="later";data.defaultZoom=.5;ok(Reflect.getProperty(g,"defaultZoom")==.5&&g.stageData==data,"read-only derived zoom/live stageData; name write no reload");
  return haxe.Json.stringify({calls:called,warn:io.warn,members:g.members.length,objects:g.objects.exists("live"),oldLive:!old.released});
 }
 static function main(){ok(run(false)==run(true),"source partial mutation/script reuse contracts");}
}
'''
class NVStageContractTest(unittest.TestCase):
 def test_complete_builder_script_and_real_container_contracts(self):
  self.run_fixture(MAIN)
 def test_actual_funkin_sprite_and_bopper_source_contracts(self):
  self.run_fixture(LEAF)
 def test_partial_state_live_mutation_and_script_reuse(self):
  self.run_fixture(EDGE)
 def run_fixture(self, main):
  files=nv_stage_fixture_files();files['Main.hx']=main
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   for n,s in files.items():
    p=Path(tmp)/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
   env=os.environ.copy();env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['NEKOPATH']=str(ROOT/'.tools/neko');env['PATH']=str(ROOT/'.tools/haxe')+os.pathsep+env['NEKOPATH']+os.pathsep+env.get('PATH','')
   cmd=[*HAXE_COMMAND,'-D','flixel','-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',tmp,'-main','Main']
   for target in [['--interp'],['-cpp',str(Path(tmp)/'cpp'),'-D','no-compilation']]:
    r=subprocess.run(cmd+target,cwd=ROOT,env=env,capture_output=True,text=True,timeout=40);self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-6000:])
   for class_name,parent in [('NightmareVisionStage','flixel::group::FlxTypedContainer_obj'),('NightmareVisionFunkinSprite','animate::FlxAnimate_obj'),('NightmareVisionBopper','NightmareVisionFunkinSprite_obj')]:
    header=Path(tmp)/'cpp/include'/f'{class_name}.h'
    if header.exists():self.assertIn(f'typedef  ::{parent} super;',header.read_text(encoding='utf-8'))
   base=Path(tmp)/'cpp/src/NightmareVisionFunkinSprite.cpp'
   if base.exists():
    code=base.read_text(encoding='utf-8')
    for name in ['animOffsets','spriteOffset','animOffset','baseScale','getAnimName','addOffset','addAnimByIndices','clone']:self.assertIn('"'+name+'"',code)
   for name in ['NightmareVisionBopper','DonorBopper']:
    p=Path(tmp)/'cpp/src'/f'{name}.cpp'
    if p.exists():self.assertIn('::hx::Mod(beat,this->danceEveryNumBeats)',p.read_text(encoding='utf-8'))
if __name__=='__main__':unittest.main()
