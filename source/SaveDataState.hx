package;

import OptionsHandler.FullOptions;
import haxe.ds.Option;
import OptionsHandler.TOptions;
import Controls.Control;
import flash.text.TextField;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
import flixel.math.FlxMath;
import flixel.text.FlxText;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxEase;
import flixel.util.FlxColor;
import lime.utils.Assets;
import Controls.KeyboardScheme;
import OptionsHandler.AccuracyMode;
// visual studio code gets pissy when you don't use conditionals
#if sys
import sys.io.File;
#end
import haxe.Json;
import tjson.TJSON;

#if (sys && windows)
import UpdateChecker.UpdateRelease;
import UpdateChecker.UpdateCheckResult;
#end

using StringTools;
typedef TOption = {
	var name:String;
	var intName:String;
	var value:Bool;
	var desc:String;
	var ?ignore:Bool;
	var ?amount:Float;
	var ?defAmount:Float;
	var ?precision:Float;
	var ?max:Float;
	var ?min:Float;
}
class SaveDataState extends MusicBeatState {
	var saves:FlxTypedSpriteGroup<SaveFile>;
	var options:FlxTypedSpriteGroup<Alphabet>;
	var optionMenu:FlxTypedSpriteGroup<FlxSprite>;
	// this will need to be initialized in title state!!!
	public static var optionList:Array<TOption>;
	var optionMask:Mask<FullOptions>;
	var curSelected:Int = 0;
	var amountRepeat:OptionsValueRepeat = new OptionsValueRepeat();
	var mappedOptions:Dynamic = {};
	var inOptionsMenu:Bool = false;
	var optionsSelected:Int = 0;
	var categoryRows:FlxTypedSpriteGroup<Alphabet>;
	var categoryHeading:FlxText;
	var categoryHelp:FlxText;
	var categorySelected:Int = 0;
	var inOptionCategory:Bool = false;
	var categoryOptions:Array<Int> = [];
	var checkmarks:FlxTypedSpriteGroup<FlxSprite>;
	var numberDisplays:Array<NumberDisplay> = [];
	var sfxJson:Dynamic = CoolUtil.parseJson(FNFAssets.getText("assets/sounds/custom_menu_sounds/custom_menu_sounds.json"));
	var musicJson:Dynamic = CoolUtil.parseJson(FNFAssets.getText("assets/music/custom_menu_music/custom_menu_music.json"));
	var preferredSave:Int = 0;
	var description:FlxText;
	var importWorkBusy:Bool = false;
	var forbiddenIndexes:Array<Int> = [];
	#if (sys && windows)
	var updateDialogBackground:FlxSprite;
	var updateDialogText:FlxText;
	var updateDialogVisible:Bool = false;
	var updateDialogMode:String = '';
	var updateCheckRequestId:Int = -1;
	var updateOffer:Null<UpdateRelease>;
	var updateInstallStatusPath:Null<String>;
	var lastInstallStatus:Null<String>;
	var updateProgressDismissed:Bool = false;
	#end
	public static var prevPath:String = 'title';
	override function create() {
		FlxG.sound.music.stop();
		var goodSound = FNFAssets.getSound('assets/music/custom_menu_music/'
			+ musicJson.Options
			+ '/options'
			+ TitleState.soundExt);
		optionMask = CoolUtil.parseJson(FNFAssets.getJson('assets/data/optionsMask'));
		FlxG.sound.playMusic(goodSound);
		var menuBG:FlxSprite = new FlxSprite().loadGraphic('assets/images/menuDesat.png');
			optionList = [
							{name: "Controls...", value: false, intName:'controls', desc:"Edit bindings!", ignore: true,},
							{name: "FPS Limit", value: false, intName: "fpsCap", desc: "Set any positive whole-number FPS limit. Shift + Left/Right changes 20 FPS. Hold Control to scroll faster.", amount: 60, defAmount: 60, max: OptionsHandler.MAX_FPS_CAP, min: 1, precision: 1},
							{name: "Unlimited FPS", value: false, intName: "unlimitedFPS", desc: "Removes the engine frame cap and updates on every rendered frame."},
							{name: "Show FPS Counter", value: false, intName: "showFPS", desc: "Shows current and average FPS in the top left"},
							{name: "Show Memory Counter", value: false, intName: "showMemory", desc: "Shows the memory counter in the top left"}, 
							{name: "Scroll Speed", value: false, intName: "scrollSpeed", desc: "Sets the scroll speed (1 uses the song's scroll speed)", amount: 1.0, defAmount: 1.0, max: 10.0, min: 1.0, precision: 0.1},
							{name: "Static Scroll Speed", value: false, intName: "dynamicScrollSpeed", desc: "0 = off. Nonzero fixes scroll speed across all charts and overrides Scroll Speed, including chart speed changes.", amount: OptionsHandler.DYNAMIC_SCROLL_SPEED_DEFAULT, defAmount: OptionsHandler.DYNAMIC_SCROLL_SPEED_DEFAULT, max: OptionsHandler.DYNAMIC_SCROLL_SPEED_MAX, min: OptionsHandler.DYNAMIC_SCROLL_SPEED_MIN, precision: OptionsHandler.DYNAMIC_SCROLL_SPEED_STEP},
							{name: "Downscroll", value: false, intName: "downscroll", desc: "Put da arrows on the bottom and have em scroll down"},
							{name: "Middlescroll", value: false, intName: "midscroll", desc: "Become the main attraction. Your story will be told"},
							{name: "Highway Dim", value: false, intName: "highwayDim", desc: "Puts a black veil behind your arrows so notes pop. 0 = off, 0.9 = 90% black.", amount: 0, defAmount: 0, max: 0.9, min: 0, precision: 0.1},
							{name: "Camera Zoom Events", value: false, intName: "zoomCamera", desc: "Allow imported charts to add gameplay/HUD camera zoom."},
							{name: "Flashing Lights", value: false, intName: "flashingLights", desc: "Allow imported charts to flash the gameplay or HUD camera."},
							{name: "Vignette Effects", value: false, intName: "vignetteEffects", desc: "Allow imported charts to render vignette overlays."},
							{name: "Song Lyrics", value: false, intName: "lyricsEnabled", desc: "Show lyrics and captions authored by imported songs."},
							{name: "Always Show Cutscenes", intName: "alwaysDoCutscenes", value: false, desc: "Force show cutscenes, even in freeplay"}, 
							{name: "Skip Modifier Menu", value: false, intName: "skipModifierMenu", desc: "Skip the modifier menu"}, 
							{name: "Skip Victory Screen", value: false, intName : "skipVictoryScreen", desc: "Skip the victory screen at the end of songs."},
							{name: "Don't mute on miss", intName: "dontMuteMiss", value: false, desc: "When missing notes, don't mute vocals"},
							{name: "Normalize Song Audio", value: false, intName: "normalizeSongAudio", desc: "Balance vocal and instrumental loudness. Takes effect when a song loads."},
							{name: "Judge", value: false, intName: "judge", desc: "The Judge to use.", amount: cast Judge.Jury.Classic, defAmount: cast Judge.Jury.Classic, max: 10},
							{name: "Ghost Tapping", value: false, intName: "useCustomInput", desc: "Whether to allow spamming"},
							{name: "Sing Whenever", value: false, intName: "singYourHeartOut", desc: "Lets you do the sing animation whenever you want (Requires ghost tapping)"},
							{name: "Modern Sustains", value: false, intName: "modernSustains", desc: "Sustain notes will play animations like in modern FNF, not repeating the animation"},
							{name: "Move cam with notes", value: false, intName: "camNotes", desc: "Moves the camera in the direction of the notes."},
							// sorry, always ignore bad timing :penisve:
							/*{name: "Ignore Bad Timing", value: false, intName:"ignoreShittyTiming", desc: "Even with new input on, if you hit a note really poorly, it counts as a miss. This disables that."},*/
							{name: "Show Song Position", value: false, intName: "showSongPos", desc: "Whether to show the song bar."},
							{name: "Show Timings", value: false, intName: "showTimings", desc: "Whether to show the timings after hitting a note."},
							{name: "Show Note Splashes", value: false, intName: "showNoteSplashes", desc: "Whether to show the note splahes for getting a sick."},
							{name: "Style", value: false, intName: "style", desc: "Whether to use fancy style or default to base game."},
							{
								name: "Ignore Unlocks",
								value: false,
								intName: "ignoreUnlocks",
								desc: "Show/Unlock all songs/weeks, even if you haven't met conditions."
							},
							{
								name: "New Judgement Layout",
								value: false,
								intName: "newJudgementPos",
								desc: "Put judgements in a more convenient place."
							},
							{name: "Overwrite Judgement", value: false, intName: "preferJudgement", desc: "What judgement to display other than default, if any.", defAmount: 0, amount: 0, max: CoolUtil.coolTextFile('assets/data/judgements.txt').length - 1},
							{name: "Emulate Osu Lifts", value: false, intName: "emuOsuLifts", desc: "Whether to add lift notes at the end of sustains to force releasing buttons."},
							{name: "Show Combo Breaks", value: false, intName:"showComboBreaks", desc: "Whether to display any combo breaks by flashing the screen."},
							{name: "Funny Songs", value: false, intName: "stressTankmen", desc: "funny songs"},
							{name: "Use Kade Health", value: false, intName: "useKadeHealth", desc: "Use kade engines health numbers when healing and dealing damage"},
							{name: "Healthbar Uses Chars' Colors", value: false, intName: "useCharColor", desc: "Makes the health bar use the characters' colors"},
							{name: "Use Miss Stun", value: false, intName: "useMissStun", desc: "Prevent hitting notes for a short time after missing."},
							{name: "Don't Use Vile Rating", value: false, intName: "ignoreVile", desc: "Don't use the \"Vile\" rating"},
							{name: "Offset", value: false, intName: "offset", desc: "How much to offset notes when playing. Shift + Left/Right changes 20 ms at a time. Hold Control to scroll faster.", amount: 0, defAmount: 0, max: 1000, min: -1000, precision: 0.1,},
							{name: "Calibrate Offset...", value: false, intName: 'calibrate', desc: "Tap SPACE with the metronome to measure your audio latency (Bluetooth etc.) and set the offset for you.", ignore: true,},
							{name: "Accuracy Mode", value: false, intName: "accuracyMode", desc: "How accuracy is calculated. Complex = uses ms timing, Simple = uses rating only", amount: 0, defAmount: 0, min: -1, max: 2,},
							{name: "Credits", value: false, intName:'credits', desc: "Show the credits!", ignore: true},
							{name: "Sound Test...", value: false, intName: 'soundtest', desc: "Listen to the soundtrack", ignore: true,},
							{name: "Hit Sounds", value: false, intName:"hitSounds", desc: "Play a sound when hitting a note"},
							{name: "Allow Story Mode", value: false, intName:"allowStoryMode", desc: "Show story mode from the main menu."},
							{name: "Allow Freeplay", value: false, intName:"allowFreeplay", desc: "Show freeplay from the main menu."},
							{name: "Fast Scene Transitions", value: false, intName:"fastSceneTransitions", desc: "Make scene fade-in and fade-out transitions three times faster."},
							#if sys
							{name: "Toggle Title Background", value: true, intName:'titleToggle', desc:"Turn on/off the title screen background.", ignore: true,},
							//{name: "UI Layout...", value: false, intName:'newui', desc: "Change the layout of the UI in-game!", ignore: true,},
								{name:"Module...", value:false, intName:'module', desc: "Make new stuff!", ignore: true,},
								{name:"newModule...", value:false, intName:'newmodule', desc: "Make newnew stuff!", ignore: true,},
								{name:"Import Settings...", value:false, intName:'importSettings', desc: "Choose the song importer.", ignore: true,},
								#if windows
								{name:"Check for Updates...", value:false, intName:'checkUpdates', desc: "Check for a newer Windows release and choose whether to download and install it.", ignore:true,},
								#end
							//{name:"New Character...", value: false, intName:'newchar', desc: "Make a new character!", ignore: true,},
							//{name:"New Stage...", value:false, intName:'newstage', desc: "Make a new stage!", ignore: true,},
							//{name: "New Song...", value: false, intName:'newsong', desc: "Make a new song!", ignore: true,},
							//{name: "New Week...", value: false, intName: 'newweek', desc: "Make a new week!", ignore: true,},
							{name: "Sort...", value: false, intName: 'sort', desc: "Sort some of your current songs/weeks!", ignore : true,}
							#end
						];
		var kidsToKill:Array<TOption> = [];
		for (option in optionList) {
			if (Reflect.field(optionMask, option.intName) != null && !Reflect.field(optionMask, option.intName))
				kidsToKill.push(option);
		}
		for (kid in kidsToKill) {
			optionList.remove(kid);
		}
		// amount of things that aren't options
		var curOptions:TOptions = OptionsHandler.options;
		for (i in 0...optionList.length) {
			if (optionList[i].ignore)
				continue;
			Reflect.setField(mappedOptions, optionList[i].intName, optionList[i]);
			optionList[i].value = Reflect.field(curOptions, optionList[i].intName);
			if ((Reflect.field(curOptions, optionList[i].intName) is Int) || (Reflect.field(curOptions, optionList[i].intName) is Float)) {
				optionList[i].amount = Reflect.field(curOptions, optionList[i].intName);
				optionList[i].value = optionList[i].amount != optionList[i].defAmount;
			}
		}
		// we use a var because if we don't it will read the file each time
		// although it isn't as laggy thanks to assets
		
		preferredSave = curOptions.preferredSave;
		saves = new FlxTypedSpriteGroup<SaveFile>();
		menuBG.color = 0xFF7194fc;
		menuBG.setGraphicSize(Std.int(menuBG.width * 1.1));
		menuBG.updateHitbox();
		menuBG.screenCenter();
		menuBG.antialiasing = true;
		trace("before");
		for (i in 0...10) {
			var saveFile = new SaveFile(420, 0, i);

			saves.add(saveFile);
		}
		trace("x3");
		checkmarks = new FlxTypedSpriteGroup<FlxSprite>();
		options = new FlxTypedSpriteGroup<Alphabet>();
		optionMenu = new FlxTypedSpriteGroup<FlxSprite>();
		optionMenu.add(options);
		trace("hmmm");
		var curNum = 0;
		for (j in 0...optionList.length) {
			if (Reflect.field(optionMask, optionList[j].intName) != null && !Reflect.field(optionMask, optionList[j].intName)) {
				// skip display if it is masked out
				continue;
			}
			forbiddenIndexes.push(j);
			trace("l53");
			var swagOption = new Alphabet(0,0,optionList[j].name,true,false, false, 90, 0.48);
			var rowTextScale = Math.min(0.85, 620 / Math.max(1, swagOption.width));
			swagOption.isMenuItem = true;
			swagOption.menuMotionRate = 2;
			swagOption.menuRowSpacing = 96;
			swagOption.itemType = "Classic";
			swagOption.targetY = curNum;
			trace("l57");
			var coolCheckmark = new FlxSprite().loadGraphic('assets/images/checkmark.png');
			coolCheckmark.scale.set(0.55, 0.55);
			coolCheckmark.updateHitbox();
			coolCheckmark.x = -70;
			var numDisplay = new NumberDisplay(0, 0, optionList[j].defAmount, optionList[j].precision != null ? optionList[j].precision : 1, optionList[j].min != null ? optionList[j].min : 0, optionList[j].max);
			numDisplay.visible = optionList[j].amount != null;
			numberDisplays.push(numDisplay);
			numDisplay.value = optionList[j].amount;
			coolCheckmark.visible = optionList[j].value;
			if (optionList[j].intName == "judge") {
				switch (cast(Std.int(optionList[j].amount) : Judge.Jury)) {
					case Judge.Jury.Classic:
						numDisplay.text = "Classic";
					case Judge.Jury.Hard:
						numDisplay.text = "Hard";
					default:
						numDisplay.text = optionList[j].amount + 1 + "";
				}
			}
			numDisplay.size = 40;
			numDisplay.x += numDisplay.width + swagOption.width;
			
			checkmarks.add(coolCheckmark);
			swagOption.add(coolCheckmark);
			swagOption.add(numDisplay);
			swagOption.setMenuTextScale(rowTextScale);
			options.add(swagOption);
			curNum++;
		}
		add(menuBG);
		add(saves);
		add(optionMenu);
		trace("hewwo");
		options.x = 10;
		optionMenu.x = FlxG.width;
		options.y = 10;
		description = new FlxText(750, 150, 350, "", 90);
		description.setFormat("assets/fonts/vcr.ttf", 32, FlxColor.WHITE, LEFT, OUTLINE, FlxColor.BLACK);
		description.text = "Amongus???";
		description.scrollFactor.set();
		optionMenu.add(description);
		description.setFormat("assets/fonts/vcr.ttf", 27, FlxColor.WHITE, LEFT, OUTLINE, FlxColor.BLACK);
		categoryRows = new FlxTypedSpriteGroup<Alphabet>();
		var sectionNames = OptionsCategories.names();
		for (index in 0...sectionNames.length) {
			var row = new Alphabet(90, FlxG.height * 0.48 + index * 96,
				sectionNames[index], true, false, false, 90, 0.48);
			row.isMenuItem = true;
			row.itemType = "Classic";
			row.targetY = index;
			row.menuMotionRate = 2;
			row.menuRowSpacing = 96;
			// Section names are longer than most option labels; use one smaller
			// Scale long section names to the same column as the option labels.
			row.setMenuTextScale(Math.min(0.85, 620 / Math.max(1, row.width)));
			categoryRows.add(row);
		}
		optionMenu.add(categoryRows);
		categoryHeading = new FlxText(140, 28, FlxG.width - 160, "", 28);
		categoryHeading.setFormat("assets/fonts/vcr.ttf", 28, FlxColor.WHITE, LEFT, OUTLINE, FlxColor.BLACK);
		optionMenu.add(categoryHeading);
		categoryHelp = new FlxText(20, FlxG.height - 42, FlxG.width - 40, "", 17);
		categoryHelp.setFormat("assets/fonts/vcr.ttf", 17, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		optionMenu.add(categoryHelp);
		refreshCategoryRows();
		#if (sys && windows)
		updateDialogBackground = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, FlxColor.fromRGB(0, 0, 0, 220));
		updateDialogBackground.scrollFactor.set();
		updateDialogBackground.visible = false;
		add(updateDialogBackground);
		updateDialogText = new FlxText(90, 145, FlxG.width - 180, '', 420);
		updateDialogText.setFormat('assets/fonts/vcr.ttf', 24, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		updateDialogText.scrollFactor.set();
		updateDialogText.visible = false;
		add(updateDialogText);
		updateInstallStatusPath = UpdateChecker.activeInstallStatusPath();
		add(new UpdateProgressBar());
		#end
		changeSelection();
		if (curOptions.allowEditOptions)
			swapMenus();
		#if sys
		add(new ImportRefreshProgressBar(this));
		#end
		super.create();
	}
	override function update(elapsed:Float) {
		super.update(elapsed);
		#if sys
		importWorkBusy = ImportRefreshManager.browseTick().busy;
		#end
		#if (sys && windows)
		pollUpdateCheck();
		pollUpdateInstall();
		if (handleUpdateDialog()) {
			amountRepeat.reset();
			return;
		}
		#end
		if (controls.BACK) {
			if (inOptionsMenu && inOptionCategory) {
				inOptionCategory = false;
				amountRepeat.reset();
				playMenuSound('cancel');
				refreshCategoryRows();
				return;
			}
			if (!saves.members[curSelected].beingSelected) {
				// our current save saves this
				// we are gonna have to do some shenanagins to save our preffered save

				saveOptions();
				FlxG.sound.music.stop();
				if (prevPath == 'freeplay') {
					#if sys
					var folder = PlayState.SONG == null ? '' : Song.storageFolder(PlayState.SONG);
					var owner = folder == '' ? '' : ImportedModDiscovery.ownerForSong(folder, 'assets/data');
					var ready = folder != '' && FreeplaySongAvailability.songReadiness(
						ImportRefreshManager.availabilitySnapshot(), owner,
						DifficultyManager.getSupportedDiffs(folder).length > 0, 'assets/data/' + folder.toLowerCase()).ready;
					LoadingState.loadAndSwitchState(ready ? new PlayState() : new FreeplayState());
					#else
					LoadingState.loadAndSwitchState(new PlayState());
					#end
				} else
					LoadingState.loadAndSwitchState(new MainMenuState());
			} else {
				if (saves.members[curSelected].askingToConfirm)
					saves.members[curSelected].askToConfirm(false);
				else
					saves.members[curSelected].beSelected(false);
			}
			return;
		}
		if (inOptionsMenu || !saves.members[curSelected].askingToConfirm) {
			if (controls.UP_MENU) {
				if (inOptionsMenu||!saves.members[curSelected].beingSelected)
					changeSelection(-1);
			}
			if (controls.DOWN_MENU) {
				if (inOptionsMenu||!saves.members[curSelected].beingSelected)
					changeSelection(1);
			}
			if ((controls.RIGHT_MENU || controls.LEFT_MENU)) {
				if (saves.members[curSelected].beingSelected)
					saves.members[curSelected].changeSelection();
				else if (inOptionsMenu && inOptionCategory && optionList[optionsSelected].amount != null) {
					if (!(inOptionsMenu && FlxG.keys.pressed.CONTROL))
						changeAmount(controls.RIGHT_MENU);

				}	else if (!inOptionsMenu || !inOptionCategory) {
					if ((OptionsHandler.options.allowEditOptions && !inOptionsMenu) || (OptionsHandler.options.useSaveDataMenu && inOptionsMenu))
						swapMenus();

				}
			}
		}
		var repeatDirection = controls.RIGHT_MENU_H ? 1 : controls.LEFT_MENU_H ? -1 : 0;
		var repeatAllowed = inOptionsMenu && inOptionCategory && FlxG.keys.pressed.CONTROL
			&& optionList[optionsSelected].amount != null && numberDisplays[optionsSelected].visible;
		var repeatChanges = amountRepeat.update(repeatDirection, elapsed, optionsSelected, repeatAllowed);
		if (repeatChanges > 0) {
			for (i in 0...repeatChanges)
				changeAmount(repeatDirection > 0);
		}
		if (controls.ACCEPT) {
			if (importWorkBusy && !inOptionsMenu) {
				playMenuSound('cancel'); return;
			}
			if (inOptionsMenu && inOptionCategory && !ImportMenuNavigationPolicy.optionsActionAllowed(importWorkBusy, optionList[optionsSelected].name)) {
				description.text = 'An import is still running. You can browse available songs or return to the importer.';
				playMenuSound('cancel'); return;
			}
			if (inOptionsMenu && !inOptionCategory) {
				openOptionCategory();
				return;
			}
			if (saves.members[curSelected].beingSelected) {
				if (!saves.members[curSelected].askingToConfirm) {
					if (saves.members[curSelected].selectingLoad) {
						var saveName = "save" + curSelected;
						FlxG.save.close();
						preferredSave = curSelected;
						FlxG.save.bind(saveName, "bulbyVR");
						FlxG.sound.play('assets/sounds/custom_menu_sounds/'
							+ CoolUtil.parseJson(FNFAssets.getText("assets/sounds/custom_menu_sounds/custom_menu_sounds.json")).customMenuConfirm+'/confirmMenu.ogg');
						// don't edit the djkf
						if (FlxG.save.data.songScores == null)
							FlxG.save.data.songScores = ["tutorial" => 0];
						Highscore.load();
					} else {
						saves.members[curSelected].askToConfirm(true);
					}

				} else {
					// this means the user confirmed!
					var oldSave = FlxG.save.name;
					var saveName = "save" + curSelected;
					FlxG.save.bind(saveName, "bulbyVR");
					FlxG.save.erase();
					saves.members[curSelected].askToConfirm(false);
					// sounds like someone farted into the mic. perfect for a delete sfx
					FlxG.sound.play('assets/sounds/freshIntro.ogg');
					FlxG.save.data.songScores = ["tutorial" => 0];
					FlxG.save.bind(oldSave, "bulbyVR");
					Highscore.load();
				}
			} else if (!inOptionsMenu) {
				FlxG.sound.play('assets/sounds/custom_menu_sounds/'
					+ sfxJson.customMenuScroll+'/scrollMenu' + TitleState.soundExt);
				saves.members[curSelected].beSelected(true);
			} else {
				switch (optionList[optionsSelected].name) {
					case "New Character...":
						// our current save saves this
						// we are gonna have to do some shenanagins to save our preffered save

						saveOptions();
						LoadingState.loadAndSwitchState(new NewCharacterState());
					case "New Stage...":
						// our current save saves this
						// we are gonna have to do some shenanagins to save our preffered save

						saveOptions();

						LoadingState.loadAndSwitchState(new NewStageState());
					case "New Song...":
						saveOptions();

						LoadingState.loadAndSwitchState(new NewSongState());
					case "Module...":
						saveOptions();

						LoadingState.loadAndSwitchState(new ModuleState());
					case "newModule...":
						saveOptions();

						LoadingState.loadAndSwitchState(new NewModule());
					case "Import Settings...":
						saveOptions();

						LoadingState.loadAndSwitchState(new ImportSettingsState());
					#if windows
					case "Check for Updates...":
						beginUpdateCheck();
					#end
					case "New Week...":
						saveOptions();
						NewWeekState.sorted = false;
						LoadingState.loadAndSwitchState(new NewWeekState());
					case "Sort...":
						saveOptions();

						LoadingState.loadAndSwitchState(new SelectSortState());
					case "UI Layout...":
						//saveOptions();

						//LoadingState.loadAndSwitchState(new SongUIState());
					case "Sound Test...":
						saveOptions();
						FreeplayState.soundTest = true;
						CategoryState.choosingFor = "freeplay";
						LoadingState.loadAndSwitchState(new CategoryState());
					case "Controls...":
						saveOptions();
						LoadingState.loadAndSwitchState(new ControlsState());
					case "Calibrate Offset...":
						saveOptions();
						LoadingState.loadAndSwitchState(new CalibrationState());
					case "Credits": 
						saveOptions();
						LoadingState.loadAndSwitchState(new CreditsState());
					default:
						if (OptionsHandler.options.allowEditOptions){
							checkmarks.members[optionsSelected].visible = !checkmarks.members[optionsSelected].visible;
							optionList[optionsSelected].value = checkmarks.members[optionsSelected].visible;
						}
				}

				FlxG.sound.play('assets/sounds/custom_menu_sounds/'
					+ CoolUtil.parseJson(FNFAssets.getText("assets/sounds/custom_menu_sounds/custom_menu_sounds.json")).customMenuScroll+'/scrollMenu' + TitleState.soundExt);
			}
		}

	}
	#if (sys && windows)
	function beginUpdateCheck():Void {
		if (updateCheckRequestId >= 0 || updateInstallStatusPath != null) return;
		var currentTag = UpdateChecker.installedReleaseTag();
		var installedLabel = currentTag == 'unknown'
			? 'unknown (app version v' + EngineBranding.version() + ')'
			: currentTag;
		showUpdateDialog('Checking GitHub releases...\nInstalled release: ' + installedLabel
			+ '\n\nBACK: dismiss', 'checking');
		updateCheckRequestId = UpdateChecker.beginCheck(currentTag);
	}

	function pollUpdateCheck():Void {
		if (updateCheckRequestId < 0) return;
		var result:UpdateCheckResult = UpdateChecker.takeCheckResult(updateCheckRequestId);
		if (result == null) return;
		updateCheckRequestId = -1;
		if (result.error != null) {
			showUpdateDialog('Could not check for updates.\n' + result.error + '\n\nACCEPT or BACK: close', 'message');
			return;
		}
		var latest = result.latest;
		if (latest == null) {
			showUpdateDialog('No Windows release package is available.\n\nACCEPT or BACK: close', 'message');
			return;
		}
		var currentLabel = result.currentTag == 'unknown'
			? 'unknown (app version v' + EngineBranding.version() + ')'
			: result.currentTag;
		if (!result.updateAvailable) {
			showUpdateDialog('Installed: ' + currentLabel + '\nLatest: ' + latest.tag
				+ '\n\nYou are up to date.\n\nACCEPT or BACK: close', 'message');
			return;
		}
		updateOffer = latest;
		showUpdateDialog('Update available\nInstalled: ' + currentLabel + '\nLatest: ' + latest.tag
			+ '\nDownload size: ' + UpdateChecker.formatSize(latest.sizeBytes)
			+ '\n\nThe full Windows package will download and install after you close the game.'
			+ '\nSettings and imported content are preserved. Existing asset files stay in place, so static asset changes require a manual clean install.'
			+ '\n\nACCEPT: download and install\nBACK: cancel', 'prompt');
	}

	function pollUpdateInstall():Void {
		if (updateInstallStatusPath == null) return;
		var status = UpdateChecker.readInstallStatus(updateInstallStatusPath);
		if (status == null || status == lastInstallStatus) return;
		lastInstallStatus = status;
		if (updateProgressDismissed) return;
		switch (status) {
			case 'downloading':
				showUpdateDialog('Downloading the full Windows package...\nThis can take a while. You can keep playing; the verified update installs after the game closes.\n\nBACK: hide this message', 'progress');
			case 'verifying':
				showUpdateDialog('Download complete. Verifying the ZIP against GitHub and its release checksum...\n\nBACK: hide this message', 'progress');
			case 'extracting':
				showUpdateDialog('The package is verified. Preparing the files for installation...\n\nBACK: hide this message', 'progress');
			case 'ready':
				showUpdateDialog('The update is verified and ready. It will install automatically after you close the game. You can keep playing.\n\nSettings and imported content are preserved. Existing asset files stay in place, so static asset changes require a manual clean install.\n\nBACK: close', 'ready');
			case 'installing':
				showUpdateDialog('Installing the verified update.\n\nThe update helper will ask whether to start the new version when installation finishes.', 'progress');
			case 'complete':
				updateInstallStatusPath = null;
				showUpdateDialog('The update has been installed.\n\nACCEPT or BACK: close', 'message');
			default:
				if (StringTools.startsWith(status, 'error:')) {
					updateInstallStatusPath = null;
					showUpdateDialog(status.substr('error:'.length) + '\n\nACCEPT or BACK: close', 'message');
				}
		}
	}

	function handleUpdateDialog():Bool {
		if (!updateDialogVisible) return false;
		if (controls.ACCEPT) {
			if (updateDialogMode == 'prompt' && updateOffer != null) {
				var started = UpdateChecker.startInstall(updateOffer);
				if (started.error != null) {
					showUpdateDialog('Could not start the update.\n' + started.error + '\n\nACCEPT or BACK: close', 'message');
				} else {
					updateInstallStatusPath = started.statusPath;
					lastInstallStatus = null;
					updateProgressDismissed = false;
					showUpdateDialog('The Windows update helper has started. It downloads and verifies the full package, then installs it after you close the game.\n\nYou can keep playing. BACK hides this message.', 'progress');
				}
			} else if (updateDialogMode == 'checking') {
				updateCheckRequestId = -1;
				hideUpdateDialog();
			} else if (updateDialogMode != 'progress') {
				if (updateDialogMode == 'message' && lastInstallStatus != null
					&& (lastInstallStatus == 'complete' || StringTools.startsWith(lastInstallStatus, 'error:')))
					UpdateChecker.clearInstallProgress();
				hideUpdateDialog();
			}
			return true;
		}
		if (controls.BACK) {
			if (updateDialogMode == 'prompt') updateOffer = null;
			if (updateDialogMode == 'checking') updateCheckRequestId = -1;
			if ((updateDialogMode == 'progress' || updateDialogMode == 'ready') && updateInstallStatusPath != null)
				updateProgressDismissed = true;
			if (updateDialogMode == 'message' && lastInstallStatus != null
				&& (lastInstallStatus == 'complete' || StringTools.startsWith(lastInstallStatus, 'error:')))
				UpdateChecker.clearInstallProgress();
			hideUpdateDialog();
			return true;
		}
		return true;
	}

	function showUpdateDialog(text:String, mode:String):Void {
		updateDialogMode = mode;
		updateDialogVisible = true;
		updateDialogBackground.visible = true;
		updateDialogText.text = text;
		updateDialogText.visible = true;
	}

	function hideUpdateDialog():Void {
		updateDialogVisible = false;
		updateDialogBackground.visible = false;
		updateDialogText.visible = false;
	}
	#end

	function changeAmount(increase:Bool = false) {
		if (!inOptionCategory || optionsSelected < 0 || optionsSelected >= optionList.length)
			return;
		if (!numberDisplays[optionsSelected].visible)
			return;
		var field = optionList[optionsSelected].intName;
		var step:Null<Float> = (field == "offset" || field == "fpsCap") && FlxG.keys.pressed.SHIFT ? 20 : null;
		numberDisplays[optionsSelected].changeAmount(increase, step);
		if (field == "offset")
			numberDisplays[optionsSelected].value = OptionsHandler.sanitizeOffset(numberDisplays[optionsSelected].value);
		optionList[optionsSelected].amount = numberDisplays[optionsSelected].value;
		if (numberDisplays[optionsSelected].value == numberDisplays[optionsSelected].useDefaultValue && optionList[optionsSelected].value) {
			toggleSelection();
		}
		else if (numberDisplays[optionsSelected].value != numberDisplays[optionsSelected].useDefaultValue && !optionList[optionsSelected].value) {
			toggleSelection();
		}
		if (optionList[optionsSelected].intName == "judge") {
			switch (cast (Std.int(optionList[optionsSelected].amount) : Judge.Jury)) {
				case Judge.Jury.Classic:
					numberDisplays[optionsSelected].text = "Classic";
				case Judge.Jury.Hard:
					numberDisplays[optionsSelected].text = "Hard";
				default:
					numberDisplays[optionsSelected].text = optionList[optionsSelected].amount + 1 + "";
			}
		}
		if (optionList[optionsSelected].intName == "preferJudgement") {
			var judgementList = CoolUtil.coolTextFile('assets/data/judgements.txt');
			numberDisplays[optionsSelected].text = judgementList[Std.int(optionList[optionsSelected].amount)];
		}
		if (optionList[optionsSelected].intName == "accuracyMode") {
			switch (cast (Std.int(optionList[optionsSelected].amount) : OptionsHandler.AccuracyMode)) {
				case Simple: 
					numberDisplays[optionsSelected].text = "Simple";
				case Binary:
					numberDisplays[optionsSelected].text = "Binary";
				case Complex:
					numberDisplays[optionsSelected].text = "Complex";
				case None:
					numberDisplays[optionsSelected].text = "Disable";
			}
		}
	}
	function changeSelection(change:Int = 0) {
		if (!inOptionsMenu) {
			if (change != 0) playMenuSound('scroll');

			curSelected += change;

			if (curSelected < 0)
				curSelected = saves.members.length - 1;
			if (curSelected >= saves.members.length)
				curSelected = 0;

			var bullShit:Int = 0;

			for (item in saves.members) {
				item.targetY = bullShit - curSelected;
				bullShit++;

				item.color = 0xFF828282;
				// item.setGraphicSize(Std.int(item.width * 0.8));

				if (item.targetY == 0) {
					item.color = 0xFFFFFFFF;
					// item.setGraphicSize(Std.int(item.width));
				}
			}
		} else if (!inOptionCategory) {
			if (change != 0) playMenuSound('scroll');
			var names = OptionsCategories.names();
			categorySelected = (categorySelected + change) % names.length;
			if (categorySelected < 0) categorySelected += names.length;
			refreshCategoryRows();
		} else {
			if (change != 0) playMenuSound('scroll');

			optionsSelected = OptionsCategories.move(categoryOptions, optionsSelected, change);
			if (optionsSelected < 0) return;


			refreshOptionRows();
			description.text = optionList[optionsSelected].desc;
		}

	}
	function openOptionCategory():Void {
		categoryOptions = OptionsCategories.indices(cast optionList, OptionsCategories.names()[categorySelected]);
		if (categoryOptions.length == 0) return;
		inOptionCategory = true;
		playMenuSound('confirm');
		optionsSelected = categoryOptions[0];
		amountRepeat.reset();
		refreshCategoryRows();
		changeSelection();
	}

	function refreshOptionRows():Void {
		for (index in 0...options.members.length) {
			var item = options.members[index];
			var position = categoryOptions.indexOf(index);
			var shown = inOptionCategory && position >= 0;
			item.visible = shown;
			item.active = shown;
			item.targetY = position - categoryOptions.indexOf(optionsSelected);
			item.alpha = index == optionsSelected ? 1 : 0.6;
			// FlxSpriteGroup visibility propagates to every child. Restore the
			// numeric/toggle decorations from saved model values after each filter.
			checkmarks.members[index].visible = shown && optionList[index].value;
			numberDisplays[index].visible = shown && optionList[index].amount != null;
		}
	}

	function refreshCategoryRows():Void {
		if (categoryRows == null) return;
		categoryRows.visible = !inOptionCategory;
		categoryRows.active = !inOptionCategory;
		options.visible = inOptionCategory;
		refreshOptionRows();
		categoryHeading.text = inOptionCategory
			? 'Options / ' + OptionsCategories.names()[categorySelected] : 'Options';
		categoryHelp.text = inOptionCategory
			? 'Up/Down: choose   Left/Right: change   Enter: toggle   Back: sections'
			: 'Up/Down: choose section   Enter: open   Back: return'
				+ (OptionsHandler.options.useSaveDataMenu ? '   Left/Right: saves' : '');
		for (index in 0...categoryRows.members.length) {
			categoryRows.members[index].targetY = index - categorySelected;
			categoryRows.members[index].alpha = index == categorySelected ? 1 : 0.6;
		}
		if (!inOptionCategory) {
			var section = OptionsCategories.names()[categorySelected];
			var count = OptionsCategories.indices(cast optionList, section).length;
			description.text = section + '\n\n' + count + ' settings\n\nPress Enter to open.';
		}
	}
	function playMenuSound(action:String):Void {
		var key = switch (action) {
			case 'confirm': 'customMenuConfirm';
			case 'cancel': 'customMenuCancel';
			default: 'customMenuScroll';
		};
		var pack:Dynamic = Reflect.field(sfxJson, key);
		var sound = action == 'confirm' ? 'confirmMenu' : action == 'cancel' ? 'cancelMenu' : 'scrollMenu';
		var path = 'assets/sounds/' + sound + TitleState.soundExt;
		if (Std.isOfType(pack, String) && pack != '') {
			var customPath = 'assets/sounds/custom_menu_sounds/' + pack + '/' + sound + TitleState.soundExt;
			if (FNFAssets.exists(customPath)) path = customPath;
		}
		FlxG.sound.play(path, 0.4);
	}
	function swapMenus() {
		if (inOptionsMenu) {
			FlxTween.tween(optionMenu, {x: FlxG.width}, 0.1, {type: FlxTweenType.ONESHOT, ease: FlxEase.backInOut});
			FlxTween.tween(saves, {x: 0}, 0.1, {type: FlxTweenType.ONESHOT, ease: FlxEase.backInOut});
			inOptionsMenu = false;
		} else {
			FlxTween.tween(optionMenu, {x: 0}, 0.1, {type: FlxTweenType.ONESHOT, ease: FlxEase.backInOut});
			FlxTween.tween(saves, {x: -FlxG.width }, 0.1, {type: FlxTweenType.ONESHOT, ease: FlxEase.backInOut});
			inOptionsMenu = true;
			refreshCategoryRows();
		}
	}
	function saveOptions() {
		var noneditableoptions:Dynamic = CodenameOptionsMenuModel.copyOptions(OptionsHandler.options);
		Reflect.setField(noneditableoptions, "preferredSave", preferredSave);
		Reflect.setField(noneditableoptions, "importType", ImportSettings.getSelectedType());
		Reflect.setField(noneditableoptions, "importPath", ImportSettings.getSourcePath());
		for (field in Reflect.fields(mappedOptions)) {
			Reflect.setField(noneditableoptions, field, Reflect.field(mappedOptions, field).value);
			if (Reflect.field(mappedOptions, field).amount != null) {
				Reflect.setField(noneditableoptions, field, Reflect.field(mappedOptions, field).amount);
			}
		}
		OptionsHandler.options = noneditableoptions;
		Main.fpsCounter.visible = OptionsHandler.options.showFPS;
		Main.memoryCounter.visible = OptionsHandler.options.showMemory;
	}
	function toggleSelection() { 
		switch (optionList[optionsSelected].name) {
			case "New Character...":
				// our current save saves this
				// we are gonna have to do some shenanagins to save our preffered save

				saveOptions();
				LoadingState.loadAndSwitchState(new NewCharacterState());
			case "New Stage...":
				// our current save saves this
				// we are gonna have to do some shenanagins to save our preffered save

				saveOptions();

				LoadingState.loadAndSwitchState(new NewStageState());
			case "New Song...":
				saveOptions();

				LoadingState.loadAndSwitchState(new NewSongState());
			case "New Week...":
				saveOptions();
				NewWeekState.sorted = false;
				LoadingState.loadAndSwitchState(new NewWeekState());
			case "Sort...":
				saveOptions();

				LoadingState.loadAndSwitchState(new SelectSortState());
			case "Sound Test...":
				saveOptions();
				FreeplayState.soundTest = true;
				CategoryState.choosingFor = "freeplay";
				LoadingState.loadAndSwitchState(new CategoryState());
			case "Credits":
				saveOptions();
				LoadingState.loadAndSwitchState(new CreditsState());
			case "Import Settings...":
				saveOptions();
				LoadingState.loadAndSwitchState(new ImportSettingsState());
			default:
				if (OptionsHandler.options.allowEditOptions) {
					checkmarks.members[optionsSelected].visible = !checkmarks.members[optionsSelected].visible;
					optionList[optionsSelected].value = checkmarks.members[optionsSelected].visible;
				}
		}
	}
}
