package;

using StringTools;

/**
	Engine-neutral adapter for the fourth value in legacy/Psych sectionNotes
	rows.  Psych calls this value `noteType`, while the older chart schema used
	it for a numeric alt-animation selector.  Keeping the translation here
	means every importer and runtime path can share the same aliases without
	editing donor charts.

	The adapter never rewrites a chart.  Import discovery may emit a shared
	`noteInfo.json` table, and the gameplay loader calls `nativeNoteData` for
	each row while constructing its transient Note objects.  The authored row
	(and the destination chart JSON) therefore keeps the source engine's value.
*/
class NoteTypeCompat {
	/** Return a stable display/source name for a donor note type. */
	public static function canonical(value:Dynamic):String {
		if (value == null)
			return '';
		var text = StringTools.trim(Std.string(value));
		if (text == '')
			return '';
		switch (text.toLowerCase()) {
			case 'normal' | 'normal note' | 'default': return 'Normal';
			case 'alt' | 'alt anim' | 'alt animation' | 'alt-animation' | 'altanimation': return 'Alt Animation';
			case 'gf sing' | 'gf sing note' | 'girlfriend sing' | 'girlfriend note': return 'GF Sing';
			case 'hurt' | 'hurt note' | 'hurt-note' | 'damaging note': return 'Hurt Note';
			case "can't hit" | 'cant hit' | 'cannot hit' | 'un hittable' | 'unhittable': return "Can't Hit";
			case 'no animation' | 'no anim' | 'no-animation' | 'noanimation': return 'No Animation';
			default: return text;
		}
	}

	public static function isStringType(value:Dynamic):Bool {
		return value != null && Std.isOfType(value, String) && StringTools.trim(Std.string(value)) != '';
	}

	/** Built-in types need no noteInfo entry, but script callbacks still need
		their authored identity. Numeric and boolean legacy alt selectors are not
		note type names. Apply equally to heads and sustain segments. */
	public static function applySourceType(note:Dynamic, row:Array<Dynamic>):Void {
		if (note == null || row == null || row.length < 4 || !isStringType(row[3]))
			return;
		Reflect.setProperty(note, 'sourceKind', canonical(row[3]));
	}

	public static function isAlt(value:Dynamic):Bool {
		return canonical(value).toLowerCase() == 'alt animation';
	}

	public static function isGfSing(value:Dynamic):Bool {
		return canonical(value).toLowerCase() == 'gf sing';
	}

	/**
		Apply note-kind behavior which has the same meaning in V-Slice and the
		native custom-note channel.  Keep this separate from `canonical()` because
		short names such as `gf` are V-Slice kind ids, not universal Psych noteType
		aliases.

		Unknown/authored kinds deliberately return false.  Their identity stays in
		`sourceKind` for a companion HXC/song/character callback instead of being
		guessed from a chart name.
	*/
	public static function applyVSliceKind(definition:Dynamic, value:Dynamic):Bool {
		if (definition == null || value == null)
			return false;
		var normalized = StringTools.trim(Std.string(value)).toLowerCase();
		var type = switch (normalized) {
			case 'gf' | 'gf sing' | 'gf-sing' | 'girlfriend' | 'girlfriend sing': 'GF Sing';
			case 'hurt' | 'hurt note' | 'hurt-note': 'Hurt Note';
			case 'noanim' | 'noanimation' | 'no anim' | 'no animation' | 'no-animation': 'No Animation';
			default: '';
		};
		if (type == '')
			return false;
		Reflect.setField(definition, 'sourceNoteType', type);
		applyDefinitionSemantics(definition, type);
		return true;
	}

	/**
		Resolve the native Note data value for one authored row without changing
		the row.  The first two values in a legacy row carry the lane and side;
		custom Note definitions use the engine's reserved block beginning at
		`NOTE_AMOUNT * 10`, so only the lane is retained in that block.  Normal
		and alt rows return their original lane/side value unchanged.
	*/
	public static function nativeNoteData(row:Dynamic, noteAmount:Int, definitions:Array<Dynamic>):Int {
		if (row == null || !Std.isOfType(row, Array))
			return 0;
		var values:Array<Dynamic> = cast row;
		if (values.length < 2)
			return 0;
		var encoded = Std.parseInt(Std.string(values[1]));
		if (encoded == null)
			encoded = 0;
		if (values.length < 4 || !isStringType(values[3]))
			return encoded;
		var type = canonical(values[3]);
		if (type == '' || type == 'Normal' || type == 'Alt Animation')
			return encoded;
		if (noteAmount <= 0)
			noteAmount = 4;
		var customIndex = ensureDefinition(type, definitions);
		if (customIndex < 0)
			return encoded;
		var lane = encoded % noteAmount;
		if (lane < 0)
			lane += noteAmount;
		return lane + (customIndex + 5) * noteAmount * 2;
	}

	/** Read an authored alt selector without letting string note types become
		`Std.int("Hurt Note") == 0` in the old PlayState path. */
	public static function altNum(value:Dynamic, fallback:Int = 0):Int {
		if (value == null)
			return fallback;
		if (isStringType(value))
			return isAlt(value) ? 1 : fallback;
		if (Std.isOfType(value, Bool))
			return (cast value:Bool) ? 1 : 0;
		var parsed = Std.parseInt(Std.string(value));
		return parsed == null ? fallback : parsed;
	}

	/**
		Add a native noteInfo definition once and return its zero-based custom
		index.  Built-in normal/alt rows return -1 because they need no metadata.
	*/
	public static function ensureDefinition(value:Dynamic, definitions:Array<Dynamic>):Int {
		var type = canonical(value);
		if (type == '' || type == 'Normal' || type == 'Alt Animation')
			return -1;
		if (definitions == null)
			return -1;
		for (index in 0...definitions.length) {
			var existing = definitions[index];
			var existingType = existing == null ? '' : StringTools.trim(Std.string(Reflect.field(existing, 'sourceNoteType')));
			if (existingType != '' && existingType.toLowerCase() == type.toLowerCase())
				return index;
		}
		var id = safeId(type);
		var definition:Dynamic = {
			noteName: 'Psych ' + type,
			animNames: ['purple', 'blue', 'green', 'red'],
			animInt: [4, 5, 6, 7],
			classes: ['psych', 'psych-note-type:' + id],
			id: 'psych:' + id,
			sourceNoteType: type,
			sourceEngine: 'Psych/Kade'
		};
		applyDefinitionSemantics(definition, type);
		definitions.push(definition);
		return definitions.length - 1;
	}

	/** Shared behavior for canonical note types after an importer has positively
		identified their source-engine meaning. */
	static function applyDefinitionSemantics(definition:Dynamic, type:String):Void {
		// These are engine-defined conventions, not chart-specific guesses. The
		// values match the source engines' stock note intent while leaving arbitrary
		// custom note types identity-only until their script bridge is available.
		switch (type.toLowerCase()) {
			case 'no animation':
				definition.shouldSing = false;
			case "can't hit":
				definition.shouldSing = false;
				definition.dontCountNote = true;
				definition.dontStrum = true;
				definition.damageAmount = 0;
			case 'hurt note':
				definition.shouldSing = false;
				definition.dontCountNote = true;
				definition.dontStrum = true;
				// A negative health amount makes hitting a Psych Hurt Note hurt
				// instead of rewarding the player through the native judgement path.
				definition.damageAmount = -0.04;
			case 'gf sing':
				// This is a normal hittable note whose singer is GF. Receptor,
				// scoring, and sustain behaviour remain identical to a normal note.
				definition.shouldSing = true;
			default:
				// Preserve unknown names/classes, but let the native note path keep
				// the normal hit/miss behaviour until a donor callback is available.
		}
	}

	static function safeId(value:String):String {
		var result = '';
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			var good = (code >= 48 && code <= 57) || (code >= 65 && code <= 90)
				|| (code >= 97 && code <= 122) || code == 95 || code == 45;
			result += good ? value.charAt(index).toLowerCase() : '_';
		}
		return result == '' ? 'custom' : result;
	}
}
