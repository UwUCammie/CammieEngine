package;

/** Shared section names and native option routing; never owns saved values. */
class OptionsCategories {
	static final sections:Array<String> = ['Gameplay', 'Controls & Timing',
		'Graphics & Performance', 'Audio', 'Interface', 'Compatibility'];

	public static function names():Array<String> return sections.copy();

	public static function sectionFor(field:String):String {
		return switch (field) {
			case 'controls', 'offset', 'calibrate', 'judge', 'accuracyMode', 'showTimings': 'Controls & Timing';
			case 'fpsCap', 'unlimitedFPS', 'showFPS', 'showMemory',
				'flashingLights', 'vignetteEffects': 'Graphics & Performance';
			case 'dontMuteMiss', 'normalizeSongAudio', 'hitSounds', 'soundtest': 'Audio';
			case 'showSongPos', 'showNoteSplashes', 'style', 'newJudgementPos', 'preferJudgement',
				'showComboBreaks', 'useCharColor', 'lyricsEnabled', 'allowStoryMode',
				'allowFreeplay', 'titleToggle', 'credits', 'fastSceneTransitions': 'Interface';
			case 'scrollSpeed', 'dynamicScrollSpeed', 'downscroll', 'midscroll', 'highwayDim',
				'alwaysDoCutscenes', 'skipModifierMenu', 'skipVictoryScreen', 'useCustomInput',
				'singYourHeartOut', 'modernSustains', 'camNotes', 'zoomCamera', 'useMissStun': 'Gameplay';
			default: 'Compatibility';
		};
	}

	/** Keep global indices so checkmarks, values and save mappings stay aligned. */
	public static function indices(rows:Array<Dynamic>, section:String):Array<Int> {
		var result:Array<Int> = [];
		if (rows == null || sections.indexOf(section) < 0) return result;
		for (index in 0...rows.length) {
			var row = rows[index];
			if (row != null && sectionFor(Reflect.field(row, 'intName')) == section)
				result.push(index);
		}
		return result;
	}

	public static function move(indices:Array<Int>, selected:Int, direction:Int):Int {
		if (indices == null || indices.length == 0) return -1;
		var position = indices.indexOf(selected);
		if (position < 0) position = 0;
		position = (position + direction) % indices.length;
		if (position < 0) position += indices.length;
		return indices[position];
	}
}
