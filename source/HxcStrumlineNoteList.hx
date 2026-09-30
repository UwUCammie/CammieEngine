package;

/** Live HXC `.members` and iterator view for the selected native strumline. */
class HxcStrumlineNoteList {
	var line:Strumline;
	var holds:Bool;
	public var members(get, never):Array<Dynamic>;
	function get_members():Array<Dynamic> {
		var state = PlayState.instance;
		return state == null ? [] : state.hxcStrumlineMembers(line, holds);
	}
	public function iterator():Iterator<Dynamic> return members.iterator();
	public function new(line:Strumline, holds:Bool) {
		this.line = line;
		this.holds = holds;
	}
}
