package;

/**
	Small script-facing collection for live Nightmare Vision field views.
	`members`, `length`, iteration and `add` cover the source gameplay callers
	that enumerate PlayState.playFields. Native lines remain owned by PlayState;
	this collection does not emulate FlxGroup drawing, updating or full mutation.
*/
@:keep
class NightmareVisionPlayFields {
	@:keep public var members:Array<NightmareVisionPlayFieldView> = [];
	public var length(get, never):Int;

	public function new() {}

	function get_length():Int return members == null ? 0 : members.length;

	@:keep public function add(field:NightmareVisionPlayFieldView):NightmareVisionPlayFieldView {
		if (field != null) members.push(field);
		return field;
	}

	/** Match the source lookup: mutable field IDs take precedence over array order. */
	@:keep public function getFieldFromID(id:Int):NightmareVisionPlayFieldView {
		for (field in members)
			if (field != null && field.ID == id) return field;
		return id >= 0 && id < members.length ? members[id] : null;
	}

	@:keep public function iterator():Iterator<NightmareVisionPlayFieldView>
		return members.iterator();
}
