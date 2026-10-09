package;

/** Captured source IO; one Paths extension array is shared with Stage lookup. */
typedef NightmareVisionScriptContext = {
	var paths:NightmareVisionScriptPaths;
	var read:String->String;
	var requireActive:Void->Void;
	var parent:Void->Dynamic;
	var configure:NightmareVisionScriptInterp->Void;
	var report:(String, String, Dynamic)->Void;
}

class NightmareVisionScriptBindings {
	public static function requireContext(context:Null<NightmareVisionScriptContext>):NightmareVisionScriptContext {
		if (context == null) throw '[nightmare-vision-script] Source construction requires a captured owner';
		context.requireActive();
		return context;
	}
	public static function getPath(path:String, paths:NightmareVisionScriptPaths):String {
		for (extension in paths.scriptExtensions) {
			var file = path + '.' + extension;
			var selected = paths.getPath(file, null, true);
			if (paths.exists(selected)) return selected;
			if (paths.exists(file)) return file;
		}
		return path;
	}
	public static function install(interp:NightmareVisionScriptInterp, context:NightmareVisionScriptContext):Void {
		var scope = interp.sourceClassScope();
		var current = interp.variables.get('script');
		if (Std.isOfType(current, NightmareVisionScriptModule)) {
			var module:NightmareVisionScriptModule = cast current;
			if (!module.historicalCalls) module.bindSourceInstances(context.paths.scriptInstances);
		}
		interp.variables.set('FunkinScript', NightmareVisionScriptModule);
		interp.bindImport('funkin.scripts.FunkinScript', NightmareVisionScriptModule);
		scope.bindRuntimeClass('funkin.scripts.FunkinScript', NightmareVisionScriptModule);
		interp.variables.set('ScriptGroup', NightmareVisionScriptGroup);
		interp.bindImport('funkin.scripts.ScriptGroup', NightmareVisionScriptGroup);
		scope.bindRuntimeClass('funkin.scripts.ScriptGroup', NightmareVisionScriptGroup);
		interp.bindConstructorFactory(NightmareVisionScriptGroup, function(args) {
			var parent = args.length > 0 ? args[0] : null;
			#if flixel
			if (parent == null && flixel.FlxG.game != null) parent = flixel.FlxG.state;
			#end
			return new NightmareVisionScriptGroup(parent);
		}, null);

		scope.bindStaticField(NightmareVisionScriptModule, 'H_EXTS', function() return context.paths.scriptExtensions);
		var getPath = function(path:String) return NightmareVisionScriptModule.getPath(path, context);
		var isHxFile = function(path:String) return NightmareVisionScriptModule.isHxFile(path, context);
		var fromString = function(code:String, ?name:String = 'Script', autoExecute:Bool = true,
			?shared:Map<String, Dynamic>, ?modFolder:String) {
			return NightmareVisionScriptModule.fromString(code, name, autoExecute, shared, modFolder, context);
		};
		var fromFile = function(path:String, ?name:String, autoExecute:Bool = true,
			?shared:Map<String, Dynamic>, ?modFolder:String) {
			return NightmareVisionScriptModule.fromFile(path, name, autoExecute, shared, modFolder, context);
		};
		scope.bindStaticField(NightmareVisionScriptModule, 'getPath', function() return getPath);
		scope.bindStaticField(NightmareVisionScriptModule, 'isHxFile', function() return isHxFile);
		scope.bindStaticField(NightmareVisionScriptModule, 'fromString', function() return fromString);
		scope.bindStaticField(NightmareVisionScriptModule, 'fromFile', function() return fromFile);
		interp.bindConstructorFactory(NightmareVisionScriptModule, function(args) return fromString(
			args[0], args.length > 1 ? args[1] : 'Script', args.length > 2 ? args[2] : true,
			args.length > 3 ? args[3] : null, args.length > 4 ? args[4] : null), null);
	}
}
