package;

/** The Codename Character.fixChar orientation step, kept separate from the
 * native FNF player flip rules. */
class CodenameCharacterOrientation {
	/** Apply Codename's slot flip and its playerOffsets-dependent direction
	 * frame/offset swap. Suffixes come from authored singRIGHT animation names,
	 * matching Codename's XML-order enumeration. Returns the resulting flipX. */
	public static function apply<T>(isPlayer:Bool, playerOffsets:Bool, initialFlipX:Bool,
		animationNames:Array<String>,
		getFrames:String->Array<T>, setFrames:String->Array<T>->Void,
		offsets:Map<String, Array<Dynamic>>):Bool {
		if (isPlayer != playerOffsets) {
			var variants:Array<String> = [''];
			var pose = 'singRIGHT';
			for (name in animationNames)
				if (name != pose && StringTools.startsWith(name, pose))
					variants.push(name.substr(pose.length));
			for (variant in variants)
				swapPair('singLEFT' + variant, pose + variant, getFrames, setFrames, offsets);
		}
		// Upstream toggles the definition flip for every player-flipped slot,
		// even for dance-pair/GF characters which native code marks noFlip.
		return isPlayer ? !initialFlipX : initialFlipX;
	}

	static function swapPair<T>(left:String, right:String, getFrames:String->Array<T>,
		setFrames:String->Array<T>->Void, offsets:Map<String, Array<Dynamic>>):Void {
		var leftFrames = getFrames(left);
		var rightFrames = getFrames(right);
		if (leftFrames != null && rightFrames != null) {
			setFrames(left, rightFrames);
			setFrames(right, leftFrames);
		}

		// FunkinSprite.switchOffset swaps named entries, removing a key when its
		// partner has no offset. Keep that missing-key behavior exactly.
		var leftOffset = offsets.get(left);
		var rightOffset = offsets.get(right);
		if (rightOffset == null)
			offsets.remove(left);
		else
			offsets.set(left, rightOffset);
		if (leftOffset == null)
			offsets.remove(right);
		else
			offsets.set(right, leftOffset);
	}
}
