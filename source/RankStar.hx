package;

import flixel.FlxSprite;
import lime.utils.Assets;
import lime.system.System;
import flash.display.BitmapData;
#if sys
import sys.io.File;
import haxe.io.Path;
import openfl.utils.ByteArray;

import sys.FileSystem;
#end
import haxe.Json;
import haxe.format.JsonParser;
import tjson.TJSON;
using StringTools;
class RankStar extends FlxSprite {
	public var sprTracker:FlxSprite;
	public var starNum:Int = 0;
	public var selectoffset:Float = 0;

	public var song:String = '';
	public var diff:Int = 0;
	public var inCard:Bool = false;
	public var focused:Bool = false;
	public var showLegend:Bool = false;
	public var density:Null<ChartDifficultyAnalysis.ChartDensity>;
	public var cardX:Float = 0;
	public var cardY:Float = 0;
	var pulseTime:Float = 0;
	var legend:flixel.text.FlxText;
	var shadowGlow:FlxSprite;
	var ratingLabel:String = '';
	var difficultyLabel:String = '';
	public function configureCard(value:Null<ChartDifficultyAnalysis.ChartDensity>):Void {
		inCard = true; density = value; whitenCard();
		if (ChartDifficultyAnalysis.shadow(density)) createShadowGlow();
		legend = new flixel.text.FlxText(0, 0, 42, '', 10);
		legend.setFormat('assets/fonts/vcr.ttf', 10, 0xFFFFFFFF, CENTER);
		legend.scrollFactor.set();
		difficultyLabel = DifficultyManager.getDiffName(diff).toUpperCase().substr(0, 4);
		ratingLabel = density == null ? '?/20' : Std.string(Std.int(density.difficulty)) + '/20';
		legend.text = difficultyLabel + '\n' + ratingLabel;
	}
	function whitenCard():Void {
		// A subtle gradient stays inside the star silhouette, with no rectangular backing.
		var bitmap = new BitmapData(32, 32, true, 0);
		var shape = new openfl.display.Shape();
		var gradient = new openfl.geom.Matrix();
		gradient.createGradientBox(32, 32, Math.PI / 2);
		shape.graphics.beginGradientFill(openfl.display.GradientType.LINEAR, [0xFFFFFF, 0xE3E7F0], [1, 1], [0, 255], gradient);
		shape.graphics.lineStyle(2.4, 0x25332B, 1, true, NORMAL, ROUND, ROUND);
		for (i in 0...11) {
			var phase = -Math.PI / 2 + i * Math.PI / 5; var radius = i % 2 == 0 ? 14 : 6;
			var px = 16 + Math.cos(phase) * radius; var py = 16 + Math.sin(phase) * radius;
			if (i == 0) shape.graphics.moveTo(px,py); else shape.graphics.lineTo(px,py);
		}
		shape.graphics.endFill(); bitmap.draw(shape);
		loadGraphic(bitmap); setGraphicSize(26,26); updateHitbox();
	}
	function createShadowGlow():Void {
		// The light travels around a fixed star silhouette, never an orbit of round blobs.
		// Bake once into a shared, padded animation; drawing does not allocate or blur.
		var key = 'freeplay-density-star-halo';
		var graphic = flixel.FlxG.bitmap.get(key);
		shadowGlow = new FlxSprite();
		if (graphic != null) shadowGlow.loadGraphic(graphic, true, 52, 52);
		else {
			var sheet = new BitmapData(52 * 32, 52, true, 0);
			for (frame in 0...32) {
				var bitmap = new BitmapData(52, 52, true, 0);
				var shape = new openfl.display.Shape();
				var gradient = new openfl.geom.Matrix();
				gradient.createGradientBox(38, 38, frame * Math.PI * 2 / 32, 7, 7);
				shape.graphics.beginGradientFill(openfl.display.GradientType.LINEAR,
					[0x65408E, 0xBE94F5], [0.45, 1], [0, 255], gradient);
				for (i in 0...11) {
					var phase = -Math.PI / 2 + i * Math.PI / 5; var radius = i % 2 == 0 ? 18 : 8;
					var px = 26 + Math.cos(phase) * radius; var py = 26 + Math.sin(phase) * radius;
					if (i == 0) shape.graphics.moveTo(px, py); else shape.graphics.lineTo(px, py);
				}
				shape.graphics.endFill(); bitmap.draw(shape);
				bitmap.applyFilter(bitmap, bitmap.rect, new openfl.geom.Point(), new openfl.filters.BlurFilter(2, 2, 1));
				sheet.copyPixels(bitmap, bitmap.rect, new openfl.geom.Point(frame * 52, 0)); bitmap.dispose();
			}
			shadowGlow.loadGraphic(sheet, true, 52, 52, false, key);
		}
		shadowGlow.animation.add('swirl', [for (i in 0...32) i], 16, true);
		shadowGlow.animation.play('swirl');
		shadowGlow.scrollFactor.set(); shadowGlow.antialiasing = true;
	}
	override public function draw():Void {
		if (!inCard) { super.draw(); return; }
		var savedColor = color; var savedAlpha = alpha; var savedX = x; var savedY = y;
		if (ChartDifficultyAnalysis.shadow(density)) {
			shadowGlow.cameras = cameras; shadowGlow.alpha = savedAlpha;
			shadowGlow.setPosition(savedX - 13, savedY - 13); shadowGlow.angle = angle;
			shadowGlow.draw();
			color = 0xFF000000;
		} else color = ChartDifficultyAnalysis.color(density);
		alpha = savedAlpha; setPosition(savedX, savedY); super.draw();
		if (legend != null) {
			var text = showLegend ? difficultyLabel + '\n' + ratingLabel : ratingLabel;
			if (legend.text != text) legend.text = text;
			legend.setPosition(savedX - 8, cardY + (showLegend ? 28 : 26)); legend.alpha = savedAlpha;
			legend.color = focused ? 0xFFFFD166 : 0xFFCFD8E5;
			legend.cameras = cameras; legend.draw();
		}
		color = savedColor;
	}
	override public function destroy():Void {
		if (legend != null) legend.destroy();
		if (shadowGlow != null) shadowGlow.destroy();
		super.destroy();
	}

	public function new(song:String, diff:Int) {
		super();

		this.song = song;
		this.diff = diff;

		checkStar();
		//trace(song + '($diff) - ' + rankNum);
		setGraphicSize(Std.int(width * 0.4));
		antialiasing = true;
		scrollFactor.set();
	}

	public function checkStar() {
		var rankNum = Highscore.getFCLevel(song, diff);

		var defaultDiff = DifficultyManager.getDefaultForDiff(diff);
		var diffName = '';
		if (FileSystem.exists('assets/images/ranks/rank' + rankNum + '-' + defaultDiff + '.png'))
			diffName = '-' + defaultDiff;

		loadGraphic(FNFAssets.getBitmapData('assets/images/ranks/rank' + rankNum + diffName + '.png'));
		if (inCard) whitenCard();
	}

	override function update(elapsed:Float) {
		super.update(elapsed);
		if (inCard) {
			pulseTime += elapsed;
			if (shadowGlow != null) shadowGlow.update(elapsed);
			var jump = focused ? Math.abs(Math.sin(pulseTime * 4)) : 0;
			setPosition(cardX, cardY - jump * 5); angle = focused ? Math.sin(pulseTime * 4) * 7 : 0;
			return;
		}

		if (sprTracker != null) {
			setPosition(sprTracker.x + (sprTracker.width - 50) + (width * 0.4 * starNum), sprTracker.y - 10 - selectoffset);
			alpha = sprTracker.alpha;
		}
	}
}
