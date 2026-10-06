package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionTransformModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,?parent:NightmareVisionModifier) { super(mgr,'transformX','transformX',1000,false,parent);  }
}
