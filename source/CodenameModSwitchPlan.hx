package;

#if sys
import sys.FileSystem;
#end

typedef CodenameModSwitchEntry = {
	var label:String;
	var root:String;
	var disable:Bool;
	var active:Bool;
}

typedef CodenameModSwitchPlanData = {
	var valid:Bool;
	var entries:Array<CodenameModSwitchEntry>;
	var diagnostics:Array<String>;
}

/** One selectable row per validated Codename owner, plus the native option. */
class CodenameModSwitchPlan {
	public static function initialSelection(entries:Array<CodenameModSwitchEntry>):Int {
		if (entries != null) for (index in 0...entries.length)
			if (!entries[index].disable && entries[index].active) return index;
		return 0;
	}

	public static function fromCatalog(raw:String, activeRoot:String):CodenameModSwitchPlanData {
		var launchPlan = CodenameModLaunchPlan.fromCatalog(raw);
		var catalog = CodenameModCatalog.parse(raw);
		var diagnostics = launchPlan.diagnostics.copy();
		if (!catalog.valid) diagnostics.push('[codename-mod-catalog] invalid catalog: ' + catalog.error);
		var result:CodenameModSwitchPlanData = {valid:launchPlan.valid && catalog.valid,
			entries:[], diagnostics:diagnostics};
		result.entries.push({label:'Disable Mods', root:'', disable:true, active:activeRoot == null || activeRoot == ''});
		var owners:Map<String, CodenameModSwitchEntry> = new Map();
		for (owner in catalog.data.entries) {
			#if sys
			if (owner == null || !FileSystem.isDirectory(owner.root)) continue;
			#else
			continue;
			#end
			var key = CompatScriptManifest.destinationKey(owner.root);
			if (key == '' || owners.exists(key)) continue;
			owners.set(key, {label:owner.label, root:owner.root, disable:false,
				active:CompatScriptManifest.destinationKey(activeRoot) == key});
		}
		var mods = [for (owner in owners) owner];
		mods.sort(function(a:CodenameModSwitchEntry, b:CodenameModSwitchEntry):Int {
			var order = Reflect.compare(a.label.toLowerCase(), b.label.toLowerCase());
			return order == 0 ? Reflect.compare(a.root, b.root) : order;
		});
		for (mod in mods) result.entries.push(mod);
		return result;
	}
}
