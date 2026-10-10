package;

/** Temporary public callback checks with native live/game-over roots. */
@:access(PlayState)
@:access(GameOverSubstate)
class RuntimeSmokePsychPublicReflection {
	static function check(ok:Bool,message:String):Void {if(!ok)throw message;}
	public static function verify(state:PlayState):Void {
		var old=state.variables;var oldLegacy=state.nightmareVisionLegacyFieldCameras;
		var oldDead=state.isDead;var oldOver=GameOverSubstate.instance;
		var dead:GameOverSubstate=Type.createEmptyInstance(GameOverSubstate);
		@:privateAccess dead.members=[];@:privateAccess dead.length=0;
		var lua=new LuaCompatInterp();
		var cleanup=function(){state.variables=old;state.nightmareVisionLegacyFieldCameras=oldLegacy;state.isDead=oldDead;GameOverSubstate.instance=oldOver;lua.variables.clear();};
		try {
			state.variables=[];state.nightmareVisionLegacyFieldCameras=false;state.isDead=true;GameOverSubstate.instance=dead;
			new PsychReflectionBindings(state,lua).install();
			lua.variables.set('deadMembers',dead.members);lua.variables.set('liveMembers',state.members);
			lua.execute(new hscript.Parser().parseString('if(getProperty("members")!=deadMembers||getProperty("this.members")!=liveMembers)throw "source game-over roots";', '__public_roots'));
			state.isDead=false;
			var bag:Dynamic={value:null,rows:[[1]],sum:function(n:Int)return n+5};
			state.variables.set('bag',bag);state.variables.set('rows',[[2]]);state.variables.set('slot',null);
			state.variables.set('map',new Map<String,Dynamic>());state.variables.set('fn',function(n:Int)return n+8);
			lua.variables.set('expectedRegistry',state.variables);lua.variables.set('expectedHealth',state.health);
			lua.execute(new hscript.Parser().parseString('var marker=instanceArg("health");if(setProperty("slot",marker,false,true)!=marker||getProperty("slot")!=expectedHealth)throw "source setter input return";setProperty("bag.rows[0][0]",99);setProperty("map.key",17,true);if(getProperty("map.key",true)!=17)throw "source map write";if(callMethod(" bag . sum ",[4])!=9||callMethod("fn",[2])!=10)throw "source method path";if(callMethodFromClass("backend.MusicBeatState","getVariables",[])!=expectedRegistry)throw "source static method";if(getPropertyFromClass("missing.SourceProbe","value")!=null||setPropertyFromClass("missing.SourceProbe","value",1)!=null)throw "missing class result";', '__public_properties'));
			check((cast state.variables.get('rows'):Array<Dynamic>)[0][0]==99&&bag.rows[0][0]==1,'Raw bracket write follows variable priority');
			@:privateAccess RuntimeSmokeHarness.emit('psych_public_reflection_native_verified',{publicBindings:true,gameOverRoots:true,originalSetterResult:true,mapWrite:true,rawBracketPriority:true,trimmedMethods:true,directCallable:true,staticMethod:true,missingClassNull:true});
		} catch(error:Dynamic){cleanup();throw error;}
		cleanup();
	}
}
