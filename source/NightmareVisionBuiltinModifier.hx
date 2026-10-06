package;
import nightmarevision.modchart.NightmareVisionModchartVector;
import nightmarevision.modchart.NightmareVisionModifierFormulaState;
import nightmarevision.modchart.NightmareVisionModifierRegistry.NightmareVisionModifierExecution;
/** Actual source instance methods delegate one shared leaf, never a full manager pass. */
@:keep
class NightmareVisionBuiltinModifier extends NightmareVisionNoteModifier {
	public final formulaKind:String;
	public final formulaState:NightmareVisionModifierFormulaState;
	final name:String;
	final order:Int;
	final always:Bool;
	var entry:NightmareVisionModifierExecution;
	public function new(mgr:NightmareVisionModManager,kind:String,name:String,order:Int=0,always:Bool=false,?parent:NightmareVisionModifier,prefix:String='') {
		formulaKind=kind;this.name=name;this.order=order;this.always=always;
		formulaState=new NightmareVisionModifierFormulaState();formulaState.prefix=prefix;
		super(mgr,parent);
		formulaState.receptorCount=function(player) return mgr.receptors[player].length;
		formulaState.reverseValue=function(data,player,scrolling) {
			var reverse:Dynamic=mgr.register.get('reverse');return reverse.getReverseValue(data,player,scrolling);
		};
	}
	public override function getName():String return name;
	public override function getOrder():Int return order;
	public override function shouldExecute(player:Int,value:Float):Bool return always||value!=0;
	public override function getSubmods():Array<String> return NightmareVisionBuiltinCatalog.submods(formulaKind,modMgr.sourceKeyCount(),formulaState.prefix);
	public function refreshFormulaState():Void {}
	public function leafEntry():NightmareVisionModifierExecution {
		refreshFormulaState();
		if(entry==null) entry={builtin:formulaKind,state:formulaState,value:getValue,subValue:getSubmodValue,getPosition:getPos,updateObject:dispatchObject};
		return entry;
	}
	public override function getPos(time:Float,diff:Float,tDiff:Float,beat:Float,pos:NightmareVisionModchartVector,data:Int,player:Int,obj:Dynamic):NightmareVisionModchartVector {
		if(!NightmareVisionBuiltinCatalog.hasPosition(formulaKind)) return pos;
		return modMgr.instancePosition(leafEntry(),obj,pos,time,diff,tDiff,beat,data,player);
	}
	function applyObject(kind:String,beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int):Void {
		if(NightmareVisionBuiltinCatalog.hasObject(formulaKind,kind)) modMgr.instanceObject(leafEntry(),obj,kind,pos,beat,player);
	}
	function dispatchObject(beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int,kind:String):Void {
		switch(kind) {
			case 'note':updateNote(beat,obj,pos,player);
			case 'receptor':updateReceptor(beat,obj,pos,player);
			case 'noteSplash':updateNoteSplash(beat,obj,pos,player);
			case 'sustainSplash':updateSustainSplash(beat,obj,pos,player);
		}
	}
	public override function updateNote(beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int):Void applyObject('note',beat,obj,pos,player);
	public override function updateReceptor(beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int):Void applyObject('receptor',beat,obj,pos,player);
	public override function updateNoteSplash(beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int):Void applyObject('noteSplash',beat,obj,pos,player);
	public override function updateSustainSplash(beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int):Void applyObject('sustainSplash',beat,obj,pos,player);
}
