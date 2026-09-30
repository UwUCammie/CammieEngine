package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

using StringTools;

typedef CodenameSoundAssetResolution = {
	var source:Null<String>;
	var relative:String;
	var status:String;
	var origin:String;
}

/** Resolves Codename script sounds without borrowing a different mod owner.
	The only fallback is the selected mod's own installation-level assets/sounds.
*/
class CodenameInstallationSoundAssets {
	#if sys
	public static function resolve(ownerRoot:String, key:String,
		?installationAssetRoot:String):CodenameSoundAssetResolution {
		var clean = key == null ? '' : StringTools.replace(StringTools.trim(key), '\\', '/');
		if (ownerRoot == null || !FileSystem.isDirectory(ownerRoot) || !safeKey(clean))
			return result(null, '', 'unsafe', 'none');

		var extensions = ['.ogg', '.wav', '.mp3'];
		for (extension in extensions)
			if (clean.toLowerCase().endsWith(extension)) {
				extensions = [clean.substr(clean.length - extension.length)];
				clean = clean.substr(0, clean.length - extension.length);
				break;
			}
		if (clean == '') return result(null, '', 'unsafe', 'none');

		// CodenamePaths checks every supported extension inside the selected owner
		// before it can return a sound. Preserve that precedence before considering
		// the installation fallback, or a base OGG could shadow an owner WAV.
		for (extension in extensions) {
			var authoredRelative = 'sounds/' + clean + extension;
			var owner = CodenameScriptDiscovery.scopedResolution(ownerRoot, authoredRelative);
			if (owner.relative != null)
				return result(Path.join([ownerRoot, owner.relative]), authoredRelative, 'ok', 'owner');
			if (owner.status != 'missing')
				return result(null, authoredRelative, owner.status, 'owner');
		}

		var assetsRoot = installationAssetRoot;
		if (!CodenameInstallationAssetOverlay.isInstallationAssetsRootForOwner(ownerRoot, assetsRoot)) {
			assetsRoot = CodenameInstallationAssetOverlay.installationAssetsForOwner(ownerRoot);
			if (assetsRoot == null)
				return result(null, 'sounds/' + clean, 'unsupported-layout', 'none');
		}

		for (extension in extensions) {
			var authoredRelative = 'sounds/' + clean + extension;
			var installed = CodenameScriptDiscovery.scopedResolution(assetsRoot, authoredRelative);
			if (installed.relative != null)
				return result(Path.join([assetsRoot, installed.relative]), authoredRelative, 'ok', 'installation');
			if (installed.status != 'missing')
				return result(null, authoredRelative, installed.status, 'installation');
		}
		return result(null, 'sounds/' + clean, 'missing', 'installation');
	}

	static function safeKey(value:String):Bool {
		if (value == null || value == '' || value.startsWith('/') || value.indexOf(':') >= 0)
			return false;
		for (part in value.split('/'))
			if (part == '' || part == '.' || part == '..') return false;
		return true;
	}
	#else
	public static function resolve(ownerRoot:String, key:String):CodenameSoundAssetResolution
		return result(null, '', 'unavailable', 'none');
	#end

	static function result(source:Null<String>, relative:String, status:String, origin:String):CodenameSoundAssetResolution
		return {source:source, relative:relative, status:status, origin:origin};
}
