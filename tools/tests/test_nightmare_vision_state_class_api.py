"""Source class references retain statics and reach their owner state's instance API."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path, HAXE_COMMAND
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionStateClassApiTest(unittest.TestCase):
    def test_source_launch_seek_alias_resets_without_losing_native_transport_offset(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = source.index("\tvar nightmareVisionStartOnTime:Float")
        end = source.index("\tpublic static var startingPosition", start)
        members = source[start:end].replace("@:keep ", "")
        capture = "nightmareVisionStartOnTime = Math.max(0, startTimestamp);"
        self.assertIn("startTimestamp = consumeStartingPosition();\n\t\t" + capture, source)
        song_start = source[source.index("function startSong("):source.index("// ---- hscript helper shaders")]
        self.assertLess(song_start.index("nightmareVisionStartOnTime = 0;"), song_start.index("callNightmareVision('onSongStart'"))
        self.assertNotIn("startOnTime = 0;", song_start)
        seed = source[source.index("function seedNightmareVision("):source.index("function seedNightmareVision(") + 600]
        self.assertIn("interp.bindClassParent(PlayState);", seed)
        main = """class State {
 public var startTimestamp:Float = 0;
 MEMBERS
 public function new(offset:Float) { startTimestamp=offset; CAPTURE }
 public function songStart():Void nightmareVisionStartOnTime=0;
}
class Main {
 static function check(ok:Bool):Void if(!ok)throw 'source seek lifecycle';
 static function main():Void {
  var ordinary=new State(0); check(ordinary.startOnTime<=0);
  var editor=new State(42000); check(editor.startOnTime==42000);
  editor.songStart(); check(editor.startOnTime==0 && editor.startTimestamp==42000);
  ordinary.startOnTime=1500; check(ordinary.startOnTime==1500 && ordinary.startTimestamp==1500);
  ordinary.startOnTime=-10; check(ordinary.startOnTime==0 && ordinary.startTimestamp==0);
  ordinary.startOnTime=Math.NaN; check(ordinary.startOnTime==0);
  ordinary.startOnTime=Math.POSITIVE_INFINITY; check(ordinary.startOnTime==0);
  check(editor.startTimestamp==42000);
 }
}""".replace("MEMBERS", members).replace("CAPTURE", capture)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(main, encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_intro_conditions_camera_lookup_and_owner_isolation(self):
        main = r'''
import crowplexus.hscript.Parser;
class SourceStateClass {
 public static var SONG:Dynamic = {song:'Synthetic'};
 public static var collision:String = 'static';
 public static var nullable:Dynamic = null;
}
class State {
 public var camHUD:Dynamic;
 public var camGame:Dynamic = {};
 public var camOther:Dynamic = {};
 public var collision:String = 'instance';
 public var nullable:String = 'instance';
 public var startOnTime(get,set):Float;
 public var offset:Float;
 public function new(offset:Float) {this.offset=offset;camHUD={name:'hud'};}
 function get_startOnTime():Float return offset;
 function set_startOnTime(value:Float):Float return offset=value;
}
class Main {
 static function check(ok:Bool, message:String):Void if(!ok)throw message;
 static function load(state:State, bound:Bool):NightmareVisionScriptGroup {
  var g=new NightmareVisionScriptGroup(state,function(name,phase,error):Void {
   throw 'unexpected source error: '+phase+':'+Std.string(error);
  });
  var parser=new Parser();parser.allowTypes=true;
  g.load('global',parser.parseString('
   var card = null;
   var layers = [];
   function onCreatePost() {
    if (PlayState.startOnTime <= 0 && metadata != null) {
     card = {song:PlayState.SONG.song,composer:metadata.composer};
     layers.insert(layers.indexOf(PlayState.camHUD), card);
    }
   }
   function readCard() return card;
   function readLayers() return layers;
   function initializeLayers(game, hud, other) layers=[game,hud,other];
   function writeOffset(value) PlayState.startOnTime=value;
   function readOffset() return PlayState.startOnTime;
   function readHud() return PlayState.camHUD;
   function readCollision() return PlayState.collision;
   function readNullable() return PlayState.nullable;
  '),function(interp):Void {
   interp.variables.set('PlayState',SourceStateClass);
   interp.variables.set('metadata',{composer:'Synthetic Composer'});
   if(bound) interp.bindClassParent(SourceStateClass);
  });
  g.call('initializeLayers',[state.camGame,state.camHUD,state.camOther]);
  return g;
 }
 static function main():Void {
  var ordinary=new State(0);
  var negative=load(ordinary,false);negative.call('onCreatePost');
  check(negative.getScript('global').call('readCard')==null,
   'negative control should reproduce a missing numeric state-class property');
  negative.destroy();
  var first=new State(0);
  var g=load(first,true);g.call('onCreatePost');
  var script=g.getScript('global');
  var card:Dynamic=script.call('readCard');
  check(card!=null&&card.song=='Synthetic'&&card.composer=='Synthetic Composer',
   'normal launch cannot create its authored intro');
  var layers:Array<Dynamic>=script.call('readLayers');
  check(layers.length==4&&layers[0]==first.camGame&&layers[1]==card
   &&layers[2]==first.camHUD&&layers[3]==first.camOther,
   'source class camera must place the card above game and below HUD');
  check(script.call('readCollision')=='static'&&script.call('readNullable')==null,
   'real static fields, including null, must precede instance aliases');
  script.call('writeOffset',[12000]);check(first.offset==12000,'instance setter not forwarded');
  var editor=new State(42000);var other=load(editor,true);other.call('onCreatePost');
  check(other.getScript('global').call('readCard')==null,'editor seek should suppress authored intro');
  check(script.call('readOffset')==12000&&other.getScript('global').call('readOffset')==42000,
   'source state class aliases leaked across owners');
  check(script.call('readHud')==first.camHUD&&other.getScript('global').call('readHud')==editor.camHUD,
   'camera alias leaked across owners');
  var replacement=new State(7);g.parent=replacement;
  check(script.call('readOffset')==7&&script.call('readHud')==replacement.camHUD,
   'class alias retained a stale parent');
  g.destroy();other.destroy();
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(main, encoding='utf-8')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work),
                '--main', 'Main', '--interp'], cwd=work,
                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
