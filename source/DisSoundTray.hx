package;

import flixel.FlxG;
import flixel.FlxBasic;
import flixel.FlxSprite;
import flixel.sound.FlxSound;
import flixel.text.FlxText;
import openfl.display.Bitmap;
import openfl.display.BitmapData;
import openfl.display.Sprite;
import openfl.text.TextField;
import openfl.text.TextFormat;
import openfl.text.TextFormatAlign;
import openfl.events.Event;
import flixel.util.FlxTimer;

class DisSoundTray extends Sprite {
	private var soundTray:Bitmap;
	private var mutedTxt:TextField;
	private var vols:Array<Bitmap> = [];
	private var activated:Bool = false;
	private var distime:Float = 200;
	private var lastVol:Float = 0;
	private var lastW:Int = 0;
	private var lastH:Int = 0;
	public function new() {
		super();

		lastVol = FlxG.sound.volume;

		//soundTray = new FlxSprite(FlxG.width, FlxG.height - 200).makeGraphic(120, 200, 0xFF404040);
		soundTray = new Bitmap(new BitmapData(70, 150, true, 0x7F404040));
		soundTray.visible = false;
		addChild(soundTray);

		for (i in 0...10) {
			var vol = new Bitmap(new BitmapData(20 + 2*i, 10, false, 0xFF808080));
			vols.push(vol);
			addChild(vol);
		}

		//mutedTxt = new FlxText(FlxG.width, FlxG.height, 0, "MUTED", 24);
		mutedTxt = new TextField();
		mutedTxt.text = 'MUTED';
		mutedTxt.width = 100;
		mutedTxt.height = 30;
		var dtf:TextFormat = new TextFormat('assets/fonts/vcr.ttf', 24, 0xffffff);
		mutedTxt.defaultTextFormat = dtf;
		mutedTxt.visible = false;
		addChild(mutedTxt);

		// we live on the raw flash stage (real window pixels) while FlxG.width/height
		// stay frozen at whatever the window was at startup (1280x720) - so in fullscreen
		// the tray would get "hidden" at x=1280, which is still ON screen. lay out from
		// the stage's actual size instead, and redo it whenever the window resizes
		reposition();
		if (FlxG.stage != null)
			FlxG.stage.addEventListener(Event.RESIZE, onResize);

		addEventListener(Event.ENTER_FRAME, update);
	}

	// pin everything to the bottom right of the actual window
	private function reposition() {
		var w:Float = FlxG.stage != null ? FlxG.stage.stageWidth : FlxG.width;
		var h:Float = FlxG.stage != null ? FlxG.stage.stageHeight : FlxG.height;

		soundTray.y = h - 150;
		for (i in 0...vols.length)
			vols[i].y = soundTray.y + 120 - 12*i;
		mutedTxt.x = w - mutedTxt.width;
		mutedTxt.y = h - mutedTxt.height;
	}

	private function onResize(_) {
		reposition();
		if (FlxG.stage != null) {
			lastW = FlxG.stage.stageWidth;
			lastH = FlxG.stage.stageHeight;
		}
		// glued to the right edge when showing, parked fully past it when hidden
		var w:Float = FlxG.stage != null ? FlxG.stage.stageWidth : FlxG.width;
		soundTray.x = w - (soundTray.visible ? soundTray.width : 0);
	}

	private function update(_) {
		// fallback for missed RESIZE events / fullscreen toggles: redo the layout
		// if the window changed size since we last looked
		if (FlxG.stage != null && (FlxG.stage.stageWidth != lastW || FlxG.stage.stageHeight != lastH))
			onResize(null);

		var stageW:Float = FlxG.stage != null ? FlxG.stage.stageWidth : FlxG.width;

		if (!activated) {
			distime -= 1;
			if (distime <= 0)
				activated = true;
		}

		if (soundTray.x < stageW && activated) {
			soundTray.x += soundTray.width * 0.02;
			if (soundTray.x >= stageW) {
				soundTray.visible = false;
				soundTray.x = stageW; // park it fully past the right edge
				if (FlxG.save.isBound) {
					FlxG.save.data.mute = FlxG.sound.muted;
					FlxG.save.data.volume = FlxG.sound.volume;
				}
			}
		}

		if (lastVol != FlxG.sound.volume) {
			activated = false;
			soundTray.x = stageW - soundTray.width;
			soundTray.visible = true;
			FlxG.sound.play('assets/sounds/clickText' + TitleState.soundExt, 0.8);
			distime = 200;
		}

		for (i in 0...vols.length) {
			vols[i].x = soundTray.x + 10 + i;
			if (i + 1 <= Math.round(FlxG.sound.volume * 10))
				vols[i].alpha = 1;
			else
				vols[i].alpha = 0.5;
		}
		mutedTxt.visible = FlxG.sound.muted;
		lastVol = FlxG.sound.volume;
	}
}
