package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.util.FlxTimer;
import flixel.tweens.FlxTween;

/** Frame-driven checks on the actual mounted PlayState, enabled only by a smoke flag. */
@:access(PlayState)
@:access(flixel.FlxSubState)
class RuntimeSmokePsychCustomTransitions {
	public static var pending(default, null):Bool = false;
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function begin(state:PlayState):Void {
		#if sys
		if (Sys.getEnv('CAMMIE_PSYCH_SUBSTATE_TRANSITION_SMOKE') != '1' || pending) return;
		#else
		return;
		#end
		check(state.subState == null && state.compatCustomSubstate == null, 'Transition probe requires an idle substate slot');
		pending = true;
		var oldScripts=state.hscriptStates;var oldVars=state.variables;var oldStart=state.startTimer;
		var oldLegacy=state.nightmareVisionLegacyFieldCameras;var oldName=PsychCustomSubstate.name;var oldInstance=PsychCustomSubstate.instance;
		var oldUpdate=state.persistentUpdate;var oldDraw=state.persistentDraw;
		var tasks:Array<{task:Dynamic, active:Bool}>=[];
		FlxTimer.globalManager.forEach(function(task)tasks.push({task:task,active:task.active}));
		FlxTween.globalManager.forEach(function(task)tasks.push({task:task,active:task.active}));
		var countdown=new FlxTimer().start(60);var inactive=new FlxTimer().start(60);inactive.active=false;
		var tween=FlxTween.tween({value:0.0},{value:1.0},60);
		var menuTimers:Array<FlxTimer>=[];var events:Array<String>=[];
		var sprite=new FlxSprite().makeGraphic(1,1,0);var lua=new LuaCompatInterp();
		var first:PsychCustomSubstate=null;var replacement:PsychCustomSubstate=null;
		var phase=0;var frames=0;var totalFrames=0;var updates=0;var parentPosition=0.0;
		var tick:Void->Void=null;
		var cleanup=function(){
			FlxG.signals.postUpdate.remove(tick);
			countdown.cancel();countdown.destroy();inactive.cancel();inactive.destroy();tween.cancel();tween.destroy();
			for(timer in menuTimers){timer.cancel();timer.destroy();}
			if(sprite.animation!=null)sprite.destroy();
			for(entry in tasks)if(entry.task!=null&&!entry.task.finished)entry.task.active=entry.active;
			state.hscriptStates=oldScripts;state.variables=oldVars;state.startTimer=oldStart;state.nightmareVisionLegacyFieldCameras=oldLegacy;
			state.persistentUpdate=oldUpdate;state.persistentDraw=oldDraw;
			PsychCustomSubstate.name=oldName;PsychCustomSubstate.instance=oldInstance;lua.variables.clear();pending=false;
		};
		try {
			state.hscriptStates=[];state.variables=[];state.startTimer=countdown;
			state.nightmareVisionLegacyFieldCameras=false;new PsychSourceBindings(state).install(lua);state.nightmareVisionLegacyFieldCameras=oldLegacy;
			lua.variables.set('__psychScoreGlobals',true);lua.variables.set('events',events);
			lua.variables.set('makeMenuTimer',function(){menuTimers.push(new FlxTimer().start(60));});
			lua.variables.set('countUpdate',function(){updates++;});
			lua.execute(new hscript.Parser().parseString('function onCustomSubstateCreate(n){events.push("create:"+n);makeMenuTimer();return null;} function onCustomSubstateCreatePost(n){events.push("post:"+n);return null;} function onCustomSubstateUpdate(n,e){countUpdate();return null;} function onCustomSubstateDestroy(n){events.push("destroy:"+n);return null;} function onResume(){events.push("resume");return null;}', '__mounted_substate_callbacks'));
			state.hscriptStates.set('__mounted_substate_probe',lua);
			tick=function(){
				try {
					totalFrames++;frames++;
					if(frames<2)return;
					frames=0;
					switch(phase++) {
						case 0:
							PsychCustomSubstate.openCustomSubstate('discarded');var discarded=state.compatCustomSubstate;
							check(PsychCustomSubstate.instance==null&&!PsychCustomSubstate.closeCustomSubstate(),'Queued open remains unpublished');
							PsychCustomSubstate.openCustomSubstate('first',true);first=state.compatCustomSubstate;
							check(discarded.members==null&&events.length==0,'Replaced queued substate disposed without callbacks');
							check(state.paused&&!state.persistentUpdate&&!FlxG.sound.music.playing,'Native parent/audio pause');
							check(!countdown.active&&!inactive.active&&!tween.active,'All unfinished global tasks pause');
							parentPosition=Conductor.songPosition;
						case 1:
							check(state.subState==first&&first._parentState==state&&PsychCustomSubstate.instance==first,'Queued open mounts in the real parent');
							check(events.join('|')=='create:first|post:first'&&updates>0,'Substate callbacks keep running with parent paused');
							check(menuTimers[0].active,'New menu timer runs while parent is paused');
							parentPosition=Conductor.songPosition;
							state.variables.set('retained',sprite);check(PsychCustomSubstate.insertToCustomSubstate('retained'),'Mounted native insertion');
							PsychCustomSubstate.openCustomSubstate('replacement',false);replacement=state.compatCustomSubstate;
							check(PsychCustomSubstate.instance==first&&state.paused&&!menuTimers[0].active,'Replacement retains old publication and source pause');
						case 2:
							check(Conductor.songPosition==parentPosition,'Mounted parent song clock remains frozen');
							check(state.subState==replacement&&PsychCustomSubstate.instance==replacement&&first.members==null,'Mounted replacement disposes the previous substate');
							check(events.join('|')=='create:first|post:first|destroy:replacement|create:unnamed|post:unnamed','Source static-name ordering through replacement: '+events.join('|'));
							check(sprite.animation==null&&state.variables.get('retained')==sprite,'Native child lifetime preserves the registry reference');
							check(menuTimers[1].active&&PsychCustomSubstate.closeCustomSubstate(),'Published close requests native transition');
							check(!state.paused&&FlxG.sound.music.playing&&countdown.active&&inactive.active&&tween.active,'Close resumes audio and all unfinished tasks');
							check(PsychCustomSubstate.instance==replacement,'Close publication persists until native disposal');
						case 3:
							check(state.subState==null&&PsychCustomSubstate.instance==null&&state.compatCustomSubstate==null&&!state.compatCustomSubstateOpen,'Mounted close clears native and adapter state');
							check(events.join('|')=='create:first|post:first|destroy:replacement|create:unnamed|post:unnamed|resume|destroy:unnamed','Resume/destroy order: '+events.join('|'));
							check(Conductor.songPosition>=parentPosition,'Parent song clock resumes');
							@:privateAccess RuntimeSmokeHarness.emit('psych_custom_transitions_native_verified',{mounted:true,queuedReplacement:true,callbackClock:true,sourceNameOrder:true,nativeChildLifetime:true,retainedReference:true,audioPauseResume:true,countdownPauseResume:true,globalTasks:true,frames:totalFrames});
							cleanup();
						default: throw 'Unexpected custom transition phase';
					}
				} catch(error:Dynamic){cleanup();RuntimeSmokeHarness.fail('psych-custom-transition',Std.string(error));}
			};
			FlxG.signals.postUpdate.add(tick);
		} catch(error:Dynamic){cleanup();throw error;}
	}
}
