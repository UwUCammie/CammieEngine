package;

/** Logical viewport geometry shared by host rows and their native checks. */
class FreeplayBrowserLayout {
	public static inline var TOP:Int = 112;
	public static inline var ROW_HEIGHT:Int = 42;
	public static inline var SELECTED_HEIGHT:Int = 82;
	public static function capacity(height:Int, selectedHeight:Int = SELECTED_HEIGHT):Int return Std.int(Math.max(1, Math.floor((height - TOP - 84 - (selectedHeight - ROW_HEIGHT)) / ROW_HEIGHT)));
	public static function rowY(position:Int, selectedPosition:Int, selectedHeight:Int = SELECTED_HEIGHT):Float return TOP + position * ROW_HEIGHT
		+ (selectedPosition >= 0 && position > selectedPosition ? selectedHeight - ROW_HEIGHT : 0);
	public static function listWidth(width:Int):Int return Std.int(width * 0.64) - 24;
	public static function detailX(width:Int):Int return Std.int(width * 0.66);
	public static function page(visible:Array<Int>, selected:Int, height:Int, selectedHeight:Int = SELECTED_HEIGHT):Array<Int> {
		var position = visible.indexOf(selected);
		if (position < 0) return [];
		var count = capacity(height, selectedHeight);
		var first = Std.int(Math.max(0, Math.min(position - Std.int(count / 2), visible.length - count)));
		return visible.slice(first, first + count);
	}
	public static function difficultyColumns(count:Int):Int return Std.int(Math.max(1, Math.min(6, count)));
	public static function difficultyHeight(count:Int):Int return Std.int(Math.max(SELECTED_HEIGHT, 24 + Math.ceil(count / difficultyColumns(count)) * 40));
	/** VCR is monospaced; truncate before rasterizing instead of spilling into adjacent columns. */
	public static function label(text:String, columns:Int):String {
		if (text == null) return '';
		text = text.split('\n').join(' ').split('\r').join(' ');
		return text.length <= columns ? text : text.substr(0, Std.int(Math.max(0, columns - 3))) + '...';
	}
}
