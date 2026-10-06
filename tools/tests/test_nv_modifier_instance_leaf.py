"""Direct builtin leaf comparisons against executable pinned donor methods."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from tools.tests.test_psych_character_scope import extract_method

ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT.parent / "fnf_sources/NightmareVision/source/funkin/game/modchart/modifiers"


def methods(file, markers):
    text = (DONOR / file).read_text()
    return "\n".join("public " + extract_method(text, marker).replace("override ", "").replace("inline ", "") for marker in markers)


class NightmareVisionModifierInstanceLeafTest(unittest.TestCase):
    def test_extracted_source_leaves_and_direct_override_only_fields(self):
        if not DONOR.is_dir():
            self.skipTest("pinned Nightmare Vision donor unavailable")
        reverse = methods("ReverseModifier.hx", ["function getReverseValue(", "function getPos("])
        path = methods("PathModifier.hx", ["function tracePath(", "function getPos("])
        rotate = methods("RotateModifier.hx", ["function rotateV3(", "function getPos("])
        perspective = methods("PerspectiveModifier.hx", ["function getVector("])
        alpha = methods("AlphaModifier.hx", ["function getHiddenSudden(", "function getHiddenEnd(", "function getHiddenStart(", "function getSuddenEnd(", "function getSuddenStart("])
        extra_classes = []
        for name, file, fields, markers in [
            ("DonorOpponent", "OpponentModifier.hx", "", ["function getPos("]),
            ("DonorFlip", "FlipModifier.hx", "", ["function getPos("]),
            ("DonorInvert", "InvertModifier.hx", "", ["function getPos("]),
            ("DonorDrunk", "DrunkModifier.hx", "", ["function getPos("]),
            ("DonorBeat", "BeatModifier.hx", "", ["function getPos("]),
            ("DonorTransform", "TransformModifier.hx", "", ["function getPos("]),
            ("DonorScroll", "ReceptorScrollModifier.hx", "var moveSpeed:Float=1500;", ["function lerp(", "function getPos("]),
            ("DonorAccel", "AccelModifier.hx", "", ["function getPos("]),
            ("DonorLocal", "LocalRotateModifier.hx", 'var prefix="custom";', ["function rotateV3(", "function getPos("]),
        ]:
            extra_classes.append("class " + name + " extends Base {" + fields + methods(file, markers).replace("flixel.FlxSprite", "FlxSprite") + "}")
        for name, file, markers in [
            ("DonorConfusion", "ConfusionModifier.hx", ["function updateNote("]),
            ("DonorXmod", "XModifier.hx", ["function updateNote("]),
            ("DonorScrollObject", "ReceptorScrollModifier.hx", ["function updateNote("]),
            ("DonorScale", "ScaleModifier.hx", ["function lerp(", "function getScale(", "function getObjectScale(", "function updateNote(", "function updateReceptor(", "function updateNoteSplash(", "function updateSustainSplash("]),
        ]:
            fields = "var moveSpeed:Float=1500;" if name == "DonorScrollObject" else ""
            body = methods(file, markers)
            for kind in ["NoteSplash", "SustainSplash", "StrumNote", "FunkinSprite", "ModchartNote", "Note"]:
                body = body.replace(":" + kind, ":Dynamic")
            extra_classes.append("class " + name + " extends Base {" + fields + body + "}")
        fixture = r'''
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModifierRegistry.NightmareVisionModifierExecution;
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import nightmarevision.modchart.NightmareVisionModifierFormulaState;
import nightmarevision.modchart.NightmareVisionModifierFormulaState.NightmareVisionModifierPathInfo;
import nightmarevision.modchart.NightmareVisionModchartVector;
typedef Vector3=NightmareVisionModchartVector;
typedef FlxSprite=Dynamic;
typedef FlxPoint=Point;
typedef PathInfo=NightmareVisionModifierPathInfo;
class FlxG { public static var width=1280; public static var height=720; }
class ClientPrefs { public static var downScroll=false; }
class Conductor {public static var songPosition:Float=350;}
class PlayState {public static var instance:Dynamic={curDecBeat:2.,songSpeed:1.};}
class Note { public static var swagWidth=112.; }
class Point {public var x:Float;public var y:Float;public function new(x,y){this.x=x;this.y=y;}public function putWeak(){}public static function weak(x:Float,y:Float):Point return new Point(x,y);public function copyFrom(p:Point):Point{x=p.x;y=p.y;return this;}}
class MathUtil {
 public static function scale(v:Float,a:Float,b:Float,c:Float,d:Float):Float return (v-a)*(d-c)/(b-a)+c;
 public static function clamp(v:Float,a:Float,b:Float):Float return FlxMath.bound(v,a,b);
 public static function rotate(x:Float,y:Float,a:Float):Point return new Point(x*Math.cos(a)-y*Math.sin(a),x*Math.sin(a)+y*Math.cos(a));
 public static function fastTan(a:Float):Float return FlxMath.fastSin(a)/FlxMath.fastCos(a);
}
class FlxMath {
 public static inline var EPSILON:Float=0.0000001;
 public static function fastSin(a:Float):Float return nightmarevision.modchart.NightmareVisionModchartMath.fastSin(a);
 public static function fastCos(a:Float):Float return nightmarevision.modchart.NightmareVisionModchartMath.fastCos(a);
 public static function bound(v:Float,a:Float,b:Float):Float return v<a?a:v>b?b:v;
}
class Base {
 public var amount:Float=.4; public var subs:Map<String,Float>=new Map();public var modMgr:Dynamic;
 public function new(){modMgr={keys:4,register:new Map<String,Dynamic>(),receptors:[[0,1,2,3,4,5],[0,1,2],[0,1,2,3]], getBaseX:function(d:Int,p:Int)return NightmareVisionModchartTransform.baseX(new NightmareVisionModchartContext(1280,720,4,112),d,p)};}
 public function getValue(p:Int):Float return amount+p*.1;
 public function getSubmodValue(n:String,p:Int):Float return subs.exists(n)?subs.get(n):0;
 public function getName():String return "custom";
}
class DonorReverse extends Base { REVERSE }
class DonorPath extends Base {var pathData:Array<Array<PathInfo>>=[];var totalDists:Array<Float>=[];var moveSpeed:Float=2000; PATH }
class DonorRotate extends Base {public var daOrigin:Vector3;var prefix="custom"; ROTATE }
class DonorPerspective extends Base {var halfOffset=Vector3.get(640,360);final fov:Float=Math.PI/2;final near:Float=0;final far:Float=2; PERSPECTIVE }
class DonorAlpha extends Base {public static var fadeDistY=120.; ALPHA }
EXTRACLASSES
class Main {
 static function check(v:Bool,s:String) if(!v) throw s;
 static function near(a:Float,b:Float,s:String) check(Math.abs(a-b)<.00001 || Math.isNaN(a)&&Math.isNaN(b) || a==b,s+":"+a+" != "+b);
 static function vec(a:Vector3,b:Vector3,s:String){near(a.x,b.x,s+"x");near(a.y,b.y,s+"y");near(a.z,b.z,s+"z");}
 static function entry(kind:String,b:Base,state:NightmareVisionModifierFormulaState):NightmareVisionModifierExecution return {builtin:kind,state:state,value:b.getValue,subValue:b.getSubmodValue,getPosition:function(t,d,td,beat,p,data,player,obj)return p,updateObject:function(beat,obj,pos,player,kind){}};
 static function main(){
  var registry=new NightmareVisionModifierRegistry(4);var t=new NightmareVisionModchartTransform(registry);var r=new NightmareVisionModchartRenderer(t);var c=new NightmareVisionModchartContext(1280,720,4,112,350,2,1,900);
  var reverse=new DonorReverse(); reverse.subs.set("split",.2);reverse.subs.set("cross",.3);reverse.subs.set("alternate",.1);reverse.subs.set("reverseScroll",.6);
  var state=new NightmareVisionModifierFormulaState();state.receptorCount=function(p)return reverse.modMgr.receptors[p].length;
  var e=entry("reverse",reverse,state);
  for(ds in [false,true]) {c=new NightmareVisionModchartContext(1280,720,4,112,350,2,1,900,ds);ClientPrefs.downScroll=ds;for(p in 0...2) for(d in 0...6){near(t.instanceReverseValue(c,e,d,p),reverse.getReverseValue(d,p),"reverse bank keys");near(t.instanceReverseValue(c,e,d,p,true),reverse.getReverseValue(d,p,true),"reverse scrolling");var a=new Vector3(35,88,.2),b=a.copy();check(r.applyInstancePosition(c,e,null,"note",a,4,77,22,2,d,p)==a,"reverse identity/null");vec(a,reverse.getPos(4,77,22,2,b,d,p,null),"reverse donor");}}
  c=new NightmareVisionModchartContext(1280,720,4,112,350,2,1,900);
  var extras:Array<Base>=[new DonorOpponent(),new DonorFlip(),new DonorInvert(),new DonorDrunk(),new DonorBeat(),new DonorTransform(),new DonorScroll(),new DonorAccel(),new DonorLocal()];
  var families=["opponentSwap","flip","invert","drunk","beat","transformX","receptorScroll","boost","localrotateX"];
  for(i in 0...extras.length){var source=extras[i];source.subs.set("tipsy",.3);source.subs.set("bumpy",.6);source.subs.set("tipZ",.4);source.subs.set("wave",.3);source.subs.set("brake",.1);source.subs.set("transformY",11);source.subs.set("customrotateY",.4);source.subs.set("customrotate2X",.2);source.modMgr.register.set("reverse",reverse);
   state=new NightmareVisionModifierFormulaState();state.prefix="custom";state.moveSpeed=1500;state.reverseValue=function(d,p,scrolling)return reverse.getReverseValue(d,p,scrolling);e=entry(families[i],source,state);
   for(player in 0...3)for(diff in [-99.,50.,640.]){var a=new Vector3(430,290,.2),b=a.copy();var out=r.applyInstancePosition(c,e,null,"note",a,123,diff,800,99,2,player);var expected:Vector3=Reflect.callMethod(source,Reflect.field(source,"getPos"),[123,diff,800,99,b,2,player,null]);vec(out,expected,"leaf "+families[i]);}
  }
  var path=new DonorPath();state=new NightmareVisionModifierFormulaState();state.prefix="custom";state.moveSpeed=2000; e=entry("path",path,state);
  var authored=[[new Vector3(0,10,0),new Vector3(40,60,.5),new Vector3(100,-20,1)],[]];path.tracePath(authored);NightmareVisionModchartTransform.tracePath(state,authored);check(state.pathData[0][1].position==authored[0][1],"retained path reference");
  for(td in [-500.,0.,700.,2500.])for(d in 0...2){var a=new Vector3(13,29,.7),b=a.copy();vec(r.applyInstancePosition(c,e,null,"note",a,0,44,td,0,d,0),path.getPos(0,44,td,0,b,d,0,null),"path donor/extrapolation");}
  authored[0][1].y=90;var a=new Vector3(1,2,3),b=a.copy();vec(r.applyInstancePosition(c,e,null,"note",a,0,1,600,0,0,0),path.getPos(0,1,600,0,b,0,0,null),"live path alias");NightmareVisionModchartTransform.tracePath(state,[]);check(state.pathData.length==0&&state.totalDists.length==0,"retrace clears");
  var rotation=new DonorRotate();rotation.daOrigin=new Vector3(400,220,.3);rotation.subs.set("customrotateY",.35);rotation.subs.set("customrotateZ",-.7);state=new NightmareVisionModifierFormulaState();state.prefix="custom";state.origin=rotation.daOrigin;e=entry("rotateX",rotation,state);a=new Vector3(480,310,.5);b=a.copy();check(r.applyInstancePosition(c,e,null,"note",a,0,0,0,0,1,0)==a,"rotate input identity");vec(a,rotation.getPos(0,0,0,0,b,1,0,null),"custom origin donor");near(rotation.daOrigin.z,.3,"caller origin retained");
  var projection=new DonorPerspective();state=new NightmareVisionModifierFormulaState();state.halfOffset=new Vector3(640,360);e=entry("perspectiveDONTUSE",projection,state);for(z in [0.,.25,-.4,1.]){a=Vector3.get(690,380,z);b=new Vector3(690,380,z);var out=t.instancePerspectiveVector(c,e,z,a),expected=projection.getVector(z,b);vec(out,expected,"perspective donor");if(z==0)check(out==a,"zero z identity");}
  var fade=new DonorAlpha();fade.subs.set("hidden",.8);fade.subs.set("sudden",.5);fade.subs.set("hiddenOffset",.2);state=new NightmareVisionModifierFormulaState();state.fadeDistY=213;DonorAlpha.fadeDistY=213;e=entry("stealth",fade,state);near(t.alphaBoundary(c,e,"hiddenSudden",0),fade.getHiddenSudden(0),"hs donor");near(t.alphaBoundary(c,e,"hiddenEnd",0),fade.getHiddenEnd(0),"hiddenEnd donor");near(t.alphaBoundary(c,e,"hiddenStart",0),fade.getHiddenStart(0),"hiddenStart donor");near(t.alphaBoundary(c,e,"suddenEnd",0),fade.getSuddenEnd(0),"suddenEnd donor");near(t.alphaBoundary(c,e,"suddenStart",0),fade.getSuddenStart(0),"suddenStart donor");
  // Unoverridden callbacks touch neither a null sprite nor a null position.
  for(kind in ["reverse","flip","path","transformX"])r.applyInstanceObject(c,entry(kind,fade,state),null,"note",null,0,0);
  r.applyInstanceObject(c,entry("perspectiveDONTUSE",fade,state),null,"note",new Vector3(),0,0);
  var native:Dynamic={x:31.,y:47.,angle:9.,scale:{x:3.,y:4.},baseScale:{x:2.,y:5.},noteData:1,lane:1,strumTime:400.,multSpeed:2.,alphaMod:.8,alpha:.6,rgbGraphics:{flash:.2,alpha:.3},isSustainNote:false,isSustainEnd:false,wasGoodHit:true};
  fade.subs.clear();fade.amount=.7;r.applyInstanceObject(c,entry("stealth",fade,state),native,"note",null,0,0);near(native.alphaMod,.4,"alpha uses actual note lane");near(native.x,31,"leaf preserves x");near(native.scale.x,3,"alpha preserves scale");near(native.alpha,.6,"native alpha preserved");
  fade.amount=.25;fade.subs.set("noteScaleX",2);fade.subs.set("noteScaleY",-3);r.applyInstanceObject(c,entry("mini",fade,state),native,"note",null,0,0);near(native.scale.y,-2.25,"negative preset retained when other positive");near(native.angle,9,"scale preserves angle");
  var objc:Array<Base>=[new DonorConfusion(),new DonorXmod(),new DonorScrollObject(),new DonorScale()];var objfamilies=["confusion","xmod","receptorScroll","mini"];
  for(i in 0...objc.length){var source=objc[i];source.amount=.3;source.subs.set("noteScaleX",2);source.subs.set("noteScaleY",-3);source.subs.set("xmod1",1.2);source.subs.set("confusion1",.6);state=new NightmareVisionModifierFormulaState();state.moveSpeed=1500;e=entry(objfamilies[i],source,state);
   var actual:Dynamic={noteData:1,isSustainNote:false,isSustainEnd:false,strumTime:2200.,multSpeed:2.,alphaMod:.7,wasGoodHit:true,garbage:false,angle:4.,scale:new Point(3,4),baseScale:new Point(2,5)};
   var expected:Dynamic={noteData:1,isSustainNote:false,isSustainEnd:false,strumTime:2200.,multSpeed:2.,alphaMod:.7,wasGoodHit:true,garbage:false,angle:4.,scale:new Point(3,4),baseScale:new Point(2,5)};
   r.applyInstanceObject(c,e,actual,"note",null,99,1);Reflect.callMethod(source,Reflect.field(source,"updateNote"),[99,expected,null,1]);near(actual.angle,expected.angle,"object donor angle");near(actual.multSpeed,expected.multSpeed,"object donor speed");near(actual.alphaMod,expected.alphaMod,"object donor alpha");near(actual.scale.x,expected.scale.x,"object donor scaleX");near(actual.scale.y,expected.scale.y,"object donor scaleY");check(actual.garbage==expected.garbage,"object donor garbage");
  }
  state=new NightmareVisionModifierFormulaState();state.moveSpeed=1500;fade.amount=1;r.applyInstanceObject(c,entry("receptorScroll",fade,state),native,"note",null,0,0);check(native.garbage==true,"actual garbage flag");near(native.x,31,"no geometry initialization");
 }
}
'''
        fixture = fixture.replace("EXTRACLASSES", "\n".join(extra_classes))
        for token, value in [("REVERSE", reverse), ("PATH", path), ("ROTATE", rotate), ("PERSPECTIVE", perspective), ("ALPHA", alpha)]:
            fixture = fixture.replace(" " + token + " }", " " + value + " }")
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "Main.hx").write_text(fixture)
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", directory, "-main", "Main", "--interp"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-12000:])
