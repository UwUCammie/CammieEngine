package;

import openfl.display.BitmapData;
import flixel.FlxSprite;
import lime.utils.Assets;
import lime.system.System;
import flash.display.BlendMode;
import openfl.filters.ColorMatrixFilter;
import flixel.addons.plugin.taskManager.FlxTask;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxEase;
import tjson.TJSON;
using StringTools;

#if sys
import sys.io.File;
import haxe.io.Path;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import sys.FileSystem;
import flash.media.Sound;
#end


class CoolUtil {
	public static var fps:Int = 60;

	/** Convert a per-frame lerp amount into an equivalent elapsed-time amount. */
	public static function timeAdjustedLerpAlpha(baseAlpha:Float, elapsed:Float, referenceFps:Float = 60):Float {
		return 1 - Math.pow(1 - baseAlpha, elapsed * referenceFps);
	}

	/** Collapse two sequential, equal-alpha lerps into one time-adjusted lerp. */
	public static function timeAdjustedTwoTargetLerp(current:Float, firstTarget:Float, secondTarget:Float, baseAlpha:Float, elapsed:Float, referenceFps:Float = 60):Float {
		var resolvedTarget = ((1 - baseAlpha) * firstTarget + secondTarget) / (2 - baseAlpha);
		var combinedAlpha = baseAlpha * (2 - baseAlpha);
		return current + (resolvedTarget - current) * timeAdjustedLerpAlpha(combinedAlpha, elapsed, referenceFps);
	}

	// hxs, like kotlin's kts
	public static final HSCRIPT_EXT:Array<String> = ['hscript', 'hxs'];
	public static final JSON_EXT:Array<String> = ['json', 'jsonc'];
	public static function formatCustomChars() {
		var epicCharFile:Dynamic = CoolUtil.parseJson(FNFAssets.getJson('assets/images/custom_chars/custom_chars'));
		/*
		this is what im basing off
		"template": {
			"like": "bf",
			"icons": [0,1,2,3],
			"colors": ["#149DFF"],
			"iconbop": "test"
		},
		*/
		var finalString = '{';

		var components:Array<String> = [ // a pain to look at but I like it
			'\n  "', 
			'": {\n    "like": "', 
			'",\n    "icons": ',
			',\n    "colors": [',
			']\n  },',
			'],\n    "iconbop": ',
			'\n  },'
		];

		var daFields = Reflect.fields(epicCharFile);
		for (i in 0...daFields.length) {
			var char = daFields[i];
			var charData:Dynamic = Reflect.field(epicCharFile, char);
			// Older registries (and some imported character packs) omit optional
			// metadata.  Do not dereference a missing entry while normalizing the
			// registry: native cpp builds can turn a null .length access into a
			// SIGSEGV instead of a useful exception.
			if (charData == null)
				continue;
			trace(char);
			var like:Dynamic = Reflect.field(charData, 'like');
			if (like == null || StringTools.trim(Std.string(like)) == '')
				like = char;
			trace(like);
			var icons:Dynamic = Reflect.field(charData, 'icons');
			if (icons == null)
				icons = [0, 0, 0, 0];
			if ((icons is String))
				icons = '"' + icons + '"';
			else
				icons = icons.toString();
			trace(icons);
			
			var colorsValue:Dynamic = Reflect.field(charData, 'colors');
			var colors:Array<Dynamic>;
			if (colorsValue == null)
				colors = ['#FFFFFF'];
			else if (Std.isOfType(colorsValue, Array))
				colors = cast colorsValue;
			else
				colors = [colorsValue];
			if (colors.length == 0)
				colors.push('#FFFFFF');
			trace(colors);
			var fixedColors = '';
			for(i in 0...colors.length) {
				fixedColors += '"' + colors[i] + '"';
				if (i != colors.length-1)
					fixedColors += ',';
			}
			trace(fixedColors);

			var iconbop = Reflect.field(charData, 'iconbop');
			if (iconbop != null) {
				finalString += components[0] + char + components[1] + like + components[2] + icons + components[3] + fixedColors + components[5] + iconbop + components[6];
			} else
				finalString += components[0] + char + components[1] + like + components[2] + icons + components[3] + fixedColors + components[4];
		}

		finalString += '\n}';
		trace('done');
		File.saveContent('assets/images/custom_chars/custom_chars.jsonc', finalString);
	}

	public static function getSongFile(song:String, path:String, inst:Bool = true, ?extension:String = '') { // 'path' is the song folder path
		var daSong:String = null;
		var songType = if (inst) 'Inst'; else 'Voices';
		var candidates:Array<String> = [
			haxe.io.Path.join([path, song + '_' + songType + extension + TitleState.soundExt]),
			haxe.io.Path.join([path, songType + extension + TitleState.soundExt]),
			haxe.io.Path.join([path, '../../music/' + song + '_' + songType + extension + TitleState.soundExt])
		];
		for (candidate in candidates) {
			var resolved = FNFAssets.resolveCaseInsensitivePath(candidate);
			if (resolved != null) {
				daSong = resolved;
				break;
			}
		}
		return daSong;
	}

	/** Returns a FlxEase function from the source-compatible easing name. */
	public static function getEaseFromString(ease:Null<String>)
	{
		if (ease == null) return FlxEase.linear;
		return switch (ease.toLowerCase().trim())
		{
			case 'backin': FlxEase.backIn;
			case 'backinout': FlxEase.backInOut;
			case 'backout': FlxEase.backOut;
			case 'bouncein': FlxEase.bounceIn;
			case 'bounceinout': FlxEase.bounceInOut;
			case 'bounceout': FlxEase.bounceOut;
			case 'circin': FlxEase.circIn;
			case 'circinout': FlxEase.circInOut;
			case 'circout': FlxEase.circOut;
			case 'cubein': FlxEase.cubeIn;
			case 'cubeinout': FlxEase.cubeInOut;
			case 'cubeout': FlxEase.cubeOut;
			case 'elasticin': FlxEase.elasticIn;
			case 'elasticinout': FlxEase.elasticInOut;
			case 'elasticout': FlxEase.elasticOut;
			case 'expoin': FlxEase.expoIn;
			case 'expoinout': FlxEase.expoInOut;
			case 'expoout': FlxEase.expoOut;
			case 'quadin': FlxEase.quadIn;
			case 'quadinout': FlxEase.quadInOut;
			case 'quadout': FlxEase.quadOut;
			case 'quartin': FlxEase.quartIn;
			case 'quartinout': FlxEase.quartInOut;
			case 'quartout': FlxEase.quartOut;
			case 'quintin': FlxEase.quintIn;
			case 'quintinout': FlxEase.quintInOut;
			case 'quintout': FlxEase.quintOut;
			case 'sinein': FlxEase.sineIn;
			case 'sineinout': FlxEase.sineInOut;
			case 'sineout': FlxEase.sineOut;
			case 'smoothstepin': FlxEase.smoothStepIn;
			case 'smoothstepinout': FlxEase.smoothStepInOut;
			case 'smoothstepout': FlxEase.smoothStepOut;
			case 'smootherstepin': FlxEase.smootherStepIn;
			case 'smootherstepinout': FlxEase.smootherStepInOut;
			case 'smootherstepout': FlxEase.smootherStepOut;
			default: FlxEase.linear;
		}
	}

	public static function getBlendMode(blend:String) {
		var daBlend = switch(blend.toLowerCase()) {
			case "add":
				BlendMode.ADD;
			case "alpha":
				BlendMode.ALPHA;
			case "darken":
				BlendMode.DARKEN;
			case "difference":
				BlendMode.DIFFERENCE;
			case "erase":
				BlendMode.ERASE;
			case "hardlight":
				BlendMode.HARDLIGHT;
			case "invert":
				BlendMode.INVERT;
			case "layer":
				BlendMode.LAYER;
			case "lighten":
				BlendMode.LIGHTEN;
			case "multiply":
				BlendMode.MULTIPLY;
			case "normal":
				BlendMode.NORMAL;
			case "overlay":
				BlendMode.OVERLAY;
			case "screen":
				BlendMode.SCREEN;
			case "shader":
				BlendMode.SHADER;
			case "subtract":
				BlendMode.SUBTRACT;
			default:
				null;
		}
		return daBlend;
	}
	public static function getFilter(filterName:String, ?customArray:Array<Float>) {
		var daFilter = switch(filterName.toLowerCase()) {
			case 'grayscale' | 'monochrome' | 'blackandwhite':
				new ColorMatrixFilter(
					[0.5, 0.5, 0.5, 0, 0,
					0.5, 0.5, 0.5, 0, 0,
					0.5, 0.5, 0.5, 0, 0,
					0, 0, 0, 1, 0]
				);
			case 'invert' | 'negative':
				new ColorMatrixFilter(
					[-1, 0, 0, 0, 255,
					 0, -1, 0, 0, 255,
					 0, 0, -1, 0, 255,
					 0, 0, 0, 1, 0]
				);
			case 'deuteranopia' | 'deuter':
				new ColorMatrixFilter(
					[0.43, 0.72, -.15, 0, 0,
					0.34, 0.57, 0.09, 0, 0,
					-.02, 0.03, 1, 0, 0,
					0, 0, 0, 1, 0]
				);
			case 'protanopia' | 'prot':
				new ColorMatrixFilter(
					[0.20, 0.99, -.19, 0, 0,
					0.16, 0.79, 0.04, 0, 0,
					0.01, -.01, 1, 0, 0,
					0, 0, 0, 1, 0]
				);
			case 'tritanopia' | 'trit':
				new ColorMatrixFilter(
					[0.97, 0.11, -.08, 0, 0,
					0.02, 0.82, 0.16, 0, 0,
					0.06, 0.88, 0.18, 0, 0,
					0, 0, 0, 1, 0]
				);
			case 'blank' | 'normal' | 'default':
				new ColorMatrixFilter(
					[1, 0, 0, 0, 0,
					0, 1, 0, 0, 0,
					0, 0, 1, 0, 0,
					0, 0, 0, 1, 0]
				);
			case 'custom':
				if (customArray != null)
					new ColorMatrixFilter(customArray);
				else
					null;
			default:
				null;
		}
		return daFilter;
	}
	public static function coolTextFile(path:String):Array<String> {
		var daList:Array<String> = FNFAssets.getText(path).trim().split('\n');

		for (i in 0...daList.length) {
			daList[i] = daList[i].trim();
		}

		return daList;
	}
	public static function coolDynamicTextFile(path:String):Array<String> {
		return coolTextFile(path);
	}
	public static function numberArray(max:Int, ?min = 0):Array<Int> {
		var dumbArray:Array<Int> = [];
		for (i in min...max) {
			dumbArray.push(i);
		}
		return dumbArray;
	}
	/**
	 * Compatibility helper from Wednesday's Infidelity. This deliberately only
	 * changes the render scale: refreshing the hitbox also shifts the effective
	 * origin of its oversized Hellhole background layers.
	 * It intentionally leaves width, height, offset and origin untouched.
	 */
	public static function exactSetGraphicSize(sprite:FlxSprite, width:Float = 0, height:Float = 0):Void {
		if (sprite == null || sprite.width == 0 || sprite.height == 0)
			return;
		sprite.scale.set(
			Math.abs(((sprite.width - width) / sprite.width) - 1),
			Math.abs(((sprite.height - height) / sprite.height) - 1)
		);
	}
	public static function clamp(mini:Float, maxi:Float, value:Float):Float {
		return Math.min(Math.max(mini,value), maxi);
	}
	// can either return an array or a dynamic
	public static function parseJson(json:String):Dynamic {
		// the reason we do this is to make it easy to swap out json parsers
		// release cpp builds have no null checks: TJSON.parse(null) SEGFAULTS
		// (the story menu did exactly that via a mis-cased asset path), so
		// fail with a message naming the real problem instead
		if (json == null)
			throw "parseJson: null input - an asset passed in above this call is missing or mis-cased";
		// A few Kade-era releases were packaged with fixed-size chart buffers:
		// their otherwise valid JSON is followed by NUL padding.  Keep this
		// cleanup at the shared parser boundary so every importer/runtime path
		// accepts those charts without rewriting the donor files.
		var end:Int = json.length;
		while (end > 0) {
			var code:Int = json.charCodeAt(end - 1);
			if (code == 0 || code == 9 || code == 10 || code == 13 || code == 32)
				end--;
			else
				break;
		}
		if (end != json.length)
			json = json.substr(0, end);
		return TJSON.parse(json);
	}
	public static function stringifyJson(json:Dynamic, ?fancy:Bool = true):String {
		// use tjson to prettify it
		var style:String = if (fancy) 'fancy' else null;
		return TJSON.encode(json,style);
	}
	// include all helper functions to keep shit in the same place
	public static function truncateFloat(number:Float, precision:Int):Float {
		return HelperFunctions.truncateFloat(number, precision);
	}
	public static function erf(x:Float):Float {
		return HelperFunctions.erf(x);
	}
	public static function getNotes():Int {
		return HelperFunctions.getNotes();
	}
	public static function getHolds():Int {
		return HelperFunctions.getHolds();
	}
	public static function getMapMaxScore():Int {
		return HelperFunctions.getMapMaxScore();
	}
	public static function wife3(maxms:Float, ts:Float) {
		return HelperFunctions.wife3(maxms, ts);
	}

	public static function pauseTween(tween:FlxTween) {
		if (tween != null)
			tween.active = false;
	}
	public static function pauseTweensOf(object:Dynamic) {
		@:privateAccess
		FlxTween.globalManager.forEachTweensOf(object, null, function(tween) {
			pauseTween(tween);
		});
	}

	public static function resumeTween(tween:FlxTween) {
		if (tween != null)
			tween.active = true;
	}
	public static function resumeTweensOf(object:Dynamic) {
		@:privateAccess
		FlxTween.globalManager.forEachTweensOf(object, null, function(tween) {
			resumeTween(tween);
		});
	}
}

class FlxTools {
	// Load a graphic and ensure it exists
	static public function loadGraphicDynamic(s:FlxSprite, path:String, animated:Bool=false, width:Int=0, height:Int=0, unique:Bool=false, ?key:String):FlxSprite {
		var sus:BitmapData = FNFAssets.getBitmapData(path);
		s.loadGraphic(sus,animated,width,height,unique,key);
		return s;
	}
}
