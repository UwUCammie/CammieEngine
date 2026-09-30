package;

import haxe.io.Path;
using StringTools;

/** Resolve Psych's Paths.font key in the selected import before native fonts. */
class PsychFontPath {
	public static function resolve(font:String, selectedRoot:String):String {
		if (font == null)
			return null;
		var key = font.trim().replace('\\', '/');
		if (key.startsWith('assets/fonts/'))
			key = key.substr('assets/fonts/'.length);
		else if (key.startsWith('fonts/'))
			key = key.substr('fonts/'.length);
		if (key == '' || key.startsWith('/') || key.indexOf(':') >= 0)
			return null;
		for (part in key.split('/'))
			if (part == '' || part == '.' || part == '..')
				return null;
		var root = selectedRoot == null ? '' : selectedRoot.trim().replace('\\', '/');
		if (root != '' && root.startsWith('assets/imported_mods/') && root.indexOf('..') < 0) {
			var scoped = Path.join([root, 'fonts', key]);
			if (FNFAssets.exists(scoped))
				return scoped;
		}
		return 'assets/fonts/' + key;
	}
}
