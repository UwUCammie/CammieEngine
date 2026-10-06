// @author Nebula_Zorua
package;

@:keep
class NightmareVisionModEvent extends NightmareVisionBaseEvent
{
	public var modName:String = '';
	public var endVal:Float = 0;
	public var player:Int = -1;

	private var mod:NightmareVisionModifier;

	public function new(step:Float, modName:String, target:Float, player:Int = -1, modMgr:NightmareVisionModManager)
	{
		super(step, modMgr);
		this.modName = modName;
		this.player = player;
		endVal = target;

		this.mod = modMgr.get(modName);
	}
}
