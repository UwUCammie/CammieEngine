"""Nightmare Vision atlas caches never hand back frames whose graphic was destroyed.

A destroyed FlxGraphic empties its frame collections, so a stale cache entry
gave note splashes no animations and stopped the song with
"Missing historical animation". Dead entries are now dropped and reloaded,
and a splash without its lane animation is simply not shown.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionAtlasCacheLivenessTest(unittest.TestCase):
    def test_dead_cached_frames_are_dropped(self):
        paths = (ROOT / 'source/NightmareVisionPaths.hx').read_text(encoding='utf-8')
        live = method(paths, 'public function liveCachedFrames(')
        usable = method(paths, 'public static function usableFrames(')
        files = {
            'Graphic.hx': 'class Graphic {public var bitmap:Dynamic={};public function new(){}}',
            'FlxAtlasFrames.hx': 'class FlxAtlasFrames {public var frames:Array<Int>=[1,2];public var parent:Graphic=new Graphic();public function new(){}'
                                 'public function destroy(){frames=null;parent=null;}}',
            'Paths.hx': 'class Paths {public var tempAtlasFramesCache:Map<String, FlxAtlasFrames>=[];public function new(){}' + live + usable + '}',
            'Main.hx': r'''class Main {
 static function ok(v:Bool,m:String):Void if(!v)throw m;
 static function main(){
  var p=new Paths();var a=new FlxAtlasFrames();p.tempAtlasFramesCache.set('k',a);
  ok(p.liveCachedFrames('k')==a,'live frames are reused');
  a.destroy();
  ok(p.liveCachedFrames('k')==null&&!p.tempAtlasFramesCache.exists('k'),'destroyed frames are dropped');
  var empty=new FlxAtlasFrames();empty.frames=[];p.tempAtlasFramesCache.set('e',empty);
  ok(p.liveCachedFrames('e')==null,'empty frames are dropped');
  var gone=new FlxAtlasFrames();gone.parent.bitmap=null;p.tempAtlasFramesCache.set('g',gone);
  ok(p.liveCachedFrames('g')==null,'frames of a disposed bitmap are dropped');
  ok(p.liveCachedFrames('missing')==null,'unknown key');
 }
}''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            for name, text in files.items():
                (work / name).write_text(text, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
                                    cwd=work, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_atlas_cache_lookup_checks_liveness(self):
        paths = (ROOT / 'source/NightmareVisionPaths.hx').read_text(encoding='utf-8')
        # Only liveCachedFrames itself reads the cache directly.
        self.assertEqual(paths.count('tempAtlasFramesCache.get('), 1)
        self.assertIn('var cached = tempAtlasFramesCache.get(key);', method(paths, 'public function liveCachedFrames('))
        self.assertEqual(paths.count('var cached = liveCachedFrames(directPath);'), 3)
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        self.assertNotIn('nightmareVisionPaths.tempAtlasFramesCache.get(', play)
        self.assertIn('nightmareVisionPaths.liveCachedFrames(cacheKey)', play)

    def test_missing_lane_animation_hides_the_splash_instead_of_stopping_the_song(self):
        splash = (ROOT / 'source/NightmareVisionNoteSplash.hx').read_text(encoding='utf-8')
        self.assertNotIn('Missing historical animation', splash)
        self.assertIn('if (animation.curAnim == null) { kill(); return; }', splash)


if __name__ == '__main__':
    unittest.main()
