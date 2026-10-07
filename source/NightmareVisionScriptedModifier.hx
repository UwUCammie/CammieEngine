package;
import NightmareVisionModifier.ModifierType;
import nightmarevision.modchart.NightmareVisionModchartVector;
/** Owner-local modifier interpreter, distinct from the gameplay callback group. */
@:keep
class NightmareVisionScriptedModifier extends NightmareVisionModifier {
	public var name:String;
	public var prefix:String;
	public var script(default,null):NightmareVisionScriptModule;
	var modName:String;
	var modType:ModifierType = MISC_MOD;
	var modOrder:Int = 0;
	var modUpdate:Bool = false;
	var released:Bool = false;
	public function new(mgr:NightmareVisionModManager, name:String = '', prefix:String = '', ?parent:NightmareVisionModifier) {
		this.name=name; this.prefix=prefix; modName=name.toLowerCase();
		mgr.ownScript(this);
		if (mgr.loadModifierScript != null) script=mgr.loadModifierScript(this,name);
		if (script == null) mgr.diagnostic(name,'load','Modifier script could not be loaded');
		else {
			var value=script.callValue('getName',null,this); if(value!=null) modName=cast value;
			value=script.callValue('getModType',null,this); if(value!=null) modType=cast value;
			value=script.callValue('getOrder',null,this); if(value!=null) modOrder=cast value;
			value=script.callValue('doesUpdate',null,this); modUpdate=value==null ? modType==MISC_MOD : cast value;
		}
		super(mgr,parent);
		if(script!=null) script.callValue('onLoad',[mgr,name,prefix,parent],this);
	}
	public override function getName():String return modName;
	public override function getModType():ModifierType return modType;
	public override function getOrder():Int return modOrder;
	public override function doesUpdate():Bool return modUpdate;
	public override function getSubmods():Array<String> {
		var result=script==null?null:script.callValue('getSubmods',null,this);
		return result==null?[]:cast result;
	}
	public override function getPos(time:Float,diff:Float,tDiff:Float,beat:Float,pos:NightmareVisionModchartVector,data:Int,player:Int,obj:Dynamic):NightmareVisionModchartVector {
		var result=script==null?null:script.callValue('getPos',[time,diff,tDiff,beat,pos,data,player,obj],this);
		return result==null?pos:cast result;
	}
	public override function update(elapsed:Float):Void { if(script!=null) script.callValue('onUpdate',[elapsed],this); }
	public override function updateNote(beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int):Void { if(script!=null) script.callValue('updateNote',[beat,obj,pos,player],this); }
	public override function updateReceptor(beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int):Void { if(script!=null) script.callValue('updateReceptor',[beat,obj,pos,player],this); }
	public override function updateNoteSplash(beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int):Void { if(script!=null) script.callValue('updateNoteSplash',[beat,obj,pos,player],this); }
	public override function updateSustainSplash(beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int):Void { if(script!=null) script.callValue('updateSustainSplash',[beat,obj,pos,player],this); }
	public override function destroy():Void {
		if(released) return; released=true;
		var owned=script;
		if(owned!=null) { owned.callValue('destroy',null,this); script=null; owned.destroy(); }
		super.destroy();
	}
}
