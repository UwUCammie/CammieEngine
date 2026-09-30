package;

import haxe.io.Path;
#if sys
import openfl.text.Font;
import sys.FileSystem;
#end

using StringTools;

/** Resolve and register fonts from the manifest root which owns one HXC script. */
class HxcOwnerFont {
	#if sys
	static var registeredFamilies:Map<String, String> = new Map();
	static var reportedDiagnostics:Map<String, Bool> = new Map();
	#end

	/** Return the registered family for an owner-local font key, or null. */
	public static function family(root:String, key:String, ?nativeFallback:String):String {
		#if sys
		var cleanRoot = normalizeRoot(root);
		if (cleanRoot == '' || cleanRoot == 'assets')
			return null;

		var cleanKey = normalizeKey(key);
		if (cleanKey == '') {
			reportOnce('[hxc-font-asset-reject] Invalid owner font key: ' + Std.string(key));
			return null;
		}

		var candidate = Path.normalize(Path.join([cleanRoot, 'fonts', cleanKey]));
		if (!FileSystem.exists(candidate) || FileSystem.isDirectory(candidate)) {
			// A native/shared font is a valid source fallback. Only report an
			// unresolved dependency when neither owner nor native tree has it.
			if (nativeFallback == null || !FileSystem.exists(nativeFallback)
				|| FileSystem.isDirectory(nativeFallback))
				reportOnce('[hxc-font-asset-missing] Owner ' + cleanRoot + ' has no fonts/' + cleanKey);
			return null;
		}

		var fullRoot:String;
		var fullCandidate:String;
		try {
			fullRoot = Path.normalize(StringTools.replace(FileSystem.fullPath(cleanRoot), '\\', '/'));
			fullCandidate = Path.normalize(StringTools.replace(FileSystem.fullPath(candidate), '\\', '/'));
		} catch (error:Dynamic) {
			reportOnce('[hxc-font-asset-error] Could not resolve owner font ' + candidate + ': ' + Std.string(error));
			return null;
		}

		var fontsRoot = fullRoot.endsWith('/') ? fullRoot + 'fonts/' : fullRoot + '/fonts/';
		if (!fullCandidate.startsWith(fontsRoot)) {
			reportOnce('[hxc-font-asset-reject] Owner font escaped its fonts directory: ' + candidate);
			return null;
		}

		var cacheKey = fullCandidate;
		if (registeredFamilies.exists(cacheKey))
			return registeredFamilies.get(cacheKey);

		var font:Font = null;
		try font = Font.fromFile(fullCandidate) catch (error:Dynamic) {
			reportOnce('[hxc-font-asset-error] Could not load owner font ' + candidate + ': ' + Std.string(error));
			return null;
		}
		if (font == null || font.fontName == null || StringTools.trim(font.fontName) == '') {
			reportOnce('[hxc-font-asset-error] Owner font has no registered family: ' + candidate);
			return null;
		}
		try Font.registerFont(font) catch (error:Dynamic) {
			reportOnce('[hxc-font-asset-error] Could not register owner font ' + candidate + ': ' + Std.string(error));
			return null;
		}

		registeredFamilies.set(cacheKey, font.fontName);
		return font.fontName;
		#else
		return null;
		#end
	}

	#if sys
	static function normalizeRoot(root:String):String {
		if (root == null || StringTools.trim(root) == '')
			return '';
		var clean = StringTools.replace(StringTools.trim(root), '\\', '/');
		if (clean.indexOf('\u0000') >= 0 || clean.indexOf(':') >= 0)
			return '';
		return Path.normalize(clean);
	}

	static function normalizeKey(key:String):String {
		if (key == null)
			return '';
		var clean = StringTools.replace(StringTools.trim(key), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean.toLowerCase().startsWith('assets/fonts/'))
			clean = clean.substr('assets/fonts/'.length);
		else if (clean.toLowerCase().startsWith('fonts/'))
			clean = clean.substr('fonts/'.length);
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0 || clean.indexOf('\u0000') >= 0)
			return '';
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..')
				return '';
		return clean;
	}

	static function reportOnce(message:String):Void {
		if (message == null || reportedDiagnostics.exists(message))
			return;
		reportedDiagnostics.set(message, true);
		trace(message);
	}
	#end
}
