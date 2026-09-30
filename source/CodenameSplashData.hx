package;

/** One Codename splash animation entry from data/splashes/<name>.xml. */
typedef CodenameSplashAnimation = {
	var name:String;
	var prefix:String;
	var fps:Float;
	var x:Float;
	var y:Float;
	var loop:Bool;
	var indices:Array<Int>;
}

/** Parsed, renderer-neutral view of Codename's note splash XML format. */
class CodenameSplashData {
	public final sprite:String;
	public final alpha:Float;
	public final scale:Float;
	public final antialiasing:Bool;
	public final laneCount:Int;
	final laneAnimations:Map<Int, Array<CodenameSplashAnimation>>;

	function new(sprite:String, alpha:Float, scale:Float, antialiasing:Bool,
		laneCount:Int, laneAnimations:Map<Int, Array<CodenameSplashAnimation>>) {
		this.sprite = sprite;
		this.alpha = alpha;
		this.scale = scale;
		this.antialiasing = antialiasing;
		this.laneCount = laneCount;
		this.laneAnimations = laneAnimations;
	}

	/** Parse the fields Codename SplashGroup consumes. Invalid or incomplete
		definitions are ignored so a malformed imported XML file cannot abort play.
	*/
	public static function parse(source:String):Null<CodenameSplashData> {
		if (source == null || StringTools.trim(source) == '')
			return null;
		try {
			var root = Xml.parse(source).firstElement();
			if (root == null || root.nodeName != 'splashes' || !root.exists('sprite'))
				return null;
			var sprite = StringTools.trim(root.get('sprite'));
			if (!CodenameScriptDiscovery.safeRelativeName(sprite))
				return null;
			var alpha = parseFloat(root, 'alpha', 1);
			var scale = parseFloat(root, 'scale', 1);
			var antialiasing = !root.exists('antialiasing') || root.get('antialiasing') == 'true';
			var lanes:Map<Int, Array<CodenameSplashAnimation>> = new Map();
			var laneCount = 0;
			for (strum in root.elementsNamed('strum')) {
				if (!strum.exists('id')) continue;
				var id = Std.parseInt(strum.get('id'));
				if (id == null || id < 0 || id > 64) continue;
				var animations:Array<CodenameSplashAnimation> = [];
				for (node in strum.elementsNamed('anim')) {
					var animation = parseAnimation(node);
					if (animation != null) animations.push(animation);
				}
				lanes.set(id, animations);
				if (id + 1 > laneCount) laneCount = id + 1;
			}
			var shared:Array<CodenameSplashAnimation> = [];
			for (node in root.elementsNamed('anim')) {
				var animation = parseAnimation(node);
				if (animation != null) shared.push(animation);
			}
			// Upstream registers root-level animations on every lane that has a
			// <strum> block; an XML file without any such block has no usable lane.
			for (id in lanes.keys())
				for (animation in shared) lanes.get(id).push(animation);
			return new CodenameSplashData(sprite, alpha, scale, antialiasing, laneCount, lanes);
		} catch (_:Dynamic) {
			return null;
		}
	}

	/** Resolve the same lane slot SplashGroup uses (strum ID modulo its lane
		array size), then choose an animation by index. Passing an index keeps the
		selection deterministic for tests; runtime passes a random index.
	*/
	public function animationForLane(strumId:Int, index:Int):Null<CodenameSplashAnimation> {
		if (laneCount <= 0) return null;
		var lane = strumId % laneCount;
		if (lane < 0) lane += laneCount;
		var animations = laneAnimations.get(lane);
		if (animations == null || animations.length == 0) return null;
		var selected = index % animations.length;
		if (selected < 0) selected += animations.length;
		return animations[selected];
	}

	public function animationCountForLane(strumId:Int):Int {
		if (laneCount <= 0) return 0;
		var lane = strumId % laneCount;
		if (lane < 0) lane += laneCount;
		var animations = laneAnimations.get(lane);
		return animations == null ? 0 : animations.length;
	}

	static function parseAnimation(node:Xml):Null<CodenameSplashAnimation> {
		if (!node.exists('name') || !node.exists('anim')) return null;
		var name = StringTools.trim(node.get('name'));
		var prefix = StringTools.trim(node.get('anim'));
		if (name == '' || prefix == '') return null;
		var fps = parseFloat(node, 'fps', 24);
		if (fps <= 0) fps = 24;
		return {name:name, prefix:prefix, fps:fps,
			x:parseFloat(node, 'x', 0), y:parseFloat(node, 'y', 0),
			loop:node.exists('loop') && node.get('loop') == 'true',
			indices:node.exists('indices') ? parseIndices(node.get('indices')) : []};
	}

	static function parseFloat(node:Xml, attribute:String, fallback:Float):Float {
		if (!node.exists(attribute)) return fallback;
		var result = Std.parseFloat(node.get(attribute));
		return Math.isFinite(result) ? result : fallback;
	}

	static function parseIndices(value:String):Array<Int> {
		var result:Array<Int> = [];
		if (value == null) return result;
		for (part in value.split(',')) {
			var clean = StringTools.trim(part);
			var range = ~/^(-?\d+)\s*-\s*(-?\d+)$/;
			if (range.match(clean)) {
				var first = Std.parseInt(range.matched(1));
				var last = Std.parseInt(range.matched(2));
				if (first == null || last == null || Math.abs(last - first) > 1024) continue;
				var step = first <= last ? 1 : -1;
				var index = first;
				while (step > 0 ? index <= last : index >= last) {
					result.push(index);
					index += step;
				}
			} else {
				var index = Std.parseInt(clean);
				if (index != null) result.push(index);
			}
		}
		return result;
	}
}
