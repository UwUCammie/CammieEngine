"""Foreground progress retires without consuming status or warning evidence."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


class ImportRefreshNotificationLifecycleTest(unittest.TestCase):
    def run_haxe(self, source):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            main = Path(directory) / 'Main.hx'
            main.write_text(source, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', directory, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-5000:])

    def test_actual_coordinator_status_and_diagnostic_snapshots_are_idempotent(self):
        source = (ROOT / 'source/ImportRefreshManager.hx').read_text(encoding='utf-8')
        methods = '\n'.join(method(source, marker) for marker in [
            'public static function browseTick(', 'public static function diagnostics(',
            'public static function diagnosticCount(', 'public static function reportFailure(',
            'static function recordDiagnosticLocked('])
        self.run_haxe('''typedef ImportRefreshBrowseStatus={var busy:Bool;@:optional var backgroundBusy:Bool;var label:String;var fraction:Float;var complete:Bool;var changed:Bool;var blocked:Bool;}
class ModuleFunctions {
 public static var calls=0;public static var failure:Dynamic;
 public static function completeImportOnMainThread(names:Array<String>):Void {calls++;if(failure!=null)throw failure;}
}
class Main {
 static var mutex=new sys.thread.Mutex();static var checked=true;static var active=false;
 static var inspectionPending=false;static var queue:Array<Dynamic>=[];static var measurements:Dynamic=null;
 static var pendingHandoffs:Array<String>=[];
 static var handedOff=false;static var pendingHandoff=false;static var completedNames:Array<String>=[];
 static var generation=0;static var diagnosticMessages:Array<String>=[];
 static var status:ImportRefreshBrowseStatus={busy:false,label:"Imports refreshed.",fraction:1,complete:true,changed:true,blocked:false};
 // Filesystem/thread startup is an explicit boundary; transaction tests cover it.
 static function ensureQueueInspection():Void {}
 static function startQueueInspection():Void {active=true;status.busy=true;}
 static function startNext():Void {queue.shift();active=true;status.busy=true;}
 static function performPendingHandoffs():Void {
  if(active||!pendingHandoff)return;
  try ModuleFunctions.completeImportOnMainThread(completedNames) catch(error:Dynamic) {
   recordDiagnosticLocked(Std.string(error));return;
  }
  pendingHandoff=false;if(pendingHandoffs.length>0)pendingHandoffs.shift();generation++;
 }
 ''' + methods + '''
 static function ok(v:Bool,m:String):Void {if(!v)throw m;}
 static function main(){
  var first=browseTick(),second=browseTick();
  ok(first.complete&&second.complete&&first.changed&&second.changed&&!first.busy&&!second.busy,"multiple consumers retain terminal status");
  pendingHandoff=true;pendingHandoffs=["manual"];completedNames=["updated"];handedOff=false;
  var handed=browseTick();ok(!handed.busy&&handed.backgroundBusy==false&&generation==1&&ModuleFunctions.calls==1&&!pendingHandoff,"handoff finishes before returning idle");
  var again=browseTick();ok(again.complete&&again.changed&&ModuleFunctions.calls==1,"next screen cannot repeat handoff or consume terminal fields");
  reportFailure("Local registry edits preserved: assets/data/example.json /record");
  var copy=diagnostics();copy[0]="mutated";copy.push("foreign");
  ok(diagnosticCount()==1&&diagnostics()[0].indexOf("Local registry edits preserved:")==0,"unshortened warning record retained independently");
  var blocked=browseTick();ok(blocked.blocked&&!blocked.busy&&blocked.label==diagnostics()[0],"idle warning still inspectable without popup policy");
  reportFailure(diagnostics()[0]);ok(diagnosticCount()==1,"same repeated failure is not unbounded duplicate text");
  active=true;status.busy=false;
  var manual=browseTick();ok(manual.busy&&manual.backgroundBusy==false,"manual import still gates navigation but uses own job UI");
  status.busy=true;var background=browseTick();ok(background.busy&&background.backgroundBusy==true,"actual background progress is distinguishable");
  status.busy=false;active=false;queue=[{record:true}];var queued=browseTick();ok(queued.busy&&queued.backgroundBusy==true,"queued background work starts same progress route");
  status.busy=false;active=true;pendingHandoff=true;pendingHandoffs=["manual"];
  var pending=browseTick();ok(pending.busy&&pending.backgroundBusy==true&&pendingHandoff,"active worker cannot hand off early");
  active=false;handedOff=false;ModuleFunctions.failure="handoff failed";
  var failedHandoff=browseTick();
  ok(failedHandoff.busy&&failedHandoff.backgroundBusy==true&&diagnostics()[1]=="handoff failed"&&generation==1,
   "handoff error remains attributable, pending, and does not advance generation");
 }
}''')

    def test_actual_import_settings_wraps_full_refresh_warnings_without_scan(self):
        source = (ROOT / 'source/ImportSettingsState.hx').read_text(encoding='utf-8')
        wrapped = method(source, 'function wrappedDetailLines(')
        wrap = method(source, 'static function wrapDetailLine(')
        self.run_haxe('''class ImportRefreshManager {
 public static var warnings:Array<String>=[];
 public static function diagnostics():Array<String> return warnings.copy();
}
class Main {
 var detailLines:Array<String>=[];
 function detailCharsPerLine():Int return 28;
 public function new(){}
 ''' + wrapped + wrap + '''
 static function ok(v:Bool,m:String):Void {if(!v)throw m;}
 static function main(){
  var ui=new Main();
  var warning="Local registry edits preserved: assets/data/a/very-long-registry-name.json /owner/song/path";
  ImportRefreshManager.warnings=[warning];
  var lines=ui.wrappedDetailLines();var compact=StringTools.replace(lines.join("")," ","");
  ok(compact.indexOf(StringTools.replace(warning," ",""))>=0,"full warning accessible before any scan, without truncation");
  for(line in lines)ok(line.length<=28,"warning obeys visual page line width");
  ui.detailLines=["Existing scan diagnostic"];
  var again=ui.wrappedDetailLines();
  ok(again[again.length-1]=="Existing scan diagnostic"&&ImportRefreshManager.warnings[0]==warning,"scan diagnostics and stored warning retained independently");
 }
}''')
        self.assertIn('ImportRefreshManager.diagnosticCount()', source)
        for name in ['MainMenuState.hx', 'FreeplayState.hx', 'SaveDataState.hx']:
            caller = (ROOT / 'source' / name).read_text(encoding='utf-8')
            self.assertIn('new ImportRefreshProgressBar(this)', caller)
        importer = (ROOT / 'source/ImportSettingsState.hx').read_text(encoding='utf-8')
        self.assertIn('new ImportRefreshProgressBar(this, progressPresentationStatus, true)', importer)

    def test_back_leaves_while_automatic_work_continues(self):
        source = (ROOT / 'source/ImportSettingsState.hx').read_text(encoding='utf-8')
        leave_state = method(source, 'function leaveState(')
        detach_import = method(source, 'function detachImportAndLeave(')
        coordinator_busy = method(source, 'function coordinatorWorkBusy(')
        update = method(source, 'override function update(')
        retry = update.rfind('if (backRequested) {')
        self.assertGreater(retry, update.index('if (hasJobHandle())'))
        self.assertLess(retry, update.rfind('if (controls.BACK'))
        self.run_haxe('''
class ImportRefreshManager {
 public static var busy=false;
 public static function browseTick():Dynamic return {busy:busy};
}
class SaveDataState { public function new() {} }
class LoadingState {
 public static var loads=0;
 public static function loadAndSwitchState(state:Dynamic):Void loads++;
}
class Main {
 var scanJob:Dynamic=null;var importJob:Dynamic=null;var active=false;
 var progressPresentation:Dynamic=null;var workerRunning=false;
 var backRequested=false;var buttonRefreshes=0;var cancelCalls=0;
 public function new() {}
 function hasJobHandle():Bool return scanJob!=null||importJob!=null;
 function hasActiveJob():Bool return active;
 function cancelActiveJob():Void cancelCalls++;
 function refreshButtons():Void buttonRefreshes++;
 ''' + coordinator_busy + leave_state + detach_import + '''
 static function ok(value:Bool,message:String):Void if(!value)throw message;
 static function main(){
  var ui=new Main();ui.backRequested=true;ImportRefreshManager.busy=true;
  ui.leaveState();
  ok(LoadingState.loads==1&&!ui.backRequested,
   "Back did not leave Import Settings while automatic work continues");
  ImportRefreshManager.busy=false;ui.leaveState();
  ok(LoadingState.loads==2,
   "Back failed after automatic refresh became idle");
  ui.active=true;ui.leaveState();
  ok(LoadingState.loads==2&&ui.cancelCalls==1,
   "Back with an active manual job did not request safe cancellation");
  ui.active=false;ui.importJob={handle:true};ui.workerRunning=true;ui.leaveState();
  ok(LoadingState.loads==3&&ui.importJob==null&&ui.workerRunning&&ui.cancelCalls==1,
   "Back should hide Import Settings while manager-owned import work continues");
 }
}''')


if __name__ == '__main__':
    unittest.main()
