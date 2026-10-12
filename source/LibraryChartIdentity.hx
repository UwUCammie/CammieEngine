package;

typedef LibraryChartRecord = {
	var ownerRoot:String;
	var sourceFolder:String;
	var provenance:Dynamic;
	var hasReceipt:Bool;
}

/** Shared lazy receipt/owner resolution for library browsing and play history. */
class LibraryChartIdentity {
	public static function read(folder:String):Null<LibraryChartRecord> {
		if (folder == null || folder == '' || folder.indexOf('/') >= 0
			|| folder.indexOf('\\') >= 0 || folder.indexOf('..') >= 0) return null;
		var result:LibraryChartRecord = {ownerRoot:'', sourceFolder:'', provenance:null, hasReceipt:false};
		#if sys
		var path = 'assets/data/' + folder.toLowerCase() + '/importProvenance.json';
		result.hasReceipt = FNFAssets.exists(path);
		if (result.hasReceipt) try {
			result.provenance = CoolUtil.parseJson(FNFAssets.getText(path));
			var source:Dynamic = Reflect.field(result.provenance, 'sourceFolder');
			if (Std.isOfType(source, String)) result.sourceFolder = cast source;
		} catch (_:Dynamic) {}
		result.ownerRoot = ImportedModDiscovery.ownerForSong(folder, 'assets/data');
		#end
		return result;
	}
}
