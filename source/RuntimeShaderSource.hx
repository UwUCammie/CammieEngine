package;

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
		return source == null ? null : CodenameShaderSource.normalizeOpenFL(source);
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
