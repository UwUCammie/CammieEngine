package;
import nightmarevision.modchart.NightmareVisionModchartVector;
import nightmarevision.modchart.NightmareVisionModchartTransform;
@:keep
class NightmareVisionPathModifier extends NightmareVisionBuiltinModifier {
	public function new(mgr:NightmareVisionModManager,prefix:String='basePath',?parent:NightmareVisionModifier) {
		super(mgr,'path',prefix,0,false,parent,prefix);
		formulaState.moveSpeed=getMoveSpeed();tracePath(getPath());
	}
	public override function getSubmods():Array<String> return [getName()+'visual',getName()+'speed'];
	public override function refreshFormulaState():Void formulaState.prefix=getName();
	public function getMoveSpeed():Float return 5000;
	public function getPath():Array<Array<NightmareVisionModchartVector>> return [];
	public function tracePath(path:Array<Array<NightmareVisionModchartVector>>):Void NightmareVisionModchartTransform.tracePath(formulaState,path);
}
