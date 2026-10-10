package;

/** Source stage iteration and callback-time timing publication. */
class SourceStageCallbacks {
	public static function enabled(stage:Dynamic, read:Dynamic->String->Dynamic):Bool
		return stage != null && read(stage, 'exists') && read(stage, 'active');
	public static function each(stages:Array<Dynamic>, read:Dynamic->String->Dynamic, visit:Dynamic->Void):Void {
		for (stage in stages) if (enabled(stage, read)) visit(stage);
	}
	public static function publish(host:Dynamic, stage:Dynamic, callback:String,
		read:Dynamic->String->Dynamic, write:Dynamic->String->Dynamic->Void):Void {
		switch (callback) {
			case 'stepHit':
				write(stage, 'curStep', read(host, 'curStep'));
				write(stage, 'curDecStep', read(host, 'curDecStep'));
			case 'beatHit':
				write(stage, 'curBeat', read(host, 'curBeat'));
				write(stage, 'curDecBeat', read(host, 'curDecBeat'));
			case 'sectionHit': write(stage, 'curSection', read(host, 'curSection'));
			default:
		}
	}
}
