package;

/** Muted native verification of historical map identity and loader ordering. */
@:access(PlayState)
class RuntimeSmokeLegacyEventMap {
	public static function verify():Void {
		#if sys
		if (Sys.getEnv('CAMMIE_LEGACY_EVENT_MAP_SMOKE') != '1') return;
		var state = PlayState.instance;
		if (!state.nightmareVisionLegacyFieldCameras) throw 'Historical event map profile unavailable';
		var reset = RuntimeSmokeLegacyRegistry.isolate(state);
		var oldBackend = state.nightmareVisionScripts;
		var phases:Array<String> = [];
		var entry:NightmareVisionScriptDiscovery.NightmareVisionScriptEntry = {scope:'event',name:'__native_event_probe',relative:'events/__native_event_probe.hx',path:state.nightmareVisionPaths.root+'/events/__native_event_probe.hx'};
		var instances = state.nightmareVisionPaths.scriptInstances;
		var hadInstance = instances.exists(entry.name);var oldInstance = instances.get(entry.name);
		var sentinel = new NightmareVisionScriptModule(entry.name,new NightmareVisionScriptInterp(),function(n,c,e) throw e);
		instances.set(entry.name,sentinel);
		var backend = new NightmareVisionGameplayScripts(state,{root:state.nightmareVisionPaths.root,baseAssetsRoot:'',song:'probe',stage:'',coverageNotes:[],scripts:[entry]},
			function(path) return 'record("top",eventScripts.exists("__native_event_probe"),funkyScripts.indexOf(script)>=0);function onLoad(n){record("load",eventScripts.get(n)==script,hscriptArray.indexOf(script)>=0);}function onTrigger(a,b){return a+":"+b;}',
			function(i,e,a) {state.seedNightmareVision(i,e,a);i.variables.set('record',function(n:String,m:Bool,r:Bool)phases.push(n+":"+m+":"+r));},
			function(n,c,e) throw e);
		state.scripts = backend.group;state.nightmareVisionScripts = backend;
		backend.legacyEventRegistry = function() return state.legacyScriptRegistry().eventScripts;
		var api:NightmareVisionScriptInterp = null;
		var restore = function() {if (api != null) api.release();backend.destroy();state.nightmareVisionScripts = oldBackend;reset();if (hadInstance) instances.set(entry.name,oldInstance);else instances.remove(entry.name);sentinel.destroy();};
		try {
			if (backend.hasEventCallback(entry.name,'onTrigger') || phases.length != 0) throw 'Native event lookup loaded a module';
			backend.loadScope('event',entry.name);
			if (state.callEventScript(entry.name,'onTrigger',['left','right']) != 'left:right'
				|| phases.join(',') != 'top:false:false,load:true:false') throw 'Native historical event initialization: '+phases.join(',');
			var registry = state.legacyScriptRegistry();var original = registry.eventScripts;
			var module:NightmareVisionScriptModule = cast original.get(entry.name);
			if (module.scriptName != entry.name || instances.get(entry.name) != sentinel) throw 'Historical script name inherited modern uniqueness: '+module.scriptName+' / retained='+Std.string(instances.get(entry.name)==sentinel);
			api = new NightmareVisionScriptInterp(state);state.seedNightmareVision(api,{scope:'song',name:'__event_map_api',relative:'__event_map_api.hx',path:state.nightmareVisionPaths.root+'/__event_map_api.hx'},null);
			var replacement:Map<String,Dynamic> = ['Alias'=>module];api.variables.set('replacementMap',replacement);
			api.execute(new NightmareVisionScriptParser().parseString('if(eventScripts!=game.eventScripts||eventScripts!=PlayState.eventScripts||eventScripts!=Reflect.getProperty(game,"eventScripts"))throw "native map identity";Reflect.setProperty(game,"eventScripts",replacementMap);','__event_map_api'));
			if (registry.eventScripts != replacement || original == replacement || !original.exists(entry.name)
				|| state.callEventScript('Alias','onTrigger',['new','map']) != 'new:map'
				|| state.callEventScript(entry.name,'onTrigger',['old','map']) != 0 || backend.group.members.indexOf(cast module)<0)
				throw 'Native event map replacement/ownership';
			replacement.remove('Alias');
			if (backend.hasEventCallback('Alias','onTrigger') || state.callEventScript('Alias','onTrigger',[]) != 0) throw 'Native removed event was recreated';
			@:privateAccess RuntimeSmokeHarness.emit('legacy_event_map_native_verified',{sourceProfile:true,authoredNamePreserved:true,constructorBeforeMap:true,onLoadBeforeArrays:true,liveAliases:true,reflectedReplacement:true,unplannedAlias:true,removedEntryStaysRemoved:true,sharedModule:true});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
		#end
	}
}
