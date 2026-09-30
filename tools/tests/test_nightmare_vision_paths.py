"""NMV source-shaped path calls keep package and engine-core assets isolated."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionPathsTest(unittest.TestCase):
    def test_lookup_precedence_suffixes_case_media_and_containment(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            stubs = {
                'flixel/FlxG.hx': '''package flixel;
class FlxG {public static var bitmap={add:function(value:Dynamic,unique:Bool,key:String):flixel.graphics.FlxGraphic return new flixel.graphics.FlxGraphic(key)};
public static var random={int:function(min:Int,max:Int):Int return min};}''',
                'flixel/graphics/FlxGraphic.hx': '''package flixel.graphics;
class FlxGraphic {public var key:String;public function new(key:String)this.key=key;}''',
                'flixel/graphics/frames/FlxAtlasFrames.hx': '''package flixel.graphics.frames;
class FlxAtlasFrames {public var kind:String;public var image:flixel.graphics.FlxGraphic;public var text:String;
public function new(kind:String,image:flixel.graphics.FlxGraphic,text:String){this.kind=kind;this.image=image;this.text=text;}
public static function fromSparrow(i:flixel.graphics.FlxGraphic,t:String)return new FlxAtlasFrames('xml',i,t);
public static function fromAseprite(i:flixel.graphics.FlxGraphic,t:String)return new FlxAtlasFrames('json',i,t);
public static function fromSpriteSheetPacker(i:flixel.graphics.FlxGraphic,t:String)return new FlxAtlasFrames('txt',i,t);}''',
                'openfl/media/Sound.hx': '''package openfl.media;
class Sound {public var path:String; public function new(path:String)this.path=path;}''',
                'flixel/system/FlxAssets.hx': '''package flixel.system;
class FlxAssets {public static function getSoundAddExtension(path:String)return new openfl.media.Sound(path);}''',
                'FNFAssets.hx': '''class FNFAssets {
public static function exists(path:String)return sys.FileSystem.exists(path);
public static function getText(path:String)return sys.io.File.getContent(path);
public static function getBitmapData(path:String):Dynamic return path;
public static function getSound(path:String)return new openfl.media.Sound(path);
}'''
            }
            for name, content in stubs.items():
                p = work / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
            owner = work / 'assets/imported_mods/owner'
            foreign = work / 'assets/imported_mods/foreign'
            files = {
                'images/sheet.png':'owner', 'images/sheet.xml':'owner-xml',
                'images/sheet.json':'owner-json', 'images/sheet.txt':'owner-txt',
                'sounds/noise.wav':'wav', 'sounds/noise.ogg':'ogg',
                'sounds/keys/keyClick5.ogg':'owner-key-click',
                'locale/data/info.txt':'localized', 'songs/chart.json':'{}',
                'shaders/effect.frag':'owner-frag', 'shaders/effect.vert':'owner-vert',
                'noteskins/skin.json':'skin',
                '__nmv_core/shaders/effect.frag':'core-frag',
                '__nmv_core/shaders/core.frag':'core-only',
                '__nmv_core/sounds/noise.ogg':'core-ogg',
                '__nmv_core/images/core.png':'core',
                '__nmv_core/images/core.xml':'core-xml',
            }
            for name, content in files.items():
                p = owner / name; p.parent.mkdir(parents=True, exist_ok=True);p.write_text(content)
            foreign.mkdir(parents=True)
            (foreign / 'secret.txt').write_text('foreign')
            (owner / 'escape').symlink_to(foreign, target_is_directory=True)
            (owner / 'foreignCore').symlink_to(foreign, target_is_directory=True)
            (owner / 'images/atlasFolder').mkdir()
            (work / 'Main.hx').write_text(r'''
class Main {
 static function check(ok:Bool, why:String)if(!ok)throw why;
 static function rejected(f:Void->Dynamic):Bool{try{f();return false;}catch(_:Dynamic)return true;}
 static function main(){
  var p=new NightmareVisionPaths('assets/imported_mods/owner');
  var root=p.root;
  check(p.fragment('effect')==root+'/shaders/effect.frag','owner shader');
  check(p.fragment('effect',false)==root+'/__nmv_core/shaders/effect.frag','core-only shader');
  check(p.fragment('core')==root+'/__nmv_core/shaders/core.frag','explicit core fallback');
  check(p.vertex('effect')==root+'/shaders/effect.vert','vertex');
  check(!p.fileExists('shaders/Effect.frag'),'exact case');
  check(!p.fileExists('secret.txt'),'no foreign fallback');
  check(p.getPath('shaders/effect.frag')==root+'/__nmv_core/shaders/effect.frag','getPath defaults to core');
  check(p.txt('info','locale')==root+'/locale/data/info.txt','parent prefix');
  check(p.json('chart')==root+'/songs/chart.json','json source songs prefix');
	check(p.modFolders('songs/chart.json')==root+'/songs/chart.json','direct selected mod path');
	check(p.modFolders('sounds/missing.ogg')==root+'/sounds/missing.ogg','modFolders does not substitute core paths');
  check(p.noteskin('skin')==root+'/noteskins/skin.json','noteskin legacy fallback');
  check(p.textureAtlas('atlasFolder')==root+'/images/atlasFolder','directory paths');
  check(p.getTextFromFile('missing.txt')=='','missing text source behavior');
  check(p.getTextFromFile('data/info.txt','locale')=='localized','text retrieval');
  check(p.sound('noise').path==root+'/sounds/noise.ogg','ogg before wav');
  check(p.sound('noise.wav').path==root+'/sounds/noise.wav','explicit extension fallback');
  check(p.sound('noise',null,false).path==root+'/__nmv_core/sounds/noise.ogg','core sound');
  check(p.sound('keys/keyClick5').path==root+'/sounds/keys/keyClick5.ogg','owner key sound');
  check(p.sound('keys/keyClick6').path=='flixel/sounds/beep','source beep for missing owner/core sound');
  check(p.music('missing-track').path=='flixel/sounds/beep','source beep for missing music');
  check(p.sanitize('My Song')=='my-song','source sanitize');
  var ownerAssets=new NightmareVisionFunkinAssets(p);
  check(ownerAssets.exists(root+'/sounds/noise.ogg'),'FunkinAssets owner exists');
  check(!ownerAssets.exists('assets/data/options.json'),'FunkinAssets cannot see engine assets');
  check(rejected(function()return ownerAssets.exists(root+'/escape/secret.txt')),'FunkinAssets symlink escape');
  var atlas=p.getAtlasFrames('sheet');
  check(atlas.kind=='xml'&&atlas.text=='owner-xml'&&atlas.image.key==root+'/images/sheet.png','atlas precedence and owner');
  check(p.getSparrowAtlas('core').image.key==root+'/__nmv_core/images/core.png','core atlas');
  check(p.getPackerAtlas('sheet').kind=='txt','packer');
  check(rejected(function()return p.image('missing')),'missing image diagnosed');
  check(rejected(function()return p.getPath('../foreign/secret.txt',null,true)),'traversal');
	check(rejected(function()return p.modFolders('../foreign/secret.txt')),'modFolders traversal');
  check(rejected(function()return p.getPath('escape/secret.txt',null,true)),'symlink escape');
  check(rejected(function()return p.getPath('escape/missing.txt',null,true)),'missing symlink child');
  check(rejected(function()return new NightmareVisionPaths('assets')),'native root rejected');
  check(rejected(function()return new NightmareVisionPaths(root,'assets/imported_mods/foreign')),'foreign core rejected');
  check(rejected(function()return new NightmareVisionPaths(root,root+'/foreignCore').getCorePath('secret.txt')),'symlink core rejected');
 }
}''')
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                                     '-cp', str(work), '--run', 'Main'], cwd=work,
                                    text=True, capture_output=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('requested=assets/imported_mods/owner/__nmv_core/sounds/keys/keyClick6 '
                          'fallback=flixel/sounds/beep', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
