"""Reusable typed attachment dependencies and complete immutable donor classes."""
from pathlib import Path
import re
from source_icon_fixture_support import source_icon_fixture_files
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]

def attachment_fixture_files():
    files=source_icon_fixture_files()
    for name in ['Main.hx','DonorPsychIcon.hx','DonorNVIcon.hx','Context.hx']:
        files.pop(name, None)
    flixel=ROOT/'.haxelib/flixel/6,1,2/flixel'
    files['flixel/util/FlxAxes.hx']=(flixel/'util/FlxAxes.hx').read_text()
    files['flixel/FlxBasic.hx']=files['flixel/FlxBasic.hx'].replace('public function update(e:Float){updates++;}', 'public var onUpdate:Void->Void;public function update(e:Float){updates++;if(onUpdate!=null)onUpdate();}')
    files['flixel/FlxObject.hx']='package flixel;class FlxObject extends FlxBasic {public var x(default,set)=0.;public var y(default,set)=0.;public var width=1.;public var height=1.;public var angle=0.;public var scrollFactor=new flixel.math.FlxPoint(1,1);public function new(x=0.,y=0.){super();this.x=x;this.y=y;}public function set_x(v:Float)return x=v;public function set_y(v:Float)return y=v;public function setPosition(x:Float,y:Float){this.x=x;this.y=y;}}'
    sprite=files['flixel/FlxSprite.hx'].replace('extends FlxBasic', 'extends FlxObject')
    for text in ['public var x(default,set)=0.;','public var y(default,set)=0.;','public var width=1.;','public var height=1.;','public var scrollFactor=new FlxPoint(1,1);','public function set_x(v:Float)return x=v;','public function set_y(v:Float)return y=v;','public function setPosition(x:Float,y:Float){this.x=x;this.y=y;}']:
        sprite=sprite.replace(text,'')
    alpha=method((flixel/'FlxSprite.hx').read_text(),'function set_alpha(').replace('function set_alpha','public function set_alpha')
    sprite=sprite.replace('public function set_alpha(v:Float)return alpha=v;',alpha)
    files['flixel/FlxSprite.hx']=sprite.replace('import flixel.math.FlxPoint;', 'import flixel.math.FlxMath;import flixel.math.FlxPoint;').replace('public function updateMotion', 'public function updateColorTransform(){}public function updateMotion')
    files['flixel/graphics/frames/FlxAtlasFrames.hx']='package flixel.graphics.frames;class FlxAtlasFrames {public var frames:Array<FlxFrame>;public function new(){frames=[new FlxFrame("idle0000"),new FlxFrame("idle0001")];}}class FlxFrame {public var name:String;public function new(n:String)name=n;}'
    prefix=method((flixel/'animation/FlxAnimationController.hx').read_text(),'public function addByPrefix(')
    files['IconAnimation.hx']='import flixel.graphics.frames.FlxAtlasFrames.FlxFrame;'+files['IconAnimation.hx'].replace('public function addByPrefix(a:String,b:String,c:Int,d:Bool):Void{}', '').replace('public function clear()',prefix+' function findByPrefix(a:Array<FlxFrame>,p:String){for(f in (_sprite.frames.frames:Array<FlxFrame>))if(StringTools.startsWith(f.name,p))a.push(f);}function byPrefixHelper(a:Array<Int>,f:Array<FlxFrame>,p:String){for(v in f)a.push((_sprite.frames.frames:Array<FlxFrame>).indexOf(v));}public function clear()')
    files['AttachmentContext.hx']='class AttachmentContext {public var log:Array<String>=[];public var aa=false;public var fail=false;public function new(){}public function image(s:String,f:Null<String>):flixel.graphics.FlxGraphic {log.push("image:"+s+":"+f);if(fail)throw "load-failed";return new flixel.graphics.FlxGraphic(33,27);}public function atlas(s:String,f:Null<String>):flixel.graphics.frames.FlxAtlasFrames {log.push("atlas:"+s+":"+f);if(fail)throw "load-failed";return new flixel.graphics.frames.FlxAtlasFrames();}public function owner():SourceAttachedSpriteOwner return {image:image,sparrowAtlas:atlas,antialiasing:function(){log.push("aa");return aa;}};}'
    files['Paths.hx']='class Paths {public static var ctx:AttachmentContext;public static function image(s:String,?f:String)return ctx.image(s,f);public static function getSparrowAtlas(s:String,?f:String)return ctx.atlas(s,f);}'
    files['ClientPrefs.hx']='class ClientPrefs {public static var data(get,never):Dynamic;static function get_data(){Paths.ctx.log.push("aa");return {antialiasing:Paths.ctx.aa};}}'
    psych=(ROOT.parent/'fnf_sources/FNF-PsychEngine/source/objects/AttachedSprite.hx').read_text()
    psych=re.sub(r'^package[^\n]*\n','',psych,flags=re.M).replace('class AttachedSprite','class DonorPsychAttachedSprite').replace('override function update','override public function update')
    files['DonorPsychAttachedSprite.hx']='import flixel.FlxSprite;'+psych
    nv=(ROOT.parent/'fnf_sources/NightmareVision/source/funkin/objects/nodes/AttachedNode.hx').read_text()
    nv=re.sub(r'^package[^\n]*\n','',nv,flags=re.M).replace('AttachedNode','DonorNVAttachedNode').replace('AttachedSprite','DonorNVAttachedSprite').replace('override function','override public function')
    files['DonorNVAttachedNode.hx']='import flixel.FlxBasic;import flixel.FlxSprite;import flixel.math.FlxPoint;'+nv
    return files
