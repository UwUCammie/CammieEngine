package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionFlipModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,?parent:NightmareVisionModifier) { super(mgr,'flip','flip',0,false,parent);  }
}
