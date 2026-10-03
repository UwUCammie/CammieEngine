package;

import flixel.sound.FlxSound;

/** Non-owning PlayableSong-shaped view over this PlayState's audio tracks. */
@:keep
class NightmareVisionPlayableSongView {
	var instrumental:NightmareVisionAudioSoundView;
	var vocalTracksProvider:Void->VocalTracks;
	var released:Bool = false;
	var rememberedVolume:Float = 1;

	@:keep public var inst(get, never):Null<NightmareVisionAudioSoundView>;
	@:keep public var playerVocals(default, null):NightmareVisionSoundGroupView;
	@:keep public var opponentVocals(default, null):NightmareVisionSoundGroupView;
	@:keep public var volume(get, set):Float;
	@:keep public var time(get, set):Float;
	@:keep public var playing(get, never):Bool;
	@:keep public var songLength(get, never):Float;
	@:keep public var members(get, never):Array<Dynamic>;

	public function new(instrumentalProvider:Void->FlxSound, instrumentalLength:Void->Float,
		vocalTracksProvider:Void->VocalTracks) {
		if (instrumentalProvider == null || instrumentalLength == null || vocalTracksProvider == null)
			throw '[nightmare-vision-audio] PlayableSong views require live state providers';
		this.vocalTracksProvider = vocalTracksProvider;
		instrumental = new NightmareVisionAudioSoundView(instrumentalProvider, instrumentalLength);
		playerVocals = new NightmareVisionSoundGroupView(this, 'player');
		opponentVocals = new NightmareVisionSoundGroupView(this, 'opponent');
	}

	function get_inst():Null<NightmareVisionAudioSoundView>
		return instrumental != null && instrumental.length > 0 ? instrumental : null;

	function get_volume():Float {
		if (inst != null) return instrumental.volume;
		var sounds = allVocalSounds();
		return sounds.length == 0 ? rememberedVolume : sounds[0].volume;
	}

	function set_volume(value:Float):Float {
		rememberedVolume = value;
		if (inst != null) instrumental.volume = value;
		for (sound in allVocalSounds()) sound.volume = value;
		return value;
	}

	function get_time():Float {
		if (inst != null) return instrumental.time;
		var sounds = allVocalSounds();
		return sounds.length == 0 ? 0 : sounds[0].time;
	}

	function set_time(value:Float):Float {
		if (inst != null) instrumental.time = value;
		for (sound in allVocalSounds()) sound.time = value;
		return value;
	}

	function get_playing():Bool {
		if (inst != null) return instrumental.playing;
		var sounds = allVocalSounds();
		return sounds.length > 0 && sounds[0].playing;
	}

	function get_songLength():Float {
		if (inst != null) return instrumental.length;
		var sounds = allVocalSounds();
		return sounds.length == 0 ? 0 : sounds[0].length;
	}

	function get_members():Array<Dynamic> {
		var result:Array<Dynamic> = [];
		// The source PlayableSong inserts its instrumental first, before any vocal
		// tracks. Keep that slot visible before countdown as a lazy sound view.
		if (inst != null) result.push(instrumental);
		for (sound in allVocalSounds()) result.push(sound);
		return result;
	}

	@:keep public function pause():Void {
		if (inst != null) instrumental.pause();
		for (sound in allVocalSounds()) sound.pause();
	}

	@:keep public function resume():Void {
		if (inst != null) instrumental.resume();
		for (sound in allVocalSounds()) sound.resume();
	}

	@:keep public function play(forceRestart:Bool = false, startTime:Float = 0, ?endTime:Null<Float>):Void {
		var sourceEndTime = endTime;
		if (sourceEndTime == null || sourceEndTime == 0) sourceEndTime = songLength;
		if (inst != null) instrumental.play(forceRestart, startTime, sourceEndTime);
		for (sound in allVocalSounds()) sound.play(forceRestart, startTime, sourceEndTime);
	}

	@:keep public function stop():Void {
		if (inst != null) instrumental.stop();
		for (sound in allVocalSounds()) sound.stop();
	}

	@:keep public function setTrackVolumeState(hasMissed:Bool = false):Void {
		// Nightmare Vision's PlayableSong inherits VocalGroup: miss()/hit()
		// mute/unmute only the player bus, leaving opponent voices untouched.
		for (sound in roleSounds('player')) sound.volume = hasMissed ? 0 : 1;
	}

	/** Called after native startSong has installed the current music FlxSound. */
	public function attachCurrentInstrumental(sound:FlxSound):Void {
		if (released || instrumental == null) return;
		instrumental.attachCurrentSound(sound);
	}

	@:keep public function roleSounds(role:String):Array<FlxSound> {
		if (released || vocalTracksProvider == null)
			throw '[nightmare-vision-audio] PlayableSong view has been released';
		var tracks = vocalTracksProvider();
		if (tracks == null)
			throw '[nightmare-vision-audio] Vocal tracks were not initialized before the source callback';
		return [for (sound in tracks.forRole(role)) if (sound != null && sound.length > 0) sound];
	}

	function allVocalSounds():Array<FlxSound> {
		if (released || vocalTracksProvider == null) return [];
		var tracks = vocalTracksProvider();
		if (tracks == null) return [];
		return [for (sound in tracks.tracks) if (sound != null && sound.length > 0) sound];
	}

	public function release():Void {
		if (released) return;
		released = true;
		if (instrumental != null) instrumental.release();
		instrumental = null;
		vocalTracksProvider = null;
		playerVocals = null;
		opponentVocals = null;
	}
}

/** Role-specific non-owning group view matching the source VocalGroup members. */
@:keep
class NightmareVisionSoundGroupView {
	final owner:NightmareVisionPlayableSongView;
	final role:String;

	@:keep public var members(get, never):Array<FlxSound>;
	@:keep public var length(get, never):Int;
	@:keep public var volume(get, set):Float;
	@:keep public var time(get, set):Float;
	@:keep public var playing(get, never):Bool;

	public function new(owner:NightmareVisionPlayableSongView, role:String) {
		this.owner = owner;
		this.role = role;
	}

	function get_members():Array<FlxSound> return owner.roleSounds(role);
	function get_length():Int return members.length;

	function get_volume():Float return members.length == 0 ? 1 : members[0].volume;

	function set_volume(value:Float):Float {
		for (sound in members) sound.volume = value;
		return value;
	}

	function get_time():Float return members.length == 0 ? 0 : members[0].time;

	function set_time(value:Float):Float {
		for (sound in members) sound.time = value;
		return value;
	}

	function get_playing():Bool return members.length > 0 && members[0].playing;

	@:keep public function play(forceRestart:Bool = false, startTime:Float = 0, ?endTime:Null<Float>):Void
		for (sound in members) sound.play(forceRestart, startTime, endTime);

	@:keep public function pause():Void for (sound in members) sound.pause();
	@:keep public function resume():Void for (sound in members) sound.resume();
	@:keep public function stop():Void for (sound in members) sound.stop();
}
