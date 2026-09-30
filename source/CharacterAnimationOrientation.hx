package;

/** Keeps named animation offsets attached when legacy player-facing setup
 * exchanges left/right frame lists. */
class CharacterAnimationOrientation {
	public static function swapAll<T>(names:Array<String>,
		getFrames:String->Array<T>, setFrames:String->Array<T>->Void,
		offsets:Map<String, Array<Dynamic>>):Int {
		if (names == null)
			return 0;
		var swapped = 0;
		for (right in names) {
			if (right == null || !StringTools.startsWith(right, 'singRIGHT'))
				continue;
			var left = 'singLEFT' + right.substr('singRIGHT'.length);
			if (swapPair(left, right, getFrames, setFrames, offsets))
				swapped++;
		}
		return swapped;
	}

	public static function swapPair<T>(left:String, right:String,
		getFrames:String->Array<T>, setFrames:String->Array<T>->Void,
		offsets:Map<String, Array<Dynamic>>):Bool {
		var leftFrames = getFrames(left);
		var rightFrames = getFrames(right);
		if (leftFrames == null || rightFrames == null)
			return false;

		setFrames(left, rightFrames);
		setFrames(right, leftFrames);

		if (offsets != null) {
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
		return true;
	}
}
