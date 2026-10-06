package;
import nightmarevision.modchart.NightmareVisionModchartVector;
@:keep
class NightmareVisionPerspectiveModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,?parent:NightmareVisionModifier) { super(mgr,'perspectiveDONTUSE','perspectiveDONTUSE',1100,true,parent); formulaState.halfOffset=NightmareVisionModchartVector.get(mgr.formulaContext().width/2,mgr.formulaContext().height/2); }
	public function getVector(curZ:Float,pos:NightmareVisionModchartVector):NightmareVisionModchartVector return modMgr.instancePerspectiveVector(leafEntry(),curZ,pos);
}
