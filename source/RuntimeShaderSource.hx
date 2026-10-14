package;

/** A value written as `uniform <type> <name> = <value>;` in shader text. */
typedef UniformDefault = {
	var name:String;
	var type:String;
	var values:Array<Float>;
}

/**
	The parts of a runtime shader that do not need a GL context: getting the
	source text ready for the compiler, and deciding what happens when the
	driver rejects it. Kept apart from the shader class so both can be run
	without a window.
*/
class RuntimeShaderSource {
	/** Draw the sprite untouched with the stock fragment when the shader is broken. */
	public static inline var PASS_THROUGH:Int = 0;
	/** Hand back no program at all, which is what Psych does: the sprite stops drawing. */
	public static inline var NULL_PROGRAM:Int = 1;

	/** Older scripts pass GLSL text where newer ones pass a shader name. */
	public static function looksLikeSource(text:String):Bool {
		return text != null && (StringTools.ltrim(text).indexOf('#pragma') == 0 || text.indexOf('void main') != -1);
	}

	/** One half of a shader pair, ready for OpenFL. A missing half stays missing
		so the runtime shader falls back to its stock source for it. */
	public static function prepare(source:Null<String>):Null<String> {
		return source == null ? null : CodenameShaderSource.normalizeOpenFL(stripUniformInitializers(source));
	}

	/**
		Desktop GLSL accepts `uniform float x = 0.5;` but GLSL ES 1.00 does not,
		so on those drivers the whole shader used to be dropped. The initializer
		is removed here and the value comes back through uniformDefaults, which
		the shader class applies once it exists.
	*/
	public static function stripUniformInitializers(source:Null<String>):Null<String> {
		if (source == null || source.indexOf('uniform') == -1) return source;
		return scanUniformInitializers(source, null);
	}

	/** The initial values written on uniform declarations, in source order. A
		value that is not a plain literal or same-type constructor is left out
		and the uniform starts at zero, as it would without an initializer. */
	public static function uniformDefaults(source:Null<String>):Array<UniformDefault> {
		var found:Array<UniformDefault> = [];
		if (source != null && source.indexOf('uniform') != -1) scanUniformInitializers(source, found);
		return found;
	}

	static function scanUniformInitializers(source:String, found:Null<Array<UniformDefault>>):String {
		var declaration = ~/\buniform[ \t]+((lowp|mediump|highp)[ \t]+)?([A-Za-z0-9_]+)[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*=([^;]*);/g;
		return declaration.map(source, function(match:EReg):String {
			var start = match.matchedPos().pos;
			var lineStart = source.lastIndexOf('\n', start) + 1;
			// A declaration sitting in a line comment is not compiled, so it is
			// neither rewritten nor turned into a default.
			if (source.substring(lineStart, start).indexOf('//') != -1) return match.matched(0);
			var precision = match.matched(2) == null ? '' : match.matched(2) + ' ';
			var type = match.matched(3);
			var name = match.matched(4);
			if (found != null) {
				var values = parseUniformInitializer(type, match.matched(5));
				if (values != null) found.push({name: name, type: type, values: values});
			}
			return 'uniform ' + precision + type + ' ' + name + ';';
		});
	}

	static function uniformComponentCount(type:String):Int {
		if (type == 'float' || type == 'int' || type == 'bool') return 1;
		var last = type.charCodeAt(type.length - 1) - '0'.code;
		var prefix = type.substr(0, type.length - 1);
		if (last >= 2 && last <= 4 && (prefix == 'vec' || prefix == 'ivec' || prefix == 'bvec')) return last;
		return 0;
	}

	static function parseUniformInitializer(type:String, text:String):Null<Array<Float>> {
		var size = uniformComponentCount(type);
		if (size == 0) return null;
		text = StringTools.trim(text);
		var parts:Array<String>;
		var open = text.indexOf('(');
		if (open != -1) {
			if (!StringTools.endsWith(text, ')') || StringTools.trim(text.substr(0, open)) != type) return null;
			parts = text.substring(open + 1, text.length - 1).split(',');
		} else
			parts = [text];
		var values:Array<Float> = [];
		for (part in parts) {
			var item = StringTools.trim(part);
			var value = item == 'true' ? 1.0 : item == 'false' ? 0.0 : Std.parseFloat(item);
			if (item == '' || Math.isNaN(value)) return null;
			values.push(value);
		}
		// `vec3(0.5)` fills every component, as GLSL does.
		if (values.length == 1 && size > 1) values = [for (_ in 0...size) values[0]];
		return values.length == size ? values : null;
	}

	/** Both halves at once, as [fragment, vertex]. */
	public static function prepareSources(fragment:Null<String>, vertex:Null<String>):Array<Null<String>> {
		return [prepare(fragment), prepare(vertex)];
	}

	/**
		Runs the compile step and recovers when it throws. The error hook is told
		exactly once per failed shader, before any retry, so a retry that also
		fails cannot report twice.
	*/
	public static function recover<T>(mode:Int, compile:(String, String)->T, vertex:String, fragment:String,
		templateFragment:String, ?onError:Dynamic->Void):Null<T> {
		try {
			return compile(vertex, fragment);
		} catch (error:Dynamic) {
			if (onError != null) try onError(error) catch (_:Dynamic) {}
			if (mode != PASS_THROUGH || templateFragment == null) return null;
			// The vertex half is kept: a broken fragment is by far the common
			// case, and if the vertex is the broken one this fails again and
			// ends up as no program.
			try return compile(vertex, templateFragment) catch (_:Dynamic) return null;
		}
	}
}
