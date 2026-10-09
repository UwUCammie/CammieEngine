package;

/** Ordering tokens shared by source script runtimes, independent of language. */
class SourceScriptRegistrationOrder {
	static var serial:Int = 0;
	public static function next():Int return ++serial;
}
