package;

import haxe.ds.ObjectMap;

private typedef NightmareVisionNoteApiState = {
	var prefix:String;
	var suffix:String;
	var texture:String;
	var atlasPath:String;
	var rgbEnabled:Bool;
	var customColors:Array<Dynamic>;
	var canMiss:Bool;
}

/**
	Runtime adapter for the source note-type lifecycle. The selected script stays
	in NightmareVisionGameplayScripts' main group; these targeted calls only run
	the script whose registered name matches the live note's authored type.
*/
class NightmareVisionNoteTypeRuntime {
	public final scripts:NightmareVisionGameplayScripts;
	public final api:NightmareVisionNoteApiBridge;

	public function new(scripts:NightmareVisionGameplayScripts,
		?api:NightmareVisionNoteApiBridge) {
		this.scripts = scripts;
		this.api = api == null ? new NightmareVisionNoteApiBridge() : api;
	}

	/** NoteType files must be loaded before generation so top-level state and
	 * onCreatePost are ready before notes are recycled or spawned. */
	public function loadBeforeNoteGeneration():Void {
		if (scripts != null) scripts.loadNoteTypes();
	}

	public static function noteTypeOf(note:Dynamic):String {
		if (note == null) return '';
		var value:Dynamic = null;
		try value = Reflect.getProperty(note, 'noteType') catch (_:Dynamic) {}
		if (value == null || Std.string(value) == '') {
			try value = Reflect.getProperty(note, 'sourceKind') catch (_:Dynamic) {}
		}
		return value == null ? '' : Std.string(value);
	}

	function call(note:Dynamic, callback:String, args:Array<Dynamic>, ?receiver:Dynamic):Dynamic {
		if (scripts == null) return NightmareVisionScriptGroup.CONTINUE_FUNC;
		return scripts.callNoteType(noteTypeOf(note), callback, args, receiver);
	}

	/** Called after the default/chart note skin is configured but before the
	 * source onSpawnNote gate and before the note enters the live note group. */
	public function setupNote(note:Dynamic):Dynamic {
		api.attach(note);
		var result = call(note, 'setupNote', [note], note);
		api.syncNote(note);
		return result;
	}

	/** Reset sidecar values when a pooled native Note begins a fresh recycle.
	 * Call after its chart-skin defaults are established and before note-type
	 * behavior applies custom colors, flags, or a texture prefix. */
	public function resetNote(note:Dynamic, rgbEnabled:Bool, canMiss:Bool = false):Void
		api.resetNote(note, rgbEnabled, canMiss);

	/** Source calls this type-local gate after setupNote and before PlayField
	 * insertion. STOP cancels this spawn in the caller. */
	public function spawnNote(note:Dynamic):Dynamic {
		var result = call(note, 'spawnNote', [note]);
		api.syncNote(note);
		return result;
	}

	/** Called after insertion into the active note group, matching source
	 * postSpawnNote ordering. */
	public function postSpawnNote(note:Dynamic):Dynamic {
		var result = call(note, 'postSpawnNote', [note]);
		api.syncNote(note);
		return result;
	}

	/** PlayField.noteHit sends the type-wide hit callback before the selected
	 * player/opponent callback, both with the source [note, fieldID] arguments. */
	public function hit(note:Dynamic, fieldID:Int):Dynamic {
		var result = call(note, 'hit', [note, fieldID]);
		api.syncNote(note);
		return result;
	}

	public function goodNoteHit(note:Dynamic, fieldID:Int):Dynamic {
		var result = call(note, 'goodNoteHit', [note, fieldID]);
		api.syncNote(note);
		return result;
	}

	public function opponentNoteHit(note:Dynamic, fieldID:Int):Dynamic {
		var result = call(note, 'opponentNoteHit', [note, fieldID]);
		api.syncNote(note);
		return result;
	}

	public function extraNoteHit(note:Dynamic, fieldID:Int):Dynamic {
		var result = call(note, 'extraNoteHit', [note, fieldID]);
		api.syncNote(note);
		return result;
	}

	/** Source calls this after the native miss health/animation effects. */
	public function noteMiss(note:Dynamic, fieldID:Int):Dynamic {
		var result = call(note, 'noteMiss', [note, fieldID]);
		api.syncNote(note);
		return result;
	}

	/** Note.update invokes a note-type update function with the live Note as
	 * callback receiver, unlike the state-level onUpdate broadcast. */
	public function update(note:Dynamic, elapsed:Float):Dynamic {
		var result = call(note, 'update', [note, elapsed], note);
		api.syncNote(note);
		return result;
	}

	/** Source Note.reloadNote gives type scripts a cancellable pre-hook and a
	 * post-hook around the owner-scoped atlas reload. */
	public function reloadNote(note:Dynamic, prefix:String = '', texture:String = '',
		suffix:String = ''):Bool {
		if (prefix == null) prefix = '';
		if (texture == null) texture = '';
		if (suffix == null) suffix = '';
		// The source saves prefix/suffix before dispatching onReloadNote, so the
		// callback can inspect the updated values and STOP does not roll them back.
		api.rememberPrefixSuffix(note, prefix, suffix);
		var args:Array<Dynamic> = [note, prefix, texture, suffix];
		if (call(note, 'onReloadNote', args, note) == NightmareVisionScriptGroup.STOP_FUNC)
			return false;
		var loaded = api.reloadNote(note, prefix, texture, suffix);
		if (loaded) {
			call(note, 'postReloadNote', args, note);
			api.syncNote(note);
		}
		return loaded;
	}

	/** The parent must use this on note expiry and bot-hit paths. canMiss is a
	 * separate source flag: it suppresses automatic miss bookkeeping and
	 * botplay auto-hit, while leaving manual hit dispatch available. */
	public function canMiss(note:Dynamic):Bool return api.canMiss(note);

	/** Sync dynamic type-script writes such as rgbEnabled after a global update
	 * broadcast. A Note field setter can also call api.setRgbEnabled directly. */
	public function syncNote(note:Dynamic):Void api.syncNote(note);

	public function syncNotes(notes:Array<Dynamic>):Void {
		if (notes == null) return;
		for (note in notes) if (note != null) api.syncNote(note);
	}

	/** Release sidecar state when the native pooled Note is destroyed/recycled. */
	public function releaseNote(note:Dynamic):Void api.releaseNote(note);

	public function destroy():Void api.clear();
}

/**
	State and operations behind source Note's direct properties/methods. The
	engine Note class can delegate its rgbEnabled/canMiss accessors and
	reloadNote/setCustomColor methods here without coupling script dispatch to
	Flixel. The atlas callback must resolve through the selected owner's Paths,
	install its frames/animations, and refresh note geometry.
*/
class NightmareVisionNoteApiBridge {
	final states:ObjectMap<Dynamic, NightmareVisionNoteApiState> = new ObjectMap();
	final defaultTexture:Dynamic->String;
	final loadAtlas:Dynamic->String->Bool;
	final readInitialRgb:Dynamic->Bool;
	final applyRgb:Dynamic->Bool->Void;
	final applyColors:Dynamic->Array<Dynamic>->Void;

	public function new(?defaultTexture:Dynamic->String,
		?loadAtlas:Dynamic->String->Bool,
		?applyRgb:Dynamic->Bool->Void,
		?applyColors:Dynamic->Array<Dynamic>->Void,
		?readInitialRgb:Dynamic->Bool) {
		this.defaultTexture = defaultTexture;
		this.loadAtlas = loadAtlas;
		this.applyRgb = applyRgb;
		this.applyColors = applyColors;
		this.readInitialRgb = readInitialRgb;
	}

	public function attach(note:Dynamic):Void {
		if (note != null) stateFor(note, true);
	}

	public function resetNote(note:Dynamic, rgbEnabled:Bool, canMiss:Bool = false):Void {
		var state = stateFor(note, true);
		if (state == null) return;
		state.prefix = '';
		state.suffix = '';
		state.texture = '';
		state.atlasPath = '';
		state.rgbEnabled = rgbEnabled;
		state.customColors = null;
		state.canMiss = canMiss;
		if (applyColors != null) applyColors(note, null);
		if (applyRgb != null) applyRgb(note, rgbEnabled);
	}

	public function prefix(note:Dynamic):String {
		var state = stateFor(note, false);
		return state == null ? '' : state.prefix;
	}

	public function suffix(note:Dynamic):String {
		var state = stateFor(note, false);
		return state == null ? '' : state.suffix;
	}

	/** Mirrors the source reloadNote prefix mutation that precedes its veto hook. */
	public function rememberPrefixSuffix(note:Dynamic, prefix:String, suffix:String):Void {
		var state = stateFor(note, true);
		if (state == null) return;
		if (prefix != null && prefix.length > 0) state.prefix = prefix;
		if (suffix != null && suffix.length > 0) state.suffix = suffix;
	}

	function stateFor(note:Dynamic, create:Bool):Null<NightmareVisionNoteApiState> {
		if (note == null) return null;
		var state = states.get(note);
		if (state == null && create) {
			var rgb = true;
			if (readInitialRgb != null)
				try rgb = readInitialRgb(note) catch (_:Dynamic) {}
			state = {prefix:'', suffix:'', texture:'', atlasPath:'',
				rgbEnabled:rgb, customColors:null, canMiss:false};
			states.set(note, state);
		}
		return state;
	}

	public function getRgbEnabled(note:Dynamic):Bool {
		var state = stateFor(note, true);
		return state == null ? true : state.rgbEnabled;
	}

	public function setRgbEnabled(note:Dynamic, value:Bool):Bool {
		var state = stateFor(note, true);
		if (state == null) return value;
		state.rgbEnabled = value;
		if (applyRgb != null) applyRgb(note, value);
		return value;
	}

	public function setCustomColor(note:Dynamic, colors:Array<Dynamic>):Void {
		var state = stateFor(note, true);
		if (state == null) return;
		state.customColors = colors == null ? null : colors.copy();
		if (applyColors != null) applyColors(note,
			state.customColors == null ? null : state.customColors.copy());
	}

	public function customColors(note:Dynamic):Array<Dynamic> {
		var state = stateFor(note, false);
		return state == null || state.customColors == null ? null : state.customColors.copy();
	}

	public function setCanMiss(note:Dynamic, value:Bool):Bool {
		var state = stateFor(note, true);
		if (state != null) state.canMiss = value;
		return value;
	}

	public function canMiss(note:Dynamic):Bool {
		var state = stateFor(note, false);
		return state != null && state.canMiss;
	}

	/** Reproduce the donor prefix/suffix insertion rule and delegate actual
	 * texture loading to the selected-owner host adapter. */
	public function reloadNote(note:Dynamic, prefix:String = '', texture:String = '',
		suffix:String = ''):Bool {
		var state = stateFor(note, true);
		if (state == null) return false;
		rememberPrefixSuffix(note, prefix, suffix);
		var base = texture == null ? '' : texture;
		if (base == '') {
			base = defaultTexture == null ? '' : defaultTexture(note);
			if (base == null || StringTools.trim(base) == '') base = 'NOTE_assets';
		} else {
			state.texture = base;
		}
		var parts = base.split('/');
		if (parts.length == 0) return false;
		var last = parts.length - 1;
		parts[last] = state.prefix + parts[last] + state.suffix;
		var atlasPath = parts.join('/');
		state.atlasPath = atlasPath;
		return loadAtlas != null && loadAtlas(note, atlasPath);
	}

	public function atlasPath(note:Dynamic):String {
		var state = stateFor(note, false);
		return state == null ? '' : state.atlasPath;
	}

	/** Reapply script-visible palette and shader enable state after lifecycle or
	 * update callbacks. Parent closures should mutate the native shader directly
	 * to avoid recursing through Note's script-facing property. */
	public function syncNote(note:Dynamic):Void {
		var state = stateFor(note, false);
		if (state == null) return;
		if (state.customColors != null && applyColors != null)
			applyColors(note, state.customColors.copy());
		if (applyRgb != null) applyRgb(note, state.rgbEnabled);
	}

	public function releaseNote(note:Dynamic):Void {
		if (note != null) states.remove(note);
	}

	public function clear():Void {
		states.clear();
	}
}
