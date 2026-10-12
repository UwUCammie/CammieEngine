package;

/** Independent ordering and named metric scope, persisted through the shared library transaction. */
class LibrarySortingSubState extends LibraryMenuSubState {
	public function new() super();
	override function create():Void { super.create(); refresh(); }
	function refresh():Void {
		var order = UserLibrary.data().sorting();
		showActions('Library grouping and sorting', [
			{label:'Grouping: ' + LibrarySort.label(order.grouping), run:function() advance(0)},
			{label:'Group order: ' + LibrarySort.label(order.groups) + (order.grouping == 'flat' ? ' (inactive in flat list)' : ''), run:function() advance(1)},
			{label:'Chart order: ' + LibrarySort.label(order.charts), run:function() advance(2)},
			{label:'Comparison difficulty: ' + order.difficulty + (LibraryChartMetric.active(order.charts) ? '' : ' (score/rating only)'), run:advanceDifficulty},
			{label:'Return', run:function() close()}
		], false);
	}

	function advance(field:Int):Void {
		var order = UserLibrary.data().sorting();
		var options = field == 0 ? ['flat', 'mod', 'engine']
			: (field == 1 ? ['default', 'az', 'za', 'engine', 'imported'] : ['default', 'az', 'za', 'favorites', 'recent', 'scoreHigh', 'scoreLow', 'ratingLow', 'ratingHigh']);
		var value = field == 0 ? order.grouping : (field == 1 ? order.groups : order.charts);
		var next = options[(options.indexOf(value) + 1) % options.length];
		if (field == 0) order.grouping = next; else if (field == 1) order.groups = next; else order.charts = next;
		UserLibrary.change(function(data) data.setSorting(order.grouping, order.groups, order.charts));
		refresh();
	}
	function advanceDifficulty():Void {
		var current = UserLibrary.data().sorting().difficulty;
		var names:Array<String> = [];
		for (name in DifficultyManager.getDifficultyNames()) {
			var key = StringTools.trim(name).toLowerCase();
			if (key != '' && names.indexOf(key) < 0) names.push(key);
		}
		if (names.indexOf(current) < 0) names.push(current);
		names.sort(Reflect.compare);
		var next = names[(names.indexOf(current) + 1) % names.length];
		UserLibrary.change(function(data) data.setComparisonDifficulty(next)); refresh();
	}

}
