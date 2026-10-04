package;

/** Psych's score-facing script values, derived without changing native scoring. */
class PsychScoreScriptGlobals {
	public static final ratingFields = ['rating', 'ratingName', 'ratingFC'];
	/** Source setters change the presentation independently of native tallies. */
	public static function apply(snapshot:Dynamic, hitsAdjustment:Int,
		overrides:Map<String, Dynamic>, ?previous:Dynamic):Dynamic {
		snapshot.hits += hitsAdjustment;
		for (name in ratingFields) {
			if (previous != null) Reflect.setField(snapshot, name, Reflect.field(previous, name));
			if (overrides != null && overrides.exists(name))
				Reflect.setField(snapshot, name, overrides.get(name));
		}
		return snapshot;
	}
	static final thresholds = [0.2, 0.4, 0.5, 0.6, 0.69, 0.7, 0.8, 0.9, 1.0];
	static final names = ['You Suck!', 'Shit', 'Bad', 'Bruh', 'Meh', 'Nice', 'Good', 'Great', 'Sick!'];
	public static function snapshot(score:Int, misses:Int, sicks:Int, goods:Int,
		bads:Int, shits:Int, accuracy:Float):Dynamic {
		var hits = sicks + goods + bads + shits;
		var rating = Math.isFinite(accuracy) ? Math.max(0, Math.min(1, accuracy / 100)) : 0;
		var name = '?';
		if (hits + misses > 0) {
			name = 'Perfect!!';
			for (index in 0...thresholds.length) if (rating < thresholds[index]) {
				name = names[index];
				break;
			}
		}
		var fullCombo = misses > 0 ? (misses < 10 ? 'SDCB' : 'Clear')
			: bads > 0 || shits > 0 ? 'FC' : goods > 0 ? 'GFC' : sicks > 0 ? 'SFC' : '';
		return {score:score, misses:misses, hits:hits, rating:rating, ratingName:name, ratingFC:fullCombo};
	}
}
