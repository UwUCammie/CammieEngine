"""Actor metadata upgrades preserve edits and roll back interrupted writes."""
from haxe_test_support import HAXE_COMMAND
import copy
from tools import file_lock as fcntl
import importlib.util
import json
import os
import shutil
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
SPEC = importlib.util.spec_from_file_location('actor_refresh_test', ROOT / 'tools/refresh_codename_actor_metadata.py')
REFRESH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REFRESH)


class ActorMetadataRefreshTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        self.addCleanup(self.scratch.cleanup)
        self.work = Path(self.scratch.name)
        self.runtime, self.preview = self.work / 'runtime', self.work / 'preview'
        self.owner = 'assets/imported_mods/codename-engine-fixture-123'
        self.locks = self.work / 'locks'
        self.locks.mkdir()
        for setting in (patch.object(REFRESH, 'LOCK_ROOT', self.locks),
                        patch.object(REFRESH, 'TMP', self.work)):
            setting.start()
            self.addCleanup(setting.stop)
        source = '''import haxe.Json; import sys.io.File;
class Main { static function main() {
 var entry:Dynamic={stage:"stage",nativeStage:"stage",lines:[
  {role:"player",type:1,position:null,visible:true,characters:["hero"]}],
  characters:{},missingCharacters:["hero"],stageOffsets:{},stageOffsetsKnown:true,
  stageStartCamera:{x:null,y:null},nativeCharacters:{hero:"hero"},
  stagePlacement:CodenameStagePlacement.toData(CodenameStagePlacement.parse('<stage/>'))};
 File.saveContent(Sys.args()[0],CodenameScriptPlan.stringifyCamera(
  CodenameScriptPlan.createCamera("fixture",{hard:entry})));
}}'''
        (self.work / 'Main.hx').write_text(source, newline='\n')
        generated = self.work / 'fresh.json'
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                 '-cp', str(self.work), '--run', 'Main', str(generated)],
                                cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.fresh = json.loads(generated.read_text())
        self.old = copy.deepcopy(self.fresh)
        for key in REFRESH.ADDITIONS:
            self.old['difficulties']['hard'].pop(key)
        self.targets = []
        for root, camera in ((self.runtime, self.old), (self.preview, self.fresh)):
            folder = root / 'assets/data/fixture'
            folder.mkdir(parents=True)
            (folder / 'compatScripts.json').write_text(json.dumps({'version':1,
                'selectedRoot':self.owner, 'roots':[{'path':self.owner,'engine':'Codename Engine'}]}), newline='\n')
            (folder / 'fixture-hard.json').write_text('{"song":{"notes":[[1,2,3]],"keep":true}}', newline='\n')
            plan = root / self.owner / 'songs/fixture'
            plan.mkdir(parents=True)
            (plan / '__cammie_compat_scripts.json').write_text(json.dumps(
                {'version':1,'song':'fixture','stages':{'hard':'stage'}}), newline='\n')
            target = plan / REFRESH.CAMERA
            target.write_text(json.dumps(camera), newline='\n')
            self.targets.append(target)
            for relative, content in (('custom_chars/hero.hscript', 'function init(char) {}'),
                                      ('custom_chars/hero/char.png', 'fixture image'),
                                      ('custom_stages/stage.hscript', 'function start(song) {}')):
                implementation = root / self.owner / 'images' / relative
                implementation.parent.mkdir(parents=True, exist_ok=True)
                implementation.write_text(content, newline='\n')
        self.plan_path = self.work / 'plan.json'

    def plan(self):
        plan = REFRESH.make_plan(self.runtime, self.preview)
        self.plan_path.write_text(json.dumps(plan), newline='\n')
        return plan

    def test_reviewed_after_image_is_stable_across_python_processes(self):
        request = self.work / 'upgrade-input.json'
        request.write_text(json.dumps([self.old, self.fresh]), newline='\n')
        script = ('import json,sys; import refresh_codename_actor_metadata as r; '
                  'old,fresh=json.load(open(sys.argv[1])); '
                  'print(json.dumps(r.additive_upgrade(old,fresh),ensure_ascii=False,indent=2))')
        outputs = []
        for seed in ('1', '2', '3', '4'):
            run = subprocess.run([sys.executable, '-c', script, str(request)],
                cwd=ROOT / 'tools', env={**os.environ, 'PYTHONHASHSEED': seed},
                capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            outputs.append(run.stdout)
        self.assertTrue(all(value == outputs[0] for value in outputs),
                        'identical metadata produced different reviewed after-images')

    def test_upgrade_backup_idempotence_and_chart_preservation(self):
        before = self.targets[0].read_bytes()
        chart = self.runtime / 'assets/data/fixture/fixture-hard.json'
        chart_before = chart.read_bytes()
        plan = self.plan()
        self.assertEqual(len(plan['candidates']), 1, plan['skipped'])
        backup = REFRESH.apply_plan(plan, self.plan_path)
        self.assertEqual((backup / self.targets[0].relative_to(self.runtime)).read_bytes(), before)
        self.assertEqual(json.loads(self.targets[0].read_text()), self.fresh)
        self.assertEqual(chart.read_bytes(), chart_before)
        self.assertEqual(self.plan()['candidates'], [])

    def test_edited_values_unknown_keys_and_difficulty_changes_are_preserved(self):
        for mutate in (
            lambda d: d['difficulties']['hard']['lines'][0].update(visible=False),
            lambda d: d['difficulties']['hard'].update(userSetting=42),
            lambda d: d['difficulties'].update(easy=copy.deepcopy(d['difficulties']['hard'])),
        ):
            current = copy.deepcopy(self.old)
            mutate(current)
            self.targets[0].write_text(json.dumps(current), newline='\n')
            before = self.targets[0].read_bytes()
            self.assertEqual(self.plan()['candidates'], [])
            self.assertEqual(self.targets[0].read_bytes(), before)

    def test_stale_destination_or_preview_refused(self):
        for target in self.targets:
            plan = self.plan()
            original = target.read_bytes()
            target.write_bytes(original + b' ')
            with self.assertRaisesRegex(ValueError, 'changed since review'):
                REFRESH.apply_plan(plan, self.plan_path)
            target.write_bytes(original)

    def test_runtime_lock_prevents_writes(self):
        plan = self.plan()
        before = self.targets[0].read_bytes()
        with (self.locks / 'runtime-1.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                REFRESH.apply_plan(plan, self.plan_path)
        self.assertEqual(self.targets[0].read_bytes(), before)

    def test_missing_or_custom_owned_implementations_block_upgrade(self):
        implementation = self.runtime / self.owner / 'images/custom_stages/stage.hscript'
        original = implementation.read_bytes()
        implementation.unlink()
        plan = self.plan()
        self.assertEqual(plan['candidates'], [])
        self.assertIn('missing owned implementation', plan['skipped'][0]['reason'])
        implementation.write_bytes(original + b'\n// user edit')
        plan = self.plan()
        self.assertEqual(plan['candidates'], [])
        self.assertIn('changed owned implementation', plan['skipped'][0]['reason'])

    def test_changed_implementation_after_review_blocks_apply(self):
        plan = self.plan()
        implementation = self.runtime / self.owner / 'images/custom_chars/hero/char.png'
        implementation.write_bytes(b'changed image')
        with self.assertRaisesRegex(ValueError, 'changed since review'):
            REFRESH.apply_plan(plan, self.plan_path)

    def test_replace_failure_retains_backup_and_cleans_stage(self):
        for root in (self.runtime, self.preview):
            shutil.copytree(root / 'assets/data/fixture', root / 'assets/data/second')
            source = root / self.owner / 'songs/fixture'
            second = source.with_name('second')
            shutil.copytree(source, second)
            for name in (REFRESH.CAMERA, '__cammie_compat_scripts.json'):
                data = json.loads((second / name).read_text())
                data['song'] = 'second'
                (second / name).write_text(json.dumps(data), newline='\n')
        plan = self.plan()
        self.assertEqual(len(plan['candidates']), 2)
        before = self.targets[0].read_bytes()
        original = REFRESH.os.replace
        count = 0
        def fail_second(source, target):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('replace failed')
            return original(source, target)
        with patch.object(REFRESH.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'replace failed'):
                REFRESH.apply_plan(plan, self.plan_path)
        self.assertEqual(self.targets[0].read_bytes(), before)
        self.assertEqual(list(self.work.glob('actor-refresh-*')), [])
        self.assertEqual(len(list((self.work / 'import-refresh-backups').iterdir())), 1)

    def test_old_order_upgrade_does_not_replace_existing_slots(self):
        old = copy.deepcopy(self.fresh)
        old['difficulties']['hard']['stagePlacement'].pop('order')
        upgraded = REFRESH.additive_upgrade(old, self.fresh)
        self.assertEqual(upgraded, self.fresh)
        old['difficulties']['hard']['stagePlacement']['slots']['dad']['x'] += 1
        with self.assertRaisesRegex(ValueError, 'edited or changed'):
            REFRESH.additive_upgrade(old, self.fresh)

    def test_line_geometry_upgrade_is_additive_and_rejects_edited_values(self):
        old = copy.deepcopy(self.fresh)
        fresh = copy.deepcopy(self.fresh)
        line = fresh['difficulties']['hard']['lines'][0]
        line.update(keyCount=4, strumLinePos=0.75, strumPos=[0, 50],
                    strumScale=1, strumSpacing=1)
        self.assertEqual(REFRESH.additive_upgrade(old, fresh), fresh)
        old['difficulties']['hard']['lines'][0]['visible'] = False
        with self.assertRaisesRegex(ValueError, 'edited or changed'):
            REFRESH.additive_upgrade(old, fresh)
        old = copy.deepcopy(self.fresh)
        fresh['difficulties']['hard']['lines'][0]['unreviewedField'] = 1
        with self.assertRaisesRegex(ValueError, 'unexpected new metadata'):
            REFRESH.additive_upgrade(old, fresh)

    def test_line_only_refresh_preserves_divergent_actor_metadata_and_implementations(self):
        current = copy.deepcopy(self.old)
        stage = copy.deepcopy(self.fresh['difficulties']['hard']['stagePlacement'])
        stage['startCamera']['x'] = 7
        current['difficulties']['hard']['stagePlacement'] = stage
        for key in REFRESH.LINE_ADDITIONS:
            current['difficulties']['hard']['lines'][0].pop(key, None)
        self.targets[0].write_text(json.dumps(current), newline='\n')
        implementation = self.runtime / self.owner / 'images/custom_chars/hero.hscript'
        implementation.write_text('custom implementation', newline='\n')
        plan = REFRESH.make_plan(self.runtime, self.preview, line_only=True)
        self.plan_path.write_text(json.dumps(plan), newline='\n')
        self.assertEqual(len(plan['candidates']), 1, plan['skipped'])
        self.assertTrue(plan['lineOnly'])
        backup = REFRESH.apply_plan(plan, self.plan_path)
        self.assertIsNotNone(backup)
        after = json.loads(self.targets[0].read_text())
        self.assertEqual(after['difficulties']['hard']['stagePlacement'], stage)
        self.assertEqual(after['difficulties']['hard']['lines'],
                         self.fresh['difficulties']['hard']['lines'])
        self.assertEqual(implementation.read_text(), 'custom implementation')

    def test_new_difficulty_requires_identical_installed_chart(self):
        current = copy.deepcopy(self.old)
        self.targets[0].write_text(json.dumps(current), newline='\n')
        generated = copy.deepcopy(self.fresh)
        generated['difficulties']['easy'] = copy.deepcopy(generated['difficulties']['hard'])
        self.targets[1].write_text(json.dumps(generated), newline='\n')
        for root in (self.runtime, self.preview):
            (root / 'assets/data/fixture/fixture-easy.json').write_text(
                '{"song":{"notes":[[1,2,3]],"keep":true}}', newline='\n')
        before = self.targets[0].read_bytes()
        plan = REFRESH.make_plan(self.runtime, self.preview, line_only=True)
        self.assertEqual(plan['candidates'], [])
        plan = REFRESH.make_plan(self.runtime, self.preview, line_only=True,
                                 include_new_difficulties=True)
        self.assertEqual(len(plan['candidates']), 1, plan['skipped'])
        self.plan_path.write_text(json.dumps(plan), newline='\n')
        REFRESH.apply_plan(plan, self.plan_path)
        after = json.loads(self.targets[0].read_text())
        self.assertEqual(after['difficulties']['easy'], generated['difficulties']['easy'])
        self.assertEqual(after['difficulties']['hard']['stage'], current['difficulties']['hard']['stage'])
        self.targets[0].write_bytes(before)
        (self.preview / 'assets/data/fixture/fixture-easy.json').write_text(
            '{"song":{"notes":[[9,9,9]],"keep":true}}', newline='\n')
        refused = REFRESH.make_plan(self.runtime, self.preview, line_only=True,
                                    include_new_difficulties=True)
        self.assertEqual(refused['candidates'], [])
        self.assertIn('changed native chart', refused['skipped'][0]['reason'])


if __name__ == '__main__':
    unittest.main()
