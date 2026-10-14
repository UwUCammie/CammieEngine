"""Execute modern Psych property bindings against displaced live HUD aliases."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, ROOT
from test_psych_property_paths import extract_method

class PsychHUDPropertyIdentityTest(unittest.TestCase):
    def test_reads_writes_and_relative_restore_use_actual_source_hud(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        aliases = "\n".join(extract_method(play, marker).replace("function ", "public function ", 1) for marker in (
            "function isSourceHUDBarAlias(", "function sourceHUDBarAlias(", "function writeSourceHUDBarAlias(",
            "function isSourceHUDIconAlias(", "function sourceHUDIconAlias(", "function writeSourceHUDIconAlias("))
        files = {
            "SourceNativeClassScope.hx": "class SourceNativeClassScope {public function new(){} public function hasRuntimeClass(n:String)return n=='PlayState'; public function resolveClass(n:String):Dynamic return PlayState; public function read(o:Dynamic,k:String):Dynamic return Reflect.getProperty(o,k); public function write(o:Dynamic,k:String,v:Dynamic):Void Reflect.setProperty(o,k,v); public function createInstance(t:Dynamic,a:Array<Dynamic>):Dynamic return {};}",
            "MusicBeatState.hx": "class MusicBeatState {public static var variables:Map<String,Dynamic>=[]; public static function getVariables():Dynamic return variables;public static function getState():Dynamic return PlayState.instance;public function new(){}}",
            "PsychCustomSubstate.hx": "class PsychCustomSubstate {public static var instance:Dynamic;}",
            "GameOverSubstate.hx": "class GameOverSubstate {public static var instance:Dynamic;}",
            "PsychSceneAnchors.hx": "class PsychSceneAnchors {public static function lowestCharacter(s:Dynamic):Int return 0;}",
            "PsychSourceBar.hx": "class PsychSourceBar {}",
            "NightmareVisionBar.hx": "class NightmareVisionBar {}",
        }
        files["PlayState.hx"] = r'''class PlayState extends MusicBeatState {
 public static var instance:PlayState; public var isDead=false; public var watchedCutscene=false;
 public var sourceHUDBarMode=1; public var sourceHUDIconMode=1; public var playHUD:Dynamic;
 public var healthBar:Dynamic={y:652.}; public var healthBarBG:Dynamic={y:648.}; public var iconP1:Dynamic={y:565.8};public var iconP2:Dynamic={y:565.8};
 public var psychSourceHealthBar:Dynamic={y:640.8,bg:{y:640.8},leftBar:{y:640.8}};
 public var psychSourceTimeBar:Dynamic={y:25.,bg:{y:25.}}; public var nightmareVisionSourceHealthBar:Dynamic; public var nightmareVisionSourceTimeBar:Dynamic;
 public var psychSourceIconP1:Dynamic={y:565.8}; public var psychSourceIconP2:Dynamic={y:565.8}; public var nightmareVisionSourceIconP1:Dynamic;public var nightmareVisionSourceIconP2:Dynamic;
 public var ordinary:Dynamic={y:9.};
 public function new(){super();instance=this;}public function sourceNoteTimingMode():Int return 1;
 public function compatReadPathPart(o:Dynamic,k:String):Dynamic return isSourceHUDBarAlias(k)?sourceHUDBarAlias(k):sourceHUDIconAlias(k);
 public function compatWritePathPart(o:Dynamic,k:String,v:Dynamic):Bool {if(isSourceHUDBarAlias(k))writeSourceHUDBarAlias(k,v);else writeSourceHUDIconAlias(k,v);return true;}
 public function compatResolveClass(n:String):Dynamic return n=='PlayState'?PlayState:null;
 public function compatSourceClientPrefs(n:Dynamic):Dynamic return null;
 public function compatSourcePreferencePath(prefs:Dynamic,path:Dynamic):String return Std.string(path);
 __ALIASES__
}'''.replace("__ALIASES__", aliases)
        files["Main.hx"] = r'''class Main {
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function main(){var host=new PlayState();var interp=new hscript.Interp();var classes=new SourceNativeClassScope();PsychPropertyBindings.install(host,interp,classes,function(v)return v);
 var get:Dynamic=interp.variables.get('getProperty');var set:Dynamic=interp.variables.get('setProperty');var getClass:Dynamic=interp.variables.get('getPropertyFromClass');var setClass:Dynamic=interp.variables.get('setPropertyFromClass');
 check(get('healthBar')==host.psychSourceHealthBar,'bare live bar identity');check(get('game.healthBar')==host.psychSourceHealthBar,'game live bar identity');check(get('healthBarBG')==host.psychSourceHealthBar.bg,'background child identity');check(get('iconP1')==host.psychSourceIconP1,'icon identity');
 var baseline:Float=get('healthBar.y');host.psychSourceHealthBar.y=get('healthBar.y')+160;check(get('healthBar.y')==baseline+160,'out tween position must be current');host.psychSourceHealthBar.y=get('healthBar.y')-160;check(get('healthBar.y')==baseline&&host.healthBar.y==652,'relative return restores original live source position');
 host.psychSourceIconP1.y=get('iconP1.y')+160;host.psychSourceIconP1.y=get('iconP1.y')-160;check(get('iconP1.y')==565.8,'relative icon restore');
 set('healthBar.y',712.);check(host.psychSourceHealthBar.y==712&&host.healthBar.y==652,'writes target source bar');set('iconP2.y',81.);check(host.psychSourceIconP2.y==81&&host.iconP2.y==565.8,'writes target source icon');
 check(getClass('PlayState','instance.healthBar')==host.psychSourceHealthBar&&getClass('PlayState','healthBar')==host.psychSourceHealthBar,'class paths use source aliases');setClass('PlayState','instance.healthBar.y',711.);check(host.psychSourceHealthBar.y==711,'class nested write');
 check(PsychObjectProviders.direct('healthBar')==host.psychSourceHealthBar&&PsychObjectProviders.text('healthBar.bg')==host.psychSourceHealthBar.bg,'text/object providers share alias boundary');
 var replacement:Dynamic={y:333.,bg:{y:333.}};set('healthBar',replacement);check(get('healthBar')==replacement&&host.healthBar.y==652,'pointer replacement');set('iconP1',null);check(get('iconP1')==null,'source null never falls back to native icon');
 check(get('ordinary.y')==9,'ordinary fields preserve native class boundary');set('ordinary.y',10.);check(host.ordinary.y==10,'ordinary writes preserve native class boundary');
 host.sourceHUDBarMode=host.sourceHUDIconMode=0;check(get('healthBar')==host.healthBar&&get('iconP1')==host.iconP1,'native profile retains typed HUD');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            for name, source in files.items():
                (Path(folder) / name).write_text(source, encoding="utf-8")
            result=subprocess.run([*HAXE_COMMAND,"-cp",str(ROOT/"source"),"-cp",str(ROOT/".haxelib/hscript/2,5,0"),"-cp",folder,"-main","Main","--interp"],cwd=ROOT,capture_output=True,text=True,timeout=40)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
