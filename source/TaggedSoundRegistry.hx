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
