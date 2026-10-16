package;

import MenuStyle.MenuHint;

/** The key hints each Freeplay-style screen shows in its footer, kept apart
 * from the display objects so they can be checked against the footer's room. */
class MenuHints {
	/** The options screen, by what it is doing: choosing a save slot, working
	 * through one, picking a section, or changing a setting. */
	public static function options(inOptions:Bool, inSection:Bool, slotOpen:Bool, slotConfirm:Bool,
		canEdit:Bool, useSaves:Bool):Array<MenuHint> {
		if (!inOptions) {
			if (slotConfirm)
				return [{key: 'ACCEPT', action: 'Erase'}, {key: 'BACK', action: 'Keep'}];
			if (slotOpen)
				return [{key: 'LEFT/RIGHT', action: 'Load or delete'}, {key: 'ACCEPT', action: 'Confirm'}, {key: 'BACK', action: 'Close'}];
			var saves:Array<MenuHint> = [{key: 'UP/DOWN', action: 'Choose'}, {key: 'ACCEPT', action: 'Open'}];
			if (canEdit)
				saves.push({key: 'LEFT/RIGHT', action: 'Options'});
			saves.push({key: 'BACK', action: 'Return'});
			return saves;
		}
		if (inSection)
			return [{key: 'UP/DOWN', action: 'Choose'}, {key: 'LEFT/RIGHT', action: 'Change'}, {key: 'ENTER', action: 'Toggle'},
				{key: 'CTRL', action: 'Hold to scroll fast'}, {key: 'BACK', action: 'Sections'}];
		var sections:Array<MenuHint> = [{key: 'UP/DOWN', action: 'Choose section'}, {key: 'ENTER', action: 'Open'}];
		if (useSaves)
			sections.push({key: 'LEFT/RIGHT', action: 'Saves'});
		sections.push({key: 'BACK', action: 'Return'});
		return sections;
	}

	public static function importer():Array<MenuHint> return [
		{key: 'UP/DOWN', action: 'Action'},
		{key: 'LEFT/RIGHT', action: 'Importer'},
		{key: 'ENTER', action: 'Run'},
		{key: 'PAGE UP/DOWN', action: 'Details'},
		{key: 'MOUSE', action: 'Click'},
		{key: 'BACK', action: 'Return'},
	];

	public static function mainMenu():Array<MenuHint> return [
		{key: 'UP/DOWN', action: 'Choose'},
		{key: 'ENTER', action: 'Open'},
		{key: 'I', action: 'Imported mods'},
		{key: 'BACK', action: 'Title'},
	];
}
