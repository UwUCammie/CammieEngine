package;

typedef ImportRefreshFailureMarker = {
	var version:Int;
	var id:String;
	/** Receipt and importer state the failures were observed against. */
	var fingerprint:String;
	var attempts:Int;
	/** The cause cannot change until the importer or the receipt does. */
	var permanent:Bool;
	var reason:String;
}

typedef ImportEngineMismatch = {
	var relative:String;
	var recorded:String;
	var detected:String;
	var evidence:String;
}

/** Remembers that an outdated retained import could not be refreshed, so the
 * same doomed conversion is not repeated on every launch. A marker only applies
 * while the receipt, the importer revisions and the application version are all
 * unchanged; any of them changing allows fresh attempts. */
class ImportRefreshFailure {
	public static inline var VERSION:Int = 1;
	/** Ordinary failures get one retry in case the first was transient. */
	public static inline var MAX_ATTEMPTS:Int = 2;
	public static inline var MAX_REASON:Int = 600;
	public static inline var MISTYPED_PREFIX:String = "Recorded source engine does not match this package: ";

	public static function fingerprint(record:Dynamic, applicationVersion:String):String {
		var engines:Array<String> = [];
		var recorded:Dynamic = record == null ? null : Reflect.field(record, "engines");
		if (Std.isOfType(recorded, Array)) for (engine in (cast recorded:Array<Dynamic>)) {
			var name = ImportRevision.normalizeEngine(Std.string(engine));
			if (name != "" && engines.indexOf(name) < 0) engines.push(name);
		}
		engines.sort(Reflect.compare);
		var current = [for (engine in engines) engine + "@" + ImportRevision.current(engine).engineRevision];
		var stamps:Array<String> = [];
		var revisions:Dynamic = record == null ? null : Reflect.field(record, "revisions");
		if (Std.isOfType(revisions, Array)) for (stamp in (cast revisions:Array<Dynamic>)) if (stamp != null)
			stamps.push(Std.string(Reflect.field(stamp, "sourceEngine")) + "@" + Std.string(Reflect.field(stamp, "commonRevision"))
				+ "." + Std.string(Reflect.field(stamp, "engineRevision")));
		stamps.sort(Reflect.compare);
		return [Std.string(record == null ? null : Reflect.field(record, "snapshotId")),
			applicationVersion == null ? "" : applicationVersion,
			"common@" + ImportRevision.COMMON_REVISION, current.join(","), stamps.join(",")].join("|");
	}

	/** Parse a stored marker. Anything malformed or for another record is ignored. */
	public static function read(text:String, id:String):Null<ImportRefreshFailureMarker> {
		if (text == null || id == null) return null;
		var raw:Dynamic = null;
		try raw = haxe.Json.parse(text) catch (_:Dynamic) return null;
		if (raw == null || Type.typeof(raw) != TObject || Reflect.field(raw, "version") != VERSION
			|| Reflect.field(raw, "id") != id) return null;
		var fingerprint:Dynamic = Reflect.field(raw, "fingerprint");
		var attempts:Dynamic = Reflect.field(raw, "attempts");
		var reason:Dynamic = Reflect.field(raw, "reason");
		if (!Std.isOfType(fingerprint, String) || !Std.isOfType(attempts, Int) || attempts < 1 || !Std.isOfType(reason, String))
			return null;
		return {version:VERSION, id:id, fingerprint:fingerprint, attempts:attempts,
			permanent:Reflect.field(raw, "permanent") == true, reason:bounded(reason)};
	}

	/** True when another automatic attempt would repeat a known failure. */
	public static function blocks(marker:Null<ImportRefreshFailureMarker>, fingerprint:String):Bool
		return marker != null && marker.fingerprint == fingerprint && (marker.permanent || marker.attempts >= MAX_ATTEMPTS);

	public static function next(previous:Null<ImportRefreshFailureMarker>, id:String, fingerprint:String,
			error:String, permanent:Bool):ImportRefreshFailureMarker {
		var repeated = previous != null && previous.fingerprint == fingerprint;
		return {version:VERSION, id:id, fingerprint:fingerprint, attempts:repeated ? previous.attempts + 1 : 1,
			permanent:permanent || (repeated && previous.permanent), reason:bounded(error)};
	}

	public static function isMistyped(error:String):Bool return error != null && StringTools.startsWith(error, MISTYPED_PREFIX);

	/** Folded, capped text: one failing package can repeat a line thousands of times. */
	public static function bounded(error:String):String {
		var text = TraceDigest.collapse(error, 6);
		return text.length <= MAX_REASON ? text : text.substr(0, MAX_REASON - 3) + "...";
	}

	public static function message(marker:ImportRefreshFailureMarker, label:String):String
		return "The outdated import \"" + label + "\" could not be refreshed by this version and was left unchanged. "
			+ "Remove it from the library and import the original package again. Reason: " + marker.reason;

	/** Explain a refresh that failed because the receipt names the wrong engine.
	 * `duplicate` is the label of an installed import that already has the
	 * detected identity, or null. */
	public static function mistyped(mismatch:ImportEngineMismatch, duplicate:Null<String>):String
		return MISTYPED_PREFIX + "it was imported as " + mismatch.recorded + ", but "
			+ (mismatch.relative == "" ? "its root" : mismatch.relative) + " is " + mismatch.detected
			+ " (" + mismatch.evidence + "). "
			+ (duplicate == null ? "Import the original package again with Auto detection, then remove this copy."
				: "A correctly detected copy (\"" + duplicate + "\") is already installed; remove this older copy from the library.");

	/** Compare an explicitly typed, evidence-free root with what detection now
	 * proves from its executable. Layout hints alone never contradict the receipt. */
	public static function mismatch(relative:String, recordedType:String, recordedEngine:String, recordedEvidence:Dynamic,
			detectedEngine:String, detectedEvidence:Array<String>):Null<ImportEngineMismatch> {
		var chosen = ImportRevision.normalizeEngine(recordedType);
		var recorded = ImportRevision.normalizeEngine(recordedEngine);
		var detected = ImportRevision.normalizeEngine(detectedEngine);
		if (chosen == "" || recorded == "" || recorded != chosen || detected == "" || detected == recorded) return null;
		if (Std.isOfType(recordedEvidence, Array) && (cast recordedEvidence:Array<Dynamic>).length > 0) return null;
		if (detectedEvidence != null) for (line in detectedEvidence)
			if (line != null && line.toLowerCase().indexOf("executable") >= 0)
				return {relative:relative == null ? "" : relative, recorded:recorded, detected:detected, evidence:line};
		return null;
	}
}
