package;

using StringTools;

#if sys
import sys.io.File;
#end

/** A source location attached to a finding emitted by the Psych stage adapter. */
typedef PsychStageDiagnostic = {
	var severity:String;
	var code:String;
	var message:String;
	var line:Int;
	@:optional var path:String;
}

/** A static point recovered from a Psych stage script. */
typedef PsychStagePoint = {
	var x:Float;
	var y:Float;
}

/** One animation declaration recovered from addAnimationBy*(). */
typedef PsychStageAnimation = {
	var name:String;
	var prefix:String;
	var fps:Float;
	var looped:Bool;
	var indices:Array<Int>;
}

/** Static properties of a Lua sprite created by a Psych stage onCreate(). */
typedef PsychStageSprite = {
	var tag:String;
	var image:String;
	var x:Float;
	var y:Float;
	var animated:Bool;
	var front:Bool;
	var scaleX:Float;
	var scaleY:Float;
	var scrollX:Float;
	var scrollY:Float;
	var camera:String;
	var animations:Array<PsychStageAnimation>;
	var initialAnimation:String;
	/** Whether addLuaSprite() was seen in the static construction pass. */
	@:optional var added:Bool;
	/** Whether a static removeLuaSprite()/removeLuaText() call removed it. */
	@:optional var removed:Bool;
	/** Literal order supplied to setObjectOrder(), when statically known. */
	@:optional var order:Null<Int>;
}

/** Logical asset copy instructions for the importer. */
typedef PsychStageAssetMapping = {
	var sourceKey:String;
	var destination:String;
	var xmlDestination:String;
	var animated:Bool;
}

/**
	The result of translating the static part of a Psych stage Lua file.

	Psych stages are Lua programs, not data files.  This adapter intentionally
	translates only the deterministic construction part of `onCreate`: sprite
	creation, ordering, camera assignment, scroll factors, scale, graphic sizing,
	hitbox updates, blend modes, visibility, animations,
	background colour, and the default camera zoom.  Runtime callbacks such as
	`onUpdate` are reported rather than guessed at.  The importer can therefore
	keep the generated static stage while presenting an actionable diagnostic for
	content which still needs a runtime compatibility route.
*/
typedef PsychStageTranslation = {
	var hscript:String;
	var supported:Bool;
	var diagnostics:Array<PsychStageDiagnostic>;
	var sprites:Array<PsychStageSprite>;
	var assets:Array<PsychStageAssetMapping>;
	var defaultZoom:Null<Float>;
	var stagePosition:Null<PsychStagePoint>;
	var characterPositions:Map<String, PsychStagePoint>;
	/** Runtime callback names preserved in the generated HScript module. */
	var runtimeCallbacks:Array<String>;
}

private typedef PsychStageCall = {
	var name:String;
	var args:Array<String>;
	var start:Int;
}

private typedef PsychStageBody = {
	var text:String;
	var startLine:Int;
	var found:Bool;
}

private typedef PsychStageCallback = {
	var name:String;
	var args:String;
	var body:String;
	var startLine:Int;
}

private typedef PsychStageStateAssignment = {
	var name:String;
	var value:String;
}

private typedef PsychStageParsedAssignment = {
	var name:String;
	var value:String;
	var local:Bool;
}

/**
	Pure Psych stage Lua -> native stage HScript adapter.

	The class deliberately has no Flixel, PlayState, or importer dependency. It
	returns text and metadata only, so scan/import code can plan work and show
	diagnostics without loading the game state.  Source files are never changed.
*/
class PsychStageCompat {
	public static inline var ENGINE_NAME:String = 'Psych Engine';

	static inline var DEFAULT_ZOOM:Float = 1.05;

	/** Translate a stage source string without touching the filesystem. */
	public static function translate(source:String, ?origin:String):PsychStageTranslation {
		var path = origin == null || origin.trim() == '' ? 'stage.lua' : origin;
		var diagnostics:Array<PsychStageDiagnostic> = [];
		var sprites:Array<PsychStageSprite> = [];
		var assets:Array<PsychStageAssetMapping> = [];
		var spriteByTag:Map<String, PsychStageSprite> = new Map<String, PsychStageSprite>();
		var identifiers:Map<String, String> = new Map<String, String>();
		var numericVars:Map<String, Float> = new Map<String, Float>();
		var characterPositions:Map<String, PsychStagePoint> = new Map<String, PsychStagePoint>();
		var defaultZoom:Null<Float> = null;
		var stagePosition:Null<PsychStagePoint> = null;
		var hscriptLines:Array<String> = [];
		var runtimeCallbacks:Array<String> = [];
		var stateDefaults:Map<String, String> = new Map<String, String>();
		var stateOrder:Array<String> = [];
		var onCreateAssignments:Array<PsychStageStateAssignment> = [];

		if (source == null || source.trim() == '') {
			diagnostics.push(makeDiagnostic('error', 'stage-empty', 'No Psych stage Lua source was supplied.', 1, path));
			return result(hscriptLines, diagnostics, sprites, assets, defaultZoom, stagePosition, characterPositions,
				runtimeCallbacks);
		}

		var normalized = StringTools.replace(source, '\r\n', '\n');
		var allLines = normalized.split('\n');
		var body = findCallbackBody(allLines, 'onCreate');
		var callbacks = findCallbacks(allLines);
		// Seed the numeric environment before hoisting state so values such as
		// `cloudGap = gap` can be emitted as literals in the static fallback.
		collectNumericAssignments(normalized, numericVars);
		if (body.found)
			collectNumericAssignments(body.text, numericVars);
		// The static fallback must retain the small amount of mutable state which
		// donor callbacks share with onCreate.  Haven.lua, for example, declares
		// `acc`/`cloudGap` above onCreate and initializes `dir1`/bounds inside it.
		// Only literal numeric/bool/string assignments are hoisted; arbitrary Lua
		// expressions remain in the callback pass and are diagnosed by LuaCompat.
		collectStateAssignments(allLines, body, callbacks, numericVars, stateDefaults, stateOrder,
			onCreateAssignments);
		for (name in stateOrder)
			hscriptLines.push('var ' + name + ' = ' + stateDefaults.get(name) + ';');
		if (!body.found) {
			diagnostics.push(makeDiagnostic('error', 'missing-oncreate',
				'Psych stage has no onCreate callback; no static stage setup can be imported.', 1, path));
			hscriptLines.push('function start(song) {}');
		} else {
			// Resolve simple numeric locals before translating calls.  Haven.lua,
			// for example, writes `local gap = 15000` and then uses `-10 - gap`
			// for the second looping cloud.
			// Psych stage authors commonly put reusable constants above
			// onCreate (Haven.lua's `local gap` is one example), while other
			// stages declare them inside the callback. Collect both forms before
			// resolving sprite coordinates.
			// Resolve assignment values again after the complete numeric environment
			// has been collected; this lets `cloudGap = gap` remain deterministic.
			hscriptLines.push('function start(song) {');
			for (assignment in onCreateAssignments) {
				var assignmentValue = safeAssignmentValue(assignment.value, numericVars);
				if (assignmentValue != null)
					hscriptLines.push('    ' + assignment.name + ' = ' + assignmentValue + ';');
			}
			var calls = scanTopLevelCalls(body.text);
			for (callIndex in 0...calls.length) {
				var call = calls[callIndex];
				var line = body.startLine + countNewlines(body.text.substr(0, call.start));
				var name = call.name.toLowerCase();
				switch (name) {
					case 'makeluasprite' | 'makeanimatedluasprite':
						translateMakeSprite(call, name == 'makeanimatedluasprite', line, path,
							numericVars, sprites, assets, spriteByTag, identifiers, hscriptLines, diagnostics);
					case 'addanimationbyprefix':
						translateAnimationPrefix(call, line, path, numericVars, spriteByTag, identifiers, hscriptLines, diagnostics);
					case 'addanimationbyindices':
						translateAnimationIndices(call, line, path, numericVars, spriteByTag, identifiers, hscriptLines, diagnostics);
					case 'objectplayanimation':
						translatePlayAnimation(call, line, path, spriteByTag, identifiers, hscriptLines, diagnostics);
					case 'scaleobject':
						translateScale(call, line, path, numericVars, spriteByTag, identifiers, hscriptLines, diagnostics);
					case 'setgraphicsize':
						translateGraphicSize(call, line, path, numericVars, spriteByTag, hscriptLines, diagnostics);
					case 'updatehitbox':
						translateUpdateHitbox(call, line, path, spriteByTag, hscriptLines, diagnostics);
					case 'setblendmode':
						translateBlendMode(call, line, path, spriteByTag, hscriptLines, diagnostics);
					case 'setscrollfactor' | 'setluaspritescrollfactor':
						translateScroll(call, line, path, numericVars, spriteByTag, identifiers, hscriptLines, diagnostics);
					case 'setobjectcamera':
						translateCamera(call, line, path, spriteByTag, identifiers, hscriptLines, diagnostics);
					case 'addluasprite':
						translateAddSprite(call, line, path, spriteByTag, identifiers, hscriptLines, diagnostics);
					case 'setobjectorder':
						translateObjectOrder(call, line, path, numericVars, spriteByTag, hscriptLines, diagnostics);
					case 'removeobject' | 'removeluasprite' | 'removeluatext':
						translateRemoveObject(call, line, path, spriteByTag, hscriptLines, diagnostics);
					case 'setproperty':
						var metadata = translateSetProperty(call, line, path, numericVars, spriteByTag,
							identifiers, hscriptLines, diagnostics, characterPositions, stagePosition, defaultZoom);
						stagePosition = metadata.stagePosition;
						defaultZoom = metadata.defaultZoom;
					case 'setpropertyfromclass':
						translateSetPropertyFromClass(call, line, path, hscriptLines, diagnostics);
					case 'screencenter':
						translateScreenCenter(call, line, path, spriteByTag, identifiers, hscriptLines, diagnostics);
					case 'close':
						// Psych uses close(true) to end the Lua state after static stage
						// construction. The generated HScript has no Lua state to close;
						// consume only a standalone terminal literal call. Keep any later
						// callback (including onCreatePost) on the normal runtime route.
						if (!isTerminalStaticClose(call, body.text, calls, callIndex))
							diagnostics.push(makeDiagnostic('warning', 'unsupported-stage-api',
								'Psych stage API ' + call.name + '() is not supported by the static translator.', line, path));
					default:
						// getColorFromHex() nested inside setProperty is not returned by
						// scanTopLevelCalls. Every other top-level call is actionable.
						diagnostics.push(makeDiagnostic('warning', 'unsupported-stage-api',
							'Psych stage API ' + call.name + '() is not supported by the static translator.', line, path));
				}
			}
			hscriptLines.push('}');
		}

		// Keep common Psych lifecycle callbacks live in the static fallback too.
		// The body is passed through LuaCompat rather than copied as raw Haxe/Lua;
		// this gives the fallback exactly the same whitelisted native helper ABI as
		// the normal runtime Lua path.  onCreate remains represented by `start`.
		for (callback in callbacks) {
			if (callback.name == 'onCreate')
				continue;
			translateRuntimeCallback(callback, path, hscriptLines, diagnostics, runtimeCallbacks);
		}

		// Add a comment to the generated module so a scan log remains useful even
		// after the result has been copied into a custom stage folder.
		if (diagnostics.length > 0) {
			var first = diagnostics[0];
			hscriptLines.insert(0, '// PsychStageCompat: static translation has ' + diagnostics.length
				+ ' diagnostic(s); see importer scan log.');
		}
		return result(hscriptLines, diagnostics, sprites, assets, defaultZoom, stagePosition, characterPositions,
			runtimeCallbacks);
	}

	/** Static stage setup may select Psych's per-song game-over actor and audio. Keep
	 * dynamic class/property expressions diagnosed instead of guessing them. */
	static function translateSetPropertyFromClass(call:PsychStageCall, line:Int, path:String,
		output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length != 3) {
			diagnostics.push(makeDiagnostic('warning', 'unsupported-stage-api',
				'setPropertyFromClass() requires three literal arguments in stage setup.', line, path));
			return;
		}
		var className = stringLiteral(call.args[0]);
		var property = stringLiteral(call.args[1]);
		var value = stringLiteral(call.args[2]);
		var classKey = className.toLowerCase();
		var propertyKey = property.toLowerCase();
		if ((classKey != 'gameoversubstate' && !classKey.endsWith('.gameoversubstate'))
			|| ['charactername', 'deathsoundname', 'loopsoundname', 'endsoundname'].indexOf(propertyKey) < 0
			|| value == '') {
			diagnostics.push(makeDiagnostic('warning', 'unsupported-stage-api',
				'Psych stage API setPropertyFromClass() has an unsupported class, property, or dynamic value.', line, path));
			return;
		}
		output.push('currentPlayState.setPsychClassProperty("' + quote(className) + '", "'
			+ quote(property) + '", "' + quote(value) + '");');
	}

	#if sys
	/** Read and translate one stage file. The donor file is read-only. */
	public static function translateFile(path:String):PsychStageTranslation {
		return translate(File.getContent(path), path);
	}
	#end

	static function result(lines:Array<String>, diagnostics:Array<PsychStageDiagnostic>, sprites:Array<PsychStageSprite>,
		assets:Array<PsychStageAssetMapping>,
		defaultZoom:Null<Float>, stagePosition:Null<PsychStagePoint>, characterPositions:Map<String, PsychStagePoint>,
		runtimeCallbacks:Array<String>):PsychStageTranslation {
		var output = lines.copy();
		if (output.length == 0 || output[output.length - 1] != '')
			output.push('');
		return {
			hscript: output.join('\n'),
			supported: diagnostics.length == 0,
			diagnostics: diagnostics,
			sprites: sprites,
			assets: assets,
			defaultZoom: defaultZoom,
			stagePosition: stagePosition,
			characterPositions: characterPositions,
			runtimeCallbacks: runtimeCallbacks
		};
	}

	static function translateMakeSprite(call:PsychStageCall, animated:Bool, line:Int, path:String,
		numericVars:Map<String, Float>, sprites:Array<PsychStageSprite>, assets:Array<PsychStageAssetMapping>,
		spriteByTag:Map<String, PsychStageSprite>,
		identifiers:Map<String, String>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 2) {
			diagnostics.push(makeDiagnostic('error', 'invalid-stage-sprite',
				call.name + '() needs at least a tag and image path.', line, path));
			return;
		}
		var tag = stringLiteral(call.args[0]);
		var image = stringLiteral(call.args[1]);
		if (tag == '' || image == '') {
			diagnostics.push(makeDiagnostic('error', 'invalid-stage-sprite',
				call.name + '() requires literal tag and image values for static conversion.', line, path));
			return;
		}
		var x = numericExpression(call.args.length > 2 ? call.args[2] : '0', numericVars);
		var y = numericExpression(call.args.length > 3 ? call.args[3] : '0', numericVars);
		if (x == null || y == null) {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-position',
				'Could not statically resolve ' + tag + '() position; using 0,0 in generated setup.', line, path));
			x = 0;
			y = 0;
		}
		var sprite:PsychStageSprite = {
			tag: tag,
			image: image,
			x: x,
			y: y,
			animated: animated,
			front: false,
			scaleX: 1,
			scaleY: 1,
			scrollX: 1,
			scrollY: 1,
			camera: 'camGame',
			animations: [],
			initialAnimation: '',
			added: false,
			removed: false,
			order: null
		};
		if (spriteByTag.exists(tag)) {
			diagnostics.push(makeDiagnostic('warning', 'duplicate-stage-sprite',
				'Psych stage created sprite tag ' + tag + ' more than once; the later construction replaces the static metadata.', line, path));
			var previous = spriteByTag.get(tag);
			sprites.remove(previous);
		}
		spriteByTag.set(tag, sprite);
		sprites.push(sprite);
		var identifier = '__psychStage_' + safeIdentifier(tag);
		if (identifiers.exists(tag))
			identifier += '_' + sprites.length;
		identifiers.set(tag, identifier);
		// Use the same native helper as the live Lua path. Besides keeping asset
		// resolution centralized, this registers the tag in haxeSprites so a
		// runtime onUpdate/onEvent callback can find the object created by this
		// static fallback and remove/reorder it later.
		output.push('var ' + identifier + ' = ' + (animated ? 'makeAnimatedLuaSprite' : 'makeLuaSprite')
			+ '("' + quote(tag) + '", "' + quote(image) + '", ' + formatNumber(x) + ', ' + formatNumber(y) + ');');
		var png = imagePath(image);
		var xml = xmlPath(image);
		assets.push({sourceKey: image, destination: 'assets/images/' + png + '.png',
			xmlDestination: 'assets/images/' + xml, animated: animated});
	}

	static function translateAnimationPrefix(call:PsychStageCall, line:Int, path:String, numericVars:Map<String, Float>,
		spriteByTag:Map<String, PsychStageSprite>, identifiers:Map<String, String>, output:Array<String>,
		diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 3) {
			diagnostics.push(makeDiagnostic('warning', 'invalid-stage-animation',
				'addAnimationByPrefix() needs a tag, animation name, and prefix.', line, path));
			return;
		}
		var tag = stringLiteral(call.args[0]);
		var sprite = spriteByTag.get(tag);
		if (sprite == null) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'Animation references stage sprite tag ' + tag + ' before static construction.', line, path));
			return;
		}
		var fps = numericExpression(call.args.length > 3 ? call.args[3] : '24', numericVars);
		if (fps == null)
			fps = 24;
		var looped = call.args.length < 5 || boolLiteral(call.args[4], true);
		var animationName = stringLiteral(call.args[1]);
		var prefix = stringLiteral(call.args[2]);
		sprite.animations.push({name: animationName, prefix: prefix, fps: fps, looped: looped, indices: []});
		var id = identifiers.get(tag);
		if (id != null)
			output.push('addAnimationByPrefix("' + quote(tag) + '", "' + quote(animationName) + '", "'
				+ quote(prefix) + '", ' + formatNumber(fps) + ', ' + (looped ? 'true' : 'false') + ');');
	}

	static function translateAnimationIndices(call:PsychStageCall, line:Int, path:String, numericVars:Map<String, Float>,
		spriteByTag:Map<String, PsychStageSprite>, identifiers:Map<String, String>, output:Array<String>,
		diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 3) {
			diagnostics.push(makeDiagnostic('warning', 'invalid-stage-animation',
				'addAnimationByIndices() needs a tag, animation name, and prefix.', line, path));
			return;
		}
		var tag = stringLiteral(call.args[0]);
		var sprite = spriteByTag.get(tag);
		if (sprite == null) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'Animation references stage sprite tag ' + tag + ' before static construction.', line, path));
			return;
		}
		var indices = parseIntArray(call.args.length > 3 ? call.args[3] : '[]');
		var fps = numericExpression(call.args.length > 4 ? call.args[4] : '24', numericVars);
		if (fps == null)
			fps = 24;
		var looped = call.args.length < 6 || boolLiteral(call.args[5], true);
		var animationName = stringLiteral(call.args[1]);
		var prefix = stringLiteral(call.args[2]);
		sprite.animations.push({name: animationName, prefix: prefix, fps: fps, looped: looped, indices: indices});
		var id = identifiers.get(tag);
		if (id != null)
			output.push('addAnimationByIndices("' + quote(tag) + '", "' + quote(animationName) + '", "'
				+ quote(prefix) + '", [' + indices.join(', ') + '], ' + formatNumber(fps) + ', '
				+ (looped ? 'true' : 'false') + ');');
	}

	static function translatePlayAnimation(call:PsychStageCall, line:Int, path:String,
		spriteByTag:Map<String, PsychStageSprite>, identifiers:Map<String, String>, output:Array<String>,
		diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 2)
			return;
		var tag = stringLiteral(call.args[0]);
		var sprite = spriteByTag.get(tag);
		if (sprite == null) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'Animation playback references stage sprite tag ' + tag + ' before static construction.', line, path));
			return;
		}
		sprite.initialAnimation = stringLiteral(call.args[1]);
		var id = identifiers.get(tag);
		if (id != null)
			output.push('objectPlayAnimation("' + quote(tag) + '", "' + quote(sprite.initialAnimation) + '", true);');
	}

	static function translateScale(call:PsychStageCall, line:Int, path:String, numericVars:Map<String, Float>,
		spriteByTag:Map<String, PsychStageSprite>, identifiers:Map<String, String>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 2)
			return;
		var tag = stringLiteral(call.args[0]);
		var sprite = spriteByTag.get(tag);
		if (sprite == null) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'Scale references stage sprite tag ' + tag + ' before static construction.', line, path));
			return;
		}
		var x = numericExpression(call.args[1], numericVars);
		var y = numericExpression(call.args.length > 2 ? call.args[2] : call.args[1], numericVars);
		if (x == null || y == null) {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-scale',
				'Could not statically resolve scaleObject(' + tag + ', ...); using 1,1.', line, path));
			x = 1;
			y = 1;
		}
		sprite.scaleX = x;
		sprite.scaleY = y;
		var id = identifiers.get(tag);
		if (id != null)
			output.push('scaleObject("' + quote(tag) + '", ' + formatNumber(x) + ', ' + formatNumber(y) + ');');
	}

	/** Lower Psych's tagged graphic-size helper only when its sprite and dimensions are static. */
	static function translateGraphicSize(call:PsychStageCall, line:Int, path:String, numericVars:Map<String, Float>,
		spriteByTag:Map<String, PsychStageSprite>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 2 || call.args.length > 3) {
			diagnostics.push(makeDiagnostic('warning', 'invalid-stage-graphic-size',
				'setGraphicSize() needs a literal sprite tag, width, and optional height.', line, path));
			return;
		}
		var tag = stringLiteral(call.args[0]);
		if (tag == '') {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-target',
				'setGraphicSize() requires a literal sprite tag in static setup.', line, path));
			return;
		}
		if (!spriteByTag.exists(tag)) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'setGraphicSize() references stage sprite tag ' + tag + ' before construction.', line, path));
			return;
		}
		var width = numericExpression(call.args[1], numericVars);
		var height = call.args.length > 2 ? numericExpression(call.args[2], numericVars) : null;
		if (width == null || (call.args.length > 2 && height == null)) {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-graphic-size',
				'setGraphicSize(' + tag + ', ...) has a dynamic dimension and was not emitted.', line, path));
			return;
		}
		var arguments = '"' + quote(tag) + '", ' + formatNumber(Std.int(width));
		if (height != null)
			arguments += ', ' + formatNumber(Std.int(height));
		output.push('setGraphicSize(' + arguments + ');');
	}

	/** Resolve a tagged sprite before asking FlxSprite to recompute its hitbox. */
	static function translateUpdateHitbox(call:PsychStageCall, line:Int, path:String,
		spriteByTag:Map<String, PsychStageSprite>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length != 1) {
			diagnostics.push(makeDiagnostic('warning', 'invalid-stage-hitbox',
				'updateHitbox() needs exactly one literal sprite tag.', line, path));
			return;
		}
		var tag = stringLiteral(call.args[0]);
		if (tag == '') {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-target',
				'updateHitbox() requires a literal sprite tag in static setup.', line, path));
			return;
		}
		if (!spriteByTag.exists(tag)) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'updateHitbox() references stage sprite tag ' + tag + ' before construction.', line, path));
			return;
		}
		output.push('updateHitbox("' + quote(tag) + '");');
	}

	/** Keep Psych blend names on the existing shared engine compatibility bridge. */
	static function translateBlendMode(call:PsychStageCall, line:Int, path:String,
		spriteByTag:Map<String, PsychStageSprite>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length != 2) {
			diagnostics.push(makeDiagnostic('warning', 'invalid-stage-blend-mode',
				'setBlendMode() needs a literal sprite tag and blend mode.', line, path));
			return;
		}
		var tag = stringLiteral(call.args[0]);
		if (tag == '') {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-target',
				'setBlendMode() requires a literal sprite tag in static setup.', line, path));
			return;
		}
		if (!spriteByTag.exists(tag)) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'setBlendMode() references stage sprite tag ' + tag + ' before construction.', line, path));
			return;
		}
		var authoredMode = stringLiteral(call.args[1]);
		if (authoredMode == '') {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-blend-mode',
				'setBlendMode(' + tag + ', ...) has a dynamic blend mode and was not emitted.', line, path));
			return;
		}
		var mode = authoredMode.toLowerCase();
		if (!isPsychBlendMode(mode)) {
			diagnostics.push(makeDiagnostic('warning', 'unsupported-stage-blend-mode',
				'setBlendMode(' + tag + ', ' + authoredMode + ') uses an unsupported blend mode.', line, path));
			return;
		}
		output.push('setBlendMode("' + quote(tag) + '", "' + quote(mode) + '");');
	}

	static function isPsychBlendMode(mode:String):Bool {
		return switch (mode) {
			case 'add' | 'alpha' | 'darken' | 'difference' | 'erase' | 'hardlight' | 'invert' | 'layer'
				| 'lighten' | 'multiply' | 'normal' | 'overlay' | 'screen' | 'shader' | 'subtract': true;
			default: false;
		};
	}

	static function translateScroll(call:PsychStageCall, line:Int, path:String, numericVars:Map<String, Float>,
		spriteByTag:Map<String, PsychStageSprite>, identifiers:Map<String, String>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 2)
			return;
		var tag = stringLiteral(call.args[0]);
		var sprite = spriteByTag.get(tag);
		if (sprite == null) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'Scroll factor references stage sprite tag ' + tag + ' before construction.', line, path));
			return;
		}
		var x = numericExpression(call.args[1], numericVars);
		var y = numericExpression(call.args.length > 2 ? call.args[2] : call.args[1], numericVars);
		if (x == null || y == null) {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-scroll',
				'Could not statically resolve scroll factor for ' + tag + '; using 1,1.', line, path));
			x = 1;
			y = 1;
		}
		sprite.scrollX = x;
		sprite.scrollY = y;
		var id = identifiers.get(tag);
		if (id != null)
			output.push('setScrollFactor("' + quote(tag) + '", ' + formatNumber(x) + ', ' + formatNumber(y) + ');');
	}

	static function translateCamera(call:PsychStageCall, line:Int, path:String,
		spriteByTag:Map<String, PsychStageSprite>, identifiers:Map<String, String>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 2)
			return;
		var tag = stringLiteral(call.args[0]);
		var sprite = spriteByTag.get(tag);
		if (sprite == null) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'Camera assignment references stage sprite tag ' + tag + ' before construction.', line, path));
			return;
		}
		var camera = stringLiteral(call.args[1]).toLowerCase();
		var canonical = camera == 'hud' || camera == 'camhud' || camera == 'other' || camera == 'camother' ? 'camHUD' : 'camGame';
		sprite.camera = canonical;
	var id = identifiers.get(tag);
		if (id != null)
			output.push('setObjectCamera("' + quote(tag) + '", "' + canonical + '");');
	}

	static function translateAddSprite(call:PsychStageCall, line:Int, path:String,
		spriteByTag:Map<String, PsychStageSprite>, identifiers:Map<String, String>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 1)
			return;
		var tag = stringLiteral(call.args[0]);
		var sprite = spriteByTag.get(tag);
		if (sprite == null) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'addLuaSprite() references stage sprite tag ' + tag + ' before construction.', line, path));
			return;
		}
		var layer = call.args.length > 1 ? call.args[1].trim().toLowerCase() : '';
		var front = layer == 'true';
		if (call.args.length > 1 && layer != 'true' && layer != 'false' && layer != 'nil')
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-layer',
				'addLuaSprite() has a layer expression that cannot be resolved statically; using the back layer.', line, path));
		sprite.front = front;
		sprite.added = true;
		var id = identifiers.get(tag);
		if (id != null)
			output.push('addLuaSprite("' + quote(tag) + '", ' + (front ? 'true' : 'false') + ');');
	}

	/** Only consume a standalone literal close(true) at the end of onCreate. */
	static function isTerminalStaticClose(call:PsychStageCall, source:String, calls:Array<PsychStageCall>, callIndex:Int):Bool {
		if (call.args.length != 1 || call.args[0].trim() != 'true' || callIndex != calls.length - 1)
			return false;
		var open = call.start + call.name.length;
		while (open < source.length && isWhitespace(source.charAt(open)))
			open++;
		if (open >= source.length || source.charAt(open) != '(')
			return false;
		var close = matchingParen(source, open);
		if (close < 0)
			return false;
		// A close nested in an expression or preceded by another token on the
		// same statement is not a terminal cleanup call.
		var statementStart = source.lastIndexOf('\n', call.start - 1);
		var semicolonStart = source.lastIndexOf(';', call.start - 1);
		if (semicolonStart > statementStart)
			statementStart = semicolonStart;
		if (source.substr(statementStart + 1, call.start - statementStart - 1).trim() != '')
			return false;
		var tail = source.substr(close + 1);
		return ~/^[\s;]*$/.match(tail);
	}

	/** Lower Psych's layer mutation API through the native object-order bridge. */
	static function translateObjectOrder(call:PsychStageCall, line:Int, path:String,
		numericVars:Map<String, Float>, spriteByTag:Map<String, PsychStageSprite>, output:Array<String>,
		diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 2) {
			diagnostics.push(makeDiagnostic('warning', 'invalid-stage-order',
				'setObjectOrder() needs an object tag and an order.', line, path));
			return;
		}
		var tag = stringLiteral(call.args[0]);
		if (tag == '') {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-order',
				'setObjectOrder() requires a literal object tag in static setup.', line, path));
			return;
		}
		var order = safeOrderExpression(call.args[1], numericVars);
		if (order == null) {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-order',
				'Could not statically resolve setObjectOrder(' + tag + ', ...); runtime LuaCompat will handle it.', line, path));
			return;
		}
		var front = call.args.length > 2 ? boolLiteral(call.args[2], false) : false;
		var sprite = spriteByTag.get(tag);
		if (sprite != null) {
			var literalOrder = numericExpression(call.args[1], numericVars);
			if (literalOrder != null)
				sprite.order = Std.int(literalOrder);
		}
		output.push('setObjectOrder("' + quote(tag) + '", ' + order + ', ' + (front ? 'true' : 'false') + ');');
	}

	/** Lower removal while keeping the authored destroy flag intact. */
	static function translateRemoveObject(call:PsychStageCall, line:Int, path:String,
		spriteByTag:Map<String, PsychStageSprite>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 1) {
			diagnostics.push(makeDiagnostic('warning', 'invalid-stage-removal',
				call.name + '() needs an object tag.', line, path));
			return;
		}
		var tag = stringLiteral(call.args[0]);
		if (tag == '') {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-removal',
				call.name + '() requires a literal object tag in static setup.', line, path));
			return;
		}
		var destroy = call.args.length < 2 || boolLiteral(call.args[1], true);
		var sprite = spriteByTag.get(tag);
		if (sprite != null)
			sprite.removed = true;
		// removeLuaText shares the haxeSprites registry in PlayState, so the
		// central removeLuaSprite bridge preserves both sprite and text tags.
		output.push('removeLuaSprite("' + quote(tag) + '", ' + (destroy ? 'true' : 'false') + ');');
	}

	static function translateScreenCenter(call:PsychStageCall, line:Int, path:String,
		spriteByTag:Map<String, PsychStageSprite>, identifiers:Map<String, String>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>):Void {
		if (call.args.length < 1)
			return;
		var tag = stringLiteral(call.args[0]);
		if (!spriteByTag.exists(tag)) {
			diagnostics.push(makeDiagnostic('warning', 'unknown-stage-sprite',
				'screenCenter() references stage sprite tag ' + tag + ' before construction.', line, path));
			return;
		}
		var id = identifiers.get(tag);
		if (id == null)
			return;
		var axis = call.args.length > 1 ? stringLiteral(call.args[1]).toUpperCase() : '';
		if (axis == 'X' || axis == 'Y')
			output.push('screenCenter("' + quote(tag) + '", "' + axis + '");');
		else
			output.push('screenCenter("' + quote(tag) + '");');
	}

	static function translateSetProperty(call:PsychStageCall, line:Int, path:String, numericVars:Map<String, Float>,
		spriteByTag:Map<String, PsychStageSprite>, identifiers:Map<String, String>, output:Array<String>, diagnostics:Array<PsychStageDiagnostic>,
		characterPositions:Map<String, PsychStagePoint>, stagePosition:Null<PsychStagePoint>, defaultZoom:Null<Float>):Dynamic {
		if (call.args.length < 2)
			return {stagePosition: stagePosition, defaultZoom: defaultZoom};
		var property = stringLiteral(call.args[0]);
		var value = call.args[1];
		if (property == '') {
			diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-property',
				'setProperty() requires a literal property path in static setup.', line, path));
			return {stagePosition: stagePosition, defaultZoom: defaultZoom};
		}
		var lower = property.toLowerCase();
		if (lower == 'defaultcamzoom') {
			var zoom = numericExpression(value, numericVars);
			if (zoom == null) {
				diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-zoom',
					'defaultCamZoom is not a static number and was not emitted.', line, path));
			} else {
				defaultZoom = zoom;
				output.push('setDefaultZoom(' + formatNumber(zoom) + ');');
			}
			return {stagePosition: stagePosition, defaultZoom: defaultZoom};
		}
		if (lower == 'camgame.bgcolor') {
			var color = colorExpression(value);
			if (color == null) {
				diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-color',
					'camGame.bgColor uses an unsupported dynamic expression.', line, path));
			} else {
				output.push('camGame.bgColor = ' + color + ';');
			}
			return {stagePosition: stagePosition, defaultZoom: defaultZoom};
		}
		var dot = property.indexOf('.');
		if (dot > 0) {
			var target = property.substr(0, dot);
			var field = property.substr(dot + 1).toLowerCase();
			if (field == 'visible' || field == 'flipx' || field == 'flipy') {
				var booleanValue = value.trim().toLowerCase();
				if (spriteByTag.exists(target) && (booleanValue == 'true' || booleanValue == 'false')) {
					output.push('setProperty("' + quote(property) + '", ' + booleanValue + ');');
				} else if (spriteByTag.exists(target)) {
					diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-property',
						'Boolean property ' + property + ' is not a literal boolean and was not emitted.', line, path));
				} else {
					diagnostics.push(makeDiagnostic('warning', 'unknown-stage-property',
						'Boolean property target ' + target + ' is not a known stage sprite.', line, path));
				}
				return {stagePosition: stagePosition, defaultZoom: defaultZoom};
			}
			var numeric = numericExpression(value, numericVars);
			if (field == 'alpha') {
				if (!spriteByTag.exists(target)) {
					diagnostics.push(makeDiagnostic('warning', 'unknown-stage-property',
						'Alpha property target ' + target + ' is not a known stage sprite.', line, path));
				} else if (numeric == null) {
					diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-property',
						'Alpha property ' + property + ' is dynamic and was not emitted.', line, path));
				} else {
					output.push('setProperty("' + quote(property) + '", ' + formatNumber(numeric) + ');');
				}
				return {stagePosition: stagePosition, defaultZoom: defaultZoom};
			}
			if (field == 'x' || field == 'y') {
				if (numeric == null) {
					diagnostics.push(makeDiagnostic('warning', 'dynamic-stage-property',
						'Position property ' + property + ' is dynamic and was not emitted.', line, path));
				} else if (target.toLowerCase() == 'stage') {
					var current:PsychStagePoint = stagePosition == null ? {x: 0.0, y: 0.0} : stagePosition;
					if (field == 'x') current.x = numeric; else current.y = numeric;
					stagePosition = current;
					output.push('stage.' + field + ' = ' + formatNumber(numeric) + ';');
				} else if (target.toLowerCase() == 'boyfriend' || target.toLowerCase() == 'bf'
					|| target.toLowerCase() == 'boyfriendgroup' || target.toLowerCase() == 'dad'
					|| target.toLowerCase() == 'dadgroup' || target.toLowerCase() == 'gf'
					|| target.toLowerCase() == 'gfgroup') {
					var targetName = target.toLowerCase();
					var key = targetName == 'boyfriend' || targetName == 'boyfriendgroup' ? 'bf'
						: targetName == 'dadgroup' ? 'dad' : targetName == 'gfgroup' ? 'gf' : targetName;
					var charPoint:PsychStagePoint = characterPositions.exists(key) ? characterPositions.get(key) : {x: 0.0, y: 0.0};
					if (field == 'x') charPoint.x = numeric; else charPoint.y = numeric;
					characterPositions.set(key, charPoint);
					var actor = key == 'bf' ? 'boyfriend' : key;
					output.push(actor + '.' + field + ' = ' + formatNumber(numeric) + ';');
				} else if (spriteByTag.exists(target)) {
					var sprite = spriteByTag.get(target);
					if (field == 'x') sprite.x = numeric; else sprite.y = numeric;
					var id = identifiers.get(target);
					if (id != null)
						output.push(id + '.' + field + ' = ' + formatNumber(numeric) + ';');
				} else {
					diagnostics.push(makeDiagnostic('warning', 'unknown-stage-property',
						'Position property target ' + target + ' is not a known stage sprite or actor.', line, path));
				}
				return {stagePosition: stagePosition, defaultZoom: defaultZoom};
			}
		}
		diagnostics.push(makeDiagnostic('warning', 'unsupported-stage-property',
			'Psych stage property ' + property + ' is not represented by the static translator.', line, path));
		return {stagePosition: stagePosition, defaultZoom: defaultZoom};
	}

	/**
		Return a whitelisted order expression for static setObjectOrder().  The
		mounted corpus uses both literal orders and getObjectOrder(tag) +/- a
		small offset. Do not copy arbitrary Lua/Haxe expressions into generated
		HScript; unsupported expressions remain runtime-only and diagnosed.
	*/
	static function safeOrderExpression(expression:String, vars:Map<String, Float>):Null<String> {
		if (expression == null)
			return null;
		var text = expression.trim();
		var number = numericExpression(text, vars);
		if (number != null)
			return formatNumber(number);
		while (text.startsWith('(') && text.endsWith(')') && matchingParen(text, 0) == text.length - 1)
			text = text.substr(1, text.length - 2).trim();
		var matcher = ~/^getObjectOrder\s*\(\s*(['"])(.*?)\1\s*\)$/;
		if (matcher.match(text))
			return 'getObjectOrder("' + quote(matcher.matched(2)) + '")';
		var parts = splitNumericOperator(text);
		if (parts == null)
			return null;
		var left = safeOrderExpression(parts.left, vars);
		var right = safeOrderExpression(parts.right, vars);
		if (left == null || right == null)
			return null;
		return '(' + left + ' ' + parts.op + ' ' + right + ')';
	}

	/**
		Collect state shared by static construction and runtime callbacks. Only
		plain assignments with a safe literal/numeric RHS are hoisted. This keeps
		the fallback deterministic while leaving loops, tables, and arbitrary
		calls to LuaCompat's diagnosed subset.
	*/
	static function collectStateAssignments(lines:Array<String>, onCreate:PsychStageBody,
		callbacks:Array<PsychStageCallback>, vars:Map<String, Float>, defaults:Map<String, String>,
		order:Array<String>, onCreateAssignments:Array<PsychStageStateAssignment>):Void {
		var firstCallback = lines.length;
		for (i in 0...lines.length)
			if (callbackName(lines[i]) != null) {
				firstCallback = i;
				break;
			}
		for (i in 0...firstCallback)
			collectStateAssignmentLine(lines[i], vars, defaults, order, null);
		if (onCreate.found) {
			for (line in onCreate.text.split('\n')) {
				var assignment = parseStateAssignment(line);
				if (assignment == null)
					continue;
				var value = safeAssignmentValue(assignment.value, vars);
				if (value == null)
					continue;
				if (!defaults.exists(assignment.name))
					rememberState(defaults, order, assignment.name, 'null');
				onCreateAssignments.push({name: assignment.name, value: assignment.value});
			}
		}
		// A callback may introduce a global on its first invocation (Haven's
		// resetting flags are initialized in onCreate, but donor scripts often
		// assign counters lazily). Declare only non-local plain assignments so
		// generated callbacks never reach an undeclared HScript slot.
		for (callback in callbacks)
			for (line in callback.body.split('\n')) {
				var assignment = parseStateAssignment(line);
				if (assignment == null || assignment.local)
					continue;
				if (!defaults.exists(assignment.name))
					rememberState(defaults, order, assignment.name, 'null');
			}
	}

	static function parseStateAssignment(line:String):Null<PsychStageParsedAssignment> {
		var clean = stripLineComment(line).trim();
		var matcher = ~/^(local\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*;?$/;
		if (!matcher.match(clean))
			return null;
		return {local: matcher.matched(1) != null && matcher.matched(1) != '',
			name: matcher.matched(2), value: matcher.matched(3)};
	}

	static function collectStateAssignmentLine(line:String, vars:Map<String, Float>, defaults:Map<String, String>,
		order:Array<String>, onCreateAssignments:Null<Array<PsychStageStateAssignment>>):Void {
		var assignment = parseStateAssignment(line);
		if (assignment == null)
			return;
		var value = safeAssignmentValue(assignment.value, vars);
		if (value == null)
			return;
		rememberState(defaults, order, assignment.name, value);
		if (onCreateAssignments != null)
			onCreateAssignments.push({name: assignment.name, value: assignment.value});
	}

	static function rememberState(defaults:Map<String, String>, order:Array<String>, name:String, value:String):Void {
		if (!defaults.exists(name))
			order.push(name);
		defaults.set(name, value);
	}

	static function safeAssignmentValue(expression:String, vars:Map<String, Float>):Null<String> {
		if (expression == null)
			return null;
		var text = expression.trim();
		var number = numericExpression(text, vars);
		if (number != null)
			return formatNumber(number);
		if (text == 'true' || text == 'false')
			return text;
		if (text == 'nil' || text == 'null')
			return 'null';
		var value = stringLiteral(text);
		if (text.length >= 2 && ((text.charAt(0) == '"' && text.charAt(text.length - 1) == '"')
			|| (text.charAt(0) == '\'' && text.charAt(text.length - 1) == '\'')))
			return '"' + quote(value) + '"';
		return null;
	}

	/** Extract all plain named callbacks, preserving declaration order. */
	static function findCallbacks(lines:Array<String>):Array<PsychStageCallback> {
		var result:Array<PsychStageCallback> = [];
		for (i in 0...lines.length) {
			var signature = callbackSignature(lines[i]);
			if (signature == null)
				continue;
			var body = findCallbackBody(lines, signature.name, i);
			result.push({name: signature.name, args: signature.args, body: body.text, startLine: i + 1});
		}
		return result;
	}

	static function callbackSignature(line:String):Null<{name:String, args:String}> {
		var matcher = ~/^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)/;
		if (!matcher.match(stripLineComment(line)))
			return null;
		return {name: matcher.matched(1), args: matcher.matched(2)};
	}

	/**
		Pass one callback through LuaCompat. Its diagnostics are attached to the
		stage source location so importer scans can distinguish unsupported runtime
		constructs from static sprite metadata findings.
	*/
	static function translateRuntimeCallback(callback:PsychStageCallback, path:String, output:Array<String>,
		diagnostics:Array<PsychStageDiagnostic>, runtimeCallbacks:Array<String>):Void {
		var snippet = 'function ' + callback.name + '(' + callback.args + ')\n' + callback.body + '\nend\n';
		var translated = LuaCompat.translate(snippet, path + '#' + callback.name, true);
		if (translated.hscript == null || StringTools.trim(translated.hscript) == '') {
			diagnostics.push(makeDiagnostic('warning', 'unsupported-stage-runtime',
				'Psych stage callback ' + callback.name + '() could not be converted by LuaCompat.',
				callback.startLine, path));
			return;
		}
		runtimeCallbacks.push(callback.name);
		for (line in translated.hscript.split('\n'))
			output.push(line);
		for (finding in translated.diagnostics) {
			var code = luaDiagnosticCode(finding);
			diagnostics.push(makeDiagnostic('warning', code,
				'Psych stage callback ' + callback.name + '(): ' + finding,
				callback.startLine, path));
		}
	}

	static function luaDiagnosticCode(finding:String):String {
		if (finding == null)
			return 'unsupported-stage-runtime';
		var start = finding.indexOf('[lua-');
		if (start < 0)
			return 'unsupported-stage-runtime';
		var end = finding.indexOf(']', start);
		if (end <= start)
			return 'unsupported-stage-runtime';
		return 'unsupported-stage-runtime-' + finding.substr(start + 5, end - start - 5);
	}

	static function findCallbackBody(lines:Array<String>, wanted:String, ?startAt:Int = 0):PsychStageBody {
		var inCallback = false;
		var depth = 0;
		var startLine = 1;
		var body:Array<String> = [];
		for (i in startAt...lines.length) {
			var line = stripLineComment(lines[i]);
			if (!inCallback) {
				var callback = callbackName(line);
				if (callback != wanted)
					continue;
				inCallback = true;
				depth = 1;
				startLine = i + 1;
				var open = line.indexOf(')');
				if (open >= 0 && open + 1 < line.length) {
					var inlineBody = line.substr(open + 1).trim();
					var inlineEnd = ~/^(.*)\bend\s*;?$/;
					if (inlineEnd.match(inlineBody))
						return {text: inlineEnd.matched(1).trim(), startLine: startLine, found: true};
					body.push(line.substr(open + 1));
				}
				continue;
			}
			var trimmed = line.trim();
			if (trimmed == 'end' || trimmed.startsWith('end ')) {
				depth--;
				if (depth <= 0)
					return {text: body.join('\n'), startLine: startLine, found: true};
				body.push(line);
				continue;
			}
			// Count nested control blocks so one-line `if ... then ... end`
			// statements (Haven.lua uses one) do not swallow the next callback.
			// `for ... do`/`while ... do` already contribute one opener through
			// their control keyword; a standalone `do` contributes its own.
			var delta = countWord(line, 'function') + countWord(line, 'if')
				+ countWord(line, 'for') + countWord(line, 'while');
			if (countWord(line, 'do') > 0 && countWord(line, 'for') == 0 && countWord(line, 'while') == 0)
				delta += countWord(line, 'do');
			delta -= countWord(line, 'end');
			depth += delta;
			if (depth <= 0)
				return {text: body.join('\n'), startLine: startLine, found: true};
			body.push(line);
		}
		return {text: body.join('\n'), startLine: startLine, found: inCallback};
	}

	static function callbackName(line:String):Null<String> {
		var matcher = ~/^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/;
		if (!matcher.match(line))
			return null;
		return matcher.matched(1);
	}

	static function countWord(line:String, word:String):Int {
		var count = 0;
		var matcher = new EReg('\\b' + word + '\\b', 'g');
		while (matcher.match(line)) {
			count++;
			line = line.substr(matcher.matchedPos().pos + matcher.matchedPos().len);
		}
		return count;
	}

	static function collectNumericAssignments(source:String, vars:Map<String, Float>):Void {
		for (line in source.split('\n')) {
			var matcher = ~/^\s*(?:local\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*;?\s*$/;
			if (!matcher.match(stripLineComment(line)))
				continue;
			var name = matcher.matched(1);
			var expression = matcher.matched(2);
			var value = numericExpression(expression, vars);
			if (value != null)
				vars.set(name, value);
		}
	}

	/** Return top-level calls in source order, including calls on one Lua line. */
	static function scanTopLevelCalls(source:String):Array<PsychStageCall> {
		var calls:Array<PsychStageCall> = [];
		var i = 0;
		while (i < source.length) {
			var c = source.charAt(i);
			if (c == '-' && i + 1 < source.length && source.charAt(i + 1) == '-') {
				var newline = source.indexOf('\n', i + 2);
				i = newline < 0 ? source.length : newline + 1;
				continue;
			}
			if (c == '"' || c == "'") {
				i = skipQuoted(source, i);
				continue;
			}
			if (!isIdentifierStart(c)) {
				i++;
				continue;
			}
			var start = i;
			i++;
			while (i < source.length && isIdentifierPart(source.charAt(i)))
				i++;
			var name = source.substr(start, i - start);
			while (i < source.length && isWhitespace(source.charAt(i)))
				i++;
			if (i >= source.length || source.charAt(i) != '(')
				continue;
			var end = matchingParen(source, i);
			if (end < 0)
				break;
			var rawArgs = source.substr(i + 1, end - i - 1);
			calls.push({name: name, args: splitArguments(rawArgs), start: start});
			i = end + 1;
		}
		return calls;
	}

	static function splitArguments(source:String):Array<String> {
		var result:Array<String> = [];
		var start = 0;
		var depth = 0;
		var quote = '';
		var i = 0;
		while (i < source.length) {
			var c = source.charAt(i);
			if (quote != '') {
				if (c == '\\') i += 2; else { if (c == quote) quote = ''; i++; }
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c == '(' || c == '[' || c == '{') depth++;
			else if (c == ')' || c == ']' || c == '}') depth--;
			else if (c == ',' && depth == 0) { result.push(source.substr(start, i - start).trim()); start = i + 1; }
			i++;
		}
		var last = source.substr(start).trim();
		if (last != '' || result.length > 0)
			result.push(last);
		return result;
	}

	static function matchingParen(source:String, open:Int):Int {
		var depth = 0;
		var quote = '';
		var i = open;
		while (i < source.length) {
			var c = source.charAt(i);
			if (quote != '') {
				if (c == '\\') i += 2; else { if (c == quote) quote = ''; i++; }
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c == '(') depth++;
			else if (c == ')') { depth--; if (depth == 0) return i; }
			i++;
		}
		return -1;
	}

	static function numericExpression(expression:String, vars:Map<String, Float>):Null<Float> {
		if (expression == null)
			return null;
		var text = expression.trim();
		while (text.startsWith('(') && text.endsWith(')') && matchingParen(text, 0) == text.length - 1)
			text = text.substr(1, text.length - 2).trim();
		var direct = Std.parseFloat(text);
		if (!Math.isNaN(direct) && (~/^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$/.match(text)))
			return direct;
		if (vars != null && vars.exists(text))
			return vars.get(text);
		var parts = splitNumericOperator(text);
		if (parts != null) {
			var left = numericExpression(parts.left, vars);
			var right = numericExpression(parts.right, vars);
			if (left == null || right == null)
				return null;
			return switch (parts.op) {
				case '+': left + right;
				case '-': left - right;
				case '*': left * right;
				case '/': right == 0 ? null : left / right;
				default: null;
			};
		}
		return null;
	}

	static function splitNumericOperator(text:String):Dynamic {
		var depth = 0;
		var quote = '';
		for (i in 0...text.length) {
			var c = text.charAt(i);
			if (quote != '') { if (c == quote && (i == 0 || text.charAt(i - 1) != '\\')) quote = ''; continue; }
			if (c == '"' || c == "'") { quote = c; continue; }
			if (c == '(') { depth++; continue; }
			if (c == ')') { depth--; continue; }
			if (depth != 0 || (c != '+' && c != '-' && c != '*' && c != '/')) continue;
			if ((c == '+' || c == '-') && i == 0) continue;
			if ((c == '+' || c == '-') && (text.charAt(i - 1) == 'e' || text.charAt(i - 1) == 'E')) continue;
			var left = text.substr(0, i).trim();
			var right = text.substr(i + 1).trim();
			if (left == '' || right == '') continue;
			return {left: left, right: right, op: c};
		}
		return null;
	}

	static function parseIntArray(text:String):Array<Int> {
		var result:Array<Int> = [];
		var clean = text.trim();
		if (clean.startsWith('{') && clean.endsWith('}')) clean = clean.substr(1, clean.length - 2);
		if (clean.startsWith('[') && clean.endsWith(']')) clean = clean.substr(1, clean.length - 2);
		for (part in clean.split(',')) {
			var value = Std.parseInt(part.trim());
			if (value != null) result.push(value);
		}
		return result;
	}

	static function colorExpression(text:String):Null<String> {
		var matcher = ~/^\s*getColorFromHex\s*\(\s*['"]([^'"]+)['"]\s*\)\s*$/;
		if (matcher.match(text)) return 'getColorFromHex("' + quote(matcher.matched(1)) + '")';
		var literal = stringLiteral(text);
		if (literal != '') return 'getColorFromHex("' + quote(literal) + '")';
		return null;
	}

	static function stringLiteral(text:String):String {
		var value = text == null ? '' : text.trim();
		if (value.length >= 2 && ((value.charAt(0) == '"' && value.charAt(value.length - 1) == '"')
			|| (value.charAt(0) == "'" && value.charAt(value.length - 1) == "'"))) {
			value = value.substr(1, value.length - 2);
			value = StringTools.replace(value, '\\' + text.charAt(0), text.charAt(0));
			return value;
		}
		return '';
	}

	static function boolLiteral(text:String, fallback:Bool):Bool {
		var value = text == null ? '' : text.trim().toLowerCase();
		if (value == 'true') return true;
		if (value == 'false') return false;
		return fallback;
	}

	static function imagePath(image:String):String {
		var clean = StringTools.replace(image, '\\', '/');
		while (clean.startsWith('/')) clean = clean.substr(1);
		if (clean.toLowerCase().startsWith('assets/images/')) clean = clean.substr('assets/images/'.length);
		else if (clean.toLowerCase().startsWith('images/')) clean = clean.substr('images/'.length);
		var lower = clean.toLowerCase();
		if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg'))
			clean = clean.substr(0, clean.lastIndexOf('.'));
		return clean;
	}

	static function xmlPath(image:String):String {
		return imagePath(image) + '.xml';
	}

	static function safeIdentifier(value:String):String {
		var result = '';
		for (i in 0...value.length) {
			var c = value.charAt(i);
			if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_') result += c;
			else result += '_';
		}
		if (result == '' || (result.charAt(0) >= '0' && result.charAt(0) <= '9')) result = '_' + result;
		return result;
	}

	static function formatNumber(value:Float):String {
		if (value == Math.ffloor(value)) return Std.string(Std.int(value));
		return Std.string(value);
	}

	static function quote(value:String):String {
		return StringTools.replace(StringTools.replace(value, '\\', '\\\\'), '"', '\\"');
	}

	static function stripLineComment(line:String):String {
		var quote = '';
		for (i in 0...line.length - 1) {
			var c = line.charAt(i);
			if (quote != '') { if (c == quote && (i == 0 || line.charAt(i - 1) != '\\')) quote = ''; continue; }
			if (c == '"' || c == "'") { quote = c; continue; }
			if (c == '-' && line.charAt(i + 1) == '-') return line.substr(0, i);
		}
		return line;
	}

	static function countNewlines(text:String):Int {
		var count = 0;
		for (i in 0...text.length) if (text.charAt(i) == '\n') count++;
		return count;
	}

	static function skipQuoted(text:String, start:Int):Int {
		var quote = text.charAt(start);
		var i = start + 1;
		while (i < text.length) {
			if (text.charAt(i) == '\\') { i += 2; continue; }
			if (text.charAt(i) == quote) return i + 1;
			i++;
		}
		return text.length;
	}

	static function isWhitespace(c:String):Bool return c == ' ' || c == '\t' || c == '\r' || c == '\n';
	static function isIdentifierStart(c:String):Bool return c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c == '_';
	static function isIdentifierPart(c:String):Bool return isIdentifierStart(c) || c >= '0' && c <= '9';

	static function makeDiagnostic(severity:String, code:String, message:String, line:Int, path:String):PsychStageDiagnostic {
		return {severity: severity, code: code, message: message, line: line, path: path};
	}
}
