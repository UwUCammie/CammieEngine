"""Direct NMV gameplay script inventory must reflect source scopes and ownership."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionScriptDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        self.addCleanup(self.scratch.cleanup)
        self.work = Path(self.scratch.name)
        self.game = self.work / 'renamed-game'
        self.owner = self.game / 'content/renamed-owner'
        self.owner.mkdir(parents=True)
        self.base = self.game / 'assets'
        self.base.mkdir()
        (self.work / 'Main.hx').write_text('''class Main {
 static function main() {
  var args=Sys.args();
  var chart=haxe.Json.parse(sys.io.File.getContent(args[1]));
  var plan=NightmareVisionScriptDiscovery.discover(args[0], "wrong-folder", chart, null, function(text:String) return tjson.TJSON.parse(text));
  Sys.println(haxe.Json.stringify({plan:plan, diagnostics:NightmareVisionScriptDiscovery.unsupportedDiagnostics(plan)}));
 }
}''', newline='\n')

    def write(self, root, relative, value='function onLoad() {}'):
        p = root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value, newline='\n')
        return p.as_posix()

    def discover(self, song, root=None):
        chart = self.work / 'chart.json'
        chart.write_text(json.dumps(song), newline='\n')
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                 '-cp', str(self.work), '-cp', str(ROOT / '.haxelib/tjson/1,4,0'), '--run', 'Main', str(root or self.owner), str(chart)],
                                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_installed_core_globals_keep_distinct_identity_and_source_order(self):
        installed = self.work / 'assets/imported_mods/installed-owner'
        core = installed / '__nmv_core'
        self.write(core, 'scripts/shared.hx')
        self.write(installed, 'scripts/shared.hx')
        self.write(core, 'data/stages/demo/script.hx')
        self.write(installed, 'stages/demo.hx')
        result = self.discover({'song': 'demo', 'stage': 'demo'}, installed)['plan']
        globals_ = [entry for entry in result['scripts'] if entry['scope'] == 'global']
        self.assertEqual([entry['relative'] for entry in globals_],
                         ['__nmv_core/scripts/shared.hx', 'scripts/shared.hx'])
        stage = next(entry for entry in result['scripts'] if entry['scope'] == 'stage')
        self.assertEqual(stage['relative'], '__nmv_core/data/stages/demo/script.hx')
        self.assertEqual(result['baseAssetsRoot'], core.as_posix())

    def test_owner_base_overlay_extensions_and_all_direct_scopes(self):
        stage = self.write(self.base, 'data/stages/demo/script.hx')
        self.write(self.owner, 'data/stages/demo/script.hscript')
        core = self.write(self.base, 'scripts/core.hx')
        overlay = self.write(self.game / 'content', 'scripts/overlay.hxs')
        own = self.write(self.owner, 'scripts/owner.hscript')
        self.write(self.game / 'content/unselected', 'scripts/wrong.hx')
        self.write(self.owner, 'scripts/states/TitleState.hx')
        self.write(self.owner, 'scripts/unused.lua')
        gf = self.write(self.base, 'data/characters/gf.hx')
        dad = self.write(self.owner, 'data/characters/nested/dad.hx')
        bf = self.write(self.owner, 'characters/bf.hxs')
        local = self.write(self.owner, 'songs/display-title/events.hx')
        nested = self.write(self.owner, 'songs/display-title/scripts/song.hx')
        note = self.write(self.owner, 'data/notetypes/Hurt Note.hx')
        event = self.write(self.owner, 'data/events/nested/event.hx')
        swap = self.write(self.owner, 'data/characters/swapped.hx')
        self.write(self.owner, 'songs/display-title/charts/events.json', json.dumps({'song':{'events':[
            [10,[['nested/event','',''],['Change Character','dad','swapped']]]
        ]}}))
        result = self.discover({'song': {'song':'Display Title','stage':'demo','player1':'bf',
                               'player2':'nested/dad','notes':[{'sectionNotes':[[0,0,0,3]]}]}})
        entries = result['plan']['scripts']
        self.assertEqual([e['path'] for e in entries],
                         [stage,core,overlay,own,gf,dad,bf,local,nested,note,event,swap])
        self.assertEqual([e['scope'] for e in entries],
                         ['stage','global','global','global','character','character','character',
                          'song','song','notetype','event','character_event'])
        self.assertTrue(any('[nightmare-vision-unsupported-script]' in d for d in result['diagnostics']))
        self.assertTrue(any('inventory-incomplete' in d for d in result['diagnostics']))

    def test_hidden_girlfriend_bare_chart_and_source_sidecar_precedence(self):
        self.write(self.owner, 'data/stages/demo/data.json', '{// authored stage\n hide_girlfriend:true,}')
        self.write(self.owner, 'data/characters/gf.hx')
        first = self.write(self.owner, 'data/events/source.hx')
        self.write(self.owner, 'data/events/release.hx')
        for directory, event in [('charts','source'),('data','release')]:
            self.write(self.owner, f'songs/display-title/{directory}/events.json', json.dumps({
                'song': {'events':[[0,[[event,'','']]]]}}))
        result = self.discover({'song':'Display Title','stage':'demo','notes':[]})
        self.assertEqual([e['path'] for e in result['plan']['scripts']], [first])
        self.assertFalse(any('Release-layout' in n for n in result['plan']['coverageNotes']))

    def test_release_sidecar_is_explicitly_provisional(self):
        event = self.write(self.owner, 'data/events/release.hx')
        self.write(self.owner, 'songs/title/data/events.json', '{"song":{"events":[[0,[["release","",""]]]]}}')
        result = self.discover({'song':'title','notes':[]})
        self.assertEqual([e['path'] for e in result['plan']['scripts']], [event])
        self.assertTrue(any('Release-layout' in n for n in result['plan']['coverageNotes']))

    def test_executable_root_uses_assets_and_content_without_sibling_packages(self):
        base = self.write(self.base, 'scripts/base.hx')
        overlay = self.write(self.game/'content', 'scripts/overlay.hx')
        self.write(self.owner, 'scripts/not-selected.hx')
        result = self.discover({'song':'title','notes':[]}, self.game)
        self.assertEqual([e['path'] for e in result['plan']['scripts']], [base,overlay])

    def test_legacy_event_rows_are_inspected_only_when_events_are_absent(self):
        event = self.write(self.owner, 'data/events/Change Character.hx')
        actor = self.write(self.owner, 'data/characters/swapped.hx')
        self.write(self.owner, 'data/notetypes/dad.hx')
        chart = {'song':'title','notes':[{'sectionNotes':[[0,-1,'Change Character','dad','swapped']]}]}
        result = self.discover(chart)
        self.assertEqual([e['path'] for e in result['plan']['scripts']], [event,actor])
        chart['events'] = []
        result = self.discover(chart)
        self.assertFalse(any(e['scope'] in ('event','character_event') for e in result['plan']['scripts']))

    def test_immediate_inventory_is_not_silently_truncated(self):
        for i in range(1030):
            self.write(self.owner, f'scripts/file{i}.hx')
        result = self.discover({'song':'title','notes':[]})
        self.assertEqual(len(result['plan']['scripts']), 1030)
        self.assertEqual(sum('[nightmare-vision-unsupported-script]' in d for d in result['diagnostics']), 1030)


if __name__ == '__main__':
    unittest.main()
