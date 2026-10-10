package;

import flixel.FlxG;
import flixel.FlxBasic;

/** Reversible native checks for the distinct source stage roots. */
@:access(PlayState)
@:access(flixel.FlxGame)
class RuntimeSmokePsychStageContext {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState):Void {
		#if sys
		if (Sys.getEnv('CAMMIE_PSYCH_STAGE_CONTEXT_SMOKE') != '1') return;
		#else
		return;
		#end
		var active = FlxG.game._state, oldPlay = PlayState.instance;
		var oldSong = PlayState.SONG, oldStory = PlayState.isStoryMode, oldSeen = PlayState.watchedCutscene;
		var other = new MusicBeatState();
		var play:PlayState = Type.createEmptyInstance(PlayState);
		var view = new PsychBaseStageCompat(state);
		view.attachContext(PsychObjectProviders.stageContext());
		var object = new FlxBasic();
		var runtime:PsychCompiledStageRuntime = null;
		var factoryRuntime:PsychCompiledStageRuntime = null;
		var iris = new SourceIrisBridge(state);
		var nativeScope = new SourceNativeClassScope();
		var direct:Array<PsychBaseStageCompat> = [];
		var cleanup = function() {
			if (runtime != null) runtime.destroy();
			if (factoryRuntime != null) factoryRuntime.destroy();
			for (stage in direct) stage.destroy();
			iris.release();nativeScope.release();
			other.remove(object, true);object.destroy();view.destroy();
			FlxG.game._state = active;PlayState.instance = oldPlay;
			PlayState.SONG = oldSong;PlayState.isStoryMode = oldStory;PlayState.watchedCutscene = oldSeen;
			other.destroy();
		};
		try {
			PlayState.instance = play;
			var callback = function() {};
			view.setStartCallback(callback);view.setEndCallback(callback);
			check(play.psychStageStartCallback == callback && play.psychStageEndCallback == callback, 'Stage callbacks use live PlayState.instance');
			FlxG.game._state = other;
			check(view.game == other && !view.onPlayState, 'Stage game follows active native state');
			play.psychStageStartCallback = null;play.psychStageEndCallback = null;
			view.setStartCallback(callback);view.setEndCallback(callback);
			check(play.psychStageStartCallback == null && play.psychStageEndCallback == null
				&& view.startCountdown() == false && view.endSong() == false, 'Non-gameplay state gates gameplay helpers');
			view.moveCamera(true);view.moveCameraSection();
			other.variables.set('__stage_context', 73);
			check(view.getStageObject('__stage_context') == 73 && view.getStageObject('__missing_stage_context') == null, 'Stage object uses live typed variable map');
			check(view.add(object) == object && other.members.indexOf(object) >= 0, 'Stage scene insertion follows active state');
			check(view.remove(object, true) == object && other.members.indexOf(object) < 0, 'Stage removal follows active state');
			PlayState.isStoryMode = true;PlayState.watchedCutscene = true;
			check(view.isStoryMode && view.seenCutscene, 'PlayState statics remain available outside gameplay');
			PlayState.SONG = cast {gfVersion:''};view.setDefaultGF('probe-gf');
			check(Reflect.field(PlayState.SONG, 'gfVersion') == 'probe-gf', 'Stage default GF fills an empty static value');
			view.setDefaultGF('replacement');check(Reflect.field(PlayState.SONG, 'gfVersion') == 'probe-gf', 'Stage default GF preserves authored value');
			var log:Array<String> = [];
			var bindings:Map<String, Dynamic> = ['record' => function(value:String):Void {log.push(value);}];
			runtime = new PsychCompiledStageRuntime('tmp/source-stage-callback-probe', 'demo.ConstructorProbe', state, bindings, null, PsychObjectProviders.stageContext());
			check(runtime.create(), 'Stage construction in active alternate state: ' + runtime.diagnostics.join('; '));
			check(other.stages.length == 2 && other.stages[0] == runtime.sourceObject
				&& log.join('|') == 'child-before|middle-before|create:0|leaf:1|middle-after|child-after', 'Nested stage registration follows active state without changing asset owner');
			PsychStateClassBindings.installScope(nativeScope);
			PsychStateClassBindings.installScope(nativeScope);
			var unrelated:Dynamic = nativeScope.createInstance(FlxBasic, []);
			check(Type.getClass(unrelated) == FlxBasic && unrelated.exists, 'Factory chain preserves unrelated native class identity');
			unrelated.destroy();
			var reflected:PsychBaseStageCompat = nativeScope.createInstance(nativeScope.resolveClass('backend.BaseStage'), []);
			direct.push(reflected);
			check(other.stages[2] == reflected && reflected.game == other && reflected.exists, 'Reflection stage registers once in current state');
			PsychStateClassBindings.install(iris.evaluator);
			iris.variables.set('Type', Type);
			iris.variables.set('directStage', null);iris.variables.set('reflectedStage', null);
			iris.evaluate('import backend.BaseStage; directStage = new BaseStage(); reflectedStage = Type.createInstance(Type.resolveClass("backend.BaseStage"), []);', '__source_direct_stage');
			var scripted:PsychBaseStageCompat = iris.variables.get('directStage');
			var scriptedReflection:PsychBaseStageCompat = iris.variables.get('reflectedStage');
			direct.push(scripted);direct.push(scriptedReflection);
			check(scripted != null && scriptedReflection != null && other.stages.length == 5
				&& other.stages[3] == scripted && other.stages[4] == scriptedReflection, 'Iris construction and reflection share stage registration');
			check(Type.getClass(scripted) == PsychBaseStageCompat && scripted.game == other, 'Direct stage retains native identity and live roots');
			other.add(object);
			check(scripted.add(view) == view && other.members.indexOf(view) > other.members.indexOf(object), 'Direct stage uses normal native scene order');
			other.remove(view, true);other.remove(object, true);
			factoryRuntime = new PsychCompiledStageRuntime('tmp/source-stage-callback-probe', 'demo.FactoryProbe', state, null, null, PsychObjectProviders.stageContext());
			check(factoryRuntime.create(), 'Source-class native constructor: ' + factoryRuntime.diagnostics.join('; '));
			check(other.stages.length == 7 && other.stages[5] == factoryRuntime.sourceObject
				&& Std.isOfType(other.stages[6], PsychBaseStageCompat), 'Native construction inside a source method shares registration');
			var nestedNative:PsychBaseStageCompat = other.stages[6];factoryRuntime.destroy();
			check(!nestedNative.exists, 'Source owner releases nested native stage lifetime');
			@:privateAccess RuntimeSmokeHarness.emit('psych_direct_stage_native_verified', {reflection:true,irisConstructor:true,irisReflection:true,singleRegistration:true,liveContext:true,nativeIdentity:true,nestedNative:true,ownedCleanup:true});
			@:privateAccess RuntimeSmokeHarness.emit('psych_stage_context_native_verified', {activeState:true,playInstance:true,gates:true,statics:true,typedRegistry:true,sceneMembership:true,nestedRegistration:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
