package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

/** Resolves a selected Codename mod asset first, then the engine installation's
	assets root.  The fallback is deliberately an assets/ directory, never a
	sibling mod or arbitrary parent path. */
class CodenameInstallationAssetOverlay {
	public static function resolve(ownerRoot:String, installationAssetRoot:String,
		relative:String):{source:Null<String>, relative:String, status:String, origin:String} {
		#if sys
		if (ownerRoot == null || !FileSystem.isDirectory(ownerRoot)
			|| !CodenameScriptDiscovery.safeRelativeName(relative))
			return result(null, relative, 'unsafe', 'none');

		var owner = CodenameScriptDiscovery.scopedResolution(ownerRoot, relative);
		if (owner.relative != null)
			return result(Path.join([ownerRoot, owner.relative]), relative, 'ok', 'owner');
		if (owner.status != 'missing') return result(null, relative, owner.status, 'owner');

		if (!isInstallationAssetsRootForOwner(ownerRoot, installationAssetRoot)
			|| Path.normalize(FileSystem.fullPath(installationAssetRoot))
				== Path.normalize(FileSystem.fullPath(ownerRoot)))
			return result(null, relative, 'missing', 'installation');

		var installed = CodenameScriptDiscovery.scopedResolution(installationAssetRoot, relative);
		if (installed.relative != null)
			return result(Path.join([installationAssetRoot, installed.relative]), relative, 'ok', 'installation');
		return result(null, relative, installed.status, 'installation');
		#else
		return result(null, relative, 'unavailable', 'none');
		#end
	}

	public static function ownsSource(ownerRoot:String, installationAssetRoot:String,
		source:String):Bool {
		#if sys
		if (source == null || !FileSystem.exists(source) || FileSystem.isDirectory(source)) return false;
		if (ownerRoot != null && CodenameScriptDiscovery.withinRoot(ownerRoot, source)) return true;
		return isInstallationAssetsRootForOwner(ownerRoot, installationAssetRoot)
			&& CodenameScriptDiscovery.withinRoot(installationAssetRoot, source);
		#else
		return false;
		#end
	}

	/** Locate the shared assets sibling only for an owner below the structural
	 * <installation>/mods/<name> layout. A standalone folder has no inherited
	 * installation layer. */
	public static function installationAssetsForOwner(ownerRoot:String):String {
		#if sys
		if (ownerRoot == null || !FileSystem.isDirectory(ownerRoot)) return null;
		var modsRoot = Path.directory(ownerRoot);
		if (modsRoot == null || Path.withoutDirectory(Path.normalize(modsRoot)).toLowerCase() != 'mods')
			return null;
		var installationRoot = Path.directory(modsRoot);
		if (installationRoot == null || !FileSystem.isDirectory(installationRoot)
			|| !CodenameScriptDiscovery.withinRoot(installationRoot, ownerRoot)) return null;
		var assetsRoot = Path.join([installationRoot, 'assets']);
		if (!isInstallationAssetsRoot(assetsRoot)
			|| !CodenameScriptDiscovery.withinRoot(installationRoot, assetsRoot)) return null;
		return assetsRoot;
		#else
		return null;
		#end
	}

	public static function isInstallationAssetsRootForOwner(ownerRoot:String,
		installationAssetRoot:String):Bool {
		#if sys
		var expected = installationAssetsForOwner(ownerRoot);
		if (expected == null || !isInstallationAssetsRoot(installationAssetRoot)) return false;
		try return Path.normalize(FileSystem.fullPath(expected))
			== Path.normalize(FileSystem.fullPath(installationAssetRoot))
		catch (_:Dynamic) return false;
		#else
		return false;
		#end
	}

	#if sys
	public static function isInstallationAssetsRoot(root:String):Bool {
		if (root == null || !FileSystem.isDirectory(root)
			|| Path.withoutDirectory(Path.normalize(root)).toLowerCase() != 'assets') return false;
		try return Path.withoutDirectory(Path.normalize(FileSystem.fullPath(root))).toLowerCase() == 'assets'
		catch (_:Dynamic) return false;
	}
	#end

	static function result(source:Null<String>, relative:String, status:String,
		origin:String):{source:Null<String>, relative:String, status:String, origin:String}
		return {source:source, relative:relative, status:status, origin:origin};
}
