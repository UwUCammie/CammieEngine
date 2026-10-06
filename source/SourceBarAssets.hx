package;

/** Stock source group frames; selected-owner art always takes precedence. */
class SourceBarAssets {
	public static function coreImage(engine:String, image:String):Null<String> {
		if (engine == 'psych' && (image == 'healthBar' || image == 'timeBar'))
			return 'assets/images/source_compat/psych/' + image + '.png';
		if (engine == 'nightmare-vision') {
			var name = switch (image) {
				case 'healthBar' | 'UI/healthBar' | 'UI/core/healthBar': 'healthBar';
				case 'timeBar' | 'UI/timeBar' | 'UI/core/timeBar': 'timeBar';
				default: null;
			};
			if (name != null) return 'assets/images/source_compat/nightmare-vision/' + name + '.png';
		}
		return null;
	}
}
