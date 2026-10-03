"""Focused generic HXC song-credit banner compatibility coverage."""
from haxe_test_support import HAXE_COMMAND

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR_ROOT = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE"
)
DONOR = DONOR_ROOT / "scripts/modules/Credits.hxc"


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain unavailable")
class HxcRound16CreditsTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-round16-credits-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp", str(ROOT / "source"),
                    "-cp", folder,
                    "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                    "-main", "Main", "--interp",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_synthetic_complete_body_executes_only_native_boundaries(self):
        source = r'''class GenericCredits extends Module {
  var metaName:FlxText;
  var metaIcon:FunkinSprite;
  var metaArtist:FlxText;
  var isPixel:Bool;
  var metaNameTween:FlxTween;
  var metaIconTween:FlxTween;
  var metaArtistTween:FlxTween;
  var tweenOutTimer:FlxTimer;
  function new() { super('Credits'); }
  override function onPause(event) {
    super.onPause(event);
    if (tweenOutTimer != null && tweenOutTimer.active == true) tweenOutTimer.active = false;
    if (metaNameTween != null) metaNameTween.active = false;
    if (metaIconTween != null) metaIconTween.active = false;
    if (metaArtistTween != null) metaArtistTween.active = false;
  }
  override function onResume(event) {
    super.onResume(event);
    if (tweenOutTimer != null && tweenOutTimer.active == false) tweenOutTimer.active = true;
    if (metaNameTween != null) metaNameTween.active = true;
    if (metaIconTween != null) metaIconTween.active = true;
    if (metaArtistTween != null) metaArtistTween.active = true;
  }
  function cleanup() {
    if (tweenOutTimer != null) { tweenOutTimer.cancel(); tweenOutTimer.destroy(); tweenOutTimer = null; }
    if (metaName != null) { metaNameTween.cancel(); PlayState.instance.remove(metaName); metaName.destroy(); metaName = null; }
    if (metaIcon != null) { metaIconTween.cancel(); PlayState.instance.remove(metaIcon); metaIcon.destroy(); metaIcon = null; }
    if (metaArtist != null) { metaArtistTween.cancel(); PlayState.instance.remove(metaArtist); metaArtist.destroy(); metaArtist = null; }
  }
  function onSongRetry(event:ScriptEvent) { super.onSongRetry(event); cleanup(); }
  function manualCreditsSummon() {}
  function onSongStart(event) {
    super.onSongStart(event);
    cleanup();
    isPixel = (PlayState.instance.currentStageId.toLowerCase().indexOf('pixel') != -1 ||
      PlayState.instance.playerStrumline.noteStyle.id.toLowerCase().indexOf('pixel') != -1);
    var songKey:String = PlayState.instance.currentSong.id.toLowerCase();
    var iconName:String = isPixel ? 'pen-pixel' : 'pen';
    switch (songKey) {
      case 'libitina': iconName = 'file';
      case 'drinks-on-me': iconName = 'shaker';
      case 'your-demise': iconName = 'pen-demise';
    }
    metaName = new FlxText(20, 15, 0, PlayState.instance.currentChart.songName, 36);
    metaIcon = FunkinSprite.create(0, 0, 'songCredits/' + iconName);
    metaArtist = new FlxText(38, 38, 0, PlayState.instance.currentChart.songArtist, 20);
    PlayState.instance.add(metaName);
    PlayState.instance.add(metaIcon);
    PlayState.instance.add(metaArtist);
    manualCreditsSummon();
  }
}'''
        main = f'''import hscript.Interp;
import hscript.Parser;
class PlayState {{
  public static var instance:PlayState;
  public var clears:Int = 0;
  public var shows:Int = 0;
  public var pauses:Int = 0;
  public var resumes:Int = 0;
  public var shownIcon:String = '';
  public var shownPixel:Bool = false;
  public function new() {{}}
  public function hxcSongCreditsPixel():Bool return true;
  public function hxcClearSongCredits():Bool {{ clears++; return true; }}
  public function hxcShowSongCredits(song:Dynamic, artist:Dynamic, pixel:Bool, icon:String, root:String):Bool {{
    shows++; shownIcon = icon; shownPixel = pixel; return song != null && root == 'assets/imported_mods/test-root';
  }}
  public function hxcPauseSongCredits():Bool {{ pauses++; return true; }}
  public function hxcResumeSongCredits():Bool {{ resumes++; return true; }}
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, 'scripts/modules/GenericCredits.hxc');
    if (!result.moduleSafe || !result.moduleInitializationSafe
      || hasCode(result, 'unsupported-hxc-module-body')
      || hasCode(result, 'unsupported-hxc-callback-body'))
      fail('synthetic Credits safety: ' + result.moduleSafetyReasons.join(','));
    var generated = result.generatedHscript;
    for (required in ['showSongCredits', 'clearSongCredits', 'pauseSongCredits', 'resumeSongCredits'])
      if (generated.indexOf(required) < 0) fail('missing Credits bridge: ' + required + '\\n' + generated);
    if (generated.indexOf('new FlxText') >= 0 || generated.indexOf('FunkinSprite.create') >= 0
      || generated.indexOf('currentChart') >= 0)
      fail('donor Credits graph escaped: ' + generated);
    new Parser().parseString(generated);

    HxcCompatRuntime.clear();
    PlayState.instance = new PlayState();
    var interp = new Interp();
    interp.variables.set('HxcCompatRuntime', HxcCompatRuntime);
    interp.variables.set('PlayState', PlayState);
    interp.variables.set('Std', Std);
    interp.variables.set('SONG', {{song: 'libitina', songArtist: 'Synthetic Artist'}});
    interp.variables.set('hxcAssetRoot', 'assets/imported_mods/test-root');
    interp.execute(new Parser().parseString(generated));
    Reflect.callMethod(null, interp.variables.get('songStart'), [null]);
    Reflect.callMethod(null, interp.variables.get('pause'), [null]);
    Reflect.callMethod(null, interp.variables.get('resume'), [null]);
    Reflect.callMethod(null, interp.variables.get('songRetry'), [null]);
    if (PlayState.instance.shows != 1 || PlayState.instance.shownIcon != 'file'
      || !PlayState.instance.shownPixel || PlayState.instance.pauses != 1
      || PlayState.instance.resumes != 1 || PlayState.instance.clears != 2)
      fail('synthetic Credits execution: ' + PlayState.instance.shows + '/'
        + PlayState.instance.shownIcon + '/' + PlayState.instance.clears);
    if (HxcCompatRuntime.songCreditsIcon('../escape') != '') fail('icon path escaped');

    var partial = HxcCompat.analyze(
      "class Partial extends Module {{ function onSongStart(event) {{ "
        + "var iconName = event.value; FunkinSprite.create(0, 0, 'songCredits/' + iconName); }} }}",
      'scripts/modules/partial-credits.hxc');
    if (partial.moduleSafe || !hasCode(partial, 'unsupported-hxc-module-body'))
      fail('partial Credits graph was whitelisted');
    Sys.println('round16-credits-synthetic-ok');
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('round16-credits-synthetic-ok', result.stdout)

    def test_song_credit_literals_are_planned_without_dynamic_media_walk(self):
        main = r'''class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(
      "var iconName:String = isPixel ? 'pen-pixel' : 'pen';"
      + "switch (songKey) { case 'libitina': iconName = 'file'; }"
      + "FunkinSprite.create(0, 0, 'songCredits/' + iconName);"
      + "var dynamic = event.value;"
      + "FunkinSprite.create(0, 0, 'songCredits/' + dynamic);");
    var keys = [];
    for (ref in refs)
      if (ref.key.indexOf('songCredits/') == 0) keys.push(ref.key);
    if (keys.length != 3 || keys.indexOf('songCredits/pen-pixel') < 0
      || keys.indexOf('songCredits/pen') < 0 || keys.indexOf('songCredits/file') < 0)
      throw 'song-credit plan changed: ' + keys.join(',');
    Sys.println('round16-credits-planner-ok');
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('round16-credits-planner-ok', result.stdout)

    @unittest.skipUnless(DONOR.is_file(), "mounted TAKEOVER Credits HXC unavailable")
    def test_mounted_credits_is_read_only_safe_and_plans_icons(self):
        before = DONOR.read_bytes()
        source = DONOR.read_text(errors="ignore")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, {hx_string(str(DONOR))});
    if (!result.moduleSafe || !result.moduleInitializationSafe
      || hasCode(result, 'unsupported-hxc-module-body')
      || hasCode(result, 'unsupported-hxc-callback-body'))
      fail('mounted Credits safety: ' + result.moduleSafetyReasons.join(','));
    for (required in ['showSongCredits', 'clearSongCredits', 'pauseSongCredits', 'resumeSongCredits'])
      if (result.generatedHscript.indexOf(required) < 0) fail('missing mounted bridge: ' + required);
    if (result.generatedHscript.indexOf('new FlxText') >= 0
      || result.generatedHscript.indexOf('FunkinSprite.create') >= 0
      || result.generatedHscript.indexOf('currentChart') >= 0)
      fail('mounted donor graph escaped');
    new Parser().parseString(result.generatedHscript);
    var plan = HxcAssetPlanner.plan({hx_string(str(DONOR_ROOT))});
    var icons = 0;
    for (ref in plan.references)
      if (ref.kind == 'image' && ref.key.indexOf('songCredits/') == 0) icons++;
    if (icons != 5) fail('mounted song-credit plan count: ' + icons);
    Sys.println('round16-credits-mounted-ok');
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('round16-credits-mounted-ok', result.stdout)
        self.assertEqual(before, DONOR.read_bytes())

    def test_native_boundaries_are_present(self):
        runtime = (ROOT / "source/HxcCompatRuntime.hx").read_text()
        play_state = (ROOT / "source/PlayState.hx").read_text()
        planner = (ROOT / "source/HxcAssetPlanner.hx").read_text()
        compat = (ROOT / "source/HxcCompat.hx").read_text()
        for name in ["showSongCredits", "clearSongCredits", "pauseSongCredits", "resumeSongCredits"]:
            self.assertIn(name, runtime)
        for name in ["hxcShowSongCredits", "hxcClearSongCredits", "hxcPauseSongCredits", "hxcResumeSongCredits"]:
            self.assertIn(name, play_state)
        self.assertIn("collectSongCreditReferences", planner)
        self.assertIn("songCreditsPlan", compat)


if __name__ == "__main__":
    unittest.main()
