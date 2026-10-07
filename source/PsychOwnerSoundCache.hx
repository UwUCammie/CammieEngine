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

		// Match Psych's per-call local tracking. clearStoredMemory keeps sounds
		// requested in the current state and releases older owner entries.
		localTrackedAssets.push(file);
		return currentTrackedSounds.get(file);
	}

	public function returnMissing(file:String, beepOnNull:Bool = true, ?requestKey:String, ?path:String):Sound {
		ensureAlive();
		if (beepOnNull) {
			var key = requestKey == null ? file : requestKey;
			trace('SOUND NOT FOUND: $key, PATH: $path');
			FlxG.log.error('SOUND NOT FOUND: $key, PATH: $path');
			return FlxAssets.getSound('flixel/sounds/beep');
		}
		localTrackedAssets.push(file);
		return null;
	}

	public function clearStoredMemory():Void {
		ensureAlive();
		for (key in currentTrackedSounds.keys())
			if (!localTrackedAssets.contains(key) && !dumpExclusions.contains(key))
				currentTrackedSounds.remove(key);
		localTrackedAssets.resize(0);
	}

	public function release():Void {
		if (released) return;
		released = true;
		currentTrackedSounds.clear();
		localTrackedAssets.resize(0);
		dumpExclusions.resize(0);
	}

	public function isReleased():Bool return released;

	function ensureAlive():Void {
		if (released) throw '[psych-assets] The selected owner sound cache has been released';
	}
}
