"""Psych Lua behaviours imported scripts rely on: block-ending returns, sized sprites, character names."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''class Main {
 static function main() {
  var source = "function finish(a, b)\n if a then\n  first()\n  return\n elseif b == 'x' then\n  second()\n else\n  third()\n  return\n end\nend\n"
   + "function loop()\n while busy do\n  if done then\n   return\n  else\n   again()\n  end\n end\nend\n"
   + "function value()\n return\n  compute(1,\n   2)\nend\n";
  var result = LuaCompat.translate(source, 'returns.lua');
  if (!result.supported) throw result.diagnostics.join(' | ');
  new hscript.Parser().parseString(result.hscript);
  var flat = ~/\s+/g.replace(result.hscript, ' ');
  if (flat.indexOf("return; } else if (b == 'x' ) {") < 0) throw 'bare return swallowed the elseif: ' + flat;
  if (flat.indexOf('return; } else { again();') < 0) throw 'bare return swallowed the else: ' + flat;
  if (flat.indexOf('return compute(1, 2)') < 0) throw 'wrapped return value lost: ' + flat;
 }
}'''


class PsychLuaScriptParityTest(unittest.TestCase):
    def test_bare_return_ends_at_the_next_block_keyword(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            (Path(temp) / 'Main.hx').write_text(FIXTURE, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                                     '-cp', temp, '--run', 'Main'], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_resized_sprites_refresh_their_hitbox_and_scripts_know_the_cast(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
        self.assertIn('function compatSetGraphicSize(name:Dynamic, width:Int, ?height:Int, ?updateHitbox:Null<Bool>):Void {', play)
        self.assertIn('if (updateHitbox != false) (cast object : FlxSprite).updateHitbox();', play)
        self.assertIn('for (name => value in psychCharacterNames()) interp.variables.set(name, value);', play)
        self.assertIn('for (name => value in psychCharacterNames()) setAllHaxeVar(name, value);', play)
        for name in ('boyfriendName', 'dadName', 'gfName'):
            self.assertIn("'" + name + "' =>", play)

    def test_older_psych_names_and_arguments_keep_working(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
        # Exclusions arrive as comma separated text, and a negative frame must never reach Flixel.
        self.assertIn('public static function compatRandomExclusions(exclude:Dynamic):Array<Float> {', play)
        self.assertIn('function compatRandomInt(min:Int = 0, max:Int = FlxMath.MAX_VALUE_INT, ?exclude:Dynamic):Int {', play)
        self.assertIn('var indices = [for (index in compatNormalizeAnimationIndices(frames)) if (index >= 0) index];', play)
        # Flat 0.6 preference names, judgement counters and the song name still answer.
        self.assertIn('installPsychLegacyPropertyNames(interp);\n\t\tPsychLuaApiResults.install(interp);', play)
        self.assertIn('if (value == null && args.length >= 2 && compatSourceClientPrefs(args[0]) != null) return compatGetPropertyFromClass(args[0], args[1]);', play)
        self.assertIn('if (value == null && args.length > 0) return compatGetProperty(args[0]);', play)
        self.assertIn("case 'songname': return psychSongPath(SONG == null ? '' : Std.string(SONG.song));", play)
        for name in ('noteOffset', 'framerate', 'songPath', 'curSection', 'buildTarget'):
            self.assertIn("'" + name + "' =>", play)
        self.assertIn("setAllHaxeVar('curSection', curSection);", play)
        self.assertIn('if (showRatings && showRating)', play)
        self.assertIn('&& showRatings && showComboNum)', play)
        discord = (ROOT / 'source/PsychDiscordBindings.hx').read_text(encoding='utf-8')
        self.assertIn("interp.variables.set('changePresence', interp.variables.get('changeDiscordPresence'));", discord)

    def test_random_exclusions_and_song_paths(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
            def body(marker):
                start = play.index(marker); end = play.index('\n\t}\n', start) + 4
                return play[start:end]
            (Path(temp) / 'Probe.hx').write_text('class Probe {\n' + body('\tpublic static function compatRandomExclusions(')
                + body('\tpublic static function psychSongPath(') + '}\n', encoding='utf-8')
            (Path(temp) / 'Main.hx').write_text("""class Main { static function main() {
  if (Probe.compatRandomExclusions('-1').join('|') != '-1') throw 'single exclusion';
  if (Probe.compatRandomExclusions(' 1, 2 ,x,3').join('|') != '1|2|3') throw 'text exclusions';
  if (Probe.compatRandomExclusions([4, 5]).join('|') != '4|5') throw 'list exclusions';
  if (Probe.compatRandomExclusions(null).length != 0 || Probe.compatRandomExclusions('').length != 0) throw 'empty exclusions';
  if (Probe.psychSongPath('Safety Lullaby') != 'safety-lullaby') throw 'song path';
  if (Probe.psychSongPath("Don't Stop!") != 'dont-stop') throw 'punctuation';
} }""", encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', temp, '--run', 'Main'], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_engine_version_labels_are_blanked(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            (Path(temp) / 'Main.hx').write_text("""class Main { static function main() {
  for (text in ['Psych Engine v0.7.0', 'Psych Engine 0.6.3', ' psych engine v1.0.4 ', 'Kade Engine 1.8', 'Codename Engine v1.0.1', 'Engine v2', "Mic'd Up Engine ver. 2.0.3", 'OS Engine - v1.5.1'])
   if (!SourceEngineWatermark.matches(text) || SourceEngineWatermark.clean(text) != '') throw 'kept ' + text;
  for (text in ['Score: 0', '- Safety Lullaby [NORMAL] -', 'The engine stalls at 3', 'Engine', 'Psych Engine', 'v0.7.0', 'Start your engine 2 times and then go', '', 'Psych Engine v0.7.0\nSecond line'])
   if (SourceEngineWatermark.matches(text) || SourceEngineWatermark.clean(text) != text) throw 'blanked ' + text;
  if (SourceEngineWatermark.matches(null) || SourceEngineWatermark.clean(5) != 5) throw 'non text';
} }""", encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', temp, '--run', 'Main'], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        self.assertIn("for (name in ['makeLuaText', 'setTextString']) {", play)
        self.assertIn('if (args.length > 1) args[1] = SourceEngineWatermark.clean(args[1]);', play)

    def test_older_nightmare_vision_imports_read_their_own_files_without_an_index(self):
        assets = (ROOT / 'source/PsychOwnerOpenFlAssets.hx').read_text(encoding='utf-8')
        self.assertIn("context.engine == 'Nightmare Vision' && (selected == null || selected.result.state == 'no-index')", assets)
        self.assertIn('if (ownerPath.blocked || ownerPath.owned) return ownerPath;', assets)


if __name__ == '__main__':
    unittest.main()
