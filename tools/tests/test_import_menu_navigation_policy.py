"""Import ownership replaces blanket menu locks without allowing pending entries."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]

class ImportMenuNavigationTest(unittest.TestCase):
    def compile(self,code):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory)
            (work/'Main.hx').write_text(code,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],cwd=work,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_actual_navigation_policy_allows_safe_entry_during_work(self):
        self.compile(r"""class Main {static function main(){
 for(action in ['freeplay','options'])if(!ImportMenuNavigationPolicy.mainActionAllowed(true,action))throw action;
 for(action in ['story mode','costumes'])if(ImportMenuNavigationPolicy.mainActionAllowed(true,action))throw action;
 for(action in ['Import Settings...','Controls...','Show FPS Counter','Sound Test...'])if(!ImportMenuNavigationPolicy.optionsActionAllowed(true,action))throw action;
 for(action in ['Module...','New Character...','New Song...','Sort...'])if(ImportMenuNavigationPolicy.optionsActionAllowed(true,action))throw action;
 if(!ImportMenuNavigationPolicy.optionsActionAllowed(false,'Module...'))throw 'idle editor';
}}""")

    def test_actual_chooser_launch_checks_owner_before_factory(self):
        source=(ROOT/'source/CodenameImportedModsState.hx').read_text(encoding='utf-8')
        launch=extract_method(source,'function launchSelected():Void').replace('function launchSelected','public function launchSelected',1)
        code=r"""
class CodenameModRuntime {public static var opened='';public static function activateOwner(r:String):Bool {opened=r;return true;}public static function diagnostics():Array<String>return [];public static function clearActiveOwner():Void{}}
class CodenameImportedState {public var root:String;public function new(r:String,s:String)root=r;}
class LoadingState {public static var target:Dynamic;public static function loadAndSwitchState(s:Dynamic):Void target=s;}
class FreeplayRegistry {public static function getJson():Dynamic return [];}
class FreeplayDirectEntry {public static function select(a:Dynamic,r:String,f:Dynamic):Array<Dynamic>return [];}
class ImportedModDiscovery {public static function ownerForSong(n:String,r:String):String return '';}
class ImportedFreeplayCaller {public static function capturePackage(r:String):Void{}}
class FreeplayState {public static var currentSongList:Array<Dynamic>;public function new(){}}
class Main {
 var selected=0;var diagnostics:Array<String>=[];var details:Dynamic={text:''};
 var entries:Array<Dynamic>=[{root:'assets/imported_mods/a',launchState:'title',songCount:1},{root:'assets/imported_mods/b',launchState:'title',songCount:1}];
 var importAvailability:ImportRefreshAvailabilitySnapshot;
 function new(){importAvailability={revision:1,inspectionPending:false,pendingOwnerRoots:['assets/imported_mods/a'],handoffPendingOwnerRoots:[],committedOwnerRoots:['assets/imported_mods/a','assets/imported_mods/b'],pendingTouchedPaths:[],pendingSongs:[]};}
 function syncImportAvailability():Bool return false;
 function refreshRows():Void {}
"""+launch+r"""
 static function main(){
 var state=new Main();state.launchSelected();
 if(CodenameModRuntime.opened!=''||LoadingState.target!=null||state.details.text=='')throw 'pending owner reached factory';
 state.selected=1;state.launchSelected();
 if(CodenameModRuntime.opened!='assets/imported_mods/b'||LoadingState.target.root!='assets/imported_mods/b')throw 'ready unrelated owner was blocked';
 }
}
"""
        self.compile(code)

    def test_blanket_returns_removed_and_status_caches_are_bound(self):
        main=(ROOT/'source/MainMenuState.hx').read_text(encoding='utf-8')
        options=(ROOT/'source/SaveDataState.hx').read_text(encoding='utf-8')
        chooser=(ROOT/'source/CodenameImportedModsState.hx').read_text(encoding='utf-8')
        self.assertNotIn('if (refresh.busy) { super.update(elapsed); return; }',main)
        self.assertNotIn('if (ImportRefreshManager.browseTick().busy)',options)
        self.assertIn('mainActionAllowed(importWorkBusy',main)
        self.assertIn('optionsActionAllowed(importWorkBusy',options)
        self.assertIn('availabilityRevision != ImportRefreshManager.availabilityRevision()',chooser)
        self.assertIn('reconcilePendingEntries()',chooser)
        self.assertIn('!ready ? 0xFF777777',chooser)
