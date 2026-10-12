"""Successful manual imports supply chronology without changing content or chart order."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]
class LibraryImportHistoryTest(unittest.TestCase):
    def test_import_batch_migration_validation_and_independent_group_order(self):
        body=r"""import LibrarySort.LibrarySortRow;
class Main {
 static function check(ok:Bool,s:String){if(!ok)throw s;}
 static function row(i:Int,owner:String,engine:String,rank:Float):LibrarySortRow return {index:i,id:'id'+i,title:'Title'+i,owner:owner,modTitle:owner,engine:engine,ordinal:i,favorite:false,random:false,imported:rank};
 static function main(){
  var data=new UserLibraryData();var key=UserLibraryData.chartKey('a','song');
  data.setFavorite(key,true);data.recordPlay(key,500);var category=data.createCategory('Keep');data.setMembership(category,'a',true);
  var old:Dynamic=haxe.Json.parse(data.encode());Reflect.deleteField(old,'imports');Reflect.deleteField(old,'importSequence');
  data=UserLibraryData.decode(haxe.Json.stringify(old));check(data.importOrder('a')==0,'legacy save invented dates');
  data.recordImports([' a/ ','b','a'],2000);
  check(data.importOrder('a')==1 && data.importOrder('b')==1 && data.lastImported('a/')==2000,'batch identities or sequence wrong');
  data.recordImports(['c'],1000);check(data.importOrder('c')==2,'wall clock rollback reordered import');
  data.setSorting('mod','imported','za');data=UserLibraryData.decode(data.encode());
  check(data.importOrder('c')==2 && data.sorting().groups=='imported','history/preference lost on reload');
  check(data.isFavorite(key) && data.playOrder(key)==1 && data.hasMod(category,'a'),'import history damaged other metadata');
  data.recordImports(['a'],1000);check(data.importOrder('a')==3 && data.importOrder('b')==1,'manual reimport changed unrelated roots');
  var before=data.encode();data.recordImports([],0);data.recordImports(null,0);check(data.encode()==before,'empty completion mutated history');
  for(at in [0.0,-1.0,Math.NaN,Math.POSITIVE_INFINITY]) {var failed=false;try data.recordImports(['d'],at) catch(_:Dynamic)failed=true;check(failed && data.encode()==before,'invalid timestamp mutated history');}
  var failed=false;try data.recordImports(['d',' '],3000) catch(_:Dynamic)failed=true;check(failed && data.encode()==before,'invalid batch partially applied');
  for(kind in 0...9){
   var broken:Dynamic=haxe.Json.parse(before);
   switch(kind){case 0:broken.importSequence=-1;case 1:broken.imports[0].sequence=1.5;case 2:broken.imports[0].sequence=99;case 3:broken.imports[0].at='2000';case 4:broken.imports.push(broken.imports[0]);case 5:broken.imports[1].sequence=broken.imports[0].sequence;broken.imports[1].at=99;case 6:Reflect.deleteField(broken,'imports');case 7:broken.imports[0].key='a/';case 8:broken.importSequence=1.5;}
   var rejected=false;try UserLibraryData.decode(haxe.Json.stringify(broken)) catch(_:Dynamic)rejected=true;check(rejected,'invalid history accepted '+kind);
  }
  var rows=[row(0,'a','Psych',1),row(1,'b','Psych',3),row(2,'a','Psych',1),row(3,'c','NV',2),row(4,'unknown','',0),row(5,'same-time','NV',3)];
  check(LibrarySort.order(rows,'mod','imported','za').join(',')=='1,5,3,2,0,4','package order/local chart order or unknown tail wrong');
  var tied=LibrarySort.order(rows,'mod','imported','za').join(',');rows.reverse();check(LibrarySort.order(rows,'mod','imported','za').join(',')==tied,'batch tie order unstable');rows.reverse();
  check(LibrarySort.order(rows,'engine','imported','default').join(',')=='3,5,0,1,2,4','engine group must use newest contained package');
  check(LibrarySort.order(rows,'flat','imported','default').join(',')=='0,1,2,3,4,5','inactive group order affected flat charts');
  var large:Dynamic=haxe.Json.parse(before);large.importSequence=4294967296.0;
  data=UserLibraryData.decode(haxe.Json.stringify(large));data.recordImports(['a'],3000);check(data.importOrder('a')==4294967297.0,'ordinal narrowed to 32 bits');
 }
}"""
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            (Path(temp)/'Main.hx').write_text(body)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
