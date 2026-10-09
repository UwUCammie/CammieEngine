package;

import flixel.graphics.frames.FlxAtlasFrames;
import flixel.math.FlxPoint;
import haxe.ds.Vector;
import Strumline.StrumNote;

/** Owner-scoped runtime implementation of the source NoteSkin data object. */
@:keep
class NightmareVisionNoteSkin {
	public static inline var DEFAULT_TEXTURE:String = NightmareVisionNoteSkinDefaults.DEFAULT_TEXTURE;
	public static inline var DEFAULT_SPLASH_TEXTURE:String = NightmareVisionNoteSkinDefaults.DEFAULT_SPLASH_TEXTURE;
	public static inline var DEFAULT_SUSTAIN_SPLASH_TEXTURE:String = NightmareVisionNoteSkinDefaults.DEFAULT_SUSTAIN_SPLASH_TEXTURE;

	@:keep public var data:Dynamic;
	@:keep public var name:String = '';
	@:keep public var keys:Int = 4;
	@:keep public var ID:Int = 0;

	@:keep public var noteTexture:String = '';
	@:keep public var splashTexture:String = '';
	@:keep public var sustainSplashTexture:String = '';

	@:keep public var noteAnims:Array<Array<Dynamic>> = [];
	@:keep public var receptorAnims:Array<Array<Dynamic>> = [];
	@:keep public var splashAnims:Array<Dynamic> = [];
	@:keep public var susSplashAnims:Array<Array<Dynamic>> = [];

	@:keep public var noteOffsets:Vector<FlxPoint>;
	@:keep public var sustainOffsets:Vector<FlxPoint>;
	@:keep public var susEndOffsets:Vector<FlxPoint>;
	@:keep public var splashOffsets:Vector<FlxPoint>;
	@:keep public var sustainSplashOffsets:Vector<FlxPoint>;
	@:keep public var receptorOffsets:Vector<FlxPoint>;

	@:keep public var quantsEnabled:Bool = true;
	@:keep public var splashesEnabled:Bool = true;
	@:keep public var sustainSplashes:Bool = true;
	@:keep public var antialiasing:Bool = true;

	@:keep public var receptorAlpha:Float = 1;
	@:keep public var sustainAlpha:Float = 1;
	@:keep public var splashAlpha:Float = 1;
	@:keep public var susSplashAlpha:Float = 1;

	@:keep public var receptorScale:Float = 0.7;
	@:keep public var noteScale:Float = 0.7;
	@:keep public var splashScale:Float = 1;
	@:keep public var susSplashScale:Float = 1;

	@:keep public var inEngineColoring:Bool = true;
	@:keep public var colors:Array<Dynamic> = [];
	@:keep public var singAnimations:Array<String> = ['singLEFT', 'singDOWN', 'singUP', 'singRIGHT'];

	public final paths:NightmareVisionPaths;
	var noteFrames:FlxAtlasFrames;
	var noteFramesTexture:String;
	var noteFramesAttempted:Bool = false;
	var splashFrames:FlxAtlasFrames;
	var splashFramesTexture:String;
	var splashFramesAttempted:Bool = false;
	var sustainSplashFramesTexture:String;
	var sustainSplashPrecached:Bool = false;
	var effectsPrecached:Bool = false;
	var palettes:Array<PsychRGBPalette> = [];
	var paletteSignatures:Array<String> = [];
	var reported:Map<String, Bool> = new Map();

	/** Native host form. The source-shaped constructor is installed by bindings. */
	@:keep public function new(paths:NightmareVisionPaths, name:String, keys:Int = 4, id:Int = 0) {
		if (paths == null) throw '[nightmare-vision-note-skin] Missing selected owner paths';
		if (keys < 0) throw '[nightmare-vision-note-skin] Vector size must be >= 0';
		this.paths = paths;
		this.name = name;
		this.keys = keys;
		this.ID = id;
		var skinPath = paths.noteskin(this.name);
		data = loadFromPath(skinPath);
		readRuntimeFields();
		if (boolField('isPixel', false))
			throw '[nightmare-vision-note-skin] Pixel-sheet skins need a separate source geometry adapter: ' + skinPath;
		refreshNoteFrames();
	}

	/** Exact source static helper: defaults are filled in place and null-only. */
	@:keep public static function resolveData(data:Dynamic):Void
		NightmareVisionNoteSkinDefaults.resolveData(data);

	function readRuntimeFields():Void {
		noteTexture = data.noteTexture;
		splashTexture = data.splashTexture;
		sustainSplashTexture = data.sustainSplashTexture;
		noteAnims = cast data.noteAnimations;
		receptorAnims = cast data.receptorAnimations;
		splashAnims = cast data.noteSplashAnimations;
		susSplashAnims = cast data.susSplashAnimations;
		singAnimations = cast data.singAnimations;
		splashesEnabled = data.splashesEnabled;
		sustainSplashes = data.susSplashesEnabled;
		antialiasing = data.antialiasing;
		receptorScale = data.receptorScale;
		noteScale = data.noteScale;
		splashScale = data.splashScale;
		susSplashScale = data.susSplashScale;
		inEngineColoring = data.inGameColoring;
		colors = cast data.arrowRGB;
		noteOffsets = pointVector(keys);
		sustainOffsets = pointVector(keys);
		susEndOffsets = pointVector(keys);
		splashOffsets = pointVector(keys);
		sustainSplashOffsets = pointVector(keys);
		receptorOffsets = pointVector(keys);
	}

	static function pointVector(count:Int):Vector<FlxPoint> {
		var values = new Vector<FlxPoint>(count);
		for (index in 0...count) values[index] = new FlxPoint();
		return values;
	}

	/** Load through this import's owner path scope; a missing JSON follows the donor's empty-data defaults. */
	@:keep public function loadFromPath(path:String):Dynamic {
		var selected = paths.scopeAssetPath(path);
		if (selected == null && path != null) {
			try selected = paths.scopeAssetPath(paths.getPath(path, null, true)) catch (_:Dynamic) {}
		}
		if (selected == null)
			throw '[nightmare-vision-note-skin] Refused skin data path outside selected owner: ' + path;
		var raw:Dynamic = {};
		if (paths.exists(selected)) {
			var content = FNFAssets.getText(selected);
			if (content != null && StringTools.trim(content) != '') {
				try raw = CoolUtil.parseJson(content) catch (error:Dynamic)
					throw '[nightmare-vision-note-skin] Invalid skin JSON at ' + selected + ': ' + Std.string(error);
				if (raw == null) raw = {};
			}
		}
		NightmareVisionNoteSkinDefaults.resolveOwnerData(raw,
			paths.hudProfile != null && paths.hudProfile.name == 'legacy-shared');
		return raw;
	}

	/** The donor method is currently an intentional no-op. Cached atlases are owner-managed. */
	@:keep public function destroy():Void {}

	public function stringField(key:String, fallback:String):String {
		var runtimeName = runtimeFieldName(key);
		var value:Dynamic = runtimeName == null ? Reflect.field(data, key) : Reflect.field(this, runtimeName);
		return value == null || StringTools.trim(Std.string(value)) == '' ? fallback : Std.string(value);
	}

	public function numberField(key:String, fallback:Float):Float {
		var runtimeName = runtimeFieldName(key);
		var value:Dynamic = runtimeName == null ? Reflect.field(data, key) : Reflect.field(this, runtimeName);
		if (value == null) return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) || !Math.isFinite(parsed) ? fallback : parsed;
	}

	public function boolField(key:String, fallback:Bool):Bool {
		var runtimeName = runtimeFieldName(key);
		var value:Dynamic = runtimeName == null ? Reflect.field(data, key) : Reflect.field(this, runtimeName);
		return value == null ? fallback : value == true;
	}

	static function runtimeFieldName(key:String):Null<String> return switch (key) {
		case 'susSplashesEnabled': 'sustainSplashes';
		case 'inGameColoring': 'inEngineColoring';
		case 'noteTexture', 'splashTexture', 'sustainSplashTexture', 'antialiasing',
			'noteScale', 'receptorScale', 'splashScale', 'susSplashScale', 'receptorAlpha',
			'sustainAlpha', 'splashAlpha', 'susSplashAlpha', 'splashesEnabled': key;
		default: null;
	};

	public function precacheEffects():Void {
		if (!splashFramesAttempted || splashFramesTexture != splashTexture) {
			splashFramesTexture = splashTexture;
			splashFrames = loadAtlas(splashTexture, 'splash-atlas');
			splashFramesAttempted = true;
		}
		if (!sustainSplashPrecached || sustainSplashFramesTexture != sustainSplashTexture) {
			sustainSplashFramesTexture = sustainSplashTexture;
			loadAtlas(sustainSplashTexture, 'sustain-splash-atlas');
			sustainSplashPrecached = true;
		}
		effectsPrecached = true;
	}

	function loadAtlas(texture:String, diagnosticKey:String):FlxAtlasFrames {
		try {
			var atlas = paths.getSparrowAtlas(texture);
			if (atlas == null) diagnose(diagnosticKey + '-' + texture, 'missing atlas ' + texture);
			return atlas;
		} catch (error:Dynamic) {
			diagnose(diagnosticKey + '-' + texture, 'missing atlas ' + texture + ': ' + Std.string(error));
			return null;
		}
	}

	/** SustainSplash.addAnims reloads its owner's current texture on every call. */
	public function loadSustainSplashFrames():FlxAtlasFrames {
		return loadAtlas(sustainSplashTexture, 'sustain-splash-atlas');
	}

	/** NoteSplash owns the explicit texture cache, rather than the skin helper. */
	public function loadNoteSplashFrames(texture:String):FlxAtlasFrames {
		return loadAtlas(texture, 'splash-atlas');
	}

	function refreshNoteFrames():FlxAtlasFrames {
		if (noteFramesAttempted && noteFramesTexture == noteTexture) return noteFrames;
		noteFramesTexture = noteTexture;
		noteFramesAttempted = true;
		noteFrames = loadAtlas(noteTexture, 'note-atlas');
		return noteFrames;
	}

	static function laneItems(table:Dynamic, lane:Int):Array<Dynamic> {
		if (!Std.isOfType(table, Array)) return [];
		var rows:Array<Dynamic> = cast table;
		if (rows.length == 0) return [];
		var row = rows[laneIndex(rows.length, lane)];
		return Std.isOfType(row, Array) ? cast row : [];
	}

	static function laneIndex(rowCount:Int, lane:Int):Int
		return rowCount <= 0 ? 0 : ((lane % rowCount) + rowCount) % rowCount;

	static function noteAnimationKind(name:String, direction:Int):Null<String> {
		if (name == null) return null;
		for (kind in ['scroll', 'hold', 'holdend']) if (name == kind || name == kind + direction) return kind;
		return null;
	}

	static function prefixExists(frames:FlxAtlasFrames, prefix:String):Bool {
		if (frames == null || prefix == null) return false;
		for (frame in frames.frames) if (frame.name != null && StringTools.startsWith(frame.name, prefix)) return true;
		return false;
	}

	function diagnose(key:String, message:String):Void {
		if (reported.exists(key)) return;
		reported.set(key, true);
		trace('[nightmare-vision-note-skin] ' + paths.root + ' skin=' + name + ' ' + message);
	}

	public function palette(lane:Int):PsychRGBPalette {
		var index = ((lane % 4) + 4) % 4;
		var entry:Dynamic = colors != null && index >= 0 && index < colors.length ? colors[index] : null;
		var components = [colorField(entry, 'r'), colorField(entry, 'g'), colorField(entry, 'b')];
		var signature = components.join(':');
		if (palettes[index] == null || paletteSignatures[index] != signature) {
			var palette = PsychRGBPalette.defaultFor(index, false);
			var hasColor = false;
			for (channel in 0...components.length) if (components[channel] != null) hasColor = true;
			if (hasColor) {
				palette = palette.copy();
				if (components[0] != null) palette.r = components[0];
				if (components[1] != null) palette.g = components[1];
				if (components[2] != null) palette.b = components[2];
			}
			palettes[index] = palette;
			paletteSignatures[index] = signature;
		}
		return palettes[index];
	}

	function refreshRGB(graphics:NightmareVisionRGBGraphics, lane:Int):NightmareVisionRGBGraphics {
		if (graphics == null) graphics = new NightmareVisionRGBGraphics(palette(lane));
		else graphics.palette.copyValues(palette(lane));
		graphics.enabled = inEngineColoring;
		return graphics;
	}

	static function colorField(entry:Dynamic, key:String):Null<Int> {
		if (entry == null) return null;
		var raw = Reflect.field(entry, key);
		if (raw == null) return null;
		if (Std.isOfType(raw, Int)) return cast raw;
		return Std.parseInt(Std.string(raw));
	}

	public function applyNote(note:Note, lane:Int, ?overrideFrames:FlxAtlasFrames):Bool {
		var frames = overrideFrames == null ? refreshNoteFrames() : overrideFrames;
		if (frames == null) return false;
		var direction = noteAnims == null ? lane : laneIndex(noteAnims.length, lane);
		var entries = laneItems(noteAnims, lane);
		var needed = note.isSustainNote ? ['hold', 'holdend'] : ['scroll'];
		var selected:Map<String, Dynamic> = new Map();
		for (entry in entries) {
			var sourceName:Dynamic = entry == null ? null : Reflect.field(entry, 'anim');
			var name = noteAnimationKind(sourceName == null ? null : Std.string(sourceName), direction);
			if (name == null || needed.indexOf(name) < 0) continue;
			var prefix = Std.string(Reflect.field(entry, 'xmlName')) + '0';
			selected.set(name, entry);
			if (!prefixExists(frames, prefix)) {
				diagnose('note-' + lane + '-' + sourceName, 'missing note animation ' + prefix);
				// Source Note.reloadNote replaces the resolved atlas before asking
				// the current skin to add its usual animation prefixes. A partial
				// note-type atlas is still authoritative; Flixel simply leaves any
				// absent animation uncreated. Only the initial skin load keeps the
				// strict validation that protects the native/default fallback.
				if (overrideFrames == null) return false;
			}
		}
		for (name in needed) if (!selected.exists(name)) {
			diagnose('note-' + lane + '-' + name, 'missing note metadata ' + name);
			return false;
		}
		var oldAnim = note.animation.curAnim == null ? null : note.animation.curAnim.name;
		var oldScaleY = note.scale.y;
		note.frames = frames;
		for (name in needed) {
			var entry = selected.get(name);
			note.animation.addByPrefix(name == 'scroll' ? 'Scroll' : name,
				Std.string(Reflect.field(entry, 'xmlName')) + '0',
				Std.int(numberValue(Reflect.field(entry, 'fps'), 24)), true);
		}
		note.scale.set(noteScale, note.isSustainNote ? oldScaleY : noteScale);
		note.antialiasing = antialiasing;
		note.resetPsychVisualOffset();
		note.updateHitbox();
		var target = oldAnim != null && note.animation.exists(oldAnim) ? oldAnim
			: (note.isSustainNote ? 'holdend' : 'Scroll');
		note.animation.play(target, true);
		if (!note.isSustainNote) {
			note.centerOffsets();
			note.centerOrigin();
		}
		note.normalSize = note.scale.x;
		note.baseScale.set(note.scale.x, note.scale.y);
		note.nightmareVisionRGB = refreshRGB(note.nightmareVisionRGB, lane);
		note.nightmareVisionRGB.apply(note);
		return true;
	}

	public function applyReceptor(strum:StrumNote, lane:Int, ?overrideFrames:FlxAtlasFrames):Bool {
		var frames = overrideFrames == null ? refreshNoteFrames() : overrideFrames;
		if (frames == null) return false;
		var entries = laneItems(receptorAnims, lane);
		var needed = ['static', 'pressed', 'confirm'];
		var selected:Map<String, Dynamic> = new Map();
		for (entry in entries) {
			var name = Std.string(Reflect.field(entry, 'anim'));
			if (needed.indexOf(name) < 0) continue;
			var prefix = Std.string(Reflect.field(entry, 'xmlName'));
			if (!prefixExists(frames, prefix)) {
				diagnose('receptor-' + lane + '-' + name, 'missing receptor animation ' + prefix);
				return false;
			}
			selected.set(name, entry);
		}
		for (name in needed) if (!selected.exists(name)) {
			diagnose('receptor-' + lane + '-' + name, 'missing receptor metadata ' + name);
			return false;
		}
		strum.frames = frames;
		var offsets:Map<String, Array<Float>> = new Map();
		for (name in needed) {
			var entry = selected.get(name);
			strum.animation.addByPrefix(name, Std.string(Reflect.field(entry, 'xmlName')),
				Std.int(numberValue(Reflect.field(entry, 'fps'), 24)), Reflect.field(entry, 'looping') == true);
			var values:Dynamic = Reflect.field(entry, 'offsets');
			var pair:Array<Dynamic> = Std.isOfType(values, Array) ? cast values : [];
			offsets.set(name, [pair.length > 0 ? numberValue(pair[0], 0) : 0,
				pair.length > 1 ? numberValue(pair[1], 0) : 0]);
		}
		strum.nightmareVisionOffsets = offsets;
		// Donor PlayField sets this on every receptor whenever a skin is applied.
		// Source PlayState can reuse a line previously configured by Psych, whose
		// RGB flag may be false even though this skin enables lane coloring.
		strum.useRGBShader = inEngineColoring;
		strum.nightmareVisionPalette = inEngineColoring ? palette(lane) : null;
		strum.nightmareVisionRGB = refreshRGB(strum.nightmareVisionRGB, lane);
		strum.scale.set(receptorScale, receptorScale);
		strum.baseScale.set(strum.scale.x, strum.scale.y);
		strum.antialiasing = antialiasing;
		strum.isPixel = boolField('isPixel', false);
		strum.updateHitbox();
		strum.normalSize = strum.scale.x;
		strum.playAnim('static', true);
		strum.resetAnim = 0;
		return true;
	}

	public function applySplash(splash:NoteSplash, lane:Int):Bool {
		if (!splashesEnabled) return false;
		if (!splashFramesAttempted || splashFramesTexture != splashTexture) {
			splashFramesTexture = splashTexture;
			splashFramesAttempted = true;
			splashFrames = loadAtlas(splashTexture, 'splash-atlas');
		}
		if (splashFrames == null) return false;
		if (splashAnims == null || splashAnims.length == 0) return false;
		var entry = splashAnims[((lane % splashAnims.length) + splashAnims.length) % splashAnims.length];
		if (entry == null) return false;
		var prefix = Std.string(Reflect.field(entry, 'xmlName'));
		if (!prefixExists(splashFrames, prefix)) {
			diagnose('splash-' + lane, 'missing splash animation ' + prefix);
			return false;
		}
		var atlasChanged = splash.frames != splashFrames;
		if (atlasChanged) splash.frames = splashFrames;
		var animationName = 'note' + lane + '-0';
		if (atlasChanged || !splash.animation.exists(animationName))
			splash.animation.addByPrefix(animationName, prefix,
				Std.int(numberValue(Reflect.field(entry, 'fps'), 24)), Reflect.field(entry, 'looping') == true);
		splash.variants = 1;
		var values:Dynamic = Reflect.field(entry, 'offsets');
		var pair:Array<Dynamic> = Std.isOfType(values, Array) ? cast values : [];
		splash.nightmareVisionSplashOffset = [pair.length > 0 ? numberValue(pair[0], 0) : 0,
			pair.length > 1 ? numberValue(pair[1], 0) : 0];
		splash.scale.set(splashScale, splashScale);
		splash.baseScale.set(splash.scale.x, splash.scale.y);
		splash.antialiasing = antialiasing;
		splash.nightmareVisionRGB = refreshRGB(splash.nightmareVisionRGB, lane);
		splash.nightmareVisionRGB.apply(splash);
		return true;
	}

	static function numberValue(value:Dynamic, fallback:Float):Float {
		if (value == null) return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) || !Math.isFinite(parsed) ? fallback : parsed;
	}
}
