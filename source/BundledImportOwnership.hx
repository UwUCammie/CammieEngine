package;

/** Compiled host content, never inferred from editable installed metadata. */
class BundledImportOwnership {
	public static inline var RESULTS_ROOT:String = 'assets/imported_mods/bundled-vslice-results';
	public static function roots():Array<String> return [RESULTS_ROOT];
	public static function protectedOwner(owner:String):Bool {
		return owner != null && owner.toLowerCase() == RESULTS_ROOT;
	}
}
