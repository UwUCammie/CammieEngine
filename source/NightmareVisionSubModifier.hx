package;
@:keep
class NightmareVisionSubModifier extends NightmareVisionModifier {
	public var name:String;
	public function new(name:String, mgr:NightmareVisionModManager, ?parent:NightmareVisionModifier) { super(mgr, parent); this.name = name; }
	public override function getName():String return name;
	public override function getOrder():Int return 1000;
	public override function doesUpdate():Bool return false;
}
