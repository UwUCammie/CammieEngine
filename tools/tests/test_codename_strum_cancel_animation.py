"""Pin Codename's cancellable receptor entrance animation behavior."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def method(source: str, name: str) -> str:
    match = re.search(r"(?:override public |public )function " + re.escape(name) + r"\(", source)
    if match is None:
        raise AssertionError(name)
    start = match.start()
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    for index in range(brace, len(source)):
        char = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unclosed method {name}")


class CodenameStrumCancelAnimationTest(unittest.TestCase):
    def test_event_suppresses_only_the_native_entrance_tween(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        event_source = (ROOT / "source/CodenameStrumCreationEvent.hx").read_text()
        strum_source = (ROOT / "source/Strumline.hx").read_text()
        trans_in = method(strum_source, "transIn")
        self.assertIn("arrow.codenameIntroAnimationCancelled", trans_in)
        self.assertIn("@:keep public function cancelCodenameIntroAnimation()", strum_source)

        with tempfile.TemporaryDirectory(prefix="codename-strum-cancel-") as temp:
            scratch = Path(temp)
            (scratch / "CodenameGameEvent.hx").write_text(
                (ROOT / "source/CodenameGameEvent.hx").read_text()
            )
            (scratch / "CodenameStrumCreationEvent.hx").write_text(event_source)
            (scratch / "Strumline.hx").write_text(
                """import flixel.tweens.FlxTween;
import flixel.tweens.FlxEase;
class Strumline {
 public var members:Array<Strumline.StrumNote>;
 public var length(get, never):Int;
 function get_length():Int return members.length;
 public function new(members:Array<Strumline.StrumNote>) this.members=members;
 """ + trans_in + "\n}\n"
                "class StrumNote {\n"
                " public var y:Float;public var alpha:Float;\n"
                " @:keep public var codenameIntroAnimationCancelled:Bool=false;\n"
                " public function new(y:Float,alpha:Float) {this.y=y;this.alpha=alpha;}\n"
                " @:keep public function cancelCodenameIntroAnimation():Void "
                "codenameIntroAnimationCancelled=true;\n"
                "}\n"
            )
            (scratch / "flixel/tweens").mkdir(parents=True)
            (scratch / "flixel/tweens/FlxTween.hx").write_text(
                """package flixel.tweens;
class FlxTween {
 public static var calls:Array<Dynamic>=[];
 public function new() {}
 public static function tween(target:Dynamic,values:Dynamic,duration:Float,options:Dynamic):FlxTween {
  calls.push({target:target,values:values,duration:duration,options:options});return new FlxTween();
 }
}
"""
            )
            (scratch / "flixel/tweens/FlxEase.hx").write_text(
                "package flixel.tweens; class FlxEase { public static var circOut:Dynamic={}; }\n"
            )
            (scratch / "Main.hx").write_text(
                """import flixel.tweens.FlxTween;
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var hidden=new Strumline.StrumNote(100,0);
  var hiddenEvent=new CodenameStrumCreationEvent(hidden,0,0,'left','game/notes/default');
  hiddenEvent.cancelAnimation();
  check(hidden.codenameIntroAnimationCancelled,'event did not mark this receptor');
  check(!hiddenEvent.cancelled,'cancelAnimation incorrectly cancelled creation');

  var visible=new Strumline.StrumNote(100,.4);
  var line=new Strumline([hidden,visible]);
  line.transIn();
  check(hidden.y==100&&hidden.alpha==0,'cancelled entrance changed the authored receptor state');
  check(visible.y==90&&visible.alpha==0,'uncancelled receptor lost the native entrance setup');
  check(FlxTween.calls.length==1&&FlxTween.calls[0].target==visible,
   'native intro tween ran for a cancelled receptor or skipped the live receptor');
  check(FlxTween.calls[0].values.y==100&&FlxTween.calls[0].values.alpha==1,
   'native intro tween endpoint changed');

  var separatelyCancelled=new CodenameStrumCreationEvent(visible,1,0,'left','game/notes/default');
  separatelyCancelled.cancel();
  check(separatelyCancelled.cancelled&&!visible.codenameIntroAnimationCancelled,
   'event cancellation and animation cancellation were conflated');
 }
}
"""
            )
            subprocess.run(
                [str(HAXE), "-cp", str(scratch), "--interp", "-main", "Main"],
                cwd=ROOT,
                check=True,
                text=True,
                timeout=30,
            )


if __name__ == "__main__":
    unittest.main()
