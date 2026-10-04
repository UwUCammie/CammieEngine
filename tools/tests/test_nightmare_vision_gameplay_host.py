"""Executed contracts for the NMV per-play-state gameplay script host."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"
IRIS = ROOT / ".haxelib" / "hscript-iris" / "1,1,3"


def extract_block(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed block: {marker}")


class NightmareVisionGameplayHostTest(unittest.TestCase):
    def test_host_scopes_callbacks_errors_lifetime_and_owner_isolation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / "Main.hx").write_text(r'''
import NightmareVisionScriptDiscovery.NightmareVisionScriptEntry;
import NightmareVisionScriptDiscovery.NightmareVisionScriptPlan;

class HostState {
 public var stateName:String = 'host';
 public function new() {}
}
class Actor {
 public var name:String;
 public function new(name:String) this.name = name;
}
class Main {
 static var scriptSources:Map<String, String> = new Map();
 static var readCounts:Map<String, Int> = new Map();

 static function fail(message:String):Void throw message;
 static function eq(actual:Dynamic, expected:Dynamic):Void {
  if (actual != expected) fail('expected ' + expected + ', got ' + actual);
 }
 static function entry(owner:String, scope:String, name:String, relative:String):NightmareVisionScriptEntry {
  return {scope:scope, name:name, relative:relative, path:owner + '/' + relative};
 }
 static function plan(owner:String):NightmareVisionScriptPlan {
  var entries:Array<NightmareVisionScriptEntry> = [
   entry(owner, 'stage', 'stage', 'data/stages/stage.hx'),
   entry(owner, 'global', 'globalA', 'scripts/a.hx'),
   entry(owner, 'global', 'globalB', 'scripts/b.hx'),
   entry(owner, 'global', 'bad', 'scripts/bad.hx'),
   entry(owner, 'global', 'recover', 'scripts/recover.hx'),
   entry(owner, 'character', 'gf', 'data/characters/gf.hx'),
   entry(owner, 'character', 'dad', 'data/characters/dad.hx'),
   entry(owner, 'character', 'bf', 'data/characters/bf.hx'),
   entry(owner, 'song', 'demo', 'songs/demo.hx'),
   entry(owner, 'song', 'demo', 'songs/demo/scripts/reader.hxs')
  ];
  return {root:owner, baseAssetsRoot:'', song:'demo', stage:'stage', scripts:entries,
   coverageNotes:[]};
 }
 static function registerSources(owner:String):Void {
  var prefix = owner + '/';
  scriptSources.set(prefix + 'data/stages/stage.hx', '
   record("stage:top:addBound=" + hasStageAdd());
   function onLoad() { record("stage:load:" + stage.stageData.defaultZoom + ":addBound=" + hasStageAdd()); add("from-onLoad"); }
   var countdownAttempts = 0;
   function onStartCountdown() {
    countdownAttempts++;
    record("stage:startCountdown:" + countdownAttempts);
    if (countdownAttempts == 1) return Function_Stop;
    return Function_Continue;
   }
   function cancel() { record("stage:cancel"); return Function_Stop; }
   function onDestroy() record("stage:destroy");
  ');
  scriptSources.set(prefix + 'scripts/a.hx', '
   function onLoad() record("globalA:load");
   function cancel() { record("globalA:cancel"); return Function_Continue; }
   function zero() return 10;
   function one(value) return value + 2;
   function three(a, b, c) return a + b + c;
   function onDestroy() record("globalA:destroy");
  ');
  scriptSources.set(prefix + 'scripts/b.hx', '
   function onLoad() record("globalB:load");
   function cancel() { record("globalB:cancel"); return Function_Continue; }
   function onDestroy() record("globalB:destroy");
  ');
  scriptSources.set(prefix + 'scripts/bad.hx', 'throw "module failure";');
  scriptSources.set(prefix + 'scripts/recover.hx', '
   var attempts = 0;
   function onLoad() record("recover:load");
   function recover() { attempts++; if (attempts == 1) throw "first call"; return attempts + 10; }
   function onDestroy() record("recover:destroy");
  ');
  scriptSources.set(prefix + 'data/characters/gf.hx', '
   public var firstActor:Dynamic = null;
   function onLoad() record("character:gf:load:parentBound=" + hasActorParent());
   function captureActor() { firstActor = parent; return parent.name; }
   function currentName() return parent.name;
   function onDestroy() record("character:gf:destroy");
  ');
  scriptSources.set(prefix + 'data/characters/dad.hx', '
   function onLoad() record("character:dad:load:parentBound=" + hasActorParent());
   function currentName() return parent.name;
   function firstName() return firstActor.name;
   function onDestroy() record("character:dad:destroy");
  ');
  scriptSources.set(prefix + 'data/characters/bf.hx', '
   function onLoad() record("character:bf:load:parentBound=" + hasActorParent());
   function currentName() return parent.name;
   function onDestroy() record("character:bf:destroy");
  ');
  scriptSources.set(prefix + 'songs/demo.hx', '
   public var ownerShared:String = ownerToken;
   function onLoad() record("song:load");
   function ownerValue() return ownerShared;
   function onDestroy() record("song:destroy");
  ');
  scriptSources.set(prefix + 'songs/demo/scripts/reader.hxs', '
   function onLoad() record("songReader:load");
   function ownerValue() return ownerShared;
   function onDestroy() record("songReader:destroy");
  ');
 }
 static function createHost(owner:String, token:String):Dynamic {
  registerSources(owner);
  var log:Array<String> = [];
  var errors:Array<String> = [];
  var reads:Array<String> = [];
  var host = new NightmareVisionGameplayScripts(new HostState(), plan(owner),
   function(path:String):String {
    reads.push(path);
    readCounts.set(path, (readCounts.exists(path) ? readCounts.get(path) : 0) + 1);
    if (!scriptSources.exists(path)) throw 'missing script: ' + path;
    return scriptSources.get(path);
   },
   function(interp:NightmareVisionScriptInterp, entry:NightmareVisionScriptEntry, actor:Dynamic):Void {
    interp.variables.set('record', function(text:String):Void log.push(text));
    interp.variables.set('ownerToken', token);
    interp.variables.set('stage', {stageData:{defaultZoom:0.8}});
    interp.variables.set('hasActorParent', function():Bool return interp.variables.exists('parent'));
    interp.variables.set('hasStageAdd', function():Bool return interp.variables.exists('add'));
    interp.variables.set('Function_Continue', NightmareVisionScriptGroup.CONTINUE_FUNC);
    interp.variables.set('Function_Stop', NightmareVisionScriptGroup.STOP_FUNC);
    interp.variables.set('Function_Halt', NightmareVisionScriptGroup.HALT_FUNC);
   },
   function(name:String, phase:String, error:Dynamic):Void errors.push(name + '#' + phase + ':' + Std.string(error)),
   function(interp:NightmareVisionScriptInterp, entry:NightmareVisionScriptEntry):Void {
    if (entry.scope == 'stage') {
     log.push('stage:beforeLoad');
     interp.variables.set('add', function(label:String):Void log.push('stage:add:' + label));
    }
   });
  return {host:host, log:log, errors:errors, reads:reads};
 }
 static function main() {
  var a = createHost('owner-A', 'token-A');
  var host:NightmareVisionGameplayScripts = a.host;
  var gf = new Actor('gf'); var dad = new Actor('dad'); var bf = new Actor('bf');

  // Each requested scope loads in source order; repeated scope requests do not
  // re-read, re-execute, or repeat onLoad.
  host.loadScope('stage'); host.loadScope('stage');
  host.loadScope('global'); host.loadScope('global');
  host.loadScope('character', 'gf', gf); host.loadScope('character', 'gf', gf);
  host.loadScope('character', 'dad', dad);
  host.loadScope('character', 'bf', bf);
  host.loadScope('song'); host.loadScope('song');
  eq(a.log.join(','), 'stage:top:addBound=false,stage:beforeLoad,'
   + 'stage:load:0.8:addBound=true,stage:add:from-onLoad,'
   + 'globalA:load,globalB:load,recover:load,'
   + 'character:gf:load:parentBound=false,character:dad:load:parentBound=false,'
   + 'character:bf:load:parentBound=false,'
   + 'song:load,songReader:load');
  if (a.errors.length != 1 || a.errors[0].indexOf('scripts/bad.hx#module:') != 0)
   fail('bad module reports=' + a.errors.join(','));
  eq(readCounts.get('owner-A/data/stages/stage.hx'), 1);
  if (readCounts.get('owner-A/scripts/bad.hx') != 1)
   fail('bad script reads=' + readCounts.get('owner-A/scripts/bad.hx'));

  // Stage-owned intros can stop the first countdown and release it on their
  // next authored startCountdown() handoff.
  eq(host.call('onStartCountdown'), NightmareVisionScriptGroup.STOP_FUNC);
  eq(host.call('onStartCountdown'), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(a.log.slice(-2).join(','), 'stage:startCountdown:1,stage:startCountdown:2');

  // Character `parent` is module-local and live; public fields cross scripts
  // inside this owner and retain the actual actor object.
  var gfScript = host.group.getScript('data/characters/gf.hx');
  var dadScript = host.group.getScript('data/characters/dad.hx');
  eq(gfScript.call('captureActor'), 'gf');
  eq(gfScript.call('currentName'), 'gf');
  eq(dadScript.call('currentName'), 'dad');
  eq(dadScript.call('firstName'), 'gf');
  gf.name = 'gf-live';
  eq(gfScript.call('currentName'), 'gf-live');
  eq(dadScript.call('firstName'), 'gf-live');
  bf.name = 'bf-live';
  eq(host.group.getScript('data/characters/bf.hx').call('currentName'), 'bf-live');

  // The real gameplay host forwards supported callback arities unchanged.
  eq(host.call('zero'), 10);
  eq(host.call('one', [5]), 7);
  eq(host.call('three', [1, 2, 3]), 6);

  // STOP is returned to the PlayState caller while later scripts still receive
  // the callback, matching the source ScriptGroup's continue-on-STOP behavior.
  a.log.resize(0);
  eq(host.call('cancel'), NightmareVisionScriptGroup.STOP_FUNC);
  eq(a.log.join(','), 'stage:cancel,globalA:cancel,globalB:cancel');

  // A callback error is reported once, but does not poison later invocations.
  var errorCount = a.errors.length;
  eq(host.call('recover'), 0);
  eq(a.errors.length, errorCount + 1);
  if (a.errors[a.errors.length - 1].indexOf('scripts/recover.hx#recover:') != 0)
   fail('callback report=' + a.errors.join(','));
  var recovered = host.call('recover');
  if (recovered != 12) fail('recovery result=' + recovered + ' reports=' + a.errors.join(','));
  eq(a.errors.length, errorCount + 1);

  // Public state is shared across modules only within its owning group.
  eq(host.group.getScript('songs/demo/scripts/reader.hxs').call('ownerValue'), 'token-A');
  var b = createHost('owner-B', 'token-B');
  var hostB:NightmareVisionGameplayScripts = b.host;
  hostB.loadScope('song');
  eq(hostB.group.getScript('songs/demo/scripts/reader.hxs').call('ownerValue'), 'token-B');
  eq(host.group.getScript('songs/demo/scripts/reader.hxs').call('ownerValue'), 'token-A');

  // Destruction broadcasts once to every loaded member, then releases the
  // group; later calls, scope loads, and repeated destroy cannot run callbacks.
  a.log.resize(0);
  host.destroy(); host.destroy();
  eq(a.log.join(','), 'stage:destroy,globalA:destroy,globalB:destroy,recover:destroy,'
   + 'character:gf:destroy,character:dad:destroy,character:bf:destroy,'
   + 'song:destroy,songReader:destroy');
  var destroyedLog = a.log.join(',');
  eq(host.call('cancel'), NightmareVisionScriptGroup.CONTINUE_FUNC);
  host.loadScope('global');
  eq(a.log.join(','), destroyedLog);
  eq(host.group.released, true);
  eq(host.group.members.length, 0);
  hostB.destroy();
 }
}
''', newline='\n')
            for defines in ([], ["-D", "hscriptPos"]):
                with self.subTest(defines=defines):
                    result = subprocess.run(
                        [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", str(work)]
                        + defines + ["--main", "Main", "--interp"],
                        cwd=work,
                        capture_output=True,
                        text=True,
                        timeout=45,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_event_scripts_are_owner_scoped_and_receive_only_their_trigger(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / "Main.hx").write_text(r'''
import NightmareVisionScriptDiscovery.NightmareVisionScriptEntry;
import NightmareVisionScriptDiscovery.NightmareVisionScriptPlan;

class HostState { public function new() {} }
class Main {
 static var sources:Map<String, String> = new Map();
 static function fail(message:String):Void throw message;
 static function eq(actual:Dynamic, expected:Dynamic):Void {
  if (actual != expected) fail('expected ' + expected + ', got ' + actual);
 }
 static function entry(owner:String, scope:String, name:String, relative:String):NightmareVisionScriptEntry {
  return {scope:scope, name:name, relative:relative, path:owner + '/' + relative};
 }
 static function main() {
  var plan:NightmareVisionScriptPlan = {
   root:'owner-A', baseAssetsRoot:'', song:'demo', stage:'stage', coverageNotes:[],
   scripts:[
    entry('owner-A', 'global', 'global', 'scripts/global.hx'),
    entry('owner-A', 'event', 'Alpha', 'data/events/Alpha.hx'),
    entry('owner-A', 'event', 'Beta', 'data/events/Beta.hx')
   ]
  };
  sources.set('owner-A/scripts/global.hx', '
   function onEvent(name, v1, v2) record("global:" + name + ":" + v1 + ":" + v2);
   function onDestroy() record("global:destroy");
  ');
  sources.set('owner-A/data/events/Alpha.hx', '
   function onLoad() record("alpha:load");
   function onEvent(name, v1, v2) record("alpha:generic:" + name + ":" + v1 + ":" + v2);
   function onTrigger(v1, v2) { record("alpha:trigger:" + v1 + ":" + v2); return 7; }
   function onDestroy() record("alpha:destroy");
  ');
  sources.set('owner-A/data/events/Beta.hx', '
   function onLoad() record("beta:load");
   function onEvent(name, v1, v2) record("beta:generic:" + name + ":" + v1 + ":" + v2);
   function onTrigger(v1, v2) record("beta:trigger:" + v1 + ":" + v2);
   function onDestroy() record("beta:destroy");
  ');
  sources.set('owner-B/data/events/Alpha.hx', 'function onTrigger() record("foreign:trigger");');
  var log:Array<String> = [];
  var reads:Array<String> = [];
  var host = new NightmareVisionGameplayScripts(new HostState(), plan,
   function(path:String):String {
    reads.push(path);
    if (!sources.exists(path)) throw 'unexpected read: ' + path;
    return sources.get(path);
   },
   function(interp:NightmareVisionScriptInterp, entry:NightmareVisionScriptEntry, actor:Dynamic):Void {
    interp.variables.set('record', function(message:String):Void log.push(message));
   },
   function(name:String, phase:String, error:Dynamic):Void throw name + '#' + phase + ':' + Std.string(error));

  // Event files are lazy, but once initialized they join the main group as in
  // initFunkinScript and receive later ordinary callbacks in source order.
  host.loadScope('global');
  eq(reads.join(','), 'owner-A/scripts/global.hx');
  host.call('onEvent', ['before', '1', '2']);
  eq(log.join(','), 'global:before:1:2');

  eq(host.callEvent('Alpha', 'onTrigger', ['a1', 'a2']), 7);
  eq(log.join(','), 'global:before:1:2,alpha:load,alpha:trigger:a1:a2');
  eq(reads.join(','), 'owner-A/scripts/global.hx,owner-A/data/events/Alpha.hx');
  host.call('onEvent', ['after-alpha', '3', '4']);
  eq(log.slice(-2).join(','), 'global:after-alpha:3:4,alpha:generic:after-alpha:3:4');

  host.callEvent('Beta', 'onTrigger', ['b1', 'b2']);
  host.callEvent('Alpha', 'onTrigger', ['a3', 'a4']);
  eq(reads.filter(function(path:String):Bool return path.indexOf('/Alpha.hx') >= 0).length, 1);
  eq(reads.filter(function(path:String):Bool return path.indexOf('/Beta.hx') >= 0).length, 1);
  if (reads.join(',').indexOf('owner-B/') >= 0) fail('loaded a foreign same-named event: ' + reads.join(','));
  eq(log.slice(-3).join(','), 'beta:load,beta:trigger:b1:b2,alpha:trigger:a3:a4');
  eq(host.group.members.length, 3);
  eq(host.eventGroup.members.length, 2);

  host.destroy();
  eq(log.slice(-3).join(','), 'global:destroy,alpha:destroy,beta:destroy');
 }
}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=45,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_lifecycle_wiring_order(self):
        source = (ROOT / "source" / "PlayState.hx").read_text()

        init = source.index("initializeNightmareVisionScripts();")
        gf_create = source.index("gf = addCharacter(SONG.gf")
        self.assertLess(init, gf_create, "stage/global NMV modules must precede actor creation")
        self.assertLess(source.index("loadNightmareVisionCharacter(gf);", gf_create),
                        source.index("dad = addCharacter(SONG.player2", gf_create))

        song_scope = source.index("nightmareVisionScripts.loadScope('song');")
        pre_generation = source.index("callNightmareVision('preNoteGeneration', []);", song_scope)
        generation = source.index("generateSong(SONG.song);", pre_generation)
        note_type_load = source.index("nightmareVisionNoteTypes.loadBeforeNoteGeneration();")
        self.assertLess(song_scope, pre_generation)
        self.assertLess(pre_generation, generation)
        self.assertLess(note_type_load, generation,
                        "chart-selected note-type modules must load before note generation")
        event_scope = source.index("nightmareVisionScripts.loadScope('event');", generation)
        self.assertLess(generation, event_scope,
                        "event modules should initialize after chart events are generated")

        create_post = source.index("callNightmareVision('onCreatePost', []);")
        super_create = source.index("super.create();", create_post)
        self.assertLess(create_post, super_create)

        event = extract_block(source, "function fireSongEvent(e:Dynamic)")
        self.assertLess(event.index("fireNativeSongEvent(e);"),
                        event.index("callNightmareVision('onEvent'"))
        self.assertLess(event.index("callNightmareVision('onEvent'"),
                        event.index("nightmareVisionScripts.callEvent("))
        initialization = extract_block(source, "function initializeNightmareVisionScripts()")
        self.assertNotIn("entry.scope == 'event'", initialization,
                         "supported event scripts must not be diagnosed as unsupported")
        self.assertIn("if (entry.scope == 'character_event')", initialization)
        self.assertNotIn("entry.scope == 'notetype'", initialization,
                         "notetype scripts are supported by NightmareVisionNoteTypeRuntime")

        # Shared StageHelper owns props in the live state already. Mounting
        # its sprite group again duplicates update/draw and propagates the
        # gameplay camera over explicitly assigned overlay cameras.
        self.assertIn("interp.variables.set('add', curStage.add)", initialization)
        self.assertNotIn("add(curStage)", initialization)
        self.assertIn("nightmareVisionAddActors = callNightmareVision('onAddSpriteGroups'", initialization)

        pause_start = source.index("if (controls.PAUSE && startedCountdown && canPause")
        pause_end = source.index("var canShowKeys = true;", pause_start)
        pause = source[pause_start:pause_end]
        self.assertLess(pause.index("callNightmareVision('onPause', [])"), pause.index("paused = true;"))

        countdown = extract_block(source, "public function startCountdown():Void")
        nmv_countdown = countdown.index("countdownResults.push(callNightmareVision('onStartCountdown', []));")
        hscript_countdown = countdown.index("callAllHScript('startCountdown', [], false, countdownResults);")
        self.assertLess(nmv_countdown, hscript_countdown)
        self.assertLess(countdown.index("if (EngineCompat.anyFunctionStop(countdownResults))"),
                        countdown.index("startedCountdown = true;"))
        self.assertIn("hxcCountdownHookDispatching = true;", countdown[:nmv_countdown])

    def test_donor_character_onload_precedes_parent_assignment(self):
        donor = ROOT.parent / "FNF-Example-Mods" / "misc" / "nightmare_vision_source_code" / "source" / "funkin" / "states" / "PlayState.hx"
        if not donor.is_file():
            self.skipTest("supplied Nightmare Vision gameplay source unavailable")
        source = donor.read_text()
        start_character = extract_block(source, "function startCharacterScript(name:String, char:Character)")
        init_script = extract_block(source, "public function initFunkinScript(filePath:String, ?name:String)")
        self.assertLess(start_character.index("initFunkinScript(hscriptPath)"),
                        start_character.index("script.set('parent', char)"))
        self.assertLess(init_script.index("script.execute();"),
                        init_script.index("script.call('onLoad')"))


if __name__ == "__main__":
    unittest.main()
