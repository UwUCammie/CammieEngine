package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.group.FlxGroup;
import flixel.util.FlxAxes;
import flixel.util.FlxColor;
import flixel.util.FlxDestroyUtil;
import flixel.util.FlxTimer;

/** Native implementation of the pinned Nightmare Vision TitleState. */
@:keep
class NightmareVisionTitleState extends NightmareVisionMusicBeatState {
	static final logoAtlas:String = 'menus/title/logoBumpin';
	static final girlfriendAtlas:String = 'menus/title/gfDanceTitle';
	static final titleAtlas:String = 'menus/title/titleEnter';
	static final newgroundsImage:String = 'menus/title/newgrounds_logo';
	static final alphabetAtlas:String = 'alphabet';

	final session:NightmareVisionStateSession;
	final alphabetContext:NightmareVisionAlphabetContext;
	final assets:NightmareVisionFunkinAssets;
	var skippedIntro:Bool = false;
	var transitioning:Bool = false;
	var introEndingText:Array<String> = ['FRIDAY', 'NIGHT', 'FUNKIN'];
	var randomIntroText:Array<String> = [];
	var textGroup:Null<FlxGroup>;
	var ngSpr:Null<FlxSprite>;
	var logo:Null<FlxSprite>;
	var gfDance:Null<FlxSprite>;
	var titleText:Null<FlxSprite>;
	var swagShader:Null<NightmareVisionColorSwap>;
	var danceLeft:Bool = false;
	var sickBeats:Int = 0;
	var alphabetAtlasChecked:Bool = false;

	public function new(session:NightmareVisionStateSession) {
		if (session == null) throw '[nightmare-vision-title] Missing captured source session';
		super(session.stateHost());
		this.session = session;
		var paths = session.paths;
		assets = new NightmareVisionFunkinAssets(paths);
		var alphabetOwner:NightmareVisionAlphabetOwner = {
			atlas:function(name:String):FlxAtlasFrames return paths.getSparrowAtlas(name),
			spriteOwner:NightmareVisionSpriteRegistry.capture(paths)
		};
		alphabetContext = NightmareVisionAlphabetRegistry.get(paths.root, alphabetOwner);
	}

	/** Match TitleState.create ordering: init, intro text choice, state onLoad,
		intro callbacks and visuals, then MusicBeatState.create/onStateCreate. */
	public override function create():Void {
		session.titleInit();
		var choices = getIntroText();
		randomIntroText = choices.length == 0 ? [] : FlxG.random.getObject(choices);
		initStateScript('TitleState');
		startIntro();
		super.create();
		persistentUpdate = true;
		FlxG.mouse.visible = false;
	}

	function startIntro():Void {
		if (!titleInitialized()) playMenuMusic(0);

		Conductor.changeBPM(102);
		if (scriptGroup.call('onStartIntro', []) != NightmareVisionScriptGroup.STOP_FUNC)
			makeBaseTitle();

		if (titleInitialized()) skipIntro();
		else setTitleInitialized(true);

		scriptGroup.call('onCreatePost', []);
	}

	function makeBaseTitle():Void {
		var logoFrames = requireAtlas(logoAtlas);
		var girlfriendFrames = requireAtlas(girlfriendAtlas);
		var enterFrames = requireAtlas(titleAtlas);
		requireImage(newgroundsImage);

		swagShader = new NightmareVisionColorSwap();

		logo = new FlxSprite(-150, -100);
		logo.frames = logoFrames;
		logo.animation.addByPrefix('bump', 'logo bumpin', 24, false);
		logo.animation.play('bump');
		logo.updateHitbox();
		add(logo);
		logo.shader = swagShader.shader;

		gfDance = new FlxSprite(512, 40);
		gfDance.frames = girlfriendFrames;
		gfDance.animation.addByIndices('danceLeft', 'gfDance', [30, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14], '', 24, false);
		gfDance.animation.addByIndices('danceRight', 'gfDance', [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29], '', 24, false);
		add(gfDance);
		gfDance.shader = swagShader.shader;

		titleText = new FlxSprite(100, 576);
		titleText.frames = enterFrames;
		titleText.animation.addByPrefix('idle', 'Press Enter to Begin', 24);
		titleText.animation.addByPrefix('press', 'ENTER PRESSED', 24);
		titleText.animation.play('idle');
		titleText.updateHitbox();
		add(titleText);

		textGroup = new FlxGroup();
		add(textGroup);

		ngSpr = new FlxSprite(0, FlxG.height * 0.52, session.paths.image(newgroundsImage));
		add(ngSpr);
		ngSpr.visible = false;
		ngSpr.scale.set(0.8, 0.8);
		ngSpr.updateHitbox();
		ngSpr.screenCenter(FlxAxes.X);

		logo.alpha = 0.001;
		gfDance.alpha = 0.001;
		titleText.alpha = 0.001;
	}

	function requireAtlas(key:String):FlxAtlasFrames {
		requireImage(key);
		var metadataFound = false;
		for (extension in ['xml', 'json', 'txt']) {
			if (sourceFileExists('images/' + key + '.' + extension)) {
				metadataFound = true;
				break;
			}
		}
		if (!metadataFound) missingTitleAsset('images/' + key + ' atlas metadata');
		var frames = session.paths.getAtlasFrames(key);
		if (frames == null) missingTitleAsset('images/' + key + ' decoded atlas');
		return frames;
	}

	function requireImage(key:String):Void {
		var relative = 'images/' + key + '.png';
		var path = session.paths.getPath(relative, null, true);
		if (!session.paths.exists(path) || session.paths.isDirectory(path)
			|| assets.getGraphicUnsafe(path) == null)
			missingTitleAsset(relative);
	}

	function sourceFileExists(relative:String):Bool {
		var path = session.paths.getPath(relative, null, true);
		return session.paths.exists(path) && !session.paths.isDirectory(path);
	}

	function missingTitleAsset(asset:String):Void {
		var message = '[nightmare-vision-title-asset-missing] Required source title asset is unavailable in the selected package or its captured core: ' + asset;
		sourceHost.report('TitleState', 'assets', message);
		throw message;
	}

	function playMenuMusic(volume:Float):Void {
		requireSound('music/freakyMenu');
		FlxG.sound.playMusic(session.paths.music('freakyMenu'), volume);
	}

	function playConfirmSound():Void {
		requireSound('sounds/confirmMenu');
		FlxG.sound.play(session.paths.sound('confirmMenu'), 0.7);
	}

	function requireSound(relativeBase:String):Void {
		var path = session.paths.findFileWithExts(relativeBase, ['ogg', 'wav'], null, true);
		if (!session.paths.exists(path) || session.paths.isDirectory(path)
			|| assets.getSoundUnsafe(path) == null)
			missingTitleAsset(relativeBase);
	}

	function getIntroText():Array<Array<String>> {
		var path = session.paths.getPath('data/introText.txt', null, true);
		if (!session.paths.exists(path)) return [];
		var fullText = session.paths.getTextFromFile('data/introText.txt', null, true);
		var result:Array<Array<String>> = [];
		for (line in fullText.split('\n')) result.push(line.split('--'));
		return result;
	}

	function randomText(index:Int):Null<String> {
		return randomIntroText != null && index >= 0 && index < randomIntroText.length
			? randomIntroText[index] : null;
	}

	public override function update(elapsed:Float):Void {
		if (FlxG.sound.music != null) Conductor.songPosition = FlxG.sound.music.time;

		if (FlxG.keys.justPressed.F) FlxG.fullscreen = !FlxG.fullscreen;

		var pressedEnter = FlxG.keys.justPressed.ENTER || controls.ACCEPT;
		var gamepad = FlxG.gamepads.lastActive;
		if (gamepad != null && gamepad.justPressed.START) pressedEnter = true;

		if (skippedIntro) {
			if (pressedEnter && scriptGroup.call('onEnter', []) != NightmareVisionScriptGroup.STOP_FUNC && !transitioning) {
				var flash = session.prefs.view.flashing ? FlxColor.WHITE : cast 0x4CFFFFFF;
				FlxG.camera.flash(flash, 1);
				transitioning = true;
				if (titleText != null) titleText.animation.play('press');
				playConfirmSound();
				new FlxTimer().start(1, function(_):Void {
					requestMainMenu();
				});
			} else if (pressedEnter && transitioning) {
				session.setTransSkip(true, false);
				requestMainMenu();
			}
		}

		if (pressedEnter && !skippedIntro) skipIntro();
		if (swagShader != null) {
			if (controls.UI_LEFT) swagShader.hue -= elapsed * 0.1;
			if (controls.UI_RIGHT) swagShader.hue += elapsed * 0.1;
		}

		super.update(elapsed);
	}

	function requestMainMenu():Void {
		var factory = sourceHost.createStateFactory('MainMenuState');
		if (factory == null) {
			var message = '[nightmare-vision-title-transition] No source MainMenuState factory is available';
			sourceHost.report('TitleState', 'onEnter', message);
			throw message;
		}
		session.switchState(factory);
		setTitleClosedState(true);
	}

	function createCoolText(textArray:Array<String>, offset:Float = 0):Void {
		if (textGroup == null) return;
		for (index in 0...textArray.length) {
			var text = makeAlphabet(textArray[index]);
			text.screenCenter(FlxAxes.X);
			text.y += (index * 60) + 200 + offset;
			textGroup.add(text);
		}
	}

	function addMoreText(text:String, offset:Float = 0):Void {
		if (textGroup == null) return;
		var coolText = makeAlphabet(text);
		coolText.screenCenter(FlxAxes.X);
		coolText.y += (textGroup.length * 60) + 200 + offset;
		textGroup.add(coolText);
	}

	function makeAlphabet(text:String):NightmareVisionAlphabet {
		if (!alphabetAtlasChecked) {
			requireAtlas(alphabetAtlas);
			alphabetAtlasChecked = true;
		}
		return new NightmareVisionAlphabet(0, 0, text, true, 1, alphabetContext);
	}

	function deleteCoolText():Void {
		if (textGroup == null || textGroup.members.length == 0) return;
		while (textGroup.members.length > 0) {
			var text = textGroup.members[0];
			textGroup.remove(text, true);
			FlxDestroyUtil.destroy(text);
		}
	}

	public override function beatHit():Void {
		super.beatHit();
		if (!titleClosedState()) {
			sickBeats++;
			scriptGroup.set('curBeat', sickBeats);
		}

		if (logo != null) logo.animation.play('bump', true);
		if (gfDance != null) {
			danceLeft = !danceLeft;
			gfDance.animation.play(danceLeft ? 'danceRight' : 'danceLeft');
		}

		if (!titleClosedState()) {
			switch (sickBeats) {
				case 1:
					playMenuMusic(0);
					if (FlxG.sound.music != null) FlxG.sound.music.fadeIn(4, 0, 0.7);
				case 2:
					createCoolText(['ninjamuffin99', 'phantomArcade', 'kawaisprite', 'evilsk8er']);
				case 4:
					addMoreText('present');
				case 5:
					deleteCoolText();
				case 6:
					createCoolText(['In association', 'with'], -40);
				case 8:
					addMoreText('newgrounds', -40);
					if (ngSpr != null) ngSpr.visible = true;
				case 9:
					deleteCoolText();
					if (ngSpr != null) ngSpr.visible = false;
				case 10:
					var first = randomText(0);
					if (first != null) createCoolText([first]);
				case 12:
					var second = randomText(1);
					if (second != null) addMoreText(second);
				case 13:
					deleteCoolText();
				case 14:
					var first = endingText(0);
					if (first != null) addMoreText(first);
				case 15:
					var second = endingText(1);
					if (second != null) addMoreText(second);
				case 16:
					var third = endingText(2);
					if (third != null) addMoreText(third);
				case 17:
					skipIntro();
			}
		}
	}

	public function skipIntro():Void {
		if (scriptGroup.call('onSkipIntro', []) != NightmareVisionScriptGroup.STOP_FUNC && !skippedIntro) {
			if (ngSpr != null) ngSpr.kill();
			if (textGroup != null) textGroup.kill();
			if (logo != null) logo.alpha = 1;
			if (gfDance != null) gfDance.alpha = 1;
			if (titleText != null) titleText.alpha = 1;
			FlxG.camera.flash(FlxColor.WHITE, 4);
			skippedIntro = true;
		}
	}

	inline function titleInitialized():Bool {
		return sourceHost.getTitleInitialized == null ? session.titleInitialized : sourceHost.getTitleInitialized();
	}

	inline function endingText(index:Int):Null<String> {
		return introEndingText != null && index >= 0 && index < introEndingText.length
			? introEndingText[index] : null;
	}

	inline function setTitleInitialized(value:Bool):Void {
		if (sourceHost.setTitleInitialized != null) sourceHost.setTitleInitialized(value);
		else session.titleInitialized = value;
	}

	inline function titleClosedState():Bool {
		return sourceHost.getTitleClosedState == null ? session.titleClosedState : sourceHost.getTitleClosedState();
	}

	inline function setTitleClosedState(value:Bool):Void {
		if (sourceHost.setTitleClosedState != null) sourceHost.setTitleClosedState(value);
		else session.titleClosedState = value;
	}
}
