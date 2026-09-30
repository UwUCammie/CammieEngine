package;

import haxe.Json;
import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

using StringTools;

typedef CodenameModLaunchEntry = {
	var root:String;
	var label:String;
	var relativePath:String;
	var stateName:String;
}

typedef CodenameModLaunchPlanData = {
	var valid:Bool;
	var entries:Array<CodenameModLaunchEntry>;
	var diagnostics:Array<String>;
}

/** Runtime projection of the destination-only Codename state catalog.
	Every visible row names a state script which still resolves below its own
	import namespace; stale or escaped paths are reported and never launched.
*/
class CodenameModLaunchPlan {
	public static function fromCatalog(raw:String):CodenameModLaunchPlanData {
		var result:CodenameModLaunchPlanData = {valid:false, entries:[], diagnostics:[]};
		var catalog = CodenameModCatalog.parse(raw);
		if (!catalog.valid) {
			result.diagnostics.push('[codename-mod-catalog] invalid catalog: ' + catalog.error);
			return result;
		}
		result.valid = true;
		#if sys
		for (owner in catalog.data.entries) {
			// Interrupted imports and manually removed owners can leave stale
			// catalog rows. Hide those rows quietly; a later importer reconciliation
			// removes only the dead catalog reference, never any owner files.
			if (owner == null || owner.root == null || !FileSystem.isDirectory(owner.root)) continue;
			for (state in owner.states) {
				var resolution = CodenameScriptDiscovery.scopedResolution(owner.root, state);
				if (resolution.relative == null) {
					result.diagnostics.push('[codename-mod-state] ' + owner.label + '/' + state + ' ' + resolution.status);
					continue;
				}
				var name = Path.withoutExtension(Path.withoutDirectory(resolution.relative));
				result.entries.push({root:owner.root, label:owner.label,
					relativePath:resolution.relative, stateName:name});
			}
		}
		// Catalog parsing intentionally drops stale state paths so consumers can
		// never launch them. Revisit only the raw state strings for diagnostics;
		// this keeps the chooser useful after an interrupted/partial refresh.
		try {
			var rawData:Dynamic = Json.parse(raw);
			var rawEntries:Dynamic = Reflect.field(rawData, 'entries');
			if (Std.isOfType(rawEntries, Array)) for (rawOwner in (cast rawEntries:Array<Dynamic>)) {
				if (rawOwner == null) continue;
				var rawRoot = Std.string(Reflect.field(rawOwner, 'root'));
				var owner = null;
				for (candidate in catalog.data.entries)
					if (CompatScriptManifest.destinationKey(candidate.root)
						== CompatScriptManifest.destinationKey(rawRoot)) { owner = candidate; break; }
				if (owner == null || !Std.isOfType(Reflect.field(rawOwner, 'states'), Array)) continue;
				#if sys
				if (!FileSystem.isDirectory(owner.root)) continue;
				#end
				for (rawState in (cast Reflect.field(rawOwner, 'states'):Array<Dynamic>)) {
					if (rawState == null) continue;
					var state = Std.string(rawState);
					if (!CodenameScriptDiscovery.safeRelativeName(state)
						|| !state.startsWith('data/states/') || !state.toLowerCase().endsWith('.hx')) {
						result.diagnostics.push('[codename-mod-state] ' + owner.label + '/' + state + ' unsafe');
						continue;
					}
					var resolution = CodenameScriptDiscovery.scopedResolution(owner.root, state);
					if (resolution.relative == null)
						result.diagnostics.push('[codename-mod-state] ' + owner.label + '/' + state + ' ' + resolution.status);
				}
			}
		} catch (_:Dynamic) {}
		#else
		if (catalog.data.entries.length > 0)
			result.diagnostics.push('[codename-mod-state] imported state scripts require a filesystem-backed runtime');
		#end
		result.entries.sort(function(a:CodenameModLaunchEntry, b:CodenameModLaunchEntry):Int {
			var ownerOrder = Reflect.compare(a.label.toLowerCase(), b.label.toLowerCase());
			if (ownerOrder != 0) return ownerOrder;
			var stateOrder = Reflect.compare(a.stateName.toLowerCase(), b.stateName.toLowerCase());
			return stateOrder == 0 ? Reflect.compare(a.relativePath, b.relativePath) : stateOrder;
		});
		return result;
	}
}
