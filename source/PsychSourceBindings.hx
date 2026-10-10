package;

import flixel.math.FlxPoint;
import flixel.FlxG;
import flixel.FlxObject;
import flixel.FlxSprite;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.input.gamepad.FlxGamepadInputID;
import flixel.sound.FlxSound;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween;
import flixel.util.FlxColor;
import flixel.util.FlxSave;
import haxe.io.Path;
import openfl.utils.AssetType;
#if (!flash && sys)
import flixel.addons.display.FlxRuntimeShader;
#end
#if sys
import sys.FileSystem;
#end

/**
	Binds the common Psych Lua callback surface onto the host's existing
	compatibility operations. It is installed only for a selected Psych source
	owner, after the general HScript seed has been created.
*/
@:access(PlayState)
@:access(flixel.util.FlxSave.validate)
class PsychSourceBindings {
	final host:PlayState;
	final ownerRoot:String;
	final files:SourceScriptFileAccess;
	final runtimeShaders:Map<String, Array<String>> = new Map();

	public function new(host:PlayState, ?ownerRoot:String) {
		this.host = host;
		this.ownerRoot = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		this.files = this.ownerRoot == '' ? null : new SourceScriptFileAccess(resolveSourcePath);
	}

	function addScore(value:Int = 0):Void {
		host.songScore += value;
		host.psychScoreChanged();
	}

	function setScore(value:Int = 0):Void {
		host.songScore = value;
		host.psychScoreChanged();
	}

	function addMisses(value:Int = 0):Void {
		PlayState.misses += value;
		host.psychScoreChanged();
	}

	function setMisses(value:Int = 0):Void {
		PlayState.misses = value;
		host.psychScoreChanged();
	}

	function addHits(value:Int = 0):Void {
		if (host.sourceScoreLedgerActive()) host.songHits += value;
		else host.psychHitsAdjustment += value;
		host.psychScoreChanged();
	}

	function setHits(value:Int = 0):Void {
		if (host.sourceScoreLedgerActive()) host.songHits = value;
		else host.psychHitsAdjustment = value - PlayState.sicks - PlayState.goods - PlayState.bads - PlayState.shits;
		host.psychScoreChanged();
	}

	static function scorePropertyAlias(path:Dynamic):String {
		var normalized = EngineCompat.propertyPath(path).toLowerCase();
		if (normalized.indexOf('.') >= 0 || normalized.indexOf('[') >= 0) return '';
		return switch (normalized) {
			case 'score' | 'songscore': 'score';
			case 'misses' | 'songmisses': 'misses';
			case 'hits': 'hits';
			default: '';
		};
	}

	function readScorePropertyAlias(alias:String):Dynamic {
		return switch (alias) {
			case 'score': host.songScore;
			case 'misses': PlayState.misses;
			case 'hits': host.sourceScoreLedgerActive() ? host.songHits
				: PlayState.sicks + PlayState.goods + PlayState.bads + PlayState.shits + host.psychHitsAdjustment;
			default: null;
		};
	}

	function writeScorePropertyAlias(alias:String, value:Dynamic):Bool {
		if (alias == '') return false;
		var parsed = Std.parseFloat(Std.string(value));
		var number = Math.isFinite(parsed) ? Std.int(parsed) : 0;
		switch (alias) {
			case 'score': setScore(number);
			case 'misses': setMisses(number);
			case 'hits': setHits(number);
			default: return false;
		}
		return true;
	}

	public function install(interp:Dynamic):Void {
		var variables:Dynamic = interp.variables;
		var previousGetProperty:Dynamic = variables.get('getProperty');
		var previousSetProperty:Dynamic = variables.get('setProperty');
		variables.set('getProperty', function(path:Dynamic, allowMaps:Bool = false):Dynamic {
			var alias = scorePropertyAlias(path);
			if (alias != '') return readScorePropertyAlias(alias);
			return previousGetProperty == null ? host.compatGetProperty(path)
				: Reflect.callMethod(null, previousGetProperty, allowMaps ? [path, true] : [path]);
		});
		variables.set('setProperty', function(path:Dynamic, value:Dynamic, allowMaps:Bool = false,
			allowInstances:Bool = false):Dynamic {
			var alias = scorePropertyAlias(path);
			if (alias != '') {
				writeScorePropertyAlias(alias, value);
				return value;
			}
			if (previousSetProperty == null) {
				host.compatSetProperty(path, value);
				return value;
			}
			return Reflect.callMethod(null, previousSetProperty,
				allowMaps || allowInstances ? [path, value, allowMaps, allowInstances] : [path, value]);
		});
		variables.set('Function_Stop', ScriptCallbackResult.STOP);
		variables.set('Function_Continue', ScriptCallbackResult.CONTINUE);
		variables.set('Function_StopLua', ScriptCallbackResult.STOP_LUA);
		variables.set('Function_StopHScript', ScriptCallbackResult.STOP_HSCRIPT);
		variables.set('Function_StopAll', ScriptCallbackResult.STOP_ALL);
		variables.set('setVar', function(name:String, value:Dynamic):Dynamic {
			return setVar(name, value);
		});
		variables.set('getVar', function(name:String):Dynamic return SourceScriptVariables.get(function() return PsychStateClassBindings.registry(host), name));
		variables.set('removeVar', function(name:String):Bool return SourceScriptVariables.remove(function() return PsychStateClassBindings.registry(host), name, false));
		variables.set('getPropertyLuaSprite', function(tag:String, variable:String):Dynamic
			return getPropertyLuaSprite(tag, variable));
		variables.set('setPropertyLuaSprite', function(tag:String, variable:String, value:Dynamic):Bool
			return setPropertyLuaSprite(tag, variable, value));
		variables.set('noteTweenDirection', function(tag:String, note:Int, value:Dynamic,
			duration:Float, ?ease:String = 'linear'):Dynamic
			return noteTweenDirection(tag, note, value, duration, ease));

		variables.set('stringStartsWith', function(value:String, prefix:String):Bool
			return PsychSourceBindings.stringStartsWith(value, prefix));
		variables.set('stringEndsWith', function(value:String, suffix:String):Bool
			return PsychSourceBindings.stringEndsWith(value, suffix));
		variables.set('stringSplit', function(value:String, separator:String):Array<String>
			return PsychSourceBindings.stringSplit(value, separator));
		variables.set('stringTrim', function(value:String):String return PsychSourceBindings.stringTrim(value));

		// Psych's geometry getters return world-space points except the explicit
		// screen-position variants. FlxPoint results are pooled by Flixel.
		variables.set('getMidpointX', function(name:String):Float return pointComponent(name, 'getMidpoint', 'x'));
		variables.set('getMidpointY', function(name:String):Float return pointComponent(name, 'getMidpoint', 'y'));
		variables.set('getGraphicMidpointX', function(name:String):Float return pointComponent(name, 'getGraphicMidpoint', 'x'));
		variables.set('getGraphicMidpointY', function(name:String):Float return pointComponent(name, 'getGraphicMidpoint', 'y'));
		variables.set('getScreenPositionX', function(name:String, ?camera:String = 'game'):Float
			return screenPositionComponent(name, camera, 'x'));
		variables.set('getScreenPositionY', function(name:String, ?camera:String = 'game'):Float
			return screenPositionComponent(name, camera, 'y'));

		installTextLifecycle(variables);
		installSpriteLifecycle(variables);
		new SourceScriptTextBindings(false, psychObject, function(name) return PsychFontPath.resolve(name, ownerRoot),
			SourceTextStyle.psychColor, SourceTextStyle.border, function(message) trace('[psych-text] ' + message)).install(variables);

		variables.set('addAnimationByIndicesLoop', function(tag:String, name:String, prefix:String,
			indices:Dynamic, framerate:Int = 24):Bool {
			var object:Dynamic = host.compatFindObject(tag);
			if (object == null || object.animation == null) return false;
			host.compatAddAnimationByIndices(tag, name, prefix, indices, framerate, true);
			return true;
		});
		variables.set('luaSpriteMakeGraphic', function(tag:String, width:Int, height:Int, color:String):Void
			host.compatMakeGraphic(tag, width, height, color));
		variables.set('luaSpriteAddAnimationByPrefix', function(tag:String, name:String, prefix:String,
			framerate:Int = 24, loop:Bool = true):Void
			host.compatAddAnimationByPrefix(tag, name, prefix, framerate, loop));
		variables.set('luaSpriteAddAnimationByIndices', function(tag:String, name:String, prefix:String,
			indices:String, framerate:Int = 24):Void
			host.compatAddAnimationByIndices(tag, name, prefix, indices, framerate, false));
		variables.set('luaSpritePlayAnimation', function(tag:String, name:String, forced:Bool = false):Void
			host.compatPlayAnim(tag, name, forced));
		variables.set('setLuaSpriteCamera', function(tag:String, camera:String = ''):Bool {
			if (host.compatFindObject(tag) == null) return false;
			host.compatSetObjectCamera(tag, camera);
			return true;
		});
		variables.set('musicFadeIn', function(duration:Float, fromValue:Float = 0, toValue:Float = 1):Void {
			if (FlxG.sound.music != null) FlxG.sound.music.fadeIn(duration, fromValue, toValue);
		});
		variables.set('musicFadeOut', function(duration:Float, toValue:Float = 0):Void {
			if (FlxG.sound.music != null) FlxG.sound.music.fadeOut(duration, toValue);
		});
		variables.set('updateHitboxFromGroup', function(group:String, index:Int):Void {
			var object:Dynamic = host.compatGroupMember(group, index);
			if (object != null) try object.updateHitbox() catch (_:Dynamic) {}
		});

		variables.set('addOffset', function(tag:String, animation:String, x:Float, y:Float):Bool {
			var object:Dynamic = host.compatFindObject(tag);
			if (object == null) return false;
			var addOffset = Reflect.field(object, 'addOffset');
			if (!Reflect.isFunction(addOffset)) return false;
			Reflect.callMethod(object, addOffset, [animation, x, y]);
			return true;
		});
		variables.set('luaSpriteExists', function(tag:String):Bool {
			var object:Dynamic = host.nightmareVisionLegacyFieldCameras ? host.compatFindObject(tag) : host.psychScriptVariables.get(tag);
			return host.nightmareVisionLegacyFieldCameras ? Std.isOfType(object, FlxSprite)
				: Std.isOfType(object, PsychModchartSprite) || Std.isOfType(object, PsychModchartAnimateSprite);
		});
		variables.set('luaTextExists', function(tag:String):Bool return host.nightmareVisionLegacyFieldCameras
			? psychText(tag) != null : Std.isOfType(host.psychScriptVariables.get(tag), FlxText));
		variables.set('luaSoundExists', function(tag:String):Bool return psychSound(tag) != null);
		variables.set('setTimeBarColors', function(left:String, right:String):Void setTimeBarColors(left, right));
		variables.set('objectsOverlap', function(first:String, second:String):Bool {
			var a:Dynamic = psychObject(first);
			var b:Dynamic = psychObject(second);
			return a != null && b != null && FlxG.overlap(cast a, cast b);
		});
		variables.set('getPixelColor', function(tag:String, x:Int, y:Int):Int {
			var sprite:Dynamic = psychObject(tag);
			if (!Std.isOfType(sprite, FlxSprite)) return FlxColor.BLACK;
			try return (cast sprite:FlxSprite).pixels.getPixel32(x, y) catch (_:Dynamic) return FlxColor.BLACK;
		});

		variables.set('getCharacterX', function(role:String):Float return actorPosition(role, 'x'));
		variables.set('getCharacterY', function(role:String):Float return actorPosition(role, 'y'));
		variables.set('setCharacterX', function(role:String, value:Float):Void setActorPosition(role, 'x', value));
		variables.set('setCharacterY', function(role:String, value:Float):Void setActorPosition(role, 'y', value));
		variables.set('cameraSetTarget', function(target:String):Void cameraSetTarget(target));
		variables.set('setCameraScroll', function(x:Float, y:Float):Void {
			if (host.camGame != null) host.camGame.scroll.set(x - host.camGame.width / 2, y - host.camGame.height / 2);
		});
		variables.set('addCameraScroll', function(?x:Float = 0, ?y:Float = 0):Void {
			if (host.camGame != null) host.camGame.scroll.add(x, y);
		});
		variables.set('getCameraScrollX', function():Float return host.camGame == null ? 0 : host.camGame.scroll.x + host.camGame.width / 2);
		variables.set('getCameraScrollY', function():Float return host.camGame == null ? 0 : host.camGame.scroll.y + host.camGame.height / 2);
		variables.set('setCameraFollowPoint', function(x:Float, y:Float):Void host.camFollow.setPosition(x, y));
		variables.set('addCameraFollowPoint', function(?x:Float = 0, ?y:Float = 0):Void {
			host.camFollow.x += x;
			host.camFollow.y += y;
		});
		variables.set('getCameraFollowX', function():Float return host.camFollow.x);
		variables.set('getCameraFollowY', function():Float return host.camFollow.y);

		variables.set('getColorFromName', function(color:String):Int return colorFromString(color));
		variables.set('getColorFromString', function(color:String):Int return colorFromString(color));

		variables.set('keyPressed', function(name:String = ''):Bool return actionState(name, 'held'));
		variables.set('keyReleased', function(name:String = ''):Bool return actionState(name, 'release'));
		variables.set('keyboardPressed', function(name:String):Bool return keyboardState(name, 'pressed'));
		variables.set('keyboardReleased', function(name:String):Bool return keyboardState(name, 'justReleased'));
		variables.set('anyGamepadJustPressed', function(name:String):Bool return anyGamepadState(name, 'justPressed'));
		variables.set('anyGamepadPressed', function(name:String):Bool return anyGamepadState(name, 'pressed'));
		variables.set('anyGamepadReleased', function(name:String):Bool return anyGamepadState(name, 'justReleased'));
		variables.set('gamepadAnalogX', function(id:Int, ?leftStick:Bool = true):Float
			return gamepadAnalog(id, leftStick, true));
		variables.set('gamepadAnalogY', function(id:Int, ?leftStick:Bool = true):Float
			return gamepadAnalog(id, leftStick, false));
		variables.set('gamepadJustPressed', function(id:Int, name:String):Bool return gamepadButton(id, name, 'justPressed'));
		variables.set('gamepadPressed', function(id:Int, name:String):Bool return gamepadButton(id, name, 'pressed'));
		variables.set('gamepadReleased', function(id:Int, name:String):Bool return gamepadButton(id, name, 'justReleased'));
		variables.set('mousePressed', function(?button:String = 'left'):Bool return mouseState(button, 'pressed'));
		variables.set('mouseReleased', function(?button:String = 'left'):Bool return mouseState(button, 'justReleased'));

		variables.set('addScore', function(value:Int = 0):Void addScore(value));
		variables.set('setScore', function(value:Int = 0):Void setScore(value));
		variables.set('addMisses', function(value:Int = 0):Void addMisses(value));
		variables.set('setMisses', function(value:Int = 0):Void setMisses(value));
		variables.set('addHits', function(value:Int = 0):Void addHits(value));
		variables.set('setHits', function(value:Int = 0):Void setHits(value));
		variables.set('setHealth', function(value:Float = 1):Void host.health = value);
		variables.set('addHealth', function(value:Float = 0):Void host.health += value);
		variables.set('getHealth', function():Float return host.health);
		variables.set('setRatingPercent', function(value:Float):Void {
			host.setPsychRatingValue('ratingPercent', value);
			host.psychScoreChanged();
		});
		variables.set('setRatingName', function(value:String):Void {
			host.setPsychRatingValue('ratingName', value);
			host.psychScoreChanged();
		});
		variables.set('setRatingFC', function(value:String):Void {
			host.setPsychRatingValue('ratingFC', value);
			host.psychScoreChanged();
		});
		variables.set('updateScoreText', function():Void host.psychScoreChanged());

		variables.set('pauseSound', function(tag:String):Void soundAction(tag, 'pause'));
		variables.set('resumeSound', function(tag:String):Void soundAction(tag, 'resume'));
		variables.set('soundFadeCancel', function(tag:String):Void soundAction(tag, 'cancelFade'));
		variables.set('getSoundVolume', function(tag:String):Float return soundNumber(tag, 'volume'));
		variables.set('setSoundVolume', function(tag:String, value:Float):Void setSoundNumber(tag, 'volume', value));
		variables.set('getSoundTime', function(tag:String):Float return soundNumber(tag, 'time'));
		variables.set('setSoundTime', function(tag:String, value:Float):Void setSoundNumber(tag, 'time', value));
		variables.set('getSoundPitch', function(tag:String):Float return soundNumber(tag, 'pitch', false));
		variables.set('setSoundPitch', function(tag:String, value:Float, ?doPause:Bool = false):Void {
			var sound = psychSound(tag);
			if (sound == null) return;
			var wasPlaying = sound.playing;
			if (doPause) sound.pause();
			sound.pitch = value;
			if (doPause && wasPlaying) sound.play();
		});

		variables.set('insertToCustomSubstate', function(tag:String, ?position:Int = -1):Bool
			return insertToCustomSubstate(tag, position));

		variables.set('initSaveData', function(name:String, ?folder:String = 'psychenginemods'):Void
			initSaveData(name, folder));
		variables.set('flushSaveData', function(name:String):Void saveAction(name, 'flush'));
		variables.set('getDataFromSave', function(name:String, field:String, ?defaultValue:Dynamic = null):Dynamic
			return getSaveData(name, field, defaultValue));
		variables.set('setDataFromSave', function(name:String, field:String, value:Dynamic):Void
			setSaveData(name, field, value));
		variables.set('eraseSaveData', function(name:String):Void saveAction(name, 'erase'));

		variables.set('checkFileExists', function(path:String, ?absolute:Bool = false):Bool
			return files != null && files.exists(path, absolute));
		variables.set('saveFile', function(path:String, content:String, ?absolute:Bool = false):Bool
			return files != null && files.saveText(path, content, absolute));
		variables.set('deleteFile', function(path:String, ?ignoreModFolders:Bool = false,
			?absolute:Bool = false):Bool {
			// Imported scripts may only delete files owned by their selected import.
			// Ignoring mods would target the host's shared installation instead.
			if (ignoreModFolders) return false;
			return files != null && files.deleteFile(path, absolute);
		});
		variables.set('getTextFromFile', function(path:String, ?ignoreModFolders:Bool = false):String
			return getTextFromFile(path, ignoreModFolders));
		variables.set('directoryFileList', function(folder:String):Array<String>
			return files == null ? [] : files.readDirectory(folder));

		// These helpers operate on the calling import's path facade. In
		// particular, shader and atlas lookups cannot be satisfied by a sibling
		// imported mod with the same asset name.
		variables.set('loadFrames', function(tag:String, image:String, ?spriteType:String = 'auto'):Void
			loadFrames(tag, image, spriteType));
		variables.set('loadMultipleFrames', function(tag:String, images:Array<String>):Void
			loadMultipleFrames(tag, images));
		variables.set('startVideo', function(videoFile:String, ?canSkip:Bool = true,
			?forMidSong:Bool = false, ?shouldLoop:Bool = false, ?playOnLoad:Bool = true):Bool
			return host.psychStartVideo(ownerRoot, videoFile, canSkip, forMidSong, shouldLoop, playOnLoad));

		variables.set('initLuaShader', function(name:String):Bool return initLuaShader(name));
		variables.set('setSpriteShader', function(tag:String, shaderName:String):Bool
			return setSpriteShader(tag, shaderName));
		variables.set('removeSpriteShader', function(tag:String):Bool return removeSpriteShader(tag));
		for (kind in ['Bool', 'BoolArray', 'Int', 'IntArray', 'Float', 'FloatArray']) {
			var suffix = kind;
			variables.set('getShader' + suffix, function(tag:String, property:String):Dynamic
				return getShaderValue(tag, property, suffix));
		}
		for (kind in ['Bool', 'BoolArray', 'Int', 'IntArray', 'Float', 'FloatArray']) {
			var suffix = kind;
			variables.set('setShader' + suffix, function(tag:String, property:String, value:Dynamic):Bool
				return setShaderValue(tag, property, value, suffix));
		}
		variables.set('setShaderSampler2D', function(tag:String, property:String, image:String):Bool
			return setShaderSampler2D(tag, property, image));

		variables.set('addAnimationBySymbol', function(tag:String, name:String, symbol:String,
			?framerate:Float = 24, ?loop:Bool = false, ?matX:Float = 0, ?matY:Float = 0):Bool
			return addAnimationBySymbol(tag, name, symbol, framerate, loop, matX, matY));
		variables.set('addAnimationBySymbolIndices', function(tag:String, name:String, symbol:String,
			?indices:Dynamic = null, ?framerate:Float = 24, ?loop:Bool = false,
			?matX:Float = 0, ?matY:Float = 0):Bool
			return addAnimationBySymbolIndices(tag, name, symbol, indices, framerate, loop, matX, matY));
	}

	static public function stringStartsWith(value:String, prefix:String):Bool
		return value != null && prefix != null && StringTools.startsWith(value, prefix);

	static public function stringEndsWith(value:String, suffix:String):Bool
		return value != null && suffix != null && StringTools.endsWith(value, suffix);

	static public function stringSplit(value:String, separator:String):Array<String>
		return value == null ? [] : value.split(separator == null ? '' : separator);

	static public function stringTrim(value:String):String
		return value == null ? '' : StringTools.trim(value);

	function getTextFromFile(path:String, ignoreModFolders:Bool):String {
		if (files == null) return null;
		if (ignoreModFolders) {
			var shared = sharedFilePath(path);
			if (shared == null) return null;
			try return FNFAssets.getText(shared) catch (_:Dynamic) return null;
		}
		return files.getText(path);
	}

	function resolveSourcePath(path:String, write:Bool, absolute:Bool):Null<String> {
		if (ownerRoot == '') return null;
		if (absolute) return resolveAbsoluteOwnerPath(path);
		var clean = PsychOwnerAssetPath.cleanId(path);
		if (clean == null) return null;
		if (write) return ownerDestination(clean);

		var ownerPath = PsychOwnerAssetPath.resolve(ownerRoot, clean);
		if (ownerPath.blocked || ownerPath.unavailable) return null;
		if (ownerPath.owned) return ownerPath.path;

		// Source reads may fall back to the host's shared library, but never to a
		// different imported mod or whichever level happens to be globally active.
		return sharedFilePath(clean);
	}

	function sharedFilePath(path:String):Null<String> {
		var clean = PsychOwnerAssetPath.cleanId(path);
		if (clean == null) return null;
		var lower = clean.toLowerCase();
		if (StringTools.startsWith(lower, CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/')) return null;
		if (StringTools.startsWith(lower, 'assets/shared/'))
			return FNFAssets.exists(clean) ? clean : null;
		var key = StringTools.startsWith(lower, 'assets/') ? clean.substr('assets/'.length) : clean;
		var resolved = Paths.file(key, AssetType.TEXT, 'shared');
		return FNFAssets.exists(resolved) ? resolved : null;
	}

	function ownerDestination(relative:String):Null<String> {
		var clean = PsychOwnerAssetPath.cleanId(relative);
		if (clean == null) return null;
		var candidate = Path.normalize(Path.join([ownerRoot, clean]));
		var root = Path.normalize(ownerRoot);
		if (candidate == root || !StringTools.startsWith(candidate, root + '/')) return null;
		return ownerContainedDestination(candidate);
	}

	function resolveAbsoluteOwnerPath(path:String):Null<String> {
		if (path == null || StringTools.trim(path) == '') return null;
		#if sys
		var candidate = Path.normalize(StringTools.replace(StringTools.trim(path), '\\', '/'));
		var root:String;
		try root = Path.normalize(StringTools.replace(FileSystem.fullPath(ownerRoot), '\\', '/')) catch (_:Dynamic) return null;
		var comparedCandidate = candidate;
		var comparedRoot = root;
		#if windows
		comparedCandidate = comparedCandidate.toLowerCase();
		comparedRoot = comparedRoot.toLowerCase();
		#end
		if (comparedCandidate == comparedRoot || !StringTools.startsWith(comparedCandidate, comparedRoot + '/')) return null;
		return ownerContainedDestination(candidate);
		#else
		return null;
		#end
	}

	function ownerContainedDestination(candidate:String):Null<String> {
		#if sys
		var parent = Path.directory(candidate);
		var root = Path.normalize(ownerRoot);
		while (parent != null && parent != '' && parent != '.') {
			var normalizedParent = Path.normalize(parent);
			if (FileSystem.exists(normalizedParent)) {
				if (normalizedParent != root && !PsychOwnerAssetPath.withinOwner(ownerRoot, normalizedParent)) return null;
				if (FileSystem.exists(candidate) && !PsychOwnerAssetPath.withinOwner(ownerRoot, candidate)) return null;
				return candidate;
			}
			if (normalizedParent == root) break;
			parent = Path.directory(normalizedParent);
		}
		return null;
		#else
		return null;
		#end
	}

	function psychObject(name:Dynamic):Dynamic {
		if (name == null) return null;
		var tagged = host.compatFindObject(name);
		return tagged == null ? host.compatGetProperty(name) : tagged;
	}

	function pointComponent(name:String, methodName:String, axis:String):Float {
		var object:Dynamic = psychObject(name);
		if (!Std.isOfType(object, FlxObject)) return 0;
		var point:FlxPoint = null;
		var value = 0.0;
		try {
			point = methodName == 'getMidpoint'
				? (cast object:FlxObject).getMidpoint()
				: (cast object:FlxSprite).getGraphicMidpoint();
			value = axis == 'x' ? point.x : point.y;
		} catch (_:Dynamic) {
		}
		if (point != null) point.put();
		return value;
	}

	function screenPositionComponent(name:String, camera:String, axis:String):Float {
		var object:Dynamic = psychObject(name);
		if (!Std.isOfType(object, FlxObject)) return 0;
		var point:FlxPoint = null;
		var value = 0.0;
		try {
			point = (cast object:FlxObject).getScreenPosition(null, host.compatCameraForName(camera));
			value = axis == 'x' ? point.x : point.y;
		} catch (_:Dynamic) {
		}
		if (point != null) point.put();
		return value;
	}

	function installSpriteLifecycle(variables:Map<String,Dynamic>):Void {
		if (host.nightmareVisionLegacyFieldCameras) return;
		var registry = function():Dynamic return host.psychScriptVariables;
		var scene = function():Dynamic return host.historicalPropertyInstance();
		variables.set('makeLuaSprite', function(tag:String, image:String = null, x:Float = 0, y:Float = 0):Void {
			SourceScriptSpriteLifecycle.create(tag, registry, scene, function() {
				var sprite = new PsychModchartSprite(x, y, textSpriteAntialiasing());
				if (image != null && image.length > 0 && host.compatPsychOwnerFallbackAllowed(ownerRoot, image)) {
					var graphic = host.compatPsychPathCall(ownerRoot, 'image', [host.compatPsychAssetKey(image, '.png')]);
					if (graphic != null) sprite.loadGraphic(cast graphic);
				}
				return sprite;
			}, true);
		});
		variables.set('makeAnimatedLuaSprite', function(tag:String, image:String = null, x:Float = 0, y:Float = 0, spriteType:String = 'auto'):Void {
			SourceScriptSpriteLifecycle.create(tag, registry, scene, function() {
				var sprite = new PsychModchartSprite(x, y, textSpriteAntialiasing());
				if (image != null && image.length > 0) loadFramesObject(sprite, image, spriteType);
				return sprite;
			}, false);
		});
		variables.set('makeFlxAnimateSprite', function(tag:String, x:Float = 0, y:Float = 0, loadFolder:String = null):Void {
			SourceScriptSpriteLifecycle.createAnimate(tag, registry, function():Dynamic return host, function() {
				var sprite = new PsychModchartAnimateSprite(x, y);
				sprite.antialiasing = textSpriteAntialiasing();
				if (loadFolder != null) host.compatLoadAnimateAtlasObject(ownerRoot, sprite, loadFolder);
				return sprite;
			});
		});
		variables.set('addLuaSprite', function(tag:String, front:Bool = false):Void {
			SourceScriptSpriteLifecycle.add(tag, front, registry, scene, lowestSpriteAnchor, function() return host.isDead, function():Dynamic return GameOverSubstate.instance);
		});
		variables.set('removeLuaSprite', function(tag:String, destroy:Bool = true, group:String = null):Void {
			SourceScriptSpriteLifecycle.remove(tag, destroy, group, psychObject, registry, scene);
		});
		var previousRemove = variables.get('removeObject');
		variables.set('removeObject', function(tag:String, destroy:Bool = true):Void {
			var object = registry().get(tag);
			if (Std.isOfType(object, FlxSprite) && !Std.isOfType(object, FlxText))
				SourceScriptSpriteLifecycle.remove(tag, destroy, null, psychObject, registry, scene);
			else Reflect.callMethod(null, previousRemove, [tag, destroy]);
		});
	}
	function textSpriteAntialiasing():Bool {
		return host.psychClientPrefs == null ? OptionsHandler.options.antialiasing : host.psychClientPrefs.data.antialiasing;
	}
	function lowestSpriteAnchor():Dynamic {
		if (host.isDead) return Reflect.getProperty(GameOverSubstate.instance, 'boyfriend');
		// Native host scenes may keep actors directly until source groups are mounted.
		var bf:Dynamic = host.boyfriendGroup == null ? host.boyfriend : host.boyfriendGroup;
		var dad:Dynamic = host.dadGroup == null ? host.dad : host.dadGroup;
		var gf:Dynamic = host.gfGroup == null ? host.gf : host.gfGroup;
		var hidden = host.curStage != null && host.curStage.stageData != null && host.curStage.stageData.hide_girlfriend == true;
		var group:Dynamic = hidden ? bf : gf;
		for (candidate in [bf, dad]) if (host.members.indexOf(candidate) < host.members.indexOf(group)) group = candidate;
		return group;
	}

	function installTextLifecycle(variables:Map<String,Dynamic>):Void {
		if (host.nightmareVisionLegacyFieldCameras) return;
		var registry = function():Dynamic return host.psychScriptVariables;
		var scene = function():Dynamic return host.historicalPropertyInstance();
		variables.set('makeLuaText', function(tag:String, text:String = '', width:Int = 0, x:Float = 0, y:Float = 0):Void {
			SourceScriptTextLifecycle.create(tag, registry, scene, function() {
				var label = new FlxText(x, y, width, text, 16);
				SourceTextDefaults.apply(label, PsychFontPath.resolve('vcr.ttf', ownerRoot), host.camHUD);
				return label;
			}, true);
		});
		variables.set('addLuaText', function(tag:String):Void {
			SourceScriptTextLifecycle.add(tag, registry, scene, true);
		});
		var remove = function(tag:String, destroy:Bool = true):Void {
			SourceScriptTextLifecycle.remove(tag, destroy, registry,
				function():Dynamic return host.compatCustomSubstate != null ? host.compatCustomSubstate : scene(), true);
		};
		variables.set('removeLuaText', remove);
		// Preserve the host's generic removal spelling for modern variable-owned text.
		variables.set('removeObject', function(tag:String, destroy:Bool = true):Void {
			if (Std.isOfType(host.psychScriptVariables.get(tag), FlxText)) remove(tag, destroy);
			else host.compatRemoveObject(tag, destroy);
		});
	}

	function psychText(tag:Dynamic):FlxText {
		var object = psychObject(tag);
		return Std.isOfType(object, FlxText) ? cast object : null;
	}

	function setTimeBarColors(left:String, right:String):Void {
		if (host.songPosBar == null) return;
		var empty:FlxColor = timeBarLeft;
		var fill:FlxColor = timeBarRight;
		var parsedLeft = host.compatParseColor(left);
		var parsedRight = host.compatParseColor(right);
		if (left != null && left != '' && parsedLeft != null) empty = cast parsedLeft;
		if (right != null && right != '' && parsedRight != null) fill = cast parsedRight;
		timeBarLeft = empty;
		timeBarRight = fill;
		host.songPosBar.createFilledBar(empty, fill);
	}

	var timeBarLeft:FlxColor = FlxColor.GRAY;
	var timeBarRight:FlxColor = FlxColor.LIME;

	function actorForRole(role:String):Dynamic {
		return host.getHaxeActor(role == null ? '' : role);
	}

	function actorPosition(role:String, axis:String):Float {
		var actor:Dynamic = actorForRole(role);
		if (actor == null) return 0;
		try return axis == 'x' ? actor.x : actor.y catch (_:Dynamic) return 0;
	}

	function setActorPosition(role:String, axis:String, value:Float):Void {
		var actor:Dynamic = actorForRole(role);
		if (actor == null) return;
		try {
			if (axis == 'x') actor.x = value else actor.y = value;
		} catch (_:Dynamic) {}
	}

	function cameraSetTarget(target:String):Void {
		var role = target == null ? '' : StringTools.trim(target).toLowerCase();
		if (role == 'gf' || role == 'girlfriend') {
			var gf = actorForRole('gf');
			if (gf != null) host.setCameraFollowActor(cast gf, 'gf');
		} else host.moveCamera(role == 'dad' || role == 'opponent');
	}

	function psychSound(tag:Dynamic):FlxSound {
		return host.compatTaggedSound(tag);
	}

	function soundAction(tag:Dynamic, action:String):Void {
		var sound = tag == null || StringTools.trim(tag) == '' ? FlxG.sound.music : psychSound(tag);
		if (sound == null) return;
		switch (action) {
			case 'pause': sound.pause();
			case 'resume': sound.play();
			case 'cancelFade':
				var fade = Reflect.getProperty(sound, 'fadeTween');
				if (fade != null) {
					var cancel = Reflect.field(fade, 'cancel');
					if (Reflect.isFunction(cancel)) Reflect.callMethod(fade, cancel, []);
				}
		}
	}

	function soundNumber(tag:Dynamic, property:String, emptyUsesMusic:Bool = true):Float {
		var empty = tag == null || StringTools.trim(Std.string(tag)) == '';
		var sound = empty && emptyUsesMusic ? FlxG.sound.music : psychSound(tag);
		if (sound == null) return property == 'pitch' ? 1 : 0;
		try return Reflect.getProperty(sound, property) catch (_:Dynamic) return 0;
	}

	function setSoundNumber(tag:Dynamic, property:String, value:Float):Void {
		var sound = tag == null || StringTools.trim(Std.string(tag)) == '' ? FlxG.sound.music : psychSound(tag);
		if (sound != null) try Reflect.setProperty(sound, property, value) catch (_:Dynamic) {}
	}

	function actionState(name:String, state:String):Bool {
		var token = name == null ? '' : StringTools.trim(name).toLowerCase();
		var action = switch (token) {
			case 'left': state == 'press' ? 'ctrl1-press' : state == 'release' ? 'ctrl1-release' : 'ctrl1';
			case 'down': state == 'press' ? 'ctrl2-press' : state == 'release' ? 'ctrl2-release' : 'ctrl2';
			case 'up': state == 'press' ? 'ctrl3-press' : state == 'release' ? 'ctrl3-release' : 'ctrl3';
			case 'right': state == 'press' ? 'ctrl4-press' : state == 'release' ? 'ctrl4-release' : 'ctrl4';
			default: token;
		};
		var controls:Dynamic = host.controls;
		if (controls == null) return false;
		var methodName = state == 'held' ? 'pressedByName' : 'checkByName';
		var method = Reflect.field(controls, methodName);
		if (!Reflect.isFunction(method)) return false;
		try return Reflect.callMethod(controls, method, [action]) == true catch (_:Dynamic) return false;
	}

	static function keyboardState(name:String, state:String):Bool {
		if (name == null) return false;
		var keys:Dynamic = FlxG.keys;
		var values:Dynamic = Reflect.getProperty(keys, state);
		return values != null && Reflect.getProperty(values, name) == true;
	}

	static function anyGamepadState(name:String, state:String):Bool {
		if (name == null) return false;
		var gamepads:Dynamic = FlxG.gamepads;
		var methodName = switch (state) {
			case 'justPressed': 'anyJustPressed';
			case 'justReleased': 'anyJustReleased';
			default: 'anyPressed';
		};
		var method = Reflect.field(gamepads, methodName);
		if (!Reflect.isFunction(method)) return false;
		try return Reflect.callMethod(gamepads, method, [name]) == true catch (_:Dynamic) return false;
	}

	static function gamepadAnalog(id:Int, leftStick:Bool, horizontal:Bool):Float {
		var controller = FlxG.gamepads.getByID(id);
		if (controller == null) return 0;
		var axis:FlxGamepadInputID = leftStick
			? FlxGamepadInputID.LEFT_ANALOG_STICK : FlxGamepadInputID.RIGHT_ANALOG_STICK;
		return horizontal ? controller.getXAxis(axis) : controller.getYAxis(axis);
	}

	static function gamepadButton(id:Int, name:String, state:String):Bool {
		if (name == null) return false;
		var controller = FlxG.gamepads.getByID(id);
		if (controller == null) return false;
		var values = switch (state) {
			case 'justPressed': controller.justPressed;
			case 'justReleased': controller.justReleased;
			default: controller.pressed;
		};
		return Reflect.getProperty(values, name) == true;
	}

	static function mouseState(button:String, state:String):Bool {
		var mouse:Dynamic = FlxG.mouse;
		var token = button == null ? 'left' : StringTools.trim(button).toLowerCase();
		var field = switch (token) {
			case 'right': state == 'pressed' ? 'pressedRight' : 'justReleasedRight';
			case 'middle': state == 'pressed' ? 'pressedMiddle' : 'justReleasedMiddle';
			default: state == 'pressed' ? 'pressed' : 'justReleased';
		};
		return Reflect.getProperty(mouse, field) == true;
	}

	function insertToCustomSubstate(tag:String, position:Int):Bool {
		var substate = host.compatCustomSubstate;
		var object:Dynamic = host.compatFindObject(tag);
		if (substate == null || object == null || !Std.isOfType(object, FlxObject)) return false;
		if (position < 0) substate.add(cast object) else substate.insert(position, cast object);
		return true;
	}

	function initSaveData(name:String, folder:String):Bool {
		if (name == null || StringTools.trim(name) == '') return false;
		var key = 'save_' + name;
		if (host.psychScriptVariables.exists(key)) return false;
		var save = new FlxSave();
		var app = FlxG.stage.application;
		var savePath = Std.string(app.meta.get('company')) + '/'
			+ FlxSave.validate(app.meta.get('file')) + '/' + folder;
		save.bind(name, savePath);
		host.psychScriptVariables.set(key, save);
		return true;
	}

	function saveAction(name:String, action:String):Bool {
		var save = psychSave(name);
		if (save == null) return false;
		if (action == 'erase') save.erase() else save.flush();
		return true;
	}

	function psychSave(name:String):FlxSave {
		if (name == null) return null;
		return cast host.psychScriptVariables.get('save_' + name);
	}

	function getSaveData(name:String, field:String, defaultValue:Dynamic):Dynamic {
		var save = psychSave(name);
		if (save == null || field == null || !Reflect.hasField(save.data, field)) return defaultValue;
		return Reflect.field(save.data, field);
	}

	function setSaveData(name:String, field:String, value:Dynamic):Bool {
		var save = psychSave(name);
		if (save == null || field == null) return false;
		Reflect.setField(save.data, field, value);
		return true;
	}

	function colorFromString(value:String):Int {
		var parsed = host.compatParseColor(value);
		return parsed == null ? FlxColor.WHITE : cast parsed;
	}

	function loadFrames(tag:String, image:String, spriteType:String):Void {
		loadFramesObject(psychObject(tag), image, spriteType);
	}

	function loadFramesObject(sprite:Dynamic, image:String, spriteType:String):Void {
		if (!Std.isOfType(sprite, FlxSprite) || image == null || StringTools.trim(image) == '') return;
		if (!host.compatPsychOwnerFallbackAllowed(ownerRoot, image)) return;
		var key = host.compatPsychAssetKey(image, '.png');
		var kind = spriteType == null ? 'auto' : StringTools.replace(StringTools.trim(spriteType).toLowerCase(), ' ', '');
		var method = switch (kind) {
			case 'aseprite', 'ase', 'json', 'jsoni8': 'getAsepriteAtlas';
			case 'packer', 'packeratlas', 'pac': 'getPackerAtlas';
			case 'sparrow', 'sparrowatlas', 'sparrowv2': 'getSparrowAtlas';
			default: 'getAtlas';
		};
		var atlas:Dynamic = host.compatPsychPathCall(ownerRoot, method, [key]);
		if (atlas == null) return;
		try {
			(cast sprite:FlxSprite).frames = cast atlas;
			if (Std.isOfType(sprite, PsychModchartSprite))
				(cast sprite:PsychModchartSprite).sourceAtlasNames = host.compatPsychSpriteFrameNames(ownerRoot, key, method);
		} catch (_:Dynamic) {}
	}

	function loadMultipleFrames(tag:String, images:Array<String>):Void {
		var sprite = psychObject(tag);
		if (!Std.isOfType(sprite, FlxSprite) || images == null || images.length == 0) return;
		var atlases:Array<FlxAtlasFrames> = [];
		for (image in images) {
			if (image == null || StringTools.trim(image) == ''
				|| !host.compatPsychOwnerFallbackAllowed(ownerRoot, image)) continue;
			var key = host.compatPsychAssetKey(StringTools.trim(image), '.png');
			var atlas:Dynamic = host.compatPsychPathCall(ownerRoot, 'getAtlas', [key]);
			if (Std.isOfType(atlas, FlxAtlasFrames)) atlases.push(cast atlas);
		}
		if (atlases.length == 0) return;
		var first = atlases[0];
		var merged = new FlxAtlasFrames(first.parent);
		merged.addAtlas(first, true);
		for (i in 1...atlases.length) merged.addAtlas(atlases[i], true);
		try (cast sprite:FlxSprite).frames = merged catch (_:Dynamic) {}
	}

	function initLuaShader(name:String):Bool {
		#if (!flash && sys)
		if (!OptionsHandler.options.gameplayShaders || name == null || StringTools.trim(name) == '') return false;
		if (runtimeShaders.exists(name)) return true;
		if (!PsychOwnerAssetPath.ownerReferenceAllowed(ownerRoot, name)) return false;
		var fragPath:Dynamic = host.compatPsychPathCall(ownerRoot, 'shaderFragment', [name]);
		var vertPath:Dynamic = host.compatPsychPathCall(ownerRoot, 'shaderVertex', [name]);
		var frag:Null<String> = null;
		var vert:Null<String> = null;
		try if (fragPath != null && FNFAssets.exists(Std.string(fragPath))) frag = FNFAssets.getText(Std.string(fragPath)) catch (_:Dynamic) {}
		try if (vertPath != null && FNFAssets.exists(Std.string(vertPath))) vert = FNFAssets.getText(Std.string(vertPath)) catch (_:Dynamic) {}
		if (frag == null && vert == null) return false;
		runtimeShaders.set(name, [frag, vert]);
		return true;
		#else
		return false;
		#end
	}

	function setSpriteShader(tag:String, shaderName:String):Bool {
		#if (!flash && sys)
		if (!OptionsHandler.options.gameplayShaders || tag == null || shaderName == null) return false;
		if (!runtimeShaders.exists(shaderName) && !initLuaShader(shaderName)) return false;
		var sprite = psychObject(tag);
		if (!Std.isOfType(sprite, FlxSprite)) return false;
		var sources = runtimeShaders.get(shaderName);
		try {
			(cast sprite:FlxSprite).shader = new ShaderHandler.CoolRuntimeShader(sources[0], sources[1]);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
		#else
		return false;
		#end
	}

	function removeSpriteShader(tag:String):Bool {
		var sprite = psychObject(tag);
		if (!Std.isOfType(sprite, FlxSprite)) return false;
		(cast sprite:FlxSprite).shader = null;
		return true;
	}

	function shaderFor(tag:String):Dynamic {
		#if (!flash && sys)
		var sprite = psychObject(tag);
		if (!Std.isOfType(sprite, FlxSprite)) return null;
		var shader:Dynamic = (cast sprite:FlxSprite).shader;
		return Std.isOfType(shader, FlxRuntimeShader) ? shader : null;
		#else
		return null;
		#end
	}

	function getShaderValue(tag:String, property:String, kind:String):Dynamic {
		var shader = shaderFor(tag);
		if (shader == null || property == null) return null;
		var method = Reflect.field(shader, 'get' + kind);
		if (!Reflect.isFunction(method)) return null;
		try return Reflect.callMethod(shader, method, [property]) catch (_:Dynamic) return null;
	}

	function setShaderValue(tag:String, property:String, value:Dynamic, kind:String):Bool {
		var shader = shaderFor(tag);
		if (shader == null || property == null) return false;
		var method = Reflect.field(shader, 'set' + kind);
		if (!Reflect.isFunction(method)) return false;
		try {
			Reflect.callMethod(shader, method, [property, value]);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	function setShaderSampler2D(tag:String, property:String, image:String):Bool {
		#if (!flash && sys)
		if (image == null || !host.compatPsychOwnerFallbackAllowed(ownerRoot, image)) return false;
		var shader = shaderFor(tag);
		if (shader == null) return false;
		var graphic:Dynamic = host.compatPsychPathCall(ownerRoot, 'image', [host.compatPsychAssetKey(image, '.png')]);
		var bitmap:Dynamic = graphic == null ? null : Reflect.getProperty(graphic, 'bitmap');
		if (bitmap == null) return false;
		var method = Reflect.field(shader, 'setSampler2D');
		if (!Reflect.isFunction(method)) return false;
		try {
			Reflect.callMethod(shader, method, [property, bitmap]);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
		#else
		return false;
		#end
	}

	function addAnimationBySymbol(tag:String, name:String, symbol:String, framerate:Float,
		loop:Bool, matX:Float, matY:Float):Bool {
		var object = psychObject(tag);
		var anim:Dynamic = object == null ? null : Reflect.getProperty(object, 'anim');
		if (anim == null) return false;
		var method = Reflect.field(anim, 'addBySymbol');
		if (!Reflect.isFunction(method)) return false;
		try {
			Reflect.callMethod(anim, method, [name, symbol, framerate, loop, matX, matY]);
			if (Reflect.getProperty(anim, 'curSymbol') == null) host.compatPlayAnim(tag, name, true);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	function addAnimationBySymbolIndices(tag:String, name:String, symbol:String, indices:Dynamic,
		framerate:Float, loop:Bool, matX:Float, matY:Float):Bool {
		var object = psychObject(tag);
		var anim:Dynamic = object == null ? null : Reflect.getProperty(object, 'anim');
		if (anim == null) return false;
		var parsed:Array<Int> = [0];
		if (indices != null) {
			if (Std.isOfType(indices, String)) {
				parsed = [];
				for (part in StringTools.trim(cast indices).split(',')) {
					var value = Std.parseInt(StringTools.trim(part));
					parsed.push(value == null ? 0 : value);
				}
			} else if (Std.isOfType(indices, Array)) parsed = cast indices;
			else return false;
		}
		var method = Reflect.field(anim, 'addBySymbolIndices');
		if (!Reflect.isFunction(method)) return false;
		try {
			Reflect.callMethod(anim, method, [name, symbol, parsed, framerate, loop, matX, matY]);
			if (Reflect.getProperty(anim, 'curSymbol') == null) host.compatPlayAnim(tag, name, true);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Deprecated Psych API: only the variables map tag is used as the root. */
	function getPropertyLuaSprite(tag:String, variable:String):Dynamic {
		return readTaggedProperty(host.psychScriptVariables, tag, variable);
	}

	/** setVar resolves Psych's explicit instanceArg marker, then returns its input. */
	function setVar(name:String, value:Dynamic):Dynamic {
		return SourceScriptVariables.set(function() return PsychStateClassBindings.registry(host), name, value, storePsychVariable);
	}

	function storePsychVariable(value:Dynamic):Dynamic {
		return SourceScriptReflection.parseInstances(value, resolveInstancePath);
	}

	function resolveInstancePath(path:String, type:Null<String>):Dynamic {
		var tokens = host.compatPathTokens(EngineCompat.propertyPath(path));
		var object:Dynamic = null;
		if (type == null) {
			if (tokens.length == 0) return null;
			var root = tokens.shift();
			object = host.psychScriptVariables.exists(root)
				? host.psychScriptVariables.get(root) : host.compatPropertyRoot(root);
		} else {
			object = host.compatResolveClass(type);
		}
		for (token in tokens) object = host.compatReadPathPart(object, token);
		return object;
	}

	/** Deprecated Psych API: a present tag reports success after Reflect writes. */
	function setPropertyLuaSprite(tag:String, variable:String, value:Dynamic):Bool {
		return writeTaggedProperty(host.psychScriptVariables, tag, variable, value);
	}

	/** Psych's direction tween uses only strumLineNotes.members[note % length]. */
	function noteTweenDirection(tag:String, note:Int, value:Dynamic, duration:Float,
		?ease:String = 'linear'):Dynamic {
		if (host.strumLineNotes == null || host.strumLineNotes.length == 0) return null;
		var target:Dynamic = host.strumLineNotes.members[note % host.strumLineNotes.length];
		if (target == null) return null;
		var tweenEase = psychEaseName(ease);
		var tweenTag:String = tag == null ? null : 'tween_' + formatTweenTag(tag);
		if (tweenTag != null) host.compatCancelTween(tweenTag);
		var props:Dynamic = {direction:value};
		var created:FlxTween = null;
		var complete = function(_) {
			if (tweenTag != null && host.compatTweens.get(tweenTag) == created)
				host.compatTweens.remove(tweenTag);
			if (tag != null) host.callAllHScript('onTweenCompleted', [tag]);
		};
		var params:Dynamic = {ease:Reflect.field(FlxEase, tweenEase)};
		if (tag != null) Reflect.setField(params, 'onComplete', complete);
		created = FlxTween.tween(target, props, duration, params);
		if (tweenTag != null) host.compatTweens.set(tweenTag, created);
		return tweenTag;
	}

	static function psychEaseName(ease:String):String {
		return switch (StringTools.trim(ease == null ? '' : ease).toLowerCase()) {
			case 'backin': 'backIn'; case 'backinout': 'backInOut'; case 'backout': 'backOut';
			case 'bouncein': 'bounceIn'; case 'bounceinout': 'bounceInOut'; case 'bounceout': 'bounceOut';
			case 'circin': 'circIn'; case 'circinout': 'circInOut'; case 'circout': 'circOut';
			case 'cubein': 'cubeIn'; case 'cubeinout': 'cubeInOut'; case 'cubeout': 'cubeOut';
			case 'elasticin': 'elasticIn'; case 'elasticinout': 'elasticInOut'; case 'elasticout': 'elasticOut';
			case 'expoin': 'expoIn'; case 'expoinout': 'expoInOut'; case 'expoout': 'expoOut';
			case 'quadin': 'quadIn'; case 'quadinout': 'quadInOut'; case 'quadout': 'quadOut';
			case 'quartin': 'quartIn'; case 'quartinout': 'quartInOut'; case 'quartout': 'quartOut';
			case 'quintin': 'quintIn'; case 'quintinout': 'quintInOut'; case 'quintout': 'quintOut';
			case 'sinein': 'sineIn'; case 'sineinout': 'sineInOut'; case 'sineout': 'sineOut';
			case 'smoothstepin': 'smoothStepIn'; case 'smoothstepinout': 'smoothStepInOut'; case 'smoothstepout': 'smoothStepOut';
			case 'smootherstepin': 'smootherStepIn'; case 'smootherstepinout': 'smootherStepInOut'; case 'smootherstepout': 'smootherStepOut';
			default: 'linear';
		};
	}

	static function readTaggedProperty(variables:Map<String, Dynamic>, tag:String,
		variable:String):Dynamic {
		if (!variables.exists(tag)) return null;
		var tokens = variable.split('.');
		var value:Dynamic = variables.get(tag);
		for (token in tokens) value = Reflect.getProperty(value, token);
		return value;
	}

	static function writeTaggedProperty(variables:Map<String, Dynamic>, tag:String,
		variable:String, value:Dynamic):Bool {
		if (!variables.exists(tag)) return false;
		var tokens = variable.split('.');
		var object:Dynamic = variables.get(tag);
		for (i in 0...tokens.length - 1) object = Reflect.getProperty(object, tokens[i]);
		Reflect.setProperty(object, tokens[tokens.length - 1], value);
		return true;
	}

	static function formatTweenTag(tag:String):String {
		return StringTools.replace(StringTools.replace(StringTools.trim(tag), ' ', '_'), '.', '');
	}
}
