package;

import flixel.FlxG;
import flixel.FlxObject;
import flixel.FlxSprite;
import flixel.FlxSubState;
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
	var camFollow:FlxObject;
	var gameoverStarted:Bool = false;
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
		instance = this;
		var psychCharacter = PlayState.instance == null ? null
			: PlayState.instance.psychGameOverCharacterName();
		var daBf:String = psychCharacter == null ? player.curCharacter + '-dead' : psychCharacter;
		trace(player.curCharacter);

		super();
		Conductor.songPosition = 0;

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
		if (bf.deathCameraZoom > 0)
			FlxG.camera.zoom = bf.deathCameraZoom;
		var psychDeathSound = PlayState.instance == null ? null
			: PlayState.instance.psychGameOverSoundPath('deathSoundName', true);
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

		FlxG.camera.focusOn(PlayState.instance.camFollow.getPosition());
		FlxG.camera.target = null;

		if (bf.animation.exists('firstDeath'))
			bf.playAnim('firstDeath');
		else { // backup if the player character has no death animation
			new FlxTimer().start(0.6, function(tmr:FlxTimer) { FlxG.camera.follow(camFollow, LOCKON, 0.01); });
			new FlxTimer().start(2.1, function(tmr:FlxTimer) { playGameoverMusic(); });
		}
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

	override function update(elapsed:Float) {
		super.update(elapsed);
		// Opening a substate pauses the parent state, which also stops the
		// smoke gate's bounded-window clock. Keep the clock running through a
		// game-over so a demo death still produces a clean success marker.
		RuntimeSmokeHarness.tick(elapsed);
		if (codenameGameOverRuntime != null)
			codenameGameOverRuntime.update(elapsed);
		if (codenameGameOverCancelled)
			return;

		if (controls.ACCEPT)
			endBullshit();

		if (controls.BACK) {
			hxcClearDeathOverlays();
			HxcCompatRuntime.clearGameOverCharacter(bf);
			FlxG.sound.music.stop();

			if (PlayState.isStoryMode)
				LoadingState.loadAndSwitchState(new StoryMenuState());
			else
				LoadingState.loadAndSwitchState(new FreeplayState());
		}

		var currentAnim = bf.animation != null ? bf.animation.curAnim : null;
		if (currentAnim == null)
			startGameoverLoop();
		else if (currentAnim.name == 'firstDeath') {
			if (currentAnim.curFrame == 12)
				FlxG.camera.follow(camFollow, LOCKON, 0.01);
			else if (currentAnim.finished)
				playGameoverMusic();
		}

		if (FlxG.sound.music.playing)
			Conductor.songPosition = FlxG.sound.music.time;
	}

	function startGameoverLoop() {
		if (gameoverStarted) return;
		gameoverStarted = true;
		FlxG.camera.follow(camFollow, LOCKON, 0.01);
		playGameoverMusic();
	}

	function playGameoverMusic() {
		var psychLoopSound = PlayState.instance == null ? null
			: PlayState.instance.psychGameOverSoundPath('loopSoundName', false);
		if (psychLoopSound != null) {
			FlxG.sound.playMusic(FNFAssets.getSound(psychLoopSound));
			return;
		}
		if (!FNFAssets.exists('assets/music/${bf.gameoverMusic}'))
			bf.gameoverMusic = 'gameOver.ogg';
		bf.gameoverMusic = HxcCompatRuntime.resolveGameOverTrack(bf.gameoverMusic,
			'assets/music', bf.isPixel);
		FlxG.sound.playMusic(FNFAssets.getSound('assets/music/' + bf.gameoverMusic));
	}

	override function beatHit() {
		super.beatHit();

		FlxG.log.add('beat');
	}

	var isEnding:Bool = false;

	function endBullshit():Void {
		if (!isEnding) {
			isEnding = true;
			bf.playAnim('deathConfirm', true);

			FlxG.sound.music.stop();
			var psychEndSound = PlayState.instance == null ? null
				: PlayState.instance.psychGameOverSoundPath('endSoundName', false);
			if (psychEndSound != null)
				FlxG.sound.play(FNFAssets.getSound(psychEndSound));
			else {
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
		}
	}

	override public function destroy():Void {
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
