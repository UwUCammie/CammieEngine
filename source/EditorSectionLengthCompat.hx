package;

/** Section duration for editor grids when a donor chart omits the old
 * lengthInSteps field. Psych sectionBeats expresses the same duration in beats. */
class EditorSectionLengthCompat {
	public static function steps(section:Dynamic):Int {
		if (section == null)
			return 16;
		var authored:Dynamic = Reflect.field(section, 'lengthInSteps');
		if (Std.isOfType(authored, Int) && authored > 0)
			return authored;
		if (Std.isOfType(authored, Float) && Math.isFinite(authored) && authored > 0)
			return Std.int(Math.round(authored));
		var beats:Dynamic = Reflect.field(section, 'sectionBeats');
		if ((Std.isOfType(beats, Int) || Std.isOfType(beats, Float))
			&& Math.isFinite(beats) && beats > 0)
			return Std.int(Math.max(1, Math.round(beats * 4)));
		return 16;
	}

	public static function normalize(sections:Array<Dynamic>):Void {
		if (sections == null)
			return;
		for (section in sections)
			if (section != null)
				Reflect.setField(section, 'lengthInSteps', steps(section));
	}
}
