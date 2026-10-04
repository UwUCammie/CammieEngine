package;

import haxe.ds.StringMap;

/** Owner-local implementation of Nightmare Vision's ModOptions add/getValue
 * surface. Values use the selected import's save record instead of ModOptions'
 * process-global FlxSave namespace. */
@:keep
class NightmareVisionSourceOptions {
	public static inline var SAVE_FIELD:String = 'nightmareVisionSourceModOptions';
	public final ownerRoot:String;
	final ownerSave:Dynamic;
	var released:Bool = false;

	public function new(ownerRoot:String, ownerSave:Dynamic) {
		this.ownerRoot = normalizeOwner(ownerRoot);
		if (this.ownerRoot == '' || ownerSave == null
			|| Reflect.field(ownerSave, 'getField') == null
			|| Reflect.field(ownerSave, 'setField') == null)
			throw '[nightmare-vision-options] Missing owner-scoped save data';
		var saveOwner:Dynamic = Reflect.field(ownerSave, 'ownerKey');
		if (saveOwner != null && normalizeOwner(Std.string(saveOwner)) != this.ownerRoot)
			throw '[nightmare-vision-options] Save data belongs to a different imported owner';
		this.ownerSave = ownerSave;
	}

	/** Mirrors ModOptions.add's default sentinel, duplicate behavior, and option
	 * ordering, while persisting only JSON-safe fields in this owner's save. */
	public function add(key:String, type:String = 'string', defaultValue:Dynamic = 'null', ?settings:Dynamic):Void {
		ensureAlive();
		if (key == null) return;
		var options = loadOptions();
		if (options.exists(key)) return;
		if (type == null || type == '') type = 'string';
		var normalizedType = type.toLowerCase();
		if (defaultValue == 'null') {
			switch (normalizedType) {
				case 'bool': defaultValue = false;
				case 'int' | 'float': defaultValue = 0;
				case 'string': defaultValue = '';
				default:
					trace('[nightmare-vision-options] Unable to create option [' + key + ']: invalid type ' + type);
					return;
			}
		}
		var nextIndex = 0;
		for (existingKey in options.keys()) {
			var existing:Dynamic = options.get(existingKey);
			var index:Dynamic = existing == null ? null : Reflect.field(existing, 'idx');
			if (Std.isOfType(index, Int) && (cast index:Int) >= nextIndex) nextIndex = (cast index:Int) + 1;
		}
		options.set(key, {
			type:normalizedType,
			value:defaultValue,
			idx:nextIndex,
			settings:safeSettings(settings)
		});
		writeOptions(options);
	}

	/** Source getValue returns null for an unregistered or invalid option. */
	public function getValue(key:String):Dynamic {
		ensureAlive();
		if (key == null) return null;
		var option:Dynamic = loadOptions().get(key);
		if (option == null || Reflect.field(option, 'type') == 'null') return null;
		return Reflect.field(option, 'value');
	}

	function loadOptions():StringMap<Dynamic> {
		var stored = callSave('getField', [SAVE_FIELD]);
		if (stored == null) return new StringMap<Dynamic>();
		if (Std.isOfType(stored, StringMap)) return cast stored;
		// Accept an object record written by a previous checkpoint and normalize
		// it into the owner-save StringMap codec used for new writes.
		if (Type.typeof(stored) == TObject) {
			var result = new StringMap<Dynamic>();
			for (key in Reflect.fields(stored)) result.set(key, Reflect.field(stored, key));
			return result;
		}
		throw '[nightmare-vision-options] Malformed owner option data';
	}

	function writeOptions(options:StringMap<Dynamic>):Void {
		callSave('setField', [SAVE_FIELD, options]);
		var flush:Dynamic = Reflect.field(ownerSave, 'flush');
		if (flush != null) Reflect.callMethod(ownerSave, flush, []);
	}

	function callSave(methodName:String, args:Array<Dynamic>):Dynamic {
		var method:Dynamic = ownerSave == null ? null : Reflect.field(ownerSave, methodName);
		if (method == null) throw '[nightmare-vision-options] Owner save has no ' + methodName + ' method';
		return Reflect.callMethod(ownerSave, method, args);
	}

	static function safeSettings(settings:Dynamic):Dynamic {
		if (settings == null) return null;
		var output:Dynamic = {};
		// The donor stores callbacks alongside display metadata in ModOptions.
		// Callbacks are live HScript functions and cannot safely be serialized;
		// retain the UI/value metadata while keeping this save JSON-compatible.
		for (name in ['description', 'options', 'displayFormat', 'stepSize', 'minValue', 'maxValue', 'decimals']) {
			if (!Reflect.hasField(settings, name)) continue;
			var value = Reflect.field(settings, name);
			if (isSerializable(value)) Reflect.setField(output, name, value);
		}
		return output;
	}

	static function isSerializable(value:Dynamic):Bool {
		if (value == null || Std.isOfType(value, String) || Std.isOfType(value, Bool)
			|| Std.isOfType(value, Int) || Std.isOfType(value, Float)) return true;
		if (Std.isOfType(value, Array)) {
			for (item in (cast value:Array<Dynamic>)) if (!isSerializable(item)) return false;
			return true;
		}
		return Type.typeof(value) == TObject;
	}

	function ensureAlive():Void {
		if (released || ownerSave == null) throw '[nightmare-vision-options] This owner options view has been released';
	}

	function release():Void {
		released = true;
	}

	static function normalizeOwner(value:String):String {
		if (value == null) return '';
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		if (!StringTools.startsWith(clean, 'assets/imported_mods/') || clean.indexOf('/../') >= 0
			|| StringTools.endsWith(clean, '/..') || clean.indexOf(':') >= 0 || clean.indexOf('\x00') >= 0) return '';
		return clean;
	}
}
