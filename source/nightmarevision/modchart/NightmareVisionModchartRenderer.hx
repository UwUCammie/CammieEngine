package nightmarevision.modchart;

import haxe.ds.ObjectMap;

private typedef NightmareVisionSpriteBaseline = {
	var scaleX:Float;
	var scaleY:Float;
	var width:Float;
	var height:Float;
	var frameWidth:Float;
	var frameHeight:Float;
	var state:NightmareVisionModchartVisualState;
}

/**
	Small Flixel-facing adapter for the pure Nightmare Vision transform port.
	Sprite inputs stay Dynamic so this layer can also be exercised with source
	fixtures without initializing a game state. The runtime caller supplies the
	selected NoteSkin's offset table and exact current/end visual deltas.
*/
class NightmareVisionModchartRenderer {
	public final transform:NightmareVisionModchartTransform;
	public final skinOffsets:NightmareVisionModchartSkinOffsets;
	/** Optional bridge into the selected sprite's owner-local RGB graphics. */
	public var applyVisual:Null<Dynamic->NightmareVisionModchartVisualState->Void>;
	/** Receives features that have no host rendering bridge. */
	public var onUnsupportedFeature:Null<String->Void>;

	var baselines:ObjectMap<Dynamic, NightmareVisionSpriteBaseline> = new ObjectMap();
	var warnedUnsupported:ObjectMap<Dynamic, Map<String, Bool>> = new ObjectMap();

	public function new(transform:NightmareVisionModchartTransform,
		?skinOffsets:NightmareVisionModchartSkinOffsets,
		?applyVisual:Dynamic->NightmareVisionModchartVisualState->Void,
		?onUnsupportedFeature:String->Void) {
		if (transform == null) throw 'Nightmare Vision renderer requires a transform';
		this.transform = transform;
		this.skinOffsets = skinOffsets == null ? new NightmareVisionModchartSkinOffsets(transform.registry.keys) : skinOffsets;
		this.applyVisual = applyVisual;
		this.onUnsupportedFeature = onUnsupportedFeature;
	}

	/** Capture the post-skin base values once before per-frame modifier scaling. */
	public function configureNote(note:Dynamic):NightmareVisionModchartVisualState
		return configureSprite(note);

	public function configureReceptor(receptor:Dynamic):NightmareVisionModchartVisualState
		return configureSprite(receptor);

	public function configureSplash(splash:Dynamic):NightmareVisionModchartVisualState
		return configureSprite(splash);

	public function visualState(sprite:Dynamic):Null<NightmareVisionModchartVisualState> {
		var baseline = sprite == null ? null : baselines.get(sprite);
		return baseline == null ? null : baseline.state;
	}

	/** Drop a retired sprite's captured state and one-time feature warnings. */
	public function release(sprite:Dynamic):Void {
		if (sprite == null) return;
		baselines.remove(sprite);
		warnedUnsupported.remove(sprite);
	}

	/** Clear all sprite-owned snapshots when the modchart renderer is torn down. */
	public function destroy():Void {
		baselines = new ObjectMap();
		warnedUnsupported = new ObjectMap();
	}

	/**
		Source PlayState calls getPos/updateObject for the note, then computes the
		sustain direction and segment length from the exact future endpoint. The
		caller supplies both endpoint deltas so SV/visual-time behavior is retained.
	*/
	public function updateNote(context:NightmareVisionModchartContext, note:Dynamic, player:Int,
		visualDiff:Float, timeDiff:Float, endVisualDiff:Float, endTimeDiff:Float,
		endBeat:Float, ?strum:Dynamic, ?segmentDuration:Float,
		?isSustainEnd:Bool):NightmareVisionModchartVisualState {
		var baseline = ensureBaseline(note);
		if (baseline == null) return null;
		syncLiveBaseScale(note, baseline);
		var object = snapshot(note, NightmareVisionModchartObject.NOTE, player, baseline);
		if (segmentDuration != null) object.sustainLength = segmentDuration;
		if (isSustainEnd != null) object.isSustainEnd = isSustainEnd;
		var position = transform.getPosition(context, object, visualDiff, timeDiff, context.beat);
		transform.updateObject(context, object, position, context.beat);
		copySpriteResult(note, object, position, baseline, NightmareVisionModchartObject.NOTE);

		var state = baseline.state;
		if (object.isSustain) {
			var tailPosition = transform.getPosition(context, object, endVisualDiff, endTimeDiff, endBeat);
			var radians = Math.atan2(tailPosition.y - position.y, tailPosition.x - position.x);
			var degrees = radians * 180 / Math.PI - 90;
			state.holdAngle = degrees;
			setField(note, 'angle', degrees);
			var sustainSplash = linkedSustainSplash(note);
			if (object.wasGoodHit && sustainSplash != null && field(sustainSplash, 'alive') != false)
				setField(sustainSplash, 'angle', degrees);

			// Donor PlayState overwrites ScaleModifier's Y result after getPos:
			// each body stretches to the distance between its exact endpoints.
			var dx = tailPosition.x - position.x;
			var dy = tailPosition.y - position.y;
			var distance = Math.sqrt(dx * dx + dy * dy);
			state.holdSegmentDistance = distance;
			state.holdSegmentDuration = object.sustainLength;
			state.isSustainEnd = object.isSustainEnd;
			var isEnd = object.isSustainEnd;
			if (!isEnd) {
				var antialiasing = field(note, 'antialiasing') == true;
				var denominator = baseline.frameHeight - (antialiasing ? 1 : 0);
				if (denominator > 0 && Math.isFinite(distance)) {
					var bodyScaleY = distance / denominator;
					setScaleY(note, bodyScaleY);
					baseline.scaleY = bodyScaleY;
					setScaleField(note, 'baseScale', 'y', bodyScaleY);
					state.baseScaleY = bodyScaleY;
				}
			}
			if (strum != null) applySourceClip(note, strum, context, baseline, state);
		}
		applyVisualResult(note, state);
		return state;
	}

	/** Source modchart(splash) calls getPos(0, 0, 0), then updateObject. */
	public function updateReceptor(context:NightmareVisionModchartContext, receptor:Dynamic,
		player:Int):NightmareVisionModchartVisualState
		return updateSprite(context, receptor, NightmareVisionModchartObject.RECEPTOR, player,
			intField(receptor, 'noteData', intField(receptor, 'ID', 0)), 0, 0);

	public function updateSplash(context:NightmareVisionModchartContext, splash:Dynamic,
		kind:String, player:Int, data:Int):NightmareVisionModchartVisualState {
		if (kind != NightmareVisionModchartObject.NOTE_SPLASH
			&& kind != NightmareVisionModchartObject.SUSTAIN_SPLASH)
			throw 'Unsupported Nightmare Vision splash kind: ' + Std.string(kind);
		return updateSprite(context, splash, kind, player, data, 0, 0);
	}

	function updateSprite(context:NightmareVisionModchartContext, sprite:Dynamic, kind:String,
		player:Int, data:Int, visualDiff:Float, timeDiff:Float):NightmareVisionModchartVisualState {
		var baseline = ensureBaseline(sprite);
		if (baseline == null) return null;
		var object = snapshot(sprite, kind, player, baseline);
		object.data = data;
		var position = transform.getPosition(context, object, visualDiff, timeDiff, context.beat);
		transform.updateObject(context, object, position, context.beat);
		copySpriteResult(sprite, object, position, baseline, kind);
		applyVisualResult(sprite, baseline.state);
		return baseline.state;
	}

	function configureSprite(sprite:Dynamic):NightmareVisionModchartVisualState {
		if (sprite == null) return null;
		var scale = field(sprite, 'scale');
		var sourceBaseScale = liveBaseScale(sprite);
		var baseline:NightmareVisionSpriteBaseline = {
			scaleX:number(field(sourceBaseScale, 'x'), number(field(scale, 'x'), 1)),
			scaleY:number(field(sourceBaseScale, 'y'), number(field(scale, 'y'), 1)),
			width:number(field(sprite, 'width')),
			height:number(field(sprite, 'height')),
			frameWidth:number(field(sprite, 'frameWidth')),
			frameHeight:number(field(sprite, 'frameHeight')),
			state:new NightmareVisionModchartVisualState()
		};
		baselines.set(sprite, baseline);
		return baseline.state;
	}

	/** Source scripts can tween baseScale after sprite configuration. */
	function syncLiveBaseScale(sprite:Dynamic, baseline:NightmareVisionSpriteBaseline):Void {
		var point = liveBaseScale(sprite);
		if (point == null) return;
		baseline.scaleX = number(field(point, 'x'), baseline.scaleX);
		baseline.scaleY = number(field(point, 'y'), baseline.scaleY);
	}

	function liveBaseScale(sprite:Dynamic):Dynamic {
		var point = property(sprite, 'baseScale');
		return point == null ? property(sprite, 'defScale') : point;
	}

	function ensureBaseline(sprite:Dynamic):Null<NightmareVisionSpriteBaseline> {
		if (sprite == null) return null;
		var baseline = baselines.get(sprite);
		if (baseline == null) {
			configureSprite(sprite);
			baseline = baselines.get(sprite);
		}
		return baseline;
	}

	function snapshot(sprite:Dynamic, kind:String, player:Int,
		baseline:NightmareVisionSpriteBaseline):NightmareVisionModchartObject {
		var object = new NightmareVisionModchartObject(kind);
		object.player = player;
		object.data = intField(sprite, 'noteData', intField(sprite, 'direction', intField(sprite, 'ID', 0)));
		object.active = field(sprite, 'active') != false;
		object.isSustain = field(sprite, 'isSustainNote') == true;
		object.isSustainEnd = field(sprite, 'isSustainEnd') == true
			|| StringTools.endsWith(currentAnimation(sprite), 'end');
		object.wasGoodHit = field(sprite, 'wasGoodHit') == true;
		object.strumTime = number(field(sprite, 'strumTime'));
		object.sustainLength = number(field(sprite, 'sustainLength'));
		object.multSpeed = number(field(sprite, 'multSpeed'), 1);
		object.width = baseline.width;
		object.height = baseline.height;
		object.frameHeight = baseline.frameHeight;
		object.baseScaleX = baseline.scaleX;
		object.baseScaleY = baseline.scaleY;
		object.scaleX = baseline.scaleX;
		object.scaleY = baseline.scaleY;
		object.x = number(field(sprite, 'x'));
		object.y = number(field(sprite, 'y'));
		object.typeOffsetX = number(field(sprite, 'offsetX'), number(field(sprite, 'typeOffsetX')));
		object.typeOffsetY = number(field(sprite, 'offsetY'), number(field(sprite, 'typeOffsetY')));
		return object;
	}

	function copySpriteResult(sprite:Dynamic, object:NightmareVisionModchartObject,
		position:NightmareVisionModchartVector, baseline:NightmareVisionSpriteBaseline,
		kind:String):Void {
		var state = baseline.state;
		state.position = position.copy();
		state.baseScaleX = baseline.scaleX;
		state.baseScaleY = baseline.scaleY;
		state.alphaMod = object.alphaMod;
		state.rgbFlash = object.rgbFlash;
		state.rgbAlpha = object.rgbAlpha;
		var offset = skinOffsets.get(kind, object.data, object.isSustain);
		state.spriteOffsetX = offset.x + object.spriteOffsetX;
		state.spriteOffsetY = offset.y + object.spriteOffsetY;
		if (kind == NightmareVisionModchartObject.NOTE && object.isSustainEnd) {
			var endOffset = skinOffsets.getSustainEnd(object.data);
			state.spriteOffsetX += endOffset.x;
			state.spriteOffsetY += endOffset.y;
		}

		setField(sprite, 'x', object.x);
		setField(sprite, 'y', object.y);
		var scale = field(sprite, 'scale');
		setField(scale, 'x', object.scaleX);
		setField(scale, 'y', object.scaleY);
		if (kind == NightmareVisionModchartObject.NOTE || kind == NightmareVisionModchartObject.RECEPTOR)
			setField(sprite, 'angle', object.angle);

		if (object.centerOriginAndOffsets) {
			callNoArg(sprite, 'centerOrigin');
			callNoArg(sprite, 'centerOffsets');
			if (kind == NightmareVisionModchartObject.NOTE && object.isSustain) {
				setNestedField(sprite, 'origin', 'y', 0);
				setNestedField(sprite, 'offset', 'y', 0);
			}
		}
		setNestedPoint(sprite, 'spriteOffset', state.spriteOffsetX, state.spriteOffsetY);
		// Keep the source-only draw offset accessible to a host renderer even
		// when the native FlxSprite class has no `spriteOffset` vector.
		try {
			Reflect.setField(sprite, 'nightmareVisionSourceOffsetX', state.spriteOffsetX);
			Reflect.setField(sprite, 'nightmareVisionSourceOffsetY', state.spriteOffsetY);
		} catch (_:Dynamic) {}
	}

	function applySourceClip(note:Dynamic, strum:Dynamic,
		context:NightmareVisionModchartContext, baseline:NightmareVisionSpriteBaseline,
		state:NightmareVisionModchartVisualState):Void {
		var reduce = field(strum, 'sustainReduce');
		if (reduce == null) reduce = true; // NMV StrumNote's declared default.
		if (reduce != true || field(note, 'wasGoodHit') != true
			|| context.songPosition < number(field(note, 'strumTime'))) return;
		var noteScale = field(note, 'scale');
		var scaleY = number(field(noteScale, 'y'), 1);
		if (scaleY == 0) return;
		var x = number(field(note, 'x')) - number(field(strum, 'x'))
			- (number(field(strum, 'width')) - number(field(note, 'width'))) * 0.5;
		var y = number(field(note, 'y')) - number(field(strum, 'y'))
			- number(field(strum, 'height')) * 0.5;
		var clipY = Math.sqrt(x * x + y * y) / scaleY;
		state.clipX = 0;
		state.clipY = clipY;
		state.clipWidth = baseline.frameWidth;
		state.clipHeight = baseline.frameHeight - clipY;
		state.clipApplied = true;
		applyClipRect(note, state);
	}

	static function applyClipRect(sprite:Dynamic, state:NightmareVisionModchartVisualState):Void {
		var rect = field(sprite, 'clipRect');
		if (rect == null) {
			var rectClass = Type.resolveClass('flixel.math.FlxRect');
			if (rectClass != null) {
				try rect = Type.createInstance(rectClass, [0, state.clipY, state.clipWidth, state.clipHeight]) catch (_:Dynamic) {}
			}
			if (rect == null) rect = {x:0.0, y:state.clipY, width:state.clipWidth, height:state.clipHeight};
		}
		setField(rect, 'x', 0);
		setField(rect, 'y', state.clipY);
		setField(rect, 'width', state.clipWidth);
		setField(rect, 'height', state.clipHeight);
		setField(sprite, 'clipRect', rect);
	}

	function applyVisualResult(sprite:Dynamic, state:NightmareVisionModchartVisualState):Void {
		if (applyVisual != null) {
			applyVisual(sprite, state);
			return;
		}
		if (state.rgbFlash != 0) warnUnsupported(sprite, 'stealthGlow');
	}

	function warnUnsupported(sprite:Dynamic, feature:String):Void {
		var warned = warnedUnsupported.get(sprite);
		if (warned == null) {
			warned = new Map();
			warnedUnsupported.set(sprite, warned);
		}
		if (warned.exists(feature)) return;
		warned.set(feature, true);
		var message = 'Nightmare Vision render effect is unsupported without an owner-local visual bridge: ' + feature;
		if (onUnsupportedFeature != null) onUnsupportedFeature(message);
		else trace('[nightmare-vision-modchart] ' + message);
	}

	static function linkedSustainSplash(note:Dynamic):Dynamic {
		var direct = field(note, 'sustainSplash');
		if (direct != null) return direct;
		var tailState = field(note, 'tailState');
		return field(tailState, 'splash');
	}

	static function currentAnimation(sprite:Dynamic):String {
		var animation = field(sprite, 'animation');
		var current = field(animation, 'curAnim');
		var name = field(current, 'name');
		return name == null ? '' : Std.string(name);
	}

	static function field(value:Dynamic, name:String):Dynamic
		return value == null ? null : Reflect.field(value, name);

	static function property(value:Dynamic, name:String):Dynamic {
		if (value == null) return null;
		try {
			var result = Reflect.getProperty(value, name);
			return result == null ? Reflect.field(value, name) : result;
		} catch (_:Dynamic) {
			return Reflect.field(value, name);
		}
	}

	static function number(value:Dynamic, fallback:Float = 0):Float {
		if (value == null) return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) || !Math.isFinite(parsed) ? fallback : parsed;
	}

	static function intField(value:Dynamic, name:String, fallback:Int):Int {
		var raw = field(value, name);
		return raw == null ? fallback : Std.int(number(raw, fallback));
	}

	static function setField(target:Dynamic, name:String, value:Dynamic):Void {
		if (target == null) return;
		try Reflect.setProperty(target, name, value) catch (_:Dynamic) {}
	}

	static function setNestedField(target:Dynamic, name:String, child:String, value:Dynamic):Void
		setField(field(target, name), child, value);

	static function setNestedPoint(target:Dynamic, name:String, x:Float, y:Float):Void {
		var point = field(target, name);
		if (point == null) return;
		var setter = Reflect.field(point, 'set');
		if (setter != null && Reflect.isFunction(setter)) {
			try Reflect.callMethod(point, setter, [x, y]) catch (_:Dynamic) {}
		} else {
			setField(point, 'x', x);
			setField(point, 'y', y);
		}
	}

	static function setScaleY(sprite:Dynamic, value:Float):Void
		setNestedField(sprite, 'scale', 'y', value);

	static function setScaleField(sprite:Dynamic, scaleName:String, axis:String, value:Float):Void {
		var point = scaleName == 'baseScale' || scaleName == 'defScale'
			? property(sprite, scaleName) : field(sprite, scaleName);
		setField(point, axis, value);
	}

	static function callNoArg(target:Dynamic, name:String):Void {
		var method = field(target, name);
		if (method != null && Reflect.isFunction(method))
			try Reflect.callMethod(target, method, []) catch (_:Dynamic) {}
	}
}
