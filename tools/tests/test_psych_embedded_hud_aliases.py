"""Actual persistent Iris HUD identity through the embedded Psych preset."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from source_icon_fixture_support import source_icon_fixture_files
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


class PsychEmbeddedHudAliasesTest(unittest.TestCase):
    def test_embedded_current_icon_identity_and_native_bindings(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        installer = (ROOT / 'source/PsychHscriptSourceBindings.hx').read_text(encoding='utf-8')
        runtime = (ROOT / 'source/PsychRuntimeBindings.hx').read_text(encoding='utf-8')
        methods = '\n'.join(method(play, name).replace('function ', 'public function ', 1) for name in [
            'function isSourceHUDIconAlias(', 'function sourceHUDIconAlias(',
            'function writeSourceHUDIconAlias(', 'function bindSourceHealthIconClass(', 'function bindSourceBarClass('])
        files = source_icon_fixture_files()
        from psych_standard_fixture_support import STANDARD_SERVICES
        files['PsychStandardServices.hx'] = STANDARD_SERVICES
        files['PsychHscriptSourceBindings.hx'] = r'''import hscript.Interp;import Main.Host;
class PsychHscriptSourceBindings {
 final host:Host;final interp:Interp;final origin:String;final callbackBridge:Dynamic=null;final parentLua:Dynamic=null;
 public function new(host:Host,interp:Interp,origin:String,bridge:Dynamic){this.host=host;this.interp=interp;this.origin=origin;}
 __INSTALL__
 static function sourceBuildTarget():String return 'fixture';
 static function setSharedVar(m:Map<String,Dynamic>,n:String,v:Dynamic):Dynamic {m.set(n,v);return v;}
 static function getSharedVar(m:Map<String,Dynamic>,n:String):Dynamic return m.get(n);
 static function removeSharedVar(m:Map<String,Dynamic>,n:String):Bool return m.remove(n);
 static function registerGlobal(b:Dynamic,o:String,n:String,f:Dynamic):Void{}
 static function registerLocal(b:Dynamic,o:String,n:String,f:Dynamic,t:Dynamic):Void{}
}'''.replace('__INSTALL__', method(installer, 'public function install():Void'))
        files['PsychAchievementsIntegration.hx'] = r'''import hscript.Interp;
class PsychAchievementsIntegration {
 public static var hscriptCalls:Array<Array<Dynamic>>=[];
 public static function installHscript(host:Dynamic,interp:Interp,origin:String):Void
  hscriptCalls.push([host,interp,origin]);
}'''
        files['PsychRuntimeBindings.hx'] = r'''import hscript.Interp;import Main.Host;
class PsychRuntimeBindings {
 final host:Host;final owner:Interp;final origin='embedded.lua';final ownerRoot='owner';var embedded:SourceIrisBridge;
 public function new(host:Host,owner:Interp){this.host=host;this.owner=owner;}
 __MODULE__
 __PRESET__
 function attachCallbackScope(i:Interp):Void{}
 public function current():SourceIrisBridge return module();
}'''.replace('__MODULE__', method(runtime, 'function module():SourceIrisBridge')).replace('__PRESET__', method(runtime, 'function installHscriptPreset('))
        files['PsychCamera.hx'] = 'class PsychCamera {}'
        files['PsychBaseStageActorGroupCompat.hx'] = 'class PsychBaseStageActorGroupCompat {}'
        files['PsychOwnerPaths.hx'] = 'class PsychOwnerPaths {public static function create(r:String,?l:String):Dynamic return {};}'
        files['DynamicSprite.hx'] = 'typedef DynamicAtlasFrames = flixel.graphics.frames.FlxAtlasFrames;'
        files['PsychHscriptErrorHandledRuntimeShader.hx'] = 'class PsychHscriptErrorHandledRuntimeShader {}'
        # No video objects are constructed by this HUD fixture; isolate the
        # native-only HXC video dependency pulled in by source normalization.
        files['HxcOwnedVideoSprite.hx'] = 'class HxcOwnedVideoSprite {public static function create(o:Dynamic,r:String,x:Float=0,y:Float=0):Dynamic return null;public static function pauseForState(s:Dynamic):Void{}public static function resumeForState(s:Dynamic):Void{}public static function destroyForState(s:Dynamic):Void{}}'
        files['PsychHscriptCamera.hx'] = 'class PsychHscriptCamera {}'
        files['PsychHscriptCustomSubstateFacade.hx'] = 'class PsychHscriptCustomSubstateFacade {public function new(v:Dynamic){}}'
        files['Main.hx'] = r'''import flixel.FlxSprite;import flixel.graphics.FlxGraphic;import hscript.Interp;
class Host {
 public var sourceHUDIconMode=1;public var psychSourceIconP1:PsychSourceHealthIcon;public var psychSourceIconP2:PsychSourceHealthIcon;
 public var nightmareVisionSourceIconP1:NightmareVisionHealthIcon;public var nightmareVisionSourceIconP2:NightmareVisionHealthIcon;
 public var playHUD:Dynamic;public var iconP1=new FlxSprite();public var iconP2=new FlxSprite();
 public var psychStageLibrary:String;public var compatCustomSubstate:Dynamic=null;public var psychScriptVariables:Map<String,Dynamic>=[];
 public var psychSourceCallbacks:Dynamic={bridge:function(r:String,s:hscript.Interp,o:String,p:hscript.Interp):Dynamic {return null;}};
 public var installedPaths:Dynamic;public var attachmentCalls=0;public var alphabetCalls=0;public var members:Array<FlxSprite>;
 public function new(){psychSourceIconP1=new PsychSourceHealthIcon('bf',false,true,sourceHealthIconOwner(false));psychSourceIconP2=new PsychSourceHealthIcon('dad',false,true,sourceHealthIconOwner(false));members=[psychSourceIconP1,psychSourceIconP2];}
 public function compatPsychOwnerForScript(o:String):String return 'owner';
 function sourceNoteTimingMode():Int return 1;
 function sourceHealthIconOwner(n:Bool,?p:Dynamic):SourceHealthIconOwner return {image:(key,gpu)->new FlxGraphic(300,150),exists:p->true,uiPrefix:()->'',antialiasing:()->true};
 function sourceBarOwner(n:Bool,?p:Dynamic):SourceBarOwner {installedPaths=p;return {image:key->new FlxGraphic(601,19),antialiasing:()->true};}
 function bindSourceHUDBarAliases(i:NightmareVisionScriptInterp):Void{}
 function bindSourceHealthValues(i:NightmareVisionScriptInterp):Void{}
 function bindSourceAttachmentClasses(i:NightmareVisionScriptInterp,n:Bool,p:Dynamic):Void attachmentCalls++;
 public function bindSourceAlphabetClasses(i:NightmareVisionScriptInterp,p:Dynamic):Void alphabetCalls++;
 __METHODS__
}
class Main {
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function main(){
  var host=new Host();var lua=new Interp();var paths:Dynamic={__sourceOwnerRoot:()->'owner'};
  lua.variables.set('Paths',paths);lua.variables.set('iconP2',host.iconP2);
  var runtime=new PsychRuntimeBindings(host,lua);var embedded=runtime.current();
  check(PsychAchievementsIntegration.hscriptCalls.length==1
   && PsychAchievementsIntegration.hscriptCalls[0][0]==host
   && PsychAchievementsIntegration.hscriptCalls[0][1]==embedded
   && PsychAchievementsIntegration.hscriptCalls[0][2]=='embedded.lua',
   'embedded preset passes its captured host, interpreter, and script origin');
  check(runtime.current()==embedded,'persistent module identity');
  check(host.installedPaths==paths,'captured Paths identity retained');
  check(host.attachmentCalls==1&&host.alphabetCalls==1,'accepted preset installers called once');
  embedded.evaluate("observed=game.iconP2;bare=iconP2;game.iconP2.changeIcon('icon-greenWiz');",'first');
  check(embedded.variables.get('observed')==host.psychSourceIconP2&&embedded.variables.get('bare')==host.psychSourceIconP2,'actual game/bare icon source identity');
  check(host.psychSourceIconP2.getCharacter()=='icon-greenWiz','displayed source icon changed');
  check(host.members[1]==host.psychSourceIconP2&&embedded.variables.get('observed')!=host.iconP2,'legacy icon remains detached');
  var replacement=new PsychSourceHealthIcon('replacement',false,true,host.sourceHealthIconOwner(false));
  host.psychSourceIconP2=replacement;
  embedded.evaluate("again=game.iconP2;againBare=iconP2;game.iconP2.changeIcon('icon-yelWiz');",'second');
  check(embedded.variables.get('again')==replacement&&embedded.variables.get('againBare')==replacement,'live source replacement');
  check(replacement.getCharacter()=='icon-yelWiz','replacement callback targets current source icon');
  check(host.attachmentCalls==1&&host.alphabetCalls==1,'evaluate does not reinstall or change ownership');
  host.psychSourceIconP2=null;embedded.evaluate('empty=game.iconP2;','null');check(embedded.variables.get('empty')==null,'authored null never falls back legacy');
  embedded.evaluator.release();check(replacement.animation!=null,'interpreter release does not destroy borrowed HUD sprite');
 }
}'''.replace('__METHODS__', methods).replace('function sourceHealthIconOwner(', 'public function sourceHealthIconOwner(')
        # Native state registration is tested by the connected state-registry probe.
        files['PsychStateClassBindings.hx'] = 'class PsychStateClassBindings {public static function installScope(s:Dynamic):Void {} public static function install(i:Dynamic):Void {}}'
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            temp = Path(directory)
            for name, content in files.items():
                path = temp / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
            env = os.environ.copy()
            env['HAXELIB_PATH'] = str(ROOT / '.haxelib')
            env['NEKOPATH'] = str(ROOT / '.tools/neko')
            env['PATH'] = str(ROOT / '.tools/haxe') + os.pathsep + env['NEKOPATH'] + os.pathsep + env.get('PATH', '')
            command = [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                       '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(temp), '-main', 'Main']
            result = subprocess.run([*command, '--interp'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-4000:])
            cpp = subprocess.run([*command, '-cpp', str(temp / 'cpp'), '-D', 'no-compilation'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=45)
            self.assertEqual(cpp.returncode, 0, (cpp.stdout + cpp.stderr)[-4000:])
            generated = (temp / 'cpp/src/Host.cpp').read_text(encoding='utf-8')
            self.assertIn('bindLiveValue', generated)
            self.assertIn('psychSourceIconP2', generated)
            preset = (temp / 'cpp/src/PsychHscriptSourceBindings.cpp').read_text(encoding='utf-8')
            self.assertIn('bindSourceBarClass', preset)


if __name__ == '__main__':
    unittest.main()
