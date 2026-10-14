"""One chart walk finds the event and note type scripts for every Psych-family chart."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


FIXTURE = r'''
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function alwaysMinusOne(values:Array<Dynamic>, hasEvents:Bool):Bool return values[1] == -1;
 static function onlyWithoutEvents(values:Array<Dynamic>, hasEvents:Bool):Bool return !hasEvents && values[1] < 0;
 static function tableA(index:Int):String return ['', 'Alt Animation', 'Hey!', 'Hurt Note'][index];
 static function tableB(index:Int):String return ['', 'Alt Animation', 'Cheer Note'][index];
 static function row(values:Array<Dynamic>):Array<Dynamic> return values;

 static function main():Void {
  // A numeric note type is an index into the caller's built-in table.
  var numeric:Dynamic = {song:{song:'demo', events:[], notes:[
   {sectionNotes:[row([0, 0, 0, 2]), row([10, 1, 0, 2]), row([20, 2, 0, 0]), row([30, 3, 0]), row([40, 0, 0, null])]}
  ]}};
  var first = SourceChartReferences.collect(numeric, null, tableA, alwaysMinusOne);
  var second = SourceChartReferences.collect(numeric, null, tableB, alwaysMinusOne);
  check(first.noteTypes.join('|') == 'Hey!', 'numeric type with the first table: ' + first.noteTypes.join('|'));
  check(second.noteTypes.join('|') == 'Cheer Note', 'numeric type with the second table: ' + second.noteTypes.join('|'));

  // Names the engine handles itself are still reported, once, whatever their case.
  var named:Dynamic = {song:'demo', notes:row([
   {sectionNotes:row([row([0, 0, 0, 'Hurt Note']), row([5, 1, 0, 'hurt note']), row([9, 1, 0, 'GF Sing']), row([12, 1, 0, '']),
    row([15, 2, 0, 'folder\\Deep']), row([18, 2, 0, '../escape']), 'not a row'])},
   null, {sectionNotes:null}
  ])};
  var names = SourceChartReferences.collect(named, null, tableA, alwaysMinusOne);
  check(names.noteTypes.join('|') == 'Hurt Note|GF Sing|folder/Deep', 'named note types: ' + names.noteTypes.join('|'));

  // Whether an old in-section event row counts is the caller's rule.
  var legacy:Array<Dynamic> = row([1000, -2, 'Deep', 'a', 'b']);
  var flat:Array<Dynamic> = row([2000, -1, 'Flat', 'value', '']);
  var withEvents:Dynamic = {song:{song:'demo', events:[row([0, row([row(['Listed', '', ''])])])],
   notes:[{sectionNotes:[legacy, flat, row([3000, 1, 0, 'Typed'])]}]}};
  var withoutEvents:Dynamic = {song:{song:'demo', notes:[{sectionNotes:[legacy, flat, row([3000, 1, 0, 'Typed'])]}]}};
  var strict = SourceChartReferences.collect(withEvents, null, tableA, onlyWithoutEvents);
  check(strict.events.join('|') == 'Listed', 'rows were read as events although the chart lists events: ' + strict.events.join('|'));
  check(strict.noteTypes.join('|') == 'a|value|Typed', 'such rows stay notes: ' + strict.noteTypes.join('|'));
  var loose = SourceChartReferences.collect(withoutEvents, null, tableA, onlyWithoutEvents);
  check(loose.events.join('|') == 'Deep|Flat', 'old event rows were missed: ' + loose.events.join('|'));
  check(loose.noteTypes.join('|') == 'Typed', 'an event row value became a note type: ' + loose.noteTypes.join('|'));
  var pump = SourceChartReferences.collect(withEvents, null, tableA, alwaysMinusOne);
  check(pump.events.join('|') == 'Listed|Flat', 'a -1 row next to an events list was missed: ' + pump.events.join('|'));
  check(pump.noteTypes.join('|') == 'a|Typed', 'note types beside a -1 row: ' + pump.noteTypes.join('|'));

  // Events files in every shape, after the chart's own events and without repeats.
  var companion:Dynamic = {song:{events:row([row([0, row([row(['Listed', '', '']), row(['Extra', 'x', 'y'])])]),
   {e:'Compact', v:['one', 'two']}, {name:'Named'}, 'Bare', row([5, -1, 'FlatListed', '', ''])])}};
  var merged = SourceChartReferences.collect(withEvents, companion, tableA, onlyWithoutEvents);
  check(merged.events.join('|') == 'Listed|Extra|Compact|Named|Bare|FlatListed', 'companion events: ' + merged.events.join('|'));
  var rows = SourceChartReferences.eventRows(companion);
  check(rows[1].join(',') == 'Extra,x,y' && rows[2].join(',') == 'Compact,one,two', 'event values were lost');
  check(SourceChartReferences.eventRows(withoutEvents, onlyWithoutEvents)[0].join(',') == 'Deep,a,b',
   'old event rows lost their values');
  check(SourceChartReferences.eventRows(withoutEvents).length == 0 && SourceChartReferences.eventRows(null).length == 0,
   'events appeared without a rule or a payload');
  check(SourceChartReferences.eventRows({name:'Loose'})[0][0] == 'Loose', 'a single loose event record was dropped');

  // The row callback runs before a row is looked at.
  var seen:Array<String> = [];
  SourceChartReferences.collect(named, null, tableA, alwaysMinusOne, null,
   function(phase, section, index) seen.push(phase + ':' + section + ':' + index));
  check(seen.join(' ') == 'section:0:-1 row:0:0 row:0:1 row:0:2 row:0:3 row:0:4 row:0:5 row:0:6 section:1:-1 section:2:-1',
   'coordinates: ' + seen.join(' '));

  // Shared helpers.
  check(SourceChartReferences.songName({song:{song:' Demo '}}) == 'Demo' && SourceChartReferences.songName({song:'Bare'}) == 'Bare'
   && SourceChartReferences.songName(null) == '', 'song name');
  check(SourceChartReferences.cleanReference('./a\\b') == 'a/b' && SourceChartReferences.cleanReference('/a') == ''
   && SourceChartReferences.cleanReference('C:/a') == '' && SourceChartReferences.cleanReference('a/../b') == '', 'reference cleanup');
  check(SourceChartReferences.isScriptFile('A.LUA', ['.lua']) && !SourceChartReferences.isScriptFile('a.txt', ['.lua'])
   && SourceChartReferences.stripScriptExtension('Name.Lua', ['.lua']) == 'Name', 'script extension helpers');
  check(SourceChartReferences.collect(null, null, tableA, alwaysMinusOne).events.length == 0, 'a missing chart');
 }
}
'''

DISCOVERY = r'''
class Main {
 static function row(values:Array<Dynamic>):Array<Dynamic> return values;
 static function main():Void {
  var chart:Dynamic = {song:{song:'demo', events:[], notes:[
   {sectionNotes:[row([0, 0, 0, 2]), row([10, 1, 0, 'Hurt Note']), row([20, -1, 'Cheer', 'value', '']), row([30, 2, 0, 5])]}
  ]}};
  var plan = PsychScriptDiscovery.discover(Sys.args()[0], 'demo', chart);
  var found = [for (entry in plan.scripts) entry.scope + ':' + entry.name];
  Sys.println(found.join('|'));
 }
}
'''


class SourceChartReferencesTest(unittest.TestCase):
    def run_fixture(self, fixture, *args):
        with tempfile.TemporaryDirectory(prefix='source-chart-refs-', dir=ROOT / 'tmp') as scratch:
            (Path(scratch) / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', scratch, '--run', 'Main', *args],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def test_event_and_note_type_names_follow_the_callers_rules(self):
        self.run_fixture(FIXTURE)

    def test_scripts_for_numeric_and_built_in_note_types_are_discovered(self):
        with tempfile.TemporaryDirectory(prefix='source-chart-refs-mod-', dir=ROOT / 'tmp') as folder:
            owner = Path(folder) / 'owner'
            for relative in ('custom_notetypes/Hey!.lua', 'custom_notetypes/Hurt Note.lua',
                             'custom_notetypes/No Animation.lua', 'custom_notetypes/value.lua',
                             'custom_notetypes/Unused.lua', 'custom_events/Cheer.lua'):
                target = owner / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('-- script', newline='\n')
            output = self.run_fixture(DISCOVERY, str(owner))
        self.assertEqual(output, 'custom_event:Cheer|custom_notetype:Hey!|custom_notetype:Hurt Note'
                                 '|custom_notetype:No Animation')


if __name__ == '__main__':
    unittest.main()
