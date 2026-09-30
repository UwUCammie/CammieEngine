package;

import flixel.input.keyboard.FlxKey;
import flixel.util.typeLimit.OneOfTwo;
import FreeplayState.JsonMetadata;
import FreeplaySongOrder.FreeplaySongEntry;
import flash.text.TextField;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.addons.display.FlxGridOverlay;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.math.FlxMath;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;
import flixel.util.FlxColor;
import lime.utils.Assets;
import DifficultyIcons;
import lime.system.System;
#if sys
import haxe.io.Path;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import sys.FileSystem;
import flash.media.Sound;
#end
import haxe.Json;
import tjson.TJSON;
using StringTools;

class CategoryState extends MusicBeatState
{
	var categories:Array<String> = [];
	public static var choosingFor:String = "freeplay";
	var categorySongs:Array<Array<OneOfTwo<JsonMetadata, String>>> =[];
	var categorybgs:Array<Array<String>> =[];
	var selector:FlxText;
	static var curSelected:Int = 0;
	// type-to-search, same deal as FreeplayState's chart search: the category
	// list stays complete and `categoryMatches` hides non-matching entries, so
	// filtering never has to rebuild anything
	var searchString:String = "";
	var searchText:FlxText;
	var searchBG:FlxSprite;
	// height of the bottom search strip (the list is numbered above it)
	static inline var SEARCH_BAR_HEIGHT:Int = 46;

	private var grpSongs:FlxTypedGroup<Alphabet>;
	private var curPlaying:Bool = false;

	override function create()
	{
		// it's a js file to make syntax highlighting acceptable
		#if windows
		// Updating Discord Rich Presence
		Discord.DiscordClient.changePresence("In the Freeplay Menu", null);
		#end
		var epicCategoryJs:Array<Dynamic> = cast FreeplayRegistry.getJson();
		if (epicCategoryJs.length > 1 || choosingFor != "freeplay") {
			for (category in epicCategoryJs) {
				categories.push(category.name);
				categorySongs.push(category.songs);
				categorybgs.push(category.bgs);
			}
		} else {
			// just set freeplay states songs to the only category
			trace(epicCategoryJs[0].songs);
			trace(epicCategoryJs[0].Bg);
			FreeplayState.currentSongList = epicCategoryJs[0].songs;
			LoadingState.loadAndSwitchState(new FreeplayState());
		}

		/*
			if (FlxG.sound.music != null)
			{
				if (!FlxG.sound.music.playing)
					FlxG.sound.playMusic('assets/music/freakyMenu' + TitleState.soundExt);
			}
		 */


		// LOAD MUSIC

		// LOAD CHARACTERS

		var bg:FlxSprite = new FlxSprite().loadGraphic('assets/images/menuBGBlue.png');
		add(bg);

		grpSongs = new FlxTypedGroup<Alphabet>();
		add(grpSongs);

		for (i in 0...categories.length)
		{
			var songText:Alphabet = new Alphabet(0, (70 * i) + 30, categories[i], true, false);
			songText.isMenuItem = true;
			songText.targetY = i;
			grpSongs.add(songText);
			// songText.x += 40;
			// DONT PUT X IN THE FIRST PARAMETER OF new ALPHABET() !!
			// songText.screenCenter(X);
		}

		// a stale index (or one left past the end of a shorter list) would point
		// nowhere - keep it in range before the first layout pass
		if (categories.length > 0 && curSelected >= categories.length)
			curSelected = 0;

		// search bar: bottom-left strip, translucent black, always on screen
		searchBG = new FlxSprite(0, FlxG.height - SEARCH_BAR_HEIGHT).makeGraphic(FlxG.width, SEARCH_BAR_HEIGHT, FlxColor.BLACK);
		searchBG.alpha = 0.6;
		add(searchBG);
		searchText = new FlxText(10, FlxG.height - SEARCH_BAR_HEIGHT + 6, 0, "", 24);
		searchText.setFormat("assets/fonts/vcr.ttf", 24, FlxColor.WHITE, FlxTextAlign.LEFT);
		add(searchText);
		applySearchFilter(); // shows the placeholder

		changeSelection();
		// FlxG.sound.playMusic('assets/music/title' + TitleState.soundExt, 0);
		// FlxG.sound.music.fadeIn(2, 0, 0.8);
		selector = new FlxText();

		selector.size = 40;
		selector.text = ">";
		// add(selector);

		var swag:Alphabet = new Alphabet(1, 0, "swag");

		// JUST DOIN THIS SHIT FOR TESTING!!!
		/*
			var md:String = Markdown.markdownToHtml(Assets.getText('CHANGELOG.md'));

			var texFel:TextField = new TextField();
			texFel.width = FlxG.width;
			texFel.height = FlxG.height;
			// texFel.
			texFel.htmlText = md;

			FlxG.stage.addChild(texFel);

			// scoreText.textField.htmlText = md;

			trace(md);
		 */

		super.create();
	}

	override function update(elapsed:Float)
	{
		super.update(elapsed);

		if (FlxG.sound.music.volume < 0.7)
		{
			FlxG.sound.music.volume += 0.5 * FlxG.elapsed;
		}


		var upP = controls.UP_MENU;
		var downP = controls.DOWN_MENU;

		// type-to-search: letters/digits filter the category list, backspace
		// deletes. nav keys that produce a character type instead of moving on the
		// frame they're typed so searching doesn't fight the controls
		var typedChar:String = "";
		if (FlxG.keys.justPressed.BACKSPACE) {
			if (searchString.length > 0) {
				searchString = searchString.substr(0, searchString.length - 1);
				applySearchFilter();
			}
		} else if (FlxG.keys.justPressed.ANY) {
			var key:Int = FlxG.keys.firstJustPressed();
			var A:Int = FlxKey.A;
			var Z:Int = FlxKey.Z;
			var ZERO:Int = FlxKey.ZERO;
			var NINE:Int = FlxKey.NINE;
			var NPZERO:Int = FlxKey.NUMPADZERO;
			var NPNINE:Int = FlxKey.NUMPADNINE;
			if (key >= A && key <= Z)
				typedChar = String.fromCharCode(key - A + "a".code);
			else if (key >= ZERO && key <= NINE)
				typedChar = String.fromCharCode(key - ZERO + "0".code);
			else if (key >= NPZERO && key <= NPNINE)
				typedChar = String.fromCharCode(key - NPZERO + "0".code);
			else if (key == (FlxKey.SPACE : Int))
				typedChar = " ";
			else if (key == (FlxKey.MINUS : Int))
				typedChar = "-";
			if (typedChar.length > 0) {
				searchString += typedChar;
				applySearchFilter();
			}
		}

		// Z/Q/E/W/S/A/D are all bound to menu actions, so a keystroke that typed
		// must not also accept/open (typing "z" used to launch the highlighted
		// category) - the same reason space only ever types
		var accepted = controls.ACCEPT && typedChar.length == 0
			&& !FlxG.keys.justPressed.SPACE && curSelected >= 0
			&& curSelected < categories.length && categoryMatches(curSelected);

		if (upP && typedChar.length == 0 && anyVisibleCategories())
			changeSelection(FlxG.keys.pressed.SHIFT ? -5 : -1);
		if (downP && typedChar.length == 0 && anyVisibleCategories())
			changeSelection(FlxG.keys.pressed.SHIFT ? 5 : 1);


		if (controls.BACK && !FlxG.keys.justPressed.BACKSPACE)
		{
			// backspace is a search key here - only escape actually goes back
			if (searchString.length > 0) {
				// escape clears an active search before leaving
				searchString = "";
				applySearchFilter();
			} else {
				LoadingState.loadAndSwitchState(new MainMenuState());
			}
		}
		// make sure it isn't a header

		if (accepted)
			openCategory();
	}

	// the songs a category hands to FreeplayState/SortState. "All" re-lists every
	// other category's songs (generating our own metadata for bare string
	// entries); anything else just lists its own
	function songsFor(i:Int):Array<JsonMetadata> {
		var songsButData:Array<JsonMetadata> = [];
		if (categories[i] == 'All') {
			songsButData.push({name: "Random-Song", week: 0, character: "bf"});
			var allEntries:Array<FreeplaySongEntry> = [];
			for (c in 0...categories.length) {
				if (c == i || categories[c] == 'All')
					continue;
				for (song in categorySongs[c]) {
					var data:JsonMetadata;
					if ((song is String)) {
						// we have to generate our own metadata
						data = {name: song, week: -1, character: "face"};
					} else {
						data = cast(song : JsonMetadata);
					}
					allEntries.push({song:data, base:categories[c] == 'Base Game',
						order:allEntries.length});
				}
			}
			for (song in FreeplaySongOrder.sort(allEntries))
				songsButData.push(cast song);
		} else {
			for (song in categorySongs[i]) {
				if ((song is String)) {
					// we have to generate our own metadata
					songsButData.push({name: song, week: -1, character: "face"});
				} else {
					songsButData.push(cast(song : JsonMetadata));
				}
			}
		}
		return songsButData;
	}

	function openCategory() {
		// make sure it isn't a header / empty category
		if (categorySongs[curSelected].length == 0)
			return;
		var songsButData:Array<JsonMetadata> = songsFor(curSelected);
		if (choosingFor == "freeplay") {
			FreeplayState.curCategory = categories[curSelected];
			FreeplayState.currentSongList = songsButData;
			LoadingState.loadAndSwitchState(new FreeplayState());
		} else {
			SortState.stuffToSort = songsButData;
			SortState.category = categories[curSelected];
			LoadingState.loadAndSwitchState(new SortState());
		}
	}

	// search matching: lowercase + alphanumeric only, so "week 2" finds
	// "Week-2" and dashes/spaces are interchangeable. Shares FreeplayState's
	// normalization so the two searches behave identically.
	function searchNorm(s:String):String {
		return FreeplayState.searchNorm(s);
	}

	function categoryMatches(i:Int):Bool {
		if (searchString.length == 0)
			return true;
		var needle = searchNorm(searchString);
		if (needle.length == 0)
			return true;
		return searchNorm(categories[i]).indexOf(needle) != -1;
	}

	function anyVisibleCategories():Bool {
		for (i in 0...categories.length)
			if (categoryMatches(i))
				return true;
		return false;
	}

	function applySearchFilter() {
		var searching:Bool = searchString.length > 0;
		if (searching) {
			searchText.text = "search: " + searchString + "_";
			searchText.alpha = 1;
		} else {
			searchText.text = "search: (type to filter)";
			searchText.alpha = 0.45;
		}
		if (!categoryMatches(curSelected) && anyVisibleCategories())
			changeSelection(0); // hops to the next visible category + refreshes
		else
			applyListLayout(); // clearing a search must unhide the list again
	}

	// hops onto the next matching entry; shares FreeplayState's implementation so
	// the two searches wrap/skip identically
	static function nextVisibleSelection(current:Int, change:Int, count:Int, matches:Int->Bool):Int {
		return FreeplayState.nextVisibleSelection(current, change, count, matches);
	}

	function changeSelection(change:Int = 0)
	{

		FlxG.sound.play('assets/sounds/scrollMenu' + TitleState.soundExt, 0.4);

		if (categories.length == 0)
			return;

		curSelected = nextVisibleSelection(curSelected, change, categories.length, categoryMatches);

		// selector.y = (70 * curSelected) + 30;

		applyListLayout();
	}

	// layout for the current filter: hides the non-matching rows and numbers the
	// visible ones by their position among the visible, so the list closes ranks
	// instead of leaving gaps while a search is active
	function applyListLayout() {
		var curVisPos:Int = 0;
		var countVis:Int = 0;
		for (i in 0...categories.length) {
			if (categoryMatches(i)) {
				if (i == curSelected)
					curVisPos = countVis;
				countVis++;
			}
		}
		var visPos:Int = 0;
		for (i in 0...grpSongs.members.length) {
			var item = grpSongs.members[i];
			var vis:Bool = categoryMatches(i);
			item.visible = vis;
			if (vis) {
				item.targetY = visPos - curVisPos;
				visPos++;

				item.alpha = 0.6;
				// item.setGraphicSize(Std.int(item.width * 0.8));

				if (item.targetY == 0)
				{
					item.alpha = 1;
					// item.setGraphicSize(Std.int(item.width));
				}
			}
		}
	}
}
