package;

import flixel.FlxG;
import lime.graphics.Image;
import Discord.DiscordClient;

/** Native configuration services captured for a whole imported owner session.
	No callback captures a PlayState, so persistent plugins and later songs share
	the selected package's options, paths and presentation safely. */
@:keep
class NightmareVisionModConfigRuntime implements NightmareVisionModConfigHost {
	public static var active(default, null):NightmareVisionModConfigRuntime;
	public final mods:NightmareVisionModsContext;
	public var paths(default, null):NightmareVisionPaths;
	final persistentPaths:NightmareVisionPaths;
	public final options:NightmareVisionSourceOptions;
	public var transitionIn:NightmareVisionModTransition = ENGINE_DEFAULT;
	public var transitionOut:NightmareVisionModTransition = ENGINE_DEFAULT;
	public var selectedDirectory(default, null):String;
	public var selectedRoot(default, null):String;
	public var configuredIcon(default, null):Image;
	public var liveConfig(get, never):Dynamic;
	function get_liveConfig():Dynamic return mods.currentModConfig;
	final previousTitle:String;
	final previousRpc:String;
	var released:Bool = false;

	public function new(mods:NightmareVisionModsContext, paths:NightmareVisionPaths) {
		if (mods == null || paths == null || mods.ownerRoot != paths.root)
			throw '[nightmare-vision-mod-config] Config services require the same owner lease';
		if (active != null && active != mods.nativeConfig) {
			try active.release() catch (error:Dynamic)
				trace('[nightmare-vision-mod-config-release] ' + Std.string(error));
		}
		this.mods = mods; this.paths = this.persistentPaths = paths;
		previousTitle = FlxG.stage.window.title;
		previousRpc = DiscordClient.getClientId();
		options = new NightmareVisionSourceOptions(paths.root, new CodenameOwnerSaveData(paths.root));
		options.bindFamily(function(directory) return directory == mods.currentModDirectory
			? mods.selectedRoot() : mods.rootForDirectory(directory),
			function(root) return new CodenameOwnerSaveData(root), function() return mods.globalMods.copy());
		mods.optionSession = options;
		mods.nativeConfig = this;
		active = this;
		mods.bindConfigHost(this);
	}

	/** A later song has a fresh state facade; source Paths statics still retain
	 * the current configuration. Keep only it and the plugin's captured facade. */
	public function attachPaths(next:NightmareVisionPaths):Void {
		ensureAlive();
		if (next == null || next.root != mods.ownerRoot)
			throw '[nightmare-vision-mod-config] Paths belongs to a different owner lease';
		next.DEFAULT_FONT = paths.DEFAULT_FONT;
		next.UI_PREFIX = paths.UI_PREFIX;
		next.COMBO_PREFIX = paths.COMBO_PREFIX;
		next.RATINGS_PREFIX = paths.RATINGS_PREFIX;
		next.COUNTDOWN_PREFIX = paths.COUNTDOWN_PREFIX;
		paths = next;
	}

	public function defaultAppTitle():String return lime.app.Application.current.meta.get('name');
	public function defaultRpcId():String return #if cpp '1252033037680513115' #else '' #end;
	public function defaultUiPrefix():String return persistentPaths.hudProfile.uiPrefix;
	public function resolveSelectedPath(relativePath:String):String return paths.getPath(relativePath, null, true);
	public function resolveSelectedFont(key:String):String return paths.font(key);
	public function pathExists(path:String):Bool {
		var scoped = paths.scopeAssetPath(path);
		return scoped != null && paths.exists(scoped);
	}
	public function selectedDirectoryExists(relativePath:String):Bool
		return paths.isDirectory(paths.mods() + '/images/' + relativePath);

	public function updateLiveConfig(directory:String, root:String, pack:Dynamic):Void {
		ensureAlive();
		if (root == null || !mods.authorizedRoots().contains(root) || mods.currentModConfig != pack)
			throw '[nightmare-vision-mod-config] Config identity does not match the selected package';
		selectedDirectory = directory; selectedRoot = root;
	}
	public function initializeOptions(directory:String, root:String):Void options.initForOwner(directory, root);
	public function setWindowTitle(title:String):Void {ensureAlive(); FlxG.stage.window.title = title;}
	public function setWindowIcon(path:String):Void {
		ensureAlive();
		if (!pathExists(path)) {trace('[nightmare-vision-mod-config] Could not find Icon ' + path); return;}
		var bytes = new NightmareVisionFunkinAssets(paths).getBytes(path);
		configuredIcon = Image.fromBytes(bytes);
		FlxG.stage.window.setIcon(configuredIcon);
	}
	public function reportMissingIcon(iconFile:String):Void
		trace('[nightmare-vision-mod-config] Could not find Icon ' + iconFile);
	/** Source config assigns the two variables; the source state factory consumes
	 * them when an actual transition is requested, rather than switching here. */
	public function setTransition(transition:NightmareVisionModTransition):Void {
		ensureAlive(); transitionIn = transition; transitionOut = transition;
	}
	public function setRpcId(clientId:String):Void {ensureAlive(); DiscordClient.setClientId(clientId);}
	public function setDefaultFont(path:String):Void {
		ensureAlive(); paths.DEFAULT_FONT = path; persistentPaths.DEFAULT_FONT = path;
	}
	public function setPrefix(field:String, value:String):Void {
		ensureAlive();
		switch (field) {
			case 'UI_PREFIX': paths.UI_PREFIX = persistentPaths.UI_PREFIX = value;
			case 'COMBO_PREFIX': paths.COMBO_PREFIX = persistentPaths.COMBO_PREFIX = value;
			case 'RATINGS_PREFIX': paths.RATINGS_PREFIX = persistentPaths.RATINGS_PREFIX = value;
			case 'COUNTDOWN_PREFIX': paths.COUNTDOWN_PREFIX = persistentPaths.COUNTDOWN_PREFIX = value;
			default: throw '[nightmare-vision-mod-config] Unknown source Paths prefix: ' + field;
		}
	}

	public function release():Void {
		if (released) return;
		var failure:Dynamic = null;
		try options.release() catch (error:Dynamic) failure = error;
		if (active == this) {
			try FlxG.stage.window.title = previousTitle catch (error:Dynamic) {if (failure == null) failure = error;}
			try DiscordClient.setClientId(previousRpc) catch (error:Dynamic) {if (failure == null) failure = error;}
			try {
				var icon = haxe.Resource.getBytes('cammie-native-window-icon');
				if (icon != null) FlxG.stage.window.setIcon(Image.fromBytes(icon));
			} catch (error:Dynamic) {if (failure == null) failure = error;}
			active = null;
		}
		released = true;
		if (failure != null) throw failure;
	}

	function ensureAlive():Void {
		if (released || mods.released) throw '[nightmare-vision-mod-config] Config owner has been released';
	}
}
