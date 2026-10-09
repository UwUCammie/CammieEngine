package;

import flixel.math.FlxPoint;

/** Historical post-skin hold construction; source bodies retain their raw scale. */
class NightmareVisionLegacySustain {
	public static function finish(note:Dynamic, initialWidth:Float, step:Float, speed:Float, pixel:Bool, pixelZoom:Float):Void {
		note.hitsoundDisabled = true;
		note.copyAngle = false;
		note.offsetX += initialWidth / 2;
		note.updateHitbox();
		note.offsetX -= note.width / 2;
		if (pixel) note.offsetX += 30;
		var previous:Dynamic = note.prevNote;
		if (previous != null && previous.isSustainNote) {
			previous.animation.play('hold');
			previous.scale.y *= step / 100 * 1.05;
			previous.scale.y *= speed;
			if (pixel) {
				previous.scale.y *= 1.19;
				previous.scale.y *= 6 / note.height;
			}
			previous.updateHitbox();
			capture(previous);
		}
		if (pixel) {
			note.scale.y *= pixelZoom;
			note.updateHitbox();
		}
		note.x += note.offsetX;
		capture(note);
	}

	static function capture(note:Dynamic):Void {
		NightmareVisionLegacyFieldScale.captureNote(note);
		var base:FlxPoint = Reflect.getProperty(note, 'baseScale');
		var scale:FlxPoint = note.scale;
		base.copyFrom(scale);
	}
}
