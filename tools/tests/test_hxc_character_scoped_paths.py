"""HXC character hooks may use the owner-scoped Paths proxy and the engine precache, like song and stage scripts."""
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / '.haxelib/hscript/2,5,0'

MAIN = r'''import hscript.Interp;
import hscript.Parser;
class Main {
 static function character(body:String):HxcCompat.HxcCompatResult
  return HxcCompat.analyze("class Probe extends SparrowCharacter { function new() { super('probe'); } "
   + "override function onCreate(event) { super.onCreate(event); " + body + " } }", 'scripts/characters/probe.hxc');
 static function main() {
  var accepted = [
   "FunkinMemory.cacheSound(Paths.sound('characters/warmup'));",
   "var atlas = Paths.getSparrowAtlas('characters/overlay');",
   "FunkinMemory.permanentCacheTexture(Paths.image('characters/flash'));",
   "var font = Paths.font('quote.ttf'); FlxG.sound.play(Paths.sound('characters/hit'));"
  ];
  for (body in accepted) {
   var result = character(body);
   if (result.kind != 'character' || result.characterHookGaps.indexOf('onCreate') >= 0)
    throw 'scoped asset use was dropped: ' + body + ' -> ' + result.characterHookGaps;
   if (result.generatedHscript.indexOf('FunkinMemory') >= 0)
    throw 'cache warm-ups must reach the engine precache: ' + result.generatedHscript;
  }
  // Members the scoped proxy does not implement stay reported gaps.
  for (body in ["Paths.animateAtlas('characters/big');", "trace(Paths.currentLevel);",
   "FlxAnimationUtil.addTextureAtlasAnimations(this, []);"]) {
   var result = character(body);
   if (result.characterHookGaps.indexOf('onCreate') < 0)
    throw 'an unscoped operation was accepted: ' + body;
  }
  // The generated hook runs against the proxy once PlayState has rewritten Paths.
  var generated = character("FunkinMemory.cacheSound(Paths.sound('characters/warmup')); var a = Paths.getSparrowAtlas('x');").generatedHscript;
  var interp = new Interp();
  var calls:Array<String> = [];
  interp.variables.set('hxcPaths', {sound: function(key:String) { calls.push('sound:' + key); return 'snd'; },
   getSparrowAtlas: function(key:String) { calls.push('atlas:' + key); return 'frames'; }});
  interp.variables.set('hxcCacheSound', function(asset:Dynamic) { calls.push('cache:' + asset); return null; });
  interp.variables.set('hxcCharacter', function() return null);
  interp.variables.set('HxcCompatRuntime', HxcCompatRuntime);
  var scoped = new EReg('\\bPaths\\s*\\.', 'g').replace(generated, 'hxcPaths.');
  interp.execute(new Parser().parseString(scoped));
  var start:Dynamic = interp.variables.get('start');
  if (start == null) throw 'character start hook missing: ' + generated;
  start(null);
  if (calls.join(',') != 'sound:characters/warmup,cache:snd,atlas:x') throw 'hook ran ' + calls.join(',');
 }
}
'''


class HxcCharacterScopedPathsTest(unittest.TestCase):
    def test_scoped_asset_hooks_are_kept_and_unscoped_ones_reported(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(HSCRIPT), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_accepted_members_exist_on_the_playstate_proxy(self):
        compat = (ROOT / 'source/HxcCompat.hx').read_text(encoding='utf-8')
        listed = compat[compat.index('CHARACTER_SCOPED_PATHS_MEMBERS:Array<String> = ['):]
        listed = re.findall(r"'([A-Za-z]+)'", listed[:listed.index('];')])
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        proxy = play[play.index('function makeHxcPathsProxy('):]
        proxy = proxy[:proxy.index('\n\t}\n')]
        self.assertGreater(len(listed), 10)
        for member in listed:
            self.assertIn("setField(proxy, '%s'" % member, proxy, member)
        rewrite = (ROOT / 'source/EngineCompat.hx').read_text(encoding='utf-8')
        self.assertIn("replace(source, 'hxcPaths.')", rewrite)


if __name__ == '__main__':
    unittest.main()
