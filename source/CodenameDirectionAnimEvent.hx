package;

/** Mutable source directional animation event, before suffix fallback. */
@:keep
class CodenameDirectionAnimEvent extends CodenameGameEvent {
	public var animName:String;
	public var direction:Int;
	public var suffix:String;
	public var context:Dynamic;
	public var reversed:Bool;
	public var frame:Int;
	public var force:Null<Bool>;
	public function new(animName:String, direction:Int, suffix:String, context:Dynamic,
		reversed:Bool, frame:Int, force:Null<Bool>) {
		super();
		recycle(animName, direction, suffix, context, reversed, frame, force);
	}
	public function recycle(animName:String, direction:Int, suffix:String, context:Dynamic,
		reversed:Bool, frame:Int, force:Null<Bool>):CodenameDirectionAnimEvent {
		recycleBase();
		this.animName = animName;
		this.direction = direction;
		this.suffix = suffix;
		this.context = context;
		this.reversed = reversed;
		this.frame = frame;
		this.force = force;
		return this;
	}
}
