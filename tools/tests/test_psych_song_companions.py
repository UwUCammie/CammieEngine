"""Chart-authored script-only folders remain scoped to their imported owner."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
class PsychSongCompanionTest(unittest.TestCase):
 def test_referenced_scopes_and_runtime_song_directory(self):
  method=extract_method((ROOT/'source/ModuleFunctions.hx').read_text(),'static function mergePsychSongCompanions(')
  fixture=r'''import haxe.io.Path;import sys.FileSystem;import sys.io.File;using StringTools;
typedef ImportAssetMergeResult={var copied:Int;var skipped:Int;var failed:Int;}
class ImportDirectoryListing {public static function normalize(a:Array<String>):Array<String>return a;}
class Main {
 static function importWorkCancelled():Bool return false;
 static function validModuleName(n:String):Bool return n!=null && n!='' && n.indexOf('/')<0 && n.indexOf('\\')<0;
 static function readSongChart(path:String):Dynamic return haxe.Json.parse(File.getContent(path));
 static function findChildDirectory(parent:String,name:String):String {
  for(n in FileSystem.readDirectory(parent))if(n.toLowerCase()==name.toLowerCase())return Path.join([parent,n]);return null;
 }
 static function importPathIsWithin(path:String,root:String):Bool return StringTools.startsWith(Path.normalize(FileSystem.fullPath(path)),Path.normalize(FileSystem.fullPath(root))+'/');
 static function mergeTreeNonOverwriting(source:String,dest:String,depth:Int,result:ImportAssetMergeResult,skip:Map<String,Bool>):Void {
  FileSystem.createDirectory(dest);for(n in FileSystem.readDirectory(source)){var p=Path.join([source,n]);if(!FileSystem.isDirectory(p)){File.copy(p,Path.join([dest,n]));result.copied++;}}
 }
 __METHOD__
 static function main(){var root=Sys.args()[0];var source=root+'/source';var owner=root+'/owner';
  for(n in ['base','base-remix','unused'])FileSystem.createDirectory(source+'/data/'+n);
  File.saveContent(source+'/data/base/base-hard.json','{"song":{"song":"base"}}');
  File.saveContent(source+'/data/base/base-demon.json','{"song":{"song":"base-remix"}}');
  File.saveContent(source+'/data/base/script.lua','function onUpdate() end');
  File.saveContent(source+'/data/base-remix/cams.lua','function onUpdate() end');
  File.saveContent(source+'/data/unused/foreign.lua','should not run');
  var result:ImportAssetMergeResult={copied:0,skipped:0,failed:0};
  mergePsychSongCompanions(source+'/data/base',source,owner,result,[]);
  if(result.failed!=0 || !FileSystem.exists(owner+'/data/base-remix/cams.lua'))throw 'script-only authored scope omitted';
  if(FileSystem.exists(owner+'/data/unused'))throw 'unreferenced song scope retained';
  var directory=PsychScriptDiscovery.songDirectory(owner,'base-remix');
  if(Path.normalize(directory)!=Path.normalize(owner+'/data/base-remix'))throw 'runtime directory differs from retained scope';
  if(PsychScriptDiscovery.songDirectory(owner,'missing')!=null)throw 'missing scope invented';
 }}'''.replace('__METHOD__',method)
  with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
   work=Path(temp);(work/'Main.hx').write_text(fixture);install=work/'install';install.mkdir()
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main',str(install)],cwd=work,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
