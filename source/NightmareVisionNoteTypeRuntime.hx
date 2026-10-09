package;

import haxe.ds.ObjectMap;

private typedef NightmareVisionNoteApiState = {
	var prefix:String;
	var suffix:String;
	var scriptTexture:String;
	var fieldTexture:String;
	var atlasPath:String;
	var rgbEnabled:Bool;
	var customColors:Array<Dynamic>;
	var canMiss:Bool;
}

/**
	Runtime adapter for the source note-type lifecycle. Modern callbacks select
	the live registered type; historical callbacks use the note's captured script.
	Both reuse the shared module loader, interpreter and main-group lifetime.
*/
class NightmareVisionNoteTypeRuntime {
	public final scripts:NightmareVisionGameplayScripts;
	public var legacyNoteScripts:Bool = false;
	public final api:NightmareVisionNoteApiBridge;
	public var prepareLegacyColors:(Dynamic, Bool)->Int;
	public var finishLegacyColors:Dynamic->Void;

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
		if (legacyNoteScripts) {
			var script = attachedScript(note);
			if (script == null || !script.exists(callback)) return NightmareVisionScriptGroup.CONTINUE_FUNC;
			var result = script.callValue(callback, args, receiver);
			return result == null ? NightmareVisionScriptGroup.CONTINUE_FUNC : result;
		}
		return scripts.callNoteType(noteTypeOf(note), callback, args, receiver);
	}

	function attachedScript(note:Dynamic):NightmareVisionScriptModule {
		var script:Dynamic = note == null ? null : Reflect.getProperty(note, 'noteScript');
		if (script != null && !Std.isOfType(script, NightmareVisionScriptModule))
			throw '[nightmare-vision-note] Unsupported attached noteScript implementation';
		return cast script;
	}

	/** Called after the default/chart note skin is configured but before the
	 * source onSpawnNote gate and before the note enters the live note group. */
	public function setupNote(note:Dynamic, force:Bool = false):Dynamic {
		api.attach(note);
		var mode = prepareLegacyColors == null ? 1 : prepareLegacyColors(note, force);
		return finishSetup(note, noteTypeOf(note), mode);
	}

	/** Keep the requested type separate from the value callbacks can currently read. */
	public function assignLegacyType(note:Dynamic, value:String, mode:Int, commit:Void->Void):Dynamic {
		api.attach(note);
		return finishSetup(note, value, mode, commit);
	}

	function finishSetup(note:Dynamic, type:String, mode:Int, ?commit:Void->Void):Dynamic {
		if (mode == 0) return NightmareVisionScriptGroup.CONTINUE_FUNC;
		if (legacyNoteScripts) Reflect.setProperty(note, 'noteScript',
			mode == 1 && scripts != null ? scripts.captureLegacyNoteScript(type) : null);
		var result = mode == 2 ? NightmareVisionScriptGroup.CONTINUE_FUNC : call(note, 'setupNote', [note], note);
		if (commit != null) commit();
		if (finishLegacyColors != null) finishLegacyColors(note);
		api.syncNote(note);
		return result;
	}

	/** Reset sidecar values when a pooled native Note begins a fresh recycle.
	 * Call after its chart-skin defaults are established and before note-type
	 * behavior applies custom colors, flags, or a texture prefix. */
	public function resetNote(note:Dynamic, rgbEnabled:Bool, canMiss:Bool = false):Void {
		if (legacyNoteScripts) Reflect.setProperty(note, 'noteScript', null);
		api.resetNote(note, rgbEnabled, canMiss);
		var reset = Reflect.field(note, 'resetSourceRatingState');
		if (reset != null) Reflect.callMethod(note, reset, []);
	}

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

	/** Historical hit/miss notifications never use a returned value to cancel another family. */
	public function legacyHit(note:Dynamic, callback:String, groupSlot:Int,
		lua:(String, Array<Dynamic>)->Dynamic, hscript:(String, Array<Dynamic>)->Dynamic):Void {
		var direction:Dynamic = Reflect.getProperty(note, 'noteData');
		var luaArgs:Array<Dynamic> = [groupSlot, callback == 'noteMiss' ? direction : Math.abs(direction),
			noteTypeOf(note), Reflect.getProperty(note, 'isSustainNote'), Reflect.getProperty(note, 'ID')];
		var hscriptArgs:Array<Dynamic> = [note];
		lua(callback, luaArgs);
		hscript(callback, hscriptArgs);
		// A global callback may replace or clear the attachment before this phase.
		call(note, callback, hscriptArgs);
		api.syncNote(note);
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

	/** Historical animation overrides replace the default and may call it through super. */
	public function loadLegacyAnimations(note:Dynamic, pixel:Bool, fallback:Void->Void):Void {
		var script = legacyNoteScripts ? attachedScript(note)
			: scripts == null || scripts.group.released || scripts.noteTypeGroup.released
				? null : scripts.noteTypeGroup.getScript(noteTypeOf(note));
		NightmareVisionLegacyNoteAnimations.dispatch(script, note, pixel, fallback);
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
			if (texture != '') api.rememberScriptTexture(note, texture);
			call(note, 'postReloadNote', args, note);
			api.syncNote(note);
		}
		return loaded;
	}

	/** Mirror source PlayField.addNote's texture assignment. Reloading through
	 * this runtime preserves each note type's prefix and callback lifecycle. */
	public function reloadForFieldSkin(note:Dynamic, texture:String, rgbEnabled:Bool,
		forceReload:Bool = false):Bool {
		if (note == null || texture == null) return false;
		var changed = api.fieldTexture(note) != texture;
		var result = true;
		if (changed) {
			result = reloadFieldSkin(note, texture);
			api.rememberFieldTexture(note, texture);
		}
		// PlayField assigns the field's RGB mode after the texture setter returns.
		// On a skin change this deliberately falls between the source setter's
		// reload and its explicit second reload.
		api.setRgbEnabled(note, rgbEnabled);
		// Source PlayField.changeSkin explicitly reloads again after assigning
		// Note.texture and refreshing the skin animation table.
		if (forceReload) result = reloadFieldSkin(note, texture);
		return result;
	}

	function reloadFieldSkin(note:Dynamic, texture:String):Bool {
		var args:Array<Dynamic> = [note, '', texture, ''];
		if (call(note, 'onReloadNote', args, note) == NightmareVisionScriptGroup.STOP_FUNC)
			return false;
		var loaded = api.reloadForFieldSkin(note, texture);
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
	public function releaseNote(note:Dynamic):Void {
		if (legacyNoteScripts) Reflect.setProperty(note, 'noteScript', null);
		api.releaseNote(note);
	}

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
	final atlasAvailable:Null<String->Bool>;
	final reportAtlasFailure:Null<Dynamic->String->Void>;

	public function new(?defaultTexture:Dynamic->String,
		?loadAtlas:Dynamic->String->Bool,
		?applyRgb:Dynamic->Bool->Void,
		?applyColors:Dynamic->Array<Dynamic>->Void,
		?readInitialRgb:Dynamic->Bool,
		?atlasAvailable:String->Bool,
		?reportAtlasFailure:Dynamic->String->Void) {
		this.defaultTexture = defaultTexture;
		this.loadAtlas = loadAtlas;
		this.applyRgb = applyRgb;
		this.applyColors = applyColors;
		this.readInitialRgb = readInitialRgb;
		this.atlasAvailable = atlasAvailable;
		this.reportAtlasFailure = reportAtlasFailure;
	}

	public function attach(note:Dynamic):Void {
		if (note != null) stateFor(note, true);
	}

	public function resetNote(note:Dynamic, rgbEnabled:Bool, canMiss:Bool = false):Void {
		var state = stateFor(note, true);
		if (state == null) return;
		state.prefix = '';
		state.suffix = '';
		state.scriptTexture = '';
		state.fieldTexture = '';
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
			state = {prefix:'', suffix:'', scriptTexture:'', atlasPath:'',
				fieldTexture:'',
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
		}
		var parts = base.split('/');
		if (parts.length == 0) return false;
		var last = parts.length - 1;
		parts[last] = state.prefix + parts[last] + state.suffix;
		var atlasPath = parts.join('/');
		state.atlasPath = atlasPath;
		return loadAtlas != null && loadAtlas(note, atlasPath);
	}

	/** Field skin reloads keep script-authored texture overrides separate from
	 * the changing field texture. Missing atlases fall back only within the
	 * same composed field directory. */
	public function reloadForFieldSkin(note:Dynamic, texture:String):Bool {
		var state = stateFor(note, true);
		if (state == null) return false;
		var selectedTexture = texture == null ? '' : texture;
		if (StringTools.trim(selectedTexture) == '') {
			selectedTexture = defaultTexture == null ? '' : defaultTexture(note);
			if (selectedTexture == null || StringTools.trim(selectedTexture) == '')
				selectedTexture = 'NOTE_assets';
		}

		var candidates:Array<String> = [];
		appendCandidate(candidates, composeAtlas(selectedTexture, state.prefix, state.suffix));
		if (state.scriptTexture != null && state.scriptTexture != '')
			appendCandidate(candidates, composeAtlas(state.scriptTexture, state.prefix, state.suffix));
		appendCandidate(candidates, composeAtlas(conventionalTexture(selectedTexture), state.prefix, state.suffix));

		var selected:String = null;
		for (candidate in candidates) {
			if (atlasAvailable == null || atlasAvailable(candidate)) {
				selected = candidate;
				break;
			}
		}
		if (selected == null) {
			var message = 'No owner PNG and XML atlas found for field texture '
				+ selectedTexture + ' or its explicit/conventional fallbacks: '
				+ candidates.join(', ');
			if (reportAtlasFailure != null) reportAtlasFailure(note, message);
			else trace('[nightmare-vision-note-atlas] ' + message);
			return false;
		}
		state.atlasPath = selected;
		if (loadAtlas == null || !loadAtlas(note, selected)) {
			var message = 'Owner atlas could not be loaded after PNG/XML validation: ' + selected;
			if (reportAtlasFailure != null) reportAtlasFailure(note, message);
			else trace('[nightmare-vision-note-atlas] ' + message);
			return false;
		}
		return true;
	}

	public function rememberScriptTexture(note:Dynamic, texture:String):Void {
		var state = stateFor(note, true);
		if (state != null && texture != null && texture != '') state.scriptTexture = texture;
	}

	public function scriptTexture(note:Dynamic):String {
		var state = stateFor(note, false);
		return state == null ? '' : state.scriptTexture;
	}

	static function composeAtlas(base:String, prefix:String, suffix:String):String {
		if (base == null) base = '';
		if (prefix == null) prefix = '';
		if (suffix == null) suffix = '';
		var parts = base.split('/');
		if (parts.length == 0) return '';
		var last = parts.length - 1;
		parts[last] = prefix + parts[last] + suffix;
		return parts.join('/');
	}

	static function conventionalTexture(base:String):String {
		if (base == null || base == '') return 'NOTE_assets';
		var parts = base.split('/');
		if (parts.length == 0) return 'NOTE_assets';
		parts[parts.length - 1] = 'NOTE_assets';
		return parts.join('/');
	}

	static function appendCandidate(candidates:Array<String>, value:String):Void {
		if (value != null && value != '' && candidates.indexOf(value) < 0) candidates.push(value);
	}

	/** Last texture assigned by the owning field, separate from texture values
	 * passed directly to a note-type reloadNote call. */
	public function fieldTexture(note:Dynamic):String {
		var state = stateFor(note, false);
		return state == null ? '' : state.fieldTexture;
	}

	public function rememberFieldTexture(note:Dynamic, texture:String):Void {
		var state = stateFor(note, true);
		if (state != null) state.fieldTexture = texture;
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
