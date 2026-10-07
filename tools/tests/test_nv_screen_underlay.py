"""Execute SCREEN creation/geometry with pinned Flixel hitbox, center and zoom methods."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from nv_sprite_dependency_support import add_native_sprite_dependencies
from haxe_test_support import HAXE_COMMAND
from test_psych_note_follow import extract_method

ROOT = Path(__file__).resolve().parents[2]
FLIXEL = ROOT / '.haxelib/flixel/6,1,2/flixel'


class NvScreenUnderlayTest(unittest.TestCase):
    def test_playstate_global_creation_and_ordinary_update_phase(self):
        play=(ROOT/'source/PlayState.hx').read_text(encoding='utf-8')
        assignment=play.index('screenDim = NightmareVisionScreenUnderlay.createScreen(')
        start=play.rfind('if (nightmareVisionScripts != null && nightmareVisionPrefs != null)',0,assignment)
        end=play.index('playerComboBreak = new FlxTypedGroup<FlxSprite>();',assignment)
        creation=play[start:end]
        update=extract_method(play,'function updateNightmareVisionScreenUnderlay(')
        dispatcher=extract_method(play,'function dispatchNightmareVisionUpdatePost(')
        self.assertNotIn('updateNightmareVisionScreenUnderlay',dispatcher)
        self.assertEqual(play.count('updateNightmareVisionScreenUnderlay();'),3)
        for call in ('updateNightmareVisionScreenUnderlay();\n\t\t\t\t\tdispatchNightmareVisionUpdatePost(sourceBatch);',
                     'updateNightmareVisionScreenUnderlay();\n\t\t\tdispatchNightmareVisionUpdatePost(sourceBatch);',
                     'updateNightmareVisionScreenUnderlay();\n\t\tdispatchNightmareVisionUpdatePost(sourceBatch);'):
            self.assertIn(call,play)
        self.assertIn('@:keep public var screenDim:FlxSprite;',play)
        self.assertLess(assignment,play.index('add(playerComboBreak);',assignment))
        self.assertLess(assignment,play.index('add(enemyStrums);',assignment))
        self.assertLess(assignment,play.index('add(healthBarBG);',assignment))
        fixture=r"""class Sprite {public var updated=0;public var camera:Dynamic;public var alpha:Float;public function new(camera:Dynamic,alpha:Float){this.camera=camera;this.alpha=alpha;}}
class NightmareVisionScreenUnderlay {
 public static var created=0;
 public static function createScreen(type:String,opacity:Float,camera:Dynamic):Sprite {if(type!='Screen Dim')return null;created++;return new Sprite(camera,opacity);}
 public static function updateScreen(type:String,sprite:Sprite):Void {if(type=='Screen Dim' && sprite!=null)sprite.updated++;}
}
class NightmareVisionSpriteMethods {public static function bind(object:Dynamic,owner:Dynamic):Void {}}
class NightmareVisionSpriteRegistry {public static function capture(paths:Dynamic):Dynamic return null;}
class Main {
 public var nightmareVisionPaths:Dynamic=null;
 public var nightmareVisionScripts:Dynamic={};public var nightmareVisionPrefs:Dynamic={view:{underlayType:'Screen Dim',underlayOpacity:0.6}};
 public var camHUD:Dynamic={width:1280};public var screenDim:Sprite;public var members:Array<Dynamic>=[];
 public function new(){}
 function add(sprite:Sprite):Void members.push(sprite);
 function create():Void {__CREATE__}
 __UPDATE__
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function main():Void {
  var state=new Main();state.create();var original=state.screenDim;
  check(state.members.length==1 && state.members[0]==original && NightmareVisionScreenUnderlay.created==1,'one state-owned overlay');
  state.updateNightmareVisionScreenUnderlay();check(original.updated==1,'ordinary phase update');
  var replacement=new Sprite({width:800},0.2);state.screenDim=replacement;
  state.updateNightmareVisionScreenUnderlay();
  check(replacement.updated==1 && original.updated==1 && state.members[0]==original,'public replacement updated but not autoattached');
  state.nightmareVisionPrefs.view.underlayOpacity=0.9;state.nightmareVisionPrefs.view.underlayType='Lane Underlay';state.updateNightmareVisionScreenUnderlay();
  check(replacement.updated==1 && replacement.alpha==0.2,'runtime preference switch preserves sprite');
  var fieldMode=new Main();fieldMode.nightmareVisionPrefs.view.underlayType='Lane Underlay';fieldMode.create();
  fieldMode.nightmareVisionPrefs.view.underlayType='Screen Dim';fieldMode.updateNightmareVisionScreenUnderlay();
  check(fieldMode.screenDim==null && fieldMode.members.length==0,'type change must not create a late overlay');
  var native=new Main();native.nightmareVisionScripts=null;native.create();native.screenDim=replacement;native.updateNightmareVisionScreenUnderlay();
  check(native.members.length==0 && replacement.updated==1,'native/Psych surface unchanged');
  trace('NV_SCREEN_INTEGRATION_OK');
 }
}""".replace('__CREATE__',creation).replace('__UPDATE__',update).replace(':FlxSprite',':Sprite')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            path=Path(folder)/'Main.hx';path.write_text(fixture,encoding='utf-8',newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('NV_SCREEN_INTEGRATION_OK',result.stdout)

    def test_single_screen_overlay_source_geometry_and_mutable_sprite(self):
        hitbox = extract_method((FLIXEL/'FlxSprite.hx').read_text(encoding='utf-8'), 'public function updateHitbox(')
        center = extract_method((FLIXEL/'FlxObject.hx').read_text(encoding='utf-8'), 'public inline function screenCenter(').replace(':FlxObject', ':FlxSprite')
        zoom = extract_method((FLIXEL/'FlxCamera.hx').read_text(encoding='utf-8'), 'function set_zoom(')
        fixture = r"""import flixel.FlxCamera;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.util.FlxColor;
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function near(a:Float,b:Float,label:String):Void check(Math.abs(a-b)<0.001,label+': '+a+' != '+b);
 static function main():Void {
  var hud=new FlxCamera(1280,720);
  check(NightmareVisionScreenUnderlay.createScreen('Lane Underlay',0.7,hud)==null,'FIELD must not create SCREEN');
  check(NightmareVisionScreenUnderlay.createScreen('unknown',0.7,hud)==null,'unknown preference must not create SCREEN');
  var zero=NightmareVisionScreenUnderlay.createScreen('Screen Dim',0,hud);
  check(zero!=null && zero.alpha==0,'SCREEN must exist even at zero opacity');
  var original=NightmareVisionScreenUnderlay.createScreen('Screen Dim',0.65,hud);
  check(Std.isOfType(original,NightmareVisionFlxSprite),'actual SCREEN helper wrapper identity');
  var helper:Dynamic=original;check(helper.setScale(2,3,true)==original,'real SCREEN setScale return');near(original.width,2,'real SCREEN virtual hitbox');helper.setScale(1,1,true);
  check(original.frameWidth==1 && original.frameHeight==1 && original.fillColor==FlxColor.BLACK,'source black pixel');
  check(original.color==FlxColor.WHITE && original.camera==hud,'default tint/HUD camera');
  check(original.scrollFactor.x==0 && original.scrollFactor.y==0,'fixed scroll factor');
  near(original.width,1,'creation width remains unscaled until update');
  NightmareVisionScreenUnderlay.updateScreen('Screen Dim',original);
  near(original.scale.x,1280,'screen scaleX');near(original.scale.y,720,'screen scaleY');
  near(original.width,1280,'hitbox width');near(original.height,720,'hitbox height');
  near(original.x,0,'full screen x');near(original.y,0,'full screen y');
  near(original.offset.x,-639.5,'actual Flixel hitbox offset');near(original.origin.x,0.5,'actual Flixel origin');
  original.alpha=0.23;original.color=0xFFFF0000;original.exists=false;original.visible=false;
  var custom=new FlxCamera(800,600);custom.zoom=2;custom.x=91;custom.y=73;custom.angle=45;
  original.camera=custom;
  NightmareVisionScreenUnderlay.updateScreen('Screen Dim',original);
  near(original.width,400,'live override camera width/zoom');near(original.height,300,'live override camera height/zoom');
  near(original.x,440,'global logical screen center, not camera viewport offset');near(original.y,210,'global center Y');
  check(original.alpha==0.23 && original.color==0xFFFF0000 && !original.exists && !original.visible,'geometry must not override script display fields');
  custom.zoom=0;near(custom.zoom,1,'actual Flixel zero zoom resolves default');
  NightmareVisionScreenUnderlay.updateScreen('Screen Dim',original);near(original.width,800,'resolved zero zoom width');
  custom.zoom=-2;
  NightmareVisionScreenUnderlay.updateScreen('Screen Dim',original);
  near(original.scale.x,-400,'negative zoom division retained');near(original.width,400,'negative scale hitbox absolute width');
  near(original.x,440,'negative zoom remains globally centered');
  original.x=37;original.scale.set(3,4);var hitboxes=original.hitboxes;
  NightmareVisionScreenUnderlay.updateScreen('Lane Underlay',original);
  check(original.x==37 && original.scale.x==3 && original.hitboxes==hitboxes,'type switch must leave original overlay untouched');
  NightmareVisionScreenUnderlay.updateScreen('Screen Dim',null);
  var replacement=new FlxSprite().makeGraphic(2,3,FlxColor.WHITE);replacement.camera=hud;replacement.alpha=0.4;
  NightmareVisionScreenUnderlay.updateScreen('Screen Dim',replacement);
  near(replacement.width,2560,'mutable graphic dimensions retained');near(replacement.height,2160,'replacement frameheight retained');
  near(replacement.x,-640,'replacement global centering');near(replacement.alpha,0.4,'replacement alpha retained');
  check(!original.destroyed,'helper must not destroy displaced state-owned overlay');
  trace('NV_SCREEN_UNDERLAY_OK');
 }
}
"""
        sprite = r"""package flixel;
import flixel.util.FlxAxes;
class Point {public var x:Float=1;public var y:Float=1;public function new(){} public function set(x:Float=0,y:Float=0):Void{this.x=x;this.y=y;}}
class FlxSprite {
 public var x:Float=0;public var y:Float=0;public var width:Float=1;public var height:Float=1;
 public var frameWidth:Int=1;public var frameHeight:Int=1;public var fillColor:Int;
 public var color:Int=0xFFFFFFFF;public var alpha:Float=1;public var exists=true;public var visible=true;public var destroyed=false;
 public var camera:FlxCamera;public var scale=new Point();public var offset=new Point();public var origin=new Point();public var scrollFactor=new Point();
 public var hitboxes:Int=0;
 public function new(x:Float=0,y:Float=0){}
 public function destroy():Void destroyed=true;
 public function makeGraphic(w:Int,h:Int,c:Int=-1,unique:Bool=false,?key:String):FlxSprite{frameWidth=w;frameHeight=h;width=w;height=h;fillColor=c;return this;}
 public function centerOrigin():Void{origin.set(frameWidth/2,frameHeight/2);hitboxes++;}
 __HITBOX__
 __CENTER__
}
""".replace('__HITBOX__', hitbox).replace('__CENTER__', center)
        camera = """package flixel; class FlxCamera {
 public static var defaultZoom:Float=1;public var width:Int;public var height:Int;
 public var x:Float=0;public var y:Float=0;public var angle:Float=0;public var zoom(default,set):Float=1;
 public function new(w:Int,h:Int){width=w;height=h;} function setScale(x:Float,y:Float):Void{}
 __ZOOM__
}""".replace('__ZOOM__', zoom)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            work=Path(folder)
            files={'Main.hx':fixture,'flixel/FlxSprite.hx':sprite,'flixel/FlxCamera.hx':camera,
                   'flixel/FlxG.hx':'package flixel; class FlxG {public static var width:Int=1280;public static var height:Int=720;}',
                   'flixel/util/FlxColor.hx':'package flixel.util; class FlxColor {public static inline var BLACK:Int=0xFF000000;public static inline var WHITE:Int=0xFFFFFFFF;}',
                   'flixel/util/FlxAxes.hx':(FLIXEL/'util/FlxAxes.hx').read_text(encoding='utf-8')}
            add_native_sprite_dependencies(files)
            for name,text in files.items():
                path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('NV_SCREEN_UNDERLAY_OK',result.stdout)


if __name__ == '__main__':
    unittest.main()
