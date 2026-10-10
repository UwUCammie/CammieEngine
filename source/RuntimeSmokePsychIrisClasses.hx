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
		var nativeGroup = new flixel.group.FlxGroup.FlxTypedGroup<flixel.FlxBasic>();
		var nativeTween:flixel.tweens.FlxTween = null;
		var recycleGroup = new flixel.group.FlxGroup.FlxTypedGroup<flixel.FlxBasic>();
		var recycleOwner:CodenameScriptClassLoader = null;
		var cleanup = function() {
			if (nativeTween != null) nativeTween.cancel();if (nativeGroup != null) nativeGroup.destroy();
			recycleGroup.destroy();if (recycleOwner != null) recycleOwner.scope.release();
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
			plain.variables.set('nativeProbeGroup', nativeGroup);
			plain.variables.set('FlxTween', flixel.tweens.FlxTween);
			plain.evaluate('import demo.NativeMember; nativeMemberProbe=new NativeMember(); capturedAddProbe=nativeProbeGroup.add; addedProbe=capturedAddProbe(nativeMemberProbe); indexedProbe=nativeProbeGroup.members[0]; nativeProbeGroup.forEach(function(value) {callbackProbe=value;}); reflectedRemoveProbe=Reflect.field(nativeProbeGroup,"remove"); removedProbe=Reflect.callMethod(nativeProbeGroup,reflectedRemoveProbe,[nativeMemberProbe,true]); nativeProbeGroup.add(nativeMemberProbe); capturedTweenProbe=FlxTween.tween; tweenProbe=capturedTweenProbe(nativeMemberProbe,{x:25},1);', 'native-boundary-probe');
			var member = plain.variables.get('nativeMemberProbe');
			for (key in ['addedProbe', 'indexedProbe', 'callbackProbe', 'removedProbe'])
				check(plain.variables.get(key) == member, 'Native boundary preserves source identity: ' + key);
			nativeTween = plain.variables.get('tweenProbe');
			@:privateAccess nativeTween.update(1);
			nativeTween.cancel();
			check(session.read(member, 'x') == 25, 'Captured native tween targets source superclass');
			nativeGroup.update(0.1);
			check(session.read(member, 'ticks') == 1, 'Native group drives source lifecycle');
			recycleOwner = CodenameScriptClassLoader.open(root, ['flixel.FlxObject'=>flixel.FlxObject], new Map());
			var recycleLoaded = recycleOwner.importClasses(['demo.NativeMember']);
			check(recycleLoaded.diagnostics.length == 0, 'Native recycle owner imports');
			plain.variables.set('foreignRecycleClass', recycleOwner.scope.resolveClassSymbol('demo.NativeMember'));
			plain.variables.set('recycleProbeGroup', recycleGroup);
			plain.evaluate('capturedRecycleProbe=recycleProbeGroup.recycle; recycledProbe=capturedRecycleProbe(foreignRecycleClass);', 'recycle-probe');
			var recycled = plain.variables.get('recycledProbe');
			recycleGroup.members[0].kill();
			plain.evaluate('reusedProbe=capturedRecycleProbe(foreignRecycleClass,null,false,false);', 'recycle-reuse-probe');
			check(plain.variables.get('reusedProbe') == recycled && !recycleGroup.members[0].exists, 'Native Iris foreign recycle identity and revive false');
			plain.evaluate('recycleProbeGroup.recycle(foreignRecycleClass);', 'recycle-revive-probe');
			recycleGroup.update(0.1);
			check(session.read(recycled, 'ticks') == 1, 'Foreign recycled member retains actual source lifecycle');
			plain.evaluate('import demo.ExtraStage; createdStageProbe=new ExtraStage();', 'stage-probe');
			var stage = plain.variables.get('createdStageProbe');
			check(state.stages.length == 2 && state.stages[0] == stage, 'Automatic source stage/native helper registration: count=' + state.stages.length + ', found=' + (stage != null));
			plain.release();runtime.release();
			state.stagesFunc(function(value) PsychStageObject.call(value, 'stepHit', []));
			check(session.read(stage, 'ticks') == 11, 'Native source callback survives both scripts closing');
			nativeGroup.update(0.1);nativeGroup.destroy();nativeGroup = null;
			check(session.read(member, 'ticks') == 2 && session.read(member, 'destroyed') == 1, 'Native source member survives script closure and destroys once');
			state.stagesFunc(function(value) PsychStageObject.call(value, 'destroy', []));
			session.release();
			var rejected = false;try session.read(item, 'count') catch (_:Dynamic) rejected = true;
			check(rejected, 'State session release rejects retained objects');
			@:privateAccess RuntimeSmokeHarness.emit('psych_iris_classes_native_verified', {
				crossOwnerRecycle:true,nativeGroups:true,nativeTweens:true,capturedMethods:true,reflectedMethods:true,indexedIdentity:true,plainPreset:true,embeddedPreset:true,sharedIdentity:true,sharedStatics:true,sourceStage:true,scriptClose:true,orderedDestroy:true,releasedOwner:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
