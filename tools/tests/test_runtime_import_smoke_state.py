"""The native import smoke waits for startup importer inspection before import."""

from __future__ import annotations

from haxe_test_support import HAXE_COMMAND, TEST_TMP

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
HAXE = ROOT / ".tools" / "haxe" / "haxe"


FIXTURE_FILES = {
    "flixel/FlxG.hx": r'''package flixel;
class FlxG {
  public static var autoPause:Bool = true;
  public static var sound:Dynamic = {muted:false};
  public static function switchState(value:Dynamic):Void {}
}
''',
    "flixel/FlxState.hx": r'''package flixel;
class FlxState {
  public function new() {}
  public function create():Void {}
  public function update(elapsed:Float):Void {}
}
''',
    "ImportWorkflow.hx": r'''package;
typedef ImportWorkflowProgress = {
  var complete:Bool;
  var result:Dynamic;
  var error:String;
  @:optional var runtimeCommitted:Bool;
}
class ImportScanJob {
  public static var cancelCalls:Int = 0;
  public function new() {}
  public function snapshot():ImportWorkflowProgress return {
    complete:true,
    result:{songs:[],songsFound:1,songsToImport:1,duplicateSongs:0,missingDependencies:0,errors:[]},
    error:null
  };
  public function isFinished():Bool return true;
  public function cancel():Void cancelCalls++;
}
class ImportImportJob {
  public function new() {}
  public function snapshot():ImportWorkflowProgress return {complete:false,result:null,error:null};
  public function isFinished():Bool return false;
  public function cancel():Void {}
}
class ImportWorkflow {
  public static var beginScanCalls:Int = 0;
  public static var beginImportCalls:Int = 0;
  public static function beginScan(_source:String, _type:String):ImportScanJob {
    beginScanCalls++;
    return new ImportScanJob();
  }
  public static function beginImport(_source:String, _scan:Dynamic, _type:String,
      ?_names:Map<String,String>):ImportImportJob {
    beginImportCalls++;
    return new ImportImportJob();
  }
}
''',
    "ImportRefreshManager.hx": r'''package;
typedef ImportRefreshBrowseStatus = { var busy:Bool; }
class ImportRefreshManager {
  public static var busySequence:Array<Bool> = [];
  public static var calls:Int = 0;
  public static function browseTick():ImportRefreshBrowseStatus {
    var index = calls++;
    var busy = index < busySequence.length ? busySequence[index] : false;
    return {busy:busy};
  }
}
''',
    "PluginManager.hx": "class PluginManager { public static function init():Void {} }\n",
    "DifficultyManager.hx": "class DifficultyManager { public static function init():Void {} }\n",
    "ModifierState.hx": "class ModifierState { public static function init():Void {} }\n",
    "PlayerSettings.hx": "class PlayerSettings { public static function init():Void {} }\n",
    "RuntimeSmokeHarness.hx": r'''class RuntimeSmokeHarness {
  public static function config():Dynamic return {
    chartEditor:false,freeplay:false,freeplayAcceptSong:'',songFolder:'fixture',chart:'fixture-hard'
  };
  public static function getConfigurationError():String return '';
}
''',
    "RuntimeSmokeState.hx": "class RuntimeSmokeState extends flixel.FlxState {}\n",
    "RuntimeSmokeFreeplayState.hx": "class RuntimeSmokeFreeplayState extends flixel.FlxState {}\n",
    "ImportPackageNamePrompt.hx": r'''class ImportPackageNamePrompt {
  public static function collectUnnamedRoots(_songs:Array<Dynamic>):Array<Dynamic> return [];
  public static function validName(_name:String):Bool return true;
  public static function createOverrides(_requests:Array<Dynamic>, _names:Array<String>):Map<String,String>
    return new Map<String,String>();
}
''',
    "RuntimeImportSmokeHarness.hx": r'''class RuntimeImportSmokeHarness {
  public static var options:Dynamic;
  public static var timeout:Bool = false;
  public static var events:Array<String> = [];
  public static function config():Dynamic return options;
  public static function start():Void {}
  public static function expired():Bool return timeout;
  public static function requestTimeoutCancellation():Void events.push('timeout');
  public static function markScanReady(_result:Dynamic):Void events.push('scan_ready');
  public static function finishScan(_result:Dynamic):Void events.push('scan_success');
  public static function markImportStart():Void events.push('import_start');
  public static function finish(_result:Dynamic, _error:Dynamic):Bool return false;
  public static function fail(kind:String, _detail:String):Void events.push('failure:' + kind);
}
''',
}


class RuntimeImportSmokeStateTest(unittest.TestCase):
    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_completed_scan_waits_for_coordinator_and_timeout_wins(self):
        with tempfile.TemporaryDirectory(prefix="runtime-import-smoke-state-", dir=TEST_TMP) as folder:
            work = Path(folder)
            for relative, contents in FIXTURE_FILES.items():
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, encoding="utf-8", newline="\n")
            (work / "RuntimeImportSmokeState.hx").write_text(
                (SOURCE / "RuntimeImportSmokeState.hx").read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )
            (work / "Main.hx").write_text(r'''class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function reset(scanOnly:Bool, busy:Array<Bool>):Void {
    RuntimeImportSmokeHarness.options = {
      source:'fixture-source', importType:'Auto', scanOnly:scanOnly,
      playAfterImport:false, packageName:'', packageNameProvided:false
    };
    RuntimeImportSmokeHarness.timeout = false;
    RuntimeImportSmokeHarness.events = [];
    ImportRefreshManager.busySequence = busy;
    ImportRefreshManager.calls = 0;
    ImportWorkflow.beginScanCalls = 0;
    ImportWorkflow.beginImportCalls = 0;
    ImportWorkflow.ImportScanJob.cancelCalls = 0;
  }
  static function main():Void {
    reset(false,[true,true,false]);
    var waiting = new RuntimeImportSmokeState();
    waiting.create();
    waiting.update(0.016);
    check(RuntimeImportSmokeHarness.events.length == 0
      && ImportWorkflow.beginImportCalls == 0 && ImportRefreshManager.calls == 1,
      'completed scan was published before startup inspection finished');
    waiting.update(0.016);
    check(RuntimeImportSmokeHarness.events.length == 0
      && ImportWorkflow.beginImportCalls == 0 && ImportRefreshManager.calls == 2,
      'completed scan did not remain pending through coordinator work');
    waiting.update(0.016);
    check(RuntimeImportSmokeHarness.events.join(',') == 'scan_ready,import_start'
      && ImportWorkflow.beginImportCalls == 1 && ImportRefreshManager.calls == 3,
      'ready coordinator did not advance the scan/import exactly once');
    waiting.update(0.016);
    check(RuntimeImportSmokeHarness.events.join(',') == 'scan_ready,import_start'
      && ImportWorkflow.beginImportCalls == 1,
      'completed scan emitted duplicate readiness or import markers');

    reset(true,[true]);
    var scanOnly = new RuntimeImportSmokeState();
    scanOnly.create();
    scanOnly.update(0.016);
    check(RuntimeImportSmokeHarness.events.join(',') == 'scan_ready,scan_success'
      && ImportRefreshManager.calls == 0 && ImportWorkflow.beginImportCalls == 0,
      'scan-only unexpectedly waited for importer readiness or started an import');

    reset(false,[true,false]);
    var expiring = new RuntimeImportSmokeState();
    expiring.create();
    expiring.update(0.016);
    check(RuntimeImportSmokeHarness.events.length == 0 && ImportRefreshManager.calls == 1,
      'timeout fixture did not reach the manager wait');
    RuntimeImportSmokeHarness.timeout = true;
    expiring.update(0.016);
    check(RuntimeImportSmokeHarness.events.join(',') == 'timeout,failure:timeout'
      && ImportRefreshManager.calls == 1 && ImportWorkflow.beginImportCalls == 0,
      'timeout did not win while waiting for importer readiness');
  }
}
''', encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--interp", "-main", "Main"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
