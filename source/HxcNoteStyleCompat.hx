package;

import flixel.FlxSprite;

using StringTools;

/** A small, copied view of one style from the caller's imported root. */
class HxcNoteStyleCompat {
	public var id(default, null):String;
	public var root(default, null):String;
	public var splashAsset(default, null):String = '';
	public var splashScale(default, null):Float = 1;
	public var splashAlpha(default, null):Float = 0.6;
	var splashOffsets:Array<Float> = [0, 0];
	var splashPrefixes:Array<Array<String>> = [];

	public static function fetchEntry(root:String, id:String):HxcNoteStyleCompat {
		if (id == null || !~/^[A-Za-z0-9_-]+$/.match(id))
			return null;
		var style = new HxcNoteStyleCompat(root, id);
		var path = HxcStateAssetScope.scopedAssetPath(root, 'data/notestyles/' + id + '.json');
		if (path == null)
			return style;
		try {
			var document:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
			var assets = Reflect.field(document, 'assets');
			var splash = assets == null ? null : Reflect.field(assets, 'noteSplash');
			var data:Dynamic = splash == null ? null : Reflect.field(splash, 'data');
			if (splash == null || (data != null && Reflect.field(data, 'enabled') == false))
				return style;
			var rawAsset:Dynamic = Reflect.field(splash, 'assetPath');
			if (rawAsset != null) {
				var key = StringTools.trim(Std.string(rawAsset));
				var colon = key.indexOf(':');
				if (colon >= 0) key = key.substr(colon + 1);
				if (key != '' && !key.startsWith('/') && key.indexOf('..') < 0 && key.indexOf(':') < 0)
					style.splashAsset = key;
			}
			style.splashScale = positiveNumber(Reflect.field(splash, 'scale'), 1);
			style.splashAlpha = boundedAlpha(Reflect.field(splash, 'alpha'));
			var offsets:Dynamic = Reflect.field(splash, 'offsets');
			if (Std.isOfType(offsets, Array)) {
				var values:Array<Dynamic> = cast offsets;
				if (values.length >= 2)
					style.splashOffsets = [number(values[0], 0), number(values[1], 0)];
			}
			for (direction in ['left', 'down', 'up', 'right']) {
				var prefixes:Array<String> = [];
				var values:Dynamic = data == null ? null : Reflect.field(data, direction + 'Splashes');
				if (Std.isOfType(values, Array))
					for (entry in (cast values:Array<Dynamic>)) {
						var raw = entry == null ? null : Reflect.field(entry, 'prefix');
						if (raw != null && StringTools.trim(Std.string(raw)) != '')
							prefixes.push(Std.string(raw));
					}
				style.splashPrefixes.push(prefixes);
			}
			return style;
		} catch (_:Dynamic) {
			return style;
		}
	}

	public function getSplashOffsets():Array<Float> return splashOffsets.copy();
	public function getSplashPrefixes(direction:Int):Array<String> {
		return direction >= 0 && direction < splashPrefixes.length
			? splashPrefixes[direction].copy() : [];
	}

	function new(root:String, id:String) {
		this.root = root;
		this.id = id;
	}

	static function number(value:Dynamic, fallback:Float):Float {
		if (value == null) return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) || parsed == Math.POSITIVE_INFINITY
			|| parsed == Math.NEGATIVE_INFINITY ? fallback : parsed;
	}
	static function positiveNumber(value:Dynamic, fallback:Float):Float {
		var parsed = number(value, fallback);
		return parsed > 0 ? parsed : fallback;
	}
	static function boundedAlpha(value:Dynamic):Float {
		var parsed = number(value, 0.6);
		return Math.max(0, Math.min(1, parsed));
	}
}

/** V-Slice's style-taking NoteSplash constructor and play(direction) surface. */
class HxcNoteSplashCompat extends FlxSprite {
	var style:HxcNoteStyleCompat;
	var hasAnimations:Bool = false;

	public function new(style:HxcNoteStyleCompat) {
		super();
		this.style = style;
		visible = false;
		if (style == null || style.splashAsset == '') return;
		var atlas = HxcStateAssetScope.eventAtlas(style.root, style.splashAsset, 'sparrow',
			'HXC note-style splash ' + style.id);
		if (atlas == null) return;
		frames = atlas;
		var direction = 0;
		for (_ in ['left', 'down', 'up', 'right']) {
			var prefixes = style.getSplashPrefixes(direction);
			for (variant in 0...prefixes.length) {
				animation.addByPrefix('note' + direction + '-' + variant,
					prefixes[variant], 24, false);
				hasAnimations = true;
			}
			direction++;
		}
		scale.set(style.splashScale, style.splashScale);
		alpha = style.splashAlpha;
	}

	public function play(direction:Int):Void {
		if (!hasAnimations || style == null) return;
		var prefixes = style.getSplashPrefixes(direction);
		if (prefixes.length == 0) return;
		var variant = flixel.FlxG.random.int(0, prefixes.length - 1);
		revive();
		animation.play('note' + direction + '-' + variant, true);
		visible = animation.curAnim != null;
		if (visible) updateHitbox();
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (visible && animation.curAnim != null && animation.curAnim.finished)
			kill();
	}
}
