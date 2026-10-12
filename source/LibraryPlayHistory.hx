package;

/** One successful song start per PlayState instance, shared by all launch routes. */
class LibraryPlayHistory {
	var attempted:Bool = false;
	public function new() {}
	public function started(folder:String):Void {
		if (attempted) return;
		attempted = true;
		try {
			var identity = LibraryChartIdentity.read(folder);
			if (identity == null) return;
			var key = UserLibraryData.resolvedChartKey(identity.ownerRoot, folder,
				identity.sourceFolder, identity.hasReceipt);
			if (key == '') return;
			if (!UserLibrary.change(function(data) data.recordPlay(key, Date.now().getTime())))
				trace('[library-history] ' + UserLibrary.error);
		} catch (error:Dynamic) trace('[library-history] ' + Std.string(error));
	}
}
