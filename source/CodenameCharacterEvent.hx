package;

/** Mutable donor character event fields; each dispatch gets its own payload. */
@:keep
class CodenameCharacterEvent extends CodenameGameEvent {
	public var character:Character;
	public var xml:CodenameXmlAccess;
	public var node:CodenameXmlAccess;
	public var name:String;
	public var danced:Bool;
	public var animName:String;
	public var force:Null<Bool>;
	public var reverse:Bool;
	public var startingFrame:Int = 0;
	public var context:Dynamic;
	public var x:Float;
	public var y:Float;
	public function new() super();
}
