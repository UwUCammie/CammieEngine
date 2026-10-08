"""Actual Windows snapshot-to-Project mapping and shared walker checks."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import TEST_TMP
from windows_native_import_fixture import NativeFixtureUnavailable, get_native_fixture


ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT.parent / 'fnf_sources/FNF-PsychEngine'


@unittest.skipUnless(os.name == 'nt', 'actual Windows C++ snapshot/profile check')
class PsychAssetProfileNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            fixture = get_native_fixture()
        except NativeFixtureUnavailable as error:
            raise unittest.SkipTest(str(error))
        cls.binary = fixture.executable
        cls.environment = fixture.environment
        cls.cache_key = fixture.key
        cls.cache_reused = fixture.reused

    def setUp(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='psych-profile-native-', dir=TEST_TMP)
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_fixture(self, *args):
        process = subprocess.run([str(self.binary), *map(str, args)], cwd=self.base,
                                 env=self.environment, text=True, encoding='utf-8',
                                 capture_output=True, timeout=60)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        lines = [line for line in process.stdout.splitlines() if line.startswith('{')]
        self.assertTrue(lines, process.stdout + process.stderr)
        return json.loads(lines[-1])

    def capture(self, project_bytes, language_bytes, additional_files=None):
        source = self.base / 'selected-source'
        source.mkdir()
        (source / 'Project.xml').write_bytes(project_bytes)
        language = source / 'assets/translations/shared/data/pt-BR.lang'
        language.parent.mkdir(parents=True)
        language.write_bytes(language_bytes)
        for relative in ('assets/fonts', 'assets/shared', 'assets/embed', 'assets/songs',
                         'assets/week_assets', 'assets/videos', 'assets/secrets', 'assets/base_game'):
            (source / relative).mkdir(parents=True, exist_ok=True)
        for relative, content in (additional_files or {}).items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        captured = self.run_fixture('capture', source, self.base / 'snapshots')
        self.assertTrue(captured['ok'], captured)
        self.assertTrue(captured['result']['complete'], captured)
        return source, language, captured['result']

    def profile(self, captured, flags):
        build = {'target': 'explicit-native-test', 'command':'', 'flags': [
            {'name': name, 'state': 'enabled' if enabled else 'disabled',
             'provenance': 'test build context'} for name, enabled in flags.items()]}
        return self.run_fixture('psych-asset-profile', captured['snapshotRoot'],
                                captured['snapshotId'], '', 'psych-profile-owner',
                                json.dumps(build, separators=(',', ':')))

    def test_pinned_project_and_language_map_through_real_snapshot(self):
        project_path = DONOR / 'Project.xml'
        language_path = DONOR / 'assets/translations/shared/data/pt-BR.lang'
        if not project_path.is_file() or not language_path.is_file():
            self.skipTest('pinned Psych Project/language input is unavailable')
        project_bytes = project_path.read_bytes()
        language_bytes = language_path.read_bytes()
        source, language, captured = self.capture(project_bytes, language_bytes)
        result = self.profile(captured, {
            'windows': True, 'desktop': True, 'web': False, 'officialBuild': False,
            '32bits': False, 'linux': False, 'android': False, 'mac': False,
            'html5': False, 'mobile': False,
        })
        self.assertTrue(result['ok'], result)
        plan = result['profile']
        self.assertEqual(plan['provenance'], 'receipt-bound', result)
        self.assertEqual(plan['snapshotId'], captured['snapshotId'])
        self.assertEqual(plan['namespace'], 'psych-profile-owner')
        self.assertEqual(plan['projectSha256'], hashlib.sha256(project_bytes).hexdigest())
        self.assertFalse(plan['complete'], 'opaque compiler/haxelib inputs remain unresolved')
        self.assertEqual(result['walk']['files'], 1, result)
        self.assertEqual([row['ownerRelative'] for row in result['mapped']],
                         ['shared/data/pt-BR.lang'], result)
        self.assertEqual(language.read_bytes(), language_bytes)
        self.assertEqual((source / 'Project.xml').read_bytes(), project_bytes)
        self.assertEqual(project_path.read_bytes(), project_bytes)
        self.assertEqual(language_path.read_bytes(), language_bytes)

        retained_project = Path(captured['snapshotRoot']) / 'content/Project.xml'
        retained_project.write_bytes(project_bytes + b'\n<!-- changed retained bytes -->\n')
        rejected = self.profile(captured, {'web': False})
        self.assertFalse(rejected['ok'], rejected)
        self.assertIn('Snapshot file', rejected['error'])
        self.assertEqual((source / 'Project.xml').read_bytes(), project_bytes)

    def test_unknown_conditions_and_repeated_mapping_events(self):
        project = b'''<project>
 <assets path="assets/translations" rename="assets" unless="web" />
 <assets path="assets/translations" rename="assets/second" unless="web" />
</project>'''
        source, language, captured = self.capture(project, b'Portuguese\nhello: "Authored phrase"\n')
        unresolved = self.profile(captured, {})
        self.assertTrue(unresolved['ok'], unresolved)
        self.assertFalse(unresolved['profile']['complete'], unresolved)
        self.assertEqual(unresolved['mapped'], [], unresolved)
        known = self.profile(captured, {'web': False})
        self.assertTrue(known['ok'], known)
        self.assertEqual([row['ownerRelative'] for row in known['mapped']], [
            'shared/data/pt-BR.lang', 'second/shared/data/pt-BR.lang'], known)
        self.assertEqual(known['walk']['files'], 2, known)
        self.assertEqual(language.read_bytes(), b'Portuguese\nhello: "Authored phrase"\n')

    def test_shared_psych_nv_mapped_walk_preserves_non_language_assets_and_order(self):
        project = b'''<project>
 <assets path="assets/translations" rename="assets" unless="web" />
 <assets path="assets/shared" rename="assets/shared" unless="web" />
 <assets path="assets/shared" rename="assets/duplicate" unless="web" />
 <assets path="plugins/settings.ini" rename="plugins/alsoft.ini" />
</project>'''
        authored = {
            'assets/shared/images/Atlas.PNG': b'authored-image-bytes',
            'assets/shared/scripts/Effect.hx': b'class Effect {}',
            'plugins/settings.ini': b'[audio]\n',
        }
        source, language, captured = self.capture(project, b'Portuguese\nhello: "Phrase"\n', authored)
        context = {'target':'explicit-native-fixture', 'command':'', 'flags':[
            {'name':'web', 'state':'disabled', 'provenance':'fixture input'}]}
        for engine in ('Psych Engine', 'Nightmare Vision'):
            with self.subTest(engine=engine):
                result = self.run_fixture('source-asset-profile', captured['snapshotRoot'],
                    captured['snapshotId'], '', engine, 'shared-profile-owner', json.dumps(context))
                self.assertTrue(result['ok'], result)
                events = result['mapped']
                self.assertEqual([row['candidateOrder'] for row in events],
                                 sorted(row['candidateOrder'] for row in events))
                for relative, content in authored.items():
                    matching = [row for row in events if row['sourceRelative'] == relative]
                    self.assertEqual(len(matching), 1 if relative.startswith('plugins/') else 2, result)
                    for row in matching:
                        self.assertEqual(row['size'], len(content))
                        self.assertEqual(row['sha256'], hashlib.sha256(content).hexdigest())
                    self.assertEqual((source / relative).read_bytes(), content)
                outside = next(row for row in events if row['sourceRelative'].startswith('plugins/'))
                self.assertEqual(outside['mappedPath'], 'plugins/alsoft.ini')
                self.assertIsNone(outside.get('ownerRelative'))
                language_only = self.run_fixture('source-asset-profile', captured['snapshotRoot'],
                    captured['snapshotId'], '', engine, 'shared-profile-owner', json.dumps(context), 'language')
                self.assertTrue(language_only['ok'], language_only)
                self.assertEqual([row['sourceRelative'] for row in language_only['mapped']],
                                 ['assets/translations/shared/data/pt-BR.lang'], language_only)
                unknown = self.run_fixture('source-asset-profile', captured['snapshotRoot'],
                    captured['snapshotId'], '', engine, 'shared-profile-owner', '{}')
                self.assertTrue(unknown['ok'], unknown)
                self.assertEqual([row['mappedPath'] for row in unknown['mapped']], ['plugins/alsoft.ini'])
                self.assertNotEqual(unknown['walk']['status'], 'complete')
        self.assertEqual(language.read_bytes(), b'Portuguese\nhello: "Phrase"\n')
        self.assertEqual((source / 'Project.xml').read_bytes(), project)

    def test_local_include_values_and_parent_merge_are_shared_and_receipt_bound(self):
        project = b'''<project>
 <library name="empty-test" />
 <set name="ROOT_TARGET" value="assets" />
 <include path="${PROJECT_FILE}" />
 <assets path="assets/translations" rename="${ROOT_TARGET}/after" />
</project>'''
        included = b'''<project>
 <set name="ROOT_TARGET" value="assets/from-include" />
 <assets path="../assets/translations" rename="${ROOT_TARGET}" />
</project>'''
        source, language, captured = self.capture(project, b'English\nkey: "Retained"\n',
                                                  {'proj/include.xml':included})
        context = {'flagsComplete':True, 'command':'', 'values':[
            {'name':'PROJECT_FILE','value':'proj/include.xml','provenance':'native fixture'},
            {'name':'UNICODE_CONTEXT','value':'retained \U0001f319','provenance':'native fixture'}]}
        fingerprints = []
        for engine in ('Psych Engine', 'Nightmare Vision'):
            with self.subTest(engine=engine):
                result = self.run_fixture('source-asset-profile', captured['snapshotRoot'],
                    captured['snapshotId'], '', engine, 'include-profile-owner', json.dumps(context), 'language')
                self.assertTrue(result['ok'], result)
                self.assertEqual(result['profile']['version'], 4)
                self.assertEqual(result['walk']['status'], 'complete', result)
                self.assertEqual(result['profile']['libraries'], [
                    {'order': 0, 'name': 'empty-test', 'state': 'enabled',
                     'sourcePath': '', 'type': '', 'typeState': 'known',
                     'embed': None, 'embedState': 'known',
                     'preload': False, 'preloadState': 'known',
                     'generate': False, 'generateState': 'known',
                     'prefix': '', 'prefixState': 'known',
                     'conditions': [], 'diagnostic': ''}])
                self.assertTrue(result['profile']['librariesComplete'], result)
                self.assertEqual([row['ownerRelative'] for row in result['mapped']], [
                    'from-include/shared/data/pt-BR.lang', 'after/shared/data/pt-BR.lang'], result)
                inputs = result['profile']['inputFiles']
                self.assertEqual([row['path'] for row in inputs], ['Project.xml', 'proj/include.xml'])
                for row, content in zip(inputs, (project, included)):
                    self.assertEqual(row['size'], len(content))
                    self.assertEqual(row['sha256'], hashlib.sha256(content).hexdigest())
                self.assertEqual(inputs[1]['parentInclude'], 'Project.xml')
                values = {row['name']:row['value'] for row in result['profile']['values']}
                self.assertEqual(values['ROOT_TARGET'], 'assets')
                self.assertEqual(values['UNICODE_CONTEXT'], 'retained \U0001f319')
                fingerprint = result['profile']['contextFingerprint']
                self.assertRegex(fingerprint, r'^[0-9a-f]{64}$')
                fingerprints.append(fingerprint)
        self.assertEqual(fingerprints[0], fingerprints[1])
        self.assertEqual((source / 'proj/include.xml').read_bytes(), included)
        self.assertEqual(language.read_bytes(), b'English\nkey: "Retained"\n')
        retained_include = Path(captured['snapshotRoot']) / 'content/proj/include.xml'
        retained_include.write_bytes(included + b'\n<!-- changed -->\n')
        rejected = self.run_fixture('source-asset-profile', captured['snapshotRoot'],
            captured['snapshotId'], '', 'Psych Engine', 'include-profile-owner', json.dumps(context), 'language')
        self.assertFalse(rejected['ok'], rejected)
        self.assertIn('Snapshot file', rejected['error'])
        self.assertEqual((source / 'proj/include.xml').read_bytes(), included)

    def test_native_project_resolution_pauses_and_cancels_without_blocking_foreground(self):
        project = b'<project><include path="proj/include.xml" /></project>'
        included = b'<extension><assets path="../assets/translations" rename="assets" /></extension>'
        source, language, captured = self.capture(project, b'English\nkey: "Retained"\n',
                                                  {'proj/include.xml':included})
        result = self.run_fixture('project-resolution-scheduler', captured['snapshotRoot'],
                                  captured['snapshotId'], json.dumps({'flagsComplete':True, 'command':''}))
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['cancelled'], result)
        self.assertTrue(result['foreground'], result)
        self.assertEqual((source / 'Project.xml').read_bytes(), project)
        self.assertEqual((source / 'proj/include.xml').read_bytes(), included)
        self.assertEqual(language.read_bytes(), b'English\nkey: "Retained"\n')


if __name__ == '__main__':
    unittest.main()
