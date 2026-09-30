package;

/** Owner-scoped subset of the source engine's FunkinAssets API. */
@:keep
class NightmareVisionFunkinAssets {
	final paths:NightmareVisionPaths;

	public function new(paths:NightmareVisionPaths) {
		this.paths = paths;
	}

	/** Match the source API's common existence check while keeping reads inside
	 * the selected package and its explicitly installed engine-core subtree. */
	public function exists(path:String):Bool {
		var scoped = paths.scopeAssetPath(path);
		return scoped != null && FNFAssets.exists(scoped);
	}
}
