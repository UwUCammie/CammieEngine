"""Shared base/NV library ordering and scoped historical core resolution."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
class SourceLibraryPathsTest(unittest.TestCase):
 def test_source_order_and_scoped_core_identity(self):
  nv=(ROOT/'source/NightmareVisionPaths.hx').read_text()
  core=method(nv,'function coreLibraryPath(file:String')
  play=(ROOT/'source/PlayState.hx').read_text()
  pair=method(play,'function nightmareVisionOwnerSparrowPaths(').replace('function nightmareVisionOwner','public function nightmareVisionOwner',1)
  within=method(play,'function nightmareVisionPathIsWithin(')
  ownercore=method(nv,'public function getOwnerCorePath(')
  label=method(nv,'static function validDirectoryLabel(')
  base=method((ROOT/'source/Paths.hx').read_text(),'static function getPath(').replace('static function','public static function',1)
  fixture=r"""import haxe.io.Path;
 using StringTools;
 typedef AssetType=String;
 class Game {
 public var nightmareVisionPaths:Main;public function new(p:Main)nightmareVisionPaths=p;
 __PAIR__
 __WITHIN__
 }
 class RuntimeOwnerAssetIdentity {
 public static var results:Map<String,Dynamic>=new Map();public static var calls:Array<String>=[];
 public static function lookup(owner:String,engine:String,scope:String,id:String,type:Dynamic):Dynamic {
  Main.check(owner=='owner'&&engine=='Nightmare Vision'&&scope=='core','only selected core index queried');calls.push(id);
  return results.exists(id)?results.get(id):{state:'no-index',path:null};
 }
 }
 class OpenFlAssets {public static var ids:Array<String>=[];public static function exists(id:String,type:String):Bool return ids.indexOf(id)>=0;}
 class Base {
 public static var currentLevel:String;
 static function getPreloadPath(file:String):String return 'case-resolved:assets/'+file;
 __BASE__
 }
 class Main {
 public var root='owner';public var CORE_DIRECTORY='owner/core';public var files:Array<String>=[];
 public var currentLevel:String='shared';
 public function new(){}
 public function scopeAssetPath(path:String):String return path;
 __OWNERCORE__
 __LABEL__
 function scopedPath(base:String,file:String):String {if(file.indexOf('..')>=0||file.indexOf(':')>=0||StringTools.startsWith(file,'/'))throw 'unsafe';return base+'/'+file;}
 public function exists(path:String):Bool return files.indexOf(path)>=0;
 __CORE__
 public static function check(ok:Bool,s:String):Void {if(!ok)throw s;}
 static function main(){
  var f='images/note.png';var shared='shared:assets/shared/'+f,level='week:assets/week/'+f;
  Base.currentLevel='week';OpenFlAssets.ids=[shared,level];check(Base.getPath(f,'IMAGE',null)==level,'base level first');
  OpenFlAssets.ids=[shared];check(Base.getPath(f,'IMAGE',null)==shared,'base shared fallback');
  OpenFlAssets.ids=[];check(Base.getPath(f,'IMAGE',null)=='case-resolved:assets/'+f,'base preserves case-aware preload');
  check(Base.getPath(f,'IMAGE','other')=='other:assets/other/'+f,'explicit library does not fall back');
  Base.currentLevel=null;OpenFlAssets.ids=[shared];check(Base.getPath(f,'IMAGE',null)=='case-resolved:assets/'+f,'unset level ignores shared');
  Base.currentLevel='preload';OpenFlAssets.ids=['preload:assets/preload/'+f,shared];
  check(Base.getPath(f,'IMAGE',null)=='preload:assets/preload/'+f,'current-level spelling uses forced namespace');
  check(Base.getPath(f,'IMAGE','preload')=='case-resolved:assets/'+f,'explicit preload remains an alias');
  var p=new Main();p.files=['owner/core/'+f,'owner/core/shared/'+f,'owner/core/week/'+f];
  check(p.coreLibraryPath(f,null)=='owner/core/'+f,'modern flat core unchanged');
  check(p.coreLibraryPath(f,'week')=='owner/core/week/'+f,'historical level first');
  p.files.remove('owner/core/week/'+f);check(p.coreLibraryPath(f,'week')=='owner/core/shared/'+f,'historical shared fallback');
  RuntimeOwnerAssetIdentity.results.set(shared,{state:'found',path:'owner/core/catalog/sheet.png'});
  check(p.coreLibraryPath(f,'shared')=='owner/core/catalog/sheet.png','authenticated index identity wins physical convention');
  for(state in ['missing','unknown','invalid','type-mismatch']) {
   RuntimeOwnerAssetIdentity.results.set(shared,{state:state,path:null});
   check(p.coreLibraryPath(f,'shared')=='owner/core/'+f,'definitive catalog status never borrows unverified shared file '+state);
  }
  RuntimeOwnerAssetIdentity.results.set(shared,{state:'unclaimed',path:null});check(p.coreLibraryPath(f,'shared')=='owner/core/shared/'+f,'unclaimed older core uses exact scoped file');
  RuntimeOwnerAssetIdentity.results=new Map();
  var game=new Game(p);
  p.files=['owner/images/note.png','owner/core/shared/images/note.xml'];
  check(game.nightmareVisionOwnerSparrowPaths('note')==null,'never combine partial mod/core atlases');
  p.files.push('owner/core/shared/images/note.png');
  check(game.nightmareVisionOwnerSparrowPaths('note').join('|')=='owner/core/shared/images/note.png|owner/core/shared/images/note.xml','reload pair follows shared library');
  p.files.push('owner/images/note.xml');check(game.nightmareVisionOwnerSparrowPaths('note')[0]=='owner/images/note.png','complete mod override wins');
  p.files=['sibling/images/note.png','sibling/images/note.xml'];check(game.nightmareVisionOwnerSparrowPaths('note')==null,'never borrow sibling pair');
  p.files=['owner/core/shared/images/note.png','owner/core/shared/images/note.xml'];
  RuntimeOwnerAssetIdentity.results.set(shared,{state:'missing',path:null});check(game.nightmareVisionOwnerSparrowPaths('note')==null,'catalog denial also blocks reload availability');
  check(game.nightmareVisionOwnerSparrowPaths('../note')==null,'pair rejects traversal');
  check(game.nightmareVisionOwnerSparrowPaths('shared:note')==null,'pair rejects injected library');
  p.currentLevel=null;RuntimeOwnerAssetIdentity.results=new Map();
  p.files=['owner/core/images/note.png','owner/core/images/note.xml'];check(game.nightmareVisionOwnerSparrowPaths('note')[0]=='owner/core/images/note.png','modern flat pair remains valid');
  var blocked=false;try p.coreLibraryPath('../other/secret','shared')catch(_:Dynamic)blocked=true;check(blocked,'reject traversal');
  blocked=false;try p.coreLibraryPath(f,'bad:library')catch(_:Dynamic)blocked=true;check(blocked,'reject namespace injection before lookup');
  blocked=false;try p.coreLibraryPath(f,'../other')catch(_:Dynamic)blocked=true;check(blocked,'reject unsafe library before lookup');
 }
 }
 """.replace('__OWNERCORE__',ownercore).replace('__PAIR__',pair).replace('__WITHIN__',within).replace('__LABEL__',label).replace('__CORE__',core).replace('__BASE__',base)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
   work=FixturePath(directory);(work/'Main.hx').write_text(fixture)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=45)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  self.assertIn("NightmareVisionStageProfile.LEGACY) currentLevel = 'shared'",nv)
if __name__=='__main__':unittest.main()
