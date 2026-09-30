package;

import hscript.ScriptClass;
import openfl.filters.ShaderFilter;

/** ShaderFilter constructor that accepts an owner-scoped HScript class proxy
	and gives OpenFL the native FlxShader object it wraps. */
class PsychShaderFilterCompat extends ShaderFilter {
	public function new(shader:Dynamic) {
		super(cast unwrapShader(shader));
	}

	static function unwrapShader(value:Dynamic):Dynamic {
		var current = value;
		var seen:Array<Dynamic> = [];
		while (current != null && Std.isOfType(current, ScriptClass)) {
			if (seen.indexOf(current) >= 0)
				throw '[psych-stage] cyclic HScript shader superclass chain';
			seen.push(current);
			current = (cast current:ScriptClass).superClass;
		}
		return current;
	}
}
