/** Pure rendering for standard Psych character JSON converted to HScript. */
class PsychCharacterDanceCompat {
	/** Older generated Psych HScripts set scale without updating the hitbox.
	 * Psych's Character constructor updates width/height before its first dance;
	 * these dimensions determine the camera midpoint for large characters. */
	public static function needsScaledHitbox(scaleX:Float, scaleY:Float,
		frameWidth:Float, frameHeight:Float, width:Float, height:Float):Bool {
		if ((scaleX == 1 && scaleY == 1) || frameWidth <= 0 || frameHeight <= 0)
			return false;
		return Math.abs(width - Math.abs(scaleX) * frameWidth) > 0.01
			|| Math.abs(height - Math.abs(scaleY) * frameHeight) > 0.01;
	}

	/** Repair only a byte-for-byte legacy standard Psych conversion belonging
	 * to the selected owner. Old imports wrote the converted script in the
	 * global character folder, so its path alone cannot establish ownership. */
	public static function needsOwnedLegacyHitbox(characterId:String, selectedRoot:String,
		implementationPath:String, scaleX:Float, scaleY:Float,
		frameWidth:Float, frameHeight:Float, width:Float, height:Float,
		readText:String->Null<String>):Bool {
		if (!needsScaledHitbox(scaleX, scaleY, frameWidth, frameHeight, width, height)
			|| characterId == null || !~/^[A-Za-z0-9_-]+$/.match(characterId)
			|| selectedRoot == null || !StringTools.startsWith(selectedRoot, 'assets/imported_mods/')
			|| implementationPath == null || readText == null)
			return false;
		var globalScript = 'assets/images/custom_chars/' + characterId + '.hscript';
		var ownedScript = selectedRoot + '/images/custom_chars/' + characterId + '.hscript';
		if (implementationPath != globalScript && implementationPath != ownedScript)
			return false;
		try {
			var metadata = readText(selectedRoot + '/characters/' + characterId + '.json');
			if (metadata == null)
				metadata = readText(selectedRoot + '/shared/characters/' + characterId + '.json');
			if (metadata == null)
				return false;
			var data:Dynamic = haxe.Json.parse(metadata);
			var authoredScale = Std.parseFloat(Std.string(Reflect.field(data, 'scale')));
			if (Math.isNaN(authoredScale) || Math.abs(scaleX - authoredScale) > 0.01
				|| Math.abs(scaleY - authoredScale) > 0.01)
				return false;
			var script = readText(implementationPath);
			if (script == null)
				return false;
			for (legacyDance in [true, false]) {
				var generated = renderStandardScript(data, false, false, false, legacyDance);
				// The legacy converter predates Psych's scaled-hitbox call. The
				// current renderer includes it; remove only that exact generated line.
				var oldGenerated = StringTools.replace(generated, '\n    char.updateHitbox();', '');
				if (script == oldGenerated)
					return true;
			}
		} catch (_:Dynamic) {}
		return false;
	}

	public static function hasDancePair(charJson:Dynamic):Bool {
		var animations:Dynamic = charJson == null ? null : Reflect.field(charJson, 'animations');
		if (!Std.isOfType(animations, Array))
			return false;
		var left:Array<String> = [];
		var right:Array<String> = [];
		for (animation in (cast animations:Array<Dynamic>)) {
			if (animation == null)
				continue;
			var name:Dynamic = Reflect.field(animation, 'anim');
			if (!Std.isOfType(name, String))
				continue;
			if (StringTools.startsWith(name, 'danceLeft'))
				left.push(name.substr('danceLeft'.length));
			if (StringTools.startsWith(name, 'danceRight'))
				right.push(name.substr('danceRight'.length));
		}
		for (suffix in left)
			if (right.indexOf(suffix) >= 0)
				return true;
		return false;
	}

	/** Animate imports use the same authored animation inventory as standard
	 * Psych characters. Emit only the dance behavior the metadata can support:
	 * toggle an authored dance pair, fall back to an authored idle, or do nothing.
	 * This avoids generated references to undeclared `danced` and missing anims. */
	public static function renderAnimateDance(charJson:Dynamic):String {
		if (hasDancePair(charJson))
			return "var danced = false;\nfunction dance(char) {\n"
				+ "    var suffix = char.idleSuffix;\n"
				+ "    var left = 'danceLeft' + suffix;\n"
				+ "    var right = 'danceRight' + suffix;\n"
				+ "    if (char.animation.exists(left) && char.animation.exists(right)) {\n"
				+ "        danced = !danced;\n"
				+ "        char.playAnim(danced ? right : left);\n"
				+ "    } else if (char.animation.exists('idle' + suffix))\n"
				+ "        char.playAnim('idle' + suffix);\n"
				+ "    else if (char.animation.exists('idle'))\n"
				+ "        char.playAnim('idle');\n}\n";
		var animations:Dynamic = charJson == null ? null : Reflect.field(charJson, 'animations');
		var hasIdle = false;
		if (Std.isOfType(animations, Array))
			for (animation in (cast animations:Array<Dynamic>)) {
				if (animation == null)
					continue;
				var name:Dynamic = Reflect.field(animation, 'anim');
				if (Std.isOfType(name, String) && StringTools.startsWith(name, 'idle')) {
					hasIdle = true;
					break;
				}
			}
		if (!hasIdle)
			return "function dance(char) {\n}\n";
		return "function dance(char) {\n"
			+ "    var suffix = char.idleSuffix;\n"
			+ "    if (char.animation.exists('idle' + suffix))\n"
			+ "        char.playAnim('idle' + suffix);\n"
			+ "    else if (char.animation.exists('idle'))\n"
			+ "        char.playAnim('idle');\n}\n";
	}

	/** `legacyDance` reproduces the old importer bytes for provenance checks. */
	public static function renderStandardScript(charJson:Dynamic, isPixel:Bool, isBF:Bool,
		isGF:Bool, legacyDance:Bool = false, atlasFiles:Array<String> = null):String {
		var script = "function init(char) {\n";
		if (atlasFiles == null || atlasFiles.length < 2)
			script += "    char.frames = FlxAtlasFrames.fromSparrow(hscriptPath + 'char.png', hscriptPath + 'char.xml');\n";
		else {
			var pairs:Array<String> = [];
			for (atlasName in atlasFiles) if (atlasName != null && atlasName != '')
				pairs.push("[hscriptPath + '" + atlasName + ".png', hscriptPath + '"
					+ atlasName + ".xml']");
			script += "    char.frames = FlxAtlasFrames.combineSparrow([" + pairs.join(', ')
				+ "]);\n";
		}
		var animations:Array<Dynamic> = charJson.animations;
		for (anim in animations) {
			var addAnimation;
			if (anim.indices.length >= 1)
				addAnimation = "char.animation.addByIndices('" + anim.anim + "', '" + anim.name + "', " + anim.indices + ', "", ' + anim.fps + ", " + anim.loop + ");";
			else
				addAnimation = "char.animation.addByPrefix('" + anim.anim + "', '" + anim.name + "', " + anim.fps + ", " + anim.loop + ");";
			var addOffset = "char.addOffset('" + anim.anim + "', " + anim.offsets[0] + ", " + anim.offsets[1] + ");";
			script += '\n    ' + addAnimation + '\n    ' + addOffset + '\n';
		}
		script += '\n    char.flipX = ' + charJson.flip_x + ';';
		if (charJson.scale != 1)
			script += "\n    char.scale.x = " + charJson.scale + ';\n    char.scale.y = ' + charJson.scale + ';\n    char.updateHitbox();';
		if (charJson.no_antialiasing)
			script += "\n    char.antialiasing = " + !charJson.no_antialiasing + ';';
		if (isBF)
			script += "    char.like = 'bf';\n    char.likeBf = true;";
		if (isGF)
			script += "    char.like = 'gf';\n    char.likeGf = true;\n    char.gfEpicLevel = Level_Sing;";
		script += '\n}\ndadVar = ' + charJson.sing_duration + ';';
		script += "\nisPixel = " + isPixel + ";\nfunction update(elapsed, char) {\n\n}\n";
		if (!legacyDance)
			script += 'var danced = false;\n';
		script += "function dance(char) {\n    ";
		if (legacyDance) {
			if (isGF)
				script += "    danced = !danced;\n    if (danced)\n\tchar.playAnim('danceRight');\n    else\n\tchar.playAnim('danceLeft');";
			else
				script += "char.playAnim('idle');\n}";
		} else {
			// Psych recalculates danceIdle from the active suffix. The first
			// paired dance is Right because `danced` starts false.
			script += "var suffix = char.idleSuffix;\n    var left = 'danceLeft' + suffix;\n    var right = 'danceRight' + suffix;\n    if (char.animation.exists(left) && char.animation.exists(right)) {\n        danced = !danced;\n        char.playAnim(danced ? right : left);\n    } else if (char.animation.exists('idle' + suffix))\n        char.playAnim('idle' + suffix);\n}";
		}
		return script;
	}
}
