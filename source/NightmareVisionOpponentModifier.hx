package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionOpponentModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,?parent:NightmareVisionModifier) { super(mgr,'opponentSwap','opponentSwap',0,false,parent);  }
}
