package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.text.FlxText;
import flixel.util.FlxColor;

/**
	Small menu overlay for the shared import-refresh coordinator. Each attached
	menu may poll it independently; `ImportRefreshManager.browseTick()` is the
	coordinator's idempotent status pump, so state transitions do not own jobs.
*/
class ImportRefreshProgressBar extends FlxTypedGroup<FlxSprite> {
	static inline var PANEL_WIDTH:Int = 440;
	static inline var PANEL_HEIGHT:Int = 82;
	static inline var PANEL_MARGIN:Int = 16;
	static inline var TOAST_SECONDS:Float = 2.4;

	public var panel:FlxSprite;
	public var progressTrack:FlxSprite;
	public var progressFill:FlxSprite;
	public var statusText:FlxText;

	var toastRemaining:Float = 0;
	var showingCompletion:Bool = false;
	var displayedFraction:Float = 0;

	public function new() {
		super();
		active = true;
		visible = false;

		panel = new FlxSprite().makeGraphic(PANEL_WIDTH, PANEL_HEIGHT, FlxColor.fromRGB(10, 12, 20, 235));
		panel.alpha = 0.94;
		progressTrack = new FlxSprite().makeGraphic(PANEL_WIDTH - PANEL_MARGIN * 2, 10,
			FlxColor.fromRGB(43, 47, 60));
		progressFill = new FlxSprite().makeGraphic(PANEL_WIDTH - PANEL_MARGIN * 2, 10,
			FlxColor.fromRGB(92, 203, 255));
		progressFill.origin.set(0, 0);
		statusText = new FlxText(0, 0, PANEL_WIDTH - PANEL_MARGIN * 2, "", 16);
		statusText.color = FlxColor.WHITE;
		statusText.wordWrap = false;
		panel.scrollFactor.set(0, 0);
		progressTrack.scrollFactor.set(0, 0);
		progressFill.scrollFactor.set(0, 0);
		statusText.scrollFactor.set(0, 0);
		add(panel);
		add(progressTrack);
		add(progressFill);
		add(statusText);
		positionOverlay();
	}

	/** Poll once per menu update, even while hidden, so newly queued work can
	 * become visible without a state transition or a one-shot event listener. */
	public override function update(elapsed:Float):Void {
		super.update(elapsed);
		#if sys
		var state:Dynamic;
		try {
			state = ImportRefreshManager.browseTick();
		} catch (error:Dynamic) {
			state = {busy: false, label: "Import refresh failed: " + Std.string(error),
				fraction: 0.0, complete: false, changed: false, blocked: true};
		}
		#else
		var state:Dynamic = null;
		#end
		if (state == null) {
			visible = false;
			showingCompletion = false;
			toastRemaining = 0;
			return;
		}

		var busy = boolField(state, "busy");
		var blocked = boolField(state, "blocked");
		var complete = boolField(state, "complete");
		var changed = boolField(state, "changed");
		var completionEdge = complete && changed && !showingCompletion;
		if (completionEdge) toastRemaining = TOAST_SECONDS;
		showingCompletion = complete && changed;
		if (!busy && !blocked && toastRemaining > 0) {
			toastRemaining -= Math.max(0, elapsed);
			if (toastRemaining < 0) toastRemaining = 0;
		}

		visible = busy || blocked || toastRemaining > 0;
		if (!visible) return;

		positionOverlay();
		displayedFraction = fractionField(state);
		progressFill.scale.x = displayedFraction;
		progressFill.color = blocked ? FlxColor.fromRGB(255, 176, 79) : FlxColor.fromRGB(92, 203, 255);
		var label = stringField(state, "label");
		if (blocked && (label == null || StringTools.trim(label) == "")) label = "Import refresh needs attention";
		if (busy && (label == null || StringTools.trim(label) == "")) label = "Refreshing imported mods…";
		if (!busy && !blocked && (label == null || StringTools.trim(label) == "")) label = "Imported mods refreshed";
		statusText.text = label;
	}

	/** Exposed for small UI tests and callers that want a stable displayed
	 * fraction without reaching through Flixel's sprite scale. */
	public function progressFraction():Float return displayedFraction;

	static function boolField(value:Dynamic, name:String):Bool {
		return Reflect.field(value, name) == true;
	}

	static function stringField(value:Dynamic, name:String):String {
		var field:Dynamic = Reflect.field(value, name);
		return field == null ? "" : Std.string(field);
	}

	static function fractionField(value:Dynamic):Float {
		var field:Dynamic = Reflect.field(value, "fraction");
		var fraction:Float = field == null ? 0 : Std.parseFloat(Std.string(field));
		if (Math.isNaN(fraction) || fraction == Math.POSITIVE_INFINITY || fraction == Math.NEGATIVE_INFINITY) return 0;
		if (fraction < 0) return 0;
		if (fraction > 1) return 1;
		return fraction;
	}

	function positionOverlay():Void {
		var x = Std.int(Math.max(8, (FlxG.width - PANEL_WIDTH) * 0.5));
		var y = PANEL_MARGIN;
		panel.setPosition(x, y);
		statusText.setPosition(x + PANEL_MARGIN, y + 10);
		progressTrack.setPosition(x + PANEL_MARGIN, y + 58);
		progressFill.setPosition(x + PANEL_MARGIN, y + 58);
	}
}
