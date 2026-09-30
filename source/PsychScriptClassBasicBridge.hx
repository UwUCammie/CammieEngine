package;

import flixel.FlxBasic;
import hscript.ScriptClass;
import hscript.ScriptClassScope;

/**
	Native Flixel member for an owner-scoped ScriptClass that composes a
	FlxBasic. Flixel groups drive this bridge, which forwards lifecycle calls to
	the authored class while preserving the native superclass implementation.
*/
class PsychScriptClassBasicBridge extends FlxBasic {
	var scriptObject:ScriptClass;
	var nativeBasic:FlxBasic;
	var ownerScope:ScriptClassScope;
	var ownerDestroyCalled:Bool = false;
	var destroying:Bool = false;

	public function new(scriptObject:ScriptClass, nativeBasic:FlxBasic, ownerScope:ScriptClassScope) {
		super();
		this.scriptObject = scriptObject;
		this.nativeBasic = nativeBasic;
		this.ownerScope = ownerScope;
		syncFromNative();
	}

	public function wraps(scriptObject:ScriptClass):Bool return this.scriptObject == scriptObject;
	public function scriptOwner():ScriptClass return scriptObject;

	/** ScriptClass.destroy may be called before its wrapper is removed. */
	public function noteOwnerDestroyCalled():Void ownerDestroyCalled = true;

	/** FlxTypedGroup calls the bridge, not the composed owner object. */
	override public function update(elapsed:Float):Void {
		if (destroying || scriptObject == null || nativeBasic == null) return;
		syncFromNative();
		if (!exists || !active) return;
		try scriptObject.callFunction('update', [elapsed]) catch (error:Dynamic) {
			trace('[psych-basic-bridge] ' + scriptObject.className + '.update failed: ' + Std.string(error));
			throw error;
		}
		syncFromNative();
	}

	/** Preserve FlxCamera's current group draw target while invoking the owner. */
	override public function draw():Void {
		if (destroying || scriptObject == null || nativeBasic == null) return;
		syncFromNative();
		if (!exists || !visible) return;
		try scriptObject.callFunction('draw', []) catch (error:Dynamic) {
			trace('[psych-basic-bridge] ' + scriptObject.className + '.draw failed: ' + Std.string(error));
			throw error;
		}
		syncFromNative();
	}

	override public function kill():Void {
		super.kill();
		if (nativeBasic != null) nativeBasic.kill();
	}

	override public function revive():Void {
		super.revive();
		if (nativeBasic != null) nativeBasic.revive();
	}

	override public function destroy():Void {
		if (destroying) return;
		destroying = true;

		var owner = scriptObject;
		var basic = nativeBasic;
		var scope = ownerScope;
		if (owner != null && scope != null && scope.isActive() && !ownerDestroyCalled) {
			try owner.callFunction('destroy', []) catch (error:Dynamic) {
				trace('[psych-basic-bridge] owner destroy callback failed: ' + Std.string(error));
				// Ensure the native member still releases its resources if an authored
				// cleanup hook fails. Keep the error visible in the runtime log.
				if (basic != null) try basic.destroy() catch (_:Dynamic) {}
			}
		}
		// A direct owner destroy hook may intentionally omit super.destroy(). Keep
		// the native superclass lifecycle complete without destroying it twice.
		if (basic != null && basic.exists) try basic.destroy() catch (_:Dynamic) {}

		if (scope != null) scope.forgetNativeBasicBridge(this);
		scriptObject = null;
		nativeBasic = null;
		ownerScope = null;
		super.destroy();
	}

	function syncFromNative():Void {
		if (nativeBasic == null) return;
		active = nativeBasic.active;
		visible = nativeBasic.visible;
		alive = nativeBasic.alive;
		exists = nativeBasic.exists;
	}
}
