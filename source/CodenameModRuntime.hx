package;

import flixel.FlxG;
import flixel.FlxState;
import haxe.io.Path;
import CodenameModLaunchPlan.CodenameModLaunchPlanData;
import CodenameScriptDiscovery.CodenameScriptFile;
#if sys
import sys.FileSystem;
#end

using StringTools;

/** Explicit session owner for Codename global and state scripts.
	No owner is selected at startup. The Imported Mods chooser or a chart whose
	installed manifest names the owner activates one root for that session.
*/
class CodenameModRuntime {
	static var selectedRoot:String = '';
	static var activeStatePaths:Array<String> = [];
	static var globalRuntime:CodenameGlobalScriptRuntime;
	static var preSwitchHandler:Void->Void;
	static var postSwitchHandler:Void->Void;
	static var preStateCreateSmokeHandler:FlxState->Void;
	static var globalFailure:String = '';

	public static function activeRoot():String return selectedRoot;

	public static function hasInstalledStates(root:String):Bool {
		var plan = readCatalog();
		if (!plan.valid) return false;
		for (entry in plan.entries)
			if (root != null && CompatScriptManifest.destinationKey(entry.root)
				== CompatScriptManifest.destinationKey(root)) return true;
		return false;
	}

	/** Activate only an owner with an installed Codename catalog entry. */
	public static function activateOwner(root:String):Bool {
		if (root == null || StringTools.trim(root) == '') return false;
		if (!FNFAssets.exists(CodenameModCatalog.PATH)) {
			trace('[codename-mod-catalog] no imported Codename owners are installed');
			return false;
		}
		var catalog = CodenameModCatalog.parse(FNFAssets.getText(CodenameModCatalog.PATH));
		if (!catalog.valid) {
			trace('[codename-mod-catalog] ' + catalog.error);
			return false;
		}
		var key = CompatScriptManifest.destinationKey(root);
		var found = false;
		var selectedStates:Array<String> = [];
		for (entry in catalog.data.entries) {
			#if sys
			if (entry != null && FileSystem.isDirectory(entry.root)
				&& CompatScriptManifest.destinationKey(entry.root) == key) {
				found = true;
				selectedStates = entry.states == null ? [] : entry.states.copy();
				break;
			}
			#end
		}
		if (!found) {
			trace('[codename-mod-owner] Owner is not present in the installed Codename owner catalog.');
			return false;
		}
		if (selectedRoot == root && globalRuntime != null) return true;
		clearActiveOwner();
		selectedRoot = root;
		activeStatePaths = selectedStates;
		installStateCreateSmokeTrace(root);
		loadGlobal(root);
		return true;
	}

	/** A current chart can activate only the owner already named by its manifest. */
	public static function activateChartOwner(root:String):Bool return activateOwner(root);

	/** Direct Freeplay/editor/retry launches must initialize the selected
	 * package before its stage, characters and note scripts read saved defaults.
	 * An existing session survives same-owner loads; foreign/native charts end it. */
	public static function synchronizeChartOwner(root:String):Bool {
		if (root == null || StringTools.trim(root) == '') {
			if (activeRoot() != '') clearActiveOwner();
			return true;
		}
		if (isActiveOwner(root) && globalFailure == '') return true;
		// Failed selection must not leave the previous package's global callbacks
		// running against an unrelated chart.
		if (activeRoot() != '') clearActiveOwner();
		return activateChartOwner(root);
	}

	/** Clear all owner-global resources after the user exits the imported session. */
	public static function clearActiveOwner():Void {
		CodenameRequestedStateCompat.clear();
		if (preSwitchHandler != null) {
			FlxG.signals.preStateSwitch.remove(preSwitchHandler);
			preSwitchHandler = null;
		}
		if (postSwitchHandler != null) {
			FlxG.signals.postStateSwitch.remove(postSwitchHandler);
			postSwitchHandler = null;
		}
		if (preStateCreateSmokeHandler != null) {
			FlxG.signals.preStateCreate.remove(preStateCreateSmokeHandler);
			preStateCreateSmokeHandler = null;
		}
		if (globalRuntime != null) {
			var ownerRuntime = globalRuntime;
			globalRuntime = null;
			ownerRuntime.destroy();
			if (globalFailure == '' && ownerRuntime.failure != '') globalFailure = ownerRuntime.failure;
		}
		if (selectedRoot != '') CodenameMusicBeatTransition.clearOwner(selectedRoot);
		selectedRoot = '';
		activeStatePaths = [];
		globalFailure = '';
	}

	public static function isActiveOwner(root:String):Bool
		return root != null && selectedRoot != ''
			&& CompatScriptManifest.destinationKey(selectedRoot) == CompatScriptManifest.destinationKey(root);

	/** Frame callback for the currently selected owner's data/global.hx. */
	public static function updateGlobal(elapsed:Float):Void {
		if (globalRuntime == null) return;
		globalRuntime.update(elapsed);
		if (globalFailure == '' && globalRuntime.failure != '') globalFailure = globalRuntime.failure;
	}

	/** Materialize an owner-local classless state; callers still choose when to switch. */
	public static function stateInit(root:String, name:String):Dynamic {
		if (!isActiveOwner(root)) {
			trace('[codename-mod-state] State request crossed the selected owner boundary.');
			return null;
		}
		var target = stateInitIfAvailable(root, name, '');
		if (target != null) return target;
		trace('[codename-mod-state] No installed state script named ' + name + ' in the selected owner.');
		return null;
	}

	/** Resolve a conventional `new MainMenuState()` classless script constructor
		only against the currently active owner's validated catalog. Native
		constructors continue normally when that owner has no matching script.
	*/
	public static function stateInitIfAvailable(root:String, name:String,
		?sourcePath:String):Dynamic {
		if (!isActiveOwner(root) || name == null || activeStatePaths == null) return null;
		var resolution = CodenameModStateResolver.resolve(activeStatePaths, name, sourcePath);
		if (resolution.ambiguous) {
			var diagnostic = '[codename-mod-state-resolution] Ambiguous state constructor '
				+ name + ' from ' + (sourcePath == null ? '' : sourcePath)
				+ '; qualify the state path within the active owner.';
			trace(diagnostic);
			throw diagnostic;
		}
		return resolution.path == '' ? null : new CodenameImportedState(root, resolution.path);
	}

	/** State switch callback used by the owner-local ModState constructor. */
	public static function switchToState(name:String):Dynamic {
		var target = stateInit(selectedRoot, name);
		if (target == null) return null;
		if (!switchTarget(selectedRoot, target)) return null;
		return target;
	}

	public static function switchTarget(root:String, target:Dynamic):Bool {
		if (!isActiveOwner(root) || target == null) {
			trace('[codename-mod-state-switch] Refused an inactive owner or null target.');
			return false;
		}
		if (Std.isOfType(target, CodenameImportedState)
			&& !isActiveOwner((cast target:CodenameImportedState).ownerRoot)) {
			trace('[codename-mod-state-switch] Refused a cross-owner imported state transition.');
			return false;
		}
		if (!Std.isOfType(target, flixel.FlxState)) {
			trace('[codename-mod-state-switch] Refused a non-FlxState target.');
			return false;
		}
		CodenameTransitionScope.queueStateTarget(root, target);
		try CodenameRequestedStateCompat.switchToKnownTarget(cast target,
			function():Void FlxG.switchState(cast target)) catch (error:Dynamic) {
			CodenameTransitionScope.clearPendingStateTarget(root);
			throw error;
		}
		// FlxG.switchState calls startOutro synchronously. A selected custom
		// transition consumes the target there; otherwise discard it now so a
		// later, unrelated outro cannot inherit this destination.
		CodenameTransitionScope.clearPendingStateTarget(root);
		return true;
	}

	/** Explicit user exit: release owner globals before returning to native menus. */
	public static function exitToNativeMenu():Void {
		clearActiveOwner();
		LoadingState.loadAndSwitchState(new MainMenuState());
	}

	static function readCatalog():CodenameModLaunchPlanData {
		if (!FNFAssets.exists(CodenameModCatalog.PATH))
			return {valid:true, entries:[], diagnostics:['[codename-mod-catalog] no imported Codename states are installed']};
		try return CodenameModLaunchPlan.fromCatalog(FNFAssets.getText(CodenameModCatalog.PATH))
		catch (error:Dynamic) return {valid:false, entries:[], diagnostics:[Std.string(error)]};
	}

	static function loadGlobal(root:String):Void {
		#if sys
		var discovered = CodenameScriptDiscovery.discoverOwnerScriptsDetailed(root, '');
		var global:CodenameScriptFile = null;
		for (file in discovered.files) if (file.family == 'global') { global = file; break; }
		if (global == null) return;
		var paths = new CodenamePaths(root);
		var interp = new CodenameScriptInterp(paths, new CodenameFlxGFacade([FlxG.camera], root),
			function(name:String):Dynamic return CodenameModBindings.customShader(paths, name));
		interp.flxG.stateSwitch = function(target:Dynamic):Bool return switchTarget(root, target);
		interp.modStateFactory = function(name:String):Dynamic return stateInit(root, name);
		var bindings = CodenameModBindings.create(root, paths, interp, null);
		var source = FNFAssets.getText(global.path);
		var parsed = CodenameScriptParser.prepare(source, bindings, global.relative);
		CodenameScriptParser.reportRecoverableDiagnostics(parsed, global.relative);
		if (parsed.program == null || CodenameScriptParser.hasFatalDiagnostics(parsed)) {
			for (diagnostic in parsed.diagnostics)
				trace('[codename-script-' + diagnostic.code + '] ' + global.relative + ':'
					+ diagnostic.line + ': ' + diagnostic.message);
			interp.release();
			globalFailure = global.relative + ' could not be parsed';
			return;
		}
		CodenameModBindings.seed(interp, root, null, paths);
		for (name in bindings.keys())
			interp.variables.set(name.substr(name.lastIndexOf('.') + 1), bindings.get(name));
		var runtime = new CodenameGlobalScriptRuntime(interp, global.relative);
		globalRuntime = runtime;
		if (!runtime.initialize(parsed.program)) {
			globalFailure = runtime.failure;
			globalRuntime = null;
			return;
		}
		preSwitchHandler = function():Void {
			if (globalRuntime == null) {
				CodenameRequestedStateCompat.clear(FlxG.game);
				return;
			}
			CodenameStateSmokeTrace.mark('global-pre-switch-before', root, global.relative,
				[CodenameStateSmokeTrace.field('nextState', pendingStateName('_nextState')),
					CodenameStateSmokeTrace.field('legacyRequestedState', pendingStateName('_requestedState'))]);
			globalRuntime.preStateSwitch();
			CodenameStateSmokeTrace.mark('global-pre-switch-after', root, global.relative,
				[CodenameStateSmokeTrace.field('nextState', pendingStateName('_nextState')),
					CodenameStateSmokeTrace.field('legacyRequestedState', pendingStateName('_requestedState'))]);
			CodenameRequestedStateCompat.clear(FlxG.game);
		};
		FlxG.signals.preStateSwitch.add(preSwitchHandler);
		postSwitchHandler = function():Void {
			if (globalRuntime == null) return;
			globalRuntime.postStateSwitch();
			if (globalFailure == '' && globalRuntime.failure != '') globalFailure = globalRuntime.failure;
		};
		FlxG.signals.postStateSwitch.add(postSwitchHandler);
		#end
	}

	static function installStateCreateSmokeTrace(root:String):Void {
		if (!CodenameStateSmokeTrace.enabled()) return;
		preStateCreateSmokeHandler = function(target:FlxState):Void {
			if (!isActiveOwner(root)) return;
			CodenameStateSmokeTrace.mark('pre-state-create', root, '',
				[CodenameStateSmokeTrace.field('target', CodenameStateSmokeTrace.stateName(target))]);
		};
		FlxG.signals.preStateCreate.add(preStateCreateSmokeHandler);
	}

	static function pendingStateName(field:String):String {
		try {
			var game:Dynamic = FlxG.game;
			if (game == null) return 'no-game';
			var pending = field == '_requestedState'
				? CodenameRequestedStateCompat.getRequestedState(game)
				: Reflect.field(game, field);
			return CodenameStateSmokeTrace.stateName(pending);
		} catch (_:Dynamic) {
			return 'read-error';
		}
	}

	public static function diagnostics():Array<String> {
		var result:Array<String> = [];
		if (globalFailure != '') result.push(globalFailure);
		return result;
	}
}
