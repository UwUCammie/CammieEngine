package;

/** Ordering persisted through the shared library transaction. */
class LibrarySortingSubState extends LibraryMenuSubState {
	public function new() super();
	override function create():Void { super.create(); refresh(); }
	function refresh():Void {
		var order = UserLibrary.data().sorting();
		showActions('Sorting / Favorites always first', [
			{label:'Grouping: ' + LibrarySort.label(order.grouping), run:function() advance(0)},
			{label:'Group order: ' + LibrarySort.label(order.groups) + (order.grouping == 'flat' ? ' (inactive in flat list)' : ''), run:function() advance(1)},
			{label:'Chart order: ' + LibrarySort.label(order.charts), run:function() advance(2)},
			{label:'Return', run:function() close()}
		], false);
	}

	function advance(field:Int):Void {
		var order = UserLibrary.data().sorting();
		var options = field == 0 ? ['flat', 'mod', 'engine']
			: (field == 1 ? ['default', 'az', 'za', 'engine', 'imported'] : ['default', 'az', 'za', 'favorites', 'recent', 'scoreHigh', 'scoreLow', 'ratingLow', 'ratingHigh', 'npsHigh', 'npsLow']);
		var value = field == 0 ? order.grouping : (field == 1 ? order.groups : order.charts);
		var next = options[(options.indexOf(value) + 1) % options.length];
		if (field == 0) order.grouping = next; else if (field == 1) order.groups = next; else order.charts = next;
		UserLibrary.change(function(data) data.setSorting(order.grouping, order.groups, order.charts));
		refresh();
	}
}
