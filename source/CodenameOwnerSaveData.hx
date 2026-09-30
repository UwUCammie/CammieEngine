package;

using StringTools;

/** A script-facing view onto one Codename import's private save record.
	The backend stores only JSON data below one engine-owned root key; it never
	returns FlxSave.data itself, so a script cannot replace native settings or
	read another import's preferences. */
class CodenameOwnerSaveData {
	static inline var ROOT_FIELD:String = 'codenameImportedModData';
	static inline var ROOT_PREFIX:String = 'assets/imported_mods/';

	final ownerKey:String;
	final storage:Dynamic;

	public function new(ownerRoot:String, ?storage:Dynamic) {
		ownerKey = CompatScriptManifest.destinationKey(ownerRoot);
		if (!isImportedOwnerRoot(ownerKey))
			throw '[codename-save] Refused a save view without an imported owner root';
		this.storage = storage == null ? CodenameOwnerSaveStorage.create() : storage;
	}

	public static function isImportedOwnerRoot(root:String):Bool {
		var key = CompatScriptManifest.destinationKey(root);
		return key != '' && key.startsWith(ROOT_PREFIX);
	}

	public function getField(name:String):Dynamic {
		if (!validField(name)) return null;
		var reader:Dynamic = Reflect.field(storage, 'read');
		return reader == null ? null : Reflect.callMethod(storage, reader, [ownerKey, name]);
	}

	public function setField(name:String, value:Dynamic):Dynamic {
		if (!validField(name))
			throw '[codename-save] Refused an invalid owner save field';
		var writer:Dynamic = Reflect.field(storage, 'write');
		if (writer == null) throw '[codename-save] Owner save storage is unavailable';
		Reflect.callMethod(storage, writer, [ownerKey, name, value]);
		return value;
	}

	public function flush():Void {
		var flushStorage:Dynamic = Reflect.field(storage, 'flush');
		if (flushStorage != null) Reflect.callMethod(storage, flushStorage, []);
	}

	function validField(name:String):Bool
		return name != null && name != '' && name != ROOT_FIELD
			&& name != '__proto__' && name != 'prototype' && name != 'constructor';
}
