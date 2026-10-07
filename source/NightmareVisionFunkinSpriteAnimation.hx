package;

import animate.FlxAnimate;
import animate.FlxAnimateFrames;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.math.FlxPoint;
import flixel.math.FlxMath;

/** Shared actual-controller atlas/animation operations for source sprite families. */
@:access(NightmareVisionSpriteMethods)
@:access(openfl.display.BitmapData)
class NightmareVisionFunkinSpriteAnimation {
 public static function loadAtlas(sprite:FlxAnimate, paths:NightmareVisionPaths, path:String):FlxAnimate {
  NightmareVisionSpriteMethods.selected(sprite).requireActive();
  if (paths == null) throw '[nightmare-vision-asset] Sprite is not bound to an imported owner';
  var found:Array<FlxAtlasFrames> = [];
  var containsAnimate = false;
  for (part in path.split(',')) {
   var key = StringTools.trim(part);
   var animated = paths.fileExists('images/' + key + '/Animation.json');
   var atlas = animated ? paths.getTextureAtlas(key) : paths.getAtlasFrames(key);
   if (atlas != null) {
    if (animated) {
     if (paths.gpuCachingEnabled() && atlas.parent.bitmap != null) atlas.parent.bitmap.disposeImage();
     containsAnimate = true;
    }
    found.push(atlas);
   }
  }
  if (found.length != 0) {
   if (containsAnimate) for (collection in found) {
    paths.forgetAtlasGraphic(collection.parent);
    collection.parent.persist = false;
   }
   sprite.frames = FlxAnimateFrames.combineAtlas(found);
  }
  return sprite;
 }
 public static function addAnimByPrefix(sprite:FlxAnimate, name:String, prefix:String, fps:Int = 24,
  looping:Bool = true, flipX:Bool = false, flipY:Bool = false):Void {
  if (sprite.library != null && sprite.anim.findFrameLabelIndices(prefix).length > 0)
   sprite.anim.addByFrameLabel(name, prefix, fps, looping, flipX, flipY);
  else if (hasSymbol(sprite.library, prefix))
   sprite.anim.addBySymbol(name, prefix, fps, looping, flipX, flipY);
  else sprite.animation.addByPrefix(name, prefix, fps, looping, flipX, flipY);
 }
 public static function addAnimByIndices(sprite:FlxAnimate, name:String, prefix:String, indices:Array<Int>, fps:Int = 24,
  looping:Bool = true, flipX:Bool = false, flipY:Bool = false):Void {
  if (sprite.library != null && sprite.anim.findFrameLabelIndices(prefix).length > 0)
   sprite.anim.addByFrameLabelIndices(name, prefix, indices, fps, looping, flipX, flipY);
  else if (hasSymbol(sprite.library, prefix))
   sprite.anim.addBySymbolIndices(name, prefix, indices, fps, looping, flipX, flipY);
  else sprite.animation.addByIndices(name, prefix, indices, '', fps, looping, flipX, flipY);
 }
 @:access(animate.FlxAnimateFrames)
 static function hasSymbol(atlas:FlxAnimateFrames, symbol:String):Bool {
  if (atlas == null) return false;
  if (atlas.existsSymbol(symbol)) return true;
  for (collection in atlas.addedCollections) if (collection.dictionary.exists(symbol)) return true;
  return false;
 }
 public static function transformOffset(sprite:FlxAnimate, input:FlxPoint, baseScale:FlxPoint, output:FlxPoint,
  scalable:Bool = true, rotatable:Bool = true, skewable:Bool = true):FlxPoint {
  output.copyFrom(input);
  if (scalable && (Math.abs(sprite.scale.x - baseScale.x) > FlxMath.EPSILON || Math.abs(sprite.scale.y - baseScale.y) > FlxMath.EPSILON))
   output.scale(sprite.scale.x / baseScale.x, sprite.scale.y / baseScale.y);
  if (rotatable && Math.abs(sprite.angle) > FlxMath.EPSILON) output.rotateByDegrees(sprite.angle);
  if (skewable && (Math.abs(sprite.skew.x) > FlxMath.EPSILON || Math.abs(sprite.skew.y) > FlxMath.EPSILON)) {
   var pX:Float = output.x, pY:Float = output.y;
   output.x += pY * (FlxMath.fastSin(sprite.skew.x / 180 * Math.PI) / FlxMath.fastCos(sprite.skew.x / 180 * Math.PI));
   output.y += pX * (FlxMath.fastSin(sprite.skew.y / 180 * Math.PI) / FlxMath.fastCos(sprite.skew.y / 180 * Math.PI));
  }
  return output;
 }

}
