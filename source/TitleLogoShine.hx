package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.graphics.FlxGraphic;
import openfl.display.BitmapData;

/**
	Puts the trans flag shine on the stock title logo and times its sweeps.

	The shine is decoration: it is only attached to the logo that ships with the
	game (a custom title script that loads its own logo atlas, or a pack that
	replaced the atlas with another layout, gets the logo untouched), only when
	shaders are on in the options, and only when the mask and the shader can be
	created. Every other case returns null and leaves the sprite exactly as it
	was. Once attached it is dropped again if a script swaps the logo's graphic
	or installs a shader of its own.
**/
class TitleLogoShine
{
	/** Folder of the stock title assets. Scripts that load other art pass their own. */
	public static inline var STOCK_PATH:String = 'assets/images/';
	public static inline var MASK_PATH:String = 'assets/images/logoBumpinShine.png';
	public static inline var SHEET_SIZE:Int = 2048;

	/** Seconds from the start of one sweep to the start of the next. */
	public static inline var PERIOD:Float = 4.8;
	/** Seconds a sweep takes to cross the text. */
	public static inline var SWEEP:Float = 1.7;
	/** Seconds after the title appears before the first sweep, so the camera flash has faded. */
	public static inline var FIRST_DELAY:Float = 1.2;
	/** Half the shine's width in mask units: the band starts and ends this far outside the text. */
	public static inline var REACH:Float = 0.12;

	/**
		The four distinct frame rectangles of assets/images/logoBumpin.xml, as
		x, y, width, height. The mask only fits an atlas laid out like this.
	**/
	static final STOCK_RECTS:Array<Array<Int>> = [[0, 0, 922, 670], [922, 0, 969, 703], [0, 703, 940, 683], [940, 703, 933, 679]];

	/** Harness override: when set, the sweep is frozen at this many seconds into its cycle. */
	public static var frozenTime:Null<Float> = null;

	var sprite:FlxSprite;
	var shader:TitleShineShader;
	var graphic:FlxGraphic;
	var time:Float = -FIRST_DELAY;
	var running:Bool = false;

	function new(sprite:FlxSprite, shader:TitleShineShader)
	{
		this.sprite = sprite;
		this.shader = shader;
		this.graphic = sprite.graphic;
	}

	/**
		Band centre, in mask units, `seconds` into the cycle; TitleShineShader.IDLE
		between sweeps. It runs from one reach left of the text to one reach right
		of it, slowing slightly at both ends.
	**/
	public static function centerAt(seconds:Float):Float
	{
		if (seconds < 0)
			return TitleShineShader.IDLE;
		var phase = seconds % PERIOD;
		if (phase >= SWEEP)
			return TitleShineShader.IDLE;
		var t = phase / SWEEP;
		var eased = t * t * (3 - 2 * t);
		t = t * 0.5 + eased * 0.5;
		return -REACH + t * (1 + 2 * REACH);
	}

	/** True when `rects` (x, y, width, height per frame) are all frames of the stock logo sheet. */
	public static function isStockLayout(rects:Array<Array<Int>>, sheetWidth:Int, sheetHeight:Int):Bool
	{
		if (sheetWidth != SHEET_SIZE || sheetHeight != SHEET_SIZE || rects == null || rects.length == 0)
			return false;
		for (rect in rects)
		{
			var known = false;
			for (stock in STOCK_RECTS)
				if (rect.length == 4 && rect[0] == stock[0] && rect[1] == stock[1] && rect[2] == stock[2] && rect[3] == stock[3])
					known = true;
			if (!known)
				return false;
		}
		return true;
	}

	/** False without a GL context (software rendering), where shaders do not run. */
	static function shadersAvailable():Bool
	{
		#if flash
		return false;
		#else
		return FlxG.stage != null && FlxG.stage.context3D != null;
		#end
	}

	/**
		Attach the shine to `logo`, which was just loaded from the atlas in `path`.
		Returns null, with the sprite untouched, when the shine does not apply.
	**/
	public static function attach(logo:FlxSprite, path:String):Null<TitleLogoShine>
	{
		if (logo == null || path != STOCK_PATH || logo.frames == null || logo.graphic == null)
			return null;
		if (!OptionsHandler.options.gameplayShaders || !shadersAvailable())
			return null;
		var rects:Array<Array<Int>> = [];
		for (frame in logo.frames.frames)
			rects.push([Std.int(frame.frame.x), Std.int(frame.frame.y), Std.int(frame.frame.width), Std.int(frame.frame.height)]);
		if (!isStockLayout(rects, logo.graphic.width, logo.graphic.height))
			return null;
		try
		{
			var mask:BitmapData = FNFAssets.getBitmapData(MASK_PATH);
			if (mask == null || mask.width != SHEET_SIZE || mask.height != SHEET_SIZE)
				return null;
			var shader = new TitleShineShader();
			shader.setMask(mask);
			var shine = new TitleLogoShine(logo, shader);
			logo.shader = shader;
			return shine;
		}
		catch (error:Dynamic)
		{
			trace('Title logo shine is unavailable: ' + error);
			return null;
		}
	}

	/** Start the clock; called when the logo comes into view. */
	public function start():Void
	{
		running = true;
	}

	public function update(elapsed:Float):Void
	{
		if (shader == null)
			return;
		if (sprite == null || !sprite.exists || sprite.graphic != graphic || sprite.shader != shader)
		{
			release();
			return;
		}
		if (frozenTime != null)
		{
			shader.setCenter(centerAt(frozenTime));
			return;
		}
		if (!running)
			return;
		time += elapsed;
		shader.setCenter(centerAt(time));
	}

	/** Stop shining. The shader is only removed if it is still the sprite's own. */
	public function release():Void
	{
		if (shader != null && sprite != null && sprite.shader == shader)
			sprite.shader = null;
		shader = null;
		sprite = null;
		graphic = null;
	}
}
