package;

typedef FreeplaySongEntry = {
	var song:Dynamic;
	var base:Bool;
	var order:Int;
}

/** Presentation order for the generated All category. Its registry order is
 * left alone, including any order chosen by the user in other categories. */
class FreeplaySongOrder {
	static function ownerQualifiedBase(name:String):String {
		if (name == null)
			return '';
		var split = name.lastIndexOf('--');
		if (split <= 0)
			return name;
		var suffix = name.substr(split + 2);
		var digestAt = suffix.lastIndexOf('-');
		if (digestAt <= 0)
			return name;
		var digest = suffix.substr(digestAt + 1);
		if (digest.length != 10 || !~/^[0-9a-f]+$/i.match(digest))
			return name;
		return name.substr(0, split);
	}

	static function normalized(value:String):String {
		var result = '';
		if (value != null)
			for (char in value.toLowerCase().split(''))
				if ((char >= 'a' && char <= 'z') || (char >= '0' && char <= '9'))
					result += char;
		return result;
	}

	/** Older imports stored the source suffix only in their owner receipt.
	 * Read a bounded receipt when the generated All list needs their title. */
	static function legacyDisplayTitle(name:String, display:String):String {
		#if sys
		if (name == null || name == '' || name.indexOf('/') >= 0
			|| name.indexOf('\\') >= 0 || name.indexOf('..') >= 0)
			return '';
		var path = 'assets/data/' + name.toLowerCase() + '/importProvenance.json';
		try {
			if (!sys.FileSystem.exists(path) || sys.FileSystem.stat(path).size > 65536)
				return '';
			var provenance:Dynamic = haxe.Json.parse(sys.io.File.getContent(path));
			var resolved = FreeplaySourceDisplay.resolve(display, '', name, provenance);
			return resolved.source == '' ? '' : resolved.title;
		} catch (_:Dynamic) {}
		#end
		return '';
	}

	public static function titleKey(song:Dynamic):String {
		if (song == null)
			return '';
		var rawName:Dynamic = Reflect.field(song, 'name');
		var name = rawName == null ? '' : Std.string(rawName);
		var rawDisplay:Dynamic = Reflect.field(song, 'display');
		var display = rawDisplay == null ? name : Std.string(rawDisplay);
		var rawSource:Dynamic = Reflect.field(song, 'sourceLabel');
		var source = rawSource == null ? '' : StringTools.trim(Std.string(rawSource));
		if (source != '') {
			var suffix = ' · ' + source;
			if (StringTools.endsWith(display, suffix))
				display = display.substr(0, display.length - suffix.length);
			return normalized(display);
		}
		// Older imported registry rows have no separate sourceLabel. Their
		// owner receipt retains the exact label even if its title differs from
		// the donor's folder key.
		var canonical = ownerQualifiedBase(name);
		if (canonical != name) {
			var authoredTitle = legacyDisplayTitle(name, display);
			if (authoredTitle != '')
				return normalized(authoredTitle);
		}
		return normalized(canonical != name ? canonical : display);
	}

	public static function sort(entries:Array<FreeplaySongEntry>):Array<Dynamic> {
		if (entries == null)
			return [];
		var indexed = [];
		for (entry in entries)
			indexed.push({song:entry.song, base:entry.base, order:entry.order,
				key:titleKey(entry.song)});
		indexed.sort(function(a, b) {
			if (a.key < b.key) return -1;
			if (a.key > b.key) return 1;
			if (a.base != b.base) return a.base ? -1 : 1;
			return a.order - b.order;
		});
		var result:Array<Dynamic> = [];
		for (entry in indexed)
			result.push(entry.song);
		return result;
	}
}
