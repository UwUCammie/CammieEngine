package;

import flixel.FlxSprite;
import flixel.system.FlxAssets.FlxGraphicAsset;
import hscript.ScriptClass;
import hscript.ScriptClassScope;

/** Native storage and rendering for an authored source subclass of FlxSprite. */
class PsychScriptClassSprite extends FlxSprite {
	var owner:ScriptClass;
	var scope:ScriptClassScope;
	var ownerDestroyed:Bool = false;
	var nativeDestroyed:Bool = false;
	var destroying:Bool = false;

	public function new(x:Float = 0, y:Float = 0, ?graphic:FlxGraphicAsset) {
		super(x, y, graphic);
	}

	public function bind(owner:ScriptClass, scope:ScriptClassScope):Void {
		this.owner = owner;
		this.scope = scope;
	}
	public function scriptOwner():ScriptClass return owner;
	public function noteOwnerDestroyCalled():Void ownerDestroyed = true;
	function usable():Bool return !nativeDestroyed && !destroying && owner != null && scope != null && scope.isActive();

	override public function update(elapsed:Float):Void {
		if (usable()) owner.callFunction('update', [elapsed]);
	}
	override public function draw():Void {
		if (usable()) owner.callFunction('draw', []);
	}
	override function updateAnimation(elapsed:Float):Void {
		if (usable()) owner.callFunction('updateAnimation', [elapsed]);
	}
	override public function kill():Void {
		if (usable()) owner.callFunction('kill', []);
	}
	override public function revive():Void {
		if (usable()) owner.callFunction('revive', []);
	}

	/** Explicit source super calls bypass virtual entry while sharing Flixel code. */
	public static function hasNativeSuper(name:String):Bool {
		return ['update', 'draw', 'updateAnimation', 'kill', 'revive', 'destroy'].indexOf(name) >= 0;
	}
	public function callNativeSuper(name:String, args:Array<Dynamic>):Dynamic {
		switch (name) {
			case 'update': if (!nativeDestroyed) super.update(args[0]);
			case 'draw': if (!nativeDestroyed) super.draw();
			case 'updateAnimation': if (!nativeDestroyed) super.updateAnimation(args[0]);
			case 'kill': if (!nativeDestroyed) super.kill();
			case 'revive': if (!nativeDestroyed) super.revive();
			case 'destroy': destroyNative();
			default: throw '[source-sprite] Unsupported native super method: ' + name;
		}
		return null;
	}
	function destroyNative():Void {
		if (nativeDestroyed) return;
		nativeDestroyed = true;
		super.destroy();
	}
	override public function destroy():Void {
		if (destroying || owner == null) return;
		destroying = true;
		var failure:Dynamic = null;
		if (scope != null && scope.isActive() && !ownerDestroyed) {
			try owner.callFunction('destroy', []) catch (error:Dynamic) failure = error;
		}
		// Native resources still need release when authored cleanup omits super.
		try destroyNative() catch (error:Dynamic) {if (failure == null) failure = error;}
		if (scope != null) scope.forgetNativeSprite(this);
		owner = null;
		scope = null;
		if (failure != null) throw failure;
	}
}
