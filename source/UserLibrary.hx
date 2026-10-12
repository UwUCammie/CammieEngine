package;

import flixel.util.FlxSave;

/** A separate application save, independent of imported scripts and score slots. */
class UserLibrary {
	static var storage:FlxSave;
	static var current:UserLibraryData;
	static var writable:Bool = false;
	public static var error(default, null):String = '';

	public static function data():UserLibraryData {
		if (current != null) return current;
		current = new UserLibraryData();
		writable = false;
		error = '';
		try {
			storage = new FlxSave();
			var name = RuntimeSmokeHarness.enabled() ? 'CammieEngineLibrarySmoke' : 'CammieEngineLibrary';
			if (!storage.bind(name, 'CammieEngine')) throw 'Library save could not be opened.';
			var raw:Dynamic = Reflect.field(storage.data, 'library');
			if (raw != null && !Std.isOfType(raw, String)) throw 'Invalid library save.';
			current = UserLibraryData.decode(raw);
			writable = true;
		} catch (failure:Dynamic) error = Std.string(failure);
		return current;
	}

	/** Publish changes only after storage accepts them. Preserve unreadable saves. */
	public static function change(edit:UserLibraryData->Void):Bool {
		data();
		if (!writable) return false;
		var previous:Dynamic = Reflect.field(storage.data, 'library');
		try {
			var next = UserLibraryData.decode(current.encode());
			edit(next);
			Reflect.setField(storage.data, 'library', next.encode());
			if (!storage.flush()) throw 'Library save failed. Your previous selection was kept.';
			current = next;
			error = '';
			return true;
		} catch (failure:Dynamic) {
			Reflect.setField(storage.data, 'library', previous);
			error = Std.string(failure);
			return false;
		}
	}
}
