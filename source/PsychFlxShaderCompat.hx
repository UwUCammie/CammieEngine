package;

import flixel.graphics.tile.FlxGraphicsShader;
import openfl.display.BitmapData;
import openfl.display.ShaderInput;

/** Flixel shader base used by interpreted Psych shader classes. OpenFL's
	@:gl* macros do not run on hscript-ex modules, so the owner loader supplies
	expanded GLSL and this constructor creates the usual ShaderData wrappers. */
@:access(openfl.display.Shader)
@:access(openfl.display.ShaderInput)
class PsychFlxShaderCompat extends FlxGraphicsShader {
	public function new(?vertexSource:String, ?fragmentSource:String) {
		super();
		if (vertexSource != null) glVertexSource = vertexSource;
		if (fragmentSource != null) glFragmentSource = fragmentSource;

		// Keep OpenFL's generated values in ShaderData only. The HScript subclass
		// gets matching interpreted fields from PsychShaderSourceCompat, which
		// initializes them from this shader's data after super(). Setting
		// __isGenerated here would also Reflect.setField(this, uniform, value);
		// native targets reject those undeclared fields on this compiled adapter.
		__isGenerated = false;
		if (__inputBitmapData == null) __inputBitmapData = [];
		if (__paramBool == null) __paramBool = [];
		if (__paramFloat == null) __paramFloat = [];
		if (__paramInt == null) __paramInt = [];
		if (glVertexSource != null) {
			processGLData(glVertexSource, 'attribute');
			processGLData(glVertexSource, 'uniform');
		}
		if (glFragmentSource != null)
			processGLData(glFragmentSource, 'uniform');

		// __processGLData is also called lazily by Shader.data. We already built
		// the parameter arrays above, so keep the compiled source dirty flag clear
		// to prevent that second parse from reflecting arbitrary uniform names on
		// this native class. A null program still makes __initGL compile the full
		// original sources later when a rendering context is available.
		if (vertexSource != null || fragmentSource != null) {
			program = null;
			__glSourceDirty = false;
		}
	}

	function processGLData(source:String, storageType:String):Void {
		if (source == null) return;
		if (storageType != 'uniform') {
			__processGLData(source, storageType);
			return;
		}

		// OpenFL's sampler path reflects each ShaderInput onto the native shader
		// object. Keep those declarations out of that parser and register the
		// equivalent input wrapper in ShaderData and __inputBitmapData directly.
		var sampler = ~/\buniform\s+(sampler[A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)(?:\s*\[[^\]]+\])?\s*;?/g;
		var names:Array<String> = [];
		var masked = new StringBuf();
		var offset = 0;
		while (sampler.matchSub(source, offset)) {
			var span = sampler.matchedPos();
			masked.add(source.substring(offset, span.pos));
			masked.add(' ');
			offset = span.pos + span.len;
			names.push(sampler.matched(2));
		}
		masked.add(source.substr(offset));
		__processGLData(masked.toString(), storageType);

		for (name in names) {
			var existing:Dynamic = Reflect.field(__data, name);
			var input:ShaderInput<BitmapData> = Std.isOfType(existing, ShaderInput)
				? cast existing : new ShaderInput<BitmapData>();
			input.name = name;
			input.__isUniform = true;
			if (__inputBitmapData.indexOf(input) < 0) __inputBitmapData.push(input);
			switch (name) {
				case 'openfl_Texture': __texture = input;
				case 'bitmap': __bitmap = input;
				default:
			}
			Reflect.setField(__data, name, input);
		}
	}
}

/** Runtime constants for the abstract ShaderParameterType names that Haxe
	imports as type-only module paths. */
class PsychShaderParameterTypeCompat {
	public static var BOOL:Dynamic = openfl.display.ShaderParameterType.BOOL;
	public static var BOOL2:Dynamic = openfl.display.ShaderParameterType.BOOL2;
	public static var BOOL3:Dynamic = openfl.display.ShaderParameterType.BOOL3;
	public static var BOOL4:Dynamic = openfl.display.ShaderParameterType.BOOL4;
	public static var FLOAT:Dynamic = openfl.display.ShaderParameterType.FLOAT;
	public static var FLOAT2:Dynamic = openfl.display.ShaderParameterType.FLOAT2;
	public static var FLOAT3:Dynamic = openfl.display.ShaderParameterType.FLOAT3;
	public static var FLOAT4:Dynamic = openfl.display.ShaderParameterType.FLOAT4;
	public static var INT:Dynamic = openfl.display.ShaderParameterType.INT;
	public static var INT2:Dynamic = openfl.display.ShaderParameterType.INT2;
	public static var INT3:Dynamic = openfl.display.ShaderParameterType.INT3;
	public static var INT4:Dynamic = openfl.display.ShaderParameterType.INT4;
}
