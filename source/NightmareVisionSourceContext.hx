package;

/** Read the source engine's logical mod folder without deriving it from a
 * generated destination namespace or a human-readable package title. */
class NightmareVisionSourceContext {
	public static function directoryFromReceipt(record:Dynamic, owner:String, folder:String):String {
		if (record == null || record.version != 1 || record.sourceEngine != ImportEngine.NIGHTMARE_VISION
			|| record.destinationFolder != folder || record.sourceOwner != owner)
			throw '[nightmare-vision-source-context] Missing or mismatched import provenance';
		return NightmareVisionModsContext.sourceDirectoryFromProvenance(record);
	}
	public static function modDirectory(owner:String, folder:String):String {
		if (!CodenameScriptDiscovery.safeName(folder))
			throw '[nightmare-vision-source-context] Invalid chart storage folder';
		var path = 'assets/data/' + folder + '/importProvenance.json';
		return directoryFromReceipt(CoolUtil.parseJson(FNFAssets.getText(path)), owner, folder);
	}
}
