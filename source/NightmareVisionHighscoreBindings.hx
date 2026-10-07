package;

/** The source static class API delegates to a single captured score service. */
class NightmareVisionHighscoreBindings {
	public static function install(interp:NightmareVisionScriptInterp,
		scores:NightmareVisionHighscore, requireActive:Void->Void):Void {
		var type = NightmareVisionHighscore;
		var scope = interp.sourceClassScope();
		interp.variables.set('Highscore', type);
		interp.bindImport('funkin.data.Highscore', type);
		scope.bindRuntimeClass('funkin.data.Highscore', type);
		for (name in ['weekScores','songScores','songRating']) {
			var field = name;
			scope.bindStaticField(type, field,
				function() {requireActive(); return Reflect.getProperty(scores, field);},
				function(value) {requireActive(); Reflect.setProperty(scores, field, value); return value;});
		}
		for (name in ['resetSong','resetWeek','saveScore','saveWeekScore','setScore',
			'setWeekScore','setRating','formatSong','getScore','getRating','getWeekScore','load']) {
			var field = name;
			scope.bindStaticField(type, field, function() {
				requireActive(); return Reflect.field(scores, field);
			});
		}
	}
}
