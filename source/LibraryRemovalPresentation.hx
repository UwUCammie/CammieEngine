package;

/** Presentation rules shared by the confirmation UI and isolated probes. */
class LibraryRemovalPresentation {
	public static function eligible(owner:String):Bool {
		if (owner == null || BundledImportOwnership.protectedOwner(owner)) return false;
		var parts = owner.split('/');
		return parts.length == 3 && parts[0] == 'assets' && parts[1] == 'imported_mods'
			&& ~/^[a-zA-Z0-9_-]+$/.match(parts[2]);
	}
	public static function summary(plan:Dynamic, ?selectedOwner:String, ?displayTitle:String):String {
		if (plan == null) return 'Checking committed ownership and current managed files...';
		var owners:Array<String> = plan.affectedOwners;
		var names:Array<String> = [];
		var labels:Map<String,String> = Reflect.field(plan, 'packageNames');
		for (owner in owners) {
			var label = labels == null ? null : labels.get(owner);
			if (label == null || label == '') label = owner == selectedOwner && displayTitle != null && displayTitle != '' ? displayTitle : owner.split('/').pop();
			names.push(LibraryPackageLabel.caption(owner, label));
		}
		var lines = ['Installed packages: ' + names.join(', '),
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
