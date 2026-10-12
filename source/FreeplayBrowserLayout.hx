package;

/** Logical viewport geometry shared by host rows and their native checks. */
class FreeplayBrowserLayout {
	public static inline var TOP:Int = 112;
	public static inline var ROW_HEIGHT:Int = 64;
	public static function capacity(height:Int):Int return Std.int(Math.max(1, Math.floor((height - TOP - 84) / ROW_HEIGHT)));
	public static function listWidth(width:Int):Int return Std.int(width * 0.64) - 24;
	public static function detailX(width:Int):Int return Std.int(width * 0.66);
	public static function page(visible:Array<Int>, selected:Int, height:Int):Array<Int> {
		var position = visible.indexOf(selected);
		if (position < 0) return [];
		var count = capacity(height);
		var first = Std.int(Math.max(0, Math.min(position - Std.int(count / 2), visible.length - count)));
		return visible.slice(first, first + count);
	}
	/** VCR is monospaced; truncate before rasterizing instead of spilling into adjacent columns. */
	public static function label(text:String, columns:Int):String {
		if (text == null) return '';
		text = text.split('\n').join(' ').split('\r').join(' ');
		return text.length <= columns ? text : text.substr(0, Std.int(Math.max(0, columns - 3))) + '...';
	}
}
