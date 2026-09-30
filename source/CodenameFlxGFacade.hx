package;

import flixel.FlxCamera;
import flixel.FlxBasic;
import flixel.FlxG;
import flixel.FlxState;
import flixel.math.FlxRect;

/** Interpreter-local FlxG view. Camera mutations stay in the owning scope. */
class CodenameFlxGFacade {
	public final cameras:CodenameCameraFacade;
	public final worldBounds:FlxRect;
	/** Codename save data is isolated under the selected import owner. */
	public final save:Null<CodenameOwnerSaveFacade>;
	var released:Bool = false;
	var originalAutoPause:Bool;
	var changedAutoPause:Bool = false;
	/** Optional owner-local state resolver; native FlxG switches still fire the
		active global preStateSwitch callback. */
	public var stateSwitch:Null<Dynamic->Bool>;
	/** A constructed state becomes Flixel's responsibility only after its
		owner-local switch request has been accepted. */
	public var onStateSwitchAccepted:Null<Dynamic->Void>;

	public function new(hostCameras:Array<FlxCamera>, ?owner:String) {
		cameras = new CodenameCameraFacade(FlxG.cameras, hostCameras, owner);
		worldBounds = FlxRect.get(FlxG.worldBounds.x, FlxG.worldBounds.y,
			FlxG.worldBounds.width, FlxG.worldBounds.height);
		save = !CodenameOwnerSaveData.isImportedOwnerRoot(owner)
			? null : new CodenameOwnerSaveFacade(owner);
	}

	/** Collision bounds are local to the interpreter, even though native Flixel
		uses a process-wide rectangle while executing a collision check. */
	function withWorldBounds(check:Void->Bool):Bool {
		var native = FlxG.worldBounds;
		var x = native.x;
		var y = native.y;
		var width = native.width;
		var height = native.height;
		native.set(worldBounds.x, worldBounds.y, worldBounds.width, worldBounds.height);
		try {
			var result = check();
			native.set(x, y, width, height);
			return result;
		} catch (error:Dynamic) {
			native.set(x, y, width, height);
			throw error;
		}
	}

	public function collide(?first:FlxBasic, ?second:FlxBasic,
		?notify:Dynamic->Dynamic->Void):Bool
		return withWorldBounds(function():Bool return FlxG.collide(first, second, notify));

	public function overlap(?first:FlxBasic, ?second:FlxBasic,
		?notify:Dynamic->Dynamic->Void, ?process:Dynamic->Dynamic->Bool):Bool
		return withWorldBounds(function():Bool return FlxG.overlap(first, second, notify, process));

	public function switchState(target:Dynamic):Bool {
		if (stateSwitch != null) {
			var accepted = stateSwitch(target);
			if (accepted && onStateSwitchAccepted != null)
				onStateSwitchAccepted(target);
			return accepted;
		}
		if (!Std.isOfType(target, FlxState)) {
			trace('[codename-state-switch] Refused a non-FlxState target.');
			return false;
		}
		FlxG.switchState(cast target);
		if (onStateSwitchAccepted != null) onStateSwitchAccepted(target);
		return true;
	}

	public function resetState():Void FlxG.resetState();

	/** Open only validated web URLs through Flixel's host browser bridge. */
	public function openURL(url:String, target:String = '_blank'):Bool return CodenameOpenURLCompat.open(url,
		function(safeUrl:String):Void FlxG.openURL(safeUrl, target));

	public var camera(get, set):FlxCamera;
	function get_camera():FlxCamera return FlxG.camera;
	function set_camera(value:FlxCamera):FlxCamera return cameras.selectMain(value);

	public var width(get, never):Int;
	function get_width():Int return FlxG.width;
	public var height(get, never):Int;
	function get_height():Int return FlxG.height;
	public var elapsed(get, never):Float;
	function get_elapsed():Float return FlxG.elapsed;
	/** Codename's debug and playtest scripts adjust the shared game clock. */
	public var timeScale(get, set):Float;
	function get_timeScale():Float return FlxG.timeScale;
	function set_timeScale(value:Float):Float return FlxG.timeScale = value;
	/** Codename global scripts use FlxG's native fullscreen toggle. */
	public var fullscreen(get, set):Bool;
	function get_fullscreen():Bool return FlxG.fullscreen;
	function set_fullscreen(value:Bool):Bool return FlxG.fullscreen = value;
	public var autoPause(get, set):Bool;
	function get_autoPause():Bool return FlxG.autoPause;
	function set_autoPause(value:Bool):Bool {
		if (released) return FlxG.autoPause;
		if (!changedAutoPause) originalAutoPause = FlxG.autoPause;
		changedAutoPause = true;
		return FlxG.autoPause = value;
	}
	public var keys(get, never):Dynamic;
	function get_keys():Dynamic return FlxG.keys;
	public var random(get, never):Dynamic;
	function get_random():Dynamic return FlxG.random;
	public var mouse(get, never):Dynamic;
	function get_mouse():Dynamic return FlxG.mouse;
	public var sound(get, never):Dynamic;
	function get_sound():Dynamic return FlxG.sound;
	public var state(get, never):Dynamic;
	function get_state():Dynamic return FlxG.state;
	public var game(get, never):Dynamic;
	function get_game():Dynamic return FlxG.game;

	public function release():Void {
		if (released) return;
		released = true;
		stateSwitch = null;
		onStateSwitchAccepted = null;
		if (changedAutoPause) FlxG.autoPause = originalAutoPause;
		cameras.release();
		worldBounds.put();
	}
}
