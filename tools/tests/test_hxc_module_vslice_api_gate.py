"""The HXC module gate admits the V-Slice API the engine now provides and still rejects the rest."""
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function module(body:String):Dynamic
  return HxcCompat.analyze("class Probe extends Module { function new() { super('probe'); } override function onUpdate(event) { "
   + body + " } }", 'scripts/modules/Probe.hxc');
 static function safe(body:String):Void {
  var result = module(body);
  if (result.kind != 'module' || !result.moduleSafe)
   throw 'expected executable: ' + body + ' :: ' + result.moduleSafetyReasons.join(',');
 }
 static function unsafe(body:String):Void {
  if (module(body).moduleSafe)
   throw 'expected rejection: ' + body;
 }
 static function main() {
  // Registries, playlist and launch are bound base-game facades.
  safe("var song = SongRegistry.instance.fetchEntry('x'); if (song != null) trace(song.songName);");
  safe("for (id in LevelRegistry.instance.listSortedLevelIds()) trace(LevelRegistry.instance.fetchEntry(id).getTitle());");
  safe("var player = PlayerRegistry.instance.fetchEntry('bf'); trace(player.getName());");
  safe("PlayStatePlaylist.reset(); PlayStatePlaylist.campaignId = null;");
  safe("LoadingState.loadPlayState({targetSong: SongRegistry.instance.fetchEntry('x'), targetDifficulty: 'hard'}, true);");
  safe("var data = Json.parse('{}'); trace(Date.now().getTime());");
  // V-Slice PlayState instance members the native PlayState now has.
  safe("if (PlayState.instance.isChartingMode || PlayState.instance.isPracticeMode) return; trace(PlayState.instance.currentDifficulty + PlayState.instance.currentVariation);");
  safe("PlayState.instance.resetCamera(); PlayState.instance.togglePauseButton(false); trace(PlayState.instance.camPause); if (PlayState.instance.justUnpaused) return;");
  safe("PlayState.instance.currentInstrumental = PlayState.instance.currentChart.characters.instrumental;");
  safe("for (data in PlayState.instance.currentChart.events) trace(data.eventKind); trace(PlayState.instance.currentChart.timeChanges);");
  safe("trace(PlayState.instance.currentChart.variation);");
  // Facade members with a base-game implementation.
  safe("VideoCutscene.pauseVideo(); VideoCutscene.resumeVideo(); VideoCutscene.restartVideo(); VideoCutscene.finishVideo(); VideoCutscene.hideVideo(); VideoCutscene.showVideo();");
  safe("FullScreenScaleMode.addCutouts(3.0, FlxEase.quintOut); trace(FullScreenScaleMode.cutoutSize.y + FullScreenScaleMode.gameNotchSize.x); if (FullScreenScaleMode.instance != null) return;");
  safe("FunkinSound.setMusic(null);");
  // Still rejected: fields the chart view does not carry, unknown members and unknown roots.
  unsafe("trace(PlayState.instance.currentChart.noteStyle);");
  unsafe("PlayState.instance.vocals = PlayState.instance.currentChart.buildVocals('x');");
  unsafe("trace(PlayState.instance.currentChart.characters.somethingElse);");
  unsafe("VideoCutscene.rewindVideo();");
  unsafe("PlayState.instance.notARealMember = 1;");
  unsafe("NotSeededRegistry.instance.fetchEntry('x');");
  // A type test against a class no interpreter binds would throw on every dispatch.
  unsafe("if (!Std.isOfType(FlxG.state, OptionsState)) return; trace('x');");
  unsafe("if (Std.isOfType(event.targetState, NotBound)) trace('x');");
  safe("if (Std.isOfType(FlxG.state, PlayState) || Std.isOfType(FlxG.state, FreeplayState)) trace('x');");
  // The desktop FullScreenScaleMode view: no cutouts, no instance, points that answer set().
  var scale:Dynamic = HxcCompatRuntime.fullScreenScaleMode;
  if (scale.instance != null || scale.cutoutSize.y != 0 || scale.gameNotchSize.x != 0 || scale.wideScale.x != 1)
   throw 'desktop scale view values';
  scale.addCutouts(3.0, null);
  scale.removeCutouts();
  if (scale.cutoutSize.set(4, 5) != scale.cutoutSize || scale.cutoutSize.x != 4 || scale.cutoutSize.y != 5)
   throw 'scale points answer set()';
  scale.cutoutSize.set(0, 0);
  if (HxcCompatRuntime.setMusic(null) != null)
   throw 'setMusic ignores a missing sound';
 }
}
'''


class HxcModuleVSliceApiGateTest(unittest.TestCase):
    def test_gate_admits_provided_api_only(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                '-cp', folder, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_new_module_root_is_bound_by_the_shared_interpreter_setup(self):
        """A root the gate trusts must be a value every script interpreter receives."""
        plugin = (ROOT / 'source/PluginManager.hx').read_text(encoding='utf-8')
        catalogue = (ROOT / 'source/ScriptNativeClasses.hx').read_text(encoding='utf-8')
        seeded = set(re.findall(r'variables\.set\(\s*["\']([A-Za-z_]\w*)["\']', plugin))
        seeded |= set(re.findall(r"entry\('([A-Za-z_]\w*)'", catalogue))
        for name in ['SongRegistry', 'LevelRegistry', 'PlayerRegistry', 'PlayStatePlaylist', 'LoadingState', 'Type',
                     'VideoCutscene', 'FunkinSound', 'Json', 'Date', 'String', 'Array', 'FlxBarFillDirection',
                     'FlxRect', 'FlxSort', 'FlxSpriteUtil', 'FlxEmitter', 'IntMap', 'ObjectMap', 'AnimateAtlasUtil']:
            self.assertIn(name, seeded, name + ' is trusted by the module gate but never bound')
        gate = (ROOT / 'source/HxcCompat.hx').read_text(encoding='utf-8')
        start = gate.index('static function moduleKnownRoot')
        roots = set(re.findall(r"'([A-Za-z_]\w*)'", gate[start:gate.index('default: false', start)]))
        for name in ['SongRegistry', 'LevelRegistry', 'PlayerRegistry', 'LoadingState', 'Type', 'FunkinSound']:
            self.assertIn(name, roots)


if __name__ == '__main__':
    unittest.main()
