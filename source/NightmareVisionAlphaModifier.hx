package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionAlphaModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,?parent:NightmareVisionModifier) { super(mgr,'stealth','stealth',0,true,parent);  }
	public static var fadeDistY:Float=120;
	public override function refreshFormulaState():Void formulaState.fadeDistY=fadeDistY;
	public function getHiddenSudden(player:Int=-1):Float return modMgr.alphaBoundary(leafEntry(),'hiddenSudden',player);
	public function getHiddenEnd(player:Int=-1):Float return modMgr.alphaBoundary(leafEntry(),'hiddenEnd',player);
	public function getHiddenStart(player:Int=-1):Float return modMgr.alphaBoundary(leafEntry(),'hiddenStart',player);
	public function getSuddenEnd(player:Int=-1):Float return modMgr.alphaBoundary(leafEntry(),'suddenEnd',player);
	public function getSuddenStart(player:Int=-1):Float return modMgr.alphaBoundary(leafEntry(),'suddenStart',player);
}
