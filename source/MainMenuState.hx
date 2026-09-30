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
	var menuItems:FlxTypedGroup<FlxSprite>;
	var menuFrames:FlxAtlasFrames;
	var hxcCostumeState:Dynamic;
	#if !switch
	var optionShit:Array<String> = ['story mode', 'freeplay', 'donate', 'options'];
	#else
	var optionShit:Array<String> = ['story mode', 'freeplay'];
	#end
	var menuSoundJson:Dynamic;
	var scrollSound:String;
	var magenta:FlxSprite;
	var camFollow:FlxObject;
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
		if (!FlxG.sound.music.playing) {
			FlxG.sound.playMusic(FNFAssets.getSound('assets/music/custom_menu_music/'
				+ CoolUtil.parseJson(FNFAssets.getText("assets/music/custom_menu_music/custom_menu_music.json")).Menu+'/freakyMenu' + TitleState.soundExt));
		}
		
		persistentUpdate = persistentDraw = true;
		var bg:FlxSprite = new FlxSprite(-80).loadGraphic('assets/images/menuBG.png');
		bg.scrollFactor.x = 0;
		bg.scrollFactor.y = 0.18;
		bg.setGraphicSize(Std.int(bg.width * 1.2));
		bg.updateHitbox();
		bg.screenCenter();
		bg.antialiasing = true;
		add(bg);

		camFollow = new FlxObject(0, 0, 1, 1);
		add(camFollow);

		magenta = new FlxSprite(-80).loadGraphic('assets/images/menuDesat.png');
		magenta.scrollFactor.x = 0;
		magenta.scrollFactor.y = 0.18;
		magenta.setGraphicSize(Std.int(magenta.width * 1.2));
		magenta.updateHitbox();
		magenta.screenCenter();
		magenta.visible = false;
		magenta.antialiasing = true;
		magenta.color = 0xFFfd719b;
		add(magenta);
		// magenta.scrollFactor.set();

		menuItems = new FlxTypedGroup<FlxSprite>();
		add(menuItems);

		menuFrames = FlxAtlasFrames.fromSparrow('assets/images/FNF_main_menu_assets.png', 'assets/images/FNF_main_menu_assets.xml');

		for (i in 0...optionShit.length) {
			var menuItem:FlxSprite = new FlxSprite(0, 100 + (i * 160));
			menuItem.frames = menuFrames;
			menuItem.animation.addByPrefix('idle', optionShit[i] + " basic", 24);
			menuItem.animation.addByPrefix('selected', optionShit[i] + " white", 24);
			menuItem.animation.play('idle');
			menuItem.ID = i;
			menuItems.add(menuItem);
			menuItem.scrollFactor.set();
			menuItem.antialiasing = true;
		}

		FlxG.camera.follow(camFollow, null, 0.06);
		version = 'v' + EngineBranding.version();
		var appName = Application.current.meta.get('name');
		var versionShit:FlxText = new FlxText(5, FlxG.height - 18, 0, appName + ' ' + version, 12);
		var usingSave:FlxText = new FlxText(5, FlxG.height - 36, 0, FlxG.save.name, 12);
		versionShit.scrollFactor.set();
		versionShit.setFormat("VCR OSD Mono", 16, FlxColor.WHITE, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		usingSave.scrollFactor.set();
		usingSave.setFormat("VCR OSD Mono", 16, FlxColor.WHITE, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		add(versionShit);
		importedModsHint = new FlxText(FlxG.width - 242, FlxG.height - 25, 236,
			'Imported Mods  [I]', 14);
		importedModsHint.setFormat(null, 14, 0xFFA0A0A0, RIGHT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		importedModsHint.scrollFactor.set();
		add(importedModsHint);
		if (OptionsHandler.options.useSaveDataMenu)
			add(usingSave);
		// NG.core.calls.event.logEvent('swag').send();
		usingSave.text = switch (FlxG.save.name) {
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

		changeItem();

		super.create();
	}

	var selectedSomethin:Bool = false;

	override function update(elapsed:Float) {
		if (FlxG.sound.music.volume < 0.8) {
			FlxG.sound.music.volume += 0.5 * FlxG.elapsed;
		}

		// Keep the owner chooser reachable when a HXC overlay owns menu input.
		// This route is checked first so the overlay's normal update still runs
		// unchanged for every other key and only an explicit I press exits it.
		if (tryOpenImportedMods())
			return;

		if (hxcOverlaySpec != null) {
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

					menuItems.forEach(function(spr:FlxSprite) {
						if (curSelected != spr.ID) {
							FlxTween.tween(spr, {alpha: 0}, 0.4, {
								ease: FlxEase.quadOut,
								onComplete: function(twn:FlxTween) {
									spr.kill();
								}
							});
						} else {
							FlxFlicker.flicker(spr, 1, 0.06, false, false, function(flick:FlxFlicker) {
								var daChoice:String = optionShit[curSelected];

								switch (daChoice) {
									case 'story mode':
										LoadingState.loadAndSwitchState(new StoryMenuState());
										trace("Story Menu Selected");
									case 'freeplay':
										CategoryState.choosingFor = "freeplay";
										var epicCategoryJs:Array<Dynamic> = cast FreeplayRegistry.getJson();
										FreeplayState.soundTest = false;
										if (epicCategoryJs.length > 1) {
											LoadingState.loadAndSwitchState(new CategoryState());
										}  else {
											FreeplayState.currentSongList = epicCategoryJs[0].songs;
											LoadingState.loadAndSwitchState(new FreeplayState());
										}
										
									case 'options':
										SaveDataState.prevPath = 'title';
										LoadingState.loadAndSwitchState(new SaveDataState());
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

		menuItems.forEach(function(spr:FlxSprite) {
			spr.screenCenter(X);
		});
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
		hxcOverlayBusy = true;
		var item = hxcOverlaySpec.items[hxcOverlayIndex];
		var route = item.route;
		hxcClearMenuOverlay();
		switch (route) {
			case HxcMenuSpec.ROUTE_STORY:
				LoadingState.loadAndSwitchState(new StoryMenuState());
			case HxcMenuSpec.ROUTE_FREEPLAY:
				CategoryState.choosingFor = 'freeplay';
				var categories:Array<Dynamic> = cast FreeplayRegistry.getJson();
				FreeplayState.soundTest = false;
				if (categories != null && categories.length > 1)
					LoadingState.loadAndSwitchState(new CategoryState());
				else if (categories != null && categories.length > 0) {
					FreeplayState.currentSongList = categories[0].songs;
					LoadingState.loadAndSwitchState(new FreeplayState());
				} else
					trace('[hxc-menu-route-fallback] freeplay registry is empty; native menu retained.');
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
		this class owns the option list, atlas frames, and selection behavior.
	*/
	public function hxcAddCostumeMenuItem(target:Dynamic, ?assetRoot:String):Bool {
		if (target == null)
			return false;
		hxcCostumeState = target;
		var existing = optionShit.indexOf('costumes');
		if (existing >= 0)
			return true;
		optionShit.push('costumes');
		if (menuItems == null || menuFrames == null)
			return true;

		var menuItem:FlxSprite = new FlxSprite(0, 100 + (menuItems.length * 160));
		var scopedFrames = HxcStateAssetScope.sparrowAtlas(assetRoot,
			'mainmenu/PleaseKrillMe', null, 'CostumeMenuButtonv2 main-menu item');
		if (scopedFrames != null) {
			menuItem.frames = scopedFrames;
			menuItem.animation.addByPrefix('idle', 'costumes idle', 24);
			menuItem.animation.addByPrefix('selected', 'costumes selected', 24);
		} else {
			// A missing/partial donor atlas is an explicit diagnostic from the
			// manifest asset boundary; keep the menu action usable with native frames.
			// The former asset-scope gap is therefore visible and recoverable.
			menuItem.frames = menuFrames;
			menuItem.animation.addByPrefix('idle', 'freeplay basic', 24);
			menuItem.animation.addByPrefix('selected', 'freeplay white', 24);
		}
		menuItem.animation.play('idle');
		menuItem.ID = optionShit.length - 1;
		menuItem.scrollFactor.set();
		menuItem.antialiasing = true;
		menuItems.add(menuItem);
		changeItem();
		return true;
	}

	function changeItem(huh:Int = 0) {
		curSelected += huh;

		if (curSelected >= menuItems.length)
			curSelected = 0;
		if (curSelected < 0)
			curSelected = menuItems.length - 1;

		menuItems.forEach(function(spr:FlxSprite) {
			spr.animation.play('idle');

			if (spr.ID == curSelected) {
				spr.animation.play('selected');
				camFollow.setPosition(spr.getGraphicMidpoint().x, spr.getGraphicMidpoint().y);
			}

			spr.updateHitbox();
		});
	}
}
