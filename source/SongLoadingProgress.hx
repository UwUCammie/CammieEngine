package;

/** Lifecycle handoff and completed synchronous work, independent of elapsed time. */
class SongLoadingProgress {
	public static inline var TOTAL:Int = 4;
	public var completed(default, null):Int = 0;
	public var label(default, null):String = 'Preparing your track';
	public var detail(default, null):String = '';
	public var phase(default, null):String = 'scene';
	public function describe(name:String, text:String, information:String):Void {
		phase = name; label = text; detail = information;
	}
	/** These are chart rows already parsed, not an asset-completion estimate. */
	public static function chartDetail(chart:Dynamic):String {
		if (chart == null) return '';
		var sections:Array<Dynamic> = chart.notes;
		var rows = 0;
		if (sections != null) for (section in sections) {
			var notes:Array<Dynamic> = section.sectionNotes;
			if (notes != null) rows += notes.length;
		}
		var stage = chart.stage == null || chart.stage == '' ? 'chart default' : Std.string(chart.stage);
		var actors:Array<String> = [];
		for (key in ['player1', 'player2', 'gf']) {
			var value:Dynamic = Reflect.field(chart, key);
			if (value != null && value != '' && actors.indexOf(Std.string(value)) < 0) actors.push(Std.string(value));
		}
		return 'Chart read: ' + (sections == null ? 0 : sections.length) + ' sections, ' + rows + ' rows' + (chart.events == null ? '' : ', ' + (cast chart.events:Array<Dynamic>).length + ' event groups') + '\n'
			+ 'Stage: ' + (stage.length > 36 ? stage.substr(0, 33) + '...' : stage) + '\nCharacters: ' + [for (actor in actors) actor.length > 18 ? actor.substr(0, 15) + '...' : actor].join(', ') + '\n'
			+ (chart.needsVoices == true ? 'Music: instrumental and vocals' : 'Music: instrumental');
	}
	public var workCompleted(default, null):Float = 0;
	public var workTotal(default, null):Float = 0;
	var workStart:Float = 0;
	var workEnd:Float = 0;
	var shown:Float = 0;
	public function new() {}
	/** Planned operations are counted before work starts. Resources discovered
	 * while executing enroll and complete together, leaving pending operations
	 * in the denominator. Their completion can only advance the fraction. */
	public function beginWork(name:String, total:Float, start:Float, end:Float):Void {
		phase = name; workCompleted = 0; workTotal = Math.max(1, total);
		workStart = Math.max(shown, start); workEnd = Math.max(workStart, end);
		shown = workStart;
	}
	public function worked(units:Float = 1, discovered:Bool = false):Void {
		if (units <= 0 || workTotal <= 0) return;
		if (discovered) workTotal += units;
		workCompleted = Math.min(workTotal, workCompleted + units);
		shown = Math.max(shown, workStart + (workEnd - workStart) * workCompleted / workTotal);
	}
	public static function chartRows(chart:Dynamic):Int {
		if (chart == null || chart.notes == null) return 0;
		var rows = 0;
		for (section in (cast chart.notes:Array<Dynamic>))
			if (section.sectionNotes != null) rows += (cast section.sectionNotes:Array<Dynamic>).length;
		return rows;
	}
	public function finish(stage:Int, text:String):Void {
		if (stage <= completed || stage > TOTAL) return;
		completed = stage;
		label = text;
		if (stage == TOTAL) shown = 1;
	}
	public function fraction():Float return shown;
}
