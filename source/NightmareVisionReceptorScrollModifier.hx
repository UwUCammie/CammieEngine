package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionReceptorScrollModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,?parent:NightmareVisionModifier) { super(mgr,'receptorScroll','receptorScroll',0,false,parent); formulaState.moveSpeed=mgr.formulaContext().crotchet*3; }
}
