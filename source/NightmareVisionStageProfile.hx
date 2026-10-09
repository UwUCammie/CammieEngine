package;

#if sys
import sys.FileSystem;
import sys.io.File;
#end

/** Import-owned API identity, separate from authored mod metadata and HUD art. */
class NightmareVisionStageProfile {
	public static inline var FILE_NAME = '__cammie_nv_stage_api.json';
	public static inline var LEGACY = 'legacy-group';
	public static inline var MODERN = 'modern-container';
	public static inline var UNKNOWN = 'unknown';


	public static function read(root:String):String {
		#if sys
		try {
			var path = root + '/' + FILE_NAME;
			if (!FileSystem.exists(path) || FileSystem.isDirectory(path)) return UNKNOWN;
			var value:Dynamic = haxe.Json.parse(File.getContent(path));
			if (value == null || value.version != 1 || value.owner != root) return UNKNOWN;
			return value.stageApi == LEGACY ? LEGACY : value.stageApi == MODERN ? MODERN : UNKNOWN;
		} catch (_:Dynamic) {}
		#end
		return UNKNOWN;
	}
}
