package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.util.FlxTimer;
import HxcStoryMenuSpec.HxcStoryMenuSpecData;
import HxcStoryMenuSpec.HxcStoryMenuSpriteSpec;
#if sys
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

private typedef HxcStoryMenuModuleScope = {
	var path:String;
	var root:String;
	var identity:String;
	var global:Bool;
	var associatedSongs:Array<String>;
	var spec:HxcStoryMenuSpecData;
	var sprite:FlxSprite;
	var frameCallback:Dynamic;
	var timer:FlxTimer;
	var selectionStarted:Bool;
}

/**
	Native owner for structurally recognized HXC story-menu modules.

	The runtime loads only data plans produced by HxcCompat. It never instantiates
	a donor Module or evaluates its constructor/callback bodies. Assets, timers,
	and display objects remain attached to this StoryMenuState and its selected
	manifest roots for their full lifetime.
*/
class HxcStoryMenuRuntime {
	var owner:StoryMenuState;
	var scopes:Array<HxcStoryMenuModuleScope> = [];
	var rootSongs:Map<String, Array<String>> = new Map();
	var rootPriorityBySong:Map<String, Map<String, Int>> = new Map();
	var rootGlobal:Map<String, Bool> = new Map();
	var disposed:Bool = false;

	public function new(owner:StoryMenuState) {
		this.owner = owner;
		load();
	}

	/** Return true when a supported module owns the current week's transition. */
	public function handlesCurrentSelection():Bool {
		if (disposed || owner == null || !owner.hxcStoryMenuCanSelectCurrentWeek())
			return false;
		var levelId = owner.hxcStoryMenuCurrentLevelId();
		var songs = owner.hxcStoryMenuCurrentSongs();
		for (scope in selectedScopes(songs))
			if (scope.spec != null && HxcStoryMenuRouting.levelMatches(scope.spec.levelId, levelId))
				return true;
		return false;
	}

	/** Run the supported module's native equivalent of its update hook. */
	public function update():Void {
		if (disposed || owner == null || FlxG.state != owner)
			return;
		var levelId = owner.hxcStoryMenuCurrentLevelId();
		var songs = owner.hxcStoryMenuCurrentSongs();
		for (scope in selectedScopes(songs)) {
			if (scope == null || scope.spec == null
				|| !HxcStoryMenuRouting.levelMatches(scope.spec.levelId, levelId))
				continue;
			if (scope.sprite == null)
				createMenuSprite(scope);
			if (owner.hxcStoryMenuIsSelected() && !scope.selectionStarted)
				beginSelection(scope);
		}
	}

	/** Called when this StoryMenuState is destroyed or replaced. */
	public function dispose():Void {
		if (disposed)
			return;
		disposed = true;
		for (scope in scopes)
			clearScope(scope);
		scopes.resize(0);
		rootSongs = new Map();
		rootPriorityBySong = new Map();
		rootGlobal = new Map();
		owner = null;
	}

	/**
		Materialize the optional gameplay character helper from a module plan.
		The sprite is attached to the supplied PlayState, so normal state teardown
		owns its lifetime; the atlas and sound stay confined to the module root.
	*/
	public static function createCharacterHelper(state:Dynamic, assetRoot:Dynamic,
		rawSpec:Dynamic):Dynamic {
		if (state == null || rawSpec == null || assetRoot == null)
			return null;
		var root = HxcFreeplayRouting.normalizeRoot(Std.string(assetRoot));
		if (!isImportedRoot(root))
			return null;
		var spec:HxcStoryMenuSpriteSpec = cast rawSpec;
		if (!validSpriteSpec(spec))
			return null;
		var frames = HxcStateAssetScope.eventAtlas(root, spec.atlas, 'sparrow',
			'HXC story character helper');
		if (frames == null)
			return null;
		var camera:Dynamic = null;
		try camera = Reflect.getProperty(state, spec.camera == null ? 'camCutscene' : spec.camera)
		catch (_:Dynamic) {}
		if (camera == null)
			return null;

		var sprite = new FlxSprite(spec.x, spec.y);
		sprite.frames = frames;
		sprite.animation.addByPrefix(spec.animation, spec.prefix, spec.fps, false);
		sprite.scale.set(spec.scaleX, spec.scaleY);
		sprite.scrollFactor.set(0, 0);
		sprite.camera = cast camera;
		if (spec.selectedAlpha >= 0)
			sprite.alpha = spec.selectedAlpha;
		HxcCompatRuntime.setZIndex(sprite, spec.zIndex);
		var add = Reflect.field(state, 'add');
		if (add == null || !Reflect.isFunction(add)) {
			sprite.destroy();
			return null;
		}
		try {
			Reflect.callMethod(state, add, [sprite]);
		} catch (_:Dynamic) {
			sprite.destroy();
			return null;
		}
		for (activeCamera in FlxG.cameras.list)
			@:privateAccess activeCamera._fxFadeAlpha = 1;
		sprite.animation.play(spec.animation, false, false,
			spec.startFrame == null ? 0 : spec.startFrame);
		return sprite;
	}

	function load():Void {
		#if sys
		if (owner == null)
			return;
		var roots:Array<String> = [];
		addRoot(roots, 'assets/scripts', true);
		for (song in owner.hxcStoryMenuAllSongs())
			collectManifestRoots(roots, song);

		var paths:Array<String> = [];
		var pathRoots:Map<String, String> = new Map();
		for (root in roots) {
			if (!FileSystem.isDirectory(root))
				continue;
			var plan = HxcScriptDiscovery.discoverRoot(root, '');
			var modules = plan == null || plan.families == null ? null : plan.families.get('module');
			if (modules == null)
				continue;
			for (path in modules)
				if (path != null && paths.indexOf(path) < 0) {
					paths.push(path);
					pathRoots.set(path, HxcFreeplayRouting.normalizeRoot(root));
				}
		}
		paths.sort(Reflect.compare);
		for (path in paths)
			registerModule(path, pathRoots.get(path));
		#end
	}

	#if sys
	function addRoot(roots:Array<String>, root:String, global:Bool, ?song:String):Void {
		var key = HxcFreeplayRouting.normalizeRoot(root);
		if (key == '')
			return;
		if (roots.indexOf(key) < 0)
			roots.push(key);
		if (global || !rootGlobal.exists(key))
			rootGlobal.set(key, global);
		if (song != null)
			HxcFreeplayRouting.associateSong(rootSongs, key, song);
	}

	function collectManifestRoots(roots:Array<String>, song:String):Void {
		if (song == null || StringTools.trim(song) == '')
			return;
		var cleanSong = StringTools.trim(song);
		var manifestPath = 'assets/data/' + cleanSong.toLowerCase() + '/'
			+ CompatScriptManifest.FILE_NAME;
		if (!FNFAssets.exists(manifestPath))
			return;
		try {
			var manifest = CompatScriptManifest.parse(FNFAssets.getText(manifestPath));
			var ordered = CompatScriptManifest.rootsInPrecedence(manifest);
			for (index in 0...ordered.length) {
				var entry = ordered[index];
				if (entry == null || entry.path == null)
					continue;
				var root = HxcFreeplayRouting.normalizeRoot(entry.path);
				if (root == '' || !FileSystem.isDirectory(root))
					continue;
				addRoot(roots, root, false, cleanSong);
				setRootPriority(root, cleanSong, index + 1);
			}
		} catch (error:Dynamic) {
			trace('[hxc-story-menu-manifest-error] ' + manifestPath + ': ' + Std.string(error));
		}
	}

	function setRootPriority(root:String, song:String, priority:Int):Void {
		var rootKey = HxcFreeplayRouting.normalizeRoot(root);
		var songKey = HxcFreeplayRouting.normalizeSong(song);
		if (rootKey == '' || songKey == '')
			return;
		var priorities = rootPriorityBySong.get(songKey);
		if (priorities == null) {
			priorities = new Map<String, Int>();
			rootPriorityBySong.set(songKey, priorities);
		}
		var current = priorities.get(rootKey);
		if (current == null || priority < current)
			priorities.set(rootKey, priority);
	}

	function registerModule(path:String, root:String):Void {
		if (path == null || root == null || !FileSystem.exists(path))
			return;
		try {
			var result:Dynamic = HxcCompat.analyze(File.getContent(path), path);
			if (result == null || Reflect.field(result, 'kind') != 'module'
				|| Reflect.field(result, 'moduleSafe') != true
				|| Reflect.field(result, 'moduleInitializationSafe') != true)
				return;
			var rawSpec = Reflect.field(result, 'storyMenuSpec');
			if (rawSpec == null)
				return;
			var spec:HxcStoryMenuSpecData = cast rawSpec;
			if (!validPlan(spec))
				return;
			var rootKey = HxcFreeplayRouting.normalizeRoot(root);
			var scope:HxcStoryMenuModuleScope = {
				path: path,
				root: rootKey,
				identity: relativeModuleIdentity(path, rootKey),
				global: rootGlobal.exists(rootKey) && rootGlobal.get(rootKey) == true,
				associatedSongs: rootSongs.exists(rootKey) ? rootSongs.get(rootKey).copy() : [],
				spec: spec,
				sprite: null,
				frameCallback: null,
				timer: null,
				selectionStarted: false
			};
			// The donor constructor permanently caches these sounds. Resolve them at
			// module registration through the root-checked bounded sound cache.
			HxcCompatRuntime.cacheFunkinSound(rootKey, spec.selectionSound);
			HxcCompatRuntime.cacheFunkinSound(rootKey, spec.frameSound);
			scopes.push(scope);
		} catch (error:Dynamic) {
			trace('[hxc-story-menu-analyze-error] ' + path + ': ' + Std.string(error));
		}
	}
	#end

	function selectedScopes(songs:Array<String>):Array<HxcStoryMenuModuleScope> {
		var result:Array<HxcStoryMenuModuleScope> = [];
		for (scope in scopes) {
			if (scope == null || (!scope.global && !intersects(scope.associatedSongs, songs)))
				continue;
			var selected = true;
			for (candidate in scopes) {
				if (candidate == null || candidate == scope
					|| !HxcStoryMenuRouting.sameModuleIdentity(candidate.identity, scope.identity)
					|| (!candidate.global && !intersects(candidate.associatedSongs, songs)))
					continue;
				var ownPriority = rootPriority(scope.root, songs);
				var candidatePriority = rootPriority(candidate.root, songs);
				if (HxcStoryMenuRouting.candidateWins(candidatePriority, candidate.path,
					ownPriority, scope.path)) {
					selected = false;
					break;
				}
			}
			if (selected)
				result.push(scope);
		}
		return result;
	}

	function rootPriority(root:String, songs:Array<String>):Int {
		if (root == 'assets/scripts')
			return 0;
		var best = 1000000;
		if (songs != null)
			for (song in songs) {
				var priorities = rootPriorityBySong.get(HxcFreeplayRouting.normalizeSong(song));
				var value = priorities == null ? null : priorities.get(root);
				if (value != null && value < best)
					best = value;
			}
		return best;
	}

	function intersects(scopeSongs:Array<String>, songs:Array<String>):Bool {
		if (scopeSongs == null || songs == null)
			return false;
		for (scopeSong in scopeSongs)
			for (song in songs)
				if (HxcFreeplayRouting.normalizeSong(scopeSong) == HxcFreeplayRouting.normalizeSong(song))
					return true;
		return false;
	}

	function createMenuSprite(scope:HxcStoryMenuModuleScope):Void {
		var spec = scope.spec.menuSprite;
		if (!validSpriteSpec(spec))
			return;
		var frames = HxcStateAssetScope.eventAtlas(scope.root, spec.atlas, 'sparrow',
			'HXC story-menu module ' + scope.path);
		if (frames == null)
			return;
		var sprite = new FlxSprite(spec.x, spec.y);
		sprite.frames = frames;
		sprite.animation.addByPrefix(spec.animation, spec.prefix, spec.fps,
			spec.loop == true);
		sprite.scale.set(spec.scaleX, spec.scaleY);
		sprite.scrollFactor.set(0, 0);
		sprite.alpha = spec.idleAlpha;
		HxcCompatRuntime.setZIndex(sprite, spec.zIndex);
		var callback:Dynamic = function(_name:String, _frameNumber:Int, frameIndex:Int):Void {
			if (frameIndex == spec.frameSoundIndex && sprite.alpha == spec.frameSoundAlpha)
				playSound(scope.root, scope.spec.frameSound);
		};
		scope.sprite = sprite;
		scope.frameCallback = callback;
		try sprite.animation.onFrameChange.add(callback) catch (_:Dynamic) {}
		owner.hxcAddOwnedStorySprite(sprite);
		sprite.animation.play(spec.animation);
	}

	function beginSelection(scope:HxcStoryMenuModuleScope):Void {
		if (scope == null || scope.selectionStarted || scope.spec == null)
			return;
		scope.selectionStarted = true;
		if (scope.sprite != null) {
			scope.sprite.alpha = scope.spec.menuSprite.selectedAlpha;
			scope.sprite.animation.play(scope.spec.menuSprite.animation, true);
		}
		playSound(scope.root, scope.spec.selectionSound);
		var delay = scope.spec.transitionDelay;
		if (delay <= 0)
			finishSelection(scope);
		else {
			scope.timer = new FlxTimer().start(delay, function(_timer:FlxTimer):Void {
				scope.timer = null;
				finishSelection(scope);
			});
		}
	}

	function finishSelection(scope:HxcStoryMenuModuleScope):Void {
		if (disposed || owner == null || scope == null || owner != FlxG.state
			|| !owner.hxcStoryMenuIsSelected()
			|| owner.hxcStoryMenuCurrentLevelId() != scope.spec.levelId)
			return;
		if (scope.spec.stopCameraEffects)
			for (camera in FlxG.cameras.list)
				camera.stopFX();
		owner.hxcStartImportedStorySelection(scope.spec.songIndex);
	}

	function clearScope(scope:HxcStoryMenuModuleScope):Void {
		if (scope == null)
			return;
		if (scope.timer != null) {
			try scope.timer.cancel() catch (_:Dynamic) {}
			scope.timer = null;
		}
		if (scope.sprite != null) {
			if (scope.frameCallback != null)
				try scope.sprite.animation.onFrameChange.remove(scope.frameCallback) catch (_:Dynamic) {}
			if (owner != null)
				owner.hxcRemoveOwnedStorySprite(scope.sprite);
			else
				scope.sprite.destroy();
			scope.sprite = null;
		}
		scope.frameCallback = null;
	}

	static function playSound(root:String, key:String):Void {
		if (key == null || StringTools.trim(key) == '')
			return;
		var sound = HxcCompatRuntime.cacheFunkinSound(root, key);
		if (sound != null)
			try FlxG.sound.play(sound) catch (_:Dynamic) {}
	}

	static function validPlan(spec:HxcStoryMenuSpecData):Bool {
		return spec != null && spec.levelId != null && spec.levelId != ''
			&& spec.songIndex >= 0
			&& Math.isFinite(spec.transitionDelay)
			&& spec.transitionDelay >= 0 && validSpriteSpec(spec.menuSprite)
			&& spec.selectionSound != null && spec.selectionSound != ''
			&& spec.frameSound != null && spec.frameSound != ''
			&& (spec.characterHelper == null || validSpriteSpec(spec.characterHelper));
	}

	static function validSpriteSpec(spec:HxcStoryMenuSpriteSpec):Bool {
		return spec != null && safeAssetKey(spec.atlas) && spec.animation != null && spec.animation != ''
			&& spec.prefix != null && spec.prefix != '' && Math.isFinite(spec.fps) && spec.fps > 0
			&& Math.isFinite(spec.x) && Math.isFinite(spec.y)
			&& Math.isFinite(spec.scaleX) && Math.isFinite(spec.scaleY)
			&& spec.scaleX > 0 && spec.scaleY > 0 && Math.isFinite(spec.idleAlpha)
			&& Math.isFinite(spec.selectedAlpha) && spec.idleAlpha >= 0
			&& spec.idleAlpha <= 1 && spec.selectedAlpha >= 0 && spec.selectedAlpha <= 1;
	}

	static function safeAssetKey(value:String):Bool {
		if (value == null || StringTools.trim(value) == '' || value.length > 96)
			return false;
		return new EReg('^[A-Za-z0-9_./ -]+$', '').match(value)
			&& value.indexOf('..') < 0 && value.indexOf(':') < 0;
	}

	static function isImportedRoot(root:String):Bool {
		return root != null && root.startsWith(CompatScriptManifest.ROOT_PREFIX + '/')
			&& root.indexOf('..') < 0 && root.indexOf(':') < 0;
	}

	static function relativeModuleIdentity(path:String, root:String):String {
		#if sys
		if (path != null && root != null) {
			var fullPath = StringTools.replace(FileSystem.fullPath(path), '\\', '/');
			var fullRoot = StringTools.replace(FileSystem.fullPath(root), '\\', '/');
			if (fullPath.startsWith(fullRoot + '/'))
				return HxcStoryMenuRouting.moduleIdentity(fullPath.substr(fullRoot.length + 1));
		}
		#end
		return HxcStoryMenuRouting.moduleIdentity(HxcScriptDiscovery.stem(path));
	}
}
