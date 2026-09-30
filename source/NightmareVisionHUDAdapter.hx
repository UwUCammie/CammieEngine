package;

/** Construction inputs for the non-rendering bridge to NMV's PsychHUD API.

	Every sprite/bar supplied here is already owned by PlayState. The adapter
	never inserts those objects into a second FlxGroup, which would update and
	draw them twice. Optional callbacks are explicit host operations; if a
	script asks for an operation that is not wired, it receives a diagnostic
	instead of a silent no-op.
*/
typedef NightmareVisionHUDAdapterConfig = {
	var parent:Dynamic;
	var healthFill:Dynamic;
	var healthBackground:Dynamic;
	var iconP1:Dynamic;
	var iconP2:Dynamic;
	var scoreText:Dynamic;
	var songFill:Dynamic;
	var songBackground:Dynamic;
	var timeText:Dynamic;
	@:optional var healthValue:Void->Float;
	@:optional var songProgress:Void->Float;
	@:optional var healthMin:Float;
	@:optional var healthMax:Float;
	@:optional var ratingPrefix:String;
	/** Optional bridge into the native judgement image resolver. */
	@:optional var applyRatingPrefix:String->Void;
	@:optional var songTitle:String;
	@:optional var timeBarType:String;
	@:optional var showTime:Bool;
	@:optional var setHealthDirection:Bool->Void;
	@:optional var setSongDirection:Bool->Void;
	/** Tween `target.alpha` to 1 over the given duration with circOut easing. */
	@:optional var tweenAlpha:Dynamic->Float->Void;
	@:optional var reportUnsupported:String->Void;
	/** These callbacks must route to the actual PlayState display list. */
	@:optional var addDisplay:Dynamic->Dynamic;
	@:optional var removeDisplay:Dynamic->Bool->Dynamic;
	@:optional var insertDisplay:Int->Dynamic->Dynamic;
}

/** A PsychHUD Bar-shaped view over two native HUD objects.

	This is deliberately not a FlxBasic or FlxGroup. `fill` and `bg` remain in
	PlayState's real display list, and the view forwards changes to them.
*/
class NightmareVisionHUDBarView {
	public var fill(default, null):Dynamic;
	public var bg(default, null):Dynamic;
	public var bounds(default, null):Dynamic;
	public var valueFunction(default, null):Void->Float;
	public var percent(get, set):Float;
	public var alpha(get, set):Float;
	public var visible(get, set):Bool;
	public var x(get, set):Float;
	public var y(get, set):Float;
	public var leftToRight(get, set):Bool;
	public var barCenter(get, never):Float;
	public var width(get, never):Float;
	public var height(get, never):Float;
	public var cameras(get, set):Dynamic;
	public var scrollFactor(get, set):Dynamic;
	public var scale(default, null):NightmareVisionHUDScaleView;

	var directionChanged:Null<Bool->Void>;
	var reportUnsupported:Null<String->Void>;
	var leftToRightValue:Bool;
	var groupX:Float;
	var groupY:Float;
	var bgOffsetX:Float = 0;
	var bgOffsetY:Float = 0;
	var leftColor:Dynamic;
	var rightColor:Dynamic;
	var released:Bool = false;

	public function new(fill:Dynamic, bg:Dynamic, leftToRight:Bool,
		?directionChanged:Bool->Void, ?valueFunction:Void->Float,
		min:Float = 0, max:Float = 1, ?reportUnsupported:String->Void) {
		if (fill == null || bg == null)
			throw '[nightmare-vision-hud] Bar view requires the live fill and background';
		this.fill = fill;
		this.bg = bg;
		this.leftToRightValue = leftToRight;
		this.directionChanged = directionChanged;
		this.reportUnsupported = reportUnsupported;
		this.valueFunction = valueFunction;
		this.bounds = {min:min, max:max};
		this.groupX = number(bg, 'x');
		this.groupY = number(bg, 'y');
		this.scale = new NightmareVisionHUDScaleView(fill, bg);
	}

	public function setColors(?left:Dynamic, ?right:Dynamic):Void {
		ensureAlive();
		if (left != null) leftColor = left;
		if (right != null) rightColor = right;
		applySideColors();
	}

	/** Match Bar.setBGOffset, including its additive repeated-call behavior. */
	public function setBGOffset(x:Float, y:Float):Void {
		ensureAlive();
		bgOffsetX += x;
		bgOffsetY += y;
		Reflect.setProperty(bg, 'x', groupX + bgOffsetX);
		Reflect.setProperty(bg, 'y', groupY + bgOffsetY);
	}

	public function setBounds(min:Float, max:Float):Void {
		ensureAlive();
		Reflect.setProperty(bounds, 'min', min);
		Reflect.setProperty(bounds, 'max', max);
		var method = Reflect.field(fill, 'setRange');
		if (method == null) unsupported('health/time Bar.setBounds: native fill has no setRange');
		Reflect.callMethod(fill, method, [min, max]);
	}

	/** Re-read the same live value function used by the source Bar. */
	public function updateBar():Void {
		ensureAlive();
		if (valueFunction != null) {
			var minimum:Float = number(bounds, 'min');
			var maximum:Float = number(bounds, 'max');
			var value:Float = valueFunction();
			if (maximum <= minimum) {
				percent = 0;
			} else {
				value = Math.max(minimum, Math.min(value, maximum));
				percent = (value - minimum) * 100 / (maximum - minimum);
			}
		}
		call(fill, 'updateBar', []);
	}

	/** Translate both native pieces with this Bar view, retaining the BG offset. */
	public function moveBy(dx:Float, dy:Float):Void {
		ensureAlive();
		groupX += dx;
		groupY += dy;
		Reflect.setProperty(fill, 'x', number(fill, 'x') + dx);
		Reflect.setProperty(fill, 'y', number(fill, 'y') + dy);
		Reflect.setProperty(bg, 'x', groupX + bgOffsetX);
		Reflect.setProperty(bg, 'y', groupY + bgOffsetY);
	}

	public function release():Void {
		if (released) return;
		released = true;
		fill = null;
		bg = null;
		bounds = null;
		valueFunction = null;
		leftColor = null;
		rightColor = null;
		directionChanged = null;
		reportUnsupported = null;
		if (scale != null) scale.release();
		scale = null;
	}

	function get_percent():Float {
		ensureAlive();
		return number(fill, 'percent');
	}

	function set_percent(value:Float):Float {
		ensureAlive();
		Reflect.setProperty(fill, 'percent', value);
		return value;
	}

	function get_alpha():Float {
		ensureAlive();
		return number(fill, 'alpha');
	}

	function set_alpha(value:Float):Float {
		ensureAlive();
		Reflect.setProperty(fill, 'alpha', value);
		Reflect.setProperty(bg, 'alpha', value);
		return value;
	}

	function get_visible():Bool {
		ensureAlive();
		return Reflect.getProperty(fill, 'visible') == true && Reflect.getProperty(bg, 'visible') == true;
	}

	function set_visible(value:Bool):Bool {
		ensureAlive();
		Reflect.setProperty(fill, 'visible', value);
		Reflect.setProperty(bg, 'visible', value);
		return value;
	}

	function get_x():Float return groupX;
	function set_x(value:Float):Float {
		moveBy(value - groupX, 0);
		return value;
	}
	function get_y():Float return groupY;
	function set_y(value:Float):Float {
		moveBy(0, value - groupY);
		return value;
	}

	function get_leftToRight():Bool return leftToRightValue;
	function set_leftToRight(value:Bool):Bool {
		ensureAlive();
		if (directionChanged == null)
			unsupported('Bar.leftToRight: host did not provide a native fill-direction setter');
		directionChanged(value);
		leftToRightValue = value;
		applySideColors();
		return value;
	}

	/**
		Source Bar colors are attached to physical left and right halves.
		FlxBar exposes filled/empty colors, whose physical sides depend on fill
		direction, so remap retained colors whenever direction changes.
	*/
	function applySideColors():Void {
		if (leftToRightValue) {
			if (leftColor != null) call(fill, 'createColoredFilledBar', [leftColor]);
			if (rightColor != null) call(fill, 'createColoredEmptyBar', [rightColor]);
		} else {
			if (leftColor != null) call(fill, 'createColoredEmptyBar', [leftColor]);
			if (rightColor != null) call(fill, 'createColoredFilledBar', [rightColor]);
		}
	}

	function get_barCenter():Float {
		ensureAlive();
		var fillWidth = number(fill, 'barWidth');
		var p = percent / 100;
		return number(fill, 'x') - 1 + fillWidth * (leftToRightValue ? p : 1 - p);
	}

	function get_width():Float return number(bg, 'width');
	function get_height():Float return number(bg, 'height');
	function get_cameras():Dynamic return Reflect.getProperty(fill, 'cameras');
	function set_cameras(value:Dynamic):Dynamic {
		ensureAlive();
		Reflect.setProperty(fill, 'cameras', value);
		Reflect.setProperty(bg, 'cameras', value);
		return value;
	}
	function get_scrollFactor():Dynamic return Reflect.getProperty(fill, 'scrollFactor');
	function set_scrollFactor(value:Dynamic):Dynamic {
		ensureAlive();
		Reflect.setProperty(fill, 'scrollFactor', value);
		Reflect.setProperty(bg, 'scrollFactor', value);
		return value;
	}

	function ensureAlive():Void {
		if (released) throw '[nightmare-vision-hud] Bar view was released';
	}

	static function number(target:Dynamic, field:String):Float {
		var value:Dynamic = Reflect.getProperty(target, field);
		return value == null ? 0 : value;
	}

	function call(target:Dynamic, methodName:String, args:Array<Dynamic>):Dynamic {
		var method = Reflect.field(target, methodName);
		if (method == null) unsupported('native Bar method is unavailable: ' + methodName);
		return Reflect.callMethod(target, method, args);
	}

	function unsupported(message:String):Dynamic {
		var diagnostic = '[nightmare-vision-hud-unsupported] ' + message;
		if (reportUnsupported != null) reportUnsupported(diagnostic);
		throw diagnostic;
		return null;
	}
}

/** Keeps FlxSpriteGroup-like scale writes applied to both native components. */
class NightmareVisionHUDScaleView {
	public var x(get, set):Float;
	public var y(get, set):Float;
	var fill:Dynamic;
	var bg:Dynamic;
	var released:Bool = false;

	public function new(fill:Dynamic, bg:Dynamic) {
		this.fill = fill;
		this.bg = bg;
	}

	public function set(x:Float = 1, y:Float = 1):NightmareVisionHUDScaleView {
		set_x(x);
		set_y(y);
		return this;
	}

	public function copyFrom(other:Dynamic):NightmareVisionHUDScaleView {
		return set(Reflect.getProperty(other, 'x'), Reflect.getProperty(other, 'y'));
	}

	public function release():Void {
		released = true;
		fill = null;
		bg = null;
	}

	function get_x():Float return number(Reflect.getProperty(fill, 'scale'), 'x');
	function set_x(value:Float):Float {
		setComponent(Reflect.getProperty(fill, 'scale'), 'x', value);
		setComponent(Reflect.getProperty(bg, 'scale'), 'x', value);
		return value;
	}
	function get_y():Float return number(Reflect.getProperty(fill, 'scale'), 'y');
	function set_y(value:Float):Float {
		setComponent(Reflect.getProperty(fill, 'scale'), 'y', value);
		setComponent(Reflect.getProperty(bg, 'scale'), 'y', value);
		return value;
	}

	function setComponent(target:Dynamic, field:String, value:Float):Void {
		if (released) throw '[nightmare-vision-hud] Scale view was released';
		Reflect.setProperty(target, field, value);
	}

	static function number(target:Dynamic, field:String):Float {
		var value:Dynamic = Reflect.getProperty(target, field);
		return value == null ? 0 : value;
	}
}

/** PsychHUD names mapped onto the real HUD sprites created by this PlayState. */
class NightmareVisionHUDAdapter {
	public var name(default, null):String = 'PSYCH';
	public var parent(default, null):Dynamic;
	public var healthBar:NightmareVisionHUDBarView;
	public var timeBar:NightmareVisionHUDBarView;
	public var iconP1:Dynamic;
	public var iconP2:Dynamic;
	public var scoreTxt:Dynamic;
	public var timeTxt:Dynamic;
	public var ratingPrefix(get, set):String;
	/** Native HUD objects, already owned and displayed by PlayState. */
	public var members(default, null):Array<Dynamic> = [];
	public var curStep(get, never):Int;
	public var curBeat(get, never):Int;
	public var curSection(get, never):Int;
	public var alpha(get, set):Float;
	public var visible(get, set):Bool;
	public var x(get, set):Float;
	public var y(get, set):Float;
	public var cameras(get, set):Dynamic;
	public var timeBarType:String;
	public var showTime(default, null):Bool;

	var tweenAlpha:Null<Dynamic->Float->Void>;
	var reportUnsupported:Null<String->Void>;
	var addDisplay:Null<Dynamic->Dynamic>;
	var removeDisplay:Null<Dynamic->Bool->Dynamic>;
	var insertDisplay:Null<Int->Dynamic->Dynamic>;
	var groupX:Float = 0;
	var groupY:Float = 0;
	var ratingPrefixValue:String = '';
	var applyRatingPrefix:Null<String->Void>;
	var alphaValue:Float = 1;
	var visibleValue:Bool = true;
	var released:Bool = false;

	public function new(config:NightmareVisionHUDAdapterConfig) {
		if (config == null || config.parent == null || config.healthFill == null
			|| config.healthBackground == null || config.iconP1 == null || config.iconP2 == null
			|| config.scoreText == null || config.songFill == null || config.songBackground == null
			|| config.timeText == null)
			throw '[nightmare-vision-hud] Adapter requires all live PlayState HUD objects';

		parent = config.parent;
		iconP1 = config.iconP1;
		iconP2 = config.iconP2;
		scoreTxt = config.scoreText;
		timeTxt = config.timeText;
		ratingPrefixValue = config.ratingPrefix == null ? '' : config.ratingPrefix;
		timeBarType = config.timeBarType == null ? 'Time Left' : config.timeBarType;
		showTime = config.showTime == null
			? Reflect.getProperty(config.songFill, 'visible') == true
				&& Reflect.getProperty(config.songBackground, 'visible') == true
				&& Reflect.getProperty(config.timeText, 'visible') == true
			: config.showTime;
		if (timeBarType == 'Disabled') showTime = false;
		tweenAlpha = config.tweenAlpha;
		reportUnsupported = config.reportUnsupported;
		addDisplay = config.addDisplay;
		removeDisplay = config.removeDisplay;
		insertDisplay = config.insertDisplay;
		applyRatingPrefix = config.applyRatingPrefix;

		var healthValue = config.healthValue == null
			? function():Float return number(parent, 'health')
			: config.healthValue;
		var healthMin = config.healthMin == null ? number(config.healthFill, 'min') : config.healthMin;
		var healthMax = config.healthMax == null ? number(config.healthFill, 'max') : config.healthMax;
		healthBar = new NightmareVisionHUDBarView(config.healthFill, config.healthBackground,
			false, config.setHealthDirection, healthValue, healthMin, healthMax, reportUnsupported);
		var songProgress = config.songProgress == null
			? function():Float return number(parent, 'songPositionBar')
			: config.songProgress;
		timeBar = new NightmareVisionHUDBarView(config.songFill, config.songBackground,
			true, config.setSongDirection, songProgress, 0, 1, reportUnsupported);

		members = [config.healthBackground, config.healthFill, iconP1, iconP2,
			scoreTxt, config.songBackground, config.songFill, timeTxt];
		timeBar.visible = showTime;
		Reflect.setProperty(timeTxt, 'visible', showTime);
		if (timeBarType == 'Song Name' && config.songTitle != null)
			Reflect.setProperty(timeTxt, 'text', config.songTitle);
		// PsychHUD begins its time elements transparent and fades them in from
		// onSongStart. This mutates the live display targets, not placeholders.
		timeBar.alpha = 0;
		Reflect.setProperty(timeTxt, 'alpha', 0);
	}

	/** PsychHUD's source fade: tween the fill+background view and actual label. */
	public function onSongStart():Void {
		ensureAlive();
		if (tweenAlpha == null)
			unsupported('onSongStart requires the PlayState FlxTween adapter');
		tweenAlpha(timeBar, 0.5);
		tweenAlpha(timeTxt, 0.5);
	}

	/** Refresh the native health fill using the source Bar value function. */
	public function onHealthChange(?health:Float):Void {
		ensureAlive();
		healthBar.updateBar();
	}

	/** PsychHUD bops the same two live health icons on every beat. */
	public function beatHit():Void {
		ensureAlive();
		call(iconP1, 'bump', []);
		call(iconP2, 'bump', []);
	}

	/** Flip the native bar fill direction and both actual player icons. */
	public function flipBar():Void {
		ensureAlive();
		healthBar.leftToRight = !healthBar.leftToRight;
		Reflect.setProperty(iconP1, 'flipX', Reflect.getProperty(iconP1, 'flipX') != true);
		Reflect.setProperty(iconP2, 'flipX', Reflect.getProperty(iconP2, 'flipX') != true);
	}

	/** Update the source PsychHUD timer from the live audio clock.
		The native song position bar tracks `parent.songPositionBar`; the text
		field remains the actual PlayState song label/time label.
	*/
	public function updateTimer(songPosition:Float, songLength:Float, noteOffset:Float,
		type:String, startingSong:Bool, paused:Bool, endingSong:Bool,
		?songTitle:String):Void {
		ensureAlive();
		timeBarType = type == null ? timeBarType : type;
		var enabled = showTime && timeBarType != 'Disabled';
		if (!enabled || startingSong || paused || endingSong) return;
		var current = Math.max(0, songPosition - noteOffset);
		var fraction = songLength <= 0 ? 0 : current / songLength;
		Reflect.setProperty(parent, 'songPositionBar', fraction);
		timeBar.percent = fraction * 100;
		if (timeBarType == 'Song Name') {
			return;
		}
		var displayed = timeBarType == 'Time Elapsed' ? current : songLength - current;
		var seconds = Std.int(Math.max(0, Math.floor(displayed / 1000)));
		Reflect.setProperty(timeTxt, 'text', formatTime(seconds));
	}

	/** Refresh only the live objects that PsychHUD exposes through BaseHUD. */
	public function refreshAlpha(value:Float):Void {
		alpha = value;
	}

	/** Keep the source variable live and report when the native popup path cannot use it. */
	function get_ratingPrefix():String return ratingPrefixValue;
	function set_ratingPrefix(value:String):String {
		ensureAlive();
		ratingPrefixValue = value == null ? '' : value;
		if (applyRatingPrefix != null) applyRatingPrefix(ratingPrefixValue);
		else if (reportUnsupported != null)
			reportUnsupported('[nightmare-vision-hud-unsupported] ratingPrefix is stored, but the native rating popup renderer is not connected');
		return ratingPrefixValue;
	}

	/** State-owner callbacks preserve display-list ownership for added sprites. */
	public function add(object:Dynamic):Dynamic {
		ensureAlive();
		if (addDisplay == null) unsupported('playHUD.add requires a PlayState display-owner callback');
		var result = addDisplay(object);
		if (members.indexOf(object) < 0) members.push(object);
		return result;
	}

	public function remove(object:Dynamic, splice:Bool = false):Dynamic {
		ensureAlive();
		if (removeDisplay == null) unsupported('playHUD.remove requires a PlayState display-owner callback');
		var result = removeDisplay(object, splice);
		members.remove(object);
		return result;
	}

	public function insert(position:Int, object:Dynamic):Dynamic {
		ensureAlive();
		if (insertDisplay == null) unsupported('playHUD.insert requires a PlayState display-owner callback');
		var result = insertDisplay(position, object);
		members.insert(position, object);
		return result;
	}

	/** Explicit diagnostic for BaseHUD methods not backed by native behavior. */
	public function onUpdateScore(score:Int = 0, accuracy:Float = 0, misses:Int = 0, missed:Bool = false):Void
		unsupported('PsychHUD.onUpdateScore has no source-equivalent score formatter in this host');

	public function popUpScore(rating:Dynamic, combo:Int, note:Dynamic):Void
		unsupported('PsychHUD.popUpScore requires its source-owned rating sprites and cache');

	public function onEvent(eventName:String, v1:String, v2:String, strumTime:Float):Void
		unsupported('PsychHUD.onEvent is not implemented by the shared HUD host');

	public function onCharacterChange():Void
		unsupported('PsychHUD.onCharacterChange needs a host character/color refresh callback');

	public function stepHit():Void
		unsupported('BaseHUD.stepHit is not implemented by the shared HUD host');

	public function sectionHit():Void
		unsupported('BaseHUD.sectionHit is not implemented by the shared HUD host');

	public function cachePopUpScore():Void
		unsupported('PsychHUD.cachePopUpScore requires its source-owned rating sprites and cache');

	/** Release the bridge only; PlayState remains the sole owner of its sprites. */
	public function release():Void {
		if (released) return;
		released = true;
		if (healthBar != null) healthBar.release();
		if (timeBar != null) timeBar.release();
		healthBar = null;
		timeBar = null;
		iconP1 = null;
		iconP2 = null;
		scoreTxt = null;
		timeTxt = null;
		parent = null;
		members.resize(0);
		tweenAlpha = null;
		reportUnsupported = null;
		addDisplay = null;
		removeDisplay = null;
		insertDisplay = null;
		applyRatingPrefix = null;
	}

	/** Native state teardown owns the component destruction; scripts cannot
		independently destroy objects shared with PlayState. */
	public function destroy():Void
		unsupported('playHUD.destroy would destroy shared PlayState-owned HUD objects; use state teardown');

	function get_curStep():Int return Std.int(number(parent, 'curStep'));
	function get_curBeat():Int return Std.int(number(parent, 'curBeat'));
	function get_curSection():Int return Std.int(number(parent, 'curSection'));
	function get_alpha():Float return alphaValue;
	function set_alpha(value:Float):Float {
		ensureAlive();
		alphaValue = Math.max(0, Math.min(value, 1));
		for (object in members) if (object != null)
			Reflect.setProperty(object, 'alpha', alphaValue);
		return alphaValue;
	}
	function get_visible():Bool return visibleValue;
	function set_visible(value:Bool):Bool {
		ensureAlive();
		visibleValue = value;
		for (object in members) if (object != null)
			Reflect.setProperty(object, 'visible', value);
		return value;
	}
	function get_x():Float return groupX;
	function set_x(value:Float):Float {
		ensureAlive();
		var delta = value - groupX;
		groupX = value;
		if (healthBar != null) healthBar.moveBy(delta, 0);
		if (timeBar != null) timeBar.moveBy(delta, 0);
		for (object in [iconP1, iconP2, scoreTxt, timeTxt]) if (object != null)
			Reflect.setProperty(object, 'x', number(object, 'x') + delta);
		return value;
	}
	function get_y():Float return groupY;
	function set_y(value:Float):Float {
		ensureAlive();
		var delta = value - groupY;
		groupY = value;
		if (healthBar != null) healthBar.moveBy(0, delta);
		if (timeBar != null) timeBar.moveBy(0, delta);
		for (object in [iconP1, iconP2, scoreTxt, timeTxt]) if (object != null)
			Reflect.setProperty(object, 'y', number(object, 'y') + delta);
		return value;
	}
	function get_cameras():Dynamic return members.length == 0 ? null : Reflect.getProperty(members[0], 'cameras');
	function set_cameras(value:Dynamic):Dynamic {
		ensureAlive();
		for (object in members) if (object != null)
			Reflect.setProperty(object, 'cameras', value);
		return value;
	}

	function ensureAlive():Void {
		if (released) throw '[nightmare-vision-hud] Adapter was released';
	}

	function unsupported(message:String):Dynamic {
		var diagnostic = '[nightmare-vision-hud-unsupported] ' + message;
		if (reportUnsupported != null) reportUnsupported(diagnostic);
		throw diagnostic;
		return null;
	}

	static function formatTime(seconds:Int):String {
		var minutes = Std.int(seconds / 60);
		var remainder = seconds % 60;
		return minutes + ':' + (remainder < 10 ? '0' : '') + remainder;
	}

	static function number(target:Dynamic, field:String):Float {
		var value:Dynamic = target == null ? null : Reflect.getProperty(target, field);
		return value == null ? 0 : value;
	}

	static function call(target:Dynamic, methodName:String, args:Array<Dynamic>):Dynamic {
		var method = Reflect.field(target, methodName);
		if (method == null)
			throw '[nightmare-vision-hud-unsupported] native HUD method is unavailable: ' + methodName;
		return Reflect.callMethod(target, method, args);
	}
}
