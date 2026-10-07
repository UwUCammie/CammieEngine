package;

import flixel.FlxG;
import flixel.FlxObject;
import flixel.FlxSprite;
import flixel.effects.FlxFlicker;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.input.keyboard.FlxKey;
import flixel.math.FlxMath;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween;
import flixel.util.FlxAxes;
import flixel.util.FlxColor;

/** Native implementation of the pinned Nightmare Vision MainMenuState. */
@:keep
class NightmareVisionMainMenuState extends NightmareVisionMusicBeatState {
	static inline var BACKGROUND:String = 'menus/menuBG';
	static inline var MAGENTA:String = 'menus/menuDesat';
	static inline var NMV_VERSION:String = '1.0';
	static inline var PSYCH_VERSION:String = '0.5.2h';
	static inline var FUNKIN_VERSION:String = '0.2.7';
	final session:NightmareVisionStateSession;
	final assets:NightmareVisionFunkinAssets;
	final debugKeys:Array<FlxKey>;
	var optionShit:Array<String> = ['story_mode', 'freeplay', 'credits', 'options'];
	var canInteract:Bool = false;
	var menuItems:Null<FlxTypedGroup<FlxSprite>>;
	var magenta:Null<FlxSprite>;
	var camFollow:Null<FlxObject>;

	public function new(session:NightmareVisionStateSession) {
		if (session == null) throw '[nightmare-vision-main-menu] Missing captured source session';
		super(session.stateHost());
		this.session = session;
		assets = new NightmareVisionFunkinAssets(session.paths);
		var storedKeys:Dynamic = session.prefs.view.keyBinds.get('debug_1');
		debugKeys = cast session.prefs.view.copyKey(storedKeys);
	}

	/** Match the donor sequence so scripts see the constructed menu on onCreate. */
	public override function create():Void {
		session.mods.pushGlobalMods();
		session.changePresence('In the Menus');

		FlxG.cameras.reset();
		persistentUpdate = true;
		persistentDraw = true;
		initStateScript('MainMenuState');

		camFollow = new FlxObject(FlxG.width / 2, 0, 1, 1);
		add(camFollow);
		FlxG.camera.follow(camFollow, null, 0.075);

		var yScroll:Float = Math.max(0.25 - (0.05 * (optionShit.length - 4)), 0.1);
		var bg = new FlxSprite(-80, 0, requireGraphic(BACKGROUND));
		bg.scrollFactor.set(0, yScroll);
		bg.scale.scale(1.175);
		bg.updateHitbox();
		bg.screenCenter();
		add(bg);

		magenta = new FlxSprite(-80, 0, requireGraphic(MAGENTA));
		magenta.scrollFactor.copyFrom(bg.scrollFactor);
		magenta.scale.copyFrom(bg.scale);
		magenta.updateHitbox();
		magenta.screenCenter();
		magenta.visible = false;
		magenta.color = 0xFFfd719b;
		add(magenta);

		menuItems = new FlxTypedGroup<FlxSprite>();
		add(menuItems);
		for (index in 0...optionShit.length) {
			var option = optionShit[index];
			var offset:Float = 108 - (Math.max(optionShit.length, 4) - 4) * 80;
			var menuItem = new FlxSprite(0, (index * 140) + offset);
			menuItem.frames = requireAtlas('menus/mainmenu/menu_' + option);
			menuItem.animation.addByPrefix('idle', option + ' basic', 24);
			menuItem.animation.addByPrefix('selected', option + ' white', 24);
			menuItem.animation.play('idle');
			menuItem.ID = index;
			menuItem.screenCenter(FlxAxes.X);
			menuItems.add(menuItem);
			var scroll:Float = optionShit.length < 6 ? 0 : (optionShit.length - 4) * 0.135;
			menuItem.scrollFactor.set(0, scroll);
			menuItem.updateHitbox();
		}

		var versionText = 'Nightmare Vision Engine v' + NMV_VERSION
			+ '\nPsych Engine v' + PSYCH_VERSION
			+ "\nFriday Night Funkin' v" + FUNKIN_VERSION;
		var verionDesc = new FlxText(12, 0, 0, versionText, 16);
		verionDesc.setFormat(session.paths.DEFAULT_FONT, 16, FlxColor.WHITE, FlxTextAlign.LEFT,
			FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		verionDesc.borderSize = 1.5;
		verionDesc.y = FlxG.height - verionDesc.height - 12;
		verionDesc.scrollFactor.set();
		add(verionDesc);

		changeSelection();
		super.create();
		scriptGroup.call('onCreate', []);
	}

	public override function update(elapsed:Float):Void {
		if (FlxG.sound.music != null && FlxG.sound.music.volume < 0.8) {
			FlxG.sound.music.volume += 0.5 * elapsed;
			if (session.menuVocals != null) session.menuVocals.volume += 0.5 * elapsed;
		}

		if (!canInteract) {
			if (FlxG.keys.justPressed.TAB) {
				canInteract = true;
				switchTo('ModsState');
			}

			if (controls.UI_UP_P || controls.UI_DOWN_P) {
				playMenuSound('scrollMenu');
				changeSelection(controls.UI_UP_P ? -1 : 1);
			}

			if (controls.BACK) {
				canInteract = true;
				playMenuSound('cancelMenu');
				switchTo('TitleState');
			}

			scriptGroup.set('curSelected', selectedIndex());
			if (controls.ACCEPT) acceptSelection();
			else if (FlxG.keys.anyJustPressed(debugKeys)) {
				canInteract = true;
				switchTo('MasterEditorMenu');
			}
		}

		super.update(elapsed);
		scriptGroup.call('onUpdatePost', [elapsed]);
	}

	function acceptSelection():Void {
		var selected = selectedIndex();
		var option = optionShit[selected];
		if (scriptGroup.call('onSelect', [option]) == NightmareVisionScriptGroup.STOP_FUNC) return;

		canInteract = true;
		playMenuSound('confirmMenu');
		if (session.prefs.view.flashing && magenta != null)
			FlxFlicker.flicker(magenta, 1.1, 0.15, false);

		var items = menuItems;
		if (items == null || selected < 0 || selected >= items.members.length)
			throw '[nightmare-vision-main-menu] Selected source menu item is unavailable';
		var selectedObject = items.members[selected];
		FlxFlicker.flicker(selectedObject, 1, 0.06, false, false, function(_):Void {
			switch (optionShit[selectedIndex()]) {
				case 'story_mode': switchTo('StoryMenuState', NightmareVisionModTransition.NONE);
				case 'freeplay': switchTo('FreeplayState', NightmareVisionModTransition.SWIPE);
				case 'credits': switchTo('CreditsState');
				case 'options': switchTo('OptionsState');
				default: throw '[nightmare-vision-main-menu] Unknown source menu selection';
			}
		});

		items.forEachAlive(function(item:FlxSprite):Void {
			if (item != selectedObject)
				FlxTween.tween(item, {alpha: 0}, 0.4, {ease:FlxEase.quadOut});
		});
	}

	function switchTo(name:String, transition:NightmareVisionModTransition = NightmareVisionModTransition.ENGINE_DEFAULT):Void {
		var factory = session.createStateFactory(name);
		if (transition == NightmareVisionModTransition.ENGINE_DEFAULT) session.switchState(factory);
		else session.switchWithTransition(factory, transition);
	}

	function changeSelection(diff:Int = 0):Void {
		var items = menuItems;
		if (items == null || items.length == 0) return;
		var previous = selectedIndex();
		setSelectedIndex(FlxMath.wrap(previous + diff, 0, items.length - 1));
		if (scriptGroup.call('onChangeSelection', [selectedIndex()]) == NightmareVisionScriptGroup.STOP_FUNC) return;

		var previousItem = items.members[previous];
		previousItem.animation.play('idle');
		previousItem.updateHitbox();

		var selectedItem = items.members[selectedIndex()];
		selectedItem.animation.play('selected');
		selectedItem.centerOffsets();
		var offset:Float = items.length > 4 ? items.length * 8 : 0;
		if (camFollow != null) camFollow.y = selectedItem.getGraphicMidpoint().y - offset;
	}

	function selectedIndex():Int return session.mainMenuSelected;
	function setSelectedIndex(value:Int):Void session.mainMenuSelected = value;

	function requireAtlas(key:String):FlxAtlasFrames {
		requireGraphic(key);
		var metadataFound = false;
		for (extension in ['xml', 'json', 'txt']) {
			var metadata = session.paths.getPath('images/' + key + '.' + extension, null, true);
			if (session.paths.exists(metadata) && !session.paths.isDirectory(metadata)) {
				metadataFound = true;
				break;
			}
		}
		if (!metadataFound) missingMenuAsset('images/' + key + ' atlas metadata');
		var frames = session.paths.getSparrowAtlas(key);
		if (frames == null) missingMenuAsset('images/' + key + ' decoded atlas');
		return frames;
	}

	function requireGraphic(key:String):flixel.graphics.FlxGraphic {
		var relative = 'images/' + key + '.png';
		var path = session.paths.getPath(relative, null, true);
		if (!session.paths.exists(path) || session.paths.isDirectory(path)) missingMenuAsset(relative);
		var graphic = assets.getGraphicUnsafe(path);
		if (graphic == null) missingMenuAsset(relative + ' decoded image');
		return graphic;
	}

	function playMenuSound(key:String):Void {
		var path = session.paths.findFileWithExts('sounds/' + key, ['ogg', 'wav'], null, true);
		if (!session.paths.exists(path) || session.paths.isDirectory(path)) missingMenuAsset(path);
		var sound = assets.getSoundUnsafe(path);
		if (sound == null) missingMenuAsset(path + ' decoded audio');
		FlxG.sound.play(sound);
	}

	function missingMenuAsset(asset:String):Void {
		var message = '[nightmare-vision-main-menu-asset-missing] Required source menu asset is unavailable in the selected package or its captured core: ' + asset;
		sourceHost.report('MainMenuState', 'assets', message);
		throw message;
	}
}
