"""Targeted real methods versus actual immutable NV macro-generated references."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from nv_sprite_macro_fixture_support import nv_sprite_macro_fixture_files

ROOT = Path(__file__).resolve().parents[2]
MAIN = r'''
import flixel.FlxSprite;import flixel.FlxObject;import flixel.util.FlxAxes;
class Main {
 static function ok(v:Bool,m:String)if(!v)throw m;
 static function snap(s:FlxSprite):String return haxe.Json.stringify([s.x,s.y,s.width,s.height,s.frameWidth,s.frameHeight,s.offset.x,s.offset.y,s.scale.x,s.scale.y,s.color,s.active,s.makes,s.hitboxes,s.lastKey,s.animation.name]);
 static function main(){
  var atlas=new flixel.graphics.frames.FlxAtlasFrames();var paths:Array<String>=[];
  var load=function(p:String){paths.push(p);return atlas;};funkin.Paths.loader=load;var owner=new NightmareVisionSpriteOwner(load);
  var d=new ReferenceSprite();var h=new TargetSprite();ok(Reflect.fields(h).indexOf('__nightmareVisionSpriteOwner')>=0 && Reflect.field(h,'__nightmareVisionSpriteOwner')==null,'nullable cell enumerated before binding');NightmareVisionSpriteMethods.bind(h,null);NightmareVisionSpriteMethods.bind(h,owner);
  for(name in ['loadFromSheet','loadAtlasFrames','makeScaledGraphic','setScale','centerOnObject'])ok(Type.getInstanceFields(TargetSprite).indexOf(name)>=0&&Reflect.isFunction(Reflect.field(h,name)),'actual exported method '+name);
  ok(d.loadFromSheet('default','A bold')==d && h.loadFromSheet('default','A bold')==h && snap(d)==snap(h),'loader defaults and receiver');
  var single=new flixel.graphics.frames.FlxAtlasFrames();single.frames=single.frames.slice(0,1);
  funkin.Paths.loader=function(p)return single;owner.rebind(function(p)return single);
  var firstName=single.frames[0].name;d.loadFromSheet('single',firstName);h.loadFromSheet('single',firstName);ok(!h.active&&snap(d)==snap(h),'single disables');
  funkin.Paths.loader=load;owner.rebind(load);d.loadFromSheet('multi','A bold',17,false);h.loadFromSheet('multi','A bold',17,false);ok(!h.active&&snap(d)==snap(h),'multi does not reactivate');
  d.loadFromSheet('absent','__missing__');h.loadFromSheet('absent','__missing__');ok(!h.active&&snap(d)==snap(h),'missing animation');
  funkin.Paths.loader=function(p)throw 'atlas-failure';owner.rebind(function(p)throw 'atlas-failure');var oldFrames=h.frames;var de='';var he='';
  try d.loadFromSheet('broken','A bold')catch(e:Dynamic)de=Std.string(e);try h.loadFromSheet('broken','A bold')catch(e:Dynamic)he=Std.string(e);ok(de=='atlas-failure'&&he==de&&h.frames==oldFrames&&snap(d)==snap(h),'atlas failure before frame assignment');funkin.Paths.loader=load;owner.rebind(load);
  var hit=h.hitboxes;ok(d.loadAtlasFrames(atlas)==d&&h.loadAtlasFrames(atlas)==h&&h.frames==atlas&&snap(d)==snap(h)&&h.hitboxes==hit,'borrowed frames only assignment');
  for(color in [-1,0x80402010,0])for(pair in [[12.5,7.25],[0.,-3.],[1.,1.]]){
   ok(d.makeScaledGraphic(pair[0],pair[1],color)==d&&h.makeScaledGraphic(pair[0],pair[1],color)==h&&snap(d)==snap(h),'solid geometry/key');
  }
  d.makeScaledGraphic(3,4);h.makeScaledGraphic(3,4);ok(snap(d)==snap(h)&&h.lastKey=='solid#FFFFFFFF','default ARGB key');
  hit=h.hitboxes;ok(d.setScale(2.5,-1.2,false)==d&&h.setScale(2.5,-1.2,false)==h&&snap(d)==snap(h)&&h.hitboxes==hit,'no optional hitbox');
  d.setScale(.7,3.1);h.setScale(.7,3.1);ok(snap(d)==snap(h),'virtual hitbox default');
  var target=new FlxObject(71,83);target.width=211;target.height=149;
  for(axis in [FlxAxes.X,FlxAxes.Y,FlxAxes.XY,FlxAxes.NONE]){d.centerOnObject(target,axis);ok(h.centerOnObject(target,axis)==h&&snap(d)==snap(h),'axes center');}
  d.centerOnObject(null,FlxAxes.NONE);h.centerOnObject(null,FlxAxes.NONE);ok(snap(d)==snap(h),'NONE avoids null dereference');
  de='';he='';try d.centerOnObject(null)catch(e:Dynamic)de=Std.string(e);try h.centerOnObject(null)catch(e:Dynamic)he=Std.string(e);ok(de!=''&&he!='','null target source error');
  var child=new TargetChild();NightmareVisionSpriteMethods.bind(child,owner);ok(child.loadAtlasFrames(atlas)==child,'compatible inherited methods/cell');
  var gd=new ReferenceGroup();var gh=new TargetGroup();NightmareVisionSpriteMethods.bind(gh,owner);
  var cd=new FlxSprite(3,7);var ch=new FlxSprite(3,7);gd.add(cd);gh.add(ch);
  ok(gd.makeScaledGraphic(2,4)==gd&&gh.makeScaledGraphic(2,4)==gh&&gd.makes==0&&gh.makes==0&&snap(cd)==snap(ch)&&ch.scale.x==2&&ch.scale.y==4,'actual group makeGraphic override and callback scale');
  ok(gd.loadAtlasFrames(atlas)==gd&&gh.loadAtlasFrames(atlas)==gh&&gd.frames==null&&gh.frames==null,'group frame setter returns without adopting');
  gd.loadFromSheet('group','A bold');gh.loadFromSheet('group','A bold');ok(!gh.active&&snap(gd)==snap(gh),'group loader virtual frame setter');
  var hd=new HitboxReference();var hh=new HitboxTarget();hd.setScale(2,3);hh.setScale(2,3);ok(hd.calls==hh.calls&&hh.calls==1&&hh.offset.x==37,'custom virtual hitbox');
  for(mode in 0...3){var own=new DestroyOwn();NightmareVisionSpriteMethods.bind(own,owner);own.early=mode==1;var original:Dynamic={reason:'own-error'};own.failure=mode==2?original:null;var caught:Dynamic=null;try own.destroy()catch(e:Dynamic)caught=e;ok(own.during&&Reflect.field(own,'__nightmareVisionSpriteOwner')==null,'own callback/nested return before cleanup');ok(own.destroyed==(mode==0?1:0)&&caught==(mode==2?original:null),'own return/throw semantics');ok(owner.atlasFrames('borrowed')==atlas,'sprite cleanup does not release shared owner');}
  var inherited=new DestroyInherited();var inheritedError:Dynamic={reason:'inherited-error'};inherited.failure=inheritedError;NightmareVisionSpriteMethods.bind(inherited,owner);var caught:Dynamic=null;try inherited.destroy()catch(e:Dynamic)caught=e;ok(caught==inheritedError&&Reflect.field(inherited,'__nightmareVisionSpriteOwner')==null,'inherited throwing destroy cleanup');
  for(throwParent in [false,true]){var after=new DestroyAfterSuper();after.early=!throwParent;var original:Dynamic={reason:'caught-parent'};after.failure=throwParent?original:null;NightmareVisionSpriteMethods.bind(after,owner);after.destroy();ok(after.after&&after.caught==(throwParent?original:null)&&Reflect.field(after,'__nightmareVisionSpriteOwner')==null,'owner survives early/throwing parent, preserves error identity and clears after child body');}
  var nested=new DestroyNestedSuper();nested.early=true;NightmareVisionSpriteMethods.bind(nested,owner);nested.destroy();ok(nested.after&&Reflect.field(nested,'__nightmareVisionSpriteOwner')==null,'nested callback return does not exit or clear outer destructor');
  var compound=new DestroyReturnSuper();compound.early=true;NightmareVisionSpriteMethods.bind(compound,owner);compound.destroy();ok(Reflect.field(compound,'__nightmareVisionSpriteOwner')==null,'compound return super cleanup');
  var callsBefore=paths.length;owner.requireActive();ok(paths.length==callsBefore,'requireActive performs no atlas IO');
  owner.release();var activeError='';try owner.requireActive()catch(e:Dynamic)activeError=Std.string(e);ok(activeError=='[nightmare-vision-sprite] Selected atlas owner has been released'&&paths.length==callsBefore,'released dependency checked before IO');he='';try h.loadFromSheet('after','A bold')catch(e:Dynamic)he=Std.string(e);ok(he==activeError,'atlas and dependency share released diagnostic');
  h.setScale(1,1);h.centerOnObject(target);h.loadAtlasFrames(atlas);h.makeScaledGraphic(1,1);ok(h.lastKey=='solid#FFFFFFFF','nonatlas methods never require owner IO');
  var unbound=new TargetSprite();unbound.setScale(2,2);unbound.loadAtlasFrames(atlas);unbound.centerOnObject(target);unbound.makeScaledGraphic(2,3);he='';try unbound.loadFromSheet('x','A bold')catch(e:Dynamic)he=Std.string(e);ok(he.indexOf('selected')>=0,'unbound IO diagnostic');
  he='';try NightmareVisionSpriteMethods.bind(new FlxSprite(),null)catch(e:Dynamic)he=Std.string(e);ok(he.indexOf('targeted')>=0,'unsupported receiver diagnostic');
  d.destroy();h.destroy();child.destroy();gd.destroy();gh.destroy();hd.destroy();hh.destroy();unbound.destroy();ok(Reflect.field(h,'__nightmareVisionSpriteOwner')==null&&Reflect.field(child,'__nightmareVisionSpriteOwner')==null&&Reflect.field(gh,'__nightmareVisionSpriteOwner')==null,'generated inherited cleanup clears borrowed cells');ok(target.destroyed==0&&atlas.frames.length>0,'borrowed targets/frames not destroyed');
 }
}
class HitboxReference extends ReferenceSprite {public var calls=0;public function new(){super();}override public function updateHitbox(){calls++;super.updateHitbox();offset.x=37;}}
class HitboxTarget extends TargetSprite {public var calls=0;public function new(){super();}override public function updateHitbox(){calls++;super.updateHitbox();offset.x=37;}}
'''

class NightmareVisionSpriteMacroTest(unittest.TestCase):
    def test_actual_donor_macro_eval_cpp_and_inheritance(self):
        files = nv_sprite_macro_fixture_files()
        files['Main.hx'] = MAIN
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for name, content in files.items():
                p = temp / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')
            command = [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main']
            result = subprocess.run([*command, '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-7000:])
            env = os.environ.copy()
            env.update(HAXEPATH=str(ROOT / '.tools/haxe'), NEKOPATH=str(ROOT / '.tools/neko'), HAXELIB_PATH=str(ROOT / '.haxelib'))
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            cpp = subprocess.run([*command, '-cpp', str(temp / 'cpp'), '-D', 'no-compilation'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(cpp.returncode, 0, (cpp.stdout + cpp.stderr)[-7000:])
            generated = (temp / 'cpp/src/TargetSprite.cpp').read_text(encoding='utf-8')
            self.assertGreaterEqual(generated.count('HX_FIELD_EQ(inName,"__nightmareVisionSpriteOwner")'), 2)
            self.assertNotIn('__HasField', generated)
            enumeration = generated[generated.index('void TargetSprite_obj::__GetFields'):]
            self.assertIn('outFields->push(HX_("__nightmareVisionSpriteOwner"', enumeration)
            methods = (temp / 'cpp/src/NightmareVisionSpriteMethods.cpp').read_text(encoding='utf-8')
            self.assertIn('Type_obj::getInstanceFields', methods)
            self.assertIn('Type_obj::getClass', methods)
            self.assertNotIn('Reflect_obj::hasField', methods)
            table = generated[generated.index('static ::String TargetSprite_obj_sMemberFields'):]
            self.assertIn('HX_("__nightmareVisionSpriteOwner"', table)
            child = (temp / 'cpp/src/TargetChild.cpp').read_text(encoding='utf-8')
            self.assertNotIn('TargetChild_obj::destroy(', child)
            for field in ['loadFromSheet','loadAtlasFrames','makeScaledGraphic','setScale','centerOnObject']:
                self.assertIn(f'HX_FIELD_EQ(inName,"{field}")', generated)

    def test_incompatible_signature_is_rejected(self):
        files = nv_sprite_macro_fixture_files()
        files['Main.hx'] = '@:build(NightmareVisionSpriteMacro.build()) class Main extends flixel.FlxSprite {public function setScale(x:Float,?y:Float):Void{}static function main(){}}'
        with tempfile.TemporaryDirectory() as directory:
            for name, content in files.items():
                p = Path(directory) / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Target already declares setScale', result.stdout + result.stderr)

    def test_unmarked_inherited_method_is_rejected(self):
        files = nv_sprite_macro_fixture_files()
        files['Main.hx'] = 'class Parent extends flixel.FlxSprite {public function setScale(x:Float,y:Float,update:Bool=true):flixel.FlxSprite return this;}@:build(NightmareVisionSpriteMacro.build()) class Main extends Parent {static function main(){}}'
        with tempfile.TemporaryDirectory() as directory:
            for name, content in files.items():
                p = Path(directory) / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Incompatible inherited method or owner cell: setScale', result.stdout + result.stderr)

    def test_super_in_local_function_remains_illegal(self):
        files = nv_sprite_macro_fixture_files()
        files['Main.hx'] = '@:build(NightmareVisionSpriteMacro.build()) class Main extends TargetSprite {override public function destroy(){var nested=function(){super.destroy();};nested();}static function main(){}}'
        with tempfile.TemporaryDirectory() as directory:
            for name, content in files.items():
                p = Path(directory) / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Cannot access super inside a local function', result.stdout + result.stderr)
