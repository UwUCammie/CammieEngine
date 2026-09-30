package;

import haxe.io.Path;

/** Psych character JSON owns its direction labels and named animation offsets. */
class PsychCharacterOrientation {
	/**
		Read flip_x only from the selected Psych owner. A null result means there
		is no usable Psych character definition, so native legacy orientation can
		continue unchanged.
	*/
	public static function authoredFlipX(characterId:String, scopedRoot:String,
		readText:String->Null<String>):Null<Bool> {
		var name = characterId == null ? '' : StringTools.trim(characterId);
		if (name == '' || !~/^[A-Za-z0-9_-]+$/.match(name)
			|| scopedRoot == null || StringTools.trim(scopedRoot) == '' || readText == null)
			return null;
		for (folder in ['characters', 'shared/characters']) {
			try {
				var source = readText(Path.join([scopedRoot, folder, name + '.json']));
				if (source == null)
					continue;
				var data:Dynamic = haxe.Json.parse(source);
				if (data != null)
					return Reflect.field(data, 'flip_x') == true;
			} catch (_:Dynamic) {}
		}
		return null;
	}

	/** Psych applies the authored flip in the character's stage slot. */
	public static inline function flipX(authoredFlipX:Bool, isPlayer:Bool):Bool {
		return authoredFlipX != isPlayer;
	}
}
