"""Source-selected custom effects use one renderer while donor builtins remain shared."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]


class NVCustomEventOwnershipTest(unittest.TestCase):
    def run_fixture(self, source):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(source, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'),
                '-cp', str(work), '-main', 'Main', '--interp'], cwd=ROOT,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-5000:])

    def test_exact_donor_builtin_policy_and_psych_wrapper(self):
        donor = ROOT.parent / 'fnf_sources/NightmareVision/source/funkin/states/PlayState.hx'
        source = donor.read_text(encoding='utf-8')
        body = source[source.index('public function triggerEventNote('):source.index('\n\tfunction moveCameraSection(', source.index('public function triggerEventNote('))]
        names = re.findall(r"^\t\t\tcase '([^']+)'", body, re.M)
        self.assertEqual(len(names), 16)
        import json
        self.run_fixture('''class Main {
 static function ok(v:Bool,s:String) {if(!v)throw s;}
 static function main() {
  var builtins:Array<String> = ''' + json.dumps(names) + ''';
  for (name in builtins) {
   ok(!EngineCompat.sourceCustomEventOwnsNativeFallback(ImportEngine.NIGHTMARE_VISION,name,true),"donor builtin "+name);
   ok(EngineCompat.sourceCustomEventOwnsNativeFallback(ImportEngine.NIGHTMARE_VISION," "+name,true),"source does not trim "+name);
  }
  ok(EngineCompat.sourceCustomEventOwnsNativeFallback(ImportEngine.NIGHTMARE_VISION,"Lyrics",true),"NV custom owns host-only Lyrics");
  ok(!EngineCompat.sourceCustomEventOwnsNativeFallback(ImportEngine.NIGHTMARE_VISION,"Lyrics",false),"missing callable retains fallback");
  ok(!EngineCompat.sourceCustomEventOwnsNativeFallback(ImportEngine.AUTO,"Lyrics",true),"native chart remains native");
  ok(!EngineCompat.psychCustomEventOwnsNativeFallback(" Add Camera Zoom ",true),"Psych trim preserved");
  ok(EngineCompat.psychCustomEventOwnsNativeFallback("Camera Zoom",true),"Psych donor does not acquire NV builtin");
  ok(!EngineCompat.sourceCustomEventOwnsNativeFallback(ImportEngine.NIGHTMARE_VISION,"Camera Zoom",true),"NV donor builtin retained");
  ok(EngineCompat.psychCustomEventOwnsNativeFallback("Lyrics",true),"existing Psych wrapper preserved");
 }
}''')

    def test_actual_selected_live_callback_and_single_effect_execution(self):
        self.run_fixture(r'''import NightmareVisionScriptDiscovery.NightmareVisionScriptEntry;
class Main {
 static function ok(v:Bool,s:String) {if(!v)throw s;}
 static function main() {
  var calls:Array<String>=[];
  var errors:Array<String>=[];
  var source='function onLoad(){record("load");} function onEvent(n,a,b){record("observed");} function onTrigger(a,b){record("authored:"+a);}';
  var entries:Array<NightmareVisionScriptEntry>=[{scope:'event',name:'Lyrics',path:'owner/data/events/Lyrics.hx',relative:'data/events/Lyrics.hx'}];
  var host=new NightmareVisionGameplayScripts({}, {root:'owner',baseAssetsRoot:'',song:'synthetic',stage:'stage',scripts:entries,coverageNotes:[]},
   function(path)return source, function(i,e,a)i.variables.set('record',function(s:String)calls.push(s)),
   function(n,p,e)errors.push(n+':'+p));
  ok(!host.hasEventCallback('lyrics','onTrigger')&&calls.length==0,"exact selected name, no lowercase file match");
  ok(host.hasEventCallback('Lyrics','onTrigger')&&calls.join(',')=='load',"first direct trigger lazy prepares once");
  ok(host.hasEventCallback('Lyrics','onTrigger')&&calls.length==1,"query does not repeat load");
  var nativeEffects=0;
  if(!EngineCompat.sourceCustomEventOwnsNativeFallback(ImportEngine.NIGHTMARE_VISION,'Lyrics',host.hasEventCallback('Lyrics','onTrigger')))nativeEffects++;
  host.call('onEvent',['Lyrics','text','']);host.callEvent('Lyrics','onTrigger',['text','']);
  ok(nativeEffects==0&&calls.join(',')=='load,observed,authored:text',"one authored effect, observer retained");
  var script=host.eventGroup.getScript('Lyrics');
  script.interp.variables.remove('onTrigger');
  ok(!host.hasEventCallback('Lyrics','onTrigger'),"removed callback stops owning");
  script.set('onTrigger',7);
  ok(!host.hasEventCallback('Lyrics','onTrigger'),"mere nonfunction value cannot own");
  script.set('onTrigger',function(a:String,b:String)calls.push('replacement'));
  ok(host.hasEventCallback('Lyrics','onTrigger'),"live replacement callable owns");
  host.callEvent('Lyrics','onTrigger',['','']);ok(calls[calls.length-1]=='replacement',"dispatch uses live replacement");
  var old=host.eventGroup;
  host.eventGroup=new NightmareVisionScriptGroup();
  ok(!host.hasEventCallback('Lyrics','onTrigger'),"replaced live registry does not use cached old module");
  var replacement=NightmareVisionScriptModule.fromSource('Lyrics','function onTrigger(a,b){record("new-group");}',{},null,
   function(i)i.variables.set('record',function(s:String)calls.push(s)),function(n,p,e)errors.push(n+':'+p));
  host.eventGroup.addScript(replacement);
  ok(host.hasEventCallback('Lyrics','onTrigger'),"current registry replacement owns");
  host.callEvent('Lyrics','onTrigger',['','']);ok(calls[calls.length-1]=='new-group',"current group dispatch");
  var aliasModule=NightmareVisionScriptModule.fromSource('DynamicAlias','function onTrigger(a,b){}',{},null,function(i){},function(n,p,e){});
  host.eventGroup.addScript(aliasModule);
  ok(!host.hasEventCallback('DynamicAlias','onTrigger'),"unselected dynamic alias matches existing source adapter limitation");
  replacement.destroy();ok(!host.hasEventCallback('Lyrics','onTrigger'),"released selected module cannot own");
  ok(errors.length==0,"no swallowed errors");
  old.destroy();host.destroy();aliasModule.destroy();
 }
}''')

    def test_actual_playstate_orchestration_and_native_render_boundary(self):
        from test_nv_multifield_routes import method
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        wrapper = method(play, 'function fireSongEvent(e:Dynamic)')
        selector = method(play, 'function sourceCustomEventOwnsNativeFallback(')
        psych = method(play, 'function psychCustomEventHasCallback(')
        native = method(play, 'function fireNativeSongEvent(')
        guard = method(native, 'if (sourceCustomEventOwnsNativeFallback(e.name))')
        self.assertLess(native.index("callAllHScript('onEvent'"), native.index('sourceCustomEventOwnsNativeFallback(e.name)'))
        self.assertLess(native.index('sourceCustomEventOwnsNativeFallback(e.name)'), native.index('EngineCompat.routeLegacyEvent('))
        self.assertLess(wrapper.index('fireNativeSongEvent(e)'), wrapper.index("callNightmareVision('onEvent'"))
        self.run_fixture('''class CodenameEventDispatch {public static function fromNative(e:Dynamic):Dynamic return null;}
class Main {
 var nightmareVisionScripts:NightmareVisionGameplayScripts;
 var psychCustomEventScopes:Map<String,String>=[];
 var hscriptStates:Map<String,NightmareVisionScriptInterp>=[];
 var nativeEffects=0;var compiledStage=0;var observations=0;var authored=0;var psychObservations=0;var errors:Array<String>=[];
 public function new(){}
 function codenameSelectedRoot():String return '';
 function executeCodenameEvent(e:Dynamic):Void throw 'Unexpected Codename branch';
 function callNightmareVision(name:String,args:Array<Dynamic>):Dynamic return nightmareVisionScripts==null?0:nightmareVisionScripts.call(name,args);
 function dispatchPsychCompiledStageEvent(e:Dynamic):Void compiledStage++;
 // Rendering and unrelated HXC/legacy phases are an explicit boundary. The
 // guard/return and entire outer dispatch below are exact production bodies.
 function fireNativeSongEvent(e:Dynamic):Void {
  var psychStageEvent=e;psychObservations++;
 ''' + guard + '''
  nativeEffects++;
  dispatchPsychCompiledStageEvent(psychStageEvent);
 }
 ''' + selector + psych + wrapper + '''
 static function ok(v:Bool,s:String){if(!v)throw s;}
 static function main(){
  var game=new Main();
  var entries:Array<NightmareVisionScriptDiscovery.NightmareVisionScriptEntry>=[
   {scope:'event',name:'Lyrics',path:'lyrics',relative:'lyrics'},
   {scope:'event',name:'Add Camera Zoom',path:'zoom',relative:'zoom'}];
  game.nightmareVisionScripts=new NightmareVisionGameplayScripts(game,
   {root:'owner',baseAssetsRoot:'',song:'synthetic',stage:'stage',scripts:entries,coverageNotes:[]},
   function(p)return 'function onEvent(n,a,b){observe();} function onTrigger(a,b){effect();}',
   function(i,e,a){i.variables.set('observe',function(){game.observations++;});i.variables.set('effect',function(){game.authored++;});},
   function(n,p,e)game.errors.push(Std.string(e)));
  game.fireSongEvent({name:'Lyrics',v1:'one',v2:'',time:0});
  ok(game.nativeEffects==0&&game.observations==1&&game.authored==1&&game.compiledStage==1,"real wrapper custom effect once + observer/compiled dispatch");
  game.fireSongEvent({name:'Add Camera Zoom',v1:'',v2:'',time:1});
  ok(game.nativeEffects==1&&game.authored==2&&game.compiledStage==2,"donor builtin retains native effect plus authored callback");
  var script=game.nightmareVisionScripts.eventGroup.getScript('Lyrics');script.interp.variables.remove('onTrigger');
  game.fireSongEvent({name:'Lyrics',v1:'missing',v2:'',time:2});
  ok(game.nativeEffects==2&&game.authored==2,"removed handler fallback");
  script.set('onTrigger',null);
  game.fireSongEvent({name:'Lyrics',v1:'null',v2:'',time:3});
  ok(game.nativeEffects==3&&game.authored==2,"noncallable null field fallback");
  ok(game.errors.length==1&&game.errors[0].indexOf("Callback is not a function: onTrigger")>=0,"existing callback diagnostic retained");
  game.nightmareVisionScripts.destroy();game.nightmareVisionScripts=null;
  var i=new NightmareVisionScriptInterp();i.variables.set('onEvent',function(){});
  game.psychCustomEventScopes.set('custom','lyrics');game.hscriptStates.set('custom',i);
  game.fireSongEvent({name:'Lyrics',v1:'psych',v2:'',time:4});
  ok(game.nativeEffects==3,"existing Psych custom ownership retained");
  game.fireSongEvent({name:'Add Camera Zoom',v1:'',v2:'',time:5});
  ok(game.nativeEffects==4,"existing Psych builtin remains native");
  game.hscriptStates.clear();game.fireSongEvent({name:'Lyrics',v1:'native',v2:'',time:6});
  ok(game.nativeEffects==5,"native chart fallback retained");
  ok(game.psychObservations==7&&game.compiledStage==7,"ownership cannot suppress prior observation or compiled stage callback");
  i.release();
 }
}''')


if __name__ == '__main__':
    unittest.main()
