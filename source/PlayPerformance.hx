package;

typedef PlayPerformanceRecord = {var misses:Int; var maxCombo:Int; var totalPlayerNotes:Int;}
class PlayPerformance {
	public static function read(raw:Dynamic):Null<PlayPerformanceRecord> {
		if (raw == null) return null;
		for (field in ['misses','maxCombo','totalPlayerNotes']) {
			var value:Dynamic = Reflect.field(raw, field);
			if (!Std.isOfType(value, Int) || value < 0) return null;
		}
		return {misses:raw.misses, maxCombo:raw.maxCombo, totalPlayerNotes:raw.totalPlayerNotes};
	}
	public static function label(record:Null<PlayPerformanceRecord>):String return record == null
		? 'Misses: --\nMax combo: -- / --'
		: 'Misses: ' + record.misses + '\nMax combo: ' + record.maxCombo + ' / ' + record.totalPlayerNotes;
}
