package;

/** Authored identity of one Codename note before native lane conversion. */
typedef CodenameNoteOrigin = {
	var engine:String;
	var version:Int;
	var lineIndex:Int;
	var noteIndex:Int;
	var lineType:Null<Int>;
	/** Absolute authored side: 0 player, 1 opponent. */
	var nativeSide:Int;
}

/**
	Optional native note row column 13. Columns 0..12 retain their existing
	meanings. The null padding makes the tag unambiguous beside native note
	columns and other importers' row extensions. A stale or malformed tag is
	ignored; it never changes timing, lane, sustain, or note-kind behavior.
*/
class CodenameNoteMetadata {
	public static inline var SLOT:Int = 13;
	public static inline var VERSION:Int = 1;

	public static function create(lineIndex:Int, noteIndex:Int, lineType:Null<Int>, nativeSide:Int):CodenameNoteOrigin {
		if (lineIndex < 0 || noteIndex < 0 || (nativeSide != 0 && nativeSide != 1))
			throw 'Invalid Codename note origin';
		return {engine:'codename', version:VERSION, lineIndex:lineIndex,
			noteIndex:noteIndex, lineType:lineType, nativeSide:nativeSide};
	}

	/** Return a new row; never mutate the converter's/native caller's row. */
	public static function apply(row:Array<Dynamic>, origin:CodenameNoteOrigin):Array<Dynamic> {
		if (row == null || row.length > SLOT || origin == null)
			throw 'Codename note metadata needs a native row without column 13';
		var result = row.copy();
		while (result.length < SLOT) result.push(null);
		result.push({engine:origin.engine, version:origin.version,
			lineIndex:origin.lineIndex, noteIndex:origin.noteIndex,
			lineType:origin.lineType, nativeSide:origin.nativeSide});
		if (read(result) == null)
			throw 'Codename note origin does not match native lane';
		return result;
	}

	/**
		Read only when the tag still describes the row's absolute gameplay side.
		Codename's native projection has four keys per side. Native sections with
		mustHitSection=false invert the 0..3 / 4..7 lane blocks.
	*/
	public static function read(row:Array<Dynamic>, ?mustHitSection:Bool = true,
		?keyCount:Int = 4):Null<CodenameNoteOrigin> {
		if (row == null || row.length <= SLOT || keyCount != 4) return null;
		var meta:Dynamic = row[SLOT];
		if (meta == null || Std.isOfType(meta, Array)
			|| Reflect.field(meta, 'engine') != 'codename'
			|| !isInteger(Reflect.field(meta, 'version')) || Reflect.field(meta, 'version') != VERSION
			|| !isNonnegativeInteger(Reflect.field(meta, 'lineIndex'))
			|| !isNonnegativeInteger(Reflect.field(meta, 'noteIndex')))
			return null;
		var lineType:Dynamic = Reflect.field(meta, 'lineType');
		if (lineType != null && !isInteger(lineType)) return null;
		var nativeSide:Dynamic = Reflect.field(meta, 'nativeSide');
		if (!isInteger(nativeSide) || (nativeSide != 0 && nativeSide != 1)) return null;
		var nativeLane:Dynamic = row[1];
		if (!isNonnegativeInteger(nativeLane)) return null;
		var encodedSide = (nativeLane % 8) >= 4 ? 1 : 0;
		var absoluteSide = mustHitSection ? encodedSide : 1 - encodedSide;
		if (nativeSide != absoluteSide) return null;
		return {engine:'codename', version:VERSION,
			lineIndex:cast Reflect.field(meta, 'lineIndex'),
			noteIndex:cast Reflect.field(meta, 'noteIndex'),
			lineType:cast lineType, nativeSide:cast nativeSide};
	}

	static function isInteger(value:Dynamic):Bool {
		return Std.isOfType(value, Int) && !Std.isOfType(value, Bool);
	}

	static function isNonnegativeInteger(value:Dynamic):Bool {
		return isInteger(value) && value >= 0;
	}
}
