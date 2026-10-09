"""Captured source providers, real helper classes and interpreter constructors."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from nv_sprite_macro_fixture_support import nv_sprite_macro_fixture_files
from test_source_attachment_integration import integration_files
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]

def sprite_integration_files():
    files = integration_files()
    files.update(nv_sprite_macro_fixture_files())
    files['NightmareVisionPaths.hx'] = '''class NightmareVisionPaths {
 public final root:String; public final view:String; public var calls:Array<String>=[];
 public function new(r:String,v:String){root=r;view=v;}
 public function getAtlasFrames(name:String):flixel.graphics.frames.FlxAtlasFrames {calls.push(view+":atlas:"+name);return new flixel.graphics.frames.FlxAtlasFrames();}
 public function getSparrowAtlas(name:String)return getAtlasFrames(name);
 public function image(name:String):flixel.graphics.FlxGraphic {calls.push(view+":image:"+name);return new flixel.graphics.FlxGraphic(31,27);}
}'''
    files['flixel/system/FlxAssets.hx'] = 'package flixel.system;class FlxAssets {}typedef FlxGraphicAsset=Dynamic;'
    sprite = files['flixel/FlxSprite.hx']
    sprite = sprite.replace('public function loadGraphic(g:FlxGraphic,animated:Bool=false,w:Int=0,h:Int=0)', 'public function loadGraphic(g:Dynamic,animated:Bool=false,w:Int=0,h:Int=0,unique:Bool=false,?key:String):FlxSprite')
    sprite = sprite.replace('{name:"cell"+i}', '{name:"cell"+i,w:frameWidth,h:frameHeight}')
    files['flixel/FlxSprite.hx'] = sprite
    files['flixel/group/FlxSpriteGroup.hx'] = files['flixel/group/FlxSpriteGroup.hx'].replace('public function new(x=0.,y=0.)', 'public function new(x=0.,y=0.,maxSize=0)')
    # Other owner-aware constructor APIs are isolated here; the real plain,
    # group, attached and glyph classes exercise helper execution itself.
    files['NightmareVisionBopper.hx'] = '''class NightmareVisionBopper extends NightmareVisionFlxSprite {public var rate:Int;public function new(x=0.,y=0.,rate=2,?paths:NightmareVisionPaths){super(x,y,null,paths);this.rate=rate;}}'''
    files['NightmareVisionVideoSprite.hx'] = '''class NightmareVisionVideoSprite extends NightmareVisionFlxSprite {public var state:Dynamic;public function new(state:Dynamic,paths:NightmareVisionPaths,x=0.,y=0.,once=true,skip=false){super(x,y,null,paths);this.state=state;}}'''
    # The constructor registry now names the real source FlxAnimate base.
    # Its typed dependency boundary is shared with complete Stage donor tests.
    from nv_stage_fixture_support import nv_stage_fixture_files
    base = nv_stage_fixture_files()
    for key in ['animate/FlxAnimate.hx','animate/FlxAnimateFrames.hx','flixel/FlxCamera.hx',
                'flixel/math/FlxPoint.hx','flixel/math/FlxMath.hx','flixel/util/FlxDestroyUtil.hx',
                'flixel/util/FlxPool.hx','flixel/util/FlxSignal.hx','IconAnimation.hx',
                'flixel/graphics/FlxGraphic.hx','flixel/graphics/frames/FlxAtlasFrames.hx']:
        files[key] = base[key]
    files['flixel/util/FlxTimer.hx'] = files['flixel/util/FlxTimer.hx'].replace('public function new()', 'public function start(t:Float,c:FlxTimer->Void):FlxTimer return this;public function new()')
    files['animate/FlxAnimateFrames.hx'] = files['animate/FlxAnimateFrames.hx'].replace('StageIO.current.frame(path)', 'new flixel.graphics.frames.FlxAtlasFrames()')
    sprite = files['flixel/FlxSprite.hx'].replace('function set_frames(', 'public function set_frames(')
    sprite = sprite.replace('class FlxSprite extends FlxObject {', 'class FlxSprite extends FlxObject {public var flipX=false;public var flipY=false;public function getScreenPosition(?p:flixel.math.FlxPoint,?c:flixel.FlxCamera):flixel.math.FlxPoint {if(p==null)p=flixel.math.FlxPoint.get();return p.set(x,y);}public function clone():FlxSprite return new FlxSprite();')
    files['flixel/FlxSprite.hx'] = sprite
    files['NightmareVisionPaths.hx'] = files['NightmareVisionPaths.hx'].replace(' public function getSparrowAtlas', ' public function fileExists(p:String):Bool return false;public function gpuCachingEnabled():Bool return false;public function forgetAtlasGraphic(g:flixel.graphics.FlxGraphic):Void{}public function getTextureAtlas(p:String)return getAtlasFrames(p); public function getSparrowAtlas')
    return files

class NVSpriteIntegrationTest(unittest.TestCase):
    def run_haxe(self, files, cpp=True):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            temp = Path(directory)
            for name, content in files.items():
                path = temp / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
            env = os.environ.copy()
            env.update(HAXEPATH=str(ROOT / '.tools/haxe'), NEKOPATH=str(ROOT / '.tools/neko'), HAXELIB_PATH=str(ROOT / '.haxelib'))
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            command = [*HAXE_COMMAND, '-D', 'flixel', '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', directory, '-main', 'Main']
            targets = [['--interp']]
            if cpp:
                targets.append(['-cpp', str(temp / 'cpp'), '-D', 'no-compilation'])
            for target in targets:
                result = subprocess.run(command + target, cwd=ROOT, env=env, capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-5000:])

    def test_actual_camera_manager_getter_guards_direct_and_captured_mutations(self):
        files = sprite_integration_files()
        files['Main.hx'] = r'''
class Main {
 static function ok(value:Bool,message:String) {if(!value)throw message;}
 static function main() {
  var manager=new flixel.system.frontEnds.CameraFrontEnd();
  var interp=new NightmareVisionScriptInterp({});
  var errors:Array<String>=[];
  interp.sourceError=function(message,pos)errors.push(message);
  interp.variables.set('manager',manager);
  var a={tag:'a'},b={tag:'b'};
  interp.variables.set('a',a);interp.variables.set('b',b);
  interp.execute(new NightmareVisionScriptParser().parseString(
   "var borrowed=manager.add;manager.add(null);borrowed(null);manager.insert(null,0);first=borrowed(a);second=manager.insert(b,0,false);"));
  ok(errors.length==3,'each rejected null mutation is diagnosed');
  for(error in errors)ok(error.indexOf('[source-camera-assignment]')>=0,'camera diagnostic code');
  ok(manager.list.length==2&&manager.list[0]==b&&manager.list[1]==a,'valid restoration continues in source order');
  ok(interp.variables.get('first')==a&&interp.variables.get('second')==b,'valid return identity preserved');
 }
}
'''
        self.run_haxe(files)

    def test_legacy_sheet_constructor_animation_controls_and_owner_capture(self):
        files = sprite_integration_files()
        files['Main.hx'] = r'''
class Main {
 static function ok(value:Bool,message:String) {if(!value)throw message;}
 static function main() {
  NightmareVisionSpriteRegistry.enterSession('sheet');
  var paths=new NightmareVisionPaths('sheet','selected');var other=new NightmareVisionPaths('other','other');
  var owner=NightmareVisionSpriteRegistry.setup(paths);var aa=false;
  var interp=new NightmareVisionScriptInterp({});interp.sourceSpriteOwner=owner;
  NightmareVisionSpriteBindings.install(interp,paths,owner,function()return aa);
  NightmareVisionSpriteRegistry.setup(other);
  var parser=new NightmareVisionScriptParser();
  interp.execute(parser.parseString("sheet=new SpriteFromSheet(12,34,'stage/atlas','A bold');"));
  var sheet:NightmareVisionSpriteFromSheet=cast interp.variables.get('sheet');
  ok(paths.calls.join('|')=='selected:atlas:stage/atlas'&&other.calls.length==0,'construction captures selected owner before atlas lookup');
  ok(sheet.x==12&&sheet.y==34&&!sheet.antialiasing&&sheet.active,'source coordinates, preference and active default');
  ok(sheet.animation.curAnim.name=='A bold'&&Math.abs(sheet.animation.curAnim.frameDuration-1/30)<0.00001&&sheet.animation.curAnim.looped,'native constructor animation defaults');
  sheet.frames.frames.push(sheet.frames.frames[sheet.animation.curAnim.frames[0]]);
  sheet.adjust(12,false,true);
  ok(Math.abs(sheet.animation.curAnim.frameDuration-1/12)<0.00001&&!sheet.animation.curAnim.looped,'adjust replaces the definition and restarts');
  sheet.play(true,true,1);
  ok(sheet.animation.curAnim.reversed&&sheet.animation.curAnim.curFrame==sheet.animation.curAnim.numFrames-2,'public forced/reversed/frame arguments reach native playback');
  aa=true;
  interp.execute(parser.parseString("import Type; type=Type.resolveClass('gameObjects.SpriteFromSheet'); second=Type.createInstance(type,[0,0,'other/atlas','A bold']);"));
  var second:NightmareVisionSpriteFromSheet=cast interp.variables.get('second');
  ok(second.antialiasing&&interp.variables.get('type')==NightmareVisionSpriteFromSheet,'qualified reflection and current owner preference');
  sheet.destroy();ok(sheet.ownerPaths==null,'shared sprite destruction clears captured paths');
  owner.release();var rejected=false;
  try interp.execute(parser.parseString("new SpriteFromSheet(0,0,'bad','A bold');")) catch (_:Dynamic) rejected=true;
  ok(rejected&&paths.calls.length==2,'released factory cannot perform atlas IO');
 }
}
'''
        self.run_haxe(files)

    def test_actual_iris_factories_and_provider_lifetime(self):
        files = sprite_integration_files()
        files['Main.hx'] = r'''
class Main {
 static function ok(value:Bool,message:String) {if(!value)throw message;}
 static function main() {
  NightmareVisionSpriteRegistry.enterSession('a');
  var pa=new NightmareVisionPaths('a','first');var latest=new NightmareVisionPaths('a','latest');var pb=new NightmareVisionPaths('b','other');
  var owner=NightmareVisionSpriteRegistry.setup(pa);var bOwner=NightmareVisionSpriteRegistry.setup(pb);
  var state={tag:'scene'};var i=new NightmareVisionScriptInterp(state);i.sourceSpriteOwner=owner;
  NightmareVisionSpriteBindings.install(i,pa,owner);NightmareVisionAlphabetBindings.install(i,pa);
  NightmareVisionSpriteRegistry.setup(latest);
  var parser=new NightmareVisionScriptParser();
  var directCheck=new NightmareVisionFlxSprite(0,0,'direct',pa);directCheck.destroy();pa.calls=[];
  var factoryCheck=i.createSourceInstance(NightmareVisionFlxSprite,[0,0,'factory']);factoryCheck.destroy();pa.calls=[];
  for(statement in "import flixel.FlxSprite; import flixel.group.FlxSpriteGroup; import funkin.objects.Alphabet; import Type; import Reflect; plain=new FlxSprite(12,24,'owned'); spriteClass=Type.resolveClass('flixel.FlxSprite'); fromType=Type.createInstance(spriteClass,[3,4,'typeOwned']); group=new FlxSpriteGroup(); fromTypeGroup=Type.createInstance(FlxSpriteGroup,[5,6,0]); group.add(plain); reflected=Reflect.field(plain,'makeScaledGraphic'); result=Reflect.callMethod(plain,reflected,[20,30]); glyphs=new Alphabet(0,0,'AB',true,1);".split(';')) if(StringTools.trim(statement)!='')try i.execute(parser.parseString(statement+';'))catch(error:Dynamic)throw statement+': '+Std.string(error);
  var plain:NightmareVisionFlxSprite=cast i.variables.get('plain');var fromType:NightmareVisionFlxSprite=cast i.variables.get('fromType');
  ok(i.variables.get('spriteClass')==NightmareVisionFlxSprite&&i.variables.get('result')==plain,'actual classes and return identity');
  ok(pa.calls.join('|')=='first:image:owned|first:image:typeOwned|first:atlas:alphabet|first:atlas:alphabet','captured image factory and glyph owner IO');
  plain.loadFromSheet('sheet','A bold');fromType.loadFromSheet('sheet2','B bold');
  ok(latest.calls.join('|')=='latest:atlas:sheet|latest:atlas:sheet2','construction does not rebind latest shared provider');
  var group:NightmareVisionSpriteGroup=cast i.variables.get('group');
  ok(Std.isOfType(group,flixel.group.FlxSpriteGroup)&&Std.isOfType(i.variables.get('fromTypeGroup'),NightmareVisionSpriteGroup),'native generic group class and real helper factory');
  var before=plain.scale.x;group.setScale(2,3);ok(plain.scale.x==2&&plain.scale.y==3,'actual group virtual scale propagation');
  var text:NightmareVisionAlphabet=cast i.variables.get('glyphs');var glyph:NightmareVisionAlphaCharacter=text.lettersArray[0];
  glyph.loadFromSheet('glyphsheet','A bold');ok(latest.calls[2]=='latest:atlas:glyphsheet','internal glyph borrows shared provider');
  var attached=new NightmareVisionAttachedSprite();NightmareVisionSpriteMethods.bind(attached,owner);attached.setScale(2,3);attached.loadFromSheet('attached','A bold');
  var bg=new NightmareVisionBGSprite('background',0,0,1,1,null,false,pa);ok(pa.calls[pa.calls.length-1]=='first:image:background','BG captures paths before load');
  var video:NightmareVisionVideoSprite=cast i.createSourceInstance(NightmareVisionVideoSprite,[10,11,true,false]);ok(video.state==state&&video.ownerPaths==pa,'Type video factory captures scene and paths before constructor');
  var other=new NightmareVisionFlxSprite(0,0,null,pb);other.loadFromSheet('other','A bold');ok(pb.calls[0]=='other:atlas:other','distinct root isolation');
  plain.destroy();ok(Reflect.field(plain,'__nightmareVisionSpriteOwner')==null,'destroy clears only borrowed cell');
  fromType.loadFromSheet('survivor','A bold');NightmareVisionSpriteRegistry.enterSession('a');fromType.loadFromSheet('retry','A bold');
  NightmareVisionSpriteRegistry.enterSession('');var released=false;try fromType.loadFromSheet('stale','A bold')catch(error:Dynamic)released=Std.string(error).indexOf('released')>=0;ok(released,'owner exit releases IO');
  fromType.makeScaledGraphic(2,3);fromType.destroy();group.destroy();text.destroy();attached.destroy();other.destroy();bg.destroy();video.destroy();i.release();
 }
}'''
        self.run_haxe(files)

    def test_primary_lease_keeps_old_plugin_atlas_until_teardown_returns(self):
        files = sprite_integration_files()
        initialization = method((ROOT / 'source/PlayState.hx').read_text(encoding='utf-8'), 'function initializeNightmareVisionScripts(')
        start = initialization.index('var root = nightmareVisionSelectedRoot();')
        end = initialization.index('if (nightmareVisionActiveMods', start)
        files['LeaseHost.hx'] = 'class LeaseHost {public var selected:String;public function new(s:String)selected=s;function nightmareVisionSelectedRoot():String return selected;public function begin():Void {' + initialization[start:end] + '}}'
        files['NightmareVisionPluginHost.hx'] = 'class NightmareVisionPluginHost {public static var cleanup:Void->Void;public static function releaseOtherOwner(root:String):Void if(cleanup!=null)cleanup();}'
        files['Main.hx'] = '''class Main {static function main(){NightmareVisionSpriteRegistry.enterSession("old");var paths=new NightmareVisionPaths("old","old");var owner=NightmareVisionSpriteRegistry.setup(paths);var sprite=new NightmareVisionFlxSprite(0,0,null,paths);var called=false;NightmareVisionPluginHost.cleanup=function(){sprite.loadFromSheet("plugin-teardown","A bold");called=true;};new LeaseHost("new").begin();if(!called||paths.calls.length!=1)throw "old plugin IO must survive until teardown returns";var released=false;try sprite.loadFromSheet("stale","A bold")catch(error:Dynamic)released=Std.string(error).indexOf("released")>=0;if(!released)throw "changed primary releases borrowed old provider";sprite.destroy();}}'''
        self.run_haxe(files)

    def test_supported_real_class_matrix_and_source_only_live_dimension_reads(self):
        direct = ['NightmareVisionFlxSprite', 'NightmareVisionBopper', 'NightmareVisionMeshRender',
                  'NightmareVisionVideoSprite', 'NightmareVisionAttachedSprite', 'NightmareVisionSplashSprite',
                  'NightmareVisionAlphabet', 'NightmareVisionAlphaCharacter', 'NightmareVisionBar',
                  'NightmareVisionHealthIcon', 'NightmareVisionSpriteGroup', 'Note', 'Character']
        for name in direct:
            source = (ROOT / 'source' / (name + '.hx')).read_text(encoding='utf-8')
            self.assertIn('@:build(NightmareVisionSpriteMacro.build())', source, name)
        source = (ROOT / 'source/Strumline.hx').read_text(encoding='utf-8')
        self.assertEqual(source.count('@:build(NightmareVisionSpriteMacro.build())'), 2)
        for name in ['NightmareVisionBGSprite', 'NightmareVisionNoteSplash', 'NightmareVisionSustainSplash']:
            self.assertRegex((ROOT / 'source' / (name + '.hx')).read_text(encoding='utf-8'), r'extends NightmareVision(?:FlxSprite|SplashSprite)')
        # The non-sprite compatibility facade must not acquire a fake bridge.
        self.assertNotIn('NightmareVisionSpriteMacro', (ROOT / 'source/NightmareVisionCharacterGroupCompat.hx').read_text(encoding='utf-8'))
        ps = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        common = method(ps, 'static function seedNightmareVisionCommon(')
        self.assertIn('NightmareVisionSpriteBindings.install(interp, paths, spriteOwner, function() return prefs.view.globalAntialiasing)', common)
        self.assertIn('NightmareVisionSpriteRegistry.setup(paths)', common)
        renderer = (ROOT / 'source/nightmarevision/modchart/NightmareVisionModchartRenderer.hx').read_text(encoding='utf-8')
        self.assertIn("transform.registry.executionEntry == null ? baseline.frameHeight : number(property(note, 'frameHeight')", renderer)
        self.assertIn("transform.registry.executionEntry == null ? baseline.frameWidth : number(property(note, 'frameWidth')", renderer)

if __name__ == '__main__':
    unittest.main()
