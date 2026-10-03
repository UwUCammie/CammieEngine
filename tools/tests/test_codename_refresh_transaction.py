"""Exercise refresh transaction failures using isolated locks and real files."""
import base64
import copy
from tools import file_lock as fcntl
import importlib.util
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('codename_refresh_transaction', ROOT / 'tools/refresh_codename_events.py')
REFRESH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REFRESH)


class CodenameRefreshTransactionTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        self.addCleanup(self.scratch.cleanup)
        self.work = Path(self.scratch.name)
        (self.work / '.tools').mkdir()
        runtime = self.work / 'runtime'
        data = runtime / 'assets/data/example'
        data.mkdir(parents=True)
        self.targets = [data / 'example.json', data / 'example-hard.json']
        self.before = b'{"song":{"events":[]},"preserve":true}\n'
        after = b'{"song":{"events":[[100,[]]]},"preserve":true}\n'
        candidates = []
        for target in self.targets:
            target.write_bytes(self.before)
            candidates.append({'id': target.name, 'target': str(target),
                'beforeSha256': REFRESH.digest(self.before),
                'afterSha256': REFRESH.digest(after),
                'afterBase64': base64.b64encode(after).decode()})
        self.plan = {'version': 1, 'donorRoot': str(self.work / 'donor'),
            'runtimeRoot': str(runtime), 'selectedRoot': 'owner',
            'inputsSha256': {'frozen': 'test'}, 'candidates': candidates}
        self.path = self.work / 'plan.json'
        self.path.write_text(json.dumps(self.plan), newline='\n')
        # Conversion/provenance is covered by the renderer suite; this exercises
        # the transaction after a freshly regenerated plan has been obtained.
        for mock in (patch.object(REFRESH, 'ROOT', self.work),
                     patch.object(REFRESH, 'TMP', self.work / 'tmp'),
                     patch.object(REFRESH, 'fingerprint_inputs', return_value={'frozen': 'test'}),
                     patch.object(REFRESH, 'make_plan', return_value=copy.deepcopy(self.plan))):
            mock.start()
            self.addCleanup(mock.stop)

    def test_second_replace_failure_restores_first_and_cleans_staged_files(self):
        original = REFRESH.os.replace
        calls = []
        def fail_second(source, target):
            calls.append(target)
            if len(calls) == 2:
                raise OSError('simulated replacement failure')
            return original(source, target)
        with patch.object(REFRESH.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'simulated replacement failure'):
                REFRESH.apply_plan(self.plan, self.path)
        self.assertEqual(len(calls), 2)
        for target in self.targets:
            self.assertEqual(target.read_bytes(), self.before)
        self.assertEqual(list(self.targets[0].parent.glob('.codename-events-*')), [])
        backups = list((self.work / 'tmp/import-refresh-backups').iterdir())
        self.assertEqual(len(backups), 1)
        for target in self.targets:
            saved = backups[0] / target.relative_to(self.work / 'runtime')
            self.assertEqual(saved.read_bytes(), self.before)

    def test_debug_runtime_lock_prevents_any_write_and_releases_release_lock(self):
        with (self.work / '.tools/runtime-1.lock').open('a+') as occupied:
            fcntl.flock(occupied, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                REFRESH.apply_plan(self.plan, self.path)
            with (self.work / '.tools/runtime-0.lock').open('a+') as released:
                fcntl.flock(released, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for target in self.targets:
            self.assertEqual(target.read_bytes(), self.before)
        self.assertFalse((self.work / 'tmp/import-refresh-backups').exists())

    def test_modified_reviewed_output_is_rejected_before_backup(self):
        changed = copy.deepcopy(self.plan)
        changed['candidates'][0]['afterBase64'] = base64.b64encode(b'changed').decode()
        changed['candidates'][0]['afterSha256'] = REFRESH.digest(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed since plan'):
            REFRESH.apply_plan(changed, self.path)
        for target in self.targets:
            self.assertEqual(target.read_bytes(), self.before)
        self.assertFalse((self.work / 'tmp/import-refresh-backups').exists())


if __name__ == '__main__':
    unittest.main()
