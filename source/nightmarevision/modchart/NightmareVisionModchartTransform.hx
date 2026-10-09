package nightmarevision.modchart;

import nightmarevision.modchart.NightmareVisionModifierRegistry.NightmareVisionModifierExecution;

private typedef InfinitePathCache = {
	var points:Array<NightmareVisionModchartVector>;
	var totalDistance:Float;
}

/**
	Source-formula port with an ordered live-instance execution bridge.
	Builtin formulas use snapshots; owner callbacks receive the real native sprite.
	Formula provenance is the supplied NMV source tree's ModManager and
	modifiers/*.hx implementations. The owner manager resolves scripted/custom instances at each active-name step.
*/
class NightmareVisionModchartTransform {
	var currentFormulaEntry:Null<NightmareVisionModifierExecution>;
	public final registry:NightmareVisionModifierRegistry;
	static var infinitePathCache:Map<String, InfinitePathCache> = new Map();

	public function new(registry:NightmareVisionModifierRegistry) {
		if (registry == null) throw 'Nightmare Vision transform requires a registry';
		this.registry = registry;
	}

	/** Source ModManager.getCenterX/getStrumX/getBaseX equations. */
	public static function centerX(width:Float, noteWidth:Float, keys:Int, player:Int):Float {
		return switch (player) {
			case 0: width - noteWidth * (keys / 2) - 100 - 3;
			case 1: noteWidth * (keys / 2) + 100 - 3;
			default: width * 0.5 - 3;
		};
	}

	public static function strumX(noteWidth:Float, keys:Int, data:Int):Float
		return noteWidth * (data - (keys / 2) + 0.5);

	public static function baseX(context:NightmareVisionModchartContext, data:Int, player:Int):Float
		return context.legacyCoordinates ? NightmareVisionPlayfieldLayout.legacyBaseX(data, player, context.width, context.noteWidth)
			: centerX(context.width, context.noteWidth, context.keys, player)
			+ strumX(context.noteWidth, context.keys, data);

	public static function baseY(noteWidth:Float):Float return noteWidth * 0.5 + 50;

	/** Source ModManager.getVisPos, used by donor alpha and note construction. */
	public static function visualPosition(songPosition:Float, strumTime:Float, songSpeed:Float, legacyCoordinates:Bool = false):Float
		return -0.45 * (songPosition - strumTime) * (legacyCoordinates ? 1 : songSpeed);

	/**
		Run the source getPos chain, in the source ModifierOrder and registration
		order. The caller supplies the same visualDiff/timeDiff values as PlayState.
	*/
	public function getPosition(context:NightmareVisionModchartContext, object:NightmareVisionModchartObject,
		visualDiff:Float, timeDiff:Float, beat:Float):NightmareVisionModchartVector {
		return getPositionInto(context, object, visualDiff, timeDiff, beat,
			new NightmareVisionModchartVector());
	}

	/** Initialize caller-owned storage; a source modifier may return another vector.
	 * The caller owns the returned position through the end of the render pass. */
	public function getPositionInto(context:NightmareVisionModchartContext, object:NightmareVisionModchartObject,
		visualDiff:Float, timeDiff:Float, beat:Float, pos:NightmareVisionModchartVector, ?exclusions:Array<String>,
		?time:Float):NightmareVisionModchartVector {
		if (pos == null) throw 'Nightmare Vision position output cannot be null';
		if (registry.executionNames == null) { pos.x = 0; pos.y = 0; pos.z = 0; }
		if (object == null || !liveActive(object)) return pos;
		pos.z = 0;
		pos.x = baseX(context, object.data, object.player);
		pos.y = (context.legacyCoordinates ? 50 : baseY(context.noteWidth)) + visualDiff;

		for (name in registry.executionList(object.player)) {
			if (!liveActive(object) || exclusions != null && exclusions.indexOf(name) >= 0) continue;
			var entry = registry.executionEntry == null ? null : registry.executionEntry(name);
			if (registry.executionEntry != null && entry == null) continue;
			if (entry != null && entry.builtin == null) {
				pos = entry.getPosition(time == null ? object.kind == NightmareVisionModchartObject.NOTE ? object.strumTime : 0 : time,
					visualDiff, timeDiff, beat, pos, object.data, object.player, object.nativeObject);
				if (object.readLive != null) object.readLive();
				continue;
			}
			var family = entry == null ? name : entry.builtin;
			pos = applyInstancePosition(context, entry, object, pos,
				time == null ? object.strumTime : time, visualDiff, timeDiff, beat, family);
		}
		return pos;
	}

	/**
		Apply source updateObject's note/receptor/splash passes to a primitive
		object snapshot. Flixel centering and final engine offsets are signaled via
		centerOriginAndOffsets for the host adapter to perform on its real object.
	*/
	public function updateObject(context:NightmareVisionModchartContext,
		object:NightmareVisionModchartObject, position:NightmareVisionModchartVector,
		beat:Float):Void {
		if (object == null || position == null) return;
		object.livePosition = position;
		// Historical updateObject only runs modifiers/centering. Gameplay assigns
		// the resulting position afterward; direct script calls preserve x/y.
		if (!context.legacyCoordinates) {
			object.x = position.x - object.width * 0.5;
			object.y = object.kind == NightmareVisionModchartObject.NOTE && object.isSustain
				? position.y : position.y - object.height * 0.5;
		}

		for (name in registry.executionList(object.player)) {
			if (!liveActive(object)) continue;
			var entry = registry.executionEntry == null ? null : registry.executionEntry(name);
			if (registry.executionEntry != null && entry == null) continue;
			if (entry != null && entry.builtin == null) {
				if (object.flushLive != null) object.flushLive();
				entry.updateObject(beat, object.nativeObject, position, object.player, object.kind);
				if (object.readLive != null) object.readLive();
				continue;
			}
			var family = entry == null ? name : entry.builtin;
			applyInstanceObject(context, entry, object, position, beat, family);
		}

		object.centerOriginAndOffsets = true;
		if (object.kind == NightmareVisionModchartObject.NOTE) {
			object.spriteOffsetX = context.legacyCoordinates ? object.legacyTypeOffsetX : object.typeOffsetX;
			object.spriteOffsetY = context.legacyCoordinates ? object.legacyTypeOffsetY : object.typeOffsetY;
		}
	}

	/** One formula only: no base positioning, liveness gate, traversal or final centering. */
	public function applyInstancePosition(context:NightmareVisionModchartContext,
		entry:NightmareVisionModifierExecution, object:NightmareVisionModchartObject,
		pos:NightmareVisionModchartVector, time:Float, visualDiff:Float, timeDiff:Float,
		beat:Float, ?family:String):NightmareVisionModchartVector {
		if (family == null) family = entry.builtin;
		var previous = currentFormulaEntry;
		currentFormulaEntry = entry;
		try { switch (family) {
			case 'reverse': applyReverse(context, object, pos, visualDiff);
			case 'opponentSwap': applyOpponentSwap(context, object, pos);
			case 'flip': applyFlip(context, object, pos);
			case 'invert': applyInvert(context, object, pos);
			case 'drunk': applyDrunk(context, object, pos, visualDiff);
			case 'beat': applyBeat(context, object, pos, visualDiff, beat);
			case 'receptorScroll': applyReceptorScroll(context, object, pos, timeDiff);
			case 'transformX': applyTransform(object, pos);
			case 'infinite', 'path':
				if (entry != null && entry.state != null) pos = instancePathPosition(object, pos, visualDiff, timeDiff);
				else applyInfinitePath(context, object, pos, visualDiff, timeDiff);
			case 'boost': applyBoost(context, object, pos, visualDiff);
			case 'rotateX': applyRotate(context, object, pos, '', false);
			case 'centerrotateX': applyRotate(context, object, pos, 'center', true);
			case 'localrotateX': applyLocalRotate(context, object, pos);
			case 'perspectiveDONTUSE':
				if (entry != null && entry.state != null) pos = perspectiveVector(context, pos.z, pos);
				else applyPerspective(context, pos);
			default:
		} } catch (error:Dynamic) { currentFormulaEntry = previous; throw error; }
		currentFormulaEntry = previous;
		return pos;
	}

	public function applyInstanceObject(context:NightmareVisionModchartContext,
		entry:NightmareVisionModifierExecution, object:NightmareVisionModchartObject,
		position:NightmareVisionModchartVector, beat:Float, ?family:String):Void {
		if (family == null) family = entry.builtin;
		var previous = currentFormulaEntry;
		currentFormulaEntry = entry;
		try { switch (family) {
			case 'stealth': applyAlpha(context, object);
			case 'confusion': applyConfusion(object);
			case 'receptorScroll': applyReceptorScrollObject(context, object);
			case 'mini': applyScale(object);
			case 'xmod': applyXMod(object);
			case 'perspectiveDONTUSE': applyPerspectiveScale(object, position);
			default:
		} } catch (error:Dynamic) { currentFormulaEntry = previous; throw error; }
		currentFormulaEntry = previous;
	}

	public function instanceReverseValue(context:NightmareVisionModchartContext,
		entry:NightmareVisionModifierExecution, dir:Int, player:Int, scrolling:Bool = false):Float {
		var previous = currentFormulaEntry;
		currentFormulaEntry = entry;
		var result:Float;
		try { result = reverseFactor(context, dir, player, scrolling); }
		catch (error:Dynamic) { currentFormulaEntry = previous; throw error; }
		currentFormulaEntry = previous;
		return result;
	}

	public function alphaBoundary(context:NightmareVisionModchartContext,
		entry:NightmareVisionModifierExecution, boundary:String, player:Int):Float {
		var previous = currentFormulaEntry;
		currentFormulaEntry = entry;
		var result:Float;
		try { result = boundaryValue(context, boundary, player); }
		catch (error:Dynamic) { currentFormulaEntry = previous; throw error; }
		currentFormulaEntry = previous;
		return result;
	}

	function boundaryValue(context:NightmareVisionModchartContext, boundary:String, player:Int):Float {
		var hs = sub('stealth', 'hidden', player) * sub('stealth', 'sudden', player);
		if (boundary == 'hiddenSudden') return hs;
		var fade = currentFormulaEntry != null && currentFormulaEntry.state != null ? currentFormulaEntry.state.fadeDistY : 120;
		var hidden = StringTools.startsWith(boundary, 'hidden');
		var end = StringTools.endsWith(boundary, 'End');
		var lo = hidden ? (end ? -1.0 : 0.0) : (end ? 1.0 : 0.0);
		var hi = hidden ? (end ? -1.25 : -0.25) : (end ? 1.25 : 0.25);
		return context.height * 0.5 + fade * scale(hs, 0, 1, lo, hi)
			+ context.height * 0.5 * sub('stealth', hidden ? 'hiddenOffset' : 'suddenOffset', player);
	}

	public function instancePerspectiveVector(context:NightmareVisionModchartContext,
		entry:NightmareVisionModifierExecution, z:Float, pos:NightmareVisionModchartVector):NightmareVisionModchartVector {
		var previous = currentFormulaEntry;
		currentFormulaEntry = entry;
		var result:NightmareVisionModchartVector;
		try { result = perspectiveVector(context, z, pos); }
		catch (error:Dynamic) { currentFormulaEntry = previous; throw error; }
		currentFormulaEntry = previous;
		return result;
	}

	function perspectiveVector(context:NightmareVisionModchartContext, curZ:Float,
		pos:NightmareVisionModchartVector):NightmareVisionModchartVector {
		if (Math.abs(curZ) < NightmareVisionModchartMath.EPSILON) return pos;
		var half = currentFormulaEntry.state.halfOffset;
		pos.subtract(half, pos);
		var ox = pos.x, oy = pos.y;
		pos.put();
		var clipped = curZ - 1;
		if (clipped > 0) clipped = 0;
		var tangent = NightmareVisionModchartMath.fastSin(Math.PI / 4) / NightmareVisionModchartMath.fastCos(Math.PI / 4);
		var result = NightmareVisionModchartVector.get(ox / tangent / -clipped, oy / tangent / -clipped, -clipped);
		return result.add(half, result);
	}

	public static function tracePath(state:NightmareVisionModifierFormulaState,
		path:Array<Array<NightmareVisionModchartVector>>):Void {
		state.pathData.resize(0);
		state.totalDists.resize(0);
		for (dir in 0...path.length) {
			state.pathData[dir] = [];
			state.totalDists[dir] = 0;
			for (index in 0...path[dir].length) {
				var pos = path[dir][index];
				if (index > 0) {
					var last = state.pathData[dir][index - 1];
					var distance = state.totalDists[dir] += NightmareVisionModchartVector.distance(last.position, pos);
					last.end = distance;
					last.dist = last.start - distance;
				}
				state.pathData[dir].push({position:pos, start:state.totalDists[dir], end:state.totalDists[dir], dist:0});
			}
		}
	}

	function instancePathPosition(object:NightmareVisionModchartObject, pos:NightmareVisionModchartVector,
		visualDiff:Float, timeDiff:Float):NightmareVisionModchartVector {
		var state = currentFormulaEntry.state;
		var value = currentFormulaEntry.value(object.player);
		if (value == 0 || state.pathData.length == 0) return pos;
		var path = state.pathData[object.data % state.pathData.length];
		var total = state.totalDists[object.data % state.pathData.length];
		var speed = state.moveSpeed * (1 - currentFormulaEntry.subValue(state.prefix + 'speed', object.player));
		var progress = (currentFormulaEntry.subValue(state.prefix + 'visual', object.player) > 0 ? visualDiff : timeDiff) / speed * total;
		var clamped = clamp(progress, 0, total);
		for (index in 0...path.length - 1) {
			var current = path[index];
			if (clamped >= current.start && clamped <= current.end) {
				var alpha = (current.start - progress) / current.dist;
				return pos.lerp(current.position.lerp(path[index + 1].position, alpha), value);
			}
		}
		return path.length == 0 ? pos : pos.lerp(path[0].position, value);
	}

	static function liveActive(object:NightmareVisionModchartObject):Bool {
		if (object.nativeObject == null) return object.active;
		return Reflect.getProperty(object.nativeObject, 'active') != false;
	}

	function get(family:String, player:Int):Float {
		if (currentFormulaEntry != null && currentFormulaEntry.value != null)
			return currentFormulaEntry.value(player);
		return registry.value(family, player);
	}

	function sub(family:String, name:String, player:Int):Float {
		if (currentFormulaEntry != null && currentFormulaEntry.subValue != null)
			return currentFormulaEntry.subValue(name, player);
		return registry.getSubmodValue(family, name, player);
	}

	static inline function scale(value:Float, lowA:Float, highA:Float, lowB:Float, highB:Float):Float
		return (value - lowA) * (highB - lowB) / (highA - lowA) + lowB;

	static inline function clamp(value:Float, low:Float, high:Float):Float {
		if (value > high) value = high;
		if (value < low) value = low;
		return value;
	}

	static inline function lerp(a:Float, b:Float, t:Float):Float return a + (b - a) * t;

	function reverseFactor(context:NightmareVisionModchartContext, data:Int, player:Int,
		scrolling:Bool = false):Float {
		var suffix = scrolling ? 'Scroll' : '';
		var keys = currentFormulaEntry != null && currentFormulaEntry.state != null && currentFormulaEntry.state.receptorCount != null
			? currentFormulaEntry.state.receptorCount(player) : context.keys;
		var val = 0.0;
		if (data >= keys / 2) val += sub('reverse', 'split' + suffix, player);
		if (data % 2 == 1) val += sub('reverse', 'alternate' + suffix, player);
		if (data >= keys / 4 && data <= keys * 3 / 4 - 1)
			val += sub('reverse', 'cross' + suffix, player);
		if (!scrolling) val += get('reverse', player) + sub('reverse', 'reverse' + data, player);
		else val += sub('reverse', 'reverse' + suffix, player);
		if (sub('reverse', 'unboundedReverse', player) == 0) {
			val %= 2;
			if (val > 1) val = 2 - val;
		}
		if (context.downScroll) val = 1 - val;
		return val;
	}

	function applyReverse(context:NightmareVisionModchartContext, object:NightmareVisionModchartObject,
		pos:NightmareVisionModchartVector, visualDiff:Float):Void {
		var reverse = reverseFactor(context, object.data, object.player);
		var shift = scale(reverse, 0, 1, context.legacyCoordinates ? 50 : 50 + context.noteWidth * 0.5,
			context.legacyCoordinates ? context.height - 150 : context.height - 50 - context.noteWidth * 0.5);
		shift = scale(sub('reverse', 'centered', object.player), 0, 1, shift, context.height / 2 - (context.legacyCoordinates ? 56 : 0));
		var multiplier = scale(reverse, 0, 1, 1, -1);
		pos.y = shift + visualDiff * multiplier;
		if (context.legacyCoordinates && object.kind == NightmareVisionModchartObject.NOTE && object.isSustain && reverse > 0) {
			var crochet = 60000 / context.songBpm;
			var speed = context.songSpeed * object.multSpeed;
			var adjusted = pos.y;
			if (object.isSustainEnd) {
				adjusted += 10.5 * (crochet * 0.0025) * 1.5 * speed + 46 * (speed - 1);
				adjusted -= 46 * (1 - crochet / 600) * speed;
				adjusted -= 19;
			}
			adjusted += context.noteWidth * 0.5 - 60.5 * (speed - 1);
			adjusted += 27.5 * (context.songBpm * 0.01 - 1) * (speed - 1);
			pos.y = lerp(pos.y, adjusted, reverse);
		}
	}

	function applyOpponentSwap(context:NightmareVisionModchartContext,
		object:NightmareVisionModchartObject, pos:NightmareVisionModchartVector):Void {
		var opposite = 1 - object.player;
		var distanceX = baseX(context, object.data, opposite) - baseX(context, object.data, object.player);
		pos.x += distanceX * get('opponentSwap', object.player);
	}

	function applyFlip(context:NightmareVisionModchartContext, object:NightmareVisionModchartObject,
		pos:NightmareVisionModchartVector):Void {
		var distance = context.noteWidth * (context.keys * 0.5 - 0.5 - object.data) * 2;
		pos.x += distance * get('flip', object.player);
	}

	function applyInvert(context:NightmareVisionModchartContext, object:NightmareVisionModchartObject,
		pos:NightmareVisionModchartVector):Void {
		var distance = context.noteWidth * (object.data % 2 == 0 ? 1 : -1);
		pos.x += distance * get('invert', object.player);
	}

	function applyDrunk(context:NightmareVisionModchartContext, object:NightmareVisionModchartObject,
		pos:NightmareVisionModchartVector, visualDiff:Float):Void {
		var player = object.player;
		var drunk = get('drunk', player);
		var tipsy = sub('drunk', 'tipsy', player);
		var bumpy = sub('drunk', 'bumpy', player);
		var tipZ = sub('drunk', 'tipZ', player);
		var time = context.songPosition / 1000;
		if (tipsy != 0) {
			var speed = sub('drunk', 'tipsySpeed', player);
			var offset = sub('drunk', 'tipsyOffset', player);
			pos.y += tipsy * (NightmareVisionModchartMath.fastCos(time * ((speed * 1.2) + 1.2)
				+ object.data * ((offset * 1.8) + 1.8)) * context.noteWidth * 0.4);
		}
		if (drunk != 0) {
			var speed = sub('drunk', 'drunkSpeed', player);
			var period = sub('drunk', 'drunkPeriod', player);
			var offset = sub('drunk', 'drunkOffset', player);
			var angle = time * (1 + speed) + object.data * ((offset * 0.2) + 0.2)
				+ visualDiff * ((period * 10) + 10) / context.height;
			pos.x += drunk * (NightmareVisionModchartMath.fastCos(angle) * context.noteWidth * 0.5);
		}
		if (tipZ != 0) {
			var speed = sub('drunk', 'tipZSpeed', player);
			var offset = sub('drunk', 'tipZOffset', player);
			pos.z += tipZ * (NightmareVisionModchartMath.fastCos(time * ((speed * 1.2) + 1.2)
				+ object.data * ((offset * 1.8) + 3.2)) * 0.15);
		}
		if (bumpy != 0) {
			var period = sub('drunk', 'bumpyPeriod', player);
			var offset = sub('drunk', 'bumpyOffset', player);
			var angle = (visualDiff + 100.0 * offset) / ((period * 16.0) + 16.0);
			pos.z += (bumpy * 40 * NightmareVisionModchartMath.fastSin(angle)) / 250;
		}
	}

	function applyBeat(context:NightmareVisionModchartContext, object:NightmareVisionModchartObject,
		pos:NightmareVisionModchartVector, visualDiff:Float, _beat:Float):Void {
		var value = get('beat', object.player);
		if (value == 0) return;
		var accelTime = 0.3;
		var totalTime = 0.7;
		// Donor BeatModifier reads PlayState.instance.curDecBeat, not the beat
		// argument supplied to Modifier.getPos.
		var beat = context.beat + accelTime;
		var oddBeat = Std.int(beat) % 2 != 0;
		if (beat < 0) return;
		beat -= Math.floor(beat);
		beat += 1;
		beat -= Math.floor(beat);
		if (beat >= totalTime) return;
		var amount = 0.0;
		if (beat < accelTime) {
			amount = scale(beat, 0, accelTime, 0, 1);
			amount *= amount;
		} else {
			amount = scale(beat, accelTime, totalTime, 1, 0);
			amount = 1 - (1 - amount) * (1 - amount);
		}
		if (oddBeat) amount *= -1;
		var shift = 40 * amount * NightmareVisionModchartMath.fastSin((visualDiff / 30) + Math.PI / 2);
		pos.x += value * shift;
	}

	function applyReceptorScroll(context:NightmareVisionModchartContext,
		object:NightmareVisionModchartObject, pos:NightmareVisionModchartVector,
		timeDiff:Float):Void {
		var moveSpeed = currentFormulaEntry != null && currentFormulaEntry.state != null ? currentFormulaEntry.state.moveSpeed : context.crotchet * 3;
		var diff = timeDiff;
		var songPosition = context.songPosition;
		var visual = -(-diff - songPosition) / moveSpeed;
		var reversed = Math.floor(visual) % 2 == 0;
		var startY = pos.y;
		var percent = reversed ? 1 - visual % 1 : visual % 1;
		var upscrollOffset = 50.0;
		var downscrollOffset = context.height - 50 - context.noteWidth;
		var endY = upscrollOffset + ((downscrollOffset - context.noteWidth / 2) * percent);
		pos.y = lerp(startY, endY, get('receptorScroll', object.player)) + context.noteWidth * 0.5;
	}

	function applyTransform(object:NightmareVisionModchartObject,
		pos:NightmareVisionModchartVector):Void {
		var player = object.player;
		pos.x += get('transformX', player) + sub('transformX', 'transformX-a', player);
		pos.y += sub('transformX', 'transformY', player) + sub('transformX', 'transformY-a', player);
		pos.z += sub('transformX', 'transformZ', player) + sub('transformX', 'transformZ-a', player);
		pos.x += sub('transformX', 'transform' + object.data + 'X', player)
			+ sub('transformX', 'transform' + object.data + 'X-a', player);
		pos.y += sub('transformX', 'transform' + object.data + 'Y', player)
			+ sub('transformX', 'transform' + object.data + 'Y-a', player);
		pos.z += sub('transformX', 'transform' + object.data + 'Z', player)
			+ sub('transformX', 'transform' + object.data + 'Z-a', player);
	}

	function applyInfinitePath(context:NightmareVisionModchartContext,
		object:NightmareVisionModchartObject, pos:NightmareVisionModchartVector,
		visualDiff:Float, timeDiff:Float):Void {
		var value = get('infinite', object.player);
		if (value == 0) return;
		var data = infinitePath(context);
		if (data.points.length == 0) return;
		var moveSpeed = 1850 * (1 - sub('infinite', 'infiniteSpeed', object.player));
		var diff = sub('infinite', 'infiniteVisual', object.player) > 0 ? visualDiff : timeDiff;
		var progress = diff / moveSpeed * data.totalDistance;
		var clamped = progress < 0 ? 0 : (progress > data.totalDistance ? data.totalDistance : progress);
		for (index in 0...data.points.length - 1) {
			var current = data.points[index];
			var next = data.points[index + 1];
			var start = index == 0 ? 0 : pathDistanceTo(data.points, index);
			var end = pathDistanceTo(data.points, index + 1);
			if (clamped >= start && clamped <= end) {
				var segmentDistance = start - end;
				var alpha = (start - progress) / segmentDistance;
				pos.x = lerp(pos.x, current.x + (next.x - current.x) * alpha, value);
				pos.y = lerp(pos.y, current.y + (next.y - current.y) * alpha, value);
				pos.z = lerp(pos.z, current.z + (next.z - current.z) * alpha, value);
				return;
			}
		}
		var first = data.points[0];
		pos.x = lerp(pos.x, first.x, value);
		pos.y = lerp(pos.y, first.y, value);
		pos.z = lerp(pos.z, first.z, value);
	}

	function infinitePath(context:NightmareVisionModchartContext):InfinitePathCache {
		var key = Std.string(context.width) + 'x' + Std.string(context.height) + ':' + context.lowQuality;
		var existing = infinitePathCache.get(key);
		if (existing != null) return existing;
		var points:Array<NightmareVisionModchartVector> = [];
		var step = context.lowQuality ? 15 : 3;
		var degrees = 0;
		while (degrees < 360) {
			var radians = degrees * Math.PI / 180;
			points.push(new NightmareVisionModchartVector(
				context.width * 0.5 + NightmareVisionModchartMath.fastSin(radians) * 600,
				context.height * 0.5 + NightmareVisionModchartMath.fastSin(radians) * NightmareVisionModchartMath.fastCos(radians) * 600,
				0));
			degrees += step;
		}
		var distance = 0.0;
		for (index in 1...points.length) distance += NightmareVisionModchartVector.distance(points[index - 1], points[index]);
		var result:InfinitePathCache = {points:points, totalDistance:distance};
		infinitePathCache.set(key, result);
		return result;
	}

	function pathDistanceTo(points:Array<NightmareVisionModchartVector>, endIndex:Int):Float {
		var total = 0.0;
		for (index in 1...(endIndex + 1)) total += NightmareVisionModchartVector.distance(points[index - 1], points[index]);
		return total;
	}

	function applyBoost(context:NightmareVisionModchartContext,
		object:NightmareVisionModchartObject, pos:NightmareVisionModchartVector,
		visualDiff:Float):Void {
		var player = object.player;
		var wave = sub('boost', 'wave', player);
		var brake = sub('boost', 'brake', player);
		var boost = get('boost', player);
		var effectHeight = 500.0;
		var yAdjust = 0.0;
		var reversePercent = currentFormulaEntry != null && currentFormulaEntry.state != null
			? currentFormulaEntry.state.reverseValue(object.data, player, false) : reverseFactor(context, object.data, player);
		var multiplier = scale(reversePercent, 0, 1, 1, -1);
		if (brake != 0) {
			var factor = scale(visualDiff, 0, effectHeight, 0, 1);
			var offset = visualDiff * factor;
			yAdjust += clamp(brake * (offset - visualDiff), -400, 400);
		}
		if (boost != 0) {
			var offset = visualDiff * 1.5 / ((visualDiff + effectHeight / 1.2) / effectHeight);
			yAdjust += clamp(boost * (offset - visualDiff), -400, 400);
		}
		yAdjust += wave * 20 * NightmareVisionModchartMath.fastSin(visualDiff / 38);
		pos.y += yAdjust * multiplier;
	}

	/** Source rotateV3 vector ownership, with MathUtil.rotate's scalar equations. */
	static function rotateVector(vec:NightmareVisionModchartVector, xAngle:Float,
		yAngle:Float, zAngle:Float):NightmareVisionModchartVector {
		var zx = vec.x * Math.cos(zAngle) - vec.y * Math.sin(zAngle);
		var zy = vec.x * Math.sin(zAngle) + vec.y * Math.cos(zAngle);
		var offZ = NightmareVisionModchartVector.get(zx, zy, vec.z);
		var xx = offZ.z * Math.cos(xAngle) - offZ.y * Math.sin(xAngle);
		var xy = offZ.z * Math.sin(xAngle) + offZ.y * Math.cos(xAngle);
		var offX = NightmareVisionModchartVector.get(offZ.x, xy, xx);
		var yx = offX.x * Math.cos(yAngle) - offX.z * Math.sin(yAngle);
		var yy = offX.x * Math.sin(yAngle) + offX.z * Math.cos(yAngle);
		var offY = NightmareVisionModchartVector.get(yx, offX.y, yy);
		offZ.put();
		offX.put();
		return offY;
	}

	function applyRotate(context:NightmareVisionModchartContext,
		object:NightmareVisionModchartObject, pos:NightmareVisionModchartVector,
		prefix:String, centered:Bool):Void {
		var origin = NightmareVisionModchartVector.get(centered ? context.width * 0.5 : baseX(context, object.data, object.player), context.height * 0.5);
		if (currentFormulaEntry != null && currentFormulaEntry.state != null) {
			prefix = currentFormulaEntry.state.prefix;
			if (currentFormulaEntry.state.origin != null) origin = currentFormulaEntry.state.origin;
		}
		var root = prefix + 'rotateX';
		var diff = pos.subtract(origin);
		diff.z *= context.height;
		var out = rotateVector(diff, get(root, object.player),
			sub(root, prefix + 'rotateY', object.player), sub(root, prefix + 'rotateZ', object.player));
		out.z /= context.height;
		origin.add(out, pos);
		out.put();
	}

	function applyLocalRotate(context:NightmareVisionModchartContext,
		object:NightmareVisionModchartObject, pos:NightmareVisionModchartVector):Void {
		var x = context.width * 0.5;
		switch (object.player) {
			case 0: x += context.width * 0.5 - context.noteWidth * (context.keys / 2) - 100;
			case 1: x -= context.width * 0.5 - context.noteWidth * (context.keys / 2) - 100;
		}
		var prefix = currentFormulaEntry != null && currentFormulaEntry.state != null ? currentFormulaEntry.state.prefix : 'local';
		var root = 'localrotateX';
		var origin = NightmareVisionModchartVector.get(x, context.height * 0.5);
		var diff = pos.subtract(origin);
		diff.z *= context.height;
		var values = NightmareVisionModchartVector.get(get(root, object.player),
			sub(root, prefix + 'rotateY', object.player), sub(root, prefix + 'rotateZ', object.player));
		values.x += sub(root, prefix + 'rotate' + object.data + 'X', object.player);
		values.y += sub(root, prefix + 'rotate' + object.data + 'Y', object.player);
		values.z += sub(root, prefix + 'rotate' + object.data + 'Z', object.player);
		var out = rotateVector(diff, values.x, values.y, values.z);
		out.z /= context.height;
		origin.add(out, pos);
		out.put();
		values.put();
	}

	function applyPerspective(context:NightmareVisionModchartContext,
		pos:NightmareVisionModchartVector):Void {
		var curZ = pos.z;
		if (Math.abs(curZ) < NightmareVisionModchartMath.EPSILON) return;
		var originalX = pos.x - context.width / 2;
		var originalY = pos.y - context.height / 2;
		var clipped = curZ - 1;
		if (clipped > 0) clipped = 0;
		var tangent = NightmareVisionModchartMath.fastSin(Math.PI / 4) / NightmareVisionModchartMath.fastCos(Math.PI / 4);
		var x = originalX / tangent;
		var y = originalY / tangent;
		var z = -clipped;
		pos.x = x / z + context.width / 2;
		pos.y = y / z + context.height / 2;
		pos.z = z;
	}

	function applyConfusion(object:NightmareVisionModchartObject):Void {
		var player = object.player;
		if (object.kind == NightmareVisionModchartObject.NOTE && object.isSustain) return;
		if (object.kind != NightmareVisionModchartObject.NOTE
			&& object.kind != NightmareVisionModchartObject.RECEPTOR) return;
		var family = 'confusion';
		var suffix = object.kind == NightmareVisionModchartObject.NOTE ? 'note' : 'receptor';
		object.angle = get(family, player) + sub(family, 'confusion' + object.data, player)
			+ sub(family, suffix + 'Angle', player)
			+ sub(family, suffix + object.data + 'Angle', player);
	}

	function applyAlpha(context:NightmareVisionModchartContext,
		object:NightmareVisionModchartObject):Void {
		var family = 'stealth';
		var player = object.player;
		if (object.kind == NightmareVisionModchartObject.NOTE) {
			player = object.player; // donor Note.lane selects the owning playfield.
			var speed = context.songSpeed * object.multSpeed;
			var yPos = visualPosition(context.songPosition, object.strumTime, speed, context.legacyCoordinates) + 50;
			object.rgbFlash = 0;
			var alphaMultiplier = (1 - sub(family, 'alpha', player))
				* (1 - sub(family, 'alpha' + object.data, player))
				* (1 - sub(family, 'noteAlpha', player))
				* (1 - sub(family, 'noteAlpha' + object.data, player));
			var visible = visibility(context, yPos, player);
			// `dontUseStealthGlow` is read in source but is not in getSubmods();
			// parent Modifier.getSubmodValue therefore returns zero for it.
			if (sub(family, 'dontUseStealthGlow', player) == 0) {
				object.alphaMod = getAlpha(visible);
				object.rgbFlash = getGlow(visible);
			} else object.alphaMod = visible;
			object.alphaMod *= alphaMultiplier;
		} else if (object.kind == NightmareVisionModchartObject.RECEPTOR) {
			var alpha = (1 - sub(family, 'alpha', player)) * (1 - sub(family, 'alpha' + object.data, player));
			if (sub(family, 'dark', player) != 0 || sub(family, 'dark' + object.data, player) != 0)
				alpha *= (1 - sub(family, 'dark', player)) * (1 - sub(family, 'dark' + object.data, player));
			object.rgbAlpha = alpha;
		} else if (object.kind == NightmareVisionModchartObject.NOTE_SPLASH
			|| object.kind == NightmareVisionModchartObject.SUSTAIN_SPLASH) {
			var alpha = (1 - sub(family, 'alpha', player)) * (1 - sub(family, 'alpha' + object.data, player));
			if (object.kind == NightmareVisionModchartObject.NOTE_SPLASH)
				alpha *= (1 - sub(family, 'noteSplashAlpha', player))
					* (1 - sub(family, 'noteSplash' + object.data + 'Alpha', player));
			else alpha *= (1 - sub(family, 'sustainSplashAlpha', player))
				* (1 - sub(family, 'sustainSplash' + object.data + 'Alpha', player));
			object.rgbAlpha = alpha;
		}
	}

	function visibility(context:NightmareVisionModchartContext, yPos:Float, player:Int):Float {
		var family = 'stealth';
		if (yPos < 0 && sub(family, 'stealthPastReceptors', player) == 0) return 1;
		var alpha = 0.0;
		var hiddenEnd = boundaryValue(context, 'hiddenEnd', player);
		var hiddenStart = boundaryValue(context, 'hiddenStart', player);
		var suddenEnd = boundaryValue(context, 'suddenEnd', player);
		var suddenStart = boundaryValue(context, 'suddenStart', player);
		var hidden = sub(family, 'hidden', player);
		if (hidden != 0) alpha += hidden * clamp(scale(yPos, hiddenStart, hiddenEnd, 0, -1), -1, 0);
		var sudden = sub(family, 'sudden', player);
		if (sudden != 0) alpha += sudden * clamp(scale(yPos, suddenStart, suddenEnd, 0, -1), -1, 0);
		if (get(family, player) != 0) alpha -= get(family, player);
		if (sub(family, 'blink', player) != 0) {
			var blink = Std.int((NightmareVisionModchartMath.fastSin(context.songPosition / 1000 * 10) + 0.3333 / 2) / 0.3333) * 0.3333;
			alpha += scale(blink, 0, 1, -1, 0);
		}
		var vanish = sub(family, 'randomVanish', player);
		if (vanish != 0)
			alpha += scale(Math.abs(yPos), 240, 480, -1, 0) * vanish;
		return clamp(alpha + 1, 0, 1);
	}

	static function getGlow(visible:Float):Float return clamp(scale(visible, 1, 0.5, 0, 1.3), 0, 1);
	static function getAlpha(visible:Float):Float return clamp(scale(visible, 0.5, 0, 1, 0), 0, 1);

	function applyReceptorScrollObject(context:NightmareVisionModchartContext,
		object:NightmareVisionModchartObject):Void {
		if (object.kind != NightmareVisionModchartObject.NOTE || get('receptorScroll', object.player) == 0) return;
		var moveSpeed = currentFormulaEntry != null && currentFormulaEntry.state != null ? currentFormulaEntry.state.moveSpeed : context.crotchet * 3;
		var diff = object.strumTime - context.songPosition;
		var songPosition = context.songPosition;
		var songPositionWrap = songPosition / moveSpeed;
		var notePositionWrap = -(-diff - songPosition) / moveSpeed;
		if (Math.floor(songPositionWrap) != Math.floor(notePositionWrap)) object.alphaMod *= 0.5;
		if (object.wasGoodHit) object.garbage = true;
	}

	function applyScale(object:NightmareVisionModchartObject):Void {
		if (object.kind != NightmareVisionModchartObject.NOTE
			&& object.kind != NightmareVisionModchartObject.RECEPTOR
			&& object.kind != NightmareVisionModchartObject.NOTE_SPLASH
			&& object.kind != NightmareVisionModchartObject.SUSTAIN_SPLASH) return;
		var family = 'mini';
		var player = object.player;
		var data = object.data;
		var prefix = object.kind;
		var presetX = sub(family, prefix + 'ScaleX', player);
		var presetY = sub(family, prefix + 'ScaleY', player);
		var preset = presetX > 0 || presetY > 0;
		var scaleX = preset && presetX != 0 ? presetX : object.baseScaleX;
		var scaleY = preset && presetY != 0 ? presetY : object.baseScaleY;
		var sustainBody = object.kind == NightmareVisionModchartObject.NOTE && object.isSustain && !object.isSustainEnd;
		var squish = lerp(1, 2, sub(family, 'squish', player) + sub(family, 'squish' + data, player));
		var stretch = lerp(1, 0.5, sub(family, 'stretch', player) + sub(family, 'stretch' + data, player));
		if (sustainBody) scaleY = object.baseScaleY;
		else {
			scaleY *= 1 - get(family, player);
			scaleY *= 1 - sub(family, 'miniY', player);
			scaleY *= 1 - sub(family, 'mini' + data + 'Y', player);
			scaleY *= 1 - sub(family, prefix + data + 'ScaleY', player);
			scaleY /= squish;
			scaleY /= stretch;
		}
		scaleX *= 1 - get(family, player);
		scaleX *= 1 - sub(family, 'miniX', player);
		scaleX *= 1 - sub(family, 'mini' + data + 'X', player);
		scaleX *= 1 - sub(family, prefix + data + 'ScaleX', player);
		scaleX *= squish;
		scaleX *= stretch;
		object.scaleX = scaleX;
		object.scaleY = scaleY;
	}

	function applyXMod(object:NightmareVisionModchartObject):Void {
		if (object.kind != NightmareVisionModchartObject.NOTE) return;
		object.multSpeed = get('xmod', object.player) * sub('xmod', 'xmod' + object.data, object.player);
	}

	static function applyPerspectiveScale(object:NightmareVisionModchartObject,
		position:NightmareVisionModchartVector):Void {
		if (object.kind != NightmareVisionModchartObject.NOTE
			&& object.kind != NightmareVisionModchartObject.RECEPTOR
			&& object.kind != NightmareVisionModchartObject.NOTE_SPLASH
			&& object.kind != NightmareVisionModchartObject.SUSTAIN_SPLASH) return;
		if (Math.abs(position.z) > NightmareVisionModchartMath.EPSILON) {
			object.scaleX *= 1 / position.z;
			object.scaleY *= 1 / position.z;
		}
	}
}
