"""Executable probes for Psych and Nightmare Vision chart-event preparation."""

from haxe_test_support import HAXE_COMMAND

from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    """Extract a Haxe method while ignoring braces inside comments and strings."""
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    line_comment = False
    block_comment = False
    escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unterminated Haxe method: {marker}")


class SourceEventPreparationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play = (ROOT / "source/PlayState.hx").read_text()
        cls.song_events = (ROOT / "source/SongEvents.hx").read_text()
        cls.collect_events = extract_method(cls.song_events, "public static function collect(")
        cls.extracted = "\n".join((
            extract_method(cls.play, "function preparePsychSourceEvents("),
            extract_method(cls.play, "function precachePsychSourceEvent("),
            extract_method(cls.play, "function finalizePsychSourceEvents("),
            extract_method(cls.play, "function sourceEventEarlyOffset("),
            extract_method(cls.play, "function sortSourceSongEvents("),
            extract_method(cls.play, "function sourceChartNoteOffset("),
            extract_method(cls.play, "function prepareNightmareVisionSourceEvents("),
            extract_method(cls.play, "function precacheNightmareVisionSourceEvent("),
        ))

    def run_haxe_fixture(self, main_source: str):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main_source, newline="\n")
            for name in ("SourceEventNote.hx", "ScriptCallbackResult.hx"):
                (temp / name).write_text((ROOT / "source" / name).read_text(), newline="\n")
            velocity = (ROOT / "source/NightmareVisionScrollVelocity.hx").read_text()
            velocity = velocity.replace("import nightmarevision.modchart.NightmareVisionModchartTransform;", "")
            transform = (ROOT / "source/nightmarevision/modchart/NightmareVisionModchartTransform.hx").read_text()
            distance = transform[transform.index("public static function visualPosition("):]
            distance = distance[:distance.index(";")+1]
            (temp / "NightmareVisionScrollVelocity.hx").write_text(velocity)
            (temp / "NightmareVisionModchartTransform.hx").write_text("class NightmareVisionModchartTransform {"+distance+"}")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_extracted_psych_and_nightmare_vision_event_pipelines(self):
        fixture = r'''
class SourceOptions { public var offset:Float = 0; public function new() {} }
class OptionsHandler { public static var options:SourceOptions = new SourceOptions(); }
class SourceRow {
 public var time:Float; public var name:String; public var v1:Null<String>; public var v2:Null<String>; public var order:Int;
 public function new(time:Float, name:String, v1:Null<String>, v2:Null<String>, order:Int) {
  this.time = time; this.name = name; this.v1 = v1; this.v2 = v2; this.order = order;
 }
}
class PsychCall {
 public var name:String; public var args:Array<Dynamic>; public var family:String; public var ignoreStops:Bool;
 public function new(name:String, args:Array<Dynamic>, family:String, ignoreStops:Bool) {
  this.name = name; this.args = args; this.family = family; this.ignoreStops = ignoreStops;
 }
}
class PsychRuntimeBindings {
 public static function dispatch(host:PlayState, name:String, args:Array<Dynamic>,
   family:String = 'Scripts', ignoreStops:Bool = false, ?hscriptArgs:Array<Dynamic>):Dynamic {
  host.log.push('psych-runtime:' + name);
  host.psychCalls.push(new PsychCall(name, args.copy(), family, ignoreStops));
  var key = args.length > 0 ? name + ':' + Std.string(args[0]) : name;
  return host.psychReturns.get(key);
 }
}
class NightmareVisionScriptGroup { public static inline var CONTINUE_FUNC:Int = 0; }
class NightmareVisionCharacterEvent {
 public static function preloadRole(value:String):Int return value == 'gf' ? 2 : 1;
}
class NightmareVisionCharacterBank {
 var host:PlayState; var role:Int;
 public function new(host:PlayState, role:Int) { this.host = host; this.role = role; }
 public function addToList(name:Dynamic):Void host.log.push('nv-precache-character:' + role + ':' + Std.string(name));
}
class NightmareVisionNoteSkin {
 public function new(paths:Dynamic, name:Dynamic) {}
 public function precacheEffects():Void {}
}
class NightmareVisionPaths { public function new() {} public function getSparrowAtlas(name:String):Dynamic return null; }
class NvPrefsView { public var noteOffset:Float = 0; public function new() {} }
class NvPrefs { public var view:NvPrefsView = new NvPrefsView(); public function new() {} }
class NvCall {
 public var name:String; public var callback:String; public var args:Array<Dynamic>;
 public function new(name:String, callback:String, args:Array<Dynamic>) {
  this.name = name; this.callback = callback; this.args = args.copy();
 }
}
class NvGlobalCall {
 public var name:String; public var args:Array<Dynamic>;
 public function new(name:String, args:Array<Dynamic>) { this.name = name; this.args = args.copy(); }
}
class NvScriptHost {
 public var owner:PlayState;
 public function new(owner:PlayState) this.owner = owner;
 public function loadScope(scope:String,name:String):Void owner.log.push("nv-load:"+scope+":"+name);
 public function callEvent(name:String, callback:String, args:Array<Dynamic>):Dynamic {
  owner.log.push('nv-module:' + callback + ':' + name);
  owner.nvModuleCalls.push(new NvCall(name, callback, args));
  if (callback == 'onFirstPush' && owner.firstNvPushTime == null) {
   var initialEvent:SourceEventNote = cast args[0];
   owner.firstNvPushTime = initialEvent.strumTime;
  }
  if (callback == 'onFirstPush' && owner.mutateFirstPush && name == owner.mutateFirstPushName) {
   var event:SourceEventNote = cast args[0];
   event.value1 = 'mutated-on-first-push';
  }
  if (callback == 'offsetStrumTime') return owner.nvModuleOffsets.get(name);
  return null;
 }
}
class PlayState {
 public var songEvents:Array<Dynamic> = [];
 public var sourceEventViews:Array<SourceEventNote> = [];
 public var psychSourceEventsPrepared:Bool = false;
 public var psychSourceEventsFinalized:Bool = false;
 public var nightmareVisionSourceEventsPrepared:Bool = false;
 public var nightmareVisionLegacyFieldCameras:Bool = false;
 public var songSpeed:Float = 2;
 public var speedChanges:Array<NightmareVisionScrollVelocity.NightmareVisionSpeedEvent> = [NightmareVisionScrollVelocity.initial()];
 public var sourceEventPreparationInProgress:Bool = false;
 public var nightmareVisionScripts:Dynamic = null;
 public var nightmareVisionPrefs:NvPrefs = null;
 public var psychClientPrefs:Dynamic = null;
 public var gf:Dynamic = null;
 public var nightmareVisionPaths:NightmareVisionPaths = new NightmareVisionPaths();
 public var nightmareVisionNoteSkins:Map<String, NightmareVisionNoteSkin> = new Map();
 public var psychCalls:Array<PsychCall> = [];
 public var psychReturns:Map<String, Dynamic> = new Map();
 public var nvModuleCalls:Array<NvCall> = [];
 public var nvGlobalCalls:Array<NvGlobalCall> = [];
 public var nvModuleOffsets:Map<String, Dynamic> = new Map();
 public var nvGlobalOffsets:Map<String, Dynamic> = new Map();
 public var log:Array<String> = [];
 public var mutateFirstPush:Bool = false;
 public var mutateFirstPushName:String = '';
 public var firstNvPushTime:Null<Float> = null;
 public var stageSawNullValues:Bool = false;
 public function new() {}
 function selectedPsychSkinRoot():String return 'fixture-psych-root';
 function compatAddCharacterToList(value2:Dynamic, value1:Dynamic):Void
  log.push('psych-precache-character:' + Std.string(value1) + ':' + Std.string(value2));
 function compatPrecacheSoundForOwner(root:String, sound:Dynamic):Void
  log.push('psych-precache-sound:' + root + ':' + Std.string(sound));
 function dispatchPsychCompiledStage(name:String, args:Array<Dynamic>):Void {
  log.push('psych-stage:' + name);
  if (name == 'eventPushedUnique' && args.length > 0) {
   var event:SourceEventNote = cast args[0];
   if (event.event == 'Other' && event.value1 == 'before') event.value1 = 'stage-edited';
   if (event.event == 'Null Values')
    stageSawNullValues = event.value1 == null && event.value2 == null;
  }
 }
 function callNightmareVision(name:String, args:Array<Dynamic>):Dynamic {
  var key = name;
  if (name == 'eventEarlyTrigger' && args.length > 1)
   key = Std.string(args[0]) + ':' + Std.string(args[1]);
  log.push('nv-global:' + name + ':' + key);
  nvGlobalCalls.push(new NvGlobalCall(name, args));
  var result = nvGlobalOffsets.get(key);
  // Donor ScriptGroup.call propagates Int values only; zero means continue.
  return Std.isOfType(result, Int) ? result : NightmareVisionScriptGroup.CONTINUE_FUNC;
 }
 // Event-pipeline fixture records the source caller boundary, not renderer membership.
 function addNightmareVisionCharacterToList(name:String,role:Int):Void {
  log.push('nv-precache-character:' + role + ':' + name);
 }
 public function exercisePsychPrepare():Void preparePsychSourceEvents();
 public function exercisePsychFinalize():Void finalizePsychSourceEvents();
 public function exerciseNvPrepare():Void prepareNightmareVisionSourceEvents();
 public function exerciseChartNoteTime(authored:Float):Float return authored + sourceChartNoteOffset();
 public function exerciseOffset(value:Dynamic, name:String):Null<Float>
  return sourceEventEarlyOffset(value, name);
__METHOD_INSERTION__
}
class Main {
 static function check(condition:Bool, message:String):Void if (!condition) throw message;
 static function psychCalls(host:PlayState, name:String):Array<PsychCall>
  return host.psychCalls.filter(function(call) return call.name == name);
 static function nvCalls(host:PlayState, callback:String):Array<NvCall>
  return host.nvModuleCalls.filter(function(call) return call.callback == callback);
 static function main():Void {
  OptionsHandler.options.offset = 5;
  var psych = new PlayState();
  var kill = new SourceRow(100, 'Kill Henchmen', 'kill-v1', 'kill-v2', 0);
  var other = new SourceRow(100, 'Other', 'before', 'other-v2', 1);
  var beta = new SourceRow(100, 'Beta', 'beta-v1', 'beta-v2', 2);
  var negative = new SourceRow(120, 'Negative', 'negative-v1', 'negative-v2', 3);
  var sound = new SourceRow(150, 'Play Sound', 'blip', '', 4);
  var nullValues = new SourceRow(160, 'Null Values', null, null, 5);
  psych.songEvents = [kill, other, beta, negative, sound, nullValues];
  check(psych.exerciseChartNoteTime(100) == 105,
   'Psych chart note offset must fall back to the global native option');
  psych.psychReturns.set('eventEarlyTrigger:Kill Henchmen', 0);
  psych.psychReturns.set('eventEarlyTrigger:Other', 25);
  psych.psychReturns.set('eventEarlyTrigger:Beta', 25);
  psych.psychReturns.set('eventEarlyTrigger:Negative', -2);
  psych.psychReturns.set('eventEarlyTrigger:Play Sound', Math.NaN);
  psych.psychReturns.set('eventEarlyTrigger:Null Values', 4);
  psych.exercisePsychFinalize();
  check(psych.psychCalls.length == 0, 'Psych finalizer must wait until preparation');
  psych.exercisePsychPrepare();
  psych.exercisePsychPrepare();
  check(psych.psychSourceEventsPrepared && psych.sourceEventViews.length == 6,
   'Psych preparation guard or retained event-view count changed');
  check(psych.log.filter(function(value) return value == 'psych-stage:eventPushedUnique').length == 6
   && psych.log.filter(function(value) return value == 'psych-stage:eventPushed').length == 6,
   'Psych stage notifications must be per row and once per unique name');
  var pushed = psychCalls(psych, 'onEventPushed');
  check(pushed.length == 6 && pushed[1].args.length == 4
   && pushed[1].args[0] == 'Other' && pushed[1].args[1] == 'stage-edited'
   && pushed[1].args[2] == 'other-v2' && pushed[1].args[3] == 105,
   'Psych onEventPushed scalar ABI or live stage mutation changed');
  check(psych.stageSawNullValues && pushed[5].args.length == 4
   && pushed[5].args[1] == '' && pushed[5].args[2] == '',
   'Psych stage views must preserve source nulls while onEventPushed scalar args blank them');
  check(psych.log.indexOf('psych-precache-sound:fixture-psych-root:blip')
   < psych.log.lastIndexOf('psych-stage:eventPushedUnique'),
   'Psych event precache should run before stage push notification');
  psych.exercisePsychFinalize();
  psych.exercisePsychFinalize();
  check(psych.psychSourceEventsFinalized, 'Psych event offsets did not finalize');
  check(psych.log.indexOf('psych-runtime:onEventPushed')
   < psych.log.indexOf('psych-runtime:eventEarlyTrigger'),
   'Psych early-trigger callbacks must wait until after push notifications');
  var earlyCalls = psychCalls(psych, 'eventEarlyTrigger');
  check(earlyCalls.length == 6 && earlyCalls[1].args.length == 4
   && earlyCalls[1].args[0] == 'Other' && earlyCalls[1].args[1] == 'stage-edited'
   && earlyCalls[1].args[3] == 105 && earlyCalls[1].family == 'Scripts'
   && earlyCalls[1].ignoreStops,
   'Psych early-trigger callback ABI or ignore-stops behavior changed');
  check(earlyCalls[5].args.length == 4 && earlyCalls[5].args[1] == null
   && earlyCalls[5].args[2] == null && nullValues.v1 == null && nullValues.v2 == null
   && psych.sourceEventViews[5].value1 == null && psych.sourceEventViews[5].value2 == null,
   'Psych eventEarlyTrigger and retained source view must preserve raw null values');
  check(kill.time == -175 && other.time == 80 && beta.time == 80
   && negative.time == 127 && sound.time == 155 && nullValues.time == 161,
   'Psych offsets, builtin fallback, invalid-return fallback, or noteOffset changed');
  check(psych.songEvents[0] == kill && psych.songEvents[1] == other && psych.songEvents[2] == beta,
   'Psych queue must sort adjusted times stably by authored order');
  check(psych.sourceEventViews[1].strumTime == other.time
   && psych.sourceEventViews[1].value1 == 'stage-edited',
   'Psych callback view must continue to alias its native queue row');
  check(psych.exerciseOffset('12', 'numeric-string') == null
   && psych.exerciseOffset(Math.POSITIVE_INFINITY, 'infinite') == null,
   'Psych offset validator must reject strings and non-finite numbers');
  OptionsHandler.options.offset = 8.25;
  check(psych.exerciseChartNoteTime(100) == 108.25,
   'native chart note offset must stay live when no Nightmare Vision owner view exists');

  var historical = new PlayState();
  historical.nightmareVisionLegacyFieldCameras = true;
  historical.nightmareVisionScripts = new NvScriptHost(historical);
  historical.nightmareVisionPrefs = new NvPrefs();
  historical.nightmareVisionPrefs.view.noteOffset = 5;
  historical.songEvents = [new SourceRow(100, 'Mult SV', '2', '', 0), new SourceRow(200, 'Constant SV', '4', '', 1)];
  historical.nvModuleOffsets.set('Mult SV', 10.);
  historical.exerciseNvPrepare();
  check(historical.log.indexOf('nv-load:event:Mult SV') < historical.log.indexOf('nv-module:onFirstPush:Mult SV') && historical.log.filter(v -> v.indexOf('nv-load:')==0).length==2,'historical preparation loads before dispatch exactly once per authored name');
  check(historical.speedChanges.length == 3 && historical.speedChanges[1].songTime == 95,
   'Historical SV must capture source noteOffset and early timing before note constructors');
  check(historical.speedChanges[2].position == 141.75 && historical.speedChanges[2].speed == .5,
   'Historical SV continuity or source Constant SV conversion changed');
  check(historical.nvModuleCalls.filter(c -> c.callback == 'onPush').length == 0,
   'Built-in SV preparation must not run a second event-module handler');
  historical.exerciseNvPrepare();
  check(historical.speedChanges.length == 3, 'SV preparation should not repeat after generation');
  var modern = new PlayState();modern.nightmareVisionScripts = new NvScriptHost(modern);
  modern.songEvents = [new SourceRow(100, 'Mult SV', '2', '', 0)];modern.exerciseNvPrepare();
  check(modern.speedChanges.length == 1, 'Historical clock must not change modern owners');

  var nv = new PlayState();
  nv.nightmareVisionScripts = new NvScriptHost(nv);
  nv.nightmareVisionPrefs = new NvPrefs();
  nv.nightmareVisionPrefs.view.noteOffset = 4;
  check(nv.exerciseChartNoteTime(100) == 104,
   'Nightmare Vision chart note offset must prefer its owner view over native global offset');
  nv.nightmareVisionPrefs.view.noteOffset = 6.5;
  check(nv.exerciseChartNoteTime(100) == 106.5,
   'Nightmare Vision chart note offset must read live owner preference changes');
  nv.mutateFirstPush = true;
  nv.mutateFirstPushName = 'Event A';
  var eventA = new SourceRow(100, 'Event A', 'original', 'a-v2', 0);
  var eventA2 = new SourceRow(120, 'Event A', 'second', 'a2-v2', 1);
  var tieA = new SourceRow(50, 'Tie A', 'ta', '', 2);
  var tieB = new SourceRow(50, 'Tie B', 'tb', '', 3);
  var character = new SourceRow(200, 'Change Character', 'bf', 'new-bf', 4);
  var nvKill = new SourceRow(300, 'Kill Henchmen', '', '', 5);
  nv.songEvents = [eventA, eventA2, tieA, tieB, character, nvKill];
  nv.nvGlobalOffsets.set('Event A:mutated-on-first-push', 0);
  nv.nvGlobalOffsets.set('Event A:second', 1); // STOP is also numeric offset 1 in this hook.
  nv.nvGlobalOffsets.set('Tie A:ta', Math.POSITIVE_INFINITY); // Group ignores non-Int result.
  nv.nvGlobalOffsets.set('Tie B:tb', 0);
  nv.nvGlobalOffsets.set('Change Character:bf', 0);
  nv.nvGlobalOffsets.set('Kill Henchmen:', 0);
  nv.nvModuleOffsets.set('Event A', 12.5);
  nv.nvModuleOffsets.set('Tie A', 0);
  nv.nvModuleOffsets.set('Tie B', 0);
  nv.nvModuleOffsets.set('Change Character', 0);
  nv.nvModuleOffsets.set('Kill Henchmen', 0);
  nv.exerciseNvPrepare();
  nv.exerciseNvPrepare();
  check(nv.nightmareVisionSourceEventsPrepared && nv.sourceEventViews.length == 6,
   'Nightmare Vision preparation guard or event-view count changed');
  var firstPushes = nvCalls(nv, 'onFirstPush');
  check(firstPushes.length == 5 && firstPushes[0].name == 'Event A'
   && firstPushes[0].args.length == 1 && firstPushes[0].args[0] == nv.sourceEventViews[0],
   'Nightmare Vision onFirstPush must run once per unique event with one live view');
  check(nv.log.filter(function(value) return StringTools.startsWith(value, 'nv-global:eventEarlyTrigger:')).length == 6,
   'Nightmare Vision eventEarlyTrigger must run once for every event row');
  var globalEarly = nv.nvGlobalCalls.filter(function(call) return call.name == 'eventEarlyTrigger');
  check(globalEarly.length == 6 && globalEarly[0].args.length == 3
   && globalEarly[0].args[0] == 'Event A'
   && globalEarly[0].args[1] == 'mutated-on-first-push'
   && globalEarly[0].args[2] == 'a-v2',
   'Nightmare Vision global early-trigger scalar ABI or live mutation changed');
  var offsets = nvCalls(nv, 'offsetStrumTime');
  check(offsets.length == 5 && offsets[0].args.length == 1
   && offsets[0].args[0] == nv.sourceEventViews[0],
   'Nightmare Vision module offset callback must receive its live event view');
  var callsA = nv.log;
  var firstPushIndex = callsA.indexOf('nv-module:onFirstPush:Event A');
  var globalEarlyIndex = callsA.indexOf('nv-global:eventEarlyTrigger:Event A:mutated-on-first-push');
  var moduleOffsetIndex = callsA.indexOf('nv-module:offsetStrumTime:Event A');
  var modulePushIndex = callsA.indexOf('nv-module:onPush:Event A');
  var globalPushIndex = callsA.indexOf('nv-global:onEventPush:onEventPush');
  check(firstPushIndex >= 0 && firstPushIndex < globalEarlyIndex
   && globalEarlyIndex < moduleOffsetIndex && moduleOffsetIndex < modulePushIndex,
   'Nightmare Vision per-row order must be first-push, global early, module offset, then onPush');
  check(globalPushIndex >= 0 && modulePushIndex < globalPushIndex,
   'Nightmare Vision global onEventPush must follow the per-event onPush: ' + callsA.join('|'));
  var pushesA = nvCalls(nv, 'onPush').filter(function(call) return call.name == 'Event A');
  check(pushesA.length == 2 && pushesA[0].args[0] == nv.sourceEventViews[0]
   && nv.sourceEventViews[0].value1 == 'mutated-on-first-push',
   'Nightmare Vision default onPush should observe first-push mutation for each row');
  check(nv.firstNvPushTime == 106.5,
   'Nightmare Vision event construction must use the same live owner offset as chart notes');
  check(eventA.time == 94 && eventA2.time == 125.5 && tieA.time == 56.5 && tieB.time == 56.5
   && character.time == 206.5 && nvKill.time == 26.5,
   'Nightmare Vision Float module offset, Int STOP offset, zero fallthrough, or builtin fallback changed');
  check(nv.songEvents[0] == nvKill && nv.songEvents[1] == tieA && nv.songEvents[2] == tieB
   && nv.songEvents[3] == eventA && nv.songEvents[4] == eventA2 && nv.songEvents[5] == character,
   'Nightmare Vision final queue must be time-sorted and stable for ties');
  check(nv.log.indexOf('nv-precache-character:1:new-bf') >= 0
   && nvCalls(nv, 'onPush').filter(function(call) return call.name == 'Change Character').length == 0
   && nv.log.filter(function(value) return value == 'nv-global:onEventPush:onEventPush').length == 6,
   'Nightmare Vision built-in prep must suppress module onPush but retain global onEventPush');
  check(offsets.filter(function(call) return call.name == 'Event A').length == 1,
   'nonzero global offset must skip module offset; duplicate rows otherwise get per-row callbacks');
 }
}
'''
        fixture = fixture.replace("__METHOD_INSERTION__", self.extracted)
        self.run_haxe_fixture(fixture)

    def test_source_order_collection_keeps_nullable_slots_and_companion_first(self):
        fixture = r'''
class CodenameEventMetadata { public static function read(row:Array<Dynamic>, time:Float):Dynamic return null; }
class SongEvents {
 static function editorSidecarSourceKey(event:Array<Dynamic>):String return null;
 static function eventSignature(event:Array<Dynamic>, time:Float):String return Std.string(time) + ':' + Std.string(event[0]);
 static function isEditorSidecarTombstone(event:Array<Dynamic>):Bool return false;
__COLLECT_METHOD__
}
class Main {
 static function check(condition:Bool, message:String):Void if (!condition) throw message;
 static function main():Void {
  var embedded:Array<Dynamic> = [[100, [['embedded', null, 'embedded-v2']]]];
  var companion:Array<Dynamic> = [[100, [['companion', null, null]]]];
  var rows = SongEvents.collect(embedded, companion, true, false);
  check(rows.length == 2 && rows[0].name == 'companion' && rows[1].name == 'embedded',
   'sourceOrder collection must visit companion rows before embedded rows');
  check(rows[0].order == 0 && rows[1].order == 1
   && rows[0].v1 == null && rows[0].v2 == null
   && rows[1].v1 == null && rows[1].v2 == 'embedded-v2',
   'sourceOrder collection must preserve nullable authored slots and visitation order');
 }
}
'''.replace("__COLLECT_METHOD__", self.collect_events)
        self.run_haxe_fixture(fixture)

    def test_preparation_lifecycle_is_wired_after_event_collection(self):
        create = extract_method(self.play, "override public function create()")
        psych_first_generation = create.index("loadPsychSourceGlobals();")
        psych_generate = create.index("generateSong(SONG.song);", psych_first_generation)
        psych_prepare = create.index("preparePsychSourceSongScripts();", psych_generate)
        nv_generate = create.index("generateSong(SONG.song);", psych_prepare)
        self.assertLess(psych_first_generation, psych_generate)
        self.assertLess(psych_generate, psych_prepare)
        self.assertLess(psych_prepare, nv_generate)

        generate = extract_method(self.play, "private function generateSong(dataPath:String)")
        self.assertLess(generate.index("songEvents = SongEvents.collect("),
                        generate.index("prepareNightmareVisionSourceEvents();"))
        self.assertIn("var daStrumTime:Float = songNotes[0] + sourceChartNoteOffset();", generate)
        self.assertIn("SongEvents.isNightmareVisionLegacyEventRow(songNotes, songData.keys == null ? 4 : songData.keys)", generate)
        nv_prepare = extract_method(self.play, "function prepareNightmareVisionSourceEvents()")
        self.assertIn("new SourceEventNote(row, sourceChartNoteOffset())", nv_prepare)
        note_offset = extract_method(self.play, "function sourceChartNoteOffset()")
        self.assertIn("return nightmareVisionPrefs != null ? nightmareVisionPrefs.view.noteOffset", note_offset)
        self.assertIn(": psychClientPrefs != null ? psychClientPrefs.data.noteOffset : OptionsHandler.options.offset;",
                      note_offset)

        song_events = (ROOT / "source/SongEvents.hx").read_text()
        self.assertIn("public static function fromSong(data:Dynamic, includeLegacy:Bool = true)", song_events)
        self.assertIn("SongEvents.fromSong(eventData, nightmareVisionScripts == null)", generate)
        self.assertIn("SongEvents.fromSong(songData, nightmareVisionScripts == null)", generate)
        self.assertIn("if (nightmareVisionScripts != null) SongEvents.appendLegacySourceEvents(songEvents, songData);",
                      generate)
        psych_scripts = extract_method(self.play, "function preparePsychSourceSongScripts()")
        self.assertLess(psych_scripts.index("preparePsychSourceEvents();"),
                        psych_scripts.index("loadPsychCompatScripts();"))
        self.assertLess(psych_scripts.index("loadPsychCompatScripts();"),
                        psych_scripts.index("loadCountdownModchart();"))
        self.assertLess(psych_scripts.index("loadCountdownModchart();"),
                        psych_scripts.index("finalizePsychSourceEvents();"))


if __name__ == "__main__":
    unittest.main()
