package;

/** Normalize nullable results from native filesystem directory enumeration.
	Some Windows runtimes return null for an unreadable or concurrently removed
	directory rather than throwing. */
class ImportDirectoryListing {
	public static function normalize(entries:Array<String>):Array<String> {
		return entries == null ? [] : entries;
	}
}
