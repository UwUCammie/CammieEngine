package;
import nightmarevision.modchart.NightmareVisionModchartVector;
import nightmarevision.modchart.NightmareVisionModchartMath;
@:keep
class NightmareVisionInfinitePathModifier extends NightmareVisionPathModifier {
	public function new(mgr:NightmareVisionModManager,prefix:String='infinite',?parent:NightmareVisionModifier) super(mgr,prefix,parent);
	public override function getMoveSpeed():Float return 1850;
	public override function getPath():Array<Array<NightmareVisionModchartVector>> {
		var c=modMgr.formulaContext();var path:Array<NightmareVisionModchartVector>=[];
		var step=c.lowQuality?15:3;var r=0;
		while(r<360) {
			var rad=r*Math.PI/180;
			path.push(NightmareVisionModchartVector.get(c.width*.5+NightmareVisionModchartMath.fastSin(rad)*600,
				c.height*.5+NightmareVisionModchartMath.fastSin(rad)*NightmareVisionModchartMath.fastCos(rad)*600,0));r+=step;
		}
		return [path];
	}
}
