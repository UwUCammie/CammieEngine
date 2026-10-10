package;

import flixel.FlxSprite;
import flixel.text.FlxText;
import openfl.display.BitmapData;

/** Disposable public-callback checks for cross-kind registry replacement. */
@:access(PlayState)
@:access(GameOverSubstate)
class RuntimeSmokePsychSpriteLifecycle {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState):Void {
		var oldVars = state.psychScriptVariables;var oldLegacy = state.nightmareVisionLegacyFieldCameras;
		var oldDead = state.isDead;var oldOver = GameOverSubstate.instance;var oldCustom = state.compatCustomSubstate;
		var dead:GameOverSubstate = Type.createEmptyInstance(GameOverSubstate);
		@:privateAccess dead.members = [state.boyfriend];@:privateAccess dead.length = 1;
		dead.boyfriend = state.boyfriend;
		var created:Array<FlxSprite> = [];var lua = new LuaCompatInterp();
		var cleanup = function() {
			for (sprite in created) {dead.remove(sprite,true);if(sprite.animation!=null)sprite.destroy();}
			state.psychScriptVariables=oldVars;state.nightmareVisionLegacyFieldCameras=oldLegacy;state.isDead=oldDead;
			GameOverSubstate.instance=oldOver;state.compatCustomSubstate=oldCustom;lua.variables.clear();
		};
		try {
			state.psychScriptVariables=[];state.nightmareVisionLegacyFieldCameras=false;state.isDead=true;
			GameOverSubstate.instance=dead;state.compatCustomSubstate=null;
			new PsychSourceBindings(state).install(lua);
			lua.variables.set('playAnim', state.compatPlayAnim);
			lua.execute(new hscript.Parser().parseString('if(makeLuaSprite("__cross.kind",null,12,34)!=null)throw "sprite constructor result";if(!luaSpriteExists("__crosskind")||luaTextExists("__crosskind"))throw "sprite type existence";addLuaSprite("__crosskind",false);', '__psych_sprite_create'));
			var sprite:PsychModchartSprite=cast state.psychScriptVariables.get('__crosskind');created.push(sprite);
			check(sprite.x==12&&sprite.y==34&&sprite.active&&!state.haxeSprites.exists('__crosskind')&&dead.members.indexOf(sprite)<dead.members.indexOf(state.boyfriend), 'Shared variable sprite and game-over insertion');
			sprite.sourceAtlasNames=['old'];sprite.loadGraphic(new BitmapData(3,1,false,0xffffffff),true,1,1);
			check(sprite.sourceAtlasNames==null,'Frame replacement invalidates source atlas metadata');sprite.animation.add('probe',[0,1,2],24,false);
			lua.execute(new hscript.Parser().parseString('addOffset("__crosskind","probe",7,9);playAnim("__crosskind","probe",true,false,1);makeLuaText("__cross.kind","replacement",100);if(luaSpriteExists("__crosskind")||!luaTextExists("__crosskind"))throw "text type existence";', '__psych_sprite_to_text'));
			check(sprite.animation==null, 'Sprite disposed by text creation');
			var text:FlxText=cast state.psychScriptVariables.get('__crosskind');created.push(text);
			lua.execute(new hscript.Parser().parseString('addLuaText("__crosskind");makeFlxAnimateSprite("__cross.kind",5,6);if(!luaSpriteExists("__crosskind")||luaTextExists("__crosskind"))throw "Animate type existence";', '__psych_text_to_animate'));
			var animate:PsychModchartAnimateSprite=cast state.psychScriptVariables.get('__crosskind');created.push(animate);
			check(!text.exists&&text.animation==null&&animate.x==5&&animate.y==6&&animate.active, 'Animate replacement kills then destroys prior text');
			lua.execute(new hscript.Parser().parseString('makeAnimatedLuaSprite("__cross.kind");addLuaSprite("__crosskind",true);removeLuaSprite("__crosskind",false);', '__psych_animate_to_sprite'));
			var animated:PsychModchartSprite=cast state.psychScriptVariables.get('__crosskind');created.push(animated);
			check(animate.animation==null&&animated.exists&&animated.container==null, 'Animated sprite replaces Animate; retained removal keeps live object');
			animated.loadGraphic(new BitmapData(3,1,false,0xffffffff),true,1,1);animated.animation.add('probe',[0,1,2],24,false);
			lua.execute(new hscript.Parser().parseString('addOffset("__crosskind","probe",7,9);playAnim("__crosskind","probe",true,false,1);', '__psych_sprite_offsets'));
			check(animated.offset.x==7&&animated.offset.y==9&&animated.animation.curAnim.curFrame==1, 'Native ModchartSprite offset and frame dispatch');
			lua.execute(new hscript.Parser().parseString('addLuaSprite("__crosskind",true);removeObject("__crosskind");if(luaSpriteExists("__crosskind"))throw "removed sprite registry";', '__psych_sprite_remove'));
			check(animated.animation==null&&!state.psychScriptVariables.exists('__crosskind'), 'Generic sprite removal clears the shared tag');
			@:privateAccess RuntimeSmokeHarness.emit('psych_sprite_lifecycle_native_verified',{sharedRegistry:true,crossKindReplacement:true,sourceTypes:true,gameOverInsertion:true,retainedTags:true,animationOffsets:true,frameMetadataInvalidation:true,publicBindings:true,genericRemoval:true});
		} catch(error:Dynamic){cleanup();throw error;}
		cleanup();
	}
}
