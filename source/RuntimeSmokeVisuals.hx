package;

/**
 * Small read-only snapshots of native render bindings for opt-in smoke runs.
 * Dynamic access keeps the diagnostic independent of the Flixel renderer.
 */
class RuntimeSmokeVisuals {
	static function field(value:Dynamic, name:String):Dynamic {
		if (value == null)
			return null;
		try return Reflect.getProperty(value, name) catch (_:Dynamic) return null;
	}

	static function count(value:Dynamic):Int {
		return value != null && Std.isOfType(value, Array)
			? (cast value:Array<Dynamic>).length : 0;
	}

	static function number(value:Dynamic):Null<Float> {
		if (value == null)
			return null;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) || !Math.isFinite(parsed) ? null : parsed;
	}

	static function call(value:Dynamic, name:String, args:Array<Dynamic>):Dynamic {
		var method = field(value, name);
		if (method == null)
			return null;
		try return Reflect.callMethod(value, method, args) catch (_:Dynamic) return null;
	}

	static function graphicKey(sprite:Dynamic):String {
		var key = field(field(sprite, 'graphic'), 'key');
		return key == null ? '' : Std.string(key);
	}

	public static function note(note:Dynamic, laneWidth:Float):Dynamic {
		var animation = field(note, 'animation');
		var scroll = call(animation, 'getByName', ['Scroll']);
		var current = field(animation, 'curAnim');
		var x = number(field(note, 'x'));
		var width = number(field(note, 'width'));
		var originX = number(field(field(note, 'origin'), 'x'));
		var offsetX = number(field(field(note, 'offset'), 'x'));
		var offsetY = number(field(field(note, 'offset'), 'y'));
		var scaleX = number(field(field(note, 'scale'), 'x'));
		var renderCenterX:Null<Float> = x == null || width == null || originX == null
			|| offsetX == null || scaleX == null ? null
			: x + originX - offsetX - originX * scaleX + width / 2;
		return {
			sourceKind: field(note, 'sourceKind'),
			noteType: field(note, 'noteType'),
			id: field(note, 'coolId'),
			trueNoteData: field(note, 'trueNoteData'),
			noteData: field(note, 'noteData'),
			customNotePath: field(note, 'customNotePath'),
			graphicKey: graphicKey(note),
			atlasFrames: count(field(field(note, 'frames'), 'frames')),
			scrollFrames: count(field(scroll, 'frames')),
			scrollLooped: field(scroll, 'looped'),
			currentAnimation: field(current, 'name'),
			currentFrame: field(current, 'curFrame'),
			isPixel: field(note, 'isPixel'),
			avoidAutoHit: field(note, 'avoidAutoHit'),
			ignoreNote: field(note, 'ignoreNote'),
			hitCausesMiss: field(note, 'hitCausesMiss'),
			hitHealth: field(note, 'hitHealth'),
			missHealth: field(note, 'missHealth'),
			mustPress: field(note, 'mustPress'),
			autoHitAllowed: call(note, 'canAutoHit', []),
			autoControlled: call(note, 'isAutoPlayed', []),
			wasGoodHit: field(note, 'wasGoodHit'),
			x: x,
			width: width,
			scaleX: scaleX,
			offsetX: offsetX,
			offsetY: offsetY,
			renderCenterX: renderCenterX,
			laneCenterX: x == null ? null : x + laneWidth / 2,
			centerErrorX: renderCenterX == null || x == null
				? null : renderCenterX - (x + laneWidth / 2)
		};
	}

	/** Read the live atlas frame and renderer geometry of an imported receptor. */
	public static function receptor(receptor:Dynamic, laneWidth:Float):Dynamic {
		var animation = field(receptor, 'animation');
		var current = field(animation, 'curAnim');
		var frame = field(receptor, 'frame');
		var line = field(receptor, 'parentLine');
		var x = number(field(receptor, 'x'));
		var y = number(field(receptor, 'y'));
		var frameWidth = number(field(receptor, 'frameWidth'));
		var frameHeight = number(field(receptor, 'frameHeight'));
		var originX = number(field(field(receptor, 'origin'), 'x'));
		var originY = number(field(field(receptor, 'origin'), 'y'));
		var offsetX = number(field(field(receptor, 'offset'), 'x'));
		var offsetY = number(field(field(receptor, 'offset'), 'y'));
		var scaleX = number(field(field(receptor, 'scale'), 'x'));
		var scaleY = number(field(field(receptor, 'scale'), 'y'));
		var graphicWidth = frameWidth == null || scaleX == null ? null : frameWidth * scaleX;
		var graphicHeight = frameHeight == null || scaleY == null ? null : frameHeight * scaleY;
		var renderCenterX:Null<Float> = x == null || frameWidth == null || originX == null
			|| offsetX == null || scaleX == null ? null
			: x + originX - offsetX - originX * scaleX + frameWidth * scaleX / 2;
		var renderCenterY:Null<Float> = y == null || frameHeight == null || originY == null
			|| offsetY == null || scaleY == null ? null
			: y + originY - offsetY - originY * scaleY + frameHeight * scaleY / 2;
		var laneCenterX = x == null ? null : x + laneWidth / 2;
		var laneCenterY = y == null ? null : y + laneWidth / 2;
		return {
			type: field(receptor, 'type'),
			width: number(field(receptor, 'width')),
			height: number(field(receptor, 'height')),
			centerReceptors: field(line, 'centerReceptors'),
			lineX: number(field(line, 'x')),
			lineY: number(field(line, 'y')),
			lane: field(receptor, 'ID'),
			animation: field(current, 'name'),
			animationFrame: field(current, 'curFrame'),
			frameName: field(frame, 'name'),
			frameWidth: frameWidth,
			frameHeight: frameHeight,
			graphicWidth: graphicWidth,
			graphicHeight: graphicHeight,
			originX: originX,
			originY: originY,
			scaleX: scaleX,
			scaleY: scaleY,
			offsetX: offsetX,
			offsetY: offsetY,
			x: x,
			y: y,
			renderCenterX: renderCenterX,
			renderCenterY: renderCenterY,
			laneCenterX: laneCenterX,
			laneCenterY: laneCenterY,
			centerErrorX: renderCenterX == null || laneCenterX == null ? null : renderCenterX - laneCenterX,
			centerErrorY: renderCenterY == null || laneCenterY == null ? null : renderCenterY - laneCenterY
		};
	}

	public static function character(role:String, actor:Dynamic):Dynamic {
		var animation = field(actor, 'animation');
		var current = field(animation, 'curAnim');
		var names:Dynamic = call(animation, 'getNameList', []);
		var dance:Array<Dynamic> = [];
		if (Std.isOfType(names, Array))
			for (entry in (cast names:Array<Dynamic>)) {
				if (entry == null)
					continue;
				var name = Std.string(entry);
				var lower = name.toLowerCase();
				if (!StringTools.startsWith(lower, 'dance') && !StringTools.startsWith(lower, 'idle'))
					continue;
				var selected = call(animation, 'getByName', [name]);
				dance.push({
					name: name,
					frames: count(field(selected, 'frames')),
					looped: field(selected, 'looped'),
					frameRate: field(selected, 'frameRate')
				});
			}
		dance.sort(function(a, b) return Reflect.compare(a.name, b.name));
		return {
			role: role,
			requestedCharacter: field(actor, 'requestedCharacter'),
			resolvedCharacter: field(actor, 'resolvedCharacter'),
			imageFile: field(actor, 'imageFile'),
			graphicKey: graphicKey(actor),
			atlasFrames: count(field(field(actor, 'frames'), 'frames')),
			currentAnimation: field(current, 'name'),
			currentFrame: field(current, 'curFrame'),
			currentLength: count(field(current, 'frames')),
			currentLooped: field(current, 'looped'),
			currentFinished: field(current, 'finished'),
			scheduledAnimationNotes: count(field(actor, 'animationNotes')),
			skipDance: field(actor, 'skipDance'),
			geometry: characterGeometry(actor),
			dance: dance
		};
	}

	/** Sample both the Bopper-equivalent base and the final HXC-routed draw point. */
	public static function characterGeometry(actor:Dynamic):Dynamic {
		if (actor == null)
			return null;
		var basePoint = call(actor, 'hxcBaseScreenPosition', [null, null]);
		var baseScreenX = number(field(basePoint, 'x'));
		var baseScreenY = number(field(basePoint, 'y'));
		var screenPoint = call(actor, 'getScreenPosition', [null, null]);
		var screenX = number(field(screenPoint, 'x'));
		var screenY = number(field(screenPoint, 'y'));
		var offsetX = number(field(field(actor, 'offset'), 'x'));
		var offsetY = number(field(field(actor, 'offset'), 'y'));
		var snapshot = {
			x: number(field(actor, 'x')),
			y: number(field(actor, 'y')),
			scaleX: number(field(field(actor, 'scale'), 'x')),
			scaleY: number(field(field(actor, 'scale'), 'y')),
			offsetX: offsetX,
			offsetY: offsetY,
			originX: number(field(field(actor, 'origin'), 'x')),
			originY: number(field(field(actor, 'origin'), 'y')),
			frameWidth: number(field(actor, 'frameWidth')),
			frameHeight: number(field(actor, 'frameHeight')),
			frameTrimX: number(field(field(field(actor, 'frame'), 'offset'), 'x')),
			frameTrimY: number(field(field(field(actor, 'frame'), 'offset'), 'y')),
			animationOffsetX: number(call(actor, 'getCurrentAnimationOffset', [0])),
			animationOffsetY: number(call(actor, 'getCurrentAnimationOffset', [1])),
			globalOffsetX: number(field(actor, 'playerOffsetX')),
			globalOffsetY: number(field(actor, 'playerOffsetY')),
			baseScreenX: baseScreenX,
			baseScreenY: baseScreenY,
			screenX: screenX,
			screenY: screenY,
			// FlxSprite drawComplex starts its matrix at screen minus hitbox offset;
			// origin, scale and atlas trim are reported separately for reconstruction.
			drawX: screenX == null || offsetX == null ? null : screenX - offsetX,
			drawY: screenY == null || offsetY == null ? null : screenY - offsetY
		};
		// FlxObject.getScreenPosition returns pooled FlxPoints. Do not keep the
		// native points in a smoke payload or leak them across every hit sample.
		if (screenPoint != null && screenPoint != basePoint)
			call(screenPoint, 'put', []);
		if (basePoint != null)
			call(basePoint, 'put', []);
		return snapshot;
	}
}
