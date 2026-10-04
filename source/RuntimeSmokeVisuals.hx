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
		var frameWidth = number(field(note, 'frameWidth'));
		var originX = number(field(field(note, 'origin'), 'x'));
		var offsetX = number(field(field(note, 'offset'), 'x'));
		var offsetY = number(field(field(note, 'offset'), 'y'));
		var scaleX = number(field(field(note, 'scale'), 'x'));
		var scaleY = number(field(field(note, 'scale'), 'y'));
		var renderCenterX:Null<Float> = x == null || originX == null
			|| offsetX == null || scaleX == null || frameWidth == null ? null
			: x + originX - offsetX - originX * scaleX + frameWidth * scaleX / 2;
		return {
			visible: field(note, 'visible'),
			alpha: number(field(note, 'alpha')),
			camera: camera(field(note, 'camera')),
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
			isSustainNote: field(note, 'isSustainNote'),
			wasGoodHit: field(note, 'wasGoodHit'),
			x: x,
			width: width,
			frameWidth: frameWidth,
			originX: originX,
			scaleX: scaleX,
			scaleY: scaleY,
			offsetX: offsetX,
			offsetY: offsetY,
			renderCenterX: renderCenterX,
			laneCenterX: x == null ? null : x + laneWidth / 2,
			centerErrorX: renderCenterX == null || x == null
				? null : renderCenterX - (x + laneWidth / 2)
		};
	}

	public static function camera(value:Dynamic):Dynamic {
		var filters:Array<Dynamic> = [];
		var live = field(value, 'filters');
		if (Std.isOfType(live, Array)) for (filter in (cast live:Array<Dynamic>)) {
			if (filter == null) continue;
			filters.push({type:Type.getClassName(Type.getClass(filter)),
				blurX:number(field(filter, 'blurX')), blurY:number(field(filter, 'blurY')),
				quality:number(field(filter, 'quality')),
				shaderPasses:number(field(filter, '__numShaderPasses'))});
		}
		return {
			filters:filters,
			visible: field(value, 'visible'), alpha: number(field(value, 'alpha')),
			zoom: number(field(value, 'zoom')), angle: number(field(value, 'angle')),
			x: number(field(value, 'x')), y: number(field(value, 'y')),
			width: number(field(value, 'width')), height: number(field(value, 'height')),
			scrollX: number(field(field(value, 'scroll'), 'x')),
			scrollY: number(field(field(value, 'scroll'), 'y')),
			fadeAlpha: number(field(value, '_fxFadeAlpha'))
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
			isPlayer: field(actor, 'isPlayer'),
			flipX: field(actor, 'flipX'),
			flipY: field(actor, 'flipY'),
			stageBaseFlipX: field(actor, 'stageBaseFlipX'),
			animationFlipX: field(current, 'flipX'),
			frameFlipX: field(field(actor, 'frame'), 'flipX'),
			libraryScaleX: field(field(field(actor, 'library'), 'matrix'), 'a'),
			libraryScaleY: field(field(field(actor, 'library'), 'matrix'), 'd'),
			requestedCharacter: field(actor, 'requestedCharacter'),
			resolvedCharacter: field(actor, 'resolvedCharacter'),
			resolvedAssetRoot: field(actor, 'resolvedAssetRoot'),
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

	/** Bounded source-stage inventory for an opt-in native smoke. It records
	 * the actual render members after stage scripts have finished loading. */
	public static function stage(stage:Dynamic):Dynamic {
		var raw = field(stage, 'members');
		var members:Array<Dynamic> = Std.isOfType(raw, Array) ? cast raw : [];
		var visuals:Array<Dynamic> = [];
		for (member in members) {
			if (member == null || visuals.length >= 128) continue;
			var kind = Type.getClass(member);
			var camera = field(member, 'camera');
			visuals.push({
				kind: kind == null ? '' : Type.getClassName(kind),
				exists: field(member, 'exists'),
				alive: field(member, 'alive'),
				bitmapWidth: number(field(field(field(member, 'graphic'), 'bitmap'), 'width')),
				bitmapHeight: number(field(field(field(member, 'graphic'), 'bitmap'), 'height')),
				visible: field(member, 'visible'),
				alpha: number(field(member, 'alpha')),
				blend: field(member, 'blend'),
				shader: field(field(member, 'shader'), 'fragmentPath'),
				camera: camera == field(stage, 'camGame') ? 'game' : camera == field(stage, 'camHUD') ? 'hud' : camera == field(stage, 'camOther') ? 'other' : 'explicit',
				ownerRoot: field(field(member, 'ownerPaths'), 'root'),
				graphicKey: graphicKey(member),
				atlasFrames: count(field(field(member, 'frames'), 'frames')),
				animation: field(field(field(member, 'animation'), 'curAnim'), 'name'),
				x: number(field(member, 'x')),
				y: number(field(member, 'y')),
				width: number(field(member, 'width')),
				height: number(field(member, 'height')),
				scaleX: number(field(field(member, 'scale'), 'x')),
				scaleY: number(field(field(member, 'scale'), 'y')),
				offsetX: number(field(field(member, 'offset'), 'x')),
				offsetY: number(field(field(member, 'offset'), 'y')),
				scrollFactorX: number(field(field(member, 'scrollFactor'), 'x')),
				scrollFactorY: number(field(field(member, 'scrollFactor'), 'y')),
				cameraWidth: number(field(camera, 'width')),
				cameraHeight: number(field(camera, 'height')),
				cameraZoom: number(field(camera, 'zoom')),
				cameraAlpha: number(field(camera, 'alpha')),
				cameraVisible: field(camera, 'visible'),
				cameraFadeAlpha: number(field(camera, '_fxFadeAlpha')),
				cameraScrollX: number(field(field(camera, 'scroll'), 'x')),
				cameraScrollY: number(field(field(camera, 'scroll'), 'y')),
				zIndex: field(member, 'zIndex')
			});
		}
		return {memberCount: members.length, members: visuals};
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
