package;

import lime.utils.AssetLibrary;
import openfl.events.EventDispatcher;

using StringTools;

/** Owner-local Lime/OpenFL Assets events shared by every facade for a context. */
@:keep
class SourceOwnerAssetsEvents {
	static var providers:Map<String, SourceOwnerAssetsEvents> = new Map();

	public final ownerRoot:String;
	public final engine:String;
	public final scope:String;
	public final limeOnChange:lime.app.Event<Void->Void>;
	var dispatcher:EventDispatcher;
	var watchedLibraries:haxe.ds.ObjectMap<AssetLibrary, Void->Void>;
	var bridgeOpenFlChange:Void->Void;
	var openFlBridgeAttached:Bool = false;
	var released:Bool = false;

	private function new(context:SourceOwnerAssetContext) {
		ownerRoot = context.ownerRoot;
		engine = context.engine;
		scope = context.scope;
		limeOnChange = new lime.app.Event<Void->Void>();
		dispatcher = new EventDispatcher();
		watchedLibraries = new haxe.ds.ObjectMap();
		bridgeOpenFlChange = function():Void {
			if (!released && dispatcher != null)
				dispatcher.dispatchEvent(new openfl.events.Event(openfl.events.Event.CHANGE));
		};
	}

	/** Return one event surface for this exact owner, engine, and logical scope. */
	public static function forContext(context:SourceOwnerAssetContext):SourceOwnerAssetsEvents {
		if (context == null) throw '[source-assets] An owner context is required for asset events';
		var key = contextKey(context.ownerRoot, context.engine, context.scope);
		if (!providers.exists(key)) providers.set(key, new SourceOwnerAssetsEvents(context));
		return providers.get(key);
	}

	/** The package lifecycle calls this for each exact owner retirement. */
	public static function releaseOwner(ownerRoot:String):Void {
		if (ownerRoot == null) return;
		var prefix = ownerKey(ownerRoot) + '\x00';
		var keys:Array<String> = [];
		for (key in providers.keys()) if (key.startsWith(prefix)) keys.push(key);
		for (key in keys) {
			var provider = providers.get(key);
			providers.remove(key);
			if (provider != null) provider.release();
		}
	}

	/** Mirror Lime Assets.onChange with a separate event for this owner context. */
	public function addOnChange(listener:Void->Void, once:Bool = false, priority:Int = 0):Void {
		requireActive();
		limeOnChange.add(listener, once, priority);
	}

	public function removeOnChange(listener:Void->Void):Void {
		if (!released && listener != null) limeOnChange.remove(listener);
	}

	public function hasOnChange(listener:Void->Void):Bool
		return !released && listener != null && limeOnChange.has(listener);

	/** Bridge one exact local Lime library into this context's change signal. */
	public function watchLibrary(library:AssetLibrary):Void {
		requireActive();
		if (library == null || watchedLibraries.exists(library)) return;
		var listener = function():Void {
			if (!released) limeOnChange.dispatch();
		};
		library.onChange.add(listener);
		watchedLibraries.set(library, listener);
	}

	public function unwatchLibrary(library:AssetLibrary):Void {
		if (released || library == null || !watchedLibraries.exists(library)) return;
		var listener = watchedLibraries.get(library);
		library.onChange.remove(listener);
		watchedLibraries.remove(library);
	}

	/** Match OpenFL Assets.addEventListener's lazy Lime change subscription. */
	public function addEventListener(type:String, listener:Dynamic, useCapture:Bool = false,
		priority:Int = 0, useWeakReference:Bool = false):Void {
		requireActive();
		if (dispatcher == null) throw '[source-assets] Owner asset event dispatcher is unavailable';
		if (!openFlBridgeAttached) {
			limeOnChange.add(bridgeOpenFlChange);
			openFlBridgeAttached = true;
		}
		dispatcher.addEventListener(type, listener, useCapture, priority, useWeakReference);
	}

	public function removeEventListener(type:String, listener:Dynamic, useCapture:Bool = false):Void {
		if (!released && dispatcher != null)
			dispatcher.removeEventListener(type, listener, useCapture);
	}

	public function dispatchEvent(event:openfl.events.Event):Bool {
		requireActive();
		return dispatcher != null && dispatcher.dispatchEvent(event);
	}

	public function hasEventListener(type:String):Bool
		return !released && dispatcher != null && dispatcher.hasEventListener(type);

	public function willTrigger(type:String):Bool
		return !released && dispatcher != null && dispatcher.willTrigger(type);

	function release():Void {
		if (released) return;
		released = true;
		if (openFlBridgeAttached) limeOnChange.remove(bridgeOpenFlChange);
		openFlBridgeAttached = false;
		var libraries:Array<AssetLibrary> = [];
		for (library in watchedLibraries.keys()) libraries.push(library);
		for (library in libraries) unwatchBeforeRelease(library);
		watchedLibraries.clear();
		limeOnChange.removeAll();
		// Dropping the dispatcher releases all owner script listeners together.
		dispatcher = null;
		bridgeOpenFlChange = null;
	}

	function unwatchBeforeRelease(library:AssetLibrary):Void {
		var listener = watchedLibraries.get(library);
		if (listener != null) library.onChange.remove(listener);
	}

	function requireActive():Void {
		if (released) throw '[source-assets] Owner asset events have been released';
	}

	static function contextKey(ownerRoot:String, engine:String, scope:String):String
		return ownerKey(ownerRoot) + '\x00' + engine + '\x00' + scope;

	static function ownerKey(ownerRoot:String):String {
		var owner = StringTools.replace(StringTools.trim(ownerRoot), '\\', '/');
		#if windows
		owner = owner.toLowerCase();
		#end
		return owner;
	}
}
