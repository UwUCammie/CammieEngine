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
	static inline var PANEL_WIDTH:Int = 660;
	static inline var PANEL_HEIGHT:Int = 170;
	static inline var PANEL_MIN_WIDTH:Int = 240;
	static inline var PANEL_MARGIN:Int = 22;
	static inline var PANEL_TOP:Int = 16;
	static inline var TRACK_HEIGHT:Int = 12;
	static inline var TOAST_SECONDS:Float = 2.4;
	static inline var TEXT_REFRESH_SECONDS:Float = 0.25;
	static inline var INDETERMINATE_WIDTH:Float = 0.24;

	public var panel:FlxSprite;
	public var progressTrack:FlxSprite;
	public var progressFill:FlxSprite;
	/** Kept as the public headline field for existing callers and UI probes. */
	public var statusText:FlxText;
	public var phaseText:FlxText;
	public var currentFileText:FlxText;
	public var activityText:FlxText;
	public var timingText:FlxText;

	var toastRemaining:Float = 0;
	var showingCompletion:Bool = false;
	var displayedFraction:Float = 0;
	var statusPollElapsed:Float = 0;
	var hasPolledStatus:Bool = false;
	var polledStatus:Dynamic;
	var textRefreshElapsed:Float = 0;
	var hasRenderedText:Bool = false;
	var indeterminateElapsed:Float = 0;
	var currentPanelWidth:Int = PANEL_WIDTH;
	var contentWidth:Int = PANEL_WIDTH - PANEL_MARGIN * 2;
	var trackX:Float = 0;
	var trackY:Float = 0;
	var trackWidth:Float = PANEL_WIDTH - PANEL_MARGIN * 2;
	var graphicsWidthScale:Float = 1;

	public function new() {
		super();
		active = true;
		visible = false;

		panel = new FlxSprite().makeGraphic(PANEL_WIDTH, PANEL_HEIGHT, FlxColor.fromRGB(10, 12, 20, 235));
		panel.alpha = 0.96;
		progressTrack = new FlxSprite().makeGraphic(PANEL_WIDTH - PANEL_MARGIN * 2, TRACK_HEIGHT,
			FlxColor.fromRGB(43, 47, 60));
		progressFill = new FlxSprite().makeGraphic(PANEL_WIDTH - PANEL_MARGIN * 2, TRACK_HEIGHT,
			FlxColor.fromRGB(92, 203, 255));
		progressFill.origin.set(0, 0);

		// FlxText's engine default font is used throughout the menus. Its normal
		// font keeps file paths and counters easier to scan than mod display fonts.
		statusText = new FlxText(0, 0, PANEL_WIDTH - PANEL_MARGIN * 2, "", 20);
		statusText.color = FlxColor.WHITE;
		statusText.wordWrap = false;
		phaseText = new FlxText(0, 0, PANEL_WIDTH - PANEL_MARGIN * 2, "", 15);
		phaseText.color = FlxColor.fromRGB(224, 230, 242);
		phaseText.wordWrap = false;
		currentFileText = new FlxText(0, 0, PANEL_WIDTH - PANEL_MARGIN * 2, "", 14);
		currentFileText.color = FlxColor.fromRGB(212, 220, 234);
		currentFileText.wordWrap = false;
		activityText = new FlxText(0, 0, PANEL_WIDTH - PANEL_MARGIN * 2, "", 13);
		activityText.color = FlxColor.fromRGB(179, 190, 209);
		activityText.wordWrap = false;
		timingText = new FlxText(0, 0, PANEL_WIDTH - PANEL_MARGIN * 2, "", 13);
		timingText.color = FlxColor.fromRGB(179, 190, 209);
		timingText.wordWrap = false;

		panel.scrollFactor.set(0, 0);
		progressTrack.scrollFactor.set(0, 0);
		progressFill.scrollFactor.set(0, 0);
		statusText.scrollFactor.set(0, 0);
		phaseText.scrollFactor.set(0, 0);
		currentFileText.scrollFactor.set(0, 0);
		activityText.scrollFactor.set(0, 0);
		timingText.scrollFactor.set(0, 0);
		add(panel);
		add(progressTrack);
		add(progressFill);
		add(statusText);
		add(phaseText);
		add(currentFileText);
		add(activityText);
		add(timingText);
		positionOverlay();
	}

	/** Keep polling even while hidden so newly queued work becomes visible. The
	 * 250ms cadence is fast enough for UI handoffs and avoids work at frame rate. */
	public override function update(elapsed:Float):Void {
		super.update(elapsed);
		statusPollElapsed += Math.max(0, elapsed);
		if (!hasPolledStatus || statusPollElapsed >= TEXT_REFRESH_SECONDS) {
			pollStatus();
			statusPollElapsed = 0;
			hasPolledStatus = true;
		}
		var state = polledStatus;
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
		updateProgress(state, busy, blocked, complete, elapsed);
		textRefreshElapsed += Math.max(0, elapsed);
		if (!hasRenderedText || textRefreshElapsed >= TEXT_REFRESH_SECONDS) {
			renderText(state, busy, blocked, complete);
			textRefreshElapsed = 0;
			hasRenderedText = true;
		}
	}

	function pollStatus():Void {
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
		polledStatus = state;
	}

	/** Exposed for small UI tests and callers that want a stable displayed
	 * fraction without reaching through Flixel's sprite scale. */
	public function progressFraction():Float return displayedFraction;

	function updateProgress(state:Dynamic, busy:Bool, blocked:Bool, complete:Bool, elapsed:Float):Void {
		displayedFraction = fractionField(state);
		var total = intField(state, "total", 0);
		var indeterminate = busy && total <= 0;
		progressFill.color = blocked ? FlxColor.fromRGB(255, 176, 79) : FlxColor.fromRGB(92, 203, 255);
		if (complete) displayedFraction = 1;

		if (indeterminate) {
			indeterminateElapsed += Math.max(0, elapsed) * 0.8;
			var cycle = indeterminateElapsed % 2;
			var position = cycle <= 1 ? cycle : 2 - cycle;
			var visibleWidth = trackWidth * INDETERMINATE_WIDTH;
			progressFill.scale.x = graphicsWidthScale * INDETERMINATE_WIDTH;
			progressFill.x = trackX + position * Math.max(0, trackWidth - visibleWidth);
		} else {
			progressFill.scale.x = graphicsWidthScale * displayedFraction;
			progressFill.x = trackX;
		}
		progressFill.y = trackY;
	}

	function renderText(state:Dynamic, busy:Bool, blocked:Bool, complete:Bool):Void {
		var label = stringField(state, "label");
		if (blocked && StringTools.trim(label) == "") label = "Import refresh needs attention";
		if (busy && StringTools.trim(label) == "") label = "Refreshing imported mods...";
		if (!busy && !blocked && StringTools.trim(label) == "") label = complete ? "Imported mods refreshed" : "Import refresh";
		var titleCharacters = charsForWidth(contentWidth, 20);
		statusText.text = busy ? ellipsizeMiddle(label, titleCharacters) : ellipsizeEnd(label, titleCharacters);

		if (!busy) {
			phaseText.text = "";
			currentFileText.text = "";
			activityText.text = "";
			timingText.text = "";
			return;
		}

		var rawPhase = stringField(state, "phase");
		var phase = readablePhase(rawPhase);
		var unit = countUnit(stringField(state, "phase"));
		var completed = Math.max(0, intField(state, "completed", 0));
		var total = Math.max(0, intField(state, "total", 0));
		var phaseWidthCharacters = phaseCharsForWidth(contentWidth);
		var phaseLine:String;
		if (total > 0) {
			if (completed > total) completed = total;
			phaseLine = phaseWidthCharacters < 45 ? "Phase: " + unitTitle(unit) + " | " + (total - completed) + " left | " + completed + "/" + total :
				compactPhaseLine(phase, " | " + (total - completed) + " " + unit + " left | " + completed + "/" + total + " done");
		} else if (completed > 0) {
			if (unit == "folders") phaseLine = phaseWidthCharacters < 45 ? "Phase: Folders | " + completed + " checked | unknown" :
				compactPhaseLine(phase, " | " + completed + " folders checked | unknown");
			else phaseLine = phaseWidthCharacters < 45 ? "Phase: " + unitTitle(unit) + " | " + completed + " processed | unknown" :
				compactPhaseLine(phase, " | " + completed + " " + unit + " processed | remaining unknown");
		} else {
			phaseLine = phaseWidthCharacters < 45 ? "Phase: " + unitTitle(unit) + " | total unknown" :
				compactPhaseLine(phase, " | total not yet known");
		}
		phaseText.text = phaseLine;

		var current = displayCurrentPath(stringField(state, "current"));
		if (StringTools.trim(current) == "") current = "Waiting for file details...";
		var filePrefix = "Current file: ";
		var fileCharacters = Std.int(Math.max(3, charsForWidth(contentWidth, 14) - filePrefix.length));
		currentFileText.text = filePrefix + ellipsizeMiddle(current, fileCharacters);

		var activityAge = floatField(state, "activityAgeSeconds", -1);
		var ageText = activityAge < 0 ? "not reported" : activityAge < 1 ? "just now" : formatDuration(activityAge, true) + " ago";
		activityText.text = ellipsizeEnd("Last progress: " + ageText, charsForWidth(contentWidth, 13));

		var elapsed = floatField(state, "elapsedSeconds", -1);
		var eta = floatField(state, "etaSeconds", -1);
		var queueRemaining = Math.max(0, intField(state, "queueRemaining", 0));
		var timing = eta >= 0 ? "Phase ETA ~" + formatDuration(eta, true) : "Phase ETA unavailable";
		timing += " | Queue remaining " + queueRemaining;
		timing += elapsed < 0 ? " | Elapsed unavailable" : " | Elapsed " + formatDuration(elapsed, false);
		timingText.text = ellipsizeEnd(timing, charsForWidth(contentWidth, 13));
	}

	static function boolField(value:Dynamic, name:String):Bool {
		return Reflect.field(value, name) == true;
	}

	static function stringField(value:Dynamic, name:String):String {
		var field:Dynamic = Reflect.field(value, name);
		return field == null ? "" : Std.string(field);
	}

	static function intField(value:Dynamic, name:String, fallback:Int):Int {
		var field:Dynamic = Reflect.field(value, name);
		if (field == null) return fallback;
		var parsed = Std.parseInt(Std.string(field));
		return parsed == null ? fallback : parsed;
	}

	static function floatField(value:Dynamic, name:String, fallback:Float):Float {
		var field:Dynamic = Reflect.field(value, name);
		if (field == null) return fallback;
		var parsed = Std.parseFloat(Std.string(field));
		if (Math.isNaN(parsed) || parsed == Math.POSITIVE_INFINITY || parsed == Math.NEGATIVE_INFINITY) return fallback;
		return parsed;
	}

	static function fractionField(value:Dynamic):Float {
		var fraction = floatField(value, "fraction", 0);
		if (fraction < 0) return 0;
		if (fraction > 1) return 1;
		return fraction;
	}

	static function readablePhase(phase:String):String {
		phase = StringTools.trim(phase == null ? "" : phase.toLowerCase());
		return switch (phase) {
			case "checking-import-receipts": "Checking saved imports";
			case "retaining-source": "Retaining source files";
			case "checking-retained-source": "Checking retained source";
			case "scanning-retained-source": "Scanning retained source";
			case "preparing-import": "Preparing import";
			case "scan-roots": "Scanning folders";
			case "scan-discovery": "Discovering folders";
			case "scan-songs": "Scanning songs";
			case "scan-assets": "Scanning assets";
			case "songs": "Importing songs";
			case "assets": "Importing asset folders";
			case "charts": "Processing charts";
			case "checking-output": "Checking staged output";
			case "checking-installed": "Checking installed content";
			case "preparing-output": "Preparing imported output";
			case "backing-up-import": "Backing up import files";
			case "publishing-import": "Publishing imported files";
			case "cleaning-up-import": "Cleaning up temporary files";
			case "": "Preparing refresh";
			default:
				var readable = StringTools.trim(StringTools.replace(StringTools.replace(phase, "-", " "), "_", " "));
				readable.charAt(0).toUpperCase() + readable.substr(1);
		};
	}

	static function countUnit(phase:String):String {
		phase = phase == null ? "" : phase.toLowerCase();
		if (phase == "scan-roots" || phase == "scan-discovery" || phase == "scan-assets" || phase == "assets") return "folders";
		if (phase.indexOf("song") >= 0) return "songs";
		if (phase == "checking-output" || phase == "checking-installed" || phase == "backing-up-import"
			|| phase == "publishing-import" || phase == "cleaning-up-import") return "items";
		return "files";
	}

	static function unitTitle(unit:String):String {
		return unit == null || unit == "" ? "Work" : unit.charAt(0).toUpperCase() + unit.substr(1);
	}

	function compactPhaseLine(phase:String, suffix:String):String {
		var prefix = "Phase: ";
		var maximum = phaseCharsForWidth(contentWidth);
		var phaseCharacters = maximum - prefix.length - suffix.length;
		if (phaseCharacters < 3) {
			suffix = ellipsizeEnd(suffix, Std.int(Math.max(4, maximum - prefix.length - 3)));
			phaseCharacters = maximum - prefix.length - suffix.length;
		}
		return prefix + ellipsizeMiddle(phase, Std.int(Math.max(3, phaseCharacters))) + suffix;
	}

	static function displayCurrentPath(current:String):String {
		if (current == null || current == "") return "";
		var normalized = StringTools.replace(current, "\\", "/");
		var cacheMarker = "import-cache/sources/";
		var cacheIndex = normalized.lastIndexOf(cacheMarker);
		if (cacheIndex >= 0) {
			var contentMarker = "/content/";
			var contentIndex = normalized.indexOf(contentMarker, cacheIndex + cacheMarker.length);
			if (contentIndex >= 0) return normalized.substr(contentIndex + contentMarker.length);
		}
		return normalized;
	}

	static function charsForWidth(width:Float, fontSize:Int):Int {
		return Std.int(Math.max(3, width / (fontSize * 0.80)));
	}

	static function phaseCharsForWidth(width:Float):Int {
		return Std.int(Math.max(3, width / (15 * 0.70)));
	}

	static function ellipsizeEnd(text:String, maxCharacters:Int):String {
		if (text == null || maxCharacters <= 0 || text.length <= maxCharacters) return text;
		if (maxCharacters <= 3) return "...";
		return text.substr(0, maxCharacters - 3) + "...";
	}

	static function ellipsizeMiddle(text:String, maxCharacters:Int):String {
		if (text == null || maxCharacters <= 0 || text.length <= maxCharacters) return text;
		if (maxCharacters <= 3) return "...";
		var remaining = maxCharacters - 3;
		var left = Std.int(Math.ceil(remaining / 2));
		var right = remaining - left;
		return text.substr(0, left) + "..." + (right > 0 ? text.substr(text.length - right) : "");
	}

	static function formatDuration(seconds:Float, roundUp:Bool):String {
		if (Math.isNaN(seconds) || seconds < 0) seconds = 0;
		var whole = roundUp ? Math.ceil(seconds) : Math.floor(seconds);
		var hours = Std.int(whole / 3600);
		var minutes = Std.int((whole % 3600) / 60);
		var remainder = Std.int(whole % 60);
		if (hours > 0) return hours + "h " + minutes + "m";
		if (minutes > 0) return minutes + "m " + (remainder < 10 ? "0" : "") + remainder + "s";
		return remainder + "s";
	}

	function positionOverlay():Void {
		currentPanelWidth = Std.int(Math.max(PANEL_MIN_WIDTH, Math.min(PANEL_WIDTH, FlxG.width - PANEL_MARGIN * 2)));
		contentWidth = currentPanelWidth - PANEL_MARGIN * 2;
		graphicsWidthScale = contentWidth / (PANEL_WIDTH - PANEL_MARGIN * 2);
		var x = Std.int(Math.max(8, (FlxG.width - currentPanelWidth) * 0.5));
		var y = PANEL_TOP;
		var textX = x + PANEL_MARGIN;
		panel.scale.x = currentPanelWidth / PANEL_WIDTH;
		panel.setPosition(x, y);
		statusText.width = contentWidth;
		phaseText.width = contentWidth;
		currentFileText.width = contentWidth;
		activityText.width = contentWidth;
		timingText.width = contentWidth;
		statusText.setPosition(textX, y + 10);
		phaseText.setPosition(textX, y + 38);
		trackX = textX;
		trackY = y + 63;
		trackWidth = contentWidth;
		progressTrack.scale.x = graphicsWidthScale;
		progressTrack.setPosition(trackX, trackY);
		currentFileText.setPosition(textX, y + 82);
		activityText.setPosition(textX, y + 105);
		timingText.setPosition(textX, y + 128);
	}
}
