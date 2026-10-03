"""Focused native-adapter contract tests without launching the game."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"
TMP.mkdir(exist_ok=True)
SOURCE = ROOT / "source/CodenameFunkinSprite.hx"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(marker)


class CodenameFunkinSpriteTest(unittest.TestCase):
    def compile_probe(self, source: str, main: str = "Main") -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            Path(folder, "Main.hx").write_text(textwrap.dedent(source), newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", main, "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(TMP)},
                capture_output=True, text=True, timeout=90,
            )
            return result

    def test_camera_transform_matches_matrix_and_culling_bounds(self):
        source = SOURCE.read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "\tpublic static function cameraZoomScale(",
                "\tpublic static function hasCameraTransform(",
                "\tpublic static function transformCameraPoint(",
                "\tpublic static function applyCameraTransform(",
                "\toverride function drawFrameComplex(",
                "\toverride function prepareDrawMatrix(",
            )
        )
        bounds = extract_method(source, "\toverride public function getScreenBounds(")
        simple = extract_method(source, "\toverride public function isSimpleRenderBlit(")
        fixture = '''
            class FlxCamera {
              public var width:Int=800; public var height:Int=600;
              public var scaleX:Float=2; public var scaleY:Float=2; public var angle:Float=0;
              public var scroll:FlxPoint=new FlxPoint();
              public var drawn:FlxMatrix;
              public function new() {}
              public function drawPixels(_frame:Dynamic,_pixels:Dynamic,matrix:FlxMatrix,
                _color:Dynamic,_blend:Dynamic,_smooth:Bool,_shader:Dynamic):Void {
                drawn=matrix.copy();
              }
            }
            class FlxFrameAngle {public static var ANGLE_0:Int=0;}
            class FlxFrame {
              public function new() {}
              public function prepareMatrix(m:FlxMatrix,_angle:Int,_flipX:Bool,_flipY:Bool):Void m.identity();
            }
            class FlxAngle { public static var TO_RAD:Float=Math.PI/180; }
            class FlxPoint {
              public var x:Float; public var y:Float;
              public function new(x:Float=0,y:Float=0) {this.x=x;this.y=y;}
              public function set(x:Float,y:Float):FlxPoint {this.x=x;this.y=y;return this;}
              public function subtract(other:FlxPoint):FlxPoint {x-=other.x;y-=other.y;return this;}
              public function add(dx:Float,dy:Float):FlxPoint {x+=dx;y+=dy;return this;}
            }
            class FlxRect {
              public var x:Float; public var y:Float; public var width:Float; public var height:Float;
              public function new(x:Float=0,y:Float=0,w:Float=0,h:Float=0) set(x,y,w,h);
              public function set(x:Float,y:Float,w:Float,h:Float):FlxRect {
                this.x=x;this.y=y;this.width=w;this.height=h;return this;
              }
              public function floor():FlxRect {x=Math.floor(x);y=Math.floor(y);return this;}
            }
            class FlxMatrix {
              public var a:Float=1; public var b:Float=0; public var c:Float=0; public var d:Float=1;
              public var tx:Float=0; public var ty:Float=0;
              public function new() {}
              public function identity():Void setTo(1,0,0,1,0,0);
              public function copy():FlxMatrix return new FlxMatrix().setTo(a,b,c,d,tx,ty);
              public function setTo(a:Float,b:Float,c:Float,d:Float,tx:Float,ty:Float):FlxMatrix {
                this.a=a;this.b=b;this.c=c;this.d=d;this.tx=tx;this.ty=ty;return this;
              }
              public function translate(x:Float,y:Float):FlxMatrix {tx+=x;ty+=y;return this;}
              public function scale(sx:Float,sy:Float):FlxMatrix {
                a*=sx;c*=sx;tx*=sx;b*=sy;d*=sy;ty*=sy;return this;
              }
              public function rotateWithTrig(cos:Float,sin:Float):FlxMatrix {
                var aa=a*cos-b*sin;b=a*sin+b*cos;a=aa;
                var cc=c*cos-d*sin;d=c*sin+d*cos;c=cc;
                var xx=tx*cos-ty*sin;ty=tx*sin+ty*cos;tx=xx;return this;
              }
              public function rotate(r:Float):FlxMatrix {
                var cos=Math.cos(r),sin=Math.sin(r);
                var aa=a*cos-b*sin; b=a*sin+b*cos; a=aa;
                var cc=c*cos-d*sin; d=c*sin+d*cos; c=cc;
                var xx=tx*cos-ty*sin; ty=tx*sin+ty*cos; tx=xx;return this;
              }
              public function concat(other:FlxMatrix):FlxMatrix {
                var aa=a*other.a+c*other.b,bb=b*other.a+d*other.b;
                var cc=a*other.c+c*other.d,dd=b*other.c+d*other.d;
                var xx=a*other.tx+c*other.ty+tx,yy=b*other.tx+d*other.ty+ty;
                return setTo(aa,bb,cc,dd,xx,yy);
              }
            }
            class FakeTimeline {
              public var calls:Int=0;
              public function new() {}
              public function getBoundsOrigin(point:FlxPoint):FlxPoint {
                calls++;return point.set(4,5);
              }
            }
            class FakeLibrary {
              public var matrix:FlxMatrix=new FlxMatrix();
              public function new() {}
            }
            class FakeSprite {
              public var x:Float=0; public var y:Float=0; public var width:Float=100; public var height:Float=50;
              public var isAnimate:Bool=false;
              public var frameWidth:Float=100;public var frameHeight:Float=50;
              public var frameOffset:FlxPoint=new FlxPoint();
              public var frameOffsetAngle:Null<Float>=null;
              public var timeline:FakeTimeline=new FakeTimeline();
              public var library:FakeLibrary=new FakeLibrary();
              public var applyStageMatrix:Bool=true;
              public var skew:FlxPoint=new FlxPoint();
              public var origin:FlxPoint=new FlxPoint();public var offset:FlxPoint=new FlxPoint();
              public var scrollFactor:FlxPoint=new FlxPoint(1,1);
              public var scale:FlxPoint=new FlxPoint(1,1);
              public var angle:Float=0;public var bakedRotationAngle:Float=0;
              public var _cosAngle:Float=1;public var _sinAngle:Float=0;
              public var _matrix:FlxMatrix=new FlxMatrix();public var _point:FlxPoint=new FlxPoint();
              public var framePixels:Dynamic=null;public var colorTransform:Dynamic=null;
              public var blend:Dynamic=null;public var antialiasing:Bool=false;public var shader:Dynamic=null;
              public var pixelPerfect:Bool=false;
              public var pixelPerfectPosition:Bool=false;
              public var zoomFactor:Float=1; public var angleFactor:Float=1;
              public var zoomFactorEnabled:Bool=true; public var angleFactorEnabled:Bool=true;
              public function new() {}
              public function getDefaultCamera():FlxCamera return new FlxCamera();
              public function getScreenBounds(?r:FlxRect,?camera:FlxCamera):FlxRect {
                if(r==null)r=new FlxRect();
                if(camera==null)camera=getDefaultCamera();
                r.set(x,y,0,0);
                if(pixelPerfectPosition)r.floor();
                var scaledX=origin.x*scale.x,scaledY=origin.y*scale.y;
                r.x+=-Std.int(camera.scroll.x*scrollFactor.x)-offset.x+origin.x-scaledX;
                r.y+=-Std.int(camera.scroll.y*scrollFactor.y)-offset.y+origin.y-scaledY;
                if(isPixelPerfectRender(camera))r.floor();
                r.width=frameWidth*Math.abs(scale.x);r.height=frameHeight*Math.abs(scale.y);
                // FlxRect.getRotatedBounds(angle, scaledOrigin), with signed
                // origin but absolute frame dimensions, as local Flixel 6.1.2.
                var radians=angle*FlxAngle.TO_RAD,co=Math.cos(radians),si=Math.sin(radians);
                var baseX=r.x+scaledX,baseY=r.y+scaledY;
                var a=[baseX+co*(-scaledX)-si*(-scaledY),
                       baseY+si*(-scaledX)+co*(-scaledY)];
                var b=[baseX+co*(r.width-scaledX)-si*(-scaledY),
                       baseY+si*(r.width-scaledX)+co*(-scaledY)];
                var c=[baseX+co*(-scaledX)-si*(r.height-scaledY),
                       baseY+si*(-scaledX)+co*(r.height-scaledY)];
                var d=[baseX+co*(r.width-scaledX)-si*(r.height-scaledY),
                       baseY+si*(r.width-scaledX)+co*(r.height-scaledY)];
                var loX=Math.min(Math.min(a[0],b[0]),Math.min(c[0],d[0]));
                var hiX=Math.max(Math.max(a[0],b[0]),Math.max(c[0],d[0]));
                var loY=Math.min(Math.min(a[1],b[1]),Math.min(c[1],d[1]));
                var hiY=Math.max(Math.max(a[1],b[1]),Math.max(c[1],d[1]));
                return r.set(loX,loY,hiX-loX,hiY-loY);
              }
              public function getScreenPosition(p:FlxPoint,camera:FlxCamera):FlxPoint {
                p.set(pixelPerfectPosition?Math.floor(x):x,pixelPerfectPosition?Math.floor(y):y);
                return p.set(p.x-camera.scroll.x*scrollFactor.x,p.y-camera.scroll.y*scrollFactor.y);
              }
              public function isPixelPerfectRender(_camera:FlxCamera):Bool return pixelPerfect;
              public function prepareDrawMatrix(_matrix:FlxMatrix,_camera:FlxCamera):Void {}
              public function checkFlipX():Bool return false;
              public function checkFlipY():Bool return false;
              public function updateTrig():Void {
                _cosAngle=Math.cos(angle*FlxAngle.TO_RAD);
                _sinAngle=Math.sin(angle*FlxAngle.TO_RAD);
              }
              function drawFrameComplex(_frame:FlxFrame,_camera:FlxCamera):Void {}
              public function isSimpleRenderBlit(?camera:FlxCamera):Bool return true;
            }
            class Probe extends FakeSprite {
              static var _codenameSkewMatrix:FlxMatrix=new FlxMatrix();
        ''' + methods + "\n" + bounds + "\n" + simple + '''
              public function render(camera:FlxCamera):Void drawFrameComplex(new FlxFrame(),camera);
            }
            class Main {
              static function close(a:Float,b:Float):Bool return Math.abs(a-b)<0.00001;
              public static function corner(m:FlxMatrix,x:Float,y:Float):Array<Float>
                return [m.a*x+m.c*y+m.tx,m.b*x+m.d*y+m.ty];
              static function checkDrawBounds(sprite:Probe,camera:FlxCamera,label:String):Void {
                sprite.render(camera);
                var m=camera.drawn,bounds=sprite.getScreenBounds(new FlxRect(),camera);
                var corners=[corner(m,0,0),corner(m,sprite.width,0),
                  corner(m,0,sprite.height),corner(m,sprite.width,sprite.height)];
                var loX=1e20,hiX=-1e20,loY=1e20,hiY=-1e20;
                for(p in corners) {
                  loX=Math.min(loX,p[0]);hiX=Math.max(hiX,p[0]);
                  loY=Math.min(loY,p[1]);hiY=Math.max(hiY,p[1]);
                  if(p[0]<bounds.x-0.00001 || p[0]>bounds.x+bounds.width+0.00001
                    || p[1]<bounds.y-0.00001 || p[1]>bounds.y+bounds.height+0.00001)
                    throw label+' culling missed draw corner '+p+' in '+bounds.x+','+bounds.y+','+bounds.width+','+bounds.height;
                }
                if(!sprite.pixelPerfect && (!close(bounds.x,loX) || !close(bounds.y,loY)
                  || !close(bounds.width,hiX-loX) || !close(bounds.height,hiY-loY)))
                  throw label+' bounds differ from draw matrix';
              }
              static function point(p:Array<Float>,x:Float,y:Float,label:String):Void
                if(p==null || !close(p[0],x) || !close(p[1],y)) throw label+': '+p;
              static function main() {
                var camera=new FlxCamera();
                if(!close(Probe.cameraZoomScale(2,1),1)
                  || !close(Probe.cameraZoomScale(2,0),0.5)
                  || !close(Probe.cameraZoomScale(-2,0),-0.5))
                  throw 'upstream camera scale factor changed';
                point(Probe.transformCameraPoint(0,0,camera,0,1,true,true),200,150,
                  'zero zoomFactor must cancel camera zoom around viewport center');
                point(Probe.transformCameraPoint(400,300,camera,0,1,true,true),400,300,
                  'viewport center must remain fixed');
                camera.angle=90;
                var expected=Probe.transformCameraPoint(600,300,camera,0.5,0,true,true);
                var matrix=new FlxMatrix().setTo(1,0,0,1,600,300);
                Probe.applyCameraTransform(matrix,camera,0.5,0,true,true);
                if(!close(matrix.tx,expected[0]) || !close(matrix.ty,expected[1]))
                  throw 'draw matrix and culling point transform differ';
                camera.angle=0;
                var sprite=new Probe();sprite.zoomFactor=0;sprite.frameOffset.set(10,-5);
                var bounds=sprite.getScreenBounds(new FlxRect(),camera);
                if(!close(bounds.x,195) || !close(bounds.y,152.5)
                  || !close(bounds.width,50) || !close(bounds.height,25))
                  throw 'pre-draw culling bounds omitted camera transform or frame offset';
                checkDrawBounds(sprite,camera,'negative offset');
                sprite.zoomFactor=1;sprite.scale.set(2,3);sprite.angle=90;
                checkDrawBounds(sprite,camera,'nonuniform scale and sprite angle');
                sprite.frameOffsetAngle=0;
                checkDrawBounds(sprite,camera,'frameOffsetAngle sandwich');
                camera.angle=35;sprite.zoomFactor=.4;sprite.angleFactor=.2;
                checkDrawBounds(sprite,camera,'viewport camera transform');
                sprite.scale.set(-2,3);
                checkDrawBounds(sprite,camera,'negative scale');
                sprite.origin.set(32,12);sprite.angle=0;
                checkDrawBounds(sprite,camera,'negative scale with nonzero origin');
                sprite.angle=90;sprite.scale.set(-2,-3);
                checkDrawBounds(sprite,camera,'reflected axes with rotation');
                camera.scroll.set(10.25,-5.75);
                checkDrawBounds(sprite,camera,'fractional camera scroll');
                sprite.frameOffset.set(.25,-.625);sprite.pixelPerfect=true;
                checkDrawBounds(sprite,camera,'fractional pixel culling');
                sprite.frameOffset.set(0,0);
                checkDrawBounds(sprite,camera,'reflected pixel culling without offset');
                sprite.scale.set(-1.25,2.75);
                checkDrawBounds(sprite,camera,'fractional reflected scale and scroll without offset');
                sprite.pixelPerfect=false;sprite.scale.set(1,1);sprite.angle=0;
                sprite.origin.set(0,0);camera.scroll.set(0,0);
                sprite.frameOffsetAngle=null;camera.angle=0;
                if(sprite.isSimpleRenderBlit(camera)) throw 'camera zoom transform used the simple blit path';
                sprite.zoomFactor=1;sprite.angleFactor=0;
                if(sprite.isSimpleRenderBlit(camera)) throw 'non-default angleFactor used the simple blit path';
                sprite.angleFactor=1;sprite.frameOffset.set(0,0);
                checkDrawBounds(sprite,camera,'zero offset');
                if(!sprite.isSimpleRenderBlit(camera)) throw 'default factors disabled the native simple path';

                var animateSprite=new Probe();
                animateSprite.isAnimate=true;animateSprite.applyStageMatrix=true;
                animateSprite.x=100;animateSprite.y=50;
                camera.scroll.set(0,0);camera.scaleX=2;camera.scaleY=3;
                animateSprite.zoomFactor=0.5;
                var atlasMatrix=new FlxMatrix();
                animateSprite.prepareDrawMatrix(atlasMatrix,camera);
                if(animateSprite.timeline.calls!=1 || !close(atlasMatrix.tx,178)
                  || !close(atlasMatrix.ty,136.6666666667))
                  throw 'Animate draw matrix omitted stage bounds or camera-relative scaling: '+atlasMatrix.tx+','+atlasMatrix.ty;
              }
            }
        '''
        result = self.compile_probe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        self.assertIn("applyCameraTransform(matrix, camera, zoomFactor, angleFactor", source)
        self.assertIn("return camera.containsRect(getScreenBounds(_rect, camera));",
                      (ROOT / ".haxelib/flixel/6,1,2/flixel/FlxSprite.hx").read_text())
        self.assertIn("camera.drawPixels(frame, framePixels, matrix", source)
        self.assertIn("class CodenameFunkinSprite extends FlxAnimate", source)
        self.assertIn("public var frameOffsetAngle:Null<Float> = null;", source)
        self.assertIn("override function prepareDrawMatrix(matrix:FlxMatrix, camera:FlxCamera)", source)
        self.assertIn("matrix.concat(library.matrix);", source)
        self.assertIn("anim.addBySymbol(name, prefix, fps, doesLoop);", source)

    def test_scoped_loading_animation_offsets_and_swap_are_real_operations(self):
        source = SOURCE.read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "\tpublic function loadSprite(",
                "\tfunction reportAssetIssue(",
                "\tpublic function addOffset(",
                "\tpublic function switchOffset(",
                "\tpublic function getAnimOffset(",
                "\tpublic function addAnim(",
                "\tpublic inline function removeAnim(",
                "\tpublic function playAnim(",
                "\tpublic inline function isAnimAtEnd(",
            )
        ).replace("CodenameFunkinSprite", "Probe")
        has_anim_start = source.index("\tpublic inline function hasAnim(")
        has_anim_end = source.index("\n", source.index("\n", has_anim_start) + 1)
        methods += "\n" + source[has_anim_start:has_anim_end]
        fixture = '''
            class FlxFramesCollection { public function new() {} }
            class FlxAnimateFrames extends FlxFramesCollection {}
            class FlxGraphic {}
            class BitmapData { public function new() {} }
            class FlxPoint {
              public var x:Float; public var y:Float;
              public function new(x:Float=0,y:Float=0) {this.x=x;this.y=y;}
              public static function get(x:Float=0,y:Float=0):FlxPoint return new FlxPoint(x,y);
              public static function weak(x:Float=0,y:Float=0):FlxPoint return new FlxPoint(x,y);
              public function set(x:Float,y:Float):FlxPoint {this.x=x;this.y=y;return this;}
              public function put():Void {}
            }
            typedef CodenameSpriteAnimationData = { var forced:Bool; }
            class FakeAnim {
              public var name:String; public var curFrame:Int=0; public var numFrames:Int=3;
              public var finished:Bool=false; public var reversed:Bool=false;
              public function new(name:String) this.name=name;
            }
            class FakeAnimationController {
              public var curAnim:FakeAnim; public var calls:Array<Dynamic>=[];
              var names:Map<String,Bool>=new Map();
              public function new() {}
              public function addByIndices(n:String,p:String,i:Array<Int>,s:String,f:Float,l:Bool):Void {
                calls.push(['indices',n,p,i.copy(),f,l]); names.set(n,true);
              }
              public function addByPrefix(n:String,p:String,f:Float,l:Bool):Void {
                calls.push(['prefix',n,p,f,l]); names.set(n,true);
              }
              public function addBySymbol(n:String,p:String,f:Float,l:Bool):Void {
                calls.push(['symbol',n,p,f,l]); names.set(n,true);
              }
              public function addBySymbolIndices(n:String,p:String,i:Array<Int>,f:Float,l:Bool):Void {
                calls.push(['symbol-indices',n,p,i.copy(),f,l]); names.set(n,true);
              }
              public function addByFrameLabel(n:String,p:String,f:Float,l:Bool):Void {
                calls.push(['frame-label',n,p,f,l]); names.set(n,true);
              }
              public function addByFrameLabelIndices(n:String,p:String,i:Array<Int>,f:Float,l:Bool):Void {
                calls.push(['frame-label-indices',n,p,i.copy(),f,l]); names.set(n,true);
              }
              public function remove(n:String):Void names.remove(n);
              public function exists(n:String):Bool return names.exists(n);
              public function getNameList():Array<String> return [for(n in names.keys()) n];
              public function stop():Void {}
              public function play(n:String,force:Bool,reversed:Bool,frame:Int):Void {
                calls.push(['play',n,force,reversed,frame]);curAnim=new FakeAnim(n);
              }
            }
            class Paths {
              public static var calls:Int=0;
              public static function getSparrowAtlas(_path:String):FlxFramesCollection {
                calls++;return new FlxFramesCollection();
              }
              public static function image(_path:String):String {calls++;return 'native-image';}
            }
            class FakeAnimateLibrary {
              public var hasRhyme:Bool=false;
              public function new() {}
              public function getSymbol(name:String):Dynamic
                return name=='RHYME' && hasRhyme ? this : null;
            }
            class Probe {
              public var assetResolver:Dynamic;
              public var assetDiagnostic:String='';
              public var frames:Dynamic;
              public var loadedGraphic:Dynamic;
              public var animation:FakeAnimationController=new FakeAnimationController();
              public var anim:FakeAnimationController;
              public var library:FakeAnimateLibrary=new FakeAnimateLibrary();
              public var animOffsets:Map<String,FlxPoint>=new Map();
              public var animDatas:Map<String,CodenameSpriteAnimationData>=new Map();
              public var frameOffset:FlxPoint=new FlxPoint();
              public var debugMode:Bool=false;public var lastAnimContext:Dynamic='DANCE';
              public function new(resolver:Dynamic) {assetResolver=resolver;anim=animation;}
              public function loadGraphic(value:Dynamic,_animated:Bool=false,_width:Int=0,_height:Int=0,
                _unique:Bool=false,_key:String=null):Probe {loadedGraphic=value;return this;}
        ''' + methods + '''
            }
            class Main {
              static function close(a:Float,b:Float):Bool return Math.abs(a-b)<0.00001;
              static function checkOffset(sprite:Probe,name:String,x:Float,y:Float):Void {
                var value=sprite.animOffsets.get(name);
                if(value==null || !close(value.x,x) || !close(value.y,y))
                  throw name+' offset mismatch: '+value;
              }
              static function main() {
                var atlas=new FlxFramesCollection();var requested='';
                var resolver={getFrames:function(key:String):Dynamic {requested=key;return atlas;}};
                var sprite=new Probe(resolver);
                if(sprite.loadSprite('owner/sprites/monster')!=sprite || sprite.frames!=atlas
                  || requested!='owner/sprites/monster' || Paths.calls!=0)
                  throw 'scoped getFrames did not own loadSprite';
                var resolvedBitmap=new BitmapData();
                sprite.loadSprite(resolvedBitmap);
                if(sprite.loadedGraphic!=resolvedBitmap || Paths.calls!=0
                  || requested!='owner/sprites/monster')
                  throw 'Paths.image bitmap was mistaken for an asset key';
                sprite.loadSprite(atlas);
                if(sprite.frames!=atlas || Paths.calls!=0)
                  throw 'resolved atlas was mistaken for an asset key';
                sprite.addAnim('intro','MonsterIntro',24,false,true,[1,3],7,-2);
                sprite.addAnim('idle','Idle',12,true,false,null,0,5);
                if(sprite.animation.calls[0][0]!='indices' || sprite.animation.calls[1][0]!='prefix')
                  throw 'basic prefix/indices animation setup failed';

                var animateSprite=new Probe(null);
                animateSprite.frames=new FlxAnimateFrames();
                animateSprite.library.hasRhyme=true;
                animateSprite.addAnim('rhyme','RHYME',24,false);
                animateSprite.addAnim('rhymePart','RHYME',24,false,false,[1,3]);
                animateSprite.addAnim('rhymeLabel','Intro Label',24,null,false,[0,2],0,0,'LOOP',true);
                if(animateSprite.animation.calls[0][0]!='symbol'
                  || animateSprite.animation.calls[1][0]!='symbol-indices'
                  || animateSprite.animation.calls[2][0]!='frame-label-indices'
                  || animateSprite.animation.calls[2][5]!=true)
                  throw 'Animate symbol animation bypassed FlxAnimateController';
                var ordinaryAtlas=new Probe(null);
                ordinaryAtlas.frames=new FlxFramesCollection();
                ordinaryAtlas.addAnim('prefix','RHYME',24,false);
                if(ordinaryAtlas.animation.calls[0][0]!='prefix')
                  throw 'ordinary frame atlas stopped using prefix animation';
                sprite.playAnim('intro',null,'LOCK');
                var play= sprite.animation.calls[2];
                if(play[0]!='play' || play[1]!='intro' || Std.string(play[2])!='true'
                  || sprite.lastAnimContext!='LOCK' || sprite.frameOffset.x!=7 || sprite.frameOffset.y!=-2)
                  throw 'playAnim did not preserve forced animation context and offsets';
                if(sprite.isAnimAtEnd()) throw 'animation start incorrectly counts as terminal frame';
                sprite.animation.curAnim.curFrame=2;
                if(!sprite.isAnimAtEnd()) throw 'forward endpoint was not recognized';
                sprite.animation.curAnim.reversed=true;sprite.animation.curAnim.curFrame=0;
                if(!sprite.isAnimAtEnd()) throw 'reverse endpoint was not recognized';
                sprite.animation.curAnim.curFrame=1;
                if(sprite.isAnimAtEnd()) throw 'middle frame incorrectly counts as endpoint';
                sprite.playAnim('missing',null,null);
                sprite.playAnim(null,null,null);
                if(sprite.lastAnimContext!='LOCK') throw 'rejected requests changed context';
                sprite.playAnim('idle');
                if(sprite.lastAnimContext!=null) throw 'default NONE retained prior context';
                sprite.playAnim('intro',false,'LOCK');
                sprite.playAnim('idle',false,null);
                if(sprite.lastAnimContext!=null) throw 'explicit NONE retained prior context';
                sprite.switchOffset('intro','idle');
                checkOffset(sprite,'intro',0,5);checkOffset(sprite,'idle',7,-2);
                sprite.switchOffset('intro','missing');
                if(sprite.animOffsets.exists('intro')) throw 'swap with a missing second key retained the first key';
                checkOffset(sprite,'missing',0,5);
                sprite.switchOffset('absent','idle');
                checkOffset(sprite,'absent',7,-2);
                if(sprite.animOffsets.exists('idle')) throw 'swap with a missing first key retained the second key';
                sprite.removeAnim('intro');
                if(sprite.hasAnim('intro')) throw 'removeAnim retained its animation';

                var before=Paths.calls;
                var missing=new Probe({getFrames:function(_key:String):Dynamic {return null;}});
                missing.loadSprite('owner/missing');
                if(missing.assetDiagnostic.indexOf('owner/missing')<0 || Paths.calls!=before)
                  throw 'strict resolver miss was silent or fell through to global Paths';
                var bad=new Probe({getFrames:function(_key:String):Dynamic {return 'global/path.png';}});
                bad.loadSprite('owner/bad');
                if(bad.loadedGraphic!=null || bad.assetDiagnostic.indexOf('unsupported')<0)
                  throw 'scoped resolver path string escaped strict asset ownership';
              }
            }
        '''
        result = self.compile_probe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        self.assertIn("getFrames", source)
        self.assertIn("scoped asset was not found", source)
        self.assertIn("var first = animOffsets.get(anim1);", source)
        self.assertIn("var second = animOffsets.get(anim2);", source)
        self.assertIn("public var zoomFactor:Float = 1;", source)
        self.assertIn("public var angleFactor:Float = 1;", source)


if __name__ == "__main__":
    unittest.main()
