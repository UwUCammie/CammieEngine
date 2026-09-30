package;

import flixel.FlxSprite;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.tweens.FlxTween;
import flixel.util.FlxColor;
import flixel.util.FlxTimer;

/** Shared, owner-scoped implementation of HL17's public typewriter widget.

	The donor class subclasses FlxText but renders each character into a separate
	sprite group. Its bundled implementation depends only on Flixel; reproducing
	that behavior here lets imported states use it without compiling donor Haxe
	classes into the engine.
*/
class CodenameHLTypeTextCompat extends FlxText {
	public var smallCharacters:String = 'PSortfslij1:';
	public var lettersGroup:FlxTypedSpriteGroup<FlxSprite>;
	public var fadeLetters:Bool = true;
	public var onComplete:Void->Void;

	final ownerPaths:CodenamePaths;
	final ownedTimers:Array<FlxTimer> = [];
	final ownedTweens:Array<FlxTween> = [];

	public function new(x:Float, y:Float, text:String, color:Dynamic,
		playNow:Bool, paths:CodenamePaths) {
		super(x, y, 0, '', 8);
		if (paths == null)
			throw '[codename-hl17-text] HLTypeText requires selected-owner Paths';
		ownerPaths = paths;
		lettersGroup = new FlxTypedSpriteGroup<FlxSprite>();
		if (playNow) playText(x, y, text, color);
	}

	/** HScript constructor arguments are dynamic; normalize them before any
	 * native Flixel constructor receives a value. */
	public static function fromArgs(args:Array<Dynamic>, paths:CodenamePaths):CodenameHLTypeTextCompat {
		if (args == null) args = [];
		if (args.length > 5)
			throw '[codename-hl17-text] HLTypeText accepts at most five constructor arguments';
		var x = numberArg(args, 0, 0);
		var y = numberArg(args, 1, 0);
		var text = stringArg(args, 2, '');
		var color:Dynamic = args.length <= 3 || args[3] == null ? 0xFFFFAA00 : args[3];
		var playNow = boolArg(args, 4, false);
		return new CodenameHLTypeTextCompat(x, y, text, color, playNow, paths);
	}

	public function playText(?x:Float = 0, ?y:Float = 0, ?text:String = '', ?color:Dynamic = 0xFFFFAA00):Void {
		if (text == null) text = '';
		var resolvedColor:Dynamic = color == null ? 0xFFFFAA00 : color;
		var sourceColor:FlxColor = cast resolvedColor;
		var texts:Array<FlxText> = [];
		var index = 0;
		var previousCharacter = '';
		// Resolve once through the selected import. A missing owner font is a
		// real asset diagnostic; it must not silently borrow a sibling's font.
		var fontPath:String = null;

		for (character in text.split('')) {
			if (fontPath == null) fontPath = ownerPaths.font('trebuc.ttf');
			var glyph = new FlxText(x, y, -1, character, 32);
			glyph.font = fontPath;
			glyph.color = cast resolvedColor;
			glyph.alpha = 0.001;
			glyph.borderColor = 0xFF000000;
			glyph.borderSize = 1;
			glyph.borderStyle = FlxTextBorderStyle.OUTLINE;
			glyph.ID = index;
			lettersGroup.add(glyph);

			if (index > 0) {
				glyph.x = texts[index - 1].x + glyph.width;
				if (smallCharacters.indexOf(character) >= 0) glyph.x += 4;
				if (smallCharacters.indexOf(previousCharacter) >= 0) glyph.x -= 6;
				if (character == 'I') glyph.offset.x = -10;
				if (character == 'M') glyph.offset.x = 5;
			}

			texts.push(glyph);
			var currentGlyph = glyph;
			ownTimer(0.07 * index, function():Void {
				ownTween(FlxTween.color(currentGlyph, 0.19, sourceColor, cast 0xFFADADAD));
				ownTween(FlxTween.tween(currentGlyph, {alpha:0.85}, 0.2));
			});

			index++;
			previousCharacter = character;
		}

		ownTimer(0.07 * text.length, function():Void {
			if (onComplete != null) onComplete();
			if (!fadeLetters) return;
			ownTimer(2.8, function():Void {
				for (glyph in texts)
					ownTween(FlxTween.tween(glyph, {alpha:0}, 0.5));
			});
		});
	}

	function ownTimer(duration:Float, callback:Void->Void):Void {
		var timer:FlxTimer = new FlxTimer();
		ownedTimers.push(timer);
		timer.start(duration, function(_:FlxTimer):Void {
			ownedTimers.remove(timer);
			callback();
		});
	}

	function ownTween<T:FlxTween>(tween:T):T {
		ownedTweens.push(tween);
		tween.onComplete = function(_:FlxTween):Void ownedTweens.remove(tween);
		return tween;
	}

	static function numberArg(args:Array<Dynamic>, index:Int, fallback:Float):Float {
		if (args.length <= index || args[index] == null) return fallback;
		return switch (Type.typeof(args[index])) {
			case TInt | TFloat: cast args[index];
			default: throw '[codename-hl17-text] HLTypeText argument ' + index + ' must be numeric';
		};
	}

	static function stringArg(args:Array<Dynamic>, index:Int, fallback:String):String {
		if (args.length <= index || args[index] == null) return fallback;
		if (!Std.isOfType(args[index], String))
			throw '[codename-hl17-text] HLTypeText argument ' + index + ' must be a string';
		return cast args[index];
	}

	static function boolArg(args:Array<Dynamic>, index:Int, fallback:Bool):Bool {
		if (args.length <= index || args[index] == null) return fallback;
		if (!Std.isOfType(args[index], Bool))
			throw '[codename-hl17-text] HLTypeText argument ' + index + ' must be boolean';
		return cast args[index];
	}

	override public function destroy():Void {
		for (timer in ownedTimers) {
			timer.cancel();
			timer.destroy();
		}
		ownedTimers.resize(0);
		for (tween in ownedTweens) {
			tween.cancel();
			tween.destroy();
		}
		ownedTweens.resize(0);
		// The donor state usually adds both this object and lettersGroup as
		// separate state members. Flixel destruction is idempotent, and owning
		// the group here also covers script-init failures before it was added.
		if (lettersGroup != null) {
			lettersGroup.destroy();
			lettersGroup = null;
		}
		onComplete = null;
		super.destroy();
	}
}
