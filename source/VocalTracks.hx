package;

import flixel.sound.FlxSound;

/**
	Small audio-group adapter used by PlayState for songs which ship more than
	one vocal stem.  The first sound remains the legacy `vocals` object exposed
	to scripts; this class only centralises the operations which must reach every
	stem in the group.

	It deliberately does not extend a Flixel group.  FlxG.sound.list owns each
	FlxSound and the adapter has no ownership of that list, which keeps the
	legacy single-Voices path and native/web sound backends unchanged.
*/
class VocalTracks {
	public var primary:FlxSound;
	public var tracks:Array<FlxSound> = [];
	var roles:Array<String> = [];
	var lastPrimaryVolume:Float = 1;

	public function new(primary:FlxSound, ?additional:Array<FlxSound>) {
		add(primary);
		if (additional != null)
			for (sound in additional)
				add(sound);
	}

	public function add(sound:FlxSound, ?role:String = "player"):Void {
		if (sound == null)
			return;
		for (existing in tracks)
			if (existing == sound)
				return;
		if (primary == null) {
			primary = sound;
			lastPrimaryVolume = sound.volume;
		}
		tracks.push(sound);
		roles.push(role == null ? "player" : role.toLowerCase());
	}

	public function setRole(sound:FlxSound, role:String):Void {
		var index = tracks.indexOf(sound);
		if (index >= 0)
			roles[index] = role == null ? "player" : role.toLowerCase();
	}

	public function play():Void {
		for (sound in tracks)
			if (sound != null)
				sound.play();
	}

	public function pause():Void {
		for (sound in tracks)
			if (sound != null)
				sound.pause();
	}

	public function stop():Void {
		for (sound in tracks)
			if (sound != null)
				sound.stop();
	}

	public function seek(time:Float):Void {
		for (sound in tracks)
			if (sound != null)
				sound.time = time;
	}

	public function setVolume(volume:Float):Void {
		for (sound in tracks)
			if (sound != null)
				sound.volume = volume;
		if (primary != null)
			lastPrimaryVolume = primary.volume;
	}

	/** V-Slice's player vocal bus can be restored without changing opponent stems. */
	public function setPlayerVolume(volume:Float):Void {
		var hasPlayer = roles.indexOf("player") >= 0;
		for (index in 0...tracks.length)
			if (tracks[index] != null && (roles[index] == "player"
				|| (!hasPlayer && roles[index] == "shared")))
				tracks[index].volume = volume;
		if (primary != null)
			lastPrimaryVolume = primary.volume;
	}

	public function getPlayerVolume():Float {
		for (index in 0...tracks.length)
			if (tracks[index] != null && roles[index] == "player")
				return tracks[index].volume;
		for (index in 0...tracks.length)
			if (tracks[index] != null && roles[index] == "shared")
				return tracks[index].volume;
		return 1;
	}

	/** A legacy script write to the primary FlxSound still controls every stem. */
	public function syncPrimaryVolume():Void {
		if (primary == null || primary.volume == lastPrimaryVolume)
			return;
		lastPrimaryVolume = primary.volume;
		for (sound in tracks)
			if (sound != null && sound != primary)
				sound.volume = lastPrimaryVolume;
	}

	public function setPitch(pitch:Float):Void {
		for (sound in tracks)
			if (sound != null)
				sound.pitch = pitch;
	}

	public function getTime():Float {
		return primary == null ? 0 : primary.time;
	}

	public function getActualVolume():Float {
		return primary == null ? 0 : primary.getActualVolume();
	}

	public function destroy():Void {
		for (sound in tracks)
			if (sound != null)
				sound.destroy();
		tracks = [];
		roles = [];
		primary = null;
	}
}
