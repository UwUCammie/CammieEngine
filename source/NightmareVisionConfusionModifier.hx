package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionConfusionModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,?parent:NightmareVisionModifier) { super(mgr,'confusion','confusion',0,true,parent);  }
}
