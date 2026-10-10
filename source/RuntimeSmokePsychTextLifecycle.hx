package;

import flixel.text.FlxText;

/** Public modern callbacks with temporary registries and unmounted native scenes. */
@:access(PlayState)
@:access(GameOverSubstate)
class RuntimeSmokePsychTextLifecycle {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState):Void {
		var oldVariables = state.psychScriptVariables;
		var oldLegacy = state.nightmareVisionLegacyFieldCameras;
		var oldDead = state.isDead;
		var oldGameOver = GameOverSubstate.instance;
		var oldCustom = state.compatCustomSubstate;
		var dead:GameOverSubstate = Type.createEmptyInstance(GameOverSubstate);
		var custom:PsychCustomSubstate = Type.createEmptyInstance(PsychCustomSubstate);
		@:privateAccess dead.members = [];@:privateAccess dead.length = 0;
		@:privateAccess custom.members = [];@:privateAccess custom.length = 0;
		var texts:Array<FlxText> = [];
		var lua = new LuaCompatInterp();
		var cleanup = function() {
			for (label in texts) {dead.remove(label, true);custom.remove(label, true);if (label.animation != null) label.destroy();}
			state.psychScriptVariables = oldVariables;state.isDead = oldDead;state.nightmareVisionLegacyFieldCameras = oldLegacy;
			GameOverSubstate.instance = oldGameOver;state.compatCustomSubstate = oldCustom;lua.variables.clear();
		};
		try {
			state.nightmareVisionLegacyFieldCameras = false;state.psychScriptVariables = [];state.isDead = true;GameOverSubstate.instance = dead;state.compatCustomSubstate = custom;
			new PsychSourceBindings(state).install(lua);
			lua.execute(new hscript.Parser().parseString('if(makeLuaText("__modern.text","Native text",180,12,34)!=null)throw "Psych constructor result";', '__psych_text_create'));
			var label:FlxText = cast state.psychScriptVariables.get('__moderntext');texts.push(label);
			check(label != null && !state.psychScriptVariables.exists('__modern.text') && !state.haxeSprites.exists('__moderntext'), 'Shared variables and normalized tag');
			check(Type.getClass(label) == FlxText && label.text == 'Native text' && label.fieldWidth == 180 && label.x == 12 && label.y == 34
				&& label.size == 16 && label.color == 0xffffffff && label.alignment == 'center' && label.borderStyle == OUTLINE
				&& label.borderSize == 2 && label.borderColor == 0xff000000 && label.cameras[0] == state.camHUD
				&& label.scrollFactor.x == 0 && label.scrollFactor.y == 0, 'Shared native Psych formatting');
			var font = new FlxText();texts.push(font);font.font = PsychFontPath.resolve('vcr.ttf', '');
			check(label.font == font.font, 'Psych default font through native frontend');
			lua.execute(new hscript.Parser().parseString('addLuaText("__moderntext");addLuaText("__moderntext");if(getVar("__moderntext")==null||getTextString("__moderntext")!="Native text")throw "Psych shared tag visibility";', '__psych_text_add'));
			check(dead.members.length == 1 && label.container == dead && custom.members.length == 0, 'Add targets game-over even with custom substate');
			dead.remove(label, true);custom.add(label);
			lua.execute(new hscript.Parser().parseString('removeLuaText("__moderntext",false);', '__psych_text_retain'));
			check(label.container == null && label.exists && label.animation != null && state.psychScriptVariables.get('__moderntext') == label, 'Custom substate removal retains tag');
			state.compatCustomSubstate = null;
			var removedBeforeDestroy = false;
			dead.memberRemoved.add(function(item) {if (item == label) removedBeforeDestroy = label.exists && label.textField != null && label.animation != null;});
			lua.execute(new hscript.Parser().parseString('addLuaText("__moderntext");makeLuaText("__modern.text");', '__psych_text_replace'));
			var replacement:FlxText = cast state.psychScriptVariables.get('__moderntext');texts.push(replacement);
			check(removedBeforeDestroy && label.animation == null && replacement != label, 'Replacement removes before destruction without kill');
			check(replacement.text == '' && replacement.autoSize && replacement.x == 0 && replacement.y == 0, 'Zero-width constructor enables native autosizing; optional defaults');
			lua.execute(new hscript.Parser().parseString('addLuaText("__moderntext");removeObject("__moderntext");', '__psych_text_destroy'));
			check(replacement.animation == null && !state.psychScriptVariables.exists('__moderntext'), 'Destructive removal clears variable');
			@:privateAccess RuntimeSmokeHarness.emit('psych_text_lifecycle_native_verified', {sharedRegistry:true,normalizedTag:true,nativeDefaults:true,publicBindings:true,voidConstructor:true,gameOverAdd:true,customRemoval:true,retainedTag:true,replaceOrder:true,disposal:true,genericRemoval:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
