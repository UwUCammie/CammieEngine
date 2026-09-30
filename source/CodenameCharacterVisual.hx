package;

using StringTools;

/** Applies the selected owner's character XML to one live actor. The caller
 * dispatches create/XML/postCreate and owns the actor's script and lifetime. */
class CodenameCharacterVisual {
	/** Match FunkinSprite's Codename default before character scripts run. */
	public static function initializeSourceDefaults(actor:Character):Void {
		if (actor != null) actor.applyStageMatrix = true;
	}

	static function attr(node:Xml, name:String, fallback:String):String {
		var value = node.get(name);
		return value == null ? fallback : value;
	}

	static function number(node:Xml, name:String, fallback:Float):Float {
		var value = node.get(name);
		if (value == null) return fallback;
		var parsed = Std.parseFloat(value);
		return Math.isNaN(parsed) ? fallback : parsed;
	}

	static function integer(node:Xml, name:String, fallback:Int):Int {
		var value = node.get(name);
		if (value == null) return fallback;
		var parsed = Std.parseInt(value);
		return parsed == null ? fallback : parsed;
	}

	static function indices(value:String):Array<Int> {
		var result:Array<Int> = [];
		if (value == null) return result;
		for (part in value.split(',')) {
			part = part.trim();
			var separator = part.indexOf('..');
			if (separator < 0) {
				var single = Std.parseInt(part);
				if (single != null) result.push(single);
				continue;
			}
			var first = Std.parseInt(part.substr(0, separator).trim());
			var last = Std.parseInt(part.substr(separator + 2).trim());
			if (first == null || last == null) continue;
			if (first <= last)
				for (i in first...last + 1) result.push(i);
			else
				for (i in last...first + 1) result.push(first + last - i);
		}
		return result;
	}

	public static function build(actor:Character, authoredId:String, xml:Xml, paths:CodenamePaths,
		?nodeApplied:Xml->Void, ?loopPlay:(String, Bool)->Void,
		?buildingAnimations:Array<Dynamic>, ?sourceDefinitionId:String):Dynamic {
		if (actor == null || xml == null || xml.nodeType != Element || xml.nodeName != 'character')
			throw '[codename-character] Invalid live character XML';
		if (!CodenameScriptDiscovery.safeRelativeName(authoredId))
			throw '[codename-character] Invalid authored character ID: ' + authoredId;

		var sprite = attr(xml, 'sprite', sourceDefinitionId == null ? authoredId : sourceDefinitionId);
		if (!CodenameScriptDiscovery.safeRelativeName(sprite))
			throw '[codename-character] Invalid character sprite: ' + sprite;
		var diagnostics:Array<String> = [];
		var extra:Dynamic = {};
		var recognized = ['x', 'y', 'sprite', 'scale', 'antialiasing', 'flipX', 'camx', 'camy',
			'isPlayer', 'icon', 'color', 'gameOverChar', 'holdTime', 'interval', 'applyStageMatrix'];
		for (key in xml.attributes())
			if (!recognized.contains(key)) Reflect.setField(extra, key, xml.get(key));

		// A character's create callback runs before XML. Absent attributes leave
		// its live fields alone, as in the donor's buildCharacter.
		var x = number(xml, 'x', actor.globalOffset.x);
		var y = number(xml, 'y', actor.globalOffset.y);
		var camx = number(xml, 'camx', actor.cameraOffset.x);
		var camy = number(xml, 'camy', actor.cameraOffset.y);
		var playerOffsets = xml.exists('isPlayer') ? xml.get('isPlayer') == 'true' : actor.playerOffsets;
		var flipX = xml.exists('flipX') ? xml.get('flipX') == 'true' : actor.flipX;
		var scale = number(xml, 'scale', actor.scale.x);
		var holdTime = number(xml, 'holdTime', actor.holdTime);
		var interval = xml.exists('interval') ? integer(xml, 'interval', 1) : null;
		var applyStageMatrix = xml.exists('applyStageMatrix')
			? xml.get('applyStageMatrix') == 'true' : actor.applyStageMatrix;
		var icon = xml.get('icon');
		var color = xml.get('color');
		var gameOverChar = xml.get('gameOverChar');
		var dynamicActor:Dynamic = actor;
		actor.xml = new CodenameXmlAccess(xml);
		if (xml.exists('x')) actor.globalOffset.x = x;
		if (xml.exists('y')) actor.globalOffset.y = y;
		if (xml.exists('camx')) actor.cameraOffset.x = camx;
		if (xml.exists('camy')) actor.cameraOffset.y = camy;
		if (xml.exists('isPlayer')) actor.playerOffsets = playerOffsets;
		if (xml.exists('flipX')) actor.flipX = flipX;
		if (xml.exists('holdTime')) actor.holdTime = holdTime;
		if (interval != null) actor.beatInterval = interval;
		if (icon != null) Reflect.setProperty(dynamicActor, 'icon', icon);
		if (color != null) Reflect.setProperty(dynamicActor, 'iconColor', flixel.util.FlxColor.fromString(color));
		if (gameOverChar != null) Reflect.setProperty(dynamicActor, 'gameOverCharacter', gameOverChar);
		if (xml.exists('antialiasing')) actor.antialiasing = xml.get('antialiasing') == 'true';
		if (xml.exists('scale')) actor.scale.set(scale, scale);
		var atlasKey = 'characters/' + sprite;
		var animateAtlas = paths.animateAtlasPath(atlasKey) != null;
		if (animateAtlas)
			actor.loadTextureAtlas(paths.animateAtlasPath(atlasKey));
		else
			actor.frames = paths.getFrames(atlasKey);
		// FlxAnimate refreshes Animate bounds when this setter runs. Applying the
		// authored value after the atlas load matches Codename's XML behavior.
		if (xml.exists('applyStageMatrix')) actor.applyStageMatrix = applyStageMatrix;
		actor.updateHitbox();

		var anims:Array<Dynamic> = buildingAnimations == null ? [] : buildingAnimations;
		for (node in xml.elements()) {
			switch (node.nodeName) {
				case 'anim':
					var name = node.get('name');
					var prefix = node.get('anim');
					var frameRate = number(node, 'fps', 24);
					if (frameRate <= 0) frameRate = 24;
					var loop = attr(node, 'loop', 'false') == 'true';
					var frameIndices = indices(node.get('indices'));
					var offsetX = number(node, 'x', 0);
					var offsetY = number(node, 'y', 0);
					if (name == null || name == '')
						diagnostics.push('Character anim is missing name');
					else if (animateAtlas && frameIndices.length > 0 && prefix != null && prefix != '') {
						var addIndices = Reflect.field(actor.animation, 'addBySymbolIndices');
						if (addIndices == null)
							diagnostics.push('Animate character animation API is unavailable: addBySymbolIndices');
						else
							Reflect.callMethod(actor.animation, addIndices,
								[name, prefix, frameIndices, frameRate, loop]);
					} else if (animateAtlas && prefix != null && prefix != '') {
						var addSymbol = Reflect.field(actor.animation, 'addBySymbol');
						if (addSymbol == null)
							diagnostics.push('Animate character animation API is unavailable: addBySymbol');
						else
							Reflect.callMethod(actor.animation, addSymbol, [name, prefix, frameRate, loop]);
					} else if (animateAtlas)
						diagnostics.push('Animate character anim ' + name + ' is missing its symbol name');
					else if (frameIndices.length > 0 && (prefix == null || prefix == ''))
						actor.animation.add(name, frameIndices, frameRate, loop);
					else if (frameIndices.length > 0)
						actor.animation.addByIndices(name, prefix, frameIndices, '', frameRate, loop);
					else if (prefix == null || prefix == '')
						diagnostics.push('Character anim ' + name + ' is missing anim prefix and indices');
					else
						actor.animation.addByPrefix(name, prefix, frameRate, loop);
					if (name != null && name != '') {
						actor.animOffsets.set(name, [offsetX, offsetY]);
						var rawForced:Null<Bool> = node.exists('forced') ? node.get('forced') == 'true' : null;
						var animType = attr(node, 'type', 'beat').trim().toLowerCase();
						// Donor XMLUtil plays LOOP when it applies this node, before
						// storing animDatas and before onCharacterNodeParsed.
						if (animType == 'loop' && loopPlay != null) {
							var forced = rawForced == null
								? !(name.startsWith('idle') || name.startsWith('danceLeft')
									|| name.startsWith('danceRight')) : rawForced;
							loopPlay(name, forced);
						}
						anims.push({name: name, anim: prefix, indices: frameIndices, fps: frameRate,
							loop: loop, x: offsetX, y: offsetY, type: node.get('type'),
							forced: rawForced});
					}
				case 'use-extension' | 'extension' | 'ext':
					diagnostics.push('Unsupported character XML extension: ' + node.nodeName
						+ (node.get('script') == null ? '' : ' ' + node.get('script')));
				default:
			}
			if (nodeApplied != null) nodeApplied(node);
		}
		return {x: x, y: y, camx: camx, camy: camy, playerOffsets: playerOffsets,
			flipX: flipX, scale: scale, holdTime: holdTime, interval: interval,
			applyStageMatrix: applyStageMatrix,
			icon: icon, color: color, gameOverChar: gameOverChar, sprite: sprite,
			animOffsets: actor.animOffsets, animations: anims, extra: extra,
			diagnostics: diagnostics};
	}
}
