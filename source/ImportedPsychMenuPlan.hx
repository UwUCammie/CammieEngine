package;

import haxe.io.Path;
#if sys
import ImportFileSystem as FileSystem;
import ImportFile as File;
#end

/** Supported source-state menus use the shared class-to-lifecycle lowering.
 * Unsupported compiled source is retained and explicitly offered Freeplay. */
class ImportedPsychMenuPlan {
	public static function find(root:String):{state:String, sources:Array<String>, diagnostic:String} {
		var sources:Array<String> = [];
		#if sys
		for (folder in ['scripts/states', 'source/states', 'states']) collect(root + '/' + folder, sources, 0);
		if (sources.length >= 512) return {state:'', sources:[], diagnostic:'[imported-menu-entry] Menu source scan limit reached under ' + root + '; use default Freeplay'};
		var names:Map<String, String> = new Map();
		for (path in sources) {
			var name = Path.withoutExtension(Path.withoutDirectory(path));
			if (!['TitleState', 'MainMenuState', 'FreeplayState'].contains(name)) continue;
			if (names.exists(name)) return {state:'', sources:[], diagnostic:'[imported-menu-entry] Ambiguous ' + name + ': ' + names.get(name) + ', ' + path};
			names.set(name, path);
		}
		if (!names.exists('MainMenuState')) return {state:'', sources:[], diagnostic:''};
		var selected:Array<String> = [];
		for (name in names.keys()) {
			var path = names.get(name);
			try {
				if (FileSystem.stat(path).size > 262144) throw 'source exceeds menu limit';
				var adapted = HxcCompat.analyze(File.getContent(path), path);
				var missing = unsupportedCalls(adapted.generatedHscript);
				if (missing != '') throw 'unsupported menu call ' + missing;
				if (adapted.kind != 'state' || adapted.generatedHscript == '') throw 'unsupported source-state contract';
				for (callback in adapted.callbackAdapters) if (!callback.safe) throw 'unsupported callback ' + callback.sourceName;
				for (diagnostic in adapted.diagnostics) if (diagnostic.severity == 'warning' || diagnostic.severity == 'error') throw diagnostic.message;
				selected.push(path);
			} catch (error:Dynamic) return {state:'', sources:[], diagnostic:'[imported-menu-entry] ' + path + ': ' + Std.string(error) + '; use default Freeplay'};
		}
		return {state:names.exists('TitleState') ? 'TitleState' : 'MainMenuState', sources:selected, diagnostic:''};
		#end
		return {state:'', sources:[], diagnostic:''};
	}
	static function unsupportedCalls(program:String):String {
		program = HxcScriptIdentity.structuralText(program);
		var allowed = ['if', 'for', 'while', 'switch', 'catch', 'function',
			'add', 'remove', 'insert', 'addSprite', 'removeSprite', 'debugPrint', 'trace',
			'soundPlaySafe', 'preloadSound', 'openSubState', 'closeSubState', 'close',
			'hxcStateInit', 'hxcStateFactory', 'hxcSwitchState', 'hxcStartExitState',
			'hxcOpenSubState', 'hxcOpenSubStateOn', 'hxcBack', 'hxcResetState', 'hxcGetModule',
			'TitleState', 'MainMenuState', 'FreeplayState', 'PlayState', 'FlxSprite', 'FlxText', 'FlxObject', 'FlxGroup', 'FlxTypedGroup', 'FlxTimer', 'FlxSound'];
		var functions = new EReg('function[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*\\(', 'g');
		var remainder = program;
		while (functions.match(remainder)) {
			allowed.push(functions.matched(1)); remainder = functions.matchedRight();
		}
		var calls = new EReg('(^|[^A-Za-z0-9_.$])([A-Za-z_][A-Za-z0-9_]*)[ \t]*\\(', 'g');
		remainder = program;
		while (calls.match(remainder)) {
			var name = calls.matched(2);
			if (!allowed.contains(name)) return name;
			remainder = calls.matchedRight();
		}
		return '';
	}
	#if sys
	static function collect(folder:String, paths:Array<String>, depth:Int):Void {
		if (depth > 8 || paths.length >= 512 || !FileSystem.exists(folder) || !FileSystem.isDirectory(folder)) return;
		for (name in FileSystem.readDirectory(folder)) {
			if (!CodenameScriptDiscovery.safeName(name)) continue;
			var path = folder + '/' + name;
			if (FileSystem.isDirectory(path)) collect(path, paths, depth + 1);
			else if (StringTools.endsWith(name.toLowerCase(), '.hx') || StringTools.endsWith(name.toLowerCase(), '.hxc')) paths.push(path);
			if (paths.length >= 512) break;
		}
	}
	#end
}
