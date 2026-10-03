"""Execute scoped path resolution with lightweight rendering boundary stubs."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenamePathsTest(unittest.TestCase):
    def test_scoped_assets_atlas_selection_and_escape_rejection(self):
        import_bindings = (ROOT / 'source/CodenameImportBindings.hx').read_text()
        self.assertIn("bindings.set('lime.utils.Assets', paths.limeAssets());", import_bindings)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            base = Path(directory)
            own, other = base / 'owned', base / 'other'
            for folder in (own, other):
                (folder / 'images').mkdir(parents=True)
                (folder / 'assets/shared/data').mkdir(parents=True)
            (own / 'assets/shared/data/chart.json').write_text('owner A chart', newline='\n')
            (other / 'assets/shared/data/chart.json').write_text('owner B chart', newline='\n')
            (own / 'assets/shared/escape').symlink_to(other / 'assets/shared')
            (own / 'videos').mkdir()
            (own / 'fonts').mkdir()
            (own / 'fonts/aller.ttf').write_bytes(b'font fixture')
            (own / 'videos/clip.mp4').write_bytes(b'video fixture')
            (own / 'songs/tutorial').mkdir(parents=True)
            (own / 'songs/tutorial/lyrics.json').write_text('{"stuff":[]}', newline='\n')
            (own / 'videos/escape.mp4').symlink_to(other / 'images/missing.png')
            (own / 'models').mkdir()
            (own / 'models/plane.obj').write_text('o plane\n', newline='\n')
            (own / 'shaders/base').mkdir(parents=True)
            (own / 'shaders/base/postprocess.frag').write_text('uniform vec4 uCameraBounds;', newline='\n')
            (own / 'shaders/rain.frag').write_text('varying vec2 screenCoord;', newline='\n')
            (own / 'shaders/rain.vert').write_text('varying vec2 screenCoord; void main() {}', newline='\n')
            (own / 'shaders/plain.frag').write_text('void main() {}', newline='\n')
            (own / 'sounds/stickersounds/keys').mkdir(parents=True)
            (own / 'sounds/stickersounds/keys/pop.ogg').write_bytes(b'owned sound')
            (own / 'sounds/stickersounds/escape').symlink_to(other / 'images')
            (own / 'sounds/stickersounds/keys/foreign.ogg').symlink_to(other / 'images/missing.png')
            (other / 'shaders').mkdir()
            (other / 'shaders/plain.vert').write_text('foreign vertex', newline='\n')
            (own / 'shaders/plain.vert').symlink_to(other / 'shaders/plain.vert')
            for name in ('plain.png', 'sparrow.png', 'sparrow.xml', 'packer.png', 'packer.txt'):
                (own / 'images' / name).write_text(name, newline='\n')
            (other / 'images/missing.png').write_text('other owner', newline='\n')
            (own / 'images/escape.png').symlink_to(other / 'images/missing.png')
            (own / 'images/ambiguous.png').write_text('lowercase match', newline='\n')
            (own / 'images/Ambiguous.PNG').write_text('mixed-case match', newline='\n')
            (own / 'images/animate').mkdir()
            (own / 'images/animate/Animation.json').write_text('{}', newline='\n')
            (own / 'images/animate/spritemap1.json').write_text('{}', newline='\n')
            (own / 'images/animate/spritemap1.png').write_bytes(b'animate page')
            # A complete authored atlas lives under BF/, while a partial
            # lowercase bf/ tree exists. Full-path case lookup must backtrack
            # from that dead-end instead of failing at the first matching
            # directory component.
            ice_upper = own / 'images/characters/BF/wolf'
            ice_upper.mkdir(parents=True)
            (ice_upper / 'BF_Ice.png').write_bytes(b'ice image')
            (ice_upper / 'BF_Ice.xml').write_text('<TextureAtlas>ice</TextureAtlas>', newline='\n')
            ice_lower = own / 'images/characters/bf/wolf'
            ice_lower.mkdir(parents=True)
            (ice_lower / 'partial.xml').write_text('<TextureAtlas/>', newline='\n')
            (own / 'images/stages/tricky').mkdir(parents=True)
            (own / 'images/stages/tricky/tricky_fog.png').write_bytes(b'tricky fog')
            for page in range(1, 18):
                (own / f'images/pages/{page}.png').parent.mkdir(parents=True, exist_ok=True)
                (own / f'images/pages/{page}.png').write_bytes(f'page {page}'.encode())
                (own / f'images/pages/{page}.xml').write_text('<TextureAtlas/>', newline='\n')
            stubs = {
                'FNFAssets.hx': '''class FNFAssets {
 public static function exists(p:String):Bool return sys.FileSystem.exists(p);
 public static function getBitmapData(p:String):Dynamic return p;
 public static function getText(p:String):String return sys.io.File.getContent(p);
 public static function getSound(p:String):Dynamic return p;
}''',
                'flixel/graphics/FlxGraphic.hx': '''package flixel.graphics;
class FlxGraphic { public var key:String;public function new(key:String)this.key=key; }''',
                'flixel/FlxG.hx': '''package flixel;
import flixel.graphics.FlxGraphic;
class BitmapFrontEnd {
 public var lastKey:String;public var lastBitmap:Dynamic;
 public function new(){}
 public function add(bitmap:Dynamic,unique:Bool=false,?key:String):FlxGraphic {
  lastKey=key;lastBitmap=bitmap;return new FlxGraphic(key);
 }
}
class FlxG { public static var bitmap:BitmapFrontEnd=new BitmapFrontEnd(); }''',
                'openfl/text/Font.hx': '''package openfl.text;
class Font { public var fontName:String; public function new(name:String) this.fontName=name;
 public static var registered:Array<Font>=[];
 public static function registerFont(font:Font):Void registered.push(font);
 public static function fromFile(path:String):Font
  return sys.FileSystem.exists(path) ? new Font('Aller') : null;
}''',
                'flixel/graphics/frames/FlxFramesCollection.hx': '''package flixel.graphics.frames;
class FlxFramesCollection { public var kind:String; public var image:Dynamic;
 public function new(kind:String, image:Dynamic) { this.kind=kind; this.image=image; }
}''',
                'flixel/graphics/frames/FlxAtlasFrames.hx': '''package flixel.graphics.frames;
class FlxAtlasFrames extends FlxFramesCollection {
 public function new(kind:String, image:Dynamic) super(kind, image);
 public static function fromSparrow(image:Dynamic, xml:String):FlxAtlasFrames return new FlxAtlasFrames('sparrow', image);
 public static function fromSpriteSheetPacker(image:Dynamic, txt:String):FlxAtlasFrames return new FlxAtlasFrames('packer', image);
 public function addAtlas(atlas:FlxAtlasFrames):FlxAtlasFrames { kind += '+'+atlas.kind; return this; }
}''',
                'animate/FlxAnimateFrames.hx': '''package animate;
import flixel.graphics.frames.FlxAtlasFrames;
class FlxAnimateFrames extends FlxAtlasFrames {
 public static function fromAnimate(path:String):FlxAnimateFrames return new FlxAnimateFrames('animate', path);
}''',
                'flixel/graphics/frames/FlxImageFrame.hx': '''package flixel.graphics.frames;
class FlxImageFrame { public static function fromImage(image:Dynamic):FlxFramesCollection return new FlxFramesCollection('image', image); }''',
            }
            for name, source in stubs.items():
                dest = base / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(source, newline='\n')
            (base / 'Main.hx').write_text('''class Main {
 static function rejects(f:Void->Dynamic, part:String):Void {
  var error = '';
  try f() catch (e:Dynamic) error = Std.string(e);
  if (error.indexOf(part) < 0) throw 'expected ' + part + ': ' + error;
 }
 static function main() {
  var paths = new CodenamePaths(OWN);
  if (paths.getFrames('plain').kind != 'image') throw 'plain';
  if (paths.getFrames('sparrow.png').kind != 'sparrow') throw 'sparrow extension';
  if (paths.getFrames('packer').kind != 'packer') throw 'packer';
  if (paths.getFrames('animate').kind != 'animate') throw 'Animate atlas';
 if (paths.getFrames('pages').kind.split('+').length != 17) throw 'all consecutive Sparrow pages';
  var ice=paths.getFrames('characters/bf/wolf/BF_Ice');
  if (ice.kind != 'sparrow' || ice.image != OWN + '/images/characters/BF/wolf/BF_Ice.png')
   throw 'full-path case resolution did not backtrack to the unique complete atlas';
  if (paths.file('images/characters/bf/wolf/BF_Ice.xml') != OWN + '/images/characters/BF/wolf/BF_Ice.xml')
   throw 'case-insensitive atlas metadata lookup';
  if (paths.image('plain') != OWN + '/images/plain.png') throw 'ownership';
  var graphic=paths.graphic(paths.image('plain'));
  if(graphic.key!=OWN+'/images/plain.png' || flixel.FlxG.bitmap.lastKey!=OWN+'/images/plain.png'
   || flixel.FlxG.bitmap.lastBitmap!=OWN+'/images/plain.png') throw 'owner graphic cache key';
  if (paths.getFontName(paths.font('aller.ttf')) != 'Aller'
   || paths.getFontName(paths.font('aller.ttf')) != 'Aller'
   || openfl.text.Font.registered.length != 1) throw 'owner font registration/cache';
  if (paths.image('stages/tricky//tricky_fog') != OWN + '/images/stages/tricky/tricky_fog.png') throw 'duplicate separators';
  if (paths.image('animate').kind != 'animate') throw 'Paths.image Animate folder';
  if (paths.image('pages').kind.split('+').length != 17) throw 'Paths.image all paged folder entries';
  if (paths.image('missing') != null) throw 'missing owner image should be nullable';
  if (paths.getPath(paths.video('clip')) != OWN + '/videos/clip.mp4') throw 'scoped video';
  if (paths.obj('plane') != OWN + '/models/plane.obj') throw 'scoped model';
  if (paths.getPath(paths.file('videos/clip.mp4')) != OWN + '/videos/clip.mp4') throw 'scoped file';
  if (paths.getPath('songs/tutorial/lyrics.json') != OWN + '/songs/tutorial/lyrics.json') throw 'relative source key';
  if (paths.assets().getText('songs/tutorial/lyrics.json') != '{"stuff":[]}') throw 'scoped text';
  if (!paths.assets().exists('songs/tutorial/lyrics.json')) throw 'scoped exists';
  if (paths.assets().exists(OTHER + '/images/missing.png')) throw 'foreign exists';
  var limeA=paths.limeAssets();
  var pathsB=new CodenamePaths(OTHER);
  var limeB=pathsB.limeAssets();
  if (limeA.getText('assets/shared/data/chart.json') != 'owner A chart') throw 'Lime owner-relative path';
  if (limeA.getText(paths.getPath('assets/shared/data/chart.json')) != 'owner A chart') throw 'Lime absolute owner path';
  if (limeB.getText('assets/shared/data/chart.json') != 'owner B chart') throw 'Lime owner isolation';
  var cwd=Sys.getCwd();
  while (cwd.length>0 && cwd.charAt(cwd.length-1)=='/') cwd=cwd.substr(0,cwd.length-1);
  var relativeOwner=OWN.substr(cwd.length+1);
  var relativePaths=new CodenamePaths(relativeOwner);
  if (relativePaths.limeAssets().getText(relativeOwner + '/assets/shared/data/chart.json') != 'owner A chart')
   throw 'relative full owner path was double-prefixed';
  if (limeA.getText('assets/shared/data/missing.json') != null) throw 'Lime missing text is nullable';
  rejects(function() return paths.assets().getText('assets/shared/data/missing.json'), 'Missing scoped asset');
  rejects(function() return limeA.getText('assets/../other/assets/shared/data/chart.json'), 'Invalid Lime text key');
  rejects(function() return limeA.getText(OTHER + '/assets/shared/data/chart.json'), 'escaped selected owner');
  rejects(function() return relativePaths.limeAssets().getText(OTHER.substr(cwd.length+1) + '/assets/shared/data/chart.json'), 'escaped selected owner');
  rejects(function() return limeA.getText('assets/shared/escape/missing.json'), 'escaped selected owner');
  if (paths.shaderImport('base/postprocess.frag') != 'uniform vec4 uCameraBounds;') throw 'scoped shader include';
  if (paths.getFolderDirectories('sounds/stickersounds/').join(',') != 'keys') throw 'scoped folder names';
  if (paths.getFolderDirectories('sounds/stickersounds/', true).join(',') != 'sounds/stickersounds/keys') throw 'scoped folder prefixes';
  if (paths.getFolderContent('sounds/stickersounds/keys', true).join(',') != 'sounds/stickersounds/keys/pop.ogg') throw 'scoped folder files';
  if (paths.getFolderContent('sounds/stickersounds/keys', false, null, true).join(',') != 'pop') throw 'folder extension removal';
  if (paths.getFolderContent('sounds/missing').length != 0) throw 'missing folder';
  if (paths.vertexForFragment('rain') != OWN + '/shaders/rain.vert') throw 'paired vertex';
  if (paths.vertexForFragment('plain') != null) throw 'foreign vertex borrowed';
  rejects(function() return paths.vertexForFragment('../other/shaders/plain'), 'Invalid asset key');
  rejects(function() return paths.getPath(OTHER + '/images/missing.png'), 'Missing scoped asset');
  rejects(function() return paths.video('escape'), 'Missing scoped asset');
  rejects(function() return paths.obj('../other/plane'), 'Invalid asset key');
  sys.FileSystem.createDirectory(OWN + '/images/sparrow');
  sys.io.File.saveContent(OWN + '/images/sparrow/Animation.json', '{}');
  sys.io.File.saveContent(OWN + '/images/sparrow/spritemap1.json', '{}');
  sys.io.File.saveContent(OWN + '/images/sparrow/spritemap1.png', 'page');
  if (paths.image('sparrow').kind != 'animate') throw 'default image atlas detection';
  if (paths.image('sparrow', null, false) != OWN + '/images/sparrow.png') throw 'explicit raster';
  if (paths.getSparrowAtlas('sparrow').image != OWN + '/images/sparrow.png')
   throw 'explicit Sparrow loaded an Animate collection as bitmap';
  rejects(function() return paths.getSparrowAtlas('missing'), 'Missing Sparrow bitmap');
  rejects(function() return paths.image('escape'), 'escaped selected owner');
  rejects(function() return paths.image('AMBIGUOUS'), 'Ambiguous selected-owner image');
  rejects(function() return paths.image('../other/images/missing'), 'Invalid asset key');
  rejects(function() return paths.file('../other/images/missing.png'), 'Invalid asset key');
  rejects(function() return paths.file('images//../other/images/missing.png'), 'Invalid asset key');
  rejects(function() return paths.shaderImport('../other/foreign.frag'), 'Invalid asset key');
  rejects(function() return paths.getFolderContent('../other'), 'Invalid folder key');
  rejects(function() return paths.file('/images/plain.png'), 'Invalid asset key');
  rejects(function() return paths.file('images'), 'Missing scoped asset');
  sys.io.File.saveBytes(OWN + '/images/characters/bf/wolf/BF_Ice.png', haxe.io.Bytes.ofString('lowercase ice image'));
  sys.io.File.saveContent(OWN + '/images/characters/bf/wolf/BF_Ice.xml', '<TextureAtlas>lowercase ice</TextureAtlas>');
  if (paths.file('images/characters/BF/wolf/BF_Ice.xml') != OWN + '/images/characters/BF/wolf/BF_Ice.xml')
   throw 'exact-case full path must take precedence';
  rejects(function() return paths.file('images/Characters/BF/Wolf/BF_Ice.xml'), 'Ambiguous selected-owner asset');
 }
}'''.replace('OWN', json.dumps(str(own))).replace('OTHER', json.dumps(str(other))), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                     '-cp', str(base), '--run', 'Main'], cwd=ROOT,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
