package;

import flixel.FlxCamera;
import animate.FlxAnimate;
import animate.FlxAnimateFrames;
import flixel.graphics.FlxGraphic;
import flixel.graphics.frames.FlxFrame;
import flixel.graphics.frames.FlxFrame.FlxFrameAngle;
import flixel.graphics.frames.FlxFramesCollection;
import flixel.math.FlxAngle;
import flixel.math.FlxMatrix;
import flixel.math.FlxPoint;
import flixel.math.FlxRect;
import flixel.system.FlxAssets.FlxGraphicAsset;
import openfl.display.BitmapData;

using StringTools;

typedef CodenameSpriteAnimationData = {
	var forced:Bool;
}

/**
	The classless-sprite ABI used by Codename song and stage scripts.
	FlxAnimate also renders ordinary Flixel graphics, so this keeps the basic
	prefix/indices path while allowing owner-scoped Animate atlases to play.
*/
class CodenameFunkinSprite extends FlxAnimate {
	public var extra:Map<String, Dynamic> = new Map();
	public var name:String = '';
	public var zoomFactor:Float = 1;
	public var angleFactor:Float = 1;
	public var debugMode:Bool = false;
	public var animEnabled:Bool = true;
	public var zoomFactorEnabled:Bool = true;
	public var angleFactorEnabled:Bool = true;
	public var animOffsets:Map<String, FlxPoint> = new Map();
	public var animDatas:Map<String, CodenameSpriteAnimationData> = new Map();
	public var frameOffset:FlxPoint;
	public var frameOffsetAngle:Null<Float> = null;
	public var lastAnimContext:Dynamic = 'DANCE';
	/** Resolver object injected by the selected Codename script scope. */
	public var assetResolver(default, null):Dynamic;
	/** Last strict loading diagnostic, also emitted to the native trace. */
	public var assetDiagnostic:String = '';

	/** Compatibility constructor: x, y, optional graphic, optional scoped Paths facade. */
	public function new(?X:Float = 0, ?Y:Float = 0, ?SimpleGraphic:Dynamic,
		?Resolver:Dynamic) {
		super(X, Y);
		assetResolver = Resolver;
		frameOffset = FlxPoint.get();
		moves = false;
		applyStageMatrix = true;
		if (SimpleGraphic != null) {
			if (Std.isOfType(SimpleGraphic, String))
				loadSprite(Std.string(SimpleGraphic));
			else
				loadGraphic(cast SimpleGraphic);
		}
	}

	/** Load one scoped frames collection, allowing the owner facade to choose
	 * Sparrow, Packer, or a plain image. A supplied resolver is strict: failure
	 * never falls through to a same-named asset in another namespace. */
	public function loadSprite(path:Dynamic, Unique:Bool = false, Key:String = null):CodenameFunkinSprite {
		if (path == null)
			return this;
		assetDiagnostic = '';
		// Codename scripts commonly pass Paths.image(...) directly. That facade
		// already resolved the selected owner's bitmap; treating it as a string
		// would look for an unrelated images/BitmapData.png.
		if (Std.isOfType(path, FlxFramesCollection)) {
			frames = cast path;
			return this;
		}
		if (Std.isOfType(path, BitmapData) || Std.isOfType(path, FlxGraphic)) {
			loadGraphic(cast path, false, 0, 0, Unique, Key);
			return this;
		}
		if (!Std.isOfType(path, String)) {
			reportAssetIssue('unsupported graphic value');
			return this;
		}
		var sourceKey:String = cast path;
		if (StringTools.trim(sourceKey) == '') return this;

		if (assetResolver != null) {
			var getFrames = Reflect.field(assetResolver, 'getFrames');
			var resolved:Dynamic = null;
			if (getFrames != null && Reflect.isFunction(getFrames))
				resolved = Reflect.callMethod(assetResolver, getFrames, [sourceKey]);
			else if (Reflect.isFunction(assetResolver))
				resolved = Reflect.callMethod(null, assetResolver, [sourceKey]);
			else {
				// Older scoped facades exposed these two methods separately.
				var getAtlas = Reflect.field(assetResolver, 'getSparrowAtlas');
				if (getAtlas != null && Reflect.isFunction(getAtlas)) {
					try resolved = Reflect.callMethod(assetResolver, getAtlas, [sourceKey]) catch (_:Dynamic) {}
				}
				if (resolved == null) {
					var image = Reflect.field(assetResolver, 'image');
					if (image != null && Reflect.isFunction(image))
						resolved = Reflect.callMethod(assetResolver, image, [sourceKey]);
				}
			}
			if (resolved == null) {
				reportAssetIssue('scoped asset was not found: ' + sourceKey);
				return this;
			}
			if (Std.isOfType(resolved, FlxFramesCollection))
				frames = cast resolved;
			else if (Std.isOfType(resolved, BitmapData) || Std.isOfType(resolved, FlxGraphic))
				loadGraphic(cast resolved, false, 0, 0, Unique, Key);
			else
				reportAssetIssue('scoped resolver returned an unsupported value for ' + sourceKey);
			return this;
		}

		// Native use without a Codename scope retains the engine's ordinary
		// Sparrow-then-image lookup. Codename loaders always inject the strict
		// owner facade above.
		try {
			frames = Paths.getSparrowAtlas(sourceKey);
		} catch (_:Dynamic) {
			loadGraphic(cast Paths.image(sourceKey), false, 0, 0, Unique, Key);
		}
		return this;
	}

	function reportAssetIssue(message:String):Void {
		assetDiagnostic = '[codename-sprite-asset] ' + message;
		trace(assetDiagnostic);
	}

	public function addOffset(name:String, x:Float = 0, y:Float = 0):Void {
		if (name == null || name == '')
			return;
		var previous = animOffsets.get(name);
		if (previous != null)
			previous.put();
		animOffsets.set(name, FlxPoint.get(x, y));
	}

	public function switchOffset(anim1:String, anim2:String):Void {
		var first = animOffsets.get(anim1);
		var second = animOffsets.get(anim2);
		if (second == null)
			animOffsets.remove(anim1);
		else
			animOffsets.set(anim1, second);
		if (first == null)
			animOffsets.remove(anim2);
		else
			animOffsets.set(anim2, first);
	}

	public function getAnimOffset(name:String):FlxPoint {
		var value = animOffsets.get(name);
		return value == null ? FlxPoint.weak(0, 0) : value;
	}

	/** Add the basic Codename prefix/indices animation descriptor. */
	public function addAnim(name:String, prefix:String, frameRate:Float = 24,
		?looped:Null<Bool>, ?forced:Null<Bool>, ?indices:Array<Int>, x:Float = 0,
		y:Float = 0, ?animType:Dynamic, animateAtlasLabel:Bool = false):Void {
		if (name == null || prefix == null || name == '' || prefix == '')
			return;
		var fps = Math.isNaN(frameRate) || frameRate <= 0 ? 24 : frameRate;
		var typeName = animType == null ? '' : Std.string(animType).toLowerCase();
		var doesLoop = looped == null ? typeName == 'loop' : looped;
		var animateSymbol = false;
		var animateAtlas = frames is FlxAnimateFrames && library != null;
		if (animateAtlas && !animateAtlasLabel) {
			// Match Codename's XMLUtil.addAnimToSprite: Animate symbols use the
			// Animate controller; names without a symbol continue through the
			// ordinary Sparrow/prefix path.
			animateSymbol = library.getSymbol(prefix) != null;
		}
		if (animateAtlas && animateAtlasLabel) {
			if (indices != null && indices.length > 0)
				anim.addByFrameLabelIndices(name, prefix, indices, fps, doesLoop);
			else
				anim.addByFrameLabel(name, prefix, fps, doesLoop);
		} else if (animateSymbol) {
			if (indices != null && indices.length > 0)
				anim.addBySymbolIndices(name, prefix, indices, fps, doesLoop);
			else
				anim.addBySymbol(name, prefix, fps, doesLoop);
		} else if (indices != null && indices.length > 0)
			animation.addByIndices(name, prefix, indices, '', fps, doesLoop);
		else
			animation.addByPrefix(name, prefix, fps, doesLoop);
		animDatas.set(name, {forced: forced == true});
		addOffset(name, x, y);
	}

	public inline function removeAnim(name:String):Void {
		animation.remove(name);
		animDatas.remove(name);
		var old = animOffsets.get(name);
		if (old != null) {
			animOffsets.remove(name);
			old.put();
		}
	}

	public inline function hasAnim(name:String):Bool
		return name != null && animation.exists(name);

	public inline function getAnimName():String
		return animation.curAnim == null ? '' : animation.curAnim.name;

	public inline function isAnimReversed():Bool
		return animation.curAnim != null && animation.curAnim.reversed;

	public inline function getNameList():Array<String>
		return animation.getNameList();

	public inline function stopAnim():Void
		animation.stop();

	public inline function isAnimFinished():Bool
		return animation.curAnim == null || animation.curAnim.finished;

	public inline function isAnimAtEnd():Bool
	{
		var anim = animation.curAnim;
		// Codename's fork exposes the directional terminal frame as `isAtEnd`.
		// Flixel 6.1.2 only exposes `curFrame`/`numFrames`; keep this distinct
		// from `finished`, which is false for looped animations at their endpoint.
		return anim != null && anim.numFrames > 0
			&& anim.curFrame == (anim.reversed ? 0 : anim.numFrames - 1);
	}

	public inline function hasAnimation(name:String):Bool
		return hasAnim(name);

	public inline function removeAnimation(name:String):Void
		removeAnim(name);

	public inline function stopAnimation():Void
		stopAnim();

	/** The third argument is retained as a dynamic context token (`LOCK`, `DANCE`, ...). */
	public function playAnim(name:String, ?force:Null<Bool>, ?context:Dynamic,
		reversed:Bool = false, frame:Int = 0):Void {
		if (name == null || (!hasAnim(name) && !debugMode))
			return;
		var forced = force;
		if (forced == null) {
			var data = animDatas.get(name);
			forced = data != null && data.forced;
		}
		animation.play(name, forced == true, reversed, frame);
		var animOffset = getAnimOffset(name);
		frameOffset.set(animOffset.x, animOffset.y);
		lastAnimContext = context;
	}

	/** HaxeFlixel 6.1.2 has no Codename prepareDrawMatrix hook, so apply the
	 * upstream camera-relative transform after FlxSprite has built its matrix. */
	override function drawFrameComplex(frame:FlxFrame, camera:FlxCamera):Void {
		final matrix = _matrix;
		frame.prepareMatrix(matrix, FlxFrameAngle.ANGLE_0, checkFlipX(), checkFlipY());
		matrix.translate(-origin.x, -origin.y);
		if (frameOffsetAngle != null && frameOffsetAngle != angle) {
			var angleOff = (frameOffsetAngle - angle) * FlxAngle.TO_RAD;
			var cos = Math.cos(angleOff);
			var sin = Math.sin(angleOff);
			matrix.rotateWithTrig(cos, -sin);
			matrix.translate(-frameOffset.x, -frameOffset.y);
			matrix.rotateWithTrig(cos, sin);
		} else
			matrix.translate(-frameOffset.x, -frameOffset.y);
		matrix.scale(scale.x, scale.y);
		if (bakedRotationAngle <= 0) {
			updateTrig();
			if (angle != 0)
				matrix.rotateWithTrig(_cosAngle, _sinAngle);
		}
		getScreenPosition(_point, camera).subtract(offset);
		_point.add(origin.x, origin.y);
		matrix.translate(_point.x, _point.y);
		if (isPixelPerfectRender(camera)) {
			matrix.tx = Math.floor(matrix.tx);
			matrix.ty = Math.floor(matrix.ty);
		}
		applyCameraTransform(matrix, camera, zoomFactor, angleFactor,
			zoomFactorEnabled, angleFactorEnabled);
		camera.drawPixels(frame, framePixels, matrix, colorTransform, blend, antialiasing, shader);
	}

	/** FlxAnimate uses this matrix builder for both atlas drawing and its bounds.
		Keep its library transform and skew handling, while applying Codename's
		animation offset and camera-relative factors to Animate frames. */
	override function prepareDrawMatrix(matrix:FlxMatrix, camera:FlxCamera):Void {
		if (!isAnimate) {
			super.prepareDrawMatrix(matrix, camera);
			return;
		}
		var doStageMatrix = applyStageMatrix;
		if (doStageMatrix) {
			timeline.getBoundsOrigin(_point);
			matrix.translate(_point.x, _point.y);
		}
		matrix.translate(-origin.x, -origin.y);
		if (frameOffsetAngle != null && frameOffsetAngle != angle) {
			var angleOff = (frameOffsetAngle - angle) * FlxAngle.TO_RAD;
			var cos = Math.cos(angleOff);
			var sin = Math.sin(angleOff);
			matrix.rotateWithTrig(cos, -sin);
			matrix.translate(-frameOffset.x, -frameOffset.y);
			matrix.rotateWithTrig(cos, sin);
		} else
			matrix.translate(-frameOffset.x, -frameOffset.y);
		matrix.scale(scale.x, scale.y);
		if (bakedRotationAngle <= 0 && angle != 0) {
			updateTrig();
			matrix.rotateWithTrig(_cosAngle, _sinAngle);
		}
		if (skew.x != 0 || skew.y != 0) {
			_codenameSkewMatrix.setTo(1, Math.tan(skew.y * FlxAngle.TO_RAD),
				Math.tan(skew.x * FlxAngle.TO_RAD), 1, 0, 0);
			matrix.concat(_codenameSkewMatrix);
		}
		if (doStageMatrix)
			matrix.concat(library.matrix);
		getScreenPosition(_point, camera);
		_point.add(origin.x - offset.x, origin.y - offset.y);
		matrix.translate(_point.x, _point.y);
		if (isPixelPerfectRender(camera)) {
			matrix.tx = Math.floor(matrix.tx);
			matrix.ty = Math.floor(matrix.ty);
		}
		applyCameraTransform(matrix, camera, zoomFactor, angleFactor,
			zoomFactorEnabled, angleFactorEnabled);
	}

	static var _codenameSkewMatrix:FlxMatrix = new FlxMatrix();

	/** Keep transformed content from being culled before drawFrameComplex runs. */
	override public function getScreenBounds(?newRect:FlxRect, ?camera:FlxCamera):FlxRect {
		if (camera == null)
			camera = getDefaultCamera();
		// FlxAnimate's bounds are built from the exact matrix used to render its
		// timeline; our prepareDrawMatrix includes the custom offset/factors.
		if (isAnimate)
			return super.getScreenBounds(newRect, camera);
		var bounds = super.getScreenBounds(newRect, camera);
		var angleOff = frameOffsetAngle == null ? 0 : (frameOffsetAngle - angle) * FlxAngle.TO_RAD;
		var cosOff = Math.cos(angleOff);
		var sinOff = Math.sin(angleOff);
		var offsetX = -frameOffset.x * cosOff + frameOffset.y * sinOff;
		var offsetY = -frameOffset.x * sinOff - frameOffset.y * cosOff;
		// Flixel's base bounds use abs(scale) frame dimensions. A reflected
		// draw matrix starts one signed frame span before those bounds.
		var scaledX = offsetX * scale.x + (scale.x < 0 ? frameWidth * scale.x : 0);
		var scaledY = offsetY * scale.y + (scale.y < 0 ? frameHeight * scale.y : 0);
		var radians = bakedRotationAngle <= 0 ? angle * FlxAngle.TO_RAD : 0;
		var cos = Math.cos(radians);
		var sin = Math.sin(radians);
		bounds.x += scaledX * cos - scaledY * sin;
		bounds.y += scaledX * sin + scaledY * cos;
		// Base Flixel bounds truncate camera scroll; draw uses its fractional
		// value, so align the rectangle before the camera-factor transform.
		var scrollX = camera.scroll.x * scrollFactor.x;
		var scrollY = camera.scroll.y * scrollFactor.y;
		bounds.x += Std.int(scrollX) - scrollX;
		bounds.y += Std.int(scrollY) - scrollY;
		// The draw matrix floors its final translation, while Flixel's base
		// bounds can floor before rotation. Leave room for both roundings.
		if (isPixelPerfectRender(camera)) {
			bounds.x -= 2;
			bounds.y -= 2;
			bounds.width += 4;
			bounds.height += 4;
		}
		if (!hasCameraTransform(camera, zoomFactor, angleFactor,
			zoomFactorEnabled, angleFactorEnabled)) {
			return bounds;
		}
		var x0 = bounds.x;
		var y0 = bounds.y;
		var x1 = x0 + bounds.width;
		var y1 = y0 + bounds.height;
		var p0 = transformCameraPoint(x0, y0, camera, zoomFactor, angleFactor,
			zoomFactorEnabled, angleFactorEnabled);
		var p1 = transformCameraPoint(x1, y0, camera, zoomFactor, angleFactor,
			zoomFactorEnabled, angleFactorEnabled);
		var p2 = transformCameraPoint(x0, y1, camera, zoomFactor, angleFactor,
			zoomFactorEnabled, angleFactorEnabled);
		var p3 = transformCameraPoint(x1, y1, camera, zoomFactor, angleFactor,
			zoomFactorEnabled, angleFactorEnabled);
		var minX = Math.min(Math.min(p0[0], p1[0]), Math.min(p2[0], p3[0]));
		var maxX = Math.max(Math.max(p0[0], p1[0]), Math.max(p2[0], p3[0]));
		var minY = Math.min(Math.min(p0[1], p1[1]), Math.min(p2[1], p3[1]));
		var maxY = Math.max(Math.max(p0[1], p1[1]), Math.max(p2[1], p3[1]));
		return bounds.set(minX, minY, maxX - minX, maxY - minY);
	}

	/** Camera-relative scale used by both the draw transform and its culling bounds. */
	public static function cameraZoomScale(cameraScale:Float, zoom:Float):Float {
		if (cameraScale == 0 || Math.isNaN(cameraScale) || !Math.isFinite(cameraScale)
			|| Math.isNaN(zoom) || !Math.isFinite(zoom))
			return 1;
		var value = (1 - zoom) / cameraScale + zoom;
		return cameraScale > 0 ? Math.max(0, value) : Math.min(0, value);
	}

	public static function hasCameraTransform(camera:FlxCamera, zoom:Float, angle:Float,
		zoomEnabled:Bool, angleEnabled:Bool):Bool {
		return (zoomEnabled && zoom != 1) || (angleEnabled && angle != 1 && camera != null && camera.angle != 0);
	}

	/** Transform one screen-space point with the same viewport-center math as upstream. */
	public static function transformCameraPoint(x:Float, y:Float, camera:FlxCamera,
		zoom:Float, angle:Float, zoomEnabled:Bool, angleEnabled:Bool):Array<Float> {
		if (camera == null)
			return [x, y];
		var centerX = camera.width * 0.5;
		var centerY = camera.height * 0.5;
		if (zoomEnabled && zoom != 1) {
			var sx = cameraZoomScale(camera.scaleX, zoom);
			var sy = cameraZoomScale(camera.scaleY, zoom);
			x = (x - centerX) * sx + centerX;
			y = (y - centerY) * sy + centerY;
		}
		if (angleEnabled && angle != 1 && camera.angle != 0) {
			var radians = -camera.angle * FlxAngle.TO_RAD * (1 - angle);
			var cos = Math.cos(radians);
			var sin = Math.sin(radians);
			var dx = x - centerX;
			var dy = y - centerY;
			x = centerX + dx * cos - dy * sin;
			y = centerY + dx * sin + dy * cos;
		}
		return [x, y];
	}

	public static function applyCameraTransform(matrix:FlxMatrix, camera:FlxCamera,
		zoom:Float, angle:Float, zoomEnabled:Bool, angleEnabled:Bool):Void {
		if (matrix == null || camera == null)
			return;
		var centerX = camera.width * 0.5;
		var centerY = camera.height * 0.5;
		if (zoomEnabled && zoom != 1) {
			var sx = cameraZoomScale(camera.scaleX, zoom);
			var sy = cameraZoomScale(camera.scaleY, zoom);
			matrix.setTo(matrix.a * sx, matrix.b * sy,
				matrix.c * sx, matrix.d * sy,
				(matrix.tx - centerX) * sx + centerX,
				(matrix.ty - centerY) * sy + centerY);
		}
		if (angleEnabled && angle != 1 && camera.angle != 0) {
			matrix.translate(-centerX, -centerY);
			matrix.rotate(-camera.angle * FlxAngle.TO_RAD * (1 - angle));
			matrix.translate(centerX, centerY);
		}
	}

	override public function isSimpleRenderBlit(?camera:FlxCamera):Bool {
		if ((zoomFactorEnabled && zoomFactor != 1) || (angleFactorEnabled && angleFactor != 1)
			|| (frameOffset != null && (frameOffset.x != 0 || frameOffset.y != 0)))
			return false;
		return super.isSimpleRenderBlit(camera);
	}

	override function updateAnimation(elapsed:Float):Void {
		if (animEnabled)
			super.updateAnimation(elapsed);
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (!debugMode && isAnimFinished()) {
			var loopName = getAnimName() + '-loop';
			if (hasAnim(loopName))
				playAnim(loopName, null, lastAnimContext);
		}
	}

	public var globalCurFrame(get, set):Int;
	function get_globalCurFrame():Int
		return animation.curAnim == null ? 0 : animation.curAnim.curFrame;
	function set_globalCurFrame(value:Int):Int {
		if (animation.curAnim != null)
			animation.curAnim.curFrame = value;
		return value;
	}

	override public function destroy():Void {
		if (animOffsets != null) {
			for (point in animOffsets)
				if (point != null)
					point.put();
			animOffsets.clear();
		}
		if (frameOffset != null) {
			frameOffset.put();
			frameOffset = null;
		}
		super.destroy();
	}
}
