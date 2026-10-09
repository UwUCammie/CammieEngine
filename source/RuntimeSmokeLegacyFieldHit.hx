package;

/** Opt-in source callback mutation through the real native interpreter and hit dispatcher. */
class RuntimeSmokeLegacyFieldHit {
	public static function verify(note:Note):Void {
		#if sys
		if (Sys.getEnv('CAMMIE_LEGACY_FIELD_HIT_SMOKE') != '1') return;
		var state = PlayState.instance;
		var field:NightmareVisionPlayFieldView = cast note.playField;
		if (field == null || !field.legacyGroupCameras || field.noteHitCallback == null)
			throw 'Historical field callback was not installed';
		var tap:Note = null;
		for (candidate in @:privateAccess state.unspawnNotes)
			if (candidate != null && !candidate.isSustainNote) {tap = candidate;break;}
		if (tap == null) throw 'Historical callback probe requires a pending tap';
		var oldField = tap.playField;
		var oldTime = tap.strumTime;
		var oldSustain = tap.isSustainNote;
		var oldAuto = field.autoPlayed;
		var oldLate = tap.tooLate;
		var oldCallback = field.noteHitCallback;
		var oldControl = field.inControl;
		var oldHealth = state.health;
		var oldCombo = @:privateAccess state.combo;
		var oldContext = @:privateAccess state.nightmareVisionFieldHitContext;
		var errors:Array<String> = [];
		var seen:Array<String> = [];
		var module = NightmareVisionScriptModule.fromSource('__field_hit_probe',
			"function install(f) { f.noteHitCallback = function(n,bank) { record('first',n,bank); "
			+ "Reflect.setProperty(bank, 'noteHitCallback', function(n2,b2) { record('second',n2,b2); }); }; }",
			state, null, function(interp) {
				@:privateAccess state.seedNightmareVision(interp, {scope:'smoke',name:'__field_hit_probe',path:'__field_hit_probe',relative:'__field_hit_probe'}, null);
				interp.variables.set('record', function(label:String,n:Note,f:NightmareVisionPlayFieldView) {
					if (n != tap || f != field) throw 'Historical native callback payload mismatch';
					seen.push(label);
				});
			}, function(n,p,e) errors.push(p+': '+Std.string(e)));
		var restore = function() {
			field.noteHitCallback = oldCallback;field.inControl = oldControl;
			tap.playField = oldField;tap.strumTime = oldTime;tap.tooLate = oldLate;
			tap.isSustainNote = oldSustain;field.autoPlayed = oldAuto;
			module.destroy();
		};
		try {
			tap.playField = field;tap.strumTime = Conductor.songPosition;tap.tooLate = false;field.inControl = true;
			field.autoPlayed = true;tap.isSustainNote = true;
			if (!field.canAutoHit(tap, Conductor.songPosition) || field.getNotes(tap.noteData).indexOf(tap) < 0)
				throw 'Historical native computed hit window was not read';
			tap.strumTime += 100000;
			if (field.canAutoHit(tap, Conductor.songPosition) || field.getNotes(tap.noteData).indexOf(tap) >= 0)
				throw 'Historical native computed hit window was cached';
			tap.isSustainNote = oldSustain;tap.strumTime = Conductor.songPosition;
			module.callValue('install',[field]);
			for (_ in 0...2) @:privateAccess state.hitNightmareVisionNote(tap, field.playerControls);
			if (errors.length > 0 || seen.join(',') != 'first,second' || !tap.alive || tap.wasGoodHit
				|| tap.nightmareVisionHitDispatched || state.health != oldHealth || (@:privateAccess state.combo) != oldCombo
				|| @:privateAccess state.nightmareVisionFieldHitContext != oldContext)
				throw 'Historical native callback replacement failed: '+seen.join(',')+' '+errors.join(',');
			@:privateAccess RuntimeSmokeHarness.emit('legacy_field_hit_native_verified',
				{computedWindow:true,scriptAssignment:true,reflectedReplacement:true,payloadIdentity:true,nativeEffectsSuppressed:true,contextRestored:true,calls:seen.join(',')});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
		#end
	}
}
