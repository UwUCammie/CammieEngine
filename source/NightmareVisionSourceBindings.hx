package;

import flixel.input.keyboard.FlxKey;

/** Missing, genuinely source-shaped pieces of FunkinScript.preset(). Keep
 * owner bindings stable and pass per-song fields only to bindGameplay(). */
@:keep
class NightmareVisionSourceBindings {
	public static inline var SOURCE_VERSION:String = '1.0';
	static inline var ASSET_REDIRECT:Bool = #if ASSET_REDIRECT true #else false #end;

	static final gameplayNames:Array<String> = [
		'bpm', 'scrollSpeed', 'songName', 'isStoryMode', 'difficulty', 'weekRaw',
		'seenCutscene', 'week', 'difficultyName', 'songLength', 'healthGainMult',
		'healthLossMult', 'instakillOnMiss', 'botPlay', 'practice',
		'startedCountdown', 'mustHitSection'
	];

	/** Install source globals that remain valid for every script under this
	 * selected import. `scriptContext` is optional because the donor's `script`
	 * points at its full FunkinScript object; a bare interpreter is not a
	 * compatible substitute. */
	public static function bindOwner(interp:Dynamic, ownerRoot:String, modFolder:String,
		?scriptContext:Dynamic):NightmareVisionSourceOptions {
		var vars = variablesOf(interp);
		if (ownerRoot == null || !StringTools.startsWith(StringTools.replace(ownerRoot, '\\', '/'), 'assets/imported_mods/'))
			throw '[nightmare-vision-bindings] Invalid selected owner root';
		if (modFolder != null) set(vars, 'modFolder', modFolder);
		set(vars, 'version', SOURCE_VERSION);
		set(vars, 'asset_redirect', ASSET_REDIRECT);
		set(vars, 'Main', {NMV_VERSION:SOURCE_VERSION});
		var keyFacade = CodenameFlxKeyFacade.snapshot();
		set(vars, 'FlxKey', keyFacade);
		set(vars, 'keyToString', function(key:Int):Null<String> return FlxKey.toStringMap.get(cast key));
		set(vars, 'keyFromString', function(name:String):Null<Int> {
			var key = name == null ? null : FlxKey.fromStringMap.get(name);
			return key == null ? null : cast key;
		});
		set(vars, 'Random', NightmareVisionSourceRandom);
		if (scriptContext != null) set(vars, 'script', scriptContext);

		var saveFacade:Dynamic = Reflect.field(interp, 'ownerSave');
		var saveData:Dynamic = saveFacade == null ? null : Reflect.field(saveFacade, 'data');
		var options = new NightmareVisionSourceOptions(ownerRoot, saveData);
		set(vars, 'newOption', function(key:String, type:String = 'string',
			defaultValue:Dynamic = 'null', ?settings:Dynamic):Void
			options.add(key, type, defaultValue, settings));
		set(vars, 'getOption', function(key:String):Dynamic return options.getValue(key));
		bindImport(interp, 'flixel.input.keyboard.FlxKey', keyFacade);
		bindImport(interp, 'funkin.scripts.ScriptClasses.ScriptedFlxRandom', NightmareVisionSourceRandom);
		return options;
	}

	/** Install the source's per-PlayState globals and variable helpers. The
	 * `fields` map is a snapshot computed by the active gameplay host; the loader
	 * must be its owner-scoped dynamic script loader and is exposed with the
	 * donor's Void return contract. */
	public static function bindGameplay(interp:Dynamic, state:Dynamic, inPlaystate:Bool,
		fields:Map<String, Dynamic>, initScript:String->Dynamic):Void {
		var vars = variablesOf(interp);
		set(vars, 'inGameOver', false);
		set(vars, 'game', state);
		set(vars, 'inPlaystate', inPlaystate);
		if (!inPlaystate) return;
		if (state == null) throw '[nightmare-vision-bindings] Gameplay globals require the live PlayState';
		for (name in gameplayNames) if (fields != null && fields.exists(name)) set(vars, name, fields.get(name));

		// PlayState exposes this as `variables(get, never)`, so Reflect.field
		// misses the live map even though normal property access sees it.
		var stateVariables:Dynamic = Reflect.getProperty(state, 'variables');
		if (stateVariables == null)
			throw '[nightmare-vision-bindings] Live PlayState has no source variable map';
		set(vars, 'global', stateVariables);
		set(vars, 'setVar', function(name:String, value:Dynamic):Void setMapValue(stateVariables, name, value));
		set(vars, 'getVar', function(name:String):Dynamic return getMapValue(stateVariables, name));

		var constants:Dynamic = get(vars, 'ScriptConstants');
		var getInstance:Dynamic = constants == null ? null : Reflect.field(constants, 'getInstance');
		if (getInstance != null)
			set(vars, 'getInstance', function():Dynamic return Reflect.callMethod(constants, getInstance, []));
		if (initScript == null)
			throw '[nightmare-vision-bindings] Gameplay globals require the owner-scoped initScript loader';
		set(vars, 'initScript', function(path:String):Void initScript(path));
	}

	static function variablesOf(interp:Dynamic):Map<String, Dynamic> {
		var vars:Map<String, Dynamic> = interp == null ? null : cast Reflect.field(interp, 'variables');
		if (vars == null) throw '[nightmare-vision-bindings] Interpreter variables are unavailable';
		return vars;
	}

	static function set(vars:Map<String, Dynamic>, name:String, value:Dynamic):Void vars.set(name, value);

	static function get(vars:Map<String, Dynamic>, name:String):Dynamic return vars.get(name);

	static function setMapValue(values:Dynamic, name:String, value:Dynamic):Void {
		if (values != null) (cast values:Map<String, Dynamic>).set(name, value);
	}

	static function getMapValue(values:Dynamic, name:String):Dynamic {
		return values == null ? null : (cast values:Map<String, Dynamic>).get(name);
	}

	static function bindImport(interp:Dynamic, path:String, value:Dynamic):Void {
		var binder:Dynamic = interp == null ? null : Reflect.field(interp, 'bindImport');
		if (binder != null) Reflect.callMethod(interp, binder, [path, value]);
	}
}
