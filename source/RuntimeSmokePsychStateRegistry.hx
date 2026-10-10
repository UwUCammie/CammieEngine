package;

import flixel.FlxG;

/** Native class imports and registry identity, without mounting or switching scenes. */
@:access(flixel.FlxGame)
@:access(PlayState)
class RuntimeSmokePsychStateRegistry {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState):Void {
		var old = state.variables;
		var oldLegacy = state.nightmareVisionLegacyFieldCameras;
		var oldInstance = PlayState.instance;
		var active = FlxG.game._state;
		var other = new MusicBeatState();
		var iris = new SourceIrisBridge(state);
		var lua = new LuaCompatInterp();
		var cleanup = function() {
			FlxG.game._state = active;
			state.variables = old;
			state.nightmareVisionLegacyFieldCameras = oldLegacy;PlayState.instance = oldInstance;
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
			state.nightmareVisionLegacyFieldCameras = false;
			new PsychSourceBindings(state).install(lua);
			new PsychHscriptSourceBindings(state,iris,'__live_variables',null).install();
			var nv:Dynamic = {variables:new Map<String,Dynamic>()};
			NightmareVisionSourceBindings.bindGameplay(nv,state,true,[],function(_) return null,function() return PlayState.instance.variables);
			other.variables.set('__state_probe',91);
			FlxG.game._state = other;
			iris.evaluate('if(registryGetter().get("__state_probe")!=91)throw "active state map";', '__state_registry_active');
			lua.execute(new hscript.Parser().parseString('if(setVar("luaLater",12)!=12||getVar("luaLater")!=12)throw "Lua live map";', '__live_lua_vars'));
			iris.evaluate('if(setVar("hsLater",14)!=14||getVar("luaLater")!=12||!removeVar("hsLater")||removeVar("missing"))throw "HScript live map";', '__live_hscript_vars');
			check(other.variables.get('luaLater') == 12 && !replacement.exists('luaLater') && !other.variables.exists('hsLater'), 'Psych callbacks follow active base state');
			var nvVars:Map<String,Dynamic> = nv.variables;
			Reflect.callMethod(null,nvVars.get('setVar'),['nvBefore',3]);
			check(replacement.get('nvBefore') == 3 && !other.variables.exists('nvBefore'), 'NV follows PlayState rather than active base state');
			var later:PlayState = Type.createEmptyInstance(PlayState);later.variables = [];
			PlayState.instance = later;
			check(Reflect.callMethod(null,nvVars.get('setVar'),['nvLater',5]) == null, 'NV setter remains void');
			check(Reflect.callMethod(null,nvVars.get('getVar'),['nvLater']) == 5 && later.variables.get('nvLater') == 5 && nvVars.get('global') == replacement, 'NV live singleton with captured global alias');
			PlayState.instance = oldInstance;
			state.nightmareVisionLegacyFieldCameras = true;
			lua.execute(new hscript.Parser().parseString('setVar("legacyOwner",7);', '__legacy_variable_owner'));
			check(replacement.get('legacyOwner') == 7 && !other.variables.exists('legacyOwner'), 'Historical owner isolation');
			FlxG.game._state = active;
			@:privateAccess RuntimeSmokeHarness.emit('source_live_variables_native_verified',{psychActiveState:true,nvPlayState:true,nvCapturedGlobal:true,nvVoidReturn:true,hscriptRemove:true,legacyOwner:true,fullTransition:false});
			check(MusicBeatState.getVariables() == replacement && other.variables != replacement, 'Restored active state and isolated storage');
			@:privateAccess RuntimeSmokeHarness.emit('psych_state_registry_native_verified', {nativeImports:true,luaClassReflection:true,sharedMap:true,replacement:true,cachedStaticMethod:true,activeStateSelection:true,fullTransition:false});
		} catch(error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
