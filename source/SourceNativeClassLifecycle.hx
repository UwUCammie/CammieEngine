package;

import hscript.ScriptClass;
import hscript.ScriptClassScope;

/** One callback and resource lifetime shared by every native Flixel adapter. */
class SourceNativeClassLifecycle {
	public var owner(default, null):ScriptClass;
	var scope:ScriptClassScope;
	var nativeBase:(String, Array<Dynamic>)->Dynamic;
	var ownerDestroyed:Bool = false;
	var nativeDestroyed:Bool = false;
	var destroying:Bool = false;

	public function new(owner:ScriptClass, scope:ScriptClassScope, nativeBase:(String, Array<Dynamic>)->Dynamic) {
		this.owner = owner;
		this.scope = scope;
		this.nativeBase = nativeBase;
	}
	public function noteOwnerDestroyCalled():Void ownerDestroyed = true;
	public static function hasNativeSuper(name:String, animation:Bool):Bool {
		return ['updateAnimation', 'updateHitbox', 'drawSimple', 'drawComplex'].indexOf(name) >= 0
			? animation : ['update', 'draw', 'kill', 'revive', 'destroy'].indexOf(name) >= 0;
	}
	public function dispatch(name:String, args:Array<Dynamic>):Void {
		if (name == 'destroy') {destroy();return;}
		if (!nativeDestroyed && !destroying && owner != null && scope != null && scope.isActive())
			scope.callNativeLifecycle(owner, name, args);
	}
	public function callNativeSuper(name:String, args:Array<Dynamic>):Dynamic {
		if (name == 'destroy') destroyNative();
		else if (!nativeDestroyed) return nativeBase(name, args);
		return null;
	}
	function destroyNative():Void {
		if (nativeDestroyed) return;
		nativeDestroyed = true;
		nativeBase('destroy', []);
	}
	public function destroy():Void {
		if (destroying || owner == null) return;
		destroying = true;
		var failure:Dynamic = null;
		if (scope != null && scope.isActive() && !ownerDestroyed) {
			try scope.callNativeLifecycle(owner, 'destroy', []) catch (error:Dynamic) failure = error;
		}
		// Complete native cleanup even when an authored hook omits super.
		try destroyNative() catch (error:Dynamic) {if (failure == null) failure = error;}
		if (scope != null) scope.forgetNativeAdapter(this);
		owner = null;
		scope = null;
		nativeBase = null;
		if (failure != null) throw failure;
	}
}
