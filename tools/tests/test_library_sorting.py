"""Independent library ordering without changing registry, identity or source data."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]

class LibrarySortingTest(unittest.TestCase):
    def test_ordering_and_preference_migration(self):
        body=r"""import LibrarySort.LibrarySortRow;
class Main {
 static function check(ok:Bool, message:String){if(!ok)throw message;}
 static function row(i:Int, id:String, title:String, owner:String, mod:String, engine:String, ordinal:Int, favorite:Bool=false):LibrarySortRow
  return {index:i,id:id,title:title,owner:owner,modTitle:mod,engine:engine,ordinal:ordinal,favorite:favorite,random:false};
 static function main(){
  var rows=[row(0,'b-z','Zulu','b','Beta','Psych',2),row(1,'a-b','Bravo','a','Alpha','NV',0),
   row(2,'b-a','Alpha','b','Beta','Psych',3,true),row(3,'a-z','Zulu','a','Alpha','NV',1),
   row(4,'unknown','Unknown','u','','',4)];
  var unchanged=haxe.Json.stringify(rows);
  check(LibrarySort.order(rows,'mod','az','za').join(',')=='3,1,0,2,4','independent mod/chart alpha ordering');
  check(LibrarySort.order(rows,'mod','za','az').join(',')=='2,0,1,3,4','descending groups moved missing metadata to front');
  check(LibrarySort.order(rows,'engine','az','default').join(',')=='1,3,0,2,4','engine order or authored fallback wrong');
  check(LibrarySort.order(rows,'mod','engine','favorites').join(',')=='1,3,2,0,4','engine groups/favorites composition failed');
  check(LibrarySort.order(rows,'flat','az','az').join(',')==LibrarySort.order(rows,'flat','za','az').join(','),'flat list used group sorting');
  check(LibrarySort.order(rows,'flat','default','default').join(',')=='1,3,0,2,4','registry ordinal lost');
  var order=LibrarySort.order(rows,'mod','az','az');
  var filtered=[for(i in order) if(i==0 || i==2) i];
  check(filtered.join(',')=='2,0','filter split or reordered mod');
  check(LibrarySort.select(filtered,0,0)==0,'sorting lost selected chart');
  check(LibrarySort.select(filtered,0,1)==2 && LibrarySort.select(filtered,2,-1)==0,'wrapped ordered navigation wrong');
  check(LibrarySort.select(filtered,1,0)==2 && LibrarySort.select([],1,1)==1,'filtered-out or empty selection invalid');
  rows[0].modTitle='Alpha';rows[2].modTitle='Alpha';
  var tied=LibrarySort.order(rows,'mod','az','az').join(',');
  rows.reverse();check(LibrarySort.order(rows,'mod','az','az').join(',')==tied,'group tie is input-order dependent');rows.reverse();
  rows[0].modTitle='Beta';rows[2].modTitle='Beta';check(haxe.Json.stringify(rows)==unchanged,'sort mutated metadata');
  var random=row(5,'random','Random Song','','','',5);random.random=true;rows.push(random);
  check(LibrarySort.order(rows,'mod','za','za')[0]==5,'random action moved inside a mod group');
  var data=new UserLibraryData();var key=UserLibraryData.chartKey('a','song');data.setLastDifficulty(key,'Hard');data.setFavorite(key,true);
  var legacy:Dynamic=haxe.Json.parse(data.encode());Reflect.deleteField(legacy,'sorting');
  var loaded=UserLibraryData.decode(haxe.Json.stringify(legacy));check(loaded.sorting().grouping=='flat' && loaded.sorting().charts=='az','old save did not migrate');
  loaded.setSorting('mod','engine','favorites');var round=UserLibraryData.decode(loaded.encode());
  check(round.sorting().groups=='engine' && round.sorting().charts=='favorites' && round.lastDifficulty(key)=='Hard' && round.isFavorite(key),'sorting persistence damaged library');
  var detached=round.sorting();detached.groups='za';check(round.sorting().groups=='engine','UI can mutate saved preferences without transaction');
  var invalid:Dynamic=haxe.Json.parse(round.encode());invalid.sorting.charts='bogus';var rejected=false;
  try UserLibraryData.decode(haxe.Json.stringify(invalid)) catch(_:Dynamic) rejected=true;check(rejected,'invalid sorting silently overwrites save');
  var input:Dynamic={name:'zulu',display:'Zulu',week:0,character:'bf'};
  var display=FreeplaySongOrder.sort([{song:input,base:true,order:7}],true)[0];
  check(display!=input && display._libraryOrder==7 && !Reflect.hasField(input,'_libraryOrder'),'default order mutates registry');
  var many=[for(i in 0...5000) row(i,'song'+i,'Title'+(i%40),'owner'+(i%25),'Mod'+(i%25),'Psych',i)];
  var sorted=LibrarySort.order(many,'mod','az','za');check(sorted.length==5000,'large library lost rows');
  var seen:Map<Int,Bool>=[];for(i in sorted){check(!seen.exists(i),'duplicate row');seen.set(i,true);}
 }
}"""
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            (Path(temp)/'Main.hx').write_text(body)
            # FreeplaySongOrder needs only the existing test asset bridge for legacy title resolution.
            (Path(temp)/'FNFAssets.hx').write_text('class FNFAssets {public static function exists(p:String):Bool return false; public static function getText(p:String):String return "";}')
            (Path(temp)/'CoolUtil.hx').write_text('class CoolUtil {public static function parseJson(s:String):Dynamic return haxe.Json.parse(s);}')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_live_browser_cache_filters_and_selection_indexes(self):
        from test_freeplay_random_difficulty import extract_method
        source=(ROOT/'source/FreeplayState.hx').read_text()
        method=extract_method(source,'function orderedVisibleSongs():Array<Int>').replace('function orderedVisibleSongs()', 'public function orderedVisibleSongs()',1)
        main=r"""class UserLibrary {
 public static var model=new UserLibraryData(); public static function data() return model;
}
class Browser {
 public var denseBrowser=true; public var songs:Array<Dynamic>;
 public var libraryOrder:Array<Int>=[]; public var libraryOrderRows:Array<LibrarySort.LibrarySortRow>=[];
 public var libraryOrderKey='';public var libraryFavoriteData:UserLibraryData;
 public var reads=0;public var hidden=-1;
 public function new() songs=[
  {songName:'z',displayTitle:'Zulu',sourceLabel:'Misleading Psych label',owner:'nv',provenance:{sourceEngine:'Nightmare Vision',modName:'First'},libraryOrdinal:0,importProvenancePresent:true,isProvisional:false},
  {songName:'b',displayTitle:'Bravo',sourceLabel:'Psych label',owner:'psych',provenance:{sourceEngine:'Psych Engine',modName:'Second'},libraryOrdinal:1,importProvenancePresent:true,isProvisional:false},
  {songName:'a',displayTitle:'Alpha',sourceLabel:'NV',owner:'nv',provenance:{sourceEngine:'Nightmare Vision',modName:'First'},libraryOrdinal:2,importProvenancePresent:true,isProvisional:false}];
 function libraryOwner(i:Int):String {reads++; return songs[i].owner;}
 function sourceDisplayFor(song:Dynamic):Void {}
 function libraryChartKey(i:Int):String return UserLibraryData.chartKey(songs[i].owner,songs[i].songName);
 function songMatches(i:Int):Bool return i!=hidden;
METHOD
}
class Main {
 static function check(ok:Bool,message:String){if(!ok)throw message;}
 static function main(){
  var menu=new Browser();check(menu.orderedVisibleSongs().join(',')=='2,1,0' && menu.reads==0,'flat sorting eagerly loads provenance');
  UserLibrary.model.setSorting('mod','engine','za');
  check(menu.orderedVisibleSongs().join(',')=='0,2,1','source engine grouping wrong');var reads=menu.reads;
  check(menu.libraryOrderRows[0].engine=='Nightmare Vision','engine inferred from title instead of provenance');
  for(i in 0...100) menu.orderedVisibleSongs();check(menu.reads==reads,'unchanged navigation repeats metadata work');
  menu.hidden=0;check(menu.orderedVisibleSongs().join(',')=='2,1' && menu.reads==reads,'filter rebuilt or reordered groups');
  check(LibrarySort.select(menu.orderedVisibleSongs(),2,1)==1,'filtered navigation used global index');
  menu.hidden=-1;UserLibrary.model.setSorting('flat','az','favorites');
  UserLibrary.model.setFavorite(UserLibraryData.chartKey('psych','b'),true);
  check(menu.orderedVisibleSongs()[0]==1,'favorites mode ignored save');
  var next=UserLibraryData.decode(UserLibrary.model.encode());next.setFavorite(UserLibraryData.chartKey('psych','b'),false);next.setFavorite(UserLibraryData.chartKey('nv','a'),true);UserLibrary.model=next;
  check(menu.orderedVisibleSongs()[0]==2,'favorite transaction failed to invalidate order');
  UserLibrary.model.setSorting('flat','az','recent');UserLibrary.model.recordPlay(UserLibraryData.chartKey('psych','b'),2000);
  check(menu.orderedVisibleSongs()[0]==1,'actual browser did not consume play history');
  var played=UserLibraryData.decode(UserLibrary.model.encode());played.recordPlay(UserLibraryData.chartKey('nv','z'),1000);UserLibrary.model=played;
  check(menu.orderedVisibleSongs()[0]==0,'play transaction/clock rollback failed to invalidate order');
  UserLibrary.model.setSorting('mod','imported','za');UserLibrary.model.recordImports(['psych'],2000);
  check(menu.orderedVisibleSongs().join(',')=='1,0,2','browser ignored import history or changed local chart order');
  var imported=UserLibraryData.decode(UserLibrary.model.encode());imported.recordImports(['nv'],1000);UserLibrary.model=imported;
  check(menu.orderedVisibleSongs().join(',')=='0,2,1','import transaction failed to invalidate grouped order');
  var importsRead=menu.reads;for(i in 0...100)menu.orderedVisibleSongs();check(menu.reads==importsRead,'import ordering repeats metadata work');
  UserLibrary.model.setSorting('flat','default','default');
  menu.songs[0].authoredFreeplayOrder=1;menu.songs[2].authoredFreeplayOrder=0;
  check(menu.orderedVisibleSongs().join(',')=='2,1,0','live browser did not consume owner-local authored ranks');
  var orderReads=menu.reads;for(i in 0...100)menu.orderedVisibleSongs();check(menu.reads==orderReads,'default browsing repeats owner I/O');
  menu.songs[2].isProvisional=true;menu.libraryOrderKey='';
  check(menu.orderedVisibleSongs().join(',')=='0,1,2','provisional rank displaced ready song');
  menu.songs[2].isProvisional=false;
  menu.songs.pop();check(menu.orderedVisibleSongs().join(',')=='0,1','row removal retained stale indices');
  DifficultyManager.supportedDiff.set('z',[0,1]);DifficultyManager.supportedDiff.set('b',[0]);
  Highscore.values.set('z:0',0);Highscore.values.set('b:0',900);Highscore.values.set('z:1',100);
  UserLibrary.model.setSorting('flat','default','scoreHigh');
  check(menu.orderedVisibleSongs().join(',')=='1,0','browser did not read scores at comparison difficulty');
  var scoreReads=Highscore.reads;for(i in 0...100)menu.orderedVisibleSongs();check(Highscore.reads==scoreReads,'navigation repeated score reads');
  UserLibrary.model.setComparisonDifficulty('hard');check(menu.orderedVisibleSongs().join(',')=='0,1','comparison change did not invalidate ordering or used unsupported score');
  UserLibrary.model.setComparisonDifficulty('normal');menu.songs[0].authoredDifficultyRatings=FreeplayDifficultyRating.read([{difficulty:'normal',value:9,scale:'A'}]);
  menu.songs[1].authoredDifficultyRatings=FreeplayDifficultyRating.read([{difficulty:'normal',value:3,scale:'A'}]);
  UserLibrary.model.setSorting('flat','default','ratingLow');check(menu.orderedVisibleSongs().join(',')=='1,0','browser ignored named ratings');
  menu.songs[1].isProvisional=true;menu.libraryOrderKey='';check(menu.orderedVisibleSongs().join(',')=='0,1','provisional row received a comparison value');

 }
}""".replace('METHOD',method)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            (Path(temp)/'Main.hx').write_text(main)
            # Expose the in-fixture shared save facade to the extracted method.
            main=main.replace('class UserLibrary {','class FixtureLibrary {').replace('UserLibrary.', 'FixtureLibrary.')
            (Path(temp)/'Main.hx').write_text(main)
            (Path(temp)/'DifficultyManager.hx').write_text('class DifficultyManager {public static var supportedDiff:Map<String,Array<Int>>=[];public static function getDifficultyNames():Array<String> return ["normal","hard"];}')
            (Path(temp)/'Highscore.hx').write_text('class Highscore {public static var values:Map<String,Int>=[];public static var reads=0;public static function peekBestScore(song:String,diff:Int):Null<Int> {reads++;return values.get(song+":"+diff);}}')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
