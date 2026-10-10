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
		var spriteGroup = new flixel.group.FlxSpriteGroup(12, 14);
		var memberGroup = new flixel.group.FlxSpriteGroup(50, 60);
		var cleanup = function() {
			if (nativeTween != null) nativeTween.cancel();if (nativeGroup != null) nativeGroup.destroy();
			if (spriteGroup != null) spriteGroup.destroy();
			memberGroup.destroy();
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
			plain.variables.set('nativeSpriteGroup', spriteGroup);
			plain.evaluate('import demo.NativeSprite; sourceSpriteProbe=new NativeSprite(); spriteAddProbe=nativeSpriteGroup.add(sourceSpriteProbe); spriteIndexProbe=nativeSpriteGroup.members[0];', 'sprite-group-probe');
			var sourceSprite = plain.variables.get('sourceSpriteProbe');
			check(plain.variables.get('spriteAddProbe') == sourceSprite && plain.variables.get('spriteIndexProbe') == sourceSprite, 'Native sprite group source identity');
			spriteGroup.update(0.1);spriteGroup.draw();spriteGroup.x += 4;
			plain.evaluate('sourceSpriteProbe.update(0.1);', 'sprite-direct-update');
			check(session.read(sourceSprite, 'ticks') == 2 && session.read(sourceSprite, 'draws') == 1, 'Native source sprite callbacks and explicit super run once');
			check(spriteGroup.members[0].x == 20 && spriteGroup.members[0].y == 17 && spriteGroup.members[0].frameWidth == 8, 'Native sprite transform, motion and graphic preserved');
			plain.evaluate('import demo.NativePanel; sourcePanelProbe=new NativePanel(); panelAddProbe=nativeSpriteGroup.add(sourcePanelProbe);', 'native-text-panel-probe');
			var sourcePanel = plain.variables.get('sourcePanelProbe');
			var sourceLabel = session.read(sourcePanel, 'label');
			var nativePanel:flixel.group.FlxSpriteGroup = cast spriteGroup.members[1];
			var nativeLabel:flixel.text.FlxText = cast nativePanel.members[0];
			check(plain.variables.get('panelAddProbe') == sourcePanel && session.nativeValue(nativeLabel) == sourceLabel, 'Native nested text/group identity');
			nativePanel.update(0.1);nativePanel.draw();
			check(session.read(sourcePanel, 'ticks') == 1 && session.read(sourcePanel, 'draws') == 1
				&& session.read(sourceLabel, 'ticks') == 1 && session.read(sourceLabel, 'draws') == 1, 'Native nested source callbacks and super traversal once');
			check(nativePanel.x == 26 && nativeLabel.x == 29 && nativeLabel.y == 38
				&& nativeLabel.size == 14 && !nativeLabel.textField.embedFonts && nativeLabel.frameWidth > 0, 'Native text constructor and nested transforms');
			plain.evaluate('sourcePanelProbe.label.text="updated native text";', 'native-text-change');
			nativePanel.draw();
			check(nativeLabel.textField.text == 'updated native text', 'Source text writes use native formatting/rendering');
			plain.variables.set('memberProbeGroup', memberGroup);
			plain.evaluate('capturedSpriteRecycle=memberProbeGroup.recycle; recycledSprite=capturedSpriteRecycle(NativeSprite);', 'sprite-recycle-probe');
			var recycledSprite = plain.variables.get('recycledSprite');
			check(memberGroup.members[0].x == 2 && memberGroup.members[0].y == 3, 'Sprite-group recycle preserves native no-preAdd behavior');
			memberGroup.members[0].kill();
			plain.evaluate('reusedSprite=capturedSpriteRecycle(NativeSprite); replacementSprite=new NativeSprite(); capturedReplace=Reflect.field(memberProbeGroup,"replace"); replacedSprite=Reflect.callMethod(memberProbeGroup,capturedReplace,[reusedSprite,replacementSprite]);', 'sprite-replacement-probe');
			check(plain.variables.get('reusedSprite') == recycledSprite && plain.variables.get('replacedSprite') == plain.variables.get('replacementSprite')
				&& memberGroup.members[0].x == 52 && memberGroup.members[0].y == 63, 'Reflected replacement applies native group transforms once');
			plain.evaluate('rawMembers=memberProbeGroup.members; writeResult=rawMembers[0]=recycledSprite; memberTicks=0; for (value in rawMembers) memberTicks+=value.ticks; memberKeys=0; for (key=>value in rawMembers) {memberKeys+=key+1; memberTicks+=value.ticks;} rawMembers[0].ticks=7;', 'sprite-member-array-probe');
			check(plain.variables.get('writeResult') == recycledSprite && plain.variables.get('memberTicks') == 0
				&& plain.variables.get('memberKeys') == 1 && session.read(recycledSprite, 'ticks') == 7
				&& memberGroup.members[0].x == 2, 'Raw indexed writes and both loops preserve source identity without add transforms');
			memberGroup.members[0].kill();
			plain.evaluate('factoryReused=memberProbeGroup.recycle(null,function() {return new NativeSprite();});', 'sprite-factory-recycle-probe');
			check(plain.variables.get('factoryReused') == recycledSprite, 'Factory-only recycle reuses native available source member');
			plain.evaluate('import demo.ExtraStage; createdStageProbe=new ExtraStage();', 'stage-probe');
			var stage = plain.variables.get('createdStageProbe');
			check(state.stages.length == 2 && state.stages[0] == stage, 'Automatic source stage/native helper registration: count=' + state.stages.length + ', found=' + (stage != null));
			plain.release();runtime.release();
			state.stagesFunc(function(value) PsychStageObject.call(value, 'stepHit', []));
			check(session.read(stage, 'ticks') == 11, 'Native source callback survives both scripts closing');
			nativeGroup.update(0.1);nativeGroup.destroy();nativeGroup = null;
			check(session.read(member, 'ticks') == 2 && session.read(member, 'destroyed') == 1, 'Native source member survives script closure and destroys once');
			spriteGroup.update(0.1);spriteGroup.destroy();spriteGroup = null;
			check(session.read(sourceSprite, 'ticks') == 3 && session.read(sourceSprite, 'destroyed') == 1, 'Source sprite survives script closure and destroys once');
			check(session.read(sourcePanel, 'ticks') == 2 && session.read(sourceLabel, 'ticks') == 2
				&& session.read(sourcePanel, 'destroyed') == 1 && session.read(sourceLabel, 'destroyed') == 1
				&& nativeLabel.textField == null && nativePanel.group == null, 'Source text/group native teardown after script closure');
			state.stagesFunc(function(value) PsychStageObject.call(value, 'destroy', []));
			session.release();
			var rejected = false;try session.read(item, 'count') catch (_:Dynamic) rejected = true;
			check(rejected, 'State session release rejects retained objects');
			@:privateAccess RuntimeSmokeHarness.emit('psych_iris_classes_native_verified', {
				memberArrayWrites:true,memberArrayLoops:true,spriteGroupReplacement:true,spriteGroupRecycle:true,sourceTextLifecycle:true,sourceGroupLifecycle:true,variadicSuper:true,sourceSpriteLifecycle:true,sourceSpriteTransforms:true,crossOwnerRecycle:true,nativeGroups:true,nativeTweens:true,capturedMethods:true,reflectedMethods:true,indexedIdentity:true,plainPreset:true,embeddedPreset:true,sharedIdentity:true,sharedStatics:true,sourceStage:true,scriptClose:true,orderedDestroy:true,releasedOwner:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
