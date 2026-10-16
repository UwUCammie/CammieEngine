package;

/** A source engine's character id is the file name of its character JSON, so
 * it may hold spaces, dots and brackets (Psych's own "bf fnia" style names).
 * Only what could leave the character folder or is not a file name is refused. */
class SourceCharacterId {
	/** True when the id is a single, already-trimmed file name segment. */
	public static function isFileName(id:String):Bool {
		if (id == null || id == '' || id != StringTools.trim(id) || id.indexOf('..') >= 0)
			return false;
		for (index in 0...id.length) {
			var code = StringTools.fastCodeAt(id, index);
			// Path separators, drive and wildcard characters, quotes, pipes and control codes.
			if (code < 32 || code == 47 || code == 92 || code == 58 || code == 42 || code == 63
				|| code == 34 || code == 60 || code == 62 || code == 124)
				return false;
		}
		return true;
	}

	/** The root whose character folders hold the id's JSON, searched in the
	 * order given (the selected owner first). When none holds it, the first
	 * root stays the scope, as it was before dependency roots were searched. */
	public static function ownerRoot(id:String, roots:Array<String>, exists:String->Bool):String {
		if (roots == null || roots.length == 0)
			return '';
		var name = id == null ? '' : StringTools.trim(id);
		if (exists != null && isFileName(name))
			for (root in roots)
				if (root != null && root != '')
					for (folder in ['characters', 'shared/characters'])
						if (exists(root + '/' + folder + '/' + name + '.json'))
							return root;
		return roots[0] == null ? '' : roots[0];
	}
}
