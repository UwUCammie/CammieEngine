package;

using StringTools;

/**
	Owner-local adapter for the source `funkin.backend.Difficulty` API.

	The selected difficulty index is supplied by the host and can be refreshed
	when a different chart becomes active. Mutable source arrays are copied per
	owner, so a script changing its difficulty menu cannot affect another import.
*/
@:keep
class NightmareVisionDifficultyAdapter {
	public static function defaultNames():Array<String> return ['Easy', 'Normal', 'Hard'];

	public var ownerRoot(default, null):String;
	public var defaultDifficulties(default, null):Array<String>;
	public var defaultDifficulty:String = 'Normal';
	public var difficulties:Array<String>;
	public var currentDifficultyIndex(default, null):Int;
	public var released(default, null):Bool = false;

	final report:String->Void;

	/** `initialDifficulties` follows the source FreeplayState declaration when
		available; otherwise source defaults are used. */
	public function new(ownerRoot:String, ?initialDifficulties:Array<String>, currentIndex:Int = 1,
		?report:String->Void) {
		if (ownerRoot == null || StringTools.trim(ownerRoot) == '')
			throw '[nightmare-vision-difficulty] Missing selected owner root';
		this.ownerRoot = normalizeOwner(ownerRoot);
		defaultDifficulties = defaultNames();
		difficulties = initialDifficulties == null ? defaultNames() : initialDifficulties.copy();
		currentDifficultyIndex = currentIndex;
		this.report = report == null ? function(message:String):Void trace(message) : report;
	}

	public function canReuseFor(owner:String):Bool {
		if (released || owner == null) return false;
		return normalizeOwner(owner) == ownerRoot;
	}

	/** Source `reset()` restores a detached copy of the standard difficulty list. */
	public function reset():Array<String> {
		ensureAlive();
		difficulties = defaultDifficulties.copy();
		return difficulties;
	}

	/** Update the selected source difficulty after the host loads or changes charts. */
	public function selectDifficulty(index:Int):Void {
		ensureAlive();
		currentDifficultyIndex = index;
	}

	/** Exact source behavior: resolve the requested/current slot, fall back to
		`defaultDifficulty` when missing, and sanitize the suffix. */
	public function getDifficultyFilePath(number:Int = -1):String {
		ensureAlive();
		if (number == -1) number = currentDifficultyIndex;
		var suffix:Null<String> = number >= 0 && number < difficulties.length ? difficulties[number] : null;
		if (suffix == null) {
			report('[nightmare-vision-difficulty-index-fallback] difficulty index ' + number
				+ ' does not exist; using ' + defaultDifficulty);
			suffix = defaultDifficulty;
		}
		return sanitize(suffix);
	}

	/** Exact source lookup: an absent current slot resolves to defaultDifficulty. */
	public function getCurrentDifficultyString():String {
		ensureAlive();
		var selected:Null<String> = currentDifficultyIndex >= 0 && currentDifficultyIndex < difficulties.length
			? difficulties[currentDifficultyIndex] : null;
		return selected == null ? defaultDifficulty : selected;
	}

	public function release():Void {
		if (released) return;
		released = true;
		ownerRoot = '';
		defaultDifficulty = null;
		currentDifficultyIndex = -1;
		defaultDifficulties.resize(0);
		difficulties.resize(0);
	}

	function ensureAlive():Void {
		if (released)
			throw '[nightmare-vision-difficulty] This owner adapter has been released';
	}

	static function sanitize(value:String):String {
		// Mirrors the source Paths.sanitize behavior for a difficulty suffix.
		var invalidBeforeSlash = new EReg('[^- a-zA-Z0-9..\\/]+\\/', 'g');
		return invalidBeforeSlash.replace(value, '').replace(' ', '-').trim().toLowerCase();
	}

	static function normalizeOwner(value:String):String
		return StringTools.trim(value.replace('\\', '/'));
}
