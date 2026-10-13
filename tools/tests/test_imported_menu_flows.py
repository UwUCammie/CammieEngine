"""Supported imported entry contracts and partial-menu choices use real planners."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method
ROOT = Path(__file__).resolve().parents[2]

class ImportedMenuFlowsTest(unittest.TestCase):
    def run_haxe(self, work, code):
        (work / 'Main.hx').write_text(code, encoding='utf-8')
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work), '-main', 'Main', '--interp'], cwd=work, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_codename_partial_menu_and_ambiguity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory)
            root=work/'owner'
            root.mkdir()
            for name,body in {'TitleState':'FlxG.switchState(new MainMenuState());','MainMenuState':'FlxG.switchState(new FreeplayState());','FreeplayState':'function create() {}'}.items():
                (root/(name+'.hx')).write_text(body)
            self.run_haxe(work, r'''class Main {static function main() {
 var states=['TitleState.hx','MainMenuState.hx','FreeplayState.hx'];
 if(CodenameModEntryPoint.find('owner',states)!='TitleState.hx')throw 'full flow';
 if(CodenameModEntryPoint.find('owner',['TitleState.hx','FreeplayState.hx'])!='')throw 'standalone title';
 if(CodenameModEntryPoint.find('owner',['MainMenuState.hx'])!='MainMenuState.hx')throw 'main-only fallback';
 sys.FileSystem.createDirectory('owner/other'); sys.io.File.saveContent('owner/other/TitleState.hx','FlxG.switchState(new MainMenuState());');
 states.push('other/TitleState.hx');
 if(CodenameModEntryPoint.find('owner',states)!='')throw 'ambiguous title';
}}''')

    def test_nv_explicit_registration_partial_and_ambiguity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory)
            root=work/'assets/imported_mods/a'
            (root/'scripts/states').mkdir(parents=True)
            for name in ['Title','Main','Freeplay']:
                (root/'scripts/states'/(name+'.hx')).write_text('function onCreate() {}')
            (root/'meta.json').write_text(json.dumps({'stateRedirects':{'TitleState':'Title','MainMenuState':'Main','FreeplayState':'Freeplay'}}))
            self.run_haxe(work, r'''class Main {static function main() {
 var root='assets/imported_mods/a';
 var result=ImportedNightmareMenuPlan.find(root,'a');
 if(result.state!='TitleState'||result.diagnostic!='')throw 'registered full flow';
 sys.io.File.saveContent(root+'/meta.json','{"stateRedirects":{"TitleState":"Title"}}');
 if(ImportedNightmareMenuPlan.find(root,'a').state!='')throw 'standalone title';
 sys.io.File.saveContent(root+'/meta.json','{"stateRedirects":{"MainMenuState":"Main"}}');
 if(ImportedNightmareMenuPlan.find(root,'a').state!='MainMenuState')throw 'main-only';
 sys.io.File.saveContent(root+'/scripts/states/Main.hscript','function onCreate() {}');
 result=ImportedNightmareMenuPlan.find(root,'a');
 if(result.state!=''||result.diagnostic.indexOf('matching scripts')<0)throw 'ambiguous registration';
}}''')

    def test_psych_source_contract_full_partial_and_unsupported(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory)
            root=work/'owner/scripts/states'
            root.mkdir(parents=True)
            for name,target in [('TitleState','MainMenuState'),('MainMenuState','FreeplayState'),('FreeplayState','PlayState')]:
                (root/(name+'.hx')).write_text('class '+name+' extends MusicBeatState {override function create():Void {super.create();} override function update(elapsed:Float):Void {if (controls.ACCEPT) FlxG.switchState(new '+target+'());super.update(elapsed);}}')
            self.run_haxe(work, r'''class Main {static function main() {
 var result=ImportedPsychMenuPlan.find('owner');
 if(result.state!='TitleState'||result.sources.length!=3)throw result.diagnostic;
 sys.io.File.saveContent('owner/scripts/states/TitleState.hx',"class TitleState extends MusicBeatState {override function create():Void {trace('Press accept (enter)'); /* unavailableApi() */ super.create();}}");
 result=ImportedPsychMenuPlan.find('owner');
 if(result.state!='TitleState'||result.diagnostic!='')throw 'label/comment mistaken for call: '+result.diagnostic;

 sys.FileSystem.deleteFile('owner/scripts/states/MainMenuState.hx');
 if(ImportedPsychMenuPlan.find('owner').state!='')throw 'standalone compiled title';
 sys.io.File.saveContent('owner/scripts/states/MainMenuState.hx','class MainMenuState extends MusicBeatState {override function update(elapsed:Float):Void {unsupportedDonorApi();}}');
 result=ImportedPsychMenuPlan.find('owner');
 if(result.state!=''||result.diagnostic=='')throw 'unsupported silently claimed';
}}''')

    def test_gameplay_uses_shared_owner_provider_and_chart_readiness(self):
        source=(ROOT/'source/ImportedMenuEntry.hx').read_text()
        method=extract_method(source,'public static function gameplayUnavailableReason(')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory)
            (work/'ImportRefreshManager.hx').write_text('class ImportRefreshManager {public static var snapshot:ImportRefreshAvailabilitySnapshot;public static function availabilitySnapshot():ImportRefreshAvailabilitySnapshot return snapshot;}')
            self.run_haxe(work, 'class Main {static function requiredOwnerRoots(owner:String):Array<String> return [owner,"assets/imported_mods/provider"];'+method+r'''static function main(){
 var owner="assets/imported_mods/a"; var provider="assets/imported_mods/provider";
 var snapshot:ImportRefreshAvailabilitySnapshot={revision:1,inspectionPending:false,refreshInProgress:false,pendingOwnerRoots:[],handoffPendingOwnerRoots:[],committedOwnerRoots:[owner,provider],pendingTouchedPaths:[],pendingSongs:[]};
 ImportRefreshManager.snapshot=snapshot;
 if(gameplayUnavailableReason(owner,"song")!="")throw "ready gameplay rejected";
 for(root in [owner,provider]){
 snapshot.pendingOwnerRoots=[root];if(gameplayUnavailableReason(owner,"song")=="")throw "pending owner/provider allowed";
 snapshot.pendingOwnerRoots=[];snapshot.handoffPendingOwnerRoots=[root];if(gameplayUnavailableReason(owner,"song")=="")throw "handoff owner/provider allowed";
 snapshot.handoffPendingOwnerRoots=[];
 }
 snapshot.inspectionPending=true;if(gameplayUnavailableReason(owner,"song")=="")throw "unknown inspection allowed";
 snapshot.inspectionPending=false;snapshot.pendingTouchedPaths=["assets/data/song/chart.json"];
 if(gameplayUnavailableReason(owner,"song")=="")throw "chart publication overlap allowed";
 }}''')
