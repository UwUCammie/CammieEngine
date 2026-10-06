"""Source health math and native icon-frame setter comparisons with pinned donors."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_nv_multifield_routes import method
from source_bar_fixture_support import bar_fixture_files

ROOT = Path(__file__).resolve().parents[2]


class SourceHealthPolicyTest(unittest.TestCase):
    def test_numeric_policy_and_actual_icon_method_match_donor(self):
        donor_root = ROOT.parent / 'fnf_sources'
        psych = (donor_root / 'FNF-PsychEngine/source/states/PlayState.hx').read_text()
        nv = (donor_root / 'NightmareVision/source/funkin/states/PlayState.hx').read_text()
        icon = (donor_root / 'NightmareVision/source/funkin/objects/HealthIcon.hx').read_text()
        native_icon = (ROOT / 'source/HealthIcon.hx').read_text()
        psych_setter = method(psych, 'function set_health(')
        nv_setter = method(nv, 'function set_health(')
        nv_update = nv[nv.index('\t\tif (healthBounds.max > healthBounds.min && health > healthBounds.max)'):nv.index('\t\tif (startingSong)', nv.index('\t\tif (healthBounds.max > healthBounds.min && health > healthBounds.max)'))]
        psych_update = psych[psych.index('\t\tif (healthBar.bounds.max != null && health > healthBar.bounds.max)'):psych.index('\t\tupdateIconsScale(elapsed);', psych.index('\t\tif (healthBar.bounds.max != null && health > healthBar.bounds.max)'))]
        files = bar_fixture_files()
        files['DonorHealth.hx'] = '''import flixel.math.FlxMath;
class DonorHealth {public var health(default,set):Float=1;public var iconsAnimations=true;public var healthBar:Dynamic;public var iconP1={animation:{curAnim:{curFrame:3}}};public var iconP2={animation:{curAnim:{curFrame:3}}};public var calls=0;public var observed=0.;public var healthBounds={min:0.,max:2.};public function new(){healthBar={enabled:true,bounds:{min:0.,max:2.},percent:0.,valueFunction:function(){calls++;observed=health;return health;}};}
__SETTER__ public function nvBound(value:Float,min:Float,max:Float):Float { @:bypassAccessor health=value;healthBounds={min:min,max:max};__NV__return health;}public function psychBound(value:Float,max:Null<Float>):Float {@:bypassAccessor health=value;healthBar.bounds.max=max;__PS__return health;}}
'''.replace('__SETTER__', psych_setter).replace('__NV__', nv_update).replace('__PS__', psych_update)
        files['DonorNVHealth.hx'] = 'class DonorNVHealth {public var health(default,set):Float=1;public var healthBounds={min:0.,max:2.};public var calls=0;public function new(){}function callHUDFunc(fn:Dynamic->Void):Void {calls++;fn({onHealthChange:function(v:Float){}});}' + nv_setter + 'public function bound(value:Float,min:Float,max:Float):Float {@:bypassAccessor health=value;healthBounds={min:min,max:max};' + nv_update + 'return health;}}'
        animation = (ROOT / '.haxelib/flixel/6,1,2/flixel/animation/FlxAnimationController.hx').read_text()
        frame_setter = method(animation, 'function set_frameIndex(')
        callback = method(animation, 'function fireCallback(')
        files['FrameController.hx'] = '''import flixel.util.FlxSignal.FlxTypedSignal;
class FrameController {public var frameIndex(default,set)=0;public var numFrames:Int;public var _sprite:Dynamic;public var _curAnim:Dynamic;public var callback:String->Int->Int->Void;public var onFrameChange=new FlxTypedSignal<String->Int->Int->Void>();public function new(count:Int){numFrames=count;_sprite={frame:null,frames:{frames:[for(i in 0...count){name:"cell"+i}]}};}__SETTER__ __CALLBACK__}
'''.replace('__SETTER__', frame_setter).replace('__CALLBACK__', callback)
        files['HostIcon.hx'] = 'class HostIcon {public var updateFrames=true;public var autoUpdate=false;public var animation:FrameController;public function new(count:Int)animation=new FrameController(count);@:keep ' + method(native_icon, 'public inline function updateIconAnim(') + '}'
        files['DonorIcon.hx'] = 'class DonorIcon {public var updateFrames=true;public var animation:FrameController;public function new(count:Int)animation=new FrameController(count);' + method(icon, 'public inline function updateIconAnim(') + '}'
        files['Main.hx'] = r'''
class Main {
 static function check(v:Bool,m:String)if(!v)throw m;
 static function same(a:Float,b:Float,m:String)check((Math.isNaN(a)&&Math.isNaN(b))||a==b,m+":"+a+" != "+b);
 static function main(){
  var d=new DonorHealth(),nv=new DonorNVHealth();
  for(v in [-3.123456,-.000006,-.000005,-.000004,0.,.000004,.000005,.000006,.399999,.4,1.,1.600001,2.123456,5.,Math.NaN,Math.POSITIVE_INFINITY,Math.NEGATIVE_INFINITY]){
   d.healthBar.bounds={min:0.,max:2.};d.iconsAnimations=false;d.health=v;same(SourceHealthPolicy.psychAssignment(v),d.health,"actual setter rounding");
   d.iconsAnimations=true;d.healthBar.enabled=true;d.health=v;same(SourceHealthPolicy.percent(d.health,0,2),d.healthBar.percent,"actual setter percent");
   check(SourceHealthPolicy.psychPlayerFrame(d.healthBar.percent)==d.iconP1.animation.curAnim.curFrame&&SourceHealthPolicy.psychOpponentFrame(d.healthBar.percent)==d.iconP2.animation.curAnim.curFrame,"actual strict icon thresholds");same(d.observed,d.health,"store before source callback");
   for(pair in [[0.,2.],[-2.,4.],[2.,0.],[1.,1.],[0.,3.123456]]){nv.calls=0;same(SourceHealthPolicy.nightmareUpdateBound(v,pair[0],pair[1]),nv.bound(v,pair[0],pair[1]),"actual NV update bound");check(SourceHealthPolicy.shouldNightmareUpdateBound(v,pair[0],pair[1])==(nv.calls==1),"actual cap decision, including NaN without callbacks");}
   for(max in [null,-2.,0.,2.,4.]){same(SourceHealthPolicy.psychUpdateBound(v,max),d.psychBound(v,max),"actual Psych nullable update maximum");check(SourceHealthPolicy.shouldPsychUpdateBound(v,max)==(max!=null&&v>max),"actual Psych cap predicate");}
  }
  // Actual source setter remaps reversed/equal bounds using sequential Flixel.bound.
  for(pair in [[0.,2.],[2.,0.],[1.,1.],[-2.,4.]])for(v in [-4.,0.,1.,6.]){d.healthBar.bounds={min:pair[0],max:pair[1]};d.health=v;same(SourceHealthPolicy.percent(d.health,pair[0],pair[1]),d.healthBar.percent,"actual bound/remap extremes");}
  for(count in [0,1,2,4])for(enabled in [false,true])for(v in [-1.,.199999,.2,.200001,.8,1.,2.]){
   var h=new HostIcon(count),i=new DonorIcon(count);h.updateFrames=i.updateFrames=enabled;var hc=0,dc=0;h.animation.onFrameChange.add(function(n,f,index){hc++;});i.animation.onFrameChange.add(function(n,f,index){dc++;});h.updateIconAnim(v);i.updateIconAnim(v);
   check(h.animation.frameIndex==i.animation.frameIndex&&hc==dc,"actual icon and Flixel setter dispatch");check((h.animation._sprite.frame==null)==(i.animation._sprite.frame==null),"actual native frame selection/null frames");if(count==2&&enabled){check(h.animation.frameIndex==(v<.2?1:0)&&hc==1,"source two-frame threshold independent from host autoUpdate");}
  }
  var reflected=new HostIcon(2);var callable=Reflect.field(reflected,"updateIconAnim");check(Reflect.isFunction(callable),"source script/Reflect method remains callable");Reflect.callMethod(reflected,callable,[.1]);check(reflected.animation.frameIndex==1,"reflected source frame mutation");
 }
}
'''
        signal_root = ROOT / '.haxelib/flixel/6,1,2/flixel/util'
        files['flixel/util/FlxSignal.hx'] = (signal_root / 'FlxSignal.hx').read_text()
        destroy = (signal_root / 'FlxDestroyUtil.hx').read_text()
        files['flixel/util/FlxDestroyUtil.hx'] = 'package flixel.util;interface IFlxDestroyable {public function destroy():Void;}class FlxDestroyUtil {' + method(destroy, 'public static function destroy<') + method(destroy, 'public static function destroyArray<') + '}'
        files['flixel/util/IFlxDestroyable.hx'] = 'package flixel.util;typedef IFlxDestroyable=flixel.util.FlxDestroyUtil.IFlxDestroyable;'
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for name, source in files.items():
                p = temp / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(source)
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True)
            env = os.environ.copy()
            env['HAXEPATH'] = str(ROOT / '.tools/haxe')
            env['NEKOPATH'] = str(ROOT / '.tools/neko')
            env['HAXELIB_PATH'] = str(ROOT / '.haxelib')
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            cpp = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main', '-cpp', str(temp / 'cpp'), '-D', 'no-compilation'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            generated = (temp / 'cpp/src/HostIcon.cpp').read_text() if cpp.returncode == 0 else ''
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-8000:])
        self.assertEqual(cpp.returncode, 0, (cpp.stdout + cpp.stderr)[-8000:])
        self.assertIn('HX_FIELD_EQ(inName,"updateIconAnim")', generated)
        self.assertIn('updateIconAnim_dyn()', generated)
