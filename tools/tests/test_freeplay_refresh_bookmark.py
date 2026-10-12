"""Keep a live library view by retained identity through published registry changes."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
from test_freeplay_random_difficulty import extract_method
ROOT=Path(__file__).resolve().parents[2]
class FreeplayRefreshBookmarkTest(unittest.TestCase):
    def test_actual_restore_methods_preserve_identity_search_and_named_difficulty(self):
        source=(ROOT/'source/FreeplayState.hx').read_text()
        methods='\n'.join(extract_method(source,m) for m in (
            'function refreshSelectionKey(',
            'function restoreRefreshSelection(', 'function restoreRefreshDifficulty('))
        # The expression-bodied scope method is intentionally separate from brace extraction.
        methods+="\nfunction refreshViewScope():String return haxe.Json.stringify([soundTest,curCategory,libraryViewId,directOwnerRoot]);"
        fixture=r"""class DifficultyManager {
 public static var names=['normal','hard'];
 public static function getDifficultyNames()return names;
 public static function getSupportedDiffs(song:String):Array<Int> return [0,1];
}
class Browser {
 public var soundTest=false;public var songs:Array<Dynamic>=[];
 public var curSelected=0;public var curDifficulty=0;
 public var curCategory='All';public var libraryViewId='';public var directOwnerRoot='';
 public var searchString='';public var refreshNotice='';public var refreshBookmark:FreeplayRefreshBookmark;
 public var denseBrowser=true;public var hxcDifficultyOrder:Array<String>=[];
 public var visible=true;public var allowed=true;public var refreshed=0;public var diffUpdates=0;
 public function new(){}
 function libraryChartKey(i:Int):String return songs[i].key;
 function selectionHasChart(name:String,index:Int):Bool return allowed;
 function songMatches(index:Int):Bool return visible;
 function changeDiff():Void diffUpdates++;
 function updateBrowserDetails():Void refreshed++;
 public function select():Void restoreRefreshSelection();
 public function difficulty():Void restoreRefreshDifficulty();
 public function scope():String return refreshViewScope();
 METHODS
}
class Main {
 static function check(v:Bool,m:String){if(!v)throw m;}
 static function row(id:String,key:String):Dynamic return {songName:id,key:key,isProvisional:false,ownerRoot:'',sourceFolder:'',pendingKey:''};
 static function main(){
  var a=UserLibraryData.chartKey('owner-a','same'),b=UserLibraryData.chartKey('owner-b','same');
  var menu=new Browser();menu.songs=[row('inserted',b),row('new-destination',a)];
  menu.refreshBookmark=new FreeplayRefreshBookmark(a,'my search','hard',menu.scope());
  menu.select();check(menu.curSelected==1 && menu.searchString=='my search','selected by stale ordinal/title or lost search');
  DifficultyManager.names=['hard','normal'];menu.curDifficulty=1;
  menu.difficulty();check(menu.curDifficulty==0 && menu.diffUpdates==1 && menu.refreshBookmark==null,'difficulty restored by old index or bookmark not consumed');
  menu.refreshBookmark=new FreeplayRefreshBookmark(a,'still searching','absent',menu.scope());menu.select();menu.curDifficulty=1;menu.difficulty();
  check(menu.curDifficulty==1,'removed difficulty invented');
  menu.refreshBookmark=new FreeplayRefreshBookmark(a,'query','hard',menu.scope());menu.select();menu.allowed=false;menu.difficulty();
  check(menu.curDifficulty==1,'missing chart bypassed availability');
  menu.songs=[row('same',b)];menu.refreshBookmark=new FreeplayRefreshBookmark(a,'query','hard',menu.scope());menu.select();menu.difficulty();
  check(menu.curSelected==0 && menu.refreshNotice.indexOf('no longer listed')>=0,'foreign same-name owner substituted silently');
  menu.songs=[row('one',a),row('two',a)];menu.refreshBookmark=new FreeplayRefreshBookmark(a,'query','hard',menu.scope());menu.select();
  check(menu.refreshNotice.indexOf('ambiguous')>=0,'ambiguous source identity picked first row');
  menu.refreshNotice='';menu.songs=[row('same',a)];menu.refreshBookmark=new FreeplayRefreshBookmark(a,'query','hard',menu.scope());menu.select();menu.visible=false;menu.difficulty();
  check(menu.refreshNotice.indexOf('hidden by filters')>=0,'filtered selection reported as deletion');
  menu.visible=true;menu.refreshNotice='';menu.searchString='new context';menu.directOwnerRoot='different';
  menu.refreshBookmark=new FreeplayRefreshBookmark(a,'leaked search','hard','old scope');menu.select();
  check(menu.searchString=='new context' && menu.refreshBookmark==null,'bookmark leaked into another view');
  var pending=row('pending-opaque','');pending.isProvisional=true;pending.ownerRoot='owner-a';pending.sourceFolder='same';pending.pendingKey='opaque';
  menu.songs=[pending];menu.refreshBookmark=new FreeplayRefreshBookmark(a,'query','hard',menu.scope());menu.select();var calls=menu.diffUpdates;menu.difficulty();
  check(menu.curSelected==0 && menu.diffUpdates==calls && pending.isProvisional,'provisional restoration changed launch readiness');
  menu.songs=[row('ready-renamed',a)];menu.refreshBookmark=new FreeplayRefreshBookmark(a,'query','hard',menu.scope());menu.select();
  check(menu.curSelected==0,'pending identity did not map to published row');
  var library=new UserLibraryData();library.setFavorite(a,true);library.setLastDifficulty(a,'hard');
  var category=library.createCategory('Tests');library.setMembership(category,'owner-a',true);
  library.setSorting('mod','az','default');library.recordPlay(a,10);library.recordImports(['owner-a'],20);
  var snapshot=library.encode();var reload=UserLibraryData.decode(snapshot);
  check(reload.isFavorite(a) && reload.lastDifficulty(a)=='hard' && reload.encode()==snapshot,'view restoration mutated independent library save');
 }
}""".replace('METHODS',methods)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as td:
            base=Path(td);(base/'Main.hx').write_text(fixture)
            proc=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',td,'--run','Main'],cwd=ROOT,text=True,capture_output=True,timeout=60)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)

    def test_real_constructor_keeps_only_explicit_same_menu_refresh_caller(self):
        source=(ROOT/'source/FreeplayState.hx').read_text()
        ctor=extract_method(source,'public function new()')
        body=r"""class FlxG {public static var state:Dynamic;}
class CodenameImportedState {public var ownerRoot='';public var scriptPath='';}
class CodenameModRuntime {public static var owner='';public static function activeRoot()return owner;}
class ModifierState {}
class PlayState {}
class Base {public function new(){}}
class FreeplayState extends Base {
 public var refreshBookmark:FreeplayRefreshBookmark;
 public var outgoingRefreshBookmark:FreeplayRefreshBookmark;
 CTOR
}
class Main {
 static function check(v:Bool,m:String){if(!v)throw m;}
 static function main(){
  var old=new FreeplayState();FlxG.state=old;
  CodenameModRuntime.owner='owner-a';ImportedFreeplayCaller.capture('owner-a','states/menu.hx');
  var bookmark=new FreeplayRefreshBookmark('key','search','hard','scope');old.outgoingRefreshBookmark=bookmark;
  // The existing zero-argument factory remains a zero-argument function.
  var factory:Void->FreeplayState=FreeplayState.new;var next=factory();
  check(next.refreshBookmark==bookmark && old.outgoingRefreshBookmark==null,'bookmark not transferred once');
  check(ImportedFreeplayCaller.ownerForFreeplay('owner-a')=='owner-a','refresh lost imported menu caller');
  FlxG.state=next;var ordinary=new FreeplayState();
  check(ordinary.refreshBookmark==null && ImportedFreeplayCaller.ownerForFreeplay('owner-a')=='','bookmark leaked to ordinary menu launch');
 }
}""".replace('CTOR',ctor)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as td:
            base=Path(td);(base/'Main.hx').write_text(body)
            (base/'CompatScriptManifest.hx').write_text("class CompatScriptManifest {public static function destinationKey(s:String):String return s==null?'':s.toLowerCase();}")
            proc=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',td,'--run','Main'],cwd=ROOT,text=True,capture_output=True,timeout=60)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)

    def test_departed_selection_requires_changed_revision_and_matching_scope_once(self):
        fixture=r"""class Main {
 static function check(v:Bool,m:String){if(!v)throw m;}
 static function main(){
  var memory=new FreeplaySessionSelection();
  var a=new FreeplayRefreshBookmark('owner-a:chart','search a','hard','scope-a');
  var b=new FreeplayRefreshBookmark('owner-b:chart','search b','normal','scope-b');
  check(memory.take('scope-a',2)==null,'empty session invents selection');
  memory.remember(a,2);check(memory.take('scope-a',2)==null,'ordinary return changes existing entry behavior');
  check(memory.take('scope-a',3)==null,'unchanged return retained stale bookmark');
  memory.remember(a,2);check(memory.take('scope-b',3)==null,'old owner leaks into another view');
  check(memory.take('scope-a',3)==null,'discarded scope reappears later');
  memory.remember(a,2);check(memory.take('scope-a',4)==a,'multiple publications lost departure');
  check(memory.take('scope-a',5)==null,'departure restored twice');
  memory.remember(a,2);memory.remember(b,4);
  check(memory.take('scope-b',5)==b,'latest departing view did not replace previous');
  memory.remember(a,2);memory.remember(null,3);
  check(memory.take('scope-a',4)==null,'failed capture retained an older selection');
 }
}"""
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as td:
            base=Path(td);(base/'Main.hx').write_text(fixture)
            proc=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',td,'--run','Main'],cwd=ROOT,text=True,capture_output=True,timeout=60)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
