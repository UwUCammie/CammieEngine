"""Native-shaped Bar dependencies with actual pinned group operations."""
from pathlib import Path
import re
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]

def bar_fixture_files():
    flixel = ROOT / '.haxelib/flixel/6,1,2/flixel'
    sg = (flixel / 'group/FlxSpriteGroup.hx').read_text()
    group = (flixel / 'group/FlxGroup.hx').read_text()
    group_methods = '\n'.join(method(group, name) for name in ['public function add(', 'public function getFirstNull(', 'override public function update(', 'override public function destroy('])
    sprite_methods = '\n'.join(method(sg, name) for name in ['public function add(', 'function preAdd(', 'public function transformChildren<', 'override function set_x(', 'override function set_y(', 'override function set_alpha(', 'override public function update('])
    sprite_methods = sprite_methods.replace('override function', 'override public function').replace('public function add(Sprite:T)', 'public function add(Sprite:T)')
    files = {
        'flixel/FlxBasic.hx': 'package flixel;class FlxBasic implements flixel.util.IFlxDestroyable {public var exists=true;public var active=true;public var visible=true;public var alive=true;public var destroyed=0;public var updates=0;public function new(){}public function update(e:Float){updates++;}public function destroy(){destroyed++;}}',
        'flixel/graphics/FlxGraphic.hx': 'package flixel.graphics;class FlxGraphic {public var width:Int;public var height:Int;public function new(w:Int,h:Int){width=w;height=h;}}',
        'flixel/math/FlxPoint.hx': 'package flixel.math;class FlxPoint {public var x:Float;public var y:Float;public function new(x=0.,y=0.){set(x,y);}public function set(x=0.,y=0.){this.x=x;this.y=y;return this;}public function copyFrom(p:FlxPoint)return set(p.x,p.y);}',
        'flixel/math/FlxRect.hx': 'package flixel.math;class FlxRect {public var x:Float;public var y:Float;public var width:Float;public var height:Float;public function new(x=0.,y=0.,w=0.,h=0.){this.x=x;this.y=y;width=w;height=h;}}',
        'flixel/math/FlxMath.hx': 'package flixel.math;class FlxMath {public static function lerp(a:Float,b:Float,r:Float)return a+(b-a)*r;public static function bound(v:Float,min:Float,max:Float)return v<min?min:v>max?max:v;public static function remapToRange(v:Float,a:Float,b:Float,c:Float,d:Float)return c+(v-a)/(b-a)*(d-c);}',
        'flixel/util/FlxColor.hx': 'package flixel.util;typedef FlxColor=Null<Int>;',
        'flixel/util/IFlxDestroyable.hx': 'package flixel.util;interface IFlxDestroyable {public function destroy():Void;}',
        'flixel/util/FlxDestroyUtil.hx': 'package flixel.util;class FlxDestroyUtil {public static function destroy<T:IFlxDestroyable>(o:T):T {if(o!=null)o.destroy();return null;}}',
        'flixel/util/helpers/FlxBounds.hx': 'package flixel.util.helpers;class FlxBounds<T>{public var min:T;public var max:T;public function new(a:T,b:T){min=a;max=b;}}',
        'flixel/FlxSprite.hx': '''package flixel;import flixel.math.FlxPoint;import flixel.math.FlxRect;import flixel.graphics.FlxGraphic;
class FlxSprite extends FlxBasic {public var x(default,set)=0.;public var y(default,set)=0.;public var alpha(default,set)=1.;public var width=1.;public var height=1.;public var frameWidth=1;public var frameHeight=1;public var color:Null<Int>=0xFFFFFFFF;public var antialiasing=true;public var clipRect(default,set):FlxRect;public var clips=0;public var makes=0;public var scale=new FlxPoint(1,1);public var scrollFactor=new FlxPoint(1,1);public var cameras:Array<Dynamic>;public var _cameras:Array<Dynamic>;public var path:Dynamic;public var moves=false;public function new(x=0.,y=0.){super();this.x=x;this.y=y;}public function set_x(v:Float)return x=v;public function set_y(v:Float)return y=v;public function set_alpha(v:Float)return alpha=v;function set_clipRect(v:FlxRect){clips++;return clipRect=v;}public function setPosition(x:Float,y:Float){this.x=x;this.y=y;}public function updateMotion(e:Float){}public function loadGraphic(g:FlxGraphic){frameWidth=g.width;frameHeight=g.height;updateHitbox();return this;}public function makeGraphic(w:Int,h:Int,c:Null<Int>){makes++;frameWidth=w;frameHeight=h;scale.set(1,1);updateHitbox();color=c;return this;}public function setGraphicSize(w:Int,h:Int){scale.set(w/frameWidth,h/frameHeight);}public function updateHitbox(){width=frameWidth*scale.x;height=frameHeight*scale.y;}}
''',
        'flixel/group/FlxGroup.hx': '''package flixel.group;import flixel.FlxBasic;import flixel.util.FlxDestroyUtil;
class FlxG {public static var log={warn:function(s:String){}};}
class FlxTypedGroup<T:FlxBasic> extends FlxBasic {public var members:Array<T>=[];public var length=0;public var maxSize=0;var _memberAdded:flixel.util.IFlxDestroyable;var _memberRemoved:flixel.util.IFlxDestroyable;public function new(){super();}function onMemberAdd(v:T){} __METHODS__}
'''.replace('__METHODS__', group_methods),
        'flixel/group/FlxSpriteGroup.hx': '''package flixel.group;import flixel.FlxSprite;import flixel.math.FlxMath;import flixel.group.FlxGroup.FlxTypedGroup;
typedef FlxSpriteGroup=FlxTypedSpriteGroup<FlxSprite>;
class FlxTypedSpriteGroup<T:FlxSprite> extends FlxSprite {public var group:FlxTypedGroup<T>;public var members(get,never):Array<T>;public var directAlpha=false;var _skipTransformChildren=false;public function new(x=0.,y=0.){group=new FlxTypedGroup<T>();super(x,y);}function get_members()return group.members;
inline function xTransform(s:FlxSprite,x:Float)s.x+=x;inline function yTransform(s:FlxSprite,y:Float)s.y+=y;inline function alphaTransform(s:FlxSprite,a:Float){if(s.alpha!=0||a==0)s.alpha*=a;else s.alpha=1/a;}inline function directAlphaTransform(s:FlxSprite,a:Float)s.alpha=a;function clipRectTransform(s:FlxSprite,r:flixel.math.FlxRect)s.clipRect=r;
__METHODS__
override public function destroy(){group.destroy();super.destroy();}}
'''.replace('__METHODS__', sprite_methods),
        'Paths.hx': 'class Paths {public static var calls:Array<String>=[];public static function image(n:String):flixel.graphics.FlxGraphic {calls.push(n);return new flixel.graphics.FlxGraphic(106,26);}}',
        'ClientPrefs.hx': 'class ClientPrefs {public static var data={antialiasing:false};}',
        'Main.hx': r'''
class Main {
 static function check(v:Bool,m:String)if(!v)throw m;
 static function set(b:Dynamic,n:String,v:Dynamic)Reflect.setProperty(b,n,v);
 static function snapshot(b:Dynamic):String {var l:flixel.FlxSprite=b.leftBar,r:flixel.FlxSprite=b.rightBar;var values:Array<Dynamic>=[b.percent,b.barCenter,b.barWidth,b.barHeight,b.leftToRight,b.bg.x,b.bg.y,l.x,l.y,r.x,r.y,l.clipRect.x,l.clipRect.y,l.clipRect.width,l.clipRect.height,r.clipRect.x,r.clipRect.width,l.alpha,r.alpha,l.color,r.color,l.frameWidth,l.frameHeight,l.makes,r.makes,l.clips,r.clips];return values.join("|");}
 static function make(host:Bool,nv:Bool,fn:Void->Float):Dynamic {var owner:SourceBarOwner={image:Paths.image,antialiasing:function()return ClientPrefs.data.antialiasing};return nv?(host?new NightmareVisionBar(10,20,"custom",fn,0,2,owner):new DonorNVBar(10,20,"custom",fn,0,2)):(host?new PsychSourceBar(10,20,"custom",fn,0,2,owner):new DonorPsychBar(10,20,"custom",fn,0,2));}
 static function scenario(host:Bool,nv:Bool,n:Int):String {var value=1.;var b:Dynamic=make(host,nv,function()return value);var g:flixel.group.FlxSpriteGroup=cast b;var out=[snapshot(b)];check(g.members[0]==b.leftBar&&g.members[1]==b.rightBar&&g.members[2]==b.bg,"physical child order");b.update(.1);out.push(snapshot(b));check(b.percent==50&&b.leftBar.clipRect.width==50.&&b.barCenter==63,"source clipping and physical boundary");
 switch(n){
 case 0: set(b,"percent",25.);out.push(snapshot(b));set(b,"leftToRight",false);out.push(snapshot(b));set(b,"percent",150.);out.push(snapshot(b));
 case 1: set(b,"barWidth",64);set(b,"barHeight",8);b.barOffset.set(7,9);b.updateBar();out.push(snapshot(b));
 case 2: b.enabled=false;value=2.;b.update(.1);out.push(snapshot(b));b.enabled=true;b.update(.1);out.push(snapshot(b));b.valueFunction=null;b.update(.1);out.push(snapshot(b));
 case 3: b.setBounds(2,0);b.update(.1);out.push(snapshot(b));b.setBounds(1,1);b.update(.1);out.push(snapshot(b));
 case 4: b.setColors(12,null);out.push(snapshot(b));b.setColors(null,34);out.push(snapshot(b));set(b,"x",30.);set(b,"y",50.);out.push(snapshot(b));set(b,"alpha",.5);out.push(snapshot(b));set(b,"alpha",0.);out.push(snapshot(b));set(b,"alpha",.75);out.push(snapshot(b));
 case 5: b.bg.makeGraphic(206,46,0);b.regenerateClips();out.push(snapshot(b));
 case 6: value=2.;b.updateBar();check(b.percent==50,"updateBar only renders current percentage");out.push(snapshot(b));b.update(.1);out.push(snapshot(b));
 case 8: set(b,"percent",33.37);b.barOffset.set(.25,.75);b.updateBar();check(b.leftBar.clipRect.width==33.&&b.rightBar.clipRect.width==67.,"actual Flixel setter rounds physical clip widths");check(b.leftBar.clipRect.x==0.&&b.leftBar.clipRect.y==1.&&b.rightBar.clipRect.x==34.,"actual Flixel rect rounds positions independently");check(Math.abs(b.barCenter-43.62)<.00001,"barCenter retains float boundary before clip rounding");out.push(snapshot(b));
 case 7: if(nv){b.setBGOffset(5,7);b.updateBar();out.push(snapshot(b));b.setBGOffset(3,4);b.updateBar();out.push(snapshot(b));set(b,"alphaMultipler",.5);set(b,"alpha",.8);out.push(snapshot(b));set(b,"alphaMultipler",2.);out.push(snapshot(b));}else{b.leftBar=new flixel.FlxSprite();b.leftBar.makeGraphic(90,15,0);b.regenerateClips();b.bounds={min:0.,max:4.};b.update(.1);out.push(snapshot(b));}
 }
 var held:Array<flixel.FlxSprite>=g.members.copy();b.destroy();for(child in held)check(child.destroyed==1,"native group owns each actual child exactly once");return out.join("\n");}
 static function main(){for(nv in [false,true])for(n in 0...9){var expected=scenario(false,nv,n),actual=scenario(true,nv,n);check(expected==actual,"bar donor "+nv+":"+n+"\n"+actual+"\nexpected\n"+expected);}
  var loads:Array<String>=[],aaCalls=0;var owner:SourceBarOwner={image:function(n){loads.push(n);return new flixel.graphics.FlxGraphic(80,18);},antialiasing:function(){aaCalls++;return false;}};
  var psych=new PsychSourceBar(0,0,"owner/frame",null,0,1,owner);check(loads.join(",")=="owner/frame"&&aaCalls==3&&!psych.antialiasing&&!psych.bg.antialiasing,"Psych selected image and live AA dependency");
  var nv=new NightmareVisionBar(0,0,"nv/frame",null,0,1,owner);check(loads.join(",")=="owner/frame,nv/frame"&&aaCalls==3&&nv.bg.antialiasing,"NV preserves default AA and selected image loader");
  check(Std.isOfType(nv,NightmareVisionIUiSprite)&&!Std.isOfType(psych,NightmareVisionIUiSprite),"exact source interface identity on NV Bar only");
  var ui:NightmareVisionIUiSprite=nv;ui.alphaMultipler=.5;check(nv.alpha==.5,"interface setter invokes actual alpha behavior");
  psych.destroy();nv.destroy();
 }
}
''',
    }
    imports = 'import flixel.FlxSprite;import flixel.group.FlxSpriteGroup;import flixel.math.FlxPoint;import flixel.math.FlxMath;import flixel.util.FlxColor;\n'
    for name, path in [('DonorPsychBar', 'FNF-PsychEngine/source/objects/Bar.hx'), ('DonorNVBar', 'NightmareVision/source/funkin/objects/Bar.hx')]:
        source = (ROOT.parent / 'fnf_sources' / path).read_text()
        source = re.sub(r'^package[^\n]*\n', '', source, flags=re.M).replace('import funkin.game.IUiSprite;', '')
        source = source.replace('class Bar extends', 'class ' + name + ' extends').replace(' implements IUiSprite', '')
        source = source.replace('override function update', 'override public function update')
        files[name + '.hx'] = imports + source
    # Preserve the native Int-backed abstract and nullable optional arguments.
    files['flixel/util/FlxColor.hx'] = 'package flixel.util;@:forward abstract FlxColor(Int) from Int to Int {public static inline var WHITE:Int=-1;public static inline var BLACK:Int=0xFF000000;}'
    rect_source = (flixel / 'math/FlxRect.hx').read_text()
    rect_round = method(rect_source, 'public inline function round(')
    files['flixel/math/FlxRect.hx'] = files['flixel/math/FlxRect.hx'][:-1] + rect_round + '}'
    # Keep the exact setter/round execution, adding only the existing test counter.
    sprite_source = (flixel / 'FlxSprite.hx').read_text()
    clip_setter = method(sprite_source, 'function set_clipRect(').replace('{', '{clips++;', 1)
    files['flixel/FlxSprite.hx'] = files['flixel/FlxSprite.hx'].replace('function set_clipRect(v:FlxRect){clips++;return clipRect=v;}', clip_setter)
    math_source = (flixel / 'math/FlxMath.hx').read_text()
    files['flixel/math/FlxMath.hx'] = 'package flixel.math;class FlxMath {' + '\n'.join(method(math_source, name) for name in ['public static function roundDecimal(', 'public static inline function bound(', 'public static function remapToRange(', 'public static inline function lerp(']) + '}'
    return files
