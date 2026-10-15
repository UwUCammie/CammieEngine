"""The shared event preparation driver: hook order, first pushes and early offsets."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function rows():Array<Dynamic> return [
  {time:100., name:'A', v1:'a1', v2:'', order:0},
  {time:200., name:'Kill Henchmen', v1:'', v2:'', order:1},
  {time:300., name:'A', v1:'a2', v2:'', order:2},
  {time:400., name:'Scripted', v1:'', v2:'', order:3},
 ];
 static function main():Void {
  // Inline offsets: first push once per name, before the row's offset and push.
  var log:Array<String> = [];
  var views:Array<SourceEventNote> = [];
  SourceEventPreparation.prepare(rows(), 10, views, {
   beforeFirstPush:function(e) log.push('unique:' + e.event + ':' + views.length),
   firstPush:function(e) log.push('first:' + e.event + ':' + e.strumTime),
   earlyOffset:function(e):Null<Float> {
    log.push('offset:' + e.event);
    return e.event == 'Scripted' ? 50 : e.event == 'Kill Henchmen' ? 0 : null;
   },
   push:function(e) log.push('push:' + e.event + ':' + e.strumTime)
  });
  check(log.join('|') == 'unique:A:1|first:A:110|offset:A|push:A:110|'
   + 'unique:Kill Henchmen:2|first:Kill Henchmen:210|offset:Kill Henchmen|push:Kill Henchmen:-70|'
   + 'unique:A:3|offset:A|push:A:310|'
   + 'unique:Scripted:4|first:Scripted:410|offset:Scripted|push:Scripted:360', 'inline order ' + log.join('|'));
  check(views.length == 4 && views[1].strumTime == -70, 'a 0 answer still gets the built-in early trigger');

  // Deferred offsets leave times alone until applyEarlyOffsets runs.
  var deferred:Array<SourceEventNote> = [];
  var pushes = 0;
  SourceEventPreparation.prepare(rows(), 0, deferred, {push:function(e) pushes++});
  check(pushes == 4 && deferred[1].strumTime == 200, 'deferred profile must not shift times while pushing');
  SourceEventPreparation.applyEarlyOffsets(deferred, function(e):Null<Float> return e.event == 'A' ? -5 : null);
  check(deferred[0].strumTime == 105 && deferred[1].strumTime == -80 && deferred[3].strumTime == 400,
   'deferred offsets ' + [for (e in deferred) e.strumTime]);

  // The deferred step keeps the inline order: the time is read before the
  // script answers, the built-in default follows the name it leaves behind.
  var moved:Array<SourceEventNote> = [];
  SourceEventPreparation.prepare(rows(), 0, moved, {});
  SourceEventPreparation.applyEarlyOffsets(moved, function(e):Null<Float> {
   if (e.event == 'Scripted') {
    e.strumTime = 9999;
    e.event = 'Kill Henchmen';
   }
   return null;
  });
  check(moved[3].strumTime == 120 && moved[3].event == 'Kill Henchmen',
   'deferred step must subtract from the time read before the callback: ' + moved[3].strumTime);
  var inlined:Array<SourceEventNote> = [];
  SourceEventPreparation.prepare(rows(), 0, inlined, {earlyOffset:function(e):Null<Float> {
   if (e.event == 'Scripted') {
    e.strumTime = 9999;
    e.event = 'Kill Henchmen';
   }
   return null;
  }});
  check(inlined[3].strumTime == moved[3].strumTime, 'inline and deferred offsets must agree');

  // A script answer always beats the built-in default.
  check(SourceEventPreparation.earlyOffsetFor('Kill Henchmen', 40) == 40, 'script answer overrides the default');
  check(SourceEventPreparation.earlyOffsetFor('Kill Henchmen', null) == 280, 'no answer uses the default');
  check(SourceEventPreparation.earlyOffsetFor('Other', null) == 0, 'no default for other events');
 }
}
'''

# Psych's offset reader rejects anything that is not a finite number before the
# driver sees it, so a broken script return falls back to the default too.
OFFSET_MAIN = r'''
class ScriptCallbackResult { public static inline var CONTINUE = '#continue'; }
class Main {
 public function new() {}
 __OFFSET__
 static function main():Void {
  var host = new Main();
  for (bad in ([Math.NaN, Math.POSITIVE_INFINITY, 'text', ScriptCallbackResult.CONTINUE, null]:Array<Dynamic>))
   if (SourceEventPreparation.earlyOffsetFor('Kill Henchmen', host.sourceEventEarlyOffset(bad, 'Kill Henchmen')) != 280)
    throw 'rejected value did not fall back: ' + bad;
  if (SourceEventPreparation.earlyOffsetFor('Kill Henchmen', host.sourceEventEarlyOffset(12.5, 'Kill Henchmen')) != 12.5)
   throw 'finite script answer was dropped';
 }
}
'''


class SourceEventPreparationDriverTest(unittest.TestCase):
    def run_fixture(self, main: str):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = FixturePath(folder)
            (work / 'Main.hx').write_text(main, newline='\n')
            for name in ('SourceEventNote.hx', 'SourceEventPreparation.hx'):
                (work / name).write_text((ROOT / 'source' / name).read_text(encoding='utf-8'), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hooks_run_in_order_with_inline_and_deferred_offsets(self):
        self.run_fixture(MAIN)

    def test_non_finite_script_offsets_fall_back_to_the_default(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        offset = extract_method(play, 'function sourceEventEarlyOffset(')
        self.run_fixture(OFFSET_MAIN.replace('__OFFSET__', offset))

    def test_psych_and_both_nightmare_vision_paths_use_the_shared_driver(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        psych = extract_method(play, 'function preparePsychSourceEvents(')
        finalize = extract_method(play, 'function finalizePsychSourceEvents(')
        nv = extract_method(play, 'function prepareNightmareVisionSourceEvents(')
        self.assertIn('SourceEventPreparation.prepare(', psych)
        self.assertNotIn('earlyOffset:', psych)
        self.assertIn('SourceEventPreparation.applyEarlyOffsets(', finalize)
        self.assertIn('SourceEventPreparation.prepare(', nv)
        self.assertIn('earlyOffset:', nv)
        for source in (psych, finalize, nv):
            self.assertNotIn('280', source)
        legacy = (ROOT / 'source/NightmareVisionLegacyEventPreparation.hx').read_text(encoding='utf-8')
        self.assertIn('SourceEventPreparation.earlyOffsetFor(', legacy)
        self.assertNotIn('280', legacy)


if __name__ == '__main__':
    unittest.main()
