package;

/** Small derived sidecar only. Freeplay never parses all chart bodies to sort. */
class ChartDensityCache {
	static var cache:Map<String, Dynamic> = [];
	static var attempted:Map<String,Bool> = [];
	public static function clear():Void {cache = [];attempted = [];}
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
		// Native charts are analyzed once on demand. Imported charts are analyzed by
		// the background refresher before readiness, avoiding whole-library reads here.
		var attemptKey = key + ':' + diff;
		if (!attempted.exists(attemptKey) && ChartDifficultyAnalysis.read(Reflect.field(table,diff)) == null && !FNFAssets.exists('assets/data/' + key + '/importProvenance.json')
			&& diff.indexOf('..') < 0 && diff.indexOf('/') < 0 && diff.indexOf('\\') < 0) {
			attempted.set(attemptKey,true);
			var result:Dynamic = null;
			try {
				var path = 'assets/data/' + key + '/' + key + (diff == 'normal' ? '' : '-' + diff) + '.json';
				if (FNFAssets.exists(path)) {
					var definitions:Array<Dynamic> = [];
					var notes = 'assets/data/' + key + '/noteInfo.json';
					if (FNFAssets.exists(notes)) definitions = cast CoolUtil.parseJson(FNFAssets.getText(notes));
					// The chart's own modchart script is read, not run, for playfield movement.
					var scripts:Array<ChartMechanicScan.ChartScriptText> = [];
					var script = 'assets/data/' + key + '/modchart-' + diff + '.hscript';
					if (!FNFAssets.exists(script)) script = 'assets/data/' + key + '/modchart.hscript';
					if (FNFAssets.exists(script)) {
						var text = FNFAssets.getText(script);
						if (text.length <= ChartMechanicScan.MAX_SCRIPT_BYTES) scripts.push({text:text, lua:false});
					}
					result = ChartDifficultyAnalysis.analyze(CoolUtil.parseJson(FNFAssets.getText(path)), definitions, false,
						{modchart:ChartMechanicScan.modchart(scripts)});
				}
			} catch (_:Dynamic) {}
			Reflect.setField(table, diff, result);
		}
		return ChartDifficultyAnalysis.read(Reflect.field(table, diff));
	}
}
