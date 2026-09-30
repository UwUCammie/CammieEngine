"""Run the real Codename Charter adapter against lightweight native state stubs."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR_ROOT = (Path('/run/media/cammie/External Storage/FNF-Example-Mods')
              / 'codename/D-Sides REDUX Codename Engine (Cancelled)'
              / 'mods/D-Sides REDUX/songs')


class CodenameCharterAdapterTest(unittest.TestCase):
    def test_shared_binding_opens_active_chart_and_reports_only_supported_playtest_fields(self):
        bindings = (ROOT / 'source/CodenameImportBindings.hx').read_text()
        self.assertIn(
            "bindings.set('funkin.editors.charter.Charter', CodenameCharterAdapter);",
            bindings,
        )
        adapter_source = (ROOT / 'source/CodenameCharterAdapter.hx').read_text()
        self.assertIn("throw '[codename-charter] Requested song or difficulty does not match the active chart'",
                      adapter_source)
        self.assertIn("playbackSpeed: 1.0", adapter_source)
        self.assertNotIn('quantSelected:', adapter_source)
        self.assertNotIn('hitSounds:', adapter_source)

        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            base = Path(directory)
            (base / 'PlayState.hx').write_text('''class PlayState {
 public static var instance:PlayState;
 public static var SONG:Dynamic;
 public static var storyDifficultyText:String = "Hard";
 public static var isStoryMode:Bool = false;
 public static var loaded:String = "";
 public static var resets:Int = 0;
 public var identity:Dynamic;
 public function new(identity:Dynamic) { this.identity=identity; }
 public function codenameCharterIdentity():Dynamic return identity;
 public static function resetSongInfos():Void resets++;
 public static function __loadSong(song:String, ?difficulty:String):Void loaded=song+":"+difficulty;
}''')
            (base / 'ChartingState.hx').write_text('''class ChartingState {
 public var created:Bool=false;
 public var destroyed:Bool=false;
 public function new() {}
 public function create():Void created=true;
 public function destroy():Void destroyed=true;
}''')
            (base / 'Conductor.hx').write_text('''class Conductor {
 public static var songPosition:Float=0;
}''')
            flxg = base / 'flixel/FlxG.hx'
            flxg.parent.mkdir(parents=True)
            flxg.write_text('''package flixel;
class FlxG { public static var state:Dynamic; }''')
            (base / 'CodenameSongView.hx').write_text('''class CodenameSongView {
 public var meta:Dynamic;
 public function new(meta:Dynamic) this.meta=meta;
}''')
            (base / 'Main.hx').write_text('''import hscript.Interp;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function expectError(action:Void->Void, fragment:String):Void {
  var message="";
  try action() catch (error:Dynamic) message=Std.string(error);
  if (message.indexOf(fragment)<0) throw "expected error ["+fragment+"] but got ["+message+"]";
 }
 static function main():Void {
  var identity:Dynamic={song:"sample-song",difficulty:"Hard",variation:null,
   sourceFolder:"sample-folder",storageFolder:"sample-folder",chartFile:"sample-hard"};
  var host=new PlayState(identity);
  PlayState.instance=host;
  PlayState.SONG={meta:{name:"sample-song"}};
  flixel.FlxG.state=host;

  var facade=new CodenamePlayStateFacade(host,function() return new CodenameSongView(PlayState.SONG.meta));
  var allowed:Map<String,Dynamic>=new Map();
  allowed.set("funkin.editors.charter.Charter",CodenameCharterAdapter);
  var source='import funkin.editors.charter.Charter; '
   +'function openEditor() return new Charter(PlayState.SONG.meta.name, '
   +'PlayState.difficulty, PlayState.variation); '
   +'function restoredSpeed() { var initialPlayback=1.0; '
   +'if (Charter.playtestInfo != null) initialPlayback=Charter.playtestInfo.playbackSpeed; '
   +'return initialPlayback; }';
  var parsed=CodenameScriptParser.prepare(source,allowed);
  check(parsed.program!=null && parsed.diagnostics.length==0,
   parsed.diagnostics.length==0 ? "no program" : parsed.diagnostics[0].message);
  var interp=new Interp();
  interp.variables.set("Charter",CodenameCharterAdapter);
  interp.variables.set("PlayState",facade);
  interp.execute(parsed.program);
  var openEditor:Dynamic=interp.variables.get("openEditor");
  var editor:CodenameCharterAdapter=openEditor();
  check(editor!=null && PlayState.SONG.meta.name=="sample-song",
   "donor-style constructor did not use active chart identity");
  editor.create();
  check(editor.created,"adapter did not enter native ChartingState");

  Conductor.songPosition=1234.5;
  editor.destroy();
  check(editor.destroyed,"native ChartingState destroy was skipped");
  check(CodenameCharterAdapter.playtestInfo.songPosition==1234.5
   && CodenameCharterAdapter.playtestInfo.playbackSpeed==1.0,
   "playtestInfo did not expose the source-valid native fields");
  check(Reflect.fields(CodenameCharterAdapter.playtestInfo).length==2,
   "adapter fabricated unsupported Charter playtest settings");
  var restoredSpeed:Dynamic=interp.variables.get("restoredSpeed");
  check(restoredSpeed()==1.0,"D-Sides Debug playbackSpeed read did not work");

  expectError(function() new CodenameCharterAdapter("other-song","Hard",null),
   "does not match the active chart");
  expectError(function() new CodenameCharterAdapter("sample-song","Easy",null),
   "does not match the active chart");
  expectError(function() new CodenameCharterAdapter("sample-song","Hard","alternate"),
   "variants are not supported");
  expectError(function() new CodenameCharterAdapter("sample-song","Hard",null,false),
   "reload=false is unsupported");

  var stale=new CodenameCharterAdapter("sample-song","Hard",null);
  PlayState.SONG={meta:{name:"replacement-song"}};
  expectError(function() stale.create(),"active chart changed");
 }
}''')
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                 '-cp', str(base), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                 '-cp', str(ROOT / '.haxelib/hscript-ex/git/src'), '--run', 'Main'],
                cwd=ROOT, text=True, capture_output=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless((DONOR_ROOT / 'UI.hx').is_file() and (DONOR_ROOT / 'Debug.hx').is_file(),
                         'mounted D-Sides Codename source unavailable')
    def test_d_sides_calls_match_the_adapter_surface(self):
        ui = (DONOR_ROOT / 'UI.hx').read_text()
        debug = (DONOR_ROOT / 'Debug.hx').read_text()
        self.assertIn('new Charter(PlayState.SONG.meta.name, PlayState.difficulty, PlayState.variation)', ui)
        self.assertIn('Charter.playtestInfo.playbackSpeed', debug)
        self.assertIn('import funkin.editors.charter.Charter;', ui)
        self.assertIn('import funkin.editors.charter.Charter;', debug)


if __name__ == '__main__':
    unittest.main()
