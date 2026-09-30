package;

/** Keep the character picker tied to visuals the current installation can load.
	A registry row may survive an import while its media is absent from a clean
	release. An alias resolved through another character's atlas is not its own
	selectable character either. */
class CharacterSelectRoster {
	public static function availableNames(registry:Dynamic, resolve:String->Dynamic):Array<String> {
		var names:Array<String> = [];
		if (registry == null || resolve == null)
			return names;
		for (name in Reflect.fields(registry)) {
			if (name == null || StringTools.trim(name) == '')
				continue;
			var visual:Dynamic = null;
			try visual = resolve(name) catch (_:Dynamic) {}
			if (visual == null || Reflect.field(visual, 'complete') != true)
				continue;
			var assetName:Dynamic = Reflect.field(visual, 'assetName');
			if (assetName == null || Std.string(assetName).toLowerCase() != name.toLowerCase())
				continue;
			names.push(name);
		}
		names.sort(function(a:String, b:String):Int {
			var lowerA = a.toLowerCase();
			var lowerB = b.toLowerCase();
			if (lowerA < lowerB) return -1;
			if (lowerA > lowerB) return 1;
			return a < b ? -1 : (a > b ? 1 : 0);
		});
		return names;
	}
}
