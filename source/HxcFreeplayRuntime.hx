package;

import hscript.Interp;
import hscript.ParserEx;
import PluginManager.HscriptGlobals;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

private typedef HxcFreeplayScope = {
	var path:String;
	var identity:String;
	var root:String;
	var global:Bool;
	var associatedSongs:Array<String>;
	var interp:Interp;
	var names:Array<String>;
	/** Keep the translated program from being analyzed/read a second time. */
	var generatedHscript:String;
}

/**
	Small host for HXC module callbacks which belong to the native Freeplay
	state rather than PlayState. It deliberately loads only generated callbacks
	which passed HxcCompat's safety gate; donor constructors/classes are never
	instantiated here.
*/
class HxcFreeplayRuntime {
	static var activeRuntimes:Array<HxcFreeplayRuntime> = [];
	var owner:FreeplayState;
	var scopes:Array<HxcFreeplayScope> = [];
	// ModuleHandler lookups are scoped to the destination root or imported
	// namespace that owns the caller. A flat name map lets two donors silently
	// call one another's modules when they reuse a class name.
	var namesByRoot:Map<String, Map<String, Dynamic>> = new Map<String, Map<String, Dynamic>>();
	var rootSongs:Map<String, Array<String>> = new Map<String, Array<String>>();
	var rootGlobal:Map<String, Bool> = new Map<String, Bool>();
	// A song can retain more than one imported root after a repair/reimport.
	// Keep the manifest's selected-root precedence per song so duplicate HXC
	// modules do not dispatch twice merely because both namespaces are present.
	var rootPriorityBySong:Map<String, Map<String, Int>> = new Map<String, Map<String, Int>>();
	var destinationRoot:String = '';
	var seenPaths:Map<String, Bool> = new Map<String, Bool>();
	var loaded:Bool = false;

	public function new(owner:FreeplayState) {
		this.owner = owner;
		activeRuntimes.push(this);
		load();
	}

	/** Resolve a sibling module only inside the imported state caller's root. */
	public static function moduleProxyForRoot(root:String, name:Dynamic):Dynamic {
		var selectedRoot = HxcFreeplayRouting.normalizeRoot(root);
		if (selectedRoot == '' || name == null)
			return null;
		for (runtime in activeRuntimes) {
			if (runtime == null || runtime.owner == null)
				continue;
			var proxy = runtime.moduleProxyFromRoot(selectedRoot, name);
			if (proxy != null)
				return proxy;
		}
		return null;
	}

	/** Dispatch one native Freeplay lifecycle payload to generated HXC modules. */
	public function dispatch(callback:String, payload:Dynamic):Void {
		if (callback == null || callback == '')
			return;
		var selectedSong = HxcFreeplayRouting.selectedSong(payload);
		for (scope in scopes) {
			if (scope == null || scope.interp == null)
				continue;
			if (!HxcFreeplayRouting.scopeMatches(scope.global, scope.associatedSongs, selectedSong))
				continue;
			#if sys
			if (!scopeOwnsIdentity(scope, selectedSong))
				continue;
			#end
			var selected:String = null;
			for (candidate in EngineCompat.callbackNames(callback))
				if (scope.interp.variables.exists(candidate)) {
					selected = candidate;
					break;
				}
			if (selected == null)
				continue;
			var method = scope.interp.variables.get(selected);
			if (method == null)
				continue;
			var args = EngineCompat.callbackArguments(callback, selected, [payload], true);
			var previousAssetRoot = owner == null ? '' : owner.hxcPushAssetScope(scope.root);
			// smoke-only attribution: one section per scope so a slow imported
			// module can be named from a frame_stats line
			var scopeMark:Float = RuntimeSmokeHarness.enabled() ? haxe.Timer.stamp() : 0.0;
			try {
				switch (args.length) {
					case 0: method();
					case 1: method(args[0]);
					case 2: method(args[0], args[1]);
					case 3: method(args[0], args[1], args[2]);
					default: method(args[0], args[1], args[2], args[3]);
				}
				} catch (error:Dynamic) {
				trace('[hxc-freeplay-error] ' + callback + ' (' + scope.path + '): ' + Std.string(error));
			}
			if (scopeMark > 0)
				RuntimeSmokeHarness.profileSection('hxc:' + HxcScriptDiscovery.stem(scope.path) + ':' + scope.root.substr(-8),
					haxe.Timer.stamp() - scopeMark);
			if (owner != null)
				owner.hxcPopAssetScope(previousAssetRoot);
		}
	}

	public function dispose():Void {
		activeRuntimes.remove(this);
		for (scope in scopes)
			if (scope != null && scope.interp != null)
				scope.interp.variables.clear();
		scopes.resize(0);
		namesByRoot = new Map<String, Map<String, Dynamic>>();
		rootSongs = new Map<String, Array<String>>();
		rootGlobal = new Map<String, Bool>();
		rootPriorityBySong = new Map<String, Map<String, Int>>();
		destinationRoot = '';
		seenPaths = new Map<String, Bool>();
		owner = null;
		loaded = false;
	}

	function load():Void {
		if (loaded)
			return;
		loaded = true;
		#if sys
		var profileLoad = RuntimeSmokeHarness.enabled();
		var profileMark = profileLoad ? haxe.Timer.stamp() : 0.0;
		var roots:Array<String> = [];
		destinationRoot = HxcFreeplayRouting.normalizeRoot('assets/scripts');
		addRoot(roots, destinationRoot, true);
		collectManifestRoots(roots);
		if (profileLoad) {
			var now = haxe.Timer.stamp();
			RuntimeSmokeHarness.profileSection('fp-hxc-manifests', now - profileMark);
			profileMark = now;
		}
		var modulePaths:Array<String> = [];
		var moduleRoots:Map<String, String> = new Map<String, String>();
		for (root in roots) {
			if (root == null || !FileSystem.isDirectory(root))
				continue;
			var rootKey = HxcFreeplayRouting.normalizeRoot(root);
			var plan = HxcScriptDiscovery.discoverRoot(root, '');
			var family = plan.families.get('module');
			if (family != null)
				for (path in family)
					if (modulePaths.indexOf(path) < 0) {
						modulePaths.push(path);
						moduleRoots.set(path, rootKey);
					}
		}
		if (profileLoad) {
			var now = haxe.Timer.stamp();
			RuntimeSmokeHarness.profileSection('fp-hxc-discovery', now - profileMark);
			profileMark = now;
		}
		// Register all names before executing any generated module. This mirrors
		// PlayState's sibling-module routing and keeps load order deterministic,
		// while retaining the manifest root on every scope.
		for (path in modulePaths)
			registerModule(path, moduleRoots.get(path));
		if (profileLoad) {
			var now = haxe.Timer.stamp();
			RuntimeSmokeHarness.profileSection('fp-hxc-translation', now - profileMark);
			profileMark = now;
		}
		for (path in modulePaths)
			loadModule(path);
		if (profileLoad)
			RuntimeSmokeHarness.profileSection('fp-hxc-execution', haxe.Timer.stamp() - profileMark);
		#end
	}

	#if sys
	function addRoot(roots:Array<String>, root:String, global:Bool,
		?song:String):Void {
		var normalized = HxcFreeplayRouting.normalizeRoot(root);
		if (normalized == '')
			return;
		if (roots.indexOf(normalized) < 0)
			roots.push(normalized);
		if (global || !rootGlobal.exists(normalized))
			rootGlobal.set(normalized, global);
		if (song != null)
			HxcFreeplayRouting.associateSong(rootSongs, normalized, song);
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
		var existing = priorities.get(rootKey);
		if (existing == null || priority < existing)
			priorities.set(rootKey, priority);
	}

	function rootPriority(root:String, song:String):Int {
		var rootKey = HxcFreeplayRouting.normalizeRoot(root);
		if (rootKey == destinationRoot)
			return 0;
		var songKey = HxcFreeplayRouting.normalizeSong(song);
		var priorities = rootPriorityBySong.get(songKey);
		if (priorities == null)
			return 1000000;
		var value = priorities.get(rootKey);
		return value == null ? 1000000 : value;
	}

	/** A selected song's manifest owner shadows a same-named fallback module. */
	function scopeOwnsIdentity(scope:HxcFreeplayScope, selectedSong:String):Bool {
		if (scope == null || scope.identity == null || scope.identity == '')
			return true;
		var ownPriority = rootPriority(scope.root, selectedSong);
		for (candidate in scopes) {
			if (candidate == null || candidate == scope || candidate.identity != scope.identity
				|| !HxcFreeplayRouting.scopeMatches(candidate.global, candidate.associatedSongs, selectedSong))
				continue;
			var candidatePriority = rootPriority(candidate.root, selectedSong);
			if (candidatePriority < ownPriority
				|| (candidatePriority == ownPriority && candidate.path != null
					&& scope.path != null && Reflect.compare(candidate.path, scope.path) < 0))
				return false;
		}
		return true;
	}

	function collectManifestRoots(roots:Array<String>):Void {
		if (owner == null || FreeplayState.currentSongList == null)
			return;
		for (song in FreeplayState.currentSongList) {
			if (song == null || song.name == null)
				continue;
			var songKey = HxcFreeplayRouting.normalizeSong(song.name);
			var manifestPath = 'assets/data/' + song.name.toLowerCase() + '/'
				+ CompatScriptManifest.FILE_NAME;
			if (!FNFAssets.exists(manifestPath))
				continue;
			try {
				var manifest = CompatScriptManifest.parse(FNFAssets.getText(manifestPath));
				if (manifest == null || manifest.roots == null)
					continue;
				var orderedRoots = CompatScriptManifest.rootsInPrecedence(manifest);
				for (rootIndex in 0...orderedRoots.length) {
					var entry = orderedRoots[rootIndex];
					if (entry == null || entry.path == null)
						continue;
					var normalized = HxcFreeplayRouting.normalizeRoot(entry.path);
					if (normalized == '' || !FileSystem.isDirectory(normalized))
						continue;
					addRoot(roots, normalized, false, songKey);
					// Priority zero is reserved for native assets/scripts; the
					// selected manifest root is therefore the first foreign rank.
					setRootPriority(normalized, songKey, rootIndex + 1);
				}
			} catch (error:Dynamic) {
				trace('[hxc-freeplay-manifest-error] ' + manifestPath + ': ' + Std.string(error));
			}
		}
	}

	function registerModule(path:String, root:String):Void {
		if (path == null || seenPaths.exists(path) || !FileSystem.exists(path))
			return;
		seenPaths.set(path, true);
		try {
			var result = HxcCompat.analyze(File.getContent(path), path);
			// Debug hook: DUMP_GENERATED_HXC_FREEPLAY=<dir> writes each translated
			// freeplay module program which passed the safety gate, mirroring
			// PlayState's DUMP_GENERATED_HXC, so headless runs can be audited.
			var dumpDir = Sys.environment().get('DUMP_GENERATED_HXC_FREEPLAY');
			if (dumpDir != null && StringTools.trim(dumpDir) != '') {
				try {
					if (!FileSystem.exists(dumpDir))
						FileSystem.createDirectory(dumpDir);
					var safeName = StringTools.replace(path, '/', '_');
					safeName = StringTools.replace(safeName, '\\', '_');
					File.saveContent(dumpDir + '/' + safeName + '.generated.hscript',
						(result == null || result.generatedHscript == null ? '' : result.generatedHscript)
						+ '\n// registered: ' + (result == null ? 'null' : Std.string(result.kind == 'module'
							&& result.moduleInitializationSafe)) + '\n');
				} catch (_:Dynamic) {}
			}
			if (result == null || result.kind != 'module' || !result.moduleInitializationSafe)
				return;
			var hasFreeplay = false;
			for (callback in result.callbackAdapters)
				if (callback != null && callback.safe
					&& (callback.canonicalName == 'difficultySwitch' || callback.canonicalName == 'capsuleSelected'
						|| callback.canonicalName == 'subStateOpenEnd' || callback.canonicalName == 'update'
						|| callback.canonicalName == 'stateChangeEnd'))
					hasFreeplay = true;
			if (!hasFreeplay || result.generatedHscript == null
				|| result.generatedHscript.trim() == '')
				return;
			var rootKey = HxcFreeplayRouting.normalizeRoot(root);
			var associatedSongs = rootSongs.get(rootKey);
			var scope:HxcFreeplayScope = {
				path: path,
				identity: HxcScriptDiscovery.normalizeToken(HxcScriptDiscovery.stem(path)),
				root: rootKey,
				global: rootGlobal.exists(rootKey) && rootGlobal.get(rootKey) == true,
				associatedSongs: associatedSongs == null ? [] : associatedSongs.copy(),
				interp: null,
				generatedHscript: result.generatedHscript,
				names: [
					HxcScriptDiscovery.stem(path),
					result.identifier,
					result.className
				]
			};
			scopes.push(scope);
			var scopedNames = namesByRoot.get(rootKey);
			if (scopedNames == null) {
				scopedNames = new Map<String, Dynamic>();
				namesByRoot.set(rootKey, scopedNames);
			}
			for (name in scope.names)
				if (name != null && name.trim() != '')
					scopedNames.set(HxcScriptDiscovery.normalizeToken(name), scope);
		} catch (error:Dynamic) {
			trace('[hxc-freeplay-analyze-error] ' + path + ': ' + Std.string(error));
		}
	}

	function loadModule(path:String):Void {
		var scope:HxcFreeplayScope = null;
		for (candidate in scopes)
			if (candidate != null && candidate.path == path) {
				scope = candidate;
				break;
			}
		if (scope == null)
			return;
		try {
			var generated = scope.generatedHscript;
			if (generated == null || generated.trim() == '')
				return;
			var profileModule = RuntimeSmokeHarness.enabled();
			var profileMark = profileModule ? haxe.Timer.stamp() : 0.0;
			var profileName = HxcScriptDiscovery.stem(path);
			var parser = new ParserEx();
			var program = parser.parseString(generated);
			if (profileModule) {
				var now = haxe.Timer.stamp();
				RuntimeSmokeHarness.profileSection('fp-hxc-parse:' + profileName, now - profileMark);
				profileMark = now;
			}
			var interp = PluginManager.createSimpleInterp();
			seedInterpreter(interp, scope);
			interp.execute(program);
			if (profileModule)
				RuntimeSmokeHarness.profileSection('fp-hxc-run:' + profileName,
					haxe.Timer.stamp() - profileMark);
			scope.interp = interp;
		} catch (error:Dynamic) {
			trace('[hxc-freeplay-load-error] ' + path + ': ' + Std.string(error));
			scopes.remove(scope);
		}
	}

	function seedInterpreter(interp:Interp, scope:HxcFreeplayScope):Void {
		interp.variables.set('currentFreeplayState', owner);
		interp.variables.set('hxcFreeplayState', function() return owner);
		// Freeplay modules use the same global spelling as donor HXC.  Keep the
		// resolver explicit so generated callbacks cannot reach an arbitrary state.
		interp.variables.set('FlxG', HscriptGlobals);
		// HXC module media calls resolve inside this module's selected manifest
		// root before falling back to native engine assets.
		interp.variables.set('hxcAssetRoot', scope == null ? '' : scope.root);
		interp.variables.set('Paths', HxcStateAssetScope.paths(scope == null ? '' : scope.root));
		interp.variables.set('hxcFreeplayPlaySound', HxcCompatRuntime.freeplayPlaySound);
		interp.variables.set('hxcFreeplayPlayMusic', HxcCompatRuntime.freeplayPlayMusic);
		interp.variables.set('FreeplayState', FreeplayState);
		interp.variables.set('PlayState', PlayState);
		interp.variables.set('hxcCoalesce', HxcCompatRuntime.hxcCoalesce);
		interp.variables.set('hxcMap', HxcCompatRuntime.hxcMap);
		interp.variables.set('hxcGetModule', function(name:Dynamic) return moduleProxy(scope, name));
		// Each Freeplay module retains the manifest root which owns it. State
		// factories therefore cannot see a sibling import's states, while the
		// explicit native aliases remain available through the same resolver.
		interp.variables.set('hxcStateInit', function(name:Dynamic):Dynamic
			return HxcStateFactory.stateInit(scope == null ? '' : scope.root, name));
		interp.variables.set('hxcSubStateInit', function(name:Dynamic):Dynamic
			return HxcStateFactory.subStateInit(scope == null ? '' : scope.root, name));
		interp.variables.set('hxcStateFactory', function(name:Dynamic, ?args:Array<Dynamic>):Dynamic
			return HxcStateFactory.stateFactory(scope == null ? '' : scope.root, name, args));
		interp.variables.set('hxcDeferredStateFactory', function(name:Dynamic, ?args:Array<Dynamic>):Dynamic {
			var root = scope == null ? '' : scope.root;
			return new HxcDeferredValue(function()
				return HxcStateFactory.stateFactory(root, name, args));
		});
		interp.variables.set('hxcSwitchState', function(target:Dynamic):Bool
			return HxcStateFactory.switchStateScoped(scope == null ? '' : scope.root, target));
		interp.variables.set('hxcStartExitState', function(target:Dynamic):Bool
			return HxcStateFactory.startExitState(scope == null ? '' : scope.root, target));
		interp.variables.set('hxcOpenSubState', function(target:Dynamic):Bool
			return HxcStateFactory.openSubStateScoped(scope == null ? '' : scope.root, owner, target));
		interp.variables.set('hxcOpenSubStateOn', function(host:Dynamic, target:Dynamic):Bool
			return HxcStateFactory.openSubStateScoped(scope == null ? '' : scope.root, host, target));
		interp.variables.set('hxcBack', function():Bool return HxcStateFactory.back(owner));
		interp.variables.set('hxcResetState', HxcStateFactory.resetState);
		interp.variables.set('CreditsState', CreditsState);
		interp.variables.set('SaveDataState', SaveDataState);
		interp.variables.set('currentPlayState', owner);
	}

	function moduleProxy(caller:HxcFreeplayScope, name:Dynamic):Dynamic {
		return moduleProxyFromRoot(caller == null ? '' : caller.root, name);
	}

	function moduleProxyFromRoot(root:String, name:Dynamic):Dynamic {
		if (name == null)
			return null;
		var scope:HxcFreeplayScope = cast HxcFreeplayRouting.moduleLookup(namesByRoot,
			root == null ? '' : root, destinationRoot, Std.string(name));
		if (scope == null || scope.interp == null)
			return null;
		var proxy:Dynamic = {};
		Reflect.setField(proxy, 'scriptCall', function(methodName:String, ?args:Array<Dynamic>):Dynamic {
			var method = scope.interp.variables.get(methodName);
			return method == null ? null : Reflect.callMethod(null, method, args == null ? [] : args);
		});
		Reflect.setField(proxy, 'scriptGet', function(fieldName:String, ?_args:Array<Dynamic>):Dynamic
			return scope.interp.variables.get(fieldName));
		return proxy;
	}
	#end
}
