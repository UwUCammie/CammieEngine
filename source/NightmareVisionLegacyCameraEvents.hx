package;

import flixel.FlxG;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxEase;
import flixel.util.FlxColor;

/** Historical event arguments and handle ownership over native camera/tween services. */
@:access(PlayState)
class NightmareVisionLegacyCameraEvents {
	var state:PlayState;
	var owned:Array<FlxTween> = [];
	public function new(state:PlayState) this.state = state;

	function cancel(tween:FlxTween):Void {
		if (tween == null) return;
		tween.cancel();
		owned.remove(tween);
	}
	function tween(target:Dynamic, values:Dynamic, duration:Float, ease:Float->Float, complete:Void->Void):FlxTween {
		var created = FlxTween.tween(target, values, duration, {ease:ease, onComplete:function(t:FlxTween) {
			owned.remove(t);
			complete();
		}});
		owned.push(created);
		return created;
	}
	/** Only this state's still-managed event tweens participate in its pause. */
	public function setActive(active:Bool):Void {
		FlxTween.globalManager.forEach(function(t:FlxTween) {
			if (owned.indexOf(t) >= 0 && !t.finished) t.active = active;
		});
	}
	public function destroy():Void {
		for (t in owned.copy()) cancel(t);
		state.camTween = null;
		state.camHUDAlphaTween = null;
		state.songSpeedTween = null;
		state = null;
	}
	/** False is the source triggerEventNote early return, including notifications. */
	public function changeScrollSpeed(value1:String, value2:String):Bool {
		if (state.songSpeedType == 'constant') return false;
		var multiplier = Std.parseFloat(value1);
		var duration = Std.parseFloat(value2);
		if (Math.isNaN(multiplier)) multiplier = 1;
		if (Math.isNaN(duration)) duration = 0;
		var target = PlayState.SONG.speed * state.nightmareVisionPrefs.getGameplaySetting('scrollspeed', 1) * multiplier;
		if (duration <= 0) state.songSpeed = target;
		else state.songSpeedTween = tween(state, {songSpeed:target}, duration, FlxEase.linear,
			function() state.songSpeedTween = null);
		return true;
	}
	/** Reenter the normal event dispatcher so callbacks can mutate this live chain. */
	public static function consumeBeat(state:PlayState):Void {
		if (state.totalBeat > 0 && state.curBeat % state.timeBeat == 0) {
			state.triggerEventNote('Add Camera Zoom', '' + state.gameZ, '' + state.hudZ);
			state.totalBeat -= 1;
			if (state.shakeTime) {
				state.triggerEventNote('Screen Shake', (((1 / (Conductor.bpm / 60)) / 2) * state.timeBeat) + ', ' + state.gameShake,
					(((1 / (Conductor.bpm / 60)) / 2) * state.timeBeat) + ', ' + state.hudShake);
			}
		}
	}
	public function apply(name:String, value1:String, value2:String):Bool {
		switch (name) {
			case 'Game Flash':
				var duration = Std.parseFloat(value2);
				if (Math.isNaN(duration)) duration = 0.5;
				FlxG.camera.flash(FlxColor.fromString(value1), duration);
			case 'Add Camera Zoom':
				if (state.nightmareVisionPrefs.view.camZooms && FlxG.camera.zoom < 1.35) {
					var game = Std.parseFloat(value1);
					var hud = Std.parseFloat(value2);
					if (Math.isNaN(game)) game = 0.015;
					if (Math.isNaN(hud)) hud = 0.03;
					FlxG.camera.zoom += game;
					state.camHUD.zoom += hud;
				}
			case 'Camera Zoom':
				cancel(state.camTween);
				state.camTween = null;
				var multiplier = Std.parseFloat(value1);
				if (Math.isNaN(multiplier)) multiplier = 1;
				var target = state.defaultCamZoom * multiplier;
				if (value2 != '') {
					var split = value2.split(',');
					var duration = split[0] == null ? 0 : Std.parseFloat(StringTools.trim(split[0]));
					if (Math.isNaN(duration)) duration = 0;
					// The pinned source parses the authored ease but always uses circOut.
					if (duration > 0) state.camTween = tween(FlxG.camera, {zoom:target}, duration, FlxEase.circOut,
						function() state.camTween = null);
					else FlxG.camera.zoom = target;
				}
				state.defaultCamZoom = target;
				var registry = state.legacyScriptRegistry();
				registry.setOnScripts('defaultCamZoom', target, registry.hscriptArray);
			case 'HUD Fade':
				state.sourceHudFade(value1, value2, function() {
					cancel(state.camHUDAlphaTween);state.camHUDAlphaTween = null;
				}, function(alpha, duration) {
					state.camHUDAlphaTween = tween(state.camHUD, {alpha:alpha}, duration, FlxEase.linear,
						function() state.camHUDAlphaTween = null);
				});
			case 'Camera Follow Pos':
				state.sourceCameraFollowPosition(value1, value2);
			case 'Screen Shake':
				var values = [value1, value2];var cameras = [state.camGame, state.camHUD];
				for (i in 0...cameras.length) {
					var split = values[i].split(',');
					var duration = split[0] == null ? 0 : Std.parseFloat(StringTools.trim(split[0]));
					var intensity = split[1] == null ? 0 : Std.parseFloat(StringTools.trim(split[1]));
					if (Math.isNaN(duration)) duration = 0;
					if (Math.isNaN(intensity)) intensity = 0;
					if (duration > 0 && intensity != 0) cameras[i].shake(intensity, duration);
				}
			case 'Camera Zoom Chain':
				var split = value1.split(',');
				var game = Std.parseFloat(StringTools.trim(split[0]));
				var hud = Std.parseFloat(StringTools.trim(split[1]));
				// The historical source resets valid amplitudes to these defaults.
				if (!Math.isNaN(game)) state.gameZ = 0.015;
				if (!Math.isNaN(hud)) state.hudZ = 0.03;
				if (split.length == 4) {
					var gameShake = Std.parseFloat(StringTools.trim(split[2]));
					var hudShake = Std.parseFloat(StringTools.trim(split[3]));
					if (!Math.isNaN(gameShake)) state.gameShake = gameShake;
					if (!Math.isNaN(hudShake)) state.hudShake = hudShake;
					state.shakeTime = true;
				} else state.shakeTime = false;
				var timing = value2.split(',');
				var count:Int = Std.parseInt(StringTools.trim(timing[0]));
				var interval = Std.parseFloat(StringTools.trim(timing[1]));
				if (Math.isNaN(count)) count = 4;
				if (Math.isNaN(interval)) interval = 1;
				state.totalBeat = count;
				state.timeBeat = interval;
			case 'Screen Shake Chain':
				var split = value1.split(',');
				var game = Std.parseFloat(StringTools.trim(split[0]));
				var hud = Std.parseFloat(StringTools.trim(split[1]));
				if (!Math.isNaN(game)) state.gameShake = game;
				if (!Math.isNaN(hud)) state.hudShake = hud;
				var count:Int = Std.parseInt(value2);
				if (!Math.isNaN(count)) state.totalShake = 4;
				state.totalShake = count;
			case 'Set Cam Zoom':
				state.defaultCamZoom = Std.parseFloat(value1);
			case 'Set Cam Pos':
				var split = value1.split(',');
				var x = Std.parseFloat(StringTools.trim(split[0]));
				var y = Std.parseFloat(StringTools.trim(split[1]));
				if (Math.isNaN(x)) x = 0;
				if (Math.isNaN(y)) y = 0;
				var offsets = switch (value2) {
					case 'bf' | 'boyfriend': state.boyfriendCameraOffset;
					case 'gf' | 'girlfriend': state.girlfriendCameraOffset;
					case 'dad' | 'opponent': state.opponentCameraOffset;
					default: null;
				};
				if (offsets != null) {offsets[0] = x;offsets[1] = y;}
			default: return false;
		}
		return true;
	}
}
