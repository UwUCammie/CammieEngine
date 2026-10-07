"""Exercise Main's state-to-import lease bridge with actual worker gating."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class MainImportWorkSchedulerTest(unittest.TestCase):
    def test_gameplay_replacement_loading_and_menu_release_worker(self):
        source = (ROOT / 'source/Main.hx').read_text(encoding='utf-8')
        start = source.index('static function syncImportForegroundForState(')
        opening = source.index('{', start)
        depth = 1
        end = opening + 1
        while depth:
            if source[end] == '{':
                depth += 1
            elif source[end] == '}':
                depth -= 1
            end += 1
        method = source[start:end]
        self.assertIn('ImportWorkScheduler.bindForegroundThread();', source)
        self.assertIn('syncImportForegroundForState(_state);', source)
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='main-import-scheduler-', dir=TEST_TMP) as folder:
            work = FixturePath(folder)
            (work / 'flixel').mkdir()
            (work / 'flixel/FlxState.hx').write_text(
                'package flixel; class FlxState {public function new(){}}', encoding='utf-8')
            for name in ('PlayState', 'LoadingState', 'MenuState'):
                (work / (name + '.hx')).write_text(
                    f'class {name} extends flixel.FlxState {{public function new(){{super();}}}}', encoding='utf-8')
            (work / 'Main.hx').write_text(
                'import flixel.FlxState; class Main {static var importForegroundLease:Int=0;'
                + method + '}', encoding='utf-8')
            (work / 'MainLeaseFixture.hx').write_text(r'''import sys.thread.Thread;
import sys.thread.Lock;
@:access(Main)
class MainLeaseFixture {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  ImportWorkScheduler.bindForegroundThread();
  Main.syncImportForegroundForState(new PlayState());
  check(ImportWorkScheduler.gameplayActive(),"gameplay must own foreground");
  var begun=new Lock(); var finished=new Lock();
  Thread.create(function() { begun.release(); ImportWorkScheduler.cooperate(); finished.release(); });
  check(begun.wait(2),"worker started");
  check(!finished.wait(0.08),"worker waits during gameplay");
  Main.syncImportForegroundForState(new PlayState());
  check(ImportWorkScheduler.gameplayActive(),"replacement gameplay remains protected");
  check(!finished.wait(0.08),"replacement must not release worker");
  Main.syncImportForegroundForState(new LoadingState());
  check(ImportWorkScheduler.gameplayActive(),"loading remains protected");
  check(!finished.wait(0.08),"loading must not release worker");
  Main.syncImportForegroundForState(new MenuState());
  check(!ImportWorkScheduler.gameplayActive(),"menu clears foreground lease");
  check(finished.wait(2),"worker resumes after return");
  Main.syncImportForegroundForState(new MenuState());
  check(!ImportWorkScheduler.gameplayActive(),"repeated menu transition remains idle");
 }
}''', encoding='utf-8')
            process = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work),
                                      '--run', 'MainLeaseFixture'], cwd=ROOT, capture_output=True,
                                     text=True, timeout=30)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == '__main__':
    unittest.main()
