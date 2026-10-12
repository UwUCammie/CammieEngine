"""Metric sorting has explicit difficulty scope, scale blocks and read-only scores."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
from test_freeplay_random_difficulty import extract_method
ROOT=Path(__file__).resolve().parents[2]
class LibraryMetricSortingTest(unittest.TestCase):
    def test_metric_contract_and_optional_preference_migration(self):
        body=r"""import LibrarySort.LibrarySortRow;
class Main {
 static function check(ok:Bool,s:String){if(!ok)throw s;}
 static function row(i:Int,value:Null<Float>,scale:String):LibrarySortRow return {index:i,id:'id'+i,title:'Song'+i,owner:i<3?'a':'b',modTitle:i<3?'A':'B',engine:'Psych',ordinal:i,favorite:false,random:false,metric:value==null?null:{value:value,scale:scale}};
 static function main(){
  var rows=[row(0,9,'A'),row(1,0,'A'),row(2,null,''),row(3,1,'B'),row(4,2,'A'),row(5,null,'')];
  check(LibrarySort.order(rows,'flat','default','ratingLow').join(',')=='1,4,0,3,2,5','scale or missing-value order wrong');
  check(LibrarySort.order(rows,'flat','default','ratingHigh').join(',')=='0,4,1,3,2,5','descending compares incompatible scales or moves missing values first');
  check(LibrarySort.order(rows,'mod','za','scoreLow').join(',')=='4,3,5,1,0,2','metric escaped group boundaries');
  var action=row(6,99999,'A');action.random=true;rows.push(action);
  check(LibrarySort.order(rows,'flat','default','scoreHigh')[0]==6 && LibrarySort.order(rows,'mod','za','ratingLow')[0]==6,'Random Song action lost pinned position');rows.pop();
  rows[0].metric.value=0;var tied=LibrarySort.order(rows,'flat','default','scoreLow').join(',');rows.reverse();check(LibrarySort.order(rows,'flat','default','scoreLow').join(',')==tied,'tied order unstable');
  var data=new UserLibraryData();var old:Dynamic=haxe.Json.parse(data.encode());Reflect.deleteField(old.sorting,'difficulty');
  data=UserLibraryData.decode(haxe.Json.stringify(old));check(data.sorting().difficulty=='normal','old preference migration');
  data.setSorting('mod','imported','ratingHigh');data.setComparisonDifficulty(' HARD ');data=UserLibraryData.decode(data.encode());
  check(data.sorting().difficulty=='hard' && data.sorting().groups=='imported' && data.sorting().charts=='ratingHigh','metric scope persistence/independence');
  var prefs=data.sorting();prefs.difficulty='bad';check(data.sorting().difficulty=='hard','mutable preference escaped');
  var before=data.encode();for(value in ['', ' ', 'x\n', null]) {var bad=false;try data.setComparisonDifficulty(value) catch(_:Dynamic)bad=true;check(bad && data.encode()==before,'bad comparison accepted');}
  var ambiguous=LibraryChartMetric.difficultyIndex('hard',['easy','HARD','hard']);check(ambiguous==-1,'ambiguous name selected first registry index');
  check(LibraryChartMetric.difficultyIndex('missing',['normal'])==-1,'unknown difficulty aliased normal');
  var calls=0;var score=function(song:String,index:Int):Null<Int>{calls++;return song=='known'?0:null;};
  var ratings=FreeplayDifficultyRating.read([{difficulty:'hard',value:8,scale:'Stars'}]);
  check(LibraryChartMetric.read('known',ratings,'scoreLow','hard',1,[0],score)==null && calls==0,'unsupported difficulty read a score');
  check(LibraryChartMetric.read('known',ratings,'scoreLow','hard',1,[1],score).value==0,'earned zero treated as unknown');
  check(LibraryChartMetric.read('missing',ratings,'scoreLow','hard',1,[1],score)==null,'unknown score fabricated');
  var rating=LibraryChartMetric.read('known',ratings,'ratingHigh','hard',1,[1],score);
  check(rating.value==8 && rating.scale=='Stars','authored rating lost');
  check(LibraryChartMetric.read('known',ratings,'ratingHigh','normal',0,[0],score)==null,'rating guessed another difficulty');
 }
}"""
        self.run_haxe(body)
    def run_haxe(self,body,files=None):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            (Path(temp)/'Main.hx').write_text(body)
            for name,content in (files or {}).items():(Path(temp)/name).write_text(content)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_actual_score_lookup_does_not_create_or_merge_records(self):
        source=(ROOT/'source/Highscore.hx').read_text()
        methods='\n'.join(extract_method(source,name) for name in ['public static function peekBestScore(', 'public static function formatSong('])
        self.run_haxe("""class Main {static function main(){
 var before=[for(k in Highscore.songScores.keys()) k].length;
 if(Highscore.peekBestScore('one',1)!=null || [for(k in Highscore.songScores.keys()) k].length!=before)throw 'read mutated score save';
 Highscore.songScores.set('one-hard-best-score',0);Highscore.songScores.set('two-hard-best-score',900);Highscore.songScores.set('one-hard',123);
 if(Highscore.peekBestScore('one',1)!=0 || Highscore.peekBestScore('two',1)!=900 || Highscore.peekBestScore('one',0)!=null)throw 'score identity/category collision';
}}""",{'Highscore.hx':'class Highscore {public static var songScores:Map<String,Int>=[];'+methods+'}',
'DifficultyIcons.hx':'class DifficultyIcons {public static function getEndingFP(i:Int):String return i==0?"":"-hard";}'})
if __name__=='__main__':unittest.main()
