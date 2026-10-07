package;

import openfl.Lib;
import openfl.display.Sprite;
import openfl.display.Stage;
import PsychAchievementInfo;
import PsychAchievementPopup.PsychAchievementPopup;
import PsychAchievementPopup.PsychAchievementPopupAssets;
import PsychAchievementPopup.PsychAchievementPopupHost;
import PsychAchievementsHost.PsychAchievementSource;
import PsychAchievementsHost.PsychAchievementsHost;
#if sys
import sys.FileSystem;
#end

using StringTools;

/** Immutable owner-scoped inputs copied when gameplay first adopts a Psych owner.
 * Callbacks must capture owner services, never a short-lived gameplay state. */
typedef PsychAchievementsRuntimeContext = {
	/** Base source first, followed by the caller's authenticated order. */
	var sources:Array<PsychAchievementSource>;
	var readText:String->Null<String>;
	var report:String->Void;
	var playConfirmSound:(String, Float)->Void;
	/** Key null/base assets with the empty string; non-null keys are source.mod labels. */
	var assetFacades:Map<String, PsychAchievementPopupAssets>;
	var phrase:String->String->String;
	var antialiasing:Void->Bool;
	var stage:Stage;
	var game:Sprite;
}

/** Per-import Psych achievements and popups shared by same-owner gameplay states. */
@:keep
class PsychAchievementsRuntime {
	static var owners:Map<String, PsychAchievementsRuntime> = new Map();

	public final ownerRoot:String;
	public final service:PsychAchievements;
	public var released(default, null):Bool = false;
	public var popupCount(get, never):Int;

	var ownerKey:String;
	var paths:Dynamic;
	var ownerSave:CodenameOwnerSaveData;
	var readTextCallback:String->Null<String>;
	var reportCallback:String->Void;
	var soundCallback:(String, Float)->Void;
	var phraseCallback:String->String->String;
	var antialiasing:Void->Bool;
	var capturedStage:Stage;
	var capturedGame:Sprite;
	var authorizedSources:Array<PsychAchievementSource> = [];
	var authorizedSourcePaths:Map<String, PsychAchievementSource> = new Map();
	var assetFacades:Map<String, PsychAchievementPopupAssets> = new Map();
	var popups:Array<PsychAchievementPopup> = [];

	/** Reuse the captured context without rebuilding paths or probing JSON for
	 * every Lua/reflection scope in the same imported owner. */
	public static function lookup(ownerRoot:String):PsychAchievementsRuntime {
		var root = normalizeOwner(ownerRoot);
		if (root == '') return null;
		var runtime = owners.get(ownerKeyFor(root));
		return runtime != null && !runtime.released ? runtime : null;
	}

	/** Called by gameplay with the validated import owner and its private save view.
	 * `retainOwners` defines the wider active-provider set; adopting one owner never
	 * retires a different provider which is still needed by another script scope. */
	public static function adopt(ownerRoot:String, paths:Dynamic, ownerSave:CodenameOwnerSaveData,
		context:PsychAchievementsRuntimeContext):PsychAchievementsRuntime {
		var root = normalizeOwner(ownerRoot);
		if (root == '' || paths == null || ownerSave == null)
			throw '[psych-achievements-runtime] A validated owner, Paths facade, and private save are required';
		var pathsRoot = '';
		try pathsRoot = normalizeOwner(PsychOwnerPaths.ownerRoot(paths)) catch (error:Dynamic)
			throw '[psych-achievements-runtime] Could not read the captured owner Paths root: ' + Std.string(error);
		if (pathsRoot == '' || ownerKeyFor(pathsRoot) != ownerKeyFor(root))
			throw '[psych-achievements-runtime] Captured Paths owner does not match the selected import';

		var key = ownerKeyFor(root);
		var existing = owners.get(key);
		if (existing != null && !existing.released) return existing;
		var runtime = new PsychAchievementsRuntime(root, key, paths, ownerSave, context);
		owners.set(key, runtime);
		try runtime.initialize() catch (error:Dynamic) {
			runtime.release();
			throw error;
		}
		return runtime;
	}

	/** Retain only owners proven by the next chart's validated import manifests. */
	public static function retainOwners(roots:Array<String>):Void {
		if (roots == null) throw '[psych-achievements-runtime] An explicit retained-owner set is required';
		var keep:Map<String, Bool> = new Map();
		for (value in roots) {
			var root = normalizeOwner(value);
			if (root == '') throw '[psych-achievements-runtime] Refused an unvalidated retained owner';
			keep.set(ownerKeyFor(root), true);
		}
		var retire:Array<PsychAchievementsRuntime> = [];
		for (key => runtime in owners)
			if (runtime != null && !keep.exists(key)) retire.push(runtime);
		for (runtime in retire) runtime.release();
	}

	public static function releaseAll():Void {
		var retire:Array<PsychAchievementsRuntime> = [];
		for (runtime in owners) if (runtime != null) retire.push(runtime);
		for (runtime in retire) runtime.release();
	}

	function new(ownerRoot:String, ownerKey:String, paths:Dynamic, ownerSave:CodenameOwnerSaveData,
		context:PsychAchievementsRuntimeContext) {
		validateContext(context);
		this.ownerRoot = ownerRoot;
		this.ownerKey = ownerKey;
		this.paths = paths;
		this.ownerSave = ownerSave;
		readTextCallback = context.readText;
		reportCallback = context.report;
		soundCallback = context.playConfirmSound;
		phraseCallback = context.phrase;
		antialiasing = context.antialiasing;
		capturedStage = context.stage;
		capturedGame = context.game;
		for (label in context.assetFacades.keys()) {
			var assets = context.assetFacades.get(label);
			if (label == null || !validModLabel(label == '' ? null : label) || !validateAssetFacade(assets))
				throw '[psych-achievements-runtime] Invalid owner achievement asset facade: ' + label;
			assetFacades.set(label, assets);
		}
		if (!assetFacades.exists(''))
			throw '[psych-achievements-runtime] Base owner achievement assets are required';
		setSources(context.sources);
		service = new PsychAchievements(ownerRoot, ownerSave, makeServiceHost());
	}

	function initialize():Void {
		ensureAlive();
		service.init();
		service.load();
		service.reloadList();
	}

	function validateContext(context:PsychAchievementsRuntimeContext):Void {
		if (context == null || context.sources == null || context.readText == null || context.report == null
			|| context.playConfirmSound == null || context.assetFacades == null || context.phrase == null
			|| context.stage == null || context.game == null)
			throw '[psych-achievements-runtime] Missing captured owner source, audio, or popup services';
	}

	function setSources(sources:Array<PsychAchievementSource>):Void {
		authorizedSources = [];
		authorizedSourcePaths = new Map();
		var seen:Map<String, Bool> = new Map();
		for (source in sources) {
			if (source == null || source.path == null || StringTools.trim(source.path) == '') continue;
			var path = resolveOwnedSource(source.path);
			if (path == null) {
				report('Refused achievement JSON outside the captured owner: ' + source.path);
				continue;
			}
			if (source.mod != null && !validModLabel(source.mod)) {
				report('Refused achievement source with an unsafe mod label: ' + source.mod);
				continue;
			}
			var modKey = source.mod == null ? '' : source.mod;
			if (!assetFacades.exists(modKey)) {
				report('Refused achievement source without an authorized asset facade: ' + modKey);
				continue;
			}
			var key = sourcePathKey(path);
			if (seen.exists(key)) continue;
			seen.set(key, true);
			var accepted:PsychAchievementSource = {path:path, mod:source.mod};
			authorizedSources.push(accepted);
			authorizedSourcePaths.set(key, accepted);
		}
	}

	function makeServiceHost():PsychAchievementsHost {
		return {
			ownerActive:ownerActive,
			paths:paths,
			achievementSources:achievementSources,
			readText:readAuthorizedText,
			report:report,
			playConfirmSound:function(key:String, volume:Float):Void {
				ensureAlive(); soundCallback(key, volume);
			},
			nowMillis:function():Int return Lib.getTimer(),
			showingPopups:function():Bool {ensureAlive(); return popups.length > 0;},
			showPopup:showPopup
		};
	}

	function achievementSources():Array<PsychAchievementSource> {
		ensureAlive();
		return [for (source in authorizedSources) {path:source.path, mod:source.mod}];
	}

	function readAuthorizedText(path:String):Null<String> {
		ensureAlive();
		var resolved = resolveOwnedSource(path);
		if (resolved == null) throw '[psych-achievements-runtime] Refused to read outside the captured owner';
		var source = authorizedSourcePaths.get(sourcePathKey(resolved));
		if (source == null) throw '[psych-achievements-runtime] Refused an unregistered achievement JSON path';
		return readTextCallback(source.path);
	}

	function resolveOwnedSource(path:String):Null<String> {
		// Captured Psych Paths commonly returns an absolute filesystem path.
		// Accept it only when it resolves to a real file under this exact owner.
		#if sys
		if (path != null && FileSystem.exists(path) && !FileSystem.isDirectory(path)
			&& PsychOwnerAssetPath.withinOwner(ownerRoot, path)) {
			try {
				return FileSystem.fullPath(path);
			} catch (_:Dynamic) {
				return null;
			}
		}
		#end
		var clean = PsychOwnerAssetPath.cleanId(path);
		if (clean == null) return null;
		var result = PsychOwnerAssetPath.resolve(ownerRoot, clean);
		if (result == null || !result.owned || result.blocked || result.unavailable || result.path == null) return null;
		#if sys
		if (!FileSystem.exists(result.path) || FileSystem.isDirectory(result.path)
			|| !PsychOwnerAssetPath.withinOwner(ownerRoot, result.path)) return null;
		#end
		return result.path;
	}

	function showPopup(id:String, info:PsychAchievementInfo, endFunc:Void->Void):Void {
		ensureAlive();
		for (popup in popups.copy()) if (popup != null) popup.intendedY += 150;
		var popupHost:PsychAchievementPopupHost = {
			ownerRoot:ownerRoot,
			assetsForAchievementMod:assetsForAchievementMod,
			antialiasing:antialiasing,
			phrase:function(key:String, fallback:String):String return phraseCallback(key, fallback),
			stage:capturedStage,
			game:capturedGame,
			now:function():Float return Lib.getTimer(),
			ownerActive:ownerActive,
			registerPopup:registerPopup,
			unregisterPopup:unregisterPopup
		};
		new PsychAchievementPopup(id, endFunc, info, popupHost);
	}

	function assetsForAchievementMod(mod:Null<String>):PsychAchievementPopupAssets {
		ensureAlive();
		var label = mod == null ? '' : mod;
		if (mod != null && !validModLabel(mod))
			throw '[psych-achievements-runtime] Refused popup assets for an unsafe mod label';
		var assets = assetFacades.get(label);
		if (assets == null) throw '[psych-achievements-runtime] No owner-local achievement assets for mod: ' + label;
		return assets;
	}

	function registerPopup(popup:PsychAchievementPopup):Void {
		ensureAlive();
		if (popup != null && popups.indexOf(popup) < 0) popups.push(popup);
	}

	function unregisterPopup(popup:PsychAchievementPopup):Void {
		if (popup != null) popups.remove(popup);
	}

	function ownerActive():Bool return !released && owners.get(ownerKey) == this;

	function report(message:String):Void {
		if (reportCallback == null) return;
		try reportCallback(message) catch (error:Dynamic)
			trace('[psych-achievements-runtime-report-error] ' + ownerRoot + ': ' + Std.string(error));
	}

	public function release():Void {
		if (released) return;
		released = true;
		for (popup in popups.copy()) if (popup != null) popup.destroy();
		popups.resize(0);
		service.release();
		if (owners.get(ownerKey) == this) owners.remove(ownerKey);
		ownerSave = null;
		paths = null;
		readTextCallback = null;
		reportCallback = null;
		soundCallback = null;
		phraseCallback = null;
		capturedStage = null;
		capturedGame = null;
		assetFacades = new Map();
		authorizedSources.resize(0);
		authorizedSourcePaths = new Map();
	}

	function get_popupCount():Int return popups.length;

	function ensureAlive():Void {
		if (released || owners.get(ownerKey) != this)
			throw '[psych-achievements-runtime] This imported owner runtime has been released';
	}

	static function normalizeOwner(value:String):String
		return PsychOwnerAssetPath.normalizeOwner(value);

	static function ownerKeyFor(root:String):String
		return CompatScriptManifest.destinationKey(root);

	static function sourcePathKey(path:String):String {
		#if windows
		return path.toLowerCase();
		#else
		return path;
		#end
	}

	static function validModLabel(value:Null<String>):Bool {
		if (value == null) return true;
		var label = StringTools.trim(value);
		return label != '' && label != '.' && label != '..'
			&& label.indexOf('/') < 0 && label.indexOf('\\') < 0
			&& label.indexOf(':') < 0 && label.indexOf(String.fromCharCode(0)) < 0;
	}

	static function validateAssetFacade(assets:PsychAchievementPopupAssets):Bool
		return assets != null && assets.fileExists != null && assets.image != null && assets.font != null;
}
