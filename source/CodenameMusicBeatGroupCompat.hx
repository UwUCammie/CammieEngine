package;

import flixel.FlxSprite;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
import hscript.ScriptClass;
import hscript.ScriptClassScope;

@:access(hscript.ScriptClass)
/** Native FlxSpriteGroup base for Codename MusicBeatGroup owner classes.

	HScript-ex classes compose their native superclass instead of becoming the
	native sprite themselves. This adapter keeps the real Flixel group for scene
	placement and drawing, then dispatches only lifecycle methods declared by
	the same active owner class. A script `super.update()` re-enters this adapter
	while its callback is on the stack; the guard routes that call to Flixel's
	native group implementation without invoking the script twice.
*/
class CodenameMusicBeatGroupCompat extends FlxTypedSpriteGroup<FlxSprite> {
	var ownerScript:ScriptClass;
	var ownerScope:ScriptClassScope;
	final dispatching:Map<String, Bool> = new Map();
	var destroyedGroup:Bool = false;

	public function new(x:Float = 0, y:Float = 0) {
		super();
		this.x = x;
		this.y = y;
	}

	/** Bind the owner class whose `super` proxy composes this native group. */
	public function bindOwnerScript(scriptClass:ScriptClass):Void {
		if (scriptClass == null || scriptClass._classScope == null
			|| !scriptClass._classScope.isActive())
			throw '[codename-music-beat-group] Cannot bind an inactive owner class';
		if (ownerScript != null && ownerScript != scriptClass)
			throw '[codename-music-beat-group] Native group already belongs to another owner class';
		ownerScript = scriptClass;
		ownerScope = scriptClass._classScope;
	}

	/** MusicBeatGroup extends FlxTypedSpriteGroup and supplies virtual update. */
	override public function update(elapsed:Float):Void {
		if (!dispatchOwnerMethod('update', [elapsed])) super.update(elapsed);
	}

	/** Match MusicBeatGroup's child beat forwarding for method-capable sprites. */
	public function beatHit(curBeat:Int):Void {
		if (!dispatchOwnerMethod('beatHit', [curBeat])) forwardToMembers('beatHit', [curBeat]);
	}

	public function stepHit(curStep:Int):Void {
		if (!dispatchOwnerMethod('stepHit', [curStep])) forwardToMembers('stepHit', [curStep]);
	}

	public function measureHit(curMeasure:Int):Void {
		if (!dispatchOwnerMethod('measureHit', [curMeasure])) forwardToMembers('measureHit', [curMeasure]);
	}

	function dispatchOwnerMethod(name:String, args:Array<Dynamic>):Bool {
		if (ownerScript == null || ownerScope == null) return false;
		if (!ownerScope.isActive()) {
			clearOwnerScript();
			return false;
		}
		if (dispatching.exists(name) || !ownerScript.hasDeclaredField(name)) return false;

		dispatching.set(name, true);
		try ownerScript.callFunction(name, args) catch (error:Dynamic) {
			dispatching.remove(name);
			throw error;
		}
		dispatching.remove(name);
		return true;
	}

	function forwardToMembers(name:String, args:Array<Dynamic>):Void {
		if (members == null) return;
		for (member in members) {
			if (member == null) continue;
			var callback:Dynamic = Reflect.field(member, name);
			if (Reflect.isFunction(callback)) Reflect.callMethod(member, callback, args);
		}
	}

	/** Always release the composed owner reference and native group resources.
		If an owner destroy hook calls `super.destroy()`, the re-entry guard lets
		that call perform native destruction once; if it omits `super`, this host
		still tears down the Flixel group after the hook returns.
	*/
	override public function destroy():Void {
		if (destroyedGroup) return;
		try dispatchOwnerMethod('destroy', []) catch (error:Dynamic) {
			if (!destroyedGroup) destroyNativeGroup();
			throw error;
		}
		if (!destroyedGroup) destroyNativeGroup();
	}

	function destroyNativeGroup():Void {
		if (destroyedGroup) return;
		destroyedGroup = true;
		clearOwnerScript();
		dispatching.clear();
		super.destroy();
	}

	function clearOwnerScript():Void {
		ownerScript = null;
		ownerScope = null;
	}
}
