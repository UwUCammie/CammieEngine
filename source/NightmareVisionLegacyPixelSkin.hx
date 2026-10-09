package;

import flixel.math.FlxPoint;

/** Historical pixel reload state over the shared Psych-family sheet loader. */
class NightmareVisionLegacyPixelSkin {
	public static function applyNote(note:Note, graphic:Dynamic, lane:Int, zoom:Float):Bool {
		var animation = note.animation.curAnim == null ? null : note.animation.curAnim.name;
		var oldScaleY = note.scale.y;
		if (!SourcePixelNoteFrames.install(note, graphic, note.isSustainNote ? 2 : 5, zoom)) return false;
		if (note.isSustainNote) {
			note.originalHeightForCalcs = graphic.height / 2;
			note.offsetX += note.lastNoteOffsetXForPixelAutoAdjusting;
			note.lastNoteOffsetXForPixelAutoAdjusting = (note.width - 7) * (zoom / 2);
			note.offsetX -= note.lastNoteOffsetXForPixelAutoAdjusting;
		}
		SourcePixelNoteFrames.noteAnimations(note, lane, note.isSustainNote, true);
		note.antialiasing = false;
		if (note.isSustainNote) note.scale.y = oldScaleY;
		note.resetPsychVisualOffset();
		note.updateHitbox();
		if (!note.nightmareVisionSustainInitialized) note.nightmareVisionSustainInitialWidth = note.width;
		NightmareVisionLegacyFieldScale.captureNote(note);
		note.baseScale.copyFrom(note.scale);
		note.animation.play(animation != null && note.animation.exists(animation) ? animation : note.isSustainNote ? 'holdend' : 'Scroll', true);
		note.normalSize = note.scale.x;
		if (note.nightmareVisionRGB != null) note.nightmareVisionRGB.apply(note);
		return true;
	}

	public static function applyReceptor(strum:Strumline.StrumNote, skin:NightmareVisionNoteSkin, graphic:Dynamic, lane:Int, zoom:Float):Bool {
		var animation = strum.animation.curAnim == null ? null : strum.animation.curAnim.name;
		if (!SourcePixelNoteFrames.install(strum, graphic, 5, zoom)) return false;
		SourcePixelNoteFrames.receptorAnimations(strum, lane, true);
		strum.antialiasing = false;
		strum.isPixel = true;
		strum.nightmareVisionOffsets = new Map();
		strum.useRGBShader = skin.inEngineColoring;
		strum.nightmareVisionPalette = skin.inEngineColoring ? skin.palette(lane) : null;
		if (strum.nightmareVisionRGB == null) strum.nightmareVisionRGB = new NightmareVisionRGBGraphics(skin.palette(lane));
		strum.nightmareVisionRGB.enabled = skin.inEngineColoring;
		strum.baseScale.copyFrom(strum.scale);
		strum.updateHitbox();
		strum.normalSize = strum.scale.x;
		strum.playAnim(animation != null && strum.animation.exists(animation) ? animation : 'static', true);
		return true;
	}
}
