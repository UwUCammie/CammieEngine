package;

/** Chart metadata for one outgoing/incoming transition pair, without retaining
 * the destroyed gameplay state or its scripts and renderer. */
class CodenameTransitionSongLease {
	var owner:String = '';
	var chart:Dynamic;
	var view:CodenameSongView;
	public function new() {}
	public function capture(owner:String, chart:Dynamic, metadata:Dynamic):Void {
		clear();
		if (owner == null || owner == '' || chart == null) return;
		this.owner = owner;
		this.chart = chart;
		view = new CodenameSongView(function() return chart, metadata);
	}
	public function take(owner:String, chart:Dynamic):CodenameSongView {
		var result = CodenameTransitionScope.sameOwner(this.owner, owner)
			&& this.chart == chart ? view : null;
		clear();
		return result;
	}
	public function clear(?owner:String):Void {
		if (owner != null && !CodenameTransitionScope.sameOwner(this.owner, owner)) return;
		this.owner = '';
		chart = null;
		view = null;
	}
}
