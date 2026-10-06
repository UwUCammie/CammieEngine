// @author Nebula_Zorua
package;

@:keep
class NightmareVisionSetEvent extends NightmareVisionModEvent
{
	override function run(curStep:Float)
	{
		// mod.setValue(endVal, player);
		manager.setValue(modName, endVal, player);
		finished = true;
	}
}
