package;

/** Memoized value resolved only when an engine-owned container reads it. */
class HxcDeferredValue {
	var resolver:Void->Dynamic;
	var resolved:Bool = false;
	var value:Dynamic;

	public function new(resolver:Void->Dynamic) {
		this.resolver = resolver;
	}

	public function get():Dynamic {
		if (!resolved) {
			// Leave the wrapper retryable if native resolution throws.
			var next = resolver;
			value = next == null ? null : next();
			resolved = true;
			resolver = null;
		}
		return value;
	}
}
