package;

import haxe.io.Path;

/** The authored character JSON values scripts read back off a character. */
typedef SourceCharacterFields = {
	var jsonScale:Float;
	var originalFlipX:Bool;
	var noAntialiasing:Bool;
	var animationsArray:Array<Dynamic>;
	var vocalsFile:String;
}

/** Psych and Nightmare Vision share one character JSON shape, so both loaders
 * hand their parsed definition here and get the same script-facing fields. */
class SourceCharacterDefinition {
	/** A missing definition gives the same neutral values a fresh character has. */
	public static function fields(definition:Dynamic):SourceCharacterFields {
		var scale:Float = 1;
		var authoredScale:Dynamic = definition == null ? null : Reflect.field(definition, 'scale');
		if (authoredScale != null) {
			var parsed = Std.parseFloat(Std.string(authoredScale));
			if (!Math.isNaN(parsed)) scale = parsed;
		}
		var animations:Dynamic = definition == null ? null : Reflect.field(definition, 'animations');
		var vocals:Dynamic = definition == null ? null : Reflect.field(definition, 'vocals_file');
		return {
			jsonScale: scale,
			originalFlipX: definition != null && Reflect.field(definition, 'flip_x') == true,
			noAntialiasing: definition != null && Reflect.field(definition, 'no_antialiasing') == true,
			// Handed over as authored so scripts can copy names and offsets out of it.
			animationsArray: Std.isOfType(animations, Array) ? cast animations : [],
			vocalsFile: vocals == null ? '' : Std.string(vocals)
		};
	}

	/** Parse the character JSON kept under an import root, or null when that
	 * root has no usable definition for the id. */
	public static function read(characterId:String, scopedRoot:String, readText:String->Null<String>):Dynamic {
		var name = characterId == null ? '' : StringTools.trim(characterId);
		if (name == '' || !~/^[A-Za-z0-9_-]+$/.match(name)
			|| scopedRoot == null || StringTools.trim(scopedRoot) == '' || readText == null)
			return null;
		for (folder in ['characters', 'shared/characters']) {
			try {
				var source = readText(Path.join([scopedRoot, folder, name + '.json']));
				if (source == null) continue;
				var data:Dynamic = haxe.Json.parse(source);
				if (data != null) return data;
			} catch (_:Dynamic) {}
		}
		return null;
	}
}
