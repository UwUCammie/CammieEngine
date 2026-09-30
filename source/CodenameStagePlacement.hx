package;

typedef CodenameStagePoint = {
	var x:Null<Float>;
	var y:Null<Float>;
}

typedef CodenameStageSlot = {
	var name:String;
	var x:Float;
	var y:Float;
	var spacingX:Float;
	var spacingY:Float;
	var scrollX:Float;
	var scrollY:Float;
	var scaleX:Float;
	var scaleY:Float;
	var alpha:Float;
	var angle:Float;
	var skewX:Float;
	var skewY:Float;
	var zoomFactor:Float;
	var flip:Bool;
	var cameraX:Float;
	var cameraY:Float;
}

/** One static stage member in donor XML element order. Prop keys are the
 * element ordinal; anchor keys are canonical role or exact named slot IDs. */
typedef CodenameStageOrderEntry = {
	var kind:String;
	var ordinal:Int;
	var key:String;
}

typedef CodenameStagePlacementData = {
	var slots:Map<String, CodenameStageSlot>;
	var startCamera:CodenameStagePoint;
	/** Null for older sidecars that have no display-order information. */
	var order:Null<Array<CodenameStageOrderEntry>>;
	/** Actor-pose writes found only in callbacks that run after stage startup.
	 * These are reported for runtime parity, but do not invalidate XML startup slots. */
	var runtimeMutationHooks:Array<String>;
	/** XML extensions, conditional nodes and property nodes can change placement
	 * outside this static model. Callers must diagnose these before using it as
	 * an exact representation of the donor stage. */
	var unsupported:Array<String>;
}

typedef CodenameStageScriptPlacementEffects = {
	var initial:Bool;
	var runtimeMutationHooks:Array<String>;
}

typedef CodenameStageOccurrence = {
	var slotKey:String;
	var x:Float;
	var y:Float;
	var scrollX:Float;
	var scrollY:Float;
	var scaleX:Float;
	var scaleY:Float;
	var alpha:Float;
	var angle:Float;
	var skewX:Float;
	var skewY:Float;
	var zoomFactor:Float;
	var flip:Bool;
	var isPlayer:Bool;
	var cameraX:Float;
	var cameraY:Float;
	var supported:Bool;
}

/** Pure model of Stage.addCharPos, Stage.applyCharStuff and PlayState's
 * strumline character constructor in CodenameEngine v1.0.1. */
class CodenameStagePlacement {
	static final numericFields = ['x', 'y', 'spacingX', 'spacingY', 'scrollX', 'scrollY',
		'scaleX', 'scaleY', 'alpha', 'angle', 'skewX', 'skewY', 'zoomFactor', 'cameraX', 'cameraY'];
	static final actorPlacementWrite = ~/(?:boyfriend|bf|dad|gf|girlfriend|opponent)\s*\.\s*(?:x|y|scale|scalex|scaley|scrollfactor|angle|skewx|skewy|flipx|flipy|offset|cameraoffset|camx|camy)\s*(?:=(?!=)|\+=|-=|\*=|\/=|\+\+|--)/i;
	static final actorPlacementSetter = ~/(?:boyfriend|bf|dad|gf|girlfriend|opponent)\s*\.\s*(?:setposition|setpositionfromobject|setpositionfromcamera|setpositionandangle)\s*\(/i;
	static final actorPlacementTween = ~/(?:boyfriend|bf|dad|gf|girlfriend|opponent)\s*,\s*\{[^}]*\b(?:x|y|scale|scrollfactor|angle|skewx|skewy|flipx|flipy|offset|cameraoffset)\s*:/i;
	static final stagePlacementSetter = ~/\b(?:stage|curstage)\s*\.\s*(?:addcharpos|setoffsets|setscrollfactor|setcharacterpos|setcharpos|placecharacter|setactorposition)\s*\(/i;
	static final anyPlacementWrite = ~/\b([a-z_$][a-z0-9_$]*)\s*\??\.\s*(?:x|y|scale|scalex|scaley|scrollfactor|angle|skewx|skewy|flipx|flipy|offset|cameraoffset|camx|camy)\s*(?:=(?!=)|\+=|-=|\*=|\/=|\+\+|--)/i;
	static final anyIndexedPlacementWrite = ~/\b([a-z_$][a-z0-9_$]*)\s*\[[^\]]+\]\s*\??\.\s*(?:x|y|scale|scalex|scaley|scrollfactor|angle|skewx|skewy|flipx|flipy|offset|cameraoffset|camx|camy)\s*(?:=(?!=)|\+=|-=|\*=|\/=|\+\+|--)/i;
	static final indexedActorDirectPlacementWrite = ~/\bstrumlines\s*\.\s*members\s*\[[^\]]+\]\s*\.\s*characters\s*\[[^\]]+\]\s*\??\.\s*(?:x|y|scale|scalex|scaley|scrollfactor|angle|skewx|skewy|flipx|flipy|offset|cameraoffset|camx|camy)\s*(?:=(?!=)|\+=|-=|\*=|\/=|\+\+|--)/i;
	static final indexedActorDirectGeometryWrite = ~/\bstrumlines\s*\.\s*members\s*\[[^\]]+\]\s*\.\s*characters\s*\[[^\]]+\]\s*\??\.\s*(?:x|y|scale|scalex|scaley|scrollfactor|angle|skewx|skewy|flipx|flipy|offset|cameraoffset|camx|camy)\s*(?:=(?!=)|\+=|-=|\*=|\/=|\+\+|--)/i;
	static final indexedActorAliasPlacementWrite = ~/\b([a-z_$][a-z0-9_$]*)\s*\??\.\s*(?:x|y|scale|scalex|scaley|scrollfactor|angle|skewx|skewy|flipx|flipy|offset|cameraoffset|camx|camy)\s*(?:=(?!=)|\+=|-=|\*=|\/=|\+\+|--)/ig;
	static final anyPlacementSetter = ~/\b([a-z_$][a-z0-9_$]*)\s*\.\s*(?:setposition|setpositionfromobject|setpositionfromcamera|setpositionandangle)\s*\(/i;
	static final anyPlacementTween = ~/\b([a-z_$][a-z0-9_$]*)\s*,\s*\{[^}]*\b(?:x|y|scale|scrollfactor|angle|skewx|skewy|flipx|flipy|offset|cameraoffset)\s*:/i;
	static final actorAliasDeclaration = ~/\b(?:var|final)\s+([a-z_$][a-z0-9_$]*)(?:\s*:\s*[^=;\n]+)?\s*=\s*([^;\n]+)[;\n]?/ig;
	static final indexedActorAliasAssignment = ~/\b([a-z_$][a-z0-9_$]*)\s*=\s*(strumlines\s*\.\s*members\s*\[[^\]]+\]\s*\.\s*characters\s*\[[^\]]+\])/ig;
	static final actorArrayLoop = ~/\bfor\s*\(\s*([a-z_$][a-z0-9_$]*)\s+in\s*\[([^\]]*)\]\s*\)/ig;
	static final primaryActorReference = ~/^\s*(?:boyfriend|bf|dad|gf|girlfriend|opponent)\s*$/i;
	static final indexedActorReference = ~/\bstrumlines\s*\.\s*members\s*\[[^\]]+\]\s*\.\s*characters\s*\[[^\]]+\]/i;
	static final actorGetterReference = ~/\b(?:getcharacter|getactor|getchar|findcharacter|findactor)\s*\(/i;
	static final delayedPlacementHook = ~/\bfunction\s+(songEvents|stepHit)\s*\(/;

	static function dataObject(value:Dynamic):Bool {
		return value != null && Type.typeof(value) == TObject;
	}

	static function dataNumber(value:Dynamic):Float {
		if (!(Std.isOfType(value, Int) || Std.isOfType(value, Float)) || !Math.isFinite(value))
			throw 'Invalid Codename stage placement number';
		return value;
	}

	/** Destination metadata stores map identities as data, never filesystem
	 * paths. Preserve all slots and unresolved dependencies for runtime actors. */
	public static function toData(model:CodenameStagePlacementData):Dynamic {
		if (model == null) throw 'Missing Codename stage placement';
		var slots:Dynamic = {};
		for (key in model.slots.keys()) {
			var slot = model.slots.get(key);
			var entry:Dynamic = {name:key, flip:slot.flip};
			for (field in numericFields) Reflect.setField(entry, field, Reflect.field(slot, field));
			Reflect.setField(slots, key, entry);
		}
		var result:Dynamic = {slots:slots,
			startCamera:{x:model.startCamera.x, y:model.startCamera.y},
			runtimeMutationHooks:model.runtimeMutationHooks == null ? [] : model.runtimeMutationHooks.copy(),
			unsupported:model.unsupported.copy()};
		if (model.order != null)
			Reflect.setField(result, 'order', [for (entry in model.order)
				{kind:entry.kind, ordinal:entry.ordinal, key:entry.key}]);
		// Validate authored models as well as deserialized input.
		fromData(result);
		return result;
	}

	public static function fromData(value:Dynamic):CodenameStagePlacementData {
		if (!dataObject(value) || !dataObject(Reflect.field(value, 'slots'))
			|| !dataObject(Reflect.field(value, 'startCamera'))
			|| !Std.isOfType(Reflect.field(value, 'unsupported'), Array))
			throw 'Invalid Codename stage placement metadata';
		var start:Dynamic = Reflect.field(value, 'startCamera');
		if (!Reflect.hasField(start, 'x') || !Reflect.hasField(start, 'y'))
			throw 'Missing Codename stage camera axis';
		var result:CodenameStagePlacementData = {slots:new Map(),
			startCamera:{x:start.x == null ? null : dataNumber(start.x),
				y:start.y == null ? null : dataNumber(start.y)}, order:null,
			runtimeMutationHooks:[], unsupported:[]};
		var slots:Dynamic = Reflect.field(value, 'slots');
		for (key in Reflect.fields(slots)) {
			var entry:Dynamic = Reflect.field(slots, key);
			if (!dataObject(entry) || Reflect.field(entry, 'name') != key
				|| !Std.isOfType(Reflect.field(entry, 'flip'), Bool))
				throw 'Invalid Codename stage placement slot';
			var copy:Dynamic = {name:key, flip:Reflect.field(entry, 'flip')};
			for (field in numericFields)
				Reflect.setField(copy, field, dataNumber(Reflect.field(entry, field)));
			result.slots.set(key, cast copy);
		}
		for (role in ['dad', 'boyfriend', 'girlfriend'])
			if (!result.slots.exists(role)) throw 'Missing Codename default stage slot: ' + role;
		for (reason in (cast Reflect.field(value, 'unsupported'):Array<Dynamic>)) {
			if (!Std.isOfType(reason, String) || StringTools.trim(reason) == '')
				throw 'Invalid Codename stage dependency diagnostic';
			addUnsupported(result.unsupported, reason);
		}
		if (Reflect.hasField(value, 'runtimeMutationHooks')) {
			var rawHooks:Dynamic = Reflect.field(value, 'runtimeMutationHooks');
			if (!Std.isOfType(rawHooks, Array)) throw 'Invalid Codename stage runtime mutation hooks';
			for (hook in (cast rawHooks:Array<Dynamic>)) {
				if ((hook != 'songEvents' && hook != 'stepHit') || result.runtimeMutationHooks.indexOf(hook) >= 0)
					throw 'Invalid Codename stage runtime mutation hook';
				result.runtimeMutationHooks.push(hook);
			}
		}
		var rawOrder:Dynamic = Reflect.field(value, 'order');
		if (rawOrder != null) {
			if (!Std.isOfType(rawOrder, Array)) throw 'Invalid Codename stage order';
			result.order = [];
			var lastOrdinal = -1;
			var roleAnchors:Map<String, Bool> = new Map();
			for (item in (cast rawOrder:Array<Dynamic>)) {
				if (!dataObject(item)) throw 'Invalid Codename stage order entry';
				var kind:Dynamic = Reflect.field(item, 'kind');
				var ordinal:Dynamic = Reflect.field(item, 'ordinal');
				var key:Dynamic = Reflect.field(item, 'key');
				if ((kind != 'prop' && kind != 'anchor')
					|| !Std.isOfType(ordinal, Int) || ordinal < 0 || ordinal <= lastOrdinal
					|| !Std.isOfType(key, String))
					throw 'Invalid Codename stage order entry';
				if (kind == 'prop' && key != Std.string(ordinal))
					throw 'Invalid Codename stage prop ordinal';
				if (kind == 'anchor') {
					if (!result.slots.exists(key)) throw 'Unknown Codename stage anchor';
					if (key == 'girlfriend' || key == 'dad' || key == 'boyfriend')
						roleAnchors.set(key, true);
				}
				result.order.push({kind:kind, ordinal:ordinal, key:key});
				lastOrdinal = ordinal;
			}
			for (role in ['girlfriend', 'dad', 'boyfriend'])
				if (!roleAnchors.exists(role)) throw 'Missing Codename stage order role anchor: ' + role;
		}
		return result;
	}

	static function number(node:Xml, name:String, fallback:Float):Float {
		if (node == null || !node.exists(name)) return fallback;
		var parsed = Std.parseFloat(node.get(name));
		// Stage.addCharPos uses Std.parseFloat(...).getDefault(previousValue),
		// so malformed/NaN values retain the initialized property.
		if (Math.isNaN(parsed)) return fallback;
		if (!Math.isFinite(parsed)) throw 'Invalid Codename stage placement ' + name;
		return parsed;
	}

	static function optionalNumber(node:Xml, name:String):Null<Float> {
		if (!node.exists(name)) return null;
		var parsed = Std.parseFloat(node.get(name));
		if (Math.isNaN(parsed)) return null;
		if (!Math.isFinite(parsed)) throw 'Invalid Codename stage start camera ' + name;
		return parsed;
	}

	static function defaults(name:String):CodenameStageSlot {
		var x:Float = 0;
		var y:Float = 0;
		var scroll:Float = 1;
		var flip = false;
		switch (name) {
			case 'boyfriend': x = 770; y = 100; flip = true;
			case 'girlfriend': x = 400; y = 130; scroll = 0.95;
			case 'dad': x = 100; y = 100;
		}
		return {name:name, x:x, y:y, spacingX:20, spacingY:0,
			scrollX:scroll, scrollY:scroll, scaleX:1, scaleY:1,
			alpha:1, angle:0, skewX:0, skewY:0, zoomFactor:1,
			flip:flip, cameraX:0, cameraY:0};
	}

	/** Share canonical anchor keys with the stage XML converter. */
	public static function slotKey(node:Xml):Null<String> {
		return switch (node.nodeName) {
			case 'boyfriend' | 'bf' | 'player': 'boyfriend';
			case 'girlfriend' | 'gf': 'girlfriend';
			case 'dad' | 'opponent': 'dad';
			case 'character' | 'char': node.exists('name') ? node.get('name') : null;
			default: null;
		};
	}

	static function addUnsupported(result:Array<String>, reason:String):Void {
		if (result.indexOf(reason) < 0) result.push(reason);
	}

	/**
		Check stage HScript for statically visible actor-geometry writes. Opacity-only
		changes do not invalidate the static placement model. Harmless
		stage hooks (HUD props, camera zoom, camera effects) do not invalidate the
		XML placement model used for actors created on extra strumlines. Unknown
		computed aliases remain outside this bounded lexical check and must be
		reported by the normal script compatibility diagnostics.
	*/
	public static function scriptMayChangeActorPlacement(source:String):Bool {
		var effects = scriptPlacementEffects(source);
		return effects.initial || effects.runtimeMutationHooks.length > 0;
	}

	/** XML remains a safe baseline for additional occurrences when initial
	 * geometry writes target named primary actors. Geometry writes through
	 * unresolved aliases stay gated; opacity writes do not affect slot geometry. */
	public static function scriptWritesConfinedToPrimaryActors(source:String):Bool {
		if (source == null || source == '') return false;
		var code = stageScriptCodeOnly(source);
		var aliases = declaredPrimaryActorAliases(code);
		var hasNamedActorWrite = actorPlacementWrite.match(code)
			|| actorPlacementSetter.match(code) || actorPlacementTween.match(code)
			|| hasAliasPlacementWrite(code, aliases) || hasIndexedActorPlacementWrite(code);
		return hasNamedActorWrite && !stagePlacementSetter.match(code)
			&& !hasUnclassifiedPlacementAlias(code);
	}

	/** Unknown pose aliases get one bounded diagnostic code; donor identifiers
	 * and source expressions never enter destination metadata. */
	public static function hasUnclassifiedPlacementAlias(source:String):Bool {
		return source != null && source != '' && hasUnclassifiedPlacementAliasInCode(stageScriptCodeOnly(source));
	}

	static function hasUnclassifiedPlacementAliasInCode(code:String):Bool {
		var primaryAliases = declaredPrimaryActorAliases(code);
		var derivedAliases = declaredUnclassifiedActorAliases(code);
		var indexedAliases = declaredIndexedActorAliases(code);
		for (alias in indexedAliases.keys()) derivedAliases.set(alias, true);
		return hasUnknownTarget(anyPlacementWrite, code, primaryAliases, derivedAliases)
			|| hasUnknownTarget(anyIndexedPlacementWrite, code, primaryAliases, derivedAliases)
			|| hasUnknownTarget(anyPlacementSetter, code, primaryAliases, derivedAliases)
			|| hasUnknownTarget(anyPlacementTween, code, primaryAliases, derivedAliases)
			|| indexedActorDirectGeometryWrite.match(code);
	}

	/** Identifies aliases assigned from one indexed Codename line actor. A
	 * foreach alias is trusted only when every item in its literal source array
	 * is one of those indexed actor aliases. */
	static function declaredIndexedActorAliases(code:String):Map<String, Bool> {
		var result:Map<String, Bool> = new Map();
		var searchFrom = 0;
		while (searchFrom < code.length && indexedActorAliasAssignment.matchSub(code, searchFrom)) {
			var match = indexedActorAliasAssignment.matchedPos();
			result.set(indexedActorAliasAssignment.matched(1).toLowerCase(), true);
			searchFrom = match.pos + match.len;
		}
		searchFrom = 0;
		while (searchFrom < code.length && actorArrayLoop.matchSub(code, searchFrom)) {
			var match = actorArrayLoop.matchedPos();
			var values = StringTools.trim(actorArrayLoop.matched(2)).split(',');
			var knownActors = values.length > 0;
			for (value in values)
				if (!result.exists(StringTools.trim(value).toLowerCase())) {
					knownActors = false;
					break;
				}
			if (knownActors) result.set(actorArrayLoop.matched(1).toLowerCase(), true);
			searchFrom = match.pos + match.len;
		}
		return result;
	}

	static function hasIndexedActorPlacementWrite(code:String):Bool {
		return indexedActorDirectPlacementWrite.match(code)
			|| hasTargetInMap(indexedActorAliasPlacementWrite, code, declaredIndexedActorAliases(code));
	}

	static function declaredPrimaryActorAliases(code:String):Map<String, Bool> {
		var result:Map<String, Bool> = new Map();
		var searchFrom = 0;
		while (searchFrom < code.length && actorAliasDeclaration.matchSub(code, searchFrom)) {
			var match = actorAliasDeclaration.matchedPos();
			var alias = actorAliasDeclaration.matched(1).toLowerCase();
			var initializer = actorAliasDeclaration.matched(2);
			if (primaryActorReference.match(initializer)) result.set(alias, true);
			searchFrom = match.pos + match.len;
		}
		return result;
	}

	/** A variable initialized from a character collection/getter is known to
	 * be actor-derived, but its owner cannot be proven by this bounded lexical
	 * scan. A pose write through it retains the placement diagnostic. */
	static function declaredUnclassifiedActorAliases(code:String):Map<String, Bool> {
		var result:Map<String, Bool> = new Map();
		var searchFrom = 0;
		while (searchFrom < code.length && actorAliasDeclaration.matchSub(code, searchFrom)) {
			var match = actorAliasDeclaration.matchedPos();
			var alias = actorAliasDeclaration.matched(1).toLowerCase();
			var initializer = actorAliasDeclaration.matched(2);
			if (indexedActorReference.match(initializer) || actorGetterReference.match(initializer))
				result.set(alias, true);
			searchFrom = match.pos + match.len;
		}
		return result;
	}

	static function hasAliasPlacementWrite(code:String, aliases:Map<String, Bool>):Bool {
		return aliases != null && (hasTargetInMap(anyPlacementWrite, code, aliases)
			|| hasTargetInMap(anyPlacementSetter, code, aliases)
			|| hasTargetInMap(anyPlacementTween, code, aliases));
	}

	static function hasTargetInMap(expression:EReg, code:String, aliases:Map<String, Bool>):Bool {
		var searchFrom = 0;
		while (searchFrom < code.length && expression.matchSub(code, searchFrom)) {
			var match = expression.matchedPos();
			if (aliases.exists(StringTools.trim(expression.matched(1)).toLowerCase())) return true;
			searchFrom = match.pos + match.len;
		}
		return false;
	}

	static function hasUnknownTarget(expression:EReg, code:String, primaryAliases:Map<String, Bool>,
		derivedAliases:Map<String, Bool>):Bool {
		var searchFrom = 0;
		while (searchFrom < code.length && expression.matchSub(code, searchFrom)) {
			var match = expression.matchedPos();
			var target = StringTools.trim(expression.matched(1)).toLowerCase();
			if (['boyfriend', 'bf', 'dad', 'gf', 'girlfriend', 'opponent'].indexOf(target) < 0
				&& !primaryAliases.exists(target)
				&& (derivedAliases.exists(target) || looksLikeActorAlias(target)))
				return true;
			searchFrom = match.pos + match.len;
		}
		return false;
	}

	/** Ignore ordinary sprite/camera locals. Unknown names count only when
	 * their identifier carries an explicit actor, character, or role token;
	 * getter and strumline-derived aliases are checked separately. */
	static function looksLikeActorAlias(target:String):Bool {
		if (target == 'actor' || target == 'char' || target == 'character') return true;
		if (target.indexOf('actor') >= 0 || target.indexOf('character') >= 0) return true;
		return ~/(?:^|[_$])(?:dad|boyfriend|bf|gf|girlfriend|opponent|player)(?:[0-9]+)?(?:$|[_$])/.match(target);
	}

	public static function onlyStageScriptUnsupported(data:CodenameStagePlacementData):Bool
		return data != null && data.unsupported.length == 1 && data.unsupported[0] == 'stage-script';

	/** Divide ordinary stage initialization from the two known post-start hooks.
	 * Actor geometry writes remain explicit metadata, while visual-only writes such
	 * as alpha do not make the constructor-time XML slots unresolved. */
	public static function scriptPlacementEffects(source:String):CodenameStageScriptPlacementEffects {
		var result:CodenameStageScriptPlacementEffects = {initial:false, runtimeMutationHooks:[]};
		if (source == null || source == '') return result;
		var code = stageScriptCodeOnly(source);
		var primaryAliases = declaredPrimaryActorAliases(code);
		var hooks:Array<{name:String, start:Int, end:Int}> = [];
		var searchFrom = 0;
		while (searchFrom < code.length && delayedPlacementHook.matchSub(code, searchFrom)) {
			var match = delayedPlacementHook.matchedPos();
			var name = delayedPlacementHook.matched(1);
			var openParen = match.pos + match.len - 1;
			var closeParen = matchingDelimiter(code, openParen, '(', ')');
			if (closeParen < 0) {
				searchFrom = match.pos + match.len;
				continue;
			}
			var openBrace = code.indexOf('{', closeParen + 1);
			var closeBrace = openBrace < 0 ? -1 : matchingDelimiter(code, openBrace, '{', '}');
			if (closeBrace < 0) {
				searchFrom = match.pos + match.len;
				continue;
			}
			var body = code.substr(openBrace + 1, closeBrace - openBrace - 1);
			if (hasActorPlacementWrite(body, primaryAliases)) {
				if (result.runtimeMutationHooks.indexOf(name) < 0)
					result.runtimeMutationHooks.push(name);
				hooks.push({name:name, start:match.pos, end:closeBrace + 1});
			}
			searchFrom = closeBrace + 1;
		}
		var initialCode = new StringBuf();
		var cursor = 0;
		for (hook in hooks) {
			initialCode.add(code.substr(cursor, hook.start - cursor));
			cursor = hook.end;
		}
		initialCode.add(code.substr(cursor));
		result.initial = hasActorPlacementWrite(initialCode.toString(), primaryAliases);
		return result;
	}

	/** Apply script findings to the parsed static model. */
	public static function applyScriptPlacementEffects(model:CodenameStagePlacementData,
		source:String):CodenameStageScriptPlacementEffects {
		if (model == null) throw 'Missing Codename stage placement';
		var effects = scriptPlacementEffects(source);
		if (effects.initial) addUnsupported(model.unsupported, 'stage-script');
		if (hasUnclassifiedPlacementAlias(source))
			addUnsupported(model.unsupported, 'stage-script-unclassified-placement-alias');
		model.runtimeMutationHooks = effects.runtimeMutationHooks.copy();
		return effects;
	}

	/** Reconcile the legacy broad `stage-script` marker against the exact
	 * selected-owner stage source. Older camera sidecars marked every script as
	 * a placement dependency, including scripts that only build props or alter
	 * cameras. Keep all other unresolved XML/runtime dependencies intact. */
	public static function resolveScriptPlacement(model:CodenameStagePlacementData,
		source:String):CodenameStageScriptPlacementEffects {
		if (model == null || source == null) throw 'Missing Codename stage source';
		if (hasUnclassifiedPlacementAlias(source))
			addUnsupported(model.unsupported, 'stage-script-unclassified-placement-alias');
		else
			model.unsupported.remove('stage-script');
		return applyScriptPlacementEffects(model, source);
	}

	static function hasActorPlacementWrite(code:String, ?primaryAliases:Map<String, Bool>):Bool {
		return actorPlacementWrite.match(code) || actorPlacementSetter.match(code)
			|| actorPlacementTween.match(code) || stagePlacementSetter.match(code)
			|| hasAliasPlacementWrite(code, primaryAliases) || hasIndexedActorPlacementWrite(code);
	}

	static function matchingDelimiter(code:String, start:Int, open:String, close:String):Int {
		if (start < 0 || start >= code.length || code.charAt(start) != open) return -1;
		var depth = 0;
		for (index in start...code.length) {
			var current = code.charAt(index);
			if (current == open) depth++;
			else if (current == close) {
				depth--;
				if (depth == 0) return index;
			}
		}
		return -1;
	}

	/** Remove comments and quoted strings before matching executable API names. */
	static function stageScriptCodeOnly(source:String):String {
		var out = new StringBuf();
		var index = 0;
		var lineComment = false;
		var blockComment = false;
		var quote = '';
		while (index < source.length) {
			var current = source.charAt(index);
			var next = index + 1 < source.length ? source.charAt(index + 1) : '';
			if (lineComment) {
				if (current == '\n') {
					lineComment = false;
					out.add('\n');
				} else out.add(' ');
				index++;
			} else if (blockComment) {
				if (current == '*' && next == '/') {
					out.add('  ');
					index += 2;
					blockComment = false;
				} else {
					out.add(current == '\n' ? '\n' : ' ');
					index++;
				}
			} else if (quote != '') {
				if (current == '\\' && index + 1 < source.length) {
					out.add('  ');
					index += 2;
				} else {
					if (current == quote) quote = '';
					out.add(current == '\n' ? '\n' : ' ');
					index++;
				}
			} else if (current == '/' && next == '/') {
				out.add('  ');
				index += 2;
				lineComment = true;
			} else if (current == '/' && next == '*') {
				out.add('  ');
				index += 2;
				blockComment = true;
			} else if (current == '"' || current == "'") {
				quote = current;
				out.add(' ');
				index++;
			} else {
				out.add(current);
				index++;
			}
		}
		return out.toString();
	}

	static function parseSlot(node:Xml, key:String):CodenameStageSlot {
		// Named <character>/<char> calls addCharPos without nonXMLInfo, even
		// when its name happens to equal a built-in role key.
		var roleNode = node.nodeName != 'character' && node.nodeName != 'char';
		var slot = defaults(roleNode ? key : '');
		slot.name = key;
		slot.x = number(node, 'x', slot.x);
		slot.y = number(node, 'y', slot.y);
		slot.spacingX = number(node, 'spacingx', slot.spacingX);
		slot.spacingY = number(node, 'spacingy', slot.spacingY);
		slot.cameraX = number(node, 'camxoffset', slot.cameraX);
		slot.cameraY = number(node, 'camyoffset', slot.cameraY);
		slot.skewX = number(node, 'skewx', slot.skewX);
		slot.skewY = number(node, 'skewy', slot.skewY);
		slot.alpha = number(node, 'alpha', slot.alpha);
		slot.angle = number(node, 'angle', slot.angle);
		slot.zoomFactor = number(node, 'zoomfactor', slot.zoomFactor);
		if (node.exists('flip') || node.exists('flipX'))
			slot.flip = node.get('flip') == 'true' || node.get('flipX') == 'true';
		if (node.exists('scale')) {
			slot.scaleX = number(node, 'scale', slot.scaleX);
			slot.scaleY = slot.scaleX;
		}
		slot.scaleX = number(node, 'scalex', slot.scaleX);
		slot.scaleY = number(node, 'scaley', slot.scaleY);
		if (node.exists('scroll')) {
			slot.scrollX = number(node, 'scroll', slot.scrollX);
			slot.scrollY = slot.scrollX;
		}
		slot.scrollX = number(node, 'scrollx', slot.scrollX);
		slot.scrollY = number(node, 'scrolly', slot.scrollY);
		return slot;
	}

	public static function parse(xmlText:String, hasStageScript:Bool = false):CodenameStagePlacementData {
		if (xmlText == null || StringTools.trim(xmlText) == '') throw 'Missing Codename stage XML';
		var root = Xml.parse(xmlText).firstElement();
		if (root == null || root.nodeName != 'stage') throw 'Invalid Codename stage XML root';
		var result:CodenameStagePlacementData = {
			slots:new Map<String, CodenameStageSlot>(),
			startCamera:{x:optionalNumber(root, 'startCamPosX'), y:optionalNumber(root, 'startCamPosY')},
			order:[],
			runtimeMutationHooks:[],
			unsupported:[]
		};
		if (hasStageScript) addUnsupported(result.unsupported, 'stage-script');
		if (root.exists('extends') || root.exists('inherit'))
			addUnsupported(result.unsupported, 'stage-inheritance');
		var ordinal = 0;
		for (node in root.elements()) {
			var nodeOrdinal = ordinal++;
			if (node.nodeName == 'use-extension' || node.nodeName == 'extension' || node.nodeName == 'ext')
				addUnsupported(result.unsupported, 'stage-extension');
			if (node.nodeName == 'high-memory' || node.nodeName == 'low-memory')
				addUnsupported(result.unsupported, 'memory-conditional');
			var key = slotKey(node);
			if (key == null) {
				if (['sprite', 'spr', 'sparrow', 'box', 'solid'].indexOf(node.nodeName) >= 0) {
					var imageProp = ['sprite', 'spr', 'sparrow'].indexOf(node.nodeName) >= 0;
					var validProp = imageProp ? (node.exists('sprite') && node.exists('name'))
						: (node.exists('name') && node.exists('width') && node.exists('height'));
					if (!validProp)
						addUnsupported(result.unsupported, 'stage-order-skipped-prop');
					else {
						result.order.push({kind:'prop', ordinal:nodeOrdinal, key:Std.string(nodeOrdinal)});
						if (node.nodeName != 'sprite')
							addUnsupported(result.unsupported, 'stage-order-unconverted-prop');
					}
				} else if (['use-extension', 'extension', 'ext', 'high-memory', 'low-memory'].indexOf(node.nodeName) < 0)
					addUnsupported(result.unsupported, 'stage-order-unknown-node');
				continue;
			}
			result.order.push({kind:'anchor', ordinal:nodeOrdinal, key:key});
			// Keys are map identities, never joined to filesystem paths. An
			// authored character ID may contain nested path segments.
			for (child in node.elements())
				if (child.nodeName == 'property') addUnsupported(result.unsupported, 'slot-property');
			// Upstream characterPoses[name] assignment replaces earlier entries.
			result.slots.set(key, parseSlot(node, key));
		}
		for (name in ['girlfriend', 'dad', 'boyfriend'])
			if (!result.slots.exists(name)) {
				result.slots.set(name, defaults(name));
				result.order.push({kind:'anchor', ordinal:ordinal++, key:name});
			}
		return result;
	}

	/** Choose the named actor slot first, then the authored position (or role
	 * default). `occurrence` is the index inside that strumline's character list. */
	public static function select(data:CodenameStagePlacementData, actorId:String,
		type:Null<Int>, positionName:Null<String>, occurrence:Int,
		?allowStageScriptOnly:Bool = false):CodenameStageOccurrence {
		if (data == null || occurrence < 0) throw 'Invalid Codename stage occurrence';
		var fallback = switch (type) {
			case 0: 'dad';
			case 1: 'boyfriend';
			case 2: 'girlfriend';
			default: '';
		};
		var position = positionName == null ? fallback : positionName;
		var key = actorId != null && data.slots.exists(actorId) ? actorId : position;
		var slot = key == null ? null : data.slots.get(key);
		var hasSlot = slot != null;
		if (slot == null) slot = defaults('');
		return {slotKey:key == null ? '' : key,
			x:slot.x + (hasSlot ? occurrence * slot.spacingX : 0),
			y:slot.y + (hasSlot ? occurrence * slot.spacingY : 0),
			scrollX:slot.scrollX, scrollY:slot.scrollY,
			scaleX:slot.scaleX, scaleY:slot.scaleY,
			alpha:slot.alpha, angle:slot.angle,
			skewX:slot.skewX, skewY:slot.skewY, zoomFactor:slot.zoomFactor,
			flip:slot.flip, isPlayer:hasSlot ? slot.flip : type == 1,
			cameraX:slot.cameraX, cameraY:slot.cameraY,
			supported:data.unsupported.length == 0
				|| (allowStageScriptOnly && onlyStageScriptUnsupported(data))};
	}
}
