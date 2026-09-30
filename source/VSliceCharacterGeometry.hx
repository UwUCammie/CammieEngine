/** V-Slice Bopper's animation offset is measured in source pixels relative
 * to CharacterData's global offset, then scaled with the live actor. */
class VSliceCharacterGeometry {
	public static inline function screenShift(animationOffset:Float, globalOffset:Float, scale:Float):Float {
		return (animationOffset - globalOffset) * scale;
	}
}
