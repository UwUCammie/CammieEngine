package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionRotateModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,prefix:String='',?origin:NightmareVisionModchartVector,?parent:NightmareVisionModifier) { super(mgr,'rotateX',prefix+'rotateX',1002,false,parent,prefix);formulaState.origin=origin; }
	public var daOrigin(get,set):NightmareVisionModchartVector;
	function get_daOrigin():NightmareVisionModchartVector return formulaState.origin;
	function set_daOrigin(value:NightmareVisionModchartVector):NightmareVisionModchartVector return formulaState.origin=value;
}
