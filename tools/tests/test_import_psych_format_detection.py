"""Psych mods are recognised by their week, character and stage formats."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

CHART = {'song': {'song': 'Track', 'bpm': 120, 'notes': [{'sectionNotes': [[0, 0, 0]], 'mustHitSection': True}]}}
WEEK = {'songs': [['Track', 'face', [146, 113, 253]]], 'weekCharacters': ['', 'bf', 'gf'],
        'weekBefore': 'tutorial', 'storyName': 'A Week', 'weekName': 'A Week', 'startUnlocked': True}
CHARACTER = {'animations': [{'anim': 'idle', 'name': 'idle', 'fps': 24, 'loop': False, 'indices': [], 'offsets': [0, 0]}],
             'image': 'characters/someone', 'healthicon': 'face', 'sing_duration': 4,
             'camera_position': [0, 0], 'position': [0, 0], 'scale': 1}
STAGE = {'directory': '', 'defaultZoom': 0.9, 'boyfriend': [770, 100], 'girlfriend': [400, 130],
         'opponent': [100, 100]}

RUNNER = '''class Main { static function main() {
var base = Sys.args()[0];
var lines:Array<String> = [];
for (name in Sys.args().slice(1)) {
 var roots = ImportRootScanner.scan(base + "/" + name, ImportEngine.AUTO);
 lines.push(name + "=" + [for (root in roots) haxe.io.Path.withoutDirectory(root.root) + ":" + root.engine + ":" + root.evidence.join(",")].join(";"));
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


def song(root, name='track'):
    write(root / 'data' / name / (name + '.json'), CHART)
    write(root / 'songs' / name / 'Inst.ogg', b'fixture')


class PsychFormatDetectionTest(unittest.TestCase):
    def scan(self, base, names):
        write(base / 'Main.hx', RUNNER)
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(base), '--run', 'Main',
                                 str(base).replace('\\', '/'), *names],
                                cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)

    def test_mods_without_pack_or_lua_are_detected_by_their_json_formats(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            plain = base / 'plain'
            song(plain)
            write(plain / 'weeks/week.json', WEEK)
            write(plain / 'characters/someone.json', CHARACTER)
            write(plain / 'images/characters/someone.png', b'fixture')

            thin = base / 'thin'
            song(thin)
            write(thin / 'weeks/week.json', WEEK)

            scripted = base / 'scripted'
            write(scripted / 'data/track/track.json', CHART)
            write(scripted / 'data/track/script.hx', 'function onCreate() {\n}\n')
            write(scripted / 'stages/place.json', STAGE)
            write(scripted / 'weeks/week.json', WEEK)

            found = self.scan(base, ['plain', 'thin', 'scripted'])
            for name in ['plain', 'thin', 'scripted']:
                self.assertIn(':Psych Engine:', found[name], name)
                self.assertIn('Psych Engine week file listing a charted song: weeks/*.json', found[name], name)
            self.assertIn('Psych Engine character file: characters/*.json', found['plain'])
            self.assertIn('Psych Engine stage file: stages/*.json', found['scripted'])
            self.assertIn('Psych Engine HScript callbacks', found['scripted'])

    def test_every_sibling_in_a_mods_folder_is_found(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            first = base / 'game/mods/First'
            song(first)
            write(first / 'pack.json', {'name': 'First', 'description': ''})
            second = base / 'game/mods/Second'
            write(second / 'weeks/week.json', WEEK)
            write(second / 'images/storymenu/week.png', b'fixture')

            found = self.scan(base, ['game'])['game']
            self.assertIn('First:Psych Engine:', found)
            self.assertIn('Second:Psych Engine:', found)
            # No chart of its own, so only the week format speaks for it.
            self.assertIn('Psych Engine week file: weeks/*.json', found)

    def test_a_packaged_game_is_one_root_not_one_per_asset_library(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            # Definitions in an asset library next to the song audio.
            library = base / 'library'
            write(library / 'assets/preload/data/track/track.json', CHART)
            write(library / 'assets/preload/weeks/week.json', WEEK)
            write(library / 'assets/preload/characters/someone.json', CHARACTER)
            write(library / 'assets/preload/stages/place.json', STAGE)
            write(library / 'assets/preload/images/thing.png', b'fixture')
            write(library / 'assets/songs/track/Inst.ogg', b'fixture')
            write(library / 'manifest/default.json', {})

            # A base game folder mapped into the asset tree, as source projects do.
            mapped = base / 'mapped'
            write(mapped / 'assets/base_game/shared/data/track/track.json', CHART)
            write(mapped / 'assets/base_game/shared/weeks/week.json', WEEK)
            write(mapped / 'assets/base_game/shared/characters/someone.json', CHARACTER)
            write(mapped / 'assets/base_game/shared/images/thing.png', b'fixture')
            write(mapped / 'assets/base_game/songs/track/Inst.ogg', b'fixture')
            write(mapped / 'assets/shared/images/thing.png', b'fixture')
            # A mod next to the game is still its own root.
            song(mapped / 'mods/Extra')
            write(mapped / 'mods/Extra/weeks/week.json', WEEK)

            found = self.scan(base, ['library', 'mapped'])
            self.assertEqual(found['library'].count(';'), 0, found['library'])
            self.assertTrue(found['library'].startswith('library:Psych Engine:'), found['library'])
            self.assertIn('Psych Engine week file listing a charted song: weeks/*.json', found['library'])
            self.assertIn('Psych Engine character file: characters/*.json', found['library'])

            roots = [entry.split(':', 2)[0] for entry in found['mapped'].split(';')]
            self.assertEqual(sorted(roots), ['Extra', 'mapped'], found['mapped'])
            self.assertNotIn(':Legacy', found['mapped'])

    def test_supporting_folder_names_do_not_turn_a_psych_mod_into_a_fork(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            mod = base / 'mod'
            song(mod)
            write(mod / 'weeks/week.json', WEEK)
            write(mod / 'characters/someone.json', CHARACTER)
            # Folder names a fork's packages use, with nothing of that fork in them.
            write(mod / 'data/noteskins/readme.txt', 'fixture')
            write(mod / 'data/events/readme.txt', 'fixture')
            write(mod / 'scripts/states/readme.txt', 'fixture')

            found = self.scan(base, ['mod'])['mod']
            self.assertTrue(found.startswith('mod:Psych Engine:'), found)
            self.assertNotIn('Nightmare Vision', found)

    def test_folder_names_alone_are_not_psych_evidence(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            # Same folders, other schemas: nothing here is a Psych document.
            lookalike = base / 'lookalike'
            song(lookalike)
            write(lookalike / 'weeks/week.json', {'songs': ['track'], 'name': 'A Week'})
            write(lookalike / 'characters/someone.json',
                  {'name': 'someone', 'asset': 'someone', 'animations': [{'name': 'idle', 'prefix': 'idle'}]})
            write(lookalike / 'stages/place.json', {'camZoom': 0.9, 'objects': []})
            write(lookalike / 'data/track/script.hx', 'function create() {\n}\n// function onCreate() {}\n')

            # Kade-style packaged assets keep their result.
            legacy = base / 'legacy'
            write(legacy / 'assets/data/track/track.json', CHART)
            write(legacy / 'assets/songs/track/Inst.ogg', b'fixture')
            write(legacy / 'manifest/default.json', {})

            # An FPS Plus mod keeps its meta.json identity.
            fps = base / 'fps'
            song(fps)
            write(fps / 'images/thing.png', b'fixture')
            write(fps / 'meta.json', {'name': 'Mod', 'api_version': '1.0.0', 'description': 'FPS Plus mod'})

            found = self.scan(base, ['lookalike', 'legacy', 'fps'])
            self.assertEqual(found['lookalike'], '')
            self.assertNotIn('Psych Engine', found['legacy'])
            self.assertIn(':Legacy FNF/Polymod:', found['legacy'])
            self.assertIn(':FPS Plus:', found['fps'])

    def test_shape_checks_require_the_family_fields(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            write(base / 'Main.hx', '''class Main { static function main() {
var week:Dynamic = haxe.Json.parse(Sys.args()[0]);
var character:Dynamic = haxe.Json.parse(Sys.args()[1]);
var stage:Dynamic = haxe.Json.parse(Sys.args()[2]);
if (!PsychFamilyFormatProbe.isWeek(week) || PsychFamilyFormatProbe.weekSongs(week).join(",") != "track")
 throw "week shape rejected";
if (PsychFamilyFormatProbe.isWeek({songs:["track"], weekCharacters:["", "", ""]})) throw "name list accepted as week rows";
if (PsychFamilyFormatProbe.isWeek(haxe.Json.parse('{"songs":[["Track","face",[1,2,3]]]}'))) throw "song rows without story fields accepted";
if (!PsychFamilyFormatProbe.isCharacter(character)) throw "character shape rejected";
Reflect.deleteField(character, "image");
if (PsychFamilyFormatProbe.isCharacter(character)) throw "character without an atlas accepted";
if (PsychFamilyFormatProbe.isCharacter({version:"1.0.0", renderType:"sparrow", assetPath:"x", animations:[{name:"idle", prefix:"idle"}]}))
 throw "another engine's character accepted";
if (!PsychFamilyFormatProbe.isStage(stage)) throw "stage shape rejected";
Reflect.deleteField(stage, "opponent");
if (PsychFamilyFormatProbe.isStage(stage)) throw "stage without all three positions accepted";
if (!PsychFamilyFormatProbe.declaresLuaCallback("local function onCreatePost()\\nend")) throw "Lua callback missed";
if (PsychFamilyFormatProbe.declaresLuaCallback("--[[\\nfunction onCreate()\\nend\\n]]\\nfunction start(song)\\nend")) throw "commented Lua callback accepted";
if (!PsychFamilyFormatProbe.declaresHaxeCallback("  function onUpdate(elapsed:Float) {}")) throw "HScript callback missed";
if (PsychFamilyFormatProbe.declaresHaxeCallback("/* function onCreate() {} */\\nfunction create() {}\\nfunction onEvent(e) {}"))
 throw "callback names other engines use were accepted";
}}
''')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(base), '--run', 'Main',
                                     json.dumps(WEEK), json.dumps(CHARACTER), json.dumps(STAGE)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
