package;

import haxe.ds.StringMap;

/** Owner-local implementation of Nightmare Vision's ModOptions add/getValue
 * surface. Values use the selected import's save record instead of ModOptions'
 * process-global FlxSave namespace. */
@:keep
class NightmareVisionSourceOptions {
	public static inline var SAVE_FIELD:String = 'nightmareVisionSourceModOptions';
	public final ownerRoot:String;
	var ownerSave:Dynamic;
	var selectedOwnerRoot:String;
	var resolveDirectory:String->Null<String>;
	var saveForRoot:String->Dynamic;
	var globalDirectories:Void->Array<String>;
	public var currentMod(default, null):String = '';
	public var options:StringMap<NightmareVisionSourceModOption> = new StringMap();
	public var list(get, never):Array<NightmareVisionSourceModOption>;
	function get_list():Array<NightmareVisionSourceModOption> {
		ensureAlive();
		var result = [for (option in options) option];
		result.sort(function(a, b) return a.idx - b.idx);
		return result;
	}
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
		selectedOwnerRoot = this.ownerRoot;
		loadStoredOptions();
	}

	/** Share one live option table across scripts, with saves selected only from
	 * the provenance-authorized family. The lease root itself never changes. */
	public function bindFamily(resolveDirectory:String->Null<String>, saveForRoot:String->Dynamic,
		globalDirectories:Void->Array<String>):Void {
		ensureAlive();
		this.resolveDirectory = resolveDirectory;
		this.saveForRoot = saveForRoot;
		this.globalDirectories = globalDirectories;
	}

	public function init(modName:String = 'NMV-Base-Game'):Void {
		ensureAlive();
		var selected = resolveDirectory == null ? ownerRoot : resolveDirectory(modName);
		if (selected == null) throw '[nightmare-vision-options] Unrelated source option namespace: ' + modName;
		initForOwner(modName, selected);
	}

	public function initForOwner(modName:String, selectedRoot:String):Void {
		ensureAlive();
		var root = normalizeOwner(selectedRoot);
		if (root == '' || (root != ownerRoot && (resolveDirectory == null || resolveDirectory(modName) != root)))
			throw '[nightmare-vision-options] Unrelated source option owner';
		if (currentMod != '' && currentMod != modName) flush();
		currentMod = modName;
		options.clear();
		if (root != selectedOwnerRoot || ownerSave == null) {
			// Publish the target identity and detach the old save before binding.
			// A failed bind must never write the target table through the old owner.
			ownerSave = null;
			selectedOwnerRoot = root;
			if (saveForRoot == null) throw '[nightmare-vision-options] Missing selected owner save service';
			var nextSave = saveForRoot(root);
			validateSave(nextSave, root);
			ownerSave = nextSave;
			selectedOwnerRoot = root;
		}
		loadStoredOptions();
	}

	/** A source static assignment changes the save namespace without loading or
	 * clearing the live table. Only authenticated namespaces can be written. */
	public function assignCurrentMod(modName:String):String {
		ensureAlive();
		var root = resolveDirectory == null ? ownerRoot : resolveDirectory(modName);
		if (root == null) throw '[nightmare-vision-options] Unrelated source option namespace: ' + modName;
		if (root != selectedOwnerRoot) {
			var nextSave = saveForRoot == null ? null : saveForRoot(root);
			validateSave(nextSave, root);
			ownerSave = nextSave; selectedOwnerRoot = root;
		}
		currentMod = modName;
		return currentMod;
	}

	function loadStoredOptions():Void {
		var stored = loadOptions();
		for (key in stored.keys()) {
			var entry = stored.get(key);
			var option = new NightmareVisionSourceModOption(key, Reflect.field(entry, 'type'),
				Reflect.field(entry, 'value'), Reflect.field(entry, 'settings'));
			var idx:Dynamic = Reflect.field(entry, 'idx');
			option.idx = idx == null ? -1 : idx;
			options.set(key, option);
		}
		validateOrder();
	}

	function validateOrder():Void {
		var used:Array<Int> = [];
		var sorted = list;
		for (i in 0...sorted.length) {
			var option = sorted[i];
			if (option.idx == -1 || used.contains(option.idx)) option.idx = i;
			used.push(option.idx);
		}
	}

	/** FunkinScript's newOption supplies its own modFolder to source add. */
	public function addForMod(mod:String, key:String, type:String = 'string', defaultValue:Dynamic = 'null',
		?settings:Dynamic):Void {
		ensureAlive();
		if (currentMod != mod && (globalDirectories == null || !globalDirectories().contains(mod))) return;
		add(key, type, defaultValue, settings);
	}

	/** Mirrors ModOptions.add's default sentinel, duplicate behavior, and option
	 * ordering, while persisting only JSON-safe fields in this owner's save. */
	public function add(key:String, type:String = 'string', defaultValue:Dynamic = 'null', ?settings:Dynamic):Void {
		ensureAlive();
		if (key == null) return;
		if (options.exists(key)) return;
		if (defaultValue == 'null') {
			switch (type.toLowerCase()) {
				case 'bool': defaultValue = false;
				case 'int' | 'float': defaultValue = 0;
				case 'string': defaultValue = '';
				default: type = 'null';
			}
		}
		if (type == 'null') {
			trace('[nightmare-vision-options] Unable to create option [' + key + ']: invalid type ' + type);
			return;
		}
		var option = new NightmareVisionSourceModOption(key, type, defaultValue, settings);
		option.idx = list.length;
		options.set(key, option);
		flush();
	}

	/** Source getValue returns null for an unregistered or invalid option. */
	public function getValue(key:String):Dynamic {
		ensureAlive();
		if (key == null) return null;
		var option = get(key);
		return option == null ? null : option.value;
	}

	public function get(key:String):NightmareVisionSourceModOption {
		ensureAlive();
		var option = options.get(key);
		return option == null || option.type == 'null' ? null : option;
	}

	public function setValue(key:String, value:Dynamic):Void {
		var option = get(key);
		if (option != null) option.value = value;
	}

	public function flush():Void {
		ensureAlive();
		if (currentMod == '' && resolveDirectory != null) return;
		var expectedRoot = resolveDirectory == null ? ownerRoot : resolveDirectory(currentMod);
		if (expectedRoot == null || expectedRoot != selectedOwnerRoot)
			throw '[nightmare-vision-options] Live options do not match their save owner';
		if (ownerSave == null) {
			var nextSave = saveForRoot == null ? null : saveForRoot(expectedRoot);
			validateSave(nextSave, expectedRoot);
			ownerSave = nextSave;
		}
		var output:Dynamic = {};
		for (key => option in options) Reflect.setField(output, key, {
			type:option.type, value:option.value, idx:option.idx, settings:safeSettings(option.settings)
		});
		callSave('setField', [SAVE_FIELD, output]);
		var flush:Dynamic = Reflect.field(ownerSave, 'flush');
		if (flush != null) Reflect.callMethod(ownerSave, flush, []);
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
		if (released) throw '[nightmare-vision-options] This owner options view has been released';
	}

	public function release():Void {
		if (released) return;
		var failure:Dynamic = null;
		try flush() catch (error:Dynamic) failure = error;
		released = true;
		options.clear();
		ownerSave = null;
		resolveDirectory = null; saveForRoot = null; globalDirectories = null;
		if (failure != null) throw failure;
	}

	static function validateSave(save:Dynamic, root:String):Void {
		if (save == null || Reflect.field(save, 'getField') == null || Reflect.field(save, 'setField') == null)
			throw '[nightmare-vision-options] Missing owner-scoped save data';
		var key:Dynamic = Reflect.field(save, 'ownerKey');
		if (key != null && normalizeOwner(Std.string(key)) != root)
			throw '[nightmare-vision-options] Save data belongs to a different imported owner';
	}

	static function normalizeOwner(value:String):String {
		if (value == null) return '';
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		if (!StringTools.startsWith(clean, 'assets/imported_mods/') || clean.indexOf('/../') >= 0
			|| StringTools.endsWith(clean, '/..') || clean.indexOf(':') >= 0 || clean.indexOf('\x00') >= 0) return '';
		return clean;
	}
}
