package;

/** NMV's ScriptConstants surface, with state lookup supplied by the live host. */
@:keep
class NightmareVisionScriptConstants {
	public final STOP_FUNC:Int = NightmareVisionScriptGroup.STOP_FUNC;
	public final CONTINUE_FUNC:Int = NightmareVisionScriptGroup.CONTINUE_FUNC;
	public final HALT_FUNC:Int = NightmareVisionScriptGroup.HALT_FUNC;
	final currentState:Void->Dynamic;

	public function new(currentState:Void->Dynamic) this.currentState = currentState;

	public function getInstance():Dynamic return currentState();
}
