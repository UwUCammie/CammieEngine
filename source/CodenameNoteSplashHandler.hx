package;

import flixel.FlxCamera;
import flixel.FlxG;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.graphics.frames.FlxAtlasFrames;
import haxe.io.Path;
using StringTools;

#if sys
import sys.FileSystem;
#end

private typedef CachedCodenameSplash = {
	var definition:CodenameSplashData;
	var frames:FlxAtlasFrames;
}

/** Shared owner-scoped runtime for Codename's `note.splash` selection. */
class CodenameNoteSplashHandler extends FlxTypedGroup<CodenameNoteSplash> {
	// Codename's Flags.MAX_SPLASHES default is 8; SplashHandler removes the
	// oldest rendered effect after adding each new one when this limit is passed.
	public static inline var MAX_ACTIVE_SPLASHES:Int = 8;
	public static inline var MAX_CACHED_STYLES:Int = 8;

	public final ownerRoot:String;
	final paths:CodenamePaths;
	final styles:Map<String, CachedCodenameSplash> = new Map();
	final styleOrder:Array<String> = [];
	final warned:Map<String, Bool> = new Map();
	var fallbackCameras:Array<FlxCamera>;

	public function new(ownerRoot:String) {
		super();
		this.ownerRoot = ownerRoot;
		paths = new CodenamePaths(ownerRoot);
	}

	/** True only for a definition inside the selected owner. */
	public function hasSplashDefinition(name:String):Bool
		return splashXmlPath(name) != null;

	/** Play the selected owner's XML-defined splash at one native receptor. */
	public function showSplash(name:String, receptor:Strumline.StrumNote,
		lineScale:Float, ?fallbackCameras:Array<FlxCamera>, ?sourceNote:Note):Bool {
		if (receptor == null) return false;
		if (fallbackCameras != null) this.fallbackCameras = fallbackCameras;
		var style = loadStyle(name);
		if (style == null) return false;
		var count = style.definition.animationCountForLane(receptor.ID);
		if (count <= 0) {
			diagnose(name, 'has no animation for strum ' + receptor.ID);
			return false;
		}
		var selected = style.definition.animationForLane(receptor.ID, FlxG.random.int(0, count - 1));
		if (selected == null) return false;

		var splash = new CodenameNoteSplash(style.definition, style.frames, selected,
			receptor.ID, receptor, lineScale, this.fallbackCameras);
		if (!splash.renderable) {
			splash.destroy();
			diagnose(name, 'could not find animation prefix "' + selected.prefix + '"');
			return false;
		}
		add(splash);
		while (members.length > MAX_ACTIVE_SPLASHES)
			removeSplash(members[0]);
		RuntimeSmokeHarness.markCodenameNoteSplashRendered(sourceNote, ownerRoot,
			name, style.definition.sprite, selected.prefix, receptor.ID, splash,
			members.indexOf(splash) >= 0);
		return true;
	}

	public function reportMissingSplash(name:String):Void
		diagnose(name, 'selected owner has no data/splashes definition');

	function loadStyle(name:String):Null<CachedCodenameSplash> {
		var key = normalizeName(name);
		if (key == null) {
			diagnose(name, 'invalid or unsafe splash name');
			return null;
		}
		if (styles.exists(key)) {
			touchStyle(key);
			return styles.get(key);
		}
		var xmlPath = splashXmlPath(key);
		if (xmlPath == null) {
			diagnose(name, 'selected owner has no data/splashes definition');
			return null;
		}
		try {
			var definition = CodenameSplashData.parse(FNFAssets.getText(xmlPath));
			if (definition == null) {
				diagnose(name, 'invalid Codename splash XML');
				return null;
			}
			// Codename's note splash format uses a Sparrow atlas. Resolve both
			// files through the selected owner's Paths facade; no native or other
			// owner's same-named atlas can fill a missing dependency.
			var frames = paths.getSparrowAtlas(definition.sprite);
			if (frames == null || frames.frames == null || frames.frames.length == 0) {
				diagnose(name, 'missing or empty owner Sparrow atlas for "' + definition.sprite + '"');
				return null;
			}
			var cached:CachedCodenameSplash = {definition:definition, frames:frames};
			// The style cache outlives any one rendered splash. Keep the atlas
			// graphic alive while this cache entry points at its frame collection;
			// each transient FlxSprite releases its own graphic reference on destroy.
			retainStyle(cached);
			styles.set(key, cached);
			styleOrder.push(key);
			while (styleOrder.length > MAX_CACHED_STYLES) {
				var evicted = styleOrder[0];
				releaseStyle(evicted);
			}
			return cached;
		} catch (error:Dynamic) {
			diagnose(name, 'could not load selected-owner splash assets: ' + Std.string(error));
			return null;
		}
	}

	function retainStyle(style:CachedCodenameSplash):Void {
		if (style != null && style.frames != null && style.frames.parent != null)
			style.frames.parent.incrementUseCount();
	}

	function releaseStyle(key:String):Void {
		var cached = styles.get(key);
		styles.remove(key);
		styleOrder.remove(key);
		if (cached == null || cached.frames == null) return;
		var parent = cached.frames.parent;
		if (parent != null && !parent.isDestroyed)
			parent.decrementUseCount();
	}

	function splashXmlPath(name:String):Null<String> {
		var key = normalizeName(name);
		if (key == null) return null;
		var relative = 'data/splashes/' + key
			+ (key.toLowerCase().endsWith('.xml') ? '' : '.xml');
		#if sys
		var resolved = CodenameScriptDiscovery.scopedResolution(ownerRoot, relative);
		if (resolved.relative == null) return null;
		var path = Path.join([ownerRoot, resolved.relative]);
		return FileSystem.exists(path) && !FileSystem.isDirectory(path)
			&& CodenameScriptDiscovery.withinRoot(ownerRoot, path) ? path : null;
		#else
		return null;
		#end
	}

	static function normalizeName(name:String):Null<String> {
		if (name == null) return null;
		var key = StringTools.replace(StringTools.trim(name), '\\', '/');
		if (key.startsWith('./') || !CodenameScriptDiscovery.safeRelativeName(key)) return null;
		return key;
	}

	function touchStyle(key:String):Void {
		styleOrder.remove(key);
		styleOrder.push(key);
	}

	function diagnose(name:String, reason:String):Void {
		var key = Std.string(name) + '\n' + reason;
		if (warned.exists(key)) return;
		warned.set(key, true);
		trace('[codename-note-splash] ' + reason + ' for "' + Std.string(name) + '"');
	}

	function removeSplash(splash:CodenameNoteSplash):Void {
		if (splash == null) return;
		remove(splash, true);
		splash.destroy();
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		var index = 0;
		while (index < members.length) {
			var splash = members[index];
			if (splash == null || !splash.alive || !splash.exists) {
				if (splash != null) {
					remove(splash, true);
					splash.destroy();
				}
			} else index++;
		}
	}

	override public function destroy():Void {
		for (splash in members.copy()) removeSplash(splash);
		for (key in styleOrder.copy()) releaseStyle(key);
		styles.clear();
		styleOrder.resize(0);
		warned.clear();
		fallbackCameras = null;
		super.destroy();
	}
}
