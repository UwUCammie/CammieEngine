package;

import flixel.addons.display.FlxRuntimeShader;
import flixel.addons.system.macros.FlxRuntimeShaderMacro;
import lime.graphics.opengl.GLProgram;

/** NMV's FunkinRuntimeShader behavior over the selected import's shader text. */
@:keep
class NightmareVisionRuntimeShader extends FlxRuntimeShader {
	final fragmentPath:String;
	final vertexPath:String;

	public function new(?fragmentSource:String, ?vertexSource:String, ?fragmentPath:String, ?vertexPath:String) {
		// OpenFL's GLSL 1.00 path rejects mixed int/float arithmetic that the
		// source shader dialect accepts. Keep the asset text intact and normalize
		// only the strings passed to the shared runtime compiler.
		super(fragmentSource == null ? null : CodenameShaderSource.normalizeOpenFL(fragmentSource),
			vertexSource == null ? null : CodenameShaderSource.normalizeOpenFL(vertexSource));
		this.fragmentPath = fragmentPath;
		this.vertexPath = vertexPath;
	}

	override function __createGLProgram(vertexSource:String, fragmentSource:String):GLProgram {
		try {
			return super.__createGLProgram(vertexSource, fragmentSource);
		} catch (error:Dynamic) {
			trace('[nightmare-vision-shader-compile] fragment=' + (fragmentPath == null ? '<default>' : fragmentPath)
				+ ' vertex=' + (vertexPath == null ? '<default>' : vertexPath) + ': ' + Std.string(error));
			// Match FunkinRuntimeShader's compile-error recovery. Missing files are
			// rejected by the factory before construction and never reach this path.
			@:privateAccess return super.__createGLProgram(vertexSource, fallbackFragment);
		}
	}

	override function toString():String return 'FunkinRuntimeShader';

	static final fallbackFragment:String = FlxRuntimeShaderMacro.retrieveMetadata('glFragmentHeader') + "
		void main()
		{
			gl_FragColor = flixel_texture2D(bitmap, openfl_TextureCoordv);
		}
	";
}
