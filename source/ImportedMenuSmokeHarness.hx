package;

import flixel.FlxG;
import openfl.events.KeyboardEvent;

/** An explicit local plan drives real menu input and verifies every boundary.
 * No fixture/mod identity appears in production menu routing. */
@:access(CodenameImportedModsState)
@:access(PlayState)
@:access(CodenameScriptInterp)
@:access(HxcImportedState)
@:access(HxcImportedRuntime)
@:access(CodenameImportedState)
@:access(CodenameModStateRuntime)
@:access(HxcFreeplayRuntime)
class ImportedMenuSmokeHarness {
	static var plan:Array<Dynamic>;
	static var index:Int = 0;
	static var deadline:Float;
	static var lastAction:Float;
	static var originalOptions:String;
	static var originalVolume:Float;
	static var originalMute:Bool;
	static var deathVisit:PlayState;
	static var retries:Int = 0;
	static var completions:Int = 0;
	static var awaitingCompletion:Bool = false;
	static var nextAudioObservation:Float = 0;
	static var keyProbeFrames:Int = 0;
	static var keyProbe:String = "";
	static var keyReleaseFrames:Int = 0;
	static var keyReleaseCode:Int = 0;
	static var resourceOwners:Array<{interp:CodenameScriptInterp, state:String, timers:Array<flixel.util.FlxTimer>,
		tweens:Array<flixel.tweens.FlxTween>, sounds:Array<flixel.sound.FlxSound>}> = [];

	static function observeResources():Void {
		var scopes:Array<CodenameScriptInterp> = [];
		if (Std.isOfType(FlxG.state, HxcImportedState)) {
			var runtime = (cast FlxG.state:HxcImportedState).runtime;
			if (runtime != null && Std.isOfType(runtime.interp, CodenameScriptInterp)) scopes.push(cast runtime.interp);
		}
		if (Std.isOfType(FlxG.state, CodenameImportedState)) {
			var runtime = (cast FlxG.state:CodenameImportedState).runtime;
			if (runtime != null && runtime.interp != null) scopes.push(runtime.interp);
		}
		if (Std.isOfType(FlxG.state, NightmareVisionMusicBeatState)) {
			var source:NightmareVisionMusicBeatState = cast FlxG.state;
			for (script in source.scriptGroup.members) if (script != null && script.interp != null && script.interp.asyncResources != null)
				scopes.push(script.interp.asyncResources);
		}
		for (runtime in HxcFreeplayRuntime.activeRuntimes) for (scope in runtime.scopes)
			if (Std.isOfType(scope.interp, CodenameScriptInterp)) scopes.push(cast scope.interp);
		for (scope in scopes) {
			var known = false;
			for (entry in resourceOwners) if (entry.interp == scope) known = true;
			if (!known) resourceOwners.push({interp:scope, state:identity(), timers:scope.ownedTimers.copy(),
				tweens:scope.ownedTweens.copy(), sounds:scope.ownedSounds.copy()});
		}
		for (entry in resourceOwners) if (entry.interp.resourcesReleased) {
			for (timer in entry.timers) if (timer.active) throw 'Escaped timer after ' + entry.state;
			for (tween in entry.tweens) if (tween.active) throw 'Escaped tween after ' + entry.state;
			for (sound in entry.sounds) if (sound.playing) throw 'Escaped sound after ' + entry.state;
		}
	}

	public static function enabled():Bool {
		#if sys
		return Sys.getEnv('CAMMIE_MENU_SMOKE_PLAN') != null;
		#else
		return false;
		#end
	}
	public static function start():Void {
		#if sys
		if (!RuntimeSmokeSaveIsolation.installed) throw 'Menu smoke requires an isolated private save root';
		var path = Sys.getEnv('CAMMIE_MENU_SMOKE_PLAN');
		if (path == null || !StringTools.startsWith(path, 'tmp/') || path.indexOf('..') >= 0)
			throw 'Menu smoke plan must be below runtime tmp/';
		plan = cast haxe.Json.parse(sys.io.File.getContent(path));
		if (plan == null || plan.length == 0 || plan.length > 128) throw 'Invalid menu smoke plan';
		originalOptions = haxe.Json.stringify(OptionsHandler.options);
		originalVolume = FlxG.sound.volume; originalMute = FlxG.sound.muted;
		deadline = haxe.Timer.stamp() + 120; lastAction = haxe.Timer.stamp();
		FlxG.signals.postUpdate.add(tick);
		#end
	}
	static function identity():String {
		var state = FlxG.state;
		if (Std.isOfType(state, CodenameImportedState)) return 'codename:' + (cast state:CodenameImportedState).scriptPath;
		if (Std.isOfType(state, NightmareVisionMusicBeatState)) {
			var source:NightmareVisionMusicBeatState = cast state;
			return source.scripted ? 'nv:' + source.scriptName : Type.getClassName(Type.getClass(state));
		}
		if (Std.isOfType(state, HxcImportedState)) return 'psych:' + (cast state:HxcImportedState).factoryEntry.name;
		if (Std.isOfType(state, HxcImportedMenuState)) return 'psych:' + (cast state:HxcImportedMenuState).factoryEntry.name;
		return Type.getClassName(Type.getClass(state));
	}
	static function emit(kind:String, fields:Dynamic):Void {
		#if sys
		Reflect.setField(fields, 'event', kind); Reflect.setField(fields, 'index', index);
		Sys.println('MENU_SMOKE|' + haxe.Json.stringify(fields));
		#end
	}
	static function tick():Void {
		#if sys
		try {
			if (keyReleaseFrames > 0 && --keyReleaseFrames == 0)
				FlxG.stage.dispatchEvent(new KeyboardEvent(KeyboardEvent.KEY_UP, true, false, keyReleaseCode, keyReleaseCode));
			observeResources();
			if (awaitingCompletion && Std.isOfType(FlxG.state, PlayState) && haxe.Timer.stamp() >= nextAudioObservation) {
				var play:PlayState = cast FlxG.state;
				emit('audio-observation', {time:FlxG.sound.music == null ? null : FlxG.sound.music.time,
					playing:FlxG.sound.music != null && FlxG.sound.music.playing,
					callback:FlxG.sound.music != null && FlxG.sound.music.onComplete != null,
					clock:Conductor.songPosition, ending:play.endingSong, demo:play.demoMode,
					demoFinished:play.demoSongFinished, paused:play.paused, update:play.persistentUpdate});
				nextAudioObservation = haxe.Timer.stamp() + 1;
			}

			if (keyProbeFrames > 0 && Std.isOfType(FlxG.state, PlayState)) {
				var play:PlayState = cast FlxG.state;
				emit('input-observation', {key:keyProbe, escape:FlxG.keys.justPressed.ESCAPE,
					enter:FlxG.keys.justPressed.ENTER, nativePause:PlayerSettings.player1.controls.PAUSE,
					sourcePause:play.psychControls == null ? null : play.psychControls.PAUSE,
					canPause:play.canPause, countdown:play.startedCountdown, inCutscene:play.inCutscene,
					paused:play.paused, update:play.persistentUpdate, loader:SongLoadingScreen.active});
				keyProbeFrames--;
			}

			if (haxe.Timer.stamp() > deadline) throw 'Deadline at step ' + index + ', state ' + identity();
			if (index >= plan.length) {
				ImportedMenuEntry.release();
				if (haxe.Json.stringify(OptionsHandler.options) != originalOptions) throw 'Host options leaked';
				if (FlxG.sound.volume != originalVolume || FlxG.sound.muted != originalMute) throw 'Host audio preferences leaked';
				if (ImportedMenuEntry.activeOwnerRoots().length != 0) throw 'Owner resources remain after exit';
				observeResources();
				var engines:Dynamic = {psych:{timers:0, tweens:0, sounds:0}, nv:{timers:0, tweens:0, sounds:0}};
				for (entry in resourceOwners) {
					if (!entry.interp.resourcesReleased) throw 'Unreleased interpreter from ' + entry.state;
					var engine = StringTools.startsWith(entry.state, 'psych:') ? 'psych'
						: StringTools.startsWith(entry.state, 'nv:') ? 'nv' : '';
					if (engine == '') continue;
					var counts:Dynamic = Reflect.field(engines, engine);
					counts.timers += entry.timers.length; counts.tweens += entry.tweens.length; counts.sounds += entry.sounds.length;
				}
				emit('resource-summary', {resources:engines, trackers:resourceOwners.length});
				for (engine in ['psych', 'nv']) {
					var counts:Dynamic = Reflect.field(engines, engine);
					if (counts.timers < 1 || counts.tweens < 1 || counts.sounds < 1) throw 'Missing authored async resources for ' + engine;
				}
				if (retries < 2) throw 'Acceptance did not exercise both engines retries';
				if (completions < 2) throw 'Acceptance did not exercise both engines audio completion/results';
				emit('complete', {checks:index, retries:retries, completions:completions, resources:engines, allInterpretersReleased:true, state:identity()}); Sys.exit(0);
			}
			if (haxe.Timer.stamp() - lastAction < 0.25) return;
			var step = plan[index];
			if (identity() != step.state) return;
			// The loader temporarily exposes the target while preparing its scene.
			// Its input reset can consume a key before gameplay begins updating.
			if (SongLoadingScreen.active || SongLoadingScreen.preparing) return;
			if (Std.isOfType(FlxG.state, PlayState) && FlxG.state.subState == null) {
				var play:PlayState = cast FlxG.state;
				if (!play.startedCountdown || (step.resultProvider != true && !play.canPause) || play.paused) return;
			}

			var substate = FlxG.state.subState == null ? '' : Type.getClassName(Type.getClass(FlxG.state.subState));
			if (step.substate != null && substate != step.substate) return;
			if (step.retry == true) {
				if (FlxG.state == deathVisit || substate != '' || (cast FlxG.state:PlayState).isDead) return;
				retries++;
			}
			if (step.diagnostic == true && Std.isOfType(FlxG.state, CodenameImportedModsState)
				&& (cast FlxG.state:CodenameImportedModsState).details.text.indexOf('imported-menu-entry') < 0) return;
			if (step.action == 'complete-song') {
				var play:PlayState = cast FlxG.state;
				if (play.startingSong || FlxG.sound.music == null || !FlxG.sound.music.playing) return;
			}
			if (step.resultProvider == true) {
				var play:PlayState = cast FlxG.state;
				if (!play.endingSong || play.canPause) return;
				var providerReady = false;
				for (scope in play.defaultPsychGlobalScopes) {
					var interp = play.hscriptStates.get(scope);
					if (interp != null && interp.variables.get('songOver') == true && interp.variables.get('resultsOver') == false)
						providerReady = true;
				}
				if (!providerReady) return;
				emit('results-provider', {provider:PsychGlobalPackImporter.defaultProvider(), scopeCount:play.defaultPsychGlobalScopes.length});
			}
			if (step.completed == true) {completions++; awaitingCompletion = false;}
			var roots = ImportedMenuEntry.activeOwnerRoots();
			if (step.owner != null && !roots.contains(step.owner)) throw 'Missing owner lease: ' + step.owner;
			emit('state', {state:identity(), nativeClass:Type.getClassName(Type.getClass(FlxG.state)), substate:substate, owners:roots, action:step.action,
				loaderActive:SongLoadingScreen.active, gameplayReady:!Std.isOfType(FlxG.state, PlayState)
					|| ((cast FlxG.state:PlayState).startedCountdown && (cast FlxG.state:PlayState).canPause)});
			switch (step.action) {
				case 'launch':
					if (!Std.isOfType(FlxG.state, CodenameImportedModsState)) throw 'Launch requires picker';
					var picker:CodenameImportedModsState = cast FlxG.state;
					var found = false;
					for (position in 0...picker.entries.length) if (picker.entries[position].root == step.launchOwner) {
						picker.selected = position; found = true; break;
					}
					if (!found) throw 'Owner absent from real picker: ' + step.launchOwner;
					picker.launchSelected();
				case 'key': press(step.key);
				case 'complete-song':
					if (!Std.isOfType(FlxG.state, PlayState) || FlxG.sound.music.onComplete == null)
						throw 'Completion requires a real started gameplay instrumental callback';
					var play:PlayState = cast FlxG.state;
					play.health = 2; play.useVictoryScreen = true;
					awaitingCompletion = true; nextAudioObservation = 0;
					emit('await-audio-completion', {length:FlxG.sound.music.length, time:FlxG.sound.music.time, looped:FlxG.sound.music.looped});
				case 'exit-song':
					if (!Std.isOfType(FlxG.state, PlayState)) throw 'Expected gameplay';
					(cast FlxG.state:PlayState).compatExitSong();
				case 'game-over':
					if (!Std.isOfType(FlxG.state, PlayState)) throw 'Expected gameplay';
					deathVisit = cast FlxG.state;
					deathVisit.practiceMode = false; deathVisit.health = -1;
					deathVisit.doDeathCheck(true);
				case 'check':
				default: throw 'Unsupported menu smoke action: ' + step.action;
			}
			index++; lastAction = haxe.Timer.stamp();
		} catch (error:Dynamic) {emit('failure', {detail:Std.string(error), state:identity()}); Sys.exit(1);}
		#end
	}
	static function press(key:String):Void {
		var code:Int = switch (key) {
			case 'enter': openfl.ui.Keyboard.ENTER;
			case 'escape': openfl.ui.Keyboard.ESCAPE;
			case 'backspace': openfl.ui.Keyboard.BACKSPACE;
			case 'up': openfl.ui.Keyboard.UP;
			case 'down': openfl.ui.Keyboard.DOWN;
			case 'f': openfl.ui.Keyboard.F;
			case 'f10': openfl.ui.Keyboard.F10;
			default: throw 'Unsupported probe key: ' + key;
		};
		if (Std.isOfType(FlxG.state, PlayState)) {keyProbeFrames = 6; keyProbe = key;}
		FlxG.stage.dispatchEvent(new KeyboardEvent(KeyboardEvent.KEY_DOWN, true, false, code, code));
		keyReleaseCode = code; keyReleaseFrames = 2;
	}
}
