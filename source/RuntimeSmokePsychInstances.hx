package;

import flixel.FlxG;
import flixel.FlxSprite;

/** Public constructors and placement with temporary native state pointers. */
@:access(PlayState)
@:access(GameOverSubstate)
@:access(flixel.FlxGame)
class RuntimeSmokePsychInstances {
	static function check(ok:Bool,message:String):Void {if(!ok)throw message;}
	public static function verify(state:PlayState):Void {
		var old=state.variables;var oldLegacy=state.nightmareVisionLegacyFieldCameras;
		var oldInstance=PlayState.instance;var oldOver=GameOverSubstate.instance;var active=FlxG.game._state;
		var other=new MusicBeatState();var later=new MusicBeatState();
		var play:PlayState=Type.createEmptyInstance(PlayState);
		@:privateAccess play.members=[state.dad,state.boyfriend];@:privateAccess play.length=2;
		play.gf=state.dad;play.dad=state.dad;play.boyfriend=state.boyfriend;play.isDead=false;play.variables=[];
		var dead:GameOverSubstate=Type.createEmptyInstance(GameOverSubstate);
		@:privateAccess dead.members=[state.boyfriend];@:privateAccess dead.length=1;dead.boyfriend=state.boyfriend;
		var created:Array<FlxSprite>=[];var lua=new LuaCompatInterp();var scope=new SourceNativeClassScope();
		var cleanup=function(){
			FlxG.game._state=active;PlayState.instance=oldInstance;GameOverSubstate.instance=oldOver;
			for(sprite in created){play.remove(sprite,true);dead.remove(sprite,true);other.remove(sprite,true);later.remove(sprite,true);if(sprite.animation!=null)sprite.destroy();}
			state.variables=old;state.nightmareVisionLegacyFieldCameras=oldLegacy;lua.variables.clear();scope.release();other.destroy();later.destroy();
		};
		try {
			state.variables=[];state.nightmareVisionLegacyFieldCameras=false;
			new PsychReflectionBindings(state,lua).install();
			FlxG.game._state=other;PlayState.instance=play;GameOverSubstate.instance=dead;
			lua.execute(new hscript.Parser().parseString('if(!createInstance(" owned.sprite ","flixel.FlxSprite",[11,17]))throw "native creation";if(createInstance("ownedsprite","flixel.FlxSprite",[])||createInstance("missing","missing.SourceConstructor",[]))throw "constructor failures";if(!createInstance("empty","flixel.FlxSprite"))throw "optional arguments";','__instance_create'));
			var sprite:FlxSprite=cast other.variables.get('ownedsprite');var empty:FlxSprite=cast other.variables.get('empty');created.push(sprite);created.push(empty);
			check(sprite.x==11&&sprite.y==17&&empty.x==0&&empty.y==0&&!state.variables.exists('ownedsprite')&&!play.variables.exists('ownedsprite'),'Creation follows active base-state registry');
			lua.execute(new hscript.Parser().parseString('addInstance("ownedsprite");','__instance_back'));
			check(play.members.indexOf(sprite)==0&&sprite.container==play,'Shared lowest-character anchor');play.remove(sprite,true);
			lua.execute(new hscript.Parser().parseString('addInstance("ownedsprite",true);','__instance_front'));
			check(play.members.indexOf(sprite)==play.members.length-1,'Front insertion follows PlayState target');play.remove(sprite,true);play.isDead=true;
			lua.execute(new hscript.Parser().parseString('addInstance("ownedsprite");','__instance_dead_back'));
			check(dead.members.indexOf(sprite)==0&&dead.members.indexOf(state.boyfriend)==1,'Shared game-over anchor');dead.remove(sprite,true);
			lua.execute(new hscript.Parser().parseString('addInstance("ownedsprite",true);addInstance("missing");','__instance_dead_front'));
			check(dead.members.indexOf(sprite)==1,'Game-over front insertion');dead.remove(sprite,true);
			PlayState.instance=null;
			lua.execute(new hscript.Parser().parseString('addInstance("ownedsprite",true);','__instance_menu_front'));
			check(other.members.indexOf(sprite)>=0,'Front insertion supports an active base state');other.remove(sprite,true);PlayState.instance=play;
			scope.construct=function(type,args){var result:Dynamic=Type.createInstance(type,args);FlxG.game._state=later;return result;};
			PsychPropertyBindings.install(state,lua,scope,function(value)return value);
			lua.execute(new hscript.Parser().parseString('if(!createInstance("publishedLater","flixel.FlxSprite",[23,29]))throw "constructor publication";','__instance_publish'));
			var published:FlxSprite=cast later.variables.get('publishedLater');created.push(published);
			check(published!=null&&published.x==23&&!other.variables.exists('publishedLater'),'Publication reselects active registry after native construction');
			scope.construct=function(type,args)return null;
			lua.execute(new hscript.Parser().parseString('if(createInstance("failed","flixel.FlxSprite",[]))throw "null constructor";','__instance_null'));
			check(!later.variables.exists('failed'),'Null constructor does not publish');
			scope.construct=function(type,args){throw 'probe constructor failure';return null;};
			var threw=false;try {Reflect.callMethod(null,lua.variables.get('createInstance'),['throws','flixel.FlxSprite',[]]);}catch(_:Dynamic){threw=true;}
			check(threw&&!later.variables.exists('throws'),'Constructor exceptions propagate without publication');
			@:privateAccess RuntimeSmokeHarness.emit('psych_instance_lifecycle_native_verified',{publicBindings:true,nativeConstruction:true,activeStateRegistry:true,duplicateAndMissing:true,optionalArguments:true,sharedCharacterAnchor:true,frontAndGameOver:true,baseStateFront:true,postConstructorPublication:true,nullFailure:true,exceptionPropagation:true,fullTransition:false});
		} catch(error:Dynamic){cleanup();throw error;}
		cleanup();
	}
}
