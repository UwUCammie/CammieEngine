package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionInvertModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,?parent:NightmareVisionModifier) { super(mgr,'invert','invert',0,false,parent);  }
}
