"""Owner-local icon dependencies and actual pinned animation methods."""
from pathlib import Path
import re
from test_nv_multifield_routes import method
from source_bar_fixture_support import bar_fixture_files
ROOT=Path(__file__).resolve().parents[2]

def source_icon_fixture_files():
    files = bar_fixture_files()
    files['flixel/system/frontEnds/CameraFrontEnd.hx'] = """package flixel.system.frontEnds;
class CameraFrontEnd {
 public var list:Array<Dynamic>=[];
 public function new() {}
 public function add(camera:Dynamic,defaultDrawTarget:Bool=true):Dynamic {
  if(camera==null)throw "fixture native add received null";
  list.push(camera);return camera;
 }
 public function insert(camera:Dynamic,position:Int,defaultDrawTarget:Bool=true):Dynamic {
  if(camera==null)throw "fixture native insert received null";
  list.insert(position,camera);return camera;
 }
}"""
    flixel = ROOT / '.haxelib/flixel/6,1,2/flixel'
    controller = (flixel / 'animation/FlxAnimationController.hx').read_text()
    animation = (flixel / 'animation/FlxAnimation.hx').read_text()
    base = (flixel / 'animation/FlxBaseAnimation.hx').read_text()
    controller_methods = '\n'.join(method(controller, n) for n in ['public function add(', 'public function play(', 'function set_frameIndex(', 'function fireCallback(', 'function fireFinishCallback('])
    controller_methods = controller_methods.replace('function fireFinishCallback', 'public function fireFinishCallback')
    files['IconAnimation.hx'] = '''import flixel.util.FlxSignal.FlxTypedSignal;
class FlxG {public static var log={warn:function(v:String){}};public static var random={int:function(a:Int,b:Int)return a};}
class IconAnimation {public var _sprite:flixel.FlxSprite;public var _animations:Map<String,FlxAnimation>=[];public var _curAnim:FlxAnimation;public var curAnim(get,never):FlxAnimation;function get_curAnim()return _curAnim;public var numFrames(get,never):Int;function get_numFrames()return _sprite.frames==null?0:_sprite.frames.frames.length;public var frameIndex(default,set)=0;public var callback:String->Int->Int->Void;public var finishCallback:String->Void;public var onFrameChange=new FlxTypedSignal<String->Int->Int->Void>();public var onFinish=new FlxTypedSignal<String->Void>();public function new(s:flixel.FlxSprite)_sprite=s;public function addByPrefix(a:String,b:String,c:Int,d:Bool):Void{}public function clear(){_animations=[];_curAnim=null;}__METHODS__}
class FlxAnimation {public var parent:IconAnimation;public var name:String;public var frames:Array<Int>;public var curFrame(default,set)=0;public var curIndex(default,set)=0;public var numFrames(get,never):Int;function get_numFrames()return frames.length;public var flipX:Bool;public var flipY:Bool;public var looped:Bool;public var reversed=false;public var finished=true;public var paused=true;public var frameDuration=0.;var _frameTimer=0.;public function new(p:IconAnimation,n:String,f:Array<Int>,rate:Float,l:Bool,x:Bool,y:Bool){parent=p;name=n;frames=f;frameDuration=rate==0?0:1/rate;looped=l;flipX=x;flipY=y;}__PLAY__ __FRAME__ __INDEX__ public function stop(){finished=true;paused=true;}}
'''.replace('__METHODS__', controller_methods).replace('__PLAY__', method(animation, 'public function play(')).replace('__FRAME__', method(animation, 'function set_curFrame(')).replace('__INDEX__', method(base, 'function set_curIndex('))
    sprite = files['flixel/FlxSprite.hx'].replace('public var frames:Dynamic;public var animation:Dynamic={curAnim:null,addByPrefix:function(a:String,b:String,c:Int,d:Bool){},play:function(a:String){}};', '')
    sprite = sprite.replace('public var path:Dynamic;', 'public var offset=new FlxPoint();public var dirty=false;public var frames:Dynamic;public var frame:Dynamic;public var animation:IconAnimation;public var graphic:FlxGraphic;public var path:Dynamic;')
    sprite = sprite.replace('super();this.x=x;', 'super();animation=new IconAnimation(this);this.x=x;')
    old = 'public function loadGraphic(g:Dynamic,animated:Bool=false,w:Int=0,h:Int=0,unique:Bool=false,?key:String):FlxSprite{frameWidth=g.width;frameHeight=g.height;updateHitbox();return this;}'
    new = 'public function loadGraphic(g:Dynamic,animated:Bool=false,w:Int=0,h:Int=0,unique:Bool=false,?key:String):flixel.FlxSprite{graphic=g;animation.clear();frameWidth=w==0?g.width:w;frameHeight=h==0?g.height:h;frames={frames:[for(i in 0...(Std.int(g.width/frameWidth)*Std.int(g.height/frameHeight))){name:"cell"+i}]};frame=frames.frames[0];updateHitbox();return this;}'
    files['flixel/FlxSprite.hx'] = sprite.replace(old, new)
    files['flixel/math/FlxPoint.hx'] = files['flixel/math/FlxPoint.hx'].replace('public var x:Float;', 'public var puts=0;public static function get(x=0.,y=0.)return new FlxPoint(x,y);public function put(){puts++;}public var x:Float;')
    files['flixel/math/FlxPoint.hx'] = files['flixel/math/FlxPoint.hx'].replace('class FlxPoint {', 'class FlxPoint implements flixel.util.FlxPool.IFlxPooled {public function destroy():Void{}')
    files['flixel/util/FlxPool.hx'] = 'package flixel.util;interface IFlxPooled extends flixel.util.FlxDestroyUtil.IFlxDestroyable {public function put():Void;}'
    files['flixel/util/FlxDestroyUtil.hx'] = 'package flixel.util;import flixel.util.FlxPool.IFlxPooled;interface IFlxDestroyable {public function destroy():Void;}class FlxDestroyUtil {' + '\n'.join(method((flixel / 'util/FlxDestroyUtil.hx').read_text(), n) for n in ['public static function destroy<', 'public static function destroyArray<', 'public static function put<']) + '}'
    files['flixel/util/IFlxDestroyable.hx'] = 'package flixel.util;typedef IFlxDestroyable=flixel.util.FlxDestroyUtil.IFlxDestroyable;'
    files['flixel/util/FlxSignal.hx'] = (flixel / 'util/FlxSignal.hx').read_text()
    files.pop('flixel/util/IFlxDestroyable.hx')
    for name in list(files):
        files[name] = files[name].replace('flixel.util.IFlxDestroyable', 'flixel.util.FlxDestroyUtil.IFlxDestroyable')
    files['Paths.hx'] = '''class Paths {public static var ctx:Context;public static var UI_PREFIX(get,never):String;static function get_UI_PREFIX()return ctx.prefix;public static function fileExists(p:String,?type:Dynamic):Bool return ctx.exists(p);public static function image(p:String,?a:Dynamic,?b:Bool):flixel.graphics.FlxGraphic return ctx.image(p,b==null?(a==null?true:a):b);}'''
    files['ClientPrefs.hx'] = 'class ClientPrefs {public static var data:Dynamic={antialiasing:false};public static var globalAntialiasing(get,never):Bool;static function get_globalAntialiasing()return Paths.ctx.aa;}'
    files['Context.hx'] = '''class Context {public var prefix="UI/custom/";public var aa=false;public var files:Map<String,Bool>=[];public var log:Array<String>=[];public var w=360;public var h=160;public var fail=false;public function new(){}public function exists(p:String):Bool {log.push("exists:"+p);return files.exists(p);}public function image(p:String,gpu:Bool):flixel.graphics.FlxGraphic {log.push("image:"+p+":"+gpu);if(fail)throw "asset-failed";return new flixel.graphics.FlxGraphic(w,h);}public function owner():SourceHealthIconOwner return {exists:exists,image:image,uiPrefix:function()return prefix,antialiasing:function()return aa};}'''
    imports = 'import flixel.FlxSprite;import flixel.math.FlxPoint;import flixel.math.FlxMath;import flixel.util.FlxDestroyUtil;using StringTools;\n'
    for name, path in [('DonorPsychIcon', 'FNF-PsychEngine/source/objects/HealthIcon.hx'), ('DonorNVIcon', 'NightmareVision/source/funkin/objects/HealthIcon.hx')]:
        source = (ROOT.parent / 'fnf_sources' / path).read_text()
        source = re.sub(r'^(package|import)[^\n]*\n', '', source, flags=re.M)
        source = source.replace('class HealthIcon extends', 'class ' + name + ' extends').replace(':HealthIcon', ':' + name).replace('implements IUiSprite', 'implements NightmareVisionIUiSprite')
        for fn in ['update(', 'updateHitbox(', 'destroy(']:
            source = source.replace('override function ' + fn, 'override public function ' + fn)
        files[name + '.hx'] = imports + ('final IMAGE:Dynamic=null;\n' if name == 'DonorPsychIcon' else '') + source
    files['Main.hx'] = r'''
class Main {
 static function ok(v:Bool,m:String)if(!v)throw m;
 static function property(o:Dynamic,k:String):Dynamic return Reflect.getProperty(o,k);
 static function set(o:Dynamic,k:String,v:Dynamic)Reflect.setProperty(o,k,v);
 static function make(host:Bool,nv:Bool,c:Context,player:Bool):Dynamic {Paths.ctx=c;ClientPrefs.data.antialiasing=c.aa;return nv?(host?new NightmareVisionHealthIcon("test",player,c.owner()):new DonorNVIcon("test",player)):(host?new PsychSourceHealthIcon("test",player,false,c.owner()):new DonorPsychIcon("test",player,false));}
 static function snapshot(i:Dynamic):String {var a:IconAnimation=i.animation;var s:flixel.FlxSprite=cast i;var v:Array<Dynamic>=[s.width,s.height,s.frameWidth,s.frameHeight,s.offset.x,s.offset.y,s.scale.x,s.alpha,s.x,s.y,s.antialiasing,s.scrollFactor.x,s.scrollFactor.y,a.frameIndex,a.curAnim.name,a.curAnim.frames.join(","),a.curAnim.flipX];return v.join("|");}
 static function scenario(host:Bool,nv:Bool,n:Int):String {var c=new Context();if(n==0)c.files.set("images/"+(nv?c.prefix:"")+"icons/test.png",true);if(n==1)c.files.set("images/"+(nv?c.prefix:"")+"icons/icon-test.png",true);if(n==2)c.files.set("images/"+(nv?c.prefix:"")+"icons/icon-face.png",true);var i=make(host,nv,c,true);var out=[snapshot(i)];
 switch(n){
 case 3: var before=c.log.length;var returned:Dynamic=i.changeIcon("test",false);ok(c.log.length==before,"unchanged name does not load");if(nv){ok(returned==i,"NV returns this");i.changeIcon("test",true);ok(c.log.length>before,"NV forced reload");}else ok(returned==null,"Psych Void return");out.push(snapshot(i));
 case 4: c.w=640;c.h=160;if(nv)set(i,"frameCount",3);else i.changeIcon("wide",false);out.push(snapshot(i));
 case 5: c.aa=true;ClientPrefs.data.antialiasing=true;i.changeIcon("test-pixel",false);out.push(snapshot(i));i.changeIcon("other",false);out.push(snapshot(i));
 case 6: var tracker=new flixel.FlxSprite(50,70);tracker.width=40;i.sprTracker=tracker;i.update(.1);out.push(snapshot(i));if(nv){i.sprOffsets.set(-4,6);i.update(.1);out.push(snapshot(i));}
 case 7: var s:flixel.FlxSprite=cast i;s.scale.set(2,3);if(nv)Reflect.setField(i,"updateOffset",false);else i.autoAdjustOffset=false;s.offset.set(99,88);i.updateHitbox();out.push(snapshot(i));
 case 8: if(nv){set(i,"alphaMultipler",.5);set(i,"alphaMultipler",.5);out.push(snapshot(i));i.updateIconAnim(.1);out.push(snapshot(i));i.updateFrames=false;i.updateIconAnim(.9);out.push(snapshot(i));}else ok(i.getCharacter()=="test","Psych requested identity");
 case 9: c.fail=true;var error=false;try i.changeIcon("failed",true)catch(e:Dynamic)error=Std.string(e)=="asset-failed";ok(error,"owner failure preserved");out.push(nv?property(i,"characterName"):i.getCharacter());out.push(snapshot(i));
 }
 out.push(c.log.join(","));var point:flixel.math.FlxPoint=nv?property(i,"sprOffsets"):null;i.destroy();if(nv)ok(point.puts==1,"owned source tracker point released");return out.join("\n");}
 static function main(){for(nv in [false,true])for(n in 0...10){var expected=scenario(false,nv,n),actual=scenario(true,nv,n);ok(expected==actual,"icon donor "+nv+":"+n+"\n"+actual+"\nexpected\n"+expected);}
  var c=new Context();var nv=new NightmareVisionHealthIcon("test",false,c.owner());ok(Std.isOfType(nv,NightmareVisionIUiSprite),"actual source interface identity");var ui:NightmareVisionIUiSprite=nv;ui.alphaMultipler=.5;ok(nv.alpha==.5,"interface alpha setter");var method=Reflect.field(nv,"updateIconAnim");ok(Reflect.isFunction(method),"inline source method exported");Reflect.callMethod(nv,method,[.1]);ok(nv.animation.frameIndex==1,"reflected native frame");nv.destroy();
 }
}
'''
    return files
