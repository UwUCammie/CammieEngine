"""Persistent user metadata is separate from generated content and difficulty identity."""
from pathlib import Path
import subprocess,tempfile,unittest
from test_native_asset_resolution import extract_method
from haxe_test_support import HAXE_COMMAND,FixturePath,haxe_command
ROOT=Path(__file__).resolve().parents[2]
class UserLibraryTest(unittest.TestCase):
    def run_haxe(self,body,files=None,windows=True):
        with tempfile.TemporaryDirectory() as folder:
            p=FixturePath(folder)
            (p/'Main.hx').write_text('class Main {static function check(v:Bool,m:String){if(!v)throw m;} static function main(){'+body+'}}')
            for name,text in (files or {}).items():
                target=p/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
            result=subprocess.run([*haxe_command(windows=windows),'-cp',str(ROOT/'source'),'-cp',folder,'--run','Main'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_identity_persistence_membership_and_detached_views(self):
        body=r'''
 var a=UserLibraryData.chartKey('assets/imported_mods/alpha','Song');
 var b=UserLibraryData.chartKey('assets/imported_mods/beta','Song');
 var base=UserLibraryData.chartKey('','Song');
 check(a!=b && a!=base && b!=base,'duplicate song isolation');
 var data=new UserLibraryData();data.setFavorite(a,true);data.setLastDifficulty(a,'NIGHTMARE');
 var first=data.createCategory('Favorites are separate');var second=data.createCategory('Unicode cafe é');
 data.setMembership(first,'alpha',true);data.setMembership(second,'alpha',true);data.setMembership(first,'alpha',true);
 check(data.categoryList()[0].mods.length==1,'duplicate membership');
 check(data.matchesCategories([first,second],'alpha') && !data.matchesCategories([first,second],'beta'),'category union');
 var detached=data.categoryList();detached[0].mods.push('beta');detached[0].name='changed';
 check(!data.hasMod(first,'beta') && data.categoryList()[0].name!='changed','live metadata escaped');
 data=UserLibraryData.decode(data.encode());
 check(data.isFavorite(a) && !data.isFavorite(b) && !data.isFavorite(base),'restart favorites');
 check(data.lastDifficulty(a)=='NIGHTMARE','difficulty preference');
 data.setLastDifficulty(a,'HARD');check(data.isFavorite(a),'difficulty must not change favorite');
 data.renameCategory(first,'Renamed');data.deleteCategory(first);
 check(data.hasMod(second,'alpha') && data.isFavorite(a),'category deletion removed other membership or chart history');
 data.setMembership(second,'alpha',false);check(!data.hasMod(second,'alpha') && data.isFavorite(a),'membership changed chart history');
 data.setFavorite(a,false);check(data.lastDifficulty(a)=='HARD','unfavorite deleted difficulty');
 var third=data.createCategory('Again');check(third!=first && third!=second,'reused category identity');
 check(data.matchesCategories([],''),'empty filter');
 #if windows
 check(a==UserLibraryData.chartKey('ASSETS\\IMPORTED_MODS\\ALPHA','song'),'windows identity');
 #else
 check(a!=UserLibraryData.chartKey('ASSETS/IMPORTED_MODS/ALPHA','song'),'case sensitive identity');
 #end
 '''
        for windows in [True,False]:
            with self.subTest(windows=windows):self.run_haxe(body,windows=windows)
    def test_freeplay_uses_retained_identity_and_rejects_unresolved_receipts(self):
        method=extract_method((ROOT/'source/FreeplayState.hx').read_text(),'function libraryChartKey(')
        files={'FreeplayIdentity.hx':"""class FreeplayIdentity {
 public var soundTest=false;
 public var songs:Array<Dynamic>=[];
 public var resolves=0;
 public function new(){}
 function resolveSongIdentity(s:Dynamic):Void {resolves++;}
 public function key(i:Int):String return libraryChartKey(i);
 METHOD
}""".replace('METHOD',method)}
        self.run_haxe(r'''
 var f=new FreeplayIdentity();
 function song(name:String,owner:String,folder:String,receipt:Bool):Dynamic return {
  songName:name,ownerRoot:owner,sourceFolder:folder,importProvenancePresent:receipt,isProvisional:false,libraryKey:null};
 f.songs=[song('old-generated','assets/imported_mods/a','original',true),
  song('new-generated','assets/imported_mods/a','original',true),
  song('old-generated','assets/imported_mods/b','original',true),
  song('unresolved','','original',true),song('base','','',false),song('random-song','','',false)];
 check(f.key(0)==f.key(1),'destination rename changed source identity');
 check(f.key(0)!=f.key(2),'distinct owners merged');
 check(f.key(3)=='','unresolved receipt treated as base');
 check(f.key(4)==UserLibraryData.chartKey('','base'),'base identity');
 check(f.key(5)=='' && f.key(-1)=='' && f.key(6)=='','non-chart favorite');
 var count=f.resolves;f.key(0);f.key(3);check(f.resolves==count,'repeat identity I/O');
 f.songs[0].isProvisional=true;check(f.key(0)=='','pending placeholder favorite');
 f.soundTest=true;check(f.key(4)=='','sound test favorite');
 ''',files)
    def test_invalid_or_future_metadata_is_not_silently_reset(self):
        self.run_haxe(r'''
 for(raw in ['{}','null','{"version":2}','{"version":1,"nextCategory":1,"categories":[],"favorites":null,"difficulties":[]}',
 '{"version":1,"nextCategory":2,"categories":[{"id":"category-2","name":"x","mods":[]}],"favorites":[],"difficulties":[]}']){
  var failed=false;try UserLibraryData.decode(raw) catch(_:Dynamic)failed=true;check(failed,'invalid save accepted '+raw);
 }
 var failed=false;try new UserLibraryData().createCategory('   ') catch(_:Dynamic)failed=true;check(failed,'empty category');
 ''')
    def test_save_failure_and_future_document_preservation(self):
        files={'RuntimeSmokeHarness.hx':'class RuntimeSmokeHarness {public static function enabled():Bool return true;}',
 'flixel/util/FlxSave.hx':r'''package flixel.util;
 class FlxSave {public static var disk:Dynamic=null;public static var fail=false;public var data:Dynamic;
 public function new(){} public function bind(n:String,p:String):Bool {if(n!='CammieEngineLibrarySmoke')throw 'production save'; data={library:disk};return true;}
 public function flush():Bool {if(fail)return false;disk=data.library;return true;}}
 '''}
        self.run_haxe(r'''
 var key=UserLibraryData.chartKey('owner','song');
 check(UserLibrary.change(function(d){d.setFavorite(key,true);d.recordPlay(key,1000);}),'save');
 LibraryImportHistory.committed(['owner','second']);
 check(UserLibrary.data().importOrder('owner')==1 && UserLibrary.data().importOrder('second')==1,'batch save');
 var persisted=flixel.util.FlxSave.disk;
 flixel.util.FlxSave.fail=true;
 check(!UserLibrary.change(function(d){d.setFavorite(key,false);d.recordPlay(key,2000);}), 'failed save accepted');
 LibraryImportHistory.committed(['owner','third']);
 check(UserLibrary.data().importOrder('owner')==1 && UserLibrary.data().importOrder('third')==0,'failed import history leaked');
 check(UserLibrary.data().playOrder(key)==1 && UserLibrary.data().lastPlayed(key)==1000,'failed play history leaked');
 check(UserLibrary.data().isFavorite(key) && flixel.util.FlxSave.disk==persisted && UserLibrary.error!='','rollback');
 flixel.util.FlxSave.fail=false;
 check(UserLibrary.change(function(d)d.createCategory('Category')) && UserLibrary.error=='','recovery');
 ''',files)
        self.run_haxe(r'''
 flixel.util.FlxSave.disk='{"version":999}';
 check(!UserLibrary.change(function(d)d.createCategory('Category')),'future overwritten');
 check(flixel.util.FlxSave.disk=='{"version":999}' && UserLibrary.error!='','future lost');
 ''',files)

    def test_category_owner_normalization_and_invalid_names(self):
        self.run_haxe(r'''
 var data=new UserLibraryData();var id=data.createCategory('One');
 data.setMembership(id,' ASSETS\\IMPORTED_MODS\\EXAMPLE/ ',true);
 data.setMembership(id,'assets/imported_mods/example',true);
 check(data.categoryList()[0].mods.length==1,'canonical owner duplicated');
 check(data.hasMod(id,'assets/imported_mods/example/') && data.matchesCategories([id],'ASSETS/IMPORTED_MODS/EXAMPLE'),'owner spelling changes lost membership');
 data=UserLibraryData.decode(data.encode());data.setMembership(id,'ASSETS/IMPORTED_MODS/EXAMPLE',false);
 check(data.categoryList()[0].mods.length==0,'normalized removal');
 for(name in ['a\tb','a\nb','a'+String.fromCharCode(0)+'b']) {
  var rejected=false;try data.createCategory(name) catch(_:Dynamic) rejected=true;
  check(rejected,'control character accepted');
 }
 var rejected=false;try data.setMembership(id,'///',true) catch(_:Dynamic) rejected=true;
 check(rejected,'empty canonical owner accepted');
 ''')

    def test_name_grid_navigation_stays_in_bounds_and_wraps_rows(self):
        method=extract_method((ROOT/'source/LibraryNameSubState.hx').read_text(),'static function verticalSelection(')
        self.run_haxe('''
 check(Grid.move(0,-1,68)==60,'up wrap changed column');
 check(Grid.move(67,1,68)==7,'down wrap changed column');
 check(Grid.move(59,1,68)==67,'partial row not clamped');
 for(i in 0...68) for(d in [-1,1]) check(Grid.move(i,d,68)>=0 && Grid.move(i,d,68)<68,'out of grid');
 ''',{'Grid.hx':'class Grid {public static function move(i:Int,d:Int,c:Int):Int return verticalSelection(i,d,c);'+method+'}'})

    def test_nested_action_menu_does_not_reuse_opening_accept(self):
        method=extract_method((ROOT/'source/LibraryMenuSubState.hx').read_text(),'override function update(').replace('override function update','override public function update')
        files={'flixel/FlxG.hx':'package flixel; class FlxG {public static var game={inputFrame:40};}',
         'Base.hx':'class Base {public function new(){} public function update(elapsed:Float):Void {}}',
         'Menu.hx':'''import flixel.FlxG; class Menu extends Base {
          public var openingInputFrame=40;public var calls=0;var selected=0;
          var nativeControls={BACK:false,UP_MENU:false,DOWN_MENU:false,ACCEPT:true};
          var actions:Array<{run:Void->Void}>;
          public function new(){super();actions=[{run:function(){calls++;}}];}
          function render():Void {} function backAction():Void {}
         '''+method+'}'}
        self.run_haxe('''var child=new Menu();child.update(1/60);check(child.calls==0,'parent Accept reached child');
         flixel.FlxG.game.inputFrame++;child.update(1/60);check(child.calls==1,'later Accept blocked');''',files)

    def test_global_library_uses_registry_references_without_duplicates(self):
        self.run_haxe(r'''
 var a:Dynamic={name:'shared',week:1,character:'bf',display:'A'};
 var b:Dynamic={name:'shared--another-0123456789',week:2,character:'bf',display:'A'};
 var categories:Array<Dynamic>=[{name:'All',songs:[{name:'Random-Song'}]},
  {name:'Base Game',songs:[a]}, {name:'Imported',songs:[a,b,'third']}, {name:'User category',songs:[b]}];
 var before=haxe.Json.stringify(categories);var rows=FreeplayLibraryView.songs(categories);
 check(rows.length==3,'global view duplicated registry references');
 check(rows.indexOf(a)>=0 && rows.indexOf(b)>=0,'same title merged owners or records copied');
 check(haxe.Json.stringify(categories)==before,'global view changed registry');
 var empty=FreeplayLibraryView.songs([]);check(empty.length==1 && empty[0].name=='Random-Song','empty view scaffold');
 var allOnly=FreeplayLibraryView.songs([{name:'All',songs:[a]}]);check(allOnly.length==1 && allOnly[0]==a,'single All registry lost content');
 ''',{'FreeplaySongOrder.hx':'class FreeplaySongOrder {public static function sort(entries:Array<Dynamic>, retainOrder:Bool = false):Array<Dynamic> return [for(e in entries)e.song];} typedef FreeplaySongEntry={var song:Dynamic;var base:Bool;var order:Int;}'})

    def test_difficulty_names_survive_reordering_without_selecting_missing_charts(self):
        self.run_haxe(r'''
 var exists=function(i:Int)return i!=2;
 check(LibraryDifficultyPreference.resolve('hard',0,[0,1],['NORMAL','HARD'],[],exists)==1,'saved difficulty');
 check(LibraryDifficultyPreference.resolve('hard',1,[0,1],['HARD','NORMAL'],[],exists)==0,'index reorder');
 check(LibraryDifficultyPreference.resolve('HARD',0,[0],['NORMAL','HARD'],[],exists)==0,'unsupported selected');
 check(LibraryDifficultyPreference.resolve('HARD',0,[0,2],['NORMAL','EASY','HARD'],[],exists)==0,'missing file selected');
 check(LibraryDifficultyPreference.resolve('HARD',0,[0,1],['NORMAL','HARD'],['NORMAL'],exists)==0,'source order bypass');
 check(LibraryDifficultyPreference.resolve('removed',1,[0,1],['NORMAL','HARD'],[],exists)==1,'removed name selected default index zero');
 check(LibraryDifficultyPreference.resolve('hard',0,[1,2],['NORMAL','HARD','hard'],[],function(_)return true)==0,'ambiguous name selected');
 ''')

    def test_clearing_empty_filter_restores_selected_difficulty_details(self):
        source=(ROOT/'source/FreeplayState.hx').read_text()
        method=extract_method(source,'function applySearchFilter(')
        selection=extract_method(source,'public static function nextVisibleSelection(')
        files={'View.hx':'''class View {
         var searchFocused=false;var searchInput:Dynamic=null;public var searchString='missing';var searchText={text:'',alpha:1.0};var favoritesOnly=false;var soundTest=false;
         var libraryViewId='';var categoryFilters:Array<String>=[];var curSelected=0;
         public var denseBrowser=false; function updateBrowserDetails():Void {}
         public var scoreText={visible:true};public var infoPanel={visible:true};public var diffText={text:'HARD'};
         var previewTimer=0.0;public var changes=0;
         public function new(){} function anyVisible():Bool return searchString=='';
         function songMatches(i:Int):Bool return anyVisible();function rebuildVisibleRows():Void {} function rebuildIconQueue():Void {}
         var songs=[0];function orderedVisibleSongs():Array<Int> return anyVisible() ? [0] : [];
         function changeSelection(change:Int=0,refreshOnly:Bool=false):Void {
          if(!refreshOnly)curSelected=nextVisibleSelection(curSelected,change,songs.length,songMatches);
         }
         function stopPreviewSound():Void {}
         function changeDiff():Void {changes++;diffText.text='HARD';infoPanel.visible=true;}
         public function apply():Void applySearchFilter();
        '''+method+selection+'}'}
        self.run_haxe('''var view=new View();view.apply();check(view.diffText.text=='NO MATCHING SONGS' && !view.scoreText.visible,'empty details');
         view.searchString='';view.apply();check(view.diffText.text=='HARD' && view.scoreText.visible && view.infoPanel.visible,'restored details');
         view.apply();check(view.changes==1,'unchanged filter repeated difficulty work');''',files)
