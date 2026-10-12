package;

/** Compact display badges only; ownership always uses the complete retained root. */
class LibraryPackageLabel {
	// Identity hashes never depend on package names or availability generations.
	// Bound the cache for long-running sessions which import many distinct owners.
	static var badges:Map<String, String> = [];
	static var badgeCount:Int = 0;
	public static function badge(owner:String):String {
		var key = UserLibraryData.ownerKey(owner);
		if (key == '') return '';
		var cached = badges.get(key);
		if (cached != null) return cached;
		var result = haxe.crypto.Sha256.encode(key).substr(0, 10).toUpperCase();
		if (badgeCount >= 4096) { badges = []; badgeCount = 0; }
		badges.set(key, result); badgeCount++;
		return result;
	}

	public static function caption(owner:String, label:String):String {
		var text = label == null ? '' : StringTools.trim(label);
		var id = badge(owner);
		return id == '' ? text : '[' + id + '] ' + text;
	}

	/** A deliberate badge query may resolve identities; ordinary title search stays lazy. */
	public static function isBadgeQuery(query:String):Bool {
		if (query == null || query.length < 4 || query.length > 10) return false;
		for (i in 0...query.length) {
			var c = query.charCodeAt(i);
			if (!(c >= 48 && c <= 57 || c >= 65 && c <= 70 || c >= 97 && c <= 102)) return false;
		}
		return true;
	}

	public static function matches(owner:String, query:String):Bool {
		return isBadgeQuery(query) && badge(owner).indexOf(query.toUpperCase()) >= 0;
	}
}
