"""Psych timeBar aliases the live fill while legacy and NV keep their label."""
from pathlib import Path
from haxe_test_support import FixturePath as Path, HAXE_COMMAND
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.find("{", start)
    semicolon = source.find(";", start)
    if semicolon >= 0 and (opening < 0 or semicolon < opening):
        return source[start:semicolon + 1].strip()
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


class PsychTimeHudAliasesTest(unittest.TestCase):
    def test_source_and_legacy_aliases_and_source_only_attached_bars(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("public var timeBar:Dynamic;", source)

        methods = "\n".join(extract_method(source, marker) for marker in (
            "function get_timeTxt()",
            "function initializeSourceTimeHUDAliases()",
            "function createSourceHUDBar(",
            "public function sourceNoteTimingMode()",
        ))
        engine_source = (ROOT / "source/EngineCompat.hx").read_text(encoding="utf-8")
        engine_methods = "\n".join(extract_method(engine_source, marker) for marker in (
            "public static function propertyPath(",
            "public static function propertyRoot(",
        ))

        fixture = r'''
using StringTools;
class EngineCompat {
 __ENGINE_METHODS__
}
typedef FlxBarFillDirection = Int;
class FlxSprite {
 public var x:Float; public var y:Float; public var width:Float; public var height:Float;
 public function new() {}
}
class FlxText extends FlxSprite { public function new() super(); }
class PlayState { public static var globalSprites:Map<String,Dynamic> = new Map(); }
class FlxBar {
 public var x:Float; public var y:Float; public var width:Int; public var height:Int;
 public var direction:FlxBarFillDirection; public var parent:Dynamic; public var variable:String;
 public var minimum:Float; public var maximum:Float;
 public function new(x:Float,y:Float,direction:FlxBarFillDirection,width:Int,height:Int,
  parent:Dynamic,variable:String,minimum:Float,maximum:Float) {
  this.x=x;this.y=y;this.direction=direction;this.width=width;this.height=height;
  this.parent=parent;this.variable=variable;this.minimum=minimum;this.maximum=maximum;
 }
}
class SourceAttachedBar extends FlxBar {
 public static var events:Array<String> = [];
 public var attachedBackground:FlxSprite;
 public function new(x:Float,y:Float,direction:FlxBarFillDirection,width:Int,height:Int,
  parent:Dynamic,variable:String,minimum:Float,maximum:Float) {
  super(x,y,direction,width,height,parent,variable,minimum,maximum);
  events.push('construct');
 }
 public function attachBackground(background:FlxSprite):Void {
  attachedBackground=background;events.push('attach');
 }
}
class Main {
 static var LEFT_TO_RIGHT=1; static var RIGHT_TO_LEFT=2;
 var sourceScoreOwner:Bool; var sourceScoreNightmare:Bool;
 var timeBarBG:FlxSprite; var timeBar:Dynamic;
 public var timeTxt(get,never):FlxText;
 var songName:FlxText; var songPosBar:FlxBar; var songPosBG:FlxSprite;
 function new(mode:Int) {
  sourceScoreOwner=mode!=0;sourceScoreNightmare=mode==2;
  timeBarBG=new FlxSprite();timeBar=new FlxText();songName=new FlxText();
  songPosBG=new FlxSprite();songPosBar=new FlxBar(0,0,1,100,10,this,'songPositionBar',0,1);
 }
 __METHODS__
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  for(mode in [0,1,2]) {
   PlayState.globalSprites=new Map();SourceAttachedBar.events=[];
   var host=new Main(mode);host.initializeSourceTimeHUDAliases();
   var expectedBar:Dynamic=mode==1?host.songPosBar:host.songName;
   check(host.timeBar==expectedBar,'timeBar alias selected the wrong object for mode '+mode);
   check(host.timeTxt==host.songName,'timeTxt stopped exposing the native label for mode '+mode);
   check(EngineCompat.propertyRoot('timeTxt')=='timeTxt'
    &&EngineCompat.propertyPath('timeTxt.visible')=='timeTxt.visible'
    &&Reflect.getProperty(host,EngineCompat.propertyRoot('timeTxt'))==host.songName,
    'Psych property lookup redirected timeTxt away from the label for mode '+mode);
   check(EngineCompat.propertyPath('game.timeTxt.visible')=='timeTxt.visible'
    &&Reflect.getProperty(host,EngineCompat.propertyRoot('timeBar'))==expectedBar,
    'qualified label or legacy timeBar lookup changed for mode '+mode);
   check(host.timeBarBG==host.songPosBG,'timeBarBG alias changed');
   check(PlayState.globalSprites.get('timeBar')==expectedBar
    &&PlayState.globalSprites.get('timeBarBG')==host.songPosBG,
    'global sprite aliases were registered before their final target was selected');

   var timeBackground=new FlxSprite();timeBackground.x=100;timeBackground.y=50;
   timeBackground.width=400;timeBackground.height=20;
   var timeFill=host.createSourceHUDBar(timeBackground,3,LEFT_TO_RIGHT,'songPositionBar',0,1);
   var healthBackground=new FlxSprite();healthBackground.x=200;healthBackground.y=600;
   healthBackground.width=500;healthBackground.height=30;
   var healthFill=host.createSourceHUDBar(healthBackground,4,RIGHT_TO_LEFT,'health',0,2);
   if(mode==1) {
    check(Std.isOfType(timeFill,SourceAttachedBar)&&Std.isOfType(healthFill,SourceAttachedBar),
     'Psych source fills must use attached bars');
    var sourceTime:SourceAttachedBar=cast timeFill;var sourceHealth:SourceAttachedBar=cast healthFill;
    check(sourceTime.attachedBackground==timeBackground&&sourceHealth.attachedBackground==healthBackground,
     'source fill did not bind to its matching background');
    check(SourceAttachedBar.events.join(',')=='construct,attach,construct,attach',
     'backgrounds must be attached only after each fill is constructed');
    check(sourceTime.x==103&&sourceTime.y==53&&sourceTime.width==394&&sourceTime.height==14
     &&sourceHealth.x==204&&sourceHealth.y==604&&sourceHealth.width==492&&sourceHealth.height==22,
     'attached source fill geometry/defaults changed');
   } else {
    check(Std.isOfType(timeFill,FlxBar)&&!Std.isOfType(timeFill,SourceAttachedBar)
     &&Std.isOfType(healthFill,FlxBar)&&!Std.isOfType(healthFill,SourceAttachedBar),
     'native and Nightmare Vision fills must keep ordinary FlxBar behavior');
    check(SourceAttachedBar.events.length==0,'non-Psych mode bound source backgrounds');
   }
  }
 }
}
'''.replace("__ENGINE_METHODS__", engine_methods).replace("__METHODS__", methods)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                capture_output=True, text=True, cwd=ROOT, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        hud_init = extract_method(source, "function initializeNightmareVisionHUD()")
        self.assertIn("songFill:songPosBar, songBackground:songPosBG, timeText:songName", hud_init)

        build = source[source.index("var sourceTimeHUD = nightmareVisionScripts != null;"):]
        self.assertLess(build.index("songPosBG = new FlxSprite"), build.index("createSourceHUDBar(songPosBG"))
        self.assertLess(build.index("healthBarBG = new FlxSprite"), build.index("createSourceHUDBar(healthBarBG"))
        self.assertLess(build.index("initializeSourceTimeHUDAliases();"), build.index("if (useSongBar && !sourceTimeHUD)"))


if __name__ == "__main__":
    unittest.main()
