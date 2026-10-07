package;

/** Keep navigation available while protecting actions without import ownership gates. */
class ImportMenuNavigationPolicy {
	public static function mainActionAllowed(importBusy:Bool, action:String):Bool
		return !importBusy || action == 'freeplay' || action == 'options';

	public static function optionsActionAllowed(importBusy:Bool, action:String):Bool {
		if (!importBusy) return true;
		return !['New Character...', 'New Stage...', 'New Song...', 'Module...',
			'newModule...', 'New Week...', 'Sort...'].contains(action);
	}
}
