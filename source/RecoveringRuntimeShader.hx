package;

import flixel.addons.display.FlxRuntimeShader;
import flixel.addons.system.macros.FlxRuntimeShaderMacro;
import lime.graphics.opengl.GLProgram;

/**
	Runtime shader built from source text. Every script front end ends up here,
	so the two things they all need live here once: the text is made safe for
	OpenFL's compiler, and a shader the driver rejects does not take the game
	down with it. What "recover" means is the only thing a front end picks.
*/
class RecoveringRuntimeShader extends FlxRuntimeShader {
	/** RuntimeShaderSource.PASS_THROUGH or NULL_PROGRAM. */
	public var compileRecovery:Int = RuntimeShaderSource.PASS_THROUGH;
	/** Name or path shown in the log when the shader does not compile. */
	public var shaderLabel:String = '';
	/** Called once with the compiler error, before recovery. */
	public dynamic function onCompileError(error:Dynamic):Void {}

	public function new(?fragmentSource:String, ?vertexSource:String, ?recovery:Int, ?label:String) {
		// Either half may be missing (a vertex-only shader is fine), and
		// whichever is there still has to go through the normaliser.
		super(RuntimeShaderSource.prepare(fragmentSource), RuntimeShaderSource.prepare(vertexSource));
		if (recovery != null) compileRecovery = recovery;
		if (label != null) shaderLabel = label;
	}

	// OpenFL compiles on first draw, not in the constructor, so a try/catch
	// around `new` never sees a GLSL error. This is the one place that does.
	@:noCompletion override function __createGLProgram(vertexSource:String, fragmentSource:String):GLProgram {
		return RuntimeShaderSource.recover(compileRecovery, compileProgram, vertexSource, fragmentSource,
			passThroughFragment, reportCompileError);
	}

	function compileProgram(vertexSource:String, fragmentSource:String):GLProgram {
		return super.__createGLProgram(vertexSource, fragmentSource);
	}

	function reportCompileError(error:Dynamic):Void {
		// Keep this loud: with recovery the only other symptom is a sprite that
		// looks plain or goes missing.
		trace('[shader-compile-error] ' + (shaderLabel == null || shaderLabel == '' ? '<unnamed>' : shaderLabel)
			+ (compileRecovery == RuntimeShaderSource.PASS_THROUGH ? ' (drawing without it)' : ' (not drawing)')
			+ ': ' + Std.string(error));
		onCompileError(error);
	}

	static final passThroughFragment:String = FlxRuntimeShaderMacro.retrieveMetadata('glFragmentHeader') + "
		void main()
		{
			gl_FragColor = flixel_texture2D(bitmap, openfl_TextureCoordv);
		}
	";
}
