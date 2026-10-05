package;

/** Opt-in process-local saves for unattended native tests. */
@:access(lime.system.System)
class RuntimeSmokeSaveIsolation {
	public static function install(?importSmoke:Bool = false):Void {
		#if sys
		if (!RuntimeSmokeHarness.enabled() && !importSmoke) return;
		var relative = Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT');
		if (relative == null || relative == '') return;
		// Only an explicit private test directory below this runtime is allowed.
		if (!StringTools.startsWith(relative, 'tmp/') || relative.indexOf('..') >= 0
			|| relative.indexOf('\\') >= 0 || relative.indexOf(':') >= 0)
			throw 'Invalid private smoke save directory';
		var root = haxe.io.Path.join([Sys.getCwd(), relative]);
		sys.FileSystem.createDirectory(root);
		// Flixel 6.1 strips three components from Lime's application directory;
		// OpenFL's legacy location remains under that same private test root.
		lime.system.System.__applicationStorageDirectory = root + '/storage/company/title';
		#end
	}
}
