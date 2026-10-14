package;

import flixel.FlxSprite;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.group.FlxSpriteGroup;
import flixel.math.FlxMath;
import lime.system.System;
#if sys
import sys.io.File;
import haxe.io.Path;
import openfl.utils.ByteArray;
import flash.display.BitmapData;
#end
import haxe.Json;
import haxe.format.JsonParser;
import tjson.TJSON;
class MenuItem extends FlxSpriteGroup
{
	public var targetY:Float = 0;
	public var week:FlxSprite;

	public function new(x:Float, y:Float, weekNum:Int = 0, ?imported:ImportedStoryWeeks.ImportedStoryWeek)
	{
		super(x, y);
		// Imported weeks are not in storySonglist.json; their art lives in the owner.
		if (imported != null) {
			week = createImportedWeekSprite(imported);
			add(week);
			week.updateHitbox();
			return;
		}
		// WHAT THE FUCK
		// IS THIS :GRIEF:
		// WHY THE FUCK DO YOU READ A FILE FUCKING 5 TIMES
		// NO WONDER THERE ARE PREFORMANCE ISSUE
		
		var parsedWeekJson:StoryMenuState.StorySongsJson = CoolUtil.parseJson(FNFAssets.getJson("assets/data/storySonglist"));
		var weekName = parsedWeekJson.weeks[weekNum].name;
		var rawPic = FNFAssets.getBitmapData('assets/images/campaign-ui-week/' + weekName + ".png");
		if (rawPic == null) {
			// A week converted from another engine's level data can name a title
			// image the package never shipped. Show its name instead of loading
			// a null graphic.
			week = createWeekLabel(weekLabel('', weekName));
			add(week);
			week.updateHitbox();
			return;
		}
		
		var rawXml:String = "";
		if (FNFAssets.exists('assets/images/campaign-ui-week/' + weekName + ".xml")) {
			rawXml = FNFAssets.getText('assets/images/campaign-ui-week/' + weekName + ".xml");
		}
		if (rawXml != "") {
			var tex = FlxAtlasFrames.fromSparrow(rawPic, rawXml);
			var animName:String = "";
			animName = parsedWeekJson.weeks[weekNum].animation;

			week = new FlxSprite();
			week.frames = tex;
			// TUTORIAL IS tutorial (because I feel like it)
			week.animation.addByPrefix("default", animName, 24);
			add(week);

			week.animation.play('default');
			week.animation.pause();
			week.updateHitbox();
		} else {
			week = createWeekSpriteFromGraphic(rawPic);
			add(week);
			week.updateHitbox();
		}

	}

	/** The owner's title image, or the week's name as text when it has none. */
	static function createImportedWeekSprite(imported:ImportedStoryWeeks.ImportedStoryWeek):FlxSprite {
		if (imported.art != '') {
			var rawPic = FNFAssets.getBitmapData(imported.art);
			if (rawPic != null)
				return createWeekSpriteFromGraphic(rawPic);
		}
		return createWeekLabel(weekLabel(imported.title, imported.key));
	}

	/** Text shown for a week with no title image: its title, else its key without the owner prefix. */
	public static function weekLabel(title:String, key:String):String {
		if (title != null && title != '')
			return title.toUpperCase();
		if (key == null)
			return '';
		return key.substr(key.indexOf(':') + 1).toUpperCase();
	}

	static function createWeekLabel(label:String):FlxSprite {
		var text = new flixel.text.FlxText(0, 0, 0, label, 48);
		text.setFormat("assets/fonts/vcr.ttf", 48, flixel.util.FlxColor.WHITE, CENTER);
		return text;
	}

	/** PNG-only campaign entries still need their FlxSprite instance created. */
	static function createWeekSpriteFromGraphic(rawPic:Dynamic):FlxSprite {
		var sprite = new FlxSprite();
		sprite.loadGraphic(rawPic);
		return sprite;
	}

	override function update(elapsed:Float)
	{
		super.update(elapsed);
		y = FlxMath.lerp(y, (targetY * 120) + 480, CoolUtil.timeAdjustedLerpAlpha(0.17, elapsed));
	}
}
