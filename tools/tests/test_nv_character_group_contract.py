"""Actual source group placement/cache transaction versus the immutable donor."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from nv_character_group_fixture_support import nv_character_group_fixture_files
ROOT=Path(__file__).resolve().parents[2]
MAIN=r'''
import flixel.math.FlxPoint;
class Main {
 static function ok(b:Bool,s:String):Void if(!b)throw s;
 static function make(host:Bool,f:FixtureOwner,t:Int=1):Dynamic {PlayState.instance=f.scene;PlayState.construct=f.construct;return host?new NightmareVisionCharacterGroup(10,20,cast t,f.owner()):new DonorCharacterGroup(10,20,cast t);}
 static function snap(g:Dynamic,c:Character):String return haxe.Json.stringify([c.x,c.y,c.alpha,c.scrollFactor.x,c.danceEveryNumBeats,g.members.length,g.map.get(c.curCharacter)==c,g.parent==c]);
 static function run(host:Bool,n:Int):String {
  var f=new FixtureOwner();var g=make(host,f);var c=new Character(1,2,n==1?"gf-alt":"dad");var out=[];
  g.addChar(null);g.startPos(null);g.addChar(c);out.push(snap(g,c));g.startPos(c);out.push(snap(g,c));g.addChar(c);out.push(snap(g,c));ok(g.parent==null,"addChar never assigns parent");
  var typed:flixel.group.FlxSpriteGroup=cast g;typed.x+=7;typed.y+=9;typed.scale.set(2,3);out.push(snap(g,c));
  g.parent=c;f.scene.playFields.members=[new NightmareVisionPlayFieldView(0,c),new NightmareVisionPlayFieldView(1,new Character())];
  var created:Character=g.addToList("other");ok(g.addToList("other")==created&&f.created==1,"nonnull cached reuse");out.push(snap(g,created));
  var current:Character=g.change("other");ok(current==created&&f.scene.playFields.members[0].owner==current&&f.scene.playFields.members[1].owner!=current,"snapshot field transfer");out.push(snap(g,c));out.push(snap(g,created));
  var map:Map<String,Character>=new Map();g.map=map;map.set("other",created);ok(g.change("other")==created,"same-name no map mutation");
  typed.remove(c);out.push(snap(g,c));typed.clear();ok(g.map==map&&g.parent==created&&created.destroyed==0,"clear retains source references without destroy");
  return out.join("|");
 }
 static function failcase(host:Bool,n:Int):String {
  var f=new FixtureOwner();var g=make(host,f);var old=new Character(0,0,"dad");old.alpha=.6;g.addChar(old);g.parent=old;
  var next=new Character(0,0,"next");g.map.set("next",next);f.scene.playFields.members=[new NightmareVisionPlayFieldView(0,old)];
  switch(n){case 0:g.parent=null;case 1:g.map.set("next",null);case 2:f.scene.playFields.members=[null];case 3:f.scene=null;PlayState.instance=null;case 4:f.resolved="resolved";g.map.remove("next");case 5:g.map=null;case 6:old.positionArray=null;case 7:f.failure={message:"original constructor"};g.map.remove("next");case 8:old.curCharacter="gf";f.scene.gfPosition=null;}
  var caught:Dynamic=null;try {if(n==6||n==8)g.startPos(old);else g.change("next");}catch(e:Dynamic)caught=e;
  ok(caught!=null,"failure phase "+n);if(n==7)ok(caught==f.failure,"constructor error identity");
  return haxe.Json.stringify([old.alpha,g.parent==null,g.parent==old,g.parent==next,next.alpha,f.created]);
 }
 static function main(){for(n in 0...2)ok(run(false,n)==run(true,n),"full donor placement/cache "+n);for(n in 0...9)ok(failcase(false,n)==failcase(true,n),"partial donor failure state "+n);
  for(id in [-1,0,1,4]){var states=[];for(host in [false,true]){var f=new FixtureOwner();var g=make(host,f);var c=new Character();g.parent=c;g.map.set("next",new Character(0,0,"next"));var field=new NightmareVisionPlayFieldView(id,c);f.scene.playFields.members=[field];var caught=false;try g.change("next")catch(_:Dynamic)caught=true;states.push(Std.string(caught)+":"+Std.string(field.owner==g.parent));}ok(states[0]==states[1],"native direct Bool snapshot index "+id);}
  for(host in [false,true]){
   var f=new FixtureOwner();var g=make(host,f);var old=new Character(0,0,"dad");g.parent=old;var a=new NightmareVisionPlayFieldView(0,old),b=new NightmareVisionPlayFieldView(1,new Character());f.scene.playFields.members=[a,b];var alternate=new Character(0,0,"alternate");alternate.alpha=.35;
   f.during=function(){g.parent=alternate;f.scene.playFields.members=[b,a];b.ID=0;a.ID=1;};var next:Character=g.change("next");ok(alternate.alpha==.0001&&old.alpha==1&&next.alpha==.35,"live parent read after constructor");ok(b.owner==next&&a.owner==old,"earlier positional flags indexed by current IDs");
   var typed:flixel.group.FlxSpriteGroup=cast g;var seen=false;typed.group.added=function(c){var char:Character=cast c;var cache:Map<String,Character>=cast g.map;seen=cache.get(char.curCharacter)==char;};g.addChar(new Character(0,0,"publication"));ok(seen,"resolved map published before actual memberAdded");
   f.resolved="resolved";var first:Character=g.addToList("missing");var second:Character=g.addToList("missing");var resolvedMap:Map<String,Character>=cast g.map;ok(first!=second&&resolvedMap.get("resolved")==second&&!resolvedMap.exists("missing"),"requested/resolved cache mismatch unchanged");
   var same=next;g.parent=same;f.scene=null;PlayState.instance=null;ok(g.change("next")==same,"same-name does not require scene");var gf=new Character(4,5,"gf-empty");g.startPos(gf);ok(gf.x==3&&gf.y==5&&gf.scrollFactor.x==.95,"null scene optional GF fallback");
  }
  var dependency=new NightmareVisionSpriteOwner(function(p)return new flixel.graphics.frames.FlxAtlasFrames());var fDestroy=new FixtureOwner();var borrowed=fDestroy.owner();borrowed.spriteOwner=dependency;var dying=new NightmareVisionCharacterGroup(0,0,cast 0,borrowed);var actor=new Character();var original={reason:"child destroy"};actor.observedDestroy=function(){ok(Reflect.field(dying,"owner")!=null,"owner retained through base child cleanup");throw original;};dying.addChar(actor);var thrown:Dynamic=null;try dying.destroy()catch(e:Dynamic)thrown=e;ok(thrown==original&&Reflect.field(dying,"owner")==null&&Reflect.field(dying,"__nightmareVisionSpriteOwner")==null,"destruction error identity and borrowed references cleared");ok(dependency.atlasFrames("still-live")!=null,"group never releases provider");
  var f=new FixtureOwner();var g:NightmareVisionCharacterGroup=cast make(true,f,0);ok(g.type==0&&!g.gfCheck,"source constructor type");g.type=cast 2;var c=g.addToList("bf");ok(!c.isPlayer&&!g.gfCheck,"type write no gfCheck recompute");g.gfCheck=true;g.map.set("null",null);ok(g.addToList("null")!=null,"nonnull get cache check");var map=g.map;g.parent=c;var count=0;c.observedDestroy=function(){count++;};g.destroy();ok(count==1&&g.map==map&&g.parent==c,"group sole member destruction; source map/parent survive");
 }
}
'''
class NVCharacterGroupContractTest(unittest.TestCase):
 def test_actual_group_matches_full_donor_and_native_indexing(self):
  files=nv_character_group_fixture_files();files['Main.hx']=MAIN
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   for name,text in files.items():
    p=Path(tmp)/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
   env=os.environ.copy();env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['NEKOPATH']=str(ROOT/'.tools/neko');env['PATH']=str(ROOT/'.tools/haxe')+os.pathsep+str(ROOT/'.tools/neko')+os.pathsep+env.get('PATH','')
   cmd=[*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',tmp,'-main','Main']
   for target in [['--interp'],['-cpp',str(Path(tmp)/'cpp'),'-D','no-compilation']]:
    r=subprocess.run(cmd+target,cwd=ROOT,env=env,capture_output=True,text=True,timeout=40);self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-5000:])
   cpp=(Path(tmp)/'cpp/src/NightmareVisionCharacterGroup.cpp').read_text(encoding='utf-8')
   for name in ['parent','map','type','gfCheck','addChar','addToList','change','startPos']:self.assertIn('"'+name+'"',cpp)
   self.assertIn('checkFields->__get(field1->ID)',cpp)
   donor=(Path(tmp)/'cpp/src/DonorCharacterGroup.cpp').read_text(encoding='utf-8')
   self.assertIn('checkFields->__get(field1->ID)',donor)
   header=(Path(tmp)/'cpp/include/NightmareVisionCharacterGroup.h').read_text(encoding='utf-8')
   self.assertIn('typedef  ::flixel::group::FlxTypedSpriteGroup_obj super;',header)
   self.assertIn('void addChar(',header)
if __name__=='__main__':unittest.main()
