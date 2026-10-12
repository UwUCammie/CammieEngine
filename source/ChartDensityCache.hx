package;

/** Small derived sidecar only. Freeplay never parses all chart bodies to sort. */
class ChartDensityCache {
	static var cache:Map<String, Dynamic> = [];
	public static function clear():Void cache = [];
	public static function read(song:String, difficulty:String):Null<ChartDifficultyAnalysis.ChartDensity> {
		if (song == null || song == '' || song.indexOf('..') >= 0 || song.indexOf('/') >= 0 || song.indexOf('\\') >= 0) return null;
		var key = song.toLowerCase();
		if (!cache.exists(key)) {
			var value:Dynamic = null;
			try {
				var path = 'assets/data/' + key + '/chartDensity.json';
				if (FNFAssets.exists(path)) {
					var text = FNFAssets.getText(path);
					if (text.length <= 1048576) value = CoolUtil.parseJson(text);
				}
			} catch (_:Dynamic) {}
			cache.set(key, value);
		}
		var table = cache.get(key);
		if (difficulty == null) return null;
		var diff = difficulty.toLowerCase();
		if (table == null) { table = {}; cache.set(key, table); }
		// Base/native charts have no retained source refresh. Analyze a named chart once on demand.
		// Imported charts await their transactional refresher instead of parsing an entire library here.
		if (!Reflect.hasField(table, diff) && !FNFAssets.exists('assets/data/' + key + '/importProvenance.json')
			&& diff.indexOf('..') < 0 && diff.indexOf('/') < 0 && diff.indexOf('\\') < 0) {
			var result:Dynamic = null;
			try {
				var path = 'assets/data/' + key + '/' + key + (diff == 'normal' ? '' : '-' + diff) + '.json';
				if (FNFAssets.exists(path)) {
					var definitions:Array<Dynamic> = [];
					var notes = 'assets/data/' + key + '/noteInfo.json';
					if (FNFAssets.exists(notes)) definitions = cast CoolUtil.parseJson(FNFAssets.getText(notes));
					result = ChartDifficultyAnalysis.analyze(CoolUtil.parseJson(FNFAssets.getText(path)), definitions);
				}
			} catch (_:Dynamic) {}
			Reflect.setField(table, diff, result);
		}
		return ChartDifficultyAnalysis.read(Reflect.field(table, diff));
	}
}
