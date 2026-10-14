package;

using StringTools;

/** How one engine applies the shared stage-file fields. */
typedef SourceStageApplyProfile = {
	/** Snap the game camera to the stage zoom now instead of easing to it. */
	var snapZoom:Bool;
	var cameraSpeed:Bool;
	var stageUI:Bool;
	/** Write the anchors into the public role-group positions too. */
	var groupPositions:Bool;
}

/**
	The Psych-format stage file (also read by Nightmare Vision), parsed and
	validated once. Every field is either a usable value or null, so callers
	never have to repeat the type checks.
**/
class SourceStageMetadata {
	public static final PSYCH:SourceStageApplyProfile = {snapZoom:true, cameraSpeed:true, stageUI:true, groupPositions:false};
	// Nightmare Vision only reads camera_speed while building the first stage,
	// and has no stage UI field at all.
	public static final NIGHTMARE_VISION_CREATE:SourceStageApplyProfile = {snapZoom:true, cameraSpeed:true, stageUI:false, groupPositions:true};
	public static final NIGHTMARE_VISION_SWAP:SourceStageApplyProfile = {snapZoom:false, cameraSpeed:false, stageUI:false, groupPositions:true};

	public var boyfriend:Null<Array<Float>> = null;
	public var opponent:Null<Array<Float>> = null;
	public var girlfriend:Null<Array<Float>> = null;
	public var cameraBoyfriend:Array<Float>;
	public var cameraOpponent:Array<Float>;
	public var cameraGirlfriend:Array<Float>;
	public var defaultZoom:Null<Float> = null;
	public var cameraSpeed:Null<Float> = null;
	public var hideGirlfriend:Bool = false;
	/** null when the file says nothing about its UI, so the chart's choice stands. */
	public var stageUI:Null<String> = null;
	public var directory:Null<String> = null;
	/** Psych 1.0 stage editor sprites, only kept when the list has entries. */
	public var objects:Null<Array<Dynamic>> = null;
	public var preload:Dynamic = null;

	public function new() {}

	/**
		Read a stage file. Points and numbers that are missing or unusable come
		from `fallback` when one is given (Nightmare Vision's template), and stay
		null otherwise so the engine keeps what it already had.
	**/
	public static function parse(data:Dynamic, ?fallback:SourceStageMetadata):SourceStageMetadata {
		var result = new SourceStageMetadata();
		result.boyfriend = pick(point(data, 'boyfriend'), fallback == null ? null : fallback.boyfriend);
		result.opponent = pick(point(data, 'opponent'), fallback == null ? null : fallback.opponent);
		result.girlfriend = pick(point(data, 'girlfriend'), fallback == null ? null : fallback.girlfriend);
		result.cameraBoyfriend = cameraPoint(data, 'camera_boyfriend');
		result.cameraOpponent = cameraPoint(data, 'camera_opponent');
		result.cameraGirlfriend = cameraPoint(data, 'camera_girlfriend');
		result.defaultZoom = number(data, 'defaultZoom', true);
		if (result.defaultZoom == null && fallback != null)
			result.defaultZoom = fallback.defaultZoom;
		result.cameraSpeed = number(data, 'camera_speed', false);
		if (result.cameraSpeed == null && fallback != null)
			result.cameraSpeed = fallback.cameraSpeed;
		if (data == null)
			return result;
		result.hideGirlfriend = Reflect.field(data, 'hide_girlfriend') == true;
		result.stageUI = resolveStageUI(Reflect.field(data, 'stageUI'), Reflect.field(data, 'isPixelStage'));
		var directory:Dynamic = Reflect.field(data, 'directory');
		result.directory = directory == null ? null : Std.string(directory);
		var objects:Dynamic = Reflect.field(data, 'objects');
		if (Std.isOfType(objects, Array) && (cast objects:Array<Dynamic>).length > 0)
			result.objects = cast objects;
		var preload:Dynamic = Reflect.field(data, 'preload');
		if (preload != null && Reflect.isObject(preload) && !Std.isOfType(preload, String))
			result.preload = preload;
		return result;
	}

	/** An [x, y] pair, or null unless both halves read as numbers. */
	public static function point(data:Dynamic, field:String):Null<Array<Float>> {
		if (data == null || !Reflect.hasField(data, field))
			return null;
		var value:Dynamic = Reflect.field(data, field);
		if (!Std.isOfType(value, Array) || (cast value:Array<Dynamic>).length < 2)
			return null;
		var values:Array<Dynamic> = cast value;
		var x = Std.parseFloat(Std.string(values[0]));
		var y = Std.parseFloat(Std.string(values[1]));
		return Math.isNaN(x) || Math.isNaN(y) ? null : [x, y];
	}

	/**
		Psych's own order: a non-empty stageUI wins, and isPixelStage:true is
		the older spelling of 'pixel'. Anything else is no opinion.
	**/
	public static function resolveStageUI(stageUI:Dynamic, isPixelStage:Dynamic):Null<String> {
		if (stageUI != null) {
			var name = Std.string(stageUI).trim();
			if (name.length > 0)
				return name;
		}
		return isPixelStage == true ? 'pixel' : null;
	}

	static function cameraPoint(data:Dynamic, field:String):Array<Float> {
		var value = point(data, field);
		return value == null ? [0, 0] : value;
	}

	static function number(data:Dynamic, field:String, positive:Bool):Null<Float> {
		if (data == null)
			return null;
		var value:Dynamic = Reflect.field(data, field);
		if (value == null)
			return null;
		var parsed = Std.parseFloat(Std.string(value));
		if (!Math.isFinite(parsed) || (positive && parsed <= 0))
			return null;
		return parsed;
	}

	static inline function pick(value:Null<Array<Float>>, fallback:Null<Array<Float>>):Null<Array<Float>> {
		return value != null ? value : fallback == null ? null : fallback.copy();
	}
}
