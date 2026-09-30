package;

import NightmareVisionScriptDiscovery.NightmareVisionScriptPlan;
import NightmareVisionScriptDiscovery.NightmareVisionScriptEntry;

/** Per-play-state NMV main group. Selection is restricted to the installed
 * chart owner; foreign event/note/plugin groups have separate lifetimes. */
class NightmareVisionGameplayScripts {
	public final plan:NightmareVisionScriptPlan;
	public final group:NightmareVisionScriptGroup;
	final configure:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Dynamic->Void;
	final read:String->String;
	final report:String->String->Dynamic->Void;
	final beforeLoad:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Void;
	var attempted:Map<String, Bool> = [];

	public function new(parent:Dynamic, plan:NightmareVisionScriptPlan,
		read:String->String,
		configure:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Dynamic->Void,
		report:String->String->Dynamic->Void,
		?beforeLoad:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Void) {
		this.plan = plan;
		this.read = read;
		this.configure = configure;
		this.report = report;
		this.beforeLoad = beforeLoad;
		group = new NightmareVisionScriptGroup(parent, report);
	}

	/** A failed module is diagnosed once per state; other modules still load. */
	public function loadScope(scope:String, ?character:String, ?actor:Dynamic):Void {
		if (group.released) return;
		for (entry in plan.scripts) {
			if (entry.scope != scope || (character != null && entry.name != character)
				|| attempted.exists(entry.relative)) continue;
			attempted.set(entry.relative, true);
			try {
				var script = group.loadSource(entry.relative, read(entry.path), function(interp) {
					configure(interp, entry, null);
				}, function(interp) {
					if (beforeLoad != null) beforeLoad(interp, entry);
				});
				// NMV startCharacterScript assigns this variable only after
				// initFunkinScript has executed the module and called onLoad.
				if (script != null && actor != null) script.interp.variables.set('parent', actor);
			} catch (error:Dynamic) report(entry.relative, 'load', error);
		}
	}

	public function call(event:String, ?args:Array<Dynamic>):Dynamic
		return group.call(event, args);

	public function destroy():Void {
		if (group.released) return;
		group.call('onDestroy', [], true);
		group.destroy();
		attempted.clear();
	}
}
