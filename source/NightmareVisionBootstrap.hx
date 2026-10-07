package;

/** Native and owner-scoped operations used by the source Init state.
	TState is the host's concrete state base type, usually FlxState. */
interface INightmareVisionBootstrapHost<TState> {
	public function initializeControls():Void;
	public function loadPreferences():Void;
	public function loadHighscores():Void;
	public function restoreCompletedWeeks():Void;
	public function applyDefaultAntialiasing():Void;
	public function initializeDiscord():Void;
	public function pushGlobalMods():Void;
	public function loadTopMod():Void;
	/** Apply the Flixel settings and persistent music setup in donor order. */
	public function configureFlixelServices():Void;
	public function initializeFunkinScript():Void;
	public function initializeHotReloadPlugin():Void;
	public function initializeModPlugin():Void;
	public function initializeDebugTextPlugin():Void;
	public function initializeFullScreenPlugin():Void;
	/** These methods are no-ops when their donor compile-time feature is off. */
	public function initializeVideoPluginWhenEnabled():Void;
	public function initializeTracyWhenEnabled():Void;
	/** ModPlugin.populate runs plugin onLoad callbacks, which may request a state. */
	public function populateModPlugin():Void;
	public function retainPermanentMenuMusicAsset():Void;
	public function createBaseState():Void;

	/** These values mirror Main.startMeta and source ClientPrefs. */
	public function startMetaSkipsSplash():Bool;
	public function splashScreenEnabled():Bool;
	/** Return factories for the already-typed source metadata classes. */
	public function initialStateConstructor():Void->TState;
	public function splashStateConstructor():Void->TState;
	/** Submit the constructor closure through the captured source navigation host. */
	public function switchStartup(constructor:Void->TState):Void;
}

/** Pure orchestration for the pinned source Init.create() contract. */
@:keep
class NightmareVisionBootstrap<TState> {
	final host:INightmareVisionBootstrapHost<TState>;

	public function new(host:INightmareVisionBootstrapHost<TState>) {
		if (host == null) throw '[nightmare-vision-bootstrap] Missing source host';
		this.host = host;
	}

	/** Run one complete source Init pass. Errors propagate at their source
		boundary, so later operations do not run after a failed prerequisite. */
	public function run():Void {
		host.initializeControls();
		host.loadPreferences();
		host.loadHighscores();
		host.restoreCompletedWeeks();
		host.applyDefaultAntialiasing();
		host.initializeDiscord();
		host.pushGlobalMods();
		host.loadTopMod();
		host.configureFlixelServices();
		host.initializeFunkinScript();
		host.initializeHotReloadPlugin();
		host.initializeModPlugin();
		host.initializeDebugTextPlugin();
		host.initializeFullScreenPlugin();
		host.initializeVideoPluginWhenEnabled();
		host.initializeTracyWhenEnabled();
		host.populateModPlugin();
		host.retainPermanentMenuMusicAsset();
		host.createBaseState();

		var nextState = host.startMetaSkipsSplash() || !host.splashScreenEnabled()
			? host.initialStateConstructor()
			: host.splashStateConstructor();
		host.switchStartup(nextState);
	}
}
