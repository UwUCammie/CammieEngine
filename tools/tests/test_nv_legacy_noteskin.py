"""Historical noteskin script lifecycle, live arrays and lookup precedence."""
from pathlib import Path
import tempfile,subprocess,unittest
from haxe_test_support import HAXE_COMMAND
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
class LegacyNoteSkinTest(unittest.TestCase):
 def test_real_interpreter_callbacks_offsets_registration_and_cleanup(self):
  fixture=r'''
import nightmarevision.modchart.NightmareVisionModchartVector;
class Main {
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function main(){
  var order:Array<String>=[],errors:Array<String>=[];
  var source="record('execute');function onLoad(){record('wrong-onLoad');} function offset(n,r,s){record('offset');n[1].set(11,13);r[1].set(17,19);s[1].set(23,29);} function bfSkin(){record('bf');return 'notes/player';} function dadSkin(){record('dad');return 'notes/opponent';} function arrowSkin(){record('arrow');return 'custom';} function onUpdate(elapsed){record('update');} function onDestroy(){record('destroy');}";
  var host=new NightmareVisionGameplayScripts({}, {root:'owner',baseAssetsRoot:'',song:'s',stage:'st',scripts:[],coverageNotes:[]},
   function(path)return source,function(interp,entry,actor){check(entry.scope=='noteskin','source scope');interp.variables.set('record',function(s:String)order.push(s));},function(n,p,e)errors.push(n+':'+p));
  var n=NightmareVisionLegacyNoteSkin.offsets(4),r=NightmareVisionLegacyNoteSkin.offsets(4),s=NightmareVisionLegacyNoteSkin.offsets(4);
  var skin=new NightmareVisionLegacyNoteSkin('owner/noteskins/custom.hx',function(path)return host.fromOwnerFile(path,'noteskin',host.group.sharedFields),function(script){order.push('register');host.group.addScript(script);},n,r,s);
  check(order.join(',')=='execute,offset,register,bf,dad,arrow','source ordering '+order);
  check(skin.textures.join(',')=='notes/player,notes/opponent'&&skin.arrowSkin=='custom','texture callbacks');
  check(host.group.members.length==1&&host.group.members[0]==skin.script,'one shared module');
  var out=new NightmareVisionModchartVector();
  NightmareVisionLegacyNoteSkin.positionOffset('note',1,false,n,r,s,out);check(out.x==11&&out.y==13,'tap offsets');
  NightmareVisionLegacyNoteSkin.positionOffset('note',1,true,n,r,s,out);check(out.x==34&&out.y==42,'sustain plus note offsets');
  NightmareVisionLegacyNoteSkin.positionOffset('receptor',1,false,n,r,s,out);check(out.x==17&&out.y==19,'receptor offsets');
  n[1].x=37;NightmareVisionLegacyNoteSkin.positionOffset('note',1,false,n,r,s,out);check(out.x==37,'live mutation');
  NightmareVisionLegacyNoteSkin.positionOffset('noteSplash',1,false,n,r,s,out);check(out.x==0&&out.y==0,'no stray splash position offsets');
  host.call('onUpdate',[.1]);host.destroy();host.destroy();check(order.slice(order.length-2).join(',')=='update,destroy','single lifecycle');check(errors.length==0,'errors '+errors);
  var missing=new NightmareVisionLegacyNoteSkin(null,function(p){throw 'unexpected load';return null;},function(s){throw 'unexpected register';},n,r,s);
  check(missing.textures.join(',')=='NOTE_assets,NOTE_assets'&&missing.script==null,'missing source fallback');
  var malformed:NightmareVisionScriptModule=null;
  source='function broken( {';
  var broken=new NightmareVisionLegacyNoteSkin('owner/noteskins/broken.hx',function(path){malformed=host.fromOwnerFile(path,'noteskin',null);return malformed;},function(s){throw 'registered broken script';},n,r,s);
  check(broken.script==null && malformed.interp==null,'release failed unregistered script');
  var fresh=NightmareVisionLegacyNoteSkin.offsets(4);check(fresh[1].x==0&&fresh[1]!=n[1],'scene-owned arrays');
 }
}
'''
  self.run_haxe(fixture)
 def test_historical_extension_precedence_and_modern_path_contract(self):
  paths=(ROOT/'source/NightmareVisionPaths.hx').read_text()
  methods='\n'.join(method(paths,m) for m in ('public function legacyNoteskinScript(', 'public function noteskin('))
  methods += '\n' + paths[paths.index('public function modsNoteskin('):].split(';',1)[0] + ';'
  fixture=r'''
class Paths {
 public var scriptExtensions=['hx','hxs','hscript'];public var files:Map<String,Bool>=[];public var hudProfile:Dynamic={name:'legacy-shared'};
 public function new(){}
 public function modFolders(p:String):String {if(p.indexOf('..')>=0)throw 'invalid relative';return 'mod/'+p;}
 public function getOwnerCorePath(p:String):String return 'core/'+p;
 public function exists(p:String):Bool return files.exists(p);
 public function getPath(p:String,?folder:String,mods=false):String return (mods?'mod/':'core/')+(folder==null?'':folder+'/')+p;
 __METHODS__
}
class Main {
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function main(){
  var p=new Paths();p.files.set('core/noteskins/custom.hx',true);p.files.set('mod/noteskins/custom.hxs',true);
  check(p.legacyNoteskinScript('custom')=='core/noteskins/custom.hx','extension order before mod preference');
  p.files.set('mod/noteskins/custom.hx',true);check(p.legacyNoteskinScript('custom')=='mod/noteskins/custom.hx','same-extension mod override');
  check(p.legacyNoteskinScript('absent')==null,'no unrelated default for named skin');
  p.files.set('mod/noteskins/default.hscript',true);check(p.legacyNoteskinScript('')==null,'source default first-extension branch');
  p.files.set('core/noteskins/default.hx',true);check(p.legacyNoteskinScript(null)=='core/noteskins/default.hx','default core script');
  check(p.noteskin('custom.hx')=='core/noteskins/custom.hx','legacy explicit extension');check(p.modsNoteskin('custom.hx')=='mod/noteskins/custom.hx','mod spelling');
  var rejected=false;try p.legacyNoteskinScript('../foreign')catch(e:Dynamic)rejected=true;check(rejected,'delegates path validation');
  p.hudProfile.name='modern';p.files.set('mod/data/noteskins/custom.json',true);check(p.noteskin('custom')=='mod/data/noteskins/custom.json','modern json unchanged');
 }
}
'''.replace('__METHODS__',methods)
  self.run_haxe(fixture)
 def run_haxe(self,fixture):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
   work=Path(d);write_flixel_point_stub(work);(work/'Main.hx').write_text(fixture)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=45)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
