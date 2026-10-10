package;

import flixel.FlxG;

/** Native class imports and registry identity, without mounting or switching scenes. */
@:access(flixel.FlxGame)
class RuntimeSmokePsychStateRegistry {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState):Void {
		var old = state.variables;
		var active = FlxG.game._state;
		var other = new MusicBeatState();
		var iris = new SourceIrisBridge(state);
		var lua = new LuaCompatInterp();
		var cleanup = function() {
			FlxG.game._state = active;
			state.variables = old;
			iris.release();lua.variables.clear();other.destroy();
		};
		try {
			state.variables = [];
			PsychStateClassBindings.install(iris.evaluator);
			iris.variables.set('expected', state);
			iris.variables.set('registryGetter', null);
			iris.evaluate('import backend.MusicBeatState; import states.PlayState; if(MusicBeatState.getState()!=expected)throw "native state identity"; MusicBeatState.getVariables().set("__state_probe",42); registryGetter=MusicBeatState.getVariables;', '__state_registry');
			check(state.psychScriptVariables == state.variables && state.psychScriptVariables.get('__state_probe') == 42, 'Native class shares gameplay registry');
			new PsychReflectionBindings(state,lua).install();
			lua.variables.set('expectedRegistry',state.variables);
			lua.execute(new hscript.Parser().parseString('if(callMethodFromClass("backend.MusicBeatState","getVariables",[])!=expectedRegistry)throw "Lua class registry identity";', '__state_class_lua'));
			var replacement:Map<String,Dynamic> = ['__state_probe'=>73];
			state.psychScriptVariables = replacement;
			iris.evaluate('if(registryGetter().get("__state_probe")!=73)throw "replacement map";', '__state_registry_replaced');
			other.variables.set('__state_probe',91);
			FlxG.game._state = other;
			iris.evaluate('if(registryGetter().get("__state_probe")!=91)throw "active state map";', '__state_registry_active');
			FlxG.game._state = active;
			check(MusicBeatState.getVariables() == replacement && other.variables != replacement, 'Restored active state and isolated storage');
			@:privateAccess RuntimeSmokeHarness.emit('psych_state_registry_native_verified', {nativeImports:true,luaClassReflection:true,sharedMap:true,replacement:true,cachedStaticMethod:true,activeStateSelection:true,fullTransition:false});
		} catch(error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
