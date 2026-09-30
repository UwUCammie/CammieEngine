package;
import flixel.FlxSprite;
import DynamicSprite.DynamicAtlasFrames;
import flixel.FlxG;
import Judgement.TUI;

class NoteSplash extends FlxSprite {
    public var isPixel:Bool = false;
    public var uiType:String = 'normal';
    public var variants:Int = 0;
    public var frameRate:Int = 24;
    /** Direction and owning native line retained for generic render adapters. */
    public var direction:Int = 0;
    public var sourceStrumline:Null<Strumline> = null;
    public function new(xPos:Float, yPos:Float, ?c:Int = 0, type:String = 'normal',
        ?skipNativeSplash:Bool = false) {
        super(xPos, yPos);
		uiType = type;

		final curUiType:TUI = Reflect.field(Judgement.uiJson, type);
        isPixel = curUiType.isPixel;
        if (!skipNativeSplash) {
        var splashAsset = curUiType.noteSplashAsset == null || StringTools.trim(curUiType.noteSplashAsset) == ''
            ? 'noteSplashes' : curUiType.noteSplashAsset;
        if (!isPixel) {
            var customSplashPath = 'assets/images/custom_ui/ui_packs/${curUiType.uses}/${splashAsset}.png';
            var customSplashXml = 'assets/images/custom_ui/ui_packs/${curUiType.uses}/${splashAsset}.xml';
            if (curUiType.noteSplashAssetXml == true && FNFAssets.exists(customSplashPath)
                && FNFAssets.exists(customSplashXml))
		        frames = DynamicAtlasFrames.fromSparrow('assets/images/custom_ui/ui_packs/${curUiType.uses}/${splashAsset}.png',
			        customSplashXml);
            else
        	    frames = DynamicAtlasFrames.fromSparrow('assets/images/custom_ui/ui_packs/normal/noteSplashes.png',
			        'assets/images/custom_ui/ui_packs/normal/noteSplashes.xml');
        } else {
            if (FNFAssets.exists('assets/images/custom_ui/ui_packs/${curUiType.uses}/noteSplashes-pixel.png'))
		        frames = DynamicAtlasFrames.fromSparrow('assets/images/custom_ui/ui_packs/${curUiType.uses}/noteSplashes-pixel.png',
			        'assets/images/custom_ui/ui_packs/${curUiType.uses}/noteSplashes-pixel.xml');
            else
        	    frames = DynamicAtlasFrames.fromSparrow('assets/images/custom_ui/ui_packs/normal/noteSplashes-pixel.png',
			        'assets/images/custom_ui/ui_packs/normal/noteSplashes-pixel.xml');
        }

        final currentKey = new NoteKeys(curUiType.uses);
        for (i in 0...Note.NOTE_AMOUNT) {
            final noteName = currentKey.getNote(i);
            final noteSplashes = currentKey.getSplashes(i);
            if (noteSplashes != null) {
                variants = noteSplashes.length;
                for (splash in 0...variants)
                    animation.addByPrefix("note" + i + "-" + splash, noteSplashes[splash], 24, false);
            } else {
                if (!isPixel) {
                    variants = 2;
                    animation.addByPrefix("note" + i + "-0", "note impact 1 " + noteName, 24, false);
                    animation.addByPrefix("note" + i + "-1", "note impact 2 " + noteName, 24, false);
                } else {
                    variants = 3;
                    animation.addByPrefix("note" + i + "-0", noteName + "1", 33, false);
                    animation.addByPrefix("note" + i + "-1", noteName + "2", 33, false);
                    animation.addByPrefix("note" + i + "-2", noteName + "3", 33, false);
                    frameRate = 33;
                }
            }
        }

        if (isPixel) {
            antialiasing = false;
            scale.set(4, 4);
            updateHitbox();
        } else
            {
                antialiasing = true;
                if (curUiType.splashScale != null)
                    scale.set(curUiType.splashScale, curUiType.splashScale);
                if (curUiType.splashAlpha != null)
                    alpha = curUiType.splashAlpha;
            }

		setupNoteSplash(xPos, yPos, c);
        }
    }

    public function setupNoteSplash(xPos:Float, yPos:Float, ?c:Int = 0) {
        setPosition(xPos, yPos);
		direction = c;
		var curUiType = curUiTypeFor(uiType);
        alpha = curUiType.splashAlpha == null ? 0.6 : curUiType.splashAlpha;
        animation.play("note" + c + "-" + FlxG.random.int(0,variants-1), true);
		animation.curAnim.frameRate = frameRate + FlxG.random.int(-2, 2);
        updateHitbox();
        if (!isPixel) {
			var ui = curUiType;
            if (ui.splashOffsetX != null || ui.splashOffsetY != null)
                offset.set(ui.splashOffsetX == null ? 0 : ui.splashOffsetX,
                    ui.splashOffsetY == null ? 0 : ui.splashOffsetY);
            else
                offset.set(0.3 * width, 0.3 * height);
        }
        else
            offset.set(0.5, 13.5);
    }

    static function curUiTypeFor(type:String):TUI {
        return Reflect.field(Judgement.uiJson, type);
    }

    override public function update(elapsed) {
        if (animation.curAnim.finished) {
            // club pengiun is
            kill();
        }
        super.update(elapsed);
    }
}
