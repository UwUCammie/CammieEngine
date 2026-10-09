package;

/** Source arrays and default methods share the existing live/reflection bindings. */
class NightmareVisionLegacyRegistryBindings {
	public static function install(interp:NightmareVisionScriptInterp, state:Dynamic, stateClass:Dynamic,
		registry:NightmareVisionLegacyScriptRegistry):Void {
		for (name in ['funkyScripts','hscriptArray','luaArray']) {
			var read = function():Dynamic return Reflect.getProperty(registry, name);
			var write = function(value:Dynamic):Dynamic {Reflect.setProperty(registry, name, value);return value;};
			interp.bindLiveValue(name, read, write, function() return state);
			interp.sourceClassScope().bindStaticField(state, name, read, write);
			interp.sourceClassScope().bindStaticField(stateClass, name, read, write);
		}
		for (entry in [{name:'callOnScripts', fn:cast registry.callOnScripts}, {name:'callOnHScripts', fn:cast registry.callOnHScripts},
			{name:'callOnLuas', fn:cast registry.callOnLuas}, {name:'setOnScripts', fn:cast registry.setOnScripts}, {name:'callScript', fn:cast registry.callScript}]) {
			var read = function():Dynamic return entry.fn;
			interp.bindLiveValue(entry.name, read, null, function() return state);
			interp.sourceClassScope().bindStaticField(state, entry.name, read);
			interp.sourceClassScope().bindStaticField(stateClass, entry.name, read);
		}
	}
}
