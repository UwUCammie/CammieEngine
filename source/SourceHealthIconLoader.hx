package;

/** Exact source fallback decisions, always resolved by the selected owner. */
class SourceHealthIconLoader {
	public static function psychPath(character:String, owner:SourceHealthIconOwner):String {
		var name = 'icons/' + character;
		if (!owner.exists('images/' + name + '.png')) name = 'icons/icon-' + character;
		if (!owner.exists('images/' + name + '.png')) name = 'icons/icon-face';
		return name;
	}

	public static function nightmarePath(character:String, owner:SourceHealthIconOwner):String {
		var name = owner.uiPrefix() + 'icons/' + character;
		if (!owner.exists('images/' + name + '.png')) name = owner.uiPrefix() + 'icons/icon-' + character;
		if (!owner.exists('images/' + name + '.png')) name = owner.uiPrefix() + 'icons/icon-face';
		if (!owner.exists('images/' + name + '.png')) name = 'UI/icons/icon-face';
		return name;
	}
}
