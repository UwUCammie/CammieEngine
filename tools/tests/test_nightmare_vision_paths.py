"""NMV source-shaped path calls keep package and engine-core assets isolated."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionPathsTest(unittest.TestCase):
    def test_historical_core_layout_selects_root_icons_and_keeps_explicit_override(self):
        fixture = r'''
class NightmareVisionLegacyIconPrefixMain {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function paths(prefix:String):Array<String> {
  var files:Array<String>=[];
  for(digit in 0...10)files.push('core/images/'+prefix+'num'+digit+'.png');
  return files;
 }
 static function main():Void {
  var oldFiles=paths('');
  oldFiles.push('core/images/icons/icon-bfmobian.png');
  oldFiles.push('core/images/UI/custom/icons/icon-bfmobian.png');
  var oldCore=new NightmareVisionPaths(oldFiles);
  var oldProfile=NightmareVisionHUDProfile.detect(oldCore);
  var owner:SourceHealthIconOwner={
   image:function(name:String,gpu:Bool)return null,
   exists:function(path:String)return oldCore.exists(oldCore.getCorePath(path)),
   uiPrefix:function()return oldProfile.uiPrefix,
   antialiasing:function()return true
  };
  check(oldProfile.name=='legacy-shared'&&owner.uiPrefix()=='',
   'legacy root-level HUD marker selects root-level icon default');
  check(SourceHealthIconLoader.nightmarePath('bfmobian',owner)=='icons/icon-bfmobian',
   'legacy profile finds a real root-layout icon');
  owner.uiPrefix=function()return 'UI/custom/';
  check(SourceHealthIconLoader.nightmarePath('bfmobian',owner)=='UI/custom/icons/icon-bfmobian',
   'an explicit prefix remains authoritative even for a historical core');
  var newCore=new NightmareVisionPaths(paths('UI/combo/'));
  check(NightmareVisionHUDProfile.detect(newCore).uiPrefix=='UI/',
   'new split layout keeps the modern UI icon default');
 }
        }
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as scratch:
            (Path(scratch) / 'NightmareVisionHUDProfile.hx').write_text(
                (ROOT / 'source/NightmareVisionHUDProfile.hx').read_text(), newline='\n')
            (Path(scratch) / 'SourceHealthIconLoader.hx').write_text(
                (ROOT / 'source/SourceHealthIconLoader.hx').read_text(), newline='\n')
            (Path(scratch) / 'NightmareVisionPaths.hx').write_text(
                'class NightmareVisionPaths { public var files:Map<String,Bool>=new Map(); '
                'public function new(paths:Array<String>)for(p in paths)files.set(p,true); '
                "public function getCorePath(relative:String):String return 'core/'+relative; "
                'public function exists(path:String):Bool return files.exists(path); }', newline='\n')
            (Path(scratch) / 'SourceHealthIconOwner.hx').write_text(
                'typedef SourceHealthIconOwner={var image:(String,Bool)->Dynamic;var exists:String->Bool;'
                'var uiPrefix:Void->String;var antialiasing:Void->Bool;}', newline='\n')
            (Path(scratch) / 'NightmareVisionLegacyIconPrefixMain.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(scratch),
                                     '--main', 'NightmareVisionLegacyIconPrefixMain', '--interp'], cwd=ROOT,
                                    text=True, capture_output=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
                'animate/FlxAnimateFrames.hx': '''package animate;
import flixel.graphics.frames.FlxAtlasFrames;
typedef SpritemapInput = {source:Dynamic, json:String}
class FlxAnimateFrames extends FlxAtlasFrames {
public static var lastInput:String;public static var lastMetadata:String;public static var lastKey:String;public static var lastMaps:Array<SpritemapInput>;
public function new(path:String)super('animate',new flixel.graphics.FlxGraphic(path),path);
public static function fromAnimate(input:String,maps:Array<SpritemapInput>,?metadata:String,?key:String):FlxAnimateFrames {
lastInput=input;lastMaps=maps;lastMetadata=metadata;lastKey=key;return new FlxAnimateFrames(key);
}}''',
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
                p.write_text(content, newline='\n')
            owner = work / 'assets/imported_mods/owner'
            foreign = work / 'assets/imported_mods/foreign'
            files = {
                'images/sheet.png':'owner', 'images/sheet.xml':'owner-xml',
                'images/sheet.json':'owner-json', 'images/sheet.txt':'owner-txt',
                'images/animate/Animation.json':'owner-animation',
                'images/animate/metadata.json':'owner-metadata',
                'images/animate/spritemap1.json':'owner-map-json',
                'images/animate/spritemap1.png':'owner-map-image',
                'sounds/noise.wav':'wav', 'sounds/noise.ogg':'ogg',
                'sounds/keys/keyClick5.ogg':'owner-key-click',
                'locale/data/info.txt':'localized', 'songs/chart.json':'{}',
                'shaders/effect.frag':'owner-frag', 'shaders/effect.vert':'owner-vert',
                'noteskins/skin.json':'skin',
                'data/scripts/loader.hxs':'owner-loader',
                '__nmv_core/data/scripts/loader.hx':'core-loader',
                'data/scripts/second.hx':'owner-second',
                '__nmv_core/data/scripts/core.hscript':'core-script',
                '__nmv_core/shaders/effect.frag':'core-frag',
                '__nmv_core/shaders/core.frag':'core-only',
                '__nmv_core/sounds/noise.ogg':'core-ogg',
                '__nmv_core/images/core.png':'core',
                '__nmv_core/images/core.xml':'core-xml',
                '__nmv_core/images/icons/icon-face.png':'legacy core face',
                '__nmv_core/images/icons/icon-bfmobian.png':'legacy core icon',
                '__nmv_core/images/UI/custom/icons/icon-bfmobian.png':'explicitly prefixed icon',
                'images/custom/num0.png':'explicit owner digit',
            }
            for name, content in files.items():
                p = owner / name; p.parent.mkdir(parents=True, exist_ok=True);p.write_text(content, newline='\n')

            legacy = work / 'assets/imported_mods/legacy/__nmv_core/images'
            split = work / 'assets/imported_mods/split/__nmv_core/images/UI/combo'
            partial_core = work / 'assets/imported_mods/partial/__nmv_core/images'
            for digit in range(10):
                p = legacy / f'num{digit}.png'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('legacy', newline='\n')
                p = split / f'num{digit}.png'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('split', newline='\n')
            for digit in range(9):
                p = partial_core / f'num{digit}.png'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('partial legacy', newline='\n')
                p = partial_core / 'UI/combo' / f'num{digit}.png'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('partial split', newline='\n')

            foreign.mkdir(parents=True)
            (foreign / 'secret.txt').write_text('foreign', newline='\n')
            (owner / 'escape').symlink_to(foreign, target_is_directory=True)
            (owner / 'foreignCore').symlink_to(foreign, target_is_directory=True)
            (owner / 'images/atlasFolder').mkdir()
            (work / 'Main.hx').write_text(r'''
import animate.FlxAnimateFrames;
class Main {
 static function check(ok:Bool, why:String)if(!ok)throw why;
 static function rejected(f:Void->Dynamic):Bool{try{f();return false;}catch(_:Dynamic)return true;}
 static function main(){
  var p=new NightmareVisionPaths('assets/imported_mods/owner');
  var root=p.root;
  check(p.hudProfile.name=='unknown-split-default' && !p.hudProfile.detected
   && p.hudProfile.splitDigitCount==0 && p.hudProfile.legacyDigitCount==0,
   'an owner with no complete core digit set remains undetected');
  check(!p.usesSharedRatingPrefix && p.COMBO_PREFIX=='UI/combo/'
   && p.RATINGS_PREFIX=='UI/ratings/' && p.COUNTDOWN_PREFIX=='UI/countdown/' && p.UI_PREFIX=='UI/',
   'undetected layout preserves current split defaults');
  check(p.image('custom/num0').key==root+'/images/custom/num0.png',
   'explicit owner HUD path stays exact');
  check(p.getPath('images/UI/combo/num0.png',null,true)==root+'/__nmv_core/images/UI/combo/num0.png'
   && !p.fileExists('images/UI/combo/num0.png',null,true),
   'missing explicit split path does not alias another digit path');

  var legacyPaths=new NightmareVisionPaths('assets/imported_mods/legacy');
  check(legacyPaths.hudProfile.name=='legacy-shared' && legacyPaths.usesSharedRatingPrefix
   && legacyPaths.COMBO_PREFIX=='' && legacyPaths.RATINGS_PREFIX==''
   && legacyPaths.COUNTDOWN_PREFIX=='UI/countdown/' && legacyPaths.UI_PREFIX=='',
   'complete flat core selects historical root icons independently from the legacy shared rating/digit prefix');
  check(legacyPaths.fileExists('images/num0.png',null,false)
   && !legacyPaths.fileExists('images/UI/combo/num0.png',null,false),
   'legacy profile detects capabilities without adding path aliases');
  var legacyIconOwner:SourceHealthIconOwner={
   image:function(name:String,gpu:Bool)return new flixel.graphics.FlxGraphic(name),
   exists:function(path:String)return legacyPaths.exists(legacyPaths.getPath(path,null,true)),
   uiPrefix:function()return legacyPaths.UI_PREFIX,
   antialiasing:function()return true
  };
  check(SourceHealthIconLoader.nightmarePath('bfmobian',legacyIconOwner)=='icons/icon-bfmobian',
   'historical core profile resolves icons at images/icons');
  legacyPaths.UI_PREFIX='UI/custom/';
  check(SourceHealthIconLoader.nightmarePath('bfmobian',legacyIconOwner)=='UI/custom/icons/icon-bfmobian',
   'explicit UI prefix remains independent from historical defaults');

  var splitPaths=new NightmareVisionPaths('assets/imported_mods/split');
  check(splitPaths.hudProfile.name=='split' && splitPaths.hudProfile.detected
   && !splitPaths.usesSharedRatingPrefix && splitPaths.COMBO_PREFIX=='UI/combo/'
   && splitPaths.RATINGS_PREFIX=='UI/ratings/' && splitPaths.COUNTDOWN_PREFIX=='UI/countdown/'
   && splitPaths.UI_PREFIX=='UI/',
   'complete split core selects newer independent-prefix defaults');

  var partialPaths=new NightmareVisionPaths('assets/imported_mods/partial');
  check(partialPaths.hudProfile.name=='unknown-split-default' && !partialPaths.usesSharedRatingPrefix
   && partialPaths.hudProfile.splitDigitCount==9 && partialPaths.hudProfile.legacyDigitCount==9,
   'partial flat and split layouts do not imply a legacy API');
  check(partialPaths.getPath('images/UI/combo/num9.png',null,true)
   =='assets/imported_mods/partial/__nmv_core/images/UI/combo/num9.png'
   && !partialPaths.fileExists('images/UI/combo/num9.png',null,true),
   'incomplete explicit split asset remains missing at its requested path');
  var missingHudPath='';
  try partialPaths.image('UI/combo/num9') catch (error:Dynamic) missingHudPath=Std.string(error);
  check(missingHudPath.indexOf('assets/imported_mods/partial/__nmv_core/images/UI/combo/num9.png')>=0,
   'unsupported explicit HUD asset reports its exact missing path without fallback');

  check(p.fragment('effect')==root+'/shaders/effect.frag','owner shader');
  check(p.fragment('effect',false)==root+'/__nmv_core/shaders/effect.frag','core-only shader');
  check(p.fragment('core')==root+'/__nmv_core/shaders/core.frag','explicit core fallback');
  check(p.vertex('effect')==root+'/shaders/effect.vert','vertex');
  check(p.resolveScript('data/scripts/loader').relative=='__nmv_core/data/scripts/loader.hx','extension precedence before layer');
  check(p.resolveScript('data/scripts/second').path==root+'/data/scripts/second.hx','owner dynamic script');
  check(p.resolveScript(root+'/data/scripts/second').relative=='data/scripts/second.hx','owned resolved script path');
  check(p.resolveScript('data/scripts/core').relative=='__nmv_core/data/scripts/core.hscript','core dynamic script');
  check(p.resolveScript('data/scripts/missing')==null,'missing script');
  check(rejected(()->p.resolveScript('../foreign')),'traversal script');
  check(rejected(()->p.resolveScript('assets/imported_mods/foreign/script')),'foreign script');
  check(rejected(()->p.resolveScript('escape/secret')),'symlink script');
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
  var animateAtlas=p.getTextureAtlas('animate');
  check(animateAtlas.kind=='animate'&&animateAtlas.text==root+'/images/animate','Animate atlas cache key escaped owner');
  check(FlxAnimateFrames.lastInput=='owner-animation'&&FlxAnimateFrames.lastMetadata=='owner-metadata'
   && FlxAnimateFrames.lastKey==root+'/images/animate','Animate owner manifest/metadata were not passed directly');
  check(FlxAnimateFrames.lastMaps.length==1
   && FlxAnimateFrames.lastMaps[0].json=='owner-map-json'
   && FlxAnimateFrames.lastMaps[0].source==root+'/images/animate/spritemap1.png',
   'Animate owner spritemap files were not read from the selected package');
  check(p.getTextureAtlas('sheet').kind=='xml','non-Animate texture atlas fallback');
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
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                     '-cp', str(work), '--run', 'Main'], cwd=work,
                                    text=True, capture_output=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('requested=assets/imported_mods/owner/__nmv_core/sounds/keys/keyClick6 '
                          'fallback=flixel/sounds/beep', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
