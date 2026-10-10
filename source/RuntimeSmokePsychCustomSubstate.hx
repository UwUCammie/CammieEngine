package;

import flixel.FlxG;
import flixel.FlxSprite;

/** Isolated native source-class construction, publication and public insertion. */
@:access(PlayState)
@:access(flixel.FlxGame)
class RuntimeSmokePsychCustomSubstate {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState):Void {
		var oldVars=state.variables;var oldScripts=state.hscriptStates;var oldLegacy=state.nightmareVisionLegacyFieldCameras;
		var oldName=PsychCustomSubstate.name;var oldSub=PsychCustomSubstate.instance;var oldPlay=PlayState.instance;
		var active=FlxG.game._state;var other=new MusicBeatState();var sprite=new FlxSprite();
		var iris=new SourceIrisBridge(state);var lua=new LuaCompatInterp();var sub:PsychCustomSubstate=null;
		var cleanup=function(){
			PlayState.instance=state;
			if(sub!=null){sub.remove(sprite,true);sub.destroy();sub=null;}
			sprite.destroy();other.destroy();iris.release();lua.variables.clear();
			state.variables=oldVars;state.hscriptStates=oldScripts;state.nightmareVisionLegacyFieldCameras=oldLegacy;
			PsychCustomSubstate.name=oldName;PsychCustomSubstate.instance=oldSub;PlayState.instance=oldPlay;FlxG.game._state=active;
		};
		try {
			state.variables=[];state.hscriptStates=[];state.nightmareVisionLegacyFieldCameras=false;PlayState.instance=state;
			PsychCustomSubstate.instance=null;PsychCustomSubstate.name='unnamed';
			new PsychSourceBindings(state).install(lua);new PsychReflectionBindings(state,lua).install();
			new PsychHscriptSourceBindings(state,iris,'__custom_substate_probe',null).install();
			check(iris.variables.get('CustomSubstate')==PsychCustomSubstate,'Preset exposes native source class');
			var events:Array<String>=[];iris.variables.set('events',events);lua.variables.set('events',events);
			iris.variables.set('__psychScoreGlobals',true);lua.variables.set('__psychScoreGlobals',true);
			state.hscriptStates.set('__custom_probe_hscript',iris);state.hscriptStates.set('__custom_probe_lua',lua);
			lua.execute(new hscript.Parser().parseString('function onCustomSubstateCreate(n){events.push("lua:create:"+n);return null;} function onCustomSubstateDestroy(n){events.push("lua:destroy:"+n);return null;}', '__custom_substate_callbacks'));
			iris.evaluate('function onCustomSubstateCreate(n){if(customSubstate!=CustomSubstate.instance||customSubstateName!=n)throw "published HScript globals";events.push("hscript:create:"+n);} function onCustomSubstateDestroy(n){if(CustomSubstate.instance==null)throw "early instance clearing";events.push("hscript:destroy:"+n);}', '__custom_substate_callbacks');
			iris.variables.set('created',null);
			iris.evaluate('import psychlua.CustomSubstate; created=new CustomSubstate("native-probe"); if(CustomSubstate.instance!=null||CustomSubstate.name!="native-probe")throw "constructor publication";', '__custom_substate_ctor');
			sub=cast iris.variables.get('created');check(sub!=null&&sub.sourceLifecycle,'Native class construction');
			lua.execute(new hscript.Parser().parseString('if(closeCustomSubstate())throw "unpublished close";', '__custom_substate_queued'));
			sub.create();check(PsychCustomSubstate.instance==sub,'Native instance publication');
			FlxG.game._state=other;other.variables.set('object',sprite);
			lua.execute(new hscript.Parser().parseString('if(!insertToCustomSubstate("object")||insertToCustomSubstate("missing"))throw "active registry insertion";setPropertyFromClass("psychlua.CustomSubstate","name","changed");', '__custom_substate_insert'));
			check(sprite.container==sub&&PsychCustomSubstate.name=='changed','Shared Lua class statics and native insertion');
			sub.remove(sprite,true);iris.variables.set('sprite',sprite);
			iris.evaluate('if(!CustomSubstate.insertToCustomSubstate("object",0)||CustomSubstate.instance.members[0]!=sprite)throw "shared HScript insertion";', '__custom_substate_hscript');
			sub.update(0);sub.remove(sprite,true);sub.destroy();sub=null;
			check(PsychCustomSubstate.instance==null&&PsychCustomSubstate.name=='unnamed','Destroy clears shared publication');
			check(events.join('|')=='lua:create:native-probe|hscript:create:native-probe|lua:destroy:changed|hscript:destroy:changed','Native Lua-before-HScript lifecycle dispatch: '+events.join('|'));
			check(iris.variables.get('customSubstate')==null&&iris.variables.get('customSubstateName')=='unnamed'&&!lua.variables.exists('customSubstateName'),'HScript-only lifecycle globals');
			@:privateAccess RuntimeSmokeHarness.emit('psych_custom_substate_native_verified',{nativeConstructor:true,callbackOrder:true,hscriptOnlyGlobals:true,sourceClass:true,luaHscriptShared:true,liveRegistry:true,mutableName:true,publication:true,unpublishedClose:true,destruction:true,fullTransition:false});
		} catch(error:Dynamic){cleanup();throw error;}
		cleanup();
	}
}
