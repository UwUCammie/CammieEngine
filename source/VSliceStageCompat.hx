package;

import CompatScriptManifest.CompatScriptManifestData;

using StringTools;

/** Runtime-only repair for stage prop blocks emitted by older V-Slice imports.
 * Existing destination scripts are left intact, including authored HScript. */
class VSliceStageCompat {
	static var literalNumber = '-?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?';
	static var literalColor = '(?:-?[0-9]+|0[xX][0-9A-Fa-f]+)';
	static var literalPair = '\\(' + literalNumber + ', ' + literalNumber + '\\)';

	/** Older generated stage scripts kept only a sanitized prop identifier.
	 * Resolve an HXC authored-name lookup against that exact generated shape,
	 * while refusing ambiguous identifiers. New imports register exact names. */
	public static function legacyGeneratedProp(name:String, elements:Map<String, Dynamic>):Dynamic {
		if (name == null || name == '' || elements == null)
			return null;
		var slug = '';
		for (index in 0...name.length) {
			var c = name.charAt(index).toLowerCase();
			slug += ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_') ? c : '_';
		}
		if (slug == '') slug = 'asset';
		if (slug.charAt(0) >= '0' && slug.charAt(0) <= '9') slug = '_' + slug;
		var pattern = new EReg('^vSliceProp_' + slug + '_[0-9]+$', '');
		var found:Dynamic = null;
		for (key in elements.keys()) {
			if (!pattern.match(key)) continue;
			var candidate = elements.get(key);
			if (candidate == null) continue;
			if (found != null) {
				trace('[vslice-stage-prop-ambiguous] Multiple generated props match ' + name);
				return null;
			}
			found = candidate;
		}
		return found;
	}

	static function selectedVSlice(manifest:CompatScriptManifestData):Bool {
		if (manifest == null)
			return false;
		var normalized = CompatScriptManifest.normalize(manifest);
		var selected = CompatScriptManifest.selectedRoot(normalized);
		if (selected == '')
			return false;
		for (root in normalized.roots)
			if (root.path == selected && root.engine == ImportEngine.V_SLICE)
				return true;
		return false;
	}

	/** Recover raw role values from the exact older generated character block.
	 * The destination HScript is unchanged; this registers data only while the
	 * selected imported stage is parsed for a native runtime stage swap. */
	public static function normalizeGeneratedCharacterPresentation(source:String,
		manifest:CompatScriptManifestData, stageScope:Bool):String {
		if (!stageScope || source == null || !selectedVSlice(manifest))
			return source;
		var lines = source.split('\n');
		var start = -1;
		for (index in 0...lines.length)
			if (lines[index].trim() == 'function start(song) {') {
				start = index;
				break;
			}
		if (start < 0 || start + 1 >= lines.length
			|| !new EReg('^setDefaultZoom\\(' + literalNumber + '\\);$', '').match(lines[start + 1].trim()))
			return source;
		var additions:Array<String> = [];
		for (role in ['bf', 'dad', 'gf']) {
			var actor = role == 'bf' ? 'boyfriend' : role;
			var global = role == 'bf' ? 'playerOffset' : (role == 'gf' ? 'gfOffset' : 'enemyOffset');
			var already = 'stage.setVSliceCharacterPresentation("' + role + '", ';
			if (source.indexOf(already) >= 0)
				continue;
			var first = 'stage.setOffsets("' + role + '", ';
			for (index in start + 2...lines.length - 2) {
				var line = lines[index].trim();
				if (!line.startsWith(first) || !line.endsWith(', false);'))
					continue;
				var pair = line.substr(first.length, line.length - first.length - ', false);'.length).split(', ');
				if (pair.length != 2 || lines[index + 1].trim() != actor + '.x = ' + pair[0] + ';'
					|| lines[index + 2].trim() != actor + '.y = ' + pair[1] + ';')
					continue;
				var x = new EReg('^(' + literalNumber + ') - ' + actor
					+ '\\.width / 2(?: \\+ ' + actor + '\\.' + global + 'X)?$', '');
				var y = new EReg('^(' + literalNumber + ') - ' + actor
					+ '\\.height(?: \\+ ' + actor + '\\.' + global + 'Y)?$', '');
				if (!x.match(pair[0])) continue;
				var feetX = x.matched(1);
				if (!y.match(pair[1])) continue;
				var feetY = y.matched(1);
				var scaleX = '1';
				var scaleY = '1';
				if (index >= 2 && lines[index - 1].trim() == actor + '.updateHitbox();') {
					var scale = new EReg('^' + actor + '\\.scale\\.set\\(' + actor + '\\.scale\\.x \\* ('
						+ literalNumber + '), ' + actor + '\\.scale\\.y \\* (' + literalNumber + ')\\);$', '');
					if (!scale.match(lines[index - 2].trim()))
						continue;
					scaleX = scale.matched(1);
					scaleY = scale.matched(2);
				}
				var tailStart = index + 3;
				if (tailStart < lines.length && lines[tailStart].trim() == actor + '.followCamX = 0;') {
					if (tailStart + 1 >= lines.length || lines[tailStart + 1].trim() != actor + '.followCamY = 0;')
						continue;
					tailStart += 2;
				} else if (tailStart < lines.length && lines[tailStart].trim().startsWith(actor + '.followCam'))
					continue;
				var cameraX = '0';
				var cameraY = '0';
				var alpha = '1';
				var angle = '0';
				var camera = new EReg('^stage\\.setCamOffsets\\("' + role + '", (' + literalNumber
					+ '), (' + literalNumber + '), false\\);$', '');
				var alphaLine = new EReg('^' + actor + '\\.alpha = (' + literalNumber + ');$', '');
				var angleLine = new EReg('^' + actor + '\\.angle = (' + literalNumber + ');$', '');
				for (tail in tailStart...Std.int(Math.min(lines.length, tailStart + 6))) {
					var current = lines[tail].trim();
					if (camera.match(current)) { cameraX = camera.matched(1); cameraY = camera.matched(2); }
					if (alphaLine.match(current)) alpha = alphaLine.matched(1);
					if (angleLine.match(current)) angle = angleLine.matched(1);
				}
				additions.push('    stage.setVSliceCharacterPresentation("' + role + '", '
					+ feetX + ', ' + feetY + ', ' + scaleX + ', ' + scaleY
					+ ', 1, 1, ' + alpha + ', ' + angle + ', ' + cameraX + ', ' + cameraY + ');');
				break;
			}
		}
		if (additions.length == 0)
			return source;
		lines.insert(start + 2, additions.join('\n'));
		return lines.join('\n');
	}

	/** Insert the missing Flixel hitbox update only in an exact generated prop
	 * block from the selected V-Slice import. The older template built each
	 * `vSliceProp_*` with a graphic, scale and scroll on consecutive lines. */
	public static function normalizeGeneratedPropHitboxes(source:String,
		manifest:CompatScriptManifestData, stageScope:Bool):String {
		if (!stageScope || source == null || !selectedVSlice(manifest))
			return source;
		var lines = source.split('\n');
		var declarations:Map<String, Bool> = new Map();
		var declaration = ~/^var (vSliceProp_[A-Za-z0-9_]+);$/;
		var number = '-?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?';
		var pair = '\\(' + number + ', ' + number + '\\)';
		var scaleLine = new EReg('^(vSliceProp_[A-Za-z0-9_]+)\\.scale\\.set' + pair + ';$', '');
		for (line in lines) {
			var clean = line.trim();
			if (declaration.match(clean))
				declarations.set(declaration.matched(1), true);
		}
		var output:Array<String> = [];
		for (index in 0...lines.length) {
			var line = lines[index];
			output.push(line);
			if (!scaleLine.match(line.trim()) || index < 2 || index + 1 >= lines.length)
				continue;
			var name = scaleLine.matched(1);
			if (!declarations.exists(name))
				continue;
			var created = lines[index - 2].trim();
			var graphic = lines[index - 1].trim();
			var next = lines[index + 1].trim();
			if (!new EReg('^' + name + ' = new FlxSprite' + pair + ';$', '').match(created))
				continue;
			var asset = 'hscriptPath \\+ "prop-[A-Za-z0-9_-]+\\.';
			var loadGraphic = new EReg('^' + name + '\\.loadGraphic\\(' + asset + 'png"\\);$', '');
			var sparrow = new EReg('^' + name + '\\.frames = FlxAtlasFrames\\.fromSparrow\\('
				+ asset + 'png", ' + asset + 'xml"\\);$', '');
			var packer = new EReg('^' + name + '\\.frames = FlxAtlasFrames\\.fromSpriteSheetPacker\\('
				+ asset + 'png", ' + asset + 'txt"\\);$', '');
			var solid = new EReg('^' + name + '\\.makeGraphic\\(1, 1, ' + literalColor + '\\);$', '');
			if (!loadGraphic.match(graphic) && !sparrow.match(graphic)
				&& !packer.match(graphic) && !solid.match(graphic))
				continue;
			if (!new EReg('^' + name + '\\.scrollFactor\\.set' + pair + ';$', '').match(next))
				continue;
			var indent = line.substr(0, line.indexOf(name));
			output.push(indent + name + '.updateHitbox();' + (line.endsWith('\r') ? '\r' : ''));
		}
		return output.join('\n');
	}

	/** Older generated scripts retained only coarse actor-relative layer flags.
	 * Give those exact generated props their target actor's depth. PlayState's
	 * stable insertion sort then retains the addSprite order at equal depth.
	 * Absolute donor prop z values cannot be recovered from those scripts. */
	public static function normalizeGeneratedPropLayers(source:String,
		manifest:CompatScriptManifestData, stageScope:Bool):String {
		if (!stageScope || source == null || !selectedVSlice(manifest))
			return source;
		var lines = source.split('\n');
		var declarations:Map<String, Bool> = new Map();
		var eligible:Map<String, Bool> = new Map();
		var alreadySet:Map<String, Bool> = new Map();
		var alreadyNamed:Map<String, Bool> = new Map();
		var actorZ:Map<String, Int> = new Map();
		var declaration = ~/^var (vSliceProp_[A-Za-z0-9_]+);$/;
		var actor = ~/^stage\.setCharacterZ\("(bf|dad|gf)", (-?[0-9]+)\);$/;
		var setZ = ~/^stage\.setZIndex\((vSliceProp_[A-Za-z0-9_]+), /;
		var named = ~/^stage\.elements\.set\("(vSliceProp_[A-Za-z0-9_]+)", (vSliceProp_[A-Za-z0-9_]+)\);$/;
		for (line in lines) {
			var clean = line.trim();
			if (declaration.match(clean))
				declarations.set(declaration.matched(1), true);
			if (actor.match(clean))
				actorZ.set(actor.matched(1), Std.parseInt(actor.matched(2)));
			if (setZ.match(clean))
				alreadySet.set(setZ.matched(1), true);
			if (named.match(clean) && named.matched(1) == named.matched(2))
				alreadyNamed.set(named.matched(1), true);
		}
		// Match the exact older importer creation prefix. A similarly named
		// handwritten prop with computed graphics or transforms stays untouched.
		var creation = new EReg('^(vSliceProp_[A-Za-z0-9_]+) = new FlxSprite' + literalPair + ';$', '');
		for (index in 0...lines.length) {
			if (!creation.match(lines[index].trim()))
				continue;
			var name = creation.matched(1);
			if (!declarations.exists(name) || index + 3 >= lines.length)
				continue;
			var asset = 'hscriptPath \\+ "prop-[A-Za-z0-9_-]+\\.';
			var graphic = lines[index + 1].trim();
			var load = new EReg('^' + name + '\\.loadGraphic\\(' + asset + 'png"\\);$', '');
			var sparrow = new EReg('^' + name + '\\.frames = FlxAtlasFrames\\.fromSparrow\\('
				+ asset + 'png", ' + asset + 'xml"\\);$', '');
			var packer = new EReg('^' + name + '\\.frames = FlxAtlasFrames\\.fromSpriteSheetPacker\\('
				+ asset + 'png", ' + asset + 'txt"\\);$', '');
			var solid = new EReg('^' + name + '\\.makeGraphic\\(1, 1, ' + literalColor + '\\);$', '');
			if (!load.match(graphic) && !sparrow.match(graphic)
				&& !packer.match(graphic) && !solid.match(graphic))
				continue;
			if (!new EReg('^' + name + '\\.scale\\.set' + literalPair + ';$', '').match(lines[index + 2].trim()))
				continue;
			var scrollIndex = index + 3;
			if (lines[scrollIndex].trim() == name + '.updateHitbox();')
				scrollIndex++;
			if (scrollIndex >= lines.length || !new EReg('^' + name + '\\.scrollFactor\\.set'
				+ literalPair + ';$', '').match(lines[scrollIndex].trim()))
				continue;
			eligible.set(name, true);
		}
		var add = ~/^addSprite\((vSliceProp_[A-Za-z0-9_]+), (BEHIND_ALL|BEHIND_BF|BEHIND_DAD|BEHIND_GF|BEHIND_NONE)\);$/;
		var output:Array<String> = [];
		for (line in lines) {
			var clean = line.trim();
			if (add.match(clean)) {
				var name = add.matched(1);
				var layer = add.matched(2);
				if (eligible.exists(name) && !alreadySet.exists(name)) {
					var z:Null<Int> = switch (layer) {
						case 'BEHIND_BF': actorZ.get('bf');
						case 'BEHIND_DAD': actorZ.get('dad');
						case 'BEHIND_GF': actorZ.get('gf');
						case 'BEHIND_ALL' | 'BEHIND_NONE':
							if (!actorZ.exists('bf') || !actorZ.exists('dad') || !actorZ.exists('gf'))
								null;
							else if (layer == 'BEHIND_ALL')
								Std.int(Math.min(actorZ.get('bf'), Math.min(actorZ.get('dad'), actorZ.get('gf'))));
							else
								Std.int(Math.max(actorZ.get('bf'), Math.max(actorZ.get('dad'), actorZ.get('gf'))));
						default: null;
					};
					if (z != null) {
						var indent = line.substr(0, line.indexOf('addSprite'));
						output.push(indent + 'stage.setZIndex(' + name + ', ' + z + ');');
					}
				}
			}
			output.push(line);
			if (add.match(clean)) {
				var name = add.matched(1);
				if (eligible.exists(name) && !alreadyNamed.exists(name)) {
					var indent = line.substr(0, line.indexOf('addSprite'));
					output.push(indent + 'stage.elements.set("' + name + '", ' + name + ');');
				}
			}
		}
		return output.join('\n');
	}
}
