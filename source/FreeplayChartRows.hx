package;

typedef FreeplayChartRow = {
	var key:String;
	var song:Int;
	var difficulty:Int;
	var sort:LibrarySort.LibrarySortRow;
}

/** Lightweight presentation identities, without duplicating the song registry. */
class FreeplayChartRows {
	public static function expand(rows:Array<LibrarySort.LibrarySortRow>, supported:Int->Array<Int>,
		metric:(Int, Int)->Null<LibraryChartMetric.LibraryMetricValue>, ?difficultyName:Int->String):Array<FreeplayChartRow> {
		var result:Array<FreeplayChartRow> = [];
		for (row in rows) {
			var difficulties = row.random ? [] : supported(row.index);
			if (difficulties == null || difficulties.length == 0) difficulties = [-1];
			var seen:Map<Int, Bool> = [];
			for (difficulty in difficulties) if (!seen.exists(difficulty)) {
				seen.set(difficulty, true);
				var copy:LibrarySort.LibrarySortRow = cast Reflect.copy(row);
				copy.index = result.length;
				copy.id = row.id + ':' + (difficultyName == null || difficulty < 0 ? Std.string(difficulty) : difficultyName(difficulty).toLowerCase());
				copy.metric = difficulty < 0 ? null : metric(row.index, difficulty);
				result.push({key:copy.id, song:row.index, difficulty:difficulty, sort:copy});
			}
		}
		return result;
	}
	/** Separate presentation identities retain their canonical song/difficulty indexes. */
	public static function withFavorites(rows:Array<FreeplayChartRow>, order:Array<Int>, duplicate:Bool):Array<Int> {
		var pinned:Array<Int> = []; var ready:Array<Int> = []; var pending:Array<Int> = [];
		for (id in order) {
			var row = rows[id];
			if (row.sort.unavailable == true) { pending.push(id); continue; }
			if (row.sort.favorite && duplicate) {
				var copy:LibrarySort.LibrarySortRow = cast Reflect.copy(row.sort);
				copy.index = rows.length;
				var key = '@favorite:' + row.key;
				rows.push({key:key, song:row.song, difficulty:row.difficulty, sort:copy});
				pinned.push(copy.index);
			}
			ready.push(id);
		}
		return pinned.concat(ready).concat(pending);
	}
	public static function find(rows:Array<FreeplayChartRow>, visible:Array<Int>, song:Int, difficulty:Int):Int {
		for (id in visible) if (rows[id].song == song && rows[id].difficulty == difficulty) return id;
		for (id in visible) if (rows[id].song == song) return id;
		return -1;
	}
}
