package;

import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;

/**
	Mechanical stage-layout extraction from Kade-family Haxe source releases.

	Kade-era mods build their stages in code (`new FlxSprite(x, y).loadGraphic(...)` in
	PlayState.hx) and ship no stage data with the compiled release.  When the user
	imports a source release instead, these parsers read the authored layout back
	out of that code - coordinates, scales, scroll factors, zooms, layer order,
	animated props, and the per-stage character repositioning - so no per-mod
	translation tables are ever needed.  Deliberately standalone (sys + EReg only)
	so import-fixture tests can compile it directly.
*/
class KadeStageSource {
	/** Locate the source root above a chart folder (a directory with source/
	 * PlayState-style .hx files beside the mod's assets). */
	public static function findSourceRoot(chartRoot:String):Null<String> {
		if (chartRoot == null || chartRoot == '')
			return null;
		var candidate = Path.normalize(chartRoot);
		for (depth in 0...5) {
			if (hasPlayStateSource(candidate))
				return candidate;
			var parent = Path.normalize(Path.directory(candidate));
			if (parent == candidate || parent == '')
				return null;
			candidate = parent;
		}
		return null;
	}

	static function hasPlayStateSource(root:String):Bool {
		var sourceDir = Path.join([root, 'source']);
		if (FileSystem.isDirectory(sourceDir)
			&& playStateFiles(sourceDir).length > 0)
			return true;
		return playStateFiles(root).length > 0;
	}

	static function playStateFiles(directory:String):Array<String> {
		var results:Array<String> = [];
		try {
			var entries = FileSystem.readDirectory(directory);
			// Some Windows/Wine directory providers return null instead of
			// throwing when an optional source folder cannot be enumerated.
			if (entries == null)
				return results;
			for (entry in entries) {
				var lower = entry.toLowerCase();
				if (!StringTools.endsWith(lower, '.hx'))
					continue;
				if (lower == 'playstate.hx' || lower.indexOf('playstate') >= 0)
					results.push(Path.join([directory, entry]));
			}
		} catch (_:Dynamic) {}
		return results;
	}

	/**
		Extract one song's authored stage layout from the source root, or null.
		The returned object is { id, zoom, layers, actors, assets } where layers
		reference assets entries by index and assets carry absolute source paths.
	*/
	public static function extractStage(sourceRoot:String, songKey:String, ?player2:String):Null<Dynamic> {
		var files = playStateFiles(Path.join([sourceRoot, 'source']));
		if (files.length == 0)
			files = playStateFiles(sourceRoot);
		for (file in files) {
			var text = fileContent(file);
			if (text == null || text.indexOf('defaultCamZoom') < 0 || text.indexOf('curStage') < 0)
				continue;
			var layout = extractFromSource(text, songKey, sourceRoot, player2);
			if (layout != null)
				return layout;
		}
		return null;
	}

	static function fileContent(path:String):Null<String> {
		try {
			return File.getContent(path);
		} catch (_:Dynamic) {
			return null;
		}
	}

	/** The PlayState file this extractor reads for one source root, or null. */
	public static function playStateSource(sourceRoot:String):Null<String> {
		var sources = playStateSources(sourceRoot);
		return sources.length == 0 ? null : sources[0];
	}

	/** Every PlayState file carrying stage state, in read order. */
	public static function playStateSources(sourceRoot:String):Array<String> {
		var results:Array<String> = [];
		var files = playStateFiles(Path.join([sourceRoot, 'source']));
		if (files.length == 0)
			files = playStateFiles(sourceRoot);
		for (file in files) {
			var text = fileContent(file);
			if (text != null && text.indexOf('curStage') >= 0)
				results.push(text);
		}
		return results;
	}

	/**
		Extract one code-defined character from the source release's
		Character.hx switch, or null.  Kade-family releases author characters as
		`case '<id>':` blocks (Sparrow atlas + addByPrefix/addByIndices +
		addOffset), so the returned object is
		{ id, sourceFile, atlasKey, atlasLibrary, atlasPng, atlasXml, animations,
		offsets, initialAnim, scale } with animations carrying
		{ name, prefix, fps, loop, indices } (indices null for addByPrefix).
	*/
	public static function extractCharacter(sourceRoot:String, characterId:String):Null<Dynamic> {
		if (sourceRoot == null || characterId == null || StringTools.trim(characterId) == '')
			return null;
		var text = characterSource(sourceRoot);
		if (text == null)
			return null;
		var block = characterCaseBlock(text, StringTools.trim(characterId));
		if (block == null)
			return null;
		var animations:Array<Dynamic> = [];
		var offsets:Array<Dynamic> = [];
		var atlasKey:String = null;
		var atlasLibrary:String = null;
		var initialAnim:String = null;
		var scale:Null<Float> = null;
		for (line in splitStatements(block)) {
			if (atlasKey == null) {
				var sparrow = new EReg("(?:tex|frames)\\s*=\\s*Paths\\.getSparrowAtlas\\(\\s*['\"]([^'\"]+)['\"]\\s*(?:,\\s*['\"]([^'\"]+)['\"])?", "");
				if (sparrow.match(line)) {
					atlasKey = sparrow.matched(1);
					atlasLibrary = sparrow.matched(2);
					continue;
				}
				// Kade's CachedFrames cache passes a slot name first and the
				// atlas key second: fromSparrow('idle','hellclwn/Tricky/Idle').
				var cached = new EReg("CachedFrames[^;]*\\.fromSparrow\\(\\s*['\"][^'\"]*['\"]\\s*,\\s*['\"]([^'\"]+)['\"]", "");
				if (cached.match(line)) {
					atlasKey = cached.matched(1);
					atlasLibrary = null;
					continue;
				}
			}
			var byPrefix = new EReg("(?:animation\\.)?addByPrefix\\(\\s*['\"]([^'\"]+)['\"]\\s*,\\s*['\"]([^'\"]+)['\"]\\s*(?:,\\s*([0-9.]+))?(?:\\s*,\\s*(true|false))?", "");
			if (byPrefix.match(line)) {
				animations.push({
					name: byPrefix.matched(1),
					prefix: byPrefix.matched(2),
					fps: byPrefix.matched(3) == null ? 24 : Std.parseFloat(byPrefix.matched(3)),
					loop: byPrefix.matched(4) == 'true',
					indices: null
				});
				continue;
			}
			var byIndices = new EReg("(?:animation\\.)?addByIndices\\(\\s*['\"]([^'\"]+)['\"]\\s*,\\s*['\"]([^'\"]+)['\"]\\s*,\\s*\\[([^\\]]*)\\]", "");
			if (byIndices.match(line)) {
				var indices:Array<Int> = [];
				var list = byIndices.matched(3);
				var piece = new EReg("[0-9]+", "g");
				var pos = 0;
				while (piece.matchSub(list, pos)) {
					indices.push(Std.parseInt(piece.matched(0)));
					pos = piece.matchedPos().pos + piece.matchedPos().len;
				}
				animations.push({
					name: byIndices.matched(1),
					prefix: byIndices.matched(2),
					fps: 24,
					loop: false,
					indices: indices
				});
				// fps/loop trail the (optional) suggested-frame string; re-read
				// them from the same line so "…,[0..], "", 24, false" wins.
				var tail = new EReg("\\]\\s*(?:,\\s*['\"][^'\"]*['\"])\\s*,\\s*([0-9.]+)\\s*(?:,\\s*(true|false))?", "");
				if (tail.match(line)) {
					animations[animations.length - 1].fps = Std.parseFloat(tail.matched(1));
					animations[animations.length - 1].loop = tail.matched(2) == 'true';
				}
				continue;
			}
			var offset = new EReg("addOffset\\(\\s*['\"]([^'\"]+)['\"]\\s*(?:,\\s*(-?[0-9.]+))?(?:\\s*,\\s*(-?[0-9.]+))?", "");
			if (offset.match(line)) {
				var existing = false;
				for (entry in offsets)
					if (entry.name == offset.matched(1))
						existing = true;
				if (!existing)
					offsets.push({
						name: offset.matched(1),
						x: offset.matched(2) == null ? 0 : Std.parseFloat(offset.matched(2)),
						y: offset.matched(3) == null ? 0 : Std.parseFloat(offset.matched(3))
					});
				continue;
			}
			if (initialAnim == null) {
				var play = new EReg("playAnim\\(\\s*['\"]([^'\"]+)['\"]", "");
				if (play.match(line))
					initialAnim = play.matched(1);
			}
			var scaleMatch = new EReg("^\\s*scale\\.set\\(\\s*(-?[0-9.]+)\\s*,\\s*(-?[0-9.]+)", "");
			if (scaleMatch.match(line))
				scale = Std.parseFloat(scaleMatch.matched(1));
		}
		if (atlasKey == null || animations.length == 0)
			return null;
		var atlasPng = resolveAssetPath(sourceRoot, {key: atlasKey, library: atlasLibrary}, true);
		if (atlasPng == null)
			return null;
		return {
			id: StringTools.trim(characterId),
			sourceFile: characterFile,
			atlasKey: atlasKey,
			atlasLibrary: atlasLibrary,
			atlasPng: atlasPng,
			atlasXml: Path.withoutExtension(atlasPng) + '.xml',
			animations: animations,
			offsets: offsets,
			initialAnim: initialAnim,
			scale: scale
		};
	}

	static var characterFile:String = null;

	static function characterSource(sourceRoot:String):Null<String> {
		var directories = [Path.join([sourceRoot, 'source']), sourceRoot];
		for (directory in directories) {
			var entries:Array<String> = [];
			try {
				if (!FileSystem.isDirectory(directory))
					continue;
				entries = FileSystem.readDirectory(directory);
				if (entries == null)
					continue;
			} catch (_:Dynamic) {
				continue;
			}
			for (entry in entries) {
				var lower = entry.toLowerCase();
				if (!StringTools.endsWith(lower, '.hx') || lower.indexOf('character') < 0)
					continue;
				var text = fileContent(Path.join([directory, entry]));
				if (text != null && text.indexOf('getSparrowAtlas') >= 0) {
					characterFile = Path.join([directory, entry]);
					return text;
				}
			}
		}
		return null;
	}

	/** The body of the constructor's `case '<id>':` in Character.hx - the arm
	 * whose statements load an atlas and register animations. */
	static function characterCaseBlock(text:String, characterId:String):Null<String> {
		var switchPattern = new EReg("switch\\s*\\(\\s*curCharacter\\s*\\)", "");
		var searchPos = 0;
		while (searchPos < text.length) {
			// Substring matching keeps matchedPos() arithmetic local; Character.hx
			// is small and only a few switches sit on curCharacter.
			var window = text.substring(searchPos);
			if (!switchPattern.match(window))
				return null;
			var matched = switchPattern.matchedPos();
			var headEnd = searchPos + matched.pos + matched.len;
			var brace = text.indexOf('{', headEnd);
			if (brace < 0)
				return null;
			var end = matchingBrace(text, brace);
			if (end < 0)
				return null;
			searchPos = end;
			var body = text.substring(brace + 1, end);
			var casePattern = new EReg("case\\s+['\"]" + EReg.escape(characterId) + "['\"]\\s*:", "i");
			if (!casePattern.match(body))
				continue;
			var start = casePattern.matchedPos().pos + casePattern.matchedPos().len;
			var nextCase = body.indexOf('case ', start);
			var stop = nextCase < 0 ? body.length : nextCase;
			var block = body.substring(start, stop);
			// Only the definition arm loads an atlas or registers animations;
			// the dance()/update() switches re-play existing names.
			if (block.indexOf('getSparrowAtlas') >= 0 || block.indexOf('fromSparrow') >= 0
				|| block.indexOf('addByPrefix') >= 0 || block.indexOf('addByIndices') >= 0)
				return block;
		}
		return null;
	}

	/**
		The gf character a stage selects through PlayState's `var gfVersion`
		switch (`switch (curStage) { case 'x': gfVersion = 'y'; }`), or null
		when the stage keeps the default girlfriend.
	*/
	public static function stageGfVersion(sourceRoot:String, stageId:String):Null<String> {
		if (stageId == null || StringTools.trim(stageId) == '')
			return null;
		var mapped:String = null;
		for (text in playStateSources(sourceRoot)) {
			for (signature in ['switch (curStage)', 'switch(curStage)']) {
				for (line in switchArm(text, signature, StringTools.trim(stageId))) {
					var pattern = new EReg("gfVersion\\s*=\\s*['\"]([^'\"]+)['\"]", "");
					if (pattern.match(line))
						mapped = pattern.matched(1);
				}
			}
		}
		return mapped;
	}

	/** True when the player2 switch arm hides the opponent for this chart
	 * (`dad.visible = false;` - exTricky stages out the previous dad). */
	public static function player2HidesDad(text:String, characterId:String):Bool {
		for (signature in ['switch (SONG.player2)', 'switch(SONG.player2)']) {
			for (line in switchArm(text, signature, characterId, true)) {
				var pattern = new EReg("dad\\.visible\\s*=\\s*false", "");
				if (pattern.match(line))
					return true;
			}
		}
		return false;
	}

	/** Character offset just past this song's block in the source, so sprite
	 * collection never picks up later branches' same-name redeclarations. */
	static function textEndForSong(text:String, songKey:String):Int {
		var index = 0;
		while (index < text.length) {
			var at = text.indexOf('SONG.song.toLowerCase()', index);
			if (at < 0)
				return text.length;
			var ifAt = text.lastIndexOf("if (", at);
			if (ifAt < 0 || at - ifAt > 200) {
				index = at + 1;
				continue;
			}
			var openParen = text.indexOf('(', ifAt);
			var closeParen = openParen < 0 ? -1 : matchingParen(text, openParen);
			if (closeParen < 0)
				return text.length;
			var conditionText = text.substring(ifAt, closeParen + 1);
			var names:Array<String> = [];
			var condition = new EReg("SONG\\.song\\.toLowerCase\\(\\)\\s*(==|!=)\\s*'([^']+)'", "");
			var pos = 0;
			while (condition.matchSub(conditionText, pos)) {
				var name = condition.matched(2);
				if (names.indexOf(name) < 0)
					names.push(name);
				pos = condition.matchedPos().pos + condition.matchedPos().len;
			}
			var brace = text.indexOf('{', closeParen);
			var end = brace < 0 ? -1 : matchingBrace(text, brace);
			if (names.length == 0 || brace < 0 || end < 0) {
				index = closeParen;
				continue;
			}
			if (names.indexOf(songKey) >= 0)
				return end + 1;
			index = end;
		}
		return text.length;
	}

	static function extractFromSource(text:String, songKey:String, sourceRoot:String, ?player2:String):Null<Dynamic> {
		var block = songBlock(text, songKey);
		if (block == null)
			return null;
		// Sprite assignments carry the authored coordinates; hoisted
		// declarations outside the block contribute too (Kade builds declare
		// sprites early and configure/add them inside per-song branches).
		var sprites = new Map<String, Dynamic>();
		// Later branches of the song chain (for example the base-game else
		// arm) redeclare the same sprite names; only assignments up to the end
		// of THIS song's block can belong to it.
		collectSpriteAssignments(text.substring(0, textEndForSong(text, songKey)), sprites, songKey, sourceRoot);
		// Branch assignments inside the block (for example the nevada stage's
		// per-song island) must resolve for THIS song, not last-wins across
		// branches: re-read them from the already-evaluated block lines.
		collectSpriteAssignments(block.join('\n'), sprites, songKey, sourceRoot);

		var excluded = new Map<String, Bool>();
		collectAlphaZero(text, excluded);
		var zoom:Null<Float> = null;
		var stageId:String = null;
		var adds:Array<String> = [];
		var atlasAnims = new Map<String, Dynamic>();
		var scales = new Map<String, Array<Float>>();
		var scrolls = new Map<String, Array<Float>>();
		for (line in block) {
			var value:Dynamic;
			if ((value = matchFloat(line, 'defaultCamZoom\\s*=\\s*')) != null)
				zoom = value;
			if ((value = matchQuoted(line, 'curStage\\s*=\\s*')) != null)
				stageId = value;
			var added = matchAdded(line);
			if (added != null && adds.indexOf(added) < 0)
				adds.push(added);
			collectSpriteConfig(line, sprites, atlasAnims, scales, scrolls, sourceRoot);
		}
		// Kade adds later-conditioned sprites (spawn holes, covers) outside the
		// per-song block through `if (curStage == '<id>')` guards file-wide.
		if (stageId != null) {
			var guarded = guardedStatementsFor(text, stageId);
			for (line in guarded) {
				var added = matchAdded(line);
				if (added != null && adds.indexOf(added) < 0)
					adds.push(added);
				collectSpriteConfig(line, sprites, atlasAnims, scales, scrolls, sourceRoot);
			}
		}
		// Resolve layer order from add() calls; skip sprites with no readable
		// asset, alpha-zero overlays, and member expressions (dad.exSpikes).
		var assetIndexes = new Map<String, Int>();
		var assets:Array<Dynamic> = [];
		var layers:Array<Dynamic> = [];
		for (name in adds) {
			if (name.indexOf('.') >= 0)
				continue;
			if (excluded.exists(name))
				continue;
			var sprite:Dynamic = sprites.get(name);
			if (sprite == null || sprite.asset == null) {
				continue;
			}
			var assetPath:String = sprite.asset;
			if (!FileSystem.exists(assetPath))
				continue;
			var index:Null<Int> = assetIndexes.get(name);
			if (index == null) {
				index = assets.length;
				assets.push({source: assetPath, destination: 'prop-' + index + '.' + Path.extension(assetPath)});
				assetIndexes.set(name, index);
				var xmlSibling = Path.withoutExtension(assetPath) + '.xml';
				if (sprite.atlas == true && FileSystem.exists(xmlSibling)) {
					assets.push({source: xmlSibling, destination: 'prop-' + index + '.xml'});
				}
			}
			var layer:Dynamic = {
				file: index,
				x: sprite.x,
				y: sprite.y,
				scale: sprite.scale,
				scroll: scrolls.exists(name) ? scrolls.get(name) : [1.0, 1.0]
			};
			if (scales.exists(name))
				layer.scale = scales.get(name)[0];
			if (sprite.atlas == true && atlasAnims.exists(name))
				Reflect.setField(layer, 'anim', atlasAnims.get(name));
			layers.push(layer);
		}
		if (layers.length == 0)
			return null;
		var actors = characterLayout(text, stageId, player2);
		return {
			id: songKey,
			zoom: zoom,
			stageId: stageId,
			layers: layers,
			actors: actors,
			assets: assets
		};
	}

	/** The per-song statement lines from the `if (SONG.song.toLowerCase() ==
	 * 'x')` chain, with nested song conditionals evaluated for this song. */
	static function songBlock(text:String, songKey:String):Null<Array<String>> {
		var condition = new EReg("SONG\\.song\\.toLowerCase\\(\\)\\s*(==|!=)\\s*'([^']+)'", "");
		var index = 0;
		while (index < text.length) {
			var at = text.indexOf('SONG.song.toLowerCase()', index);
			if (at < 0)
				return null;
			var windowStart = Math.max(0, at - 200);
			var lineStart = text.lastIndexOf('\n', at) + 1;
			// Conditions appear inside `if (...)`; scan back to the if.
			var ifAt = text.lastIndexOf("if (", at);
			if (ifAt < 0 || ifAt < windowStart) {
				index = at + 1;
				continue;
			}
			// The condition itself contains parentheses (toLowerCase()); match
			// the if's opening paren by depth instead of taking the first ')'.
			var openParen = text.indexOf('(', ifAt);
			if (openParen < 0 || openParen > at)
				return null;
			var closeParen = matchingParen(text, openParen);
			if (closeParen < 0)
				return null;
			var conditionText = text.substring(ifAt, closeParen + 1);
			var names:Array<String> = [];
			var pos = 0;
			while (true) {
				if (!condition.matchSub(conditionText, pos))
					break;
				var name = condition.matched(2);
				if (names.indexOf(name) < 0)
					names.push(name);
				pos = condition.matchedPos().pos + condition.matchedPos().len;
			}
			if (names.length == 0) {
				index = closeParen;
				continue;
			}
			var brace = text.indexOf('{', closeParen);
			if (brace < 0)
				return null;
			var end = matchingBrace(text, brace);
			if (end < 0)
				return null;
			if (names.indexOf(songKey) >= 0) {
				var body = text.substring(brace + 1, end);
				return evaluateSongConditionals(splitStatements(body), songKey);
			}
			index = end;
		}
		return null;
	}

	/** Keep statements whose nested `SONG.song` conditions are true for this
	 * song; unrelated conditionals keep their content conservatively. */
	static function evaluateSongConditionals(lines:Array<String>, songKey:String):Array<String> {
		var result:Array<String> = [];
		// One entry per open conditional: true while its body is active.
		// Statements arrive split on ';', so re-split into physical lines
		// first: a `} else {` cluster must feed the stack one token at a time.
		var flags:Array<Bool> = [];
		var pendingSingle = false;
		var awaitingElse = false;
		for (chunk in lines) {
			for (raw in chunk.split('\n')) {
			var trimmed = StringTools.trim(raw);
			var isSongCondition = trimmed.indexOf('if') == 0 && trimmed.indexOf('SONG.song.toLowerCase()') >= 0;
			if (isSongCondition) {
				var inverted = trimmed.indexOf('!=') >= 0;
				var quoted = matchQuoted(trimmed, "");
				var keepFlag = quoted != null && (inverted ? quoted != songKey : quoted == songKey);
				flags.push(keepFlag);
				continue;
			}
			if (trimmed == '{') {
				pendingSingle = false;
				continue;
			}
			if (trimmed == '}') {
				pendingSingle = false;
				// An arm closer may be followed by `else`; defer the pop so
				// the else flips THIS conditional instead of an outer one.
				awaitingElse = true;
				continue;
			}
			if (trimmed == 'else' || StringTools.startsWith(trimmed, 'else')) {
				awaitingElse = false;
				if (flags.length > 0)
					flags[flags.length - 1] = !flags[flags.length - 1];
				// A braceless else arm covers exactly one statement.
				pendingSingle = true;
				continue;
			}
			if (awaitingElse) {
				awaitingElse = false;
				if (flags.length > 0)
					flags.pop();
			}
			// Unrelated conditionals push a neutral flag so their braces and
			// else arms stay balanced against ours.
			if (trimmed.indexOf('if') == 0 && trimmed.indexOf('(') >= 0) {
				flags.push(true);
				pendingSingle = true;
				continue;
			}
			if (pendingSingle && trimmed != '') {
				// The single statement of a braceless arm ended this region.
				pendingSingle = false;
				var singleLine = raw;
				var keepSingle = true;
				for (flag in flags)
					if (!flag) {
						keepSingle = false;
						break;
					}
				if (keepSingle)
					result.push(singleLine);
				if (flags.length > 0)
					flags.pop();
				continue;
			}
			var keep = true;
			for (flag in flags)
				if (!flag) {
					keep = false;
					break;
				}
			if (keep)
				result.push(raw);
			}
		}
		return result;
	}

	static function splitStatements(body:String):Array<String> {
		return body.split(';\n');
	}

	static function matchingParen(text:String, open:Int):Int {
		var depth = 0;
		var index = open;
		while (index < text.length) {
			var char = text.charAt(index);
			if (char == '(')
				depth++;
			else if (char == ')') {
				depth--;
				if (depth == 0)
					return index;
			}
			index++;
		}
		return -1;
	}

	static function matchingBrace(text:String, open:Int):Int {
		var depth = 0;
		var index = open;
		while (index < text.length) {
			var char = text.charAt(index);
			if (char == '{')
				depth++;
			else if (char == '}') {
				depth--;
				if (depth == 0)
					return index;
			}
			index++;
		}
		return -1;
	}

	static function collectSpriteAssignments(text:String, sprites:Map<String, Dynamic>, songKey:String, sourceRoot:String):Void {
		// `var bg:FlxSprite = new FlxSprite(...)` would otherwise capture the
		// type name; drop type annotations on a working copy first.
		var normalized = new EReg("var\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*:\\s*[A-Za-z_][A-Za-z0-9_.]*", "g")
			.replace(text, "var $1");
		var pattern = new EReg("([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*new FlxSprite\\(\\s*(-?[0-9.]+)\\s*,\\s*(-?[0-9.]+)", "");
		// Anchor scans keep this linear; EReg.matchSub over a whole source
		// file is quadratic on the interpreter VM.
		var searchPos = 0;
		while (true) {
			var at = normalized.indexOf('new FlxSprite(', searchPos);
			if (at < 0)
				break;
			searchPos = at + 10;
			// Parse the declaration's own line so adjacent sprite
			// declarations can never cross-contaminate names and coordinates.
			var lineStart = normalized.lastIndexOf('\n', at) + 1;
			var lineEnd = normalized.indexOf('\n', at);
			if (lineEnd < 0)
				lineEnd = normalized.length;
			var line = normalized.substring(lineStart, lineEnd);
			if (!pattern.matchSub(line, 0))
				continue;
			var name = pattern.matched(1);
			var sprite:Dynamic = sprites.exists(name) ? sprites.get(name) : {x: 0.0, y: 0.0};
			sprite.x = Std.parseFloat(pattern.matched(2));
			sprite.y = Std.parseFloat(pattern.matched(3));
			var image = matchAssetCall(line, 'Paths\\.image');
			if (image != null) {
				sprite.asset = resolveAssetPath(sourceRoot, image, false);
				sprite.atlas = false;
			}
			sprites.set(name, sprite);
		}
		// Atlas-based props: `name.frames = Paths.getSparrowAtlas('x', 'lib')`.
		var atlasPattern = new EReg("([A-Za-z_][A-Za-z0-9_]*)\\.frames\\s*=\\s*(?:Paths\\.getSparrowAtlas|CachedFrames[^\\n]*)\\(\\s*'([^']+)'\\s*(?:,\\s*'([^']+)')?", "");
		searchPos = 0;
		while (true) {
			var at = normalized.indexOf('Paths.getSparrowAtlas(', searchPos);
			if (at < 0)
				break;
			searchPos = at + 10;
			var windowStart = at - 160;
			if (windowStart < 0)
				windowStart = 0;
			var window = normalized.substring(windowStart, at + 80);
			if (!atlasPattern.matchSub(window, 0))
				continue;
			var name = atlasPattern.matched(1);
			var sprite:Dynamic = sprites.exists(name) ? sprites.get(name) : {x: 0.0, y: 0.0};
			sprite.asset = resolveAssetPath(sourceRoot, {key: atlasPattern.matched(2), library: atlasPattern.matched(3)}, true);
			sprite.atlas = true;
			sprites.set(name, sprite);
		}
	}

	static function collectAlphaZero(text:String, excluded:Map<String, Bool>):Void {
		var pattern = new EReg("([A-Za-z_][A-Za-z0-9_]*)\\.alpha\\s*=\\s*0(?:\\.0+)?\\s*;", "");
		var searchPos = 0;
		while (true) {
			var at = text.indexOf('.alpha', searchPos);
			if (at < 0)
				break;
			searchPos = at + 6;
			var windowEnd = at + 40;
			if (windowEnd > text.length)
				windowEnd = text.length;
			var windowStart = at - 60;
			if (windowStart < 0)
				windowStart = 0;
			if (pattern.matchSub(text.substring(windowStart, windowEnd), 0))
				excluded.set(pattern.matched(1), true);
		}
	}

	static function collectSpriteConfig(line:String, sprites:Map<String, Dynamic>, atlasAnims:Map<String, Dynamic>,
			scales:Map<String, Array<Float>>, scrolls:Map<String, Array<Float>>, sourceRoot:String):Void {
		var name = matchSpriteName(line);
		if (name == null)
			return;
		var value:Dynamic;
		// setGraphicSize(Std.int(name.width * 4)) -> uniform scale.
		var sizeMatch = new EReg("^\\s*" + name + "\\.setGraphicSize\\(\\s*Std\\.int\\(\\s*"
			+ name + "\\.width\\s*\\*\\s*(-?[0-9.]+)", "");
		if (sizeMatch.match(line)) {
			var scale = Std.parseFloat(sizeMatch.matched(1));
			scales.set(name, [scale, scale]);
			return;
		}
		var scaleMatch = new EReg("^\\s*" + name + "\\.scale\\.set\\(\\s*(-?[0-9.]+)\\s*,\\s*(-?[0-9.]+)", "");
		if (scaleMatch.match(line)) {
			scales.set(name, [Std.parseFloat(scaleMatch.matched(1)), Std.parseFloat(scaleMatch.matched(2))]);
			return;
		}
		var scrollMatch = new EReg("^\\s*" + name + "\\.scrollFactor\\.set\\(\\s*(-?[0-9.]+)\\s*,\\s*(-?[0-9.]+)", "");
		if (scrollMatch.match(line)) {
			scrolls.set(name, [Std.parseFloat(scrollMatch.matched(1)), Std.parseFloat(scrollMatch.matched(2))]);
			return;
		}
		var animMatch = new EReg("^\\s*" + name + "\\.animation\\.addByPrefix\\(\\s*'([^']+)'\\s*,\\s*'([^']+)'\\s*,\\s*([0-9.]+)", "");
		if (animMatch.match(line)) {
			atlasAnims.set(name, {
				name: animMatch.matched(1),
				prefix: animMatch.matched(2),
				fps: Std.parseInt(animMatch.matched(3))
			});
			return;
		}
		var image = matchAssetCall(line, 'Paths\\.image');
		if (image != null && sprites.exists(name)) {
			var sprite:Dynamic = sprites.get(name);
			sprite.asset = resolveAssetPath(sourceRoot, image, false);
			sprite.atlas = false;
			sprites.set(name, sprite);
		}
	}

	static function matchSpriteName(line:String):Null<String> {
		var pattern = new EReg("^\\s*([A-Za-z_][A-Za-z0-9_]*)\\.", "");
		if (!pattern.match(line))
			return null;
		return pattern.matched(1);
	}

	static function matchAdded(line:String):Null<String> {
		var pattern = new EReg("^\\s*add\\(\\s*([A-Za-z_][A-Za-z0-9_.]*)\\s*\\)", "");
		if (!pattern.match(line))
			return null;
		return pattern.matched(1);
	}

	static function matchAssetCall(line:String, call:String):Null<Dynamic> {
		var pattern = new EReg(call + "\\(\\s*['\"]([^'\"]+)['\"]\\s*(?:,\\s*['\"]([^'\"]+)['\"])?", "");
		if (!pattern.match(line))
			return null;
		return {key: pattern.matched(1), library: pattern.matched(2)};
	}

	static function matchQuoted(line:String, prefix:String):Null<String> {
		var pattern = new EReg(prefix + "'([^']+)'", "");
		if (!pattern.match(line))
			return null;
		return pattern.matched(1);
	}

	static function matchFloat(line:String, prefix:String):Null<Float> {
		var pattern = new EReg(prefix + "\\s*(-?[0-9.]+)", "");
		if (!pattern.match(line))
			return null;
		var value = Std.parseFloat(pattern.matched(1));
		return Math.isNaN(value) ? null : value;
	}

	/** Statements guarded file-wide by `curStage == '<stageId>'`. */
	static function guardedStatementsFor(text:String, stageId:String):Array<String> {
		var results:Array<String> = [];
		var needle = "curStage == '" + stageId + "'";
		var index = 0;
		while (true) {
			var at = text.indexOf(needle, index);
			if (at < 0)
				break;
			var lineStart = text.lastIndexOf('\n', at) + 1;
			var lineEnd = text.indexOf('\n', at);
			if (lineEnd < 0)
				lineEnd = text.length;
			var line = text.substring(lineStart, lineEnd);
			if (StringTools.trim(line).indexOf('if') == 0 || line.indexOf('&&') >= 0 || line.indexOf('||') >= 0) {
				var brace = text.indexOf('{', at);
				var statementEnd = text.indexOf(';', at);
				if (brace >= 0 && (statementEnd < 0 || brace < statementEnd)) {
					var end = matchingBrace(text, brace);
					if (end > 0)
						results = results.concat(splitStatements(text.substring(brace + 1, end)));
				} else if (statementEnd > 0) {
					var openParen = text.indexOf('(', at);
					var guardClose = openParen < 0 ? -1 : matchingParen(text, openParen);
					var bodyStart = guardClose >= 0 && guardClose < statementEnd ? guardClose + 1 : at;
					results.push(text.substring(bodyStart, statementEnd));
				}
			}
			index = at + needle.length;
		}
		return results;
	}

	/** Kade Paths: `Paths.image('key', 'library')` resolves below
	 * assets/<library>/images/ (default library: preload, then images/). */
	static function resolveAssetPath(sourceRoot:String, asset:Dynamic, atlas:Bool):Null<String> {
		var key = asset.key;
		var library = asset.library == null ? 'preload' : asset.library;
		var candidates:Array<String> = [];
		var extension = atlas ? '.png' : '.png';
		for (base in ['assets/' + library + '/images', 'assets/images', 'assets/preload/images']) {
			candidates.push(Path.join([sourceRoot, base, key + '.png']));
			candidates.push(Path.join([sourceRoot, base, key + '.xml']));
		}
		for (candidate in candidates)
			if (StringTools.endsWith(candidate, extension) && FileSystem.exists(candidate))
				return candidate;
		for (candidate in candidates)
			if (FileSystem.exists(candidate))
				return candidate;
		return null;
	}

	/** Character bases plus the curStage/player2 switch repositioning. */
	static function characterLayout(text:String, stageId:Null<String>, ?player2:String):Dynamic {
		var gf = characterBase(text, 'gf = new Character(');
		var dad = characterBase(text, 'dad = new Character(');
		var boyfriend = characterBase(text, 'boyfriend = new Boyfriend(');
		if (gf == null)
			gf = [400, 130];
		if (dad == null)
			dad = [100, 100];
		if (boyfriend == null)
			boyfriend = [770, 450];
		var gfPoint = [gf[0], gf[1]];
		var dadPoint = [dad[0], dad[1]];
		var bfPoint = [boyfriend[0], boyfriend[1]];
		if (stageId != null) {
			applyCaseAdjustments(switchArm(text, 'switch (curStage)', stageId), bfPoint, gfPoint, dadPoint);
			applyCaseAdjustments(switchArm(text, 'switch(curStage)', stageId), bfPoint, gfPoint, dadPoint);
		}
	if (player2 != null && StringTools.trim(player2) != '')
		applyCaseAdjustments(switchArm(text, 'switch (SONG.player2)', StringTools.trim(player2), true), bfPoint, gfPoint, dadPoint);
		applyCaseAdjustments(switchArm(text, 'switch(SONG.player2)', StringTools.trim(player2), true), bfPoint, gfPoint, dadPoint);
		return {bf: bfPoint, dad: dadPoint, gf: gfPoint};
	}

	static function characterBase(text:String, signature:String):Null<Array<Float>> {
		var at = text.indexOf(signature);
		if (at < 0)
			return null;
		var pattern = new EReg("\\(\\s*(-?[0-9.]+)\\s*,\\s*(-?[0-9.]+)", "");
		if (!pattern.matchSub(text, at))
			return null;
		return [Std.parseFloat(pattern.matched(1)), Std.parseFloat(pattern.matched(2))];
	}

	/** The statement lines of `case '<label>':` inside one switch. */
	static function switchArm(text:String, switchSignature:String, label:String,
		?insensitive:Bool):Array<String> {
		// Several switches share a subject (for example `switch (curStage)`
		// and `switch(curStage)`); collect the labelled arm from every one.
		var results:Array<String> = [];
		var searchPos = 0;
		while (true) {
			var at = text.indexOf(switchSignature, searchPos);
			if (at < 0)
				break;
			searchPos = at + switchSignature.length;
			var brace = text.indexOf('{', at);
			if (brace < 0)
				break;
			var end = matchingBrace(text, brace);
			if (end < 0)
				break;
			var body = text.substring(brace + 1, end);
			// Chart-facing labels (SONG.player2) arrive lowercased from the
			// importer while the source authors mixed-case ids (exTricky), so
			// those arms must match case-insensitively.
			var casePattern = new EReg("case\\s+'" + EReg.escape(label) + "'\\s*:",
				insensitive == true ? "i" : "");
			if (!casePattern.match(body))
				continue;
			var start = casePattern.matchedPos().pos + casePattern.matchedPos().len;
			var nextCase = body.indexOf('case ', start);
			var closing = body.indexOf('}', start);
			var stop = nextCase < 0 ? (closing < 0 ? body.length : closing) : (closing < 0 ? nextCase : Std.int(Math.min(nextCase, closing)));
			results = results.concat(splitStatements(body.substring(start, stop)));
		}
		return results;
	}

	static function applyCaseAdjustments(lines:Array<String>, bfPoint:Array<Float>, gfPoint:Array<Float>, dadPoint:Array<Float>):Void {
		for (line in lines) {
			var pattern = new EReg("(boyfriend|dad|gf)\\.(x|y)\\s*(\\+=|-=)\\s*([0-9.]+)", "");
			if (!pattern.match(line))
				continue;
			var point = pattern.matched(1) == 'boyfriend' ? bfPoint : (pattern.matched(1) == 'dad' ? dadPoint : gfPoint);
			var axis = pattern.matched(2) == 'x' ? 0 : 1;
			var value = Std.parseFloat(pattern.matched(4));
			point[axis] = pattern.matched(3) == '+=' ? point[axis] + value : point[axis] - value;
		}
	}

	/** Public hook for the player2 switch: adjustments for one character id. */
	public static function player2Adjustments(text:String, characterId:String):Array<Array<Dynamic>> {
		var operations:Array<Array<Dynamic>> = [];
		for (signature in ['switch (SONG.player2)', 'switch(SONG.player2)'])
		for (line in switchArm(text, signature, characterId, true)) {
			var pattern = new EReg("(dad|gf)\\.(x|y)\\s*(\\+=|-=)\\s*([0-9.]+)", "");
			if (!pattern.match(line))
				continue;
			operations.push([pattern.matched(1), pattern.matched(2), pattern.matched(3), Std.parseFloat(pattern.matched(4))]);
		}
		return operations;
	}
}
