package;

import flixel.FlxG;
import flixel.graphics.FlxGraphic;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;
import flixel.tweens.FlxEase;
import flixel.util.FlxColor;
import openfl.display.BitmapData;
import openfl.display.Sprite;
import openfl.events.Event;
import openfl.geom.Matrix;
import PsychAchievementInfo;

/** Owner-bound asset operations used by the popup's source Paths calls. */
typedef PsychAchievementPopupAssets = {
	var fileExists:String->Bool;
	var image:String->FlxGraphic;
	var font:String->String;
}

/** Captured objects and callbacks for one imported Psych owner. */
typedef PsychAchievementPopupHost = {
	var ownerRoot:String;
	var assetsForAchievementMod:Null<String>->PsychAchievementPopupAssets;
	var antialiasing:Void->Bool;
	var phrase:String->String->String;
	var stage:openfl.display.Stage;
	var game:Sprite;
	var now:Void->Float;
	var ownerActive:Void->Bool;
	var registerPopup:PsychAchievementPopup->Void;
	var unregisterPopup:PsychAchievementPopup->Void;
}

/** Native rendering for the pinned Psych achievement toast. This is a display
	object attached to the captured game Sprite, so it survives owner scene
	switches while its service lease remains active. */
@:keep
class PsychAchievementPopup extends Sprite {
	/** The source declares this public field but never assigns or invokes it. */
	public var onFinish:Void->Void = null;
	public var intendedY:Float = 0;

	static inline var WIDTH:Float = 420;
	static inline var HEIGHT:Float = 130;
	static inline var ICON_SIZE:Float = 100;

	final host:PsychAchievementPopupHost;
	final capturedStage:openfl.display.Stage;
	final capturedGame:Sprite;
	var iconGraphic:FlxGraphic;
	var iconGraphicRetained:Bool = false;
	var bitmaps:Array<BitmapData> = [];
	var alphaScale:Float = 1;
	var lerpTime:Float = 0;
	var countedTime:Float = 0;
	var timePassed:Float = -1;
	var destroyed:Bool = false;
	var attached:Bool = false;
	var listeningForResize:Bool = false;
	var listeningForFrame:Bool = false;
	var registrationAttempted:Bool = false;
	var resizeListener:Event->Void;
	var frameListener:Event->Void;

	/** `onFinish` is retained in the signature for source compatibility. The
		pinned donor never stores it or calls it, including on automatic removal. */
	public function new(achieve:String, onFinish:Void->Void, info:PsychAchievementInfo,
		host:PsychAchievementPopupHost) {
		super();
		if (host == null || host.ownerRoot == null || host.ownerRoot == ''
			|| host.stage == null || host.game == null || host.assetsForAchievementMod == null
			|| host.antialiasing == null || host.phrase == null || host.now == null
			|| host.ownerActive == null || host.registerPopup == null || host.unregisterPopup == null)
			throw '[psych-achievement-popup] Missing owner-scoped popup host';
		this.host = host;
		capturedStage = host.stage;
		capturedGame = host.game;
		try build(achieve, info) catch (error:Dynamic) {
			destroy();
			throw error;
		}
	}

	function build(achieve:String, info:PsychAchievementInfo):Void {
		var safeId = cleanAchievementId(achieve);
		if (safeId == null) safeId = '';
		var assets = host.assetsForAchievementMod(info == null ? null : info.mod);
		if (assets == null || assets.fileExists == null || assets.image == null || assets.font == null)
			throw '[psych-achievement-popup] Owner achievement assets are unavailable';

		graphics.beginFill(FlxColor.BLACK);
		graphics.drawRoundRect(0, 0, WIDTH, HEIGHT, 16, 16);

		var graphic:FlxGraphic = null;
		var hasAntialias = host.antialiasing();
		var image = 'achievements/' + safeId;
		var pixelPath = 'images/' + image + '-pixel.png';
		var pixelImage = false;
		if (safeId != '') try pixelImage = assets.fileExists(pixelPath) catch (_:Dynamic) {}
		if (pixelImage) {
			try graphic = assets.image(image + '-pixel') catch (_:Dynamic) {}
			if (graphic != null) hasAntialias = false;
		}
		if (graphic == null && safeId != '') try graphic = assets.image(image) catch (_:Dynamic) {}
		if (graphic == null) try graphic = assets.image('unknownMod') catch (_:Dynamic) {}
		if (graphic == null || graphic.bitmap == null)
			throw '[psych-achievement-popup] Owner and shared achievement icons are unavailable';
		// FNFAssets returns non-persistent graphics with useCount zero. Keep this
		// exact cache entry alive while OpenFL's bitmap fill borrows its bitmap.
		graphic.incrementUseCount();
		iconGraphic = graphic;
		iconGraphicRetained = true;

		var imgX = 15;
		var imgY = 15;
		var imageBitmap = graphic.bitmap;
		graphics.beginBitmapFill(imageBitmap,
			new Matrix(ICON_SIZE / imageBitmap.width, 0, 0, ICON_SIZE / imageBitmap.height, imgX, imgY),
			false, hasAntialias);
		graphics.drawRect(imgX, imgY, ICON_SIZE + 10, ICON_SIZE + 10);

		var name = 'Unknown';
		var description = 'Description not found';
		if (info != null) {
			if (info.name != null) name = host.phrase('achievement_' + safeId, info.name);
			if (info.description != null) description = host.phrase('description_' + safeId, info.description);
		}

		var textX = ICON_SIZE + imgX + 15;
		var textY = imgY + 20;
		var text = new FlxText(0, 0, 270, 'TEST!!!', 16);
		try {
			text.setFormat(assets.font('vcr.ttf'), 16, FlxColor.WHITE, FlxTextAlign.LEFT);
			drawTextAt(text, name, textX, textY);
			drawTextAt(text, description, textX, textY + 30);
			graphics.endFill();
		} catch (error:Dynamic) {
			disposeTemporaryText(text);
			throw error;
		}
		disposeTemporaryText(text);

		// Keep stable callback objects for removal. Haxe can materialize a fresh
		// bound-method closure for each field access, while OpenFL removes by
		// callback identity.
		resizeListener = onResize;
		capturedStage.addEventListener(Event.RESIZE, resizeListener);
		listeningForResize = true;
		frameListener = update;
		addEventListener(Event.ENTER_FRAME, frameListener);
		listeningForFrame = true;
		capturedGame.addChild(this);
		attached = true;

		var screenHeight = FlxG.height;
		alphaScale = capturedStage.stageHeight / screenHeight;
		x = 20 * alphaScale;
		y = -HEIGHT * alphaScale;
		scaleX = alphaScale;
		scaleY = alphaScale;
		intendedY = 20;

		registrationAttempted = true;
		host.registerPopup(this);
	}

	function drawTextAt(text:FlxText, value:String, textX:Float, textY:Float):Void {
		text.text = value;
		text.updateHitbox();
		var clonedBitmap:BitmapData = text.graphic.bitmap.clone();
		bitmaps.push(clonedBitmap);
		graphics.beginBitmapFill(clonedBitmap, new Matrix(1, 0, 0, 1, textX, textY), false, false);
		// Keep the donor's drawRect dimensions and glyph placement exactly.
		graphics.drawRect(textX, textY, text.width + textX, text.height + textY);
	}

	function disposeTemporaryText(text:FlxText):Void {
		if (text == null) return;
		var bitmap:BitmapData = text.graphic == null ? null : text.graphic.bitmap;
		if (bitmap != null) {
			bitmap.dispose();
			bitmap.disposeImage();
		}
		text.destroy();
	}

	function update(event:Event):Void {
		if (destroyed) return;
		var ownerIsActive = false;
		try ownerIsActive = host.ownerActive() catch (_:Dynamic) {}
		if (!ownerIsActive) {
			destroy();
			return;
		}
		if (timePassed < 0) {
			timePassed = host.now();
			return;
		}

		var time = host.now();
		var elapsed:Float = (time - timePassed) / 1000;
		timePassed = time;
		if (elapsed >= 0.5) return;

		countedTime += elapsed;
		if (countedTime < 3) {
			lerpTime = Math.min(1, lerpTime + elapsed);
			y = ((FlxEase.elasticOut(lerpTime) * (intendedY + HEIGHT)) - HEIGHT) * alphaScale;
		} else {
			y -= FlxG.height * 2 * elapsed * alphaScale;
			if (y <= -HEIGHT * alphaScale) destroy();
		}
	}

	function onResize(event:Event):Void {
		if (destroyed) return;
		var mult = capturedStage.stageHeight / FlxG.height;
		scaleX = mult;
		scaleY = mult;
		x = (mult / alphaScale) * x;
		y = (mult / alphaScale) * y;
		alphaScale = mult;
	}

	/** Remove only this popup's display object, listeners and private text copies. */
	public function destroy():Void {
		if (destroyed) return;
		destroyed = true;
		if (attached) try {
			if (capturedGame.contains(this)) capturedGame.removeChild(this);
		} catch (_:Dynamic) {}
		attached = false;
		if (listeningForResize) try capturedStage.removeEventListener(Event.RESIZE, resizeListener) catch (_:Dynamic) {}
		listeningForResize = false;
		if (listeningForFrame) try removeEventListener(Event.ENTER_FRAME, frameListener) catch (_:Dynamic) {}
		listeningForFrame = false;
		resizeListener = null;
		frameListener = null;
		if (iconGraphicRetained) {
			iconGraphicRetained = false;
			var retainedGraphic = iconGraphic;
			iconGraphic = null;
			if (retainedGraphic != null) try retainedGraphic.decrementUseCount() catch (_:Dynamic) {}
		}
		deleteClonedBitmaps();
		if (registrationAttempted) try host.unregisterPopup(this) catch (_:Dynamic) {}
		registrationAttempted = false;
	}

	function deleteClonedBitmaps():Void {
		if (bitmaps == null) return;
		for (clonedBitmap in bitmaps) if (clonedBitmap != null) {
			clonedBitmap.dispose();
			clonedBitmap.disposeImage();
		}
		bitmaps = null;
	}

	static function cleanAchievementId(value:String):Null<String> {
		if (value == null) return null;
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		if (clean == '' || StringTools.startsWith(clean, '/') || clean.indexOf(':') >= 0
			|| clean.indexOf(String.fromCharCode(0)) >= 0) return null;
		for (segment in clean.split('/'))
			if (segment == '' || segment == '.' || segment == '..') return null;
		return clean;
	}
}
