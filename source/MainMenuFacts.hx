package;

typedef MainMenuFactRow = {
	var label:String;
	var value:String;
}

/** What the main menu says about the highlighted entry: a heading, one big
 * figure, a line under it and a few label and value rows. */
typedef MainMenuFact = {
	var heading:String;
	var big:String;
	var sub:String;
	var rows:Array<MainMenuFactRow>;
	var accent:Int;
}

/** Plain-text summaries for the main menu's context panel, built from numbers
 * the menu already has so they can be checked without any display objects. */
class MainMenuFacts {
	public static function plural(count:Int, one:String, many:String):String
		return count + ' ' + (count == 1 ? one : many);

	/** Last folder of a path, for a short source label. */
	public static function pathTail(path:String, limit:Int = 28):String {
		if (path == null) return '';
		var clean = StringTools.trim(StringTools.replace(path, '\\', '/'));
		while (clean.length > 1 && clean.charAt(clean.length - 1) == '/') clean = clean.substr(0, clean.length - 1);
		var cut = clean.lastIndexOf('/');
		var tail = cut >= 0 ? clean.substr(cut + 1) : clean;
		return tail.length <= limit ? tail : tail.substr(0, limit - 3) + '...';
	}

	/** Shorten a path in the middle so it fits `limit` characters and still
	 * ends in its last folder, shown whole whenever it can be. */
	public static function middleEllipsis(path:String, limit:Int):String {
		if (path == null) return '';
		var clean = StringTools.trim(path);
		if (clean.length <= limit) return clean;
		var cut = clean.lastIndexOf('/');
		var lastFolder = clean.substr(cut + 1);
		var keep = Std.int(Math.max(lastFolder.length + 1, Math.floor(limit * 0.5)));
		keep = Std.int(Math.min(keep, limit - 4));
		var head = limit - 3 - keep;
		if (head < 3) return '...' + clean.substr(clean.length - (limit - 3));
		return clean.substr(0, head) + '...' + clean.substr(clean.length - keep);
	}

	public static function story(weeks:Int):MainMenuFact return {
		heading: 'STORY MODE',
		big: plural(weeks, 'week', 'weeks'),
		sub: 'Play a week of songs back to back.',
		rows: [],
		accent: MenuStyle.PINK
	};

	/** `checking` is true while the saved imports are still being looked at, so the
	 * ready count is not known yet and must not be shown as zero. */
	public static function freeplay(songs:Int, modsReady:Int, modsLoading:Int, checking:Bool = false):MainMenuFact {
		var rows:Array<MainMenuFactRow> = [{label: 'Imported mods ready', value: checking ? 'Checking...' : Std.string(modsReady)}];
		if (modsLoading > 0) rows.push({label: 'Still loading', value: Std.string(modsLoading)});
		return {
			heading: 'FREEPLAY',
			big: plural(songs, 'song', 'songs'),
			sub: checking ? 'Checking which imported mods are ready.'
				: (modsReady == 0 ? 'Every song in the base game.' : 'From the base game and your imported mods.'),
			rows: rows,
			accent: MenuStyle.TEAL
		};
	}

	/** A few of the settings people change most, read from the saved options. */
	public static function options(settings:Dynamic, saveName:String):MainMenuFact {
		function flag(name:String):Bool return Reflect.field(settings, name) == true;
		var cap:Dynamic = Reflect.field(settings, 'fpsCap');
		var offset:Dynamic = Reflect.field(settings, 'offset');
		return {
			heading: 'OPTIONS',
			big: 'Your settings',
			sub: 'Sections, controls and save slots.',
			rows: [
				{label: 'Scroll direction', value: flag('downscroll') ? 'Down' : 'Up'},
				{label: 'Middlescroll', value: flag('midscroll') ? 'On' : 'Off'},
				{label: 'Ghost tapping', value: flag('useCustomInput') ? 'On' : 'Off'},
				{label: 'Frame rate', value: flag('unlimitedFPS') ? 'Unlimited' : (cap == null ? 'Default' : cap + ' FPS')},
				{label: 'Note offset', value: (offset == null ? 0 : offset) + ' ms'},
				{label: 'Save slot', value: saveName}
			],
			accent: MenuStyle.GOLD
		};
	}

	/** While `checking` the number of ready mods is unknown, so the figure says so
	 * instead of showing a count that is still being worked out. */
	public static function importer(modsReady:Int, busy:Bool, status:String, type:String, source:String, checking:Bool = false):MainMenuFact {
		var rows:Array<MainMenuFactRow> = [{label: 'Importer', value: type == null || type == '' ? 'Auto' : type}];
		var tail = pathTail(source);
		rows.push({label: 'Last source', value: tail == '' ? 'Not chosen yet' : tail});
		return {
			heading: 'IMPORT',
			big: busy ? 'Refreshing' : (checking ? 'Checking...' : plural(modsReady, 'mod ready', 'mods ready')),
			sub: (busy || checking) && status != null && status != '' ? status
				: (checking ? 'Looking at your saved imports.' : 'Add songs and mods from other engines.'),
			rows: rows,
			accent: MenuStyle.PINK
		};
	}

	public static function plain(heading:String, big:String, sub:String, accent:Int):MainMenuFact return {
		heading: heading, big: big, sub: sub, rows: [], accent: accent
	};

	/** Height of the context panel for a fact: heading, figure, line and rows. */
	public static function panelHeight(fact:MainMenuFact):Int
		return 28 + 20 + 56 + 30 + fact.rows.length * 30 + (fact.rows.length > 0 ? 12 : 0) + 14;
}
