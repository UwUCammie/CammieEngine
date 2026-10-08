package;

import haxe.io.Bytes;
import lime.app.Future;
import lime.app.Promise;
import lime.graphics.Image;
import lime.media.AudioBuffer;
import lime.text.Font;
import lime.utils.AssetLibrary;

/**
	A real Lime AssetLibrary view whose lazy reads stay bound to one verified
	owner identity. The delegate is built from that identity's checked manifest;
	this subtype forwards its typed caches while rejecting stale owner epochs.
*/
@:keep
class PsychOwnerAssetLibraryView extends AssetLibrary {
	final delegate:AssetLibrary;
	final identityIsCurrent:Void->Bool;
	final staleMessage:String;
	final delegateChangeListener:Void->Void;
	var guardedLoadFuture:Future<AssetLibrary>;
	var retired:Bool = false;

	public function new(delegate:AssetLibrary, identityIsCurrent:Void->Bool,
		?staleMessage:String) {
		super();
		if (delegate == null) throw "[psych-assets] An owner AssetLibrary delegate is required";
		if (identityIsCurrent == null) throw "[psych-assets] An owner identity guard is required";
		this.delegate = delegate;
		this.identityIsCurrent = identityIsCurrent;
		this.staleMessage = staleMessage == null || staleMessage == ""
			? "[psych-assets] Selected owner identity changed while its asset library was retained"
			: staleMessage;
		delegateChangeListener = function():Void {
			if (isActive()) onChange.dispatch();
		};
		delegate.onChange.add(delegateChangeListener);
	}

	public override function exists(id:String, type:String):Bool {
		ensureActive();
		return delegate.exists(id, type);
	}

	public override function getAsset(id:String, type:String):Dynamic {
		ensureActive();
		return delegate.getAsset(id, type);
	}

	public override function getAudioBuffer(id:String):AudioBuffer {
		ensureActive();
		return delegate.getAudioBuffer(id);
	}

	public override function getBytes(id:String):Bytes {
		ensureActive();
		return delegate.getBytes(id);
	}

	public override function getFont(id:String):Font {
		ensureActive();
		return delegate.getFont(id);
	}

	public override function getImage(id:String):Image {
		ensureActive();
		return delegate.getImage(id);
	}

	public override function getPath(id:String):String {
		ensureActive();
		return delegate.getPath(id);
	}

	public override function getText(id:String):String {
		ensureActive();
		return delegate.getText(id);
	}

	public override function isLocal(id:String, type:String):Bool {
		ensureActive();
		return delegate.isLocal(id, type);
	}

	public override function list(type:String):Array<String> {
		ensureActive();
		return delegate.list(type);
	}

	public override function loadAsset(id:String, type:String):Future<Dynamic> {
		return guardedFuture(function() return delegate.loadAsset(id, type));
	}

	public override function load():Future<AssetLibrary> {
		if (!isActive()) return failed(staleMessage);
		if (guardedLoadFuture != null) return guardedLoadFuture;
		var promise = new Promise<AssetLibrary>();
		guardedLoadFuture = promise.future;
		var future:Future<AssetLibrary>;
		try future = delegate.load() catch (error:Dynamic) {
			promise.error(isActive() ? error : staleMessage);
			return guardedLoadFuture;
		}
		forwardLoad(future, promise);
		return guardedLoadFuture;
	}

	public override function loadAudioBuffer(id:String):Future<AudioBuffer> {
		return guardedFuture(function() return delegate.loadAudioBuffer(id));
	}

	public override function loadBytes(id:String):Future<Bytes> {
		return guardedFuture(function() return delegate.loadBytes(id));
	}

	public override function loadFont(id:String):Future<Font> {
		return guardedFuture(function() return delegate.loadFont(id));
	}

	public override function loadImage(id:String):Future<Image> {
		return guardedFuture(function() return delegate.loadImage(id));
	}

	public override function loadText(id:String):Future<String> {
		return guardedFuture(function() return delegate.loadText(id));
	}

	/** Lime unload only clears this library's caches; it does not revoke the
		owner identity or the detached object retained by a caller. */
	public override function unload():Void delegate.unload();

	/** Owner-proof retirement differs from source unload/remove: stale handles
		must release any caches they refilled while detached. */
	@:keep public function retire():Void {
		if (retired) return;
		retired = true;
		delegate.onChange.remove(delegateChangeListener);
		clearStaleCaches();
	}

	function ensureActive():Void {
		if (!isActive()) throw staleMessage;
	}

	function isActive():Bool {
		if (retired) return false;
		var active = false;
		try active = identityIsCurrent() catch (_:Dynamic) active = false;
		if (!active) retire();
		return active;
	}

	function guardedFuture<T>(operation:Void->Future<T>):Future<T> {
		if (!isActive()) return failed(staleMessage);
		var future:Future<T>;
		try future = operation() catch (error:Dynamic)
			return failed(isActive() ? error : staleMessage);
		var promise = new Promise<T>();
		forward(future, promise, function(value:T) return value);
		return promise.future;
	}

	function forward<A, B>(future:Future<A>, promise:Promise<B>, convert:A->B):Void {
		future.onProgress(function(loaded:Int, total:Int) {
			if (isActive()) promise.progress(loaded, total);
		});
		future.onError(function(error:Dynamic) {
			if (!isActive()) {
				clearStaleCaches();
				promise.error(staleMessage);
			} else {
				promise.error(error);
			}
		});
		future.onComplete(function(value:A) {
			if (!isActive()) {
				clearStaleCaches();
				promise.error(staleMessage);
				return;
			}
			try promise.complete(convert(value)) catch (error:Dynamic) promise.error(error);
		});
	}

	function forwardLoad(future:Future<AssetLibrary>, promise:Promise<AssetLibrary>):Void {
		future.onProgress(function(loaded:Int, total:Int) {
			if (isActive()) promise.progress(loaded, total);
		});
		future.onError(function(error:Dynamic) {
			if (!isActive()) {
				clearStaleCaches();
				promise.error(staleMessage);
			} else {
				promise.error(error);
			}
		});
		future.onComplete(function(_loaded:AssetLibrary) {
			if (!isActive()) {
				clearStaleCaches();
				promise.error(staleMessage);
			} else {
				promise.complete(cast this);
			}
		});
	}

	function clearStaleCaches():Void {
		try delegate.unload() catch (_:Dynamic) {}
	}

	function failed<T>(error:Dynamic):Future<T> return cast Future.withError(error);
}
