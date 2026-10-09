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
		state = null;
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
