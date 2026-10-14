"""A Nightmare Vision content package is recognised without its parent game."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

CHART = {'song': {'song': 'Track', 'bpm': 120, 'notes': [{'sectionNotes': [[0, 0, 0]], 'mustHitSection': True}]}}

RUNNER = '''class Main { static function main() {
var base = ImportRootScanner.canonicalize(Sys.args()[0]);
var lines:Array<String> = [];
for (name in Sys.args().slice(1)) {
 var roots = ImportRootScanner.scan(base + "/" + name, ImportEngine.AUTO);
 lines.push(name + "=" + [for (root in roots) root.root.substr(base.length + 1) + "|" + root.engine + "|"
  + (root.data == null ? "" : root.data.substr(base.length + 1)) + "|" + root.evidence.join(",")].join(";"));
}
Sys.println(lines.join("\\n"));
}}
'''


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(value if isinstance(value, str) else json.dumps(value), newline='\n')


def package(root):
    write(root / 'meta.json', {'name': 'Package', 'global': False, 'description': '', 'stateRedirects': {}})
    write(root / 'songs/track/data/hard.json', CHART)
    write(root / 'songs/track/audio/Inst.ogg', b'fixture')


class NightmareVisionStandalonePackageDetectionTest(unittest.TestCase):
    def scan(self, base, names):
        write(base / 'Main.hx', RUNNER)
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(base), '--run', 'Main',
                                 str(base).replace('\\', '/'), *names],
                                cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)

    def test_package_selected_on_its_own_and_below_a_game_without_executable(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            package(base / 'alone')
            package(base / 'game/content/pack')
            # Unmarked package: the song layout alone has to carry it.
            write(base / 'bare/songs/track/data/hard.json', CHART)
            write(base / 'bare/songs/track/Inst.ogg', b'fixture')
            write(base / 'bare/images/thing.png', b'fixture')

            found = self.scan(base, ['alone', 'game', 'bare'])
            root, engine, data, evidence = found['alone'].split('|', 3)
            self.assertEqual((root, engine, data), ('alone', 'Nightmare Vision', 'alone/songs'))
            self.assertIn('Nightmare Vision package song layout: songs/<song>/data/<chart>.json beside the song audio', evidence)
            self.assertIn('Nightmare Vision package meta.json fields', evidence)
            self.assertNotIn(';', found['alone'])

            root, engine, data, evidence = found['game'].split('|', 3)
            self.assertEqual((root, engine, data), ('game/content/pack', 'Nightmare Vision', 'game/content/pack/songs'))
            self.assertNotIn(';', found['game'])

            root, engine, data, evidence = found['bare'].split('|', 3)
            self.assertEqual((root, engine), ('bare', 'Nightmare Vision'))

    def test_family_formats_do_not_pull_the_package_over_to_psych(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            pack = base / 'pack'
            package(pack)
            write(pack / 'pack.json', {'name': 'Package'})
            write(pack / 'data/weeks/week.json', {'songs': [['Track', 'face', [1, 2, 3]]], 'weekCharacters': ['', '', '']})
            write(pack / 'data/noteskins/default.json', {})
            write(pack / 'scripts/states/Title.hx', 'function onCreate() {\n}\n')
            found = self.scan(base, ['pack'])['pack']
            root, engine, data, evidence = found.split('|', 3)
            self.assertEqual(engine, 'Nightmare Vision')
            self.assertIn('Nightmare Vision package folders: data/noteskins, scripts/states', evidence)
            self.assertIn('Nightmare Vision week file listing a charted song: weeks/*.json', evidence)

    def test_other_nested_song_layouts_keep_their_engine(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            # Codename nests per-song folders too, with charts/ and its own meta.
            codename = base / 'codename'
            write(codename / 'songs/track/meta.json', {'name': 'track', 'bpm': 120, 'stepsPerBeat': 4, 'difficulties': ['hard']})
            write(codename / 'songs/track/charts/hard.json', {'strumLines': [], 'codenameChart': True})
            write(codename / 'songs/track/data/hard.json', CHART)
            write(codename / 'songs/track/song/Inst.ogg', b'fixture')
            write(codename / 'data/config/modpack.ini', '[Common]\n')
            # A data folder without audio beside it, or with a flat chart, proves nothing.
            write(base / 'noaudio/songs/track/data/hard.json', CHART)
            write(base / 'noaudio/images/thing.png', b'fixture')
            write(base / 'flat/songs/track/data/hard.json', CHART['song'])
            write(base / 'flat/songs/track/audio/Inst.ogg', b'fixture')
            write(base / 'flat/images/thing.png', b'fixture')
            # A generic root meta.json is not package evidence.
            write(base / 'generic/meta.json', {'title': 'Something', 'version': '1.0'})
            write(base / 'generic/songs/track/Inst.ogg', b'fixture')
            write(base / 'generic/images/thing.png', b'fixture')

            found = self.scan(base, ['codename', 'noaudio', 'flat', 'generic'])
            self.assertIn('|Codename Engine|', found['codename'])
            for name in ['noaudio', 'flat', 'generic']:
                self.assertNotIn('Nightmare Vision', found[name], name)


if __name__ == '__main__':
    unittest.main()
