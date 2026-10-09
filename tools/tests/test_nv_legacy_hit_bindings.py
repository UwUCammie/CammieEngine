from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from nv_field_fixture_support import write_nv_field_dependencies
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
class HitBindingsTest(unittest.TestCase):
 def test_real_interpreter_routes_and_owner_isolation(self):
  play=(ROOT/'source/PlayState.hx').read_text()
  wrappers='\n'.join(method(play,n) for n in ['function nightmareVisionLegacyGoodNoteHit(','function nightmareVisionLegacyOpponentNoteHit(','function nightmareVisionLegacyNoteMiss(','function nightmareVisionLegacyNoteMissPress('])
  fixture='class PlayState {public static var instance:PlayState;public var log:Array<Dynamic>=[];public var explode=false;public function new(){}public function goodNoteHit(n:Note,p:Bool):Void throw "host Boolean signature entered";'+wrappers+'}'
  main=r'''@:access(PlayState)
class Main {
 static function check(b:Bool,m:String){if(!b)throw m;}
 static function scope(s:PlayState):NightmareVisionScriptInterp {
  var i=new NightmareVisionScriptInterp(s);i.bindClassParent(PlayState);
  i.variables.set('game',s);i.variables.set('PlayState',PlayState);i.bindImport('meta.states.PlayState',PlayState);
  i.variables.set('Reflect',i.sourceClassScope().reflectFacade());
  NightmareVisionLegacyHitBindings.install(i,s,PlayState,s.nightmareVisionLegacyGoodNoteHit,s.nightmareVisionLegacyOpponentNoteHit,s.nightmareVisionLegacyNoteMiss,s.nightmareVisionLegacyNoteMissPress);
  return i;
 }
 static function run(i:NightmareVisionScriptInterp,t:String):Dynamic return i.execute(new NightmareVisionScriptParser().parseString(t,'hit-api'));
 static function main(){
  var a=new PlayState(),b=new PlayState();PlayState.instance=a;var i=scope(a),j=scope(b);
  var note=new Note(),field=new NightmareVisionPlayFieldView();
  for(s in [i,j]){s.variables.set('note',note);s.variables.set('field',field);}
  var forms=['goodNoteHit(note,field);','game.goodNoteHit(note,field);','PlayState.goodNoteHit(note,field);','PlayState.instance.goodNoteHit(note,field);',
   'import meta.states.PlayState; PlayState.instance.goodNoteHit(note,field);',
   'Reflect.callMethod(game,Reflect.field(game,"goodNoteHit"),[note,field]);',
   'Reflect.callMethod(game,Reflect.getProperty(game,"goodNoteHit"),[note,field]);',
   'Reflect.callMethod(PlayState,Reflect.field(PlayState,"goodNoteHit"),[note,field]);',
   'var saved=game.goodNoteHit; saved(note,field);'];
  for(family in ['goodNoteHit','opponentNoteHit'])for(form in forms){
   run(i,StringTools.replace(form,'goodNoteHit',family));var e=a.log[a.log.length-1];
   check(e.note==note&&e.field==field&&e.player==(family=='goodNoteHit'),'signature/identity/family');
  }
  var count=forms.length*2;check(a.log.length==count&&b.log.length==0,'owner isolation');
  run(j,'PlayState.opponentNoteHit(note,field);');check(b.log.length==1&&a.log.length==count,'class owner');
  run(i,'function goodNoteHit(n,f){return "local";} if(goodNoteHit(note,field)!="local") throw "shadow"; game.goodNoteHit(note,field);');
  check(a.log.length==count+1,'local callback replaced explicit default');
  run(j,'game.goodNoteHit(null,field);game.goodNoteHit({},field);game.opponentNoteHit(note,null);');check(b.log.length==1,'invalid objects');
  for(form in forms){run(i,StringTools.replace(StringTools.replace(form,'goodNoteHit','noteMiss'),',field',''));check(a.log[a.log.length-1].miss==true,'miss signature');}
  run(i,'function noteMiss(n){return "local-miss";} if(noteMiss(note)!="local-miss") throw "miss shadow"; game.noteMiss(note);');
  check(a.log[a.log.length-1].miss==true,'explicit miss default');
  run(j,'PlayState.noteMiss(note);');check(b.log[b.log.length-1].miss==true,'miss owner');
  run(i,'noteMissPress();game.noteMissPress(3,false);');
  check(a.log[a.log.length-2].direction==1&&a.log[a.log.length-2].anim==true,'press defaults');
  check(a.log[a.log.length-1].direction==3&&a.log[a.log.length-1].anim==false,'press explicit animation');
  a.explode=true;var threw=false;try run(i,'game.opponentNoteHit(note,field);')catch(e:Dynamic)threw=true;
  check(threw,'handler failure swallowed');i.release();
  run(j,'goodNoteHit(note,field);');check(b.log.length==3,'other owner release');j.release();
 }
}'''
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);write_nv_field_dependencies(work);write_flixel_point_stub(work)
   for name,text in {'PlayState':fixture,'Note':'class Note {public function new(){}}','NightmareVisionPlayFieldView':'class NightmareVisionPlayFieldView {public function new(){}}','NightmareVisionLegacyHitFlow':'class NightmareVisionLegacyHitFlow {public static function hit(s:PlayState,n:Note,f:NightmareVisionPlayFieldView,p:Bool):Void {if(s.explode)throw "handler failure";s.log.push({note:n,field:f,player:p});}}','NightmareVisionLegacyMissFlow':'class NightmareVisionLegacyMissFlow {public static function press(s:PlayState,d:Int=1,a:Bool=true):Void {s.log.push({direction:d,anim:a});}public static function miss(s:PlayState,n:Note):Void {if(s.explode)throw "handler failure";s.log.push({note:n,miss:true});}}','Main':main}.items():(work/(name+'.hx')).write_text(text)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  seed=method(play,'function seedNightmareVision(')
  self.assertIn('if (nightmareVisionLegacyFieldCameras)\n\t\t\tNightmareVisionLegacyHitBindings.install',seed)
  self.assertIn('nightmareVisionLegacyGoodNoteHit, nightmareVisionLegacyOpponentNoteHit',seed)
if __name__=='__main__':unittest.main()
