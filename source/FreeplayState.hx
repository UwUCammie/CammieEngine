package;

import Controls.Action;
import flixel.input.keyboard.FlxKey;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween;
import flixel.util.FlxGradient;
import Section.SwagSection;
import flash.text.TextField;
import flixel.FlxG;
import flixel.FlxBasic;
import flixel.FlxCamera;
import flixel.FlxSprite;
import flixel.addons.display.FlxGridOverlay;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.sound.FlxSound;
import flixel.math.FlxMath;
import flixel.text.FlxText;
import flixel.util.FlxColor;
import lime.utils.Assets;
import DifficultyIcons;
import lime.system.System;
#if sys
import sys.io.File;
import haxe.io.Path;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import sys.FileSystem;
import flash.media.Sound;
import haxe.crypto.Sha256;
import ImportRefreshAvailabilitySnapshot.ImportRefreshAvailabilitySnapshot;
import ImportRefreshAvailabilitySnapshot.ImportRefreshPendingSong;
#end
import haxe.Json;
import tjson.TJSON;
import FreeplaySongAvailability.FreeplayAvailabilityDecision;
using StringTools;

class FreeplayState extends MusicBeatState {
	#if sys
	var importRefreshGeneration:Int = 0;
	var importAvailability:ImportRefreshAvailabilitySnapshot;
	var importAvailabilityRevision:Int = -1;
	var baseSongCount:Int = 0;
	#end
	public static var currentSongList:Array<JsonMetadata> = [];
	public static var soundTest:Bool = false;
	var vocals:FlxSound;
	var songs:Array<SongMetadata> = [];
	var directOwnerRoot:String = '';
	var bgs:Array<String> = [];

	var selector:FlxText;
	static var curSelected:Int = 0;
	static var curDifficulty:Int = 1;
	public static var curCategory = '';
	private static var prevCategory = '';
	var soundTestSong:Song.SwagSong;
	var scoreText:FlxText;
	var diffText:FlxText;
	var lerpScore:Float = 0;
	var intendedScore:Int = 0;
	var intendedAccuracy:Float = 0;
	var lerpAccuracy:Float = 0;
	var bg:FlxSprite;
	var bgInfo:Array<String> = [];
	var bgDir:Array<String> = [];
	var bgNames:Array<String> = [];
	var categoryBG:Array<String> = [];
	var categoriesNames:Array<String> = [];
	private var iconArray:Array<HealthIcon> = [];
	private var starArray:Array<Array<RankStar>> = [];
	var isPixelIcon:Array<Bool> = [];
	var usingCategoryScreen:Bool = false;
	var nightcoreMode:Bool = false;
	var daycoreMode:Bool = false;
	private var grpSongs:FlxTypedGroup<Alphabet>;
	private var grpSongSources:FlxTypedGroup<FlxText>;
	// songs keeps the full registry indexes used by search, HXC and chart launch;
	// only this small selection window has live Alphabet rows at a time.
	var songRows:Array<Alphabet> = [];
	var sourceRows:Array<FlxText> = [];
	var rowSongIndices:Array<Int> = [];
	private var curPlaying:Bool = false;
	var searchString:String = "";
	var searchText:FlxText;
	var searchBG:FlxSprite;
	var qtooltip:Tooltip;
	var etooltip:Tooltip;
	// deferred icon/rank-star creation + audio preview state
	var iconQueue:Array<Int> = [];
	// only build icon/score info for the closest charts around the selection:
	// with 1273 songs, building every song's icon bitmap + per-difficulty
	// rank-star save lookups is wasted work for songs off-screen
	public static inline var INFO_WINDOW:Int = 30;
	// A dozen rows on either side covers the viewport plus SHIFT's zoomed-out
	// view while keeping the live Alphabet/character sprite count bounded.
	public static inline var ROW_WINDOW_RADIUS:Int = 12;
	static inline var SONG_ROW_SCALE:Float = 0.85;
	static inline var SONG_ROW_MOTION_RATE:Float = 2;
	// camera zoom while SHIFT is held in freeplay (hold to see more songs at once)
	public static inline var SHIFT_ZOOM:Float = 0.65;
	var previewSound:FlxSound;
	var previewGen:Int = 0;
	var previewTimer:Float = 0;
	var previewCache:Map<String, Sound> = new Map();
	var previewOrder:Array<String> = [];
	var charJson:Dynamic;
	var iconJson:Dynamic;
	var record:Record;
	var recordPixel:Record;
	var curOverlay:FlxSprite;
	var infoPanel:SongInfoPanel;
	// HUD-style camera for the menu chrome that must stay put while the SHIFT
	// zoom-out shrinks the song list. FreeplayState draws everything on the one
	// default camera, so zooming it also dragged the search bar and the
	// score/difficulty panel around (and shrank them). The chrome is assigned to
	// camUI instead, which never zooms - same trick PlayState uses for camHUD.
	var camUI:FlxCamera;
	// HXC modules which target FreeplayState are hosted separately from
	// PlayState so difficulty/capsule hooks fire while the menu is open.
	var hxcRuntime:HxcFreeplayRuntime;
	// Bounded V-Slice capsule/difficulty views.  These are plain Dynamic
	// envelopes over the native song rows; no donor FreeplayState graph is
	// instantiated or retained.
	var hxcCapsuleGroup:Dynamic;
	var hxcCapsuleViews:Array<Dynamic> = [];
	var hxcDifficultyOrder:Array<String> = [];
	var hxcBusy:Bool = false;
	// Imported modules may attach an onConfirm callback to the current shallow
	// capsule view. The one-shot token binds that callback to the selection which
	// installed it, so a later cursor move cannot open a stale substate.
	var hxcConfirmGate:SelectionActionGate = new SelectionActionGate();
	var hxcConfirmToken:Int = 0;
	var hxcConfirmSelectionKey:String = '';
	var hxcConfirmGeneration:Int = -1;
	var hxcSelectionGeneration:Int = 0;
	var hxcPendingPromptToken:Int = 0;
	var hxcPendingPromptSelectionKey:String = '';
	var hxcPendingPromptGeneration:Int = -1;
	// Set only while a manifest-owned HXC Freeplay callback is dispatching.
	// Native display helpers therefore resolve assets in the caller's selected
	// namespace and never search a sibling import by accident.
	var hxcAssetRoot:String = '';
	// the chrome that stays screen-fixed, gathered up so it can be pointed at
	// camUI in one place and parked in front of the list in the draw order
	var uiChrome:Array<FlxBasic> = [];

	/** Shallow capsule collection exposed to imported HXC Freeplay modules. */
	public var grpCapsules(get, never):Dynamic;
	function get_grpCapsules():Dynamic {
		if (hxcCapsuleGroup == null)
			hxcCapsuleGroup = {members: hxcBuildCapsules(), clear: function():Void {}, add: function(_value:Dynamic):Void {}};
		else
			Reflect.setField(hxcCapsuleGroup, 'members', hxcBuildCapsules());
		return hxcCapsuleGroup;
	}

	/** V-Slice's variation spelling maps to the active native difficulty id. */
	public var currentVariation(get, never):String;
	function get_currentVariation():String {
		var names = DifficultyManager.getDifficultyNames();
		if (curDifficulty >= 0 && curDifficulty < names.length)
			return names[curDifficulty];
		return '';
	}

	/** Instance-shaped Freeplay fields expected by imported V-Slice scripts. */
	public var hxcSelectedIndex(get, never):Int;
	function get_hxcSelectedIndex():Int return curSelected;

	public var hxcDifficultyIndex(get, set):Int;
	function get_hxcDifficultyIndex():Int return curDifficulty;
	function set_hxcDifficultyIndex(value:Int):Int {
		var names = DifficultyManager.getDifficultyNames();
		if (value >= 0 && value < names.length)
			curDifficulty = value;
		return curDifficulty;
	}

	public var hxcCategoryId(get, set):String;
	function get_hxcCategoryId():String return curCategory;
	function set_hxcCategoryId(value:String):String {
		curCategory = value == null ? '' : value;
		return curCategory;
	}

	public var busy(get, set):Bool;
	function get_busy():Bool return hxcBusy;
	function set_busy(value:Bool):Bool return hxcBusy = value;

	/** Apply an authored difficulty order without exposing native UI objects. */
	public function hxcApplyDifficultyOrder(order:Array<String>):Dynamic {
		hxcDifficultyOrder = [];
		if (order != null) {
			var available = DifficultyManager.getDifficultyNames();
			for (name in order)
				if (name != null && available.indexOf(name) >= 0 && hxcDifficultyOrder.indexOf(name) < 0)
					hxcDifficultyOrder.push(name);
			for (name in available)
				if (hxcDifficultyOrder.indexOf(name) < 0)
					hxcDifficultyOrder.push(name);
		}
		return this;
	}

	/** Native back boundary used by generic HXC menu transition adapters. */
	public function hxcReturnToMenu():Bool {
		LoadingState.loadAndSwitchState(new MainMenuState());
		return true;
	}

	/** Keep explicit imported Freeplay scope separate from a gameplay owner. */
	function prepareDirectFreeplayContext():Void {
		var activeCodenameOwner = CodenameModRuntime.activeRoot();
		directOwnerRoot = ImportedFreeplayCaller.ownerForFreeplay(activeCodenameOwner);
		// An active chart owner must not narrow an ordinary category/All Freeplay
		// menu. Explicit imported-state/package entry tokens keep their own scope.
		if (directOwnerRoot == '' && activeCodenameOwner != '')
			CodenameModRuntime.clearActiveOwner();
	}

	/** Arm a callback currently installed on the selected manifest-scoped capsule. */
	function refreshHxcConfirm():Void {
		if (curSelected < 0 || curSelected >= songs.length)
		{
			clearHxcConfirm();
			return;
		}
		var capsule = hxcCapsuleView(curSelected);
		var callback:Dynamic = capsule == null ? null : Reflect.field(capsule, 'onConfirm');
		if (callback == null || !Reflect.isFunction(callback)) {
			clearHxcConfirm();
			return;
		}
		var key = songs[curSelected].songName;
		// Modules commonly assign a fresh closure each frame. Ownership belongs
		// to the capsule selection, so keep its one-shot token stable until that
		// selection changes rather than treating closure allocation as a new prompt.
		if (hxcConfirmToken != 0 && hxcConfirmSelectionKey == key.toLowerCase()
			&& hxcConfirmGeneration == hxcSelectionGeneration && hxcConfirmGate.isArmedFor(key))
			return;
		clearHxcConfirm();
		hxcConfirmToken = hxcConfirmGate.armFor(key, hxcSelectionGeneration);
		hxcConfirmSelectionKey = key.toLowerCase();
		hxcConfirmGeneration = hxcSelectionGeneration;
	}

	function clearHxcConfirm():Void {
		hxcConfirmToken = 0;
		hxcConfirmSelectionKey = '';
		hxcConfirmGeneration = -1;
		hxcConfirmGate.clear();
	}

	function clearHxcPendingPrompt():Void {
		hxcPendingPromptToken = 0;
		hxcPendingPromptSelectionKey = '';
		hxcPendingPromptGeneration = -1;
	}

	/** Enter one manifest-owned HXC asset scope for a callback dispatch. */
	public function hxcPushAssetScope(root:String):String {
		var previous = hxcAssetRoot;
		hxcAssetRoot = root == null ? '' : StringTools.replace(StringTools.trim(root), '\\', '/');
		return previous;
	}

	/** Restore the previous native Freeplay asset scope after a callback. */
	public function hxcPopAssetScope(previous:String):Void {
		hxcAssetRoot = previous == null ? '' : previous;
	}

	function hxcLaunchCurrentSelection():Bool {
		if (soundTest || curSelected < 0 || curSelected >= songs.length)
			return false;
		if (!availabilityAllowsLaunch(curSelected, curDifficulty)) return false;
		previewGen++;
		stopPreviewSound();
		var songName = songs[curSelected].songName;
		var chartName = songName.toLowerCase() + DifficultyIcons.getEndingFP(curDifficulty);
		PlayState.SONG = Song.loadFromJson(chartName, songName.toLowerCase());
		Song.attachFreeplayScoreSongId(PlayState.SONG, songName);
		PlayState.isStoryMode = false;
		PlayState.balls = 0;
		PlayState.watchedCutscene = false;
		ModifierState.isStoryMode = false;
		PlayState.storyDifficulty = curDifficulty;
		if (!OptionsHandler.options.skipModifierMenu)
			LoadingState.loadAndSwitchState(new ModifierState());
		else {
			if (FlxG.sound.music != null)
				FlxG.sound.music.stop();
			LoadingState.loadAndSwitchState(new PlayState());
		}
		return true;
	}

	/** Native equivalent of the default capsule confirm used by imported modules. */
	public function capsuleOnConfirmDefault(capsule:Dynamic):Bool {
		if (curSelected < 0 || curSelected >= songs.length
			|| capsule == null || capsule != hxcCapsuleView(curSelected))
			return false;
		var songKey = songs[curSelected].songName.toLowerCase();
		if (hxcPendingPromptToken != 0
			&& (hxcPendingPromptGeneration != hxcSelectionGeneration
				|| hxcPendingPromptSelectionKey != songKey)) {
			clearHxcPendingPrompt();
			return false;
		}
		clearHxcPendingPrompt();
		return hxcLaunchCurrentSelection();
	}

	function hxcBuildCapsules():Array<Dynamic> {
		var result:Array<Dynamic> = [];
		for (index in 0...songs.length) {
			var capsule = hxcCapsuleView(index);
			if (capsule != null)
				result.push(capsule);
		}
		return result;
	}
	public function new() {
		super();
		if (Std.isOfType(FlxG.state, CodenameImportedState)) {
			var source:CodenameImportedState = cast FlxG.state;
			ImportedFreeplayCaller.capture(source.ownerRoot, source.scriptPath);
		} else ImportedFreeplayCaller.keepFor(CodenameModRuntime.activeRoot(),
			Std.isOfType(FlxG.state, ModifierState) || Std.isOfType(FlxG.state, PlayState));
	}

	override function create() {
		#if sys
		importRefreshGeneration = ImportRefreshManager.generation;
		#end
		prepareDirectFreeplayContext();
		if (directOwnerRoot != '' || currentSongList == null || currentSongList.length == 0) {
			var categories:Array<Dynamic> = null;
			try categories = cast FreeplayRegistry.getJson() catch (error:Dynamic)
				trace('[freeplay-direct-entry] Could not read the Freeplay registry: ' + Std.string(error));
			currentSongList = cast FreeplayDirectEntry.select(categories,
				directOwnerRoot, function(name:String):String
					return ImportedModDiscovery.ownerForSong(name, 'assets/data'), curCategory);
		}
		var smokeProfile = RuntimeSmokeHarness.enabled();
		var createStart = smokeProfile ? haxe.Timer.stamp() : 0.0;
		var profileMark = createStart;
		Highscore.load();
		var difficultyDefinitions:Array<Dynamic> = null;
		for (songSnippet in currentSongList) {
			var songData = new SongMetadata(songSnippet.name, songSnippet.week, songSnippet.character,
				songSnippet.display, songSnippet.sourceLabel);
			if (songSnippet.flags == null || songSnippet.flags.length == 0)
				songs.push(songData);
			else {
				var canUse = true;
				for (flag in songSnippet.flags) {
					switch (flag) {
						case 'debug':
							#if debug
								continue;
							#else
								canUse = false;
								break;
							#end
						default:
							var reg = ~/week(\d+)/g;
							if (reg.match(flag)) {
								var week:Int = Std.parseInt(reg.matched(1));
								if (difficultyDefinitions == null) {
									var diffJson:Dynamic = CoolUtil.parseJson(FNFAssets.getJson("assets/images/custom_difficulties/difficulties"));
									difficultyDefinitions = diffJson.difficulties;
								}
								var existsWeek = false;
								for (diff in 0...difficultyDefinitions.length) {
									if (Highscore.getWeekScore('$week', diff) != 0) {
										existsWeek = true;
										break;
									}
										
								}
								if (existsWeek) {
									continue;
								} else {
									canUse = false;
									break;
								}
							}
							var songReg = ~/song-(.+)/g;
							if (songReg.match(flag)) {
								var songie = songReg.matched(1);
								if (difficultyDefinitions == null) {
									var diffJson:Dynamic = CoolUtil.parseJson(FNFAssets.getJson("assets/images/custom_difficulties/difficulties"));
									difficultyDefinitions = diffJson.difficulties;
								}
								var existsSong = false;
								for (diff in 0...difficultyDefinitions.length) {
									if (Highscore.getScore(songie, diff) != 0) {
										existsSong = true;
										break;
									}
								}
								if (!existsSong) {
									canUse = false;
									break;
								}
									
							}
					}
				}
				if (canUse) 
					songs.push(songData);
			}
		}
		#if sys
		baseSongCount = songs.length;
		refreshImportAvailability(true);
		#end
		if (smokeProfile) {
			profileMark = haxe.Timer.stamp();
			RuntimeSmokeHarness.profileSection('fp-create-song-filter', profileMark - createStart);
		}

		if (prevCategory != curCategory) {
			curSelected = 0;
			prevCategory = curCategory;
		}

		if (curSelected > songs.length - 1)
			curSelected = 0;
		if (songs.length == 0) {
			trace('[freeplay-direct-entry] No playable songs in the selected category or installed registry.');
			var importedCaller = ImportedFreeplayCaller.take(directOwnerRoot);
			if (importedCaller != null) {
				if (importedCaller.returnKind == 'package-picker') {
					FreeplayState.currentSongList = [];
					CodenameModRuntime.clearActiveOwner();
					LoadingState.loadAndSwitchState(new CodenameImportedModsState());
					return;
				} else {
					var target = CodenameModRuntime.stateInit(importedCaller.ownerRoot,
						importedCaller.scriptPath);
					if (Std.isOfType(target, flixel.FlxState)) {
						LoadingState.loadAndSwitchState(cast target);
						return;
					}
				}
			}
			LoadingState.loadAndSwitchState(new MainMenuState());
			return;
		}

		curDifficulty = DifficultyIcons.getDefaultDiffFP();
		/*
			if (FlxG.sound.music != null)
			{
				if (!FlxG.sound.music.playing)
					FlxG.sound.playMusic('assets/music/freakyMenu' + TitleState.soundExt);
			}
		 */
		if (!FlxG.sound.music.playing) {
			FlxG.sound.playMusic(FNFAssets.getSound('assets/music/custom_menu_music/'
				+ CoolUtil.parseJson(FNFAssets.getJson("assets/music/custom_menu_music/custom_menu_music")).Menu
				+ '/freakyMenu'
				+ TitleState.soundExt));
		}
		#if windows
		// Updating Discord Rich Presence
		var customPrecence = TitleState.discordStuff.freeplay;
		Discord.DiscordClient.changePresence(customPrecence, null);
		#end
		var isDebug:Bool = false;
		charJson = CoolUtil.parseJson(FNFAssets.getJson('assets/images/custom_chars/custom_chars'));
		iconJson = CoolUtil.parseJson(FNFAssets.getJson("assets/images/custom_chars/icon_only_chars"));
		#if debug
		isDebug = true;
		#end

		// LOAD MUSIC

		// LOAD CHARACTERS
		if (soundTest) {
			// disable auto pause. I NEED MUSIC
			FlxG.autoPause = false;
			curDifficulty = 0;
		}

		// imagine making a sprite and not assigning a var
		bg =  new FlxSprite();
		if (FNFAssets.exists('assets/images/Custom_Menu_BGs/Default/menuDesat.png')) {
			bg.loadGraphic('assets/images/Custom_Menu_BGs/Default/menuDesat.png');
 		} else {
			bg.loadGraphic('assets/images/menuDesat.png');
		}
		add(bg);
		// center it so the background scales about the screen center (see update)
		bg.screenCenter();
		// no fancy :)
		//curOverlay = FlxGradient.createGradientFlxSprite(FlxG.width, FlxG.height, [FlxColor.WHITE]);

		//add(curOverlay); 
		grpSongs = new FlxTypedGroup<Alphabet>();
		add(grpSongs);
		grpSongSources = new FlxTypedGroup<FlxText>();
		add(grpSongSources);

		if (smokeProfile)
			profileMark = haxe.Timer.stamp();
		for (i in 0...songs.length) {
			songRows.push(null);
			sourceRows.push(null);
			// Keep icon and rank-star arrays globally indexed, but only populate
			// the active row window and create its icons over a few frames.
			iconArray.push(null);
			starArray.push(null);
		}
		rebuildVisibleRows();
		if (smokeProfile) {
			var now = haxe.Timer.stamp();
			RuntimeSmokeHarness.profileSection('fp-create-alphabet-rows', now - profileMark);
			profileMark = now;
		}
		
		scoreText = new FlxText(FlxG.width * 0.56, 5, 0, "", 32);
		// scoreText.autoSize = false;
		scoreText.setFormat("assets/fonts/vcr.ttf", 32, FlxColor.WHITE, RIGHT);
		// scoreText.alignment = RIGHT;

		var scoreBG:FlxSprite = new FlxSprite(scoreText.x - 6, 0).makeGraphic(Std.int(FlxG.width * 0.45), 66, 0xFF000000);
		scoreBG.alpha = 0.6;
		add(scoreBG);
		uiChrome.push(scoreBG);

		diffText = new FlxText(scoreText.x, scoreText.y + 36, 0, "", 24);
		if (!soundTest && OptionsHandler.options.style) {
			diffText.x = scoreText.x;
			diffText.y = scoreText.y;
			diffText.size = scoreText.size;
		}
		diffText.font = scoreText.font;
		add(diffText);
		if (soundTest || !OptionsHandler.options.style)
			add(scoreText);
		var curCharacter = songs[0].songCharacter;
		
		if (OptionsHandler.options.style && !songs[0].isProvisional) {
			record = new Record(FlxG.width, FlxG.height, Reflect.field(charJson, curCharacter).colors, songs[0].week, Highscore.getComplete(songs[0].songName, curDifficulty));
			// DON'T update hitbox, it breaks everything
			record.scale.set(0.7, 0.7);
			record.x -= record.width / 1.5;
			record.y -= record.height / 1.5;
			add(record);
			uiChrome.push(record);
		}
		if (songs[0].isProvisional) {
			// The ephemeral pending identifier is not a registered chart and must
			// never be passed into metadata readers.
			infoPanel = null;
		} else {
			infoPanel = new SongInfoPanel(FlxG.width - 500, 100, songs[0].songName, curDifficulty);
		}
		qtooltip = new Tooltip(10, 0, Action.LEFT_TAB, "info backwards", Keyboard, true);
		qtooltip.y = FlxG.height - 46 - qtooltip.height - 4; // above the search strip
		etooltip = new Tooltip(10, qtooltip.y, Action.RIGHT_TAB, "info forwards", Keyboard, true);
		etooltip.x = qtooltip.x + qtooltip.width + 10;
		if (infoPanel == null) {
			etooltip.visible = false;
			qtooltip.visible = false;
		}

		add(etooltip);
		add(qtooltip);
		if (infoPanel != null) add(infoPanel);

		// search bar: bottom-left strip, translucent black, always on screen
		searchBG = new FlxSprite(0, FlxG.height - 46).makeGraphic(FlxG.width, 46, FlxColor.BLACK);
		searchBG.alpha = 0.6;
		add(searchBG);
		searchText = new FlxText(10, FlxG.height - 40, 0, "", 24);
		searchText.setFormat("assets/fonts/vcr.ttf", 24, FlxColor.WHITE, LEFT);
		add(searchText);
		applySearchFilter(); // shows the placeholder
		rebuildIconQueue(); // fill the info window around the selection

		if (soundTest || !OptionsHandler.options.style) {
			etooltip.visible = false;
			qtooltip.visible = false;
			if (infoPanel != null) infoPanel.visible = false;
		}

		// chrome that shouldn't be zoomed with the song list: the search strip,
		// the score/difficulty panel, the info panel / tooltips and the week
		// record. Everything else (bg, song list, icons, stars) stays on the
		// default camera and follows the SHIFT zoom.
		uiChrome.push(searchBG);
		uiChrome.push(searchText);
		uiChrome.push(etooltip);
		uiChrome.push(qtooltip);
		if (infoPanel != null) uiChrome.push(infoPanel);
		if (scoreText != null && members.indexOf(scoreText) != -1)
			uiChrome.push(scoreText);
		if (diffText != null)
			uiChrome.push(diffText);
		setupUICamera();
		if (smokeProfile) {
			var now = haxe.Timer.stamp();
			RuntimeSmokeHarness.profileSection('fp-create-menu-chrome', now - profileMark);
			profileMark = now;
		}

		hxcRuntime = new HxcFreeplayRuntime(this);
		if (smokeProfile) {
			var now = haxe.Timer.stamp();
			RuntimeSmokeHarness.profileSection('fp-create-hxc-runtime', now - profileMark);
			profileMark = now;
		}
		var initialHxcCapsule = hxcCapsuleView(curSelected);
		if (initialHxcCapsule != null) {
			var initialHxcPayload = EngineCompat.hxcFreeplayPayload(
				'subStateOpenEnd', this, initialHxcCapsule, curDifficulty, null);
			hxcRuntime.dispatch('subStateOpenEnd', initialHxcPayload);
		}
		if (smokeProfile) {
			var now = haxe.Timer.stamp();
			RuntimeSmokeHarness.profileSection('fp-create-hxc-start', now - profileMark);
			profileMark = now;
		}
		changeSelection();
		if (smokeProfile) {
			var now = haxe.Timer.stamp();
			RuntimeSmokeHarness.profileSection('fp-create-first-selection', now - profileMark);
			RuntimeSmokeHarness.profileSection('fp-create-total', now - createStart);
		}

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
		
		#if (sys && windows)
		var updateProgressBar = new UpdateProgressBar();
		updateProgressBar.cameras = [camUI];
		add(updateProgressBar);
		#end
		#if sys
		var importRefreshBar = new ImportRefreshProgressBar(this);
		importRefreshBar.setMenuLane(130, 16, 0.56, 20);
		importRefreshBar.cameras = [camUI];
		add(importRefreshBar);
		#end
		super.create();
	}

	#if sys
	static function ownerAvailability(snapshot:ImportRefreshAvailabilitySnapshot,
		ownerRoot:String):FreeplayAvailabilityDecision {
		return FreeplaySongAvailability.ownerReadiness(snapshot, ownerRoot);
	}

	/** The manager revision is the only per-frame importer read. Copying the
	 * immutable snapshot and reconciling provisional rows happens only on change. */
	function refreshImportAvailability(force:Bool = false):Bool {
		var managerRevision = ImportRefreshManager.availabilityRevision();
		if (!force && importAvailability != null && managerRevision == importAvailabilityRevision)
			return false;
		var next = ImportRefreshManager.availabilitySnapshot();
		if (next == null)
			return false;
		importAvailability = next;
		importAvailabilityRevision = next.revision;
		for (song in songs) {
			song.availabilityRevision = -1;
			song.chartRevision = -1;
		}
		var selectedPendingKey = curSelected >= 0 && curSelected < songs.length
			&& songs[curSelected].isProvisional ? songs[curSelected].pendingKey : '';
		var rowsChanged = reconcilePendingSongs();
		if (grpSongs != null) {
			if (rowsChanged) {
				if (songs.length == 0) {
					returnFromEmptySongList();
					return true;
				}
				if (curSelected >= songs.length)
					curSelected = songs.length - 1;
				if (curSelected < 0)
					curSelected = 0;
				rebuildVisibleRows();
				rebuildIconQueue();
			}
			for (index in rowSongIndices)
				updateRenderedRowAvailability(index);
			rebuildIconQueue();
			if (curSelected >= 0 && curSelected < songs.length
				&& !availabilityAllowsSelection(curSelected) && previewSound != null)
				stopPreviewSound();
			if (selectedPendingKey != '' && indexForPendingKey(selectedPendingKey) < 0)
				changeSelection(0, true);
		}
		return true;
	}

	function returnFromEmptySongList():Void {
		trace('[freeplay-direct-entry] No playable songs remain after import availability changed.');
		var importedCaller = ImportedFreeplayCaller.take(directOwnerRoot);
		if (importedCaller != null) {
			if (importedCaller.returnKind == 'package-picker') {
				FreeplayState.currentSongList = [];
				CodenameModRuntime.clearActiveOwner();
				LoadingState.loadAndSwitchState(new CodenameImportedModsState());
				return;
			}
			var target = CodenameModRuntime.stateInit(importedCaller.ownerRoot,
				importedCaller.scriptPath);
			if (Std.isOfType(target, flixel.FlxState)) {
				LoadingState.loadAndSwitchState(cast target);
				return;
			}
		}
		LoadingState.loadAndSwitchState(new MainMenuState());
	}

	function reconcilePendingSongs():Bool {
		var desired:Map<String, ImportRefreshPendingSong> = new Map();
		if (importAvailability != null && importAvailability.pendingSongs != null
			&& canPresentPendingSongs()) {
			for (candidate in importAvailability.pendingSongs) {
				if (candidate == null || candidate.key == null || StringTools.trim(candidate.key) == ''
					|| candidate.name == null || StringTools.trim(candidate.name) == ''
					|| candidate.ownerRoot == null || StringTools.trim(candidate.ownerRoot) == '')
					continue;
				if (directOwnerRoot != '' && FreeplaySongAvailability.normalizePath(candidate.ownerRoot)
					!= FreeplaySongAvailability.normalizePath(directOwnerRoot))
					continue;
				if (candidateAlreadyInstalled(candidate))
					continue;
				if (!desired.exists(candidate.key))
					desired.set(candidate.key, candidate);
			}
		}

		var changed = false;
		var index = songs.length - 1;
		while (index >= baseSongCount) {
			var song = songs[index];
			if (song.isProvisional && !desired.exists(song.pendingKey)) {
				removeSongAt(index);
				changed = true;
			}
			index--;
		}
		for (candidate in (importAvailability == null || importAvailability.pendingSongs == null
			? [] : importAvailability.pendingSongs)) {
			if (candidate == null || !desired.exists(candidate.key)
				|| indexForPendingKey(candidate.key) >= 0)
				continue;
			appendPendingSong(candidate);
			changed = true;
		}
		return changed;
	}

	function canPresentPendingSongs():Bool {
		return FreeplaySongAvailability.canPresentPendingSongs(curCategory, directOwnerRoot != '');
	}

	function candidateAlreadyInstalled(candidate:ImportRefreshPendingSong):Bool {
		for (index in 0...baseSongCount) {
			if (index < 0 || index >= songs.length)
				continue;
			var song = songs[index];
			if (candidate.destinationFolder != null
				&& FreeplaySongAvailability.samePathComponent(candidate.destinationFolder, song.songName)) {
				resolveSongIdentity(song);
				if (FreeplaySongAvailability.matchesInstalledDestination(candidate,
					song.ownerRoot, song.songName))
					return true;
			}
			var nameMayMatch = candidate.name != null
				&& FreeplaySongAvailability.samePathComponent(candidate.name, song.songName);
			var folderMayMatch = candidate.sourceFolder != null
				&& FreeplaySongAvailability.samePathComponent(candidate.sourceFolder, song.songName);
			if (candidate.sourceFolder != null && (nameMayMatch || folderMayMatch)) {
				resolveSongIdentity(song);
				if (FreeplaySongAvailability.matchesInstalledSource(candidate,
					song.ownerRoot, song.sourceFolder))
					return true;
			}
		}
		return false;
	}

	function indexForPendingKey(key:String):Int {
		for (index in baseSongCount...songs.length)
			if (songs[index].isProvisional && songs[index].pendingKey == key)
				return index;
		return -1;
	}

	function appendPendingSong(candidate:ImportRefreshPendingSong):Void {
		var opaqueId = Sha256.encode(candidate.key).substr(0, 16);
		var song = new SongMetadata('pending_' + opaqueId, -1, '', candidate.name, '');
		song.displayTitle = candidate.name;
		song.isProvisional = true;
		song.pendingKey = candidate.key;
		song.ownerRoot = candidate.ownerRoot;
		song.ownerResolved = true;
		song.sourceRoot = candidate.sourceRoot == null ? '' : candidate.sourceRoot;
		song.sourceFolder = candidate.sourceFolder == null ? '' : candidate.sourceFolder;
		song.destinationFolder = candidate.destinationFolder == null ? '' : candidate.destinationFolder;
		songs.push(song);
		if (songRows.length > 0) {
			songRows.push(null);
			sourceRows.push(null);
			iconArray.push(null);
			starArray.push(null);
		}
	}

	function removeSongAt(index:Int):Void {
		if (index < 0 || index >= songs.length)
			return;
		var row = index < songRows.length ? songRows[index] : null;
		if (row != null) {
			if (grpSongs != null) grpSongs.remove(row, true);
			row.destroy();
		}
		var source = index < sourceRows.length ? sourceRows[index] : null;
		if (source != null) {
			if (grpSongSources != null) grpSongSources.remove(source, true);
			source.destroy();
		}
		var icon = index < iconArray.length ? iconArray[index] : null;
		if (icon != null) {
			remove(icon, true);
			icon.destroy();
		}
		if (index < starArray.length && starArray[index] != null)
			for (star in starArray[index]) {
				FlxTween.cancelTweensOf(star);
				remove(star, true);
				star.destroy();
			}
		if (index < hxcCapsuleViews.length) {
			var capsule = hxcCapsuleViews[index];
			if (capsule != null) {
				var weekType:Dynamic = Reflect.field(capsule, 'weekType');
				if (weekType != null) {
					remove(weekType, true);
					if (Reflect.field(weekType, 'destroy') != null)
						Reflect.callMethod(weekType, Reflect.field(weekType, 'destroy'), []);
				}
			}
			hxcCapsuleViews.splice(index, 1);
		}
		if (index < songRows.length) songRows.splice(index, 1);
		if (index < sourceRows.length) sourceRows.splice(index, 1);
		if (index < iconArray.length) iconArray.splice(index, 1);
		if (index < starArray.length) starArray.splice(index, 1);
		songs.splice(index, 1);
		if (curSelected > index) curSelected--;
		else if (curSelected == index && songs.length > 0) curSelected = Std.int(Math.min(index, songs.length - 1));
		iconQueue.resize(0);
	}

	function resolveSongIdentity(song:SongMetadata):Void {
		if (song == null || song.isProvisional || song.identityResolved)
			return;
		song.identityResolved = true;
		var key = song.songName;
		if (key == null || key == '' || key.indexOf('/') >= 0 || key.indexOf('\\') >= 0 || key.indexOf('..') >= 0)
			return;
		var provenancePath = 'assets/data/' + key.toLowerCase() + '/importProvenance.json';
		if (FNFAssets.exists(provenancePath)) try {
			song.provenance = CoolUtil.parseJson(FNFAssets.getText(provenancePath));
			var sourceFolder:Dynamic = Reflect.field(song.provenance, 'sourceFolder');
			if (Std.isOfType(sourceFolder, String)) song.sourceFolder = cast sourceFolder;
		} catch (_:Dynamic) {}
		song.ownerRoot = ImportedModDiscovery.ownerForSong(key, 'assets/data');
		song.ownerResolved = true;
	}

	function songHasAnyChart(song:SongMetadata):Bool {
		if (song == null || song.isProvisional)
			return false;
		if (song.chartRevision == importAvailabilityRevision)
			return song.hasChart;
		var supported = DifficultyManager.getSupportedDiffs(song.songName);
		for (difficulty in supported)
			if (selectionHasChart(song.songName, difficulty)) {
				song.hasChart = true;
				song.chartRevision = importAvailabilityRevision;
				return true;
			}
		song.hasChart = false;
		song.chartRevision = importAvailabilityRevision;
		return false;
	}

	function songAvailability(index:Int):FreeplayAvailabilityDecision {
		if (index < 0 || index >= songs.length)
			return {ready:false, state:'missing-chart', reason:'No song is selected.'};
		var song = songs[index];
		if (song.isProvisional)
			return FreeplaySongAvailability.songReadiness(importAvailability, song.ownerRoot,
				false, null, true);
		if (soundTest)
			return {ready:true, state:'ready', reason:''};
		if (song.songName.toLowerCase() == 'random-song')
			return {ready:true, state:'ready', reason:''};
		if (song.availabilityRevision == importAvailabilityRevision && song.cachedAvailability != null)
			return song.cachedAvailability;
		resolveSongIdentity(song);
		var folder = safeSongFolder(song.songName) ? 'assets/data/' + song.songName.toLowerCase() : null;
		song.cachedAvailability = FreeplaySongAvailability.songReadiness(importAvailability,
			song.ownerRoot, songHasAnyChart(song), folder);
		song.availabilityRevision = importAvailabilityRevision;
		return song.cachedAvailability;
	}

	function refreshAvailabilityForInteraction():Void {
		var observed = ImportRefreshManager.availabilityRevision();
		if (importAvailability == null || observed != importAvailabilityRevision) {
			var next = ImportRefreshManager.availabilitySnapshot();
			if (next != null) {
				importAvailability = next;
				importAvailabilityRevision = next.revision;
				for (song in songs) {
					song.availabilityRevision = -1;
					song.chartRevision = -1;
				}
			}
		}
	}

	function safeSongFolder(name:String):Bool {
		return name != null && StringTools.trim(name) != '' && name.indexOf('/') < 0
			&& name.indexOf('\\') < 0 && name.indexOf('..') < 0 && name.indexOf(':') < 0;
	}
	#end

	function isProvisionalSelection(index:Int):Bool {
		return index >= 0 && index < songs.length && songs[index].isProvisional;
	}

	function availabilityAllowsSelection(index:Int, fresh:Bool = false):Bool {
		if (index < 0 || index >= songs.length || songs[index].isProvisional)
			return false;
		if (soundTest)
			return true;
		#if sys
		if (fresh) refreshAvailabilityForInteraction();
		return songAvailability(index).ready;
	#else
		return DifficultyManager.getSupportedDiffs(songs[index].songName).length > 0;
	#end
	}

	function availabilityAllowsLaunch(index:Int, difficulty:Int):Bool {
		if (!availabilityAllowsSelection(index, true) || !selectionHasChart(songs[index].songName, difficulty))
			return false;
		#if sys
		refreshAvailabilityForInteraction();
		#end
		return availabilityAllowsSelection(index) && selectionHasChart(songs[index].songName, difficulty);
	}

	function randomPlayableSelection():Int {
		var ready:Array<Int> = [];
		for (index in 0...songs.length) {
			if (!songMatches(index) || isProvisionalSelection(index)
				|| songs[index].songName.toLowerCase() == 'random-song')
				continue;
			var difficulty = DifficultyManager.getValidDiff(curDifficulty, songs[index].songName);
			if (availabilityAllowsLaunch(index, difficulty))
				ready.push(index);
		}
		return ready.length == 0 ? -1 : ready[FlxG.random.int(0, ready.length - 1)];
	}

	// The freeplay camera zooms out while SHIFT is held, and camera zoom shrinks
	// *everything* drawn through the camera - including the background, which no
	// longer covers the screen and leaves black borders on all sides. Growing the
	// background by the inverse of the zoom keeps it edge-to-edge at any zoom.
	// 1.02 overscans a touch so rounding can't expose a seam, and the value is
	// clamped at 1 so the normal (unzoomed) view is untouched.
	static function backgroundScaleFor(zoom:Float):Float {
		if (zoom <= 0 || zoom >= 1)
			return 1;
		return (1 / zoom) * 1.02;
	}

	// Point the screen-fixed chrome at a second, never-zooming camera and park
	// that camera's display object in front of the list so the chrome still
	// draws on top. (Both cameras are the same screen size, so no scaling.)
	function setupUICamera() {
		camUI = new FlxCamera();
		// transparent so the default camera's bg/list show through underneath
		camUI.bgColor.alpha = 0;
		FlxG.cameras.add(camUI, false); // not a default draw target
		for (element in uiChrome)
			if (element != null)
				element.cameras = [camUI];
		// cameras added later render later, so this would already be on top;
		// do it explicitly anyway so the chrome order can't drift
		FlxG.game.setChildIndex(camUI.flashSprite, FlxG.game.getChildIndex(FlxG.camera.flashSprite) + 1);
	}

	override function update(elapsed:Float) {
		#if sys
		ImportRefreshManager.browseTick();
		if (importRefreshGeneration != ImportRefreshManager.generation) {
			currentSongList = [];
			LoadingState.loadAndSwitchState(new FreeplayState());
			return;
		}
		refreshImportAvailability();
		#end
		var smokeProfile = RuntimeSmokeHarness.enabled();
		var profileMark = smokeProfile ? haxe.Timer.stamp() : 0.0;
		super.update(elapsed);
		RuntimeSourceChartingProbe.updateFreeplay();
		syncSourceRows();
		if (smokeProfile)
			RuntimeSmokeHarness.profileSection('fp-update-base', haxe.Timer.stamp() - profileMark);
		profileMark = haxe.Timer.stamp();
		var updateCapsule = hxcCapsuleView(curSelected);
		if (hxcRuntime != null && updateCapsule != null)
			hxcRuntime.dispatch('update', EngineCompat.hxcFreeplayPayload(
				'update', this, updateCapsule, curDifficulty, null));
		refreshHxcConfirm();
		if (smokeProfile)
			RuntimeSmokeHarness.profileSection('fp-update-hxc', haxe.Timer.stamp() - profileMark);
		profileMark = haxe.Timer.stamp();
		FlxG.camera.zoom = FlxMath.lerp(FlxG.camera.zoom, FlxG.keys.pressed.SHIFT ? SHIFT_ZOOM : 1.0, Math.min(1, elapsed * 12));
		// match the background to the camera zoom so it always fills the screen
		if (bg != null) {
			var bgScale:Float = backgroundScaleFor(FlxG.camera.zoom);
			if (Math.abs(bg.scale.x - bgScale) > 0.0001) {
				bg.scale.set(bgScale, bgScale);
				bg.updateHitbox();
				bg.screenCenter();
			}
		}
		// (mute the menu music completely while a preview plays - a partial
		// duck still let both play audibly at once)
		var previewing = previewSound != null && previewSound.playing;
		var musicHome = previewing ? 0.0 : 0.7;
		if (!soundTest || curDifficulty != 2) {
			if (previewing)
				// snap silent the moment a preview actually starts
				FlxG.sound.music.volume = 0;
			// recover slowly after the preview stops
			else if (FlxG.sound.music.volume < musicHome)
				FlxG.sound.music.volume += 0.5 * FlxG.elapsed;
		}

		// why the fuck does this exist
		lerpScore = FlxMath.lerp(lerpScore, intendedScore, CoolUtil.timeAdjustedLerpAlpha(0.4, elapsed));
		lerpAccuracy = Math.round(intendedAccuracy * 100) / 100;
		if (Math.abs(lerpScore - intendedScore) <= 10) lerpScore = intendedScore;
		if (!soundTest)
			scoreText.text = "PERSONAL BEST:" + Math.floor(lerpScore) + ", " + lerpAccuracy + "%";
		else
			scoreText.text = "Sound Test";

		var upP = controls.UP_MENU;
		var downP = controls.DOWN_MENU;
		#if debug
		if (FlxG.keys.justPressed.F5) {
			Highscore.saveScore('Tutorial', 0, 1, 0, Sick);
		}
		#end
		if (soundTest && soundTestSong != null)
			Conductor.songPosition += FlxG.elapsed * 1000;

		// trickle deferred icon/star creation in - a few per frame
		var buildBudget:Int = 4;
		while (iconQueue.length > 0 && buildBudget-- > 0)
			buildIconFor(iconQueue.shift());
		if (smokeProfile)
			RuntimeSmokeHarness.profileSection('fp-update-icons', haxe.Timer.stamp() - profileMark);

		// preview debounce: only after the selection has been idle a moment,
		// so scrolling never triggers audio loads
		if (previewTimer > 0) {
			previewTimer -= elapsed;
			if (previewTimer <= 0)
				startPreview();
		}

		// type-to-search: letters/digits filter the list, backspace deletes.
		// WASD-style nav keys that produce a character type instead of moving
		// on the frame they're typed so searching doesn't fight the controls
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
		// must not also accept/launch (typing "z" used to start the highlighted
		// song) - the same reason space only ever types
		var selectedVisible = curSelected >= 0 && curSelected < songs.length && songMatches(curSelected);
		var selectedRandom = selectedVisible && !soundTest
			&& songs[curSelected].songName.toLowerCase() == 'random-song';
		var accepted = controls.ACCEPT && typedChar.length == 0
			&& !FlxG.keys.justPressed.SPACE && selectedVisible
			&& (selectedRandom || availabilityAllowsSelection(curSelected));
		if (accepted && hxcConfirmToken != 0 && curSelected >= 0 && curSelected < songs.length) {
			if (selectedRandom || !availabilityAllowsSelection(curSelected, true)) {
				accepted = false;
				clearHxcConfirm();
				updateRenderedRowAvailability(curSelected);
			}
		}
		if (accepted && hxcConfirmToken != 0 && curSelected >= 0 && curSelected < songs.length) {
			var currentSongKey = songs[curSelected].songName;
			var selectedGeneration = hxcSelectionGeneration;
			var selectedToken = hxcConfirmToken;
			var capsule = hxcCapsuleView(curSelected);
			var callback:Dynamic = capsule == null ? null : Reflect.field(capsule, 'onConfirm');
			if (hxcConfirmGate.consumeFor(currentSongKey, selectedGeneration, selectedToken)
				&& callback != null && Reflect.isFunction(callback)) {
				hxcConfirmToken = 0;
				hxcConfirmSelectionKey = '';
				hxcConfirmGeneration = -1;
				hxcPendingPromptToken = selectedToken;
				hxcPendingPromptSelectionKey = currentSongKey.toLowerCase();
				hxcPendingPromptGeneration = selectedGeneration;
				var previousSubState = subState;
				try Reflect.callMethod(capsule, callback, []) catch (error:Dynamic) {
					trace('[hxc-freeplay-confirm-error] ' + currentSongKey + ': ' + Std.string(error));
					clearHxcPendingPrompt();
				}
				if (subState == previousSubState)
					clearHxcPendingPrompt();
				return;
			}
			clearHxcConfirm();
		}

		if (upP && typedChar.length == 0 && anyVisible())
			changeSelection(FlxG.keys.pressed.SHIFT ? -5 : -1);
		if (downP && typedChar.length == 0 && anyVisible())
			changeSelection(FlxG.keys.pressed.SHIFT ? 5 : 1);
		if (controls.LEFT_MENU && selectedVisible)
			changeDiff(-1);
		if (controls.RIGHT_MENU && selectedVisible)
			changeDiff(1);

		if (FlxG.keys.justPressed.DELETE && selectedVisible && !isProvisionalSelection(curSelected)) {
			Highscore.deleteSongScore(songs[curSelected].songName, curDifficulty);
			if (starArray[curSelected] != null)
				for (star in starArray[curSelected]) {
					star.checkStar();
				}
		}
		
		if (controls.LEFT_TAB && infoPanel != null && infoPanel.visible)
			infoPanel.changeDisplay(-1);
		else if (controls.RIGHT_TAB && infoPanel != null && infoPanel.visible)
			infoPanel.changeDisplay(1);
		if (controls.BACK && !FlxG.keys.justPressed.BACKSPACE) {
			// backspace is a search key here - only escape actually goes back
			previewGen++; // cancels any in-flight preview load
			stopPreviewSound();
			if (searchString.length > 0) {
				// escape clears an active search before leaving
				searchString = "";
				applySearchFilter();
			} else {
				// main menu or else we are cursed
				FlxG.autoPause = OptionsHandler.options.autoPause;
				if (soundTest)
					LoadingState.loadAndSwitchState(new SaveDataState());
				else {
					var importedCaller = ImportedFreeplayCaller.take(directOwnerRoot);
					if (importedCaller != null) {
						if (importedCaller.returnKind == 'package-picker') {
							FreeplayState.currentSongList = [];
							CodenameModRuntime.clearActiveOwner();
							LoadingState.loadAndSwitchState(new CodenameImportedModsState());
							return;
						} else {
							var target = CodenameModRuntime.stateInit(importedCaller.ownerRoot,
								importedCaller.scriptPath);
							if (Std.isOfType(target, flixel.FlxState)) {
								LoadingState.loadAndSwitchState(cast target);
								return;
							}
						}
					}
					var epicCategoryJs:Array<Dynamic> = cast FreeplayRegistry.getJson();
					if (epicCategoryJs.length > 1)
						LoadingState.loadAndSwitchState(new CategoryState());
					else
						LoadingState.loadAndSwitchState(new MainMenuState());
				}
			}
		}

		if (accepted) {
			// launching something - kill the preview before the switch
			previewGen++;
			stopPreviewSound();
			// im shortening this for my mind to be at rest
			if (soundTest) {
				// play both the vocals and inst
				// bad music >:(
				var suffix = "";
				if (nightcoreMode)
					suffix = "-Nightcore";
				if (daycoreMode)
					suffix = "-Daycore";
				var shit = "";
				
				FlxG.sound.music.stop();
				if (vocals != null) {
					vocals.stop();
					FlxG.sound.list.remove(vocals);
					vocals.destroy();
				}
				soundTestSong = Song.loadFromJson(songs[curSelected].songName.toLowerCase(), songs[curSelected].songName.toLowerCase());
				if (soundTestSong.needsVoices) {
					if (OptionsHandler.options.stressTankmen
						&& FNFAssets.exists("assets/music/" + soundTestSong.song + "Shit" + suffix + "_Voices" + TitleState.soundExt))
						shit = "Shit";
					var vocalSound = FNFAssets.getSound("assets/music/" + soundTestSong.song + shit + suffix + "_Voices" + TitleState.soundExt);
					vocals = new FlxSound().loadEmbedded(vocalSound);
					vocals.volume = curDifficulty != 1 ? 1 : 0;
					FlxG.sound.list.add(vocals);
					vocals.play();
					vocals.pause();
					vocals.looped = true;
				}
				if (OptionsHandler.options.stressTankmen
					&& FNFAssets.exists("assets/music/" + soundTestSong.song + "Shit" + suffix + "_Inst" + TitleState.soundExt))
					shit = "Shit";
				else
					shit = "";
				FlxG.sound.playMusic(FNFAssets.getSound("assets/music/" + soundTestSong.song + suffix + "_Inst" + TitleState.soundExt), curDifficulty == 2 ? 0 : 1);
				Conductor.mapBPMChanges(soundTestSong);
				Conductor.changeBPM(soundTestSong.bpm);
				if (soundTestSong.needsVoices) {
					resyncVocals();
				}
			} else {
			    var poop:String;
				var daSelection:Int = curSelected;
			    if (songs[curSelected].songName.toLowerCase() == 'random-song') {
					daSelection = randomPlayableSelection();
					if (daSelection < 0) {
						diffText.text = "NO READY SONGS";
						return;
					}
					curDifficulty = DifficultyManager.getValidDiff(curDifficulty,
						songs[daSelection].songName);
				}
				poop = songs[daSelection].songName.toLowerCase() + DifficultyIcons.getEndingFP(curDifficulty);
				if (!availabilityAllowsLaunch(daSelection, curDifficulty)) {
					updateRenderedRowAvailability(daSelection);
					RuntimeFreeplayDifficultyProbe.ordinaryRejectedSelection(songs[daSelection].songName, curDifficulty);
					return;
				}
				PlayState.SONG = Song.loadFromJson(poop, songs[daSelection].songName.toLowerCase());
				Song.attachFreeplayScoreSongId(PlayState.SONG, songs[daSelection].songName);

				PlayState.isStoryMode = false;
				PlayState.balls = 0;
				PlayState.watchedCutscene = false;
				ModifierState.isStoryMode = false;
				PlayState.storyDifficulty = curDifficulty;
				if (!OptionsHandler.options.skipModifierMenu)
					LoadingState.loadAndSwitchState(new ModifierState());
				else {
					if (FlxG.sound.music != null)
						FlxG.sound.music.stop();
					LoadingState.loadAndSwitchState(new PlayState());
				}
			}
		}
	}

	function changeDiff(change:Int = 0) {
		var previousDifficulty = curDifficulty;
		if (isProvisionalSelection(curSelected)) {
			diffText.text = "IMPORTING";
			intendedScore = 0;
			intendedAccuracy = 0;
			lerpScore = 0;
			lerpAccuracy = 0;
			if (infoPanel != null) infoPanel.visible = false;
			return;
		}
		if (infoPanel != null) infoPanel.visible = true;
		if (!soundTest) {
			refreshRankStarsFor(curSelected);
			// get valid one : )
			// also forces
			final difficultyObject:Dynamic = hxcDifficultyOrder.length > 0
				? hxcChangeDifficulty(change)
				: DifficultyManager.changeDifficultySans(curDifficulty, change, songs[curSelected].songName);
			
			curDifficulty = difficultyObject.difficulty;
			diffText.text = difficultyObject.text;

			#if !switch
			intendedScore = Highscore.getScore(songs[curSelected].songName, curDifficulty);
			intendedAccuracy = Highscore.getAccuracy(songs[curSelected].songName, curDifficulty) * 100;
			#end

			if (starArray[curSelected] != null)
			for (star in starArray[curSelected]) {
				var offset = star.diff == curDifficulty ? 25 : 0;
				if (star.selectoffset != offset) {
					FlxTween.cancelTweensOf(star);
					FlxTween.num(star.selectoffset, offset, 0.2, {ease: FlxEase.expoOut}, function(num) {
						star.selectoffset = num;
					});
				}
			}
		} else {
			curDifficulty = (curDifficulty + change) % 3;
			switch (curDifficulty) {
				case 0:
					diffText.text = "Both tracks";
				case 1:
					diffText.text = "Inst Only";
				case 2:
					diffText.text = "Vocals Only";
			}
			
		}
		// do it here for the sweet sweet gold record
		if (infoPanel != null)
			infoPanel.changeSong(songs[curSelected].songName, curDifficulty);
		if (hxcRuntime != null && previousDifficulty != curDifficulty && hxcCapsuleView(curSelected) != null)
			hxcRuntime.dispatch('difficultySwitch', EngineCompat.hxcFreeplayPayload(
			'difficultySwitch', this, hxcCapsuleView(curSelected), curDifficulty, null));
		if (OptionsHandler.options.style && false) {
			var coolors = iconArray[curSelected].healthColors;
			record.changeColor(coolors, songs[curSelected].songCharacter, songs[curSelected].week,
				songs[curSelected].songName, curDifficulty);
		}
	}

	/** Selection and both launch paths share the authoritative support list. */
	static function selectionHasChart(song:String, difficulty:Int):Bool {
		if (DifficultyManager.getSupportedDiffs(song).indexOf(difficulty) < 0) return false;
		var key = song.toLowerCase();
		return FNFAssets.exists('assets/data/' + key + '/' + key
			+ DifficultyManager.getDiffEnding(difficulty) + '.json');
	}

	function hxcChangeDifficulty(change:Int):Dynamic {
		if (hxcDifficultyOrder.length == 0)
			return DifficultyManager.changeDifficultySans(curDifficulty, change, songs[curSelected].songName);
		var currentName = DifficultyManager.getDiffName(curDifficulty);
		var index = hxcDifficultyOrder.indexOf(currentName);
		if (index < 0)
			index = 0;
		var attempts = 0;
		while (attempts++ < hxcDifficultyOrder.length) {
			index = (index + change) % hxcDifficultyOrder.length;
			if (index < 0)
				index += hxcDifficultyOrder.length;
			var candidate = DifficultyManager.getDiffNum(hxcDifficultyOrder[index]);
			// getDiffNum's legacy missing-name fallback is index zero. Verify
			// the resolved name before accepting it as an authored difficulty.
			if (DifficultyManager.getDiffName(candidate).toUpperCase()
				!= hxcDifficultyOrder[index].toUpperCase()) continue;
				var supported = DifficultyManager.getSupportedDiffs(songs[curSelected].songName);
				if (supported.indexOf(candidate) >= 0)
				return {difficulty: candidate, text: DifficultyManager.getDiffName(candidate)};
		}
		return DifficultyManager.changeDifficultySans(curDifficulty, change, songs[curSelected].songName);
	}
	override function stepHit() {
		super.stepHit();
		if (soundTest && soundTestSong != null && soundTestSong.needsVoices && curDifficulty == 0) {
			if (vocals.time > Conductor.songPosition + 20 || vocals.time < Conductor.songPosition - 20) {
				resyncVocals();
			}
		}
	}

	function resyncVocals():Void {
		vocals.pause();

		FlxG.sound.music.play();
		
		Conductor.songPosition = FlxG.sound.music.time;
		vocals.time = Conductor.songPosition;
		vocals.play();
	}

	// search matching: lowercase + alphanumeric only, so "bopeebo bside"
	// finds "Bopeebo-BSide" and dashes/spaces are interchangeable.
	// (public + static: CategoryState's category search shares it)
	public static function searchNorm(s:String):String {
		var buf = "";
		for (chr in s.toLowerCase().split(""))
			if ((chr >= "a" && chr <= "z") || (chr >= "0" && chr <= "9"))
				buf += chr;
		return buf;
	}

	function songMatches(i:Int):Bool {
		if (searchString.length == 0)
			return true;
		var needle = searchNorm(searchString);
		if (needle.length == 0)
			return true;
		var song = songs[i];
		var hay = searchNorm(song.songName);
		var display = searchNorm(song.display);
		if (hay.indexOf(needle) != -1 || display.indexOf(needle) != -1)
			return true;
		// Source labels are rendered separately from the title. Resolve them only
		// when the title misses, then keep the existing per-row cache for typing.
		sourceDisplayFor(song);
		return searchNorm(song.sourceLabel).indexOf(needle) != -1;
	}

	function anyVisible():Bool {
		for (i in 0...songs.length)
			if (songMatches(i))
				return true;
		return false;
	}

	/** Resolve a package subtitle only for a materialized row. Explicit registry
	 * labels win; same-folder provenance fills labels older imports did not store
	 * separately, without scanning every chart when Freeplay opens. */
	function sourceDisplayFor(song:SongMetadata):Void {
		if (song.sourceResolved)
			return;
		song.sourceResolved = true;
		if (song.isProvisional)
			return;
		var provenance:Dynamic = song.provenance;
		// Only rows without an explicit sourceLabel need a receipt lookup.  Rows
		// are materialized lazily and sourceResolved caches the result per song,
		// so this checks at most the visible imported candidates rather than
		// scanning every chart on entering Freeplay.  Reject path-shaped registry
		// names before constructing a path below assets/data.
		var songKey = song.songName;
		if (provenance == null && (song.sourceLabel == null || StringTools.trim(song.sourceLabel) == '')
			&& songKey != null && songKey != '' && songKey.indexOf('/') < 0
			&& songKey.indexOf('\\') < 0 && songKey.indexOf('..') < 0) {
			var path = 'assets/data/' + song.songName.toLowerCase() + '/importProvenance.json';
			if (FNFAssets.exists(path)) try {
				provenance = CoolUtil.parseJson(FNFAssets.getText(path));
				song.provenance = provenance;
			} catch (_:Dynamic) {}
		}
		var chartTitle = '';
		if (provenance != null && song.songName.indexOf('--') >= 0) {
			var modName:Dynamic = Reflect.field(provenance, 'modName');
			if (modName == null || StringTools.trim(Std.string(modName)) == '')
				chartTitle = legacyChartTitleFor(song.songName,
					Reflect.field(provenance, 'sourceFolder'));
		}
		var resolved = FreeplaySourceDisplay.resolve(song.display, song.sourceLabel,
			song.songName, provenance, chartTitle);
		song.displayTitle = resolved.title;
		song.sourceLabel = resolved.source;
	}

	/** Read only the selected owner's bounded chart directory when legacy
	 * provenance lacks a mod name and its Freeplay title differs from its ID. */
	function legacyChartTitleFor(songKey:String, sourceFolder:String):String {
		#if sys
		if (songKey == null || songKey == '' || songKey.indexOf('/') >= 0
			|| songKey.indexOf('\\') >= 0 || songKey.indexOf('..') >= 0)
			return '';
		if (sourceFolder == null || sourceFolder.indexOf('/') >= 0
			|| sourceFolder.indexOf('\\') >= 0 || sourceFolder.indexOf('..') >= 0)
			sourceFolder = '';
		var dir = 'assets/data/' + songKey.toLowerCase();
		if (!FileSystem.exists(dir) || !FileSystem.isDirectory(dir))
			return '';
		try {
			var names = FileSystem.readDirectory(dir);
			if (names.length > 128)
				return '';
			names.sort(Reflect.compare);
			for (name in names) {
				var lower = name.toLowerCase();
				if (!lower.endsWith('.json') || (!lower.startsWith(songKey.toLowerCase() + '-')
					&& lower != sourceFolder.toLowerCase() + '.json'))
					continue;
				var path = dir + '/' + name;
				if (FileSystem.isDirectory(path) || FileSystem.stat(path).size > 8388608)
					continue;
				var chart:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
				var data = chart == null ? null : Reflect.field(chart, 'song');
				var title:Dynamic = data == null ? null : Reflect.field(data, 'song');
				if (Std.isOfType(title, String) && StringTools.trim(cast title) != '')
					return StringTools.trim(cast title);
			}
		} catch (_:Dynamic) {}
		#end
		return '';
	}

	function syncSourceRows():Void {
		for (index in rowSongIndices) {
			var row = songRows[index];
			var source = sourceRows[index];
			if (row == null || source == null)
				continue;
			source.x = row.x + 10 * SONG_ROW_SCALE;
			source.y = row.y + 65 * SONG_ROW_SCALE;
			source.visible = row.visible;
			source.alpha = row.alpha;
		}
	}

	function rowAvailabilityDecision(index:Int):FreeplayAvailabilityDecision {
		#if sys
		return songAvailability(index);
		#else
		if (index < 0 || index >= songs.length)
			return {ready:false, state:'missing-chart', reason:'No song is selected.'};
		var song = songs[index];
		if (song.isProvisional)
			return {ready:false, state:'provisional', reason:'Importing. This song is unavailable until the package is committed.'};
		return songs[index].songName.toLowerCase() == 'random-song'
			? {ready:true, state:'ready', reason:''}
			: (DifficultyManager.getSupportedDiffs(song.songName).length > 0
				? {ready:true, state:'ready', reason:''}
				: {ready:false, state:'missing-chart', reason:'No supported chart is available for this song.'});
		#end
	}

	function rowAvailabilityReason(index:Int):String {
		return FreeplaySongAvailability.rowAvailabilityReason(rowAvailabilityDecision(index));
	}

	function updateRenderedRowAvailability(index:Int):Void {
		if (index < 0 || index >= songs.length || index >= songRows.length)
			return;
		var row = songRows[index];
		if (row == null)
			return;
		var song = songs[index];
		if (!song.isProvisional)
			sourceDisplayFor(song);
		var decision = rowAvailabilityDecision(index);
		var disabled = FreeplaySongAvailability.rowIsDisabled(decision);
		var tint:FlxColor = disabled ? 0xFF858585 : FlxColor.WHITE;
		for (member in row.members)
			if (member != null)
				member.color = tint;
		if (iconArray[index] != null)
			iconArray[index].color = tint;
		if (starArray[index] != null)
			for (star in starArray[index])
				star.color = tint;

		var subtitle = disabled ? FreeplaySongAvailability.rowAvailabilityReason(decision)
			: (song.sourceLabel == null || song.sourceLabel == '' ? '' : '(' + song.sourceLabel + ')');
		var source = sourceRows[index];
		if (subtitle == '') {
			if (source != null) {
				if (grpSongSources != null) grpSongSources.remove(source, true);
				source.destroy();
				sourceRows[index] = null;
			}
			return;
		}
		if (source == null) {
			source = new FlxText(0, 0, FlxG.width * 0.65, subtitle, 18);
			source.setFormat('assets/fonts/vcr.ttf', 18, FlxColor.WHITE, LEFT,
				OUTLINE, FlxColor.BLACK);
			source.scale.set(SONG_ROW_SCALE, SONG_ROW_SCALE);
			source.wordWrap = false;
			sourceRows[index] = source;
			if (grpSongSources != null) grpSongSources.add(source);
		} else {
			source.text = subtitle;
		}
		source.color = tint;
	}

	/**
		Keep the complete song registry globally indexed while only constructing
		the rows near the current selection. This bounds Alphabet's child sprites
		and per-frame updates without changing search or chart selection indexes.
	*/
	function rebuildVisibleRows():Void {
		var visible = FreeplayListWindow.visibleIndices(songs.length, songMatches);
		var desired = FreeplayListWindow.window(visible, curSelected, ROW_WINDOW_RADIUS);
		var wanted:Map<Int, Bool> = new Map();
		for (index in desired)
			wanted.set(index, true);

		for (index in rowSongIndices.copy()) {
			if (wanted.exists(index))
				continue;
			var row = songRows[index];
			if (row != null) {
				grpSongs.remove(row, true);
				row.destroy();
				songRows[index] = null;
			}
			var source = sourceRows[index];
			if (source != null) {
				grpSongSources.remove(source, true);
				source.destroy();
				sourceRows[index] = null;
			}
			var icon = iconArray[index];
			if (icon != null) {
				remove(icon, true);
				icon.destroy();
				iconArray[index] = null;
			}
			var stars = starArray[index];
			if (stars != null) {
				for (star in stars) {
					FlxTween.cancelTweensOf(star);
					remove(star, true);
					star.destroy();
				}
				starArray[index] = null;
			}
			if (index < hxcCapsuleViews.length && hxcCapsuleViews[index] != null) {
				Reflect.setField(hxcCapsuleViews[index], 'pixelIcon', null);
				var weekType:Dynamic = Reflect.field(hxcCapsuleViews[index], 'weekType');
				if (weekType != null)
					weekType.visible = false;
			}
		}

		rowSongIndices.resize(0);
		var selectedPosition = desired.indexOf(curSelected);
		for (position in 0...desired.length) {
			var index = desired[position];
			var row = songRows[index];
			var wasCreated = row == null;
			if (wasCreated) {
				sourceDisplayFor(songs[index]);
				row = new Alphabet(0, (70 * index) + 30, songs[index].displayTitle,
					true, false, false, null, null, null, true);
				row.setMenuTextScale(SONG_ROW_SCALE);
				row.menuMotionRate = SONG_ROW_MOTION_RATE;
				if (!OptionsHandler.options.style)
					row.itemType = "Classic";
				row.isMenuItem = true;
				songRows[index] = row;
				grpSongs.add(row);
			}
			var relativePosition = position - selectedPosition;
			row.targetY = relativePosition;
			row.visible = true;
			row.alpha = relativePosition == 0 ? 1 : 0.6;
			if (wasCreated)
				positionNewRow(row, relativePosition);
			updateRenderedRowAvailability(index);
			rowSongIndices.push(index);
		}
		applyListLayout();
		syncSourceRows();
	}

	/** Start newly materialized rows at their target so far-away songs do not
		animate from a y coordinate proportional to their absolute registry index. */
	function positionNewRow(row:Alphabet, targetY:Float):Void {
		var scaledY = FlxMath.remapToRange(targetY, 0, 1, 0, 1.3);
		switch (row.itemType) {
			case "Classic":
				row.x = (targetY * 20) + 90;
				row.y = (scaledY * 120) + (FlxG.height * 0.48);
			case "D-Shape":
				row.y = (scaledY * 90) + (FlxG.height * 0.45);
				row.x = Math.exp(Math.abs(scaledY * 0.8)) * -70 + (FlxG.width * 0.35);
				if (row.x < -900)
					row.x = -900;
			case "Vertical":
				row.y = (scaledY * 120) + (FlxG.height * 0.5);
			case "C-Shape":
				row.y = (scaledY * 65) + (FlxG.height * 0.39);
				row.x = Math.exp(scaledY * 0.8) * 70 + (FlxG.width * 0.1);
				if (scaledY < 0)
					row.x = Math.exp(scaledY * -0.8) * 70 + (FlxG.width * 0.1);
				if (row.x > FlxG.width + 30)
					row.x = FlxG.width + 30;
		}
	}

	// (re)fill the build queue with the not-yet-built indices nearest the
	// selection - only the closest INFO_WINDOW charts each way get icon +
	// rank-star info built at all
	function rebuildIconQueue() {
		iconQueue.resize(0);
		var selectedPosition = rowSongIndices.indexOf(curSelected);
		if (selectedPosition < 0)
			return;
		for (step in 0...rowSongIndices.length) {
			var up = selectedPosition + step;
			var down = selectedPosition - step;
			if (up < rowSongIndices.length) {
				var upIndex = rowSongIndices[up];
				if (iconArray[upIndex] == null && availabilityAllowsSelection(upIndex))
					iconQueue.push(upIndex);
			}
			if (step > 0 && down >= 0) {
				var downIndex = rowSongIndices[down];
				if (iconArray[downIndex] == null && availabilityAllowsSelection(downIndex))
					iconQueue.push(downIndex);
			}
		}
	}

	function buildIconFor(i:Int) {
		if (i < 0 || i >= songs.length || iconArray[i] != null || songRows[i] == null
			|| !availabilityAllowsSelection(i))
			return;
		var icon:HealthIcon = new HealthIcon(songs[i].songCharacter, false, false, false, songs[i].songName);
		icon.sprTracker = songRows[i];
		icon.visible = songMatches(i) && !OptionsHandler.options.style;
		iconArray[i] = icon;
		// Package subtitles are intentionally above icons when a long source
		// label extends beyond a short chart title.
		insert(members.indexOf(grpSongSources), icon);
		refreshRankStarsFor(i);
		if (i < hxcCapsuleViews.length && hxcCapsuleViews[i] != null)
			Reflect.setField(hxcCapsuleViews[i], 'pixelIcon', icon);
		if (i == curSelected) icon.alpha = 1;
	}

	/** Reconcile only the materialized row when refreshed support changes. */
	function refreshRankStarsFor(i:Int):Void {
		if (i < 0 || i >= songs.length || iconArray[i] == null || !availabilityAllowsSelection(i)) return;
		var supported = DifficultyManager.getSupportedDiffs(songs[i].songName);
		var previous = starArray[i];
		var same = previous != null && previous.length == supported.length;
		if (same) for (index in 0...supported.length)
			if (previous[index].diff != supported[index]) { same = false; break; }
		if (same) return;
		if (previous != null) for (star in previous) {
			FlxTween.cancelTweensOf(star);
			remove(star, true);
			star.destroy();
		}
		var icon = iconArray[i];
		var starCount:Array<RankStar> = [];
		for (diff in supported) {
			var rankStar:RankStar = new RankStar(songs[i].songName, diff);
			rankStar.sprTracker = icon;
			rankStar.starNum = starCount.length;
			rankStar.visible = songMatches(i) && !OptionsHandler.options.style;
			insert(members.indexOf(grpSongSources), rankStar);
			starCount.push(rankStar);
		}
		starArray[i] = starCount;
		if (i == curSelected) {
			for (star in starCount)
				star.checkStar();
		}
	}

	// ---- song previews: debounced, async-loaded, small LRU cache ----
	function previewInstPath(name:String):String {
		// freeplay names are usually lowercase while chart `song` fields are
		// often capitalized (the assets/music/<SongField>_Inst.ogg aliases),
		// so try several name forms across the CoolUtil.getSongFile layouts.
		// interpolation MUST use double quotes in Haxe - single-quoted
		// '${cand}' is a literal string
		var lower = name.toLowerCase();
		var titled = lower.charAt(0).toUpperCase() + lower.substr(1);
		// "beyond-the-stars" -> "Beyond-The-Stars" style aliases
		var wordTitled = "";
		var capNext = true;
		for (chr in lower.split("")) {
			var isAlpha = chr >= "a" && chr <= "z";
			wordTitled += capNext && isAlpha ? chr.toUpperCase() : chr;
			capNext = !isAlpha;
		}
		// chart names swap apostrophes for underscores ("it_s-complicated")
		var apos = name.split("_").join("'");
		for (cand in [name, lower, titled, wordTitled, apos]) {
			var p:String = "assets/music/" + cand + "_Inst" + TitleState.soundExt;
			if (FNFAssets.exists(p))
				return p;
			p = "assets/songs/" + cand + "/Inst" + TitleState.soundExt;
			if (FNFAssets.exists(p))
				return p;
			p = "assets/songs/" + cand + "/" + cand + "_Inst" + TitleState.soundExt;
			if (FNFAssets.exists(p))
				return p;
		}
		return null;
	}

	function startPreview() {
		if (curSelected < 0 || curSelected >= songs.length)
			return;
		var name = songs[curSelected].songName;
		if (soundTest || name.toLowerCase() == 'random-song'
			|| !availabilityAllowsLaunch(curSelected, curDifficulty))
			return;
		var path = previewInstPath(name);
		if (path == null)
			return;
		var gen = ++previewGen;
		var play = function(snd:Sound) {
			if (gen != previewGen || curSelected < 0 || curSelected >= songs.length
				|| !availabilityAllowsLaunch(curSelected, curDifficulty))
				return; // selection moved on while loading
			stopPreviewSound();
			previewSound = new FlxSound().loadEmbedded(snd);
			previewSound.volume = 0;
			previewSound.play();
			previewSound.fadeIn(1.2, 0, 0.55);
			FlxG.sound.list.add(previewSound);
		};
		var cached = previewCache.get(path);
		if (cached != null) {
			previewOrder.remove(path);
			previewOrder.push(path);
			play(cached);
			return;
		}
		// async load, uncached in openfl (we keep our own small LRU)
		if (openfl.utils.Assets.exists(path)) {
			openfl.utils.Assets.loadSound(path, false).onComplete(function(snd:Sound) {
				if (previewCache.exists(path))
					return;
				previewCache.set(path, snd);
				previewOrder.push(path);
				while (previewOrder.length > 5) {
					previewCache.remove(previewOrder.shift());
				}
				play(snd);
			});
		} else {
			// songs dropped in at runtime aren't in the asset manifest, and
			// loadSound silently never completes for those - load directly
			try {
				var snd = FNFAssets.getSound(path, false);
				if (previewCache.exists(path))
					return;
				previewCache.set(path, snd);
				previewOrder.push(path);
				while (previewOrder.length > 5) {
					previewCache.remove(previewOrder.shift());
				}
				play(snd);
			} catch (e:Any) {}
		}
	}

	function stopPreviewSound() {
		if (previewSound != null) {
			previewSound.stop();
			previewSound.kill();
			// kill() leaves it alive in the sound list holding its buffer
			FlxG.sound.list.remove(previewSound);
			previewSound = null;
		}
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
		if (!songMatches(curSelected) && anyVisible())
			changeSelection(0); // hops to the next visible song + refreshes
		else
			rebuildVisibleRows(); // clearing a search restores rows outside the old window
	}

	// Layout only the materialized window. songRows and the icon/star arrays
	// retain global song indexes; grpSongs is the small contiguous visible slice.
	function applyListLayout() {
		var selectedPosition = rowSongIndices.indexOf(curSelected);
		for (position in 0...rowSongIndices.length) {
			var index = rowSongIndices[position];
			var item = songRows[index];
			if (item == null)
				continue;
			var vis:Bool = songMatches(index);
			item.visible = vis;
			if (iconArray[index] != null)
				iconArray[index].visible = vis && !OptionsHandler.options.style;
			if (starArray[index] != null)
				for (star in starArray[index])
					star.visible = vis && !OptionsHandler.options.style;
			if (vis) {
				item.targetY = position - selectedPosition;
				item.alpha = 0.6;
				// item.setGraphicSize(Std.int(item.width * 0.8));

				if (item.targetY == 0) {
					item.alpha = 1;
					// item.setGraphicSize(Std.int(item.width));
				}
			}
		}
	}

	// steps `change` places through the list, skipping entries the search filter
	// hides; change == 0 just hops onto the next visible entry.
	// (shared with CategoryState's category search)
	public static function nextVisibleSelection(current:Int, change:Int, count:Int, matches:Int->Bool):Int {
		if (count == 0) return current;
		var direction = change < 0 ? -1 : 1;
		var moves = change == 0 ? 1 : Std.int(Math.abs(change));
		for (i in 0...moves) {
			if (change != 0) current = (current + direction + count) % count;
			var scanned = 0;
			while (!matches(current) && scanned++ < count)
				current = (current + direction + count) % count;
		}
		return current;
	}

	function changeSelection(change:Int = 0, refreshOnly:Bool = false) {
		// A prompt belongs to the capsule that armed it. Drop it before the
		// cursor moves so a later accept cannot open a previous song's popup.
		if (curSelected >= 0 && curSelected < hxcCapsuleViews.length
			&& hxcCapsuleViews[curSelected] != null)
			Reflect.setField(hxcCapsuleViews[curSelected], 'onConfirm', null);
		hxcSelectionGeneration++;
		clearHxcConfirm();
		clearHxcPendingPrompt();
		if (!refreshOnly)
			FlxG.sound.play('assets/sounds/custom_menu_sounds/'+CoolUtil.parseJson(FNFAssets.getText("assets/sounds/custom_menu_sounds/custom_menu_sounds.json")).customMenuScroll+'/scrollMenu' + TitleState.soundExt, 0.4);

		// reset the preview debounce on every selection move
		previewTimer = 0.6;
		previewGen++;

		if (starArray[curSelected] != null)
			for (star in starArray[curSelected]) {
				FlxTween.num(star.selectoffset, 0, 0.2, {ease: FlxEase.expoOut}, function(num) {
					star.selectoffset = num;
				});
			}

		if (!refreshOnly)
			curSelected = nextVisibleSelection(curSelected, change, songs.length, songMatches);
		rebuildVisibleRows();
		rebuildIconQueue(); // keep the info window centered on the new selection

		// selector.y = (70 * curSelected) + 30;

		#if false
		intendedScore = Highscore.getScore(songs[curSelected].songName, curDifficulty);
		intendedAccuracy = Highscore.getAccuracy(songs[curSelected].songName, curDifficulty);
		// lerpScore = 0;
		#end
		// comment out because lag?
		// if (!soundTest)
		//	FlxG.sound.playMusic(FNFAssets.getSound("assets/music/"+songs[curSelected].songName+"_Inst"+TitleState.soundExt), 0);
		for (index in rowSongIndices) {
			var icon = iconArray[index];
			if (icon != null)
				icon.alpha = 0.6;
		}
		if (iconArray[curSelected] != null)
			iconArray[curSelected].alpha = 1;

		// Rows outside the active window have no live display objects.
		/*
		var dealphaedColors:Array<FlxColor> = [];
		for (color in (Reflect.field(charJson,songs[curSelected].songCharacter).colors : Array<String>)) {
			var newColor = FlxColor.fromString(color);
			newColor.alphaFloat = 0.5;
			dealphaedColors.push(newColor);
		}*/
		//remove(curOverlay);
		//curOverlay = FlxGradient.createGradientFlxSprite(FlxG.width, FlxG.height, dealphaedColors);
		//insert(1, curOverlay);
		
		changeDiff();
		// trace(Highscore.getComplete(songs[0].songName, curDifficulty));

		if (iconArray[curSelected] != null) {
			var coolors = iconArray[curSelected].healthColors;
			FlxTween.cancelTweensOf(bg);
			FlxTween.color(bg, 0.5, bg.color, coolors[0]);

			if (OptionsHandler.options.style && record != null) {
				record.changeColor(coolors, songs[curSelected].songCharacter, songs[curSelected].week,
					songs[curSelected].songName, curDifficulty);
			}
		}

		if (infoPanel != null) {
			infoPanel.visible = !isProvisionalSelection(curSelected);
			if (infoPanel.visible)
				infoPanel.changeSong(songs[curSelected].songName, curDifficulty);
		}
		var selectedCapsule = hxcCapsuleView(curSelected);
		if (hxcRuntime != null && selectedCapsule != null)
			hxcRuntime.dispatch('capsuleSelected', EngineCompat.hxcFreeplayPayload(
			'capsuleSelected', this, selectedCapsule, curDifficulty, null));
	}

	/**
		Return the small native capsule view used by generic HXC selection hooks.
		It intentionally contains only fields backed by this FreeplayState; donor
		capsule collections and variation objects are not manufactured here.
	*/
	public function hxcCapsuleView(index:Int):Dynamic {
		if (index < 0 || index >= songs.length)
			return null;
		var song = songs[index];
		if (song.isProvisional || song.songName.toLowerCase() == 'random-song'
			|| !availabilityAllowsSelection(index))
			return null;
		while (hxcCapsuleViews.length <= index)
			hxcCapsuleViews.push(null);
		var capsule = hxcCapsuleViews[index];
		if (capsule == null) {
			var weekType = new HxcFreeplayWeekType();
			add(weekType);
			capsule = {
				name: song.songName,
				alive: true,
				pixelIcon: iconArray[index],
				weekType: weekType,
				controls: PlayerSettings.player1.controls,
				freeplayData: {
					levelId: song.songName,
					songCharacter: song.songCharacter,
					data: {id: song.songName}
				}
			};
			Reflect.setField(capsule, 'onConfirm', null);
			hxcCapsuleViews[index] = capsule;
		} else {
			Reflect.setField(capsule, 'pixelIcon', iconArray[index]);
		}
		return capsule;
	}

	/** Apply literal icon and overlay rules extracted from a scoped HXC module. */
	public function hxcApplyImportedFreeplayCustomization(capsule:Dynamic, plan:Dynamic):Bool {
		if (plan == null)
			return false;
		var targets:Array<Dynamic> = [];
		if (capsule == null) {
			// Only rendered rows have a native capsule view. This keeps imported
			// all-row hooks proportional to the visible list instead of allocating a
			// sprite for every song in the registry.
			for (index in rowSongIndices)
				targets.push(hxcCapsuleView(index));
		} else
			targets.push(capsule);
		var levelIds:Array<Dynamic> = cast Reflect.field(plan, 'levelIds');
		if (levelIds == null)
			return false;
		var applied = false;
		for (targetIndex in 0...targets.length) {
			var target = targets[targetIndex];
			if (target == null || Reflect.field(target, 'alive') == false)
				continue;
			var freeplayData:Dynamic = Reflect.field(target, 'freeplayData');
			if (freeplayData == null)
				continue;
			var levelId = Reflect.field(freeplayData, 'levelId');
			if (levelId == null || levelIds.indexOf(levelId) < 0)
				continue;
			var songCharacter = Std.string(Reflect.field(freeplayData, 'songCharacter'));
			var songData:Dynamic = Reflect.field(freeplayData, 'data');
			var songId = songData == null ? '' : Std.string(Reflect.field(songData, 'id'));
			var iconTarget = songCharacter;
			var characterRules:Array<Dynamic> = cast Reflect.field(plan, 'characterRules');
			if (characterRules != null)
				for (rule in characterRules)
					if (rule != null && Reflect.field(rule, 'key') == songCharacter)
						iconTarget = Std.string(Reflect.field(rule, 'icon'));
			var songRules:Array<Dynamic> = cast Reflect.field(plan, 'songRules');
			if (songRules != null)
				for (rule in songRules)
					if (rule != null && Reflect.field(rule, 'key') == songId)
						iconTarget = Std.string(Reflect.field(rule, 'icon'));
			var variationRules:Array<Dynamic> = cast Reflect.field(plan, 'variationRules');
			if (variationRules != null)
				for (rule in variationRules)
					if (rule != null && Reflect.field(rule, 'key') == songId)
						iconTarget = currentVariation == Reflect.field(rule, 'variation')
							? Std.string(Reflect.field(rule, 'matchIcon'))
							: Std.string(Reflect.field(rule, 'fallbackIcon'));
			var icon:Dynamic = Reflect.field(target, 'pixelIcon');
			if (icon != null && iconTarget != '' && Reflect.field(icon, 'character') != iconTarget) {
				var setCharacter = Reflect.field(icon, 'setCharacter');
				if (setCharacter != null && Reflect.isFunction(setCharacter)) {
					Reflect.callMethod(icon, setCharacter, [iconTarget]);
					var offset:Dynamic = Reflect.field(icon, 'offset');
					if (offset != null)
						Reflect.setField(offset, 'x', Reflect.field(plan, 'iconOffsetX'));
				}
			}
			var weekType:Dynamic = Reflect.field(target, 'weekType');
			if (Std.isOfType(weekType, HxcFreeplayWeekType)) {
				var animation = Std.string(Reflect.field(plan, 'defaultAnimation'));
				var animationOverrides:Array<Dynamic> = cast Reflect.field(plan, 'animationOverrides');
				if (animationOverrides != null)
					for (mapping in animationOverrides)
						if (mapping != null && Reflect.field(mapping, 'song') == songId)
							animation = Std.string(Reflect.field(mapping, 'animation'));
				applied = cast(weekType, HxcFreeplayWeekType).applyImportedDisplay(
					hxcAssetRoot, plan, animation) || applied;
			}
			applied = true;
		}
		return applied;
	}

	override function closeSubState():Void {
		super.closeSubState();
		clearHxcPendingPrompt();
		controls.active = true;
	}

	override function destroy() {
		if (hxcRuntime != null) {
			hxcRuntime.dispose();
			hxcRuntime = null;
		}
		FlxG.camera.zoom = 1;
		// the state's cameras are torn down by FlxGame.switchState/reset, but drop
		// our own camera explicitly in case this is destroyed another way
		if (camUI != null) {
			FlxG.cameras.remove(camUI);
			camUI = null;
		}
		uiChrome.resize(0);
		hxcCapsuleViews.resize(0);
		clearHxcConfirm();
		clearHxcPendingPrompt();
		hxcCapsuleGroup = null;
		hxcDifficultyOrder.resize(0);
		hxcAssetRoot = '';
		previewGen++;
		stopPreviewSound();
		if (vocals != null) {
			vocals.stop();
			FlxG.sound.list.remove(vocals);
			vocals.destroy();
		}
		super.destroy();
	}
}
class SongMetadata {
	public var songName:String = "";
	public var week:Int = 0;
	public var songCharacter:String = "";
	public var display:String = "";
	public var displayTitle:String = "";
	public var sourceLabel:String = "";
	public var sourceResolved:Bool = false;
	public var isProvisional:Bool = false;
	public var pendingKey:String = '';
	public var ownerRoot:String = '';
	public var ownerResolved:Bool = false;
	public var sourceRoot:String = '';
	public var sourceFolder:String = '';
	public var destinationFolder:String = '';
	public var identityResolved:Bool = false;
	public var provenance:Dynamic;
	public var availabilityRevision:Int = -1;
	public var cachedAvailability:Null<FreeplayAvailabilityDecision>;
	public var chartRevision:Int = -1;
	public var hasChart:Bool = false;

	public function new(song:String, week:Int, songCharacter:String, ?display:String, ?sourceLabel:String) {
		this.songName = song;
		this.week = week;
		this.songCharacter = songCharacter;
		this.display = display != null ? display : song;
		this.displayTitle = this.display;
		this.sourceLabel = sourceLabel == null ? '' : sourceLabel;
	}
}
typedef JsonMetadata = {
	var name:String;
	var week:Int;
	var character:String;
	var ?display:String;
	var ?sourceLabel:String;
	var ?artist:String;
	var ?songArtist:String;
	var ?album:String;
	var ?difficultyRatings:Array<Dynamic>;
	var ?flags:Array<String>;
}
