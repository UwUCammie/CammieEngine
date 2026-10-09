package;

/** Muted native verification of historical map identity and loader ordering. */
@:access(PlayState)
class RuntimeSmokeLegacyEventMap {
	public static function verify():Void {
		#if sys
		if (Sys.getEnv('CAMMIE_LEGACY_EVENT_MAP_SMOKE') != '1') return;
		var state = PlayState.instance;
		if (!state.nightmareVisionLegacyFieldCameras) throw 'Historical event map profile unavailable';
		if (state.legacyScriptRegistry().eventPushedMap != null) throw 'Historical discovery map was not released after generation';
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
			verifyPreparation(state, registry, api);
			verifyQueue(state, registry, api);
			@:privateAccess RuntimeSmokeHarness.emit('legacy_event_map_native_verified',{sourceProfile:true,authoredNamePreserved:true,constructorBeforeMap:true,onLoadBeforeArrays:true,liveAliases:true,reflectedReplacement:true,unplannedAlias:true,removedEntryStaysRemoved:true,sharedModule:true});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
		#end
	}
	static function verifyPreparation(state:PlayState, registry:NightmareVisionLegacyScriptRegistry, api:NightmareVisionScriptInterp):Void {
		var handle = NightmareVisionScriptModule.fromSource('__event_prepare',
			'var first = null; var kept = null; function shouldPush(e){e.value2="admitted";return e.value1 != "reject";} function firstPush(e){first=e;e.value1="first-only";} function getOffset(e){return 0;} function onPush(e){kept=e;e.value2="pushed";}',
			state, null, function(i) {var module:NightmareVisionScriptModule=cast i.variables.get('script');module.historicalCalls=true;}, function(n,c,e) throw e);
		registry.eventScripts = ['E'=>handle];
		var rows:Array<Dynamic> = [];var views:Array<SourceEventNote> = [];var loads = 0;
		var oldSong = PlayState.SONG;
		try {
			NightmareVisionLegacyEventPreparation.prepare(function(visit) {for(v in ['keep','reject','keep']) visit({time:100.,name:'E',v1:v,v2:null,order:0});},
				function() return 5., function() return registry.eventScripts, registry.callScript,
				function(n,a) return 30., function(n) loads++, function(r,e) {rows.push(r);views.push(e);}, function(e) return false);
			var first:SourceEventNote = cast handle.get('first');var kept:SourceEventNote = cast handle.get('kept');
			if (loads != 1 || rows.length != 2 || views[0].strumTime != 105 || views[0].value1 != 'keep'
				|| views[0].value2 != 'pushed' || first == views[0] || kept != views[1]) throw 'Native historical event preparation';
			kept.value2 = 'retained';rows[1].time = 23.;
			if (rows[1].v2 != 'retained' || kept.strumTime != 23) throw 'Native historical event view identity';
			PlayState.SONG = cast Reflect.copy(oldSong);
			PlayState.SONG.events = [[100., [['E','keep',null], ['E','reject',null]]]];
			api.variables.set('__eventExpectedTime', 100. + state.sourceChartNoteOffset());
			api.execute(new NightmareVisionScriptParser().parseString('var a=getEvents();var b=game.getEvents();var matches=[];for(e in a)if(e.event=="E")matches.push(e);if(matches.length!=1||matches[0].strumTime!=__eventExpectedTime||matches[0].value2!="admitted")throw "native getEvents";var raw={strumTime:100,event:"E",value1:"keep",value2:null};if(!shouldPush(raw)||raw.value2!="admitted")throw "native shouldPush";if(PlayState.eventNoteEarlyTrigger(raw)!=0)throw "native early offset";Reflect.callMethod(game,Reflect.field(game,"firstEventPush"),[raw]);if(raw.value1!="first-only")throw "native firstPush";', '__event_public_api'));
			PlayState.SONG = oldSong;
			@:privateAccess RuntimeSmokeHarness.emit('legacy_event_public_api_native_verified', {sourceBindings:true,plainObjects:true,getEvents:true,shouldPush:true,firstPush:true,earlyTrigger:true});
			@:privateAccess RuntimeSmokeHarness.emit('legacy_event_preparation_native_verified', {admission:true,freshPasses:true,zeroOffsetOverridesGlobal:true,duplicates:true,retainedIdentity:true});
		} catch(error:Dynamic) {PlayState.SONG = oldSong;handle.destroy();throw error;}
		handle.destroy();
	}

	static function verifyQueue(state:PlayState, registry:NightmareVisionLegacyScriptRegistry, api:NightmareVisionScriptInterp):Void {
		var oldIndex = state.songEventIndex;
		var seen:Array<String> = [];
		var handle = NightmareVisionScriptModule.fromSource('E',
			'function onTrigger(a,b){record(a+":"+b);if(a=="first")registry.eventNotes=[{strumTime:-1000,event:"E",value1:"skipped",value2:null},{strumTime:-1000,event:"E",value1:"second",value2:null}];}',
			state, null, function(i) {var module:NightmareVisionScriptModule=cast i.variables.get('script');module.historicalCalls=true;i.variables.set('registry',registry);i.variables.set('record',function(value:String)seen.push(value));}, function(n,c,e) throw e);
		registry.eventScripts = ['E'=>handle];
		try {
			api.execute(new NightmareVisionScriptParser().parseString('eventNotes=[{strumTime:-1000,event:"E",value1:"first",value2:null},{strumTime:-1000,event:"E",value1:"old-tail",value2:null}];var originalQueue=eventNotes;if(eventNotes!=game.eventNotes||eventNotes!=PlayState.eventNotes||eventNotes!=Reflect.getProperty(game,"eventNotes"))throw "native queue identity";checkEventNote();if(eventNotes.length!=0||originalQueue.length!=2)throw "native queue replacement";', '__event_queue_api'));
			if (seen.join(',') != 'first:,second:' || state.songEventIndex != oldIndex + 2) throw 'Native historical queue shift order';
			@:privateAccess RuntimeSmokeHarness.emit('legacy_event_queue_native_verified', {liveAliases:true,callbackReplacement:true,postCallbackShift:true,nullValues:true,sharedEventDispatch:true,discoveryReleased:true});
		} catch(error:Dynamic) {state.songEventIndex=oldIndex;handle.destroy();throw error;}
		state.songEventIndex=oldIndex;handle.destroy();
	}

}
