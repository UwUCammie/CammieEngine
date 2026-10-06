package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionLocalRotateModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,prefix:String='',?parent:NightmareVisionModifier) { super(mgr,'localrotateX',prefix+'rotateX',-1,false,parent,prefix); }
}
