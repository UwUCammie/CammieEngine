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
			function(path) return sys.FileSystem.exists(path) ? sys.io.File.getContent(path) : 'record("top",eventScripts.exists("__native_event_probe"),funkyScripts.indexOf(script)>=0);function onLoad(n){record("load",eventScripts.get(n)==script,hscriptArray.indexOf(script)>=0);}function onTrigger(a,b){return a+":"+b;}',
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
			verifyNotification(state, registry);
			verifyDiscovery(state, registry, api);
			verifyKillNotes(state, registry, api);
			RuntimeSmokeLegacyCameraEvents.verify(state, registry, api);
		RuntimeSmokeLegacyActorEvents.verify(state, registry);
			@:privateAccess RuntimeSmokeHarness.emit('legacy_event_map_native_verified',{sourceProfile:true,authoredNamePreserved:true,constructorBeforeMap:true,onLoadBeforeArrays:true,liveAliases:true,reflectedReplacement:true,unplannedAlias:true,removedEntryStaysRemoved:true,sharedModule:true});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
		#end
	}
	static function verifyPreparation(state:PlayState, registry:NightmareVisionLegacyScriptRegistry, api:NightmareVisionScriptInterp):Void {
		var oldMain = registry.funkyScripts.copy();
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
		} catch(error:Dynamic) {PlayState.SONG = oldSong;registry.funkyScripts=oldMain;handle.destroy();throw error;}
		registry.funkyScripts=oldMain;handle.destroy();
	}

	static function verifyQueue(state:PlayState, registry:NightmareVisionLegacyScriptRegistry, api:NightmareVisionScriptInterp):Void {
		var oldIndex = state.songEventIndex;
		var oldMain = registry.funkyScripts.copy();
		var seen:Array<String> = [];
		var handle = NightmareVisionScriptModule.fromSource('E',
			'function onTrigger(a,b){record(a+":"+b);if(a=="first")registry.eventNotes=[{strumTime:-1000,event:"E",value1:"skipped",value2:null},{strumTime:-1000,event:"E",value1:"second",value2:null}];}',
			state, null, function(i) {var module:NightmareVisionScriptModule=cast i.variables.get('script');module.historicalCalls=true;i.variables.set('registry',registry);i.variables.set('record',function(value:String)seen.push(value));}, function(n,c,e) throw e);
		registry.eventScripts = ['E'=>handle];
		try {
			api.execute(new NightmareVisionScriptParser().parseString('eventNotes=[{strumTime:-1000,event:"E",value1:"first",value2:null},{strumTime:-1000,event:"E",value1:"old-tail",value2:null}];var originalQueue=eventNotes;if(eventNotes!=game.eventNotes||eventNotes!=PlayState.eventNotes||eventNotes!=Reflect.getProperty(game,"eventNotes"))throw "native queue identity";checkEventNote();if(eventNotes.length!=0||originalQueue.length!=2)throw "native queue replacement";', '__event_queue_api'));
			if (seen.join(',') != 'first:,second:' || state.songEventIndex != oldIndex + 2) throw 'Native historical queue shift order';
			@:privateAccess RuntimeSmokeHarness.emit('legacy_event_queue_native_verified', {liveAliases:true,callbackReplacement:true,postCallbackShift:true,nullValues:true,sharedEventDispatch:true,discoveryReleased:true});
		} catch(error:Dynamic) {state.songEventIndex=oldIndex;registry.funkyScripts=oldMain;handle.destroy();throw error;}
		state.songEventIndex=oldIndex;registry.funkyScripts=oldMain;handle.destroy();
	}

	static function verifyNotification(state:PlayState, registry:NightmareVisionLegacyScriptRegistry):Void {
		var oldScopes=state.hscriptStates;var oldSpeed=state.gfSpeed;
		var oldMain=registry.funkyScripts;var oldHx=registry.hscriptArray;var oldLua=registry.luaArray;var oldEvents=registry.eventScripts;
		state.hscriptStates=[];registry.funkyScripts=[];registry.hscriptArray=[];registry.luaArray=[];registry.eventScripts=[];
		var log:Array<String>=[];var handles:Array<NightmareVisionScriptModule>=[];
		var make=function(name:String, code:String) {
			var h=NightmareVisionScriptModule.fromSource(name,code,state,null,function(i){
				var m:NightmareVisionScriptModule=cast i.variables.get('script');m.historicalCalls=true;
				i.variables.set('record',function(text:String){if(state.gfSpeed!=7)throw 'Notification preceded effect';log.push(text);});
			},function(n,c,e)throw e);handles.push(h);return h;
		};
		var first=make('__notify_first','function onEvent(n,a,b){record("hscript:"+n+":"+a+":"+b);}');registry.add(first);
		var selected=make('__notify_selected','function onTrigger(a,b){record("trigger:"+a+":"+b);}');
		var stop=false;var lua=new LuaCompatInterp();lua.variables.set('__psychScoreGlobals',true);
		var unexpected=0;
		lua.variables.set('songEvent',function(e:Dynamic){unexpected++;});
		lua.variables.set('onEvent',function(n:String,a:String,b:String):Dynamic {
			if(state.gfSpeed!=7)throw 'Lua notification preceded effect';log.push('lua:'+n+':'+a+':'+b);
			registry.eventScripts=['Set GF Speed'=>selected];return stop?2:0;
		});
		state.hscriptStates.set('compat_global_event_notify',lua);
		state.registerHistoricalNightmareLua('compat_global_event_notify',lua,'__notify.lua');
		registry.add(make('__notify_last','function onEvent(n,a,b){record("last");}'));
		var restore=function(){state.hscriptStates=oldScopes;state.gfSpeed=oldSpeed;registry.funkyScripts=oldMain;registry.hscriptArray=oldHx;registry.luaArray=oldLua;registry.eventScripts=oldEvents;state.nightmareVisionLegacyLuaHandles.remove(lua);for(h in handles)h.destroy();};
		try {
			for(halt in [false,true]) {
				stop=halt;log.resize(0);state.gfSpeed=1;registry.eventScripts=[];
				state.triggerEventNote('Set GF Speed','7','');
				var expected='hscript:Set GF Speed:7:,lua:Set GF Speed:7:,'+(halt?'':'last,')+'trigger:7:';
				if(log.join(',')!=expected||unexpected!=0)throw 'Native event notification order: '+log.join(',');
			}
			@:privateAccess RuntimeSmokeHarness.emit('legacy_event_notification_native_verified',{builtinBeforeCallbacks:true,mixedRegistrationOrder:true,noPrematureLua:true,noForeignSongEvent:true,stopRetainsSelectedEvent:true,liveMapReplacement:true,scalarArguments:true,sharedTriggerEntry:true});
		} catch(error:Dynamic){restore();throw error;}
		restore();
	}

	static function verifyDiscovery(state:PlayState, registry:NightmareVisionLegacyScriptRegistry, api:NightmareVisionScriptInterp):Void {
		#if sys
		var backend=state.nightmareVisionScripts;var oldResolve=backend.resolveHistoricalEvent;var oldLoad=backend.loadHistoricalLuaEvent;
		var oldMain=registry.funkyScripts.copy();var oldHx=registry.hscriptArray.copy();var oldLua=registry.luaArray.copy();var oldEvents=registry.eventScripts;var oldExts=registry.hscriptExts;
		var oldSpeed=state.gfSpeed;var oldScopes=state.hscriptStates;state.hscriptStates=[];registry.eventScripts=[];
		var names=['__cammie_event_discovery_hx','__cammie_event_discovery_lua'];
		var files:Array<String>=[];var lua:Dynamic=null;
		var restore=function(){
			if(lua!=null)state.nightmareVisionLegacyLuaHandles.remove(lua);
			state.hscriptStates=oldScopes;state.gfSpeed=oldSpeed;registry.funkyScripts=oldMain;registry.hscriptArray=oldHx;registry.luaArray=oldLua;registry.eventScripts=oldEvents;registry.hscriptExts=oldExts;
			backend.resolveHistoricalEvent=oldResolve;backend.loadHistoricalLuaEvent=oldLoad;
			for(file in files)if(sys.FileSystem.exists(file))sys.FileSystem.deleteFile(file);
		};
		try {
			for(index in 0...2){
				var file=state.nightmareVisionPaths.modFolders('custom_events/'+names[index]+(index==0?'.hxs':'.lua'));
				if(sys.FileSystem.exists(file))throw 'Discovery fixture already exists: '+file;
				sys.FileSystem.createDirectory(haxe.io.Path.directory(file));files.push(file);
				var code=index==0?'if(eventScripts.exists("'+names[0]+'"))throw "map before constructor";function onLoad(n){if(eventScripts.get(n)!=script||hscriptArray.indexOf(script)>=0)throw "HScript load order";game.gfSpeed=8;}':
					'created = 0; loaded = 0; post = 0; function onCreate() created = created + 1; setProperty("gfSpeed", 6); end; function onCreatePost() post = post + 1; end; function onLoad(name) loaded = loaded + 1; loadedName = name; setProperty("gfSpeed", 7); end';
				sys.io.File.saveContent(file,code);
			}
			backend.resolveHistoricalEvent=function(name)return state.nightmareVisionPaths.resolveHistoricalEvent(name,registry.hscriptExts);
			backend.loadHistoricalLuaEvent=state.loadHistoricalNightmareLuaEvent;
			api.execute(new NightmareVisionScriptParser().parseString('hscriptExts=["hxs"];if(game.hscriptExts!=hscriptExts||PlayState.hscriptExts!=hscriptExts)throw "extension aliases";','__event_extensions'));
			backend.loadScope('event',names[0]);
			if(state.gfSpeed!=8||!registry.eventScripts.exists(names[0]))throw 'Native unplanned HScript event discovery: speed='+state.gfSpeed+', registered='+registry.eventScripts.exists(names[0]);
			backend.loadScope('event',names[1]);
			var handle:NightmareVisionLegacyLuaScript=cast registry.eventScripts.get(names[1]);
			if(handle==null)throw 'Native unplanned Lua event discovery';lua=handle.interp;
			backend.loadScope('event',names[1]);
			if(state.gfSpeed!=7||handle.get('created')!=1||handle.get('loaded')!=1||handle.get('post')!=0||handle.get('loadedName')!=names[1]
				||registry.luaArray.indexOf(handle)<0||registry.funkyScripts.indexOf(handle)<0)throw 'Native Lua event initialization or identity';
			@:privateAccess RuntimeSmokeHarness.emit('legacy_event_discovery_native_verified',{unplannedHscript:true,unplannedLua:true,sharedRuntimes:true,hscriptOrder:true,luaCreateOnce:true,luaLoadOnce:true,noPrematurePost:true,authoredName:true,mutableExtensionAliases:true});
		} catch(error:Dynamic){restore();throw error;}
		restore();
		#end
	}

	static function verifyKillNotes(state:PlayState, registry:NightmareVisionLegacyScriptRegistry, api:NightmareVisionScriptInterp):Void {
		var oldNotes = state.notes;var oldUnspawn = state.unspawnNotes;var oldEvents = registry.eventNotes;var oldObjects = state.modchartObjects;
		var group = new flixel.group.FlxGroup.FlxTypedGroup<Note>();
		var field = state.nightmareVisionLegacyReceptors.player;
		var pending:Note = null;
		var restore = function() {
			for (note in group.members.copy()) if (note != null) state.retireNightmareVisionLegacyNote(note);
			state.notes = oldNotes;state.unspawnNotes = oldUnspawn;registry.eventNotes = oldEvents;state.modchartObjects = oldObjects;
			if (pending != null) pending.destroy();group.destroy();
		};
		state.notes = group;state.modchartObjects = [];
		try {
			for (form in ['KillNotes();','game.KillNotes();','PlayState.KillNotes();','Reflect.callMethod(game,Reflect.field(game,"KillNotes"),[]);']) {
				var note = new Note(100, 0);note.ID = 90101;
				group.add(note);field.addNote(note);state.modchartObjects.set('note90101', note);
				var removed = function(n:Note) {if (n != note || field.notes.indexOf(n) < 0 || state.modchartObjects.exists('note90101')) throw 'Group removal must precede field detach and follow alias removal';};
				group.memberRemoved.add(removed);
				pending = new Note(10000, 1);pending.ID = 90102;
				var queued = [pending];var queuedEvents:Array<Dynamic> = [{strumTime:0,event:'pending',value1:'',value2:''}];
				state.unspawnNotes = queued;registry.eventNotes = queuedEvents;
				api.variables.set('__oldUnspawn', queued);api.variables.set('__oldEvents', queuedEvents);
				api.execute(new NightmareVisionScriptParser().parseString(form + 'if(unspawnNotes==__oldUnspawn||eventNotes==__oldEvents||game.unspawnNotes.length!=0||PlayState.eventNotes.length!=0)throw "native KillNotes array identity";', '__kill_notes'));
				if (group.length != 0 || note.active || note.visible || note.alive || note.exists || note.animation != null
					|| field.notes.indexOf(note) >= 0 || state.nightmareVisionNoteFields.exists(note) || state.modchartObjects.exists('note90101')
					|| queued.length != 1 || queued[0].animation == null || queuedEvents.length != 1)
					throw 'Native KillNotes lifetime or ownership: ' + form + ' ' + haxe.Json.stringify({length:group.length,active:note.active,visible:note.visible,alive:note.alive,exists:note.exists,destroyed:note.animation==null,fieldMember:field.notes.indexOf(note),mapped:state.nightmareVisionNoteFields.exists(note),alias:state.modchartObjects.exists('note90101'),pendingAlive:queued[0].animation!=null});
				group.memberRemoved.remove(removed);
				pending.destroy();pending = null;
			}
			@:privateAccess RuntimeSmokeHarness.emit('legacy_kill_notes_native_verified', {publicForms:4,liveArrayAliases:true,fieldRemoval:true,aliasRemoval:true,activeDestroyed:true,pendingNotDestroyed:true});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
	}

}
