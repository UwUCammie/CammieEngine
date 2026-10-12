package;

/** Main-thread post-publication observer. Metadata failure never invalidates installed content. */
class LibraryImportHistory {
	public static function committed(owners:Array<String>):Void {
		if (owners == null || owners.length == 0) return;
		try {
			if (!UserLibrary.change(function(data) data.recordImports(owners, Date.now().getTime())))
				trace('[library-import-history] ' + UserLibrary.error);
		} catch (error:Dynamic) trace('[library-import-history] ' + Std.string(error));
	}
}
