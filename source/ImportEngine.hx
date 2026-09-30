package;

using StringTools;

/**
	Names exposed by the engine-aware importer.

	These are strings on purpose.  They are persisted in the options file and
	may be passed through HScript/UI code, so changing a label is a data-format
	change.  Keep the labels here as the single source of truth for importer
	selectors and for Auto's detection result.
*/
class ImportEngine {
	public static inline var AUTO:String = 'Auto';
	public static inline var V_SLICE:String = 'V-Slice';
	public static inline var KADE:String = 'Kade Engine';
	public static inline var MODDING_PLUS:String = 'Modding Plus';
	public static inline var PSYCH:String = 'Psych Engine';
	public static inline var NIGHTMARE_VISION:String = 'Nightmare Vision';
	public static inline var FPS_PLUS:String = 'FPS Plus';
	public static inline var CODENAME:String = 'Codename Engine';
	public static inline var LEGACY_POLYMOD:String = 'Legacy FNF/Polymod';

	public static final TYPES:Array<String> = [
		AUTO,
		V_SLICE,
		KADE,
		MODDING_PLUS,
		PSYCH,
		NIGHTMARE_VISION,
		FPS_PLUS,
		CODENAME,
		LEGACY_POLYMOD
	];

	/** Return a copy so a UI cannot mutate the registry. */
	public static function names():Array<String> {
		return TYPES.copy();
	}

	/** Normalize persisted/UI input without silently inventing an engine. */
	public static function normalize(value:Dynamic):String {
		if (value != null) {
			var candidate = StringTools.trim(Std.string(value));
			for (engine in TYPES)
				if (candidate == engine)
					return engine;
		}
		return AUTO;
	}

	public static function isSelectable(value:Dynamic):Bool {
		return normalize(value) == Std.string(value);
	}

	public static function isAuto(value:Dynamic):Bool {
		return normalize(value) == AUTO;
	}
}
