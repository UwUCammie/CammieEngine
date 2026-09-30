package;

import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.util.FlxColor;

/** Codename's shared text constructor with a selected-owner default font. */
class CodenameFunkinText extends FlxText {
	public var zoomFactor:Float = 1;
	public var zoomFactorEnabled:Bool = true;
	public var angleFactor:Float = 1;
	public var angleFactorEnabled:Bool = true;

	public function new(X:Float = 0, Y:Float = 0, FieldWidth:Float = 0,
		?Text:String, ?Size:Int, Border:Bool = true, ?paths:CodenamePaths) {
		var fontSize = Size == null ? 16 : Size;
		super(X, Y, FieldWidth, Text, fontSize);
		if (paths == null)
			throw '[codename-text] FunkinText requires selected-owner Paths';
		setFormat(defaultFont(paths), fontSize, FlxColor.WHITE);
		if (Border) {
			borderStyle = FlxTextBorderStyle.OUTLINE;
			borderSize = 1;
			borderColor = FlxColor.BLACK;
		}
	}

	/** HScript constructor arguments are dynamic, so apply Codename defaults
	 * before making the typed instance. */
	public static function fromArgs(args:Array<Dynamic>, paths:CodenamePaths):CodenameFunkinText {
		if (args == null) args = [];
		if (args.length > 6)
			throw '[codename-text] FunkinText accepts at most six constructor arguments';
		var x = numberArg(args, 0, 0);
		var y = numberArg(args, 1, 0);
		var width = numberArg(args, 2, 0);
		var text:String = null;
		if (args.length > 3 && args[3] != null) {
			if (!Std.isOfType(args[3], String))
				throw '[codename-text] FunkinText text argument must be a string';
			text = cast args[3];
		}
		var size:Null<Int> = args.length > 4 && args[4] != null ? intArg(args[4], 4) : null;
		var border = args.length <= 5 || args[5] == null ? true : boolArg(args[5], 5);
		return new CodenameFunkinText(x, y, width, text, size, border, paths);
	}

	static function numberArg(args:Array<Dynamic>, index:Int, fallback:Float):Float {
		if (args.length <= index || args[index] == null) return fallback;
		return switch (Type.typeof(args[index])) {
			case TInt | TFloat: cast args[index];
			default: throw '[codename-text] FunkinText argument ' + index + ' must be numeric';
		};
	}

	static function intArg(value:Dynamic, index:Int):Int {
		return switch (Type.typeof(value)) {
			case TInt: cast value;
			default: throw '[codename-text] FunkinText argument ' + index + ' must be an integer';
		};
	}

	static function boolArg(value:Dynamic, index:Int):Bool {
		return switch (Type.typeof(value)) {
			case TBool: cast value;
			default: throw '[codename-text] FunkinText argument ' + index + ' must be boolean';
		};
	}

	static function defaultFont(paths:CodenamePaths):String {
		try return paths.font('vcr.ttf') catch (ownerError:Dynamic) {
			// Codename's default font is an engine asset. A mod-provided vcr.ttf
			// always wins; otherwise use only the engine's shared default path.
			if (FNFAssets.exists('assets/fonts/vcr.ttf')) return 'assets/fonts/vcr.ttf';
			throw ownerError;
		}
	}
}
