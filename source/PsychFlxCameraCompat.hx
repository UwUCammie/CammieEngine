package;

import flixel.FlxCamera;
import flixel.FlxG;
import flixel.FlxObject;
import flixel.math.FlxPoint;
import flixel.util.FlxAxes;
import flixel.util.FlxColor;
import openfl.filters.BitmapFilter;

/** Small live view of a FlxCamera that restores Psych's setFilters helper
	while forwarding the camera state used by source stages to the real camera. */
@:allow(NightmareVisionScriptInterp)
@:allow(PsychFlxGCompat)
class PsychFlxCameraCompat {
	final nativeCamera:FlxCamera;

	public function new(camera:FlxCamera) {
		nativeCamera = camera;
	}

	public function wraps(camera:FlxCamera):Bool return nativeCamera == camera;
	function unwrap():FlxCamera return nativeCamera;

	public var visible(get, set):Bool;
	function get_visible():Bool return nativeCamera.visible;
	function set_visible(value:Bool):Bool return nativeCamera.visible = value;

	public var zoom(get, set):Float;
	function get_zoom():Float return nativeCamera.zoom;
	function set_zoom(value:Float):Float return nativeCamera.zoom = value;

	public var scroll(get, never):FlxPoint;
	function get_scroll():FlxPoint return nativeCamera.scroll;

	public var filters(get, set):Null<Array<BitmapFilter>>;
	function get_filters():Null<Array<BitmapFilter>> return nativeCamera.filters;
	function set_filters(value:Null<Array<BitmapFilter>>):Null<Array<BitmapFilter>> {
		nativeCamera.filters = value;
		nativeCamera.filtersEnabled = value != null;
		return value;
	}

	public var filtersEnabled(get, set):Bool;
	function get_filtersEnabled():Bool return nativeCamera.filtersEnabled;
	function set_filtersEnabled(value:Bool):Bool return nativeCamera.filtersEnabled = value;

	public var viewLeft(get, never):Float;
	function get_viewLeft():Float return nativeCamera.viewLeft;
	public var viewTop(get, never):Float;
	function get_viewTop():Float return nativeCamera.viewTop;
	public var viewRight(get, never):Float;
	function get_viewRight():Float return nativeCamera.viewRight;
	public var viewBottom(get, never):Float;
	function get_viewBottom():Float return nativeCamera.viewBottom;

	public function setFilters(value:Array<BitmapFilter>):Void {
		nativeCamera.filters = value;
		nativeCamera.filtersEnabled = value != null;
	}

	public function snapToTarget():Void nativeCamera.snapToTarget();
	public function focusOn(point:FlxPoint):Void nativeCamera.focusOn(point);
	public function follow(target:FlxObject, ?style:Dynamic, lerp:Float = 1.0):Void
		nativeCamera.follow(target, style, lerp);
	public function fade(color:Dynamic = null, duration:Float = 1, fadeIn:Bool = false,
		?onComplete:Void->Void, force:Bool = false):Void {
		nativeCamera.fade(cast (color == null ? FlxColor.BLACK : color), duration, fadeIn, onComplete, force);
	}
	public function flash(color:Dynamic = null, duration:Float = 1,
		?onComplete:Void->Void, force:Bool = false):Void {
		nativeCamera.flash(cast (color == null ? FlxColor.WHITE : color), duration, onComplete, force);
	}
	public function shake(intensity:Float = 0.05, duration:Float = 0.5,
		?onComplete:Void->Void, force:Bool = true, ?axes:FlxAxes):Void
		nativeCamera.shake(intensity, duration, onComplete, force, axes);

	/** Resolve source camera members that are not explicitly wrapped above. */
	function getField(field:String):Dynamic {
		if (field == null || field == '') return null;
		return switch (field) {
			case 'visible' | 'zoom' | 'scroll' | 'filters' | 'filtersEnabled'
				| 'viewLeft' | 'viewTop' | 'viewRight' | 'viewBottom'
				| 'setFilters' | 'snapToTarget' | 'focusOn' | 'follow' | 'fade' | 'flash' | 'shake':
				Reflect.getProperty(this, field);
			default:
				Reflect.getProperty(nativeCamera, field);
		};
	}

	/** Keep the existing filter helper's enable/disable side effect; other
	 * camera fields use FlxCamera's real setters and native read-only rules. */
	function setField(field:String, value:Dynamic):Dynamic {
		if (field == null || field == '') return value;
		if (field == 'filters')
			Reflect.setProperty(this, field, value);
		else
			Reflect.setProperty(nativeCamera, field, value);
		return value;
	}
}

/** FlxG view for owner stage modules. Static fields stay live and camera calls
	pass through PsychFlxCameraCompat only where the source API had extra helpers. */
@:allow(NightmareVisionScriptInterp)
class PsychFlxGCompat {
	static var _camera:PsychFlxCameraCompat;

	public static var camera(get, never):PsychFlxCameraCompat;
	static function get_camera():PsychFlxCameraCompat {
		if (FlxG.camera == null) return null;
		if (_camera == null || !_camera.wraps(FlxG.camera))
			_camera = new PsychFlxCameraCompat(FlxG.camera);
		return _camera;
	}

	public static var width(get, never):Int;
	static function get_width():Int return FlxG.width;
	public static var height(get, never):Int;
	static function get_height():Int return FlxG.height;
	public static var elapsed(get, never):Float;
	static function get_elapsed():Float return FlxG.elapsed;
	public static var game(get, never):Dynamic;
	static function get_game():Dynamic return FlxG.game;
	public static var cameras(get, never):Dynamic;
	static function get_cameras():Dynamic return FlxG.cameras;
	public static var sound(get, never):Dynamic;
	static function get_sound():Dynamic return FlxG.sound;
	public static var random(get, never):Dynamic;
	static function get_random():Dynamic return FlxG.random;

	/** Psych stage classes use FlxG.state to manage cutscene and temporary
	 * members. A null guard also lets imported class modules be prepared before
	 * FlxGame publishes its initial state. */
	public static var state(get, never):Dynamic;
	static function get_state():Dynamic return FlxG.game == null ? null : FlxG.state;

	/** Preserve this facade's live convenience views and delegate the rest of
	 * Psych's FlxG surface to the actual global class. */
	static function getField(field:String):Dynamic {
		if (field == null || field == '') return null;
		var local:Dynamic = Reflect.getProperty(PsychFlxGCompat, field);
		return local == null ? Reflect.getProperty(FlxG, field) : local;
	}

	static function setField(field:String, value:Dynamic):Dynamic {
		if (field != null && field != '') {
			var assigned = value;
			if (field == 'camera' && Std.isOfType(value, PsychFlxCameraCompat))
				value = (cast value:PsychFlxCameraCompat).unwrap();
			Reflect.setProperty(FlxG, field, value);
			return assigned;
		}
		return value;
	}
}
