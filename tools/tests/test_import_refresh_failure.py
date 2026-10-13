"""A failed outdated-import refresh is remembered instead of repeated every launch."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT = Path(__file__).resolve().parents[2]


class ImportRefreshFailureTest(unittest.TestCase):
    def test_marker_lifecycle_and_engine_mismatch(self):
        body = r"""class Main {
 static function check(ok:Bool, m:String) { if (!ok) throw m; }
 static function main() {
  var record:Dynamic = {id:'a', snapshotId:'snap', engines:['Nightmare Vision'], label:'pack',
   revisions:[{sourceEngine:'Nightmare Vision', commonRevision:3, engineRevision:16, schemaVersion:1}]};
  var print = ImportRefreshFailure.fingerprint(record, '1.0');
  check(print == ImportRefreshFailure.fingerprint(haxe.Json.parse(haxe.Json.stringify(record)), '1.0'), 'fingerprint unstable');
  check(print != ImportRefreshFailure.fingerprint(record, '1.1'), 'new application version must allow a retry');
  record.snapshotId = 'other'; check(print != ImportRefreshFailure.fingerprint(record, '1.0'), 'new snapshot must allow a retry');
  record.snapshotId = 'snap'; record.revisions[0].commonRevision = 4;
  check(print != ImportRefreshFailure.fingerprint(record, '1.0'), 'changed receipt must allow a retry');
  record.revisions[0].commonRevision = 3;

  check(!ImportRefreshFailure.blocks(null, print), 'no marker blocked');
  var first = ImportRefreshFailure.next(null, 'a', print, 'disk was busy', false);
  check(first.attempts == 1 && !first.permanent && !ImportRefreshFailure.blocks(first, print), 'one ordinary failure must still retry');
  var second = ImportRefreshFailure.next(first, 'a', print, 'disk was busy', false);
  check(second.attempts == 2 && ImportRefreshFailure.blocks(second, print), 'repeated failure not remembered');
  check(!ImportRefreshFailure.blocks(second, print + 'x'), 'stale marker blocked a changed importer');
  var restarted = ImportRefreshFailure.next(second, 'a', print + 'x', 'again', false);
  check(restarted.attempts == 1 && !ImportRefreshFailure.blocks(restarted, print + 'x'), 'attempts carried across fingerprints');
  var proven = ImportRefreshFailure.next(null, 'a', print, ImportRefreshFailure.MISTYPED_PREFIX + 'x', true);
  check(proven.attempts == 1 && ImportRefreshFailure.blocks(proven, print), 'proven cause retried');
  check(ImportRefreshFailure.next(proven, 'a', print, 'later', false).permanent, 'permanence lost');

  var stored = ImportRefreshFailure.read(haxe.Json.stringify(second), 'a');
  check(stored != null && stored.attempts == 2 && stored.fingerprint == print && stored.reason == 'disk was busy', 'roundtrip');
  check(ImportRefreshFailure.read(haxe.Json.stringify(second), 'b') == null, 'marker accepted for another record');
  for (bad in ['', 'nope', '[]', '{"version":1,"id":"a"}', '{"version":9,"id":"a","fingerprint":"x","attempts":2,"reason":"r"}',
   '{"version":1,"id":"a","fingerprint":"x","attempts":0,"reason":"r"}', '{"version":1,"id":"a","fingerprint":5,"attempts":2,"reason":"r"}'])
   check(ImportRefreshFailure.read(bad, 'a') == null, 'malformed marker accepted: ' + bad);
  check(ImportRefreshFailure.read(null, 'a') == null, 'null marker');

  var noisy = [for (i in 0...4000) '[source-mapped-assets] the same line'].join('\n');
  var folded = ImportRefreshFailure.next(null, 'a', print, noisy, false);
  check(folded.reason == '[source-mapped-assets] the same line (x4000)', 'repeated diagnostics stored unfolded');
  check(ImportRefreshFailure.bounded([for (i in 0...50) 'line ' + i + ' ' + [for (j in 0...40) 'word'].join(' ')].join('\n')).length <= ImportRefreshFailure.MAX_REASON, 'reason unbounded');
  var text = ImportRefreshFailure.message(second, 'pack');
  check(text.indexOf('"pack"') > 0 && text.indexOf('disk was busy') > 0 && text.indexOf('import the original package again') > 0, 'message');

  var proof = ['Psych Engine executable marker: Psych Lua/version runtime'];
  var found = ImportRefreshFailure.mismatch('bin', 'Nightmare Vision', 'Nightmare Vision', [], 'Psych Engine', proof);
  check(found != null && found.recorded == 'Nightmare Vision' && found.detected == 'Psych Engine' && found.relative == 'bin' && found.evidence == proof[0], 'forced wrong engine not detected');
  check(ImportRefreshFailure.mismatch('bin', 'Nightmare Vision', 'Nightmare Vision', null, 'psych', proof) != null, 'missing evidence field or alias');
  check(ImportRefreshFailure.mismatch('bin', 'Auto', 'Nightmare Vision', [], 'Psych Engine', proof) == null, 'automatic detection overridden');
  check(ImportRefreshFailure.mismatch('bin', 'Nightmare Vision', 'Nightmare Vision', ['Nightmare Vision executable package marker'], 'Psych Engine', proof) == null, 'recorded evidence overridden');
  check(ImportRefreshFailure.mismatch('bin', 'Nightmare Vision', 'Nightmare Vision', [], 'Psych Engine', ['pack.json present', 'Lua scripts']) == null, 'layout hints overrode an explicit choice');
  check(ImportRefreshFailure.mismatch('bin', 'Nightmare Vision', 'Nightmare Vision', [], 'Nightmare Vision', proof) == null, 'same engine reported');
  check(ImportRefreshFailure.mismatch('bin', 'Nightmare Vision', 'Nightmare Vision', [], '', proof) == null && ImportRefreshFailure.mismatch('bin', 'Nightmare Vision', 'Nightmare Vision', [], 'Psych Engine', null) == null, 'unknown detection reported');
  var alone = ImportRefreshFailure.mistyped(found, null); var copy = ImportRefreshFailure.mistyped(found, 'pack');
  check(ImportRefreshFailure.isMistyped(alone) && ImportRefreshFailure.isMistyped(copy) && !ImportRefreshFailure.isMistyped('other') && !ImportRefreshFailure.isMistyped(null), 'prefix');
  check(alone.indexOf('imported as Nightmare Vision') > 0 && alone.indexOf('bin is Psych Engine') > 0 && alone.indexOf('Auto detection') > 0, 'explanation');
  check(copy.indexOf('already installed') > 0 && copy.indexOf('"pack"') > 0, 'duplicate not named');
 }
}"""
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            (Path(temp) / 'Main.hx').write_text(body, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', temp, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manager_consults_and_maintains_the_marker(self):
        manager = (ROOT / 'source/ImportRefreshManager.hx').read_text(encoding='utf-8')
        queue = manager[manager.index('\tstatic function loadQueue('):manager.index('\tstatic function stageCommittedRoots(')]
        blocked = queue.index('ImportRefreshFailure.blocks(knownFailure')
        self.assertLess(queue.index('if (assessment.status == ImportRevision.OUTDATED) stale = true;'), blocked)
        self.assertLess(blocked, queue.index('queue.push(record);'))
        start = manager[manager.index('\tstatic function startNext('):manager.index('\tstatic function isRegistry(')]
        fingerprint = start.index('var failureFingerprint = ImportRefreshFailure.fingerprint(record')
        regenerate = start.index('regenerate(install,record,ImportWorkflow.convertRetainedSource')
        self.assertLess(fingerprint, regenerate)
        self.assertLess(regenerate, start.index('clearRefreshFailure(install, Std.string(record.id));'))
        self.assertLess(start.index('settleFailedReservation(token, install);'),
                        start.index('rememberRefreshFailure(install, record, failureFingerprint'))
        remember = manager[manager.index('\tstatic function rememberRefreshFailure('):manager.index('\tstatic function startNext(')]
        self.assertIn('retainedEngineMismatch(install, record)', remember)
        self.assertIn('mismatch != null)', remember)
        detect = manager[manager.index('\tstatic function retainedEngineMismatch('):manager.index('\tstatic function correctlyTypedCopy(')]
        self.assertLess(detect.index('ImportRootScanner.setRetainedSourceEngines(null)'), detect.index('ImportRootScanner.inspectRoot('))
        self.assertLess(detect.index('ImportRootScanner.inspectRoot('), detect.index('ImportRootScanner.setRetainedSourceEngines(previousEngines)'))


if __name__ == '__main__':
    unittest.main()
