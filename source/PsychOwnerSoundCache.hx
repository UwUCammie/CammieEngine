package;

import flixel.system.FlxAssets;
import flixel.FlxG;
import openfl.media.Sound;

/** Per-owner sound cache used by the modern Psych Paths audio helpers. */
@:keep
class PsychOwnerSoundCache {
	static var owners:Map<String, PsychOwnerSoundCache> = new Map();

	public final ownerRoot:String;
	public final currentTrackedSounds:Map<String, Sound> = new Map();
	public final localTrackedAssets:Array<String> = [];
	public final dumpExclusions:Array<String> = ['assets/shared/music/freakyMenu.' + Paths.SOUND_EXT];
	var released:Bool = false;
	// clearStoredMemory only asks whether a file was requested in this state.
	// Psych pushes every request, so a sound played each beat grew the list for
	// the whole song and made the clear quadratic. Keep each file once.
	final localTrackedSet:Map<String, Bool> = new Map();
	var localTrackedCount:Int = 0;
	// Request shape to the owner file it resolved to. Only trusted while that
	// file's decoded Sound is still held, so a hit never changes the result.
	final resolvedFiles:Map<String, String> = new Map();
	var resolvedCount:Int = 0;
	var resolvedGeneration:Int = -1;
	var resolvedRevision:Int = -1;

	public function new(ownerRoot:String) {
		if (ownerRoot == null || StringTools.trim(ownerRoot) == '')
			throw '[psych-assets] A selected owner is required for its sound cache';
		this.ownerRoot = ownerRoot;
	}

	public static function forOwner(ownerRoot:String):PsychOwnerSoundCache {
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		if (owner == '') throw '[psych-assets] A valid selected import owner root is required';
		var key = CompatScriptManifest.destinationKey(owner);
		var selected = owners.get(key);
		if (selected == null || selected.released) {
			selected = new PsychOwnerSoundCache(owner);
			owners.set(key, selected);
		}
		return selected;
	}

	/** Drop only this owner's retained Sound references. Active FlxSound channels
	 * keep their own references until playback ends. */
	public static function releaseOwner(ownerRoot:String):Void {
		if (ownerRoot == null || StringTools.trim(ownerRoot) == '') return;
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		if (owner == '') return;
		var key = CompatScriptManifest.destinationKey(owner);
		var selected = owners.get(key);
		if (selected == null) return;
		selected.release();
		owners.remove(key);
	}

	public function returnSound(file:String, beepOnNull:Bool = true, ?requestKey:String, ?path:String):Sound {
		ensureAlive();
		if (file == null || StringTools.trim(file) == '')
			throw '[psych-assets] A non-empty Psych sound path is required';

		if (!currentTrackedSounds.exists(file)) {
			if (FNFAssets.exists(file))
				currentTrackedSounds.set(file, FNFAssets.getSound(file));
			else if (beepOnNull) {
				var key = requestKey == null ? file : requestKey;
				trace('SOUND NOT FOUND: $key, PATH: $path');
				FlxG.log.error('SOUND NOT FOUND: $key, PATH: $path');
				return FlxAssets.getSound('flixel/sounds/beep');
			}
		}

		// Match Psych's local tracking. clearStoredMemory keeps sounds requested
		// in the current state and releases older owner entries.
		trackLocal(file);
		return currentTrackedSounds.get(file);
	}

	/** The file an identical earlier request resolved to, while its Sound is
	 * still cached. Import refreshes and identity changes forget every entry. */
	public function resolvedFile(request:String):Null<String> {
		if (released || request == null) return null;
		refreshResolved();
		if (resolvedCount == 0) return null;
		var file = resolvedFiles.get(request);
		if (file == null) return null;
		if (!currentTrackedSounds.exists(file)) {
			resolvedFiles.remove(request);
			resolvedCount--;
			return null;
		}
		return file;
	}

	public function rememberResolvedFile(request:String, file:String):Void {
		if (released || request == null || file == null) return;
		refreshResolved();
		if (!resolvedFiles.exists(request)) resolvedCount++;
		resolvedFiles.set(request, file);
	}

	function refreshResolved():Void {
		var generation = ImportRefreshManager.generation;
		var revision = ImportRefreshManager.availabilityRevision();
		if (resolvedCount > 0 && (generation != resolvedGeneration || revision != resolvedRevision))
			clearResolved();
		resolvedGeneration = generation;
		resolvedRevision = revision;
	}

	function clearResolved():Void {
		resolvedFiles.clear();
		resolvedCount = 0;
	}

	function trackLocal(file:String):Void {
		syncLocalTracked();
		if (localTrackedSet.exists(file)) return;
		localTrackedSet.set(file, true);
		localTrackedAssets.push(file);
		localTrackedCount++;
	}

	/** localTrackedAssets is public on the Paths facade, so a script may edit it
	 * directly. Rebuild the lookup set whenever its length moved underneath us. */
	function syncLocalTracked():Void {
		if (localTrackedAssets.length == localTrackedCount) return;
		localTrackedSet.clear();
		for (file in localTrackedAssets) localTrackedSet.set(file, true);
		localTrackedCount = localTrackedAssets.length;
	}

	function resetLocalTracked():Void {
		localTrackedAssets.resize(0);
		localTrackedSet.clear();
		localTrackedCount = 0;
	}

	public function returnMissing(file:String, beepOnNull:Bool = true, ?requestKey:String, ?path:String):Sound {
		ensureAlive();
		if (beepOnNull) {
			var key = requestKey == null ? file : requestKey;
			trace('SOUND NOT FOUND: $key, PATH: $path');
			FlxG.log.error('SOUND NOT FOUND: $key, PATH: $path');
			return FlxAssets.getSound('flixel/sounds/beep');
		}
		trackLocal(file);
		return null;
	}

	public function clearStoredMemory():Void {
		ensureAlive();
		syncLocalTracked();
		for (key in currentTrackedSounds.keys())
			if (!localTrackedSet.exists(key) && !dumpExclusions.contains(key))
				currentTrackedSounds.remove(key);
		resetLocalTracked();
	}

	public function release():Void {
		if (released) return;
		released = true;
		currentTrackedSounds.clear();
		resetLocalTracked();
		clearResolved();
		dumpExclusions.resize(0);
	}

	public function isReleased():Bool return released;

	function ensureAlive():Void {
		if (released) throw '[psych-assets] The selected owner sound cache has been released';
	}
}
