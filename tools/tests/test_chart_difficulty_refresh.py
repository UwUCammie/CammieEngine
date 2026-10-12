"""Derived ratings migrate transaction-owned sidecars without reconverting assets."""
from pathlib import Path
import os,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT=Path(__file__).resolve().parents[2]
class ChartDifficultyRefreshTest(unittest.TestCase):
 def test_receipt_bound_migration_and_noop(self):
  with tempfile.TemporaryDirectory(dir=TEST_TMP if os.environ.get('CAMMIE_TEST_TMP') else None) as tmp:
   base=Path(tmp);install=base/'install';stage=base/'stage';state=base/'state'
   for p in (install,stage,state):p.mkdir()
   (stage/'chart.json').write_text('{"song":{"notes":[{"mustHitSection":true,"sectionNotes":[[0,0,0],[1000,1,0],[2000,2,0]]}]}}')
   (stage/'audio').write_bytes(b'unchanged media')
   (stage/'provenance').write_text('{"sourceEngine":"Psych Engine"}')
   (base/'CoolUtil.hx').write_text('class CoolUtil {public static function parseJson(s:String):Dynamic return haxe.Json.parse(s);}')
   (base/'Main.hx').write_text(r'''import sys.io.File;import sys.FileSystem;class Main {
    static function check(b:Bool,s:String){if(!b)throw s;}
    static function main(){var args=Sys.args();var install=args[0];var stage=args[1];var state=args[2];
     var record:Dynamic={id:'test',schemaVersion:1,revisions:[{commonRevision:5}]};
     var r=ImportRefreshTransaction.apply(install,stage,state,'owner',['assets'],[
      {path:'assets/data/test/test.json',stagedPath:'chart.json'},
      {path:'assets/data/test/importProvenance.json',stagedPath:'provenance'},
      {path:'assets/songs/test/Inst.ogg',stagedPath:'audio'}],{importRecord:record,registries:[]});
     check(r.status=='applied','seed');var before=ImportRefreshTransaction.loadManifest(state,'owner');
     var after=ChartDifficultyRefresh.refresh(install,state,'owner',before);
     check(after.files.length==4,'sidecar not owned');
     check(haxe.Json.stringify(after.revision.importRecord)==haxe.Json.stringify(record),'import revisions changed');
     check(File.getContent(install+'/assets/songs/test/Inst.ogg')=='unchanged media','media changed');
     var table=haxe.Json.parse(File.getContent(install+'/assets/data/test/chartDensity.json'));
     check(ChartDifficultyAnalysis.read(table.normal)!=null,'analysis absent or stale');
     check(ChartDifficultyRefresh.refresh(install,state,'owner',after).transactionId==after.transactionId,'repeated migration');
     var original=haxe.Json.stringify(after);File.saveContent(install+'/assets/data/test/chartDensity.json','{"user":"edit"}');
     after.revision.chartAnalysisVersion=0;var conflict=false;
     try ChartDifficultyRefresh.refresh(install,state,'owner',after) catch(e:Dynamic) conflict=true;
     check(conflict,'local sidecar edit overwritten');
     check(File.getContent(install+'/assets/data/test/chartDensity.json')=='{"user":"edit"}','local edit destroyed');
    }}''')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',tmp,'--run','Main',str(install),str(stage),str(state)],cwd=ROOT,capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
