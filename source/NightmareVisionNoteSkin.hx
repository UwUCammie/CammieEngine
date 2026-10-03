package;

import flixel.graphics.frames.FlxAtlasFrames;
import Strumline.StrumNote;

/** Owner-scoped Nightmare Vision note skin, shared by a source playfield. */
class NightmareVisionNoteSkin {
	public final name:String;
	public final data:Dynamic;
	public final paths:NightmareVisionPaths;
	var noteFrames:FlxAtlasFrames;
	var splashFrames:FlxAtlasFrames;
	var palettes:Array<PsychRGBPalette> = [];
	var reported:Map<String, Bool> = new Map();

	public function new(paths:NightmareVisionPaths, name:String) {
		this.paths = paths;
		this.name = name == null || StringTools.trim(name) == '' ? 'default' : name;
		var path = paths.noteskin(this.name);
		if (!paths.exists(path)) throw '[nightmare-vision-note-skin] Missing ' + path;
		data = CoolUtil.parseJson(FNFAssets.getText(path));
		if (boolField('isPixel', false))
			throw '[nightmare-vision-note-skin] Pixel-sheet skins need a separate source geometry adapter: ' + path;
		var texture = stringField('noteTexture', 'UI/notes/NOTE_assets');
		noteFrames = paths.getSparrowAtlas(texture);
	}

	public function stringField(key:String, fallback:String):String {
		var value = Reflect.field(data, key);
		return value == null || StringTools.trim(Std.string(value)) == '' ? fallback : Std.string(value);
	}

	public function numberField(key:String, fallback:Float):Float {
		var value = Reflect.field(data, key);
		if (value == null) return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) || !Math.isFinite(parsed) ? fallback : parsed;
	}

	public function boolField(key:String, fallback:Bool):Bool {
		var value = Reflect.field(data, key);
		return value == null ? fallback : value == true;
	}

	static function laneItems(table:Dynamic, lane:Int):Array<Dynamic> {
		if (!Std.isOfType(table, Array)) return [];
		var rows:Array<Dynamic> = cast table;
		if (rows.length == 0) return [];
		var row = rows[((lane % rows.length) + rows.length) % rows.length];
		return Std.isOfType(row, Array) ? cast row : [];
	}

	static function prefixExists(frames:FlxAtlasFrames, prefix:String):Bool {
		if (frames == null || prefix == null) return false;
		for (frame in frames.frames)
			if (frame.name != null && StringTools.startsWith(frame.name, prefix)) return true;
		return false;
	}

	function diagnose(key:String, message:String):Void {
		if (reported.exists(key)) return;
		reported.set(key, true);
		trace('[nightmare-vision-note-skin] ' + paths.root + ' skin=' + name + ' ' + message);
	}

	public function palette(lane:Int):PsychRGBPalette {
		var index = ((lane % 4) + 4) % 4;
		if (palettes[index] == null) {
			var palette = PsychRGBPalette.defaultFor(index, false);
			var colors:Dynamic = Reflect.field(data, 'arrowRGB');
			if (Std.isOfType(colors, Array) && index < (cast colors:Array<Dynamic>).length) {
				var entry = (cast colors:Array<Dynamic>)[index];
				if (entry != null) {
					palette = palette.copy();
					for (key in ['r', 'g', 'b']) {
						var raw = Reflect.field(entry, key);
						if (raw == null) continue;
						var value = Std.isOfType(raw, Int) ? cast(raw, Int) : Std.parseInt(Std.string(raw));
						if (value == null) continue;
						switch (key) {
							case 'r': palette.r = value;
							case 'g': palette.g = value;
							case 'b': palette.b = value;
						}
					}
				}
			}
			palettes[index] = palette;
		}
		return palettes[index];
	}

	public function applyNote(note:Note, lane:Int, ?overrideFrames:FlxAtlasFrames):Bool {
		var frames = overrideFrames == null ? noteFrames : overrideFrames;
		var entries = laneItems(Reflect.field(data, 'noteAnimations'), lane);
		var needed = note.isSustainNote ? ['hold', 'holdend'] : ['scroll'];
		var selected:Map<String, Dynamic> = new Map();
		for (entry in entries) {
			var name = Std.string(Reflect.field(entry, 'anim'));
			if (needed.indexOf(name) < 0) continue;
			var prefix = Std.string(Reflect.field(entry, 'xmlName')) + '0';
			if (!prefixExists(frames, prefix)) {
				diagnose('note-' + lane + '-' + name, 'missing note animation ' + prefix);
				return false;
			}
			selected.set(name, entry);
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
		note.setGraphicSize(Std.int(note.width * numberField('noteScale', 0.7)));
		note.antialiasing = boolField('antialiasing', true);
		if (note.isSustainNote) note.scale.y = oldScaleY;
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
		note.alpha = 1;
		note.nightmareVisionRGB = new NightmareVisionRGBGraphics(palette(lane));
		note.nightmareVisionRGB.enabled = boolField('inGameColoring', true);
		note.nightmareVisionRGB.apply(note);
		return true;
	}

	public function applyReceptor(strum:StrumNote, lane:Int):Bool {
		var entries = laneItems(Reflect.field(data, 'receptorAnimations'), lane);
		var needed = ['static', 'pressed', 'confirm'];
		var selected:Map<String, Dynamic> = new Map();
		for (entry in entries) {
			var name = Std.string(Reflect.field(entry, 'anim'));
			if (needed.indexOf(name) < 0) continue;
			var prefix = Std.string(Reflect.field(entry, 'xmlName'));
			if (!prefixExists(noteFrames, prefix)) {
				diagnose('receptor-' + lane + '-' + name, 'missing receptor animation ' + prefix);
				return false;
			}
			selected.set(name, entry);
		}
		for (name in needed) if (!selected.exists(name)) {
			diagnose('receptor-' + lane + '-' + name, 'missing receptor metadata ' + name);
			return false;
		}
		strum.frames = noteFrames;
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
		strum.nightmareVisionPalette = boolField('inGameColoring', true) ? palette(lane) : null;
		strum.setGraphicSize(Std.int(strum.width * numberField('receptorScale', 0.7)));
		strum.antialiasing = boolField('antialiasing', true);
		strum.isPixel = boolField('isPixel', false);
		strum.updateHitbox();
		strum.normalSize = strum.scale.x;
		strum.playAnim('static', true);
		return true;
	}

	public function applySplash(splash:NoteSplash, lane:Int):Bool {
		if (!boolField('splashesEnabled', true)) return false;
		if (splashFrames == null) {
			try splashFrames = paths.getSparrowAtlas(stringField('splashTexture', 'UI/notes/NoteSplash'))
			catch (error:Dynamic) {
				diagnose('splash-atlas', 'missing splash atlas: ' + Std.string(error));
				return false;
			}
		}
		var entries:Dynamic = Reflect.field(data, 'noteSplashAnimations');
		if (!Std.isOfType(entries, Array)) return false;
		var items:Array<Dynamic> = cast entries;
		if (items.length == 0) return false;
		var entry = items[((lane % items.length) + items.length) % items.length];
		if (entry == null) return false;
		var prefix = Std.string(Reflect.field(entry, 'xmlName'));
		if (!prefixExists(splashFrames, prefix)) {
			diagnose('splash-' + lane, 'missing splash animation ' + prefix);
			return false;
		}
		var atlasChanged = splash.frames != splashFrames;
		if (atlasChanged) splash.frames = splashFrames;
		if (atlasChanged || !splash.animation.exists('note' + lane + '-0'))
			splash.animation.addByPrefix('note' + lane + '-0', prefix, 24, false);
		splash.variants = 1;
		var values:Dynamic = Reflect.field(entry, 'offsets');
		var pair:Array<Dynamic> = Std.isOfType(values, Array) ? cast values : [];
		splash.nightmareVisionSplashOffset = [pair.length > 0 ? numberValue(pair[0], 0) : 0,
			pair.length > 1 ? numberValue(pair[1], 0) : 0];
		splash.scale.set(numberField('splashScale', 1), numberField('splashScale', 1));
		splash.antialiasing = boolField('antialiasing', true);
		splash.alpha = numberField('splashAlpha', 1);
		if (boolField('inGameColoring', true)) splash.shader = palette(lane).shader;
		else splash.shader = null;
		return true;
	}

	static function numberValue(value:Dynamic, fallback:Float):Float {
		if (value == null) return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) || !Math.isFinite(parsed) ? fallback : parsed;
	}
}
