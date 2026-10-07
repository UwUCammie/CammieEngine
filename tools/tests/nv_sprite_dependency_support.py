"""Native-shaped compile dependencies for real targeted NV macro receiver fixtures."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]

def add_native_sprite_dependencies(files):
    from test_nv_multifield_routes import method
    native = ROOT / '.haxelib/flixel/6,1,2/flixel'
    color = (native / 'util/FlxColor.hx').read_text(encoding='utf-8')
    channels = ''.join(method(color, n) for n in ['inline function getThis(', 'inline function get_red(', 'inline function get_green(', 'inline function get_blue(', 'inline function get_alpha(', 'public inline function toHexString('])
    files['flixel/util/FlxColor.hx'] = 'package flixel.util;abstract FlxColor(Int) from Int to Int {public static inline var WHITE:Int=-1;public static inline var BLACK:Int=0xFF000000;public var red(get,never):Int;public var green(get,never):Int;public var blue(get,never):Int;public var alpha(get,never):Int;' + channels + '}'
    files.setdefault('flixel/graphics/frames/FlxAtlasFrames.hx', 'package flixel.graphics.frames;class FlxAtlasFrames {public function new(){}}')
    files.setdefault('flixel/system/FlxAssets.hx', 'package flixel.system;typedef FlxGraphicAsset=Dynamic;')
    files.setdefault('flixel/util/FlxAxes.hx', (native / 'util/FlxAxes.hx').read_text(encoding='utf-8'))
    files.setdefault('flixel/FlxObject.hx', 'package flixel;typedef FlxObject=FlxSprite;')
    files.setdefault('flixel/FlxSprite.hx', 'package flixel;class FlxSprite {public var x:Float;public var y:Float;public var width=0.;public var height=0.;public var destroyed=false;public function new(x=0.,y=0.){this.x=x;this.y=y;}public function destroy():Void destroyed=true;}')
    sprite = files['flixel/FlxSprite.hx']
    fields = ''
    for name, definition in [('width','public var width=0.;'),('height','public var height=0.;'),('active','public var active=true;'),('frames','public var frames:Dynamic;'),('animation','public var animation:Dynamic={curAnim:null,addByPrefix:function(a:String,b:String,c:Int,d:Bool){},play:function(a:String){}};'),('scale','public var scale=new FixtureMacroScale();')]:
        if not re.search(r'public var '+name+r'\b', sprite): fields += definition
    sprite = sprite.replace('class FlxSprite {', 'class FlxSprite {' + fields)
    if 'FixtureMacroScale' in fields: sprite += 'class FixtureMacroScale {public var x=1.;public var y=1.;public function new(){}public function set(x=1.,y=1.){this.x=x;this.y=y;return this;}}'
    if 'function updateHitbox(' not in sprite: sprite = sprite.replace('class FlxSprite {', 'class FlxSprite {public function updateHitbox():Void{}')
    if 'function makeGraphic(' not in sprite: sprite = sprite.replace('class FlxSprite {', 'class FlxSprite {public function makeGraphic(w:Int,h:Int,c:Int=-1,unique:Bool=false,?key:String):FlxSprite{width=w;height=h;return this;}')
    # Existing fixture geometry bodies remain intact; only native optional arguments expand.
    sprite = re.sub(r'function makeGraphic\((width|w):Int,(height|h):Int,color:Int\)', r'function makeGraphic(\1:Int,\2:Int,color:Int=-1,unique:Bool=false,?key:String)', sprite)
    sprite = re.sub(r'function new\(\) scrollFactor=', 'function new(x:Float=0,y:Float=0) scrollFactor=', sprite)
    if 'function loadGraphic(' not in sprite: sprite = sprite.replace('class FlxSprite {', 'class FlxSprite {public function loadGraphic(g:Dynamic,a:Bool=false,w:Int=0,h:Int=0,u:Bool=false,?key:String):FlxSprite return this;')
    files['flixel/FlxSprite.hx'] = sprite
    files.setdefault('NightmareVisionPaths.hx', 'class NightmareVisionPaths {public var root="fixture";public function new(){}public function image(p:String):Dynamic return p;public function getAtlasFrames(p:String):flixel.graphics.frames.FlxAtlasFrames return new flixel.graphics.frames.FlxAtlasFrames();}')
    return files
