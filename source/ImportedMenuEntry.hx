package;

import flixel.FlxG;
import flixel.FlxState;

/** Package entry shares the same source services used by gameplay. */
class ImportedMenuEntry {
	public static var departing(default, null):Bool = false;
	static var ownerLease:String = '';

	/** Keep source services alive through onDestroy, then retire before native create. */
	public static function leaveToPicker():Void {
		if (departing) return;
		departing = true;
		FlxG.signals.preStateCreate.addOnce(function(_) {release(); departing = false;});
		LoadingState.loadAndSwitchState(new CodenameImportedModsState());
	}
	/** Every gameplay exit (normal end, pause and game over) shares this route. */
	public static function returnToFreeplay():Void {
		var hxc = HxcStateFactory.menuSessionRoot();
		if (hxc != '') {
			var target = HxcStateFactory.stateInit(hxc, 'FreeplayState');
			if (Std.isOfType(target, FlxState)) {LoadingState.loadAndSwitchState(cast target); return;}
		}
		var session = NightmareVisionStateSession.active;
		if (session != null && !session.released && session.importedMenuEntry) {
			session.switchState(session.createStateFactory('FreeplayState'));
			return;
		}
		LoadingState.loadAndSwitchState(new FreeplayState());
	}

	/** Small committed chart manifests authenticate package/provider/family leases. */
	public static function requiredOwnerRoots(owner:String):Array<String> {
		#if sys
		return ImportRefreshManager.runtimeOwnerLeaseRoots(owner);
		#else
		return [owner];
		#end
	}

	static function acquire(owner:String):String {
		#if sys
		var token = ImportRefreshManager.tryAcquireRuntimeOwnerLease(requiredOwnerRoots(owner));
		if (token == '') throw '[imported-menu-busy] The selected package is being changed; retry when its import finishes';
		return token;
		#else
		return '';
		#end
	}

	public static function activeOwnerRoots():Array<String> {
		var roots:Array<String> = HxcFreeplayRuntime.activeOwnerRoots();
		var hxc = HxcStateFactory.menuSessionRoot();
		if (hxc != '') roots.push(hxc);
		var codename = CodenameModRuntime.activeRoot();
		if (codename != '') roots.push(codename);
		var nv = NightmareVisionStateSession.active;
		if (nv != null && !nv.released) {
			for (root in nv.mods.authorizedRoots()) if (!roots.contains(root)) roots.push(root);
		}
		var caller = ImportedFreeplayCaller.ownerForFreeplay(codename);
		if (caller != '' && !roots.contains(caller)) roots.push(caller);
		return roots;
	}

	public static function release():Void {
		HxcStateFactory.clearMenuSession();
		CodenameModRuntime.clearActiveOwner();
		if (NightmareVisionStateSession.active != null) NightmareVisionStateSession.active.release();
		ImportedFreeplayCaller.clear();
		#if sys
		if (ownerLease != '') ImportRefreshManager.releaseRuntimeOwnerLease(ownerLease);
		#end
		ownerLease = '';
	}

	public static function openOwnedFreeplay(owner:String):Bool {
		if (owner == '' || owner != HxcStateFactory.menuSessionRoot()) return false;
		var target = HxcStateFactory.stateInit(owner, 'FreeplayState');
		if (!Std.isOfType(target, FlxState)) return false;
		LoadingState.loadAndSwitchState(cast target);
		return true;
	}

	/** Apply the same publication gates as native Freeplay to all authenticated providers. */
	public static function gameplayUnavailableReason(owner:String, storage:String):String {
		var snapshot = ImportRefreshManager.availabilitySnapshot();
		var roots = requiredOwnerRoots(owner);
		if (roots.length == 0) return 'The imported owner dependency snapshot is unavailable.';
		for (root in roots) {
			var ready = FreeplaySongAvailability.ownerReadiness(snapshot, root);
			if (!ready.ready) return ready.reason;
		}
		var song = FreeplaySongAvailability.songReadiness(snapshot, owner, true, 'assets/data/' + storage);
		return song.ready ? '' : song.reason;
	}

	/** Translate an authored source chart name through installed provenance. */
	public static function loadOwnedChart(owner:String, json:String, folder:String):Dynamic {
		#if sys
		if (!CodenameScriptDiscovery.safeName(folder) || !CodenameScriptDiscovery.safeName(json))
			throw '[imported-menu-chart] Invalid chart name';
		var candidates:Array<String> = [];
		for (installed in sys.FileSystem.readDirectory('assets/data')) {
			if (ImportedModDiscovery.ownerForSong(installed, 'assets/data') != owner) continue;
			var receipt = 'assets/data/' + installed + '/importProvenance.json';
			if (!sys.FileSystem.exists(receipt) || sys.FileSystem.stat(receipt).size > 65536) continue;
			var provenance:Dynamic = haxe.Json.parse(sys.io.File.getContent(receipt));
			if (Std.string(Reflect.field(provenance, 'sourceFolder')).toLowerCase() == folder.toLowerCase()) candidates.push(installed);
		}
		if (candidates.length != 1) throw '[imported-menu-chart] Chart ' + folder + ' has ' + candidates.length + ' installed matches in ' + owner;
		var native = candidates[0];
		var source = folder.toLowerCase();
		var chart = json.toLowerCase();
		if (chart != source && !StringTools.startsWith(chart, source + '-')) throw '[imported-menu-chart] Chart prefix differs from source folder';
		PlayState.isStoryMode = false;
		return Song.loadFromJson(native + chart.substr(source.length), native);
		#else
		throw '[imported-menu-chart] Filesystem-backed charts are unavailable';
		#end
	}

	public static function openPsych(owner:String):Void {
		release();
		ownerLease = acquire(owner);
		var plan = ImportedPsychMenuPlan.find(owner);
		if (plan.state == '') {release(); throw plan.diagnostic;}
		HxcStateFactory.installMenuSession(owner, plan.sources);
		ImportedFreeplayCaller.capturePackage(owner);
		var target = HxcStateFactory.stateInit(owner, plan.state);
		if (!Std.isOfType(target, FlxState)) throw 'Invalid Psych source menu constructor';
		LoadingState.loadAndSwitchState(cast target);
	}

	public static function openDefaultFreeplay(owner:String):Void {
		if (departing) return;
		var nextLease = acquire(owner);
		departing = true;
		FlxG.signals.preStateCreate.addOnce(function(_) {
			release();
			ownerLease = nextLease;
			ImportedFreeplayCaller.capturePackage(owner);
			departing = false;
		});
		FreeplayState.currentSongList = [];
		// Freeplay constructs its scope before create; capture the intended filter now,
		// and renew it after retiring the old owner at the create boundary.
		ImportedFreeplayCaller.capturePackage(owner);
		LoadingState.loadAndSwitchState(new FreeplayState());
	}

	public static function openNightmareVision(owner:String, directory:String, name:String):Void {
		release();
		ownerLease = acquire(owner);
		var save = new CodenameOwnerSaveData(owner);
		var prefs = new NightmareVisionClientPrefs(owner, save, OptionsHandler.options);
		var paths = new NightmareVisionPaths(owner, null, prefs.view, directory);
		var mods = new NightmareVisionModsContext(owner, directory);
		paths.bindModFamily(mods);
		new NightmareVisionModConfigRuntime(mods, paths);
		mods.applyModConfig();
		var session = NightmareVisionStateSession.adopt(mods, paths, prefs, new NightmareVisionDifficultyAdapter(owner));
		session.importedMenuEntry = true;
		session.loadSourcePreferences();
		session.initializeSourceControls();
		session.loadHighscores();
		session.mountPlugins();
		session.bootstrapComplete = true;
		session.switchState(session.createStateFactory(name));
	}
}
