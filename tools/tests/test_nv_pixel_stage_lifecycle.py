"""Historical pixel-stage properties through production lifecycle methods and Iris."""
from pathlib import Path
import json, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from nv_field_fixture_support import write_nv_field_dependencies
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
class PixelStageLifecycleTest(unittest.TestCase):
 def test_stage_setup_script_writes_reflection_and_exit(self):
  play=(ROOT/'source/PlayState.hx').read_text()
  start=play.index('\tprivate var pixelUI:Bool = false;')
  end=play.index('\n\tfunction restoreNightmareVisionPixelStage',start)
  methods=play[start:end]+'\n'+method(play,'function restoreNightmareVisionPixelStage(')+'\n'+method(play,'function bindNightmareVisionPixelStage(')+'\n'+method(play,'public override function startOutro(')
  fixture=r"""
class FixtureBase {public function new(){}public function startOutro(done:Void->Void):Void done();}
class PlayState extends FixtureBase {
 public var nightmareVisionLegacyFieldCameras=true;
 public var nightmareVisionStartupRedirect=false;
 public var curStage:Dynamic={stageData:{isPixelStage:true}};
 public function new(){super();}
 __METHODS__
}
""".replace('__METHODS__',methods)
  main=r"""@:access(PlayState)
class Main {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function interpreter(state:PlayState):NightmareVisionScriptInterp {
  var i=new NightmareVisionScriptInterp(state);i.bindClassParent(PlayState);state.bindNightmareVisionPixelStage(i);
  i.variables.set('PlayState',PlayState);i.variables.set('game',state);i.variables.set('Reflect',i.sourceClassScope().reflectFacade());
  i.bindImport('meta.states.PlayState',PlayState);return i;
 }
 static function main(){
  var a=new PlayState(),b=new PlayState();b.curStage.stageData.isPixelStage=false;
  a.curStage.stageData=NightmareVisionStageData.getLegacyStageFile(__OWNER__,'pixel');
  check(a.curStage.stageData!=null&&a.curStage.stageData.isPixelStage==true,'authored stage file supplies mode');
  for(name in ['PlayState','states.PlayState','meta.states.PlayState','funkin.states.PlayState'])
   check(EngineCompat.legacyClassProperty(name,'isPixelStage')=='isPixelStage','shared class-property alias '+name);
  a.restoreNightmareVisionPixelStage();b.restoreNightmareVisionPixelStage();
  check(a.isPixelStage&&!b.isPixelStage,'authored stage selection precedes scripts and is scene-local');
  var i=interpreter(a),j=interpreter(b),parser=new NightmareVisionScriptParser();
  i.execute(parser.parseString("before=isPixelStage;isPixelStage=false;after=game.isPixelStage;PlayState.isPixelStage=true;reflected=Reflect.field(PlayState,'isPixelStage');Reflect.setProperty(game,'isPixelStage',false);last=isPixelStage;"));
  check(i.variables.get('before')==true&&i.variables.get('after')==false&&i.variables.get('reflected')==true&&i.variables.get('last')==false,'all source property forms share live value');
  j.execute(parser.parseString("other=PlayState.isPixelStage;Reflect.setField(PlayState,'isPixelStage',true);"));
  check(j.variables.get('other')==false&&b.isPixelStage&&!a.isPixelStage,'class identity routes remain interpreter-local');
  i.execute(parser.parseString("import meta.states.PlayState; PlayState.isPixelStage=false;"));
  var completed=false;a.startOutro(function(){completed=true;check(a.isPixelStage,'restore before state-exit callback');});
  check(completed,'normal outro callback');
  b.nightmareVisionStartupRedirect=true;b.startOutro(function(){check(!b.isPixelStage,'startup redirects restore before callback');});
  a.curStage.stageData.isPixelStage=false;a.isPixelStage=true;a.restoreNightmareVisionPixelStage();
  check(!a.isPixelStage,'restore reads live stage data');
  a.curStage=null;a.isPixelStage=true;a.restoreNightmareVisionPixelStage();check(a.isPixelStage,'incomplete startup has no authored value');
  a.curStage={stageData:{isPixelStage:false}};a.nightmareVisionLegacyFieldCameras=false;
  a.restoreNightmareVisionPixelStage();check(a.isPixelStage,'modern profile retains existing UI-pack mode');
  a.startOutro(function(){check(a.isPixelStage,'modern outro remains unchanged');});
  i.release();j.release();
 }
}
"""
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
   work=FixturePath(directory);write_nv_field_dependencies(work);write_flixel_point_stub(work)
   authored=ROOT.parent/'fnf_example_mods/nightmare vision/dsides_r_11_final/content/old-dsides/data/stages/school/data.json'
   if not authored.is_file():self.skipTest('authored pixel stage fixture unavailable')
   owner=work/'owner';(owner/'stages').mkdir(parents=True)
   (owner/'stages/pixel.json').write_bytes(authored.read_bytes())
   (work/'CoolUtil.hx').write_text('class CoolUtil {public static function parseJson(s:String):Dynamic return haxe.Json.parse(s);}')
   (work/'PlayState.hx').write_text(fixture);(work/'Main.hx').write_text(main.replace('__OWNER__',json.dumps(str(owner).replace(chr(92),'/'))))
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=45)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  setup=method(play,'function initializeNightmareVisionScripts(')
  self.assertLess(setup.index('restoreNightmareVisionPixelStage();'),setup.index('NightmareVisionStageScene.load('))
  seed=method(play,'function seedNightmareVision(')
  self.assertIn('bindNightmareVisionPixelStage(interp);',seed)
  setter=method(play,'function compatSetPropertyFromClass(')
  self.assertIn("== 'isPixelStage'",setter)
if __name__=='__main__':unittest.main()
