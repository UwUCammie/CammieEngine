package;

/** Keep navigation available while protecting actions without import ownership gates.
	The Import entry stays reachable during work so its screen can show the running job. */
class ImportMenuNavigationPolicy {
	public static function mainActionAllowed(importBusy:Bool, action:String):Bool
		return !importBusy || action == 'freeplay' || action == 'options' || action == 'import';

	public static function optionsActionAllowed(importBusy:Bool, action:String):Bool {
		if (!importBusy) return true;
		return !['New Character...', 'New Stage...', 'New Song...', 'Module...',
			'newModule...', 'New Week...', 'Sort...'].contains(action);
	}
}
