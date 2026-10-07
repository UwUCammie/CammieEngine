package;

/** Applies the pinned Nightmare Vision Mods.applyModConfig contract through
	a typed host, keeping native process effects out of owner lookup code. */
@:keep
class NightmareVisionModConfigApplier {
	static inline var DEFAULT_ICON_PATH:String = 'images/branding/icon/icon64.png';
	static inline var DEFAULT_FONT_KEY:String = 'vcr.ttf';

	final host:NightmareVisionModConfigHost;
	var released:Bool = false;

	public function new(host:NightmareVisionModConfigHost) {
		if (host == null) throw '[nightmare-vision-mod-config] Missing native host';
		this.host = host;
	}

	/**
		Mirror Mods.applyModConfig after its successful getPack lookup. The caller
		assigns currentModConfig before entering, so errors preserve that assignment
		and all earlier native effects. `directory` and `root` describe the active
		selection; they can differ from the optional directory used to read `pack`.
	*/
	public function apply(pack:Dynamic, selectedDirectory:String, selectedRoot:String):Void {
		ensureAlive();
		if (pack == null) return;

		// The donor FunkinGame reads the current config directly during the next
		// state switch. Publish the identity as soon as Mods.currentModConfig is set.
		host.updateLiveConfig(selectedDirectory, selectedRoot, pack);
		host.initializeOptions(selectedDirectory, selectedRoot);

		var title:Dynamic = field(pack, 'windowTitle');
		host.setWindowTitle(title == null ? host.defaultAppTitle() : cast title);

		var iconPath = host.resolveSelectedPath(DEFAULT_ICON_PATH);
		var iconFile:Dynamic = field(pack, 'iconFile');
		if (iconFile != null) {
			var configuredIcon = Std.string(iconFile);
			var configuredPath = host.resolveSelectedPath('images/' + configuredIcon + '.png');
			if (!host.pathExists(configuredPath)) host.reportMissingIcon(configuredIcon);
			else iconPath = configuredPath;
		}
		host.setWindowIcon(iconPath);

		host.setTransition(resolveTransition(field(pack, 'defaultTransition')));

		var rpcId:Dynamic = field(pack, 'discordClientID');
		host.setRpcId(rpcId == null ? host.defaultRpcId() : cast rpcId);

		var fontKey:Dynamic = field(pack, 'defaultFont');
		var fontPath:String;
		if (fontKey != null) {
			var configuredFont = host.resolveSelectedFont(cast fontKey);
			fontPath = host.pathExists(configuredFont)
				? host.resolveSelectedFont(cast fontKey) : host.resolveSelectedFont(DEFAULT_FONT_KEY);
		} else fontPath = host.resolveSelectedFont(DEFAULT_FONT_KEY);
		host.setDefaultFont(fontPath);

		applyPrefix('UI_PREFIX', field(pack, 'uiPrefix'), 'UI/');
		applyPrefix('COMBO_PREFIX', field(pack, 'comboPrefix'), 'UI/combo/');
		applyPrefix('RATINGS_PREFIX', field(pack, 'ratingsPrefix'), 'UI/ratings/');
		applyPrefix('COUNTDOWN_PREFIX', field(pack, 'countdownPrefix'), 'UI/countdown/');
	}

	function applyPrefix(fieldName:String, value:Dynamic, fallback:String):Void {
		var selected = value != null && host.selectedDirectoryExists(cast value)
			? cast value : fallback;
		host.setPrefix(fieldName, selected);
	}

	static function resolveTransition(value:Dynamic):NightmareVisionModTransition {
		if (value == null) return SWIPE;
		var raw = Std.string(value);
		switch (raw.toLowerCase()) {
			case 'base', 'swipe': return SWIPE;
			case 'fade': return FADE;
			default: return SCRIPTED(raw);
		}
	}

	static function field(value:Dynamic, name:String):Dynamic
		return value == null ? null : Reflect.field(value, name);

	public function release():Void released = true;

	function ensureAlive():Void {
		if (released) throw '[nightmare-vision-mod-config] This config applier has been released';
	}
}
