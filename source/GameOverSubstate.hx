package;

import flixel.FlxG;
import flixel.FlxObject;
import flixel.FlxSprite;
import flixel.FlxSubState;
import flixel.sound.FlxSound;
import flixel.animation.FlxAnimation;
import flixel.math.FlxPoint;
import flixel.tweens.FlxTween;
import flixel.util.FlxColor;
import flixel.util.FlxTimer;
import lime.system.System;
import lime.utils.Assets;
#if sys
import sys.io.File;
import sys.FileSystem;
import haxe.io.Path;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import flash.media.Sound;
#end
import haxe.Json;
import tjson.TJSON;
using StringTools;
class GameOverSubstate extends MusicBeatSubstate {
	/** HXC/V-Slice compatibility settings; values are owned by the central adapter. */
	public static var musicSuffix(get, set):String;
	static function get_musicSuffix():String
		return HxcCompatRuntime.gameOverMusicSuffix;
	static function set_musicSuffix(value:String):String
		return HxcCompatRuntime.setGameOverMusicSuffix(value);
	public static var blueBallSuffix(get, set):String;
	static function get_blueBallSuffix():String
		return HxcCompatRuntime.gameOverBlueBallSuffix;
	static function set_blueBallSuffix(value:String):String
		return HxcCompatRuntime.setGameOverBlueBallSuffix(value);
	public static var instance(default, null):GameOverSubstate;

	var bf:Character;
	@:keep public var boyfriend(get, set):Character;
	function get_boyfriend():Character return bf;
	function set_boyfriend(value:Character):Character {
		bf = value;
		return value;
	}
	@:keep public var camFollow:FlxObject;
	@:keep public var gameoverStarted:Bool = false;
	@:keep public var startedDeath:Bool = false;
	@:keep public var isEnding:Bool = false;
	var sourceOwner:PlayState;
	var sourceMode:Int = 0;
	var sourceStartStopped:Bool = false;
	var sourceDeathAnimNotified:Bool = false;
	var quoteCharacter:Character;
	var deathQuotePlayback:HxcDeathQuotePlayback;
	var deathQuoteAttempted:Bool = false;
	var gameoverLoopMusic:FlxSound;
	/**
		Handles returned to imported HXC death hooks.  The substate owns this
		collection so generated scripts cannot add arbitrary native objects or
		leave an atlas-backed sprite alive after game-over teardown.
	*/
	public var mustNotExit:Bool = false;
	var hxcDeathOverlays:Array<FlxSprite> = [];
	var codenameGameOverRuntime:CodenameModSubStateRuntime;
	var codenameGameOverCancelled:Bool = false;

	public function new(player:Character) {
		var activePlayState = PlayState.instance;
		var activeSourceMode = activePlayState == null ? 0 : activePlayState.sourceGameOverMode();
		if (activeSourceMode == 0) instance = this;
		sourceOwner = activeSourceMode == 0 ? null : activePlayState;
		sourceMode = activeSourceMode;
		quoteCharacter = player;
		var psychCharacter = activePlayState == null ? null : activePlayState.psychGameOverCharacterName();
		var daBf:String = psychCharacter == null ? player.curCharacter + '-dead' : psychCharacter;
		trace(player.curCharacter);
		super();
		if (sourceMode != 0) return;
		setupDefaultGameOver(player, daBf);
	}

	function setupDefaultGameOver(player:Character, daBf:String, resetSongPosition:Bool = true):Void {
		if (resetSongPosition) Conductor.songPosition = 0;
		var playState = sourceOwner == null ? PlayState.instance : sourceOwner;

		// Imported characters may ship no usable death variant (missing sheet or
		// a generated init that assumes one). A broken death actor must degrade
		// to the living sheet - which donor atlases usually keep the death
		// animations on - instead of crashing game over for the whole song.
		try {
			bf = new Character(player.x - player.playerOffsetX, player.y - player.playerOffsetY, daBf, true);
		} catch (error:Dynamic) {
			trace('[gameover-character-fallback] ' + daBf + ': ' + Std.string(error));
			bf = new Character(player.x - player.playerOffsetX, player.y - player.playerOffsetY,
				player.curCharacter, true);
		}
		bf.x += bf.playerOffsetX;
		bf.y += bf.playerOffsetY;
		bf.beingControlled = true;
		add(bf);

		camFollow = new FlxObject(bf.getGraphicMidpoint().x + bf.deathCameraOffsetX,
			bf.getGraphicMidpoint().y + bf.deathCameraOffsetY, 1, 1);
		add(camFollow);
		if (codenameInitGameOverScript()) {
			bf.visible = false;
			return;
		}
		// Keep native display ownership while routing authored animation
		// overrides (including costume death atlases) to this death actor.
		HxcCompatRuntime.bindGameOverCharacter(bf);
		initDeathQuotePlayback();
		if (bf.deathCameraZoom > 0)
			FlxG.camera.zoom = bf.deathCameraZoom;
		var psychDeathSound = playState == null ? null
			: playState.psychGameOverSoundPath('deathSoundName', true);
		if (psychDeathSound != null)
			FlxG.sound.play(FNFAssets.getSound(psychDeathSound));
		else {
			if (!FNFAssets.exists('assets/sounds/${bf.deathSound}'))
				bf.deathSound = 'fnf_loss_sfx.ogg';
			if (bf.deathSound == 'fnf_loss_sfx.ogg')
				bf.deathSound = HxcCompatRuntime.resolveBlueBallTrack(bf.deathSound,
					'assets/sounds', bf.isPixel);
			FlxG.sound.play(FNFAssets.getSound('assets/sounds/' + bf.deathSound));
		}
		Conductor.changeBPM(100);

		FlxG.camera.focusOn(playState.camFollow.getPosition());
		FlxG.camera.target = null;

		if (bf.animation.exists('firstDeath'))
			bf.playAnim('firstDeath');
		else { // backup if the player character has no death animation
			new FlxTimer().start(0.6, function(tmr:FlxTimer) { FlxG.camera.follow(camFollow, LOCKON, 0.01); });
			new FlxTimer().start(2.1, function(tmr:FlxTimer) {
				if (!isEnding && !gameoverStarted) {
					gameoverStarted = true;
					playGameoverMusic();
				}
			});
		}
	}

	override function create():Void {
		if (sourceMode == 0) {
			super.create();
			return;
		}

		instance = this;
		if (sourceMode == 2) {
			sourceOwner.sourceGameOverSetInGameOver(true);
			Conductor.songPosition = 0;
			var startResult = sourceOwner.sourceGameOverCall('onGameOverStart', []);
			sourceStartStopped = startResult == NightmareVisionScriptGroup.STOP_FUNC;
			if (!sourceStartStopped)
				setupDefaultGameOver(quoteCharacter, sourceDeathCharacterName(), false);
			super.create();
			sourceOwner.sourceGameOverCall('onGameOverPost', []);
			return;
		}

		setupDefaultGameOver(quoteCharacter, sourceDeathCharacterName());
		sourceOwner.sourceGameOverSetInGameOver(true);
		sourceOwner.sourceGameOverCall('onGameOverStart', []);
		super.create();
	}

	function sourceDeathCharacterName():String {
		var psychCharacter = sourceOwner == null ? null : sourceOwner.psychGameOverCharacterName();
		return psychCharacter == null ? quoteCharacter.curCharacter + '-dead' : psychCharacter;
	}

	/** Run only the game-over module belonging to the explicitly active owner. */
	function codenameInitGameOverScript():Bool {
		var owner = CodenameModRuntime.activeRoot();
		var path = 'data/scripts/jump.hx';
		if (!CodenameModSubStateRuntime.hasScript(owner, path)) return false;
		codenameGameOverRuntime = new CodenameModSubStateRuntime(this, owner, path, 'gameover');
		var event = new CodenameGameEvent();
		codenameGameOverCancelled = codenameGameOverRuntime.create(event);
		return codenameGameOverCancelled;
	}

	/**
		Apply a bounded imported-HXC game-over character hand-off.  The donor module
		reaches into a V-Slice GameOverSubState object and copies stage metadata;
		imported HScript is not given that object graph.  Keep the native substate
		as the sole owner of its boyfriend actor, camera target, and display list.
		Only fields already represented by StageHelper.bfInfo are copied.
	*/
	public function hxcApplyImportedGameOverCharacter(replacement:Character,
		stage:Dynamic, assetRoot:Dynamic):Bool {
		if (replacement == null || !HxcCompatRuntime.isImportedManifestRoot(assetRoot))
			return false;
		if (bf != null && bf != replacement) {
			remove(bf);
			bf.destroy();
		}
		replacement.isPlayer = true;
		replacement.beingControlled = true;
		replacement.flipX = !replacement.getDataFlipX();

		var info:Dynamic = stage == null ? null : Reflect.field(stage, 'bfInfo');
		var focusOffsetX:Float = 0;
		var focusOffsetY:Float = 0;
		if (info != null) {
			var x:Dynamic = Reflect.field(info, 'x');
			var y:Dynamic = Reflect.field(info, 'y');
			if (x != null) replacement.x = Std.parseFloat(Std.string(x));
			if (y != null) replacement.y = Std.parseFloat(Std.string(y));
			var camOffsetX:Dynamic = Reflect.field(info, 'camOffsetX');
			var camOffsetY:Dynamic = Reflect.field(info, 'camOffsetY');
			if (camOffsetX != null) focusOffsetX = Std.parseFloat(Std.string(camOffsetX));
			if (camOffsetY != null) focusOffsetY = Std.parseFloat(Std.string(camOffsetY));
			var scroll:Dynamic = Reflect.field(info, 'scrollFactor');
			if (scroll != null) {
				var scrollX:Dynamic = Reflect.field(scroll, 'x');
				var scrollY:Dynamic = Reflect.field(scroll, 'y');
				if (scrollX != null) replacement.scrollFactor.x = Std.parseFloat(Std.string(scrollX));
				if (scrollY != null) replacement.scrollFactor.y = Std.parseFloat(Std.string(scrollY));
			}
			var zIndex:Dynamic = Reflect.field(info, 'zIndex');
			if (zIndex != null) Reflect.setField(replacement, 'zIndex', Std.int(Std.parseFloat(Std.string(zIndex))));
		}

		bf = replacement;
		HxcCompatRuntime.bindGameOverCharacter(replacement);
		add(bf);
		if (camFollow != null) {
			camFollow.setPosition(bf.getGraphicMidpoint().x + bf.deathCameraOffsetX + focusOffsetX,
				bf.getGraphicMidpoint().y + bf.deathCameraOffsetY + focusOffsetY);
			FlxG.camera.focusOn(camFollow.getPosition());
		}
		if (bf.animation != null && bf.animation.exists('firstDeath'))
			bf.playAnim('firstDeath');
		else if (bf.animation != null && bf.animation.exists('deathLoop'))
			bf.playAnim('deathLoop');
		return true;
	}

	/** Create one manifest-scoped Sparrow overlay owned by this substate. */
	public function hxcCreateDeathOverlay(assetRoot:String, assetPath:String):Dynamic {
		if (assetRoot == null || StringTools.trim(assetRoot) == ''
			|| assetPath == null || StringTools.trim(assetPath) == '')
			return null;
		var frames = HxcStateAssetScope.sparrowAtlas(assetRoot, assetPath, null,
			'HXC game-over death overlay');
		if (frames == null)
			return null;
		var sprite = new FlxSprite();
		sprite.frames = frames;
		sprite.scrollFactor.set();
		hxcDeathOverlays.push(sprite);
		return sprite;
	}

	function hxcOwnsDeathOverlay(value:Dynamic):Bool {
		return value != null && Std.isOfType(value, FlxSprite)
			&& hxcDeathOverlays.indexOf(cast value) >= 0;
	}

	/** Add only a handle previously returned by hxcCreateDeathOverlay. */
	public function hxcAddDeathOverlay(value:Dynamic):Bool {
		if (!hxcOwnsDeathOverlay(value))
			return false;
		var sprite:FlxSprite = cast value;
		if (members == null || members.indexOf(sprite) < 0)
			add(sprite);
		return true;
	}

	public function hxcSetDeathOverlayAlpha(value:Dynamic, alpha:Dynamic):Bool {
		if (!hxcOwnsDeathOverlay(value))
			return false;
		(cast value:FlxSprite).alpha = Std.parseFloat(Std.string(alpha));
		return true;
	}

	public function hxcSetDeathOverlayVisible(value:Dynamic, visible:Dynamic):Bool {
		if (!hxcOwnsDeathOverlay(value))
			return false;
		(cast value:FlxSprite).visible = visible == true;
		return true;
	}

	public function hxcSetDeathOverlayPosition(value:Dynamic, x:Dynamic, y:Dynamic):Bool {
		if (!hxcOwnsDeathOverlay(value))
			return false;
		var sprite:FlxSprite = cast value;
		sprite.setPosition(Std.parseFloat(Std.string(x)), Std.parseFloat(Std.string(y)));
		return true;
	}

	public function hxcSetDeathOverlayX(value:Dynamic, x:Dynamic):Bool {
		if (!hxcOwnsDeathOverlay(value))
			return false;
		(cast value:FlxSprite).x = Std.parseFloat(Std.string(x));
		return true;
	}

	public function hxcSetDeathOverlayY(value:Dynamic, y:Dynamic):Bool {
		if (!hxcOwnsDeathOverlay(value))
			return false;
		(cast value:FlxSprite).y = Std.parseFloat(Std.string(y));
		return true;
	}

	public function hxcOffsetDeathOverlay(value:Dynamic, x:Dynamic, y:Dynamic):Bool {
		if (!hxcOwnsDeathOverlay(value))
			return false;
		var sprite:FlxSprite = cast value;
		sprite.x += Std.parseFloat(Std.string(x));
		sprite.y += Std.parseFloat(Std.string(y));
		return true;
	}

	public function hxcCenterDeathOverlay(value:Dynamic):Bool {
		if (!hxcOwnsDeathOverlay(value))
			return false;
		(cast value:FlxSprite).screenCenter();
		return true;
	}

	public function hxcAddDeathOverlayAnimation(value:Dynamic, name:String, prefix:String,
		fps:Dynamic, looped:Dynamic):Bool {
		if (!hxcOwnsDeathOverlay(value) || name == null || prefix == null)
			return false;
		var frameRate = Std.parseFloat(Std.string(fps));
		if (Math.isNaN(frameRate) || frameRate <= 0)
			frameRate = 24;
		(cast value:FlxSprite).animation.addByPrefix(name, prefix, frameRate, looped == true);
		return true;
	}

	public function hxcPlayDeathOverlayAnimation(value:Dynamic, name:String):Bool {
		if (!hxcOwnsDeathOverlay(value) || name == null)
			return false;
		(cast value:FlxSprite).animation.play(name);
		return true;
	}

	public function hxcTweenCameraToDeathOverlay(value:Dynamic, duration:Dynamic):Bool {
		if (!hxcOwnsDeathOverlay(value) || camFollow == null)
			return false;
		var sprite:FlxSprite = cast value;
		var midpoint = sprite.getGraphicMidpoint();
		var seconds = Std.parseFloat(Std.string(duration));
		if (Math.isNaN(seconds) || seconds < 0)
			seconds = 0;
		FlxTween.cancelTweensOf(camFollow);
		if (seconds <= 0)
			camFollow.setPosition(midpoint.x, midpoint.y);
		else
			FlxTween.tween(camFollow, {x: midpoint.x, y: midpoint.y}, seconds);
		return true;
	}

	/** Restore the ordinary gameplay zoom after an imported death hook. */
	public function hxcResetCameraZoom():Bool {
		var zoom:Dynamic = null;
		try {
			if (PlayState.instance != null)
				zoom = Reflect.field(PlayState.instance, 'defaultCamZoom');
		} catch (_:Dynamic) {}
		var parsed = zoom == null ? 1 : Std.parseFloat(Std.string(zoom));
		if (Math.isNaN(parsed) || parsed <= 0)
			parsed = 1;
		if (FlxG.camera != null)
			FlxG.camera.zoom = parsed;
		return true;
	}

	public function hxcSetMustNotExit(value:Dynamic):Bool {
		mustNotExit = value == true;
		return true;
	}

	/** Remove and destroy all imported overlay sprites before substate teardown. */
	public function hxcClearDeathOverlays():Void {
		for (sprite in hxcDeathOverlays) {
			if (sprite == null)
				continue;
			if (members != null && members.indexOf(sprite) >= 0)
				remove(sprite, true);
			sprite.destroy();
		}
		hxcDeathOverlays = [];
		mustNotExit = false;
	}

	/** Keep the quote and its completion callback owned by this substate. */
	function initDeathQuotePlayback():Void {
		deathQuotePlayback = new HxcDeathQuotePlayback({
			startLoopMusic: function(volume:Float) {
				gameoverStarted = true;
				playGameoverMusic(volume);
			},
			playDeathLoop: function() { playDeathAnimation('deathLoop'); },
			playQuote: function(path:String, done:Void->Void):Dynamic {
				RuntimeSmokeHarness.markGameOverPhase('quote_start', {path: path,
					musicVolume: gameoverLoopMusic == null ? null : gameoverLoopMusic.volume,
					animation: Character.animationName(bf)});
				if (!FNFAssets.exists(path)) {
					trace('[hxc-death-quote-error] Missing sound: ' + path);
					return null;
				}
				return FlxG.sound.play(FNFAssets.getSound(path), 1, false, null, true, function() {
					RuntimeSmokeHarness.markGameOverPhase('quote_complete', {path: path});
					done();
				});
			},
			canFadeLoopMusic: function() return !isEnding && gameoverLoopMusic != null
				&& FlxG.sound.music == gameoverLoopMusic,
			fadeLoopMusic: function(duration:Float, from:Float, to:Float) {
				gameoverLoopMusic.fadeIn(duration, from, to);
				RuntimeSmokeHarness.markGameOverPhase('quote_music_fade',
					{duration: duration, from: from, to: to});
			},
			stopQuote: function(handle:Dynamic) {
				var sound:FlxSound = cast handle;
				sound.onComplete = null;
				sound.stop();
				FlxG.sound.list.remove(sound, true);
				sound.destroy();
			}
		});
		RuntimeSmokeHarness.markGameOverPhase('created', {character: quoteCharacter.curCharacter});
	}

	function playDeathAnimation(name:String):Void {
		// A post-super custom substate may already have advanced the initial
		// death to its loop. Avoid replaying the actor's authored override.
		if (!StringTools.startsWith(Character.animationName(bf), name))
			bf.playAnim(name);
	}

	function cancelDeathQuote():Void {
		if (deathQuotePlayback != null) deathQuotePlayback.cancel();
		RuntimeSmokeHarness.markGameOverPhase('quote_cancel', {});
	}

	function dispatchSourceGameOverUpdateBeforeSuper(elapsed:Float):Void {
		if (sourceMode == 2 && sourceOwner != null)
			sourceOwner.sourceGameOverCall('onUpdate', [elapsed]);
	}

	function dispatchSourceGameOverUpdateAfterSuper(elapsed:Float):Void {
		if (sourceMode == 1 && sourceOwner != null)
			sourceOwner.sourceGameOverCall('onUpdate', [elapsed]);
	}

	function dispatchSourceGameOverUpdatePost(elapsed:Float):Void {
		if (sourceMode != 0 && sourceOwner != null)
			sourceOwner.sourceGameOverCall('onUpdatePost', [elapsed]);
	}

	function notifySourceGameOverConfirmed():Void {
		if (sourceMode != 0 && sourceOwner != null)
			sourceOwner.sourceGameOverCall('onGameOverConfirm', [true]);
	}

	function sourceResultStops(result:Dynamic):Bool {
		return sourceMode == 2 ? result == NightmareVisionScriptGroup.STOP_FUNC
			: result == ScriptCallbackResult.STOP;
	}

	function updateSourceGameOverInput():Void {
		if (sourceMode == 1) {
			if (!isEnding) {
				if (sourceOwner.sourceGameOverCheckControl('ACCEPT'))
					endBullshit();
				else if (sourceOwner.sourceGameOverCheckControl('BACK'))
					sourceBackToMenu();
			}
			return;
		}

		if (sourceMode == 2) {
			if (sourceOwner.sourceGameOverCheckControl('ACCEPT')) {
				var result = sourceOwner.sourceGameOverCall('onGameOverConfirm', []);
				if (!sourceResultStops(result)) endBullshit();
			}
			if (sourceOwner.sourceGameOverCheckControl('BACK')) {
				var result = sourceOwner.sourceGameOverCall('onGameOverCancel', []);
				if (!sourceResultStops(result)) sourceBackToMenu();
			}
		}
	}

	function sourceBackToMenu():Void {
		isEnding = true;
		var owner = sourceOwner;
		cancelDeathQuote();
		hxcClearDeathOverlays();
		HxcCompatRuntime.clearGameOverCharacter(bf);
		if (FlxG.sound.music != null) FlxG.sound.music.stop();
		owner.sourceGameOverResetForMenu();

		if (PlayState.isStoryMode)
			LoadingState.loadAndSwitchState(new StoryMenuState());
		else
			LoadingState.loadAndSwitchState(new FreeplayState());
		FlxG.sound.playMusic(Paths.music('freakyMenu'));

		// Psych's false confirmation is deliberately after the menu transition
		// and its music, matching the donor's onGameOverConfirm([false]) timing.
		if (sourceMode == 1)
			owner.sourceGameOverCall('onGameOverConfirm', [false]);
	}

	override function update(elapsed:Float) {
		if (sourceMode != 0) {
			dispatchSourceGameOverUpdateBeforeSuper(elapsed);
			super.update(elapsed);
			dispatchSourceGameOverUpdateAfterSuper(elapsed);
			var currentAnim = bf != null && bf.animation != null ? bf.animation.curAnim : null;
			RuntimeSmokeHarness.tick(elapsed);
			if (codenameGameOverRuntime != null)
				codenameGameOverRuntime.update(elapsed);
			if (!codenameGameOverCancelled) {
				updateSourceGameOverInput();
				if (bf != null) updateGameoverAnimation(currentAnim);
			}
			if (FlxG.sound.music != null && FlxG.sound.music.playing)
				Conductor.songPosition = FlxG.sound.music.time;
			dispatchSourceGameOverUpdatePost(elapsed);
			return;
		}

		var currentAnim = bf.animation != null ? bf.animation.curAnim : null;
		// Imported Codename substates retain their update-after-super ABI.
		// Preserve the animation snapshot if Character advances it in that call.
		if (codenameGameOverRuntime != null)
			super.update(elapsed);
		// The parent is paused; keep the isolated smoke window's clock running.
		RuntimeSmokeHarness.tick(elapsed);
		if (codenameGameOverRuntime != null)
			codenameGameOverRuntime.update(elapsed);
		if (codenameGameOverCancelled)
			return;

		if (controls.ACCEPT)
			endBullshit();

		if (controls.BACK) {
			isEnding = true;
			cancelDeathQuote();
			hxcClearDeathOverlays();
			HxcCompatRuntime.clearGameOverCharacter(bf);
			if (FlxG.sound.music != null) FlxG.sound.music.stop();

			if (PlayState.isStoryMode)
				LoadingState.loadAndSwitchState(new StoryMenuState());
			else
				LoadingState.loadAndSwitchState(new FreeplayState());
			return;
		}

		// V-Slice checks before super.update: Character.update may replace the
		// completed firstDeath animation with deathLoop during that call.
		updateGameoverAnimation(currentAnim);
		if (codenameGameOverRuntime == null)
			super.update(elapsed);
		if (FlxG.sound.music != null && FlxG.sound.music.playing)
			Conductor.songPosition = FlxG.sound.music.time;
	}

	function updateGameoverAnimation(currentAnim:FlxAnimation):Void {
		if (isEnding || gameoverStarted) return;
		// The source queries even when no initial death animation is available.
		var quote = quoteCharacter == null ? null : quoteCharacter.getDeathQuote();
		if (currentAnim == null) {
			startGameoverLoop();
			return;
		}
		// Preserve the source's query before animation completion, and its
		// separate second query when playback begins (the getter may use RNG).
		if (StringTools.startsWith(currentAnim.name, 'firstDeath')) {
			if (currentAnim.curFrame == 12)
				FlxG.camera.follow(camFollow, LOCKON, 0.01);
			if (currentAnim.finished) {
				if (quote != null) {
					if (!deathQuoteAttempted && deathQuotePlayback != null) {
						deathQuoteAttempted = true;
						RuntimeSmokeHarness.markGameOverPhase('first_death_complete',
							{animation: currentAnim.name, gatePath: quote});
						deathQuotePlayback.start(true, quoteCharacter.getDeathQuote());
					}
				} else startGameoverLoop();
			}
		}
	}

	function startGameoverLoop() {
		if (gameoverStarted) return;
		gameoverStarted = true;
		startedDeath = true;
		FlxG.camera.follow(camFollow, LOCKON, 0.01);
		playGameoverMusic();
		if (StringTools.startsWith(Character.animationName(bf), 'firstDeath'))
			playDeathAnimation('deathLoop');
		RuntimeSmokeHarness.markGameOverPhase('no_quote_loop', {musicVolume: gameoverLoopMusic.volume});
	}

	function playGameoverMusic(volume:Float = 1) {
		var playState = sourceOwner == null ? PlayState.instance : sourceOwner;
		var psychLoopSound = playState == null ? null
			: playState.psychGameOverSoundPath('loopSoundName', false);
		if (psychLoopSound != null)
			FlxG.sound.playMusic(FNFAssets.getSound(psychLoopSound), volume);
		else {
			if (!FNFAssets.exists('assets/music/${bf.gameoverMusic}'))
				bf.gameoverMusic = 'gameOver.ogg';
			bf.gameoverMusic = HxcCompatRuntime.resolveGameOverTrack(bf.gameoverMusic,
				'assets/music', bf.isPixel);
			FlxG.sound.playMusic(FNFAssets.getSound('assets/music/' + bf.gameoverMusic), volume);
		}
		gameoverLoopMusic = FlxG.sound.music;
		if (sourceMode == 2 && !sourceDeathAnimNotified) {
			sourceDeathAnimNotified = true;
			startedDeath = true;
			sourceOwner.sourceGameOverCall('deathAnimStart', [volume]);
		}
	}

	override function beatHit() {
		super.beatHit();

		FlxG.log.add('beat');
	}

	function endBullshit():Void {
		if (!isEnding) {
			isEnding = true;
			cancelDeathQuote();
			if (bf != null) bf.playAnim('deathConfirm', true);

			if (FlxG.sound.music != null) FlxG.sound.music.stop();
			var playState = sourceOwner == null ? PlayState.instance : sourceOwner;
			var psychEndSound = playState == null ? null
				: playState.psychGameOverSoundPath('endSoundName', false);
			if (psychEndSound != null)
				FlxG.sound.play(FNFAssets.getSound(psychEndSound));
			else if (bf != null) {
				if (!FNFAssets.exists('assets/music/${bf.gameoverMusicEnd}'))
					bf.gameoverMusicEnd = 'gameOverEnd.ogg';
				bf.gameoverMusicEnd = HxcCompatRuntime.resolveGameOverTrack(bf.gameoverMusicEnd,
					'assets/music', bf.isPixel, true);
				FlxG.sound.play(FNFAssets.getSound('assets/music/' + bf.gameoverMusicEnd));
			}

			new FlxTimer().start(0.7, function(tmr:FlxTimer) {
				FlxG.camera.fade(FlxColor.BLACK, 2, false, function() {
					hxcClearDeathOverlays();
					HxcCompatRuntime.clearGameOverCharacter(bf);
					LoadingState.loadAndSwitchState(new PlayState());
				});
			});
			notifySourceGameOverConfirmed();
		}
	}

	override public function destroy():Void {
		if (deathQuotePlayback != null) {
			deathQuotePlayback.destroy();
			deathQuotePlayback = null;
		}
		quoteCharacter = null;
		RuntimeSmokeHarness.markGameOverPhase('destroy', {});
		if (codenameGameOverRuntime != null) {
			codenameGameOverRuntime.destroy();
			codenameGameOverRuntime = null;
		}
		hxcClearDeathOverlays();
		HxcCompatRuntime.clearGameOverCharacter(bf);
		if (instance == this)
			instance = null;
		super.destroy();
	}
}
