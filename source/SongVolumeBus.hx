package;

import flixel.sound.FlxSound;
import flixel.sound.FlxSoundGroup;

/**
	One volume multiplier over a song's instrumental and vocal stems.

	Sounds are moved into a group that multiplies on top of the group they
	came from, so the player's music and sound options still apply and each
	sound keeps its own volume. Writes to a stem's volume (a miss muting the
	vocals, a script fading the instrumental) therefore never undo the
	multiplier, and the multiplier never overwrites them.
**/
class SongVolumeBus {
	var groups:Array<SongVolumeGroup> = [];

	public var multiplier(default, null):Float = 1;

	public function new() {}

	/** Put a sound under the multiplier. Safe to repeat for the same sound. */
	public function attach(sound:FlxSound):Void {
		if (sound == null)
			return;
		var base = sound.group;
		if (Std.isOfType(base, SongVolumeGroup)) {
			var scaled:SongVolumeGroup = cast base;
			if (groups.indexOf(scaled) >= 0)
				return;
			// Music outlives a song, so it can still sit in the last song's group.
			base = scaled.base;
		}
		groupOver(base).add(sound);
	}

	public function setMultiplier(value:Float):Void {
		multiplier = value;
		for (group in groups)
			group.volume = value;
	}

	/** Hand every sound back to the group it was taken from. */
	public function release():Void {
		for (group in groups)
			for (sound in group.sounds.copy()) {
				if (group.base != null)
					group.base.add(sound);
				else
					group.remove(sound);
			}
		groups = [];
	}

	function groupOver(base:FlxSoundGroup):SongVolumeGroup {
		for (group in groups)
			if (group.base == base)
				return group;
		var group = new SongVolumeGroup(base, multiplier);
		groups.push(group);
		return group;
	}
}

/** A sound group whose volume stacks on the group its sounds came from. */
class SongVolumeGroup extends FlxSoundGroup {
	public var base(default, null):FlxSoundGroup;

	public function new(base:FlxSoundGroup, volume:Float = 1) {
		this.base = base;
		super(volume);
	}

	override public function getVolume():Float {
		return (base == null ? 1.0 : base.getVolume()) * super.getVolume();
	}
}
