package;

typedef NoteData = {
	var note:String;
	var splashes:Array<String>;
	var idle:String;
	var pressed:String;
	var confirm:String;
	@:optional var confirmHold:String;
	var sing:String;
}

class NoteKeys {
	public var preset:Dynamic;
	public var definitions:Dynamic;
	public var key:Dynamic;
	public var keyAmount:Int = 4;
	public var notes(get, default):Array<NoteData>;
	// Notes are built one sprite at a time, but the selected preset usually comes
	// from the same small set of UI packs. Keep the parsed source template around
	// for the current song and clone it into each NoteKeys instance so scripts can
	// still mutate one instance without changing another.
	static inline var PRESET_CACHE_LIMIT:Int = 32;
	static var presetTemplates:Map<String, Dynamic> = new Map<String, Dynamic>();
	static var presetTemplateOrder:Array<String> = [];
	static var presetPathExists:Map<String, Bool> = new Map<String, Bool>();
	static var presetPathOrder:Array<String> = [];

	public function new(noteType:String, isPixel:Bool = false) {
		newKey(noteType, isPixel);
	}

	/**
	 * Forget parsed and missing preset paths when a song or import changes the
	 * asset view. Missing paths are only cached until this lifecycle boundary, so
	 * a newly imported preset is visible immediately after the importer handoff.
	 */
	public static function clearPresetCache():Void {
		presetTemplates = new Map<String, Dynamic>();
		presetTemplateOrder = [];
		presetPathExists = new Map<String, Bool>();
		presetPathOrder = [];
	}

	static function touchOrder(order:Array<String>, path:String):Void {
		order.remove(path);
		order.push(path);
	}

	static function touchPresetTemplate(path:String):Void {
		presetTemplateOrder.remove(path);
		presetTemplateOrder.push(path);
		while (presetTemplateOrder.length > PRESET_CACHE_LIMIT)
			presetTemplates.remove(presetTemplateOrder.shift());
	}

	static function hasPresetPath(path:String):Bool {
		if (presetPathExists.exists(path)) {
			touchOrder(presetPathOrder, path);
			return presetPathExists.get(path);
		}

		var exists = FNFAssets.exists(path);
		presetPathExists.set(path, exists);
		touchOrder(presetPathOrder, path);
		while (presetPathOrder.length > PRESET_CACHE_LIMIT)
			presetPathExists.remove(presetPathOrder.shift());
		return exists;
	}

	static function presetTemplate(path:String, required:Bool = false):Dynamic {
		if (presetTemplates.exists(path)) {
			touchPresetTemplate(path);
			return presetTemplates.get(path);
		}

		if (!hasPresetPath(path)) {
			if (!required)
				return null;
			// Keep the historical missing-default error visible to callers.
			return CoolUtil.parseJson(FNFAssets.getText(path));
		}

		var loaded:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
		if (loaded != null) {
			presetTemplates.set(path, loaded);
			touchPresetTemplate(path);
		}
		return loaded;
	}

	static function clonePresetValue(value:Dynamic):Dynamic {
		if (value == null)
			return null;
		if (Std.isOfType(value, Array)) {
			var result:Array<Dynamic> = [];
			for (item in (cast value:Array<Dynamic>))
				result.push(clonePresetValue(item));
			return result;
		}
		if (Type.typeof(value) == TObject) {
			var result:Dynamic = {};
			for (field in Reflect.fields(value))
				Reflect.setField(result, field, clonePresetValue(Reflect.field(value, field)));
			return result;
		}
		return value;
	}

	public function newKey(noteType:String, isPixel:Bool = false) {
		var presetPath:String = 'assets/images/custom_ui/ui_packs/' + noteType + '/multiNotePresets';
		if (isPixel && hasPresetPath(presetPath + '-pixel.json'))
			presetPath += '-pixel';
	
		presetPath += '.json';

		keyAmount = Note.NOTE_AMOUNT;
		var loadedPreset = presetTemplate(presetPath);
		if (loadedPreset == null || !Reflect.hasField(loadedPreset, 'key${keyAmount}'))
			preset = clonePresetValue(presetTemplate('assets/data/defaultNotePresets.json', true));
		else
			preset = clonePresetValue(loadedPreset);

		key = Reflect.field(preset, 'key${keyAmount}');

		if (Reflect.hasField(preset, 'definitions'))
			definitions = Reflect.field(preset, 'definitions');
		else
			definitions = null;

		storeNotes();
	}

	public function changeKeyAmount(amount:Int = 4):Void {
		keyAmount = amount;
		key = Reflect.field(preset, 'key${amount}');
		storeNotes();
	}

	public function storeNotes():Void {
		notes = [];
		for (i in 0...keyAmount)
			notes[i] = getDataFromID(i);
	}

	public function getDataFromID(noteID:Int):NoteData {
		var note:Dynamic = key[noteID];
		var data:Null<NoteData> = null;
		if ((note is String)) {
			if (definitions != null)
				data = Reflect.field(definitions, note);
		} else if (note != null)
			data = note;

		if (data == null)
			data = {note: 'arrowDOWN', splashes: ['note impact 1 red'], idle: 'blue', pressed: 'arrowDOWN', confirm: 'arrowDOWN', sing: 'idle'};
		return data;
	}

	public function getData(noteID:Int):NoteData {
		return notes[noteID];
	}

	public function getNote(noteID:Int):String {
		return notes[noteID].note;
	}

	public function getSing(noteID:Int):String {
		return notes[noteID].sing;
	}

	public function getSplashes(noteID:Int):Array<String> {
		return notes[noteID].splashes;
	}

	function get_notes() {
		if (notes == null)
			storeNotes();
		return notes;
	}
}
