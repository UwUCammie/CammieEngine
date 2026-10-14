"""Psych stage JSON `objects` and `preload`: draw order, filters and what gets built."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function describe(list:Array<SourceStageObjects.SourceStageObjectPlan>):String
  return [for (o in list) o.name + '>' + (o.behind == null ? 'front' : o.behind)].join(',');
 static function objects():Array<Dynamic> return [
  {type:'sprite', name:'sky', image:'stages/sky', x:-100, y:-50, scroll:[0.2, 0.2], filters:3},
  {type:'gf'},
  {type:'animatedSprite', name:'crowd', image:'stages/crowd', x:10, y:20, scroll:[0.9, 0.9], filters:3, scale:[1.5, 1.5],
   firstAnimation:'cheer', animations:[
    {anim:'idle', name:'crowd idle', fps:24, loop:true, offsets:[0, 0]},
    {anim:'cheer', name:'crowd cheer', fps:12, loop:false, indices:[0, 1, 2], offsets:[5, -5]}
   ]},
  {type:'dad'},
  {type:'square', name:'fog', x:0, y:0, scroll:[1, 1], filters:1, color:'FF0000'},
  {type:'boyfriendGroup'},
  {type:'sprite', name:'lamp', image:'stages/lamp', x:0, y:0, scroll:[1, 1], filters:3, alpha:0.5, flipX:true},
  {type:'mystery', name:'skipped'}
 ];
 static function main():Void {
  var high = SourceStageObjects.plan(objects(), false, false, false);
  check(describe(high) == 'sky>gf,crowd>dad,lamp>front', 'high quality order ' + describe(high));
  var low = SourceStageObjects.plan(objects(), true, false, false);
  check(describe(low) == 'sky>gf,crowd>dad,fog>boyfriend,lamp>front', 'low quality order ' + describe(low));
  // With no girlfriend placed, the sky sits behind the next character instead.
  check(describe(SourceStageObjects.plan(objects(), false, false, true)) == 'sky>dad,crowd>dad,lamp>front', 'hidden gf marker');

  var crowd = high[1];
  check(crowd.animations.length == 2 && crowd.firstAnimation == 'cheer', 'first animation');
  check(crowd.animations[0].indices == null && crowd.animations[1].indices.join(',') == '0,1,2', 'indices');
  check(crowd.animations[1].fps == 12 && !crowd.animations[1].loop && crowd.animations[1].offsets[0] == 5, 'animation fields');
  check(crowd.scale[0] == 1.5 && crowd.scroll[0] == 0.9 && crowd.x == 10, 'transform');
  check(high[2].alpha == 0.5 && high[2].flipX == true && high[2].flipY == null, 'optional fields stay null when absent');
  check(low[2].type == 'square' && low[2].image == '' && low[2].antialiasing == false && low[2].color == 'FF0000', 'square');

  // Without a firstAnimation the first one added plays.
  var plain = SourceStageObjects.plan([{type:'animatedSprite', name:'a', image:'a', animations:[{anim:'one', name:'one'}, {anim:'two', name:'two'}]}], false, false, false);
  check(plain[0].firstAnimation == 'one' && plain[0].animations[0].fps == 24, 'default first animation and fps');
  var unnamed = SourceStageObjects.plan([{type:'square'}, {type:'square', name:''}], false, false, false);
  check(unnamed[0].name == 'stage-object-0' && unnamed[1].name == 'stage-object-1', 'unnamed entries still get a tag');

  // Psych's own filter check: freeplay only matters together with the story bit.
  check(SourceStageObjects.visible(3, false, false) && SourceStageObjects.visible(null, true, false), 'quality bits');
  check(!SourceStageObjects.visible(1, false, false) && !SourceStageObjects.visible(2, true, false), 'wrong quality hidden');
  check(!SourceStageObjects.visible(2 | 4, false, false) && SourceStageObjects.visible(2 | 4, false, true), 'story only');
  check(SourceStageObjects.visible(2 | 8, false, true), 'freeplay bit alone is ignored, as in Psych');
  check(!SourceStageObjects.visible(2 | 4 | 8, false, true), 'story and freeplay together hide in story mode');

  var preload = SourceStageObjects.preloadPlan({'images/stages/sky':3, ' sounds/thunder ':-1, 'music/ambience':1,
   'images/stages/sky ':3, 'data/skip':3, 'images/story':6}, false, false);
  check(preload.images.join(',') == 'stages/sky', 'preload images ' + preload.images.join(','));
  check(preload.sounds.join(',') == 'thunder' && preload.music.length == 0, 'negative filters always load; low only skipped');
 }
}
'''


# The real builder runs against stub sprite and Lua-registry calls, so the
# order of what it does to each sprite and where it layers them is checked.
BUILD_MAIN = r'''
class Pair { public var x:Float = 0; public var y:Float = 0; var log:Array<String>; var what:String;
 public function new(log:Array<String>, what:String) {this.log = log; this.what = what;}
 public function set(x:Float, y:Float):Void {this.x = x; this.y = y; log.push(what + ':' + x + ',' + y);} }
class Sprite {
 public var tag:String; public var log:Array<String> = [];
 public var offset:Pair; public var scale:Pair; public var scrollFactor:Pair;
 public var flipX = false; public var flipY = false; public var antialiasing = true;
 public var color:Int = 0xFFFFFFFF; public var alpha:Float = 1; public var angle:Float = 0;
 public function new(tag:String) {this.tag = tag; offset = new Pair(log, 'offset'); scale = new Pair(log, 'scale'); scrollFactor = new Pair(log, 'scroll');}
 public function makeGraphic(w:Int, h:Int, c:Int):Void log.push('graphic:' + w + 'x' + h);
 public function updateHitbox():Void log.push('hitbox');
}
class FlxColor { public static inline var WHITE:Int = 0xFFFFFFFF; }
class OptionsHandler { public static var options = {antialiasing:true}; }
class Host {
 var BEHIND_NONE = 0; var BEHIND_GF = 1; var BEHIND_BF = 1 << 1; var BEHIND_DAD = 1 << 2;
 var isStoryMode = false;
 public var calls:Array<String> = []; public var sprites:Map<String, Sprite> = new Map(); public var layers:Array<String> = [];
 public function new() {}
 function make(owner:String, tag:String, image:String, x:Float, y:Float, kind:String):Sprite {
  calls.push(kind + ':' + owner + ':' + tag + ':' + image + '@' + x + ',' + y);
  var sprite = new Sprite(tag); sprites.set(tag, sprite); return sprite;
 }
 function compatMakeLuaSpriteForOwner(o:String, t:String, i:String, x:Float = 0, y:Float = 0):Sprite return make(o, t, i, x, y, 'sprite');
 function compatMakeAnimatedLuaSpriteForOwner(o:String, t:String, i:String, x:Float = 0, y:Float = 0):Sprite return make(o, t, i, x, y, 'atlas');
 function compatAddAnimationByPrefix(t:Dynamic, a:String, p:String, fps:Float, loop:Bool):Void sprites.get(t).log.push('prefix:' + a + ':' + p + ':' + fps + ':' + loop);
 function compatAddAnimationByIndices(t:Dynamic, a:String, p:String, i:Dynamic, fps:Float, loop:Bool):Void sprites.get(t).log.push('indices:' + a + ':' + Std.string(i) + ':' + fps);
 function compatPlayAnim(t:Dynamic, a:String, forced:Bool = false):Void sprites.get(t).log.push('play:' + a + ':' + forced);
 function compatPrecacheImageForOwner(o:String, p:String):Void calls.push('image:' + o + ':' + p);
 function compatPrecacheSoundForOwner(o:String, p:String):Void calls.push('sound:' + o + ':' + p);
 function compatPrecacheMusicForOwner(o:String, p:String):Void calls.push('music:' + o + ':' + p);
 function compatParseColor(v:Dynamic):Dynamic return v == 'FF0000' ? 0xFFFF0000 : null;
 function addHscriptSprite(s:Dynamic, position:Null<Int>):Void layers.push((cast s:Sprite).tag + '>' + position);
 __BUILD__
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var host = new Host();
  var meta = SourceStageMetadata.parse({objects:[
   {type:'sprite', name:'sky', image:'stages/sky', x:-100, y:-50, scroll:[0.2, 0.3], filters:3, antialiasing:false},
   {type:'gf'},
   {type:'animatedSprite', name:'crowd', image:'stages/crowd', x:10, y:20, scroll:[0.9, 0.9], filters:3, scale:[1.5, 1.5],
    firstAnimation:'cheer', animations:[
     {anim:'idle', name:'crowd idle', fps:24, loop:true, offsets:[0, 0]},
     {anim:'cheer', name:'crowd cheer', fps:12, loop:false, indices:[0, 1, 2], offsets:[5, -5]}
    ]},
   {type:'dad'},
   {type:'square', name:'fog', x:0, y:0, scroll:[1, 1], color:'FF0000', alpha:0.25},
   {type:'boyfriend'},
   {type:'sprite', name:'lamp', image:'stages/lamp', x:0, y:0, scroll:[1, 1], filters:1}
  ], preload:{'images/stages/sky':3, 'sounds/thunder':-1, 'music/low':1}});
  host.buildSourceStageObjects(meta, 'owner');
  check(host.calls.join('|') == 'image:owner:stages/sky|sound:owner:thunder|'
   + 'sprite:owner:sky:stages/sky@-100,-50|atlas:owner:crowd:stages/crowd@10,20|sprite:owner:fog:@0,0', 'calls ' + host.calls.join('|'));
  // Each sprite sits behind the character that follows it; the low quality lamp is skipped.
  check(host.layers.join(',') == 'sky>1,crowd>4,fog>2', 'layers ' + host.layers.join(','));
  var sky = host.sprites.get('sky');
  check(!sky.antialiasing && sky.scrollFactor.x == 0.2 && sky.scrollFactor.y == 0.3, 'sky fields');
  // Psych plays the first animation's offset, then scales, and updateHitbox comes last.
  check(host.sprites.get('crowd').log.join('|') == 'prefix:idle:crowd idle:24:true|indices:cheer:[0,1,2]:12|play:cheer:true|'
   + 'offset:5,-5|scale:1.5,1.5|hitbox|scroll:0.9,0.9', 'crowd ' + host.sprites.get('crowd').log.join('|'));
  var fog = host.sprites.get('fog');
  check(fog.log[0] == 'graphic:1x1' && !fog.antialiasing && fog.color == 0xFFFF0000 && fog.alpha == 0.25, 'square fields');
 }
}
'''


class PsychStageJsonFieldsTest(unittest.TestCase):
    def test_builder_layers_and_configures_each_sprite_like_psych(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        build = extract_method(play, '\tfunction buildSourceStageObjects(').replace('\tfunction ', '\tpublic function ', 1)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = FixturePath(folder)
            (work / 'Host.hx').write_text(BUILD_MAIN.replace('__BUILD__', build), newline='\n')
            for name in ('SourceStageObjects.hx', 'SourceStageMetadata.hx'):
                (work / name).write_text((ROOT / 'source' / name).read_text(encoding='utf-8'), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Host', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_objects_plan_keeps_draw_order_filters_and_animations(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = FixturePath(folder)
            (work / 'Main.hx').write_text(MAIN, newline='\n')
            (work / 'SourceStageObjects.hx').write_text(
                (ROOT / 'source/SourceStageObjects.hx').read_text(encoding='utf-8'), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_json_builds_objects_once_before_the_camera_refresh(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        apply = extract_method(play, 'function applyPsychStageJson(')
        self.assertIn('if (!psychStageObjectsBuilt && (meta.objects != null || meta.preload != null)) {', apply)
        self.assertLess(apply.index('buildSourceStageObjects(meta, scopedRoot);'), apply.index('refreshPsychStageCameraTarget();'))
        build = extract_method(play, 'function buildSourceStageObjects(')
        # Sprites use the owner-scoped Lua sprite registry so scripts can find them by name.
        self.assertIn('compatMakeAnimatedLuaSpriteForOwner(ownerRoot, tag', build)
        self.assertIn('compatMakeLuaSpriteForOwner(ownerRoot, tag', build)
        self.assertIn("case 'gf': BEHIND_GF;", build)
        self.assertIn('default: BEHIND_NONE;', build)
        self.assertIn('compatPrecacheImageForOwner(ownerRoot, image);', build)
        # Psych's preload and object filters see this engine as high quality.
        self.assertIn('SourceStageObjects.plan(meta.objects, false, isStoryMode, meta.hideGirlfriend)', build)


if __name__ == '__main__':
    unittest.main()
