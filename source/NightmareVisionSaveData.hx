package;

import haxe.ds.StringMap;
import haxe.ds.ObjectMap;
import haxe.io.Path;

using StringTools;

private typedef NightmareVisionSaveSession = {
	var ownerKey:String;
	var values:Map<String, Dynamic>;
	var loaded:Map<String, Bool>;
	var references:Int;
	var dirty:Bool;
}

/** Script-facing data fields backed by one imported owner's save view.
	Mutable arrays/maps stay live until flush, then are encoded into JSON-safe
	values. Persistence backends remain in the host-side session registry rather
	than the reflected session object. */
class NightmareVisionSaveData {
	static inline var ROOT_PREFIX:String = 'assets/imported_mods/';
	static inline var MAP_MARKER:String = '__nightmareVisionOwnerStringMap__';
	static var sessions:Map<String, NightmareVisionSaveSession> = new Map();
	/** Persistence backends stay off script-reflectable session instances. */
	static var sessionStorage:ObjectMap<NightmareVisionSaveSession, Dynamic> = new ObjectMap();

	public final ownerKey:String;
	final session:NightmareVisionSaveSession;
	var released:Bool = false;

	public function new(ownerRoot:String, storage:Dynamic) {
		ownerKey = canonicalOwnerKey(ownerRoot);
		if (ownerKey == '' || storage == null)
			throw '[nightmare-vision-save] An imported owner and private save storage are required';
		var existing = sessions.get(ownerKey);
		if (existing == null) {
			existing = {ownerKey:ownerKey,
				values:new Map(), loaded:new Map(), references:0, dirty:false};
			sessions.set(ownerKey, existing);
			sessionStorage.set(existing, storage);
		}
		session = existing;
		session.references++;
	}

	public function getField(name:String):Dynamic {
		ensureActive();
		if (!validField(name)) return null;
		if (!session.loaded.exists(name)) {
			var stored = storageGet(name);
			session.values.set(name, decode(stored));
			session.loaded.set(name, true);
		}
		return session.values.get(name);
	}

	public function setField(name:String, value:Dynamic):Dynamic {
		ensureActive();
		if (!validField(name)) throw '[nightmare-vision-save] Refused an invalid owner save field';
		session.values.set(name, value);
		session.loaded.set(name, true);
		session.dirty = true;
		return value;
	}

	/** Save all loaded fields, including in-place mutations made through an
	 * Array or StringMap returned by getField(). */
	public function flush():Void {
		ensureActive();
		for (name in session.loaded.keys())
			storageSet(name, encode(session.values.get(name)));
		storageFlush();
		session.dirty = false;
	}

	public function release():Void {
		if (released) return;
		var flushError:Dynamic = null;
		try flush() catch (error:Dynamic) flushError = error;
		released = true;
		session.references--;
		if (session.references <= 0) {
			session.references = 0;
			// Keep a failed in-memory session available for a later retry instead
			// of discarding values that could not be serialized or written.
			if (flushError == null && !session.dirty) {
				sessions.remove(ownerKey);
				sessionStorage.remove(session);
				session.values.clear();
				session.loaded.clear();
			}
		}
		if (flushError != null) throw flushError;
	}

	static function canonicalOwnerKey(value:String):String {
		var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0) return '';
		for (part in clean.split('/')) if (part == '' || part == '..') return '';
		var normalized = Path.normalize(clean);
		#if windows
		normalized = normalized.toLowerCase();
		#end
		return normalized.startsWith(ROOT_PREFIX) && normalized.length > ROOT_PREFIX.length
			? normalized : '';
	}

	static function validField(name:String):Bool
		return name != null && name != '' && name != 'codenameImportedModData'
			&& name != '__proto__' && name != 'prototype' && name != 'constructor';

	function ensureActive():Void
		if (released) throw '[nightmare-vision-save] This script save view has been released';

	function storageGet(name:String):Dynamic {
		var storage = sessionStorage.get(session);
		var method:Dynamic = storage == null ? null : Reflect.field(storage, 'getField');
		if (method == null) throw '[nightmare-vision-save] Owner storage has no getField method';
		return Reflect.callMethod(storage, method, [name]);
	}

	function storageSet(name:String, value:Dynamic):Void {
		var storage = sessionStorage.get(session);
		var method:Dynamic = storage == null ? null : Reflect.field(storage, 'setField');
		if (method == null) throw '[nightmare-vision-save] Owner storage has no setField method';
		Reflect.callMethod(storage, method, [name, value]);
	}

	function storageFlush():Void {
		var storage = sessionStorage.get(session);
		var method:Dynamic = storage == null ? null : Reflect.field(storage, 'flush');
		if (method != null) Reflect.callMethod(storage, method, []);
	}

	static function encode(value:Dynamic):Dynamic {
		if (value == null || Std.isOfType(value, String) || Std.isOfType(value, Bool)
			|| Std.isOfType(value, Int) || Std.isOfType(value, Float)) return value;
		if (Std.isOfType(value, Array)) {
			var output:Array<Dynamic> = [];
			for (entry in (cast value:Array<Dynamic>)) output.push(encode(entry));
			return output;
		}
		if (Std.isOfType(value, StringMap)) {
			var map:StringMap<Dynamic> = cast value;
			var keys:Array<String> = [];
			for (key in map.keys()) keys.push(key);
			keys.sort(Reflect.compare);
			var entries:Array<Dynamic> = [];
			for (key in keys) entries.push([key, encode(map.get(key))]);
			return {__nightmareVisionOwnerStringMap__:true, entries:entries};
		}
		if (Type.typeof(value) == TObject) {
			var output:Dynamic = {};
			for (field in Reflect.fields(value)) Reflect.setField(output, field, encode(Reflect.field(value, field)));
			return output;
		}
		throw '[nightmare-vision-save] Unsupported owner value type: ' + Std.string(Type.typeof(value));
	}

	static function decode(value:Dynamic):Dynamic {
		if (value == null) return null;
		if (Std.isOfType(value, Array)) {
			var output:Array<Dynamic> = [];
			for (entry in (cast value:Array<Dynamic>)) output.push(decode(entry));
			return output;
		}
		if (Type.typeof(value) == TObject) {
			if (Reflect.field(value, MAP_MARKER) == true) {
				var entries:Dynamic = Reflect.field(value, 'entries');
				if (Std.isOfType(entries, Array)) {
					var map:StringMap<Dynamic> = new StringMap();
					for (entry in (cast entries:Array<Dynamic>))
						if (Std.isOfType(entry, Array) && (cast entry:Array<Dynamic>).length == 2
							&& Std.isOfType((cast entry:Array<Dynamic>)[0], String))
							map.set((cast entry:Array<Dynamic>)[0], decode((cast entry:Array<Dynamic>)[1]));
					return map;
				}
			}
			var output:Dynamic = {};
			for (field in Reflect.fields(value)) Reflect.setField(output, field, decode(Reflect.field(value, field)));
			return output;
		}
		return value;
	}
}
