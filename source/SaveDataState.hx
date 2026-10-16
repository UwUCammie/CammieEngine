package;

import OptionsHandler.FullOptions;
import MenuStyle.MenuHint;
import haxe.ds.Option;
import OptionsHandler.TOptions;
import Controls.Control;
import flash.text.TextField;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup;
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
	var saves:FlxTypedGroup<SaveFile>;
	var optionCards:Array<MenuCard> = [];
	var sectionCards:Array<MenuCard> = [];
	/** World x of the options screen; the save slots are one screen to its left. */
	var optionsX:Float = 0;
	var footer:MenuFooter;
	var hintKey:String = '';
	// this will need to be initialized in title state!!!
	public static var optionList:Array<TOption>;
	var optionMask:Mask<FullOptions>;
	var curSelected:Int = 0;
	var amountRepeat:OptionsValueRepeat = new OptionsValueRepeat();
	var mappedOptions:Dynamic = {};
	var inOptionsMenu:Bool = false;
	var optionsSelected:Int = 0;
	var categoryHeading:FlxText;
	var listHeading:FlxText;
	var saveHeading:FlxText;
	var saveTitle:FlxText;
	var saveMeta:FlxText;
	var savePanel:MenuWidgets.MenuPanelParts;
	/** The settings list and the section tabs beside it, in screen pixels. */
	static inline var SIDEBAR_X:Int = 32;
	static inline var SIDEBAR_WIDTH:Int = 340;
	static inline var SIDEBAR_TOP:Int = 100;
	static inline var TAB_HEIGHT:Int = 54;
	static inline var TAB_GAP:Int = 6;
	static inline var LIST_X:Int = 404;
	static inline var LIST_WIDTH:Int = 680;
	static inline var LIST_TOP:Int = 100;
	static inline var LIST_BOTTOM:Int = 640;
	static inline var LIST_GAP:Int = 4;
	static inline var SAVE_X:Int = 32;
	static inline var SAVE_WIDTH:Int = 560;
	static inline var SAVE_GAP:Int = 4;
	static var tabLook:MenuStyle.MenuCardLook = {idle: TAB_HEIGHT, selected: TAB_HEIGHT, titleSize: 20, selectedTitleSize: 20,
		titleTop: 15, titleLift: 0, valueSize: 16, reserve: 40};
	static var rowLook:MenuStyle.MenuCardLook = {idle: 44, selected: 92, titleSize: 20, selectedTitleSize: 24,
		titleTop: 11, titleLift: 3, captionTop: 46, captionSize: 14, captionLines: 2};
	var categorySelected:Int = 0;
	var inOptionCategory:Bool = false;
	var categoryOptions:Array<Int> = [];
	var numberDisplays:Array<NumberDisplay> = [];
	var sfxJson:Dynamic = CoolUtil.parseJson(FNFAssets.getText("assets/sounds/custom_menu_sounds/custom_menu_sounds.json"));
	var musicJson:Dynamic = CoolUtil.parseJson(FNFAssets.getText("assets/music/custom_menu_music/custom_menu_music.json"));
	var preferredSave:Int = 0;
	var importWorkBusy:Bool = false;
	var forbiddenIndexes:Array<Int> = [];
	#if (sys && windows)
	var updateDialogGroup:FlxGroup;
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
		RuntimeSongExitProbe.mark("options-audio-begin");
		FlxG.sound.music.stop();
		var goodSound = FNFAssets.getMusic('assets/music/custom_menu_music/'
			+ musicJson.Options
			+ '/options'
			+ TitleState.soundExt);
		optionMask = CoolUtil.parseJson(FNFAssets.getJson('assets/data/optionsMask'));
		FlxG.sound.playMusic(goodSound);
		RuntimeSongExitProbe.mark("options-audio-end");
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
							{name: "Show Duplicate Base Game Charts", value: false, intName: "showDuplicateBaseCharts", desc: "List imported copies of base game songs in Freeplay. Copies share a base song's music and tempo."},
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
		// The save slots sit on the first screen and the options one screen to
		// its right; the camera slides between them.
		optionsX = FlxG.width;
		var backdrop = MenuWidgets.backdrop();
		backdrop.scrollFactor.set();
		add(backdrop);
		var shade = MenuWidgets.shade();
		shade.scrollFactor.set();
		add(shade);
		saves = new FlxTypedGroup<SaveFile>();
		for (i in 0...10) {
			saves.add(new SaveFile(i, SAVE_WIDTH));
		}
		add(saves);
		RuntimeSongExitProbe.mark("options-saves-ready");
		for (j in 0...optionList.length) {
			if (Reflect.field(optionMask, optionList[j].intName) != null && !Reflect.field(optionMask, optionList[j].intName)) {
				// skip display if it is masked out
				continue;
			}
			forbiddenIndexes.push(j);
			var numDisplay = new NumberDisplay(0, 0, optionList[j].defAmount, optionList[j].precision != null ? optionList[j].precision : 1, optionList[j].min != null ? optionList[j].min : 0, optionList[j].max);
			numDisplay.visible = optionList[j].amount != null;
			numberDisplays.push(numDisplay);
			numDisplay.value = optionList[j].amount;
			numDisplay.size = 40;
			var card = new MenuCard(optionList[j].name, LIST_WIDTH, 24, rowLook);
			card.exists = false;
			card.setCaption(FreeplayBrowserLayout.label(optionList[j].desc, Std.int((LIST_WIDTH - 48) / 8.4) * 2 - 4));
			optionCards.push(card);
			add(card);
		}
		for (j in 0...optionList.length)
			refreshAmountText(j);
		for (j in 0...optionCards.length)
			refreshOptionValue(j);
		RuntimeSongExitProbe.mark("options-rows-ready");
		var sectionNames = OptionsCategories.names();
		for (index in 0...sectionNames.length) {
			var count = OptionsCategories.indices(cast optionList, sectionNames[index]).length;
			var row = new MenuCard(sectionNames[index], SIDEBAR_WIDTH, 22, tabLook);
			row.exists = false;
			row.setValue(Std.string(count), MenuStyle.MUTED, 36);
			sectionCards.push(row);
			add(row);
		}
		// Labels over the two columns, and the one line that says where you are.
		var tabsLabel = MenuWidgets.text(SIDEBAR_X + optionsX, SIDEBAR_TOP - 22, SIDEBAR_WIDTH, 'SECTIONS', MenuStyle.SECTION_SIZE, MenuStyle.TEAL);
		add(tabsLabel);
		listHeading = MenuWidgets.text(LIST_X + optionsX, LIST_TOP - 22, LIST_WIDTH, '', MenuStyle.SECTION_SIZE, MenuStyle.PINK);
		listHeading.wordWrap = false;
		add(listHeading);
		// The save slots' own panels, sized to their text.
		var panelX = SAVE_X + SAVE_WIDTH + 40;
		savePanel = MenuWidgets.sizedPanel(this, MenuStyle.PINK, 'SAVE SLOT');
		MenuWidgets.sizePanel(savePanel, panelX, SIDEBAR_TOP, 380, 128);
		saveTitle = MenuWidgets.text(panelX + 16, SIDEBAR_TOP + 28, 350, '', 24, MenuStyle.WHITE);
		saveTitle.wordWrap = false;
		add(saveTitle);
		saveMeta = MenuWidgets.text(panelX + 16, SIDEBAR_TOP + 64, 350, '', 16, MenuStyle.MUTED);
		add(saveMeta);
		var howParts = MenuWidgets.sizedPanel(this, MenuStyle.TEAL, 'HOW SAVES WORK');
		MenuWidgets.sizePanel(howParts, panelX, SIDEBAR_TOP + 140, 380, 112);
		add(MenuWidgets.text(panelX + 16, SIDEBAR_TOP + 140 + 30, 350,
			'Each slot keeps its own scores and progress. Load switches the game to that slot. Delete erases the slot after you confirm.',
			16, MenuStyle.TEXT));
		categoryHeading = MenuWidgets.text(150 + optionsX, 14, FlxG.width - 400, '', MenuStyle.BODY_SIZE, MenuStyle.MUTED);
		categoryHeading.wordWrap = false;
		add(categoryHeading);
		saveHeading = MenuWidgets.text(150, 14, FlxG.width - 400, 'Save slots  /  10 slots', MenuStyle.BODY_SIZE, MenuStyle.MUTED);
		saveHeading.wordWrap = false;
		add(saveHeading);
		markCurrentSave();
		footer = new MenuFooter('OPTIONS', hintsFor());
		for (item in footer.members)
			item.scrollFactor.set();
		add(footer);
		refreshCategoryRows(true);
		#if (sys && windows)
		var dialogWidth = 760;
		var dialogHeight = 500;
		var dialogX = Std.int((FlxG.width - dialogWidth) / 2);
		var dialogY = Std.int((FlxG.height - dialogHeight) / 2);
		updateDialogGroup = new FlxGroup();
		MenuWidgets.panel(updateDialogGroup, dialogX, dialogY, dialogWidth, dialogHeight);
		updateDialogBackground = cast updateDialogGroup.members[0];
		updateDialogText = MenuWidgets.text(dialogX + 32, dialogY + 40, dialogWidth - 64, '', 20, MenuStyle.TEXT);
		updateDialogText.fieldHeight = dialogHeight - 80;
		updateDialogGroup.add(MenuWidgets.text(dialogX + 32, dialogY + 16, dialogWidth - 64, 'WINDOWS UPDATE', MenuStyle.SECTION_SIZE, MenuStyle.PINK));
		updateDialogGroup.add(updateDialogText);
		for (item in updateDialogGroup.members)
			if (item != null) (cast item:FlxSprite).scrollFactor.set();
		updateDialogGroup.visible = false;
		add(updateDialogGroup);
		updateInstallStatusPath = UpdateChecker.activeInstallStatusPath();
		add(new UpdateProgressBar());
		#end
		changeSelection();
		refreshHints();
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
		refreshHints();
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
				refreshSaveRows();
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
				if (saves.members[curSelected].beingSelected) {
					saves.members[curSelected].changeSelection();
					refreshSaveRows();
				}
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
			&& optionList[optionsSelected].amount != null;
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
				footer.setNote('An import is still running. You can browse available songs or return to the importer.', MenuStyle.AMBER);
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
						markCurrentSave();
					} else {
						saves.members[curSelected].askToConfirm(true);
					}
					refreshSaveRows();

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
					markCurrentSave();
					refreshSaveRows();
				}
			} else if (!inOptionsMenu) {
				FlxG.sound.play('assets/sounds/custom_menu_sounds/'
					+ sfxJson.customMenuScroll+'/scrollMenu' + TitleState.soundExt);
				saves.members[curSelected].beSelected(true);
				refreshSaveRows();
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
						if (OptionsHandler.options.allowEditOptions) {
							optionList[optionsSelected].value = !optionList[optionsSelected].value;
							refreshOptionRows();
							refreshDetails();
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
		updateDialogGroup.visible = true;
		updateDialogText.text = text;
	}

	function hideUpdateDialog():Void {
		updateDialogVisible = false;
		updateDialogGroup.visible = false;
	}
	#end

	function changeAmount(increase:Bool = false) {
		if (!inOptionCategory || optionsSelected < 0 || optionsSelected >= optionList.length)
			return;
		if (optionList[optionsSelected].amount == null)
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
		refreshAmountText(optionsSelected);
		refreshOptionRows();
		refreshDetails();
	}
	function changeSelection(change:Int = 0) {
		if (!inOptionsMenu) {
			if (change != 0) playMenuSound('scroll');

			curSelected += change;

			if (curSelected < 0)
				curSelected = saves.members.length - 1;
			if (curSelected >= saves.members.length)
				curSelected = 0;

			refreshSaveRows();
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
			refreshDetails();
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

	/** Stack a list of cards from the top of its column: the open card is taller
	 * and a list longer than the column scrolls to keep it in view. With nothing
	 * selected the cards show as a quiet preview. */
	function layoutStack(cards:Array<MenuCard>, positions:Array<Int>, selected:Int, baseX:Float, top:Float, bottom:Float, gap:Int,
		focused:Bool, snap:Bool):Void {
		var selectedPosition = Std.int(Math.max(0, positions.indexOf(selected)));
		var idle = cards.length == 0 ? MenuStyle.ROW_HEIGHT : cards[0].idleHeight;
		var open = cards.length == 0 ? MenuStyle.SELECTED_HEIGHT : cards[0].selectedHeight;
		var scroll = focused ? MenuStyle.stackScroll(selectedPosition, positions.length, idle, open, gap, bottom - top) : 0;
		for (index in 0...cards.length) {
			var card = cards[index];
			var position = positions.indexOf(index);
			var isSelected = focused && position >= 0 && index == selected;
			card.present(isSelected, false);
			card.opacity = focused ? 1 : 0.6;
			if (position < 0) {
				card.exists = false;
				continue;
			}
			var cardTop = MenuStyle.stackTop(position, focused ? selectedPosition : positions.length, top, idle, open, gap) - scroll;
			var fits = MenuStyle.fitsRegion(cardTop, isSelected ? open : idle, top, bottom);
			var appearing = fits && !card.exists;
			card.exists = fits;
			if (fits) card.moveTo(baseX, cardTop, snap || appearing);
		}
	}

	function refreshSaveRows(snap:Bool = false):Void {
		var all = [for (index in 0...saves.members.length) index];
		layoutStack(cast saves.members, all, curSelected, SAVE_X, SIDEBAR_TOP, LIST_BOTTOM, SAVE_GAP, true, snap);
		var slot = saves.members[curSelected];
		saveTitle.text = 'Save ' + (curSelected + 1);
		saveMeta.text = slot.characterName() + (slot.isCurrent ? '\nThis is the save the game is using now.' : '\nPress ACCEPT to open this save.');
	}

	function markCurrentSave():Void {
		for (slot in saves.members)
			slot.setActive(FlxG.save != null && FlxG.save.name == 'save' + slot.slot);
	}

	/** Display text of a numeric row: names where the number is a choice. */
	function refreshAmountText(index:Int):Void {
		var option = optionList[index];
		if (option.amount == null) return;
		switch (option.intName) {
			case "judge":
				switch (cast (Std.int(option.amount) : Judge.Jury)) {
					case Judge.Jury.Classic:
						numberDisplays[index].text = "Classic";
					case Judge.Jury.Hard:
						numberDisplays[index].text = "Hard";
					default:
						numberDisplays[index].text = option.amount + 1 + "";
				}
			case "preferJudgement":
				var judgementList = CoolUtil.coolTextFile('assets/data/judgements.txt');
				var at = Std.int(option.amount);
				if (at >= 0 && at < judgementList.length)
					numberDisplays[index].text = judgementList[at];
			case "accuracyMode":
				switch (cast (Std.int(option.amount) : OptionsHandler.AccuracyMode)) {
					case Simple:
						numberDisplays[index].text = "Simple";
					case Binary:
						numberDisplays[index].text = "Binary";
					case Complex:
						numberDisplays[index].text = "Complex";
					case None:
						numberDisplays[index].text = "Disable";
				}
			default:
		}
	}

	/** A row opens another screen or starts a task instead of holding a value. */
	function isActionRow(index:Int):Bool {
		return switch (optionList[index].intName) {
			case 'controls' | 'calibrate' | 'credits' | 'soundtest' | 'module' | 'newmodule' | 'checkUpdates' | 'sort': true;
			default: false;
		};
	}

	/** Draw one row's value from the model: a switch, a number or an action. */
	function refreshOptionValue(index:Int):Void {
		var option = optionList[index];
		var card = optionCards[index];
		if (option.amount != null)
			card.setValue(numberDisplays[index].text, option.value ? MenuStyle.TEAL : MenuStyle.TEXT, 180);
		else if (isActionRow(index))
			card.setValue('OPEN', MenuStyle.GOLD, 80);
		else
			card.setSwitch(option.value);
	}

	function refreshOptionRows(snap:Bool = false):Void {
		for (index in 0...optionCards.length)
			refreshOptionValue(index);
		var shown = inOptionCategory ? categoryOptions : OptionsCategories.indices(cast optionList, OptionsCategories.names()[categorySelected]);
		layoutStack(optionCards, shown, optionsSelected, optionsX + LIST_X, LIST_TOP, LIST_BOTTOM, LIST_GAP, inOptionCategory, snap);
	}

	function refreshCategoryRows(snap:Bool = false):Void {
		if (sectionCards.length == 0) return;
		refreshOptionRows(snap);
		for (index in 0...sectionCards.length) {
			var tab = sectionCards[index];
			tab.exists = true;
			tab.present(index == categorySelected, false);
			tab.moveTo(optionsX + SIDEBAR_X, SIDEBAR_TOP + index * (TAB_HEIGHT + TAB_GAP), snap);
		}
		refreshSaveRows(snap);
		refreshDetails();
	}

	/** The line that says where you are, and the label over the settings. */
	function refreshDetails():Void {
		var names = OptionsCategories.names();
		var section = names[categorySelected];
		var members = OptionsCategories.indices(cast optionList, section);
		listHeading.text = section.toUpperCase() + '  /  ' + members.length + (members.length == 1 ? ' SETTING' : ' SETTINGS');
		if (!inOptionCategory) {
			categoryHeading.text = 'Options  /  ' + names.length + ' sections';
			return;
		}
		var position = Std.int(Math.max(0, categoryOptions.indexOf(optionsSelected)));
		categoryHeading.text = 'Options  /  ' + section + '  /  ' + (position + 1) + ' of ' + categoryOptions.length;
	}

	/** Key hints for what the screen is doing now. */
	function hintsFor():Array<MenuHint> {
		var slot = saves == null || saves.members.length == 0 ? null : saves.members[curSelected];
		return MenuHints.options(inOptionsMenu, inOptionCategory, slot != null && slot.beingSelected,
			slot != null && slot.askingToConfirm, OptionsHandler.options.allowEditOptions, OptionsHandler.options.useSaveDataMenu);
	}

	/** Re-lay the footer when the screen's step changes, not every frame. */
	function refreshHints():Void {
		var slot = saves == null || saves.members.length == 0 ? null : saves.members[curSelected];
		var key = (inOptionsMenu ? 'o' : 's') + (inOptionCategory ? 'c' : 'r')
			+ (slot != null && slot.beingSelected ? 'b' : '-') + (slot != null && slot.askingToConfirm ? 'a' : '-');
		if (key == hintKey) return;
		hintKey = key;
		footer.setHints(hintsFor());
		for (item in footer.members)
			item.scrollFactor.set();
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
			slideTo(0);
			inOptionsMenu = false;
			refreshSaveRows();
		} else {
			slideTo(optionsX);
			inOptionsMenu = true;
			refreshCategoryRows();
		}
		refreshHints();
	}
	/** Slide the camera between the save slots and the options. */
	function slideTo(x:Float):Void {
		FlxTween.num(FlxG.camera.scroll.x, x, 0.1, {type: FlxTweenType.ONESHOT, ease: FlxEase.backInOut}, function(value:Float):Void {
			FlxG.camera.scroll.x = value;
		});
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
			default:
				if (OptionsHandler.options.allowEditOptions) {
					optionList[optionsSelected].value = !optionList[optionsSelected].value;
				}
		}
	}
}
