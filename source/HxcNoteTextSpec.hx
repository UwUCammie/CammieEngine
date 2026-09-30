package;

using StringTools;

/** One chart-selected HXC text cue. Song ids and copy are extracted data only. */
typedef HxcNoteTextRule = {
	var songId:String;
	var chancePercent:Float;
	var lines:Array<String>;
}

/** Optional manifest-relative animated backdrop attached to a text cue. */
typedef HxcNoteTextStaticOverlayData = {
	var image:String;
	var frameWidth:Int;
	var frameHeight:Int;
	var frames:Array<Int>;
	var fps:Float;
	var loop:Bool;
	var scaleX:Float;
	var scaleY:Float;
	var camera:String;
	var idleAlpha:Float;
	var hitAlpha:Float;
	var flickerMin:Float;
	var flickerMax:Float;
	@:optional var sound:String;
}

/**
	Data-only description of a perfect-hit text cue. The native PlayState owner
	creates and removes the FlxText; this value contains no donor objects or code.
	`expireStrictlyAfter` records the donor's `startStep + 3 < currentStep`
	boundary so the cue remains visible through the boundary step.
*/
typedef HxcNoteTextSpecData = {
	var rules:Array<HxcNoteTextRule>;
	@:optional var missRules:Array<HxcNoteTextRule>;
	var triggerJudgement:String;
	var perfectOnly:Bool;
	var onceAtATime:Bool;
	var lifetimeSteps:Int;
	var expireStrictlyAfter:Bool;
	var anchor:String;
	var xOffsetMin:Float;
	var xOffsetMax:Float;
	var yOffsetMin:Float;
	var yOffsetMax:Float;
	var font:String;
	var fontSize:Int;
	var color:Int;
	var bold:Bool;
	var zIndex:Int;
	@:optional var staticOverlay:Null<HxcNoteTextStaticOverlayData>;
}

/** Validation boundary shared by generated HScript and the native text owner. */
class HxcNoteTextSpec {
	public static inline var MAX_RULES:Int = 64;
	public static inline var MAX_LINES_PER_RULE:Int = 128;
	public static inline var MAX_LINE_LENGTH:Int = 256;
	public static inline var MAX_FONT_SIZE:Int = 512;
	public static inline var MAX_OFFSET:Float = 2048;
	public static inline var MAX_LIFETIME_STEPS:Int = 64;
	public static inline var MAX_OVERLAY_FRAMES:Int = 256;
	public static inline var MAX_OVERLAY_DIMENSION:Int = 8192;
	public static inline var MAX_OVERLAY_SCALE:Float = 64;

	public static function fromDynamic(value:Dynamic):Null<HxcNoteTextSpecData> {
		if (value == null)
			return null;
		var rawRules:Dynamic = Reflect.field(value, 'rules');
		if (!Std.isOfType(rawRules, Array))
			return null;
		var rules:Array<HxcNoteTextRule> = [];
		var seenIds:Map<String, Bool> = new Map<String, Bool>();
		var hasLines = false;
		for (raw in (cast rawRules:Array<Dynamic>)) {
			if (raw == null || rules.length >= MAX_RULES)
				return null;
			var rawSongId:Dynamic = Reflect.field(raw, 'songId');
			if (!Std.isOfType(rawSongId, String))
				return null;
			var songId:String = cast rawSongId;
			var chance = numberField(raw, 'chancePercent');
			var rawLines:Dynamic = Reflect.field(raw, 'lines');
			if (songId == '' || songId != StringTools.trim(songId) || songId.length > 128 || songId.indexOf('/') >= 0
				|| songId.indexOf('\\') >= 0 || seenIds.exists(songId)
				|| Math.isNaN(chance) || chance < 0 || chance > 100
				|| !Std.isOfType(rawLines, Array))
				return null;
			seenIds.set(songId, true);
			var lines:Array<String> = [];
			for (rawLine in (cast rawLines:Array<Dynamic>)) {
				if (!Std.isOfType(rawLine, String) || lines.length >= MAX_LINES_PER_RULE)
					return null;
				var line:String = cast rawLine;
				if (line.length == 0 || line.length > MAX_LINE_LENGTH
					|| line.indexOf('\n') >= 0 || line.indexOf('\r') >= 0)
					return null;
				lines.push(line);
				hasLines = true;
			}
			rules.push({songId:songId, chancePercent:chance, lines:lines});
		}
		if (rules.length == 0 || !hasLines)
			return null;
		var rawMissRules:Dynamic = Reflect.field(value, 'missRules');
		var missRules:Array<HxcNoteTextRule> = null;
		if (rawMissRules != null) {
			if (!Std.isOfType(rawMissRules, Array))
				return null;
			missRules = [];
			var seenMissIds:Map<String, Bool> = new Map<String, Bool>();
			for (raw in (cast rawMissRules:Array<Dynamic>)) {
				if (raw == null || missRules.length >= MAX_RULES)
					return null;
				var rawSongId:Dynamic = Reflect.field(raw, 'songId');
				var rawLines:Dynamic = Reflect.field(raw, 'lines');
				var chance = numberField(raw, 'chancePercent');
				if (!Std.isOfType(rawSongId, String) || !Std.isOfType(rawLines, Array))
					return null;
				var songId:String = cast rawSongId;
				if (!seenIds.exists(songId) || seenMissIds.exists(songId)
					|| Math.isNaN(chance) || chance < 0 || chance > 100)
					return null;
				seenMissIds.set(songId, true);
				var lines:Array<String> = [];
				for (rawLine in (cast rawLines:Array<Dynamic>)) {
					if (!Std.isOfType(rawLine, String) || lines.length >= MAX_LINES_PER_RULE)
						return null;
					var line:String = cast rawLine;
					if (line.length == 0 || line.length > MAX_LINE_LENGTH
						|| line.indexOf('\n') >= 0 || line.indexOf('\r') >= 0)
						return null;
					lines.push(line);
				}
				if (lines.length == 0)
					return null;
				missRules.push({songId:songId, chancePercent:chance, lines:lines});
			}
			if (missRules.length == 0)
				return null;
		}

		var judgement = stringField(value, 'triggerJudgement').toLowerCase();
		var perfectOnly = Reflect.field(value, 'perfectOnly') == true;
		var onceAtATime = Reflect.field(value, 'onceAtATime') == true;
		var strictExpiry = Reflect.field(value, 'expireStrictlyAfter') == true;
		var anchor = stringField(value, 'anchor');
		var lifetime = intField(value, 'lifetimeSteps');
		var font = stringField(value, 'font');
		var fontSize = intField(value, 'fontSize');
		var color = intField(value, 'color');
		var bold = Reflect.field(value, 'bold') == true;
		var zIndex = intField(value, 'zIndex');
		var rawOverlay:Dynamic = Reflect.field(value, 'staticOverlay');
		var overlay:HxcNoteTextStaticOverlayData = rawOverlay == null ? null : overlayFromDynamic(rawOverlay);
		var xMin = numberField(value, 'xOffsetMin');
		var xMax = numberField(value, 'xOffsetMax');
		var yMin = numberField(value, 'yOffsetMin');
		var yMax = numberField(value, 'yOffsetMax');
		if (judgement != 'perfect' || !perfectOnly || !onceAtATime || !strictExpiry
			|| anchor != 'opponent' || lifetime < 1 || lifetime > MAX_LIFETIME_STEPS
			|| !safeRelativeAsset(font) || fontSize < 1 || fontSize > MAX_FONT_SIZE
			|| Math.isNaN(xMin) || Math.isNaN(xMax) || Math.isNaN(yMin) || Math.isNaN(yMax)
			|| xMin < 0 || xMax < xMin || xMax > MAX_OFFSET
			|| yMin < 0 || yMax < yMin || yMax > MAX_OFFSET
			|| zIndex < -100000 || zIndex > 100000
			|| (rawOverlay != null && overlay == null))
			return null;

		var result:HxcNoteTextSpecData = {
			rules: rules,
			triggerJudgement: judgement,
			perfectOnly: perfectOnly,
			onceAtATime: onceAtATime,
			lifetimeSteps: lifetime,
			expireStrictlyAfter: strictExpiry,
			anchor: anchor,
			xOffsetMin: xMin,
			xOffsetMax: xMax,
			yOffsetMin: yMin,
			yOffsetMax: yMax,
			font: font,
			fontSize: fontSize,
			color: color,
			bold: bold,
			zIndex: zIndex,
			staticOverlay: overlay
		};
		if (missRules != null)
			result.missRules = missRules;
		return result;
	}

	/** Match the original song identifiers exactly, including case and punctuation. */
	public static function appliesToSong(songId:String, spec:HxcNoteTextSpecData):Bool {
		if (songId == null || spec == null || spec.rules == null)
			return false;
		for (rule in spec.rules)
			if (rule != null && rule.songId == songId)
				return true;
		return false;
	}

	static function overlayFromDynamic(value:Dynamic):Null<HxcNoteTextStaticOverlayData> {
		if (value == null)
			return null;
		var image = stringField(value, 'image');
		var width = intField(value, 'frameWidth');
		var height = intField(value, 'frameHeight');
		var rawFrames:Dynamic = Reflect.field(value, 'frames');
		var frames:Array<Int> = [];
		if (!Std.isOfType(rawFrames, Array))
			return null;
		for (rawFrame in (cast rawFrames:Array<Dynamic>)) {
			if (frames.length >= MAX_OVERLAY_FRAMES
				|| rawFrame == null || (!Std.isOfType(rawFrame, Int) && !Std.isOfType(rawFrame, Float)))
				return null;
			var frame = Std.parseFloat(Std.string(rawFrame));
			if (Math.isNaN(frame) || frame < 0 || frame > 100000 || frame != Math.floor(frame))
				return null;
			frames.push(Std.int(frame));
		}
		var fps = numberField(value, 'fps');
		var scaleX = numberField(value, 'scaleX');
		var scaleY = numberField(value, 'scaleY');
		var idleAlpha = numberField(value, 'idleAlpha');
		var hitAlpha = numberField(value, 'hitAlpha');
		var flickerMin = numberField(value, 'flickerMin');
		var flickerMax = numberField(value, 'flickerMax');
		var camera = stringField(value, 'camera');
		var loop = Reflect.field(value, 'loop');
		var rawSound:Dynamic = Reflect.field(value, 'sound');
		var sound = rawSound == null ? '' : stringField(value, 'sound');
		var imageKey = image == null ? '' : image.toLowerCase();
		var soundKey = sound.toLowerCase();
		if (!safeRelativeAsset(image) || !imageKey.startsWith('images/') || !imageKey.endsWith('.png')
			|| width < 1 || width > MAX_OVERLAY_DIMENSION
			|| height < 1 || height > MAX_OVERLAY_DIMENSION
			|| frames.length == 0 || Math.isNaN(fps) || fps <= 0 || fps > 120
			|| loop != true && loop != false
			|| Math.isNaN(scaleX) || Math.isNaN(scaleY) || scaleX <= 0 || scaleY <= 0
			|| scaleX > MAX_OVERLAY_SCALE || scaleY > MAX_OVERLAY_SCALE
			|| camera != 'hud'
			|| Math.isNaN(idleAlpha) || idleAlpha < 0 || idleAlpha > 1
			|| Math.isNaN(hitAlpha) || hitAlpha < 0 || hitAlpha > 1
			|| Math.isNaN(flickerMin) || flickerMin < 0 || flickerMin > 1
			|| Math.isNaN(flickerMax) || flickerMax < flickerMin || flickerMax > 1
			|| (rawSound != null && (!safeRelativeAsset(sound) || !soundKey.startsWith('sounds/')
				|| !soundKey.endsWith('.ogg'))))
			return null;
		var overlay:HxcNoteTextStaticOverlayData = {
			image: image,
			frameWidth: width,
			frameHeight: height,
			frames: frames,
			fps: fps,
			loop: loop == true,
			scaleX: scaleX,
			scaleY: scaleY,
			camera: camera,
			idleAlpha: idleAlpha,
			hitAlpha: hitAlpha,
			flickerMin: flickerMin,
			flickerMax: flickerMax
		};
		if (rawSound != null)
			overlay.sound = sound;
		return overlay;
	}

	/** Apply the cue's exact lifetime inequality to the owner's current step. */
	public static function isExpired(startStep:Int, currentStep:Int,
		spec:HxcNoteTextSpecData):Bool {
		if (spec == null || startStep < 0)
			return false;
		var limit = startStep + spec.lifetimeSteps;
		return spec.expireStrictlyAfter ? currentStep > limit : currentStep >= limit;
	}

	static function stringField(value:Dynamic, name:String):String {
		var field:Dynamic = value == null ? null : Reflect.field(value, name);
		return field == null || !Std.isOfType(field, String)
			? '' : StringTools.trim(cast field);
	}

	static function numberField(value:Dynamic, name:String):Float {
		var field:Dynamic = value == null ? null : Reflect.field(value, name);
		if (field == null || (!Std.isOfType(field, Int) && !Std.isOfType(field, Float)))
			return Math.NaN;
		var number = Std.parseFloat(Std.string(field));
		return number;
	}

	static function intField(value:Dynamic, name:String):Int {
		var field:Dynamic = value == null ? null : Reflect.field(value, name);
		if (field == null || (!Std.isOfType(field, Int) && !Std.isOfType(field, Float)))
			return -2147483648;
		if (Std.isOfType(field, Int))
			return field;
		var parsed = Std.parseFloat(Std.string(field));
		if (Math.isNaN(parsed) || parsed != Math.floor(parsed)
			|| parsed < -2147483648 || parsed > 2147483647)
			return -2147483648;
		return Std.int(parsed);
	}

	static function safeRelativeAsset(value:String):Bool {
		if (value == null || value == '' || value.length > 128 || value.startsWith('/')
			|| value.indexOf('\\') >= 0 || value.indexOf(':') >= 0)
			return false;
		for (part in value.split('/'))
			if (part == '' || part == '.' || part == '..')
				return false;
		return true;
	}
}
