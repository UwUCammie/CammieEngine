package;

/** Continue, Stop, or Unhandled when no engine owned an exclusive event. */
enum abstract SourceCallbackOutcome(Int) {
	var Continue = 0;
	var Stop = 1;
	var Unhandled = 2;

	public var stopped(get, never):Bool;
	inline function get_stopped():Bool return this == 1;
	public var handled(get, never):Bool;
	inline function get_handled():Bool return this != 2;
}
