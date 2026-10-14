package;

/** Presentation rules shared by the confirmation UI and isolated probes. */
class LibraryRemovalPresentation {
	/** Removing is the red choice and keeping is the green one, in every dialog. */
	public static inline var YES_COLOR:Int = 0xFFFF5C5C;
	public static inline var NO_COLOR:Int = 0xFF5FE08A;

	static function names(plan:Dynamic, owners:Array<String>, ?selectedOwner:String, ?displayTitle:String):Array<String> {
		var result:Array<String> = [];
		var labels:Map<String,String> = Reflect.field(plan, 'packageNames');
		for (owner in owners) {
			var label = labels == null ? null : labels.get(owner);
			if (label == null || label == '') label = owner == selectedOwner && displayTitle != null && displayTitle != '' ? displayTitle : owner.split('/').pop();
			result.push(LibraryPackageLabel.caption(owner, label));
		}
		return result;
	}
	/** Display names of the other mods a removal takes with it. */
	public static function linked(plan:Dynamic):Array<String> {
		var owners:Array<String> = plan == null ? null : Reflect.field(plan, 'linkedOwners');
		return owners == null ? [] : names(plan, owners);
	}
	public static function linkedSummary(plan:Dynamic):String {
		var list = linked(plan);
		var text = 'Linked mods cannot stay installed without it:\n' + list.join(', ');
		if (text.length > 700) text = text.substr(0, 700) + '...';
		return text + '\n' + plan.candidateFiles.length + ' managed files are removed in total.'
			+ '\nScores, favorites, categories and difficulty history are preserved.'
			+ '\nOriginal source folders are preserved.';
	}
	public static function eligible(owner:String):Bool {
		if (owner == null || BundledImportOwnership.protectedOwner(owner)) return false;
		var parts = owner.split('/');
		return parts.length == 3 && parts[0] == 'assets' && parts[1] == 'imported_mods'
			&& ~/^[a-zA-Z0-9_-]+$/.match(parts[2]);
	}
	public static function summary(plan:Dynamic, ?selectedOwner:String, ?displayTitle:String):String {
		if (plan == null) return 'Checking committed ownership and current managed files...';
		var lines = ['Installed packages: ' + names(plan, plan.affectedOwners, selectedOwner, displayTitle).join(', '),
			plan.candidateFiles.length + ' exclusive managed files to remove',
			plan.sharedFiles.length + ' shared managed files preserved',
			plan.candidateSnapshots.length + ' unneeded retained source snapshots to remove',
			plan.sharedSnapshots.length + ' shared retained snapshots preserved',
			plan.registryPaths.length + ' managed registry contributions to reconcile',
			'Scores, favorites, categories and difficulty history are preserved.',
			'Original source folders are preserved.'];
		return lines.join('\n');
	}
	public static function confirmable(phase:String, busy:Bool, plan:Dynamic):Bool {
		return phase == 'preview' && !busy && plan != null && plan.inventoryComplete == true
			&& plan.blockers != null && plan.blockers.length == 0 && plan.affectedOwners.length > 0;
	}
	public static function finished(phase:String, busy:Bool, published:Bool):Bool {
		return !busy && published && (phase == 'complete' || phase == 'cleanup-pending');
	}
}
