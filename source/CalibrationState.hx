package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.text.FlxText;
import flixel.tweens.FlxTween;
import flixel.util.FlxColor;

/**
 * Audio offset calibration. A metronome tick plays on the same clock as the
 * falling markers, so on a laggy output (Bluetooth etc.) you hear the tick
 * AFTER its marker crosses the line - tap SPACE with what you HEAR and the
 * average tap-vs-beat delta is exactly the latency your offset should
 * compensate (same convention as OptionsHandler.options.offset, see
 * Note.hx's strumTime getter which adds it).
 */
class CalibrationState extends MusicBeatState {
	// 60 BPM: tap attribution snaps at HALF a beat, and the user's ~245ms
	// Bluetooth latency sat exactly on the old 500ms beat's 250ms boundary -
	// taps a hair past it rounded to the NEXT tick and were recorded as big
	// negative "early" deltas. at 1s beats the boundary (500ms) is beyond
	// any real output latency, so every tap is attributed to the tick they
	// actually heard
	static inline var BEAT_MS:Float = 1000; // 60 BPM
	static inline var HORIZON_BEATS:Int = 4; // markers in flight
	static inline var HISTORY:Int = 24; // taps averaged
	static inline var MAX_DELTA:Float = 400; // taps further off-beat are ignored

	var markerGrp:FlxTypedGroup<CalMarker>;
	var lineY:Float = 150;
	var travelDist:Float;

	var nextBeat:Float = 0;
	var nextMarker:Float = 0;
	var beatCount:Int = 0;

	var deltas:Array<Float> = [];
	var suggested:Float = 0;
	var lastTapDelta:Float = Math.NaN;
	var lastTapKept:Bool = false;
	var appliedFlash:FlxText;

	var infoText:FlxText;
	var hintText:FlxText;

	override function create() {
		// the options-menu music would fight the metronome
		if (FlxG.sound.music != null)
			FlxG.sound.music.stop();

		// decode the ticks up front so the first beat doesn't hitch
		FlxG.sound.cache('assets/sounds/intro3.ogg');
		FlxG.sound.cache('assets/sounds/introGo.ogg');

		Conductor.bpmChangeMap = [];
		Conductor.changeBPM(60 / (BEAT_MS / 1000));
		Conductor.offset = 0;
		Conductor.songPosition = -1500; // lead-in before beat 0
		nextBeat = 0;
		nextMarker = 0;

		var bg = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, 0xFF000000);
		add(bg);

		var line = new FlxSprite(0, lineY).makeGraphic(FlxG.width, 6, FlxColor.WHITE);
		line.alpha = 0.7;
		add(line);

		markerGrp = new FlxTypedGroup<CalMarker>();
		add(markerGrp);
		travelDist = FlxG.height - lineY - 60;

		infoText = new FlxText(0, FlxG.height * 0.35, FlxG.width, "", 24);
		infoText.setFormat("assets/fonts/vcr.ttf", 24, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		add(infoText);

		appliedFlash = new FlxText(0, lineY + 30, FlxG.width, "", 20);
		appliedFlash.setFormat("assets/fonts/vcr.ttf", 20, FlxColor.LIME, CENTER, OUTLINE, FlxColor.BLACK);
		add(appliedFlash);

		hintText = new FlxText(0, FlxG.height - 70, FlxG.width, "", 16);
		hintText.setFormat("assets/fonts/vcr.ttf", 16, 0xFF9A9A9A, CENTER, OUTLINE, FlxColor.BLACK);
		hintText.text = "SPACE: tap when you HEAR the tick   LEFT/RIGHT: nudge (hold SHIFT for x10)   ENTER: apply   ESC: back";
		add(hintText);

		super.create();
	}

	override function update(elapsed:Float) {
		// no music bed - the state clock IS the metronome clock
		Conductor.songPosition += FlxG.elapsed * 1000;

		while (Conductor.songPosition >= nextBeat) {
			var accent:Bool = beatCount % 4 == 0;
			FlxG.sound.play(accent ? 'assets/sounds/introGo.ogg' : 'assets/sounds/intro3.ogg', accent ? 0.7 : 0.5);
			pulseLine();
			nextBeat += BEAT_MS;
			beatCount++;
		}
		while (nextMarker < Conductor.songPosition + HORIZON_BEATS * BEAT_MS) {
			var marker = new CalMarker(nextMarker, laneColor(Std.int(nextMarker / BEAT_MS)));
			markerGrp.add(marker);
			nextMarker += BEAT_MS;
		}
		for (m in markerGrp.members) {
			if (m == null)
				continue;
			var p:Float = (m.strumTime - Conductor.songPosition) / BEAT_MS; // 1 = far, 0 = at the line
			if (p <= -0.4) {
				markerGrp.remove(m, true);
				m.destroy();
				continue;
			}
			m.y = lineY + p * travelDist;
			m.x = FlxG.width / 2 - m.width / 2;
		}

		if (FlxG.keys.justPressed.SPACE)
			registerTap();

		var mult:Float = FlxG.keys.pressed.SHIFT ? 10 : 1;
		if (FlxG.keys.justPressed.LEFT && deltas.length > 0)
			suggested -= 1 * mult;
		if (FlxG.keys.justPressed.RIGHT && deltas.length > 0)
			suggested += 1 * mult;

		if (controls.BACK) {
			LoadingState.loadAndSwitchState(new SaveDataState());
			super.update(elapsed);
			return;
		}
		if (FlxG.keys.justPressed.ENTER && deltas.length >= 4)
			applyOffset();

		refreshText();
		super.update(elapsed);
	}

	function registerTap() {
		var pos = Conductor.songPosition;
		var nearest = Math.round(pos / BEAT_MS);
		var delta = pos - nearest * BEAT_MS;
		lastTapDelta = delta;
		if (Math.abs(delta) > MAX_DELTA) {
			lastTapKept = false;
			return; // not near a beat - don't punish
		}
		lastTapKept = true;
		deltas.push(delta);
		if (deltas.length > HISTORY)
			deltas.shift();
		suggested = 0;
		for (d in deltas)
			suggested += d;
		suggested /= deltas.length;
	}

	function applyOffset() {
		var options = OptionsHandler.options;
		options.offset = HelperFunctions.truncateFloat(suggested, 1);
		OptionsHandler.options = options; // setter persists to the options file
		FlxG.sound.play('assets/sounds/custom_menu_sounds/'
			+ CoolUtil.parseJson(FNFAssets.getText("assets/sounds/custom_menu_sounds/custom_menu_sounds.json")).customMenuConfirm
			+ '/confirmMenu' + TitleState.soundExt, 0.7);
		appliedFlash.text = "Offset applied: " + options.offset + "ms";
		new flixel.util.FlxTimer().start(0.8, function(_) {
			LoadingState.loadAndSwitchState(new SaveDataState());
		});
	}

	function pulseLine() {
		var pulse = new FlxSprite(0, lineY - 17).makeGraphic(FlxG.width, 40, FlxColor.WHITE);
		pulse.alpha = 0.35;
		add(pulse);
		FlxTween.tween(pulse, {alpha: 0}, 0.25, {onComplete: function(_) {
			remove(pulse);
			pulse.destroy();
		}});
	}

	function laneColor(beat:Int):FlxColor {
		// the four note lane colors, like real arrows
		return switch (beat % 4) {
			case 0: 0xFFC24B99;
			case 1: 0xFF00FFFF;
			case 2: 0xFF12FA05;
			default: 0xFFF9393F;
		}
	}

	function refreshText() {
		var lastTap:String = "";
		if (!Math.isNaN(lastTapDelta)) {
			var tapWord:String = lastTapDelta >= 0 ? "late" : "early";
			lastTap = lastTapKept
				? '   last tap: ${Math.round(lastTapDelta)}ms $tapWord'
				: '   last tap ignored (way off the tick)';
		}
		if (deltas.length == 0) {
			infoText.text = "tap SPACE when you HEAR the tick\npositive = you hear the game LATE (normal on Bluetooth)\nthe marker crosses when the tick is PLAYED, not when you hear it" + lastTap;
			return;
		}
		var spread = 0.0;
		for (d in deltas) {
			var e = d - suggested;
			spread += e * e;
		}
		spread = Math.sqrt(spread / deltas.length);
		var quality:String = spread < 15 ? "steady" : (spread < 35 ? "okay - keep tapping" : "taps are inconsistent, keep tapping");
		var avgWord:String = suggested >= 0 ? "late" : "early";
		infoText.text = 'taps: ${deltas.length}/$HISTORY   avg: ${HelperFunctions.truncateFloat(suggested, 1)}ms $avgWord   jitter: +-${HelperFunctions.truncateFloat(spread, 1)}ms ($quality)'
			+ '\nsuggested offset: ${HelperFunctions.truncateFloat(suggested, 1)}ms   (current: ${OptionsHandler.options.offset}ms)'
			+ lastTap
			+ (deltas.length >= 4 ? "   ENTER applies" : '   (${4 - deltas.length} more taps before ENTER works)');
	}
}

class CalMarker extends FlxSprite {
	public var strumTime:Float;

	public function new(strumTime:Float, color:FlxColor) {
		super();
		this.strumTime = strumTime;
		makeGraphic(100, 100, color);
	}
}
