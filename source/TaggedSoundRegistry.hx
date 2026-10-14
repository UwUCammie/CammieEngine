package;

/**
 * Script sounds that are addressed by a tag: one handle per tag, however many
 * tags play the same file. Generic over the handle so the bookkeeping can be
 * exercised without an audio device.
 */
class TaggedSoundRegistry<T> {
	var sounds:Map<String, T> = new Map();
	var alive:T->Bool;
	var dispose:T->Void;

	/**
	 * `alive` says whether a handle can still be driven, `dispose` silences and
	 * releases one that a tag no longer owns.
	 */
	public function new(alive:T->Bool, dispose:T->Void) {
		this.alive = alive;
		this.dispose = dispose;
	}

	/** Scripts pass nil, numbers and padded strings as tags; '' means no tag. */
	public static function key(tag:Dynamic):String {
		if (tag == null || Std.isOfType(tag, Bool))
			return '';
		return StringTools.trim(Std.string(tag));
	}

	/**
		The variable name Psych stores a tagged sound under and hands back from
		playSound: `sound_` plus the tag with spaces turned into underscores and
		dots dropped. Null for an untagged sound.
	*/
	public static function psychVariableName(tag:Dynamic):Null<String> {
		var name = key(tag);
		if (name == '')
			return null;
		return 'sound_' + StringTools.replace(StringTools.replace(name, ' ', '_'), '.', '');
	}

	/** The tag a Psych `sound_<tag>` variable name points at, or null for any other name. */
	public static function tagFromPsychVariable(variable:String):Null<String> {
		if (variable == null || !StringTools.startsWith(variable, 'sound_') || variable.length == 'sound_'.length)
			return null;
		return variable.substr('sound_'.length);
	}

	/**
		The sound a Psych `sound_<name>` variable points at. Psych builds that
		name with spaces turned into underscores and dots dropped, so a sound
		tagged 'my tag' answers to sound_my_tag as well as to its own spelling.
	*/
	public function findPsychVariable(variable:String):T {
		var tag = tagFromPsychVariable(variable);
		if (tag == null)
			return null;
		var direct = get(tag);
		if (direct != null)
			return direct;
		for (name in sounds.keys())
			if (psychVariableName(name) == variable)
				return get(name);
		return null;
	}

	public function get(tag:Dynamic):T {
		var name = key(tag);
		if (name == '')
			return null;
		var sound = sounds.get(name);
		if (sound != null && !alive(sound)) {
			// the audio system recycled it behind our back
			sounds.remove(name);
			return null;
		}
		return sound;
	}

	/** The one tag-or-music rule: an empty tag means `music` where the caller allows it. */
	public function resolve(tag:Dynamic, emptyMeansMusic:Bool, music:T):T {
		if (key(tag) == '')
			return emptyMeansMusic ? music : null;
		return get(tag);
	}

	/** Take over a tag. Whatever played under it before is silenced first. */
	public function put(tag:Dynamic, sound:T):Bool {
		var name = key(tag);
		if (name == '' || sound == null)
			return false;
		var previous = sounds.get(name);
		// a dead handle may already be somebody else's sound, so leave it be
		if (previous != null && previous != sound && alive(previous))
			dispose(previous);
		sounds.set(name, sound);
		return true;
	}

	/**
	 * A handle reached its end. Returns true when the tag still belongs to that
	 * handle, which is when scripts should hear about it. A sound that does not
	 * loop gives its tag up here.
	 */
	public function finished(tag:Dynamic, sound:T, looped:Bool):Bool {
		var name = key(tag);
		if (name == '' || sounds.get(name) != sound)
			return false;
		if (!looped)
			sounds.remove(name);
		return true;
	}

	/** Stop and forget one tag. */
	public function stop(tag:Dynamic):Bool {
		var name = key(tag);
		var sound = sounds.get(name);
		if (sound == null)
			return false;
		sounds.remove(name);
		if (alive(sound))
			dispose(sound);
		return true;
	}

	public function clear():Void {
		var old = [for (sound in sounds) sound];
		sounds = new Map();
		for (sound in old)
			if (sound != null && alive(sound))
				dispose(sound);
	}
}
