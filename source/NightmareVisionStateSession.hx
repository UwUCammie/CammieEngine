package;

import flixel.FlxG;
import flixel.FlxState;
import flixel.addons.transition.FlxTransitionableState;
import haxe.ds.ObjectMap;
import NightmareVisionMusicBeatState.NightmareVisionMusicBeatStateHost;
import NightmareVisionStateFactory.INightmareVisionStateFactoryHost;
import NightmareVisionStateFactory.NightmareVisionStateTransitionOverrides;
import NightmareVisionHighscoreMigration.NightmareVisionHighscoreMigrationEntry;

/** Source navigation retains the same authenticated family, services and plugins.
 * Individual states own their script groups; departure retires the session. */
@:keep
@:access(PlayState)
class NightmareVisionStateSession implements INightmareVisionStateFactoryHost {
	static inline var MAX_SCORE_MIGRATION_METADATA_BYTES:Int = 131072;
	public static var active(default, null):NightmareVisionStateSession;
	public final mods:NightmareVisionModsContext;
	public final paths:NightmareVisionPaths;
	public final prefs:NightmareVisionClientPrefs;
	public final difficulty:NightmareVisionDifficultyAdapter;
	public final config:NightmareVisionModConfigRuntime;
	public final factory:NightmareVisionStateFactory;
	public final highscoreSave:CodenameOwnerSaveData;
	public final highscores:NightmareVisionHighscore;
	public var weekCompleted:Dynamic = new Map<String, Bool>();
	public var startMeta:Dynamic;
	public var bootstrapComplete:Bool = false;
	var bootstrapServices:NightmareVisionBootstrapServices;
	final mainRuntime:NightmareVisionMainRuntime;
	public var plugins:NightmareVisionPluginRuntime;
	public var menuVocals:flixel.sound.FlxSound;
	public var titleInitialized:Bool = false;
	public var titleClosedState:Bool = false;
	public var flashingLeftState:Bool = false;
	public var mainMenuSelected:Int = 0;
	public var released(default, null):Bool = false;
	var highscoreMigrationAttempted:Bool = false;
	/** Optional native host service injection, never a chart-identity branch. */
	public var configureScript:NightmareVisionScriptInterp->Void;
	final inputs:NightmareVisionInputScope;
	final conductor = new NightmareVisionConductor();
	final states:ObjectMap<FlxState, String> = new ObjectMap();
	final redirectNames:Map<String, String> = new Map();
	final postCallbacks:Array<Void->Void> = [];
	final previousSkipIn:Bool;
	final previousSkipOut:Bool;
	var requestedSwitch:Bool = false;
	public var hasPendingSwitch(get, never):Bool;
	function get_hasPendingSwitch():Bool return requestedSwitch && !released;

	public static function adopt(mods:NightmareVisionModsContext, paths:NightmareVisionPaths,
		prefs:NightmareVisionClientPrefs, difficulty:NightmareVisionDifficultyAdapter):NightmareVisionStateSession {
		if (active != null && !active.released && active.mods == mods) return active;
		if (active != null) active.release();
		return new NightmareVisionStateSession(mods, paths, prefs, difficulty);
	}

	public static function leaseForChart(chartRoot:String):String {
		var session = active;
		if (session == null || session.released || session.mods.released) return chartRoot;
		if (chartRoot == session.mods.selectedRoot() && session.mods.authorizedRoots().contains(chartRoot))
			return session.mods.ownerRoot;
		return chartRoot;
	}

	public function new(mods:NightmareVisionModsContext, paths:NightmareVisionPaths,
		prefs:NightmareVisionClientPrefs, difficulty:NightmareVisionDifficultyAdapter) {
		if (mods == null || paths == null || prefs == null || difficulty == null
			|| mods.ownerRoot != paths.root || !prefs.canReuseFor(paths.root) || !difficulty.canReuseFor(paths.root)
			|| mods.nativeConfig == null)
			throw '[nightmare-vision-state-session] State services require one live owner';
		this.mods = mods; this.paths = paths; this.prefs = prefs; this.difficulty = difficulty;
		config = cast mods.nativeConfig;
		highscoreSave = new CodenameOwnerSaveData(paths.root);
		highscores = new NightmareVisionHighscore(highscoreSave, paths.sanitize, difficulty.getDifficultyFilePath);
		startMeta = {width:1280, height:720, fps:60, skipSplash:#if debug true #else false #end,
			startFullScreen:false, initialState:NightmareVisionTitleState};
		mainRuntime = new NightmareVisionMainRuntime(paths.root);
		previousSkipIn = FlxTransitionableState.skipNextTransIn;
		previousSkipOut = FlxTransitionableState.skipNextTransOut;
		factory = new NightmareVisionStateFactory(this);
		inputs = new NightmareVisionInputScope(paths.root, prefs.view, true, false);
		Reflect.setField(prefs.view, 'reloadControls', reloadSourceControls);
		Reflect.setField(prefs.view, 'load', loadSourcePreferences);
		NightmareVisionSpriteRegistry.enterSession(paths.root);
		NightmareVisionAlphabetRegistry.enterSession(paths.root);
		active = this;
		FlxG.signals.preStateCreate.add(onPreStateCreate);
		FlxG.signals.postStateSwitch.add(onPostStateSwitch);
	}

	function ensureAlive():Void {
		if (released || mods.released) throw '[nightmare-vision-state-session] Released source session';
	}

	/** Source Init backends are prepared without duplicating the gameplay preset. */
	public function services():NightmareVisionBootstrapServices {
		ensureAlive();
		if (bootstrapServices == null) bootstrapServices = new NightmareVisionBootstrapServices(
			paths.root, prefs.view, paths, function() return (PlayState.activeNightmareVisionInputScope(paths.root) ?? inputs).controls,
			resetState, populatePlugins, function() mods.applyModConfig(), function(name, value) highscoreSave.setField(name, value));
		return bootstrapServices;
	}
	public function initializeSourceControls():Void {
		mainRuntime.install();
		// Capture native settings before source preference loading changes them.
		services(); inputs.resetControls();
	}

	/** Reload source-private scores, then migrate paired native records once
		for authenticated, registered Nightmare Vision charts in this family. */
	public function loadHighscores():Void {
		ensureAlive();
		highscores.load();
		if (highscoreMigrationAttempted) return;
		highscoreMigrationAttempted = true;
		try {
			var entries = collectHighscoreMigrationEntries();
			if (entries.length == 0) return;
			var migrated = NightmareVisionHighscoreMigration.migrate(entries,
				mods.ownerRoot, mods.authorizedRoots(), highscores, difficulty,
				function(message:String) report('highscores', 'migration', message));
		} catch (error:Dynamic) {
			report('highscores', 'migration', error);
		}
	}

	/** Read only the real Freeplay registry and small owner sidecars here. Chart
		bodies stay behind each entry's callback until a paired native record exists. */
	function collectHighscoreMigrationEntries():Array<NightmareVisionHighscoreMigrationEntry> {
		ensureAlive();
		var result:Array<NightmareVisionHighscoreMigrationEntry> = [];
		if (Highscore.songScores == null || Highscore.songAccuracy == null) return result;
		var authorized = new Map<String, Bool>();
		for (root in mods.authorizedRoots()) {
			var clean = safeScoreMigrationOwner(root);
			if (clean != null) authorized.set(CompatScriptManifest.destinationKey(clean), true);
		}
		var sessionOwner = safeScoreMigrationOwner(mods.ownerRoot);
		if (sessionOwner == null || !authorized.exists(CompatScriptManifest.destinationKey(sessionOwner)))
			return result;

		var categories:Dynamic;
		try categories = FreeplayRegistry.getJson() catch (error:Dynamic) {
			report('highscores', 'freeplay-registry', error);
			return result;
		}
		if (!Std.isOfType(categories, Array)) return result;
		var difficultyNames:Array<String>;
		try difficultyNames = DifficultyManager.getDifficultyNames() catch (_:Dynamic) return result;
		if (difficultyNames == null || difficultyNames.length == 0) return result;
		var seenSongs:Map<String, Bool> = new Map();
		for (category in (cast categories:Array<Dynamic>)) {
			var rows:Dynamic = category == null ? null : Reflect.field(category, 'songs');
			if (!Std.isOfType(rows, Array)) continue;
			for (row in (cast rows:Array<Dynamic>)) {
				var rawName:Dynamic = Std.isOfType(row, String) ? row : Reflect.field(row, 'name');
				if (!Std.isOfType(rawName, String)) continue;
				var registered = StringTools.trim(cast rawName).toLowerCase();
				if (!safeScoreMigrationSongId(registered) || seenSongs.exists(registered)) continue;
				seenSongs.set(registered, true);
				var nativeCandidates:Array<Int> = [];
				for (difficultyIndex in 0...difficultyNames.length) {
					var nativeKey:String;
					try nativeKey = Highscore.formatSong(registered, difficultyIndex, 'best-score') catch (_:Dynamic) continue;
					if (Highscore.songScores.exists(nativeKey) && Highscore.songAccuracy.exists(nativeKey))
						nativeCandidates.push(difficultyIndex);
				}
				// Avoid even sidecar reads when this registered row has no complete
				// native best-score record to consider.
				if (nativeCandidates.length == 0) continue;

				var folderPath = 'assets/data/' + registered + '/';
				var provenanceText = readBoundedScoreMetadata(folderPath + 'importProvenance.json');
				if (provenanceText == null) continue;
				var provenance:Dynamic;
				try provenance = CoolUtil.parseJson(provenanceText) catch (_:Dynamic) continue;
				if (provenance == null || Reflect.field(provenance, 'version') != 1
					|| Reflect.field(provenance, 'sourceEngine') != ImportEngine.NIGHTMARE_VISION
					|| !Std.isOfType(Reflect.field(provenance, 'destinationFolder'), String)
					|| StringTools.trim(cast Reflect.field(provenance, 'destinationFolder')).toLowerCase() != registered)
					continue;
				var owner = safeScoreMigrationOwner(Reflect.field(provenance, 'sourceOwner'));
				if (owner == null || !authorized.exists(CompatScriptManifest.destinationKey(owner))) continue;
				var manifestText = readBoundedScoreMetadata(folderPath + CompatScriptManifest.FILE_NAME);
				if (manifestText == null) continue;
				var ownerManifest = CompatScriptManifest.parse(manifestText);
				if (ownerManifest == null || ownerManifest.roots == null) continue;
				var manifestOwner = CompatScriptManifest.selectedRoot(ownerManifest);
				if (CompatScriptManifest.destinationKey(manifestOwner)
					!= CompatScriptManifest.destinationKey(owner)) continue;
				var hasNmvOwnerRoot = false;
				for (root in ownerManifest.roots)
					if (root != null && root.dependency != true
						&& root.engine == ImportEngine.NIGHTMARE_VISION
						&& CompatScriptManifest.destinationKey(root.path)
							== CompatScriptManifest.destinationKey(manifestOwner)) {
						hasNmvOwnerRoot = true;
						break;
					}
				if (!hasNmvOwnerRoot) continue;
				var selectable:Dynamic = Reflect.field(provenance, 'sourceSelectableDifficulties');
				if (!Std.isOfType(selectable, Array)) continue;
				var unsupported:Dynamic = Reflect.field(provenance, 'sourceUnsupportedDifficulties');

				for (difficultyIndex in nativeCandidates) {
					var difficultyName = StringTools.trim(difficultyNames[difficultyIndex]);
					if (difficultyName == '' || !scoreMigrationContainsDifficulty(selectable, difficultyName)
						|| scoreMigrationContainsDifficulty(unsupported, difficultyName)) continue;
					var ending:String;
					try ending = DifficultyManager.getDiffEnding(difficultyIndex) catch (_:Dynamic) continue;
					if (ending == null || (ending != '' && !StringTools.startsWith(ending, '-'))) continue;
					var chartStem = registered + ending.toLowerCase();
					var chartPath = folderPath + chartStem + '.json';
					if (!FNFAssets.exists(chartPath)) chartPath = folderPath + chartStem + '.jsonc';
					if (!FNFAssets.exists(chartPath)) continue;
					var capturedPath = chartPath;
					var capturedSong = registered;
					var capturedStem = chartStem;
					result.push({registeredSong:registered, nativeDifficultyIndex:difficultyIndex,
						destinationChartPath:chartPath, provenance:provenance, ownerManifest:ownerManifest,
						loadChart:function() return loadHighscoreMigrationChart(capturedPath, capturedSong, capturedStem)});
				}
			}
		}
		return result;
	}

	/** Match Song's validated storage identity without calling its global
		loadFromJson path, which resolves sibling charts and mutates host state. */
	function loadHighscoreMigrationChart(path:String, registered:String, stem:String):Dynamic {
		if (path == null || !FNFAssets.exists(path))
			throw '[nv-score-migration-chart-path-missing] ' + registered;
		var parsed:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
		var chart:Dynamic = parsed == null ? null : Reflect.field(parsed, 'song');
		if (chart == null || !Reflect.isObject(chart) || Std.isOfType(chart, Array))
			throw '[nv-score-migration-chart-shape-invalid] ' + registered;
		// Song.loadFromJson discards chart-authored score ids before attaching the
		// id validated from the selected Freeplay row.
		Reflect.deleteField(chart, 'compatScoreSongId');
		Reflect.setField(chart, 'compatStorageFolder', registered);
		Reflect.setField(chart, 'compatChartFileName', stem);
		if (!Song.attachFreeplayScoreSongId(chart, registered))
			throw '[nv-score-migration-native-identity-invalid] ' + registered;
		return chart;
	}

	static function readBoundedScoreMetadata(path:String):Null<String> {
		if (path == null || !FNFAssets.exists(path)) return null;
		#if sys
		var resolved = FNFAssets.resolveCaseInsensitivePath(path);
		if (resolved != null) try {
			if (sys.FileSystem.stat(resolved).size > MAX_SCORE_MIGRATION_METADATA_BYTES) return null;
		} catch (_:Dynamic) {}
		#end
		try {
			var text = FNFAssets.getText(path);
			return text == null || text.length > MAX_SCORE_MIGRATION_METADATA_BYTES ? null : text;
		} catch (_:Dynamic) return null;
	}

	static function safeScoreMigrationOwner(value:Dynamic):Null<String> {
		if (!Std.isOfType(value, String)) return null;
		var clean = StringTools.replace(StringTools.trim(cast value), '\\', '/');
		while (StringTools.endsWith(clean, '/')) clean = clean.substr(0, clean.length - 1);
		if (!StringTools.startsWith(clean.toLowerCase(), 'assets/imported_mods/')) return null;
		var parts = clean.split('/');
		if (parts.length < 3) return null;
		for (index in 2...parts.length)
			if (parts[index] == '' || parts[index] == '.' || parts[index].indexOf('..') >= 0
				|| parts[index].indexOf(':') >= 0 || parts[index].indexOf('\u0000') >= 0) return null;
		return clean;
	}

	static function safeScoreMigrationSongId(value:String):Bool {
		return value != null && value != '' && value != '.' && value != '..'
			&& value.indexOf('..') < 0 && value.indexOf('/') < 0
			&& value.indexOf('\\') < 0 && value.indexOf(':') < 0
			&& value.indexOf('\u0000') < 0;
	}

	static function scoreMigrationContainsDifficulty(raw:Dynamic, wanted:String):Bool {
		if (!Std.isOfType(raw, Array)) return false;
		for (value in (cast raw:Array<Dynamic>))
			if (Std.isOfType(value, String)
				&& StringTools.trim(cast value).toLowerCase() == wanted.toLowerCase()) return true;
		return false;
	}
	public function loadSourcePreferences():Void {
		prefs.load();
		var volume = highscoreSave.getField('volume');
		var mute = highscoreSave.getField('mute');
		if (volume == null) {volume = FlxG.sound.volume; highscoreSave.setField('volume', volume);}
		if (mute == null) {mute = FlxG.sound.muted; highscoreSave.setField('mute', mute);}
		if (RuntimeSmokeHarness.enabled()) {
			mute = true;
			highscoreSave.setField('mute', true);
		}
		services().applySourceAudioPreferences(volume, mute);
		reloadSourceControls();
	}
	public function reloadSourceControls():Void {
		ensureAlive();
		var controls = (PlayState.activeNightmareVisionInputScope(paths.root) ?? inputs).controls;
		controls.setKeyboardScheme(nightmarevision.input.NightmareVisionInputEnums.KeyboardScheme.Solo);
		var gamepads = controls.gamepadsAdded.copy();
		controls.removeGamepad();
		for (id in gamepads) controls.addDefaultGamepad(id);
		prefs.view.muteKeys = prefs.view.copyKey(prefs.view.keyBinds.get('volume_mute'));
		prefs.view.volumeDownKeys = prefs.view.copyKey(prefs.view.keyBinds.get('volume_down'));
		prefs.view.volumeUpKeys = prefs.view.copyKey(prefs.view.keyBinds.get('volume_up'));
		services().applySourceSoundKeys(prefs.view.muteKeys, prefs.view.volumeDownKeys, prefs.view.volumeUpKeys);
	}
	public function restoreCompletedWeeks():Void {
		var value = highscoreSave.getField('weekCompleted');
		if (value != null) weekCompleted = value;
	}
	public function mountPlugins(populateImmediately:Bool = true):Void {
		ensureAlive();
		plugins = NightmareVisionPluginHost.mount(paths.root, function(interp, entry, runtime) {
			plugins = runtime;
			PlayState.seedNightmareVisionCommon(interp, paths, prefs, runtime, mods, difficulty, null, entry);
		}, paths, populateImmediately, discoverPlugins, report);
	}
	public function discoverPlugins():Array<NightmareVisionScriptDiscovery.NightmareVisionScriptEntry> {
		ensureAlive();
		var entries:Array<NightmareVisionScriptDiscovery.NightmareVisionScriptEntry> = [];
		for (path in paths.listAllFilesInDirectory('scripts/plugins/')) {
			var supported = false;
			for (extension in paths.scriptExtensions)
				if (StringTools.endsWith(path, extension)) {supported = true; break;}
			if (!supported) continue;
			var coreIndex = path.indexOf('/__nmv_core/');
			var relative = coreIndex >= 0 ? path.substr(coreIndex + 1)
				: StringTools.startsWith(path, paths.root + '/') ? path.substr(paths.root.length + 1) : path;
			entries.push({scope:'plugin',name:haxe.io.Path.withoutExtension(haxe.io.Path.withoutDirectory(path)),
				path:path,relative:relative});
		}
		return entries;
	}
	public function populatePlugins():Void {
		ensureAlive();
		if (plugins != null) plugins.populate();
	}
	/** Init snapshots its chosen class before submitting the constructor. */
	public function startupConstructor(type:Dynamic):Void->FlxState {
		var classes:Array<{type:Dynamic,name:String}> = [{type:NightmareVisionTitleState,name:'TitleState'},
			{type:NightmareVisionMainMenuState,name:'MainMenuState'},
			{type:NightmareVisionFlashingState,name:'FlashingState'},
			{type:NightmareVisionInitState,name:'Init'}, {type:NightmareVisionSplashState,name:'Splash'},
			{type:PlayState,name:'PlayState'}, {type:FreeplayState,name:'FreeplayState'}];
		for (entry in classes)
			if (type == entry.type) return createStateFactory(entry.name);
		return function():FlxState {ensureAlive(); return Type.createInstance(type, []);};
	}

	/** These constructors are source classes, not aliases for native host menus. */
	public function createStateFactory(name:String):Void->FlxState {
		ensureAlive();
		return function():FlxState {
			ensureAlive();
			var state:FlxState = switch (name) {
				case 'Init': new NightmareVisionInitState(this);
				case 'Splash': new NightmareVisionSplashState({paths:paths,
					readOwnerSave:highscoreSave.getField,
					onDisposed:releaseStateResources,
					initialStateConstructor:function() return startupConstructor(startMeta.initialState)(),
					switchStartup:switchState});
				case 'TitleState': new NightmareVisionTitleState(this);
				case 'MainMenuState': new NightmareVisionMainMenuState(this);
				case 'FlashingState': new NightmareVisionFlashingState(this);
				case 'MusicBeatState': new NightmareVisionMusicBeatState(stateHost());
				case 'PlayState':
					PlayState.adoptNightmareVisionStateServices(this);
					new PlayState();
				case 'FreeplayState':
					ImportedFreeplayCaller.capturePackage(mods.selectedRoot());
					new FreeplayState();
				default: new NightmareVisionUnportedState(name, this);
			};
			states.set(state, name);
			return state;
		};
	}

	public function switchState(next:Dynamic):Void {
		ensureAlive();
		var request:Void->Dynamic;
		var resetConstructor:Void->Dynamic = null;
		if (Reflect.isFunction(next)) request = cast next;
		else if (Std.isOfType(next, FlxState)) {
			request = function() return next;
			var name = requestedStateName(next);
			resetConstructor = states.exists(cast next) ? cast createStateFactory(name)
				: function():Dynamic return Type.createInstance(Type.getClass(next), []);
		}
		else throw '[nightmare-vision-state-session] Expected a state constructor or state instance';
		requestedSwitch = true;
		FlxG.switchState(function():FlxState {
			ensureAlive();
			var result = factory.construct(request, resetConstructor);
			if (!Std.isOfType(result.state, FlxState))
				throw '[nightmare-vision-state-session] Source constructor did not return a native state';
			return cast result.state;
		});
	}

	public function resetState():Void {
		ensureAlive();
		if (factory.lastConstructor == null) {
			// Initial gameplay was entered by the host rather than a source request.
			if (Std.isOfType(FlxG.state, PlayState)) {switchState(createStateFactory('PlayState')); return;}
			throw '[nightmare-vision-state-session] No source constructor available for reset';
		}
		requestedSwitch = true;
		FlxG.switchState(function():FlxState {
			var result = factory.resetState();
			if (!Std.isOfType(result.state, FlxState)) throw '[nightmare-vision-state-session] Invalid reset constructor';
			return cast result.state;
		});
	}

	public function switchWithTransition(next:Dynamic, transition:NightmareVisionModTransition = ENGINE_DEFAULT):Void {
		if (transition == ENGINE_DEFAULT) {switchState(next); return;}
		factory.switchWithTransitions(transition, transition, function():Dynamic {switchState(next); return null;});
	}

	public function setTransSkip(skipIn:Bool = true, skipOut:Bool = true):Void {
		FlxTransitionableState.skipNextTransIn = skipIn;
		FlxTransitionableState.skipNextTransOut = skipOut;
	}

	public function changePresence(details:String, state:String = ''):Void {
		ensureAlive();
		#if cpp
		Discord.DiscordClient.changePresence(details, state);
		#end
	}

	public function titleInit():Void {
		ensureAlive();
		var cache = paths.getOwnerAssetCache();
		cache.clearStoredMemory(); cache.clearUnusedMemory();
		var data = new CodenameOwnerSaveData(paths.root);
		if (data.getField('flashing') == null && !flashingLeftState) {
			setTransSkip(); switchState(createStateFactory('FlashingState'));
		}
	}

	public function requestedStateName(state:Dynamic):String {
		if (Std.isOfType(state, FlxState) && states.exists(cast state)) return states.get(cast state);
		var type = Type.getClass(state);
		return type == null ? null : Type.getClassName(type).split('.').pop();
	}
	public function stateRedirectPath(requestedName:String):Null<String> {
		ensureAlive();
		var redirects:Dynamic = mods.currentModConfig == null ? null : Reflect.field(mods.currentModConfig, 'stateRedirects');
		var target:Dynamic = redirects == null ? null : Reflect.field(redirects, requestedName);
		if (!Std.isOfType(target, String) || target == '') return null;
		var name:String = cast target;
		var path = NightmareVisionScriptBindings.getPath('scripts/states/' + name, paths);
		if (path == 'scripts/states/' + name) path = paths.getPath(path, null, true);
		if (paths.scopeAssetPath(path) == null)
			throw '[nightmare-vision-state-session] Invalid configured state path: ' + name;
		redirectNames.set(path, name);
		return path;
	}
	public function scriptExists(ownerPath:String):Bool {
		var path = paths.scopeAssetPath(ownerPath);
		return path != null && paths.exists(path) && !paths.isDirectory(path);
	}
	public function makeScriptState(ownerPath:String):Dynamic {
		ensureAlive();
		var name = redirectNames.get(ownerPath);
		if (name == null) throw '[nightmare-vision-state-session] Redirect path has no captured source identity';
		var state = new NightmareVisionScriptedState(name, stateHost());
		states.set(state, 'ScriptedState');
		return state;
	}
	public function destroyState(state:Dynamic):Void {
		(cast state:FlxState).destroy();
		states.remove(cast state);
	}
	public function warnMissingRedirect(requestedName:String, ownerPath:String):Void
		trace('[nightmare-vision-state-redirect] Could not override "' + requestedName + '" to script "' + ownerPath + '". Does the file exist?');
	public function getTransitionOverrides():NightmareVisionStateTransitionOverrides
		return {transitionIn:config.transitionIn, transitionOut:config.transitionOut};
	public function setTransitionOverrides(value:NightmareVisionStateTransitionOverrides):Void {
		if (released) return;
		config.transitionIn = cast value.transitionIn; config.transitionOut = cast value.transitionOut;
	}
	public function afterPostStateSwitch(callback:Void->Void):Void {
		var once:Void->Void = null;
		once = function() {
			postCallbacks.remove(once);
			if (!released) callback();
		};
		postCallbacks.push(once);
		FlxG.signals.postStateSwitch.addOnce(once);
	}

	function onPostStateSwitch():Void {
		if (released) return;
		requestedSwitch = false;
	}

	function onPreStateCreate(current:FlxState):Void {
		if (released) return;
		if (states.exists(current)) {requestedSwitch = false; return;}
		if (Std.isOfType(current, PlayState)) {
			var play:PlayState = cast current;
			if (play.nightmareVisionSelectedRoot() == mods.ownerRoot) {requestedSwitch = false; return;}
		}
		// The old state is destroyed; retire its process effects before an
		// unrelated destination creates its UI or invokes persistent plugins.
		release();
	}

	public function stateHost():NightmareVisionMusicBeatStateHost {
		return {
			session:this, createStateFactory:createStateFactory,
			createScriptGroup:function(parent) return new NightmareVisionScriptGroup(parent, report),
			createStateScript:createStateScript, report:report,
			callPlugins:function(event, args) {if (plugins != null) plugins.callOnPlugins(event, args); return null;},
			getControls:function() return inputs.controls,
			timing:function() {
				var entry = conductor.getBPMFromSeconds(conductor.songPosition);
				var value:Float = entry.stepTime + (conductor.songPosition - prefs.view.noteOffset - entry.songTime) / entry.stepCrotchet;
				return {step:Math.floor(value), decimalStep:value};
			},
			sectionBeats:function(index) {
				var section:Dynamic = PlayState.SONG == null || PlayState.SONG.notes == null || index >= PlayState.SONG.notes.length
					|| index < 0 ? null : PlayState.SONG.notes[index];
				var beats:Dynamic = section == null ? null : Reflect.field(section, 'sectionBeats');
				return beats == null ? 4.0 : cast beats;
			},
			sectionCount:function() return PlayState.SONG == null || PlayState.SONG.notes == null ? 0 : PlayState.SONG.notes.length,
			hasSection:function(index) return PlayState.SONG != null && PlayState.SONG.notes != null
				&& index >= 0 && index < PlayState.SONG.notes.length && PlayState.SONG.notes[index] != null,
			hasSong:function() return PlayState.SONG != null,
			openTransition:openTransition,
			cancelMenuVocals:function() {if (menuVocals != null && menuVocals.fadeTween != null) menuVocals.fadeTween.cancel();},
			failedScriptState:function(name) {
				switchState(function() {
					var fallback = new NightmareVisionFallbackState('failed to load (' + name + ')!\nDoes it exist?',
						function() switchState(createStateFactory('MainMenuState')), this);
					states.set(fallback, 'FallbackState'); return fallback;
				});
			},
			releaseStateResources:releaseStateResources,
			getTitleInitialized:function() return titleInitialized,
			setTitleInitialized:function(value) titleInitialized = value,
			getTitleClosedState:function() return titleClosedState,
			setTitleClosedState:function(value) titleClosedState = value
		};
	}

	/** Retire destroyed states without discarding constructed, pending states. */
	public function releaseStateResources(state:Dynamic):Void {
		NightmareVisionVideoSprite.destroyForState(state);
		states.remove(cast state);
	}

	public function substateHost():NightmareVisionMusicBeatSubstate.NightmareVisionMusicBeatSubstateHost {
		var host:Dynamic = stateHost();
		host.createSubstateScript = createScriptAt;
		return cast host;
	}

	function report(name:String, callback:String, error:Dynamic):Void {
		if (bootstrapServices != null) bootstrapServices.reportError(name, callback, error);
		trace('[nightmare-vision-script-error] ' + paths.root + '/' + name + '#' + callback + ': ' + Std.string(error));
	}

	function createStateScript(name:String, parent:Dynamic, group:NightmareVisionScriptGroup):NightmareVisionStateScriptLoadResult
		return createScriptAt('states', name, parent, group, true);

	public function createScriptAt(prefix:String, name:String, parent:Dynamic, group:NightmareVisionScriptGroup,
		stateScript:Bool = false):NightmareVisionStateScriptLoadResult {
		ensureAlive();
		var lookup = 'scripts/' + prefix + '/' + name;
		var entry = paths.resolveScript(lookup);
		var sourcePath = entry == null ? lookup : entry.path;
		// MusicBeatState checks the resolved path before looking for a file.
		// MusicBeatSubstate always constructs another source handle.
		if (stateScript && group.exists(sourcePath)) return AlreadyLoaded(sourcePath);
		if (entry == null) return Missing(sourcePath);
		entry.scope = 'state';
		var sourceName = stateScript ? name : sourcePath;
		entry.name = sourceName;
		var context:NightmareVisionScriptBindings.NightmareVisionScriptContext = null;
		context = {
			paths:paths, read:FNFAssets.getText, requireActive:ensureAlive,
			// Source fromFile executes before the wrapper reparents its group.
			parent:function() return FlxG.state,
			configure:function(child) {
				PlayState.seedNightmareVisionCommon(child, paths, prefs, plugins, mods, difficulty, null, entry);
				child.variables.set('game', FlxG.state); child.variables.set('inPlaystate', false);
				NightmareVisionScriptBindings.install(child, context);
			}, report:report
		};
		var module = NightmareVisionScriptModule.fromFile(sourcePath, sourceName, true, null, null, context);
		return module.parsingFailed() ? ParseFailed(sourcePath, module) : Loaded(sourcePath, sourceName, module);
	}

	/** One binding path serves gameplay, persistent plugins and source states. */
	public function install(interp:NightmareVisionScriptInterp):Void {
		ensureAlive();
		mainRuntime.install();
		var view:NightmareVisionFlxGView = cast interp.variables.get('FlxG');
		if (view != null) view.bindStateRequests(switchState, resetState);
		var scope = interp.sourceClassScope();
		var names:Map<String, Dynamic> = ['TitleState'=>NightmareVisionTitleState,
			'MainMenuState'=>NightmareVisionMainMenuState, 'FlashingState'=>NightmareVisionFlashingState,
			'Init'=>NightmareVisionInitState, 'Splash'=>NightmareVisionSplashState];
		for (name => type in names) {
			var constructor = createStateFactory(name);
			var className = name == 'Init' || name == 'Splash' ? name : 'funkin.states.' + name;
			interp.variables.set(name, type); interp.bindImport(className, type);
			scope.bindRuntimeClass(className, type);
			interp.bindConstructorFactory(type, function(args) return constructor(), null);
			scope.bindStaticField(type, 'new', function() return constructor);
		}
		NightmareVisionMainBindings.install(interp, startMeta, mainRuntime);
		NightmareVisionHighscoreBindings.install(interp, highscores, ensureAlive);
		if (bootstrapServices != null && bootstrapServices.scriptTracingReady()) bootstrapServices.configure(interp);
		for (name => type in (['PlayState'=>PlayState, 'FreeplayState'=>FreeplayState]:Map<String, Dynamic>)) {
			var constructor = createStateFactory(name);
			interp.bindConstructorFactory(type, function(args) return constructor(), null);
			scope.bindStaticField(type, 'new', function() return constructor);
		}
		scope.bindStaticField(NightmareVisionTitleState, 'initialized', function() return titleInitialized,
			function(value) return titleInitialized = value);
		scope.bindStaticField(NightmareVisionTitleState, 'closedState', function() return titleClosedState,
			function(value) return titleClosedState = value);
		scope.bindStaticField(NightmareVisionTitleState, 'init', function() return titleInit);
		scope.bindStaticField(NightmareVisionFlashingState, 'leftState', function() return flashingLeftState,
			function(value) return flashingLeftState = value);
		scope.bindStaticField(NightmareVisionMainMenuState, 'curSelected', function() return mainMenuSelected,
			function(value) return mainMenuSelected = value);
		scope.bindStaticField(FreeplayState, 'vocals', function() return menuVocals,
			function(value) return menuVocals = cast value);
		NightmareVisionModConfigBindings.install(interp, config, NightmareVisionMusicBeatState);
		var musicBeatConstructor = createStateFactory('MusicBeatState');
		interp.bindConstructorFactory(NightmareVisionMusicBeatState, function(args) return musicBeatConstructor(), null);
		scope.bindStaticField(NightmareVisionMusicBeatState, 'new', function() return musicBeatConstructor);
		interp.variables.set('MusicBeatSubstate', NightmareVisionMusicBeatSubstate);
		interp.bindImport('funkin.backend.MusicBeatSubstate', NightmareVisionMusicBeatSubstate);
		scope.bindRuntimeClass('funkin.backend.MusicBeatSubstate', NightmareVisionMusicBeatSubstate);
		var substateConstructor = function() return new NightmareVisionMusicBeatSubstate(substateHost());
		interp.bindConstructorFactory(NightmareVisionMusicBeatSubstate, function(args) return substateConstructor(), null);
		scope.bindStaticField(NightmareVisionMusicBeatSubstate, 'new', function() return substateConstructor);
		interp.variables.set('ScriptedState', NightmareVisionScriptedState);
		interp.bindImport('funkin.scripting.ScriptedState', NightmareVisionScriptedState);
		scope.bindRuntimeClass('funkin.scripting.ScriptedState', NightmareVisionScriptedState);
		var scriptedConstructor = function(name:String):FlxState {
			var state = new NightmareVisionScriptedState(name, stateHost());
			states.set(state, 'ScriptedState'); return state;
		};
		interp.bindConstructorFactory(NightmareVisionScriptedState, function(args) return scriptedConstructor(args[0]), null);
		scope.bindStaticField(NightmareVisionScriptedState, 'new', function() return scriptedConstructor);
		NightmareVisionInputBindings.install(interp, paths.root,
			function(owner) {
				ensureAlive();
				return PlayState.activeNightmareVisionInputScope(owner) ?? inputs;
			}, function(owner) return interp.parent);
		scope.bindStaticField(NightmareVisionMusicBeatState, 'getState', function() return function() return FlxG.state);
		scope.bindStaticField(CoolUtil, 'switchState', function() return switchWithTransition);
		scope.bindStaticField(CoolUtil, 'setTransSkip', function() return setTransSkip);
		if (configureScript != null) configureScript(interp);
	}

	function openTransition(state:Dynamic, incoming:Bool, ?complete:Void->Void):Bool {
		var transition = incoming ? config.transitionOut : config.transitionIn;
		var skip = incoming ? FlxTransitionableState.skipNextTransOut : FlxTransitionableState.skipNextTransIn;
		if (skip || transition == NONE) {
			if (incoming) FlxTransitionableState.skipNextTransOut = false;
			else FlxTransitionableState.skipNextTransIn = false;
			return false;
		}
		(cast state:FlxState).openSubState(new NightmareVisionStateTransition(this, transition, incoming, complete));
		if (incoming) FlxTransitionableState.skipNextTransOut = false;
		return true;
	}

	public function release():Void {
		if (released) return;
		released = true;
		FlxG.signals.preStateCreate.remove(onPreStateCreate);
		FlxG.signals.postStateSwitch.remove(onPostStateSwitch);
		for (callback in postCallbacks) FlxG.signals.postStateSwitch.remove(callback);
		postCallbacks.resize(0); states.clear(); redirectNames.clear();
		NightmareVisionPluginHost.releaseOtherOwner('');
		mainRuntime.release();
		if (bootstrapServices != null) {
			try bootstrapServices.release() catch (error:Dynamic) report('session', 'bootstrap-release', error);
			bootstrapServices = null;
		}
		highscores.release();
		inputs.destroy();
		try config.release() catch (error:Dynamic) report('session', 'config-release', error);
		FlxTransitionableState.skipNextTransIn = previousSkipIn;
		FlxTransitionableState.skipNextTransOut = previousSkipOut;
		paths.releaseOwnerAssets(); mods.release(); prefs.release(); difficulty.release();
		configureScript = null;
		menuVocals = null;
		if (active == this) active = null;
	}
}
