package;

/** Opt-in native verification of the historical notification adapter, with isolated scopes. */
@:access(PlayState)
class RuntimeSmokeLegacyHitNotifications {
	public static function verify(note:Note):Void {
		#if sys
		if (Sys.getEnv('CAMMIE_LEGACY_HIT_NOTIFY_SMOKE') != '1') return;
		var state = PlayState.instance;
		if (!state.nightmareVisionLegacyFieldCameras) throw 'Historical hit notification profile unavailable';
		var oldScripts = state.scripts;
		var oldEvents = state.eventScripts;
		var oldTypes = state.notetypeScripts;
		var oldScopes = state.hscriptStates;
		var oldAttachment = note.noteScript;
		var oldDispatched = note.nightmareVisionHitDispatched;
		var resetRegistry = RuntimeSmokeLegacyRegistry.isolate(state);
		var errors:Array<String> = [];
		var seen:Array<String> = [];
		var report = function(n:String,p:String,e:Dynamic) errors.push(n+':'+p+':'+Std.string(e));
		var group = new NightmareVisionScriptGroup(state, report);
		state.scripts = group;state.eventScripts = new NightmareVisionScriptGroup(state, report);
		state.notetypeScripts = [];state.hscriptStates = [];
		var restore = function() {
			note.noteScript = oldAttachment;note.nightmareVisionHitDispatched = oldDispatched;
			state.eventScripts = oldEvents;
			state.notetypeScripts = oldTypes;state.hscriptStates = oldScopes;
			group.destroy();resetRegistry();
		};
		try {
			var configure = function(interp:NightmareVisionScriptInterp) {
				interp.variables.set('record', function(label:String,n:Note) {
					if (n != note) throw 'Native historical HScript note identity mismatch';
					seen.push(label);
				});
			};
			var original = group.loadSource('original', "function goodNoteHit(n){record('WRONG-original',n);} function opponentNoteHit(n){goodNoteHit(n);}",configure);
			var attached = group.loadSource('attached', "function goodNoteHit(n){record('attached',n);return 1;} function opponentNoteHit(n){return goodNoteHit(n);}",configure);
			var event = group.loadSource('event', "function goodNoteHit(n){record('WRONG-event',n);} function opponentNoteHit(n){goodNoteHit(n);}",configure);
			var global = group.loadSource('global', "function goodNoteHit(n){record('global',n);n.noteScript=next;return 2;} function opponentNoteHit(n){return goodNoteHit(n);}",configure);
			group.loadSource('later', "function goodNoteHit(n){record('WRONG-halt',n);} function opponentNoteHit(n){goodNoteHit(n);}",configure);
			state.notetypeScripts.set('original',original);state.notetypeScripts.set('attached',attached);
			state.eventScripts.addScript(event);global.set('next',attached);
			for (key in ['compat_global_smoke','compat_custom_event_smoke','compat_custom_notetype_smoke']) {
				var lua = new LuaCompatInterp();
				lua.variables.set('__psychScoreGlobals',true);
				for (callback in ['goodNoteHit','opponentNoteHit']) lua.variables.set(callback,
					function(slot:Int,lane:Float,kind:String,sustain:Bool,id:Int):Dynamic {
						if (key != 'compat_global_smoke') throw 'Historical Lua broadcast included special registry scope';
						if (slot != state.notes.members.indexOf(note) || lane != Math.abs(note.noteData)
							|| kind != note.noteType || sustain != note.isSustainNote || id != note.ID)
							throw 'Native historical Lua hit arguments mismatch';
						seen.push('lua');return 1;
					});
				state.hscriptStates.set(key,lua);
				state.registerHistoricalNightmareLua(key,lua,key+".lua");
			}
			var observer = new hscript.Interp();observer.variables.set('__psychScoreGlobals',true);
			for (callback in ['goodNoteHit','opponentNoteHit']) observer.variables.set(callback,
				function(id:Int,lane:Float,kind:String,sustain:Bool) {
					// Host observers retain their existing four-scalar ABI. Historical NV
					// modules above separately assert their live-Note identity.
					if (id != note.ID || lane != Math.abs(note.noteData)
						|| kind != (note.coolId == null ? note.noteType : note.coolId) || sustain != note.isSustainNote)
						throw 'Native host observer arguments mismatch: '+haxe.Json.stringify([id,lane,kind,sustain]);
					seen.push('host-observer');
				});
			state.hscriptStates.set('compat_global_hscript_observer',observer);
			for (callback in ['goodNoteHit','opponentNoteHit']) {
				seen.resize(0);note.noteScript=original;note.nightmareVisionHitDispatched=false;
				state.dispatchNightmareVisionNoteHit(note,0,callback);
				state.dispatchNightmareVisionNoteHit(note,0,callback);
				if (seen.join(',') != 'lua,global,attached' || note.noteScript != attached || errors.length > 0)
					throw 'Native historical notification order mismatch: '+seen.join(',')+' '+errors.join(',');
				state.callAllHScript(callback,[note,true],true,null,null,false,true);
				if (seen.join(',') != 'lua,global,attached,host-observer')
					throw 'Native observer phase repeated Lua or dropped the HScript observer';
			}
			@:privateAccess RuntimeSmokeHarness.emit('legacy_hit_notifications_native_verified',
				{families:2,luaArity:5,hscriptIdentity:true,globalBeforeAttached:true,registryExclusion:true,
					ignoredStop:true,haltFamilyOnly:true,attachmentReplacement:true,duplicateSuppression:true,hostObserverPreserved:true});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
		#end
	}
}
