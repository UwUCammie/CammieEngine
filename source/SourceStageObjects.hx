package;

using StringTools;

typedef SourceStageObjectAnimation = {
	var anim:String;
	var prefix:String;
	var fps:Int;
	var loop:Bool;
	var indices:Null<Array<Int>>;
	var offsets:Null<Array<Float>>;
}

/** One sprite from a stage file's `objects` list, checked and ready to build. */
typedef SourceStageObjectPlan = {
	/** 'square', 'sprite' or 'animatedSprite'. */
	var type:String;
	var name:Null<String>;
	var image:String;
	var x:Float;
	var y:Float;
	/** The character this sprite sits behind ('gf', 'dad' or 'boyfriend'), or null for in front of all of them. */
	var behind:Null<String>;
	var scale:Null<Array<Float>>;
	var scroll:Array<Float>;
	var alpha:Null<Float>;
	var angle:Null<Float>;
	var flipX:Null<Bool>;
	var flipY:Null<Bool>;
	var antialiasing:Null<Bool>;
	var color:Null<String>;
	var animations:Array<SourceStageObjectAnimation>;
	var firstAnimation:Null<String>;
}

typedef SourceStagePreloadPlan = {
	var images:Array<String>;
	var sounds:Array<String>;
	var music:Array<String>;
}

/**
	Psych 1.0 stage editor output: sprites listed in the stage JSON instead of a
	script. The list order is the draw order, with gf/dad/boyfriend entries
	marking where each character sits among the sprites.
**/
class SourceStageObjects {
	public static inline var LOW_QUALITY:Int = 1;
	public static inline var HIGH_QUALITY:Int = 2;
	public static inline var STORY_MODE:Int = 4;
	public static inline var FREEPLAY:Int = 8;

	/**
		Psych's filter check, kept as it behaves there: the freeplay bit is only
		looked at when the story bit is set too. A missing filter field counts as
		both quality levels so a hand-written entry still shows up.
	**/
	public static function visible(filters:Dynamic, lowQuality:Bool, storyMode:Bool):Bool {
		var bits = filterBits(filters);
		if (bits & STORY_MODE == STORY_MODE) {
			if (!storyMode)
				return false;
			else if (bits & FREEPLAY == FREEPLAY)
				return false;
		}
		return (lowQuality && bits & LOW_QUALITY == LOW_QUALITY) || (!lowQuality && bits & HIGH_QUALITY == HIGH_QUALITY);
	}

	public static function plan(objects:Array<Dynamic>, lowQuality:Bool, storyMode:Bool,
		hideGirlfriend:Bool):Array<SourceStageObjectPlan> {
		var result:Array<SourceStageObjectPlan> = [];
		if (objects == null)
			return result;
		var waiting:Array<SourceStageObjectPlan> = [];
		var position = -1;
		for (data in objects) {
			position++;
			if (data == null)
				continue;
			var type = Std.string(Reflect.field(data, 'type'));
			switch (type) {
				case 'gf', 'gfGroup', 'dad', 'dadGroup', 'boyfriend', 'boyfriendGroup':
					// A hidden girlfriend is not placed, so nothing can sit behind her.
					var role = type.startsWith('gf') ? 'gf' : type.startsWith('dad') ? 'dad' : 'boyfriend';
					if (role == 'gf' && hideGirlfriend)
						continue;
					for (object in waiting)
						object.behind = role;
					waiting = [];
				case 'square', 'sprite', 'animatedSprite':
					if (!visible(Reflect.field(data, 'filters'), lowQuality, storyMode))
						continue;
					var object = planObject(type, data);
					// The editor always names entries; a hand-written one still
					// needs a tag to be built and found again.
					if (object.name == null || object.name.length == 0)
						object.name = 'stage-object-' + position;
					result.push(object);
					waiting.push(object);
				default:
					trace('[source-stage-objects] Unknown sprite type: ' + type);
			}
		}
		return result;
	}

	/** Images, sounds and music a stage asks to load up front, without their folder prefix. */
	public static function preloadPlan(preload:Dynamic, lowQuality:Bool, storyMode:Bool):SourceStagePreloadPlan {
		var result:SourceStagePreloadPlan = {images:[], sounds:[], music:[]};
		if (preload == null)
			return result;
		for (field in Reflect.fields(preload)) {
			var filters:Dynamic = Reflect.field(preload, field);
			var bits = filterBits(filters);
			if (filters != null && bits >= 0 && !visible(filters, lowQuality, storyMode))
				continue;
			var asset = field.trim();
			if (asset.startsWith('images/'))
				push(result.images, asset.substr('images/'.length));
			else if (asset.startsWith('sounds/'))
				push(result.sounds, asset.substr('sounds/'.length));
			else if (asset.startsWith('music/'))
				push(result.music, asset.substr('music/'.length));
		}
		return result;
	}

	static function planObject(type:String, data:Dynamic):SourceStageObjectPlan {
		var animations:Array<SourceStageObjectAnimation> = [];
		var firstAnimation:Null<String> = null;
		var authoredFirst = text(Reflect.field(data, 'firstAnimation'));
		var list:Dynamic = Reflect.field(data, 'animations');
		if (type == 'animatedSprite' && Std.isOfType(list, Array)) {
			for (entry in (cast list:Array<Dynamic>)) {
				if (entry == null)
					continue;
				var anim = text(Reflect.field(entry, 'anim'));
				if (anim == null)
					continue;
				var fps = number(Reflect.field(entry, 'fps'));
				var loop:Dynamic = Reflect.field(entry, 'loop');
				var indices = intList(Reflect.field(entry, 'indices'));
				animations.push({
					anim: anim,
					prefix: text(Reflect.field(entry, 'name')),
					fps: fps == null ? 24 : Std.int(fps),
					loop: loop == true,
					indices: indices == null || indices.length < 1 ? null : indices,
					offsets: pair(Reflect.field(entry, 'offsets'))
				});
				// Psych plays the first animation it adds, then switches when it
				// reaches the one named as the first animation.
				if (firstAnimation == null || authoredFirst == anim)
					firstAnimation = anim;
			}
		}
		var scroll = pair(Reflect.field(data, 'scroll'));
		return {
			type: type,
			name: text(Reflect.field(data, 'name')),
			image: type == 'square' ? '' : (text(Reflect.field(data, 'image')) == null ? '' : text(Reflect.field(data, 'image'))),
			x: orZero(number(Reflect.field(data, 'x'))),
			y: orZero(number(Reflect.field(data, 'y'))),
			behind: null,
			scale: pair(Reflect.field(data, 'scale')),
			scroll: scroll == null ? [1, 1] : scroll,
			alpha: number(Reflect.field(data, 'alpha')),
			angle: number(Reflect.field(data, 'angle')),
			flipX: bool(Reflect.field(data, 'flipX')),
			flipY: bool(Reflect.field(data, 'flipY')),
			antialiasing: type == 'square' ? false : bool(Reflect.field(data, 'antialiasing')),
			color: text(Reflect.field(data, 'color')),
			animations: animations,
			firstAnimation: firstAnimation
		};
	}

	static function filterBits(filters:Dynamic):Int {
		if (filters == null)
			return LOW_QUALITY | HIGH_QUALITY;
		var value = Std.parseInt(Std.string(filters));
		return value == null ? LOW_QUALITY | HIGH_QUALITY : value;
	}

	static function push(list:Array<String>, value:String):Void {
		if (value.length > 0 && list.indexOf(value) < 0)
			list.push(value);
	}

	static function text(value:Dynamic):Null<String> {
		return value == null ? null : Std.string(value);
	}

	static function bool(value:Dynamic):Null<Bool> {
		return value == true ? true : value == false ? false : null;
	}

	static function number(value:Dynamic):Null<Float> {
		if (value == null)
			return null;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isFinite(parsed) ? parsed : null;
	}

	static inline function orZero(value:Null<Float>):Float {
		return value == null ? 0 : value;
	}

	static function pair(value:Dynamic):Null<Array<Float>> {
		if (!Std.isOfType(value, Array))
			return null;
		var values:Array<Dynamic> = cast value;
		if (values.length < 2)
			return null;
		var x = number(values[0]);
		var y = number(values[1]);
		return x == null || y == null ? null : [x, y];
	}

	static function intList(value:Dynamic):Null<Array<Int>> {
		if (!Std.isOfType(value, Array))
			return null;
		var result:Array<Int> = [];
		for (entry in (cast value:Array<Dynamic>)) {
			var parsed = Std.parseInt(Std.string(entry));
			if (parsed != null)
				result.push(parsed);
		}
		return result;
	}
}
