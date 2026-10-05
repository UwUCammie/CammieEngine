package;

/** A chart note's authored playfield identity, kept separate from its
 * destination hit-side boolean and note-type encoding. */
typedef ChartNoteAddress = {
	var playfieldIndex:Int;
	var direction:Int;
	/** The character group that owns the source field. NMV's field 2 and later
	 * fields are BF-owned even though they do not share field 0's input policy. */
	var playerControlled:Bool;
	/** Whether the source field resolves notes automatically regardless of the
	 * active native game mode. */
	var autoPlay:Bool;
}

/** Interpret a chart row's side using the convention declared by its format.
 * Psych v1 charts store absolute player/opponent lanes; older FNF-family
 * charts store lanes relative to mustHitSection. */
class ChartNoteOwnership {
	static inline var PSYCH_V1_COLUMNS:Int = 4;

	/** Resolve the source field and local key direction before note-type metadata
	 * is encoded into the destination Note. NMV's field ID is not equivalent to
	 * `mustPress`: for example its third field is BF-controlled but autoplayed. */
	public static function address(format:String, lane:Int, mustHitSection:Bool,
		columns:Int):ChartNoteAddress {
		if (columns <= 0 || lane < 0)
			return {playfieldIndex: -1, direction: -1, playerControlled: false, autoPlay: false};

		var normalized = format == null ? '' : StringTools.trim(format).toLowerCase();
		var absoluteFields = normalized == 'nmv2' || normalized == 'psych_v1';
		var playfieldIndex = absoluteFields ? Std.int(lane / columns)
			: (mustPress(format, lane, mustHitSection, columns) ? 0 : 1);
		return {
			playfieldIndex: playfieldIndex,
			direction: lane % columns,
			// Both normalized NMV formats use the same generated field policy:
			// field 1 belongs to Dad, while field 0 and fields 2+ belong to BF.
			playerControlled: absoluteFields ? playfieldIndex != 1 : playfieldIndex == 0,
			// The source's cpuControlled setting also autoplays field 0 at runtime.
			// Every other normalized field autoplays even with botplay disabled.
			autoPlay: absoluteFields && playfieldIndex != 0
		};
	}

	/** NV's older charts convert only their first two section-relative banks.
	 * Additional banks retain their authored ID; leave retained chart rows intact. */
	public static function nightmareVisionAddress(format:String, lane:Int, mustHitSection:Bool,
		columns:Int):ChartNoteAddress {
		var normalized = format == null ? '' : StringTools.trim(format).toLowerCase();
		var result = address(normalized == 'nmv2' || normalized == 'psych_v1' ? normalized : null,
			lane, mustHitSection, columns);
		if (columns <= 0 || lane < 0) return result;
		if (lane >= columns * 2) result.playfieldIndex = Std.int(lane / columns);
		result.playerControlled = result.playfieldIndex != 1;
		result.autoPlay = result.playfieldIndex != 0;
		return result;
	}

	/** Legacy note ownership is represented by the mutable `mustPress` field.
	 * Only normalized NMV formats need a separate owner override because their
	 * authored playfield and the destination's binary hit side can differ. */
	public static function playerControlOverride(format:String,
		address:ChartNoteAddress):Null<Bool> {
		if (address == null || address.playfieldIndex < 0 || format == null)
			return null;
		var normalized = StringTools.trim(format).toLowerCase();
		return normalized == 'nmv2' || normalized == 'psych_v1'
			? address.playerControlled : null;
	}

	public static function mustPress(format:String, lane:Int, mustHitSection:Bool, columns:Int):Bool {
		if (columns <= 0)
			return false;
		if (format != null && StringTools.trim(format).toLowerCase() == 'psych_v1_convert')
			return lane >= 0 && lane < PSYCH_V1_COLUMNS;
		// Keep this legacy two-side query binary. New NMV consumers use address()
		// for the independent field ID, player owner, and autoplay policy; collapsing
		// those policies back into mustPress would misroute NMV field 2.
		if (format != null) {
			var normalized = StringTools.trim(format).toLowerCase();
			if (normalized == 'nmv2' || normalized == 'psych_v1')
				return lane >= 0 && lane < columns;
		}
		var doubled = columns * 2;
		var pairedLane = ((lane % doubled) + doubled) % doubled;
		return pairedLane >= columns ? !mustHitSection : mustHitSection;
	}
}
