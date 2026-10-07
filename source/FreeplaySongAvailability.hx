package;

import ImportRefreshAvailabilitySnapshot.ImportRefreshAvailabilitySnapshot;
import ImportRefreshAvailabilitySnapshot.ImportRefreshPendingSong;

typedef FreeplayAvailabilityDecision = {
	var ready:Bool;
	var state:String;
	var reason:String;
}

/** Pure owner and chart gate shared by Freeplay rows and imported-package entry points. */
class FreeplaySongAvailability {
	/** A static song list can outlive the FreeplayState which selected it. When
	 * the importer publishes a new generation in another safe menu, a later
	 * FreeplayState must rebuild that list from the current registry. */
	public static function songListNeedsRegistryRefresh(hasDirectOwner:Bool,
		entryCount:Int, listGeneration:Int, managerGeneration:Int):Bool {
		return hasDirectOwner || entryCount <= 0 || listGeneration != managerGeneration;
	}

	/** Provisional scan rows belong in the unscoped master lists and the native
	 * Imported category, while explicit package Freeplay remains owner-scoped. */
	public static function canPresentPendingSongs(category:String, hasDirectOwner:Bool):Bool {
		if (hasDirectOwner)
			return true;
		var normalized = category == null ? '' : StringTools.trim(category).toLowerCase();
		return normalized == '' || normalized == 'all' || normalized == 'imported';
	}

	public static function ownerReadiness(snapshot:ImportRefreshAvailabilitySnapshot,
		ownerRoot:String):FreeplayAvailabilityDecision {
		var owner = normalizePath(ownerRoot);
		if (owner == '')
			return {ready:true, state:'ready', reason:''};
		if (containsRoot(snapshot == null ? null : snapshot.handoffPendingOwnerRoots, owner))
			return {ready:false, state:'handoff', reason:'Waiting for this package to finish loading.'};
		if (containsRoot(snapshot == null ? null : snapshot.pendingOwnerRoots, owner))
			return {ready:false, state:'pending', reason:'Import, dependency refresh, or recovery is still working on this package.'};
		if (containsRoot(snapshot == null ? null : snapshot.committedOwnerRoots, owner))
			return {ready:true, state:'ready', reason:''};
		if (snapshot != null && snapshot.inspectionPending)
			return {ready:false, state:'checking', reason:'Checking whether this imported package is ready.'};
		// Imports without retained-manager receipts use the established provenance
		// and chart checks. They are stable once initial receipt inspection ends.
		return {ready:true, state:'unmanaged', reason:''};
	}

	/** Combine package publication state with one actual chart check and exact
	 * transaction-output overlap for the song's data directory. */
	public static function songReadiness(snapshot:ImportRefreshAvailabilitySnapshot,
		ownerRoot:String, chartExists:Bool, ?dataFolder:String,
		?provisional:Bool = false):FreeplayAvailabilityDecision {
		if (provisional)
			return {ready:false, state:'provisional', reason:'Importing. This song is unavailable until the package is committed.'};
		var owner = ownerReadiness(snapshot, ownerRoot);
		if (!owner.ready)
			return owner;
		if (dataFolder != null && dataFolder != '' && touchesPath(snapshot, dataFolder))
			return {ready:false, state:'overlap', reason:'A pending import is updating this song or its chart files.'};
		if (!chartExists)
			return {ready:false, state:'missing-chart', reason:'No supported chart is available for this song.'};
		return {ready:true, state:'ready', reason:''};
	}

	/** Short row text fits the existing Freeplay subtitle lane. */
	public static function rowAvailabilityReason(decision:FreeplayAvailabilityDecision):String {
		if (decision == null || decision.ready)
			return '';
		return switch (decision.state) {
			case 'provisional': 'Importing, unavailable until committed';
			case 'handoff': 'Unavailable, loading imported package';
			case 'pending': 'Unavailable, import or dependency work pending';
			case 'checking': 'Unavailable, checking package status';
			case 'overlap': 'Unavailable, chart update in progress';
			case 'missing-chart': 'Unavailable, no supported chart';
			default: 'Unavailable, import status unresolved';
		};
	}

	public static function rowIsDisabled(decision:FreeplayAvailabilityDecision):Bool
		return decision == null || !decision.ready;

	/** True when a pending transaction writes a file inside or equal to a known
	 * song data directory. The manager supplies normalized relative paths. */
	public static function touchesPath(snapshot:ImportRefreshAvailabilitySnapshot,
		scopePath:String):Bool {
		var scope = normalizePath(scopePath);
		if (scope == '' || snapshot == null || snapshot.pendingTouchedPaths == null)
			return false;
		for (path in snapshot.pendingTouchedPaths) {
			var touched = normalizePath(path);
			if (touched == scope || StringTools.startsWith(touched, scope + '/'))
				return true;
		}
		return false;
	}

	/** Authoritative destination metadata may be used to replace an existing
	 * row with a provisional one only when the owner also matches. */
	public static function matchesInstalledDestination(candidate:ImportRefreshPendingSong,
		installedOwnerRoot:String, installedSongName:String):Bool {
		if (candidate == null || candidate.destinationFolder == null
			|| StringTools.trim(candidate.destinationFolder) == '')
			return false;
		if (normalizePath(candidate.ownerRoot) != normalizePath(installedOwnerRoot))
			return false;
		return samePathComponent(candidate.destinationFolder, installedSongName);
	}

	/** Source-folder matching is also safe only within the exact owner. */
	public static function matchesInstalledSource(candidate:ImportRefreshPendingSong,
		installedOwnerRoot:String, installedSourceFolder:String):Bool {
		if (candidate == null || candidate.sourceFolder == null
			|| StringTools.trim(candidate.sourceFolder) == '' || installedSourceFolder == null
			|| StringTools.trim(installedSourceFolder) == '')
			return false;
		return normalizePath(candidate.ownerRoot) == normalizePath(installedOwnerRoot)
			&& samePathComponent(candidate.sourceFolder, installedSourceFolder);
	}

	public static function samePathComponent(left:String, right:String):Bool {
		if (left == null || right == null)
			return false;
		return normalizePath(left) == normalizePath(right);
	}

	public static function normalizePath(value:String):String {
		if (value == null)
			return '';
		var path = StringTools.replace(StringTools.trim(value), '\\', '/');
		while (path.indexOf('//') >= 0)
			path = StringTools.replace(path, '//', '/');
		while (path.length > 0 && path.charAt(path.length - 1) == '/')
			path = path.substr(0, path.length - 1);
		#if windows
		path = path.toLowerCase();
		#end
		return path;
	}

	static function containsRoot(roots:Array<String>, normalizedOwner:String):Bool {
		if (roots == null)
			return false;
		for (root in roots)
			if (normalizePath(root) == normalizedOwner)
				return true;
		return false;
	}
}
