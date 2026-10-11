package;

/** One-use, in-memory discovery data owned by a verified refresh transaction.
	The caller authorizes it only after the complete dependency scan succeeds. */
class ImportDiscoveryReuse {
	static inline var MAX_SERIALIZED_BYTES:Int = 64 * 1024 * 1024;
	var source:String;
	var selector:String;
	var context:String;
	var currentContext:Void->Null<String>;
	var verifySource:Void->Void;
	var cancelled:Void->Bool;
	var payload:Null<String>;
	var captured:Bool = false;
	var accepted:Bool = false;
	var consumed:Bool = false;

	public function new(source:String, selector:String, currentContext:Void->Null<String>,
		verifySource:Void->Void, cancelled:Void->Bool) {
		this.source = source;
		this.selector = selector;
		this.currentContext = currentContext;
		this.verifySource = verifySource;
		this.cancelled = cancelled;
		context = currentContext();
	}

	function matches(source:String, selector:String):Bool {
		return !consumed && context != null && this.source == source && this.selector == selector
			&& !cancelled() && currentContext() == context;
	}

	public function capture(source:String, selector:String, discovery:Dynamic):Void {
		if (captured || !matches(source, selector) || discovery == null) return;
		captured = true;
		var packages:Dynamic = Reflect.field(discovery, "packageDiscovery");
		if (packages == null || packages.truncated == true || packages.cancelled == true
			|| !Std.isOfType(Reflect.field(discovery, "songs"), Array)) return;
		// Serialize before dependency inspection changes destination planning and
		// diagnostics. References inside the discovery graph remain shared, while
		// none of its mutable objects are shared with the scan or caller.
		try {
			var writer = new haxe.Serializer();
			writer.useCache = true;
			writer.serialize(discovery);
			var encoded = writer.toString();
			if (encoded.length <= MAX_SERIALIZED_BYTES) payload = encoded;
		} catch (_:Dynamic) {
			// Unsupported future conversion objects keep the ordinary discovery path.
			payload = null;
		}
	}

	public function accept():Void {
		accepted = payload != null && matches(source, selector);
	}

	public function take(source:String, selector:String):Dynamic {
		if (!accepted || payload == null || !matches(source, selector)) {
			close();
			return null;
		}
		var encoded = payload;
		payload = null;
		accepted = false;
		consumed = true;
		// Recheck the receipt, exact tree, containment and every source hash.
		// A changed source fails the transaction rather than using stale data.
		verifySource();
		if (cancelled()) throw "Import cancelled before discovery reuse.";
		if (currentContext() != context) return null;
		try return haxe.Unserializer.run(encoded) catch (_:Dynamic) return null;
	}

	public function close():Void {
		payload = null;
		accepted = false;
		consumed = true;
	}
}
