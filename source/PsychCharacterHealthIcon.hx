package;

import haxe.io.Path;

/** Retained source character metadata supplies the logical icon identifier. */
class PsychCharacterHealthIcon {
	public static function authored(id:String, ownerRoot:String, load:String->Null<String>):Null<String> {
		if (id == null || ownerRoot == null || ownerRoot == '' || !~/^[A-Za-z0-9_-]+$/.match(id)) return null;
		for (folder in ['characters', 'shared/characters']) {
			var text = load(Path.join([ownerRoot, folder, id + '.json']));
			if (text == null) continue;
			var data:Dynamic = haxe.Json.parse(text);
			var value:Dynamic = Reflect.field(data, 'healthicon');
			return Std.isOfType(value, String) ? value : null;
		}
		return null;
	}
}
