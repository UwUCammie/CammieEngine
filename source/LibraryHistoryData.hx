package;

/** Shared chronology validation/serialization; package batches intentionally share one ordinal. */
class LibraryHistoryData {
	public var sequence(default, null):Float = 0;
	var values:Map<String, {at:Float, sequence:Float}> = [];
	var batches:Bool;
	public function new(batches:Bool) this.batches = batches;
	public function time(key:String):Float return values.exists(key) ? values.get(key).at : 0;
	public function order(key:String):Float return values.exists(key) ? values.get(key).sequence : 0;
	public function record(keys:Array<String>, at:Float):Void {
		if (keys.length == 0) return;
		if (!Math.isFinite(at) || at <= 0 || sequence >= 9007199254740990.0) throw 'Invalid library history.';
		for (key in keys) if (key == null || StringTools.trim(key) == '') throw 'Invalid history identity.';
		sequence++;
		for (key in keys) values.set(key, {at:at, sequence:sequence});
	}
	public function entries():Array<Dynamic> {
		var keys = [for (key in values.keys()) key]; keys.sort(Reflect.compare);
		return [for (key in keys) {key:key, at:values.get(key).at, sequence:values.get(key).sequence}];
	}
	static function number(value:Dynamic):Bool return Std.isOfType(value, Float) && Math.isFinite(value);
	public function restore(serial:Dynamic, entries:Dynamic):Void {
		if (!number(serial) || serial < 0 || serial > 9007199254740990.0 || Math.ffloor(serial) != serial
			|| !Std.isOfType(entries, Array)) throw 'Invalid library history sequence.';
		var restored:Map<String, {at:Float, sequence:Float}> = [];
		var used:Map<String, Float> = [];
		for (entry in (cast entries:Array<Dynamic>)) {
			if (entry == null) throw 'Invalid library history.';
			var key:Dynamic = entry.key; var at:Dynamic = entry.at; var ordinal:Dynamic = entry.sequence;
			if (!Std.isOfType(key, String) || StringTools.trim(cast key) == '' || restored.exists(key)
				|| !number(at) || at <= 0 || !number(ordinal) || ordinal <= 0 || ordinal > serial
				|| Math.ffloor(ordinal) != ordinal) throw 'Invalid library history.';
			if (batches && UserLibraryData.ownerKey(key) != key) throw 'Invalid imported history owner.';
			var sequenceKey = Std.string(ordinal);
			if (used.exists(sequenceKey) && (!batches || used.get(sequenceKey) != at)) throw 'Invalid history batch.';
			used.set(sequenceKey, at); restored.set(key, {at:at, sequence:ordinal});
		}
		sequence = serial; values = restored;
	}
}
