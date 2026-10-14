"""Typed modchart sprite access gives the same results as the reflective path.

The Nightmare Vision modchart renderer reads and writes note values on every
note each frame and around every scripted modifier. A sprite implementing
NightmareVisionModchartLiveSprite is served through typed calls so no Float is
boxed; these checks run one scenario with a plain reflective sprite and with a
typed one and require identical sprites and visual states afterwards.
"""
from haxe_test_support import HAXE_COMMAND, FixturePath

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"

FIXTURE = r'''
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModifierRegistry.NightmareVisionModifierExecution;
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartVector;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModchartLiveSprite;
import nightmarevision.modchart.NightmareVisionModchartLiveSprite.NightmareVisionModchartLiveField as F;

class Rgb { public var alpha:Float = 1; public var flash:Float = 0; public function new() {} }
class Point { public var x:Float; public var y:Float; public function new(x:Float, y:Float) { this.x = x; this.y = y; } }

/** Same members as the plain sprite, plus the typed interface. */
class TypedSprite implements NightmareVisionModchartLiveSprite {
	public static var typedCalls = 0;
	public var active = true; public var x = 0.; public var y = 0.; public var width = 50.; public var height = 100.;
	public var frameWidth = 50; public var frameHeight = 100; public var scale = new Point(2, 2); public var baseScale = new Point(2, 2);
	public var offset = new Point(0, 0); public var origin = new Point(0, 0); public var spriteOffset = new Point(0, 0);
	public var rgbGraphics:Rgb = new Rgb(); public var angle = 0.; public var mAngle = 0.; public var alpha = 0.75; public var alphaMod = 1.;
	public var multSpeed = 1.; public var noteData = 0; public var ID = 0; public var strumTime = 999.; public var sustainLength = 124.;
	public var isSustainNote = false; public var wasGoodHit = false; public var antialiasing = false;
	public var offsetX = 0.; public var offsetY = 0.; public var typeOffsetX = 0.; public var typeOffsetY = 0.;
	public var animation:Dynamic; public var centers = 0; public var hitboxes = 0;
	public function new(sustain:Bool) { isSustainNote = sustain; animation = {curAnim: {name: sustain ? 'hold' : 'Scroll'}}; }
	public function centerOrigin() centers++;
	public function centerOffsets() {}
	public function updateHitbox() hitboxes++;
	public function modchartLiveFloat(field:Int):Float {
		typedCalls++;
		return switch (field) {
			case F.X: x; case F.Y: y; case F.WIDTH: width; case F.HEIGHT: height; case F.FRAME_HEIGHT: frameHeight;
			case F.ANGLE: angle; case F.M_ANGLE: mAngle; case F.SCALE_X: scale.x; case F.SCALE_Y: scale.y;
			case F.BASE_SCALE_X: baseScale.x; case F.BASE_SCALE_Y: baseScale.y; case F.MULT_SPEED: multSpeed;
			case F.STRUM_TIME: strumTime; case F.SUSTAIN_LENGTH: sustainLength; case F.OFFSET_X: offsetX; case F.OFFSET_Y: offsetY;
			case F.TYPE_OFFSET_X: typeOffsetX; case F.TYPE_OFFSET_Y: typeOffsetY; case F.ALPHA_MOD: alphaMod;
			case F.RGB_FLASH: rgbGraphics == null ? Math.NaN : rgbGraphics.flash;
			case F.RGB_ALPHA: rgbGraphics == null ? Math.NaN : rgbGraphics.alpha;
			default: Math.NaN;
		}
	}
	public function modchartLiveBool(field:Int):Bool return field == F.ACTIVE ? active : field == F.WAS_GOOD_HIT ? wasGoodHit : false;
	public function modchartSetLiveFloat(field:Int, value:Float):Void {
		switch (field) {
			case F.X: x = value; case F.Y: y = value; case F.ANGLE: angle = value; case F.SCALE_X: scale.x = value;
			case F.SCALE_Y: scale.y = value; case F.MULT_SPEED: multSpeed = value; case F.ALPHA_MOD: alphaMod = value;
			case F.RGB_FLASH: if (rgbGraphics != null) rgbGraphics.flash = value;
			case F.RGB_ALPHA: if (rgbGraphics != null) rgbGraphics.alpha = value;
			default:
		}
	}
	public function modchartLiveCall(method:Int):Void {
		if (method == F.UPDATE_HITBOX) updateHitbox(); else if (method == F.CENTER_ORIGIN) centerOrigin(); else if (method == F.CENTER_OFFSETS) centerOffsets();
	}
}

class Main {
	static function check(ok:Bool, label:String):Void if (!ok) throw label;
	static function plain(sustain:Bool):Dynamic {
		var sprite:Dynamic = {active: true, x: 0., y: 0., width: 50., height: 100., frameWidth: 50, frameHeight: 100,
			scale: new Point(2, 2), baseScale: new Point(2, 2), offset: new Point(0, 0), origin: new Point(0, 0), spriteOffset: new Point(0, 0),
			rgbGraphics: new Rgb(), angle: 0., mAngle: 0., alpha: 0.75, alphaMod: 1., multSpeed: 1., noteData: 0, ID: 0,
			strumTime: 999., sustainLength: 124., isSustainNote: sustain, wasGoodHit: false, antialiasing: false,
			offsetX: 0., offsetY: 0., typeOffsetX: 0., typeOffsetY: 0., animation: {curAnim: {name: sustain ? 'hold' : 'Scroll'}},
			centers: 0, hitboxes: 0};
		sprite.centerOrigin = function() sprite.centers++;
		sprite.centerOffsets = function() {};
		sprite.updateHitbox = function() sprite.hitboxes++;
		return sprite;
	}
	static function entry(?builtin:String, ?path:Float->Float->Float->Float->NightmareVisionModchartVector->Int->Int->Dynamic->NightmareVisionModchartVector,
		?update:Float->Dynamic->NightmareVisionModchartVector->Int->String->Void):NightmareVisionModifierExecution return {
			builtin: builtin,
			getPosition: path == null ? function(t, d, td, b, p, data, player, obj) return p : path,
			updateObject: update == null ? function(b, obj, p, player, kind) {} : update
		};

	/** Runs the scenario and returns every value it produced, as text. */
	static function run(make:Bool->Dynamic, legacy:Bool, scripted:Bool):String {
		var registry = new NightmareVisionModifierRegistry(4);
		var transform = new NightmareVisionModchartTransform(registry);
		var context = new NightmareVisionModchartContext(1280, 720, 4, 112, 777, 2.5, 1, 500, false, false, legacy);
		registry.setValue('reverse', 0.5, 0);
		registry.setValue('mini', 0.25, 0);
		if (scripted) {
			var entries:Map<String, NightmareVisionModifierExecution> = new Map();
			entries.set('reverse', entry('reverse'));
			entries.set('mini', entry('mini'));
			entries.set('push', entry(null, function(t, d, td, b, p, data, player, obj) {
				obj.x += 3; obj.typeOffsetX = 2.5; p.y += obj.strumTime / 100; return p;
			}, function(b, obj, p, player, kind) {
				obj.scale.x += 0.5; obj.angle = 12; obj.alphaMod = 0.4; obj.multSpeed = 1.5; obj.rgbGraphics.flash = 0.3;
				obj.offsetY = 4; obj.baseScale.y = 3;
			}));
			entries.set('read', entry(null, null, function(b, obj, p, player, kind) {
				obj.x += obj.scale.x; obj.mAngle = obj.angle / 2;
			}));
			var names = ['push', 'reverse', 'mini', 'read'];
			registry.executionNames = function(player) return names;
			registry.executionEntry = function(name) return entries.get(name);
		}
		var renderer = new NightmareVisionModchartRenderer(transform);
		var out = [];
		for (sustain in [false, true]) {
			var sprite = make(sustain);
			for (frame in 0...3) {
				var state = renderer.updateNote(context, sprite, 0, 20 + frame, 30, 50, 100, 3.2);
				out.push([state.position.x, state.position.y, state.baseScaleX, state.baseScaleY, state.alphaMod, state.rgbFlash,
					state.spriteOffsetX, state.spriteOffsetY, state.holdAngle, state.holdSegmentDistance].join(','));
				out.push([sprite.x, sprite.y, sprite.scale.x, sprite.scale.y, sprite.angle, sprite.mAngle, sprite.alphaMod, sprite.multSpeed,
					sprite.rgbGraphics.flash, sprite.centers, sprite.hitboxes, sprite.offsetY, sprite.typeOffsetX].join(','));
			}
		}
		return out.join('\n');
	}

	static function main() {
		for (legacy in [false, true]) for (scripted in [false, true]) {
			TypedSprite.typedCalls = 0;
			var reflective = run(plain, legacy, scripted);
			var typed = run(function(sustain) return new TypedSprite(sustain), legacy, scripted);
			check(TypedSprite.typedCalls > 0, 'typed path not taken legacy=' + legacy + ' scripted=' + scripted);
			check(reflective == typed, 'legacy=' + legacy + ' scripted=' + scripted + '\nreflective:\n' + reflective + '\ntyped:\n' + typed);
		}
		// A sprite without rgbGraphics falls back exactly like a missing field.
		var bare = new TypedSprite(false); bare.rgbGraphics = null;
		var plainBare = plain(false); plainBare.rgbGraphics = null;
		var registry = new NightmareVisionModifierRegistry(4);
		var a = new NightmareVisionModchartRenderer(new NightmareVisionModchartTransform(registry)).updateNote(
			new NightmareVisionModchartContext(1280, 720, 4, 112, 777, 2.5), bare, 0, 0, 0, 0, 0, 0);
		var b = new NightmareVisionModchartRenderer(new NightmareVisionModchartTransform(registry)).updateNote(
			new NightmareVisionModchartContext(1280, 720, 4, 112, 777, 2.5), plainBare, 0, 0, 0, 0, 0, 0);
		check(a.rgbFlash == b.rgbFlash && a.position.x == b.position.x, 'missing rgbGraphics');
	}
}
'''


class NightmareVisionModchartLiveSpriteTest(unittest.TestCase):
    def test_typed_sprite_matches_reflective_sprite(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(FIXTURE, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(FixturePath(SOURCE)), "-cp", str(FixturePath(work)), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_note_serves_every_field_through_its_own_accessors(self):
        live = (SOURCE / "nightmarevision" / "modchart" / "NightmareVisionModchartLiveSprite.hx").read_text(encoding="utf-8")
        note = (SOURCE / "Note.hx").read_text(encoding="utf-8")
        self.assertIn("implements NightmareVisionModchartLiveSprite", note)
        start = note.index("public function modchartLiveFloat")
        end = note.index("public function modchartLiveCall")
        body = note[start:note.index("\n\t}\n", end)]
        ids = re.findall(r"public static inline var (\w+):Int", live)
        self.assertGreaterEqual(len(ids), 25)
        for name in ids:
            self.assertIn("LiveField." + name + ":", body, name)
        # Typed reads go through the same members Reflect.getProperty uses.
        for read in ["case LiveField.BASE_SCALE_X: baseScale.x", "case LiveField.WIDTH: width",
                     "case LiveField.RGB_FLASH: nightmareVisionRGB == null ? Math.NaN : nightmareVisionRGB.flash",
                     "case LiveField.MULT_SPEED: multSpeed = value"]:
            self.assertIn(read, body)


    def test_visual_offset_typed_branch_does_the_same_maths(self):
        play = (SOURCE / "PlayState.hx").read_text(encoding="utf-8")
        start = play.index("if (Std.isOfType(sprite, FlxSprite)) {\n\t\t\t\t\t\tvar flxSprite:FlxSprite = cast sprite;")
        typed = play[start:play.index("\t\t\t\t\t\treturn;\n\t\t\t\t\t}\n", play.index("flxSprite.offset.y += x * Math.sin", start))]
        last = "sprite.offset.y += x * Math.sin(angle) + y * Math.cos(angle);"
        dynamic = play[play.index("if (state.legacyCoordinates) {", start + len(typed)):play.index(last, start + len(typed)) + len(last)]

        def statements(text):
            text = text.replace("flxSprite", "sprite")
            return [line.strip() for line in text.splitlines()
                    if line.strip() and not line.strip().startswith("//") and "isOfType" not in line and "cast sprite" not in line]

        typed_lines = [line for line in statements(typed) if line not in ("}", "return;")]
        dynamic_lines = [line for line in statements(dynamic) if line not in ("}", "return;")]
        self.assertEqual(typed_lines, dynamic_lines)


if __name__ == "__main__":
    unittest.main()
