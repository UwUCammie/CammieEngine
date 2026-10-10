package;

/** Live source roots, independent of the owner that loaded a stage's assets. */
class SourceStageContext {
	public final state:Void->Dynamic;
	public final play:Void->Dynamic;
	public final isPlay:Dynamic->Bool;
	public final staticValue:String->Dynamic;

	public function new(state:Void->Dynamic, play:Void->Dynamic,
		isPlay:Dynamic->Bool, staticValue:String->Dynamic) {
		this.state = state;
		this.play = play;
		this.isPlay = isPlay;
		this.staticValue = staticValue;
	}
}
