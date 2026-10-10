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
		var cleanup = function() {
			if (runtime != null) runtime.destroy();
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
			@:privateAccess RuntimeSmokeHarness.emit('psych_stage_context_native_verified', {activeState:true,playInstance:true,gates:true,statics:true,typedRegistry:true,sceneMembership:true,nestedRegistration:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
