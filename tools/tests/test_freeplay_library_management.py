"""Hidden entries, mod names, base game duplicates and Freeplay beat presentation."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT = Path(__file__).resolve().parents[2]


class FreeplayLibraryManagementTest(unittest.TestCase):
    def run_haxe(self, body):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            (Path(temp) / 'Main.hx').write_text('class Main {\n static function check(ok:Bool, m:String) { if (!ok) throw m; }\n static function main() {\n' + body + '\n }\n}', encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', temp, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hidden_entries_and_names_persist_without_touching_other_data(self):
        self.run_haxe(r"""
  var data = new UserLibraryData();
  var chart = UserLibraryData.chartKey('assets/imported_mods/pack', 'song'); var base = UserLibraryData.chartKey('', 'bopeebo');
  check(!data.hasHidden() && !data.isChartHidden(chart) && !data.isModHidden('assets/imported_mods/pack') && data.modName('assets/imported_mods/pack') == '', 'empty library hides or names something');
  data.setFavorite(chart, true); data.setChartHidden(chart, true); data.setChartHidden(base, true); data.setChartHidden(base, true);
  data.setModHidden('assets/imported_mods/other/', true); data.setModName('assets/imported_mods/pack', '  My Pack  ');
  check(data.hasHidden() && data.isChartHidden(chart) && data.isChartHidden(base) && data.isModHidden('assets/imported_mods/other'), 'hidden state lost');
  check(data.modName('assets/imported_mods/pack') == 'My Pack' && data.hasModNames(), 'name not trimmed or stored');
  var restored = UserLibraryData.decode(data.encode());
  check(restored.encode() == data.encode(), 'roundtrip changed the document');
  check(restored.isChartHidden(base) && restored.isModHidden('assets/imported_mods/other') && restored.modName('assets/imported_mods/pack') == 'My Pack' && restored.isFavorite(chart), 'restored state differs');
  restored.setChartHidden(chart, false); restored.setChartHidden(base, false); restored.setModHidden('assets/imported_mods/other', false);
  check(!restored.hasHidden() && restored.isFavorite(chart), 'unhiding left residue or removed a favorite');
  restored.setModName('assets/imported_mods/pack', ''); check(!restored.hasModNames() && restored.modName('assets/imported_mods/pack') == '', 'name not cleared');
  var older:Dynamic = haxe.Json.parse(data.encode());
  for (field in ['hiddenCharts', 'hiddenMods', 'modNames']) Reflect.deleteField(older, field);
  var legacy = UserLibraryData.decode(haxe.Json.stringify(older));
  check(!legacy.hasHidden() && !legacy.hasModNames() && legacy.isFavorite(chart), 'older document without the new lists rejected');
  for (bad in [function() data.setModHidden('', true), function() data.setModName('', 'x'), function() data.setChartHidden('', true),
   function() data.setModName('assets/imported_mods/pack', [for (i in 0...90) 'x'].join(''))]) {
   var threw = false; try bad() catch (e:Dynamic) threw = true; check(threw, 'invalid management input accepted');
  }
  var fields = Reflect.fields(haxe.Json.parse(data.encode()));
  check(fields.indexOf('hiddenCharts') >= 0 && fields.indexOf('hiddenMods') >= 0 && fields.indexOf('modNames') >= 0, 'new lists not saved');""")

    def test_base_duplicates_need_title_tempo_cast_and_audio(self):
        self.run_haxe(r"""
  function print(title:String, bytes:Float, seconds:Float, bpm:Float, player:String, opponent:String):BaseGameDuplicate.ChartFingerprint
   return {title:title, audioBytes:bytes, audioSeconds:seconds, bpm:bpm, player:player, opponent:opponent};
  var base = print('Dadbattle', 1458429, 86.67, 180, 'bf', 'dad');
  check(BaseGameDuplicate.matches(print('dad-battle', 1458429, 86.67, 180, 'bf', 'dad'), base), 'identical copy missed');
  check(BaseGameDuplicate.matches(print('Dad Battle', 1400000, 86.60, 180, 'BF', 'Dad'), base, 300, 304), 're-encoded copy with the same chart missed');
  check(!BaseGameDuplicate.matches(print('Dad Battle', 1400000, 86.60, 180, 'bf', 'dad'), base, 300, 340), 'different chart over similar audio hidden');
  check(!BaseGameDuplicate.matches(print('Dad Battle', 1400000, 86.60, 180, 'bf', 'dad'), base), 'unknown note counts treated as equal');
  check(!BaseGameDuplicate.matches(print('dad-battle', 1458429, 86.67, 180, 'bf fnia', 'freddychan'), base), 'chart with its own cast hidden');
  check(!BaseGameDuplicate.matches(print('dad-battle', 1458429, 86.67, 185, 'bf', 'dad'), base), 'different tempo hidden');
  check(!BaseGameDuplicate.matches(print('babybattle', 1458429, 86.67, 180, 'bf', 'dad'), base), 'different title over the same audio hidden');
  check(!BaseGameDuplicate.matches(print('dad-battle', 2000000, 121.9, 180, 'bf', 'dad'), base, 300, 300), 'different instrumental hidden');
  check(!BaseGameDuplicate.matches(print('dad-battle', 1458429, 86.67, 180, '', ''), base), 'unknown cast treated as equal');
  check(!BaseGameDuplicate.matches(print('dad-battle', -1, -1, 180, 'bf', 'dad'), print('Dadbattle', -1, -1, 180, 'bf', 'dad'), 5, 5), 'missing audio treated as equal');
  check(BaseGameDuplicate.sameTitle('philly-nice', 'Philly') && BaseGameDuplicate.sameTitle('Winter Horrorland', 'winter-horrorland') && !BaseGameDuplicate.sameTitle('ugh', 'ughh') && !BaseGameDuplicate.sameTitle('', ''), 'titles');
  check(BaseGameDuplicate.needsNotes(print('a', 5, 1, 1, '', ''), print('a', 6, 1, 1, '', '')) && !BaseGameDuplicate.needsNotes(base, base), 'note comparison rule');
  var found = print('x', 0, 0, -1, '', '');
  BaseGameDuplicate.readChart('{"song":{"player1":"bf","player2":"dad","bpm":180,"notes":[{"bpm":180},{"bpm":90,"changeBPM":true},{"bpm":180}]}}', found);
  check(found.bpm == 180 && found.player == 'bf' && found.opponent == 'dad', 'chart fields not read');
  var head = haxe.io.Bytes.alloc(64); head.set(28, 1); head.blit(29, haxe.io.Bytes.ofString('vorbis'), 0, 6); head.setInt32(40, 44100);
  var tail = haxe.io.Bytes.alloc(64); tail.blit(20, haxe.io.Bytes.ofString('OggS'), 0, 4); tail.setInt32(26, 441000);
  check(Math.abs(BaseGameDuplicate.oggSeconds(head, tail) - 10) < 1e-9, 'ogg length');
  check(BaseGameDuplicate.oggSeconds(haxe.io.Bytes.alloc(64), tail) == -1 && BaseGameDuplicate.oggSeconds(head, haxe.io.Bytes.alloc(64)) == -1 && BaseGameDuplicate.oggSeconds(null, null) == -1, 'malformed audio measured');""")

    def test_heading_beat_meter_colors_and_hints(self):
        self.run_haxe(r"""
  check(FreeplayPulse.bpmFromChartText('{"song":{"bpm":150,"notes":[{"bpm":150},{"bpm":75},{"bpm":150}]}}') == 150, 'song tempo');
  check(FreeplayPulse.bpmFromChartText('{"song":{"notes":[{"bpm" : "102.5"}]}}') == 102.5, 'quoted decimal tempo');
  check(FreeplayPulse.bpmFromChartText('{"bpm":0,"x":{"bpm":99999}}') == FreeplayPulse.DEFAULT_BPM && FreeplayPulse.bpmFromChartText(null) == FreeplayPulse.DEFAULT_BPM && FreeplayPulse.bpmFromChartText('{"bpmx":120}') == FreeplayPulse.DEFAULT_BPM, 'implausible tempo accepted');
  var long = '{"song":{"bpm":174,"notes":[' + [for (i in 0...6000) '{"sectionNotes":[[' + i + ',1,0]],"bpm":174}'].join(',') + ']}}·';
  var started = haxe.Timer.stamp(); check(FreeplayPulse.bpmFromChartText(long) == 174, 'long chart tempo');
  check(haxe.Timer.stamp() - started < 5, 'tempo scan is not linear');
  check(FreeplayPulse.strength(0, 120) == 1 && FreeplayPulse.strength(0.5, 120) == 1 && FreeplayPulse.strength(0.25, 120) < 0.2 && FreeplayPulse.strength(0.49, 120) < 0.001, 'beat strength');
  check(FreeplayPulse.beat(0.49, 120) == 0 && FreeplayPulse.beat(0.5, 120) == 1 && FreeplayPulse.beat(1.01, 120) == 2, 'beat count');
  check(FreeplayPulse.strength(1, 0) == 0 && FreeplayPulse.strength(Math.NaN, 120) == 0 && FreeplayPulse.beat(-5, 120) == 0, 'invalid beat input');
  check(FreeplayPulse.loudness(0) == 0xFF4CFF86 && FreeplayPulse.loudness(0.5) == 0xFFF5F05D && FreeplayPulse.loudness(1) == 0xFFFF4D4D, 'green yellow red stops');
  check(FreeplayPulse.loudness(-3) == FreeplayPulse.loudness(0) && FreeplayPulse.loudness(9) == FreeplayPulse.loudness(1) && FreeplayPulse.loudness(Math.NaN) == FreeplayPulse.loudness(0), 'loudness clamp');
  var quarter = FreeplayPulse.loudness(0.25); check(((quarter >> 16) & 255) > 0x4C && ((quarter >> 16) & 255) < 0xF5, 'no gradient between stops');
  var hints = FreeplayPulse.hints(); var keys = [for (hint in hints) hint.key];
  check(hints.length >= 6 && keys.indexOf('F1') >= 0 && keys.indexOf('CTRL') == 0, 'control hints');
  for (hint in hints) check(hint.key != '' && hint.action != '' && hint.action.indexOf('(') < 0 && hint.action.toLowerCase().indexOf('shift') < 0, 'hint carries extra text: ' + hint.action);
  var top = FreeplayDetailSections.layout();
  check(FreeplayDetailSections.METER_FLOOR < top[0].y && FreeplayDetailSections.HEADER_Y < FreeplayDetailSections.METER_FLOOR - 24 && top[0].y < 120, 'freed heading space unused');""")

    def test_freeplay_wiring(self):
        freeplay = (ROOT / 'source/FreeplayState.hx').read_text(encoding='utf-8')
        matcher = freeplay[freeplay.index('\tfunction songMatches(i:Int):Bool {'):freeplay.index('\n\tfunction anyVisible()')]
        self.assertIn('if (libraryHidden(i)) return false;', matcher)
        hidden = freeplay[freeplay.index('\tfunction libraryHidden('):freeplay.index('\tfunction chartFingerprintFor(')]
        self.assertIn('!OptionsHandler.options.showDuplicateBaseCharts && baseDuplicate(i)', hidden)
        self.assertIn('data.isModHidden(libraryOwner(i)) || data.isChartHidden(libraryChartKey(i))', hidden)
        self.assertIn('FlxG.keys.justPressed.F1', freeplay)
        self.assertIn('var pointer = FlxG.mouse.visible;', freeplay)
        self.assertNotIn('hold, SHIFT faster', freeplay)
        setup = freeplay[freeplay.index('\tfunction setupBrowserChrome('):freeplay.index('\tfunction selectedCardHeight(')]
        self.assertGreater(setup.index("'FREEPLAY'"), setup.index('FreeplayPulse.hints()'))
        self.assertIn('FlxG.width - 246, FlxG.height - 62', setup)
        row = (ROOT / 'source/FreeplayBrowserRow.hx').read_text(encoding='utf-8')
        self.assertIn('flixel.FlxG.mouse.visible && flixel.FlxG.mouse.overlaps(panel)', row)
        manage = (ROOT / 'source/LibraryManageSubState.hx').read_text(encoding='utf-8')
        for label in ('Hide chart: ', 'Hide mod: ', 'Rename mod: ', 'Delete mod and all of its charts...'):
            self.assertIn(label, manage)
        self.assertNotIn('Delete chart', manage)
        star = (ROOT / 'source/RankStar.hx').read_text(encoding='utf-8')
        self.assertIn("var text = expanded ? difficultyLabel + '\\n' + ratingLabel : wholeLabel;", star)
        options = (ROOT / 'source/SaveDataState.hx').read_text(encoding='utf-8')
        self.assertIn('{name: "Show Duplicate Base Game Charts", value: false, intName: "showDuplicateBaseCharts"', options)
        seed = (ROOT / 'assets/data/options.json').read_text(encoding='utf-8')
        self.assertIn('"showDuplicateBaseCharts" : false', seed)


if __name__ == '__main__':
    unittest.main()
