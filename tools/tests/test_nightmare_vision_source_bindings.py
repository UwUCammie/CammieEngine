"""Probe the source preset helper's owner/gameplay scopes and option persistence."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class NightmareVisionSourceBindingsTest(unittest.TestCase):
    def test_owner_options_keys_random_and_gameplay_contract(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''
import haxe.ds.StringMap;
class SaveData {
 public var ownerKey:String;
 public var data:Map<String,Dynamic>=new Map();
 public var flushCount:Int=0;
 public function new(owner:String)this.ownerKey=owner;
 public function getField(key:String):Dynamic return data.get(key);
 public function setField(key:String,value:Dynamic):Dynamic {data.set(key,value);return value;}
 public function flush():Void flushCount++;
}
class SaveFacade {public var data:SaveData;public function new(data:SaveData)this.data=data;}
class LivePlayState {
 var sourceVariables:Map<String,Dynamic>;
 public var variables(get,never):Map<String,Dynamic>;
 public var variableReads:Int=0;
 public function new(values:Map<String,Dynamic>)this.sourceVariables=values;
 function get_variables():Map<String,Dynamic>{variableReads++;return sourceVariables;}
}
class Interp {
 static var saves:Map<String,SaveData>=new Map();
 public var variables:Map<String,Dynamic>=new Map();
 public var imports:Map<String,Dynamic>=new Map();
 public var ownerSave:SaveFacade;
 public function new(owner:String){if(!saves.exists(owner))saves.set(owner,new SaveData(owner));ownerSave=new SaveFacade(saves.get(owner));}
 public function bindImport(path:String,value:Dynamic):Void imports.set(path,value);
}
class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function invoke(target:Dynamic,method:String,args:Array<Dynamic>):Dynamic {
  var fn=(cast target:Map<String,Dynamic>).get(method);return Reflect.callMethod(null,fn,args);
 }
 static function main():Void {
  var owner='assets/imported_mods/selected';
  var interp=new Interp(owner);
  var options=NightmareVisionSourceBindings.bindOwner(interp,owner,'content/selected');
  check(interp.variables.get('version')=='1.0','donor NMV version global');
  check(Reflect.field(interp.variables.get('Main'),'NMV_VERSION')=='1.0','version-only Main facade');
  check(interp.variables.get('modFolder')=='content/selected','owner modFolder global');
  check(interp.variables.get('keyToString')(flixel.input.keyboard.FlxKey.A)=='A','keyToString matches FlxKey table');
  check(interp.variables.get('keyFromString')('SPACE')==flixel.input.keyboard.FlxKey.SPACE,'keyFromString matches FlxKey table');
  var runtimeKeys:Dynamic=interp.variables.get('FlxKey');
  var importedKeys:Dynamic=interp.imports.get('flixel.input.keyboard.FlxKey');
  check(runtimeKeys!=null && Reflect.field(runtimeKeys,'A')==flixel.input.keyboard.FlxKey.A
    && Reflect.field(runtimeKeys,'SPACE')==flixel.input.keyboard.FlxKey.SPACE,'runtime FlxKey snapshot exposes enum constants');
  check(importedKeys==runtimeKeys,'source FlxKey import reuses the runtime snapshot facade');
  var underlay:Dynamic=interp.variables.get('UnderlayType');
  check(underlay!=null && underlay.FIELD=='Lane Underlay' && underlay.SCREEN=='Screen Dim',
    'source UnderlayType string enum values');
  check(interp.imports.get('funkin.data.ClientPrefs.UnderlayType')==underlay,
    'qualified UnderlayType import reuses owner facade');
  var first:Array<String>=underlay.toArray();var next:Array<String>=underlay.toArray();
  check(first!=next && first.join(',')=='Lane Underlay,Screen Dim','enum returns ordered fresh arrays');
  first[0]='changed';first.push('extra');
  check(underlay.toArray().join(',')=='Lane Underlay,Screen Dim','enum array mutation is isolated');

  check(NightmareVisionSourceRandom.float(2,4)==3,'source Random.float delegates to native RNG');
  var before=interp.ownerSave.data.flushCount;
  invoke(interp.variables,'newOption',['enabled','bool','null',{description:'Toggle',onChange:function(){}}]);
  invoke(interp.variables,'newOption',['count','int','null',null]);
  check(invoke(interp.variables,'getOption',['enabled'])==false,'bool default is persisted owner-locally');
  check(invoke(interp.variables,'getOption',['count'])==0,'int default is persisted owner-locally');
  check(interp.ownerSave.data.flushCount==before+2,'each new source option flushes its selected owner save');
  invoke(interp.variables,'newOption',['enabled','bool',true,null]);
  check(invoke(interp.variables,'getOption',['enabled'])==false,'source duplicate option does not replace saved value');
  var secondInterp=new Interp(owner);
  NightmareVisionSourceBindings.bindOwner(secondInterp,owner,'content/selected');
  check(invoke(secondInterp.variables,'getOption',['enabled'])==false,'separate same-owner scripts share persisted option state');
  var other=new Interp('assets/imported_mods/other');
  NightmareVisionSourceBindings.bindOwner(other,'assets/imported_mods/other','content/other');
  check(invoke(other.variables,'getOption',['enabled'])==null,'another owner cannot see selected owner options');

  var sourceVars:Map<String,Dynamic>=new Map();
  sourceVars.set('existing',10);
  var state=new LivePlayState(sourceVars);
  var fields:Map<String,Dynamic>=new Map();
  fields.set('bpm',120);fields.set('songName','first');fields.set('startedCountdown',false);
  var current={id:'live-state'};
  interp.variables.set('ScriptConstants',{getInstance:function():Dynamic return current});
  var loaded:Array<String>=[];
  NightmareVisionSourceBindings.bindGameplay(interp,state,true,fields,function(path:String):Dynamic {loaded.push(path);return 'ignored';});
  check(interp.variables.get('inGameOver')==false && interp.variables.get('inPlaystate')==true,'PlayState context flags');
  check(interp.variables.get('game')==state && interp.variables.get('bpm')==120 && interp.variables.get('songName')=='first','per-song source globals');
  check(interp.variables.get('global')==sourceVars,'global exposes only this PlayState variable map');
  check(state.variableReads==1,'global binding reads PlayState.variables through its getter');
  invoke(interp.variables,'setVar',['written',27]);
  check(invoke(interp.variables,'getVar',['written'])==27 && sourceVars.get('written')==27,'setVar/getVar operate on current PlayState variables');
  invoke(interp.variables,'initScript',['events/example']);
  check(loaded.join(',')=='events/example','initScript delegates to owner-scoped loader');
  check(invoke(interp.variables,'getInstance',[])==current,'getInstance delegates to ScriptConstants');
  var secondStateVars:Map<String,Dynamic>=new Map();
  var secondState=new LivePlayState(secondStateVars);
  var nextFields:Map<String,Dynamic>=new Map();nextFields.set('bpm',180);nextFields.set('songName','second');
  NightmareVisionSourceBindings.bindGameplay(interp,secondState,true,nextFields,function(_path:String):Dynamic return null);
  check(interp.variables.get('game')==secondState && interp.variables.get('global')==secondStateVars
    && interp.variables.get('bpm')==180 && interp.variables.get('songName')=='second','per-song bindings refresh without replacing owner bindings');
  NightmareVisionSourceBindings.bindGameplay(interp,{menu:true},false,null,null);
  check(interp.variables.get('inPlaystate')==false && interp.variables.get('game').menu==true,'non-PlayState source context flags');
 }
}
'''
        stubs = {
            "flixel/input/keyboard/FlxKey.hx": '''package flixel.input.keyboard;
enum abstract FlxKey(Int) from Int to Int {
 public static var fromStringMap(default,null):Map<String,FlxKey>=makeNames();
 public static var toStringMap(default,null):Map<FlxKey,String>=makeCodes();
 var A=65;var SPACE=32;
 static function makeNames():Map<String,FlxKey>{var m=new Map();m.set('A',A);m.set('SPACE',SPACE);return m;}
 static function makeCodes():Map<FlxKey,String>{var m=new Map();m.set(A,'A');m.set(SPACE,'SPACE');return m;}
}''',
            "flixel/FlxG.hx": '''package flixel;
class FlxG {public static var random:flixel.math.FlxRandom=new flixel.math.FlxRandom();}''',
            "flixel/math/FlxMath.hx": '''package flixel.math;
class FlxMath {public static inline var MAX_VALUE_INT:Int=2147483647;public static function bound(value:Float,min:Float,max:Float):Float return value<min?min:value>max?max:value;}''',
            "flixel/math/FlxRandom.hx": '''package flixel.math;
class FlxRandom {public var initialSeed:Int=0;public function new(){}public static function rangeBound(value:Int):Int return value;public function int(min:Int=0,max:Int=FlxMath.MAX_VALUE_INT,?excludes:Array<Int>):Int return min;public function float(min:Float=0,max:Float=1,?excludes:Array<Float>):Float return (min+max)/2;public function floatNormal(mean:Float=0,stdDev:Float=1):Float return mean;public function weightedPick(weights:Array<Float>):Int return 0;public function color(?min:flixel.util.FlxColor,?max:flixel.util.FlxColor,?alpha:Int,greyScale:Bool=false):flixel.util.FlxColor return new flixel.util.FlxColor();}''',
            "flixel/util/FlxColor.hx": '''package flixel.util;
class FlxColor {public function new(){}}''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for name, content in stubs.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"], cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
