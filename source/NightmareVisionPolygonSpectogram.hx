package;

import flixel.FlxG;
import flixel.math.FlxMath;
import flixel.util.FlxColor;
import lime.utils.Int16Array;
import NightmareVisionSpectogramEnums.SPECDIRECTION;
import NightmareVisionSpectogramEnums.VISTYPE;

/** Source PolygonSpectogram implementation on the host FlxStrip draw path. */
@:keep
class NightmareVisionPolygonSpectogram extends NightmareVisionMeshRender {
	var sampleRate:Int = 44100;

	@:keep public var vis:NightmareVisionSpectogramAudioData;
	@:keep public var visType:VISTYPE = UPDATED;
	@:keep public var daHeight:Float = FlxG.height;
	@:keep public var realtimeVisLenght:Float = 0.2;
	@:keep public var realtimeStartOffset:Float = 0;

	var numSamples:Int = 0;
	var setBuffer:Bool = false;
	@:keep public var audioData:Null<Int16Array>;

	@:keep public var detail:Float = 1;
	@:keep public var thickness:Float = 2;
	@:keep public var waveAmplitude:Int = 100;
	@:keep public var direction:SPECDIRECTION = VERTICAL;

	public function new(?daSound:Dynamic, ?col:FlxColor = FlxColor.WHITE,
		?height:Float = 720, ?detail:Float = 1, ?dir:SPECDIRECTION = VERTICAL) {
		super(0, 0, col);
		if (daSound != null) setSound(daSound);
		if (height != null) this.daHeight = height;
		this.direction = dir;
		this.detail = detail;
	}

	@:keep public function setSound(daSound:Dynamic):Void {
		vis = new NightmareVisionSpectogramAudioData(daSound);
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (visType == UPDATED) {
			#if cpp
			var smokeProfileAt = RuntimeSmokeHarness.profileEnabled() ? haxe.Timer.stamp() : 0.0;
			#end
			realtimeVis();
			#if cpp
			if (smokeProfileAt > 0)
				RuntimeSmokeHarness.profileSection('nmv-spectrum-update', haxe.Timer.stamp() - smokeProfileAt);
			#end
		}
	}

	/** Generates the source waveform section. start is milliseconds, seconds is seconds. */
	@:keep public function generateSection(start:Float = 0, seconds:Float = 1):Void {
		checkAndSetBuffer();
		if (!setBuffer) return;
		clear();
		start = Math.max(start, 0);
		var samplesToGen:Int = Std.int(sampleRate * seconds);
		if (samplesToGen == 0) return;
		var startSample:Int = Std.int(FlxMath.remapToRange(start, 0, vis.length, 0, numSamples));
		if (startSample < 0 || startSample >= numSamples) return;
		if (samplesToGen <= 0 || startSample + samplesToGen > numSamples)
			samplesToGen = numSamples - startSample;

		var prevX:Float = 0;
		var prevY:Float = 0;
		var funnyPixels:Int = Std.int(daHeight * detail);
		if (funnyPixels <= 0) return;
		for (i in 0...funnyPixels) {
			var sampleApprox:Int = Std.int(FlxMath.remapToRange(i, 0, funnyPixels,
				startSample, startSample + samplesToGen));
			var balanced = NightmareVisionSpectogramAudioData.getBalanced(audioData, sampleApprox);
			var posX = balanced * waveAmplitude;
			var posY = i / funnyPixels * daHeight;
			var currentX:Float;
			var currentY:Float;
			switch (direction) {
				case VERTICAL:
					currentX = posX;
					currentY = posY;
				case HORIZONTAL:
					currentX = posY;
					currentY = posX;
			}
			build_quad(prevX, prevY, prevX + thickness, prevY,
				currentX, currentY, currentX + thickness, currentY + thickness);
			prevX = currentX;
			prevY = currentY;
		}
	}

	var curTime:Float = 0;

	function realtimeVis():Void {
		if (vis == null || vis.snd == null) return;
		if (curTime == vis.time) return;
		if (vis.playing) curTime = vis.time;
		else if (Math.abs(curTime - vis.time) > 10) curTime = FlxMath.lerp(curTime, vis.time, 0.5);
		// Preserve the donor's final direct assignment (the preceding lerp does
		// not survive it) and its end-window test in milliseconds.
		curTime = vis.time;
		if (vis.time < vis.length - realtimeVisLenght)
			generateSection(vis.time + realtimeStartOffset, realtimeVisLenght);
	}

	@:keep public function checkAndSetBuffer():Void {
		if (vis == null) return;
		vis.checkAndSetBuffer();
		if (vis.setBuffer) {
			audioData = vis.audioData;
			sampleRate = vis.sampleRate;
			setBuffer = vis.setBuffer;
			numSamples = vis.numSamples;
		}
	}

	override public function destroy():Void {
		if (vis != null) {
			vis.release();
			vis = null;
		}
		audioData = null;
		numSamples = 0;
		setBuffer = false;
		super.destroy();
	}
}
