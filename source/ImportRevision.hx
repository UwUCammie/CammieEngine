package;

using StringTools;

/** Compatibility version for the importer, independent of the application
 * release number.  Increment COMMON_REVISION when shared import semantics or
 * receipt interpretation changes; increment an engine revision when only
 * that source format's importer changes. */
typedef ImportRevisionStamp = {
	var schemaVersion:Int;
	var commonRevision:Int;
	var sourceEngine:String;
	var engineRevision:Int;
	/** Informational only.  It never determines compatibility. */
	var applicationVersion:String;
}

typedef ImportRevisionAssessment = {
	var status:String;
	var reason:String;
	var current:ImportRevisionStamp;
	var recorded:Dynamic;
}

/** Shared import compatibility revisions persisted with source receipts. */
class ImportRevision {
	public static inline var SCHEMA_VERSION:Int = 1;
	public static inline var COMMON_REVISION:Int = 3;
	public static inline var UNKNOWN:String = "unknown";
	public static inline var CURRENT:String = "current";
	public static inline var OUTDATED:String = "outdated";
	public static inline var FUTURE:String = "future";

	static final ENGINE_REVISIONS:Map<String, Int> = [
		"V-Slice" => 1,
		"Kade Engine" => 2,
		"Modding Plus" => 2,
		"Psych Engine" => 8,
		"Nightmare Vision" => 8,
		"FPS Plus" => 2,
		"Codename Engine" => 1,
		"Legacy FNF/Polymod" => 2
	];

	/** Returns the canonical importer name, or an empty string for Auto and
	 * unrecognized labels.  Existing UI labels remain unchanged. */
	public static function normalizeEngine(engine:String):String {
		if (engine == null) return "";
		var candidate = engine.trim().toLowerCase();
		return switch (candidate) {
			case "v-slice", "vslice", "v slice": "V-Slice";
			case "kade", "kade engine": "Kade Engine";
			case "modding plus", "moddingplus": "Modding Plus";
			case "psych", "psych engine", "psychengine": "Psych Engine";
			case "nightmare vision", "nightmarevision": "Nightmare Vision";
			case "fps plus", "fps+", "fpsplus": "FPS Plus";
			case "codename", "codename engine", "codenameengine": "Codename Engine";
			case "legacy fnf/polymod", "legacy fnf", "polymod", "legacy/polymod": "Legacy FNF/Polymod";
			default: "";
		};
	}

	public static function current(engine:String, ?applicationVersion:String):ImportRevisionStamp {
		var canonical = normalizeEngine(engine);
		if (canonical == "") throw "An explicit supported source engine is required for an import revision.";
		return {
			schemaVersion: SCHEMA_VERSION,
			commonRevision: COMMON_REVISION,
			sourceEngine: canonical,
			engineRevision: ENGINE_REVISIONS.get(canonical),
			applicationVersion: applicationVersion == null ? "" : applicationVersion
		};
	}

	/** Legacy receipts without an explicit compatibility stamp are unknown;
	 * an app-version string alone is never used to infer importer freshness. */
	public static function assess(recorded:Dynamic, engine:String):ImportRevisionAssessment {
		var canonical = normalizeEngine(engine);
		if (canonical == "") throw "An explicit supported source engine is required for an import revision assessment.";
		var now = current(canonical);
		var assessment:ImportRevisionAssessment = {
			status: UNKNOWN,
			reason: "No recognized importer compatibility revision was recorded.",
			current: now,
			recorded: recorded
		};
		if (recorded == null) return assessment;

		var schema:Dynamic = Reflect.field(recorded, "schemaVersion");
		var common:Dynamic = Reflect.field(recorded, "commonRevision");
		var recordedEngine:Dynamic = Reflect.field(recorded, "sourceEngine");
		var engineRevision:Dynamic = Reflect.field(recorded, "engineRevision");
		if (!isInt(schema) || !isInt(common) || !isInt(engineRevision)
			|| recordedEngine == null) return assessment;

		var recordedCanonical = normalizeEngine(Std.string(recordedEngine));
		if (recordedCanonical == "" || recordedCanonical != canonical) {
			assessment.reason = "The recorded source engine does not match the selected importer.";
			return assessment;
		}
		var schemaValue:Int = cast schema;
		var commonValue:Int = cast common;
		var engineValue:Int = cast engineRevision;
		if (schemaValue > SCHEMA_VERSION || commonValue > COMMON_REVISION
			|| engineValue > now.engineRevision) {
			assessment.status = FUTURE;
			assessment.reason = "The receipt was created by a newer importer compatibility revision.";
			return assessment;
		}
		if (schemaValue < SCHEMA_VERSION || commonValue < COMMON_REVISION
			|| engineValue < now.engineRevision) {
			assessment.status = OUTDATED;
			assessment.reason = "The receipt predates the current importer compatibility revision.";
			return assessment;
		}
		assessment.status = CURRENT;
		assessment.reason = "The receipt matches the current importer compatibility revision.";
		return assessment;
	}

	static function isInt(value:Dynamic):Bool {
		return value != null && Std.isOfType(value, Int);
	}
}
