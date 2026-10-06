"""Run the production health-bar color selection with small actor/icon stubs."""

from haxe_test_support import FixturePath as Path, HAXE_COMMAND
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
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
    raise AssertionError(f"Unclosed method: {marker}")


class NightmareVisionHealthColorsTest(unittest.TestCase):
    def test_nmvs_authored_colors_poison_roles_and_compat_overrides(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        method = extract_method(source, "function updateHealthColors(")
        fixture = r"""
class ColorOptions { public var useCharColor:Bool=false; public function new() {} }
class OptionsHandler { public static var options:ColorOptions=new ColorOptions(); }
class Actor {
 public var enemyColor:Int;
 public var opponentColor:Int;
 public var bfColor:Int;
 public var playerColor:Int;
 public var healthColour:Int;
 public var poisonColor:Int;
 public var poisonColorEnemy:Int;
 public function new(enemy:Int,opponent:Int,bf:Int,player:Int,health:Int,poison:Int) {
  enemyColor=enemy;opponentColor=opponent;bfColor=bf;playerColor=player;
  healthColour=health;poisonColor=poison;poisonColorEnemy=poison;
 }
}
class Icon { public var healthColors:Array<Int>; public function new(color:Int) healthColors=[color]; }
class Bar {
 public var left:Int=0; public var right:Int=0; public var updates:Int=0;
 public function new() {}
 public function createFilledBar(left:Int,right:Int):Void {this.left=left;this.right=right;}
 public function updateBar():Void updates++;
}
class HealthColorState {
 public var psychSourceHealthBar:Dynamic=null;
 public var nightmareVisionSourceHealthBar:Dynamic=null;
 public var playHUD:Dynamic=null;
 public var nightmareVisionScripts:Dynamic=null;
 public var dad:Actor=new Actor(0x1001,0x1002,0x1003,0x1004,0x1005,0x1006);
 public var boyfriend:Actor=new Actor(0x2001,0x2002,0x2003,0x2004,0x2005,0x2006);
 public var iconP2:Icon=new Icon(0x3001);
 public var iconP1:Icon=new Icon(0x3002);
 public var healthBar:Bar=new Bar();
 public var compatHealthBarLeft:Null<Int>=null;
 public var compatHealthBarRight:Null<Int>=null;
 public var duoMode:Bool=false;
 public var opponentPlayer:Bool=false;
 public function new() {}
__METHOD__
 public function refresh(poison:Bool=false):Void updateHealthColors(poison);
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function colors(state:HealthColorState,left:Int,right:Int,message:String):Void {
  check(state.healthBar.left==left && state.healthBar.right==right,
   message+' expected '+left+'/'+right+' got '+state.healthBar.left+'/'+state.healthBar.right);
  check(state.healthBar.updates>0,message+' updates the bar after choosing colors');
 }
 static function main():Void {
  var nmv=new HealthColorState();
  nmv.nightmareVisionScripts={active:true};
  OptionsHandler.options.useCharColor=true;
  nmv.refresh();
  colors(nmv,nmv.dad.healthColour,nmv.boyfriend.healthColour,
   'NMV actor healthColour takes precedence over icon colors');

  nmv.compatHealthBarLeft=0x4001; nmv.compatHealthBarRight=0x4002;
  nmv.refresh();
  colors(nmv,0x4001,0x4002,'explicit compatibility colors override NMV defaults');
  nmv.refresh(true);
  colors(nmv,nmv.dad.healthColour,nmv.boyfriend.poisonColor,
   'normal player poison affects the player side and bypasses compat overrides');

  nmv.opponentPlayer=true;
  nmv.refresh(true);
  colors(nmv,nmv.dad.poisonColorEnemy,nmv.boyfriend.healthColour,
   'opponent-player poison affects the opponent side and keeps the other NMV color');

  var classic=new HealthColorState();
  OptionsHandler.options.useCharColor=true;
  classic.refresh();
  colors(classic,classic.iconP2.healthColors[0],classic.iconP1.healthColors[0],
   'classic character-color preference retains icon colors');
  classic.refresh(true);
  colors(classic,classic.iconP2.healthColors[0],classic.boyfriend.poisonColor,
   'classic poison keeps its existing player-role color');

  OptionsHandler.options.useCharColor=false;
  classic.opponentPlayer=false; classic.duoMode=false;
  classic.refresh();
  colors(classic,classic.dad.enemyColor,classic.boyfriend.playerColor,
   'classic default color branch remains unchanged');
  classic.duoMode=true;
  classic.refresh();
  colors(classic,classic.dad.opponentColor,classic.boyfriend.bfColor,
   'classic duo color branch remains unchanged');
  classic.compatHealthBarLeft=0x5001; classic.compatHealthBarRight=0x5002;
  classic.refresh();
  colors(classic,0x5001,0x5002,'classic compatibility color overrides remain active');
  Sys.println('nightmare-vision-health-colors-ok');
 }
}
""".replace("__METHOD__", method)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            (work / "Main.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "--run", "Main"], cwd=ROOT,
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("nightmare-vision-health-colors-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
