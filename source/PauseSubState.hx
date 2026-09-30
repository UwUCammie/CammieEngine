package;

import Controls.Control;
import HxcPauseSpec.HxcPauseSpec;
import HxcPauseSpec.HxcPauseSpecData;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.FlxSubState;
import flixel.addons.transition.FlxTransitionableState;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.input.keyboard.FlxKey;
import flixel.sound.FlxSound;
import flixel.util.FlxColor;
import flixel.FlxCamera;
using StringTools;

class PauseSubState extends MusicBeatSubstate {
	/** HXC/V-Slice compatibility setting backed by HxcCompatRuntime. */
	public static var musicSuffix(get, set):String;
	static function get_musicSuffix():String
		return HxcCompatRuntime.pauseMusicSuffix;
	static function set_musicSuffix(value:String):String
		return HxcCompatRuntime.setPauseMusicSuffix(value);

	var grpMenuShit:FlxTypedGroup<Alphabet>;

	var songNameTxt:FlxText;
	var curDiffTxt:FlxText;
	var deathsTxt:FlxText;

	var menuItems:Array<String> = ['Resume', 'Restart Song', 'Change Difficulty', 'Change Modifiers', 'Change Options', 'Charting', 'Exit to menu'];
	var curSelected:Int = 0;

	var inDiffs:Bool = false;
	var diffNames:Array<String> = ['Back', 'Hard', 'Normal', 'Easy'];
	var diffs:Array<Int> = [];

	var pauseMusic:FlxSound;
	var pauseCamera:FlxCamera;
	var nativePauseBackdrop:FlxSprite;
	var codenamePauseRuntime:CodenameModSubStateRuntime;
	var codenamePauseCancelled:Bool = false;

	/** Native owner state for a manifest-scoped imported pause description. */
	var hxcPauseSpec:Null<HxcPauseSpecData>;
	var hxcPauseRoot:String = '';
	var hxcPauseObjects:Array<Dynamic> = [];
	var hxcHiddenMenuIndices:Array<Int> = [];
	var hxcNativeItemColors:Array<Int> = [];
	var hxcPracticeText:FlxText;
	var hxcNativeSongText:String;
	var hxcNativeDeathsText:String;
	var hxcNativeSongFont:String;
	var hxcNativeDeathsFont:String;
	var hxcNativeDiffVisible:Bool = true;
	var hxcNativeDeathsVisible:Bool = true;
	var hxcPauseApplied:Bool = false;

	public function new(x:Float, y:Float, camera:FlxCamera) {
		super();

		var pauseTrack = 'breakfast' + HxcCompatRuntime.pauseMusicSuffix + TitleState.soundExt;
		if (!FNFAssets.exists('assets/music/' + pauseTrack))
			pauseTrack = 'breakfast' + TitleState.soundExt;
		pauseMusic = new FlxSound().loadEmbedded('assets/music/' + pauseTrack, true, true);
		pauseMusic.volume = 0;
		pauseMusic.play(false, FlxG.random.int(0, Std.int(pauseMusic.length / 2)));
		FlxG.sound.list.add(pauseMusic);

		nativePauseBackdrop = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, FlxColor.BLACK);
		nativePauseBackdrop.alpha = 0.6;
		nativePauseBackdrop.scrollFactor.set();
		add(nativePauseBackdrop);

		grpMenuShit = new FlxTypedGroup<Alphabet>();
		add(grpMenuShit);

		if (PlayState.SONG.cutsceneType != 'none')
			menuItems.insert(2, "Replay Cutscene");

		makeMenuItems(menuItems);

		songNameTxt = new FlxText(0, 20, FlxG.width - 10, PlayState.SONG.song, 32);
		songNameTxt.font = "assets/fonts/vcr.ttf";
		songNameTxt.alignment = RIGHT;
		add(songNameTxt);

		curDiffTxt = new FlxText(0, 55, FlxG.width - 10, "Difficulty: " + PlayState.storyDifficultyText, 32);
		curDiffTxt.font = "assets/fonts/vcr.ttf";
		curDiffTxt.alignment = RIGHT;
		add(curDiffTxt);

		deathsTxt = new FlxText(0, 90, FlxG.width - 10, PlayState.balls + " Blue Balls", 32);
		deathsTxt.font = "assets/fonts/vcr.ttf";
		deathsTxt.alignment = RIGHT;
		add(deathsTxt);

		changeSelection();

		// Authored HUD fades, filters and transforms must not hide the pause UI.
		// Keep their state intact and own a transparent screen-space overlay.
		pauseCamera = new FlxCamera();
		pauseCamera.bgColor = FlxColor.TRANSPARENT;
		FlxG.cameras.add(pauseCamera, false);
		cameras = [pauseCamera];
		codenameInitPauseScript();
	}

	/** Run only the module script belonging to the explicitly active owner. */
	function codenameInitPauseScript():Void {
		var owner = CodenameModRuntime.activeRoot();
		var path = 'data/scripts/pause.hx';
		if (!CodenameModSubStateRuntime.hasScript(owner, path)) return;
		var disabler = new CodenameParentDisabler();
		add(disabler);
		codenamePauseRuntime = new CodenameModSubStateRuntime(this, owner, path,
			'pause', disabler);
		var event = new CodenamePauseCreationEvent(menuItems, 'breakfast' + musicSuffix);
		codenamePauseCancelled = codenamePauseRuntime.create(event);
		if (event.options != null) {
			menuItems = event.options.copy();
			if (!codenamePauseCancelled) {
				makeMenuItems(menuItems);
				curSelected = 0;
				changeSelection();
			}
		}
		if (codenamePauseCancelled) {
			if (nativePauseBackdrop != null) nativePauseBackdrop.visible = false;
			if (grpMenuShit != null) grpMenuShit.visible = false;
			if (songNameTxt != null) songNameTxt.visible = false;
			if (curDiffTxt != null) curDiffTxt.visible = false;
			if (deathsTxt != null) deathsTxt.visible = false;
			if (pauseMusic != null) pauseMusic.stop();
		}
	}

	function makeMenuItems(items) {
		grpMenuShit.clear();
		hxcHiddenMenuIndices.resize(0);
		hxcNativeItemColors.resize(0);

		for (i in 0...items.length) {
			var songText:Alphabet = new Alphabet(0, (70 * i) + 30, items[i], true, false);
			songText.isMenuItem = true;
			songText.targetY = i;
			grpMenuShit.add(songText);
		}
		if (hxcPauseApplied)
			hxcApplyMenuPresentation();
	}

	/**
		Native host boundary for a complete data-only HXC pause description.
		Validation is performed before replacing any stock object, so a missing
		manifest asset leaves the ordinary pause menu usable.
	*/
	public function hxcApplyPauseOverlay(assetRoot:String, rawSpec:Dynamic):Bool {
		var spec = HxcPauseSpec.fromDynamic(rawSpec);
		var cleanRoot = assetRoot == null ? '' : StringTools.replace(StringTools.trim(assetRoot), '\\', '/');
		if (spec == null || cleanRoot == ''
			|| !cleanRoot.startsWith(CompatScriptManifest.ROOT_PREFIX + '/')) {
			trace('[hxc-pause-fallback] invalid pause spec or manifest root; native pause menu retained.');
			return false;
		}
		if (spec.requiredAssets != null)
			for (asset in spec.requiredAssets)
				if (HxcStateAssetScope.scopedAssetPath(cleanRoot, asset) == null) {
					trace('[hxc-pause-fallback] missing scoped pause asset ' + asset + '; native pause menu retained.');
					return false;
				}

		// Re-applying the same spec is safe and never leaves a previous object graph
		// or hidden menu entry alive.
		hxcClearPauseOverlay();
		hxcPauseSpec = spec;
		hxcPauseRoot = cleanRoot;
		hxcNativeSongText = songNameTxt.text;
		hxcNativeDeathsText = deathsTxt.text;
		hxcNativeSongFont = songNameTxt.font;
		hxcNativeDeathsFont = deathsTxt.font;
		hxcNativeDiffVisible = curDiffTxt.visible;
		hxcNativeDeathsVisible = deathsTxt.visible;
		try {
			var titleFont = hxcPauseFontPath(cleanRoot, spec.titleFont);
			var menuFont = hxcPauseFontPath(cleanRoot, spec.menuFont);
			var textSize = spec.fontSize == null ? 32 : spec.fontSize;
			var menuSize = spec.menuFontSize == null ? 27 : spec.menuFontSize;
			if (titleFont != null) {
				songNameTxt.font = titleFont;
				deathsTxt.font = titleFont;
			}
			songNameTxt.size = textSize;
			songNameTxt.text = spec.titleLabel == null || spec.titleLabel == ''
				? PlayState.SONG.song : spec.titleLabel + ' ' + PlayState.SONG.song;
			songNameTxt.alignment = RIGHT;
			curDiffTxt.visible = false;
			if (spec.deathLabel != null && spec.deathLabel != '')
				deathsTxt.text = spec.deathLabel + PlayState.balls;
			deathsTxt.size = textSize;
			deathsTxt.alignment = RIGHT;

			if (spec.practiceLabel != null && spec.practiceLabel != '') {
				hxcPracticeText = new FlxText(0, 125, FlxG.width - 10, spec.practiceLabel, textSize);
				hxcPracticeText.alignment = RIGHT;
				if (titleFont != null)
					hxcPracticeText.font = titleFont;
				hxcPracticeText.color = FlxColor.WHITE;
				hxcPracticeText.setBorderStyle(FlxTextBorderStyle.OUTLINE, FlxColor.BLACK, 1);
				hxcPracticeText.visible = PlayState.instance != null && PlayState.instance.practiceMode;
				hxcPracticeText.cameras = cameras;
				add(hxcPracticeText);
				hxcPauseObjects.push(hxcPracticeText);
			}

			var logoPath = hxcPauseImagePath(cleanRoot, spec.logo);
			if (logoPath != null) {
				var logo = new FlxSprite(-260, 0).loadGraphic(FNFAssets.getBitmapData(logoPath));
				logo.scrollFactor.set();
				logo.cameras = cameras;
				add(logo);
				hxcPauseObjects.push(logo);
			}

			var atlas = HxcStateAssetScope.sparrowAtlas(cleanRoot, spec.atlas, null,
				'HXC pause overlay');
			if (atlas == null)
				throw 'scoped pause atlas could not be loaded';
			var logoBl = new FlxSprite(-160, -45);
			logoBl.frames = atlas;
			logoBl.scale.set(0.5, 0.5);
			logoBl.animation.addByPrefix('hxc-logo',
				spec.logoAnimation == null || spec.logoAnimation == '' ? 'logo bumpin' : spec.logoAnimation,
				24, true);
			logoBl.animation.play('hxc-logo');
			logoBl.updateHitbox();
			logoBl.scrollFactor.set();
			logoBl.cameras = cameras;
			add(logoBl);
			hxcPauseObjects.push(logoBl);

			// Dynamic character art is optional.  It is resolved from the current
			// chart's generic opponent field and can never escape the manifest root.
			var opponent = PlayState.SONG.player2;
			var artPath = hxcPauseImagePath(cleanRoot,
				(spec.artPrefix == null ? '' : spec.artPrefix) + opponent);
			if (artPath != null) {
				var pauseArt = new FlxSprite(FlxG.width, 0).loadGraphic(FNFAssets.getBitmapData(artPath));
				pauseArt.scrollFactor.set();
				pauseArt.cameras = cameras;
				add(pauseArt);
				hxcPauseObjects.push(pauseArt);
			} else {
				trace('[hxc-pause-fallback] optional scoped pause art unavailable for chart opponent; stock art retained.');
			}
			hxcApplyMenuPresentation();
			hxcPauseApplied = true;
			return true;
		} catch (error:Dynamic) {
			trace('[hxc-pause-fallback] scoped pause construction failed: ' + Std.string(error));
			hxcClearPauseOverlay();
			return false;
		}
	}

	/** Clear imported objects, restore stock text/menu state, and remain idempotent. */
	public function hxcClearPauseOverlay():Bool {
		if (hxcPauseObjects != null)
			for (object in hxcPauseObjects.copy()) {
				if (object == null)
					continue;
				try {
					remove(cast object, true);
					if (Std.isOfType(object, FlxSprite))
						(cast object:FlxSprite).destroy();
				} catch (_:Dynamic) {}
			}
		hxcPauseObjects.resize(0);
		if (hxcPauseApplied || hxcPauseSpec != null) {
			songNameTxt.text = hxcNativeSongText == null ? songNameTxt.text : hxcNativeSongText;
			deathsTxt.text = hxcNativeDeathsText == null ? deathsTxt.text : hxcNativeDeathsText;
			if (hxcNativeSongFont != null)
				songNameTxt.font = hxcNativeSongFont;
			if (hxcNativeDeathsFont != null)
				deathsTxt.font = hxcNativeDeathsFont;
			curDiffTxt.visible = hxcNativeDiffVisible;
			deathsTxt.visible = hxcNativeDeathsVisible;
		}
		for (index in 0...grpMenuShit.length) {
			var item = grpMenuShit.members[index];
			if (item == null)
				continue;
			item.visible = true;
			if (index < hxcNativeItemColors.length)
				item.color = hxcNativeItemColors[index];
		}
		hxcHiddenMenuIndices.resize(0);
		hxcNativeItemColors.resize(0);
		hxcPauseSpec = null;
		hxcPauseRoot = '';
		hxcPracticeText = null;
		hxcPauseApplied = false;
		return true;
	}

	function hxcApplyMenuPresentation():Void {
		if (hxcPauseSpec == null || grpMenuShit == null)
			return;
		hxcHiddenMenuIndices.resize(0);
		hxcNativeItemColors.resize(0);
		var hidden = hxcPauseSpec.hiddenLabels == null ? [] : hxcPauseSpec.hiddenLabels;
		for (index in 0...grpMenuShit.length) {
			var item = grpMenuShit.members[index];
			if (item == null)
				continue;
			hxcNativeItemColors.push(item.color);
			if (hidden.indexOf(item.text) >= 0) {
				item.visible = false;
				hxcHiddenMenuIndices.push(index);
			} else {
				item.visible = true;
				item.color = hxcPauseSpec.itemColor == null ? FlxColor.WHITE : hxcPauseSpec.itemColor;
			}
		}
		changeSelection();
	}

	function hxcPauseImagePath(root:String, key:String):String {
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

	function hxcPauseFontPath(root:String, key:String):String {
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

	override function update(elapsed:Float) {
		if (pauseMusic.volume < 0.5)
			pauseMusic.volume += 0.01 * elapsed;

		super.update(elapsed);
		if (codenamePauseRuntime != null)
			codenamePauseRuntime.update(elapsed);
		if (codenamePauseCancelled)
			return;

		var upP = controls.UP_MENU;
		var downP = controls.DOWN_MENU;
		var accepted = controls.ACCEPT;

		if (upP)
			changeSelection(-1);
		if (downP)
			changeSelection(1);

		if (accepted) {
			if (!inDiffs) {
				var daSelected:String = menuItems[curSelected];

				switch (daSelected) {
					case "Resume":
						close();
					case "Restart Song":
						FlxG.resetState();
					case "Replay Cutscene":
						PlayState.watchedCutscene = false;
						FlxG.resetState();
					case "Charting":
						LoadingState.loadAndSwitchState(new ChartingState());
					case "Exit to menu":
						if (PlayState.isStoryMode)
							LoadingState.loadAndSwitchState(new StoryMenuState());
						else
							LoadingState.loadAndSwitchState(new FreeplayState());
					case "Change Modifiers":
						LoadingState.loadAndSwitchState(new ModifierState());
					case "Change Options":
						SaveDataState.prevPath = 'freeplay';
						LoadingState.loadAndSwitchState(new SaveDataState());
					case "Change Difficulty":
						// Imported songs can be registered after the initial difficulty
						// scan.  Always use the null-safe lazy resolver so a song with no
						// support entry cannot crash while opening the pause menu.
						diffs = DifficultyManager.getSupportedDiffs(PlayState.SONG.song);
						diffNames = ["Back"];
						for (diff in diffs) {
							diffNames.push(DifficultyManager.getDiffName(diff).toUpperCase());
						}
						inDiffs = true;
						makeMenuItems(diffNames);
						curSelected = 0;
						changeSelection();
				}
			} else {
				var daSelected:String = diffNames[curSelected];

				if (daSelected == 'Back') {
					makeMenuItems(menuItems);
					inDiffs = false;
					curSelected = 0;
					changeSelection();
				} else {
					PlayState.SONG = daSelected.toLowerCase() == 'normal'
						? Song.loadFromJson(PlayState.SONG.song.toLowerCase(), PlayState.SONG.song.toLowerCase())
						: Song.loadFromJson(PlayState.SONG.song.toLowerCase() + '-' + daSelected.toLowerCase(), PlayState.SONG.song.toLowerCase());
					PlayState.storyDifficulty = diffs[curSelected - 1];
					FlxG.resetState();
				}
			}
		}

		if (FlxG.keys.justPressed.J) {
			// for reference later!
			// PlayerSettings.player1.controls.replaceBinding(Control.LEFT, Keys, FlxKey.J, null);
		}
	}

	override function destroy() {
		if (codenamePauseRuntime != null) {
			codenamePauseRuntime.destroy();
			codenamePauseRuntime = null;
		}
		hxcClearPauseOverlay();
		FlxG.sound.list.remove(pauseMusic);
		pauseMusic.destroy();

		super.destroy();
		if (pauseCamera != null) {
			if (FlxG.cameras.list.indexOf(pauseCamera) >= 0)
				FlxG.cameras.remove(pauseCamera, true);
			pauseCamera = null;
		}
	}

	function changeSelection(change:Int = 0):Void {
		if (grpMenuShit == null || grpMenuShit.length == 0)
			return;
		curSelected += change;

		if (curSelected < 0)
			curSelected = grpMenuShit.length - 1;
		if (curSelected >= grpMenuShit.length)
			curSelected = 0;
		var guard = 0;
		while (hxcHiddenMenuIndices.indexOf(curSelected) >= 0 && guard++ < grpMenuShit.length) {
			curSelected += change == 0 ? 1 : change;
			if (curSelected < 0)
				curSelected = grpMenuShit.length - 1;
			if (curSelected >= grpMenuShit.length)
				curSelected = 0;
		}

		var bullShit:Int = 0;

		for (index in 0...grpMenuShit.members.length) {
			var item = grpMenuShit.members[index];
			if (item == null)
				continue;
			item.targetY = bullShit - curSelected;
			bullShit++;

			item.alpha = 0.6;
			if (hxcPauseSpec != null) {
				item.visible = hxcHiddenMenuIndices.indexOf(index) < 0;
				item.color = index == curSelected
					? (hxcPauseSpec.selectedColor == null ? FlxColor.WHITE : hxcPauseSpec.selectedColor)
					: (hxcPauseSpec.itemColor == null ? FlxColor.WHITE : hxcPauseSpec.itemColor);
			}
			// item.setGraphicSize(Std.int(item.width * 0.8));

			if (item.targetY == 0) {
				item.alpha = 1;
				// item.setGraphicSize(Std.int(item.width));
			}
		}
	}
}
