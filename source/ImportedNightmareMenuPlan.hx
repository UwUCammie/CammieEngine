package;

/** Validate NV's explicit stateRedirects registration, without materializing a
 * native menu or selecting an arbitrary compiled donor class. */
@:access(NightmareVisionModsContext)
class ImportedNightmareMenuPlan {
	public static function find(root:String, directory:String):{state:String, diagnostic:String} {
		#if sys
		if (directory == null || directory == '') return {state:'', diagnostic:''};
		try {
			var metadataPath = root + '/meta.json';
			if (!ImportFileSystem.exists(metadataPath)) return {state:'', diagnostic:''};
			if (ImportFileSystem.stat(metadataPath).size > 262144) throw 'meta.json exceeds menu limit';
			var metadata = NightmareVisionModsContext.parseModConfigJson5(ImportFile.getContent(metadataPath));
			var redirects:Dynamic = metadata == null ? null : Reflect.field(metadata, 'stateRedirects');
			var main:Dynamic = redirects == null ? null : Reflect.field(redirects, 'MainMenuState');
			if (main == null) return {state:'', diagnostic:''};
			var failure = validate(root, main);
			if (failure != '') return {state:'', diagnostic:failure};
			var title:Dynamic = Reflect.field(redirects, 'TitleState');
			if (title != null) {
				failure = validate(root, title);
				if (failure != '') return {state:'', diagnostic:failure};
			}
			return {state:title == null ? 'MainMenuState' : 'TitleState', diagnostic:''};
		} catch (error:Dynamic) return {state:'', diagnostic:'[imported-menu-entry] ' + root + ': ' + Std.string(error)};
		#end
		return {state:'', diagnostic:''};
	}

	static function validate(root:String, name:Dynamic):String {
		#if sys
		if (!Std.isOfType(name, String) || name == '' || !CodenameScriptDiscovery.safeRelativeName(name))
			return '[imported-menu-entry] Invalid NV stateRedirects entry under ' + root;
		var base = root + '/scripts/states/' + Std.string(name);
		var found:Array<String> = [];
		for (extension in ['.hx', '.hxs', '.hscript']) {
			var path = base + extension;
			if (ImportFileSystem.exists(path) && !ImportFileSystem.isDirectory(path)) found.push(path);
		}
		if (found.length != 1) return '[imported-menu-entry] NV menu ' + base + ' has ' + found.length + ' matching scripts; use default Freeplay';
		#end
		return '';
	}
}
