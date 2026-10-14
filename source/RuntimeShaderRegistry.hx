package;

/**
	Shaders that scripts load by name. One copy of the rules every script
	language follows: sources are read once per name as a fragment and vertex
	pair, nothing is built while the player has gameplay shaders turned off,
	and uniforms are read and written by kind.

	Where a name is looked up is the caller's business, passed in as a
	resolver, so an imported mod can only ever load its own shader files.
	How a shader object is built is passed in too, which keeps this class free
	of anything that needs a window.
*/
class RuntimeShaderRegistry {
	/** name -> [fragment, vertex]. Either half may be null, never both. */
	public final sources:Map<String, Array<String>> = new Map();

	final enabled:Void->Bool;
	final build:(String, String, String)->Dynamic;

	/** `build` receives fragment text, vertex text and the shader's name. */
	public function new(enabled:Void->Bool, build:(String, String, String)->Dynamic) {
		this.enabled = enabled;
		this.build = build;
	}

	public function isEnabled():Bool {
		return enabled == null || enabled();
	}

	/** Load a shader's sources if they are not loaded yet. `resolve` returns
		[fragment, vertex] text, or null when the name is not there for this caller. */
	public function init(name:String, resolve:String->Array<String>):Bool {
		if (!isEnabled() || name == null || StringTools.trim(name) == '') return false;
		if (sources.exists(name)) return true;
		var pair:Array<String> = null;
		if (resolve != null) try pair = resolve(name) catch (_:Dynamic) {}
		if (pair == null || (pair[0] == null && pair[1] == null)) return false;
		sources.set(name, [pair[0], pair[1]]);
		return true;
	}

	/** A new shader object for a name, loading its sources on first use. */
	public function create(name:String, ?resolve:String->Array<String>):Dynamic {
		if (!isEnabled() || name == null) return null;
		if (!sources.exists(name) && !init(name, resolve)) return null;
		var pair = sources.get(name);
		try return build(pair[0], pair[1], name) catch (_:Dynamic) return null;
	}

	/** Build a shader for a name and put it on an object. */
	public function setOn(target:Dynamic, name:String, ?resolve:String->Array<String>):Bool {
		if (target == null) return false;
		var shader = create(name, resolve);
		if (shader == null) return false;
		try {
			Reflect.setProperty(target, 'shader', shader);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	public static function remove(target:Dynamic):Bool {
		if (target == null) return false;
		try {
			Reflect.setProperty(target, 'shader', null);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** `kind` is the uniform kind as scripts spell it: Bool, Int, Float and their Array forms. */
	public static function getValue(shader:Dynamic, property:String, kind:String):Dynamic {
		if (shader == null || property == null) return null;
		var method = Reflect.field(shader, 'get' + kind);
		if (!Reflect.isFunction(method)) return null;
		try return Reflect.callMethod(shader, method, [property]) catch (_:Dynamic) return null;
	}

	public static function setValue(shader:Dynamic, property:String, value:Dynamic, kind:String):Bool {
		if (shader == null || property == null) return false;
		var method = Reflect.field(shader, 'set' + kind);
		if (!Reflect.isFunction(method)) return false;
		try {
			Reflect.callMethod(shader, method, [property, value]);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	public static function setSampler(shader:Dynamic, property:String, bitmap:Dynamic):Bool {
		if (bitmap == null) return false;
		return setValue(shader, property, bitmap, 'Sampler2D');
	}
}
