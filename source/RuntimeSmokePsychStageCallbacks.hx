package;

/** Native stage identity, stored timing and activity-gated dispatch probe. */
@:access(PlayState)
@:access(MusicBeatState)
class RuntimeSmokePsychStageCallbacks {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState):Void {
		#if sys
		if (Sys.getEnv('CAMMIE_PSYCH_STAGE_CALLBACK_SMOKE') != '1') return;
		#else
		return;
		#end
		var key = '__sourceStageCallbackProbe';
		var hadKey = state.variables.exists(key), oldValue = state.variables.get(key);
		var oldStages = state.stages;
		var oldStep = state.curStep, oldBeat = state.curBeat, oldSection = state.curSection;
		var oldDecStep = state.curDecStep, oldDecBeat = state.curDecBeat;
		var runtime:PsychCompiledStageRuntime = null;
		var cleanup = function() {
			if (runtime != null) runtime.destroy();
			state.stages = oldStages;
			state.curStep = oldStep;state.curBeat = oldBeat;state.curSection = oldSection;
			state.curDecStep = oldDecStep;state.curDecBeat = oldDecBeat;
			if (hadKey) state.variables.set(key, oldValue); else state.variables.remove(key);
		};
		try {
			var log:Array<Dynamic> = [];state.variables.set(key, log);state.stages = [];
			runtime = new PsychCompiledStageRuntime('tmp/source-stage-callback-probe', 'demo.CallbackProbe', state);
			check(runtime.create(), 'Native stage class construction: ' + runtime.diagnostics.join('; '));
			var stage = runtime.sourceObject;
			check(state.stages.length == 1 && state.stages[0] == stage && log[0] == 'create:true', 'Stage source identity registered before create');
			state.curStep = 20;state.curDecStep = 20.25;state.curBeat = 5;state.curDecBeat = 5.0625;state.curSection = 4;
			state.dispatchPsychCompiledStage('stepHit', []);
			check(log[1] == 'step:20:20.25:0' && log.length == 2, 'Stored stage fields and single host callback');
			state.curStep = 30;
			check(PsychStageObject.read(stage, 'curStep') == 20, 'Stage timing persists between callbacks');
			runtime.dispatch('beatHit', []);state.dispatchPsychCompiledStage('sectionHit', []);
			check(PsychStageObject.read(stage, 'curBeat') == 5 && PsychStageObject.read(stage, 'curDecBeat') == 5.0625
				&& PsychStageObject.read(stage, 'curSection') == 4, 'Beat and section publication');
			var count = log.length;
			PsychStageObject.write(stage, 'active', false);state.dispatchPsychCompiledStage('stepHit', []);runtime.update(.1);
			check(log.length == count && runtime.active, 'Inactive stage skips callbacks without losing owner');
			PsychStageObject.write(stage, 'active', true);PsychStageObject.write(stage, 'exists', false);
			state.dispatchPsychCompiledStage('stepHit', []);
			check(log.length == count, 'Nonexistent stage skips callbacks');
			PsychStageObject.write(stage, 'exists', true);runtime.destroy();
			check(log[log.length - 1] == 'destroy' && PsychStageObject.read(stage, 'exists') == false, 'Stage teardown retires native lifetime');
			runtime.destroy();state.stages = [];
			var ctorLog:Array<String> = [];
			var bindings:Map<String, Dynamic> = new Map();
			bindings.set('record', function(message:String):Void {ctorLog.push(message);});
			runtime = new PsychCompiledStageRuntime('tmp/source-stage-callback-probe', 'demo.ConstructorProbe', state, bindings);
			check(runtime.create(), 'Native nested stage construction: ' + runtime.diagnostics.join('; '));
			check(ctorLog.join('|') == 'child-before|middle-before|create:0|leaf:1|middle-after|child-after', 'Virtual create must run inside super: ' + ctorLog);
			check(state.stages.length == 2 && state.stages[0] == runtime.sourceObject, 'Nested native registry identity');
			runtime.beginPostCreate();runtime.dispatch('stepHit', []);
			check(state.stages.length == 3 && ctorLog[6] == 'leaf:2', 'Callback-created native sibling');
			runtime.destroy(true, false);
			PsychStageObject.call(state.stages[1], 'destroy', []);
			PsychStageObject.call(state.stages[2], 'destroy', []);
			runtime.destroy();
			check(ctorLog.slice(7).join('|') == 'root-destroy|leaf-destroy|leaf-destroy', 'Nested cleanup must retain the owner scope');
			@:privateAccess RuntimeSmokeHarness.emit('psych_stage_construction_native_verified', {superOrder:true,nestedRegistration:true,callbackCreation:true,siblingCleanup:true});
			@:privateAccess RuntimeSmokeHarness.emit('psych_stage_callbacks_native_verified', {sourceIdentity:true,registration:true,storedTiming:true,activityGates:true,singleCallback:true,lifetime:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
