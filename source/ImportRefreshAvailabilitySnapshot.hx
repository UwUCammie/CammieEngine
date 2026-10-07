package;

/** One provisional song discovered by an import or retained-source refresh.
 * `name` is the source identifier/display string, not a registry storage key.
 * The opaque key is stable for this scan from its source path metadata. */
typedef ImportRefreshPendingSong = {
	var key:String;
	var name:String;
	var ownerRoot:String;
	var sourceRoot:String;
	@:optional var sourceFolder:String;
	/** Present only when the scan/converter has supplied the destination folder. */
	@:optional var destinationFolder:String;
}

/** Immutable, revisioned view of owner-scoped importer availability. */
typedef ImportRefreshAvailabilitySnapshot = {
	var revision:Int;
	var inspectionPending:Bool;
	var pendingOwnerRoots:Array<String>;
	var handoffPendingOwnerRoots:Array<String>;
	var committedOwnerRoots:Array<String>;
	var pendingTouchedPaths:Array<String>;
	var pendingSongs:Array<ImportRefreshPendingSong>;
}
