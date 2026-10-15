"""Actual confirmation UI and presentation gates, with deterministic worker snapshots."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT = Path(__file__).resolve().parents[2]

class LibraryRemovalUiTest(unittest.TestCase):
    def test_confirmation_defaults_cancellation_and_publication(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            for name in ('LibraryRemovalSubState', 'LibraryRemovalPresentation', 'LibraryActionsSubState', 'BundledImportOwnership'):
                (work / (name + '.hx')).write_text((ROOT / 'source' / (name + '.hx')).read_text(), encoding='utf-8')
            files = {'LibraryPackageLabel.hx':'class LibraryPackageLabel {public static function caption(owner:String,title:String):String return title;}',
                'LibraryMenuSubState.hx': '''package;
 typedef LibraryMenuAction = {var label:String; var run:Void->Void; @:optional var tone:Null<Int>;}
 class LibraryMenuSubState {
 public var actions:Array<LibraryMenuAction>=[]; public var selected:Int=0;
 public var heading:String=''; public var status:flixel.text.FlxText=new flixel.text.FlxText();public var cardTitle:String='';public var cardCaption:String='';public var panelX:Int=0;public var rowsY:Int=0;public static inline var ROW_PITCH:Int=40;public static inline var PANEL_WIDTH:Int=760;
 public var backAction:Void->Void; public var closed:Bool=false; public var cameras:Array<Dynamic>=[];public var closeCallback:Void->Void;public var child:LibraryMenuSubState;
 public function new(){} public function create():Void{} public function add(x:Dynamic):Void{}
 public function close():Void{closed=true;if(closeCallback!=null)closeCallback();}public function openSubState(state:LibraryMenuSubState):Void{child=state;state.create();} public function update(elapsed:Float):Void{}
 public function showActions(title:String, entries:Array<LibraryMenuAction>,reset:Bool=true):Void{heading=title;actions=entries;if(reset)selected=0;}
 }
''',
                'flixel/FlxG.hx': 'package flixel; class FlxG {public static var width=1280;public static var height=720;public static var state:Dynamic;}',
                'flixel/text/FlxText.hx': '''package flixel.text; enum Align {LEFT;}
 class FlxText {public var text:String;public function new(x=0,y=0,w=0,text='',size=0){this.text=text;}public function setFormat(font:String,size:Int,color:Int,align:Align):Void{}}
''',
                'ImportRemovalManager.hx': '''package; typedef StubStatus = {var phase:String;var busy:Bool;var label:String;var plan:Dynamic;var published:Bool;var cancellable:Bool;} class ImportRemovalManager {
 public static var state:StubStatus; public static var canPreview=true; public static var confirms=0;public static var cancels=0;public static var retries=0;
 public static function beginPreview(owner:String):Bool return canPreview;
 public static function poll():StubStatus return state;
 public static function confirm():Bool{confirms++;state.busy=true;state.phase='applying';return true;}
 public static function cancel():Void{cancels++;}
 public static function retryCleanup():Bool{retries++;return true;}
 }
''',
                'UserLibrary.hx': '''class UserLibrary {public static function data():LibraryStubData return new LibraryStubData();public static function change(work:LibraryStubData->Void):Bool{work(data());return true;}}class LibraryStubData {public function new(){}public function isFavorite(key:String):Bool return false;public function setFavorite(key:String,value:Bool):Void{}}''',
                'LibraryCategoriesSubState.hx': '''class LibraryCategoriesSubState extends LibraryMenuSubState {public function new(owner:String,categories:Array<String>,filter:Array<String>->Void){super();}}''',
                'LibraryCollectionsSubState.hx': '''class LibraryCollectionsSubState extends LibraryMenuSubState {public function new(value:String,filter:String->Void){super();}}''',
                'LibrarySortingSubState.hx': '''class LibrarySortingSubState extends LibraryMenuSubState {public function new(){super();}}''',
                'FreeplayState.hx': '''class FreeplayState {public function new(){}}''',
                'ImportedFreeplayCaller.hx': '''class ImportedFreeplayCaller {public static function ownerForFreeplay(value:String):String return '';}''',
                'CodenameModRuntime.hx': '''class CodenameModRuntime {public static function activeRoot():String return '';}''',
                'HxcFreeplayRuntime.hx': '''class HxcFreeplayRuntime {public static function activeOwnerRoots():Array<String> return [];}''',
                'LoadingState.hx': '''class LoadingState {public static var destination:Dynamic;public static function loadAndSwitchState(state:Dynamic):Void{destination=state;}}''',
                'LibraryRemovalState.hx': '''class LibraryRemovalState {public var owner:String;public function new(owner:String,title:String=''){this.owner=owner;}}''',
                'Main.hx': '''package;
 @:access(LibraryRemovalSubState)
 class Main {
 static function check(ok:Bool,why:String):Void if(!ok)throw why;
 static function main(){
 var plan:Dynamic={inventoryComplete:true,affectedOwners:['assets/imported_mods/alpha'],blockers:[],candidateFiles:[1,2],sharedFiles:[1],candidateSnapshots:[1],sharedSnapshots:[],registryPaths:[1]};
 ImportRemovalManager.state={phase:'preview',busy:false,label:'Review',plan:plan,published:false,cancellable:false};
 var publications=0;var ui=new LibraryRemovalSubState('assets/imported_mods/alpha',function()publications++);ui.create();
 check(ui.selected==0&&ui.actions[0].label.indexOf('NO')==0,'destructive default');
 check(ui.actions.length==2&&ui.actions[1].label.indexOf('YES')==0,'confirmation is not a plain yes or no');
 check(ui.actions[0].tone==LibraryRemovalPresentation.NO_COLOR&&ui.actions[1].tone==LibraryRemovalPresentation.YES_COLOR,'yes and no are not coloured');
 check((LibraryRemovalPresentation.NO_COLOR>>8&255)>200&&(LibraryRemovalPresentation.NO_COLOR>>16&255)<120,'keeping is not green');
 check((LibraryRemovalPresentation.YES_COLOR>>16&255)>200&&(LibraryRemovalPresentation.YES_COLOR>>8&255)<120,'removing is not red');
 check(ui.detail.text.indexOf('2 exclusive')>=0&&ui.detail.text.indexOf('1 shared')>=0&&ui.detail.text.indexOf('history are preserved')>=0,'incomplete preview');
 ui.actions[0].run();check(ui.closed&&ImportRemovalManager.confirms==0,'cancel confirmed removal');
 ui=new LibraryRemovalSubState('assets/imported_mods/alpha',function()publications++);ui.create();ui.actions[1].run();
 check(ImportRemovalManager.confirms==1,'confirmation missing');
 ImportRemovalManager.state.cancellable=true;ui.refreshRemoval();ui.backAction();
 check(ImportRemovalManager.cancels==1&&!ui.closed,'active cancel abandoned worker');
 ImportRemovalManager.state.phase='complete';ImportRemovalManager.state.busy=false;ui.refreshRemoval();
 check(publications==0,'success before main thread publication');
 ImportRemovalManager.state.published=true;ui.refreshRemoval();ui.refreshRemoval();check(publications==1,'published callback not exactly once');
 ImportRemovalManager.state.phase='cleanup-pending';ui.refreshRemoval();check(ui.actions[1].label.indexOf('Retry')==0,'pending cleanup cannot retry');
 ui.actions[1].run();check(ImportRemovalManager.retries==1,'retry lost');
 plan.blockers=['Surviving package depends on alpha'];ImportRemovalManager.state.phase='blocked';ImportRemovalManager.state.published=false;
 ui.refreshRemoval();check(ui.actions.length==1&&ui.detail.text.indexOf('Surviving package')>=0,'blocked removal offered confirmation');
 check(!LibraryRemovalPresentation.eligible(BundledImportOwnership.RESULTS_ROOT),'host root removable');
 check(!LibraryRemovalPresentation.eligible('base')&&!LibraryRemovalPresentation.eligible('assets/imported_mods/../other')&&!LibraryRemovalPresentation.eligible('assets/imported_mods/a/b'),'unsafe owner entry');
 ImportRemovalManager.canPreview=false;ImportRemovalManager.state.phase='conflict';var cold=new LibraryRemovalSubState('');cold.create();check(cold.actions.length==2&&cold.actions[1].label.indexOf('Retry')==0,'cold startup recovery inaccessible');cold.selected=1;cold.update(.01);check(cold.selected==1,'cold retry navigation reset each frame');cold.actions[1].run();check(ImportRemovalManager.retries==2,'cold recovery retry missing');
 var priorConfirms=ImportRemovalManager.confirms;var library=new LibraryActionsSubState('',false,function(_){});library.create();var recoveryIndex=-1;for(i in 0...library.actions.length)if(library.actions[i].label=='Recover interrupted mod removal')recoveryIndex=i;check(recoveryIndex>=0,'empty library has no recovery entry');library.actions[recoveryIndex].run();check(Std.isOfType(library.child,LibraryRemovalSubState)&&library.child.actions[1].label.indexOf('Retry')==0,'generic action did not open recovery');check(ImportRemovalManager.confirms==priorConfirms,'generic recovery started new deletion');library.child.actions[0].run();check(!library.closed,'return closed safe native browsing');flixel.FlxG.state=new FreeplayState();library.actions[recoveryIndex].run();check(Std.isOfType(LoadingState.destination,LibraryRemovalState)&&LoadingState.destination.owner=='','global recovery failed to leave owned scopes through neutral state');check(ImportRemovalManager.confirms==priorConfirms,'neutral empty-owner recovery began deletion');
 check(!LibraryRemovalPresentation.confirmable('preview',true,plan),'busy preview confirmable');
 plan.blockers=[];plan.inventoryComplete=false;check(!LibraryRemovalPresentation.confirmable('preview',false,plan),'incomplete inventory confirmable');
 // A removal that takes other mods with it asks a second time and names them.
 var wide:Dynamic={inventoryComplete:true,affectedOwners:['assets/imported_mods/alpha','assets/imported_mods/beta','assets/imported_mods/gamma'],linkedOwners:['assets/imported_mods/beta','assets/imported_mods/gamma'],blockers:[],candidateFiles:[1,2,3],sharedFiles:[],candidateSnapshots:[],sharedSnapshots:[],registryPaths:[]};
 ImportRemovalManager.canPreview=true;ImportRemovalManager.state={phase:'preview',busy:false,label:'Review',plan:wide,published:false,cancellable:false};
 var before=ImportRemovalManager.confirms;var linkedUi=new LibraryRemovalSubState('assets/imported_mods/alpha');linkedUi.create();
 check(linkedUi.heading=='Remove installed mod?','first question missing');
 linkedUi.actions[1].run();
 check(ImportRemovalManager.confirms==before,'linked mods removed after one confirmation');
 check(linkedUi.heading=='Also remove 2 linked mods?'&&linkedUi.selected==0,'second question missing or defaults to removal: '+linkedUi.heading);
 check(linkedUi.actions.length==2&&linkedUi.actions[0].tone==LibraryRemovalPresentation.NO_COLOR&&linkedUi.actions[1].tone==LibraryRemovalPresentation.YES_COLOR,'second question is not coloured');
 check(linkedUi.actions[1].label.indexOf('3 mods')>=0&&linkedUi.detail.text.indexOf('beta')>=0&&linkedUi.detail.text.indexOf('gamma')>=0,'linked mods are not named');
 linkedUi.actions[0].run();check(linkedUi.closed&&ImportRemovalManager.confirms==before,'declining linked mods still removed');
 linkedUi=new LibraryRemovalSubState('assets/imported_mods/alpha');linkedUi.create();linkedUi.actions[1].run();linkedUi.actions[1].run();
 check(ImportRemovalManager.confirms==before+1,'second confirmation did not remove');
 // A removal blocked only because something still holds the packages offers to release them.
 var held:Dynamic={inventoryComplete:true,affectedOwners:['assets/imported_mods/alpha','assets/imported_mods/beta'],linkedOwners:['assets/imported_mods/beta'],blockers:['Package is active or reserved: assets/imported_mods/beta'],candidateFiles:[1],sharedFiles:[],candidateSnapshots:[],sharedSnapshots:[],registryPaths:[]};
 check(LibraryRemovalPresentation.blockedByActiveSession(held)&&!LibraryRemovalPresentation.blockedByActiveSession(wide)&&!LibraryRemovalPresentation.blockedByActiveSession(null),'active session blocker not recognised');
 ImportRemovalManager.state={phase:'blocked',busy:false,label:'held',plan:held,published:false,cancellable:false};
 LoadingState.destination=null;var heldUi=new LibraryRemovalSubState('assets/imported_mods/alpha',null,'Alpha');heldUi.create();
 var release=-1;for(i in 0...heldUi.actions.length)if(heldUi.actions[i].label.indexOf('Close running mod menus')==0)release=i;
 check(heldUi.actions[0].label=='Return'&&release>0,'held packages offer no way to release them');
 check(heldUi.detail.text.indexOf('Close running mod menus')>=0,'blocked text does not say how to release the packages');
 heldUi.actions[release].run();
 check(Std.isOfType(LoadingState.destination,LibraryRemovalState)&&(cast LoadingState.destination:LibraryRemovalState).owner=='assets/imported_mods/alpha','release did not go through the neutral removal state');
 ImportRemovalManager.state.plan={inventoryComplete:true,affectedOwners:['assets/imported_mods/alpha'],blockers:['No committed ownership for assets/imported_mods/alpha.'],candidateFiles:[],sharedFiles:[],candidateSnapshots:[],sharedSnapshots:[],registryPaths:[]};
 var otherUi=new LibraryRemovalSubState('assets/imported_mods/alpha');otherUi.create();
 for(action in otherUi.actions)check(action.label.indexOf('Close running')<0,'unrelated blocker offered a session release');
 Sys.println('confirmation contracts passed');
 }}
''',
            }
            for name, content in files.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '--main', 'Main', '--interp'], cwd=work, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('confirmation contracts passed', result.stdout)

if __name__ == '__main__':
    unittest.main()
