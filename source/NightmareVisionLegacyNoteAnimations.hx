package;

import flixel.math.FlxPoint;

/** Historical animation hooks use the existing owner module and executeFunc scope. */
class NightmareVisionLegacyNoteAnimations {
	public static function dispatch(script:NightmareVisionScriptModule, note:Dynamic, pixel:Bool, fallback:Void->Void):Void {
		var callback = pixel ? 'loadPixelNoteAnims' : 'loadNoteAnims';
		// Preserve the pinned source's pixel admission check, including its normal-hook test.
		if (script != null && script.exists(callback) && Reflect.isFunction(script.get('loadNoteAnims'))) {
			script.executeFunc(callback, [note], note, ['super' => fallback]);
			return;
		}
		fallback();
	}

	public static function load(note:Dynamic, pixel:Bool, keys:Int):Void {
		var fallback = function():Void {
			if (pixel) SourcePixelNoteFrames.noteAnimations(note, note.noteData, note.isSustainNote, true);
			else defaults(note, keys);
		};
		if (note.nightmareVisionTypeRuntime == null) fallback();
		else note.nightmareVisionTypeRuntime.loadLegacyAnimations(note, pixel, fallback);
		// The host uses one direction-independent name; source scripts keep their full aliases.
		var colors = ['purple', 'blue', 'green', 'red', 'fx', 'LLAZER', 'RLAZER'];
		if (note.noteData < 0 || note.noteData >= colors.length) return;
		for (kind in (note.isSustainNote ? ['hold', 'holdend'] : ['Scroll'])) {
			var animation = note.animation.getByName(colors[note.noteData] + kind);
			if (animation != null) note.animation.add(kind, animation.frames, animation.frameRate,
				animation.looped, animation.flipX, animation.flipY);
		}
	}

	public static function defaults(note:Dynamic, keys:Int):Void {
		for (color in ['green', 'red', 'blue', 'purple']) note.animation.addByPrefix(color + 'Scroll', color + '0');
		if (keys > 4) {
			note.animation.addByPrefix('fxScroll', 'fx0');
			note.animation.addByPrefix('LLAZERScroll', 'LLAZER R2L');
			note.animation.addByPrefix('RLAZERScroll', 'RLAZER R2L');
		}
		if (note.isSustainNote) {
			for (color in ['purple', 'green', 'red', 'blue']) {
				note.animation.addByPrefix(color + 'holdend', color == 'purple' ? 'pruple end hold' : color + ' hold end');
				note.animation.addByPrefix(color + 'hold', color + ' hold piece');
			}
			if (keys > 4) {
				note.animation.addByPrefix('fxholdend', 'fx hold end');
				note.animation.addByPrefix('fxhold', 'fx hold piece');
				note.animation.addByPrefix('LLAZERholdend', 'LLAZER L2R');
				note.animation.addByPrefix('LLAZERhold', 'LLAZER HOLD');
				note.animation.addByPrefix('RLAZERholdend', 'LLAZER R2L');
				note.animation.addByPrefix('RLAZERhold', 'RLAZER HOLD');
			}
		}
		note.setGraphicSize(Std.int(note.width * 0.7));
		note.updateHitbox();
		NightmareVisionLegacyFieldScale.captureNote(note);
		var base:FlxPoint = Reflect.getProperty(note, 'baseScale');
		var scale:FlxPoint = note.scale;
		base.copyFrom(scale);
	}
}
