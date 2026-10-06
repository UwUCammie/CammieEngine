package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionReverseModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,?parent:NightmareVisionModifier) { super(mgr,'reverse','reverse',-2,true,parent);  }
	public function getReverseValue(data:Int,player:Int,scrolling:Bool=false):Float return modMgr.instanceReverseValue(leafEntry(),data,player,scrolling);
	public function getScrollReversePerc(data:Int,player:Int):Float return getReverseValue(data,player)*100;
}
