package;

/** Display only. Canonical song/chart/audio identities remain untouched. */
class FreeplaySongTitle {
	public static function display(name:String):String {
		if (name == null) return '';
		var words = StringTools.replace(name, '-', ' ').split(' ');
		return [for (word in words) word.length == 0 ? word : word.substr(0, 1).toUpperCase() + word.substr(1)].join(' ');
	}
}
