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

	/**
		Which stems the source engine would load once a character names its own
		vocal file. Psych looks for Voices-<vocals_file> instead of Voices-Player
		(and likewise for the opponent), and never loads a stem neither side asks
		for. Nothing is dropped unless at least one character's own file is among
		the stems, so packs that name stems freely and characters without the
		field keep every stem. A stem whose format already gave it a side
		(`roles`, as V-Slice lists each side's files) and whose id is not one of
		the side names is always kept: that format never asked for Psych's rule.
	*/
	public static function keepStems(stemIds:Array<Dynamic>, ?playerSuffix:String, ?opponentSuffix:String,
		?roles:Array<Dynamic>):Array<Bool> {
		var player = clean(playerSuffix);
		var opponent = clean(opponentSuffix);
		var keep = [for (_ in stemIds) true];
		var playerShipped = false;
		var opponentShipped = false;
		for (stemId in stemIds) {
			var id = clean(stemId);
			if (id == '')
				continue;
			if (id == player)
				playerShipped = true;
			if (id == opponent)
				opponentShipped = true;
		}
		if (!playerShipped && !opponentShipped)
			return keep;
		for (index in 0...stemIds.length) {
			var id = clean(stemIds[index]);
			var role = roles == null || index >= roles.length ? '' : clean(roles[index]);
			if (role != '' && role != 'shared' && !namesSide(id))
				continue;
			var forPlayer = playerShipped ? id == player : id == 'player';
			var forOpponent = opponentShipped ? id == opponent : (id == 'opp' || id == 'opponent');
			keep[index] = forPlayer || forOpponent;
		}
		return keep;
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
