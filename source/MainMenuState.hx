package;

import HxcMenuSpec.HxcMenuItemSpec;
import HxcMenuSpec.HxcMenuSpecData;

import flixel.FlxG;
import flixel.FlxCamera;
import flixel.FlxObject;
import flixel.FlxSprite;
import flixel.addons.transition.FlxTransitionableState;
import flixel.effects.FlxFlicker;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.text.FlxText;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween;
import flixel.util.FlxColor;
import lime.utils.Assets;
import lime.app.Application;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxEase;
import flixel.FlxObject;
#if sys
import sys.io.File;
import haxe.io.Path;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import flash.media.Sound;
import sys.FileSystem;
import Song.SwagSong;
#end
using StringTools;
	
class MainMenuState extends MusicBeatState {
	static var curSelected:Int = 0;
	var customMenuConfirm: Array<Array<String>>;
	var customMenuScroll: Array<Array<String>>;
	var parsedcustomMenuConfirmJson:Array<Array<String>>;
	var menuItems:FlxTypedGroup<MenuCard>;
	var saveLine:FlxText;
	var saveName:String = '';
	var stagePanel:MenuWidgets.MenuPanelParts;
	var stageBig:FlxText;
	var stageSub:FlxText;
	var stageLabels:Array<FlxText> = [];
	var stageValues:Array<FlxText> = [];
	var weekCount:Int = -1;
	var stageHeight:Int = 0;
	var stageTarget:Float = 0;
	var stageShown:Float = -1;
	var songCount:Int = -1;
	var importStatusLabel:String = '';
	var hxcCostumeState:Dynamic;
	#if !switch
	// "import" opens the song importer (ImportSettingsState).
	var optionShit:Array<String> = ['story mode', 'freeplay'#if sys, 'online'#end, 'donate', 'options'#if sys, 'import'#end];
	#else
	var optionShit:Array<String> = ['story mode', 'freeplay'];
	#end
	var menuSoundJson:Dynamic;
	var scrollSound:String;
	var magenta:FlxSprite;
	// HXC main-menu overlays are data-driven and state-owned.  Imported scripts
	// never receive these objects or a camera handle; they can only request the
	// narrow HxcCompatRuntime mount/clear boundary.
	var hxcOverlaySpec:Null<HxcMenuSpecData>;
	var hxcOverlayRoot:String = '';
	var hxcOverlayCamera:FlxCamera;
	var hxcOverlayObjects:Array<Dynamic> = [];
	var hxcOverlayIndex:Int = 0;
	var hxcOverlayBusy:Bool = false;
	var hxcOverlayMenuVisible:Bool = true;
	var hxcOverlayMagentaVisible:Bool = false;
	var importedModsHint:FlxText;
	public static var version:String = 'v' + EngineBranding.version();
	override function create() {
		if (!Std.isOfType(this, HxcImportedMenuState)) ImportedMenuEntry.release();
		RuntimeStartupProbe.mark('main_menu_enter');
		#if windows
		// Updating Discord Rich Presence
		var customPrecence = TitleState.discordStuff.mainmenu;
		Discord.DiscordClient.changePresence(customPrecence, null);
		#end
		menuSoundJson = CoolUtil.parseJson(FNFAssets.getText("assets/sounds/custom_menu_sounds/custom_menu_sounds.json"));
		scrollSound = menuSoundJson.customMenuScroll;
		transIn = FlxTransitionableState.defaultTransIn;
		transOut = FlxTransitionableState.defaultTransOut;
		if (!OptionsHandler.options.allowStoryMode) 
			optionShit.remove("story mode");
		if (!OptionsHandler.options.allowFreeplay) 
			optionShit.remove("freeplay");
		if (!OptionsHandler.options.allowDonate) 
			optionShit.remove("donate");
		if (!OptionsHandler.options.useSaveDataMenu && !OptionsHandler.options.allowEditOptions) 
			optionShit.remove("options");
		RuntimeSongExitProbe.mark("menu-audio-begin");
		if (!FlxG.sound.music.playing) {
			FlxG.sound.playMusic(FNFAssets.getMusic('assets/music/custom_menu_music/'
				+ CoolUtil.parseJson(FNFAssets.getText("assets/music/custom_menu_music/custom_menu_music.json")).Menu+'/freakyMenu' + TitleState.soundExt));
		}
		
		RuntimeSongExitProbe.mark("menu-audio-end");
		persistentUpdate = persistentDraw = true;
		// The shared Freeplay backdrop: the menu background under a dark dim.
		var bg:FlxSprite = MenuWidgets.backdrop();
		bg.scrollFactor.set();
		add(bg);
		var shade:FlxSprite = MenuWidgets.shade();
		shade.scrollFactor.set();
		add(shade);

		// A pink wash that blinks over the menu when a row is chosen.
		magenta = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, MenuStyle.PINK);
		magenta.alpha = 0.16;
		magenta.scrollFactor.set();
		magenta.visible = false;
		add(magenta);

		// The front page: the engine's name, then the entries as a stack of big
		// cards with the highlighted one open, and what it leads to beside them.
		version = 'v' + EngineBranding.version();
		var appName = Application.current.meta.get('name');
		var brand:FlxText = MenuWidgets.text(MainMenuLayout.LEFT, 76, 560, appName, 30, MenuStyle.CREAM);
		brand.wordWrap = false;
		add(brand);
		saveLine = MenuWidgets.text(MainMenuLayout.LEFT, 112, 560, version, MenuStyle.SMALL_SIZE, MenuStyle.MUTED);
		saveLine.wordWrap = false;
		add(saveLine);
		importedModsHint = MenuWidgets.text(FlxG.width - 304, 20, 280, 'Imported Mods  [I]', 16, MenuStyle.GOLD, flixel.text.FlxText.FlxTextAlign.RIGHT);
		importedModsHint.scrollFactor.set();
		add(importedModsHint);

		menuItems = new FlxTypedGroup<MenuCard>();
		add(menuItems);
		for (i in 0...optionShit.length) {
			var card = new MenuCard(rowLabel(optionShit[i]), MainMenuLayout.WIDTH, 28, MainMenuLayout.LOOK);
			card.ID = i;
			card.setCaption(rowCaption(optionShit[i]));
			menuItems.add(card);
		}
		layoutMenuItems(true);

		stagePanel = MenuWidgets.sizedPanel(this, MenuStyle.PINK, '');
		stageBig = MenuWidgets.text(0, 0, MainMenuLayout.STAGE_WIDTH - 40, '', 44, MenuStyle.WHITE);
		stageBig.wordWrap = false;
		add(stageBig);
		stageSub = MenuWidgets.text(0, 0, MainMenuLayout.STAGE_WIDTH - 40, '', 16, MenuStyle.MUTED);
		stageSub.wordWrap = false;
		add(stageSub);
		for (slot in 0...MainMenuLayout.FACT_ROWS) {
			var label = MenuWidgets.text(0, 0, MainMenuLayout.STAGE_WIDTH - 40, '', 16, MenuStyle.MUTED);
			label.wordWrap = false;
			var value = MenuWidgets.text(0, 0, MainMenuLayout.STAGE_WIDTH - 40, '', 16, MenuStyle.CREAM, flixel.text.FlxText.FlxTextAlign.RIGHT);
			value.wordWrap = false;
			add(label);
			add(value);
			stageLabels.push(label);
			stageValues.push(value);
		}
		var menuFooter = new MenuFooter('MENU', MenuHints.mainMenu());
		add(menuFooter);
		var usingSave:String = switch (FlxG.save.name) {
			case "save0":
				 "bf";
			case "save1":
				"classic";
			case "save2":
				"bf-pixel";
			case "save3":
				"spooky";
			case "save4":
				"dad";
			case "save5":
				"pico";
			case "save6":
				"mom";
			case "save7":
				"gf";
			case "save8":
				"lemon";
			case "save9":
				"senpai";
			default:
				"null";
		}
		saveName = usingSave;
		if (OptionsHandler.options.useSaveDataMenu)
			saveLine.text = version + '   /   Save: ' + usingSave;
		// NG.core.calls.event.logEvent('swag').send();

		changeItem();
		RuntimeStartupProbe.mark('main_menu_graphics_ready');
		#if (sys && windows)
		add(new UpdateProgressBar());
		#end

		#if sys
		add(new ImportRefreshProgressBar(this));
		#end
		super.create();
		RuntimeStartupProbe.mark('main_menu_ready');
	}

	/** What the highlighted entry leads to, as the panel beside the stack shows it. */
	function factFor(row:String):MainMenuFacts.MainMenuFact {
		return switch (row) {
			case 'story mode':
				if (weekCount < 0) {
					var weeks:Dynamic = Reflect.field(CoolUtil.parseJson(FNFAssets.getText('assets/data/storySonglist.json')), 'weeks');
					weekCount = Std.isOfType(weeks, Array) ? (cast weeks:Array<Dynamic>).length : 0;
				}
				MainMenuFacts.story(weekCount);
			case 'freeplay':
				if (songCount < 0) {
					var categories:Dynamic = FreeplayRegistry.exists() ? FreeplayRegistry.getJson() : [];
					songCount = Std.isOfType(categories, Array) ? FreeplayLibraryView.songs(cast categories).length : 0;
				}
				var snapshot = importAvailability == null ? ImportRefreshManager.availabilitySnapshot() : importAvailability;
				MainMenuFacts.freeplay(songCount, snapshot.committedOwnerRoots.length, snapshot.pendingOwnerRoots.length, snapshot.inspectionPending);
			case 'options':
				MainMenuFacts.options(OptionsHandler.options, saveName);
			case 'import':
				var snapshot = importAvailability == null ? ImportRefreshManager.availabilitySnapshot() : importAvailability;
				MainMenuFacts.importer(snapshot.committedOwnerRoots.length, importWorkBusy, importStatusLabel,
					ImportSettings.getSelectedType(), ImportSettings.getSourcePath(), snapshot.inspectionPending);
			case 'online':
				MainMenuFacts.plain('ONLINE', 'Play together', 'Score-race lobbies for 2 to 16 players, signed in with your uwucammie.com account.', MenuStyle.TEAL);
			case 'donate':
				MainMenuFacts.plain('DONATE', 'Support the project', 'Opens the donation page in your browser.', MenuStyle.GOLD);
			case 'costumes':
				MainMenuFacts.plain('COSTUMES', 'Dress up', 'Pick what your character wears.', MenuStyle.TEAL);
			default:
				MainMenuFacts.plain(row.toUpperCase(), rowLabel(row), '', MenuStyle.PINK);
		};
	}

	/** Fill the context panel for the highlighted entry and size it to fit. */
	function refreshFacts():Void {
		if (stagePanel == null || curSelected < 0 || curSelected >= optionShit.length) return;
		var fact = factFor(optionShit[curSelected]);
		stagePanel.accent.color = fact.accent;
		stagePanel.heading.color = fact.accent;
		stagePanel.heading.text = fact.heading;
		stageHeight = MainMenuFacts.panelHeight(fact);
		stageTarget = MainMenuLayout.stageTop(MainMenuLayout.rowTop(curSelected, curSelected, menuItems.length, FlxG.height),
			stageHeight, FlxG.height);
		if (stageShown < 0) stageShown = stageTarget;
		stageBig.text = fact.big;
		stageSub.text = fact.sub;
		for (slot in 0...stageLabels.length) {
			var shown = slot < fact.rows.length;
			stageLabels[slot].visible = stageValues[slot].visible = shown;
			if (!shown) continue;
			stageLabels[slot].text = fact.rows[slot].label;
			stageValues[slot].text = fact.rows[slot].value;
		}
		placeStage(stageShown);
	}

	/** Put the context panel and its text with its top at `top`. */
	function placeStage(top:Float):Void {
		var left = MainMenuLayout.STAGE_X;
		MenuWidgets.sizePanel(stagePanel, left, top, MainMenuLayout.STAGE_WIDTH, stageHeight);
		stageBig.setPosition(left + 20, top + 28);
		stageSub.setPosition(left + 20, top + 28 + 56);
		for (slot in 0...stageLabels.length) {
			var rowY = top + 28 + 56 + 30 + 12 + slot * 30;
			stageLabels[slot].setPosition(left + 20, rowY);
			stageValues[slot].setPosition(left + 20, rowY);
		}
	}

	/** The name a row shows. */
	static function rowLabel(row:String):String {
		return switch (row) {
			case 'story mode': 'Story Mode';
			case 'freeplay': 'Freeplay';
			case 'online': 'Online';
			case 'donate': 'Donate';
			case 'options': 'Options';
			case 'import': 'Import';
			case 'costumes': 'Costumes';
			default: row.charAt(0).toUpperCase() + row.substr(1);
		};
	}

	/** The line a row shows under its name once it is selected. */
	static function rowCaption(row:String):String {
		return switch (row) {
			case 'story mode': 'Play the story weeks one after another';
			case 'freeplay': 'Pick any song and play it';
			case 'online': 'Race other players on the same song';
			case 'donate': 'Open the donation page';
			case 'options': 'Settings, controls and save slots';
			case 'import': 'Add songs and mods from other engines';
			case 'costumes': 'Change what your character wears';
			default: '';
		};
	}

	var selectedSomethin:Bool = false;
	var startupImportCheckMarked:Bool = false;
	var importWorkBusy:Bool = false;
	var importAvailabilityRevision:Int = -1;
	var importAvailability:ImportRefreshAvailabilitySnapshot;

	override function update(elapsed:Float) {
		// The context panel follows the highlighted card, easing the way the cards do.
		if (stagePanel != null && Math.abs(stageShown - stageTarget) > 0.5) {
			stageShown += (stageTarget - stageShown) * Math.min(1, elapsed * 16);
			placeStage(stageShown);
		}
		#if sys
		if (!startupImportCheckMarked) RuntimeStartupProbe.mark('main_menu_import_check_enter');
		var refresh = ImportRefreshManager.browseTick();
		if (!startupImportCheckMarked) { RuntimeStartupProbe.mark('main_menu_import_check_ready'); startupImportCheckMarked = true; }
		if (importWorkBusy != refresh.busy) {
			importWorkBusy = refresh.busy;
			importStatusLabel = refresh.label;
			refreshFacts();
		}
		importWorkBusy = refresh.busy;
		if (importAvailabilityRevision != ImportRefreshManager.availabilityRevision()) {
			var wasChecking = importAvailability == null || importAvailability.inspectionPending;
			importAvailability = ImportRefreshManager.availabilitySnapshot();
			importAvailabilityRevision = importAvailability.revision;
			// The counts on the panel stay hidden while the check runs; show them
			// the moment it ends instead of waiting for the next selection change.
			if (wasChecking != importAvailability.inspectionPending) refreshFacts();
		}
		#end
		if (FlxG.sound.music.volume < 0.8) {
			FlxG.sound.music.volume += 0.5 * FlxG.elapsed;
		}

		// Keep the owner chooser reachable when a HXC overlay owns menu input.
		// This route is checked first so the overlay's normal update still runs
		// unchanged for every other key and only an explicit I press exits it.
		if (tryOpenImportedMods())
			return;

		if (hxcOverlaySpec != null) {
			if (!FreeplaySongAvailability.ownerReadiness(importAvailability, hxcOverlayRoot).ready) {
				super.update(elapsed); return;
			}
			updateHxcMenuOverlay();
			super.update(elapsed);
			return;
		}

		if (!selectedSomethin) {
			if (controls.UP_MENU) {
				FlxG.sound.play('assets/sounds/custom_menu_sounds/'
				+ menuSoundJson.customMenuScroll +'/scrollMenu' + TitleState.soundExt);
				changeItem(-1);
			}

			if (controls.DOWN_MENU) {
				FlxG.sound.play('assets/sounds/custom_menu_sounds/'
				+ menuSoundJson.customMenuScroll +'/scrollMenu' + TitleState.soundExt);
				changeItem(1);
			}

			if (controls.BACK) {
				LoadingState.loadAndSwitchState(new TitleState());
			}

			if (controls.ACCEPT) {
				if (!ImportMenuNavigationPolicy.mainActionAllowed(importWorkBusy, optionShit[curSelected])) {
					FlxG.sound.play('assets/sounds/cancelMenu' + TitleState.soundExt); super.update(elapsed); return;
				}
				if (optionShit[curSelected] == 'donate') {
					#if linux
					Sys.command('/usr/bin/xdg-open', [FNFAssets.getText("assets/data/donate_button_link.txt"), "&"]);
					#else
					FlxG.openURL(FNFAssets.getText("assets/data/donate_button_link.txt"));
					#end
				} else {
					selectedSomethin = true;
					FlxG.sound.play('assets/sounds/custom_menu_sounds/'
					+ menuSoundJson.customMenuConfirm+'/confirmMenu' + TitleState.soundExt);

					FlxFlicker.flicker(magenta, 1.1, 0.15, false);

					menuItems.forEach(function(spr:MenuCard) {
						if (curSelected != spr.ID) {
							FlxTween.tween(spr, {opacity: 0}, 0.4, {
								ease: FlxEase.quadOut,
								onComplete: function(twn:FlxTween) {
									spr.kill();
								}
							});
						} else {
							spr.flicker(1, 0.06, function() {
								var daChoice:String = optionShit[curSelected];

								switch (daChoice) {
									case 'story mode':
										LoadingState.loadAndSwitchState(new StoryMenuState());
										trace("Story Menu Selected");
									case 'freeplay':
										FreeplayState.openHostLibrary();
										LoadingState.loadAndSwitchState(new FreeplayState());

									case 'options':
										SaveDataState.prevPath = 'title';
										LoadingState.loadAndSwitchState(new SaveDataState());
									#if sys
									case 'online':
										LoadingState.loadAndSwitchState(new multiplayer.MpLobbyState());
									case 'import':
										LoadingState.loadAndSwitchState(new ImportSettingsState());
									#end
									case 'costumes':
										if (hxcCostumeState != null)
											LoadingState.loadAndSwitchState(cast hxcCostumeState);
								}
							});
						}
					});
				}
			}
		}

		super.update(elapsed);
	}

	/**
		Mount a complete imported main menu without executing its donor object
		graph.  All media is checked below the selected compatibility root before
		any native menu object is hidden; a missing or partial manifest therefore
		leaves the ordinary MainMenuState visible and usable.
	*/
	public function hxcMountMenuOverlay(rawSpec:Dynamic, assetRoot:String):Bool {
		var spec = HxcMenuSpec.fromDynamic(rawSpec);
		if (spec == null || assetRoot == null || StringTools.trim(assetRoot) == '') {
			trace('[hxc-menu-fallback] invalid menu spec or missing manifest root; native menu retained.');
			return false;
		}
		var cleanRoot = StringTools.replace(StringTools.trim(assetRoot), '\\', '/');
		if (!cleanRoot.startsWith(CompatScriptManifest.ROOT_PREFIX + '/')) {
			trace('[hxc-menu-fallback] menu root is outside the compatibility manifest; native menu retained.');
			return false;
		}
		if (spec.requiredAssets != null)
			for (asset in spec.requiredAssets)
				if (HxcStateAssetScope.scopedAssetPath(cleanRoot, asset) == null) {
					trace('[hxc-menu-fallback] missing scoped menu asset ' + asset + '; native menu retained.');
					return false;
				}

		// Re-mounting is idempotent and never leaves a previous camera or object
		// graph alive.  Validation above intentionally happens before this clear.
		hxcClearMenuOverlay();
		var backgroundPath = hxcOverlayImagePath(cleanRoot, spec.background);
		if (backgroundPath == null) {
			trace('[hxc-menu-fallback] missing scoped menu background; native menu retained.');
			return false;
		}
		var camera = new FlxCamera();
		camera.bgColor = 0x00000000;
		FlxG.cameras.add(camera, false);
		try {
			var background = new FlxSprite().loadGraphic(FNFAssets.getBitmapData(backgroundPath));
			background.setGraphicSize(FlxG.width, FlxG.height);
			background.updateHitbox();
			background.screenCenter();
			background.cameras = [camera];
			background.scrollFactor.set();
			add(background);
			hxcOverlayObjects.push(background);

			var atlas:FlxAtlasFrames = null;
			if (spec.style == HxcMenuSpec.STYLE_BUTTON) {
				atlas = HxcStateAssetScope.sparrowAtlas(cleanRoot, spec.atlas, null,
					'HXC main-menu overlay');
				if (atlas == null)
					throw 'scoped button atlas could not be loaded';
			}
			for (index in 0...spec.items.length) {
				var item = spec.items[index];
				if (spec.style == HxcMenuSpec.STYLE_BUTTON) {
					var button = new FlxSprite();
					button.frames = atlas;
					var idlePrefix = item.id + (spec.itemPrefix == null ? '_button0' : spec.itemPrefix);
					var selectedPrefix = item.id + (spec.selectedPrefix == null ? '_button_sel0' : spec.selectedPrefix);
					button.animation.addByPrefix('idle', idlePrefix, 24, true);
					button.animation.addByPrefix('selected', selectedPrefix, 24, false);
					button.animation.play(index == 0 ? 'selected' : 'idle');
					button.setGraphicSize(Std.int(button.width * 0.81));
					button.updateHitbox();
					button.x = FlxG.width * 0.14;
					button.y = FlxG.height * (0.09 + index * 0.20);
					button.cameras = [camera];
					button.scrollFactor.set();
					add(button);
					hxcOverlayObjects.push(button);
				} else {
					var text = new FlxText(50, 260 + index * 50, 0, item.label,
						spec.fontSize == null ? 27 : spec.fontSize);
					var fontPath = hxcOverlayFontPath(cleanRoot, spec.font);
					if (fontPath != null)
						text.setFormat(fontPath, spec.fontSize == null ? 27 : spec.fontSize,
							FlxColor.WHITE, 'left', FlxTextBorderStyle.OUTLINE, 0xFFFF7CFF);
					else
						text.setFormat(null, spec.fontSize == null ? 27 : spec.fontSize,
							FlxColor.WHITE, 'left', FlxTextBorderStyle.OUTLINE, 0xFFFF7CFF);
					text.cameras = [camera];
					text.scrollFactor.set();
					add(text);
					hxcOverlayObjects.push(text);
				}
			}
		} catch (error:Dynamic) {
			trace('[hxc-menu-fallback] scoped menu construction failed: ' + Std.string(error));
			// The clear is idempotent and restores the native menu after partial
			// allocation, including the temporary camera.
			hxcOverlayCamera = camera;
			hxcClearMenuOverlay();
			return false;
		}
		hxcOverlaySpec = spec;
		hxcOverlayRoot = cleanRoot;
		hxcOverlayCamera = camera;
		hxcOverlayIndex = 0;
		hxcOverlayBusy = false;
		hxcOverlayMenuVisible = menuItems == null ? true : menuItems.visible;
		hxcOverlayMagentaVisible = magenta == null ? false : magenta.visible;
		if (menuItems != null)
			menuItems.visible = false;
		if (magenta != null)
			magenta.visible = false;
		return true;
	}

	/** Clear every native overlay object/camera and restore this menu's UI. */
	public function hxcClearMenuOverlay():Bool {
		if (hxcOverlayObjects != null)
			for (object in hxcOverlayObjects.copy()) {
				if (object == null)
					continue;
				try {
					remove(cast object, true);
					if (Std.isOfType(object, FlxSprite))
						(cast object:FlxSprite).destroy();
				} catch (_:Dynamic) {}
			}
		hxcOverlayObjects.resize(0);
		if (hxcOverlayCamera != null) {
			try
				FlxG.cameras.remove(hxcOverlayCamera, false)
			catch (_:Dynamic) {}
			try
				hxcOverlayCamera.destroy()
			catch (_:Dynamic) {}
		}
		hxcOverlayCamera = null;
		hxcOverlaySpec = null;
		hxcOverlayRoot = '';
		hxcOverlayIndex = 0;
		hxcOverlayBusy = false;
		if (menuItems != null)
			menuItems.visible = hxcOverlayMenuVisible;
		if (magenta != null)
			magenta.visible = hxcOverlayMagentaVisible;
		return true;
	}

	/** Host-owned input/update loop for a mounted menu spec. */
	function updateHxcMenuOverlay():Void {
		if (hxcOverlaySpec == null || hxcOverlayBusy)
			return;
		if (controls.UP_MENU || controls.UP_P) {
			hxcOverlayIndex--;
			if (hxcOverlayIndex < 0)
				hxcOverlayIndex = hxcOverlaySpec.items.length - 1;
			hxcRefreshMenuOverlaySelection();
		}
		if (controls.DOWN_MENU || controls.DOWN_P) {
			hxcOverlayIndex++;
			if (hxcOverlayIndex >= hxcOverlaySpec.items.length)
				hxcOverlayIndex = 0;
			hxcRefreshMenuOverlaySelection();
		}
		if (controls.BACK) {
			hxcClearMenuOverlay();
			LoadingState.loadAndSwitchState(new TitleState());
			return;
		}
		if (controls.ACCEPT)
			hxcSelectMenuOverlayItem();
	}

	function hxcRefreshMenuOverlaySelection():Void {
		if (hxcOverlaySpec == null || hxcOverlayObjects == null)
			return;
		if (hxcOverlaySpec.style != HxcMenuSpec.STYLE_BUTTON)
			return;
		for (index in 0...hxcOverlayObjects.length) {
			var button = hxcOverlayObjects[index];
			if (Std.isOfType(button, FlxSprite))
				(cast button:FlxSprite).animation.play(index == hxcOverlayIndex ? 'selected' : 'idle');
		}
	}

	function tryOpenImportedMods():Bool {
		if (!selectedSomethin && FlxG.keys.justPressed.I) {
			selectedSomethin = true;
			LoadingState.loadAndSwitchState(new CodenameImportedModsState());
			return true;
		}
		return false;
	}

	function hxcSelectMenuOverlayItem():Void {
		if (hxcOverlaySpec == null || hxcOverlayBusy
			|| hxcOverlayIndex < 0 || hxcOverlayIndex >= hxcOverlaySpec.items.length)
			return;
		var item = hxcOverlaySpec.items[hxcOverlayIndex];
		if (!ImportMenuNavigationPolicy.mainActionAllowed(importWorkBusy, item.route)) return;
		hxcOverlayBusy = true;
		var route = item.route;
		hxcClearMenuOverlay();
		switch (route) {
			case HxcMenuSpec.ROUTE_STORY:
				LoadingState.loadAndSwitchState(new StoryMenuState());
			case HxcMenuSpec.ROUTE_FREEPLAY:
				if (!ImportedMenuEntry.openOwnedFreeplay(hxcOverlayRoot)) {
					FreeplayState.openHostLibrary();
					LoadingState.loadAndSwitchState(new FreeplayState());
				}
			case HxcMenuSpec.ROUTE_OPTIONS:
				SaveDataState.prevPath = 'title';
				LoadingState.loadAndSwitchState(new SaveDataState());
			case HxcMenuSpec.ROUTE_CREDITS:
				if (!hxcRouteImportedMenuItem(item))
					LoadingState.loadAndSwitchState(new CreditsState());
			case HxcMenuSpec.ROUTE_COSTUMES | HxcMenuSpec.ROUTE_IMPORTED:
				if (!hxcRouteImportedMenuItem(item))
					trace('[hxc-menu-route-fallback] imported menu target unavailable; native menu retained.');
			default:
				trace('[hxc-menu-route-noop] no native route for menu item ' + item.label + '; native menu retained.');
		}
	}

	function hxcRouteImportedMenuItem(item:HxcMenuItemSpec):Bool {
		if (item == null || item.target == null || StringTools.trim(item.target) == '')
			return false;
		var target = HxcStateFactory.stateInit(hxcOverlayRoot, item.target);
		if (target == null)
			return false;
		return HxcStateFactory.switchStateScoped(hxcOverlayRoot, target);
	}

	static function hxcOverlayImagePath(root:String, key:String):String {
		if (key == null || StringTools.trim(key) == '')
			return null;
		var clean = StringTools.replace(StringTools.trim(key), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean.toLowerCase().startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		if (!clean.toLowerCase().startsWith('images/'))
			clean = 'images/' + clean;
		if (!clean.toLowerCase().endsWith('.png'))
			clean += '.png';
		return HxcStateAssetScope.scopedAssetPath(root, clean);
	}

	static function hxcOverlayFontPath(root:String, key:String):String {
		if (key == null || StringTools.trim(key) == '')
			return null;
		var clean = StringTools.replace(StringTools.trim(key), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean.toLowerCase().startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		if (!clean.toLowerCase().startsWith('fonts/'))
			clean = 'fonts/' + clean;
		return HxcStateAssetScope.scopedAssetPath(root, clean);
	}

	override public function destroy():Void {
		hxcClearMenuOverlay();
		super.destroy();
	}

	/**
		Native destination for the bounded CostumeMenuButtonv2 HXC adapter.
		The imported module supplies only the manifest-scoped destination state;
		this class owns the option list, cards, and selection behavior.
	*/
	public function hxcAddCostumeMenuItem(target:Dynamic, ?assetRoot:String):Bool {
		if (target == null)
			return false;
		hxcCostumeState = target;
		var existing = optionShit.indexOf('costumes');
		if (existing >= 0)
			return true;
		optionShit.push('costumes');
		if (menuItems == null)
			return true;

		var card = new MenuCard(rowLabel('costumes'), MainMenuLayout.WIDTH, 28, MainMenuLayout.LOOK);
		card.ID = optionShit.length - 1;
		card.setCaption(rowCaption('costumes'));
		var scopedFrames = HxcStateAssetScope.sparrowAtlas(assetRoot,
			'mainmenu/PleaseKrillMe', null, 'CostumeMenuButtonv2 main-menu item');
		if (scopedFrames != null) {
			// The donor's own button art becomes the card's icon.
			var art = new FlxSprite();
			art.frames = scopedFrames;
			art.animation.addByPrefix('idle', 'costumes idle', 24);
			if (art.animation.exists('idle')) {
				art.animation.play('idle');
				card.setIcon(art);
			}
		}
		// A missing/partial donor atlas is an explicit diagnostic from the
		// manifest asset boundary; keep the menu action usable with a plain card.
		// The former asset-scope gap is therefore visible and recoverable.
		menuItems.add(card);
		layoutMenuItems(true);
		changeItem();
		return true;
	}

	/**
		Place every native row on the stack: the selected card is open and the
		others sit above and below it.
	*/
	function layoutMenuItems(snap:Bool = false):Void {
		var row = 0;
		var count = menuItems.length;
		for (card in menuItems.members) {
			card.present(row == curSelected, false);
			card.visible = MainMenuLayout.shown(row, curSelected, count, FlxG.height);
			card.moveTo(MainMenuLayout.LEFT, MainMenuLayout.rowTop(row, curSelected, count, FlxG.height), snap);
			row++;
		}
	}

	function changeItem(huh:Int = 0) {
		curSelected += huh;

		if (curSelected >= menuItems.length)
			curSelected = 0;
		if (curSelected < 0)
			curSelected = menuItems.length - 1;

		layoutMenuItems();
		refreshFacts();
	}
}
