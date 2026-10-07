"""Full NV donor and immutable atlas metadata with actual host parent methods."""
from pathlib import Path
import re
import json
import xml.etree.ElementTree as ET
from source_alphabet_fixture_support import alphabet_fixture_files
from test_nv_multifield_routes import method
ROOT = Path(__file__).resolve().parents[2]

def nv_alphabet_fixture_files():
    files = alphabet_fixture_files()
    for name in ['DonorAlphabet.hx', 'DonorAttachedText.hx', 'DonorPathsAtlas.hx', 'AlphabetIO.hx']:
        files.pop(name, None)
    native = ROOT / '.haxelib/flixel/6,1,2/flixel'
    math = (native / 'math/FlxMath.hx').read_text(encoding='utf-8')
    files['flixel/math/FlxMath.hx'] = files['flixel/math/FlxMath.hx'][:-1] + method(math, 'public static function getElapsedLerp(') + method(math, 'public static inline function absInt(') + '}'
    xml = (ROOT.parent / 'fnf_sources/NightmareVision/assets/game/images/alphabet.xml').read_text(encoding='utf-8')
    frame = (native / 'graphics/frames/FlxFrame.hx').read_text(encoding='utf-8')
    sort = method(frame, 'public static function sortByName(')
    files['flixel/graphics/frames/FlxAtlasFrames.hx'] = '''package flixel.graphics.frames;import flixel.math.FlxMath;
class FlxAtlasFrames {public var frames:Array<FlxFrame>=[];public function new(){var root=Xml.parse(__XML__).firstElement();for(e in root.elementsNamed("SubTexture")){var r={name:e.get("name"),w:Std.parseInt(e.exists("frameWidth")?e.get("frameWidth"):e.get("width")),h:Std.parseInt(e.exists("frameHeight")?e.get("frameHeight"):e.get("height")),trimX:Std.parseInt(e.exists("frameX")?e.get("frameX"):"0"),trimY:Std.parseInt(e.exists("frameY")?e.get("frameY"):"0")};frames.push(new FlxFrame(r));}}}
class FlxFrame {public var name:String;public var w:Int;public var h:Int;public var trimX:Int;public var trimY:Int;public function new(r:Dynamic){name=r.name;w=r.w;h=r.h;trimX=r.trimX;trimY=r.trimY;}public static function sortFrames(f:Array<FlxFrame>,p:String,s:String){haxe.ds.ArraySort.sort(f,function(a,b)return sortByName(a,b,p.length,s.length));}__SORT__}
'''.replace('__XML__', json.dumps(xml)).replace('__SORT__', sort)
    animation = (native / 'animation/FlxAnimationController.hx').read_text(encoding='utf-8')
    old = 'function byPrefixHelper(a:Array<Int>,f:Array<FlxFrame>,p:String){for(v in f)a.push((_sprite.frames.frames:Array<FlxFrame>).indexOf(v));}'
    files['IconAnimation.hx'] = files['IconAnimation.hx'].replace(old, method(animation, 'function byPrefixHelper(')).replace('public function clear()', 'function getFrameIndex(f:FlxFrame)return (_sprite.frames.frames:Array<FlxFrame>).indexOf(f);public function clear()')
    sprite = files['flixel/FlxSprite.hx']
    begin = sprite.index('function set_frames(')
    end = sprite.index('public var frame:Dynamic;', begin)
    sprite = sprite[:begin] + 'function set_frames(v:Dynamic){frames=v;animation.clear();if(v!=null && v.frames.length>0){frame=v.frames[0];width=frameWidth;height=frameHeight;}return v;}public var frame(default,set):Dynamic;function set_frame(v:Dynamic){frame=v;if(v!=null){frameWidth=v.w;frameHeight=v.h;}return v;}' + sprite[end + len('public var frame:Dynamic;'):]
    sprite = sprite.replace('public function setGraphicSize(w:Int,h:Int){scale.set(w/frameWidth,h/frameHeight);}', method((native / 'FlxSprite.hx').read_text(encoding='utf-8'), 'public function setGraphicSize('))
    sprite = sprite.replace('public function updateHitbox(){width=frameWidth*scale.x;height=frameHeight*scale.y;}', method((native / 'FlxSprite.hx').read_text(encoding='utf-8'), 'public function updateHitbox('))
    sprite = sprite.replace('public var offset=', 'public var origin=new FlxPoint();public function centerOrigin(){origin.set(frameWidth*.5,frameHeight*.5);}public var offset=')
    files['flixel/FlxSprite.hx'] = sprite
    files['flixel/FlxG.hx'] = files['flixel/FlxG.hx'].replace('public static var width=1280;', 'public static var width=1280;public static var height=720;')
    files['flixel/util/FlxTimer.hx'] = 'package flixel.util;class FlxTimer {public var loops:Int=0;public var destroyed=0;public function new(){}public function destroy(){destroyed++;}}'
    files['flixel/sound/FlxSound.hx'] = 'package flixel.sound;class FlxSound {}'
    files['NvAlphabetIO.hx'] = 'class NvAlphabetIO {var cached:flixel.graphics.frames.FlxAtlasFrames;public var loads=0;public var fail=false;public function new(){}public function atlas(s:String):flixel.graphics.frames.FlxAtlasFrames {loads++;if(fail)throw "missing-atlas";if(cached==null)cached=new flixel.graphics.frames.FlxAtlasFrames();return cached;}public function owner():NightmareVisionAlphabetOwner return {atlas:atlas};}'
    files['Paths.hx'] = 'class Paths {public static var io:NvAlphabetIO;public static function getSparrowAtlas(s:String)return io.atlas(s);}'
    files['ClientPrefs.hx'] = 'class ClientPrefs {}'
    files.pop('openfl/utils/Assets.hx', None)
    source = (ROOT.parent / 'fnf_sources/NightmareVision/source/funkin/objects/Alphabet.hx').read_text(encoding='utf-8')
    source = re.sub(r'^package[^\n]*\n', '', source, flags=re.M).replace('import openfl.media.Sound;', 'import flixel.sound.FlxSound;')
    source = re.sub(r'\bAlphabet\b', 'DonorNVAlphabet', source)
    source = re.sub(r'\bAlphaCharacter\b', 'DonorNVAlphaCharacter', source).replace('override function update', 'override public function update')
    files['DonorNVAlphabet.hx'] = source
    return files
