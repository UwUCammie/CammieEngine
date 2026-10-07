package;

import flixel.FlxG;
import flixel.FlxState;
import NightmareVisionBootstrap.INightmareVisionBootstrapHost;

/** Native effects for the pinned source Init sequence, scoped to one family. */
class NightmareVisionInitHost implements INightmareVisionBootstrapHost<FlxState> {
	final session:NightmareVisionStateSession;
	final createNativeBase:Void->Void;
	public function new(session:NightmareVisionStateSession, createNativeBase:Void->Void) {
		this.session = session; this.createNativeBase = createNativeBase;
	}
	public function initializeControls():Void session.initializeSourceControls();
	public function loadPreferences():Void session.loadSourcePreferences();
	public function loadHighscores():Void session.loadHighscores();
	public function restoreCompletedWeeks():Void session.restoreCompletedWeeks();
	public function applyDefaultAntialiasing():Void session.services().applyDefaultAntialiasing();
	public function initializeDiscord():Void {
		#if cpp
		if (!RuntimeSmokeHarness.enabled()) Discord.DiscordClient.initialize();
		#end
	}
	public function pushGlobalMods():Void session.mods.pushGlobalMods();
	public function loadTopMod():Void session.mods.loadTopMod();
	public function configureFlixelServices():Void session.services().configureFlixelServices();
	public function initializeFunkinScript():Void session.services().initializeFunkinScript();
	public function initializeHotReloadPlugin():Void session.services().initializeHotReloadPlugin();
	public function initializeModPlugin():Void session.mountPlugins(false);
	public function initializeDebugTextPlugin():Void session.services().initializeDebugTextPlugin();
	public function initializeFullScreenPlugin():Void session.services().initializeFullScreenPlugin();
	public function initializeVideoPluginWhenEnabled():Void session.services().initializeVideoPluginWhenEnabled();
	public function initializeTracyWhenEnabled():Void session.services().initializeTracyWhenEnabled();
	public function populateModPlugin():Void session.populatePlugins();
	public function retainPermanentMenuMusicAsset():Void {
		var key = session.paths.getPath('music/freakyMenu.ogg', null, false);
		session.paths.getOwnerAssetCache().currentTrackedSounds.addPermanentKey(key);
	}
	public function createBaseState():Void {
		createNativeBase(); session.bootstrapComplete = true;
	}
	public function startMetaSkipsSplash():Bool return session.startMeta.skipSplash;
	public function splashScreenEnabled():Bool return session.prefs.view.toggleSplashScreen;
	public function initialStateConstructor():Void->FlxState return session.startupConstructor(session.startMeta.initialState);
	public function splashStateConstructor():Void->FlxState return session.createStateFactory('Splash');
	public function switchStartup(constructor:Void->FlxState):Void session.switchState(constructor);
}
