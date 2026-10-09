package;

#if cpp
import flixel.FlxG;
import hxvlc.openfl.Location;
#end

/** Historical gameObjects.PsychVideoSprite over the shared owner video service.
 * The old constructor installs its destruction listener once. Changing the
 * public flag later does not retroactively add/remove that source listener. */
#if cpp
@:access(hxvlc.flixel.FlxInternalVideo)
#end
class NightmareVisionLegacyVideoSprite extends NightmareVisionVideoSprite {
	public static inline var looping:String = NightmareVisionVideoSprite.looping;
	public static inline var muted:String = NightmareVisionVideoSprite.muted;
	public static var heldVideos:Array<NightmareVisionLegacyVideoSprite> = [];
	static var ownerViews:Array<{state:Dynamic, root:String, refs:Int, videos:Array<NightmareVisionLegacyVideoSprite>}> = [];
	public var destroyOnUse:Bool;
	var heldPath:String = '';

	public function new(state:Dynamic, paths:Dynamic, destroyOnUse:Bool = true) {
		super(state, paths, 0, 0, false, false);
		this.destroyOnUse = destroyOnUse;
		heldVideos.push(this);
		forOwner(state, ownerRoot).push(this);
		#if cpp
		if (bitmap != null && destroyOnUse) bitmap.onEndReached.add(destroy);
		#end
	}

	#if cpp
	public override function load(location:Location, ?options:Array<String>):Bool {
		var accepted = super.load(location, options);
		if (accepted) heldPath = cast location;
		return accepted;
	}

	public function addCallback(name:String, callback:Void->Void):Void {
		if (callback == null || bitmap == null) return;
		switch (name) {
			case 'onEnd': bitmap.onEndReached.add(callback);
			case 'onStart': bitmap.onOpening.add(callback);
			case 'onFormat': bitmap.onFormatSetup.add(callback);
			default:
		}
	}

	// Legacy callbacks are decoder events, not modern synthetic completions.
	// In particular, load failure must not masquerade as an end event.
	override function finish(reason:String):Void {
		trace('[nightmare-vision-legacy-video] phase=end reason=' + reason + ' path=' + heldPath);
	}

	function setFocusEnabled(enabled:Bool):Void {
		if (bitmap == null || !FlxG.autoPause) return;
		if (enabled) {
			if (!FlxG.signals.focusGained.has(bitmap.onFocusGained)) FlxG.signals.focusGained.add(bitmap.onFocusGained);
			if (!FlxG.signals.focusLost.has(bitmap.onFocusLost)) FlxG.signals.focusLost.add(bitmap.onFocusLost);
		} else {
			FlxG.signals.focusGained.remove(bitmap.onFocusGained);
			FlxG.signals.focusLost.remove(bitmap.onFocusLost);
		}
	}

	public override function pause():Void {super.pause(); setFocusEnabled(false);}
	public override function resume():Void {super.resume(); setFocusEnabled(true);}
	#else
	public function addCallback(name:String, callback:Void->Void):Void {}
	public function pause():Void {}
	public function resume():Void {}
	#end

	public function restart(?options:Array<String>):Void {
		load(heldPath, options);
		play();
	}

	/** The historical method is explicitly empty in the source version. */
	public function initializeSkip():Void {}

	public static function globalPause():Void for (video in heldVideos.copy()) video.pause();
	public static function globalResume():Void for (video in heldVideos.copy()) video.resume();

	public static function forOwner(state:Dynamic, root:String):Array<NightmareVisionLegacyVideoSprite> {
		for (view in ownerViews) if (view.state == state && view.root == root) return view.videos;
		var videos:Array<NightmareVisionLegacyVideoSprite> = [];
		ownerViews.push({state:state, root:root, refs:0, videos:videos});
		return videos;
	}

	public static function retainOwner(state:Dynamic, root:String):Void {
		forOwner(state, root);
		for (view in ownerViews) if (view.state == state && view.root == root) view.refs++;
	}

	public static function releaseOwner(state:Dynamic, root:String):Void {
		for (view in ownerViews.copy()) if (view.state == state && view.root == root) {
			if (view.refs > 0) view.refs--;
			pruneOwnerView(view);
		}
	}

	static function pruneOwnerView(view:{state:Dynamic, root:String, refs:Int, videos:Array<NightmareVisionLegacyVideoSprite>}):Void {
		if (view.refs > 0) return;
		for (video in heldVideos) if (video.ownerState == view.state && video.ownerRoot == view.root) return;
		ownerViews.remove(view);
	}

	public static function replaceForOwner(state:Dynamic, root:String, value:Dynamic):Dynamic {
		if (!Std.isOfType(value, Array)) throw '[nightmare-vision-video-owner] Expected a video array';
		for (video in (cast value:Array<Dynamic>))
			if (video != null && (!Std.isOfType(video, NightmareVisionLegacyVideoSprite)
				|| video.ownerState != state || video.ownerRoot != root))
				throw '[nightmare-vision-video-owner] Cannot borrow another owner video';
		forOwner(state, root);
		for (view in ownerViews) if (view.state == state && view.root == root) view.videos = cast value;
		return value;
	}

	public override function destroy():Void {
		heldVideos.remove(this);
		for (view in ownerViews.copy()) if (view.state == ownerState && view.root == ownerRoot) {
			while (view.videos.remove(this)) {}
			pruneOwnerView(view);
		}
		heldPath = '';
		super.destroy();
	}
}
