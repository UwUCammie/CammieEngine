package;

import PsychFlxCameraCompat.PsychFlxGCompat;

/**
	Psych's source classes use a singleton Controls surface. This view resolves
	the active play state's native controls first and falls back to player one,
	without creating or persisting separate input settings.
*/
class PsychControlsCompat {
	static var _instance:PsychControlsCompat;
	final providedControls:Dynamic;

	public static var instance(get, never):PsychControlsCompat;
	static function get_instance():PsychControlsCompat {
		if (_instance == null) _instance = new PsychControlsCompat();
		return _instance;
	}

	/** Optional native-control source is used by compatibility tests and hosts. */
	public function new(?providedControls:Dynamic) {
		this.providedControls = providedControls;
	}

	/** Psych's pressed(name) asks whether the configured action is active. */
	public function pressed(name:String):Bool {
		#if cpp
		// The native MusicBeatState controls accessor is private and inline;
		// reflection cannot reliably discover it from a source-class facade.
		// Use the same live action set directly so custom key bindings apply.
		if (providedControls == null && PlayerSettings.player1 != null
			&& PlayerSettings.player1.controls != null && name != null)
			return PlayerSettings.player1.controls.pressedByName(cast name);
		#end
		var controls = providedControls == null ? resolveControls() : providedControls;
		if (controls == null || name == null) return false;
		var check = Reflect.field(controls, 'checkByName');
		if (Reflect.isFunction(check))
			return cast Reflect.callMethod(controls, check, [cast name]);
		// Keep the source call useful when a host exposes Psych's own Controls API
		// rather than this engine's checkByName spelling.
		var pressed = Reflect.field(controls, 'pressed');
		return Reflect.isFunction(pressed)
			? cast Reflect.callMethod(controls, pressed, [name]) : false;
	}

	function resolveControls():Dynamic {
		var state:Dynamic = null;
		try state = PsychFlxGCompat.state catch (_:Dynamic) {}
		if (state != null) {
			var controls:Dynamic = null;
			try controls = Reflect.getProperty(state, 'controls') catch (_:Dynamic) {}
			if (controls != null) return controls;
		}
		var settingsClass:Dynamic = Type.resolveClass('PlayerSettings');
		if (settingsClass == null) return null;
		var player:Dynamic = null;
		try player = Reflect.getProperty(settingsClass, 'player1') catch (_:Dynamic) {}
		if (player == null) return null;
		try return Reflect.getProperty(player, 'controls') catch (_:Dynamic) return null;
	}
}
