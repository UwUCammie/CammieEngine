package;

#if sys
import sys.FileSystem;
import sys.io.File;
#end

/** Application presentation metadata. Foreign engine API versions are separate. */
class EngineBranding {
	public static inline var NAME:String = 'CammieEngine';
	public static inline var FALLBACK_VERSION:String = '0.0.10';
	public static function version():String {
		#if sys
		try {
			var root = haxe.io.Path.directory(sys.FileSystem.fullPath(Sys.programPath()));
			var releaseTag = haxe.io.Path.join([root, 'RELEASE_TAG']);
			if (FileSystem.exists(releaseTag) && !FileSystem.isDirectory(releaseTag)) {
				var tag = StringTools.trim(File.getContent(releaseTag));
				if (~/^v?[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$/.match(tag))
					return StringTools.startsWith(tag, 'v') ? tag.substr(1) : tag;
			}
		} catch (error:Dynamic) {}
		#end
		#if lime
		var app = lime.app.Application.current;
		if (app != null && app.meta != null) {
			var value = app.meta.get('version');
			if (value != null && StringTools.trim(value) != '' && value != '0.0.1') return value;
		}
		#end
		return FALLBACK_VERSION;
	}
}
