"""Execute production scroll-speed code with the portable Haxe interpreter."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def section(text, start, end):
    pos = text.index(start)
    return text[pos:text.index(end, pos)]


class DynamicScrollSpeedTest(unittest.TestCase):
    def run_haxe(self, text, name='PlayState', extra_files=None):
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            base = Path(folder)
            (base / (name + '.hx')).write_text(text)
            for filename, content in (extra_files or {}).items():
                (base / filename).write_text(content)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', folder,
                                     '-main', name, '--interp'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_options_defaults_limits_steps_and_migration(self):
        options = (ROOT / 'source/OptionsHandler.hx').read_text()
        quality = (ROOT / 'source/CodenameOptionsQualityCompat.hx').read_text()
        helpers = section(options, '    public static inline var DYNAMIC_SCROLL_SPEED_DEFAULT',
                          '    public static function applyDisplayOptions')
        self.run_haxe('typedef TOptions = Dynamic;\nclass OptionTest {\n' + helpers + '''
 static function check(ok:Bool) {if (!ok) throw "option mismatch";}
 static function main() {
  var old:TOptions = {scrollSpeed:2.7, offset:140.2};
  sanitizeOptions(old);
  check(old.dynamicScrollSpeed == 0 && old.scrollSpeed == 2.7 && old.offset == 140.2
   && old.normalizeSongAudio == false);
  check(old.fpsCap == 60);
  check(old.quality == CodenameOptionsQualityCompat.HIGH && old.week6PixelPerfect == true);
  check(old.antialiasing == true && old.gameplayShaders == true
   && old.lowMemoryMode == false && old.gpuOnlyBitmaps == true);
  check(old.naughtyness == true && old.volumeMusic == 1 && old.volumeSFX == 1
   && old.useCharColor == true);
  var falseValues:TOptions = {antialiasing:false, gameplayShaders:false,
   lowMemoryMode:true, gpuOnlyBitmaps:false, useCharColor:false};
  sanitizeOptions(falseValues);
  check(falseValues.antialiasing == false && falseValues.gameplayShaders == false
   && falseValues.lowMemoryMode == true && falseValues.quality == CodenameOptionsQualityCompat.CUSTOM
   && falseValues.gpuOnlyBitmaps == false
   && falseValues.useCharColor == false);
  var oldPreset:TOptions = {antialiasing:false, gameplayShaders:false, lowMemoryMode:true,
   quality:CodenameOptionsQualityCompat.HIGH};
  sanitizeOptions(oldPreset);
  check(oldPreset.quality == CodenameOptionsQualityCompat.HIGH && oldPreset.antialiasing
   && !oldPreset.lowMemoryMode && oldPreset.gameplayShaders);
  var boundedAudio:TOptions = {naughtyness:false, volumeMusic:-2, volumeSFX:1.5};
  sanitizeOptions(boundedAudio);
  check(boundedAudio.naughtyness == false && boundedAudio.volumeMusic == 0
   && boundedAudio.volumeSFX == 1);
  var invalidValues:TOptions = {antialiasing:"off", gameplayShaders:1,
   lowMemoryMode:null, gpuOnlyBitmaps:"yes", useCharColor:"invalid"};
  sanitizeOptions(invalidValues);
  check(invalidValues.antialiasing == true && invalidValues.gameplayShaders == true
   && invalidValues.lowMemoryMode == false && invalidValues.gpuOnlyBitmaps == true
   && invalidValues.useCharColor == true);
  var invalidAudio:TOptions = {naughtyness:"yes", volumeMusic:"bad", volumeSFX:Math.NaN};
  sanitizeOptions(invalidAudio);
  check(invalidAudio.naughtyness == true && invalidAudio.volumeMusic == 1
   && invalidAudio.volumeSFX == 1);
  var normalizeEnabled:TOptions = {normalizeSongAudio:true};
  sanitizeOptions(normalizeEnabled);
  check(normalizeEnabled.normalizeSongAudio == true);
  var normalizeDisabled:TOptions = {normalizeSongAudio:false};
  sanitizeOptions(normalizeDisabled);
  check(normalizeDisabled.normalizeSongAudio == false);
  var normalizeInvalid:TOptions = {normalizeSongAudio:"true"};
  sanitizeOptions(normalizeInvalid);
  check(normalizeInvalid.normalizeSongAudio == false);
  for (fps in [60, 240, 480]) check(sanitizeFpsCap(fps) == fps);
  check(sanitizeFpsCap(990) == 480 && sanitizeFpsCap(5) == 10);
  var invalidFps:Array<Dynamic> = [null, true, "bad", Math.NaN, Math.POSITIVE_INFINITY];
  for (bad in invalidFps)
   check(sanitizeFpsCap(bad) == 60);
  for (i in 0...21) check(sanitizeDynamicScrollSpeed(i * 0.5) == i * 0.5);
  check(sanitizeDynamicScrollSpeed(-1) == 0);
  check(sanitizeDynamicScrollSpeed(1e100) == 10);
  check(sanitizeDynamicScrollSpeed(10.2) == 10);
  check(sanitizeDynamicScrollSpeed(2.24) == 2);
  check(sanitizeDynamicScrollSpeed(2.26) == 2.5);
  var invalid:Array<Dynamic> = [null, true, "bad", Math.NaN, Math.POSITIVE_INFINITY];
  for (bad in invalid)
   check(sanitizeDynamicScrollSpeed(bad) == 0);
  var saved:TOptions = haxe.Json.parse(haxe.Json.stringify({dynamicScrollSpeed:2.5}));
  check(sanitizeOptions(saved).dynamicScrollSpeed == 2.5);
  check(saved.zoomCamera == true && saved.flashingLights == true
   && saved.vignetteEffects == true && saved.lyricsEnabled == true
   && saved.autoPause == true);
  check(saved.normalizeSongAudio == false);
 }
 }''', 'OptionTest', {'CodenameOptionsQualityCompat.hx': quality})
        seed = json.loads((ROOT / 'assets/data/options.json').read_text())
        self.assertEqual(seed['dynamicScrollSpeed'], 0)
        for field in ('zoomCamera', 'flashingLights', 'vignetteEffects', 'lyricsEnabled'):
            self.assertIs(seed[field], True)
        menu = (ROOT / 'source/SaveDataState.hx').read_text()
        fps_row = next(line for line in menu.splitlines() if 'intName: "fpsCap"' in line)
        self.assertIn('max: OptionsHandler.MAX_FPS_CAP', fps_row)
        row = next(line for line in menu.splitlines() if 'intName: "dynamicScrollSpeed"' in line)
        self.assertIn('name: "Static Scroll Speed"', row)
        for field, constant in [('amount', 'DEFAULT'), ('defAmount', 'DEFAULT'),
                                ('min', 'MIN'), ('max', 'MAX'), ('precision', 'STEP')]:
            self.assertIn(field + ': OptionsHandler.DYNAMIC_SCROLL_SPEED_' + constant, row)
        normalize_row = next(line for line in menu.splitlines() if 'intName: "normalizeSongAudio"' in line)
        self.assertIn('name: "Normalize Song Audio"', normalize_row)
        self.assertIn('desc: "Balance vocal and instrumental loudness. Takes effect when a song loads."', normalize_row)
        self.assertIn('sanitizeOptions(lastOptions)', options)
        self.assertIn('var options = sanitizeOptions(FlxG.save.data.options);', options)
        self.assertIn('FlxSprite.defaultAntialiasing = opt.antialiasing;', options)
        self.assertIn('applyDisplayOptions(lastOptions);', options)
        self.assertIn('applyDisplayOptions(opt);', options)
        self.assertIn('applyAudioOptions(lastOptions);', options)
        self.assertIn('applyAudioOptions(opt);', options)
        self.assertIn('FlxG.autoPause = options.autoPause;', options)
        self.assertIn('return options;', options)
        self.assertIn('FlxG.save.data.options = opt;', options)
        self.assertIn('FlxG.autoPause = OptionsHandler.options.autoPause;',
                      (ROOT / 'source/TitleState.hx').read_text())
        self.assertIn('FlxG.autoPause = OptionsHandler.options.autoPause;',
                      (ROOT / 'source/FreeplayState.hx').read_text())

    def test_chart_normalization_events_movement_sustains_and_queue(self):
        ps = (ROOT / 'source/PlayState.hx').read_text()
        note = (ROOT / 'source/Note.hx').read_text()
        fields = section(ps, '\tpublic static var daScrollSpeed:Float = 1;', '\tpublic static var duoMode')
        init = section(ps, '\t\tdaScrollSpeed = OptionsHandler.options.scrollSpeed == 1', '\t\ttrace(SONG.gf);')
        tween = section(ps, '\t@:keep public function tweenScrollSpeed(', '\n\tfunction healthChange(')
        queue = section(ps, '\t\twhile (unspawnNotes.length > 0 && unspawnNotes[0].strumTime - Conductor.songPosition < noteSpawnLookahead)', '\n\t\tif (generatedMusic)')
        movement = section(ps, '\t\t\t\tvar neg = downscroll ? -1 : 1;', '\t\t\t\tif (vnshNotes)')
        sustain = section(ps, '\t\t\t\t\t\tdaNote.prevNote.scale.y =', ';') + ';'
        sinks = [line for line in note.splitlines() if 'prevNote.scale.y *= Conductor.stepCrochet' in line]
        self.assertEqual(len(sinks), 2)
        self.assertTrue(all('effectiveScrollSpeed' in line for line in sinks))
        # One resolved speed value feeds the downscroll and upscroll positions.
        self.assertEqual(ps.count('dynamicScrollTarget > 0 ? effectiveScrollSpeed'), 1)
        self.assertIn('FlxG.save.data.scrollSpeed == 1 ? daScrollSpeed : FlxG.save.data.scrollSpeed', ps)
        self.assertEqual(movement.count('* noteScrollSpeed)'), 2)
        fixture = '''
class OptionsHandler {public static var options = {scrollSpeed:1.0, dynamicScrollSpeed:0.0};}
class Conductor {public static var songPosition:Float=0; public static var stepCrochet:Float=100;
 public static function stepsToTime(v:Float):Float return v * 100;}
class FlxMath {public static function roundDecimal(v:Float,p:Int):Float return Math.round(v*100)/100;}
class FlxEase {public static function linear(t:Float):Float return t;}
class FlxTween {public static function tween(obj:Dynamic, props:Dynamic, duration:Float, opts:Dynamic) {
 Reflect.setField(obj, "daScrollSpeed", props.daScrollSpeed);
}}
class Note {
 public var strumTime:Float; public var alive:Bool=true; public var active:Bool=true; public var visible:Bool=true;
 public function new(t:Float) {strumTime=t;}
 public function kill():Void alive=false;
 public function destroy():Void {}
}
class EngineCompat {
 public static function hxcNoteIncomingPayload(note:Dynamic):Dynamic return {};
 public static function hxcApplyNoteCallbackPayload(payload:Dynamic):Void {}
}
class NightmareVisionScriptGroup {
 public static inline var CONTINUE_FUNC:Int=1;
 public static inline var STOP_FUNC:Int=2;
}
class Group {public var members:Array<Note>=[]; public function new() {} public function add(n:Note) {members.push(n);}}
class PlayState {
''' + fields + '''
 static var SONG={speed:1.0};
 var unspawnNotes:Array<Note>=[]; var notes=new Group(); var loaded=0;
 var hxcStrumlineNoteSurface:Dynamic=null;
 var codenameInputLines:Array<Dynamic>=[]; var demoMode=false;
 function bindCodenameNoteLine(note:Note):Void {}
 var downscroll=false; var drunkNotes=false; var songTime:Float=0; var noteSpeed:Float=0.45;
 var noteScrollSpeed:Float=1;
 var strums={scrollSpeed:1.0,hasScrollSpeedOverride:function()return false};
 var initialStepCrochet:Float=100;
 var daNoteStrums={members:[{y:100.0}]};
 public function new() {}
 function initializeNightmareVisionScripts():Void {}
 // The extracted chart has no selected NMV owner; preserve normal note flow.
 function callNightmareVision(_event:String, ?_args:Array<Dynamic>):Dynamic
  return NightmareVisionScriptGroup.CONTINUE_FUNC;
 function tweenVSliceScrollSpeed(speed:Dynamic, duration:Dynamic, ease:Dynamic, lines:Dynamic):Void {}
 function callAllHScript(name:String,args:Array<Dynamic>,?skipHxc:Bool=false) {if (name == 'noteLoaded') loaded++;}
 function callHxcNoteHScript(name:String,args:Array<Dynamic>):Void {}
 function init() {
''' + init + '\nnoteScrollSpeed = effectiveScrollSpeed;\n}\n' + tween + '\nfunction spawn() {\n' + queue + '''
 }
 function move(daNote:Dynamic) {
''' + movement + '''
 }
 function size(daNote:Dynamic) {
''' + sustain + '''
 }
 function ctorSize(prevNote:Dynamic) {
''' + sinks[0] + '''
 }
 function switchSize(prevNote:Dynamic) {
''' + sinks[1] + '''
 }
 static function near(a:Float,b:Float) {if (!Math.isFinite(a) || Math.abs(a-b)>0.00001) throw a+" != "+b;}
 static function main() {
  var state=new PlayState();
  for (chart in [0.7, 1.0, 2.7, 5.0]) {
   SONG.speed=chart; OptionsHandler.options.dynamicScrollSpeed=0; state.init(); near(effectiveScrollSpeed, chart);
   for (target in [0.5, 1.0, 2.5, 10.0]) {
    OptionsHandler.options.dynamicScrollSpeed=target; state.init(); near(effectiveScrollSpeed,target); near(daScrollSpeed,chart);
    for (down in [false,true]) {
     state.downscroll=down;
     var n:Dynamic={noteData:0,strumTime:1000.0,y:0.0}; state.move(n);
     near(n.y,100+(down ? -1 : 1)*450*target);
    }
    var prev:Dynamic={normalSize:0.7,scale:{y:0.7}};
    state.size({prevNote:prev}); near(prev.scale.y,0.7*1.5*target);
    prev.scale.y=0.7; state.ctorSize(prev); near(prev.scale.y,0.7*1.5*target);
    prev.scale.y=0.7; state.switchSize(prev); near(prev.scale.y,0.7*1.5*target);
    daScrollSpeed=8; near(effectiveScrollSpeed,target);
    state.tweenScrollSpeed({scroll:4,duration:0,absolute:true}); near(daScrollSpeed,4); near(effectiveScrollSpeed,target);
    state.tweenScrollSpeed({scroll:2,duration:4}); near(daScrollSpeed,chart*2); near(effectiveScrollSpeed,target);
   }
  }
  OptionsHandler.options.scrollSpeed=3; OptionsHandler.options.dynamicScrollSpeed=0; state.init(); near(effectiveScrollSpeed,3);
  state.tweenScrollSpeed({scroll:6,duration:0,absolute:true}); near(effectiveScrollSpeed,6);
  OptionsHandler.options.dynamicScrollSpeed=0.5; state.init(); near(effectiveScrollSpeed,0.5);
  state.unspawnNotes=[new Note(1400),new Note(2000),new Note(2900),new Note(3100)]; state.spawn();
  near(state.loaded,3); near(state.unspawnNotes.length,1); near(state.noteSpawnLookahead,3000);
  OptionsHandler.options.dynamicScrollSpeed=0; state.init(); near(state.noteSpawnLookahead,1500);
 }
}
'''
        self.run_haxe(fixture)


if __name__ == '__main__':
    unittest.main()
