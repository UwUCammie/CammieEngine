package;

/**
	Small data and value adapter for the shared Codename options menu host.
	Only settings already owned by this engine are exposed here; imported
	options files never add fields or replace the user's native settings.
*/
class CodenameOptionsMenuModel {
	static final CATEGORIES:Array<String> = [
		'Gameplay', 'Controls & Timing', 'Graphics & Performance', 'Audio', 'Interface', 'Compatibility'
	];

	public static function categories():Array<String>
		return CATEGORIES.copy();

	public static function rows(category:String):Array<Dynamic> {
		return switch (category) {
			case 'Gameplay': gameplayRows();
			case 'Controls & Timing', 'Controls': controlsTimingRows();
			case 'Graphics & Performance': [for (row in appearanceRows().slice(1))
				if (row.field != 'useCharColor' && row.field != 'lyricsEnabled') row].concat(performanceRows());
			case 'Appearance': appearanceRows();
			case 'Audio': audioRows();
			case 'Interface': interfaceRows();
			case 'Compatibility': compatibilityRows();
			case 'Miscellaneous': legacyMiscellaneousRows();
			default: [];
		};
	}

	static function gameplayRows():Array<Dynamic> {
		return [
				{label:'Downscroll', field:'downscroll', kind:'toggle'},
				{label:'Middlescroll', field:'midscroll', kind:'toggle'},
				{label:'Ghost Tapping', field:'useCustomInput', kind:'toggle'},
				{label:'Naughtyness', field:'naughtyness', kind:'toggle'},
				{label:'Scroll Speed', field:'scrollSpeed', kind:'number', min:1.0, max:10.0, step:0.1},
				{label:'Static Scroll Speed', field:'dynamicScrollSpeed', kind:'number', min:0.0,
					max:OptionsHandler.DYNAMIC_SCROLL_SPEED_MAX, step:OptionsHandler.DYNAMIC_SCROLL_SPEED_STEP},
				{label:'Move Camera with Notes', field:'camNotes', kind:'toggle'},
				{label:'Camera Zoom Events', field:'zoomCamera', kind:'toggle'},
				{label:'Always Show Cutscenes', field:'alwaysDoCutscenes', kind:'toggle'},
				{label:'Skip Victory Screen', field:'skipVictoryScreen', kind:'toggle'}
		];
	}

	static function controlsTimingRows():Array<Dynamic> {
		return [
			{label:'Controls...', field:'controls', kind:'action'},
			{label:'Note Offset', field:'offset', kind:'number', min:-1000.0, max:1000.0, step:0.1, suffix:' ms'},
			{label:'Show Timings', field:'showTimings', kind:'toggle'}
		];
	}

	static function appearanceRows():Array<Dynamic> {
		return [
				{label:'Camera Zoom Events', field:'zoomCamera', kind:'toggle'},
				{label:'Flashing Lights', field:'flashingLights', kind:'toggle'},
				{label:'Color Health Bar', field:'useCharColor', kind:'toggle'},
				{label:'Pixel Perfect Effect', field:'week6PixelPerfect', kind:'toggle'},
				{label:'Quality', field:'quality', kind:'choice', values:CodenameOptionsQualityCompat.choices(),
					displayNames:CodenameOptionsQualityCompat.displayNames()},
				{label:'Antialiasing', field:'antialiasing', kind:'toggle'},
				{label:'Low Memory Mode', field:'lowMemoryMode', kind:'toggle'},
				{label:'Gameplay Shaders', field:'gameplayShaders', kind:'toggle'},
				{label:'Vignette Effects', field:'vignetteEffects', kind:'toggle'},
				{label:'Song Lyrics', field:'lyricsEnabled', kind:'toggle'}
		];
	}

	static function performanceRows():Array<Dynamic> {
		return [
				{label:'FPS Cap', field:'fpsCap', kind:'number', min:1.0,
					max:OptionsHandler.MAX_FPS_CAP, step:1.0, suffix:' FPS', integral:true},
				{label:'Unlimited FPS', field:'unlimitedFPS', kind:'toggle'},
				{label:'Auto Pause', field:'autoPause', kind:'toggle'},
				{label:'Show FPS Counter', field:'showFPS', kind:'toggle'},
				{label:'Show Memory Counter', field:'showMemory', kind:'toggle'},
		];
	}

	static function audioRows():Array<Dynamic> {
		return [
			{label:'Music Volume', field:'volumeMusic', kind:'number', min:0.0, max:1.0, step:0.1},
			{label:'SFX Volume', field:'volumeSFX', kind:'number', min:0.0, max:1.0, step:0.1},
			{label:'Normalize Song Audio', field:'normalizeSongAudio', kind:'toggle'}
		];
	}

	static function interfaceRows():Array<Dynamic> {
		return [
			{label:'Show Song Position', field:'showSongPos', kind:'toggle'},
			{label:'Show Note Splashes', field:'showNoteSplashes', kind:'toggle'},
			{label:'Song Lyrics', field:'lyricsEnabled', kind:'toggle'},
			{label:'Color Health Bar', field:'useCharColor', kind:'toggle'},
			{label:'Fast Scene Transitions', field:'fastSceneTransitions', kind:'toggle'}
		];
	}

	static function compatibilityRows():Array<Dynamic> {
		return [
			{label:'Ignore Unlocks', field:'ignoreUnlocks', kind:'toggle'},
			{label:'Emulate Osu Lifts', field:'emuOsuLifts', kind:'toggle'},
			{label:'Use Kade Health', field:'useKadeHealth', kind:'toggle'}
		];
	}

	static function legacyMiscellaneousRows():Array<Dynamic> {
		return performanceRows().concat([
			{label:'Always Show Cutscenes', field:'alwaysDoCutscenes', kind:'toggle'},
			{label:'Skip Victory Screen', field:'skipVictoryScreen', kind:'toggle'}
		]);
	}

	/** Clone the existing options object so navigating the menu cannot mutate
	 * the cached settings before the user leaves the root options screen. */
	public static function copyOptions(options:Dynamic):Dynamic {
		var copy:Dynamic = {};
		if (options == null) return copy;
		for (field in Reflect.fields(options))
			Reflect.setField(copy, field, Reflect.field(options, field));
		return copy;
	}

	/** Apply one explicit key action to a private options copy. Returns false
	 * for malformed/missing rows or numeric rows with no direction. */
	public static function adjust(options:Dynamic, row:Dynamic, direction:Int, shiftHeld:Bool = false):Bool {
		if (options == null || row == null) return false;
		var field:Dynamic = Reflect.field(row, 'field');
		var kind:Dynamic = Reflect.field(row, 'kind');
		if (kind == 'action') return false;
		if (!Std.isOfType(field, String) || !Reflect.hasField(options, cast field)) return false;
		var name:String = cast field;
		if (CodenameOptionsQualityCompat.isLocked(options, name)) return false;
		var value:Dynamic = Reflect.field(options, name);
		if (kind == 'toggle') {
			if (!Std.isOfType(value, Bool)) return false;
			Reflect.setField(options, name, !cast(value, Bool));
			return true;
		}
		if (kind == 'choice') {
			var values:Dynamic = Reflect.field(row, 'values');
			if (!Std.isOfType(values, Array) || direction == 0) return false;
			var choices:Array<Dynamic> = cast values;
			var index = choices.indexOf(value);
			if (index < 0) return false;
			var next = Std.int(Math.max(0, Math.min(choices.length - 1, index + (direction < 0 ? -1 : 1))));
			if (next == index) return false;
			if (name == 'quality') return CodenameOptionsQualityCompat.apply(options, choices[next]);
			Reflect.setField(options, name, choices[next]);
			return true;
		}
		if (kind != 'number' || direction == 0
			|| !(Std.isOfType(value, Int) || Std.isOfType(value, Float))) return false;
		var number:Float = value;
		if (!Math.isFinite(number)) return false;
		var min:Float = Reflect.field(row, 'min');
		var max:Float = Reflect.field(row, 'max');
		var step:Float = Reflect.field(row, 'step');
		if (!Math.isFinite(min) || !Math.isFinite(max) || !Math.isFinite(step) || step <= 0) return false;
		var inputStep = (name == 'offset' || name == 'fpsCap') && shiftHeld ? 20.0 : step;
		var updated = Math.max(min, Math.min(max, number + (direction < 0 ? -inputStep : inputStep)));
		// Avoid accumulating binary floating point error across repeated input.
		var decimalPlaces = step >= 1 ? 0 : (step >= 0.1 ? 1 : 2);
		var scale = Math.pow(10, decimalPlaces);
		updated = Math.round(updated * scale) / scale;
		if (Reflect.field(row, 'integral') == true) updated = Std.int(updated);
		if (updated == number) return false;
		Reflect.setField(options, name, updated);
		return true;
	}

	public static function valueText(options:Dynamic, row:Dynamic):String {
		if (options == null || row == null) return '';
		if (Reflect.field(row, 'kind') == 'action') return '';
		var field:String = Reflect.field(row, 'field');
		var value:Dynamic = Reflect.field(options, field);
		if (Reflect.field(row, 'kind') == 'toggle') return value == true ? 'On' : 'Off';
		if (Reflect.field(row, 'kind') == 'choice') {
			var values:Array<Dynamic> = cast Reflect.field(row, 'values');
			var labels:Array<String> = cast Reflect.field(row, 'displayNames');
			var index = values == null ? -1 : values.indexOf(value);
			return labels == null || index < 0 || index >= labels.length ? '' : labels[index];
		}
		var display = field == 'offset' ? Std.string(OptionsHandler.sanitizeOffset(value)) : Std.string(value);
		var suffix:Dynamic = Reflect.field(row, 'suffix');
		return display + (suffix == null ? '' : cast suffix);
	}
}
