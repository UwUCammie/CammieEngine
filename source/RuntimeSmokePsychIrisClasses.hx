package;

/** Reversible native verification of automatic Psych source-class sessions. */
@:access(PlayState)
class RuntimeSmokePsychIrisClasses {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState):Void {
		#if sys
		if (Sys.getEnv('CAMMIE_PSYCH_IRIS_CLASSES_SMOKE') != '1') return;
		#else
		return;
		#end
		var root = 'assets/imported_mods/__iris_source_probe';
		var manifest = state.cachedCompatScriptManifest;
		var originalStages = state.stages;
		var originalCallbacks = state.psychSourceCallbacks;
		var plain = new SourceIrisBridge(state);
		var lua = new LuaCompatInterp();
		var runtime:PsychRuntimeBindings = null;
		var session:PsychSourceClassSession = null;
		var cleanup = function() {
			plain.release();if (runtime != null) runtime.release();
			if (session != null) session.release();
			state.psychSourceClassSessions.remove(root);
			state.psychSourceCallbacks.release();state.psychSourceCallbacks = originalCallbacks;
			state.stages = originalStages;state.cachedCompatScriptManifest = manifest;
		};
		try {
			state.cachedCompatScriptManifest = {version:CompatScriptManifest.VERSION, roots:[{engine:ImportEngine.PSYCH,path:root}]};
			state.stages = [];state.psychSourceCallbacks = new PsychSourceCallbackRegistry();
			new PsychHscriptSourceBindings(state, plain, root + '/scripts/probe.hx', null).install();
			session = state.sourceClassSession(root);
			check(plain.evaluator.sourceClasses == session, 'Plain HScript automatically borrows owner classes');
			plain.evaluate('import demo.Counter; item=new Counter(); value=item.next();', 'source-probe');
			var item = plain.variables.get('item');
			check(plain.variables.get('value') == 2, 'Native Iris source construction/method result');
			runtime = new PsychRuntimeBindings(state, lua, root + '/scripts/probe.lua');runtime.install();
			var run = lua.variables.get('runHaxeCode');
			var result = Reflect.callMethod(null, run, ['import demo.Counter; same=Type.getClass(item)==Counter; name=Type.getClassName(Counter); next=item.next(); if (!same || name!="demo.Counter") throw "native reflection identity"; Counter.count;', {item:item}]);
			check(result == 3, 'Embedded HScript shares native owner static storage');
			plain.evaluate('import demo.ExtraStage; createdStageProbe=new ExtraStage();', 'stage-probe');
			var stage = plain.variables.get('createdStageProbe');
			check(state.stages.length == 2 && state.stages[0] == stage, 'Automatic source stage/native helper registration: count=' + state.stages.length + ', found=' + (stage != null));
			plain.release();runtime.release();
			state.stagesFunc(function(value) PsychStageObject.call(value, 'stepHit', []));
			check(session.read(stage, 'ticks') == 11, 'Native source callback survives both scripts closing');
			state.stagesFunc(function(value) PsychStageObject.call(value, 'destroy', []));
			session.release();
			var rejected = false;try session.read(item, 'count') catch (_:Dynamic) rejected = true;
			check(rejected, 'State session release rejects retained objects');
			@:privateAccess RuntimeSmokeHarness.emit('psych_iris_classes_native_verified', {
				plainPreset:true,embeddedPreset:true,sharedIdentity:true,sharedStatics:true,sourceStage:true,scriptClose:true,orderedDestroy:true,releasedOwner:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
