package;

/** Captured source pointers, independent of mutable field IDs and collection order. */
class NightmareVisionLegacyReceptors {
	public var player:NightmareVisionPlayFieldView;
	public var opponent:NightmareVisionPlayFieldView;
	public function new() {}
	public function capture(lane:Int, field:NightmareVisionPlayFieldView):Void {
		if (lane == 0) player = field;
		else if (lane == 1) opponent = field;
	}
	public function release():Void {player = null; opponent = null;}
}
