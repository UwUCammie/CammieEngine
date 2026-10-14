package;

import flixel.graphics.frames.FlxAtlasFrames;
import flixel.system.FlxAssets.FlxGraphicAsset;
import flixel.FlxSprite;
import flixel.addons.display.FlxTiledSprite;
import flixel.util.FlxAxes;
import flixel.addons.display.FlxBackdrop;
/**
 * A sprite that automatically handles loading files dynamically. This is used in hscripts by default.
 * Only overwrites "loadGraphic."
 */
class DynamicSprite extends FlxSprite {
    override public function loadGraphic(Graphic:FlxGraphicAsset, Animated:Bool = false, Width:Int = 0, Height:Int = 0, Unique:Bool = false, ?Key:String) {
        if ((Graphic is String)) {
            // show time baby
            var data = FNFAssets.getBitmapData(Graphic);
            return super.loadGraphic(data, Animated, Width, Height, Unique, Key);
        }
        return super.loadGraphic(Graphic, Animated, Width, Height, Unique, Key);
    }
}
/**
 * A replacement for FlxAtlasFrames that dynamically handles loading assets.
 * Passed to hscripts by default.
 * Because of how this works only Sparrow/Packer loaders (plus the
 * multi-Sparrow combiner) are supported.
 */
class DynamicAtlasFrames {
    // Building a character atlas (multi-MB PNG + hundreds of frames) is the
    // expensive part of a mid-song "Change Character", so built atlases are
    // reused. The cache holds an extra use count on the parent FlxGraphic:
    // flixel drops a graphic from the bitmap cache once its useCount hits zero,
    // and switchCharacter destroys the outgoing character, which would otherwise
    // free a sheet another swap still needs. Bounded so a long session cannot
    // grow it forever, emptied when a song ends (Main) and when an import or a
    // file write moves FNFAssets.pathEpoch, so it never serves old frames.
    static var atlasCache:Map<String, FlxAtlasFrames> = new Map();
    static var atlasOrder:Array<String> = [];
    // Metadata handed over as text is keyed by image alone and compared here,
    // instead of building a key that copies and hashes the whole file.
    static var atlasText:Map<String, String> = new Map();
    static var atlasEpoch:Int = 0;
    static final ATLAS_CACHE_MAX = 32;
    // Longer than any asset path; atlas metadata is usually far longer.
    static final MAX_PATH_LENGTH = 1024;

    /** Release every cached atlas and the use counts it holds. */
    static public function releaseAll():Void {
        for (key in atlasOrder.copy())
            releaseCachedAtlas(key);
        atlasCache.clear();
        atlasText.clear();
    }

    static function checkEpoch():Void {
        var epoch = FNFAssets.pathEpoch();
        if (epoch == atlasEpoch)
            return;
        releaseAll();
        atlasEpoch = epoch;
    }

    /** True for an argument that is clearly file contents, not a path. Such
        text must never reach FNFAssets.exists, which would normalize it, list
        the game folder and remember it as a missed path. */
    static function isInlineText(value:String):Bool {
        // JSON text opens with a brace. A brace further in can be part of a
        // real file or folder name, so only the first character counts.
        return value != null && (value.length > MAX_PATH_LENGTH || value.indexOf('<') >= 0
            || value.indexOf('\n') >= 0 || (value.length > 0 && StringTools.fastCodeAt(value, 0) == '{'.code));
    }

    /** Cache key for an image plus metadata, null when the image is not a path. */
    static function atlasKey(kind:String, png:FlxGraphicAsset, metadata:String):String {
        if (!(png is String))
            return null;
        if (isInlineText(metadata))
            return kind + '|' + png + '|<inline>';
        return kind + '|' + png + '|' + metadata;
    }

    static function cachedFor(key:String, metadata:String):FlxAtlasFrames {
        if (key == null)
            return null;
        checkEpoch();
        if (atlasText.exists(key) && atlasText.get(key) != metadata)
            return null;
        return getCachedAtlas(key);
    }

    static function store(key:String, metadata:String, frames:FlxAtlasFrames):FlxAtlasFrames {
        if (key != null && isInlineText(metadata)) {
            if (frames == null || frames.parent == null || frames.parent.isDestroyed)
                return frames;
            // One inline slot per image: a different text replaces the old one.
            if (atlasText.exists(key) && atlasText.get(key) != metadata)
                releaseCachedAtlas(key);
            atlasText.set(key, metadata);
        }
        return putCachedAtlas(key, frames);
    }

    static public function getCachedAtlas(key:String):FlxAtlasFrames {
        if (key == null)
            return null;
        var frames = atlasCache.get(key);
        if (frames == null || frames.parent == null || frames.parent.isDestroyed) {
            if (frames != null)
                releaseCachedAtlas(key);
            return null;
        }
        atlasOrder.remove(key);
        atlasOrder.push(key);
        return frames;
    }

    static public function putCachedAtlas(key:String, frames:FlxAtlasFrames):FlxAtlasFrames {
        if (key == null || frames == null || frames.parent == null || frames.parent.isDestroyed)
            return frames;
        if (!atlasCache.exists(key))
            frames.parent.incrementUseCount();
        atlasCache.set(key, frames);
        atlasOrder.remove(key);
        atlasOrder.push(key);
        while (atlasOrder.length > ATLAS_CACHE_MAX)
            releaseCachedAtlas(atlasOrder[0]);
        return frames;
    }

    static function releaseCachedAtlas(key:String) {
        var frames = atlasCache.get(key);
        atlasCache.remove(key);
        atlasOrder.remove(key);
        atlasText.remove(key);
        if (frames != null && frames.parent != null && !frames.parent.isDestroyed)
            frames.parent.decrementUseCount();
    }

    public static function fromSparrow(png:FlxGraphicAsset, xml:String) {
        var key = atlasKey('sparrow', png, xml);
        var hit = cachedFor(key, xml);
        if (hit != null)
            return hit;
        var source = xml;
        if (!isInlineText(xml) && FNFAssets.exists(xml)) {
            xml = FNFAssets.getText(xml);
        }
        if ((png is String)) {
            // show time again
            png = FNFAssets.getFlxGraphic(png);
        }
        return store(key, source, FlxAtlasFrames.fromSparrow(png, xml));
    }
    /**
     * Load a V-Slice multi-sparrow character as one frame collection.
     *
     * V-Slice stores the primary Sparrow atlas first and puts any animation
     * specific atlases in the animation's `assetPath`.  Flixel animations
     * resolve frame indices when they are added, so simply replacing
     * `sprite.frames` per animation would silently lose the other atlases.
     * Concatenate all authored Sparrow collections once, preserving the
     * primary collection when frame names collide (the same precedence as
     * the V-Slice runtime).
     *
     * Each entry is `[pngPath, xmlPath]`. Missing pairs are skipped; the
     * importer emits the corresponding precise diagnostic before this helper
     * is reached.
     */
    public static function combineSparrow(atlases:Array<Dynamic>):FlxAtlasFrames {
        if (atlases == null || atlases.length == 0)
            return null;

        var main:FlxAtlasFrames = null;
        var additions:Array<FlxAtlasFrames> = [];
        for (entry in atlases) {
            if (!Std.isOfType(entry, Array))
                continue;
            var pair:Array<Dynamic> = cast entry;
            if (pair == null || pair.length < 2 || pair[0] == null || pair[1] == null)
                continue;
            var png = Std.string(pair[0]);
            var xml = Std.string(pair[1]);
            if (png == '' || xml == '' || !FNFAssets.exists(png) || !FNFAssets.exists(xml))
                continue;
            var atlas = fromSparrow(png, xml);
            if (atlas == null)
                continue;
            if (main == null)
                main = atlas;
            else
                additions.push(atlas);
        }
        if (main == null)
            return null;
        // Keep the primary atlas authoritative if an authored sub-atlas uses
        // a duplicate frame name. `addAtlas` already preserves the first
        // frame by default.
        for (atlas in additions)
            main.addAtlas(atlas);
        return main;
    }
    public static function fromSpriteSheetPacker(png:FlxGraphicAsset, txt:String) {
        var key = atlasKey('sspack', png, txt);
        var hit = cachedFor(key, txt);
        if (hit != null)
            return hit;
        var source = txt;
		if (!isInlineText(txt) && FNFAssets.exists(txt)) {
			txt = FNFAssets.getText(txt);
		}
		if ((png is String)) {
			// show time again
			png = FNFAssets.getFlxGraphic(png);
		}
        return store(key, source, FlxAtlasFrames.fromSpriteSheetPacker(png, txt));
    }
    // JSON-Hash atlases (Paths.getCharacterJson) go through the same cache
    public static function fromTexturePackerJson(png:FlxGraphicAsset, json:String) {
        var key = atlasKey('tpackjson', png, json);
        var hit = cachedFor(key, json);
        if (hit != null)
            return hit;
        return store(key, json, FlxAtlasFrames.fromTexturePackerJson(png, json));
    }
}

class DynamicTiledSprite extends FlxTiledSprite {
    override public function new(Graphic:FlxGraphicAsset, Width:Int, Height:Int, repeatX:Bool = true, repeatY:Bool = true) {
        if ((Graphic is String))
            Graphic = FNFAssets.getBitmapData(Graphic);
        super(Graphic, Width, Height, repeatX, repeatY);
    }
}

class DynamicBackdrop extends FlxBackdrop {
    override public function new(Graphic:FlxGraphicAsset, repeatAxes:FlxAxes = XY, spacingX:Float = 0, spacingY:Float = 0) {
        if ((Graphic is String))
            Graphic = FNFAssets.getBitmapData(Graphic);
        super(Graphic, repeatAxes, spacingX, spacingY);
    }
}
