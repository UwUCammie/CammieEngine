"""Shared native state registry and pinned source active-state access."""
from pathlib import Path
import re,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
class PsychStateRegistryTest(unittest.TestCase):
 def test_native_registry_contract(self):
  donor=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/FNF-PsychEngine'),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:source/backend/MusicBeatState.hx'],text=True)
  actual=(ROOT/'source/MusicBeatState.hx').read_text();play=(ROOT/'source/PlayState.hx').read_text()
  source_get=re.search(r'public static function getVariables\(\)\s+return [^;]+;',donor).group(0)
  source_state='public static '+extract_method(donor,'function getState(')
  native='\n'.join('public static '+extract_method(actual,'function '+name+'(') for name in ['getState','getVariables'])
  alias='public var psychScriptVariables(get,set):Map<String,Dynamic>;\n'+'\n'.join(extract_method(play,'function '+name+'(') for name in ['get_psychScriptVariables','set_psychScriptVariables'])
  fixture=r'''class FlxG {public static var state:Dynamic;}
class DonorFlxG {public static var state:Dynamic;}
class MusicBeatState {public var variables:Map<String,Dynamic>=[];public function new(){} __NATIVE__}
class DonorMusicBeatState {public var variables:Map<String,Dynamic>=[];public function new(){} __SOURCE__}
class PsychCustomSubstate {}
class PsychMusicBeatSubstate {}
class PlayState extends MusicBeatState {public var nightmareVisionLegacyFieldCameras:Bool=false;public function new(){super();}__ALIAS__}
class NightmareVisionScriptInterp {
 public var variables:Map<String,Dynamic>=[];public var imports:Map<String,Dynamic>=[];var scope=new SourceNativeClassScope();
 public var constructorType:Dynamic;public function bindConstructorFactory(t:Dynamic,c:Dynamic,o:Dynamic):Void constructorType=t;
 public function new(){}public function sourceClassScope():SourceNativeClassScope return scope;public function bindImport(n:String,t:Dynamic):Void imports.set(n,t);
}
class Main {
 static function check(ok:Bool,message:String):Void {if(!ok)throw message;}
 static function read(actual:Bool):String {try {var m=actual?MusicBeatState.getVariables():DonorMusicBeatState.getVariables();return Std.string(m.get('value'));}catch(e:Dynamic){return 'error';}}
 static function main(){
  var a=new PlayState(),b=new MusicBeatState();var x=new DonorMusicBeatState(),y=new DonorMusicBeatState();
  a.variables.set('value',1);b.variables.set('value',2);x.variables.set('value',1);y.variables.set('value',2);
  for(i in 0...80){var kind=i%4;FlxG.state=kind==0?a:kind==1?b:kind==2?null:{};DonorFlxG.state=kind==0?x:kind==1?y:kind==2?null:{};check(read(true)==read(false),'source active-state/invalid-state contract '+i);}
  var old=a.variables;var replacement:Map<String,Dynamic>=['value'=>3];a.psychScriptVariables=replacement;
  check(a.variables==replacement&&a.psychScriptVariables==replacement&&old!=replacement,'host alias writes native map');
  a.variables=old;check(a.psychScriptVariables==old&&b.variables!=old,'native map writes host alias; isolated state storage');
  FlxG.state=a;check(MusicBeatState.getState()==a&&MusicBeatState.getVariables()==old,'current native identity');
  var cached=MusicBeatState.getVariables;FlxG.state=b;check(cached()==b.variables,'cached method follows active state');
  var first=new NightmareVisionScriptInterp(),second=new NightmareVisionScriptInterp();PsychStateClassBindings.install(first);PsychStateClassBindings.install(second);
  check(first.imports.get('backend.MusicBeatState')==MusicBeatState&&first.sourceClassScope().resolveClass('states.PlayState')==PlayState,'native source class identities');
  check(first.imports.get('backend.MusicBeatSubstate')==PsychMusicBeatSubstate&&first.sourceClassScope().resolveClass('backend.MusicBeatSubstate')==PsychMusicBeatSubstate,'source substate class identity');
  check(first.constructorType==PsychMusicBeatSubstate,'source constructor identity overrides the native short-name collision');
  first.variables.set('MusicBeatState',null);check(second.variables.get('MusicBeatState')==MusicBeatState,'interpreter-local import ownership');
  trace('state-registry-contract:80');
 }
}
'''.replace('__NATIVE__',native).replace('__SOURCE__',(source_get+'\n'+source_state).replace('MusicBeatState','DonorMusicBeatState').replace('FlxG','DonorFlxG')).replace('__ALIAS__',alias)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder)
   for name in ['FlxG','DonorFlxG','MusicBeatState','DonorMusicBeatState','PlayState','PsychCustomSubstate','PsychMusicBeatSubstate','NightmareVisionScriptInterp','Main']:(work/(name+'.hx')).write_text(extract_method(fixture,'class '+name+' '))
   for name in ['SourceNativeClassScope','PsychStateClassBindings']:(work/(name+'.hx')).write_text((ROOT/'source'/(name+'.hx')).read_text())
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('state-registry-contract:80',result.stdout)
