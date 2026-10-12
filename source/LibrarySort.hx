package;

typedef LibrarySortRow = {
	var index:Int;
	var id:String;
	var title:String;
	var owner:String;
	var modTitle:String;
	var engine:String;
	var ordinal:Int;
	var ?authored:Int;
	var favorite:Bool;
	var random:Bool;
	var ?played:Float;
	var ?imported:Float;
	var ?metric:LibraryChartMetric.LibraryMetricValue;
}

/** Presentation only: original indexes remain authoritative for launch and readiness. */
class LibrarySort {
	public static function label(value:String):String return switch (value) {
		case 'npsHigh': 'Difficulty Rating: high-low'; case 'npsLow': 'Difficulty Rating: low-high';
		case 'flat': 'Flat list'; case 'mod': 'By mod'; case 'engine': 'Engine type';
		case 'az': 'Alphabetical A-Z'; case 'za': 'Alphabetical Z-A';
		case 'scoreHigh': 'Best score high-low'; case 'scoreLow': 'Best score low-high';
		case 'ratingLow': 'Rating: scale, then low-high'; case 'ratingHigh': 'Rating: scale, then high-low';
		case 'imported': 'Recently imported'; case 'recent': 'Recently played'; case 'favorites': 'Favorites first'; default: 'Default / authored order';
	};
	public static function group(row:LibrarySortRow, grouping:String):String {
		if (row.random) return '@random';
		return switch (grouping) {
			case 'mod': row.owner;
			case 'engine': row.engine;
			default: '';
		}
	}
	static function name(a:String, b:String, reverse:Bool = false):Int {
		// Missing metadata stays last in both directions.
		if (a == null || a == '') return b == null || b == '' ? 0 : 1;
		if (b == null || b == '') return -1;
		var order = Reflect.compare(a.toLowerCase(), b.toLowerCase());
		return reverse ? -order : order;
	}
	public static function order(rows:Array<LibrarySortRow>, grouping:String, groups:String, charts:String, pinFavorites:Bool = false):Array<Int> {
		var heads:Map<String, LibrarySortRow> = new Map();
		var imports:Map<String, Float> = new Map();
		for (row in rows) {
			var key = group(row, grouping); var old = heads.get(key);
			var rank = validPlay(row.imported);
			if (!imports.exists(key) || imports.get(key) < rank) imports.set(key, rank);
			if (old == null || row.ordinal < old.ordinal || (row.ordinal == old.ordinal && row.id < old.id)) heads.set(key, row);
		}
		// Reassign only each owner's existing presentation slots. Comparing a local
		// rank against another owner's registry ordinal would be non-transitive.
		var authoredSlots:Map<Int, Int> = [];
		if (charts == 'default') {
			var owners:Map<String, Array<LibrarySortRow>> = [];
			for (row in rows) if (!row.random && row.owner != '') {
				if (!owners.exists(row.owner)) owners.set(row.owner, []);
				owners.get(row.owner).push(row);
			}
			for (owned in owners) {
				var slots = [for (row in owned) row.ordinal];
				slots.sort(Reflect.compare);
				owned.sort(function(a,b) {
					var ar = FreeplayAuthoredOrder.rank(a.authored); var br = FreeplayAuthoredOrder.rank(b.authored);
					var order = ar == null ? (br == null ? 0 : 1) : (br == null ? -1 : Reflect.compare(ar,br));
					if (order == 0) order = Reflect.compare(a.ordinal,b.ordinal);
					return order == 0 ? Reflect.compare(a.id,b.id) : order;
				});
				for (i in 0...owned.length) authoredSlots.set(owned[i].index,slots[i]);
			}
		}
		var sorted = rows.copy();
		sorted.sort(function(a, b) {
			if (pinFavorites && a.favorite != b.favorite) return a.favorite ? -1 : 1;
			if (a.random != b.random) return a.random ? -1 : 1;
			var ag = group(a, grouping); var bg = group(b, grouping);
			var cmp = 0;
			if (grouping != 'flat' && ag != bg) {
				var ah = heads.get(ag); var bh = heads.get(bg);
				var at = grouping == 'engine' ? ah.engine : ah.modTitle;
				var bt = grouping == 'engine' ? bh.engine : bh.modTitle;
				cmp = switch (groups) {
					case 'az', 'za': name(at, bt, groups == 'za');
					case 'engine': name(ah.engine, bh.engine);
					case 'imported': Reflect.compare(imports.get(bg), imports.get(ag));
					default: Reflect.compare(ah.ordinal, bh.ordinal);
				};
				return cmp != 0 ? cmp : Reflect.compare(ag, bg);
			}
			cmp = switch (charts) {
				case 'az', 'za': name(a.title, b.title, charts == 'za');
				case 'favorites': a.favorite == b.favorite ? 0 : (a.favorite ? -1 : 1);
				case 'recent': Reflect.compare(validPlay(b.played), validPlay(a.played));
				case 'scoreHigh', 'scoreLow', 'ratingHigh', 'ratingLow', 'npsHigh', 'npsLow': LibraryChartMetric.compare(a.metric, b.metric, charts == 'scoreHigh' || charts == 'ratingHigh' || charts == 'npsHigh');
				default: Reflect.compare(authoredSlots.exists(a.index) ? authoredSlots.get(a.index) : a.ordinal,
					authoredSlots.exists(b.index) ? authoredSlots.get(b.index) : b.ordinal);
			};
			if (cmp == 0 && (charts == 'favorites' || charts == 'recent' || LibraryChartMetric.active(charts))) cmp = Reflect.compare(a.ordinal, b.ordinal);
			if (cmp == 0) cmp = Reflect.compare(a.id, b.id);
			return cmp != 0 ? cmp : a.index - b.index;
		});
		return [for (row in sorted) row.index];
	}
	static function validPlay(value:Null<Float>):Float return value != null && Math.isFinite(value) && value > 0 ? value : 0;
	public static function select(visible:Array<Int>, current:Int, change:Int):Int {
		if (visible.length == 0) return current;
		var at = visible.indexOf(current);
		if (at < 0) return change < 0 ? visible[visible.length - 1] : visible[0];
		var next = (at + change) % visible.length;
		if (next < 0) next += visible.length;
		return visible[next];
	}
}
