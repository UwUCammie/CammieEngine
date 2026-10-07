package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxState;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.text.FlxText;
import flixel.util.FlxColor;

/**
	Shared progress card for Import Settings jobs and automatic import refreshes.
	Menu instances poll the coordinator independently; `browseTick()` is its
	idempotent status pump, so state transitions do not own background jobs.
*/
class ImportRefreshProgressBar extends FlxTypedGroup<FlxSprite> {
	static inline var PANEL_WIDTH:Int = 660;
	static inline var PANEL_HEIGHT:Int = 170;
	static inline var PANEL_MIN_WIDTH:Int = 240;
	static inline var PANEL_MARGIN:Int = 22;
	static inline var PANEL_TOP:Int = 16;
	static inline var EMBEDDED_PANEL_TOP:Int = 226;
	static inline var TRACK_HEIGHT:Int = 12;
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

	var foregroundOwner:Null<FlxState>;
	var statusProvider:Null<Void->Dynamic>;
	var embedded:Bool = false;
	var polledStatusIsLocal:Bool = false;
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
	var localMeasurements:ImportRefreshProgress;
	var menuLane:Bool = false;
	var laneLeft:Float = 0;
	var laneTop:Float = 0;
	var laneRightRatio:Float = 1;
	var laneRightPadding:Float = 0;

	/** Reserve menu chrome without coupling this shared renderer to a state class. */
	public function setMenuLane(left:Float, top:Float, rightRatio:Float, rightPadding:Float):Void {
		menuLane = true;
		laneLeft = left; laneTop = top; laneRightRatio = rightRatio; laneRightPadding = rightPadding;
		hasRenderedText = false;
		positionOverlay();
	}

	public function new(owner:FlxState, ?statusProvider:Void->Dynamic, ?embedded:Bool = false) {
		super();
		foregroundOwner = owner;
		this.statusProvider = statusProvider;
		this.embedded = embedded;
		active = true;
		visible = false;

		panel = new FlxSprite().makeGraphic(PANEL_WIDTH, PANEL_HEIGHT, FlxColor.fromRGB(10, 12, 20, 235));
		panel.alpha = 0.96;
		panel.origin.set(0, 0);
		progressTrack = new FlxSprite().makeGraphic(PANEL_WIDTH - PANEL_MARGIN * 2, TRACK_HEIGHT,
			FlxColor.fromRGB(43, 47, 60));
		progressFill = new FlxSprite().makeGraphic(PANEL_WIDTH - PANEL_MARGIN * 2, TRACK_HEIGHT,
			FlxColor.fromRGB(92, 203, 255));
		progressFill.origin.set(0, 0);
		progressTrack.origin.set(0, 0);

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
		if (!isForeground()) {
			visible = false;
			hasPolledStatus = false;
			polledStatus = null;
			polledStatusIsLocal = false;
			return;
		}
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
			return;
		}

		var busy = boolField(state, "busy");
		var blocked = boolField(state, "blocked");
		var complete = boolField(state, "complete");
		// Completion and warnings belong to the explicit import details/result UI.
		// A background status must never start or restart a popup on a new screen.
		var backgroundBusy:Dynamic = Reflect.field(state, "backgroundBusy");
		visible = polledStatusIsLocal ? busy : (backgroundBusy == null ? busy : backgroundBusy == true);
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

	function isForeground():Bool {
		return foregroundOwner != null && FlxG.state == foregroundOwner && foregroundOwner.active
			&& foregroundOwner.exists && foregroundOwner.subState == null;
	}

	public override function draw():Void {
		// FlxState may draw its background while a substate pauses parent updates.
		if (!isForeground()) {
			visible = false;
			hasPolledStatus = false;
			polledStatus = null;
			polledStatusIsLocal = false;
			return;
		}
		if (visible) super.draw();
	}

	public override function destroy():Void {
		super.destroy();
		foregroundOwner = null;
		statusProvider = null;
	}

	/** Force a fresh provider/coordinator snapshot after starting or consuming a local job. */
	public function invalidateStatus(?resetMeasurements:Bool = true):Void {
		hasPolledStatus = false;
		polledStatus = null;
		polledStatusIsLocal = false;
		statusPollElapsed = 0;
		textRefreshElapsed = 0;
		hasRenderedText = false;
		visible = false;
		if (resetMeasurements) localMeasurements = null;
	}

	function pollStatus():Void {
		if (statusProvider != null) {
			var local:Dynamic = null;
			try {
				local = statusProvider();
			} catch (error:Dynamic) {
				#if sys
				ImportRefreshManager.reportFailure(Std.string(error));
				#end
			}
			if (local != null) {
				polledStatus = addLocalMeasurements(local);
				polledStatusIsLocal = true;
				return;
			}
		}
		localMeasurements = null;
		polledStatusIsLocal = false;
		#if sys
		var state:Dynamic;
		try {
			state = ImportRefreshManager.browseTick();
		} catch (error:Dynamic) {
			ImportRefreshManager.reportFailure(Std.string(error));
			state = {busy: false, label: "Import refresh failed: " + Std.string(error),
				fraction: 0.0, complete: false, changed: false, blocked: true};
		}
		#else
		var state:Dynamic = null;
		#end
		polledStatus = state;
	}

	function addLocalMeasurements(state:Dynamic):Dynamic {
		var now = haxe.Timer.stamp();
		if (localMeasurements == null) localMeasurements = new ImportRefreshProgress(now);
		localMeasurements.update(state, now);
		var measured = localMeasurements.snapshot(now, -1);
		var result:Dynamic = {};
		for (field in Reflect.fields(state)) Reflect.setField(result, field, Reflect.field(state, field));
		for (field in Reflect.fields(measured)) {
			if (field == "queueRemaining") continue;
			if (field == "phase" || field == "current" || field == "completed" || field == "total"
				|| Reflect.field(state, field) == null)
				Reflect.setField(result, field, Reflect.field(measured, field));
		}
		var total = intField(result, "total", 0);
		var completed = intField(result, "completed", 0);
		Reflect.setField(result, "fraction", total <= 0 ? 0.0 : Math.min(0.99, completed / total));
		// Manual imports have no coordinator queue. Keep the sentinel through the
		// presentation adapter instead of rendering the helper's queue size.
		Reflect.setField(result, "queueRemaining", -1);
		return result;
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
		var queueRemaining = intField(state, "queueRemaining", 0);
		var timing = elapsed < 0 ? "Elapsed unavailable" : "Elapsed " + formatDuration(elapsed, false);
		timing += eta >= 0 ? " | Phase ETA ~" + formatDuration(eta, true) : " | Phase ETA unavailable";
		if (queueRemaining >= 0) timing += " | Queue " + queueRemaining;
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
		if (menuLane)
			currentPanelWidth = Std.int(Math.max(120, Math.min(PANEL_WIDTH,
				FlxG.width * laneRightRatio - laneRightPadding - laneLeft)));
		contentWidth = currentPanelWidth - PANEL_MARGIN * 2;
		graphicsWidthScale = contentWidth / (PANEL_WIDTH - PANEL_MARGIN * 2);
		var x = Std.int(Math.max(8, (FlxG.width - currentPanelWidth) * 0.5));
		var y = embedded ? EMBEDDED_PANEL_TOP : PANEL_TOP;
		if (menuLane) { x = Std.int(laneLeft); y = Std.int(laneTop); }
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
