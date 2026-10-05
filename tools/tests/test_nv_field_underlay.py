"""Pin Nightmare Vision's FIELD underlay geometry and field-owned sprite lifecycle."""

import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''import flixel.FlxSprite;
import flixel.util.FlxColor;

class Main {
	static function check(ok:Bool, message:String):Void if (!ok) throw message;
	static function near(actual:Float, expected:Float, message:String):Void
		check(Math.abs(actual - expected) < 0.001, message + ': ' + actual + ' != ' + expected);

	static function main():Void {
		var receptors:Array<Dynamic> = [
			{x: 100.0, width: 50.0, exists: true, visible: true},
			{x: 200.0, width: 40.0, exists: true, visible: true},
			{x: -500.0, width: 80.0, exists: true, visible: false},
			{x: -600.0, width: 80.0, exists: false, visible: true},
			null
		];
		var notes:Array<Dynamic> = [
			{x: 60.0, width: 20.0, exists: true, alive: true, visible: false,
				isOnScreen: function() return true},
			{x: 300.0, width: 40.0, exists: true, alive: true,
				isOnScreen: function() return true},
			{x: -1000.0, width: 100.0, exists: true, alive: true,
				isOnScreen: function() return false},
			{x: -1100.0, width: 100.0, exists: true, alive: false,
				isOnScreen: function() return true},
			{x: -1200.0, width: 100.0, exists: false, alive: true,
				isOnScreen: function() return true},
			null
		];
		var bounds = NightmareVisionFieldUnderlay.measure(receptors, notes, 800, 600, 0);
		check(bounds != null, 'visible receptors/onscreen notes should produce bounds');
		near(bounds.x, 45, 'left edge should combine note and receptor extents with 15px padding');
		near(bounds.width, 310, 'right edge should combine note and receptor extents with 15px padding');
		near(bounds.height, 600, 'unrotated underlay height should equal camera view height');
		near(NightmareVisionFieldUnderlay.measure(receptors, notes, 800, 600, 90).height,
			800, 'quarter-turned height should use camera view width');
		near(NightmareVisionFieldUnderlay.measure(receptors, notes, 800, 600, -90).height,
			800, 'negative camera rotation should use absolute trigonometric extents');
		near(NightmareVisionFieldUnderlay.measure(receptors, notes, 800, 600, 45).height,
			(800 + 600) / Math.sqrt(2), 'diagonal rotation should cover the full viewport height');

		var empty:Array<Dynamic> = [
			{x: 0.0, width: 10.0, exists: true, visible: false}
		];
		check(NightmareVisionFieldUnderlay.measure(empty, [], 800, 600, 0) == null,
			'empty geometry should skip drawing instead of producing infinite coordinates');
		check(NightmareVisionFieldUnderlay.measure(receptors, notes, Math.NaN, 600, 0) == null,
			'invalid camera dimensions should skip drawing');
		near(NightmareVisionFieldUnderlay.effectiveAlpha(0.8, 0.75, 0.2, 0.5), 0.24,
			'underlay opacity should include field multiplier and mod alpha/dark complements');

		var field = new NightmareVisionPlayFieldView(0, function() return false);
		var initial:FlxSprite = field.underlaySpr;
		check(initial != null && initial.width == 1 && initial.height == 1,
			'field should initialize the source 1x1 underlay sprite');
		check(initial.color == FlxColor.BLACK && initial.alpha == 0 && initial.scrollFactor.setCalls == 1,
			'initial underlay should be black, transparent and fixed to the screen');
		check(field.underlayAlphaMult == 1, 'source field underlay multiplier should default to one');
		field.underlayAlphaMult = 0.35;
		var replacement = new FlxSprite();
		field.underlaySpr = replacement;
		check(field.underlaySpr == replacement && !initial.destroyed,
			'plain public replacement should not eagerly destroy the displaced donor sprite');
		field.destroy();
		check(replacement.destroyed && field.underlaySpr == null,
			'field destruction should destroy and clear the currently assigned underlay');
		check(!initial.destroyed, 'field destruction should only destroy the currently assigned underlay');
		field.destroy();
		check(replacement.destroyCalls == 1, 'repeated field destruction should not destroy the sprite twice');
		trace('NV_FIELD_UNDERLAY_OK');
	}
}'''


class NightmareVisionFieldUnderlayTest(unittest.TestCase):
	def test_geometry_alpha_and_mutable_sprite_lifecycle(self):
		if not (ROOT / ".tools/haxe/haxe").is_file():
			self.skipTest("portable Haxe interpreter is unavailable")
		with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
			work = Path(folder)
			(work / "Main.hx").write_text(MAIN, newline="\n")
			write_fixture_stubs(work)
			result = subprocess.run(
				[*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main"],
				cwd=ROOT, capture_output=True, text=True, timeout=60,
			)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
		self.assertIn("NV_FIELD_UNDERLAY_OK", result.stdout)


def write_fixture_stubs(work):
	files = {
		"flixel/FlxSprite.hx": r'''package flixel;
class FlxSprite {
	public var width:Float = 0;
	public var height:Float = 0;
	public var color:Int = 0;
	public var alpha:Float = 1;
	public var scrollFactor:FixtureScrollFactor;
	public var destroyed:Bool = false;
	public var destroyCalls:Int = 0;
	public function new() scrollFactor = new FixtureScrollFactor();
	public function makeGraphic(width:Int, height:Int, color:Int):FlxSprite {
		this.width = width; this.height = height; this.color = color; return this;
	}
	public function destroy():Void { destroyed = true; destroyCalls++; }
}
class FixtureScrollFactor {
	public var setCalls:Int = 0;
	public function new() {}
	public function set(x:Float = 1, y:Float = 1):Void setCalls++;
}''',
		"flixel/util/FlxColor.hx": r'''package flixel.util;
class FlxColor {
	public static inline var WHITE:Int = 0xFFFFFF;
	public static inline var BLACK:Int = 0x000000;
}''',
		"flixel/util/FlxSignal.hx": r'''package flixel.util;
class FlxTypedSignal<T> {
	public var dispatch:T;
	public function new() dispatch = cast function(value:Dynamic):Void {};
	public function add(listener:T):Void {}
	public function removeAll():Void {}
	public function destroy():Void {}
}''',
		"Strumline.hx": r'''class Strumline {
	public var members:Array<StrumNote> = [];
	public function new() {}
}
class StrumNote {
	public var resetAnim:Float = 0;
	public function new() {}
	public function playAnim(name:String):Void {}
}''',
		"NightmareVisionNoteSkin.hx": r'''class NightmareVisionNoteSkin {}''',
	}
	for relative, content in files.items():
		path = work / relative
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(content, newline="\n")


if __name__ == "__main__":
	unittest.main()
