package;

/** Live source field flags over a native receptor bank. */
@:keep
class NightmareVisionPlayFieldView {
	public final ID:Int;
	public var owner(default, set):Dynamic;
	public var singers:Array<Dynamic> = [];
	public var inControl:Bool = true;
	public var playerControls:Bool;
	public var playAnims:Bool = true;
	public var noteSplashes:Bool = false;
	public var baseAlpha:Float = 1;
	public var holdDropLeniency:Float = 1 / 3;
	public var autoPlayed(get, set):Bool;
	var autoOverride:Null<Bool>;
	final defaultAuto:Void->Bool;
	public function new(id:Int, defaultAuto:Void->Bool) {
		ID = id;
		// Nightmare Vision marks only field 1 as not player-controlled. Additional fields
		// follow the same BF-owned policy as field 0, even when they autoplay.
		playerControls = id != 1;
		this.defaultAuto = defaultAuto;
	}
	function set_owner(value:Dynamic):Dynamic {
		owner = value;
		if (singers == null) singers = [];
		singers.remove(value);
		singers.unshift(value);
		return value;
	}
	function get_autoPlayed():Bool return autoOverride == null ? defaultAuto() : autoOverride;
	function set_autoPlayed(value:Bool):Bool return autoOverride = value;
	public function canInput():Bool {
		var ownerStunned = owner != null && Reflect.field(owner, 'stunned') == true;
		return inControl && playerControls && !autoPlayed && !ownerStunned;
	}
}
