package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionBeatModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,?parent:NightmareVisionModifier) { super(mgr,'beat','beat',0,false,parent);  }
}
