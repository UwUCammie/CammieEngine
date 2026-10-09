package;

import flixel.text.FlxText;

/** Disposable native text and an unmounted game-over scene exercise public bindings. */
@:access(PlayState)
@:access(GameOverSubstate)
class RuntimeSmokeLegacyTextLifecycle {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState, lua:LuaCompatInterp):Void {
		var oldDead = state.isDead;
		var oldGameOver = GameOverSubstate.instance;
		var dead:GameOverSubstate = Type.createEmptyInstance(GameOverSubstate);
		@:privateAccess dead.members = [];
		@:privateAccess dead.length = 0;
		var created:Array<FlxText> = [];
		var cleanup = function() {
			for (text in created) {
				dead.remove(text, true);
				if (text.animation != null) text.destroy();
			}
			state.modchartTexts.remove('__lifecycle');state.modchartSprites.remove('__lifecycle');
			state.isDead = oldDead;GameOverSubstate.instance = oldGameOver;
		};
		try {
			GameOverSubstate.instance = dead;state.isDead = true;
			lua.execute(new hscript.Parser().parseString('if(makeLuaText("__life.cycle","Native text",200,12,34)!=null)throw "Lua text construction must be void";', '__text_create'));
			var label:SourceModchartText = cast state.modchartTexts.get('__lifecycle');created.push(label);
			check(label != null && !state.modchartTexts.exists('__life.cycle') && !label.wasAdded, 'Normalized text tag and initial mounting flag');
			check(label.x == 12 && label.y == 34 && label.fieldWidth == 200 && label.text == 'Native text' && label.size == 16
				&& label.alignment == 'center' && label.borderSize == 2 && label.borderStyle == OUTLINE
				&& label.borderColor == 0xff000000 && label.color == 0xffffffff && label.cameras[0] == state.camHUD
				&& label.scrollFactor.x == 0 && label.scrollFactor.y == 0, 'Historical native text defaults');
			var expectedFont = new FlxText();created.push(expectedFont);
			expectedFont.font = state.nightmareVisionPaths.font('vcr.ttf');
			check(label.font == expectedFont.font, 'Owner font resolution through the native font frontend');
			var sibling = new FlxText(0, 0, 80, 'sprite sibling');created.push(sibling);state.modchartSprites.set('__lifecycle', sibling);
			lua.execute(new hscript.Parser().parseString('addLuaText("__lifecycle");addLuaText("__lifecycle");setTextString("__lifecycle","text namespace");', '__text_mount'));
			check(dead.members.length == 1 && label.container == dead && label.wasAdded && label.text == 'text namespace' && sibling.text == 'sprite sibling', 'Game-over mounting and separate text namespace');
			lua.execute(new hscript.Parser().parseString('removeLuaText("__lifecycle",false);', '__text_detach'));
			check(!label.wasAdded && label.exists && label.animation != null && label.container == null && state.modchartTexts.get('__lifecycle') == label, 'Reusable non-destructive text removal');
			var replacementDetached = false;
			dead.memberRemoved.add(function(item) {
				if (item == label) replacementDetached = !label.exists && label.textField == null && label.animation != null && label.wasAdded;
			});
			lua.execute(new hscript.Parser().parseString('addLuaText("__lifecycle");makeLuaText("__life.cycle","replacement",200,12,34);', '__text_replace'));
			var replacement:SourceModchartText = cast state.modchartTexts.get('__lifecycle');created.push(replacement);
			check(replacementDetached && !label.exists && label.animation == null && label.wasAdded && dead.members.indexOf(label) < 0 && !replacement.wasAdded, 'Replacement uses play-state removal before native destruction detaches the game-over member');
			var removed = false;
			dead.memberRemoved.add(function(item) {
				if (item == replacement) {
					check(!replacement.exists && replacement.animation != null && replacement.wasAdded, 'Text kill/remove/destroy callback ordering');
					removed = true;
				}
			});
			lua.execute(new hscript.Parser().parseString('addLuaText("__lifecycle");removeLuaText("__lifecycle");', '__text_destroy'));
			check(removed && replacement.animation == null && !replacement.wasAdded && !state.modchartTexts.exists('__lifecycle') && sibling.exists, 'Destructive text removal preserves sprite sibling');
			@:privateAccess RuntimeSmokeHarness.emit('legacy_text_lifecycle_native_verified', {publicBindings:true,voidConstructor:true,sourceDefaults:true,ownerFont:true,normalizedTag:true,wasAdded:true,gameOverMount:true,reusableTag:true,replacementScene:true,killRemoveDestroy:true,separateNamespace:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
