package;

import haxe.ds.StringMap;

using StringTools;

/** One row of the native option seed table. A null owner field means that
	dialect has no matching preference. */
typedef SourceOwnerSeedRow = {
	var native:String;
	var psych:String;
	var nightmare:String;
	var kind:String;
}

/** The parts of an owner-scoped ClientPrefs store that do not depend on which
	Psych-family engine the mod was written for: the owner root guard, the owner
	save contract, seeding from the player's native options and the loose
	map/object helpers. The dialect classes keep their own defaults, field lists
	and script-facing methods. */
@:keep
class SourceOwnerPreferences {
	public static inline var OWNER_PREFIX:String = 'assets/imported_mods/';
	public static final NOTE_ACTIONS:Array<String> = ['note_left', 'note_down', 'note_up', 'note_right'];

	/** Native options that mean exactly the same thing as an owner preference.
		`zeroWhenFalse` is for an owner that only has a strength value where the
		player has an on/off switch. */
	public static final NATIVE_SEEDS:Array<SourceOwnerSeedRow> = [
		{native:'downscroll', psych:'downScroll', nightmare:'downScroll', kind:'bool'},
		{native:'midscroll', psych:'middleScroll', nightmare:'middleScroll', kind:'bool'},
		{native:'showFPS', psych:'showFPS', nightmare:null, kind:'bool'},
		{native:'flashingLights', psych:'flashing', nightmare:'flashing', kind:'bool'},
		{native:'autoPause', psych:'autoPause', nightmare:'autoPause', kind:'bool'},
		{native:'antialiasing', psych:'antialiasing', nightmare:'globalAntialiasing', kind:'bool'},
		{native:'gameplayShaders', psych:'shaders', nightmare:'shaders', kind:'bool'},
		{native:'zoomCamera', psych:'camZooms', nightmare:'camZooms', kind:'bool'},
		{native:'showNoteSplashes', psych:'splashAlpha', nightmare:'noteSplashes', kind:'splash'},
		{native:'offset', psych:'noteOffset', nightmare:'noteOffset', kind:'number'}
	];

	/** Clean an owner root and refuse anything that is not one imported mod.
		Both dialects must agree here, or the same root could be reusable for one
		and rejected by the other. */
	public static function normalizeOwner(owner:String, label:String):String {
		if (owner == null) throw '[' + label + '] Missing owner root';
		var path = owner.replace('\\', '/');
		while (path.indexOf('//') >= 0) path = path.replace('//', '/');
		while (path.length > OWNER_PREFIX.length && path.endsWith('/'))
			path = path.substr(0, path.length - 1);
		if (!path.startsWith(OWNER_PREFIX) || path.length <= OWNER_PREFIX.length
			|| path.indexOf('/../') >= 0 || path.endsWith('/..')
			|| path.indexOf('/./') >= 0 || path.endsWith('/.'))
			throw '[' + label + '] Refused an owner outside imported mods';
		return path;
	}

	/** The owner save view only has to read and write one field; some dialects
		also flush it themselves. */
	public static function requireOwnerSave(ownerSave:Dynamic, label:String, needsFlush:Bool):Void {
		if (ownerSave == null || !Reflect.isFunction(Reflect.field(ownerSave, 'getField'))
			|| !Reflect.isFunction(Reflect.field(ownerSave, 'setField'))
			|| (needsFlush && !Reflect.isFunction(Reflect.field(ownerSave, 'flush'))))
			throw '[' + label + '] Owner save view is unavailable';
	}

	public static function callOwnerSave(ownerSave:Dynamic, label:String, method:String, args:Array<Dynamic>):Dynamic {
		var callback:Dynamic = ownerSave == null ? null : Reflect.field(ownerSave, method);
		if (!Reflect.isFunction(callback))
			throw '[' + label + '] Owner save method unavailable: ' + method;
		return Reflect.callMethod(ownerSave, callback, args);
	}

	/** Copy the player's matching native options into a fresh owner preference
		object. Values are copied, never bound, so later owner writes stay local. */
	public static function seedNativeOptions(target:Dynamic, options:Dynamic, nightmare:Bool):Void {
		if (target == null || options == null) return;
		for (row in NATIVE_SEEDS) {
			var name = nightmare ? row.nightmare : row.psych;
			if (name == null) continue;
			var value:Dynamic = field(options, row.native);
			switch (row.kind) {
				case 'bool':
					if (Std.isOfType(value, Bool)) Reflect.setField(target, name, value);
				case 'number':
					// The host offset is fractional, so it is kept as is.
					if (!Std.isOfType(value, Int) && !Std.isOfType(value, Float)) continue;
					var number:Float = value;
					if (Math.isFinite(number)) Reflect.setField(target, name, number);
				case 'splash':
					if (!Std.isOfType(value, Bool)) continue;
					if (nightmare) Reflect.setField(target, name, value);
					else if (value == false) Reflect.setField(target, name, 0.0);
				default:
			}
		}
	}

	/** Start the four note lanes on the keys the player bound in the engine.
		Call it before the owner's saved binds are loaded so those still win. */
	public static function seedNativeNoteKeys(keyBinds:Dynamic, nativeKeys:Array<Dynamic>):Void {
		if (keyBinds == null || nativeKeys == null) return;
		for (index in 0...NOTE_ACTIONS.length) {
			var keys:Dynamic = nativeKeys[index];
			if (keys == null || !Std.isOfType(keys, Array)) continue;
			mapSet(keyBinds, NOTE_ACTIONS[index], (cast keys:Array<Dynamic>).copy());
		}
	}

	public static function gameplayDefaults():StringMap<Dynamic> {
		var settings = new StringMap<Dynamic>();
		settings.set('scrollspeed', 1.0); settings.set('scrolltype', 'multiplicative');
		settings.set('songspeed', 1.0); settings.set('healthgain', 1.0); settings.set('healthloss', 1.0);
		settings.set('instakill', false); settings.set('practice', false); settings.set('botplay', false);
		settings.set('opponentplay', false);
		return settings;
	}

	public static function isStringMap(value:Dynamic):Bool return value != null && Std.isOfType(value, StringMap);
	public static function isObject(value:Dynamic):Bool return value != null && Type.typeof(value) == TObject;

	public static function field(value:Dynamic, name:String):Dynamic {
		if (value == null) return null;
		if (isStringMap(value)) return (cast value:StringMap<Dynamic>).get(name);
		return Reflect.field(value, name);
	}

	public static function hasField(value:Dynamic, name:String):Bool {
		if (value == null) return false;
		if (isStringMap(value)) return (cast value:StringMap<Dynamic>).exists(name);
		return Reflect.hasField(value, name);
	}

	public static function mapKeys(value:Dynamic):Array<String> {
		var keys:Array<String> = [];
		if (value == null) return keys;
		if (isStringMap(value)) {
			for (key in (cast value:StringMap<Dynamic>).keys()) keys.push(key);
		} else if (isObject(value)) keys = Reflect.fields(value);
		return keys;
	}

	public static function mapGet(value:Dynamic, name:String):Dynamic return field(value, name);
	public static function mapExists(value:Dynamic, name:String):Bool return hasField(value, name);

	public static function mapSet(value:Dynamic, name:String, item:Dynamic):Void {
		if (isStringMap(value)) (cast value:StringMap<Dynamic>).set(name, item);
		else if (value != null) Reflect.setField(value, name, item);
	}

	public static function copyIntoMap(source:Dynamic, destination:Dynamic, clone:Bool = true):Void {
		if (source == null || destination == null) return;
		for (name in mapKeys(source)) mapSet(destination, name,
			clone ? cloneValue(mapGet(source, name)) : mapGet(source, name));
	}

	public static function copyMap(value:Dynamic):StringMap<Dynamic> {
		var copied = new StringMap<Dynamic>();
		copyIntoMap(value, copied);
		return copied;
	}

	public static function mapToObject(source:Dynamic):Dynamic {
		var object:Dynamic = {};
		for (name in mapKeys(source)) Reflect.setField(object, name, cloneValue(mapGet(source, name)));
		return object;
	}

	/** Deep copy of plain save data: arrays, string maps and anonymous objects. */
	public static function cloneValue(value:Dynamic):Dynamic {
		if (value == null) return null;
		if (Std.isOfType(value, Array)) {
			var copied:Array<Dynamic> = [];
			for (item in (cast value:Array<Dynamic>)) copied.push(cloneValue(item));
			return copied;
		}
		if (isStringMap(value)) return copyMap(value);
		if (isObject(value)) {
			var copied:Dynamic = {};
			for (name in Reflect.fields(value)) Reflect.setField(copied, name, cloneValue(Reflect.field(value, name)));
			return copied;
		}
		return value;
	}
}
