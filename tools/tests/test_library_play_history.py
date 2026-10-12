"""Recent-play metadata is shared across menus and actual song-start lifecycle."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]
class LibraryPlayHistoryTest(unittest.TestCase):
    def run_haxe(self,body,files=None):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            (Path(temp)/'Main.hx').write_text(body)
            for name,text in (files or {}).items():(Path(temp)/name).write_text(text)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_migration_sequence_clock_changes_and_grouped_recent_sort(self):
        self.run_haxe(r"""import LibrarySort.LibrarySortRow;
class Main {
 static function check(ok:Bool,s:String){if(!ok)throw s;}
 static function row(i:Int,id:String,owner:String,played:Float):LibrarySortRow return {index:i,id:id,title:id,owner:owner,modTitle:owner,engine:'Psych',ordinal:i,favorite:false,random:false,played:played};
 static function main(){
  var data=new UserLibraryData();var first=UserLibraryData.chartKey('one','song');var second=UserLibraryData.chartKey('two','song');
  var old:Dynamic=haxe.Json.parse(data.encode());Reflect.deleteField(old,'plays');Reflect.deleteField(old,'playSequence');
  data=UserLibraryData.decode(haxe.Json.stringify(old));check(data.playOrder(first)==0,'old saves gained invented history');
  data.recordPlay(first,2000);data.recordPlay(second,1000);
  check(data.playOrder(second)>data.playOrder(first) && data.lastPlayed(second)==1000,'clock rollback corrupted recent order');
  data.setSorting('mod','za','recent');data.setFavorite(first,true);data.setLastDifficulty(first,'Hard');
  var saved=UserLibraryData.decode(data.encode());check(saved.playOrder(second)==2 && saved.sorting().charts=='recent','history did not survive save');
  check(saved.isFavorite(first) && saved.lastDifficulty(first)=='Hard','history damaged existing preferences');
  saved.recordPlay(first,1000);check(saved.playOrder(first)==3 && saved.playOrder(second)==2,'repeat/tied-time play failed');
  var rows=[row(0,'old','a',1),row(1,'unplayed','a',0),row(2,'new','a',3),row(3,'other','b',2)];
  check(LibrarySort.order(rows,'flat','za','recent').join(',')=='2,3,0,1','flat recent order or never-played tail wrong');
  check(LibrarySort.order(rows,'mod','za','recent').join(',')=='3,2,0,1','recent charts escaped group boundaries');
  check(UserLibraryData.resolvedChartKey('', 'x', '', true)=='','unknown import aliases base history');
  check(UserLibraryData.resolvedChartKey('owner','destination','authored-folder',true)==UserLibraryData.chartKey('owner','authored-folder'),'import rename changes history key');
  for(at in [0.0,-1.0,Math.NaN,Math.POSITIVE_INFINITY]) {var rejected=false;try saved.recordPlay(first,at) catch(_:Dynamic) rejected=true;check(rejected,'invalid clock accepted');}
  for(kind in 0...7) {
   var broken:Dynamic=haxe.Json.parse(saved.encode());
   switch(kind){case 0:broken.playSequence=-1;case 1:broken.plays[0].sequence=1.5;case 2:broken.plays[0].sequence=9;case 3:broken.plays[0].at='1000';case 4:broken.plays.push(broken.plays[0]);case 5:broken.plays[1].sequence=broken.plays[0].sequence;case 6:Reflect.deleteField(broken,'plays');}
   var rejected=false;try UserLibraryData.decode(haxe.Json.stringify(broken)) catch(_:Dynamic)rejected=true;check(rejected,'malformed history accepted '+kind);
  }
  var large:Dynamic=haxe.Json.parse(saved.encode());large.playSequence=4294967296.0;
  var high=UserLibraryData.decode(haxe.Json.stringify(large));high.recordPlay(first,3000);check(high.playOrder(first)==4294967297.0,'sequence narrowed to 32 bits');
 }
}""")
    def test_shared_identity_and_once_per_successful_play_instance(self):
        self.run_haxe(r"""class Main {
 static function check(ok:Bool,s:String){if(!ok)throw s;}
 static function main(){
  var history=new LibraryPlayHistory();check(UserLibrary.writes==0,'constructing a menu/start guard recorded a play');
  history.started('Tutorial');history.started('Tutorial');
  var base=UserLibraryData.chartKey('','Tutorial');check(UserLibrary.writes==1 && UserLibrary.model.playOrder(base)==1,'repeat start double-recorded or changed base case');
  new LibraryPlayHistory().started('Tutorial');check(UserLibrary.model.playOrder(base)==2,'actual replay not recorded');
  ImportedModDiscovery.owner='owner';FNFAssets.receipt='{"sourceFolder":"DonorSong"}';new LibraryPlayHistory().started('song--owner-hash');
  var key=UserLibraryData.chartKey('owner','DonorSong');check(UserLibrary.model.playOrder(key)==3,'history used visible title/destination instead of retained identity');
  ImportedModDiscovery.owner='';FNFAssets.receipt='malformed';new LibraryPlayHistory().started('unknown');check(UserLibrary.writes==3,'unknown import wrote base history');
  new LibraryPlayHistory().started('../escape');check(UserLibrary.writes==3,'unsafe path recorded history');
  FNFAssets.receipt=null;UserLibrary.fail=true;var failed=new LibraryPlayHistory();failed.started('Tutorial');failed.started('Tutorial');
  check(UserLibrary.writes==4 && UserLibrary.model.playOrder(base)==2,'save failure changed history or repeated work');
 }
}""",{
 'FNFAssets.hx':'class FNFAssets {public static var receipt:String=null; public static function exists(p:String):Bool return receipt!=null; public static function getText(p:String):String return receipt;}',
 'CoolUtil.hx':'class CoolUtil {public static function parseJson(s:String):Dynamic return haxe.Json.parse(s);}',
 'ImportedModDiscovery.hx':'class ImportedModDiscovery {public static var owner=""; public static function ownerForSong(s:String,r:String):String return owner;}',
 'UserLibrary.hx':'''class UserLibrary {public static var writes=0; public static var fail=false; public static var error="fixture failure";public static var model=new UserLibraryData();
 public static function change(fn:UserLibraryData->Void):Bool {writes++;if(fail)return false;var next=UserLibraryData.decode(model.encode());fn(next);model=next;return true;}}'''
        })
    def test_hook_is_after_audio_start_and_uses_existing_chart_identity(self):
        from test_freeplay_random_difficulty import extract_method
        text=(ROOT/'source/PlayState.hx').read_text()
        start=extract_method(text,'function startSong():Void')
        self.assertGreater(start.index('libraryPlayHistory.started(Highscore.scoreSongIdForChart(SONG))'),start.index('FlxG.sound.music.play()'))
        self.assertNotIn('LibraryPlayHistory',(ROOT/'source/FreeplayState.hx').read_text())
if __name__=='__main__':unittest.main()
