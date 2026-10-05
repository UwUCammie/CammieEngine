package;

/** Fresh copies of the pinned Nightmare Vision NoteUtil skin defaults. */
@:keep
class NightmareVisionNoteSkinDefaults {
	public static inline var DEFAULT_TEXTURE:String = 'UI/notes/NOTE_assets';
	public static inline var DEFAULT_SPLASH_TEXTURE:String = 'UI/notes/noteSplashes';
	public static inline var DEFAULT_SUSTAIN_SPLASH_TEXTURE:String = 'UI/notes/sustainHold';

	/** Match NoteSkin.resolveData's null-coalescing defaults and animation normalization. */
	@:keep public static function resolveData(data:Dynamic):Void {
		if (data == null) throw '[nightmare-vision-note-skin] resolveData requires an object';
		if (!Reflect.isObject(data) || Std.isOfType(data, Array))
			throw '[nightmare-vision-note-skin] Skin data must be an object';

		setDefault(data, 'noteTexture', DEFAULT_TEXTURE);
		setDefault(data, 'splashTexture', DEFAULT_SPLASH_TEXTURE);
		setDefault(data, 'sustainSplashTexture', DEFAULT_SUSTAIN_SPLASH_TEXTURE);
		setDefault(data, 'antialiasing', true);
		setDefault(data, 'noteAnimations', defaultNoteAnimations());
		setDefault(data, 'receptorAnimations', defaultReceptorAnimations());
		setDefault(data, 'noteSplashAnimations', defaultSplashAnimations());
		setDefault(data, 'susSplashAnimations', defaultSustainSplashAnimations());

		var nested:Array<String> = ['noteAnimations', 'receptorAnimations', 'susSplashAnimations'];
		for (name in nested) {
			var rows:Dynamic = Reflect.field(data, name);
			if (!Std.isOfType(rows, Array)) continue;
			for (row in (cast rows:Array<Dynamic>)) correctAnimations(row);
		}
		correctAnimations(Reflect.field(data, 'noteSplashAnimations'));

		setDefault(data, 'singAnimations', ['singLEFT', 'singDOWN', 'singUP', 'singRIGHT']);
		setDefault(data, 'splashesEnabled', true);
		setDefault(data, 'susSplashesEnabled', true);
		setDefault(data, 'receptorAlpha', 1.0);
		setDefault(data, 'sustainAlpha', 1.0);
		setDefault(data, 'splashAlpha', 1.0);
		setDefault(data, 'susSplashAlpha', 1.0);
		setDefault(data, 'receptorScale', 0.7);
		setDefault(data, 'noteScale', 0.7);
		setDefault(data, 'splashScale', 1.0);
		setDefault(data, 'susSplashScale', 1.0);
		setDefault(data, 'arrowRGB', defaultColors());
		setDefault(data, 'inGameColoring', true);
	}

	static function setDefault(target:Dynamic, name:String, value:Dynamic):Void
		if (Reflect.field(target, name) == null) Reflect.setField(target, name, value);

	static function correctAnimations(entries:Dynamic):Void {
		if (!Std.isOfType(entries, Array)) return;
		for (entry in (cast entries:Array<Dynamic>)) if (entry != null) {
			if (Reflect.field(entry, 'offsets') == null) Reflect.setField(entry, 'offsets', [0, 0]);
			if (Reflect.field(entry, 'looping') == null) Reflect.setField(entry, 'looping', false);
			if (Reflect.field(entry, 'fps') == null) Reflect.setField(entry, 'fps', 24);
		}
	}

	static function defaultNoteAnimations():Array<Array<Dynamic>> return [
		[
			{anim:'scroll', xmlName:'purple', offsets:[0, 0], looping:true, fps:24},
			{anim:'hold', xmlName:'purple hold piece', offsets:[0, 0], looping:true, fps:24},
			{anim:'holdend', xmlName:'pruple end hold', offsets:[0, 0], looping:true, fps:24}
		],
		[
			{anim:'scroll', xmlName:'blue', offsets:[0, 0], looping:true, fps:24},
			{anim:'hold', xmlName:'blue hold piece', offsets:[0, 0], looping:true, fps:24},
			{anim:'holdend', xmlName:'blue hold end', offsets:[0, 0], looping:true, fps:24}
		],
		[
			{anim:'scroll', xmlName:'green', offsets:[0, 0], looping:true, fps:24},
			{anim:'hold', xmlName:'green hold piece', offsets:[0, 0], looping:true, fps:24},
			{anim:'holdend', xmlName:'green hold end', offsets:[0, 0], looping:true, fps:24}
		],
		[
			{anim:'scroll', xmlName:'red', offsets:[0, 0], looping:true, fps:24},
			{anim:'hold', xmlName:'red hold piece', offsets:[0, 0], looping:true, fps:24},
			{anim:'holdend', xmlName:'red hold end', offsets:[0, 0], looping:true, fps:24}
		]
	];

	static function defaultReceptorAnimations():Array<Array<Dynamic>> return [
		[
			{anim:'static', xmlName:'arrowLEFT', offsets:[0, 0], looping:false, fps:24},
			{anim:'pressed', xmlName:'left press', offsets:[0, 0], looping:false, fps:24},
			{anim:'confirm', xmlName:'left confirm', offsets:[0, 0], looping:false, fps:24}
		],
		[
			{anim:'static', xmlName:'arrowDOWN', offsets:[0, 0], looping:false, fps:24},
			{anim:'pressed', xmlName:'down press', offsets:[0, 0], looping:false, fps:24},
			{anim:'confirm', xmlName:'down confirm', offsets:[0, 0], looping:false, fps:24}
		],
		[
			{anim:'static', xmlName:'arrowUP', offsets:[0, 0], looping:false, fps:24},
			{anim:'pressed', xmlName:'up press', offsets:[0, 0], looping:false, fps:24},
			{anim:'confirm', xmlName:'up confirm', offsets:[0, 0], looping:false, fps:24}
		],
		[
			{anim:'static', xmlName:'arrowRIGHT', offsets:[0, 0], looping:false, fps:24},
			{anim:'pressed', xmlName:'right press', offsets:[0, 0], looping:false, fps:24},
			{anim:'confirm', xmlName:'right confirm', offsets:[0, 0], looping:false, fps:24}
		]
	];

	static function defaultSplashAnimations():Array<Dynamic> return [
		{anim:'note0', xmlName:'note splash purple', offsets:[4, 15]},
		{anim:'note1', xmlName:'note splash blue', offsets:[13, 15]},
		{anim:'note2', xmlName:'note splash green', offsets:[16, 15]},
		{anim:'note3', xmlName:'note splash red', offsets:[22, 15]}
	];

	static function defaultSustainSplashAnimations():Array<Array<Dynamic>> return [
		sustainSplashRow(), sustainSplashRow(), sustainSplashRow(), sustainSplashRow()
	];

	static function sustainSplashRow():Array<Dynamic> return [
		{anim:'start', xmlName:'start', offsets:[0, 0], looping:false},
		{anim:'loop', xmlName:'loop', offsets:[45, 35], looping:true},
		{anim:'end', xmlName:'end', offsets:[50, 60], looping:false}
	];

	static function defaultColors():Array<Dynamic> return [
		{r:0xFFC24B99, g:0xFFFFFFFF, b:0xFF3C1F56},
		{r:0xFF00FFFF, g:0xFFFFFFFF, b:0xFF1542B7},
		{r:0xFF12FA05, g:0xFFFFFFFF, b:0xFF0A4447},
		{r:0xFFF9393F, g:0xFFFFFFFF, b:0xFF651038}
	];
}
