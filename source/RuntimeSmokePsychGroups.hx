package;

import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.text.FlxText;

/** Native group callbacks with disposable members and restored scene roots. */
@:access(PlayState)
@:access(GameOverSubstate)
class RuntimeSmokePsychGroups {
	static function check(ok:Bool,message:String):Void {if(!ok)throw message;}
	public static function verify(state:PlayState):Void {
		var old=state.variables;var oldLegacy=state.nightmareVisionLegacyFieldCameras;
		var oldDead=state.isDead;var oldOver=GameOverSubstate.instance;var oldGroup=state.strumLineNotes;
		var dead:GameOverSubstate=Type.createEmptyInstance(GameOverSubstate);
		@:privateAccess dead.members=[];@:privateAccess dead.length=0;
		var group=new FlxTypedGroup<FlxSprite>();
		var arrayItem=new FlxText(1,0,10,'a');var absent=new FlxText(2,0,10,'b');
		var groupItem=new FlxText(3,0,10,'c');var indexed=new FlxText(4,0,10,'d');
		var lua=new LuaCompatInterp();
		var cleanup=function(){state.variables=old;state.nightmareVisionLegacyFieldCameras=oldLegacy;state.isDead=oldDead;GameOverSubstate.instance=oldOver;state.strumLineNotes=oldGroup;lua.variables.clear();group.clear();group.destroy();for(item in [arrayItem,absent,groupItem,indexed])if(item.textField!=null)item.destroy();};
		try {
			state.variables=[];state.nightmareVisionLegacyFieldCameras=false;state.isDead=true;GameOverSubstate.instance=dead;state.strumLineNotes=group;
			state.variables.set('arrayItem',arrayItem);state.variables.set('absent',absent);state.variables.set('groupItem',groupItem);state.variables.set('indexed',indexed);
			new PsychReflectionBindings(state,lua).install();
			lua.variables.set('expectedHealth',state.health);
			lua.execute(new hscript.Parser().parseString('addToGroup("members","arrayItem");addToGroup("members","arrayItem");if(getPropertyFromGroup("members",0,"x")!=1)throw "array field";var marker=instanceArg("health");if(setPropertyFromGroup("members",0,"x",marker,false,true)!=marker||getPropertyFromGroup("members",0,"x")!=expectedHealth)throw "array parsed setter";removeFromGroup("members",0,null,true);','__group_array'));
			check(dead.members.length==1&&dead.members[0]==arrayItem&&arrayItem.textField!=null,'Indexed array removal preserves lifetime and duplicate');
			lua.execute(new hscript.Parser().parseString('removeFromGroup("members",-1,"arrayItem",true);removeFromGroup("members",-1,"absent",true);','__group_array_destroy'));
			check(dead.members.length==0&&arrayItem.textField==null&&absent.textField==null,'Tagged array removal destroys present and absent objects');
			state.isDead=false;
			lua.execute(new hscript.Parser().parseString('addToGroup("strumLineNotes","groupItem",0);if(getPropertyFromGroup("strumLineNotes",0,"x")!=3)throw "native group field";setPropertyFromGroup("strumLineNotes",0,"x",12);removeFromGroup("strumLineNotes",0,null,false);','__group_native'));
			check(group.length==0&&groupItem.x==12&&groupItem.textField!=null,'Native group setter and retained removal');
			lua.execute(new hscript.Parser().parseString('removeFromGroup("strumLineNotes",-1,"groupItem",true);addToGroup("strumLineNotes","indexed");','__group_absent'));
			check(groupItem.textField==null,'Native absent tagged removal still destroys');
			var removedBeforeDestroy=false;
			group.memberRemoved.add(function(item){if(item==indexed){removedBeforeDestroy=indexed.textField!=null;state.variables=[];}});
			lua.execute(new hscript.Parser().parseString('removeFromGroup("strumLineNotes",0,null,true);','__group_reentry'));
			check(group.length==0&&indexed.textField==null&&removedBeforeDestroy,'Removal listener precedes destruction and cannot redirect the captured member');
			@:privateAccess RuntimeSmokeHarness.emit('psych_group_reflection_native_verified',{publicBindings:true,gameOverArray:true,originalSetterResult:true,indexedArrayLifetime:true,taggedAbsentDestruction:true,nativeGroup:true,removalBeforeDestroy:true,registryReentry:true});
		} catch(error:Dynamic){cleanup();throw error;}
		cleanup();
	}
}
