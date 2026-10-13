"""Asynchronous removal manager keeps importer leases through publication/recovery."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT = Path(__file__).resolve().parents[2]

class ImportRemovalManagerTest(unittest.TestCase):
    def test_worker_and_main_thread_reservation_handoff(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            for name in ('ImportRemovalManager', 'LibraryRemovalPresentation', 'BundledImportOwnership'):
                (work/(name+'.hx')).write_text((ROOT/'source'/(name+'.hx')).read_text(),encoding='utf-8')
            files={'LibraryPackageLabel.hx':'class LibraryPackageLabel {public static function caption(owner:String,title:String):String return title;}',
              'ImportRemovalPlan.hx': '''class ImportRemovalPlan {
 public var selectedOwners=['assets/imported_mods/alpha'];public var affectedOwners=['assets/imported_mods/alpha'];public var blockers:Array<String>=[];
 public var inventoryComplete=true;public var candidateFiles=[1];public var sharedFiles=[];public var candidateSnapshots=[];public var sharedSnapshots=[];public var registryPaths=[];
 public function new(){}
}''',
              'ImportRemovalTransaction.hx': '''typedef ImportRemovalResult={var status:String;var blockers:Array<String>;var affectedOwners:Array<String>;var transactionId:String;}
 class ImportRemovalTransaction {
 public static var mode='cancel';public static var recoveryError=false;
 public static function recover(root:String):Array<String>{Sys.sleep(.02);return recoveryError?['locked rollback']:[];}
 public static function preview(root:String, owners:Array<String>,protected:Array<String>,active:Array<String>,cancel:Void->Bool):ImportRemovalPlan {
 Sys.sleep(.02);var plan=new ImportRemovalPlan();for(owner in active)if(plan.affectedOwners.contains(owner))plan.blockers.push('active');return plan;
 }
 public static function apply(root:String, plan:ImportRemovalPlan,protected:Array<String>,cancel:Void->Bool,progress:Dynamic->Void):ImportRemovalResult {
 var until=Sys.time()+.1;while(Sys.time()<until&&!cancel())Sys.sleep(.001);
 return {status:cancel()?'cancelled':mode,blockers:mode=='conflict'?['rollback blocked']:[],affectedOwners:plan.affectedOwners,transactionId:'txn-1'};
 }}''',
              'ImportRefreshManager.hx': '''class ImportRefreshManager {
 public static var reserved=false;public static var importerBusy=false;public static var releases=0;public static var commits=0;
 public static function reserveRemovalRecovery():String{if(reserved||importerBusy)return '';reserved=true;return 'token';}
 public static function reserveForRemoval(plan:ImportRemovalPlan):String return reserveRemovalRecovery();
 public static function removalActiveOwners():Array<String> return [];
 public static function finishRemovalReservation(token:String, roots:Array<String>,committed:Bool):Void{if(token!='token'||!reserved)throw 'lease';reserved=false;releases++;if(committed)commits++;}
}''',
              'ImportedMenuEntry.hx': '''class ImportedMenuEntry {public static var roots:Array<String>=[];public static function activeOwnerRoots():Array<String>return roots.copy();}''',
              'ImportWorkScheduler.hx': '''class ImportWorkScheduler {public static var playing=false;public static function gameplayActive():Bool return playing;}''',
              'PlayState.hx':'class PlayState {public function new(){}}',
              'LoadingState.hx':'class LoadingState {public function new(){}}',
              'flixel/FlxG.hx':'package flixel;class FlxG {public static var state:Dynamic;}',
              'Main.hx': '''class Main {
 static function check(ok:Bool,why:String):Void if(!ok)throw why;
 static function wait():ImportRemovalManager.ImportRemovalStatus {var until=Sys.time()+2.;var status=ImportRemovalManager.poll();while(status.busy&&Sys.time()<until){Sys.sleep(.001);status=ImportRemovalManager.poll();}check(!status.busy,'worker stuck');return status;}
 static function preview():Void {check(ImportRemovalManager.beginPreview('assets/imported_mods/alpha'),'preview denied');check(!ImportRemovalManager.confirm(),'confirmed unvalidated preview');check(wait().phase=='preview','preview failed');}
 static function main(){
 ImportRemovalManager.install();check(ImportRefreshManager.reserved,'startup recovery unreserved');check(!ImportRemovalManager.beginPreview('assets/imported_mods/alpha'),'preview raced recovery');wait();check(!ImportRefreshManager.reserved,'startup lease retained');
 check(!ImportRemovalManager.beginPreview(BundledImportOwnership.RESULTS_ROOT),'host namespace accepted');
 preview();ImportedMenuEntry.roots=['assets/imported_mods/alpha'];check(!ImportRemovalManager.confirm(),'active lease ignored');ImportedMenuEntry.roots=[];
 preview();check(ImportRemovalManager.confirm()&&ImportRefreshManager.reserved,'confirmation unreserved');ImportRemovalManager.cancel();var cancelled=wait();check(cancelled.phase=='cancelled'&&!cancelled.published&&!ImportRefreshManager.reserved,'cancel not rolled back before release');
 ImportRemovalTransaction.mode='applied';preview();check(ImportRemovalManager.confirm(),'apply denied');var complete=wait();check(complete.phase=='complete'&&complete.published&&!ImportRefreshManager.reserved,'applied not handed off');
 ImportRemovalTransaction.mode='cleanup-pending';preview();ImportRemovalManager.confirm();check(wait().phase=='cleanup-pending','cleanup status lost');ImportRefreshManager.importerBusy=true;check(!ImportRemovalManager.retryCleanup(),'cleanup raced importer');check(ImportRemovalManager.poll().phase=='cleanup-pending','busy importer lost pending cleanup retry');ImportRefreshManager.importerBusy=false;check(ImportRemovalManager.retryCleanup(),'cleanup retry denied');check(wait().phase=='complete','cleanup retry failed');
 ImportRemovalTransaction.mode='conflict';preview();ImportRemovalManager.confirm();var conflict=wait();check(conflict.phase=='conflict'&&!conflict.published&&ImportRefreshManager.reserved,'unsafe conflict released');
 ImportRemovalTransaction.recoveryError=true;check(ImportRemovalManager.retryCleanup(),'rollback retry denied');wait();check(ImportRefreshManager.reserved,'unresolved recovery released');
 ImportRemovalTransaction.recoveryError=false;check(ImportRemovalManager.retryCleanup(),'second rollback retry denied');wait();check(!ImportRefreshManager.reserved,'restored rollback retained lease');
 ImportWorkScheduler.playing=true;check(!ImportRemovalManager.beginPreview('assets/imported_mods/alpha'),'gameplay removal started');
 Sys.println('worker handoff passed');
 }}''',
            }
            for name,content in files.items():
                path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'--main','Main','--interp'],cwd=work,capture_output=True,text=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('worker handoff passed',result.stdout)

if __name__=='__main__':unittest.main()
