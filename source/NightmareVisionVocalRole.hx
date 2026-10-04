package;

/** Resolve the two conventional Nightmare Vision split-vocal stem IDs. */
class NightmareVisionVocalRole {
	public static function resolve(stemId:Dynamic, authoredRole:Dynamic):String {
		var role = authoredRole == null ? '' : StringTools.trim(Std.string(authoredRole)).toLowerCase();
		var id = stemId == null ? '' : StringTools.trim(Std.string(stemId)).toLowerCase();
		if (role != '' && role != 'shared')
			return role;
		return switch (id) {
			case 'player': 'player';
			case 'opp' | 'opponent': 'opponent';
			default: role == '' ? 'player' : role;
		};
	}
}
