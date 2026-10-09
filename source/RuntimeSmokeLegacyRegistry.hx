package;

/** Opt-in native registry checks with complete restoration of the gameplay owner. */
@:access(PlayState)
class RuntimeSmokeLegacyRegistry {
	public static function isolate(state:PlayState):Void->Void {
		var scripts = state.scripts;
		var registry = state.nightmareVisionLegacyRegistry;
		var handles = state.nightmareVisionLegacyLuaHandles;
		var events = state.nightmareVisionLegacyLuaEvents;
		var types = state.nightmareVisionLegacyLuaTypes;
		var historical = state.nightmareVisionLegacyFieldCameras;
		state.nightmareVisionLegacyFieldCameras = false;state.scripts = null;
		state.nightmareVisionLegacyFieldCameras = historical;
		state.nightmareVisionLegacyRegistry = null;
		state.nightmareVisionLegacyLuaHandles = new haxe.ds.ObjectMap();
		state.nightmareVisionLegacyLuaEvents = [];state.nightmareVisionLegacyLuaTypes = [];
		return function() {
			state.nightmareVisionLegacyFieldCameras = false;state.scripts = scripts;
			state.nightmareVisionLegacyFieldCameras = historical;
			state.nightmareVisionLegacyRegistry = registry;
			state.nightmareVisionLegacyLuaHandles = handles;
			state.nightmareVisionLegacyLuaEvents = events;state.nightmareVisionLegacyLuaTypes = types;
		};
	}
	public static function verify():Void {
		#if sys
		if (Sys.getEnv('CAMMIE_LEGACY_REGISTRY_SMOKE') != '1') return;
		var state = PlayState.instance;
		if (!state.nightmareVisionLegacyFieldCameras) throw 'Historical registry profile unavailable';
		var reset = isolate(state);
		var oldScopes = state.hscriptStates;state.hscriptStates = [];
		var group = new NightmareVisionScriptGroup(state, function(n,c,e) throw e);state.scripts = group;
		var api:NightmareVisionScriptInterp = null;
		var restore = function() {if (api != null) api.release();group.destroy();state.hscriptStates = oldScopes;reset();};
		try {
			var log:Array<String> = [];var inserted = false;
			var first = group.loadSource('__registry_first','function registryProbe(){record();mutate();return "first";}',function(i) {
				i.variables.set('record',function() log.push('first'));
				i.variables.set('mutate',function() {
					if (inserted) return;inserted = true;
					group.loadSource('__registry_late','function registryProbe(){record();return "late";}',function(j) j.variables.set('record',function() log.push('late')));
				});
			});
			var lua = new LuaCompatInterp();lua.variables.set('__psychScoreGlobals',true);
			lua.variables.set('registryProbe',function():Dynamic {log.push('lua');return 'lua';});
			state.hscriptStates.set('compat_global_registry_probe',lua);
			state.registerHistoricalNightmareLua('compat_global_registry_probe',lua,'__registry.lua');
			api = new NightmareVisionScriptInterp(state);
			state.seedNightmareVision(api,{scope:'song',name:'__registry_api',relative:'__registry_api.hx',path:state.nightmareVisionPaths.root+'/__registry_api.hx'},null);
			var run = function(text:String) api.execute(new NightmareVisionScriptParser().parseString(text,'__registry_api'));
			run('if(funkyScripts!=game.funkyScripts||funkyScripts!=Reflect.getProperty(game,"funkyScripts")||funkyScripts!=PlayState.funkyScripts)throw "registry identity"; if(callOnScripts("registryProbe",[])!="late")throw "native result";');
			if (log.join(',') != 'first,lua,late') throw 'Native callback load order: '+log.join(',');
			api.variables.set('savedRegistry',state.legacyScriptRegistry().funkyScripts);
			run('Reflect.setProperty(game,"funkyScripts",[]);if(funkyScripts.length!=0||savedRegistry.length<3||luaArray.length!=1||hscriptArray.length!=2)throw "independent replacement";game.funkyScripts=savedRegistry;setOnScripts("registryValue",17);');
			if (first.get('registryValue') != 17 || lua.variables.get('registryValue') != 17) throw 'Native shared script setter';
			first.set('mutate',function() group.removeScript(first));log.resize(0);
			run('callOnScripts("registryProbe",[]);');
			if (log.join(',') != 'first,late' || state.legacyScriptRegistry().hscriptArray.length != 1) throw 'Native callback removal order: '+log.join(',');
			first.destroy();
			@:privateAccess RuntimeSmokeHarness.emit('legacy_registry_native_verified',{liveIdentity:true,reflectedReplacement:true,independentFamilies:true,mixedOrder:true,callbackLoad:true,callbackRemoval:true,sharedSetter:true});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
		#end
	}
}
