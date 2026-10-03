package;

import NightmareVisionScriptDiscovery.NightmareVisionScriptPlan;
import NightmareVisionScriptDiscovery.NightmareVisionScriptEntry;

/** Per-play-state NMV script groups. Event and note-type registries retain
 * source lookups over the same module instances also owned by the main group. */
class NightmareVisionGameplayScripts {
	public final plan:NightmareVisionScriptPlan;
	public final group:NightmareVisionScriptGroup;
	public final eventGroup:NightmareVisionScriptGroup;
	public final noteTypeGroup:NightmareVisionScriptGroup;
	final configure:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Dynamic->Void;
	final read:String->String;
	final report:String->String->Dynamic->Void;
	final beforeLoad:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Void;
	final resolveScript:String->NightmareVisionScriptEntry;
	var attempted:Map<String, Bool> = [];

	public function new(parent:Dynamic, plan:NightmareVisionScriptPlan,
		read:String->String,
		configure:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Dynamic->Void,
		report:String->String->Dynamic->Void,
		?beforeLoad:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Void,
		?resolveScript:String->NightmareVisionScriptEntry) {
		this.plan = plan;
		this.read = read;
		this.configure = configure;
		this.report = report;
		this.beforeLoad = beforeLoad;
		this.resolveScript = resolveScript;
		group = new NightmareVisionScriptGroup(parent, report);
		eventGroup = new NightmareVisionScriptGroup(parent, report);
		noteTypeGroup = new NightmareVisionScriptGroup(parent, report);
	}

	/** A failed module is diagnosed once per state; other modules still load. */
	public function loadScope(scope:String, ?character:String, ?actor:Dynamic):Void {
		if (group.released) return;
		for (entry in plan.scripts) {
			if (entry.scope != scope || (character != null && entry.name != character)
				|| attempted.exists(entry.relative)) continue;
			attempted.set(entry.relative, true);
			try {
				// Source initFunkinScript registers and initializes every script in
				// the main group first. Event and note-type registries then add that
				// same instance, rebinding shared fields only after onLoad completes.
				var scriptName = (scope == 'event' || scope == 'notetype')
					&& entry.name != null && entry.name != ''
					? entry.name : entry.relative;
				var script = group.loadSource(scriptName, read(entry.path), function(interp) {
					configure(interp, entry, null);
					bindDynamicLoader(interp);
				}, function(interp) {
					if (beforeLoad != null) beforeLoad(interp, entry);
				});
				if (script != null) {
					if (scope == 'event') eventGroup.addScript(script);
					else if (scope == 'notetype') noteTypeGroup.addScript(script);
				}
				// NMV startCharacterScript assigns this variable only after
				// initFunkinScript has executed the module and called onLoad.
				if (script != null && actor != null) script.interp.variables.set('parent', actor);
			} catch (error:Dynamic) report(entry.relative, 'load', error);
		}
	}

	/** Load chart-selected note-type modules before note creation. They remain in
	 * `group` so onCreatePost/onUpdate/onDestroy keep ordinary source broadcast
	 * order and lifetime. */
	public function loadNoteTypes(?noteType:String):Void
		loadScope('notetype', noteType);

	/** Dispatch one callback only to the selected chart note type. The registered
	 * name is the authored type (for example, "Ice Note"), matching source
	 * ScriptGroup exclusions. Null callback returns use Function_Continue. */
	public function callNoteType(noteType:String, callback:String,
		?args:Array<Dynamic>, ?receiver:Dynamic):Dynamic {
		if (group.released || noteTypeGroup.released || noteType == null || noteType == ''
			|| callback == null || callback == '')
			return NightmareVisionScriptGroup.CONTINUE_FUNC;
		loadNoteTypes(noteType);
		var script = noteTypeGroup.getScript(noteType);
		if (script == null || !script.exists(callback))
			return NightmareVisionScriptGroup.CONTINUE_FUNC;
		var result = script.call(callback, args, receiver);
		return result == null ? NightmareVisionScriptGroup.CONTINUE_FUNC : result;
	}

	function bindDynamicLoader(interp:NightmareVisionScriptInterp):Void {
		interp.variables.set('callNoteTypeScript', function(noteType:String, callback:String,
			args:Array<Dynamic>):Dynamic return callNoteType(noteType, callback, args));
		interp.variables.set('callEventScript', function(name:String, callback:String,
			args:Array<Dynamic>):Dynamic return callEvent(name, callback, args));
		// FunkinScript.initScript always loads into PlayState's main group,
		// including requests made by an event script. Registration before
		// module execution prevents recursive loads from duplicating a module.
		interp.variables.set('initScript', function(path:String):Void {
			loadDynamic(path);
		});
	}

	public function loadDynamic(path:String):NightmareVisionScriptModule {
		if (group.released || resolveScript == null) return null;
		try {
			var entry = resolveScript(path);
			if (entry == null || group.exists(entry.relative)) return null;
			return group.loadSource(entry.relative, read(entry.path), function(interp) {
				configure(interp, entry, null);
				bindDynamicLoader(interp);
			}, function(interp) {
				if (beforeLoad != null) beforeLoad(interp, entry);
			});
		} catch (error:Dynamic) {
			report(path, 'initScript', error);
			return null;
		}
	}

	/** Event scripts receive onTrigger only for their own event. */
	public function callEvent(name:String, callback:String, ?args:Array<Dynamic>):Dynamic {
		if (group.released || name == null || name == '') return NightmareVisionScriptGroup.CONTINUE_FUNC;
		var selected:NightmareVisionScriptEntry = null;
		for (entry in plan.scripts) {
			if (entry.scope == 'event' && entry.name == name) {
				selected = entry;
				break;
			}
		}
		if (selected == null) return NightmareVisionScriptGroup.CONTINUE_FUNC;

		loadScope('event', name);
		var script = eventGroup.getScript(selected.name);
		if (script == null || !script.exists(callback))
			return NightmareVisionScriptGroup.CONTINUE_FUNC;
		var result = script.call(callback, args);
		return result == null ? NightmareVisionScriptGroup.CONTINUE_FUNC : result;
	}

	public function call(event:String, ?args:Array<Dynamic>, ignoreStops:Bool = false,
		?exclusions:Array<String>):Dynamic
		return group.call(event, args, ignoreStops, exclusions);

	/** Names of loaded note-type modules for calls which broadcast a generic
	 * note event. Those modules share `group` for lifecycle callbacks, but their
	 * note callbacks must remain selected by the live note's type. */
	public function noteTypeExclusions():Array<String> {
		var result:Array<String> = [];
		for (entry in plan.scripts) {
			if (entry.scope != 'notetype' || entry.name == null || entry.name == ''
				|| !noteTypeGroup.exists(entry.name) || result.indexOf(entry.name) >= 0) continue;
			result.push(entry.name);
		}
		return result;
	}

	public function destroy():Void {
		if (group.released) return;
		// All registered modules receive onDestroy once through the main group.
		group.call('onDestroy', [], true);
		var firstError:Dynamic = null;
		var failed = false;
		// The source destroys the main registry before its event and note-type
		// registries. Those contain some of the same modules, whose release is
		// deliberately idempotent in NightmareVisionScriptModule.
		for (registry in [group, eventGroup, noteTypeGroup]) {
			try registry.destroy() catch (error:Dynamic) {
				if (!failed) { firstError = error; failed = true; }
			}
		}
		attempted.clear();
		if (failed) throw firstError;
	}
}
