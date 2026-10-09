package;

import flixel.math.FlxPoint;

/** Historical scalar field scaling, shared by assignment, membership and reload. */
class NightmareVisionLegacyFieldScale {
	public static function captureNote(note:Dynamic):Void {
		note.baseScaleX = note.scale.x;
		note.baseScaleY = note.scale.y;
	}
	public static function note(note:Dynamic, value:Float):Void {
		var scale:FlxPoint = note.scale;
		scale.set(note.baseScaleX * value, note.isSustainNote ? note.baseScaleY : note.baseScaleY * value);
		// Native dynamic field access does not invoke Haxe property getters.
		var baseline:FlxPoint = Reflect.getProperty(note, 'defScale');
		baseline.copyFrom(scale);
		note.updateHitbox();
	}
	public static function remove(note:Dynamic):Void {
		var scale:FlxPoint = note.scale;
		scale.set(note.baseScaleX, note.baseScaleY);
		// Native dynamic field access does not invoke Haxe property getters.
		var baseline:FlxPoint = Reflect.getProperty(note, 'defScale');
		baseline.copyFrom(scale);
		note.updateHitbox();
	}
	public static function apply(receptors:Array<Dynamic>, notes:Array<Dynamic>, value:Float):Void {
		for (strum in receptors) {
			var anim:String = strum.animation.curAnim == null ? '' : strum.animation.curAnim.name;
			strum.playAnim('static', true);
			strum.setGraphicSize(Std.int((cast Reflect.getProperty(strum, 'frameWidth'):Float) * 0.7 * value));
			strum.updateHitbox();
			strum.playAnim(anim, true);
		}
		for (entry in notes) note(entry, value);
	}
}
