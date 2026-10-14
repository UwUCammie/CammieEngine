package;

/** NMV's FunkinRuntimeShader behavior over the selected import's shader text. */
@:keep
class NightmareVisionRuntimeShader extends RecoveringRuntimeShader {
	final fragmentPath:String;
	final vertexPath:String;

	public function new(?fragmentSource:String, ?vertexSource:String, ?fragmentPath:String, ?vertexPath:String) {
		// FunkinRuntimeShader recovers from a compile error by drawing with the
		// stock fragment, which is the shared shader's pass-through policy.
		// Missing files are rejected by the factory before construction.
		super(fragmentSource, vertexSource, RuntimeShaderSource.PASS_THROUGH,
			'fragment=' + (fragmentPath == null ? '<default>' : fragmentPath)
			+ ' vertex=' + (vertexPath == null ? '<default>' : vertexPath));
		this.fragmentPath = fragmentPath;
		this.vertexPath = vertexPath;
	}

	override function toString():String return 'FunkinRuntimeShader';
}
