package;

/** Optional foreground progress sink. Asset and object helpers do not depend
 * on the display overlay, and import workers never call its renderer. */
class SongLoadingWork {
	static var sink:String->Void;
	#if (sys && target.threaded)
	static var owner:sys.thread.Thread;
	#end
	public static function install(callback:String->Void):Void {
		#if (sys && target.threaded)
		owner = sys.thread.Thread.current();
		#end
		sink = callback;
	}
	public static function complete<T>(value:T, kind:String = 'resource'):T {
		#if (sys && target.threaded)
		if (owner == null || !(sys.thread.Thread.current() == owner)) return value;
		#end
		if (sink != null) sink(kind);
		return value;
	}
}
