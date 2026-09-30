package;

import flixel.FlxCamera;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxState;
import flixel.addons.display.FlxBackdrop;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.graphics.frames.FlxFramesCollection;
import flixel.math.FlxMath;
import flixel.text.FlxText;
import flixel.tweens.FlxEase;
import flixel.util.FlxTimer;
import flixel.tweens.FlxTween;
import openfl.filters.ShaderFilter;
import openfl.Lib;
import lime.graphics.Image;

/** Explicit import aliases for selected-owner Codename global/state scripts.
	Shared engine imports are supplied by CodenameImportBindings; this class
	adds only native aliases, scoped helpers, and clear placeholders for source
	APIs which do not exist in this fork.
*/
class CodenameModBindings {
	public static function create(root:String, paths:CodenamePaths, interp:CodenameScriptInterp,
		host:Dynamic):Map<String, Dynamic> {
		var result:Map<String, Dynamic> = new Map();
		CodenameImportBindings.addShared(result, interp, paths);
		if (Std.isOfType(host, CodenameImportedState)) {
			result.set('Sys', CodenameSysCompat.importedStateFacade(root));
		}
		// CodenameScriptParser rewrites donor Map literals through this runtime
		// compatibility map. Global/state interpreters need the same alias as the
		// per-song PlayState interpreter.
		result.set('CodenameMapCompat', CodenameMapCompat);
		result.set('flixel.FlxState', FlxState);
		result.set('flixel.math.FlxMath', FlxMath);
		result.set('flixel.FlxG', interp.flxG);
		result.set('flixel.FlxCamera', FlxCamera);
		result.set('flixel.FlxSprite', FlxSprite);
		result.set('flixel.group.FlxGroup', FlxTypedGroup);
		result.set('flixel.group.FlxGroup.FlxTypedGroup', FlxTypedGroup);
		result.set('flixel.text.FlxText', FlxText);
		result.set('flixel.tweens.FlxEase', FlxEase);
		result.set('flixel.tweens.FlxTween', interp.tweenFacade());
		result.set('flixel.util.FlxColor', HxcFlxColorCompat);
		result.set('flixel.util.FlxTimer', FlxTimer);
		result.set('openfl.filters.ShaderFilter', ShaderFilter);
		result.set('openfl.Lib', Lib);
		result.set('lime.graphics.Image', Image);
		result.set('funkin.backend.utils.WindowUtils', CodenameUnavailableApi);
		result.set('funkin.backend.utils.ShaderResizeFix', CodenameUnavailableApi);
		result.set('funkin.menus.BetaWarningState', CodenameUnavailableApi);
		result.set('funkin.editors.EditorPicker', CodenameEditorPickerCompat);
		result.set('funkin.menus.ModSwitchMenu', CodenameModSwitchMenu);
		result.set('funkin.menus.credits.CreditsMain', CreditsState);
		result.set('funkin.options.OptionsMenu', CodenameOptionsMenuCompat);
		result.set('funkin.menus.MainMenuState', MainMenuState);
		result.set('funkin.menus.StoryMenuState', StoryMenuState);
		result.set('funkin.menus.FreeplayState', FreeplayState);
		var currentPlayState = PlayState.instance;
		var sourcePlayState:Dynamic = currentPlayState != null
			&& FlxG.state == currentPlayState
			&& (CodenameModRuntime.isActiveOwner(root)
				|| currentPlayState.codenameTransitionOwnerRoot() == root)
			? new CodenamePlayStateFacade(currentPlayState, currentPlayState.codenameSongView)
			: PlayState;
		if (sourcePlayState == PlayState && Std.isOfType(host, CodenameMusicBeatTransition)) {
			var transition:CodenameMusicBeatTransition = cast host;
			var view = transition.sourceSong;
			if (view != null && CodenameTransitionScope.sameOwner(root, transition.ownerRoot))
				sourcePlayState = new CodenamePlayStateFacade(null, function() return view);
		}
		result.set('funkin.game.PlayState', sourcePlayState);
		result.set('funkin.game.GameOverSubstate', GameOverSubstate);
		result.set('funkin.menus.PauseSubState', PauseSubState);
		result.set('funkin.backend.scripting.ModState', CodenameImportedState);
		result.set('ModState', CodenameImportedState);
		result.set('TitleState', TitleState);
		result.set('MainMenuState', MainMenuState);
		result.set('StoryMenuState', StoryMenuState);
		result.set('FreeplayState', FreeplayState);
		result.set('PlayState', sourcePlayState);
		result.set('OptionsMenu', CodenameOptionsMenuCompat);
		result.set('CreditsMain', CreditsState);
		result.set('ShaderFilter', ShaderFilter);
		result.set('FlxState', FlxState);
		result.set('FlxSprite', FlxSprite);
		result.set('FlxGroup', FlxTypedGroup);
		result.set('FlxText', FlxText);
		result.set('FlxTypedGroup', FlxTypedGroup);
		result.set('FlxMath', FlxMath);
		result.set('FlxEase', FlxEase);
		result.set('FlxTween', interp.tweenFacade());
		result.set('FlxColor', HxcFlxColorCompat);
		result.set('FlxTimer', FlxTimer);
		result.set('LoadingState', LoadingState);
		result.set('Conductor', Conductor);
		result.set('CoolUtil', coolUtil(paths));
		return result;
	}

	public static function seed(interp:CodenameScriptInterp, root:String,
		host:Dynamic, paths:CodenamePaths):Void {
		if (interp == null) return;
		var bindings = create(root, paths, interp, host);
		interp.protectImportAliases(bindings);
		for (name in bindings.keys())
			interp.variables.set(name.substr(name.lastIndexOf('.') + 1), bindings.get(name));
		interp.variables.set('Paths', paths);
		interp.variables.set('Assets', paths.assets());
		interp.variables.set('window', Lib.application == null ? null : Lib.application.window);
		interp.variables.set('FlxG', interp.flxG);
		interp.variables.set('Conductor', Conductor);
		interp.variables.set('CoolUtil', coolUtil(paths));
		interp.variables.set('lerp', function(from:Float, to:Float, ratio:Float):Float
			return from + ratio * (to - from));
		interp.variables.set('debugPrint', function(value:Dynamic):Void trace(value));
		interp.variables.set('controls', host != null && Reflect.hasField(host, 'controls')
			? Reflect.field(host, 'controls') : PlayerSettings.player1.controls);
		interp.variables.set('currentState', host);
		interp.variables.set('currentMenuState', host);
		interp.variables.set('state', host);
		interp.variables.set('game', host);
		interp.variables.set('curStep', 0);
		interp.variables.set('curBeat', 0);
		interp.variables.set('Math', Math);
		interp.variables.set('FlxSprite', FlxSprite);
		interp.variables.set('FlxGroup', FlxTypedGroup);
		interp.variables.set('FlxText', FlxText);
		interp.variables.set('FlxTypedGroup', FlxTypedGroup);
		interp.variables.set('FlxColor', HxcFlxColorCompat);
		interp.variables.set('FlxCamera', FlxCamera);
		interp.variables.set('FlxBackdrop', FlxBackdrop);
		interp.variables.set('FlxTimer', FlxTimer);
		interp.variables.set('FlxTween', interp.tweenFacade());
		interp.variables.set('FlxEase', FlxEase);
		interp.variables.set('FlxMath', FlxMath);
		interp.variables.set('OptionsMenu', CodenameOptionsMenuCompat);
		interp.variables.set('MainMenuState', MainMenuState);
		interp.variables.set('StoryMenuState', StoryMenuState);
		interp.variables.set('FreeplayState', FreeplayState);
		interp.variables.set('PlayState', PlayState);
		interp.variables.set('TitleState', TitleState);
		interp.variables.set('LoadingState', LoadingState);
		interp.variables.set('PauseSubState', PauseSubState);
		interp.variables.set('GameOverSubstate', GameOverSubstate);
		interp.variables.set('SONG', PlayState.SONG == null ? null : PlayState.SONG);
		if (host != null && interp != null) interp.bindScriptObject(host);
		interp.ownerStateFactory = function(name:String):Dynamic {
			var source:Dynamic = interp.variables.get('__compatDiagnosticSource');
			return CodenameModRuntime.stateInitIfAvailable(root, name,
				source == null ? '' : Std.string(source));
		};
		interp.modStateFactory = function(name:String):Dynamic return CodenameModRuntime.stateInit(root, name);
	}

	public static function customShader(paths:CodenamePaths, name:String):Dynamic {
		var resolveImport = function(key:String):String return paths.shaderImport(key);
		var fragment = CodenameShaderSource.forOpenFL(FNFAssets.getText(paths.frag(name)), resolveImport);
		var vertexPath = paths.vertexForFragment(name);
		var vertex = vertexPath == null ? null
			: CodenameShaderSource.forOpenFL(FNFAssets.getText(vertexPath), resolveImport);
		return new ShaderHandler.CoolRuntimeShader(fragment, vertex);
	}

	public static function coolUtil(paths:CodenamePaths):Dynamic {
		return {
			keyToString:function(key:Dynamic):String return CodenameKeyCodeCompat.keyToString(key),
			openURL:function(url:String):Bool return CodenameOpenURLCompat.open(url,
				function(safeUrl:String):Void FlxG.openURL(safeUrl)),
			fpsLerp:function(from:Float, to:Float, ratio:Float):Float {
				var adapted = 1 - Math.pow(1 - ratio, FlxG.elapsed * 60);
				return from + (to - from) * adapted;
			},
			quantize:function(value:Float, amount:Float):Float
				return Math.fround(value * amount) / amount,
			addZeros:function(value:String, length:Int):String {
				var padded = value == null ? '' : value;
				while (padded.length < length) padded = '0' + padded;
				return padded;
			},
			resetSprite:function(sprite:FlxSprite, x:Float, y:Float):FlxSprite {
				if (sprite == null) throw '[codename-sprite] resetSprite needs a sprite';
				sprite.reset(x, y);
				sprite.alpha = 1;
				sprite.visible = true;
				sprite.active = true;
				sprite.velocity.set();
				sprite.acceleration.set();
				sprite.drag.set();
				sprite.antialiasing = FlxSprite.defaultAntialiasing;
				FlxTween.cancelTweensOf(sprite);
				return sprite;
			},
			loadAnimatedGraphic:function(sprite:FlxSprite, graphic:Dynamic, fps:Float = 24):FlxSprite {
				if (sprite == null || graphic == null)
					throw '[codename-asset] loadAnimatedGraphic needs a sprite and graphic';
				var frames:Dynamic = Std.isOfType(graphic, String) ? paths.getFrames(cast graphic) : graphic;
				if (Std.isOfType(frames, FlxFramesCollection)) sprite.frames = cast frames;
				else sprite.loadGraphic(frames);
				if (sprite.frames != null && sprite.frames.frames != null && sprite.frames.frames.length > 0) {
					sprite.animation.add('idle', [for (i in 0...sprite.frames.frames.length) i], fps, true);
					sprite.animation.play('idle');
				}
				return sprite;
			},
			playMenuSFX:function(?id:Int, ?volume:Float):Dynamic {
				// Codename's CoolSfx IDs are shared by state and song scripts.
				if (id == null) id = 0;
				if (volume == null) volume = 1;
				var keys = ['menu/scroll', 'menu/confirm', 'menu/cancel',
					'editors/checkboxChecked', 'editors/checkboxUnchecked', 'editors/warningMenu'];
				if (id < 0 || id >= keys.length) {
					trace('[codename-menu-sfx] Unknown CoolSfx ID ' + id);
					return null;
				}
				try return FlxG.sound.play(paths.sound(keys[id]), volume) catch (error:Dynamic) {
					trace('[codename-menu-sfx] ' + Std.string(error));
					return null;
				}
			},
			playMenuSong:function(fadeIn:Bool = false):Void {
				if (FlxG.sound.music != null && FlxG.sound.music.playing) return;
				var volume = fadeIn ? 0.0 : 1.0;
				Conductor.songPosition = 0;
				Conductor.lastSongPos = 0;
				Conductor.bpmChangeMap = [];
				FlxG.sound.playMusic(paths.music('freakyMenu'), volume, true);
				Conductor.changeBPM(102);
				if (FlxG.sound.music != null) {
					FlxG.sound.music.persist = true;
					if (fadeIn) FlxG.sound.music.fadeIn(4, 0, 1);
				}
			},
			playMusic:function(sound:Dynamic, persist:Bool = false, volume:Float = 1,
				looped:Bool = true, defaultBPM:Float = 102):Void {
				var asset:Dynamic = sound;
				if (Std.isOfType(sound, String)) asset = FNFAssets.getSound(paths.getPath(Std.string(sound)));
				Conductor.songPosition = 0;
				Conductor.lastSongPos = 0;
				Conductor.bpmChangeMap = [];
				FlxG.sound.playMusic(asset, volume, looped);
				Conductor.changeBPM(defaultBPM);
				if (FlxG.sound.music != null) FlxG.sound.music.persist = persist;
			}
		};
	}
}
