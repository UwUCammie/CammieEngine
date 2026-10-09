package;

/** Source quant rules layered over the shared per-object RGB renderer. */
class NightmareVisionQuantRendering {
	public static function classify(note:Note, prefs:Dynamic, beat:Float, legacy:Bool = false):Void {
		if (note == null || note.nightmareVisionQuantInitialized) return;
		note.nightmareVisionQuantInitialized = true;
		if (prefs == null || !(legacy ? NightmareVisionLegacyNoteColors.quantMode(prefs) : prefs.quants == true) || !note.canQuant) return;
		// The host's ordinary heads also have prevNote links; the donor only
		// supplies a previous note for a sustain. Inherit that head's grid.
		note.quant = note.isSustainNote && note.prevNote != null && note.prevNote != note
			? note.prevNote.quant : NightmareVisionQuantColorCompat.getQuant(beat);
	}

	public static function apply(note:Note, skin:NightmareVisionNoteSkin, prefs:Dynamic):Void {
		if (note == null || skin == null) return;
		if (note.nightmareVisionRGB != null && note.nightmareVisionRGB.legacyHSV != null) return;
		var globalQuants = prefs != null && prefs.quants == true;
		note.isQuant = globalQuants && skin.quantsEnabled && note.canQuant;
		var lane = note.sourceDirection >= 0 ? note.sourceDirection : note.noteData;
		var graphics = note.nightmareVisionRGB;
		if (graphics == null) graphics = note.nightmareVisionRGB = new NightmareVisionRGBGraphics(skin.palette(lane));
		else graphics.palette.copyValues(skin.palette(lane));
		// NoteUtil.getCurColors uses the global flag and stored quant even when
		// a skin disables quant animation metadata; these are separate rules.
		if (globalQuants && note.quant != 0)
			graphics.setColors(NightmareVisionQuantColorCompat.defaultColors(note.quant));
		if (note.nightmareVisionTypeRuntime != null) {
			var custom = note.nightmareVisionTypeRuntime.api.customColors(note);
			if (custom != null) graphics.setColors(cast custom);
		}
		graphics.apply(note);
	}
}
