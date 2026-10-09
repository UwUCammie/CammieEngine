package;

/** Historical fully qualified class names share the existing owner objects. */
class NightmareVisionLegacyClassAliases {
	public static function create(playState:Dynamic, gameOver:Dynamic, conductor:Dynamic,
		prefs:Dynamic, paths:Dynamic, coolUtil:Dynamic):Map<String,Dynamic> {
		return [
			'meta.states.PlayState'=>playState,
			'meta.states.substate.GameOverSubstate'=>gameOver,
			'meta.data.Conductor'=>conductor,
			'meta.data.ClientPrefs'=>prefs,
			'meta.data.Paths'=>paths,
			'meta.data.CoolUtil'=>coolUtil
		];
	}
}
