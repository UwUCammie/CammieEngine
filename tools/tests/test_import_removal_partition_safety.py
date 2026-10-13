"""Independent partition sharing and registry category safety regressions."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,TEST_TMP
ROOT=Path(__file__).resolve().parents[2]
class ImportRemovalPartitionSafetyTest(unittest.TestCase):
 def test_partial_survivor_wins_and_category_name_is_not_chart_ownership(self):
  fixture=r'''@:access(ImportRemovalPartition)
class Main {
 static function check(ok:Bool,why:String):Void if(!ok)throw why;
 static function main(){
  var retained:Map<String,Array<String>>=['partial'=>['assets/common/shared.bin']];
  var selected:Map<String,Bool>=['assets/common/shared.bin'=>true];
  check(!ImportRemovalPartition.selectedCandidate('assets/common/shared.bin',['full','partial'],['partial'],selected,retained),'complete selected transaction deleted partial survivor common file');
  check(!ImportRemovalPartition.selectedCandidate('assets/common/shared.bin',['partial','otherpartial'],['partial','otherpartial'],selected,retained),'global selected path overrode partial survivor');
  var current:Dynamic=[{name:'alpha',songs:[{name:'alpha',character:'bf',week:1},{name:'beta',character:'bf',week:1}]}];
  var filtered=ImportRemovalPartition.filter([],current,['assets/imported_mods/alpha'],['assets/imported_mods/beta'],['alpha'],['beta']);
  var categories:Array<Dynamic>=cast filtered.value;
  check(categories.length==1&&categories[0].name=='alpha','selected chart name damaged category presentation');
  check(categories[0].songs.length==1&&categories[0].songs[0].name=='beta','surviving category chart damaged');
  Sys.println('partition safety passed');
 }
}'''
  with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
   work=Path(folder);(work/'Main.hx').write_text(fixture,encoding='utf-8')
   run=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--main','Main','--interp'],cwd=work,text=True,capture_output=True,timeout=30)
   self.assertEqual(run.returncode,0,run.stdout+run.stderr)
if __name__=='__main__':unittest.main()
