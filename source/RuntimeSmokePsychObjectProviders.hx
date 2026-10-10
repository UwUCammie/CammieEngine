package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;

/** Public object callbacks retained across temporary native registry/scene changes. */
@:access(PlayState)
@:access(GameOverSubstate)
@:access(flixel.FlxGame)
class RuntimeSmokePsychObjectProviders {
	static function check(ok:Bool,message:String):Void {if(!ok)throw message;}
	public static function verify(state:PlayState):Void {
		var oldVars=state.variables;var oldLegacy=state.nightmareVisionLegacyFieldCameras;
		var active=FlxG.game._state;var oldPlay=PlayState.instance;var oldOver=GameOverSubstate.instance;
		var oldCustom=state.compatCustomSubstate;var oldPublished=PsychCustomSubstate.instance;
		var other=new MusicBeatState();var next=new MusicBeatState();
		var play:PlayState=Type.createEmptyInstance(PlayState);
		@:privateAccess play.members=[state.dad,state.boyfriend];@:privateAccess play.length=2;
		play.gf=state.dad;play.dad=state.dad;play.boyfriend=state.boyfriend;play.variables=[];play.camHUD=state.camGame;play.isDead=false;
		var dead:GameOverSubstate=Type.createEmptyInstance(GameOverSubstate);
		@:privateAccess dead.members=[];@:privateAccess dead.length=0;
		var custom=new PsychCustomSubstate(null,'published-probe',false);var queued=new PsychCustomSubstate(null,'queued-probe',false);
		var lua=new LuaCompatInterp();var created:Array<FlxSprite>=[];var armed=false;
		var cleanup=function(){
			armed=false;
			for(sprite in created){play.remove(sprite,true);dead.remove(sprite,true);custom.remove(sprite,true);other.remove(sprite,true);next.remove(sprite,true);if(sprite.animation!=null)sprite.destroy();}
			custom.destroy();queued.cancelBeforeCreate();other.destroy();next.destroy();lua.variables.clear();
			FlxG.game._state=active;PlayState.instance=oldPlay;GameOverSubstate.instance=oldOver;state.variables=oldVars;
			state.nightmareVisionLegacyFieldCameras=oldLegacy;state.compatCustomSubstate=oldCustom;PsychCustomSubstate.instance=oldPublished;
		};
		try {
			state.variables=[];state.nightmareVisionLegacyFieldCameras=false;new PsychSourceBindings(state).install(lua);
			FlxG.game._state=other;PlayState.instance=play;GameOverSubstate.instance=dead;state.compatCustomSubstate=queued;
			custom.create();check(PsychCustomSubstate.instance==custom,'Published custom substate differs from queued owner substate');
			lua.execute(new hscript.Parser().parseString('makeLuaSprite("sprite");makeAnimatedLuaSprite("animated");makeFlxAnimateSprite("animate");makeLuaText("text","active text",120);if(!luaSpriteExists("sprite")||!luaSpriteExists("animated")||!luaSpriteExists("animate")||!luaTextExists("text"))throw "live object existence";','__live_objects'));
			for(name in ['sprite','animated','animate','text']) {var object:FlxSprite=cast other.variables.get(name);created.push(object);check(object!=null&&!state.variables.exists(name)&&!play.variables.exists(name),'Live active registry for '+name);}
			var sprite=created[0];var label:FlxText=cast created[3];
			check(label.cameras[0]==state.camGame,'Text camera comes from current PlayState');
			var alternate=new FlxText(0,0,100,'global rows');created.push(alternate);
			other.variables.set('bag',{label:label,rows:[label]});other.variables.set('rows',[alternate]);
			lua.execute(new hscript.Parser().parseString('if(getTextString("bag.rows[0]")!="global rows")throw "raw text bracket lookup";if(!setTextString("bag.label","changed")||getTextString("text")!="changed")throw "live nested text lookup";addLuaSprite("sprite",true);','__live_lookup'));
			check(sprite.container==play,'Sprite mount follows current gameplay state');
			play.isDead=true;
			lua.execute(new hscript.Parser().parseString('addLuaText("text");','__live_text_add'));
			check(label.container==dead&&custom.members.indexOf(label)<0,'Text add follows game-over even with published custom state');
			dead.remove(label,true);custom.add(label);
			lua.execute(new hscript.Parser().parseString('removeLuaText("text",false);','__live_custom_retain'));
			check(label.container==null&&other.variables.get('text')==label&&label.textField!=null,'Published custom target supports retained removal');
			custom.add(label);armed=true;
			custom.memberRemoved.add(function(item){if(armed&&item==label){FlxG.game._state=next;next.variables.set('text',label);}});
			lua.execute(new hscript.Parser().parseString('removeLuaText("text",true);','__live_text_remove'));
			check(!other.variables.exists('text')&&next.variables.get('text')==label&&label.textField==null,'Text removal clears the captured registry after scene reentry');
			FlxG.game._state=other;play.isDead=false;
			play.memberRemoved.add(function(item){if(armed&&item==sprite){FlxG.game._state=next;next.variables.set('sprite',sprite);}});
			lua.execute(new hscript.Parser().parseString('removeLuaSprite("sprite",true);','__live_sprite_remove'));
			check(other.variables.get('sprite')==sprite&&!next.variables.exists('sprite')&&sprite.animation==null,'Sprite removal clears the live registry after scene reentry');
			armed=false;FlxG.game._state=other;PlayState.instance=null;
			lua.execute(new hscript.Parser().parseString('makeLuaText("base","base state",100);addLuaText("base");','__base_text'));
			var base:FlxText=cast other.variables.get('base');created.push(base);
			check(base.container==other,'No-PlayState text add follows active base state');
			@:privateAccess check(base._cameras==null,'No-PlayState text keeps default cameras');
			@:privateAccess RuntimeSmokeHarness.emit('psych_object_providers_native_verified',{publicBindings:true,liveRegistry:true,typeExistence:true,nestedTextLookup:true,rawBracketPriority:true,currentHudCamera:true,gameOverAdd:true,publishedCustomRemoval:true,capturedTextRegistry:true,liveSpriteRegistry:true,baseStateText:true,fullTransition:false});
		} catch(error:Dynamic){cleanup();throw error;}
		cleanup();
	}
}
