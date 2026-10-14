"""Tempo map conversions live on the base Conductor and the layers share them."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import ROOT, HAXE_COMMAND
from test_source_gameplay_lifecycle import extract_method


CONDUCTOR_METHODS = [
    'getBPMFromSeconds', 'getBPMFromStep', 'segmentStepCrochet', 'getStep', 'getStepRounded',
    'getBeat', 'getBeatRounded', 'stepToSeconds', 'beatToSeconds', 'getCrotchetAtTime',
    'getCrochetAtTime', 'calculateCrochet', 'mapBPMChanges',
]

MAIN = r'''class Main {
 static function near(actual:Float, expected:Float, label:String):Void
  if (Math.isNaN(actual) || Math.abs(actual - expected) > 0.00001) throw label + ': ' + actual + ' != ' + expected;
 static function eq(actual:Dynamic, expected:Dynamic, label:String):Void
  if (actual != expected) throw label + ': ' + actual + ' != ' + expected;
 static function main() {
  // 120 BPM for 8 steps, then 60 BPM from step 8 (1000 ms), then 240 BPM from step 16 (3000 ms).
  Conductor.changeBPM(120);
  Conductor.mapBPMChanges({bpm:120.0, notes:[
   {lengthInSteps:8, changeBPM:false, bpm:120.0},
   {lengthInSteps:8, changeBPM:true, bpm:60.0},
   {lengthInSteps:8, changeBPM:true, bpm:240.0}
  ]});
  eq(Conductor.bpmChangeMap.length, 2, 'native map');
  near(Conductor.getStep(500), 4, 'first segment');
  near(Conductor.getStep(1500), 10, 'second segment');
  near(Conductor.getStep(3125), 18, 'third segment');
  near(Conductor.getStep(-250), -2, 'countdown uses the live tempo');
  eq(Conductor.getStepRounded(1499), 9, 'rounded step');
  near(Conductor.getBeat(3000), 4, 'beat');
  eq(Conductor.getBeatRounded(3100), 4, 'rounded beat');
  near(Conductor.stepToSeconds(10), 1500, 'step to ms');
  near(Conductor.beatToSeconds(4.5), 3125, 'beat to ms');
  near(Conductor.getCrotchetAtTime(1200), 1000, 'crotchet in the slow segment');
  near(Conductor.getCrochetAtTime(3200), 250, 'crochet spelling');
  near(Conductor.calculateCrochet(150), 400, 'calculateCrochet');
  for (fps in [60, 144, 480]) for (frame in 0...fps * 4) {
   var time = frame * 1000.0 / fps;
   near(Conductor.stepToSeconds(Conductor.getStep(time)), time, 'round trip at ' + fps);
  }
  // Note offset is taken off inside the segment chosen by the raw time.
  near(Conductor.getStep(1000, 100), 7.6, 'offset at a boundary');

  // The Nightmare Vision instance API and decimal step give the same answers.
  var nv = new NightmareVisionConductor();
  for (time in [-250.0, 0.0, 999.0, 1000.0, 2222.0, 3000.0, 4000.0]) {
   near(nv.getStep(time), Conductor.getStep(time), 'nv step ' + time);
   near(nv.beatToSeconds(nv.getBeat(time)), Conductor.beatToSeconds(Conductor.getBeat(time)), 'nv beat ' + time);
   near(NightmareVisionDecimalStep.getStep(time, 120, cast Conductor.bpmChangeMap, 35),
    Conductor.getStep(time, 35), 'decimal step ' + time);
  }

  // A map written in the Nightmare Vision spelling is read by the base API.
  Conductor.bpmChangeMap = cast [{stepTime:0, songTime:0.0, bpm:120.0, stepCrotchet:125.0},
   {stepTime:8, songTime:1000.0, bpm:60.0, stepCrotchet:250.0}];
  near(Conductor.getStep(1125), 8.5, 'stepCrotchet map');
  // So is one that only carries the bpm.
  Conductor.bpmChangeMap = cast [{stepTime:8, songTime:1000.0, bpm:60.0}];
  near(Conductor.getStep(1250), 9, 'bpm only map');

  // Charts that only say sectionBeats used to give a map with every change at step 0.
  Conductor.mapBPMChanges({bpm:120.0, notes:[
   {sectionBeats:2, changeBPM:false, bpm:120.0},
   {sectionBeats:3, changeBPM:true, bpm:60.0},
   {changeBPM:true, bpm:180.0}
  ]});
  eq(Conductor.bpmChangeMap[0].stepTime, 8, 'sectionBeats step');
  near(Conductor.bpmChangeMap[0].songTime, 1000, 'sectionBeats time');
  eq(Conductor.bpmChangeMap[1].stepTime, 20, 'second sectionBeats step');
  near(Conductor.bpmChangeMap[1].songTime, 4000, 'second sectionBeats time');

  // Nightmare Vision keeps its own map shape (initial entry, stepCrotchet).
  nv.mapBPMChanges({bpm:120.0, notes:[{sectionBeats:2.0, changeBPM:false, bpm:120.0},
   {sectionBeats:3.0, changeBPM:true, bpm:60.0}, {sectionBeats:null, changeBPM:true, bpm:180.0}]});
  var map:Array<Dynamic> = cast Conductor.bpmChangeMap;
  eq(map.length, 3, 'nv map has the initial entry');
  near(map[1].stepCrotchet, 250, 'nv spelling');
  eq(map[2].stepTime, 20, 'nv section beats');
  trace('tempo-map-ok');
 }
}
'''


class ConductorTempoMapConversionsTest(unittest.TestCase):
    def test_base_conductor_owns_tempo_map_conversions(self):
        source = (ROOT / 'source/Conductor.hx').read_text(encoding='utf-8')
        methods = '\n'.join(extract_method(source, 'public static function ' + name + '(') for name in CONDUCTOR_METHODS)
        conductor = ('typedef SwagSong = Dynamic;\n'
            'typedef BPMChangeEvent = {var stepTime:Int; var songTime:Float; var bpm:Float; @:optional var stepCrochet:Float;}\n'
            'class Conductor {\n public static var bpm:Float = 100;\n public static var crochet:Float = 600;\n'
            ' public static var stepCrochet:Float = 150;\n public static var songPosition:Float = 0;\n'
            ' public static var lastSongPos:Float = 0;\n public static var offset:Float = 0;\n'
            ' public static var safeZoneOffset:Float = 166;\n'
            ' public static var bpmChangeMap:Array<BPMChangeEvent> = [];\n'
            ' public static function changeBPM(v:Float) {bpm = v; crochet = 60000 / v; stepCrochet = crochet / 4;}\n'
            + methods + '\n}\n')
        # The layers must call the base, not keep their own copies.
        nv = (ROOT / 'source/NightmareVisionConductor.hx').read_text(encoding='utf-8')
        self.assertIn('return Conductor.getStep(time);', nv)
        self.assertIn('ConductorTempoMap.tempoChanges(song', nv)
        self.assertIn('ConductorTempoMap.stepAtTime(', (ROOT / 'source/NightmareVisionDecimalStep.hx').read_text(encoding='utf-8'))
        self.assertIn('Conductor.getStep(Conductor.songPosition', (ROOT / 'source/PsychBeatClock.hx').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            (work / 'Conductor.hx').write_text(conductor, encoding='utf-8', newline='\n')
            (work / 'Main.hx').write_text(MAIN, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work),
                '-main', 'Main', '--interp'], cwd=work, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('tempo-map-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
