package;

import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.sound.FlxSound;

/** Opt-in native miss check using isolated notes and production script bindings. */
@:access(PlayState)
class RuntimeSmokeLegacyMiss {
	public static function verify():Void {
		#if sys
		if (Sys.getEnv('CAMMIE_LEGACY_MISS_SMOKE') != '1') return;
		var state = PlayState.instance;
		if (!state.nightmareVisionLegacyFieldCameras) throw 'Historical miss profile unavailable';
		var saved:Map<String, Dynamic> = [];
		for (name in ['health','healthLoss','combo','songScore','totalPlayed','accuracy',
			'practiceMode','instakillOnMiss','ratingFC','psychScoreSnapshot','psychRatingPrevious','psychRatingOverrides'])
			saved.set(name, Reflect.getProperty(state, name));
		var oldMisses = PlayState.misses;
		var oldNotes = state.notes;var oldObjects = state.modchartObjects;
		var oldScripts = state.scripts;var oldScopes = state.hscriptStates;
		var oldEvents = state.eventScripts;var oldTypes = state.notetypeScripts;
		var oldTracks = state.vocalTracks;var oldVoice = state.vocals;
		var field = state.nightmareVisionLegacyReceptors.player;
		var oldControl = field.playerControls;
		var errors:Array<String> = [];var seen:Array<String> = [];
		var group = new NightmareVisionScriptGroup(state, function(n,p,e) errors.push(Std.string(e)));
		var events = new NightmareVisionScriptGroup(state, function(n,p,e) errors.push(Std.string(e)));
		var notes = new FlxTypedGroup<Note>();var voice = new FlxSound();
		var api:NightmareVisionScriptInterp = null;
		state.notes = notes;state.modchartObjects = [];state.scripts = group;state.hscriptStates = [];
		state.eventScripts = events;state.notetypeScripts = [];state.vocalTracks = null;state.vocals = voice;
		state.psychRatingOverrides = [];
		var restore = function() {
			for (n in notes.members) if (n != null) n.playField = null;
			PlayState.misses = oldMisses;state.notes = oldNotes;state.modchartObjects = oldObjects;state.scripts = oldScripts;state.hscriptStates = oldScopes;
			state.eventScripts = oldEvents;state.notetypeScripts = oldTypes;state.vocalTracks = oldTracks;state.vocals = oldVoice;
			field.playerControls = oldControl;
			for (name in saved.keys()) Reflect.setProperty(state, name, saved.get(name));
			if (api != null) api.release();group.destroy();events.destroy();notes.destroy();voice.destroy();
		};
		try {
			var note = new Note(100, 2);note.ID = 90001;note.noMissAnimation = true;note.noteScript = null;
			note.nightmareVisionTypeRuntime = state.nightmareVisionNoteTypes;
			note.playField = field;note.missHealth = 0.08;note.canMiss = true;note.blockHit = true;
			notes.add(note);
			group.loadSource('__miss_probe', 'function noteMiss(n){record(n);}', function(i) i.variables.set('record', function(n:Note) {
				if (n != note || state.combo != 0 || voice.volume != 0) throw 'Native miss notification timing/identity';
				seen.push('hscript');
			}));
			api = new NightmareVisionScriptInterp(state);
			state.seedNightmareVision(api, {scope:'song',name:'__miss_api',relative:'__miss_api.hx',path:state.nightmareVisionPaths.root+'/__miss_api.hx'}, null);
			api.variables.set('probeNote', note);
			var forms = ['noteMiss(probeNote);','game.noteMiss(probeNote);','PlayState.noteMiss(probeNote);',
				'Reflect.callMethod(game,Reflect.getProperty(game,"noteMiss"),[probeNote]);'];
			for (practice in [false,true]) for (form in forms) {
				var duplicate = new Note(100.5, 2);duplicate.ID = 90002;duplicate.playField = field;
				notes.add(duplicate);state.modchartObjects.set('note90002', duplicate);
				field.playerControls = true;state.practiceMode = practice;state.instakillOnMiss = false;
				state.health = 1;state.healthLoss = 2;state.songScore = 70;PlayState.misses = 2;state.totalPlayed = 3;state.combo = 8;voice.volume = 1;
				var count = seen.length;
				api.execute(new NightmareVisionScriptParser().parseString(form, '__miss_api'));
				if (Math.abs(state.health-0.84)>0.00001 || state.songScore != (practice?70:60) || PlayState.misses != 3
					|| state.totalPlayed != 4 || !note.alive || notes.members.indexOf(duplicate)>=0 || state.modchartObjects.exists('note90002')
					|| seen.length != count+1 || errors.length>0) throw 'Native historical miss mismatch: '+form+' '+errors.join(',');
			}
			@:privateAccess RuntimeSmokeHarness.emit('legacy_miss_native_verified',
				{calls:8,practiceAccounting:true,health:true,duplicateRemoval:true,registryCleanup:true,liveNote:true,callbackTiming:true,scriptBindings:true});
		} catch (error:Dynamic) {restore();throw error;}
		restore();
		#end
	}
}
