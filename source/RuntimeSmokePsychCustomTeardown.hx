package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxState;

/** Destructive lifecycle check confined to an explicitly requested disposable run. */
@:access(PlayState)
class RuntimeSmokePsychCustomTeardown {
	public static var pending(default, null):Bool = false;
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function begin(state:PlayState):Void {
		#if sys
		if (Sys.getEnv('CAMMIE_PSYCH_SUBSTATE_TEARDOWN_SMOKE') != '1' || pending) return;
		#else
		return;
		#end
		check(state.subState == null && state.compatCustomSubstate == null, 'Teardown requires idle native substate');
		pending = true;
		var events:Array<String> = [];
		var mounted:PsychCustomSubstate = null;
		var queued:PsychCustomSubstate = null;
		var child = new FlxSprite().makeGraphic(1, 1, 0);
		var abandonedChild = new FlxSprite().makeGraphic(1, 1, 0);
		var lua = new LuaCompatInterp();
		var oldLegacy = state.nightmareVisionLegacyFieldCameras;
		state.nightmareVisionLegacyFieldCameras = false;
		new PsychSourceBindings(state).install(lua);
		state.nightmareVisionLegacyFieldCameras = oldLegacy;
		lua.variables.set('__psychScoreGlobals', true);
		lua.variables.set('events', events);
		lua.variables.set('checkParent', function() {
			check(mounted.members == null && child.animation == null, 'Mounted children destroyed before parent scripts');
			check(queued.members == null && abandonedChild.animation == null && !queued.lifecycleCreated, 'Queued target cancelled without creation');
			check(state.variables.get('__teardownChild') == child, 'Retained registry reference survives child disposal');
			check(PsychCustomSubstate.instance == null && state.compatCustomSubstate == null, 'Published and pending custom slots clear before parent scripts');
			events.push('parent');
		});
		lua.execute(new hscript.Parser().parseString('function onCustomSubstateCreate(n){events.push("create:"+n);return null;} function onCustomSubstateDestroy(n){events.push("destroy:"+n);return null;} function onResume(){events.push("resume");return null;} function onDestroy(){checkParent();return null;}', '__custom_teardown_callbacks'));
		state.hscriptStates.set('__custom_teardown_probe', lua);
		var direct = false;
		#if sys
		direct = Sys.getEnv('CAMMIE_PSYCH_SUBSTATE_TEARDOWN_DIRECT') == '1';
		#end
		var phase = 0;
		var tick:Void->Void = null;
		var finished:Void->Void = null;
		finished = function() {
			FlxG.signals.postStateSwitch.remove(finished);
			try {
				check(state.members == null && state.subState == null, 'Actual PlayState native destruction finished');
				check(events.join('|') == 'create:mounted|resume|destroy:queued|parent', 'Teardown callback order: '+events.join('|'));
				check(PsychCustomSubstate.instance == null, 'No stale published substate after native transition');
				pending = false;
				@:privateAccess RuntimeSmokeHarness.emit('psych_custom_teardown_native_verified', {directSourceOpen:direct,parentDestroyed:true, mountedDisposedBeforeScripts:true, queuedCancelled:true, retainedReference:true, callbackOrder:events.join('|')});
				RuntimeSmokeHarness.succeed();
			} catch (error:Dynamic) RuntimeSmokeHarness.fail('psych-custom-teardown', Std.string(error));
		};
		tick = function() {
			try {
				switch (phase++) {
					case 0:
						PsychCustomSubstate.openCustomSubstate('mounted', true);
						mounted = state.compatCustomSubstate;
					case 1:
						check(state.subState == mounted && PsychCustomSubstate.instance == mounted, 'Custom menu mounted before exit');
						state.variables.set('__teardownChild', child);
						PsychCustomSubstate.insertToCustomSubstate('__teardownChild');
						if (direct) {
							queued = new PsychCustomSubstate('queued');
							state.openSubState(queued);
						} else {
							PsychCustomSubstate.openCustomSubstate('queued');
							queued = state.compatCustomSubstate;
						}
						queued.add(abandonedChild);
						FlxG.signals.postUpdate.remove(tick);
						FlxG.signals.postStateSwitch.add(finished);
						state.transOut = null;
						FlxG.switchState(new FlxState());
					default: throw 'Unexpected teardown phase';
				}
			} catch (error:Dynamic) RuntimeSmokeHarness.fail('psych-custom-teardown', Std.string(error));
		};
		FlxG.signals.postUpdate.add(tick);
	}
}
