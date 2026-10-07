"""Executed contracts for NMV note-type registration, callbacks, and Note API."""
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


class NightmareVisionNoteTypeRuntimeTest(unittest.TestCase):
    def compile_haxe(self, source: str) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / "Main.hx").write_text(source, newline='\n')
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

    def test_note_type_modules_share_lifecycle_group_and_targeted_dispatch(self):
        self.compile_haxe(r'''
import NightmareVisionScriptDiscovery.NightmareVisionScriptEntry;
import NightmareVisionScriptDiscovery.NightmareVisionScriptPlan;
import NightmareVisionNoteTypeRuntime.NightmareVisionNoteApiBridge;

class LiveNote {
 public var name:String;
 public var noteType:String;
 public var api:NightmareVisionNoteApiBridge;
 public var prefix(get, never):String;
 public var suffix(get, never):String;
 public function new(name:String, noteType:String, api:NightmareVisionNoteApiBridge) {
  this.name = name; this.noteType = noteType; this.api = api;
 }
 function get_prefix():String return api.prefix(this);
 function get_suffix():String return api.suffix(this);
}

class Main {
 static var sources:Map<String, String> = new Map();
 static var log:Array<String> = [];
 static function fail(message:String):Void throw message;
 static function eq(actual:Dynamic, expected:Dynamic):Void {
  if (actual != expected) fail('expected ' + expected + ', got ' + actual);
 }
 static function entry(scope:String, name:String, relative:String):NightmareVisionScriptEntry {
  return {scope:scope, name:name, relative:relative, path:'owner/' + relative};
 }
 static function main():Void {
  var plan:NightmareVisionScriptPlan = {
   root:'owner', baseAssetsRoot:'', song:'song', stage:'stage', coverageNotes:[],
   scripts:[
    entry('global', 'global', 'scripts/global.hx'),
    entry('notetype', 'Ice Note', 'data/notetypes/Ice Note.hx'),
    entry('notetype', 'Other Note', 'data/notetypes/Other Note.hx')
   ]
  };
  sources.set('owner/scripts/global.hx', '
   function onCreatePost() { record("global:create"); return Function_Continue; }
   function onUpdate() { record("global:update"); return Function_Continue; }
   function onDestroy() { record("global:destroy"); return Function_Continue; }
  ');
  sources.set('owner/data/notetypes/Ice Note.hx', '
   function onCreatePost() { record("ice:create"); return Function_Continue; }
   function onUpdate() { record("ice:update"); return Function_Continue; }
   function onDestroy() { record("ice:destroy"); return Function_Continue; }
   function setupNote(note) { record("ice:setup:" + note.name + ":this=" + this.name); return Function_Continue; }
   function spawnNote(note) { record("ice:spawn:" + note.name); return Function_Stop; }
   function postSpawnNote(note) { record("ice:postSpawn:" + note.name); return Function_Continue; }
   function update(note, elapsed) { record("ice:updateNote:" + this.name + ":" + elapsed); return Function_Continue; }
   function onReloadNote(note, prefix, texture, suffix) {
    if (note.prefix != prefix) throw "prefix must be visible before onReloadNote";
    record("ice:reload:" + this.name); return Function_Continue;
   }
   function postReloadNote(note, prefix, texture, suffix) { record("ice:postReload:" + this.name); return Function_Continue; }
   function hit(note, fieldID) { record("ice:hit:" + note.name + ":" + fieldID); return Function_Continue; }
   function goodNoteHit(note, fieldID) { record("ice:good:" + note.name + ":" + fieldID); return Function_Continue; }
   function opponentNoteHit(note, fieldID) { record("ice:opponent:" + note.name + ":" + fieldID); return Function_Continue; }
   function extraNoteHit(note, fieldID) { record("ice:extra:" + note.name + ":" + fieldID); return Function_Continue; }
   function noteMiss(note, fieldID) { record("ice:miss:" + note.name + ":" + fieldID); return Function_Continue; }
  ');
  sources.set('owner/data/notetypes/Other Note.hx', '
   function onCreatePost() { record("other:create"); return Function_Continue; }
   function onUpdate() { record("other:update"); return Function_Continue; }
   function onDestroy() { record("other:destroy"); return Function_Continue; }
   function goodNoteHit(note, fieldID) { record("other:wrong-owner:" + fieldID); return Function_Continue; }
  ');

  var reads:Map<String, Int> = new Map();
  var host = new NightmareVisionGameplayScripts({}, plan,
   function(path:String):String {
    reads.set(path, (reads.exists(path) ? reads.get(path) : 0) + 1);
    if (!sources.exists(path)) throw 'missing script: ' + path;
    return sources.get(path);
   },
   function(interp:NightmareVisionScriptInterp, entry:NightmareVisionScriptEntry, actor:Dynamic):Void {
    interp.variables.set('record', function(value:String):Void log.push(value));
    interp.variables.set('Function_Continue', NightmareVisionScriptGroup.CONTINUE_FUNC);
    interp.variables.set('Function_Stop', NightmareVisionScriptGroup.STOP_FUNC);
    interp.variables.set('Function_Halt', NightmareVisionScriptGroup.HALT_FUNC);
   },
   function(name:String, phase:String, error:Dynamic):Void fail(name + '#' + phase + ':' + Std.string(error)));
  host.loadScope('global');
  var api = new NightmareVisionNoteApiBridge(
   function(note:Dynamic):String return 'NOTE_assets',
   function(note:Dynamic, path:String):Bool { log.push('atlas:' + path); return true; });
  var runtime = new NightmareVisionNoteTypeRuntime(host, api);
  runtime.loadBeforeNoteGeneration();
  runtime.loadBeforeNoteGeneration();
  eq(host.group.members.length, 3);
  if (!host.group.exists('Ice Note') || !host.group.exists('Other Note'))
   fail('note types must be registered under their authored names in the main group');
  if (host.group.exists('data/notetypes/Ice Note.hx'))
   fail('note type was registered twice under its relative path');
  eq(reads.get('owner/data/notetypes/Ice Note.hx'), 1);
  eq(reads.get('owner/data/notetypes/Other Note.hx'), 1);

  // Main-group lifecycle broadcasts include note-type scripts exactly once.
  host.call('onCreatePost');
  host.call('onUpdate');
  eq(log.join(','), 'global:create,ice:create,other:create,global:update,ice:update,other:update');

  var note:Dynamic = new LiveNote('ice-1', 'Ice Note', api);
  var iceScript = host.group.getScript('Ice Note');
  var priorReceiver:Dynamic = {name:'outer-scope'};
  iceScript.interp.variables.set('this', priorReceiver);
  eq(runtime.setupNote(note), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(iceScript.interp.variables.get('this'), priorReceiver);
  iceScript.interp.variables.remove('this');
  eq(runtime.spawnNote(note), NightmareVisionScriptGroup.STOP_FUNC);
  eq(runtime.postSpawnNote(note), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(runtime.hit(note, 2), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(runtime.goodNoteHit(note, 2), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(runtime.opponentNoteHit(note, 2), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(runtime.extraNoteHit(note, 2), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(runtime.noteMiss(note, 2), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(log.slice(6).join(','), 'ice:setup:ice-1:this=ice-1,ice:spawn:ice-1,ice:postSpawn:ice-1,'
   + 'ice:hit:ice-1:2,ice:good:ice-1:2,ice:opponent:ice-1:2,ice:extra:ice-1:2,ice:miss:ice-1:2');

  eq(runtime.update(note, 0.5), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(runtime.reloadNote(note, 'ice/', 'UI/game/notes/NOTE_assets'), true);
  eq(log.slice(-5).join(','), 'ice:miss:ice-1:2,ice:updateNote:ice-1:0.5,ice:reload:ice-1,'
   + 'atlas:UI/game/notes/ice/NOTE_assets,ice:postReload:ice-1');

  // For generic note broadcasts, exclude every registered note type so only
  // the selected owner receives its targeted callback.
  host.call('goodNoteHit', [note, 2], false, host.noteTypeExclusions());
  eq(log[log.length - 1], 'ice:postReload:ice-1');
  eq(host.callNoteType('Missing Note', 'goodNoteHit', [note, 2]),
   NightmareVisionScriptGroup.CONTINUE_FUNC);

  // Destroy is one ordinary main-group lifecycle broadcast and releases all.
  runtime.releaseNote(note);
  host.destroy();
  eq(log.slice(-3).join(','), 'global:destroy,ice:destroy,other:destroy');
  eq(host.group.released, true);
  runtime.destroy();
 }
}
''')

    def test_note_api_bridge_matches_prefix_palette_rgb_and_can_miss_contract(self):
        self.compile_haxe(r'''
import NightmareVisionNoteTypeRuntime.NightmareVisionNoteApiBridge;

class Main {
 static function fail(message:String):Void throw message;
 static function eq(actual:Dynamic, expected:Dynamic):Void {
  if (actual != expected) fail('expected ' + expected + ', got ' + actual);
 }
 static function main():Void {
  var operations:Array<String> = [];
  var note:Dynamic = {texture:'default/NOTE_assets'};
  var api = new NightmareVisionNoteApiBridge(
   function(value:Dynamic):String return value.texture,
   function(value:Dynamic, path:String):Bool {
    operations.push('load:' + path);
    value.texture = path;
    return true;
   },
   function(value:Dynamic, enabled:Bool):Void operations.push('rgb:' + enabled),
   function(value:Dynamic, colors:Array<Dynamic>):Void {
    operations.push('colors:' + (colors == null ? 'null' : colors.join('/')));
   },
   function(value:Dynamic):Bool return false);
  api.attach(note);
  eq(api.getRgbEnabled(note), false);
  eq(api.canMiss(note), false);
  eq(api.prefix(note), '');
  eq(api.suffix(note), '');
  eq(api.setCanMiss(note, true), true);
  eq(api.canMiss(note), true);

  // Prefix is inserted before the final path component, preserving the
  // package-relative directory; the loader is the owner-scoped host seam.
  eq(api.reloadNote(note, 'ice/', 'UI/game/notes/NOTE_assets'), true);
  eq(api.atlasPath(note), 'UI/game/notes/ice/NOTE_assets');
  eq(api.prefix(note), 'ice/');
  eq(operations[0], 'load:UI/game/notes/ice/NOTE_assets');
  eq(api.reloadNote(note, '', 'UI/game/notes/NOTE_assets', '-alt'), true);
  eq(api.atlasPath(note), 'UI/game/notes/ice/NOTE_assets-alt');
  eq(api.suffix(note), '-alt');
  var palette:Array<Dynamic> = [0xFF101010, 0xFFFF0000, 0xFF990022];
  api.setCustomColor(note, palette);
  api.setRgbEnabled(note, false);
  operations.resize(0);
  api.syncNote(note);
  eq(operations.join(','), 'colors:-15724528/-65536/-6750174,rgb:false');
  eq(api.customColors(note).length, 3);

  api.setCanMiss(note, false);
  eq(api.canMiss(note), false);
  api.resetNote(note, true, false);
  eq(api.getRgbEnabled(note), true);
  eq(api.canMiss(note), false);
  eq(api.prefix(note), '');
  eq(api.suffix(note), '');
  eq(api.customColors(note), null);
  api.releaseNote(note);
  eq(api.canMiss(note), false);
  api.clear();
 }
}
''')

    def test_field_skin_reload_preserves_each_note_prefix_and_reassigns_base(self):
        self.compile_haxe(r'''
import NightmareVisionNoteTypeRuntime.NightmareVisionNoteApiBridge;

class FakeNote {
 public var noteType:String;
 public var rgbEnabled:Bool = true;
 public function new(noteType:String) this.noteType = noteType;
}

class Main {
 static function fail(message:String):Void throw message;
 static function eq(actual:Dynamic, expected:Dynamic):Void {
  if (actual != expected) fail('expected ' + expected + ', got ' + actual);
 }
 static function main():Void {
  var loads:Array<String> = [];
  var api = new NightmareVisionNoteApiBridge(
   function(note:Dynamic):String return 'UI/game/notes/NOTE_assets',
   function(note:Dynamic, path:String):Bool {
    loads.push(note.noteType + ':' + path);
    return true;
   },
   function(note:Dynamic, enabled:Bool):Void note.rgbEnabled = enabled);
  var runtime = new NightmareVisionNoteTypeRuntime(null, api);
  var bullet = new FakeNote('Bullet');
  var accel = new FakeNote('Accelerant');
  api.attach(bullet);
  api.attach(accel);

  eq(runtime.reloadNote(bullet, 'bullet/'), true);
  eq(runtime.reloadNote(accel, 'accel/'), true);
  eq(api.atlasPath(bullet), 'UI/game/notes/bullet/NOTE_assets');
  eq(api.atlasPath(accel), 'UI/game/notes/accel/NOTE_assets');

  // Field attachment changes the base texture like source Note.texture's
  // setter. The two per-note prefixes survive independently.
  eq(runtime.reloadForFieldSkin(bullet, 'UI/game/notes/NOTE_assets', false), true);
  eq(api.atlasPath(bullet), 'UI/game/notes/bullet/NOTE_assets');
  eq(bullet.rgbEnabled, false);
  eq(runtime.reloadForFieldSkin(accel, 'UI/game/notes/NOTE_assets', true), true);
  eq(api.atlasPath(accel), 'UI/game/notes/accel/NOTE_assets');
  eq(accel.rgbEnabled, true);

  // Reassigning the field skin reloads its new base with the same prefix;
  // reassigning the identical texture is the source setter's no-op.
  eq(runtime.reloadForFieldSkin(bullet, 'UI/alternate/NOTE_assets', true, true), true);
  eq(api.atlasPath(bullet), 'UI/alternate/bullet/NOTE_assets');
  var loadCount = loads.length;
  eq(runtime.reloadForFieldSkin(bullet, 'UI/alternate/NOTE_assets', false), true);
  eq(loads.length, loadCount);
  eq(runtime.reloadForFieldSkin(bullet, 'UI/alternate/NOTE_assets', true, true), true);
  eq(loads.length, loadCount + 1);
  eq(api.atlasPath(accel), 'UI/game/notes/accel/NOTE_assets');
  eq(loads.join(','), 'Bullet:UI/game/notes/bullet/NOTE_assets,'
   + 'Accelerant:UI/game/notes/accel/NOTE_assets,'
   + 'Bullet:UI/game/notes/bullet/NOTE_assets,'
   + 'Accelerant:UI/game/notes/accel/NOTE_assets,'
   + 'Bullet:UI/alternate/bullet/NOTE_assets,'
   + 'Bullet:UI/alternate/bullet/NOTE_assets,'
   + 'Bullet:UI/alternate/bullet/NOTE_assets');
  runtime.releaseNote(bullet);
  runtime.releaseNote(accel);
  runtime.destroy();
 }
}
''')


if __name__ == "__main__":
    unittest.main()
