package;

import flixel.group.FlxGroup.FlxTypedGroup;

/** Historical public spawning uses one state-owned group, independent of modern field gates. */
class NightmareVisionLegacySplashRuntime {
	public static function onNote(note:Note, prefs:Dynamic, spawn:(Float, Float, Int, Note)->Void):Void {
		if (prefs.noteSplashes && note != null) {
			var field:NightmareVisionPlayFieldView = cast note.playField;
			var strum:Strumline.StrumNote = field.members[note.noteData];
			if (strum != null) spawn(strum.x, strum.y, note.noteData, note);
		}
	}

	public static function spawn(x:Float, y:Float, data:Int, note:Note, script:NightmareVisionScriptModule,
		keys:Int, prefs:Dynamic, readGroup:Void->FlxTypedGroup<NightmareVisionNoteSplash>,
		create:Void->NightmareVisionNoteSplash, notify:Array<Dynamic>->Dynamic):Void {
		var selected = NightmareVisionLegacyNoteSkin.splash(script, keys, prefs, data, note);
		var group = readGroup();
		var splash = group.recycle(NightmareVisionLegacyNoteSplash, create);
		// The source dereferences note.playField even though the argument is optional.
		// Keep that failure attributable instead of allowing a native null dereference.
		if (note == null) throw '[nightmare-vision-note-splash] Historical spawnNoteSplash requires a note';
		var offset = selected.offsets[data];
		splash.setupLegacyCoordinates(x + offset.x, y + offset.y, data, selected.texture,
			selected.hue, selected.saturation, selected.brightness, cast note.playField);
		group.add(splash);
		notify([splash, data, note, note.mustPress, false]);
	}
}
