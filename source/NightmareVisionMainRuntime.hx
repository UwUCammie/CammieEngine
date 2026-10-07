package;

import flixel.FlxG;
import flixel.FlxGame;
import flixel.input.keyboard.FlxKey;
import openfl.display.Sprite;
import openfl.display.Stage;
import openfl.events.Event;
import openfl.events.KeyboardEvent;

/** The source Main constructor's runtime listeners, leased to one imported owner. */
@:keep
@:access(flixel.FlxCamera)
class NightmareVisionMainRuntime {
	public final ownerRoot:String;
	var capturedStage:Stage;
	var capturedResizeSignal:Dynamic;
	var keyDownHandler:Event->Void;
	var resizeHandler:Int->Int->Void;
	var installed:Bool = false;
	var released:Bool = false;

	/** Optional host arguments are a test seam; production captures Flixel's current objects. */
	public function new(ownerRoot:String, ?hostStage:Stage, ?gameResizedSignal:Dynamic) {
		if (ownerRoot == null || ownerRoot == '')
			throw '[nightmare-vision-main] Missing source owner';
		this.ownerRoot = ownerRoot;
		capturedStage = hostStage;
		capturedResizeSignal = gameResizedSignal;
	}

	/** Match the source Main listener registration and retain exact references for teardown. */
	public function install():Void {
		ensureAlive();
		if (installed) return;
		var stage = capturedStage == null ? FlxG.stage : capturedStage;
		var signal:Dynamic = capturedResizeSignal == null ? FlxG.signals.gameResized : capturedResizeSignal;
		if (stage == null || signal == null)
			throw '[nightmare-vision-main] Source Main listeners require the initialized Flixel stage and resize signal';

		capturedStage = stage;
		capturedResizeSignal = signal;
		keyDownHandler = function(event:Event):Void {
			var keyboard:KeyboardEvent = cast event;
			if (keyboard.keyCode == FlxKey.ENTER && keyboard.altKey)
				keyboard.stopImmediatePropagation();
		};
		resizeHandler = onResize;
		stage.addEventListener(KeyboardEvent.KEY_DOWN, keyDownHandler, false, 100);
		var add = Reflect.field(signal, 'add');
		if (!Reflect.isFunction(add)) {
			stage.removeEventListener(KeyboardEvent.KEY_DOWN, keyDownHandler, false);
			keyDownHandler = null;
			resizeHandler = null;
			throw '[nightmare-vision-main] Flixel gameResized signal does not support add';
		}
		try Reflect.callMethod(signal, add, [resizeHandler]) catch (error:Dynamic) {
			stage.removeEventListener(KeyboardEvent.KEY_DOWN, keyDownHandler, false);
			keyDownHandler = null;
			resizeHandler = null;
			capturedStage = null;
			capturedResizeSignal = null;
			throw error;
		}
		installed = true;
	}

	/** Source Main.onResize. The calculated scale is intentionally unused in the donor. */
	public function onResize(width:Int, height:Int):Void {
		ensureAlive();
		var scale:Float = Math.max(1, Math.min(width / FlxG.width, height / FlxG.height));
		if (FlxG.cameras != null) {
			for (camera in FlxG.cameras.list) {
				if (camera != null && camera.filters != null)
					resetSpriteCache(camera.flashSprite);
			}
		}
		var game:FlxGame = FlxG.game;
		if (game != null) resetSpriteCache(game);
	}

	/** Exact source Main cache invalidation, including its null handling. */
	@:nullSafety(Off)
	public static function resetSpriteCache(sprite:Sprite):Void {
		if (sprite == null) return;
		@:privateAccess {
			sprite.__cacheBitmap = null;
			sprite.__cacheBitmapData = null;
		}
	}

	/** Owner-bound wrapper used by captured script scopes. */
	public function resetSpriteCacheForOwner(sprite:Sprite):Void {
		requireActive();
		resetSpriteCache(sprite);
	}

	/** Guard for owner-local Main binding closures retained by a script scope. */
	public function requireActive():Void ensureAlive();

	/** Remove listeners from the same captured objects, even if Flixel globals changed. */
	public function release():Void {
		if (released) return;
		released = true;
		if (installed) {
			if (capturedStage != null && keyDownHandler != null)
				capturedStage.removeEventListener(KeyboardEvent.KEY_DOWN, keyDownHandler, false);
			if (capturedResizeSignal != null && resizeHandler != null) {
				var remove = Reflect.field(capturedResizeSignal, 'remove');
				if (Reflect.isFunction(remove)) Reflect.callMethod(capturedResizeSignal, remove, [resizeHandler]);
			}
		}
		installed = false;
		keyDownHandler = null;
		resizeHandler = null;
		capturedStage = null;
		capturedResizeSignal = null;
	}

	function ensureAlive():Void {
		if (released) throw '[nightmare-vision-main] Source Main runtime has been released';
	}
}
