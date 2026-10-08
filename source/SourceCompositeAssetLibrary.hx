package;

import haxe.io.Bytes;
import lime.app.Future;
import lime.app.Promise;
import lime.graphics.Image;
import lime.media.AudioBuffer;
import lime.text.Font;
import lime.utils.AssetLibrary;

/**
	A real Lime AssetLibrary for one declared library across the exact scopes of
	a SourceOwnerAssetContext. Methods route through the existing owner facade,
	so source-order ID shadowing, path checks, cache rules, and proof guards stay
	shared with direct Assets calls.
*/
@:keep
class SourceCompositeAssetLibrary extends AssetLibrary {
	final context:SourceOwnerAssetContext;
	final libraryName:String;
	final assets:Dynamic;
	final proofAtCreation:String;
	final assetEvents:SourceOwnerAssetsEvents;
	var loadFuture:Future<AssetLibrary>;
	var retired:Bool = false;
	var watched:Array<AssetLibrary> = [];
	var watchedListeners:haxe.ds.ObjectMap<AssetLibrary, Void->Void> = new haxe.ds.ObjectMap();
	var bridgeChangeToOwnerAssets:Void->Void;
	var ownerEventBridgeAttached:Bool = false;

	public var name(get, never):String;

	public function new(context:SourceOwnerAssetContext, libraryName:String,
		assets:Dynamic) {
		super();
		if (context == null || !context.composite || assets == null)
			throw '[source-assets] A composite owner context and Assets facade are required';
		this.context = context;
		this.libraryName = SourceLimeAssetIdentity.canonicalLibrary(libraryName);
		this.assets = assets;
		this.assetEvents = SourceOwnerAssetsEvents.forContext(context);
		this.proofAtCreation = context.proofSignature();
		bridgeChangeToOwnerAssets = function():Void {
			if (isActive()) assetEvents.limeOnChange.dispatch();
		};
		onChange.add(bridgeChangeToOwnerAssets);
		ownerEventBridgeAttached = true;
	}

	function get_name():String return libraryName;

	public override function exists(id:String, type:String):Bool {
		ensureActive();
		return invoke('exists', [qualified(id), type]);
	}

	public override function getAsset(id:String, type:String):Dynamic {
		ensureActive();
		return invoke('getAsset', [qualified(id), cast type]);
	}

	public override function getAudioBuffer(id:String):AudioBuffer {
		ensureActive();
		return invoke('getAudioBuffer', [qualified(id)]);
	}

	public override function getBytes(id:String):Bytes {
		ensureActive();
		return invoke('getBytes', [qualified(id)]);
	}

	public override function getFont(id:String):Font {
		ensureActive();
		return invoke('getFont', [qualified(id)]);
	}

	public override function getImage(id:String):Image {
		ensureActive();
		return invoke('getImage', [qualified(id)]);
	}

	public override function getPath(id:String):String {
		ensureActive();
		return invoke('getPath', [qualified(id)]);
	}

	public override function getText(id:String):String {
		ensureActive();
		return invoke('getText', [qualified(id)]);
	}

	public override function isLocal(id:String, type:String):Bool {
		ensureActive();
		return invoke('isLocal', [qualified(id), cast type]);
	}

	public override function list(type:String):Array<String> {
		ensureActive();
		return context.listAssets(libraryName, type);
	}

	public override function loadAsset(id:String, type:String):Future<Dynamic> {
		ensureActive();
		return guarded(function() return invoke('loadAsset', [qualified(id), cast type]));
	}

	public override function load():Future<AssetLibrary> {
		if (!isActive()) return failed(staleMessage());
		if (loadFuture != null) return loadFuture;

		var identities:Array<RuntimeOwnerAssetIdentity>;
		try identities = context.identitiesForLibrary(libraryName) catch (error:Dynamic)
			return failed(error);
		if (identities.length == 0) return failed('[source-assets] Owner library is not declared: ' + libraryName);
		for (identity in identities) if (identity.indexVersion < 2)
			return failed('[psych-assets] Selected-owner library load metadata is unavailable; refresh this import: ' + libraryName);

		var promise = new Promise<AssetLibrary>();
		loadFuture = promise.future;
		var remaining = identities.length;
		for (identity in identities) {
			var future:Future<AssetLibrary>;
			try future = PsychOwnerAssetLibraryCache.loadLime(identity, libraryName) catch (error:Dynamic) {
				promise.error(error);
				return loadFuture;
			}
			future.onProgress(promise.progress);
			future.onError(function(error:Dynamic) {
				if (isActive()) promise.error(error) else promise.error(staleMessage());
			});
			future.onComplete(function(loaded:AssetLibrary) {
				if (!isActive()) {
					promise.error(staleMessage());
					return;
				}
				watchLibrary(loaded);
				remaining--;
				if (remaining == 0) promise.complete(cast this);
			});
		}
		return loadFuture;
	}

	public override function loadAudioBuffer(id:String):Future<AudioBuffer> {
		ensureActive();
		return guarded(function() return invoke('loadAudioBuffer', [qualified(id)]));
	}

	public override function loadBytes(id:String):Future<Bytes> {
		ensureActive();
		return guarded(function() return invoke('loadBytes', [qualified(id)]));
	}

	public override function loadFont(id:String):Future<Font> {
		ensureActive();
		return guarded(function() return invoke('loadFont', [qualified(id)]));
	}

	public override function loadImage(id:String):Future<Image> {
		ensureActive();
		return guarded(function() return invoke('loadImage', [qualified(id)]));
	}

	public override function loadText(id:String):Future<String> {
		ensureActive();
		return guarded(function() return invoke('loadText', [qualified(id)]));
	}

	/** Match removal of the one source library by clearing all exact owner scopes. */
	public override function unload():Void {
		if (retired) return;
		// A retained composite view must never unload a newer package/core
		// identity after its proof has changed.
		if (!isActive()) {
			retire();
			return;
		}
		unwatchLibraries();
		var proof = proofAtCreation;
		var identities = context.identitiesForLibrary(libraryName);
		if (context.proofSignature() != proof) {
			retire();
			return;
		}
		for (identity in identities) {
			if (context.proofSignature() != proof) {
				retire();
				return;
			}
			PsychOwnerAssetLibraryCache.unload(identity, libraryName, true);
		}
		loadFuture = null;
	}

	@:keep public function retire():Void {
		if (retired) return;
		retired = true;
		unwatchLibraries();
		detachOwnerEventBridge();
	}

	function invoke(method:String, args:Array<Dynamic>):Dynamic {
		ensureActive();
		var callback = Reflect.field(assets, method);
		if (callback == null) throw '[source-assets] Source Assets method is unavailable: ' + method;
		return Reflect.callMethod(assets, callback, args);
	}

	function guarded<T>(operation:Void->Future<T>):Future<T> {
		if (!isActive()) return failed(staleMessage());
		var source:Future<T>;
		try source = operation() catch (error:Dynamic) return failed(isActive() ? error : staleMessage());
		var promise = new Promise<T>();
		source.onProgress(function(loaded:Int, total:Int) if (isActive()) promise.progress(loaded, total));
		source.onError(function(error:Dynamic) promise.error(isActive() ? error : staleMessage()));
		source.onComplete(function(value:T) {
			if (isActive()) promise.complete(value) else promise.error(staleMessage());
		});
		return promise.future;
	}

	function watchLibrary(library:AssetLibrary):Void {
		if (library == null || watchedListeners.exists(library)) return;
		for (existing in watched) if (existing == library) return;
		var listener = function():Void {
			if (isActive()) onChange.dispatch();
		};
		library.onChange.add(listener);
		watchedListeners.set(library, listener);
		watched.push(library);
	}

	function unwatchLibraries():Void {
		for (library in watched) {
			var listener = watchedListeners.get(library);
			if (listener != null) library.onChange.remove(listener);
			watchedListeners.remove(library);
		}
		watched = [];
	}

	function detachOwnerEventBridge():Void {
		if (!ownerEventBridgeAttached) return;
		onChange.remove(bridgeChangeToOwnerAssets);
		ownerEventBridgeAttached = false;
		bridgeChangeToOwnerAssets = null;
	}

	function isActive():Bool {
		if (retired) return false;
		try return context.proofSignature() == proofAtCreation catch (_:Dynamic) return false;
	}

	function ensureActive():Void if (!isActive()) throw staleMessage();

	function qualified(id:String):String return libraryName + ':' + id;

	function staleMessage():String
		return '[source-assets] Composite owner library proof changed while retained: ' + libraryName;

	static function failed<T>(error:Dynamic):Future<T> return cast Future.withError(error);
}
