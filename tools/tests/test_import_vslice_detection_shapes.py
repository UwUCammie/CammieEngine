"""V-Slice mods are recognised without a base-variation chart pair."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

RUNNER = '''class Main { static function main() {
var base = Sys.args()[0];
var lines:Array<String> = [];
for (name in Sys.args().slice(1)) {
 var root = ImportRootScanner.inspectRoot(base + "/" + name, ImportEngine.AUTO);
 lines.push(name + "=" + (root == null ? "" : root.engine + "|" + root.evidence.join(",")));
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


def meta(root, api_version):
    write(root / '_polymod_meta.json', {'title': 'Mod', 'description': '', 'api_version': api_version, 'mod_version': '1.0.0'})


class VSliceDetectionShapesTest(unittest.TestCase):
    def inspect(self, base, names):
        write(base / 'Main.hx', RUNNER)
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(base), '--run', 'Main',
                                 str(base).replace('\\', '/'), *names],
                                cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)

    def test_songless_variation_only_and_patch_only_mods_are_v_slice(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            # Adds a character and a script, no song at all.
            registry = base / 'registry'
            meta(registry, '0.6.3')
            write(registry / 'data/characters/someone.json',
                  {'version': '1.0.0', 'name': 'Someone', 'renderType': 'sparrow', 'assetPath': 'characters/someone', 'animations': []})
            write(registry / 'scripts/characters/someone.hxc', 'class Someone {}\n')

            # Adds only a variation of a song the base game owns.
            variation = base / 'variation'
            meta(variation, '0.1.0')
            write(variation / 'data/songs/track/track-metadata-remix.json', {'version': '2.2.4', 'songName': 'Track'})
            write(variation / 'data/songs/track/track-chart-remix.json', {'version': '2.0.0', 'notes': {}})
            write(variation / '_merge/data/songs/track/track-metadata.json', {'playData': {'songVariations': ['remix']}})

            # Only patches base files.
            patches = base / 'patches'
            meta(patches, '0.5.0')
            write(patches / '_append/data/introText.txt', 'hello--there\n')

            found = self.inspect(base, ['registry', 'variation', 'patches'])
            for name in ['registry', 'variation', 'patches']:
                self.assertTrue(found[name].startswith('V-Slice|'), name + ': ' + found[name])
                self.assertNotIn('Legacy FNF/Polymod marker', found[name])
            self.assertIn('V-Slice Polymod API version: 0.6.3', found['registry'])
            self.assertIn('V-Slice versioned registry entry: data/characters/*.json', found['registry'])
            self.assertIn('V-Slice script modules: scripts/**/*.hxc', found['registry'])
            self.assertIn('V-Slice chart pair: data/songs/*/*-metadata.json and *-chart.json', found['variation'])
            self.assertIn('V-Slice Polymod merge folder: _merge', found['variation'])
            self.assertIn('V-Slice Polymod API version: 0.5.0', found['patches'])

    def test_legacy_polymod_mods_and_mismatched_pairs_are_not_v_slice(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            legacy = base / 'legacy'
            meta(legacy, '0.1.0')
            write(legacy / 'data/track/track.json',
                  {'song': {'song': 'Track', 'bpm': 120, 'notes': [{'sectionNotes': [], 'mustHitSection': True}]}})
            write(legacy / 'songs/track/Inst.ogg', b'fixture')
            # Old Polymod builds could append to text files as well.
            write(legacy / '_append/data/introText.txt', 'hello--there\n')
            # A character JSON without the registry version field is not a registry entry.
            write(legacy / 'data/characters/someone.json', {'name': 'someone', 'assetPath': 'someone'})

            # Metadata of one variation and a chart of another are not a pair.
            mismatch = base / 'mismatch'
            meta(mismatch, '0.1.0')
            write(mismatch / 'data/songs/track/track-metadata-remix.json', {})
            write(mismatch / 'data/songs/track/track-chart-other.json', {})
            write(mismatch / 'songs/track/Inst.ogg', b'fixture')

            found = self.inspect(base, ['legacy', 'mismatch'])
            for name in ['legacy', 'mismatch']:
                self.assertTrue(found[name].startswith('Legacy FNF/Polymod|'), name + ': ' + found[name])
                self.assertIn('Legacy FNF/Polymod marker: _polymod_meta.json', found[name])


if __name__ == '__main__':
    unittest.main()
