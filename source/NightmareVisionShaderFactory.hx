package;

/** Builds source-compatible runtime shaders from one selected NMV install. */
@:keep
class NightmareVisionShaderFactory {
	/**
	 * Source-compatible equivalent of FunkinRuntimeShader.fromPath.
	 * Shader names are passed to the selected install's Paths facade, which
	 * checks that owner's content first and its explicitly staged core second.
	 */
	public static function fromPath(ownerRoot:String, ?fragFile:String, ?vertFile:String):NightmareVisionRuntimeShader {
		var paths = new NightmareVisionPaths(ownerRoot);
		var fragmentPath = fragFile == null ? null : paths.fragment(fragFile, true);
		var vertexPath = vertFile == null ? null : paths.vertex(vertFile, true);
		var fragmentSource = fragFile == null ? null : readShaderSource(paths, fragmentPath, 'fragment', fragFile);
		var vertexSource = vertFile == null ? null : readShaderSource(paths, vertexPath, 'vertex', vertFile);
		return new NightmareVisionRuntimeShader(fragmentSource, vertexSource, fragmentPath, vertexPath);
	}

	static function readShaderSource(paths:NightmareVisionPaths, path:String, kind:String, key:String):String {
		if (path == null || !paths.exists(path))
			throw '[nightmare-vision-shader] Missing ' + kind + ' shader "' + key + '" at '
				+ (path == null ? '<unresolved owner path>' : path);
		return FNFAssets.getText(path);
	}
}
