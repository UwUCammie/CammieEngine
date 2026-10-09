package;

import NightmareVisionScriptDiscovery.NightmareVisionScriptPlan;
import NightmareVisionScriptDiscovery.NightmareVisionScriptEntry;

/** State pointers stay actual typed storage; the backend follows replacements. */
typedef NightmareVisionGameplayGroupAccess = {
	var main:Void->NightmareVisionScriptGroup;
	var setMain:NightmareVisionScriptGroup->NightmareVisionScriptGroup;
	var events:Void->NightmareVisionScriptGroup;
	var setEvents:NightmareVisionScriptGroup->NightmareVisionScriptGroup;
	var notes:Void->NightmareVisionScriptGroup;
	var setNotes:NightmareVisionScriptGroup->NightmareVisionScriptGroup;
}

/** Per-play-state NMV script groups. Event and note-type registries retain
 * source lookups over the same module instances also owned by the main group. */
class NightmareVisionGameplayScripts {
	public final plan:NightmareVisionScriptPlan;
	public var group(get, set):NightmareVisionScriptGroup;
	public var eventGroup(get, set):NightmareVisionScriptGroup;
	public var noteTypeGroup(get, set):NightmareVisionScriptGroup;
	var ownGroup:NightmareVisionScriptGroup;
	var ownEvents:NightmareVisionScriptGroup;
	var ownNotes:NightmareVisionScriptGroup;
	var groupAccess:Null<NightmareVisionGameplayGroupAccess>;
	function get_group():NightmareVisionScriptGroup return groupAccess == null ? ownGroup : groupAccess.main();
	function set_group(value:NightmareVisionScriptGroup):NightmareVisionScriptGroup return groupAccess == null ? ownGroup = value : groupAccess.setMain(value);
	function get_eventGroup():NightmareVisionScriptGroup return groupAccess == null ? ownEvents : groupAccess.events();
	function set_eventGroup(value:NightmareVisionScriptGroup):NightmareVisionScriptGroup return groupAccess == null ? ownEvents = value : groupAccess.setEvents(value);
	function get_noteTypeGroup():NightmareVisionScriptGroup return groupAccess == null ? ownNotes : groupAccess.notes();
	function set_noteTypeGroup(value:NightmareVisionScriptGroup):NightmareVisionScriptGroup return groupAccess == null ? ownNotes = value : groupAccess.setNotes(value);
	final configure:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Dynamic->Void;
	final read:String->String;
	final report:String->String->Dynamic->Void;
	final beforeLoad:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Void;
	final resolveScript:String->NightmareVisionScriptEntry;
	var attempted:Map<String, Bool> = [];
	/** Historical Map identity is script-writable; module loading and lifetime stay shared. */
	public var legacyNoteRegistry:Void->Map<String, NightmareVisionScriptModule>;
	public var legacyEventRegistry:Void->Map<String, Dynamic>;

	public function new(parent:Dynamic, plan:NightmareVisionScriptPlan,
		read:String->String,
		configure:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Dynamic->Void,
		report:String->String->Dynamic->Void,
		?beforeLoad:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Void,
		?resolveScript:String->NightmareVisionScriptEntry, ?groups:NightmareVisionGameplayGroupAccess) {
		this.plan = plan;
		this.read = read;
		this.configure = configure;
		this.report = report;
		this.beforeLoad = beforeLoad;
		this.resolveScript = resolveScript;
		groupAccess = groups;
		if (groups == null) {
			ownGroup = new NightmareVisionScriptGroup(parent, report);
			ownEvents = new NightmareVisionScriptGroup(parent, report);
			ownNotes = new NightmareVisionScriptGroup(parent, report);
		}
	}

	/** Stage.fromFile executes an unregistered handle. The source filename is
	 * also its default name; injection, onLoad and registration belong to Stage. */
	public function fromStageFile(path:String, shared:Map<String, Dynamic>):NightmareVisionScriptModule {
		return fromOwnerFile(path, 'stage', shared);
	}

	/** Load an owner-validated file without automatic group/onLoad side effects. */
	public function fromOwnerFile(path:String, scope:String, shared:Map<String, Dynamic>):NightmareVisionScriptModule {
		var entry:NightmareVisionScriptEntry = {scope:scope, name:path, path:path, relative:path};
		return NightmareVisionScriptModule.fromSource(path, read(path), group.parent, shared,
			function(interp) {configure(interp, entry, null); bindDynamicLoader(interp);}, report);
	}

	/** A failed module is diagnosed once per state; other modules still load. */
	public function loadScope(scope:String, ?character:String, ?actor:Dynamic):Void {
		if (group.released) return;
		for (entry in plan.scripts) {
			if (entry.scope != scope || (character != null && entry.name != character)
				|| attempted.exists(entry.relative)) continue;
			attempted.set(entry.relative, true);
			try {
				// Modern initFunkinScript registers and initializes each script in
				// the main group first. Event and note-type registries then add that
				// same instance, rebinding shared fields only after onLoad completes.
				var scriptName = (scope == 'event' || scope == 'notetype')
					&& entry.name != null && entry.name != ''
					? entry.name : entry.relative;
				if (scope == 'event' && legacyEventRegistry != null) {
					loadHistoricalEvent(entry, scriptName);
					continue;
				}
				var script = group.loadSource(scriptName, read(entry.path), function(interp) {
					configure(interp, entry, null);
					bindDynamicLoader(interp);
				}, function(interp) {
					if (beforeLoad != null) beforeLoad(interp, entry);
				});
				if (script != null) {
					if (scope == 'event') eventGroup.addScript(script);
					else if (scope == 'notetype') {
						noteTypeGroup.addScript(script);
						if (legacyNoteRegistry != null) legacyNoteRegistry().set(entry.name, script);
					}
				}
				// NMV startCharacterScript assigns this variable only after
				// initFunkinScript has executed the module and called onLoad.
				if (script != null && actor != null) script.interp.variables.set('parent', actor);
			} catch (error:Dynamic) report(entry.relative, 'load', error);
		}
	}

	/** Historical HScript construction precedes map insertion; onLoad sees that
	 * map entry before the same module joins the main/family arrays. */
	function loadHistoricalEvent(entry:NightmareVisionScriptEntry, name:String):Void {
		var script = NightmareVisionScriptModule.fromSource(name, read(entry.path), group.parent, group.sharedFields,
			function(interp) {configure(interp, entry, null);bindDynamicLoader(interp);}, report);
		if (script.parsingFailed()) {script.destroy();return;}
		legacyEventRegistry().set(entry.name, script);
		if (beforeLoad != null) beforeLoad(script.interp, entry);
		script.callValue('onLoad', [entry.name]);
		group.addScript(script, true);
		eventGroup.addScript(script, true);
	}

	/** Load chart-selected note-type modules before note creation. They remain in
	 * `group` so onCreatePost/onUpdate/onDestroy keep ordinary source broadcast
	 * order and lifetime. */
	public function loadNoteTypes(?noteType:String):Void
		loadScope('notetype', noteType);

	/** The historical Note setter captures the current map entry without loading new scripts. */
	public function captureLegacyNoteScript(name:String):NightmareVisionScriptModule {
		var registry = legacyNoteRegistry == null ? null : legacyNoteRegistry();
		return registry == null ? null : registry.get(name);
	}

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
		var result = script.callValue(callback, args, receiver);
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

	/** Same exact selection/lazy preparation as source event dispatch. */
	function selectedEventScript(name:String):Null<NightmareVisionScriptModule> {
		if (group == null || group.released || name == null || name == '') return null;
		var selected:NightmareVisionScriptEntry = null;
		for (entry in plan.scripts) {
			if (entry.scope == 'event' && entry.name == name) {selected = entry; break;}
		}
		if (selected == null) return null;
		loadScope('event', name);
		var current = eventGroup;
		return current == null || current.released ? null : current.getScript(selected.name);
	}

	/** Presence alone cannot claim an effect: the selected live value must be callable. */
	public function hasEventCallback(name:String, callback:String):Bool {
		if (legacyEventRegistry != null) {
			var registry = legacyEventRegistry();
			return registry.exists(name) && Reflect.isFunction(NightmareVisionScriptHandle.get(registry.get(name), callback));
		}
		var script = selectedEventScript(name);
		return script != null && script.exists(callback)
			&& Reflect.isFunction(script.interp.variables.get(callback));
	}

	/** Event scripts receive onTrigger only for their own event. */
	public function callEvent(name:String, callback:String, ?args:Array<Dynamic>):Dynamic {
		if (legacyEventRegistry != null) {
			var registry = legacyEventRegistry();
			return registry.exists(name) ? NightmareVisionScriptHandle.call(registry.get(name), callback, args) : 0;
		}
		var script = selectedEventScript(name);
		if (script == null || !script.exists(callback)) return NightmareVisionScriptGroup.CONTINUE_FUNC;
		var result = script.callValue(callback, args);
		return result == null ? NightmareVisionScriptGroup.CONTINUE_FUNC : result;
	}

	public function call(event:String, ?args:Array<Dynamic>, ignoreStops:Bool = false,
		?exclusions:Array<String>):Dynamic
		return group.call(event, args, ignoreStops, exclusions);

	/** Historical global notifications exclude every live type/event registry name. */
	public function callHistorical(event:String, args:Array<Dynamic>, ignoreStops:Bool = false):Dynamic {
		return group.callFiltered(event, args, ignoreStops, null, true, function(script) {
			var registry = legacyNoteRegistry == null ? null : legacyNoteRegistry();
			return (registry != null && registry.exists(script.name))
				|| (legacyEventRegistry != null ? legacyEventRegistry().exists(script.name) : eventGroup != null && eventGroup.exists(script.name));
		});
	}


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
