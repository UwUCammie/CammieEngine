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
 def test_retained_scripts_supply_mechanics_without_running(self):
  with tempfile.TemporaryDirectory(dir=TEST_TMP if os.environ.get('CAMMIE_TEST_TMP') else None) as tmp:
   base=Path(tmp);install=base/'install';stage=base/'stage';state=base/'state'
   for p in (install,stage,state):p.mkdir()
   rows=','.join('[%d,%d,0]'%(i*250,i%4) for i in range(60))+','+','.join('[%d,%d,0,"Trap"]'%(i*1000,(i+2)%4) for i in range(15))
   (stage/'chart.json').write_text('{"song":{"notes":[{"mustHitSection":true,"sectionNotes":['+rows+']}]}}')
   (stage/'provenance').write_text('{"sourceEngine":"Psych Engine","sourceOwner":"assets/imported_mods/pack","sourceFolder":"test"}')
   (stage/'outside').write_text('{"sourceEngine":"Psych Engine","sourceOwner":"assets/imported_mods/../../escape","sourceFolder":"../test"}')
   owner=install/'assets/imported_mods/pack'
   (owner/'custom_notetypes').mkdir(parents=True);(owner/'data/test').mkdir(parents=True)
   (owner/'custom_notetypes/Trap.lua').write_text("function onCreate()\n setPropertyFromGroup('unspawnNotes', 0, 'ignoreNote', true)\nend\nfunction goodNoteHit()\n setProperty('boyfriend.stunned', true)\nend\n")
   (owner/'data/test/script.lua').write_text("function onBeatHit()\n noteTweenX('a', 4, 100, 0.5, 'quadOut')\n os.exit(1)\nend\n")
   (owner/'data/test/test.json').write_text('{"not":"a script"}')
   (base/'CoolUtil.hx').write_text('class CoolUtil {public static function parseJson(s:String):Dynamic return haxe.Json.parse(s);}')
   (base/'Main.hx').write_text(r"""import sys.io.File;class Main {
    static function check(b:Bool,s:String){if(!b)throw s;}
    static function main(){var args=Sys.args();var install=args[0];var stage=args[1];var state=args[2];
     var record:Dynamic={id:'test',schemaVersion:1,revisions:[{commonRevision:5}]};
     var r=ImportRefreshTransaction.apply(install,stage,state,'owner',['assets/data'],[
      {path:'assets/data/test/test.json',stagedPath:'chart.json'},
      {path:'assets/data/test/importProvenance.json',stagedPath:'provenance'},
      {path:'assets/data/plain/plain.json',stagedPath:'chart.json'},
      {path:'assets/data/plain/importProvenance.json',stagedPath:'outside'}],{importRecord:record,registries:[],chartAnalysisVersion:0});
     check(r.status=='applied','seed');
     var after=ChartDifficultyRefresh.refresh(install,state,'owner',ImportRefreshTransaction.loadManifest(state,'owner'));
     check(after.revision.chartAnalysisVersion==ChartDifficultyAnalysis.VERSION,'pending analysis not completed');
     var found=ChartDifficultyAnalysis.read(haxe.Json.parse(File.getContent(install+'/assets/data/test/chartDensity.json')).normal);
     var plain=ChartDifficultyAnalysis.read(haxe.Json.parse(File.getContent(install+'/assets/data/plain/chartDensity.json')).normal);
     check(found!=null && plain!=null,'analysis absent');
     check(found.mechanicNotes==15 && found.dangerNotes==15 && found.modchart>0 && found.unknownKinds==0,'retained scripts ignored');
     check(plain.mechanicNotes==0 && plain.modchart==0 && plain.unknownKinds==15,'unsafe owner was read');
     check(found.difficulty>plain.difficulty,'mechanics did not raise the rating');
     check(File.getContent(install+'/assets/imported_mods/pack/custom_notetypes/Trap.lua').indexOf('stunned')>0,'donor script changed');
    }}""")
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',tmp,'--run','Main',str(install),str(stage),str(state)],cwd=ROOT,capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_scripts_saved_in_a_legacy_encoding_do_not_block_the_refresh(self):
  # Donor scripts often carry comments in a non UTF-8 code page. The inputs are
  # checked again by raw file hash, so reading them as text must hash the same bytes.
  with tempfile.TemporaryDirectory(dir=TEST_TMP if os.environ.get('CAMMIE_TEST_TMP') else None) as tmp:
   base=Path(tmp);install=base/'install';stage=base/'stage';state=base/'state'
   for p in (install,stage,state):p.mkdir()
   (stage/'chart.json').write_text('{"song":{"notes":[{"mustHitSection":true,"sectionNotes":[[0,0,0],[500,1,0]]}]}}')
   (stage/'provenance').write_text('{"sourceEngine":"Psych Engine","sourceOwner":"assets/imported_mods/pack","sourceFolder":"test"}')
   owner=install/'assets/imported_mods/pack'
   (owner/'data/test').mkdir(parents=True)
   (owner/'data/test/intro.lua').write_bytes(b"local size = 18\t--\xcf\xd4\xca\xbe\nfunction onCreate()\nend\n")
   (base/'CoolUtil.hx').write_text('class CoolUtil {public static function parseJson(s:String):Dynamic return haxe.Json.parse(s);}')
   (base/'Main.hx').write_text(r"""class Main {
    static function check(b:Bool,s:String){if(!b)throw s;}
    static function main(){var args=Sys.args();var install=args[0];var stage=args[1];var state=args[2];
     var record:Dynamic={id:'test',schemaVersion:1,revisions:[{commonRevision:5}]};
     var r=ImportRefreshTransaction.apply(install,stage,state,'owner',['assets/data'],[
      {path:'assets/data/test/test.json',stagedPath:'chart.json'},
      {path:'assets/data/test/importProvenance.json',stagedPath:'provenance'}],{importRecord:record,registries:[],chartAnalysisVersion:0});
     check(r.status=='applied','seed');
     var after=ChartDifficultyRefresh.refresh(install,state,'owner',ImportRefreshTransaction.loadManifest(state,'owner'));
     check(after.revision.chartAnalysisVersion==ChartDifficultyAnalysis.VERSION,'analysis did not finish');
    }}""")
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',tmp,'--run','Main',str(install),str(stage),str(state)],cwd=ROOT,capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   # The interpreter keeps invalid UTF-8 as is, native builds do not; the
   # recorded hash has to come from the raw bytes on every target.
   source=(ROOT/'source/ChartDifficultyRefresh.hx').read_text(encoding='utf-8')
   self.assertNotIn('Bytes.ofString(text)',source)
   self.assertIn('Sha256.make(File.getBytes(resolved))',source)
if __name__=='__main__':unittest.main()
