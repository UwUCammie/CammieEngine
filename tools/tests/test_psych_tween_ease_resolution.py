"""Script tweens share one ease resolver and one tagged-tween function."""
import subprocess
import tempfile
import unittest

from base_helper_fixtures import COLOR_HELPERS, cool_util_class, copy_sources, play_state_method
from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

EASES = [family + suffix
         for family in ("back", "bounce", "circ", "cube", "elastic", "expo", "quad", "quart", "quint",
                        "sine", "smoothStep", "smootherStep")
         for suffix in ("In", "InOut", "Out")]

TWEEN_METHODS = (
    "public static function scriptTweenType(", "public function startTaggedTween(",
    "function compatTweenObject(", "function compatTweenProperty(", "function compatCancelTween(",
    "function compatDoTween(", "function compatStartTween(", "function compatNoteTarget(",
    "function compatNoteTween(", "public function receptorAt(", "function compatParseColor(",
    "function compatTweenCharacterColorRGB(",
)


def flx_ease() -> str:
    # Every ease is a different curve, so a wrong table entry cannot pass.
    lines = ["class FlxEase {", " public static function linear(t:Float):Float return t;"]
    for index, name in enumerate(EASES):
        lines.append(f" public static function {name}(t:Float):Float return t * {index + 2};")
    return "\n".join(lines) + "\n}\n"


FIXTURE = r'''
abstract FlxColor(Int) from Int to Int {
 public var alphaFloat(never,set):Float;
 inline function set_alphaFloat(value:Float):Float { this = (this & 0xFFFFFF) | (Std.int(value * 255) << 24); return value; }
 public static function fromString(value:String):Null<Int> return null;
}
enum abstract FlxTweenType(Int) from Int to Int { var PERSIST=1; var LOOPING=2; var PINGPONG=4; var ONESHOT=8; var BACKWARD=16; }
class FlxSprite { public var x:Float = 0; public var color:Int = 0xFFFFFFFF; public var alpha:Float = 1; public function new() {} }
class FlxCamera { public var color:FlxColor = cast 0xFFFFFFFF; public var alpha:Float = 1; public function new() {} }
class FlxTween {
 public var target:Dynamic; public var props:Dynamic; public var duration:Float; public var options:Dynamic;
 public var cancelled:Bool = false; public var route:String;
 function new(route:String, target:Dynamic, props:Dynamic, duration:Float, options:Dynamic) {
  this.route = route; this.target = target; this.props = props; this.duration = duration; this.options = options;
 }
 public function cancel():Void cancelled = true;
 public static function tween(target:Dynamic, props:Dynamic, duration:Float, options:Dynamic):FlxTween
  return new FlxTween('scalar', target, props, duration, options);
 public static function color(sprite:FlxSprite, duration:Float, from:FlxColor, to:FlxColor, options:Dynamic):FlxTween
  return new FlxTween('channels', sprite, {to: to}, duration, options);
}
class Receptor { public var x:Float = 0; public var tag:String; public function new(tag:String) this.tag = tag; }
class Line { public var members:Array<Receptor>; public function new(members:Array<Receptor>) this.members = members; }
class Actor { public var x:Float = 0; public var colorTransform:Dynamic = {redOffset: 0.0}; public function new() {} }
class Main {
 var sourceScoreOwner:Bool = false;
 var compatTweens:Map<String, FlxTween> = [];
 var calls:Array<String> = [];
 var objects:Map<String, Dynamic> = [];
 var enemyStrums = new Line([new Receptor('e0'), new Receptor('e1')]);
 var playerStrums = new Line([new Receptor('p0'), new Receptor('p1')]);
 var defaultCamZoom:Float = 1;
 var boyfriend = new Actor();
 function new() {}
 function compatFindObject(name:Dynamic):Dynamic return objects.get(Std.string(name));
 function compatGetProperty(name:Dynamic):Dynamic return null;
 function compatReadPath(target:Dynamic, path:String):Dynamic return Reflect.getProperty(target, path);
 function getHaxeActor(name:Dynamic):Dynamic return objects.get(Std.string(name));
 function callAllHScript(name:String, args:Array<Dynamic>):Void calls.push(name + '(' + args.join(',') + ')');
__METHODS__
 static function check(value:Bool, label:String):Void if (!value) throw label;
 static function main() {
  // The resolver itself: any case, surrounding space, and a linear fallback.
  for (name in __EASE_NAMES__) {
   var expected:Float->Float = Reflect.field(FlxEase, name);
   for (spelling in [name, name.toLowerCase(), name.toUpperCase(), ' ' + name + ' '])
    check(CoolUtil.getEaseFromString(spelling)(0.25) == expected(0.25), 'ease name not resolved: "' + spelling + '"');
  }
  check(CoolUtil.getEaseFromString(null)(0.25) == 0.25, 'missing ease must be linear');
  check(CoolUtil.getEaseFromString('nonsense')(0.25) == 0.25, 'unknown ease must be linear');

  var state = new Main();
  var sprite = new FlxSprite();
  state.objects.set('spr', sprite);
  state.objects.set('boyfriend', state.boyfriend);

  // The spelling scripts actually write is all lower case.
  state.compatDoTween('a', 'spr', 'x', 10, 1, 'cubeout');
  var a = state.compatTweens.get('a');
  check(a != null && a.target == sprite && a.props.x == 10, 'property tween was not created');
  check(a.options.ease(0.25) == FlxEase.cubeOut(0.25), 'lower-case ease name fell back to linear');
  state.compatDoTween('b', 'spr', 'x', 10, 1, ' sineInOut ');
  check(state.compatTweens.get('b').options.ease(0.25) == FlxEase.sineInOut(0.25), 'padded ease name not resolved');
  state.compatDoTween('c', 'spr', 'x', 10, 1, 'nonsense');
  check(state.compatTweens.get('c').options.ease(0.25) == 0.25, 'unknown ease must stay linear');
  state.compatDoTween('d', 'spr', 'x', 10, 1);
  check(!Reflect.hasField(state.compatTweens.get('d').options, 'ease'), 'no ease argument must leave the default alone');

  // Completion frees the tag and tells scripts the tag and the object.
  a.options.onComplete(a);
  check(!state.compatTweens.exists('a'), 'finished tween kept its tag');
  check(state.calls.join(';') == 'tweenCompleted(a,spr)', 'completion arguments: ' + state.calls.join(';'));

  // A new tween with a live tag replaces the old one.
  var b = state.compatTweens.get('b');
  state.compatDoTween('b', 'spr', 'x', 3, 1, 'linear');
  check(b.cancelled && state.compatTweens.get('b') != b, 'same tag did not cancel the earlier tween');
  state.compatCancelTween('b');
  check(!state.compatTweens.exists('b'), 'cancelTween left the tag behind');

  // Note tweens wrap the combined index like the source engine.
  state.calls = [];
  state.compatNoteTween('n', 5, 'x', 40, 1, 'QUADIN');
  var n = state.compatTweens.get('n');
  check(n.target == state.enemyStrums.members[1], 'index past the end did not wrap to the opponent side');
  check(n.options.ease(0.25) == FlxEase.quadIn(0.25), 'upper-case ease name not resolved');
  state.compatNoteTween('n2', 2, 'x', 40, 1);
  check(state.compatTweens.get('n2').target == state.playerStrums.members[0], 'player lanes follow the opponent lanes');
  n.options.onComplete(n);
  check(state.calls.join(';') == 'tweenCompleted(n)', 'note tween completion arguments: ' + state.calls.join(';'));

  // startTween reads every option, not just the ease.
  state.calls = [];
  state.compatStartTween('s', 'spr', {x: 5, alpha: 0.5}, 2, {ease: 'QUADOUT', type: 'pingpong', startDelay: 0.5,
   loopDelay: '0.25', onUpdate: 'whileMoving', onStart: 'onMoveStart', onComplete: 'onMoveDone'});
  var s = state.compatTweens.get('s');
  check(s != null && s.target == sprite && s.props.x == 5 && s.props.alpha == 0.5 && s.duration == 2, 'value set changed');
  check(s.options.ease(0.25) == FlxEase.quadOut(0.25), 'startTween ease not resolved');
  check(s.options.type == FlxTweenType.PINGPONG, 'tween type ignored');
  check(s.options.startDelay == 0.5 && s.options.loopDelay == 0.25, 'delays ignored');
  s.options.onStart(s); s.options.onUpdate(s); s.options.onComplete(s);
  check(state.calls.join(';') == 'onMoveStart(s,spr);whileMoving(s,spr);onMoveDone(s,spr)',
   'named callbacks: ' + state.calls.join(';'));
  check(state.compatTweens.get('s') == s, 'a ping-pong tween gave its tag away after one pass');
  check(PlayStateTypes.type('backward') == FlxTweenType.BACKWARD && PlayStateTypes.type('LOOP') == FlxTweenType.LOOPING
   && PlayStateTypes.type('looping') == FlxTweenType.LOOPING && PlayStateTypes.type('persist') == FlxTweenType.PERSIST
   && PlayStateTypes.type(null) == FlxTweenType.ONESHOT && PlayStateTypes.type('whatever') == FlxTweenType.ONESHOT,
   'tween type names');

  // Without a named completion function the general callback still fires.
  state.calls = [];
  state.compatStartTween('plain', 'spr', {x: 1}, 1);
  var plain = state.compatTweens.get('plain');
  check(!Reflect.hasField(plain.options, 'type') && !Reflect.hasField(plain.options, 'ease'), 'absent options were invented');
  plain.options.onComplete(plain);
  check(state.calls.join(';') == 'tweenCompleted(plain,spr)' && !state.compatTweens.exists('plain'), 'default completion');

  // A single number on a state field tweens the state; a value set means the object.
  state.compatStartTween('zoom', 'defaultCamZoom', 1.5, 1, {ease: 'linear'});
  var zoom = state.compatTweens.get('zoom');
  check(zoom != null && zoom.target == state && zoom.props.defaultCamZoom == 1.5, 'bare state field tween');
  state.compatStartTween('bf', 'boyfriend', {x: 300}, 1);
  var bf = state.compatTweens.get('bf');
  check(bf != null && bf.target == state.boyfriend && bf.props.x == 300, 'a character was tweened as a state field');

  // Colour tweens take the same colour text everywhere and stay channel-wise.
  state.compatStartTween('tint', 'spr', {color: 'FF0000'}, 1);
  var tint = state.compatTweens.get('tint');
  check(tint.route == 'channels' && tint.props.to == 0xFFFF0000, 'colour value set was tweened as one number');

  // Engine-side tweens take a tag for replacement but tell no script.
  state.calls = [];
  state.compatTweenCharacterColorRGB('boyfriend', 10, 20, 30, 1);
  var fade = state.compatTweens.get('__lua_color_boyfriend');
  check(fade != null && fade.target == state.boyfriend.colorTransform && fade.props.redOffset == 10, 'character colour tween');
  fade.options.onComplete(fade);
  check(state.calls.length == 0 && !state.compatTweens.exists('__lua_color_boyfriend'), 'internal tween reached scripts');
 }
}
class PlayStateTypes {
 public static function type(value:Dynamic):FlxTweenType return Main.scriptTweenType(value);
}
'''


class PsychTweenEaseResolutionTest(unittest.TestCase):
    def test_ease_names_tween_options_and_tag_bookkeeping(self):
        methods = "\n".join(play_state_method(marker) for marker in TWEEN_METHODS)
        ease_names = "[" + ", ".join(f"'{name}'" for name in EASES) + "]"
        fixture = FIXTURE.replace("__METHODS__", methods).replace("__EASE_NAMES__", ease_names)
        fixture = "using StringTools;\n" + fixture + flx_ease() + cool_util_class("getEaseFromString", *COLOR_HELPERS)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline="\n")
            (Path(folder) / "Strumline.hx").write_text(
                "class Strumline {} class StrumNote { public function cancelIntroTween(field:String):Void {} }",
                newline="\n")
            copy_sources(folder, "CombinedReceptorIndex.hx")
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_script_tweens_have_one_resolver_and_one_bookkeeper(self):
        for marker in TWEEN_METHODS:
            self.assertNotIn("Reflect.field(FlxEase", play_state_method(marker), marker)
        bindings = (ROOT / "source/PsychSourceBindings.hx").read_text(encoding="utf-8")
        self.assertNotIn("psychEaseName", bindings)
        self.assertNotIn("Reflect.field(FlxEase", bindings)
        self.assertIn("host.startTaggedTween(", bindings)
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        # Only the shared function and cancelTween write the tag map.
        self.assertEqual(play.count("compatTweens.set("), 1)
        for marker in ("function compatTweenObject(", "function compatTweenProperty(", "function compatStartTween(",
                       "function compatTweenCharacterColorRGB("):
            self.assertNotIn("FlxTween.tween(", play_state_method(marker), marker)


if __name__ == "__main__":
    unittest.main()
