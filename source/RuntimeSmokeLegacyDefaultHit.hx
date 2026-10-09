package;

/** Isolated native verification of source default callbacks on the actual fields. */
@:access(PlayState)
class RuntimeSmokeLegacyDefaultHit {
	public static function verify(note:Note):Void {
		#if sys
		var scriptCalls = Sys.getEnv('CAMMIE_LEGACY_HIT_API_SMOKE') == '1';
		if (!scriptCalls && Sys.getEnv('CAMMIE_LEGACY_DEFAULT_HIT_SMOKE') != '1') return;
		var state = PlayState.instance;
		var player = state.nightmareVisionLegacyReceptors.player;
		var opponent = state.nightmareVisionLegacyReceptors.opponent;
		if (player == null || opponent == null) throw 'Missing historical default fields';
		var oldScripts = state.scripts;
		var oldScopes = state.hscriptStates;
		var oldAttachment = note.noteScript;
		var oldHealth = state.health;
		var oldGain = state.healthGain;
		var oldCamera = state.camZooming;
		var saved:Map<String, Dynamic> = [];
		for (name in ['isSustainNote','noAnimation','wasGoodHit','hitByOpponent','nightmareVisionHitDispatched',
			'doAutoSustain','hitHealth','ignoreNote','hitCausesMiss','noteData','hitsoundDisabled'])
			saved.set(name, Reflect.getProperty(note, name));
		var oldPlayerControl = player.playerControls;
		var oldOpponentControl = opponent.playerControls;
		var oldPlayerAuto = player.autoPlayed;
		var oldOpponentAuto = opponent.autoPlayed;
		var api:NightmareVisionScriptInterp = null;
		var errors:Array<String> = [];
		var seen:Array<String> = [];
		var group = new NightmareVisionScriptGroup(state, function(n,p,e) errors.push(Std.string(e)));
		state.scripts = group;state.hscriptStates = [];
		var restore = function() {
			state.scripts = oldScripts;state.hscriptStates = oldScopes;note.noteScript = oldAttachment;
			state.health = oldHealth;state.healthGain = oldGain;state.camZooming = oldCamera;
			for (name in saved.keys()) Reflect.setProperty(note, name, saved.get(name));
			player.playerControls = oldPlayerControl;opponent.playerControls = oldOpponentControl;
			player.autoPlayed = oldPlayerAuto;opponent.autoPlayed = oldOpponentAuto;
			if (api != null) api.release();
			group.destroy();
		};
		try {
			group.loadSource('__default_hit_probe',
				"function goodNoteHit(n){record('good',n);} function opponentNoteHit(n){record('opponent',n);}",
				function(interp) interp.variables.set('record', function(name:String,n:Note) {
					if (n != note) throw 'Default hit callback lost Note identity';
					if (name == 'good' ? !n.wasGoodHit || n.hitByOpponent || !n.doAutoSustain
						: n.wasGoodHit || !n.hitByOpponent) throw 'Default hit callback flag timing mismatch';
					seen.push(name);
				}));
			note.isSustainNote = true;note.noAnimation = true;note.noteScript = null;
			note.ignoreNote = false;note.hitCausesMiss = false;note.hitsoundDisabled = true;
			note.noteData = 5;note.hitHealth = 0.04;state.healthGain = 1.25;
			player.playerControls = false;player.autoPlayed = true;
			note.wasGoodHit = false;note.hitByOpponent = false;note.doAutoSustain = false;note.nightmareVisionHitDispatched = false;
			player.dispatchNoteHit(note);
			if (Math.abs(state.health - oldHealth - 0.05) > 0.00001) throw 'Historical player health mismatch';
			player.dispatchNoteHit(note);
			if (seen.join(',') != 'good') throw 'Repeated player hit was not rejected';
			var afterPlayer = state.health;
			opponent.playerControls = true;opponent.autoPlayed = false;
			note.wasGoodHit = false;note.hitByOpponent = false;note.nightmareVisionHitDispatched = false;
			opponent.dispatchNoteHit(note);
			if (state.health != afterPlayer || note.wasGoodHit || !note.hitByOpponent
				|| seen.join(',') != 'good,opponent' || errors.length > 0)
				throw 'Historical fixed family/flag mismatch: '+seen.join(',')+' '+errors.join(',');
			NightmareVisionLegacyHitFlow.updateFlags(note);
			if (!note.wasGoodHit) throw 'Historical opponent update did not commit wasGoodHit';
			if (scriptCalls) {
				api = new NightmareVisionScriptInterp(state);
				state.seedNightmareVision(api, {scope:'song',name:'__hit_api',relative:'__hit_api.hx',
					path:state.nightmareVisionPaths.root + '/__hit_api.hx'}, null);
				api.variables.set('probeNote', note);
				var forms = ['HANDLER(probeNote,probeField);', 'game.HANDLER(probeNote,probeField);',
					'PlayState.HANDLER(probeNote,probeField);',
					'Reflect.callMethod(game,Reflect.getProperty(game,"HANDLER"),[probeNote,probeField]);'];
				for (isPlayer in [true, false]) for (form in forms) {
					note.wasGoodHit = false;note.hitByOpponent = false;note.doAutoSustain = false;
					note.nightmareVisionHitDispatched = false;
					api.variables.set('probeField', isPlayer ? player : opponent);
					var beforeHealth = state.health;var beforeCount = seen.length;
					var text = StringTools.replace(form, 'HANDLER', isPlayer ? 'goodNoteHit' : 'opponentNoteHit');
					api.execute(new NightmareVisionScriptParser().parseString(text, '__hit_api'));
					if (seen.length != beforeCount + 1 || seen[beforeCount] != (isPlayer ? 'good' : 'opponent')
						|| Math.abs(state.health - beforeHealth - (isPlayer ? 0.05 : 0)) > 0.00001 || errors.length > 0)
						throw 'Historical script entrypoint mismatch: ' + text;
				}
				@:privateAccess RuntimeSmokeHarness.emit('legacy_hit_api_native_verified',
					{bare:true,instance:true,classAlias:true,reflection:true,sourceSignature:true,families:2,calls:8});
			}
			@:privateAccess RuntimeSmokeHarness.emit('legacy_default_hit_native_verified',
				{fixedFamilies:true,playerHealth:true,playerRepeatGuard:true,callbackFlagTiming:true,deferredOpponentFlag:true,widerLaneAutoSustain:true});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
		#end
	}
}
