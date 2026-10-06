"""Native-shaped splash dependencies shared by executable donor comparisons."""

def splash_fixture_files(donor, offset_method):
    files = {
        'flixel/FlxCamera.hx': 'package flixel;class FlxCamera {}',
        'flixel/math/FlxMath.hx': 'package flixel.math;class FlxMath {public static inline var EPSILON=0.0000001;public static function fastSin(r:Float)return Math.sin(r);public static function fastCos(r:Float)return Math.cos(r);}',
        'flixel/math/FlxPoint.hx': '''package flixel.math;
    class FlxPoint {public var x:Float;public var y:Float;public var puts=0;public function new(x=0.,y=0.){set(x,y);}public static function get(x=0.,y=0.)return new FlxPoint(x,y);public function set(x=0.,y=0.){this.x=x;this.y=y;return this;}public function copyFrom(p:FlxPoint)return set(p.x,p.y);public function scale(x:Float,y:Float)return set(this.x*x,this.y*y);public function subtract(p:FlxPoint)return set(x-p.x,y-p.y);public function rotateByDegrees(a:Float){var r=a*Math.PI/180;return set(x*Math.cos(r)-y*Math.sin(r),x*Math.sin(r)+y*Math.cos(r));}public function put(){puts++;}}
    ''',
        'flixel/FlxSprite.hx': '''package flixel;
    import flixel.math.FlxPoint;import FakeAnimation;
    class FlxSprite {public var x:Float;public var y:Float;public var width=20.;public var height=30.;public var frameWidth=20;public var frameHeight=30;public var scale=FlxPoint.get(1,1);public var offset=FlxPoint.get();public var origin=FlxPoint.get();public var animation=new FakeAnimation();public var frames:Dynamic;public var shader:Dynamic;public var angle=0.;public var alpha=1.;public var visible=true;public var alive=true;public var exists=true;public var antialiasing=true;public var flipX=false;public var flipY=false;public var kills=0;public var centers=0;public var destroys=0;public function new(x=0.,y=0.){this.x=x;this.y=y;}public function setPosition(x:Float,y:Float){this.x=x;this.y=y;}public function updateHitbox(){width=frameWidth*scale.x;height=frameHeight*scale.y;}public function centerOffsets(){centers++;offset.set((frameWidth-width)*.5,(frameHeight-height)*.5);}public function centerOrigin(){origin.set(frameWidth*.5,frameHeight*.5);}public function kill(){kills++;alive=false;exists=false;}public function revive(){alive=true;exists=true;}public function update(e:Float){if(animation.pending!=null){var p=animation.pending;animation.pending=null;animation.onFinish.dispatch(p);}}public function draw(){}public function drawSimple(c:FlxCamera){}public function drawComplex(c:FlxCamera){}public function getScreenPosition(?p:FlxPoint,?c:FlxCamera):FlxPoint {if(p==null)p=FlxPoint.get();return p.set(x,y);}public function destroy(){destroys++;}}
    ''',
        'FakeAnimation.hx': '''import flixel.util.FlxSignal.FlxTypedSignal;
    class FakeAnimation {public var onFinish=new FlxTypedSignal<String->Void>();public var definitions:Map<String,Dynamic>=[];public var curAnim:Dynamic;public var pending:String;public var plays:Array<String>=[];public function new(){}public function addByPrefix(n:String,p:String,f:Float,l:Bool)definitions.set(n,{prefix:p,fps:f,looping:l});public function exists(n:String)return definitions.exists(n);public function play(n:String,force:Bool=false,reverse:Bool=false,frame:Int=0){plays.push(n+":"+force);curAnim={name:n};}}
    ''',
        'NightmareVisionRGBGraphics.hx': '''class NightmareVisionRGBGraphics {public var enabled=true;public var alpha=1.;public var flash=0.;public var colors=[1,2,3];public var applied=0;public function new(){}public function setColors(c:Array<Int>)colors=c.copy();public function getColors()return colors.copy();public function apply(s:flixel.FlxSprite){applied++;s.shader=this;}public function pushQuad(c:flixel.FlxCamera)applied++;}''',
        'Note.hx': 'class Note {public var noteData=1;public var tail:Array<Note>=[];public var garbage=false;public var wasGoodHit=false;public var alive=true;public function new(){}}',
        'Strumline.hx': 'class Strumline {}class StrumNote extends flixel.FlxSprite {public function new(){super(100,200);width=112;height=112;}}',
        'NightmareVisionPlayFieldView.hx': 'class NightmareVisionPlayFieldView {public var player=1;public function new(){}}',
        'NightmareVisionNoteSkin.hx': '''class NightmareVisionNoteSkin {public var sustainSplashTexture="cover";public var susSplashScale:Null<Float>=2;public var antialiasing=false;public var inEngineColoring=true;public var susSplashAlpha=.13;public var colors:Array<Dynamic>=[];public var sustainSplashOffsets:Array<flixel.math.FlxPoint>=[flixel.math.FlxPoint.get(2,3),flixel.math.FlxPoint.get(7,11)];public var susSplashAnims:Array<Array<Dynamic>>=[];public function new(){for(d in 0...2)susSplashAnims.push([for(n in ["start","loop","end"]) {anim:n,xmlName:n+d,fps:24.,looping:n=="loop",offsets:[3.,5.]}]);}public function loadSustainSplashFrames():Dynamic return Paths.getAtlasFrames(sustainSplashTexture);}''',
        'Paths.hx': 'class Paths {public static var loads:Array<String>=[];public static function getAtlasFrames(s:String):Dynamic {loads.push(s);return s;}}',
        'NoteUtil.hx': 'class NoteUtil {public static var skins=[new NightmareVisionNoteSkin(),new NightmareVisionNoteSkin()];public static function getSkinFromID(p:Int)return skins[p];public static function colorToArray(c:Dynamic):Array<Int>return [1,2,3];}',
        'ClientPrefs.hx': 'class ClientPrefs {public static var noteSplashType="Both";}',
        'DonorSprite.hx': '''import flixel.math.FlxPoint;
    class DonorSprite extends flixel.FlxSprite {public var noteData=0;public var baseScale=FlxPoint.get(1,1);public var spriteOffset=FlxPoint.get();public var animOffset=FlxPoint.get();public var animOffsets:Map<String,Array<Float>>=[];public var canPlayAnimations=true;public function new(x=0.,y=0.)super(x,y);public function addOffset(n:String,x=0.,y=0.)animOffsets.set(n,[x,y]);public function getAnimName():String return animation.curAnim==null?"":animation.curAnim.name;public function playAnim(n:String,f=false,r=false,i=0){if(!canPlayAnimations)return;while(!animation.exists(n)&&n.lastIndexOf("-")>=0)n=n.substring(0,n.lastIndexOf("-"));if(!animation.exists(n))return;animation.play(n,f,r,i);var a=animOffsets.get(n);if(a!=null)animOffset.set(a[0],a[1]);}}
    ''',
        'DonorSplash.hx': 'import Strumline.StrumNote;import flixel.FlxCamera;using StringTools;\ntypedef RGBGraphics=NightmareVisionRGBGraphics;typedef NoteSkin=NightmareVisionNoteSkin;typedef PlayField=NightmareVisionPlayFieldView;typedef FlxColor=Int;\n' + donor,
        'Main.hx': r'''
    class Main {
     static function check(v:Bool,s:String)if(!v)throw s;
     static function make(host:Bool):Dynamic return host?new NightmareVisionSustainSplash(9,13,1,1,{skinForID:NoteUtil.getSkinFromID,noteSplashType:function()return ClientPrefs.noteSplashType}):new DonorSplash(9,13,1,1);
     static function snap(s:Dynamic):String return [s.x,s.y,s.width,s.height,s.noteData,s.player,s.completed,s.alive,s.visible,s.angle,s.alpha,s.scale.x,s.baseScale.x,s.spriteOffset.x,s.spriteOffset.y,s.animOffset.x,s.animOffset.y,s.animation.curAnim==null?"":s.animation.curAnim.name,s.animation.plays.join(","),s.rgbGraphics.colors.join(","),s.rgbGraphics.enabled,s.kills].join("|");
     static function scenario(host:Bool,n:Int):String {
      ClientPrefs.noteSplashType="Both";Paths.loads=[];var s=make(host);var out=[snap(s)];check(s.skin==null&&s.player==0&&s.noteData==0,"constructor does not assign arguments");
      var head=new Note(),tail=new Note(),strum=new Strumline.StrumNote(),field=new NightmareVisionPlayFieldView();head.tail=[tail];var rgb=new NightmareVisionRGBGraphics();rgb.setColors([4,5,6]);
      s.setupSplash(strum,head,999.,true,rgb,field);out.push(snap(s));rgb.setColors([7,8,9]);check(s.rgbGraphics.colors[0]==4,"input colors copied");
      switch(n){
       case 0: s.animation.onFinish.dispatch("start1");out.push(snap(s));tail.wasGoodHit=true;s.update(.1);out.push(snap(s));tail.alive=false;s.update(.1);out.push(snap(s));s.update(.1);out.push(snap(s));s.animation.onFinish.dispatch("end1");out.push(snap(s));
       case 1: tail.garbage=true;tail.wasGoodHit=true;s.update(.1);out.push(snap(s));
       case 2: ClientPrefs.noteSplashType="Note Splashes";tail.alive=false;s.update(.1);out.push(snap(s));
       case 3: s.setupSplash(strum,head,.001,false,null,field);tail.alive=false;s.update(.1);out.push(snap(s));
       case 4: tail.wasGoodHit=true;s.update(.1);s.kill();s.setupSplash(strum,head,.2,true,null,field);check(!s.alive&&s.completed,"setup neither revives nor resets completed");out.push(snap(s));s.animation.plays=[];s.animation.onFinish.dispatch("start1");check(s.animation.plays.length==3,"one finish listener per constructor/setup");out.push(snap(s));
       case 5: var replacement=new Note();head.tail=[replacement];replacement.garbage=true;s.update(.1);check(s.alive,"last tail captured at setup");tail.alive=false;s.update(.1);out.push(snap(s));
       case 6: s.animation.pending="end1";tail.wasGoodHit=true;s.update(.1);check(!s.alive&&s.completed,"parent animation update before tail watcher");out.push(snap(s));
       case 7: s.canPlayAnimations=false;var centers:Int=s.centers;s.playAnim("end1");check(s.centers==centers+1,"centering even when animation disabled");out.push(snap(s));
       case 8: s.playAnim("loop1-alt");out.push(snap(s));s.playAnim("missing");out.push(snap(s));
       case 9: s.setColors(null);out.push(snap(s));s.setupSplash(null,head,.5,true,null,null);out.push(snap(s));
      }
      out.push(Paths.loads.join(","));return out.join("\n");
     }
     static function main(){for(i in 0...10){var expected=scenario(false,i),actual=scenario(true,i);check(actual==expected,"donor scenario "+i+"\n"+actual+"\nexpected\n"+expected);}
      var s=new NightmareVisionSustainSplash(0,0,0,0,{skinForID:NoteUtil.getSkinFromID,noteSplashType:function()return ClientPrefs.noteSplashType});s.update(.1);check(!s.alive,"unused seed retires without tail");s.spriteOffset.set(7,11);s.animOffset.set(3,5);s.baseScale.set(2,2);s.scale.set(4,6);s.angle=90;s.setPosition(100,200);var p=s.getScreenPosition();check(Math.abs(p.x-148)<.00001&&Math.abs(p.y-180)<.00001,"combined offsets scale then rotate in screen space");
      var donor=new DonorSprite();donor.spriteOffset.copyFrom(s.spriteOffset);donor.animOffset.copyFrom(s.animOffset);donor.baseScale.copyFrom(s.baseScale);donor.scale.copyFrom(s.scale);donor.angle=s.angle;
      for(flags in 0...8){s.scalableOffsets=donor.scalableOffsets=(flags&1)!=0;s.rotatableOffsets=donor.rotatableOffsets=(flags&2)!=0;s.skewableOffsets=donor.skewableOffsets=(flags&4)!=0;s.skew.set(17,-23);donor.skew.copyFrom(s.skew);var expected=donor.transformSpriteOffset();p=s.getScreenPosition();check(Math.abs(p.x-(100-expected.x))<.00001&&Math.abs(p.y-(200-expected.y))<.00001,"actual donor offset transform flags "+flags);}
      s.draw();check(s.shader==s.rgbGraphics&&s.rgbGraphics.applied==1,"actual RGB bridge used for draw");var base=s.baseScale,off=s.spriteOffset,anim=s.animOffset;s.destroy();check(base.puts==1&&off.puts==1&&anim.puts==1&&s.skin==null&&s.rgbGraphics==null,"owned points and references released");
     }
    }
    ''',
    }
    files['DonorSprite.hx'] = files['DonorSprite.hx'].replace('import flixel.math.FlxPoint;', 'import flixel.math.FlxPoint;import flixel.math.FlxMath;')
    files['DonorSprite.hx'] = files['DonorSprite.hx'].replace('public var canPlayAnimations=true;', 'public var canPlayAnimations=true;public var scalableOffsets=true;public var rotatableOffsets=true;public var skewableOffsets=true;public var skew=FlxPoint.get();')
    files['DonorSprite.hx'] = files['DonorSprite.hx'].rstrip()[:-1] + offset_method + '}\n'
    files['MathUtil.hx'] = 'class MathUtil {public static function fastTan(r:Float)return flixel.math.FlxMath.fastSin(r)/flixel.math.FlxMath.fastCos(r);}'
    files['flixel/math/FlxPoint.hx'] = files['flixel/math/FlxPoint.hx'].replace('public static function get', 'public static function weak(x=0.,y=0.)return get(x,y);public static function get')
    return files
