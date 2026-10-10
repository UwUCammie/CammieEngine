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
		var renderCamera = new flixel.FlxCamera(0, 0, 64, 64, 1);
		var memberGroup = new flixel.group.FlxSpriteGroup(50, 60);
		var coreGroup = new flixel.group.FlxGroup.FlxTypedGroup<flixel.FlxBasic>();
		var reentrantOwner:CodenameScriptClassLoader.CodenameScriptClassLoad = null;
		var constructionOwner:CodenameScriptClassLoader.CodenameScriptClassLoad = null;
		var cleanup = function() {
			if (nativeTween != null) nativeTween.cancel();if (nativeGroup != null) nativeGroup.destroy();
			if (spriteGroup != null) spriteGroup.destroy();
			renderCamera.destroy();
			memberGroup.destroy();
			coreGroup.destroy();if (reentrantOwner != null) reentrantOwner.scope.release();
			if (constructionOwner != null) constructionOwner.scope.release();
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
			plain.evaluate('import demo.NativeSprite; import demo.NativeSpriteDerived; sourceSpriteProbe=new NativeSpriteDerived(); spriteAddProbe=nativeSpriteGroup.add(sourceSpriteProbe); spriteIndexProbe=nativeSpriteGroup.members[0];', 'sprite-group-probe');
			var sourceSprite = plain.variables.get('sourceSpriteProbe');
			check(session.read(sourceSprite, 'initCalls') == 1 && session.read(sourceSprite, 'derivedInit') == 1, 'Native constructor dispatches most-derived source initVars exactly once');
			check(plain.variables.get('spriteAddProbe') == sourceSprite && plain.variables.get('spriteIndexProbe') == sourceSprite, 'Native sprite group source identity');
			spriteGroup.members[0].cameras = [renderCamera];
			spriteGroup.update(0.1);spriteGroup.draw();spriteGroup.x += 4;
			plain.evaluate('sourceSpriteProbe.update(0.1);', 'sprite-direct-update');
			check(session.read(sourceSprite, 'ticks') == 2 && session.read(sourceSprite, 'draws') == 1, 'Native source sprite callbacks and explicit super run once');
			check(spriteGroup.members[0].x == 20 && spriteGroup.members[0].y == 17 && spriteGroup.members[0].frameWidth == 8, 'Native sprite transform, motion and graphic preserved');
			check(session.read(sourceSprite, 'complexDraws') == 4 && session.read(sourceSprite, 'inheritedProbe') == 7 && session.read(sourceSprite, 'lastCamera') == renderCamera,
				'Native draw reaches authored complex renderer with camera identity');
			@:privateAccess check(renderCamera._headOfDrawStack != null, 'Authored render super queues native geometry');
			var hookSprite = spriteGroup.members[0];
			hookSprite.scale.set(2, 3);hookSprite.updateHitbox();
			check(session.read(sourceSprite, 'hitboxes') == 1 && hookSprite.width == 16 && hookSprite.height == 24 && hookSprite.offset.x == 3,
				'Native hitbox uses authored adjustment after Flixel scaling');
			hookSprite.scale.set(1, 1);hookSprite.updateHitbox();

			plain.evaluate('import demo.NativePanel; sourcePanelProbe=new NativePanel(); panelAddProbe=nativeSpriteGroup.add(sourcePanelProbe);', 'native-text-panel-probe');
			var sourcePanel = plain.variables.get('sourcePanelProbe');
			var sourceLabel = session.read(sourcePanel, 'label');
			check(session.read(sourcePanel, 'initCalls') == 1 && session.read(sourceLabel, 'initCalls') == 1 && session.read(sourceLabel, 'frameCalls') > 0, 'Native group/text constructors retain source initialization and frame hooks');
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
			plain.evaluate('rawMembers.resize(0); capturedArrayPush=Reflect.field(rawMembers,"push"); Reflect.callMethod(rawMembers,capturedArrayPush,[recycledSprite]); rawMembers.unshift(replacementSprite); rawMembers.insert(1,recycledSprite); sourceIterator=rawMembers.iterator(); iteratorIdentity=sourceIterator.next()==replacementSprite; pairIdentity=rawMembers.keyValueIterator().next().value==replacementSprite; arrayMapped=rawMembers.map(function(value) {return value.ticks;}).join(":"); arrayFiltered=rawMembers.filter(function(value) {return value.ticks>0;})[0]==recycledSprite; rawMembers.sort(function(left,right) {return left.ticks-right.ticks;}); arrayPopped=rawMembers.pop()==recycledSprite; arrayShifted=rawMembers.shift()==replacementSprite; arraySpliced=rawMembers.splice(0,1)[0]==recycledSprite; innerMemberGroup=memberProbeGroup.group; replacementMembers=[replacementSprite,recycledSprite]; Reflect.setProperty(innerMemberGroup,"members",replacementMembers); replacementIdentity=innerMemberGroup.members==replacementMembers; retainedArrayIterator=innerMemberGroup.members.iterator();', 'source-array-helpers-probe');
			for (key in ['iteratorIdentity', 'pairIdentity', 'arrayFiltered', 'arrayPopped', 'arrayShifted', 'arraySpliced', 'replacementIdentity'])
				check(plain.variables.get(key) == true, 'Native array operation source identity: ' + key);
			check(plain.variables.get('arrayMapped') == '0:7:7' && memberGroup.members[0].x == 52
				&& memberGroup.members[1].x == 2, 'Array callbacks and whole replacement retain source data and native storage');
			var retainedArrayIterator:Dynamic = plain.variables.get('retainedArrayIterator');
			plain.evaluate('import flixel.FlxObject; nativeMemberProbe.kill(); sourceClassAvailable=nativeProbeGroup.getFirstAvailable(NativeMember)==nativeMemberProbe; nativeClassAvailable=nativeProbeGroup.getFirstAvailable(FlxObject)==nativeMemberProbe; exactNativeExcluded=nativeProbeGroup.getFirstAvailable(FlxObject,true)==null; nativeReused=nativeProbeGroup.recycle(FlxObject)==nativeMemberProbe; queryFirst=nativeProbeGroup.getFirst(function(value) {return value.ticks==1;})==nativeMemberProbe; queryLastIndex=nativeProbeGroup.getLastIndex(function(value) {return value.ticks==1;}); queryTypedIdentity=false; nativeProbeGroup.forEachOfType(FlxObject,function(value) {queryTypedIdentity=value==nativeMemberProbe;}); queryIterator=nativeProbeGroup.iterator(function(value) {return value.ticks==1;}); queryIteratorIdentity=queryIterator.next()==nativeMemberProbe; queryPairIdentity=nativeProbeGroup.keyValueIterator().next().value==nativeMemberProbe; memberProbeGroup.sort(function(order,left,right) {return order*(left.ticks-right.ticks);},-1); querySortIdentity=memberProbeGroup.members[0]==recycledSprite;', 'source-group-query-probe');
			for (key in ['sourceClassAvailable', 'nativeClassAvailable', 'exactNativeExcluded', 'nativeReused', 'queryFirst', 'queryTypedIdentity', 'queryIteratorIdentity', 'queryPairIdentity', 'querySortIdentity'])
				check(plain.variables.get(key) == true, 'Native group query contract: ' + key);
			check(plain.variables.get('queryLastIndex') == 0 && nativeGroup.length == 1, 'Native predicate index and recycling length');
			var retainedGroupIterator:Dynamic = plain.variables.get('queryIterator');
			plain.variables.set('coreProbeGroup', coreGroup);
			plain.evaluate('import demo.NativeCluster; coreSource=new NativeCluster(); coreProbeGroup.add(coreSource); coreVisited=0; coreProbeGroup.forEachOfType(FlxObject,function(value) {coreVisited++;},true);', 'source-core-bases-probe');
			var coreSource = plain.variables.get('coreSource');
			var coreBasic = session.read(coreSource, 'basic'), coreActor = session.read(coreSource, 'actor');
			var coreNative:PsychScriptClassGroup = cast coreGroup.members[0];
			var coreNativeActor:PsychScriptClassObject = cast coreNative.members[1];
			check(Std.isOfType(coreNative.members[0], PsychScriptClassBasic) && plain.variables.get('coreVisited') == 1, 'Native core class identities and recursive source group traversal');
			coreGroup.update(0.1);coreNative.kill();coreNative.revive();
			plain.evaluate('coreSource.basic.kill();', 'source-basic-direct-kill');
			check(!coreNative.members[0].exists && session.read(coreBasic, 'kills') == 2 && session.read(coreBasic, 'revives') == 1
				&& session.read(coreBasic, 'ticks') == 1 && session.read(coreActor, 'ticks') == 1, 'Shared core callbacks and immediate native state');
			coreNative.destroy();
			check(coreNative.members == null && coreNativeActor.velocity == null && session.read(coreBasic, 'destroyed') == 1
				&& session.read(coreActor, 'destroyed') == 1, 'Killed core members release native resources exactly once');
			reentrantOwner = CodenameScriptClassLoader.load(root, ['demo.NativeCluster'], ['flixel.FlxBasic'=>flixel.FlxBasic,
				'flixel.FlxObject'=>flixel.FlxObject, 'flixel.group.FlxGroup'=>flixel.group.FlxGroup.FlxTypedGroup], new Map());
			check(reentrantOwner.diagnostics.length == 0, 'Reentrant native owner imports');
			var reentrantSource = reentrantOwner.scope.createInstance('demo.NativeCluster');
			@:privateAccess var reentrantNative:PsychScriptClassGroup = cast reentrantOwner.scope.unwrapOwnedFlxBasic(reentrantSource);
			var reentrantBasic:PsychScriptClassBasic = cast reentrantNative.members[0];
			var reentrantSourceBasic = reentrantBasic.scriptOwner();
			var continued = false, reentrantDestroyed = 0;
			@:privateAccess reentrantSourceBasic._interp.variables.set('onUpdate', function() {reentrantOwner.scope.release();continued = reentrantOwner.scope.isActive();});
			@:privateAccess reentrantSourceBasic._interp.variables.set('onDestroy', function() {reentrantDestroyed++;reentrantOwner.scope.release();});
			reentrantNative.update(0.1);reentrantNative.update(0.1);reentrantNative.destroy();
			constructionOwner = CodenameScriptClassLoader.load(root, ['demo.NativeConstructionRelease'], ['flixel.FlxObject'=>flixel.FlxObject], new Map());
			check(constructionOwner.diagnostics.length == 0, 'Constructor release probe imports');
			var constructionLive = false, constructionComplete = false, constructionDestroyed = 0;
			var heldConstruction:Dynamic = null;
			constructionOwner.scope.seed('constructorRelease', function(value:Dynamic) {
				heldConstruction = value;constructionOwner.scope.release();constructionLive = constructionOwner.scope.isActive();
			});
			constructionOwner.scope.seed('constructorDestroyed', function(complete:Bool) {constructionComplete = complete;constructionDestroyed++;});
			var constructionRejected = false;
			try constructionOwner.scope.createInstance('demo.NativeConstructionRelease') catch (error:Dynamic)
				constructionRejected = Std.string(error).indexOf('released') >= 0;
			var heldNative:flixel.FlxObject = cast (cast heldConstruction:hscript.ScriptClass).superClass;
			check(constructionRejected && constructionLive && constructionComplete && constructionDestroyed == 1 && heldNative.velocity == null,
				'Constructor teardown waits for completion, destroys once and rejects disposed results');

			check(continued && !reentrantOwner.scope.isActive() && reentrantDestroyed == 1 && reentrantNative.members == null,
				'Native callback release is deferred, nonrecursive and leaves inert adapters');
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
			rejected = false;try retainedArrayIterator.hasNext() catch (_:Dynamic) rejected = true;
			check(rejected, 'Released owner rejects retained native array iterators');
			rejected = false;try retainedGroupIterator.hasNext() catch (_:Dynamic) rejected = true;
			check(rejected, 'Released owner rejects retained native group iterators');
			@:privateAccess RuntimeSmokeHarness.emit('psych_iris_classes_native_verified', {
				nativeConstructionHooks:true,derivedConstructionHooks:true,textConstructionFrameHook:true,constructionRelease:true,inheritedSourceFieldWrites:true,nativeSpriteRenderHooks:true,nativeSpriteHitboxHook:true,coreNativeBases:true,recursiveSourceGroups:true,coreKillRevive:true,killedNativeCleanup:true,reentrantNativeRelease:true,groupClassFilters:true,groupPredicates:true,groupIterators:true,groupSort:true,memberArrayHelpers:true,memberArrayReplacement:true,memberArrayIterators:true,memberArrayWrites:true,memberArrayLoops:true,spriteGroupReplacement:true,spriteGroupRecycle:true,sourceTextLifecycle:true,sourceGroupLifecycle:true,variadicSuper:true,sourceSpriteLifecycle:true,sourceSpriteTransforms:true,crossOwnerRecycle:true,nativeGroups:true,nativeTweens:true,capturedMethods:true,reflectedMethods:true,indexedIdentity:true,plainPreset:true,embeddedPreset:true,sharedIdentity:true,sharedStatics:true,sourceStage:true,scriptClose:true,orderedDestroy:true,releasedOwner:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
