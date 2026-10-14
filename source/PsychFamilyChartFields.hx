package;

/**
	Chart rules Psych Engine and its forks share, kept in one dependency-free
	place so the importer, the root scanner and the runtime chart loader all
	agree on them.

	Two things live here: how a section chart is wrapped, and which field names
	the girlfriend. Fork-only rules (lane counts, per-field skins and so on)
	stay with that fork's own chart adapter.
*/
class PsychFamilyChartFields {
	/** Set on the wrapper this class builds around a flat chart, so a caller
	 * whose source engine refuses flat charts can still tell the two apart. */
	public static inline var FLAT_MARKER:String = 'compatFlatChart';

	/**
		Return `{song: payload}` for either chart shape, or null when the
		document is not a section chart.

		Older editors save `{"song": {...}}`. The Psych 1.0 editor saves the song
		object itself, where `song` is just the title string. A wrapped document
		is handed back untouched, a flat one gets the wrapper added, so callers
		keep reading `.song` and anything written out is in the wrapped form.
	*/
	public static function envelope(parsed:Dynamic):Dynamic {
		if (!isStructure(parsed))
			return null;
		var song:Dynamic = Reflect.field(parsed, 'song');
		if (isStructure(song))
			return Std.isOfType(Reflect.field(song, 'notes'), Array) ? parsed : null;
		if (!isFlat(parsed))
			return null;
		var wrapper:Dynamic = {};
		Reflect.setField(wrapper, 'song', parsed);
		Reflect.setField(wrapper, FLAT_MARKER, true);
		return wrapper;
	}

	/** The song object of either shape, or null when there is no chart. */
	public static function payload(parsed:Dynamic):Dynamic {
		var wrapped = envelope(parsed);
		return wrapped == null ? null : Reflect.field(wrapped, 'song');
	}

	/**
		True for a chart saved without the wrapper.

		Sidecar files in a chart folder (events, dialogue, metadata) can carry a
		top-level `song` label too, so the title alone proves nothing: `notes`
		has to be a list of real sections.
	*/
	public static function isFlat(parsed:Dynamic):Bool {
		if (!isStructure(parsed))
			return false;
		var title:Dynamic = Reflect.field(parsed, 'song');
		if (title != null && !Std.isOfType(title, String))
			return false;
		var notes:Dynamic = Reflect.field(parsed, 'notes');
		if (!Std.isOfType(notes, Array))
			return false;
		var sections = 0;
		for (section in (cast notes:Array<Dynamic>)) {
			if (section == null)
				continue;
			if (!isStructure(section) || !Std.isOfType(Reflect.field(section, 'sectionNotes'), Array))
				return false;
			sections++;
		}
		// An empty section list is only believable next to a tempo.
		return sections > 0 || isNumber(Reflect.field(parsed, 'bpm'));
	}

	/** True when `envelope` had to add the wrapper itself. */
	public static function wasFlat(wrapped:Dynamic):Bool {
		return isStructure(wrapped) && Reflect.field(wrapped, FLAT_MARKER) == true;
	}

	/**
		The girlfriend a chart names, or '' when it names none.

		Native charts say `gf`, this family says `gfVersion`, and charts from
		before that field existed say `player3`. The source loaders copy player3
		into gfVersion when the newer field is missing, so the order here is the
		same. Pass legacyPlayer3 = false when the chart may come from an engine
		outside this family, where player3 can mean a third singer instead.
	*/
	public static function girlfriend(song:Dynamic, legacyPlayer3:Bool = true):String {
		if (!isStructure(song))
			return '';
		var names = legacyPlayer3 ? ['gf', 'gfVersion', 'player3'] : ['gf', 'gfVersion'];
		for (name in names) {
			var text = fieldText(song, name);
			if (text != '')
				return text;
		}
		return '';
	}

	/** Write the resolved girlfriend into the native `gf` field. Returns
	 * false when the chart names nobody, so the caller can apply its own
	 * fallback. */
	public static function normalizeGirlfriend(song:Dynamic):Bool {
		if (!isStructure(song))
			return false;
		if (fieldText(song, 'gf') != '')
			return true;
		var resolved = girlfriend(song);
		if (resolved == '')
			return false;
		Reflect.setField(song, 'gf', resolved);
		return true;
	}

	/** Defaults both source loaders give a chart that leaves these out. */
	public static function fillSharedDefaults(song:Dynamic):Void {
		if (!isStructure(song))
			return;
		if (Reflect.field(song, 'needsVoices') == null)
			Reflect.setField(song, 'needsVoices', true);
		if (Reflect.field(song, 'speed') == null)
			Reflect.setField(song, 'speed', 1);
	}

	static function fieldText(song:Dynamic, name:String):String {
		var value:Dynamic = Reflect.field(song, name);
		if (value == null)
			return '';
		var text = StringTools.trim(Std.string(value));
		return text.toLowerCase() == 'null' ? '' : text;
	}

	static function isStructure(value:Dynamic):Bool {
		return value != null && Reflect.isObject(value) && !Std.isOfType(value, String)
			&& !Std.isOfType(value, Array);
	}

	static function isNumber(value:Dynamic):Bool {
		return Std.isOfType(value, Float) && !Math.isNaN(cast value);
	}
}
