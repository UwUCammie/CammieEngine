package;

using StringTools;

/** A bounded runtime expression retained by an imported cutscene timeline. */
typedef HxcCutsceneTime = {
	var kind:String;
	var value:Float;
	var source:String;
}

/** One literal asset lookup owned by a cutscene's manifest namespace. */
typedef HxcCutsceneAsset = {
	var kind:String;
	var key:String;
}

/** One data-only action for a future native cutscene runner. */
typedef HxcCutsceneAction = {
	var kind:String;
	@:optional var actor:String;
	@:optional var sprite:String;
	@:optional var layer:String;
	@:optional var visible:Bool;
	@:optional var asset:String;
	@:optional var target:String;
	@:optional var animation:String;
	@:optional var prefix:String;
	@:optional var x:Float;
	@:optional var y:Float;
	@:optional var value:Float;
	@:optional var intensity:Float;
	@:optional var color:Int;
	@:optional var fadeIn:Bool;
	@:optional var loop:Bool;
	@:optional var volume:Float;
	@:optional var fromVolume:Float;
	@:optional var antialiasing:Bool;
	@:optional var fps:Float;
	@:optional var looping:Bool;
	@:optional var duration:HxcCutsceneTime;
	@:optional var delay:HxcCutsceneTime;
	@:optional var ease:String;
	@:optional var expression:String;
	/** True when the action targets an engine-owned inherited value rather than a donor field. */
	@:optional var engineOwned:Bool;
	@:optional var dialoguePath:String;
	@:optional var dialogueColor:Int;
	@:optional var camera:String;
	@:optional var track:String;
	@:optional var onComplete:Array<HxcCutsceneAction>;
	@:optional var animations:Array<Dynamic>;
}

typedef HxcCutsceneEvent = {
	var at:HxcCutsceneTime;
	var callback:String;
	var actions:Array<HxcCutsceneAction>;
}

/** Serialized, manifest-relative description of one constructor-only HXC cutscene. */
typedef HxcCutsceneTimelineData = {
	var version:Int;
	var sourceClass:String;
	var sourcePath:String;
	var dialoguePath:String;
	var dialogueColor:Int;
	var initialActions:Array<HxcCutsceneAction>;
	var events:Array<HxcCutsceneEvent>;
	var dialogueEnd:Array<HxcCutsceneAction>;
	var dialogueEndDelay:HxcCutsceneTime;
	var assets:Array<HxcCutsceneAsset>;
	var diagnostics:Array<HxcCutsceneTimelineDiagnostic>;
}

typedef HxcCutsceneTimelineDiagnostic = {
	var severity:String;
	var code:String;
	var message:String;
}

typedef HxcCutsceneTimelineResult = {
	var recognized:Bool;
	var accepted:Bool;
	var timeline:Null<HxcCutsceneTimelineData>;
	var diagnostics:Array<HxcCutsceneTimelineDiagnostic>;
}

private typedef HxcCutsceneFunction = {
	var name:String;
	var arguments:String;
	var body:String;
	var start:Int;
}

private typedef HxcCutsceneCall = {
	var callee:String;
	var args:String;
	var start:Int;
	var end:Int;
}

private typedef HxcCutscenePlacedAction = {
	var position:Int;
	var action:HxcCutsceneAction;
}

/**
	Data-only lowering for the small ScriptedCutscene shape found in mounted FPS
	Plus packs.  The parser is intentionally lexical and conservative: it never
	constructs a donor object, evaluates a Haxe expression, or emits executable
	HScript.  An unsafe/partial shape returns `accepted=false` and no timeline.
*/
class HxcCutsceneTimeline {
	public static inline var VERSION:Int = 1;

	static var allowedEases:Array<String> = ['quadInOut'];

	public static function extract(source:String, path:String, className:String,
		baseClass:String):HxcCutsceneTimelineResult {
		var diagnostics:Array<HxcCutsceneTimelineDiagnostic> = [];
		var clean = stripComments(source == null ? '' : source);
		var constructor = findFunction(clean, 'new');
		if (constructor == null)
			return {recognized:false, accepted:false, timeline:null, diagnostics:diagnostics};

		var fields = collectFields(clean, constructor.start);
		var assignments = collectFieldAssignments(clean);
		var initialActions:Array<HxcCutscenePlacedAction> = [];
		var assets:Array<HxcCutsceneAsset> = [];
		var dialoguePath = '';
		var dialogueColor = 0xFFB3DFD8;
		var hadDialogue = false;
		var errors = 0;

		var dialoguePathMatch = new EReg(
			'Paths\\s*\\.\\s*json\\s*\\(\\s*["\\\']dialogue["\\\']\\s*,\\s*'
			+ '["\\\']data/songs/["\\\']\\s*\\+\\s*PlayState\\s*\\.\\s*SONG\\s*\\.\\s*song'
			+ '\\s*\\.\\s*toLowerCase\\s*\\(\\s*\\)\\s*\\)', 'm');
		if (dialoguePathMatch.match(constructor.body)) {
			dialoguePath = 'data/songs/{song}/dialogue.json';
		} else if (constructor.body.indexOf('new DialogueBox') >= 0) {
			errors++;
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dialogue-path',
				'DialogueBox JSON path is not the bounded song-local Paths.json form.');
		}

		var colorMatch = new EReg('\\bdialogueBgColor\\s*=\\s*(0x[0-9A-Fa-f]+|[0-9]+)', 'm');
		if (colorMatch.match(constructor.body)) {
			var parsedColor = parseInteger(colorMatch.matched(1));
			if (parsedColor == null) {
				errors++;
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dialogue-color',
					'Dialogue background color is not a finite integer literal.');
			} else
				dialogueColor = parsedColor;
		}
		if (constructor.body.indexOf('new DialogueBox') >= 0) {
			hadDialogue = true;
			var dialogueCall = firstCall(constructor.body, 'new\\s+DialogueBox');
			if (dialogueCall != null) {
				var dialogueArgs = splitArguments(dialogueCall.args);
				if (dialogueArgs.length != 2 || StringTools.trim(dialogueArgs[0]) != 'dialogue'
					|| StringTools.trim(dialogueArgs[1]) != 'dialogueBgColor') {
					errors++;
					diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dialogue-constructor',
						'DialogueBox must be created from the bounded sidecar and literal color variables.');
				}
			}
		}

		var spriteDiagnosticCount = diagnostics.length;
		var spriteDefinitions = collectSpriteDefinitions(constructor.body, diagnostics, assets);
		if (diagnostics.length > spriteDiagnosticCount)
			errors += diagnostics.length - spriteDiagnosticCount;
		for (placed in spriteDefinitions)
			initialActions.push(placed);

		var zoomCapture = new EReg('\\b(originalZoom)\\s*=\\s*playstate\\s*\\.\\s*defaultCamZoom\\s*;', 'g');
		var zoomBody = constructor.body;
		while (zoomCapture.match(zoomBody)) {
			var capturePosition = zoomCapture.matchedPos().pos;
			var capture:HxcCutsceneAction = {kind:'captureDefaultZoom', target:'originalZoom'};
			if (!fields.exists('originalZoom')) {
				capture.engineOwned = true;
				if (!hasDiagnostic(diagnostics, 'hxc-cutscene-adapter-engine-owned', 'originalZoom'))
					diagnose(diagnostics, 'info', 'hxc-cutscene-adapter-engine-owned',
						'Cutscene captures originalZoom through the engine-owned default zoom; no donor field is declared.');
			}
			initialActions.push({position:capturePosition, action:capture});
			var zoomPos = zoomCapture.matchedPos();
			if (zoomPos.len <= 0)
				break;
			zoomBody = zoomBody.substr(zoomPos.pos + zoomPos.len);
		}
		// The previous loop only works on a temporary string for diagnostics. The
		// constructor body is needed below, so recover it from the original source.
		constructor = findFunction(clean, 'new');

		if (hadDialogue) {
			var dialoguePosition = clean.indexOf('new DialogueBox');
			initialActions.push({position:dialoguePosition < 0 ? 0 : dialoguePosition,
				action:{kind:'dialogueConfig', dialoguePath:dialoguePath,
					dialogueColor:dialogueColor, camera:'hud'}});
		}

		var events:Array<HxcCutsceneEvent> = [];
		for (call in collectCallsAtDepth(constructor.body, 'addEvent', 0)) {
			var eventArgs = splitArguments(call.args);
			if (eventArgs.length != 2) {
				errors++;
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-event-shape',
					'addEvent requires exactly a bounded timestamp and helper name.');
				continue;
			}
			var at = parseTime(eventArgs[0]);
			var callback = StringTools.trim(eventArgs[1]);
			if (at == null || !isIdentifier(callback)) {
				errors++;
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-event-dynamic',
					'addEvent timestamp/callback must be literal and statically named.');
				continue;
			}
			var method = findFunction(clean, callback);
			if (method == null) {
				errors++;
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-event-helper',
					'addEvent callback has no statically discoverable method: ' + callback);
				continue;
			}
			var parsed = parseEventBody(method.body, fields, assignments, diagnostics, assets);
			if (!parsed.safe) {
				errors++;
				continue;
			}
			events.push({at:at, callback:callback, actions:parsed.actions});
		}
		for (index in 1...events.length) {
			if (timeOrder(events[index - 1].at, events[index].at) > 0) {
				errors++;
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-event-order',
					'addEvent timestamps must be nondecreasing; equal timestamps retain source order.');
				break;
			}
		}

		var completion = parseDialogueCompletion(clean, fields, assignments, diagnostics, assets);
		if (!completion.safe)
			errors++;
		if (!hadDialogue) {
			errors++;
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dialogue',
				'Constructor-only cutscene has no bounded DialogueBox sidecar boundary.');
		}

		var topCalls = collectAllCallsAtDepth(constructor.body, 0);
		for (call in topCalls) {
			if (call.callee == 'playstate.camMove') {
				var cameraMove = parseCameraMove(call, diagnostics);
				if (cameraMove == null)
					errors++;
				else
					initialActions.push({position:call.start, action:cameraMove});
				continue;
			}
			if (call.callee == 'playstate.camChangeZoom') {
				var cameraZoom = parseCameraZoom(call, fields, diagnostics);
				if (cameraZoom == null)
					errors++;
				else
					initialActions.push({position:call.start, action:cameraZoom});
				continue;
			}
			if (call.callee == 'playstate.camShake') {
				var cameraShake = parseCameraShake(call, diagnostics);
				if (cameraShake == null)
					errors++;
				else
					initialActions.push({position:call.start, action:cameraShake});
				continue;
			}
			if (isConstructorAllowedCall(call.callee))
				continue;
			if (call.callee == 'addEvent' || call.callee == 'new\\s+DialogueBox')
				continue;
			if (call.callee == 'Paths.json' || call.callee == 'Json.parse'
				|| call.callee == 'Utils.getText' || call.callee == 'super')
				continue;
			// Top-level helper calls are deliberately rejected rather than emitted as
			// HScript. Nested onDialogueEnd/addEvent bodies are handled separately.
			errors++;
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-helper',
				'Unmapped constructor helper/call remains in the cutscene: ' + call.callee);
		}

		if (events.length == 0) {
			errors++;
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-events',
			'No bounded addEvent timeline was found.');
		}

		initialActions.sort(function(a, b):Int return a.position - b.position);
		var initial:Array<HxcCutsceneAction> = [];
		for (placed in initialActions)
			initial.push(placed.action);

		var timeline:HxcCutsceneTimelineData = {
			version:VERSION,
			sourceClass:className == null ? '' : className,
			sourcePath:manifestPath(path),
			dialoguePath:dialoguePath,
			dialogueColor:dialogueColor,
			initialActions:initial,
			events:events,
			dialogueEnd:completion.actions,
			dialogueEndDelay:completion.delay,
			assets:assets,
			diagnostics:diagnostics.copy()
		};
		return {
			recognized:true,
			accepted:errors == 0,
			timeline:errors == 0 ? timeline : null,
			diagnostics:diagnostics
		};
	}

	static function parseEventBody(body:String, fields:Map<String, Bool>,
		assignments:Map<String, Bool>, diagnostics:Array<HxcCutsceneTimelineDiagnostic>,
		assets:Array<HxcCutsceneAsset>):{safe:Bool, actions:Array<HxcCutsceneAction>} {
		var placed:Array<HxcCutscenePlacedAction> = [];
		var safe = true;
		for (call in collectAllCallsAtDepth(body, 0)) {
			var action:HxcCutsceneAction = null;
			switch (call.callee) {
				case 'addToBackgroundLayer' | 'addToCharacterLayer':
					var addArgs = splitArguments(call.args);
					if (addArgs.length != 1 || !isIdentifier(StringTools.trim(addArgs[0]))) {
						safe = false;
						diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-layer',
							'Layer insertion requires one statically named sprite.');
					} else
						action = {kind:'spriteAdd', sprite:StringTools.trim(addArgs[0]),
							layer:call.callee == 'addToBackgroundLayer' ? 'background' : 'character'};
				case 'removeFromBackgroundLayer' | 'removeFromCharacterLayer':
					var removeArgs = splitArguments(call.args);
					if (removeArgs.length != 1 || !isIdentifier(StringTools.trim(removeArgs[0]))) {
						safe = false;
						diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-layer',
							'Layer removal requires one statically named sprite.');
					} else
						action = {kind:'spriteRemove', sprite:StringTools.trim(removeArgs[0]),
							layer:call.callee == 'removeFromBackgroundLayer' ? 'background' : 'character'};
				case 'playstate.camMove':
					action = parseCameraMove(call, diagnostics);
				case 'playstate.camChangeZoom':
					action = parseCameraZoom(call, fields, diagnostics);
				case 'playstate.camShake':
					action = parseCameraShake(call, diagnostics);
				case 'FlxG.camera.fade':
					action = parseCameraFade(call, diagnostics);
				case 'FlxG.sound.play':
					action = parseSound(call, diagnostics, assets);
				case 'boyfriend.playAnim':
					action = parseActorAnimation(call, 'boyfriend', diagnostics);
				case 'startDialogue' | 'dialogueBox.start':
					if (splitArguments(call.args).length != 0) {
						safe = false;
						diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dialogue-call',
							'Dialogue start takes no donor arguments.');
					} else
						action = {kind:'dialogueStart'};
				case 'focusCameraBasedOnFirstSection':
					if (splitArguments(call.args).length != 0) {
						safe = false;
						diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-focus',
							'Camera focus helper must take no arguments.');
					} else
						action = {kind:'focusFirstSection'};
				case 'fadeIn':
					action = parseMusicFadeIn(call, body, diagnostics);
				case 'fadeOut':
					safe = false;
					diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-fade',
						'Event-scoped fadeOut is not part of the bounded cutscene action set.');
				case 'Paths.sound' | 'Paths.music' | 'Paths.getSparrowAtlas':
					// Nested literal asset lookup; the owning action consumes it.
				default:
					if (isKnownAnimationPlay(call.callee))
						action = parseAnimationPlay(call, diagnostics);
					else if (isKnownVisibilityCall(call.callee))
						// Visibility is an assignment, not a call; this branch stays empty.
						{}
					else if (call.callee == 'function')
						{}
					else {
						safe = false;
						diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-helper',
							'Unmapped event helper/call remains in the cutscene: ' + call.callee);
					}
			}
			if (action != null)
				placed.push({position:call.start, action:action});
			else if (isEventActionCall(call.callee))
				safe = false;
		}

		for (assignment in collectVisibilityAssignments(body))
			placed.push(assignment);

		// Anonymous callbacks are safe only when a sound action parser consumed the
		// exact boyfriend idle restoration. Any remaining function expression is a
		// donor closure and invalidates this bounded event.
		var anonymousCount = countToken(body, 'function');
		for (action in placed)
			if (action.action.onComplete != null)
				anonymousCount--;
		if (anonymousCount > 0) {
			safe = false;
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-closure',
				'Arbitrary event closures are not executed by the data-only timeline.');
		}

		placed.sort(function(a, b):Int return a.position - b.position);
		var actions:Array<HxcCutsceneAction> = [];
		for (entry in placed)
			actions.push(entry.action);
		return {safe:safe, actions:actions};
	}

	static function parseDialogueCompletion(source:String, fields:Map<String, Bool>,
		assignments:Map<String, Bool>, diagnostics:Array<HxcCutsceneTimelineDiagnostic>,
		assets:Array<HxcCutsceneAsset>):{safe:Bool, delay:HxcCutsceneTime, actions:Array<HxcCutsceneAction>} {
		var boundary = firstCall(source, 'dialogueBox\\.onDialogueEnd\\.add');
		if (boundary == null) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dialogue-end',
				'No bounded dialogue onDialogueEnd callback was found.');
			return {safe:false, delay:seconds(0, '0'), actions:[]};
		}
		var callbackOpen = source.indexOf('{', boundary.start);
		if (callbackOpen < 0) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-closure',
				'Dialogue completion callback has no body.');
			return {safe:false, delay:seconds(0, '0'), actions:[]};
		}
		var callbackClose = matchingDelimiter(source, callbackOpen, '{', '}');
		if (callbackClose < 0)
			return {safe:false, delay:seconds(0, '0'), actions:[]};
		var callbackBody = source.substr(callbackOpen + 1, callbackClose - callbackOpen - 1);
		var timer = firstCall(callbackBody, 'new\\s+FlxTimer\\s*\\(\\s*\\)\\s*\\.\\s*start');
		if (timer == null) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dialogue-end',
				'Dialogue completion must use the bounded FlxTimer delay.');
			return {safe:false, delay:seconds(0, '0'), actions:[]};
		}
		var timerArgs = splitArguments(timer.args);
		if (timerArgs.length != 2 || parseNumber(timerArgs[0]) != 0.5) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dialogue-delay',
			'Dialogue completion delay must be the literal 0.5 seconds.');
			return {safe:false, delay:seconds(0, '0'), actions:[]};
		}
		var innerOpen = callbackBody.indexOf('{', timer.start);
		if (innerOpen < 0)
			return {safe:false, delay:seconds(0, '0'), actions:[]};
		var innerClose = matchingDelimiter(callbackBody, innerOpen, '{', '}');
		if (innerClose < 0)
			return {safe:false, delay:seconds(0, '0'), actions:[]};
		var inner = callbackBody.substr(innerOpen + 1, innerClose - innerOpen - 1);
		var placed:Array<HxcCutscenePlacedAction> = [];
		var safe = true;
		for (call in collectAllCallsAtDepth(inner, 0)) {
			var action:HxcCutsceneAction = null;
			switch (call.callee) {
				case 'next':
					action = {kind:'handoff'};
				case 'playstate.camChangeZoom':
					action = parseCameraZoom(call, fields, diagnostics);
				case 'focusCameraBasedOnFirstSection':
					action = {kind:'focusFirstSection'};
				case 'bgm.fadeOut':
					action = parseReceiverFade(call, 'bgm', assignments, diagnostics);
				case 'cutsceneMusic.fadeOut':
					action = parseReceiverFade(call, 'cutsceneMusic', assignments, diagnostics);
				case 'playstate.camGame.filters.remove':
					if (StringTools.trim(call.args) == 'fadeInShaderFilter') {
						action = {kind:'removeOwnedFilter', target:'fadeInShaderFilter'};
						action.engineOwned = true;
						if (!hasDiagnostic(diagnostics, 'hxc-cutscene-adapter-engine-owned', 'fadeInShaderFilter')) {
							diagnose(diagnostics, 'info', 'hxc-cutscene-adapter-engine-owned',
								'Cutscene removes the engine-owned fadeInShaderFilter; no donor field is declared.');
						}
					}
					else {
						safe = false;
						diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-filter',
							'Only the cutscene-owned fadeInShaderFilter may be removed.');
					}
				case 'Paths.sound' | 'Paths.music':
					// Nested lookup in a receiver fade is not an action.
				default:
					if (call.callee == 'function') {}
					else {
						safe = false;
						diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-helper',
							'Unmapped dialogue completion helper/call remains: ' + call.callee);
					}
			}
			if (action != null)
				placed.push({position:call.start, action:action});
			else if (isCompletionActionCall(call.callee))
				safe = false;
		}
		// FPS Plus guards the inherited cutsceneMusic handle inside an if block.
		// Preserve that bounded cleanup action without executing the donor condition
		// or treating the inherited engine handle as an unsafe object graph.
		for (call in collectAllCallsAtDepth(inner, 1)) {
			var inheritedAction:HxcCutsceneAction = null;
			if (call.callee == 'cutsceneMusic.fadeOut')
				inheritedAction = parseReceiverFade(call, 'cutsceneMusic', assignments, diagnostics);
			else if (call.callee != 'Paths.sound' && call.callee != 'Paths.music') {
				safe = false;
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-helper',
					'Unmapped dialogue completion helper/call remains: ' + call.callee);
			}
			if (inheritedAction != null)
				placed.push({position:call.start, action:inheritedAction});
			else if (call.callee == 'cutsceneMusic.fadeOut')
				safe = false;
		}
		var unknownClosures = countToken(inner, 'function');
		if (unknownClosures > 0) {
			safe = false;
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-closure',
			'Arbitrary dialogue completion closures are not executed.');
		}
		placed.sort(function(a, b):Int return a.position - b.position);
		var actions:Array<HxcCutsceneAction> = [];
		for (entry in placed)
			actions.push(entry.action);
		return {safe:safe, delay:seconds(0.5, '0.5'), actions:actions};
	}

	static function isEventActionCall(callee:String):Bool {
		return callee == 'addToBackgroundLayer' || callee == 'addToCharacterLayer'
			|| callee == 'removeFromBackgroundLayer' || callee == 'removeFromCharacterLayer'
			|| callee == 'playstate.camMove' || callee == 'playstate.camChangeZoom'
			|| callee == 'playstate.camShake' || callee == 'FlxG.camera.fade'
			|| callee == 'FlxG.sound.play' || callee == 'boyfriend.playAnim'
			|| callee == 'startDialogue' || callee == 'dialogueBox.start'
			|| callee == 'focusCameraBasedOnFirstSection' || callee == 'fadeIn'
			|| isKnownAnimationPlay(callee);
	}

	static function isCompletionActionCall(callee:String):Bool {
		return callee == 'next' || callee == 'playstate.camChangeZoom'
			|| callee == 'focusCameraBasedOnFirstSection' || callee == 'bgm.fadeOut'
			|| callee == 'cutsceneMusic.fadeOut'
			|| callee == 'playstate.camGame.filters.remove';
	}

	static function parseReceiverFade(sourceCall:HxcCutsceneCall, receiver:String,
		assignments:Map<String, Bool>, diagnostics:Array<HxcCutsceneTimelineDiagnostic>):HxcCutsceneAction {
		var args = splitArguments(sourceCall.args);
		if (args.length != 2) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-fade',
				receiver + '.fadeOut requires duration and target volume.');
			return null;
		}
		var duration = parseTime(args[0]);
		var volume = parseNumber(args[1]);
		if (duration == null || volume == null) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-fade',
				receiver + '.fadeOut duration/volume must be bounded literals.');
			return null;
		}
		if (receiver == 'bgm' && !assignments.exists('bgm')) {
			diagnose(diagnostics, 'info', 'hxc-cutscene-adapter-no-op',
				'bgm.fadeOut is retained as a diagnosed no-op because bgm is never assigned by the cutscene.');
			return {kind:'musicFadeOutSkipped', track:receiver, duration:duration, volume:volume};
		}
		return {kind:'musicFadeOut', track:receiver, duration:duration, volume:volume};
	}

	static function parseCameraMove(call:HxcCutsceneCall,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>):HxcCutsceneAction {
		var args = splitArguments(call.args);
		if (args.length < 3 || args.length > 4) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-camera',
				'camMove requires x, y, duration, and optional allow-listed ease.');
			return null;
		}
		var x = parseNumber(args[0]);
		var y = parseNumber(args[1]);
		var duration = parseDuration(args[2]);
		if (x == null || y == null || duration == null) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-camera',
				'camMove arguments must be finite literals or null duration.');
			return null;
		}
		var action:HxcCutsceneAction = {kind:'cameraMove', x:x, y:y, duration:duration};
		if (args.length == 4) {
			var ease = parseEase(args[3]);
			if (ease == '') {
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-ease',
					'camMove ease is not on the bounded allow-list.');
				return null;
			}
			action.ease = ease;
		}
		return action;
	}

	static function parseCameraZoom(call:HxcCutsceneCall, fields:Map<String, Bool>,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>):HxcCutsceneAction {
		var args = splitArguments(call.args);
		if (args.length < 2 || args.length > 3) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-camera',
				'camChangeZoom requires target, duration, and optional allow-listed ease.');
			return null;
		}
		var target = StringTools.trim(args[0]);
		var value = parseNumber(target);
		var engineOwned = false;
		if (value == null && target != 'originalZoom') {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-zoom-target',
				'Camera zoom target must be a number or declared originalZoom.');
			return null;
		}
		if (target == 'originalZoom' && !fields.exists('originalZoom')) {
			engineOwned = true;
			if (!hasDiagnostic(diagnostics, 'hxc-cutscene-adapter-engine-owned', 'originalZoom'))
				diagnose(diagnostics, 'info', 'hxc-cutscene-adapter-engine-owned',
					'Camera zoom uses the engine-owned default zoom; no donor originalZoom field is declared.');
		}
		var duration = parseDuration(args[1]);
		if (duration == null) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-camera',
				'Camera zoom duration is not a bounded literal/expression.');
			return null;
		}
		var action:HxcCutsceneAction = {kind:'cameraZoom', target:target, duration:duration};
		if (engineOwned)
			action.engineOwned = true;
		if (value != null)
			action.value = value;
		if (args.length == 3) {
			var ease = parseEase(args[2]);
			if (ease == '') {
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-ease',
					'camChangeZoom ease is not on the bounded allow-list.');
				return null;
			}
			action.ease = ease;
		}
		return action;
	}

	static function parseCameraShake(call:HxcCutsceneCall,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>):HxcCutsceneAction {
		var args = splitArguments(call.args);
		if (args.length != 3) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-camera',
				'camShake requires intensity, null axis, and duration.');
			return null;
		}
		var intensity = parseNumber(args[0]);
		var duration = parseDuration(args[2]);
		if (intensity == null || StringTools.trim(args[1]) != 'null' || duration == null) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-camera',
				'camShake arguments are outside the bounded form.');
			return null;
		}
		return {kind:'cameraShake', intensity:intensity, duration:duration};
	}

	static function parseCameraFade(call:HxcCutsceneCall,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>):HxcCutsceneAction {
		var args = splitArguments(call.args);
		if (args.length < 2 || args.length > 3) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-fade',
				'Camera fade requires color, duration, and optional fade direction.');
			return null;
		}
		var color = parseInteger(args[0]);
		var duration = parseNumber(args[1]);
		var fadeIn = args.length == 3 ? parseBool(args[2]) : false;
		if (color == null || duration == null || (args.length == 3 && fadeIn == null)) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-fade',
				'Camera fade arguments must be finite literals.');
			return null;
		}
		return {kind:'cameraFade', color:color, value:duration, fadeIn:fadeIn == true};
	}

	static function parseSound(call:HxcCutsceneCall,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>, assets:Array<HxcCutsceneAsset>):HxcCutsceneAction {
		var args = splitArguments(call.args);
		if (args.length == 0) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-sound',
				'Sound play requires a literal Paths.sound/music asset.');
			return null;
		}
		var assetCall = firstCall(args[0], 'Paths\\.sound');
		var assetKind = 'sound';
		if (assetCall == null) {
			assetCall = firstCall(args[0], 'Paths\\.music');
			assetKind = 'music';
		}
		if (assetCall == null) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dynamic-path',
			'Sound path is dynamic or not a manifest-relative Paths.sound/music literal.');
			return null;
		}
		var pathArgs = splitArguments(assetCall.args);
		if (pathArgs.length != 1 || !isStringLiteral(pathArgs[0])) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dynamic-path',
				'Sound path must be a single string literal.');
			return null;
		}
		var key = normalizeAssetKey(assetKind,
			unquote(pathArgs[0]), diagnostics);
		if (key == null)
			return null;
		addAsset(assets, assetKind, key);
		var action:HxcCutsceneAction = {kind:assetKind == 'music' ? 'musicPlay' : 'soundPlay', asset:key};
		if (args.length > 1) {
			var volume = parseNumber(args[1]);
			if (volume == null) {
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-sound',
					'Sound volume must be a finite literal.');
				return null;
			}
			action.volume = volume;
		}
		if (args.length > 2) {
			var loop = parseBool(args[2]);
			if (loop == null) {
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-sound',
					'Sound loop flag must be a boolean literal.');
				return null;
			}
			action.loop = loop;
		}
		var callback = extractTrailingFunction(args);
		if (callback != null) {
			var callbackActions = parseCallbackActions(callback, diagnostics);
			if (callbackActions == null)
				return null;
			action.onComplete = callbackActions;
		}
		return action;
	}

	static function parseMusicFadeIn(call:HxcCutsceneCall, body:String,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>):HxcCutsceneAction {
		var args = splitArguments(call.args);
		if (args.length != 3) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-fade',
				'Chained music fadeIn requires duration, starting volume, and target volume.');
			return null;
		}
		var duration = parseTime(args[0]);
		var from = parseNumber(args[1]);
		var to = parseNumber(args[2]);
		if (duration == null || from == null || to == null) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-fade',
				'Music fadeIn arguments must be bounded duration/number literals.');
			return null;
		}
		var prefix = body.substr(0, call.start);
		var receiverMatch = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*FlxG\\s*\\.\\s*sound\\s*\\.\\s*play\\s*\\([^;\\n]*\\)\\s*\\.\\s*$', 'm');
		if (!receiverMatch.match(prefix)) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-fade',
				'Music fadeIn is not attached to a statically assigned FlxG.sound.play track.');
			return null;
		}
		return {kind:'musicFadeIn', track:receiverMatch.matched(1), duration:duration,
			fromVolume:from, volume:to};
	}

	static function parseCallbackActions(body:String,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>):Array<HxcCutsceneAction> {
		var actions:Array<HxcCutsceneAction> = [];
		for (call in collectAllCallsAtDepth(body, 0)) {
			if (call.callee == 'boyfriend.playAnim') {
				var parsed = parseActorAnimation(call, 'boyfriend', diagnostics);
				if (parsed == null)
					return null;
				actions.push(parsed);
			} else if (call.callee != 'function') {
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-closure',
					'Sound callback contains an unbounded helper: ' + call.callee);
				return null;
			}
		}
		return actions;
	}

	static function parseActorAnimation(call:HxcCutsceneCall, actor:String,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>):HxcCutsceneAction {
		var args = splitArguments(call.args);
		if (args.length < 1 || args.length > 2 || !isStringLiteral(args[0])) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-animation',
				'Actor animation requires a literal animation name.');
			return null;
		}
		return {kind:'actorAnimation', actor:actor, animation:unquote(args[0])};
	}

	static function parseAnimationPlay(call:HxcCutsceneCall,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>):HxcCutsceneAction {
		var dot = call.callee.indexOf('.animation.play');
		var sprite = dot < 0 ? '' : call.callee.substr(0, dot);
		var args = splitArguments(call.args);
		if (!isIdentifier(sprite) || args.length < 1 || args.length > 2 || !isStringLiteral(args[0])) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-animation',
				'Sprite animation requires a statically named sprite and literal animation.');
			return null;
		}
		return {kind:'spriteAnimation', sprite:sprite, animation:unquote(args[0]),
			looping:args.length == 2 && parseBool(args[1]) == true};
	}

	static function collectSpriteDefinitions(body:String,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>, assets:Array<HxcCutsceneAsset>):Array<HxcCutscenePlacedAction> {
		var result:Array<HxcCutscenePlacedAction> = [];
		var expression = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*new\\s+FlxSprite\\s*\\(([^)]*)\\)', 'g');
		var search = 0;
		while (expression.match(body.substr(search))) {
			var match = expression.matchedPos();
			var position = search + match.pos;
			var name = expression.matched(1);
			var args = splitArguments(expression.matched(2));
			var x = args.length > 0 ? parseNumber(args[0]) : null;
			var y = args.length > 1 ? parseNumber(args[1]) : null;
			if (args.length != 2 || x == null || y == null) {
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-sprite',
					'Sprite position must use two finite numeric literals.');
			} else {
				var action:HxcCutsceneAction = {kind:'spriteDefine', sprite:name, x:x, y:y,
					visible:true, antialiasing:false, animations:[]};
				var after = body.substr(position + match.len);
				var atlas = new EReg('\\b' + name + '\\s*\\.\\s*frames\\s*=\\s*Paths\\s*\\.\\s*getSparrowAtlas\\s*\\(\\s*(["\\\'])([^"\\\']+)\\1\\s*\\)', 'm');
				if (atlas.match(after)) {
					var key = normalizeAssetKey('sparrow', atlas.matched(2), diagnostics);
					if (key != null) {
						action.asset = key;
						addAsset(assets, 'sparrow', key);
					}
				} else
					diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-sprite-asset',
						'Sprite frames must use a literal Paths.getSparrowAtlas asset.');
				var antialias = new EReg('\\b' + name + '\\s*\\.\\s*antialiasing\\s*=\\s*(true|false)', 'm');
				if (antialias.match(after))
					action.antialiasing = antialias.matched(1) == 'true';
				var animations:Array<Dynamic> = [];
				var animation = new EReg('\\b' + name + '\\s*\\.\\s*animation\\s*\\.\\s*addByPrefix\\s*\\(\\s*(["\\\'])([^"\\\']+)\\1\\s*,\\s*(["\\\'])([^"\\\']+)\\3\\s*,\\s*([0-9]+(?:\\.[0-9]+)?)\\s*,\\s*(true|false)\\s*\\)', 'g');
				var animationSearch = after;
				while (animation.match(animationSearch)) {
					var fps = parseNumber(animation.matched(5));
					if (fps == null) {
						diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-animation',
							'Animation FPS must be a finite literal.');
					} else
						animations.push({name:animation.matched(2), prefix:animation.matched(4),
							fps:fps, loop:animation.matched(6) == 'true'});
					var animPos = animation.matchedPos();
					if (animPos.len <= 0 || animPos.pos + animPos.len >= animationSearch.length)
						break;
					animationSearch = animationSearch.substr(animPos.pos + animPos.len);
				}
				action.animations = animations;
				var visible = new EReg('\\b' + name + '\\s*\\.\\s*visible\\s*=\\s*(true|false)', 'm');
				if (visible.match(after))
					action.visible = visible.matched(1) == 'true';
				result.push({position:position, action:action});
			}
			if (match.len <= 0 || search + match.pos + match.len >= body.length)
				break;
			search += match.pos + match.len;
		}
		return result;
	}

	static function collectVisibilityAssignments(body:String):Array<HxcCutscenePlacedAction> {
		var result:Array<HxcCutscenePlacedAction> = [];
		var expression = new EReg('\\b((?:playstate\\s*\\.\\s*)?(?:camHUD|dad|boyfriend|gf|whit|bg))\\s*\\.\\s*visible\\s*=\\s*(true|false)', 'g');
		var search = 0;
		while (expression.match(body.substr(search))) {
			var pos = expression.matchedPos();
			var target = StringTools.replace(expression.matched(1), ' ', '');
			var actor = target == 'playstate.camHUD' ? 'camHUD' : target;
			result.push({position:search + pos.pos,
				action:{kind:'visibility', actor:actor, value:expression.matched(2) == 'true' ? 1 : 0}});
			if (pos.len <= 0 || search + pos.pos + pos.len >= body.length)
				break;
			search += pos.pos + pos.len;
		}
		return result;
	}

	static function isKnownVisibilityCall(_callee:String):Bool return false;

	static function isKnownAnimationPlay(callee:String):Bool {
		return callee != null && callee.indexOf('.animation.play') >= 0;
	}

	static function isConstructorAllowedCall(callee:String):Bool {
		if (callee == null)
			return false;
		return callee == 'super' || callee == 'addGeneric' || callee == 'addEvent'
			|| callee == 'function'
			|| callee == 'playstate.camMove' || callee == 'playstate.camChangeZoom'
			|| callee == 'playstate.camShake'
			|| callee == 'Paths.json' || callee == 'Paths.getSparrowAtlas'
			|| callee == 'Json.parse' || callee == 'Utils.getText'
			|| callee == 'DialogueBox' || callee == 'FlxSprite'
			|| callee.indexOf('.animation.addByPrefix') >= 0
			|| callee.indexOf('.onDialogueEnd.add') >= 0;
	}

	static function isReceiverFadeCall(source:String, call:HxcCutsceneCall, receiver:String):Bool {
		var prefix = source.substr(0, call.start);
		var expression = new EReg('\\b' + receiver + '\\s*\\.\\s*$', 'm');
		return expression.match(prefix);
	}

	static function isReceiverFilterRemove(source:String, call:HxcCutsceneCall):Bool {
		var prefix = source.substr(0, call.start);
		return new EReg('playstate\\s*\\.\\s*camGame\\s*\\.\\s*filters\\s*\\.\\s*$', 'm').match(prefix)
			&& StringTools.trim(call.args) == 'fadeInShaderFilter';
	}

	static function collectAllCallsAtDepth(source:String, wantedDepth:Int):Array<HxcCutsceneCall> {
		var result:Array<HxcCutsceneCall> = [];
		var expression = new EReg('(?:[A-Za-z_][A-Za-z0-9_]*\\s+)?(?:[A-Za-z_][A-Za-z0-9_]*\\s*\\.)*[A-Za-z_][A-Za-z0-9_]*\\s*\\(', 'g');
		var search = 0;
		while (expression.match(source.substr(search))) {
			var matched = expression.matched(0);
			var pos = expression.matchedPos();
			var start = search + pos.pos;
			var open = start + matched.lastIndexOf('(');
			var close = matchingDelimiter(source, open, '(', ')');
			if (close < 0)
				break;
			var callee = StringTools.trim(matched.substr(0, matched.lastIndexOf('(')));
			var words = callee.split(' ');
			callee = words[words.length - 1];
			if (braceDepthAt(source, start) == wantedDepth && !isControlKeyword(callee))
				result.push({callee:callee, args:source.substr(open + 1, close - open - 1),
					start:start, end:close + 1});
			if (close + 1 >= source.length)
				break;
			search = close + 1;
		}
		return result;
	}

	static function collectCallsAtDepth(source:String, wanted:String, depth:Int):Array<HxcCutsceneCall> {
		var result:Array<HxcCutsceneCall> = [];
		var expression = new EReg(wanted + '\\s*\\(', 'g');
		var search = 0;
		while (expression.match(source.substr(search))) {
			var matched = expression.matched(0);
			var pos = expression.matchedPos();
			var start = search + pos.pos;
			var open = start + matched.lastIndexOf('(');
			var close = matchingDelimiter(source, open, '(', ')');
			if (close < 0)
				break;
			if (braceDepthAt(source, start) == depth)
				result.push({callee:normalizeCallee(wanted), args:source.substr(open + 1, close - open - 1),
					start:start, end:close + 1});
			if (close + 1 >= source.length)
				break;
			search = close + 1;
		}
		return result;
	}

	static function firstCall(source:String, wanted:String):HxcCutsceneCall {
		var calls = collectCallsAtDepth(source, wanted, 0);
		if (calls.length > 0)
			return calls[0];
		// Constructor expressions such as `new DialogueBox` and regular expression
		// alternatives contain whitespace, so retry with an unscoped search.
		var expression = new EReg(wanted + '\\s*\\(', 'm');
		if (!expression.match(source))
			return null;
		var matched = expression.matched(0);
		var pos = expression.matchedPos();
		var start = pos.pos;
		var open = start + matched.lastIndexOf('(');
		var close = matchingDelimiter(source, open, '(', ')');
		return close < 0 ? null : {callee:normalizeCallee(wanted),
			args:source.substr(open + 1, close - open - 1), start:start, end:close + 1};
	}

	static function normalizeCallee(value:String):String {
		var clean = StringTools.trim(value == null ? '' : value);
		clean = StringTools.replace(clean, '\\s*', '');
		clean = StringTools.replace(clean, '\\.', '.');
		return clean;
	}

	static function isControlKeyword(value:String):Bool {
		return value == 'if' || value == 'for' || value == 'while' || value == 'switch'
			|| value == 'catch' || value == 'else' || value == 'try';
	}

	static function findFunction(source:String, name:String):HxcCutsceneFunction {
		var expression = new EReg('\\bfunction\\s+' + name + '\\s*\\(([^)]*)\\)', 'm');
		if (!expression.match(source))
			return null;
		var pos = expression.matchedPos();
		var open = source.indexOf('(', pos.pos);
		var closeArgs = matchingDelimiter(source, open, '(', ')');
		if (closeArgs < 0)
			return null;
		var bodyOpen = source.indexOf('{', closeArgs + 1);
		if (bodyOpen < 0)
			return null;
		var bodyClose = matchingDelimiter(source, bodyOpen, '{', '}');
		if (bodyClose < 0)
			return null;
		return {name:name, arguments:source.substr(open + 1, closeArgs - open - 1),
			body:source.substr(bodyOpen + 1, bodyClose - bodyOpen - 1), start:pos.pos};
	}

	static function collectFields(source:String, before:Int):Map<String, Bool> {
		var fields:Map<String, Bool> = new Map<String, Bool>();
		var prefix = source.substr(0, before);
		var expression = new EReg('(?:^|[;{}])\\s*(?:public\\s+|private\\s+|static\\s+)*var\\s+([A-Za-z_][A-Za-z0-9_]*)\\b', 'g');
		var search = 0;
		while (expression.match(prefix.substr(search))) {
			fields.set(expression.matched(1), true);
			var pos = expression.matchedPos();
			if (pos.len <= 0 || search + pos.pos + pos.len >= prefix.length)
				break;
			search += pos.pos + pos.len;
		}
		return fields;
	}

	static function collectFieldAssignments(source:String):Map<String, Bool> {
		var assignments:Map<String, Bool> = new Map<String, Bool>();
		var expression = new EReg('(?:^|[;{}])\\s*(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*', 'g');
		var search = 0;
		while (expression.match(source.substr(search))) {
			assignments.set(expression.matched(1), true);
			var pos = expression.matchedPos();
			if (pos.len <= 0 || search + pos.pos + pos.len >= source.length)
				break;
			search += pos.pos + pos.len;
		}
		return assignments;
	}

	static function parseTime(value:String):HxcCutsceneTime {
		var clean = StringTools.trim(value == null ? '' : value);
		var numeric = parseNumber(clean);
		if (numeric != null)
			return seconds(numeric, clean);
		// Mounted FPS Plus cutscenes parenthesize the beat duration, while a few
		// packs use the equivalent unparenthesized form. Keep it symbolic and
		// bounded; never evaluate donor code here.
		var crochet = new EReg('^\\(?\\s*Conductor\\s*\\.\\s*crochet\\s*/\\s*1000\\s*\\)?\\s*\\*\\s*([0-9]+(?:\\.[0-9]+)?)$', '');
		if (crochet.match(clean)) {
			var multiplier = parseNumber(crochet.matched(1));
			return multiplier == null ? null : {kind:'crochet-multiplier', value:multiplier, source:clean};
		}
		return null;
	}

	static function parseDuration(value:String):HxcCutsceneTime {
		var clean = StringTools.trim(value == null ? '' : value);
		if (clean == 'null')
			return seconds(0, clean);
		return parseTime(clean);
	}

	static function seconds(value:Float, source:String):HxcCutsceneTime {
		return {kind:'seconds', value:value, source:source};
	}

	static function timeOrder(left:HxcCutsceneTime, right:HxcCutsceneTime):Int {
		if (left == null || right == null || left.kind != 'seconds' || right.kind != 'seconds')
			return 0;
		return left.value < right.value ? -1 : (left.value > right.value ? 1 : 0);
	}

	static function parseEase(value:String):String {
		var clean = StringTools.trim(value == null ? '' : value);
		var prefix = 'FlxEase.';
		if (clean.startsWith(prefix))
			clean = clean.substr(prefix.length);
		return allowedEases.indexOf(clean) >= 0 ? clean : '';
	}

	static function parseNumber(value:String):Null<Float> {
		var clean = StringTools.trim(value == null ? '' : value);
		if (!new EReg('^-?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)$', '').match(clean))
			return null;
		var number = Std.parseFloat(clean);
		return Math.isNaN(number) || number == Math.POSITIVE_INFINITY || number == Math.NEGATIVE_INFINITY
			? null : number;
	}

	static function parseInteger(value:String):Null<Int> {
		var clean = StringTools.trim(value == null ? '' : value);
		try {
			if (clean.toLowerCase().startsWith('0x'))
				return Std.parseInt(clean);
			var parsed = Std.parseInt(clean);
			return parsed;
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function parseBool(value:String):Null<Bool> {
		var clean = StringTools.trim(value == null ? '' : value);
		return clean == 'true' ? true : (clean == 'false' ? false : null);
	}

	static function isStringLiteral(value:String):Bool {
		var clean = StringTools.trim(value == null ? '' : value);
		return clean.length >= 2 && ((clean.charAt(0) == '"' && clean.charAt(clean.length - 1) == '"')
			|| (clean.charAt(0) == "'" && clean.charAt(clean.length - 1) == "'"));
	}

	static function unquote(value:String):String {
		var clean = StringTools.trim(value == null ? '' : value);
		return isStringLiteral(clean) ? clean.substr(1, clean.length - 2) : clean;
	}

	static function normalizeAssetKey(kind:String, value:String,
		diagnostics:Array<HxcCutsceneTimelineDiagnostic>):String {
		var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		while (clean.startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0) {
			diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dynamic-path',
				'Asset key is not a relative manifest path: ' + value);
			return null;
		}
		for (part in clean.split('/'))
			if (part == '' || part == '..') {
				diagnose(diagnostics, 'error', 'unsupported-hxc-cutscene-dynamic-path',
					'Asset key contains an unsafe path segment: ' + value);
				return null;
			}
		var prefix = kind == 'sound' ? 'sounds/' : (kind == 'music' ? 'music/' : 'images/');
		return clean.startsWith(prefix) ? clean : prefix + clean;
	}

	static function addAsset(assets:Array<HxcCutsceneAsset>, kind:String, key:String):Void {
		if (assets == null || key == null)
			return;
		for (existing in assets)
			if (existing != null && existing.kind == kind && existing.key == key)
				return;
		assets.push({kind:kind, key:key});
	}

	static function extractTrailingFunction(args:Array<String>):String {
		if (args == null || args.length == 0)
			return null;
		var last = StringTools.trim(args[args.length - 1]);
		if (!last.startsWith('function'))
			return null;
		var open = last.indexOf('{');
		if (open < 0)
			return null;
		var close = matchingDelimiter(last, open, '{', '}');
		return close < 0 ? null : last.substr(open + 1, close - open - 1);
	}

	static function splitArguments(value:String):Array<String> {
		var result:Array<String> = [];
		var start = 0;
		var parens = 0;
		var braces = 0;
		var brackets = 0;
		var quote = '';
		var escaped = false;
		for (index in 0...value.length) {
			var current = value.charAt(index);
			if (quote != '') {
				if (current == quote && !escaped)
					quote = '';
				if (current == '\\' && !escaped)
					escaped = true;
				else
					escaped = false;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				continue;
			}
			switch (current) {
				case '(': parens++;
				case ')': parens--;
				case '{': braces++;
				case '}': braces--;
				case '[': brackets++;
				case ']': brackets--;
				case ',':
					if (parens == 0 && braces == 0 && brackets == 0) {
						result.push(StringTools.trim(value.substr(start, index - start)));
						start = index + 1;
					}
				default:
			}
		}
		var tail = StringTools.trim(value.substr(start));
		if (tail != '' || result.length > 0)
			result.push(tail);
		return result;
	}

	static function countToken(source:String, token:String):Int {
		var count = 0;
		var search = 0;
		while (source != null && token != null && token != '' && search < source.length) {
			var found = source.indexOf(token, search);
			if (found < 0)
				break;
			count++;
			search = found + token.length;
		}
		return count;
	}

	static function isIdentifier(value:String):Bool {
		return value != null && new EReg('^[A-Za-z_][A-Za-z0-9_]*$', '').match(StringTools.trim(value));
	}

	static function manifestPath(path:String):String {
		var clean = StringTools.replace(StringTools.trim(path == null ? '' : path), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean.startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		else {
			// Import callers may pass an absolute donor path. Retain only the
			// manifest-root suffix; never expose or carry an absolute filesystem
			// path into the timeline result.
			var roots = ['data/', 'images/', 'sounds/', 'music/', 'scripts/'];
			var rootStart = -1;
			for (root in roots) {
				var candidate = clean.startsWith(root) ? 0 : clean.lastIndexOf('/' + root) + 1;
				if (candidate == 0 && !clean.startsWith(root))
					candidate = -1;
				if (candidate >= 0 && (rootStart < 0 || candidate > rootStart))
					rootStart = candidate;
			}
			if (rootStart >= 0)
				clean = clean.substr(rootStart);
			else
				return '';
		}
		for (part in clean.split('/'))
			if (part == '..' || part == '')
				return '';
		return clean;
	}

	static function diagnose(output:Array<HxcCutsceneTimelineDiagnostic>, severity:String,
		code:String, message:String):Void {
		output.push({severity:severity, code:code, message:message});
	}

	static function hasDiagnostic(output:Array<HxcCutsceneTimelineDiagnostic>, code:String,
		marker:String):Bool {
		for (finding in output)
			if (finding != null && finding.code == code
				&& (marker == null || finding.message.indexOf(marker) >= 0))
				return true;
		return false;
	}

	static function stripComments(source:String):String {
		var output = new StringBuf();
		var line = false;
		var block = false;
		var quote = '';
		var escaped = false;
		var index = 0;
		while (index < source.length) {
			var current = source.charAt(index);
			var next = index + 1 < source.length ? source.charAt(index + 1) : '';
			if (line) {
				if (current == '\n') {
					line = false;
					output.add('\n');
				} else output.add(' ');
				index++;
				continue;
			}
			if (block) {
				if (current == '*' && next == '/') {
					block = false;
					output.add('  ');
					index += 2;
				} else {
					output.add(current == '\n' ? '\n' : ' ');
					index++;
				}
				continue;
			}
			if (quote != '') {
				output.add(current);
				if (current == quote && !escaped)
					quote = '';
				if (current == '\\' && !escaped)
					escaped = true;
				else
					escaped = false;
				index++;
				continue;
			}
			if (current == '/' && next == '/') {
				line = true;
				output.add('  ');
				index += 2;
				continue;
			}
			if (current == '/' && next == '*') {
				block = true;
				output.add('  ');
				index += 2;
				continue;
			}
			if (current == '"' || current == "'")
				quote = current;
			output.add(current);
			index++;
		}
		return output.toString();
	}

	static function braceDepthAt(source:String, position:Int):Int {
		var depth = 0;
		var quote = '';
		var escaped = false;
		for (index in 0...Std.int(Math.min(position, source.length))) {
			var current = source.charAt(index);
			if (quote != '') {
				if (current == quote && !escaped)
					quote = '';
				if (current == '\\' && !escaped)
					escaped = true;
				else
					escaped = false;
				continue;
			}
			if (current == '"' || current == "'") quote = current;
			else if (current == '{') depth++;
			else if (current == '}') depth--;
		}
		return depth;
	}

	static function matchingDelimiter(source:String, open:Int, left:String, right:String):Int {
		if (source == null || open < 0 || open >= source.length || source.charAt(open) != left)
			return -1;
		var depth = 0;
		var quote = '';
		var escaped = false;
		for (index in open...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (current == quote && !escaped)
					quote = '';
				if (current == '\\' && !escaped)
					escaped = true;
				else
					escaped = false;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				continue;
			}
			if (current == left)
				depth++;
			else if (current == right) {
				depth--;
				if (depth == 0)
					return index;
			}
		}
		return -1;
	}
}
