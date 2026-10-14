package;

/**
 * Whose voice a split vocal stem is. Psych and Nightmare Vision both name the
 * two buses after the side that sings them, so one resolver serves both.
 */
class SourceVocalRole {
	/**
	 * An authored role other than 'shared' always wins. Otherwise the stem id
	 * decides: the conventional player/opponent names, or the file suffix a
	 * character asks for (`playerSuffix` / `opponentSuffix`). A stem with no
	 * role and no telling id stays with the player, as a lone track always has.
	 */
	public static function resolve(stemId:Dynamic, authoredRole:Dynamic, ?playerSuffix:String,
		?opponentSuffix:String):String {
		var role = clean(authoredRole);
		var id = clean(stemId);
		if (role != '' && role != 'shared')
			return role;
		switch (id) {
			case 'player': return 'player';
			case 'opp' | 'opponent': return 'opponent';
			default:
		}
		// player first: when both characters ask for the same file the source
		// engine loads it for the player too
		if (id != '' && id == clean(playerSuffix))
			return 'player';
		if (id != '' && id == clean(opponentSuffix))
			return 'opponent';
		return role == '' ? 'player' : role;
	}

	/** True for the ids that mean a side on their own, without character data. */
	public static function namesSide(stemId:Dynamic):Bool {
		var id = clean(stemId);
		return id == 'player' || id == 'opp' || id == 'opponent';
	}

	/**
	 * Which stem should be the song's main vocal object. Scripts and the miss
	 * path treat that one as the player's voice, so a player stem leads even
	 * when the files sort the other way round.
	 */
	public static function primaryIndex(roles:Array<String>):Int {
		if (roles != null)
			for (index in 0...roles.length)
				if (clean(roles[index]) == 'player')
					return index;
		return 0;
	}

	static function clean(value:Dynamic):String {
		return value == null ? '' : StringTools.trim(Std.string(value)).toLowerCase();
	}
}
