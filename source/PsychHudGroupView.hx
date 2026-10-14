package;

/**
	Psych gathers its HUD (health bar, icons, score, time bar, botplay text)
	in one sprite group, `uiGroup`, and scripts fade or hide the whole HUD
	through it. The engine keeps those objects as separate members of the
	state, so this view forwards the group-wide writes to whatever HUD objects
	exist right now instead of re-parenting them, which would change their draw
	order for every song.
*/
class PsychHudGroupView {
	var provider:Void->Array<Dynamic>;
	var groupAlpha:Float = 1;
	var groupVisible:Bool = true;

	public function new(provider:Void->Array<Dynamic>) {
		this.provider = provider;
	}

	/** The HUD objects as they are now; adding to this list changes nothing. */
	public var members(get, never):Array<Dynamic>;
	function get_members():Array<Dynamic> {
		var found:Array<Dynamic> = [];
		var listed = provider == null ? null : provider();
		if (listed != null)
			for (member in listed)
				if (member != null && found.indexOf(member) == -1)
					found.push(member);
		return found;
	}

	public var length(get, never):Int;
	function get_length():Int return members.length;

	/**
		Same rule as a sprite group: each member keeps its own alpha relative to
		the group, so a script that sets 0.0001 and later 1 gets every member
		back where it was. From zero there is nothing to scale, so the value is
		written straight through.
	*/
	public var alpha(get, set):Float;
	function get_alpha():Float return groupAlpha;
	function set_alpha(value:Float):Float {
		if (value < 0) value = 0;
		if (value > 1) value = 1;
		var factor = groupAlpha > 0 ? value / groupAlpha : 0.0;
		for (member in members) {
			try {
				var own:Dynamic = Reflect.getProperty(member, 'alpha');
				if (own == null) continue;
				Reflect.setProperty(member, 'alpha', groupAlpha > 0 ? (own : Float) * factor : value);
			} catch (_:Dynamic) {}
		}
		return groupAlpha = value;
	}

	public var visible(get, set):Bool;
	function get_visible():Bool return groupVisible;
	function set_visible(value:Bool):Bool {
		for (member in members)
			try Reflect.setProperty(member, 'visible', value) catch (_:Dynamic) {}
		return groupVisible = value;
	}

	public function forEach(callback:Dynamic->Void):Void {
		if (callback != null)
			for (member in members)
				callback(member);
	}

	public function indexOf(member:Dynamic):Int return members.indexOf(member);
}
