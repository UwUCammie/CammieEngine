package;

import haxe.Json;

using StringTools;

/** A chart-event payload after donor-engine names have been normalized. */
typedef EngineCompatEventRoute = {
	var name:String;
	var v1:String;
	var v2:String;
	var v3:String;
}

/**
	A read-only verdict for one mounted HXC SongEvent body.  `covered` means the
	native route implements the operation represented by the body; `gaps` names
	any donor-only side effects which the event adapter does not claim to run.
	This is deliberately separate from HxcCompat so the importer, diagnostics,
	and runtime all share the same semantic vocabulary.
*/
typedef EngineCompatEventBodyCoverage = {
	var covered:Bool;
	var gaps:Array<String>;
}

/**
	The stage identity that the native runtime should use for one authored
	stage id. `stageID` is deliberately kept beside the name: several FNF
	engines encode a stage variant in the id itself (for example V-Slice's
	`schoolEvilErect`), while this engine keeps the variant in the chart's
	`stageID` field and lets the stage script select its assets from there.
	`standard` means the mapping has a native stage implementation; it does not
	claim that a compiled donor class has equivalent lifecycle behavior.
*/
typedef EngineCompatStageResolution = {
	var authored:String;
	var nativeName:String;
	var stageID:Int;
	var standard:Bool;
}

/**
	A bounded plan for a visual dependency which is referenced by imported
	content but has no usable implementation in the mounted destination.  The
	plan keeps the authored id untouched and names the native runtime value used
	only for the safe fallback.  Import reports and live runtime diagnostics use
	the same record shape so a missing donor file is not confused with an
	unsupported engine API.
*/
typedef EngineCompatVisualFallback = {
	var kind:String;
	var requested:String;
	var fallback:String;
	var preserveRequested:Bool;
	var diagnostic:EngineCompatDependencyDiagnostic;
}

typedef EngineCompatDependencyDiagnostic = {
	var code:String;
	var classification:String;
	var kind:String;
	var requested:String;
	var origin:String;
	var searched:Array<String>;
	var gameplayImpact:String;
	var message:String;
}

/** A non-fatal finding produced while normalizing a legacy update hook. */
typedef LegacyFrameDeltaDiagnostic = {
	var severity:String;
	var code:String;
	var message:String;
	var line:Int;
}

/** The in-memory result of the legacy per-frame delta adapter. */
typedef LegacyFrameDeltaResult = {
	var source:String;
	var rewritten:Int;
	var diagnostics:Array<LegacyFrameDeltaDiagnostic>;
}

private typedef LegacyFrameDeltaRange = {
	var start:Int;
	var end:Int;
	var name:String;
}

private typedef LegacyFrameDeltaReplacement = {
	var start:Int;
	var end:Int;
	var value:String;
}

/**
	Names shared by the script/event/property compatibility front end.

	Imported content is allowed to keep the spelling used by its donor engine.
	The runtime asks for the canonical hook/property/event and this table routes
	that request to the donor spelling.  Keeping the table independent from
	PlayState is intentional: importers can use the same vocabulary when they
	inspect a script, while PlayState remains the single implementation of the
	underlying operation.
*/
class EngineCompat {
	/** Deduplicated runtime dependency findings.  Import screens keep their own
	 * per-song list; this process-level list is for live character/stage/icon
	 * fallback telemetry and does not turn a missing asset into a successful
	 * import. */
	public static var runtimeDependencyDiagnostics:Array<String> = [];

	/**
		Return the native value used when a visual dependency is genuinely absent.
		This is deliberately a tiny, engine-owned fallback table: it does not
		invent an asset or rewrite the authored chart id.
	*/
	public static function visualFallbackName(kind:String):String {
		var normalized = kind == null ? '' : StringTools.trim(kind).toLowerCase();
		return switch (normalized) {
			case 'stage': 'stage';
			case 'character': 'dad';
			case 'health-icon': 'iconGrid';
			case 'window-icon': 'current-window-icon';
			default: '';
		};
	}

	/** Search roots shown in runtime diagnostics when a native visual is absent. */
	public static function visualDependencySearchPaths(kind:String, reference:String,
		?ownerRoot:String):Array<String> {
		var normalized = kind == null ? '' : StringTools.trim(kind).toLowerCase();
		var clean = reference == null ? '' : StringTools.trim(reference);
		var result:Array<String> = [];
		switch (normalized) {
			case 'stage':
				result = [
					'assets/images/custom_stages/custom_stages.json',
					'assets/images/custom_stages/' + clean + '.hscript',
					'assets/stages/' + clean + '.lua',
					'assets/stages/' + clean + '.json'
				];
			case 'character':
				result = [
					'assets/images/custom_chars/custom_chars.jsonc',
					'assets/images/custom_chars/custom_chars.json',
					'assets/images/custom_chars/' + clean + '.hscript',
					'assets/images/custom_chars/' + clean + '.json',
					'assets/images/custom_chars/' + clean + '/char.png',
					'assets/images/custom_chars/' + clean + '/char.xml'
				];
			case 'health-icon':
				result = [
					'assets/images/custom_chars/custom_chars.jsonc',
					'assets/images/custom_chars/icon_only_chars.json',
					'assets/images/custom_chars/' + clean + '/icons.png',
					'assets/images/icons/icon-' + clean + '.png',
					'assets/images/icons/' + clean + '.png'
				];
		}
		if (normalized == 'health-icon') {
			var owner = safeVisualOwnerRoot(ownerRoot);
			if (owner != '' && clean != '' && new EReg('^[A-Za-z0-9_-]+$', '').match(clean)) {
				var ownerPaths = [
					owner + '/images/custom_chars/' + clean + '/icons.png',
					owner + '/images/custom_chars/' + clean + '/icons.xml',
					owner + '/images/icons/' + clean + '/icon.png',
					owner + '/images/icons/icon-' + clean + '.png',
					owner + '/images/icons/' + clean + '.png'
				];
				result = ownerPaths.concat(result);
			}
		}
		return result;
	}

	/** Accept only manifest-owned destination roots when adding scoped visual
	 * paths to runtime diagnostics. */
	static function safeVisualOwnerRoot(value:String):String {
		var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		while (clean.endsWith('/')) clean = clean.substr(0, clean.length - 1);
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0)
			return '';
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..')
				return '';
		return clean.startsWith(CompatScriptManifest.ROOT_PREFIX + '/') ? clean : '';
	}

	/**
		Build the shared missing-dependency record.  `classification` is explicit
		so a caller can report an absent donor file as `donor-source-omission`,
		while a present donor implementation that the native engine cannot execute
		can use `unsupported-engine-behavior`.  Neither case changes the authored
		chart data or the import missing count.
	*/
	public static function planVisualFallback(kind:String, requested:String, origin:String,
		searched:Array<String>, gameplayImpact:String,
		?classification:String = 'donor-source-omission'):EngineCompatVisualFallback {
		var normalizedKind = kind == null ? '' : StringTools.trim(kind).toLowerCase();
		var cleanRequested = requested == null ? '' : StringTools.trim(requested);
		var cleanClassification = classification == null || StringTools.trim(classification) == ''
			? 'unclassified-visual-dependency' : StringTools.trim(classification);
		var cleanOrigin = origin == null ? '' : StringTools.trim(origin);
		var cleanImpact = gameplayImpact == null ? '' : StringTools.trim(gameplayImpact);
		var paths:Array<String> = searched == null ? [] : searched.copy();
		var code = cleanClassification.toLowerCase().indexOf('unsupported') >= 0
			? 'unsupported-engine-dependency' : 'missing-donor-dependency';
		var fallback = visualFallbackName(normalizedKind);
		if (normalizedKind == 'stage') {
			var nativeStageAlias = resolveStageAlias(cleanRequested);
			if (nativeStageAlias != null && nativeStageAlias != ''
				&& nativeStageAlias.toLowerCase() != cleanRequested.toLowerCase())
				fallback = nativeStageAlias;
		}
		var message = '[' + code + '] kind=' + normalizedKind + ' id=' + cleanRequested
			+ ' classification=' + cleanClassification + ' origin=' + cleanOrigin
			+ ' searched=[' + paths.join(', ') + '] gameplay-impact=' + cleanImpact
			+ ' fallback=' + fallback + ' authored-id-preserved=true';
		var diagnostic:EngineCompatDependencyDiagnostic = {
			code: code,
			classification: cleanClassification,
			kind: normalizedKind,
			requested: cleanRequested,
			origin: cleanOrigin,
			searched: paths,
			gameplayImpact: cleanImpact,
			message: message
		};
		return {
			kind: normalizedKind,
			requested: cleanRequested,
			fallback: fallback,
			preserveRequested: cleanRequested != '',
			diagnostic: diagnostic
		};
	}

	/** Record and trace one live fallback without making it look like success. */
	public static function reportVisualFallback(plan:EngineCompatVisualFallback):String {
		if (plan == null || plan.diagnostic == null)
			return '';
		var message = plan.diagnostic.message;
		if (runtimeDependencyDiagnostics.indexOf(message) < 0) {
			runtimeDependencyDiagnostics.push(message);
			trace('[engine-compat] ' + message);
		}
		return message;
	}

	/** A pure launch gate used by tests and import previews before applying a
	 * fallback to live Flixel objects.  Unsupported kinds never pass silently. */
	public static function canUseVisualFallback(plan:EngineCompatVisualFallback):Bool {
		return plan != null && plan.diagnostic != null && plan.fallback != null
			&& StringTools.trim(plan.fallback) != '' && plan.preserveRequested
			&& plan.diagnostic.code != 'unsupported-engine-dependency';
	}

	/**
		Psych/Kade callbacks use two sentinel values instead of a typed result:
		`Function_Stop` blocks a gate and `Function_Continue` allows it.  The
		native HScript bridge seeds those names as booleans, while a few imported
		HScript modules still return the literal strings.  Keep the interpretation
		at this boundary so PlayState does not have to know which donor spelling
		produced a callback result.
	*/
	public static function functionStop(value:Dynamic):Bool {
		return ScriptCallbackResult.stopsGate(value);
	}

	public static function functionContinue(value:Dynamic):Bool {
		return ScriptCallbackResult.continues(value);
	}

	/** Return whether any callback in a broadcast requested a gate stop. */
	public static function anyFunctionStop(values:Array<Dynamic>):Bool {
		if (values == null)
			return false;
		for (value in values)
			if (functionStop(value))
				return true;
		return false;
	}

	/**
		Map the small ClientPrefs/PlayState class-property surface used by old
		Psych/Kade scripts.  The runtime owns the actual values; this function only
		returns a stable adapter key so import diagnostics and PlayState use the
		same route without exposing arbitrary class reflection.
	*/
	public static function legacyClassProperty(className:String, path:String):String {
		if (className == null || path == null)
			return '';
		var cls = StringTools.trim(className).toLowerCase();
		var clean = StringTools.trim(path).toLowerCase();
		while (clean.startsWith('.'))
			clean = clean.substr(1);
		if (cls == 'clientprefs' || cls == 'backend.clientprefs') {
			switch (clean) {
				case 'ratingoffset' | 'data.ratingoffset': return 'ratingOffset';
				case 'sickwindow' | 'data.sickwindow': return 'sickWindow';
				case 'goodwindow' | 'data.goodwindow': return 'goodWindow';
				case 'badwindow' | 'data.badwindow': return 'badWindow';
				case 'shitwindow' | 'data.shitwindow': return 'shitWindow';
				case 'splashalpha' | 'data.splashalpha': return 'splashAlpha';
			}
		}
		if (cls == 'playstate' || cls == 'states.playstate') {
			switch (clean) {
				case 'ispixelstage': return 'isPixelStage';
				case 'chartingmode': return 'chartingMode';
			}
		}
		return '';
	}

	/**
		Return the Psych API generation represented by the shared Lua bridge.
		Psych/Kade scripts use this global to choose old versus modern property
		paths (for example `backend.ClientPrefs.data.sickWindow`).  Keep the
		compatibility generation explicit at the engine boundary instead of making
		each imported chart invent its own version variable.
	*/
	public static function psychCompatibilityVersion():String {
		// Preserve the API generation while exposing a full release-shaped value.
		// Legacy scripts also compare versions after removing their dots.
		return '0.7.0';
	}

	/**
		Normalize Psych's judgement-counter property names before they cross the
		reflection boundary.  The native PlayState stores these counters as static
		fields, while Psych Lua addresses them as root properties (`sicks`,
		`goods`, and friends); keeping the name mapping here avoids chart-side
		reflection special cases.
	*/
	public static function legacyCounterName(name:Dynamic):String {
		if (name == null)
			return '';
		switch (StringTools.trim(Std.string(name)).toLowerCase()) {
			case 'misses': return 'misses';
			case 'shits': return 'shits';
			case 'bads': return 'bads';
			case 'goods': return 'goods';
			case 'sicks': return 'sicks';
			default: return '';
		}
	}

	/**
		Normalize the fifth value used by Modding Plus note rows.  That engine
		serializes a lift as `[time, lane, sustain, altAnim, true]`, while the
		native Note ABI selects lift graphics/behaviour from the note-data block
		at `noteAmount * 4`.  Keep this conversion at the chart boundary so the
		authored boolean remains available to charting/import diagnostics and the
		legacy donor file is never rewritten.
	*/
	public static function normalizeLegacyNoteRows(chart:Dynamic, noteAmount:Int = 4):Void {
		if (chart == null)
			return;
		if (noteAmount <= 0)
			noteAmount = 4;
		var song:Dynamic = Reflect.field(chart, 'song');
		if (song == null || Std.isOfType(song, String))
			song = chart;
		var sections:Dynamic = song == null ? null : Reflect.field(song, 'notes');
		if (!Std.isOfType(sections, Array))
			return;
		for (section in (cast sections:Array<Dynamic>)) {
			if (section == null)
				continue;
			var rows:Dynamic = Reflect.field(section, 'sectionNotes');
			if (!Std.isOfType(rows, Array))
				continue;
			for (row in (cast rows:Array<Dynamic>)) {
				var lane = legacyNoteLane(row);
				if (!legacyLiftRow(row) || lane >= noteAmount * 4 || lane < 0)
					continue;
				var values:Array<Dynamic> = cast row;
				values[1] = lane + noteAmount * 4;
			}
		}
	}

	/** Return whether a legacy row carries Modding Plus's lift marker. */
	public static function legacyLiftRow(row:Dynamic):Bool {
		if (row == null || !Std.isOfType(row, Array))
			return false;
		var values:Array<Dynamic> = cast row;
		return values.length >= 5 && legacyTruthy(values[4]);
	}

	/**
		Apply the optional per-note fields used by Modding Plus charts.  The
		fork's Note class still exposes these fields (they are also used by
		noteInfo.json), but the old chart reader had its assignments commented out
		when the extended row format was disabled.  That made a valid legacy row
		look playable while silently dropping its health and timing rules.

		Only ordinary notes are changed here.  Mine/lift/nuke rows and generated
		noteInfo entries already have native semantics in Note.new; allowing a
		legacy row's optional columns to overwrite those values would turn a
		hazard back into a normal note.  The source row is read-only and remains
		available to charting/import diagnostics.
	*/
	public static function applyLegacyNoteRow(note:Dynamic, row:Dynamic):Void {
		if (note == null || row == null || !Std.isOfType(row, Array))
			return;
		var values:Array<Dynamic> = cast row;
		if (values.length < 4)
			return;
		if (legacyBoolField(note, 'dontEdit') || legacyBoolField(note, 'mineNote')
			|| legacyBoolField(note, 'nukeNote') || legacyBoolField(note, 'isLiftNote'))
			return;

		var number:Null<Float>;
		if (values.length > 5 && (number = legacyNumber(values[5])) != null)
			Reflect.setField(note, 'healMultiplier', number);
		if (values.length > 6 && (number = legacyNumber(values[6])) != null)
			Reflect.setField(note, 'damageMultiplier', number);
		if (values.length > 7 && values[7] != null)
			Reflect.setField(note, 'consistentHealth', legacyTruthy(values[7]));
		if (values.length > 8 && (number = legacyNumber(values[8])) != null)
			Reflect.setField(note, 'timingMultiplier', number);
		if (values.length > 9 && values[9] != null)
			Reflect.setField(note, 'shouldBeSung', legacyTruthy(values[9]));
		if (values.length > 10 && values[10] != null)
			Reflect.setField(note, 'ignoreHealthMods', legacyTruthy(values[10]));
	}

	/** Return the authored note-skin suffix without mutating the source row. */
	public static function legacyNoteAnimSuffix(row:Dynamic):String {
		if (row == null || !Std.isOfType(row, Array))
			return null;
		var values:Array<Dynamic> = cast row;
		if (values.length <= 11 || values[11] == null)
			return null;
		var result = StringTools.trim(Std.string(values[11]));
		return result == '' ? null : result;
	}

	/**
		Resolve the old Kade/FPS extended hazard block without relying on a song
		filename.  This engine uses `NOTE_AMOUNT * 2 .. NOTE_AMOUNT * 4` for a
		mine and `NOTE_AMOUNT * 6 .. NOTE_AMOUNT * 8` for a nuke/death note.  A
		few Kade-era packs authored their death notes in the mine block because
		the donor's chart ABI had no named note type.  The old loader recognized
		that one case by song name, which made the same chart semantics fail as
		soon as a folder was renamed or another Kade song used the convention.

		The decision is deliberately conservative and engine-level:
		
		* an authored `convertMineToNuke` value always wins;
		* named row metadata (`death`, `nuke`, `instakill`, `mine`, etc.) wins over
		  inference; and
		* only a chart carrying the extended mine block from a Kade/FPS/legacy
		  compatibility source is promoted to the native nuke block.

		Unknown engines and ordinary native mine charts remain mines.  The chart
		rows are read only; the caller changes only its in-memory chart object.
	*/
	public static function inferMineToNuke(chart:Dynamic, noteAmount:Int = 4,
		?engine:String):Bool {
		if (chart == null)
			return false;
		var explicit:Dynamic = Reflect.field(chart, 'convertMineToNuke');
		if (explicit != null)
			return legacyTruthy(explicit);
		if (noteAmount <= 0)
			noteAmount = 4;

		var song:Dynamic = Reflect.field(chart, 'song');
		if (song == null || Std.isOfType(song, String))
			song = chart;
		if (explicit == null && song != chart) {
			explicit = Reflect.field(song, 'convertMineToNuke');
			if (explicit != null)
				return legacyTruthy(explicit);
		}
		var metadata:Dynamic = song == null ? null : Reflect.field(song, 'compatMetadata');
		if (metadata == null && song != chart)
			metadata = Reflect.field(chart, 'compatMetadata');
		var sourceEngine = engine == null ? '' : StringTools.trim(engine);
		var readEngine = function(value:Dynamic):String {
			if (value == null)
				return '';
			var text = StringTools.trim(Std.string(value));
			return text.toLowerCase() == 'null' ? '' : text;
		};
		if (sourceEngine == '' && metadata != null)
			sourceEngine = readEngine(Reflect.field(metadata, 'engine'));
		if (sourceEngine == '' && song != null)
			sourceEngine = readEngine(Reflect.field(song, 'engine'));
		if (sourceEngine == '' && chart != song)
			sourceEngine = readEngine(Reflect.field(chart, 'engine'));

		var explicitDeath = false;
		var explicitMine = false;
		var encodedMine = false;
		var sections:Dynamic = song == null ? null : Reflect.field(song, 'notes');
		if (sections == null || !Std.isOfType(sections, Array))
			return false;
		for (section in (cast sections:Array<Dynamic>)) {
			if (section == null)
				continue;
			var rows:Dynamic = Reflect.field(section, 'sectionNotes');
			if (rows == null || !Std.isOfType(rows, Array))
				continue;
			for (row in (cast rows:Array<Dynamic>)) {
				if (row == null || !Std.isOfType(row, Array))
					continue;
				var values:Array<Dynamic> = cast row;
				if (values.length < 2)
					continue;
				var lane = Std.parseInt(Std.string(values[1]));
				if (lane != null && lane >= noteAmount * 2 && lane < noteAmount * 4)
					encodedMine = true;
				if (values.length < 4 || !NoteTypeCompat.isStringType(values[3]))
					continue;
				var kind = StringTools.trim(Std.string(values[3])).toLowerCase();
				if (kind.indexOf('nuke') >= 0 || kind.indexOf('death') >= 0
					|| kind.indexOf('instakill') >= 0 || kind.indexOf('instant kill') >= 0
					|| kind == 'kill' || kind == 'kill note')
					explicitDeath = true;
				else if (kind == 'mine' || kind == 'mine note' || kind == 'mine-note'
					|| kind == 'hazard')
					explicitMine = true;
			}
		}
		if (explicitDeath)
			return true;
		if (explicitMine)
			return false;
		return encodedMine && usesLegacyDeathBlock(sourceEngine);
	}

	/** Kade/FPS/old packaged roots are the only sources with the anonymous
		mine-block death-note convention observed in the mounted corpus. */
	static function usesLegacyDeathBlock(engine:String):Bool {
		if (engine == null)
			return false;
		var value = StringTools.trim(engine).toLowerCase();
		return value == 'kade' || value == 'kade engine'
			|| value == 'fps' || value == 'fps plus' || value == 'fps plus engine'
			|| value == 'legacy' || value == 'legacy fnf/polymod';
	}

	static function legacyNumber(value:Dynamic):Null<Float> {
		if (value == null || Std.isOfType(value, Bool))
			return null;
		var result = Std.parseFloat(StringTools.trim(Std.string(value)));
		return Math.isNaN(result) ? null : result;
	}

	static function legacyBoolField(object:Dynamic, field:String):Bool {
		return object != null && Reflect.hasField(object, field) && legacyTruthy(Reflect.field(object, field));
	}

	/** Read a row's lane while retaining the side bits used by this engine. */
	public static function legacyNoteLane(row:Dynamic):Int {
		if (row == null || !Std.isOfType(row, Array))
			return 0;
		var values:Array<Dynamic> = cast row;
		if (values.length < 2)
			return 0;
		var parsed = Std.parseInt(Std.string(values[1]));
		if (parsed == null)
			return 0;
		return parsed;
	}

	static function legacyTruthy(value:Dynamic):Bool {
		if (value == true)
			return true;
		if (value == false || value == null)
			return false;
		var text = StringTools.trim(Std.string(value)).toLowerCase();
		return text == 'true' || text == '1' || text == 'yes' || text == 'on';
	}

	/**
		Turn the small JSON dialogue dialect used by FPS Plus/Kade forks into the
		native text-dialogue ABI.  The original JSON remains an import sidecar;
		this is only the destination fallback used when a foreign cutscene class
		cannot be executed.  Portrait ids are kept as the native emotion token so
		DialogueBox can resolve copied `images/ui/dialogue/portraits` assets.
	*/
	public static function legacyDialogueText(data:Dynamic, player1:String = 'bf',
		player2:String = 'dad'):String {
		if (data == null)
			return null;
		var entries:Dynamic = Reflect.field(data, 'dialogue');
		if (!Std.isOfType(entries, Array) && Std.isOfType(data, Array))
			entries = data;
		if (!Std.isOfType(entries, Array))
			return null;
		var rows:Array<String> = [
			'[178[ [179[ [223[ [216[ |Lunchbox| *100* =1= #classic#  <0.08< >4> (0.2( )5) {0.83{ }5} `hand_textbox` ~clickText~'
		];
		for (entry in (cast entries:Array<Dynamic>)) {
			if (entry == null)
				continue;
			var textValue:Dynamic = hxcField(entry, 'text');
			if (textValue == null)
				textValue = hxcField(entry, 'dialogue');
			if (textValue == null)
				textValue = hxcField(entry, 'message');
			if (textValue == null)
				continue;
			var portrait = legacyDialoguePortrait(entry);
			var speaker = legacyDialogueSpeaker(portrait, player1, player2);
			var emotion = portrait == null || StringTools.trim(portrait) == '' ? 'default' : portrait;
			var box = Std.string(hxcField(entry, 'box'));
			var boxName = box.toLowerCase() == 'pixel' || box.toLowerCase() == 'pixel_normal'
				? 'pixel_normal' : 'classic';
			var text = StringTools.replace(StringTools.replace(Std.string(textValue), '\r', ''), '\n', ' ');
			rows.push(':' + speaker + ': !' + emotion + '! [Funkin[ ]32] *100* =0= +0+ -0- <0< >0> ;0.04; |false| #'
				+ boxName + '# ^pixelText^ !#000000! ?#FFFFFF? .#FFFFFF. ~~      ' + text);
		}
		return rows.length > 1 ? rows.join('\n') : null;
	}

	/** Extract the first portrait/character token used by legacy dialogue JSON. */
	public static function legacyDialoguePortrait(entry:Dynamic):String {
		if (entry == null)
			return '';
		var portraits:Dynamic = hxcField(entry, 'portraits');
		if (Std.isOfType(portraits, Array)) {
			var list:Array<Dynamic> = cast portraits;
			for (portrait in list)
				if (portrait != null && StringTools.trim(Std.string(portrait)) != '')
					return StringTools.trim(Std.string(portrait));
		}
		for (field in ['portrait', 'character', 'speaker', 'name']) {
			var value:Dynamic = hxcField(entry, field);
			if (value != null && StringTools.trim(Std.string(value)) != '')
				return StringTools.trim(Std.string(value));
		}
		return '';
	}

	/** Map common FPS/Kade portrait ids to the native chart character roles. */
	public static function legacyDialogueSpeaker(portrait:String, player1:String = 'bf',
		player2:String = 'dad'):String {
		var token = portrait == null ? '' : portrait.toLowerCase();
		if (token.indexOf('boyfriend') >= 0 || token.indexOf('bf') == 0)
			return player1 == null || StringTools.trim(player1) == '' ? 'bf' : player1;
		if (token.indexOf('girlfriend') >= 0 || token.indexOf('gf') == 0)
			return 'gf';
		return player2 == null || StringTools.trim(player2) == '' ? 'dad' : player2;
	}

	/** Read a FPS Plus/Kade cutscene sidecar's start script name. */
	public static function legacyCutsceneScript(data:Dynamic):String {
		if (data == null)
			return null;
		var start:Dynamic = hxcField(data, 'startCutscene');
		if (Std.isOfType(start, Array)) {
			var list:Array<Dynamic> = cast start;
			start = list.length == 0 ? null : list[0];
		}
		var name:Dynamic = start == null ? null : (Std.isOfType(start, String)
			? start : hxcField(start, 'name'));
		if (name == null)
			name = hxcField(data, 'name');
		var result = name == null ? '' : StringTools.trim(Std.string(name));
		return result == '' || result.toLowerCase() == 'null' || result.toLowerCase() == 'none'
			? null : result;
	}

	/** Preserve the sidecar's story/freeplay and one-shot hints when present. */
	public static function legacyCutsceneBool(data:Dynamic, field:String, fallback:Bool):Bool {
		if (data == null || field == null)
			return fallback;
		var start:Dynamic = hxcField(data, 'startCutscene');
		if (start != null && !Std.isOfType(start, String) && !Std.isOfType(start, Array)) {
			var nested:Dynamic = hxcField(start, field);
			if (nested != null)
				return nested == true || Std.string(nested).toLowerCase() == 'true';
		}
		var value:Dynamic = hxcField(data, field);
		return value == null ? fallback : (value == true || Std.string(value).toLowerCase() == 'true');
	}

	/**
		Apply an imported cutscene's story/freeplay and one-shot policy without
		changing the native cutscene gate. FPS Plus/Kade sidecars default to the
		historical story-only/one-shot behavior when either hint is absent, while
		explicit `false` values are meaningful.
	*/
	public static function importedCutsceneAllowed(data:Dynamic, alwaysDoCutscenes:Bool,
		isStoryMode:Bool, watchedCutscene:Bool):Bool {
		if (data == null)
			return false;
		var script:Dynamic = hxcField(data, 'cutsceneScript');
		if (script == null || StringTools.trim(Std.string(script)) == '')
			return false;
		var storyOnly = legacyCutsceneBool(data, 'cutsceneStoryOnly', true);
		var playOnce = legacyCutsceneBool(data, 'cutscenePlayOnce', true);
		if (storyOnly && !alwaysDoCutscenes && !isStoryMode)
			return false;
		return !playOnce || !watchedCutscene;
	}

	/** Psych Lua commonly gates authored intros and endings on `isStoryMode`.
	 * Project the force-cutscene option into that script global only; native
	 * playlist, score, and menu flow continue to use PlayState.isStoryMode. */
	public static function importedScriptStoryMode(isStoryMode:Bool,
		alwaysDoCutscenes:Bool, translatedLua:Bool):Bool {
		return isStoryMode || (translatedLua && alwaysDoCutscenes);
	}

	/**
		HXC character/stage access is deliberately dynamic here.  HXC scripts are
		translated into isolated HScript interpreters, so referring to PlayState or
		StageHelper directly from the source adapter would make the analyser pull
		the whole gameplay state into its standalone tooling fixtures.  These small
		Reflect-based adapters keep the donor spellings usable at runtime while
		remaining safe when a stage/character is absent.
	*/
	public static function hxcGetCharacter(source:Dynamic, role:String):Dynamic {
		var normalized = hxcCharacterRole(role);
		if (source == null)
			return null;

		// A PlayState exposes its active stage as curStage.  A translated donor
		// may still hand us currentStage, so accept both names at the boundary.
		var stage:Dynamic = hxcField(source, 'curStage');
		if (stage == null)
			stage = hxcField(source, 'currentStage');
		if (stage != null && stage != source) {
			var staged = hxcCall(stage, hxcCharacterGetter(normalized), []);
			if (staged != null)
				return staged;
		}
		// A StageHelper itself is also a valid source.  This is the path used by
		// the unqualified aliases seeded in PlayState while a stage is active.
		if (stage == null || stage == source) {
			var directStaged = hxcCall(source, hxcCharacterGetter(normalized), []);
			if (directStaged != null)
				return directStaged;
		}

		var directName = switch (normalized) {
			case 'boyfriend': 'boyfriend';
			case 'gf': 'gf';
			default: 'dad';
		};
		return hxcField(source, directName);
	}

	public static function hxcGetDad(source:Dynamic):Dynamic
		return hxcGetCharacter(source, 'dad');

	public static function hxcGetBoyfriend(source:Dynamic):Dynamic
		return hxcGetCharacter(source, 'boyfriend');

	public static function hxcGetGirlfriend(source:Dynamic):Dynamic
		return hxcGetCharacter(source, 'gf');

	public static function hxcGetOpponent(source:Dynamic):Dynamic
		return hxcGetCharacter(source, 'opponent');

	/** Resolve a donor Stage.getNamedProp()/getElement() lookup. */
	public static function hxcGetNamedProp(source:Dynamic, name:String):Dynamic {
		if (source == null || name == null)
			return null;
		var stage:Dynamic = hxcField(source, 'curStage');
		if (stage == null)
			stage = hxcField(source, 'currentStage');
		if (stage == null)
			stage = source;
		var result = hxcCall(stage, 'getNamedProp', [name]);
		if (result != null)
			return result;
		result = hxcCall(stage, 'getElement', [name]);
		if (result != null)
			return result;
		var elements:Dynamic = hxcField(stage, 'elements');
		if (elements != null) {
			try {
				if (Reflect.hasField(elements, name))
					return Reflect.field(elements, name);
			} catch (_:Dynamic) {}
			try {
				if (Reflect.hasField(elements, 'get'))
					return Reflect.callMethod(elements, Reflect.field(elements, 'get'), [name]);
			} catch (_:Dynamic) {}
		}
		return null;
	}

	/** Return the active animation name, or an empty string for a missing one. */
	public static function hxcCurrentAnimation(character:Dynamic):String {
		if (character == null)
			return '';
		var direct = hxcCall(character, 'getCurrentAnimation', []);
		if (direct != null)
			return Std.string(direct);
		var animation:Dynamic = hxcField(character, 'animation');
		var current:Dynamic = hxcField(animation, 'curAnim');
		var name:Dynamic = hxcField(current, 'name');
		return name == null ? '' : Std.string(name);
	}

	/** Apply HXC's named animation offset convention to a native character. */
	public static function hxcSetAnimationOffsets(character:Dynamic, name:String,
		x:Float = 0, y:Float = 0):Dynamic {
		if (character == null)
			return character;
		if (hxcHasMethod(character, 'setAnimationOffsets'))
			return hxcCall(character, 'setAnimationOffsets', [name, x, y]);
		if (hxcHasMethod(character, 'addOffset'))
			return hxcCall(character, 'addOffset', [name, x, y]);
		return character;
	}

	/** Play an HXC animation while preserving the donor's ignoreOther argument. */
	public static function hxcPlayAnimation(character:Dynamic, name:String,
		restart:Bool = false, ignoreOther:Bool = false, reversed:Bool = false):Dynamic {
		if (character == null)
			return character;
		if (hxcHasMethod(character, 'playAnimation'))
			return hxcCall(character, 'playAnimation', [name, restart, ignoreOther, reversed]);
		if (hxcHasMethod(character, 'playAnim'))
			return hxcCall(character, 'playAnim', [name, restart, reversed, 0]);
		return character;
	}

	public static function hxcHasAnimation(character:Dynamic, name:String):Bool {
		if (character == null || name == null)
			return false;
		var direct = hxcCall(character, 'hasAnimation', [name]);
		if (direct != null)
			return direct == true;
		var animation:Dynamic = hxcField(character, 'animation');
		var exists = hxcCall(animation, 'exists', [name]);
		return exists == true;
	}

	public static function hxcIsSinging(character:Dynamic):Bool
		return StringTools.startsWith(hxcCurrentAnimation(character), 'sing');

	public static function hxcGetDataFlipX(character:Dynamic):Bool {
		if (character == null)
			return false;
		var direct = hxcCall(character, 'getDataFlipX', []);
		if (direct != null)
			return direct == true;
		return hxcField(character, 'flipX') == true;
	}

	/** Return the member names handled by PlayState/StageHelper/Character aliases. */
	public static function hxcApiNames(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || source == '')
			return result;
		for (name in hxcApiNameList())
			if (new EReg('\\b' + name + '\\s*\\(', 'm').match(source))
				appendName(result, name);
		return result;
	}

	static function hxcApiNameList():Array<String> {
		return [
			'getDad', 'getBoyfriend', 'getGirlfriend', 'getOpponent', 'getNamedProp',
			'getCurrentAnimation', 'setAnimationOffsets', 'playAnimation',
			'playSingAnimation', 'hasAnimation', 'isSinging', 'isAnimationFinished',
			'getDataFlipX'
		];
	}

	static function hxcCharacterRole(role:String):String {
		if (role == null)
			return 'dad';
		switch (StringTools.trim(role).toLowerCase()) {
			case 'bf' | 'boyfriend' | 'player' | 'player1': return 'boyfriend';
			case 'gf' | 'girlfriend': return 'gf';
			default: return 'dad';
		}
	}

	static function hxcCharacterGetter(role:String):String {
		return switch (role) {
			case 'boyfriend': 'getBoyfriend';
			case 'gf': 'getGirlfriend';
			default: 'getDad';
		};
	}

	static function hxcField(value:Dynamic, name:String):Dynamic {
		if (value == null || name == null)
			return null;
		try {
			var reflected = Reflect.field(value, name);
			if (reflected != null)
				return reflected;
		} catch (_:Dynamic) {}
		// Compiled public properties can be readable without appearing as dynamic
		// fields, which is common for typed hxcpp objects.
		try return Reflect.getProperty(value, name) catch (_:Dynamic) return null;
	}

	static function hxcHasMethod(value:Dynamic, name:String):Bool {
		return value != null && name != null && hxcField(value, name) != null;
	}

	static function hxcCall(value:Dynamic, name:String, args:Array<Dynamic>):Dynamic {
		if (!hxcHasMethod(value, name))
			return null;
		try return Reflect.callMethod(value, hxcField(value, name), args) catch (_:Dynamic) return null;
	}

	/**
		Read a V-Slice/HXC payload field without requiring the donor event class.

		The importer deliberately constructs anonymous payload objects instead of
		instantiating donor classes.  HXC's SongEventData API nevertheless exposes
		typed getters, so keep those getters on the native adapter and resolve the
		field from the same `eventData.value` object that ordinary HXC property
		access uses.  This function does not call arbitrary methods on the payload;
		it only reads the explicitly supplied data fields.
	*/
	public static function hxcPayloadValue(payload:Dynamic, name:String):Dynamic {
		if (payload == null || name == null || StringTools.trim(name) == '')
			return null;
		var eventData:Dynamic = hxcField(payload, 'eventData');
		var value:Dynamic = eventData == null ? null : hxcField(eventData, 'value');
		var result = hxcPayloadField(value, name);
		if (result != null || hxcHasField(value, name))
			return result;
		result = hxcPayloadField(payload, name);
		if (result != null || hxcHasField(payload, name))
			return result;
		result = hxcPayloadField(eventData, name);
		return result;
	}

	/** Attach the small, mutable typed-getter/cancellation surface used by HXC. */
	public static function hxcAttachPayload(payload:Dynamic):Dynamic {
		if (payload == null)
			return null;
		if (!hxcHasMethod(payload, 'getFloat'))
			Reflect.setField(payload, 'getFloat', function(name:String):Null<Float>
				return hxcPayloadGetFloat(payload, name));
		if (!hxcHasMethod(payload, 'getBool'))
			Reflect.setField(payload, 'getBool', function(name:String):Null<Bool>
				return hxcPayloadGetBool(payload, name));
		if (!hxcHasMethod(payload, 'getInt'))
			Reflect.setField(payload, 'getInt', function(name:String):Null<Int>
				return hxcPayloadGetInt(payload, name));
		if (!hxcHasMethod(payload, 'getString'))
			Reflect.setField(payload, 'getString', function(name:String):Null<String>
				return hxcPayloadGetString(payload, name));
		if (!hxcHasMethod(payload, 'cancel'))
			Reflect.setField(payload, 'cancel', function():Void hxcPayloadCancel(payload));
		if (!hxcHasMethod(payload, 'cancelEvent'))
			Reflect.setField(payload, 'cancelEvent', function():Void hxcPayloadCancel(payload));
		// HXC sometimes stores the event data object in a local and calls its
		// typed getter.  Attach the same safe surface to both nested objects, but
		// never walk or mutate arbitrary donor objects.
		var eventData:Dynamic = hxcField(payload, 'eventData');
		if (eventData != null && eventData != payload) {
			if (!hxcHasMethod(eventData, 'getFloat'))
				Reflect.setField(eventData, 'getFloat', function(name:String):Null<Float>
					return hxcPayloadGetFloat(payload, name));
			if (!hxcHasMethod(eventData, 'getBool'))
				Reflect.setField(eventData, 'getBool', function(name:String):Null<Bool>
					return hxcPayloadGetBool(payload, name));
			if (!hxcHasMethod(eventData, 'getInt'))
				Reflect.setField(eventData, 'getInt', function(name:String):Null<Int>
					return hxcPayloadGetInt(payload, name));
			if (!hxcHasMethod(eventData, 'getString'))
				Reflect.setField(eventData, 'getString', function(name:String):Null<String>
					return hxcPayloadGetString(payload, name));
			if (!hxcHasMethod(eventData, 'cancel'))
				Reflect.setField(eventData, 'cancel', function():Void hxcPayloadCancel(payload));
			if (!hxcHasMethod(eventData, 'cancelEvent'))
				Reflect.setField(eventData, 'cancelEvent', function():Void hxcPayloadCancel(payload));
			var value:Dynamic = hxcField(eventData, 'value');
			if (value != null && value != eventData)
				attachPayloadValue(value, payload);
		}
		return payload;
	}

	/** Return null only for an absent field; an authored empty/invalid value is NaN. */
	public static function hxcPayloadGetFloat(payload:Dynamic, name:String):Null<Float> {
		var value = hxcPayloadValue(payload, name);
		if (value == null)
			return null;
		if (Std.isOfType(value, Float) || Std.isOfType(value, Int))
			return Std.parseFloat(Std.string(value));
		var text = StringTools.trim(Std.string(value));
		if (text == '')
			return Math.NaN;
		return Std.parseFloat(text);
	}

	/** Return a typed HXC integer, or null when the authored field is absent. */
	public static function hxcPayloadGetInt(payload:Dynamic, name:String):Null<Int> {
		var value = hxcPayloadValue(payload, name);
		if (value == null)
			return null;
		if (Std.isOfType(value, Bool))
			return value == true ? 1 : 0;
		var text = StringTools.trim(Std.string(value));
		if (text == '')
			return null;
		var parsed = Std.parseInt(text);
		if (parsed != null)
			return parsed;
		var number = Std.parseFloat(text);
		return Math.isNaN(number) ? null : Std.int(number);
	}

	/** Return a typed HXC boolean, or null when the authored field is absent. */
	public static function hxcPayloadGetBool(payload:Dynamic, name:String):Null<Bool> {
		var value = hxcPayloadValue(payload, name);
		if (value == null)
			return null;
		if (Std.isOfType(value, Bool))
			return value;
		if (Std.isOfType(value, Int) || Std.isOfType(value, Float))
			return Std.parseFloat(Std.string(value)) != 0;
		var text = StringTools.trim(Std.string(value)).toLowerCase();
		return switch (text) {
			case 'true' | '1' | 'yes': true;
			case 'false' | '0' | 'no': false;
			default: null;
		};
	}

	/** Return a typed HXC string, or null when the authored field is absent. */
	public static function hxcPayloadGetString(payload:Dynamic, name:String):Null<String> {
		var value = hxcPayloadValue(payload, name);
		return value == null ? null : Std.string(value);
	}

	/** Mark a mutable HXC payload canceled through every supported alias. */
	public static function hxcPayloadCancel(payload:Dynamic):Void {
		if (payload == null)
			return;
		setHxcCanceled(payload);
		var eventData:Dynamic = hxcField(payload, 'eventData');
		if (eventData != null && eventData != payload)
			setHxcCanceled(eventData);
	}

	/**
		Construct the note view supplied to HXC note callbacks.  Native Note keeps
		`noteData` as an integer, while V-Slice exposes a NoteData object with
		kind/direction helpers.  The view keeps those donor reads stable while
		exposing only the generic note lifecycle/graphics operations which this
		engine can apply back to the live Note.  It is still a view, not a donor
		class instance: unknown fields and methods are never reflected through it.
	*/
	public static function hxcNoteCallbackPayload(args:Array<Dynamic>, ?callbackName:String):Dynamic {
		var note = hxcFindNote(args);
		var payload = hxcLifecyclePayload(callbackName == null ? 'note' : callbackName,
			{note: hxcNoteView(note)});
		Reflect.setField(payload, 'note', hxcNoteView(note));
		Reflect.setField(payload, 'nativeNote', note);
		var player:Dynamic = hxcFindBool(args);
		var direction:Dynamic = hxcFindDirection(note, args);
		var judgement:Dynamic = note == null ? null : hxcJudgementName(hxcField(note, 'rating'));
		Reflect.setField(payload, 'playerOne', player);
		Reflect.setField(payload, 'isPlayer', player);
		Reflect.setField(payload, 'dir', direction);
		Reflect.setField(payload, 'direction', direction);
		Reflect.setField(payload, 'judgement', judgement);
		Reflect.setField(payload, 'healthChange', 0);
		// Character companion callbacks can override the actor animation while
		// leaving note scoring/health to the native judgement path.
		Reflect.setField(payload, 'characterHandled', false);
		var value:Dynamic = hxcField(hxcField(payload, 'eventData'), 'value');
		if (value != null) {
			Reflect.setField(value, 'note', hxcField(payload, 'note'));
			Reflect.setField(value, 'playerOne', player);
			Reflect.setField(value, 'direction', direction);
		}
		return hxcAttachPayload(payload);
	}

	/** Preserve the scored judgement; V-Slice uses a separate 'perfect' bot hit. */
	static function hxcJudgementName(value:Dynamic):Dynamic {
		if (value == null)
			return null;
		return StringTools.trim(Std.string(value)).toLowerCase();
	}

	/**
		Apply mutable fields written through a HXC note view.  HXC's note event
		object is intentionally a proxy so ordinary HScript/Psych callbacks keep
		their historical Note ABI.  Copy only fields that are part of the generic
		note surface; donor-only fields remain local to the proxy and therefore
		cannot silently mutate unrelated engine state.
	*/
	public static function hxcApplyNoteCallbackPayload(payload:Dynamic):Void {
		if (payload == null)
			return;
		var note:Dynamic = hxcField(payload, 'nativeNote');
		var view:Dynamic = hxcField(payload, 'note');
		if (note == null && view != null)
			note = hxcField(view, 'nativeNote');
		if (note == null || view == null)
			return;
		for (field in ['lowPriority', 'active', 'visible', 'alpha', 'x', 'y', 'angle', 'frames']) {
			if (!hxcHasField(view, field) || !hxcHasField(note, field))
				continue;
			var value = hxcField(view, field);
			if (value != null)
				try Reflect.setField(note, field, value) catch (_:Dynamic) {}
		}
		// V-Slice note kinds position their graphics through note.offset. Keep
		// only the two numeric coordinates from the script view; do not expose
		// arbitrary writes on the native FlxPoint or Note.
		var nativeOffset:Dynamic = hxcField(note, 'offset');
		var offsetView:Dynamic = hxcField(view, 'offset');
		if (nativeOffset != null && offsetView != null) {
			for (axis in ['x', 'y']) {
				var value:Dynamic = hxcField(offsetView, axis);
				if (Std.isOfType(value, Int) || Std.isOfType(value, Float)) {
					var number:Float = value;
					if (Math.isFinite(number))
						try Reflect.setProperty(nativeOffset, axis, number) catch (_:Dynamic) {}
				}
			}
		}
		var flipY:Dynamic = hxcField(view, 'flipY');
		if (hxcHasField(note, 'flipY') && Std.isOfType(flipY, Bool))
			try Reflect.setProperty(note, 'flipY', flipY) catch (_:Dynamic) {}
		// V-Slice exposes the sustain body as a separate holdNoteSprite. This
		// engine keeps the sustain graphics on the native Note, so mirror its
		// mutable alpha through the same bounded view instead of rejecting the
		// nested write or reflecting an arbitrary donor sprite.
		var holdView:Dynamic = hxcField(view, 'holdNoteSprite');
		if (holdView != null && hxcHasField(holdView, 'alpha') && hxcHasField(note, 'alpha')) {
			var holdAlpha = hxcField(holdView, 'alpha');
			if (holdAlpha != null)
				try Reflect.setField(note, 'alpha', holdAlpha) catch (_:Dynamic) {}
		}
		if (hxcField(view, 'killed') == true)
			hxcCall(note, 'kill', []);
		if (hxcField(view, 'destroyed') == true)
			hxcCall(note, 'destroy', []);
	}

	public static function hxcNoteView(note:Dynamic):Dynamic {
		if (note == null)
			return null;
		var noteData:Dynamic = hxcField(note, 'noteData');
		var dataNumber:Int = noteData == null ? 0 : Std.int(Std.parseFloat(Std.string(noteData)));
		// Imported HXC/V-Slice definitions retain the authored kind separately
		// from the native custom-note id.  Prefer that source identity so donor
		// callbacks can continue to compare `noteData.kind` without chart edits.
		var kind:Dynamic = hxcField(note, 'sourceKind');
		if (kind == null || Std.string(kind) == '')
			kind = hxcField(note, 'sourceNoteType');
		if (kind == null || Std.string(kind) == '')
			kind = hxcField(note, 'coolId');
		if (kind == null)
			kind = hxcField(note, 'noteType');
		if (kind != null) {
			var kindText = Std.string(kind);
			// Identity-only HXC definitions may reach runtime through their native
			// id before sourceKind is materialized. Recover the authored token from
			// the stable adapter prefix rather than requiring a chart rewrite.
			if (kindText.toLowerCase().startsWith('hxc:')) {
				var pieces = kindText.split(':');
				if (pieces.length > 1 && pieces[1] != '')
					kind = pieces[1];
			}
		}
		var mustPress:Dynamic = hxcField(note, 'mustPress');
		var nativeOffset:Dynamic = hxcField(note, 'offset');
		var dataView:Dynamic = {
			data: dataNumber,
			kind: kind == null ? '' : kind,
			getDirection: function():Int return dataNumber < 0 ? -dataNumber % 4 : dataNumber % 4,
			getMustHitNote: function():Bool return mustPress == true,
			getStrumlineIndex: function():Int return mustPress == true ? 0 : 1
		};
		var view:Dynamic = null;
		view = {
			ID: hxcField(note, 'ID'),
			kind: kind == null ? '' : kind,
			noteData: dataView,
			strumTime: hxcField(note, 'strumTime'),
			isSustainNote: hxcField(note, 'isSustainNote'),
			shouldBeSung: hxcField(note, 'shouldBeSung'),
			altNum: hxcField(note, 'altNum'),
			get_isHoldNote: function():Bool return hxcField(note, 'isSustainNote') == true,
			mustPress: mustPress,
			lowPriority: hxcField(note, 'lowPriority'),
			active: hxcField(note, 'active'),
			visible: hxcField(note, 'visible'),
			alpha: hxcField(note, 'alpha'),
			x: hxcField(note, 'x'),
			y: hxcField(note, 'y'),
			angle: hxcField(note, 'angle'),
			frames: hxcField(note, 'frames'),
			offset: nativeOffset == null ? null : {
				x: hxcField(nativeOffset, 'x'), y: hxcField(nativeOffset, 'y')
			},
			flipY: hxcField(note, 'flipY'),
			hsvShader: {saturation: hxcField(note, 'hxcHsvSaturation')},
			// Animation controllers are already engine-owned, so exposing the
			// controller preserves generic add/play operations without exposing
			// arbitrary fields on the Note itself.
			animation: hxcField(note, 'animation'),
			holdNoteSprite: hxcNoteSpriteView(note),
			updateHitbox: function():Dynamic return hxcCall(note, 'updateHitbox', []),
			kill: function():Void {
				Reflect.setField(view, 'killed', true);
				hxcCall(note, 'kill', []);
			},
			destroy: function():Void {
				Reflect.setField(view, 'destroyed', true);
				// A destroyed incoming note must not be added to PlayState's active
				// group after the callback. FlxBasic.destroy() releases members but
				// does not promise to clear `alive`, so mirror donor removal semantics
				// by killing it first.
				Reflect.setField(view, 'killed', true);
				hxcCall(note, 'kill', []);
				hxcCall(note, 'destroy', []);
			},
			nativeNote: note
		};
		return view;
	}

	/** Map the donor's separate hold-note sprite API onto this engine's live
		sustain Note.  The wrapper deliberately exposes only graphic refresh
		operations; it cannot walk arbitrary donor objects. */
	static function hxcNoteSpriteView(note:Dynamic):Dynamic {
		if (note == null)
			return null;
		return {
			cover: hxcField(note, 'cover'),
			alpha: hxcField(note, 'alpha'),
			loadGraphic: function(graphic:Dynamic, ?animated:Bool = false, ?width:Int = 0,
				?height:Int = 0, ?unique:Bool = false, ?key:String = null):Dynamic
				return hxcCall(note, 'loadGraphic', [graphic, animated, width, height, unique, key]),
			updateHitbox: function():Dynamic return hxcCall(note, 'updateHitbox', []),
			updateColorTransform: function():Dynamic return hxcCall(note, 'updateColorTransform', []),
			updateClipping: function():Dynamic return hxcCall(note, 'updateClipping', []),
			nativeNote: note
		};
	}

	static function hxcFindNote(args:Array<Dynamic>):Dynamic {
		if (args != null)
			for (value in args)
				if (value != null && (isHxcNativeNote(value)
					|| hxcHasField(value, 'noteData') || hxcHasField(value, 'isSustainNote')))
					return value;
		return null;
	}

	static function hxcFindBool(args:Array<Dynamic>):Dynamic {
		if (args != null)
			for (value in args)
				if (Std.isOfType(value, Bool))
					return value;
		return null;
	}

	static function hxcFindDirection(note:Dynamic, args:Array<Dynamic>):Dynamic {
		if (note != null) {
			var value = hxcField(note, 'noteData');
			if (value != null)
				return Math.abs(Std.int(Std.parseFloat(Std.string(value))) % 4);
		}
		if (args != null)
			for (value in args)
				if (Std.isOfType(value, Int) || Std.isOfType(value, Float))
					return value;
		return 0;
	}

	static function attachPayloadValue(value:Dynamic, payload:Dynamic):Void {
		// The typed-getter surface only exists on anonymous payload objects.
		// Parsed donor values may be native numbers/strings/arrays; writing
		// fields onto a native instance throws on hxcpp and - outside every
		// script try/catch - would end the whole session.
		if (value == null || Type.typeof(value) != TObject)
			return;
		if (!hxcHasMethod(value, 'getFloat'))
			Reflect.setField(value, 'getFloat', function(name:String):Null<Float>
				return hxcPayloadGetFloat(payload, name));
		if (!hxcHasMethod(value, 'getBool'))
			Reflect.setField(value, 'getBool', function(name:String):Null<Bool>
				return hxcPayloadGetBool(payload, name));
		if (!hxcHasMethod(value, 'getInt'))
			Reflect.setField(value, 'getInt', function(name:String):Null<Int>
				return hxcPayloadGetInt(payload, name));
		if (!hxcHasMethod(value, 'getString'))
			Reflect.setField(value, 'getString', function(name:String):Null<String>
				return hxcPayloadGetString(payload, name));
	}

	static function hxcPayloadField(value:Dynamic, name:String):Dynamic {
		if (value == null || name == null)
			return null;
		try return Reflect.field(value, name) catch (_:Dynamic) return null;
	}

	static function hxcHasField(value:Dynamic, name:String):Bool {
		if (value == null || name == null)
			return false;
		if (isHxcNativeNote(value) && switch (name) {
			case 'ID' | 'noteData' | 'strumTime' | 'mustPress' | 'isSustainNote'
				| 'shouldBeSung' | 'altNum' | 'sourceKind' | 'coolId' | 'lowPriority'
				| 'hxcHsvSaturation' | 'active' | 'visible' | 'alpha' | 'x' | 'y'
				| 'angle' | 'frames' | 'offset' | 'flipY': true;
			default: false;
		})
			return true;
		try return Reflect.hasField(value, name) catch (_:Dynamic) return false;
	}

	/** Recognize native Note instances even when hxcpp reflection hides fields. */
	static function isHxcNativeNote(value:Dynamic):Bool {
		if (value == null)
			return false;
		try {
			var className = Type.getClassName(Type.getClass(value));
			return className == 'Note' || (className != null && className.endsWith('.Note'));
		} catch (_:Dynamic) {
			return false;
		}
	}

	static function setHxcCanceled(value:Dynamic):Void {
		try {
			Reflect.setField(value, 'eventCanceled', true);
			Reflect.setField(value, 'canceled', true);
			Reflect.setField(value, 'cancelled', true);
			if (Reflect.hasField(value, 'activated'))
				Reflect.setField(value, 'activated', true);
		} catch (_:Dynamic) {}
	}

	/**
		Small Lua standard-library shims used by the source adapter.  Keeping
		these here (rather than teaching each imported chart a different spelling)
		means the same implementation is available to converted Lua and native
		HScript modules.
	*/
	public static function luaNumber(value:Dynamic):Float {
		if (value == null)
			return Math.NaN;
		var text = StringTools.trim(Std.string(value));
		if (text == '')
			return Math.NaN;
		var parsed = Std.parseFloat(text);
		return parsed;
	}

	public static function luaString(value:Dynamic):String {
		return value == null ? 'nil' : Std.string(value);
	}

	/** Lua uses one-based, inclusive string indices (negative values count back). */
	public static function luaStringSub(value:Dynamic, start:Int, ?finish:Null<Int>):String {
		var text = value == null ? '' : Std.string(value);
		if (text == '')
			return '';
		var first = luaStringIndex(start, text.length);
		var last = finish == null ? text.length : luaStringIndex(finish, text.length);
		if (first < 0)
			first = 0;
		if (last >= text.length)
			last = text.length - 1;
		if (first >= text.length || last < first)
			return '';
		return text.substr(first, last - first + 1);
	}

	public static function luaStringLen(value:Dynamic):Int {
		return value == null ? 0 : Std.string(value).length;
	}

	public static function luaStringLower(value:Dynamic):String {
		return (value == null ? '' : Std.string(value)).toLowerCase();
	}

	public static function luaStringUpper(value:Dynamic):String {
		return (value == null ? '' : Std.string(value)).toUpperCase();
	}

	/** Literal Lua string.find subset. It returns the one-based start index, or
		nil; HScript call sites consume the first Lua return value as a condition. */
	public static function luaStringFind(value:Dynamic, pattern:Dynamic,
		?initial:Null<Int>, ?plain:Null<Bool>):Dynamic {
		if (value == null || pattern == null)
			return null;
		var source = Std.string(value);
		var needle = Std.string(pattern);
		if (needle == '')
			return null;
		if (plain != true && hasLuaPatternMeta(needle))
			throw 'unsupported Lua string.find pattern';
		var start = initial == null ? 0 : luaStringIndex(initial, source.length);
		if (start < 0) start = 0;
		if (start > source.length) return null;
		var found = source.indexOf(needle, start);
		return found < 0 ? null : found + 1;
	}

	static function hasLuaPatternMeta(pattern:String):Bool {
		for (i in 0...pattern.length)
			if ('.^$*+?-[]()'.indexOf(pattern.charAt(i)) >= 0 || pattern.charAt(i) == '%')
				return true;
		return false;
	}

	/** Literal-only Lua gsub subset, paired with LuaCompat's pattern gate. */
	public static function luaStringGsub(value:Dynamic, pattern:String, replacement:String,
		?maximum:Null<Int>):String {
		if (value == null || pattern == null || replacement == null)
			throw 'lua string.gsub expects string arguments';
		var source = Std.string(value);
		var limit = maximum == null ? source.length + 1 : (maximum < 0 ? 0 : maximum);
		if (pattern == '[^%a%d]') {
			var output = new StringBuf();
			var count = 0;
			for (i in 0...source.length) {
				var ch = source.charAt(i);
				var code = source.charCodeAt(i);
				var alphanumeric = code >= 48 && code <= 57 || code >= 65 && code <= 90
					|| code >= 97 && code <= 122;
				if (!alphanumeric && count < limit) {
					output.add(replacement);
					count++;
				} else output.add(ch);
			}
			return output.toString();
		}
		if (pattern == '%s+') {
			var output = new StringBuf();
			var i = 0;
			var count = 0;
			while (i < source.length) {
				if (isLuaWhitespace(source.charCodeAt(i)) && count < limit) {
					output.add(replacement);
					count++;
					i++;
					while (i < source.length && isLuaWhitespace(source.charCodeAt(i))) i++;
				} else {
					output.add(source.charAt(i));
					i++;
				}
			}
			return output.toString();
		}
		if (pattern == '^%s*(.-)%s*$' && replacement == '%1')
			return limit == 0 ? source : trimLuaWhitespace(source);
		var literal = new StringBuf();
		var meta = '.^$*+?-[]()';
		var i = 0;
		while (i < pattern.length) {
			var c = pattern.charAt(i);
			if (c == '%') {
				i++;
				if (i >= pattern.length || meta.indexOf(pattern.charAt(i)) < 0
					&& pattern.charAt(i) != '%')
					throw 'unsupported lua string.gsub pattern';
				literal.add(pattern.charAt(i));
			} else {
				if (meta.indexOf(c) >= 0)
					throw 'unsupported lua string.gsub pattern';
				literal.add(c);
			}
			i++;
		}
		var needle = literal.toString();
		if (needle == '' || replacement.indexOf('%') >= 0)
			throw 'unsupported lua string.gsub replacement';
		var output = new StringBuf();
		var cursor = 0;
		var count = 0;
		while (count < limit) {
			var at = source.indexOf(needle, cursor);
			if (at < 0) break;
			output.add(source.substr(cursor, at - cursor));
			output.add(replacement);
			cursor = at + needle.length;
			count++;
		}
		output.add(source.substr(cursor));
		return output.toString();
	}

	static function isLuaWhitespace(code:Int):Bool {
		return code == 32 || code >= 9 && code <= 13;
	}

	static function trimLuaWhitespace(value:String):String {
		var start = 0;
		var finish = value.length;
		while (start < finish && isLuaWhitespace(value.charCodeAt(start))) start++;
		while (finish > start && isLuaWhitespace(value.charCodeAt(finish - 1))) finish--;
		return value.substring(start, finish);
	}

	/**
		Small, deterministic subset of Lua's string.format used by imported
		Psych/Kade scripts.  The donor corpus only needs string/integer/float
		formats plus width/zero-padding (for example %02d and %02X); keeping this
		adapter here avoids teaching every converted module a different formatter.
	*/
	public static function luaStringFormat(format:String, ?one:Dynamic, ?two:Dynamic,
		?three:Dynamic, ?four:Dynamic, ?five:Dynamic, ?six:Dynamic,
		?seven:Dynamic, ?eight:Dynamic):String {
		if (format == null)
			return 'nil';
		var values:Array<Dynamic> = [one, two, three, four, five, six, seven, eight];
		var valueIndex = 0;
		var output = new StringBuf();
		var i = 0;
		while (i < format.length) {
			var c = format.charAt(i);
			if (c != '%') {
				output.add(c);
				i++;
				continue;
			}
			if (i + 1 < format.length && format.charAt(i + 1) == '%') {
				output.add('%');
				i += 2;
				continue;
			}
			var cursor = i + 1;
			var zeroPad = false;
			if (cursor < format.length && format.charAt(cursor) == '0') {
				zeroPad = true;
				cursor++;
			}
			var widthText = '';
			while (cursor < format.length) {
				var widthCode = format.charCodeAt(cursor);
				if (widthCode < 48 || widthCode > 57)
					break;
				widthText += format.charAt(cursor++);
			}
			var precision:Null<Int> = null;
			if (cursor < format.length && format.charAt(cursor) == '.') {
				cursor++;
				var precisionText = '';
				while (cursor < format.length) {
					var precisionCode = format.charCodeAt(cursor);
					if (precisionCode < 48 || precisionCode > 57)
						break;
					precisionText += format.charAt(cursor++);
				}
				if (precisionText != '')
					precision = Std.parseInt(precisionText);
			}
			if (cursor >= format.length) {
				output.add('%');
				i++;
				continue;
			}
			var spec = format.charAt(cursor);
			var value:Dynamic = valueIndex < values.length ? values[valueIndex++] : null;
			var rendered = switch (spec) {
				case 'd' | 'i': Std.string(value == null ? 0 : Std.int(Std.parseFloat(Std.string(value))));
				case 'f' | 'F':
					var number = value == null ? 0 : Std.parseFloat(Std.string(value));
					precision == null ? Std.string(number) : formatFloat(number, precision);
				case 'x': formatHex(value, false);
				case 'X': formatHex(value, true);
				case 'q': '"' + luaString(value) + '"';
				case 's': luaString(value);
				default: '%' + spec;
			};
			if (widthText != '') {
				var width = Std.parseInt(widthText);
				while (rendered.length < width)
					rendered = (zeroPad ? '0' : ' ') + rendered;
			}
			output.add(rendered);
			i = cursor + 1;
		}
		return output.toString();
	}

	static function formatFloat(value:Float, precision:Int):String {
		var scale = Math.pow(10, precision);
		var rounded = Math.round(value * scale) / scale;
		var text = Std.string(rounded);
		var dot = text.indexOf('.');
		if (precision <= 0)
			return dot < 0 ? text : text.substr(0, dot);
		if (dot < 0)
			text += '.';
		while (text.length - text.indexOf('.') - 1 < precision)
			text += '0';
		return text;
	}

	static function formatHex(value:Dynamic, uppercase:Bool):String {
		var parsed = value == null ? 0 : Std.int(Std.parseFloat(Std.string(value)));
		var text = StringTools.hex(parsed, 0);
		return uppercase ? text.toUpperCase() : text.toLowerCase();
	}

	/** Return a one-based Lua table length for array or object-style tables. */
	public static function luaTableLength(table:Dynamic):Int {
		if (table == null)
			return 0;
		if (Std.isOfType(table, Array))
			return (cast table : Array<Dynamic>).length;
		try return Reflect.fields(table).length catch (_:Dynamic) return 0;
	}

	/** Return the one-based key yielded by a deterministic pairs/ipairs pass. */
	public static function luaTableKey(table:Dynamic, index:Int):Dynamic {
		if (table == null || index <= 0)
			return null;
		if (Std.isOfType(table, Array))
			return index;
		try {
			var fields = Reflect.fields(table);
			return index <= fields.length ? fields[index - 1] : null;
		} catch (_:Dynamic) {
			return null;
		}
	}

	/** Read a value using the one-based key yielded by luaTableKey(). */
	public static function luaTableValue(table:Dynamic, key:Dynamic):Dynamic {
		if (table == null || key == null)
			return null;
		if (Std.isOfType(table, Array)) {
			var index = Std.int(Std.parseFloat(Std.string(key))) - 1;
			var list:Array<Dynamic> = cast table;
			return index >= 0 && index < list.length ? list[index] : null;
		}
		try return Reflect.field(table, Std.string(key)) catch (_:Dynamic) return null;
	}

	/**
		Translate the small delimiter-pattern form used by Lua string.gmatch
		(split(input, sep) in the imported camera helper).  Arbitrary Lua
		patterns remain intentionally unsupported by LuaCompat.
	*/
	public static function luaStringGmatch(value:Dynamic, pattern:Dynamic):Array<String> {
		var text = value == null ? '' : Std.string(value);
		var expression = pattern == null ? '' : Std.string(pattern);
		var excluded = '';
		if (StringTools.startsWith(expression, '([^') && StringTools.endsWith(expression, ']+)'))
			// Strip the `([^` prefix and `]+)` suffix.  This intentionally only
			// recognizes the delimiter-class split pattern; arbitrary Lua
			// patterns remain unsupported by LuaCompat.
			excluded = expression.substr(3, expression.length - 6);
		if (excluded == '')
			return text == '' ? [] : [text];
		var result:Array<String> = [];
		var current = new StringBuf();
		var currentLength = 0;
		for (i in 0...text.length) {
			var ch = text.charAt(i);
			if (excluded.indexOf(ch) >= 0) {
				if (currentLength > 0) {
					result.push(current.toString());
					current = new StringBuf();
					currentLength = 0;
				}
			} else {
				current.add(ch);
				currentLength++;
			}
		}
		if (currentLength > 0)
			result.push(current.toString());
		return result;
	}

	public static function luaMathRad(value:Float):Float {
		return value * Math.PI / 180;
	}

	public static function luaMathClamp(value:Float, minimum:Float, maximum:Float):Float {
		return Math.max(minimum, Math.min(value, maximum));
	}

	/** Lua's seed is process-global; FlxG owns the actual deterministic RNG. */
	public static function luaMathRandomSeed(_value:Dynamic):Void {}

	public static function luaType(value:Dynamic):String {
		if (value == null)
			return 'nil';
		if (Std.isOfType(value, Bool))
			return 'boolean';
		if (Std.isOfType(value, String))
			return 'string';
		if (Std.isOfType(value, Int) || Std.isOfType(value, Float))
			return 'number';
		if (Std.isOfType(value, Array))
			return 'table';
		// HScript anonymous objects are Lua tables after convertTables(). Native
		// engine instances remain TClass values and therefore keep userdata.
		try {
			switch (Type.typeof(value)) {
				case TObject: return 'table';
				default:
			}
		} catch (_:Dynamic) {}
		return 'userdata';
	}

	public static function luaTableFind(table:Dynamic, value:Dynamic):Int {
		if (table == null || !Std.isOfType(table, Array))
			return -1;
		var list:Array<Dynamic> = cast table;
		for (i in 0...list.length)
			if (list[i] == value)
				return i + 1;
		return -1;
	}

	public static function luaTableClear(table:Dynamic):Void {
		if (table != null && Std.isOfType(table, Array))
			(cast table : Array<Dynamic>).resize(0);
	}

	/**
		A bounded metatable adapter for translated Lua tables.  It deliberately
		models only the `__index`-style method sharing used by imported camera
		templates: the metadata is retained for a later copy and callable fields
		are copied onto the target so HScript property calls remain ordinary
		function calls.  Arbitrary Lua metamethod dispatch is not exposed.
	*/
	public static function luaSetMetatable(table:Dynamic, meta:Dynamic):Dynamic {
		var target = table;
		if (target == null)
			target = {};
		if (Std.isOfType(target, Array)) {
			var values:Array<Dynamic> = cast target;
			var object:Dynamic = {};
			for (i in 0...values.length)
				Reflect.setField(object, Std.string(i + 1), values[i]);
			target = object;
		}
		try Reflect.setField(target, '__luaMetatable', meta) catch (_:Dynamic) {}
		if (meta != null) {
			try {
				for (field in Reflect.fields(meta)) {
					if (field == '__index' || field == '__luaMetatable')
						continue;
					if (!Reflect.hasField(target, field))
						Reflect.setField(target, field, Reflect.field(meta, field));
				}
			} catch (_:Dynamic) {}
		}
		return target;
	}

	/** Read metadata retained by luaSetMetatable(). */
	public static function luaGetMetatable(table:Dynamic):Dynamic {
		if (table == null)
			return null;
		try return Reflect.field(table, '__luaMetatable') catch (_:Dynamic) return null;
	}

	/**
		Clone Lua array/object tables while preserving cycles and the narrow
		metatable metadata above.  `destination` is accepted for Lua call-shape
		compatibility but a mismatched HScript array/object container is replaced.
	*/
	public static function luaTableCopy(source:Dynamic, ?destination:Dynamic,
		?copyMeta:Dynamic, ?depth:Dynamic):Dynamic {
		if (source == null)
			return null;
		var preserveMeta = copyMeta == null || copyMeta == true || Std.string(copyMeta).toLowerCase() == 'true';
		var seenSources:Array<Dynamic> = [];
		var seenTargets:Array<Dynamic> = [];
		return luaTableCopyInner(source, destination, preserveMeta, seenSources, seenTargets);
	}

	static function luaTableCopyInner(source:Dynamic, destination:Dynamic, copyMeta:Bool,
		seenSources:Array<Dynamic>, seenTargets:Array<Dynamic>):Dynamic {
		if (source == null || !luaTableLike(source))
			return source;
		for (i in 0...seenSources.length)
			if (seenSources[i] == source)
				return seenTargets[i];
		var target:Dynamic;
		if (Std.isOfType(source, Array)) {
				target = Std.isOfType(destination, Array) ? destination : [];
			var values:Array<Dynamic> = cast source;
			var targetValues:Array<Dynamic> = cast target;
			seenSources.push(source);
			seenTargets.push(target);
			targetValues.resize(0);
			for (value in values)
				targetValues.push(luaTableCopyInner(value, null, copyMeta, seenSources, seenTargets));
		} else {
			target = destination != null && !Std.isOfType(destination, Array) ? destination : {};
			seenSources.push(source);
			seenTargets.push(target);
			for (field in Reflect.fields(source)) {
				if (field == '__luaMetatable')
					continue;
				Reflect.setField(target, field,
					luaTableCopyInner(Reflect.field(source, field), null, copyMeta, seenSources, seenTargets));
			}
		}
		if (copyMeta) {
			var meta = luaGetMetatable(source);
			if (meta != null)
				target = luaSetMetatable(target, meta);
		}
		return target;
	}

	static function luaTableLike(value:Dynamic):Bool {
		if (value == null || Std.isOfType(value, Array))
			return value != null;
		try {
			switch (Type.typeof(value)) {
				case TObject: return true;
				default: return Reflect.fields(value).length > 0;
			}
		} catch (_:Dynamic) return false;
	}

	/**
		Validate the deliberately small dynamic-global surface used by the
		mounted Psych/Kade donor.  `_G` is an environment table in Lua, but
		making that table writable from converted HScript would let an imported
		module mutate arbitrary interpreter bindings.  Keep the adapter limited to
		the two named local exports plus the captured player/opponent strum slots.
	*/
	public static function luaDynamicGlobalName(value:Dynamic):String {
		if (value == null)
			return '';
		return StringTools.trim(Std.string(value));
	}

	public static function luaDynamicGlobalAllowed(name:String):Bool {
		if (name == 'objects')
			return true;
		if (name == null)
			return false;
		return new EReg('^default(?:Player|Opponent)Strum[XY][0-3]$', '').match(name);
	}

	/** Return whether a dynamic key is one of the explicitly mutable exports. */
	public static function luaDynamicGlobalWritable(name:String):Bool {
		return luaDynamicGlobalAllowed(name);
	}

	/** Read a validated script-local global without exposing the interpreter map. */
	public static function luaGetScriptGlobal(globals:Map<String, Dynamic>, name:Dynamic):Dynamic {
		var key = luaDynamicGlobalName(name);
		if (!luaDynamicGlobalAllowed(key) || globals == null || !globals.exists(key))
			return null;
		return globals.get(key);
	}

	/** Store a validated script-local global; unknown keys are rejected. */
	public static function luaSetScriptGlobal(globals:Map<String, Dynamic>, name:Dynamic,
		value:Dynamic):Bool {
		var key = luaDynamicGlobalName(name);
		if (!luaDynamicGlobalWritable(key) || globals == null)
			return false;
		globals.set(key, value);
		return true;
	}

	/**
		Read one of the immutable baseline receptor positions exposed by Kade's
		`defaultStrum0X` ... `defaultStrum7Y` globals.  The baseline arrays are
		captured by PlayState before a converted modchart receives its callbacks,
		so a later `setActorX/Y` cannot feed back into the default value.
	*/
	public static function luaGetDefaultStrum(defaultX:Array<Float>, defaultY:Array<Float>,
		index:Dynamic, axis:Dynamic):Float {
		if (defaultX == null || defaultY == null)
			return 0;
		var parsed = Std.int(Std.parseFloat(Std.string(index)));
		if (parsed < 0)
			return 0;
		var key = axis == null ? 'x' : Std.string(axis).toLowerCase();
		var values = key == 'y' ? defaultY : key == 'x' ? defaultX : null;
		if (values == null || parsed >= values.length)
			return 0;
		return values[parsed];
	}

	/**
		Read Psych's side-specific bare `defaultPlayerStrumX0` /
		`defaultOpponentStrumY3` globals.  Kade's `defaultStrum0X` family uses one
		combined receptor array, but Psych exposes each side as a zero-based pack;
		keeping that distinction here avoids depending on the render group's order.
	*/
	public static function luaGetSideDefaultStrum(opponentX:Array<Float>, opponentY:Array<Float>,
		playerX:Array<Float>, playerY:Array<Float>, side:Dynamic, index:Dynamic, axis:Dynamic):Float {
		var sideName = side == null ? 'player' : StringTools.trim(Std.string(side)).toLowerCase();
		if (sideName == 'opponent' || sideName == 'enemy' || sideName == 'dad')
			return luaGetDefaultStrum(opponentX, opponentY, index, axis);
		return luaGetDefaultStrum(playerX, playerY, index, axis);
	}

	public static function luaOsClock():Float {
		return haxe.Timer.stamp();
	}

	public static function luaOsTime():Float {
		return Date.now().getTime() / 1000;
	}

	static function luaStringIndex(value:Int, length:Int):Int {
		return value < 0 ? length + value : value - 1;
	}

	/** Return the four-argument Psych note ABI from a native Note-like object. */
	public static function psychNoteCallbackArguments(args:Array<Dynamic>,
		?livePsychNotes:Array<Dynamic>):Array<Dynamic> {
		var note:Dynamic = null;
		if (args != null)
			for (value in args) {
				if (value == null)
					continue;
				try {
					if (isNoteLike(value)) {
						note = value;
						break;
					}
				} catch (_:Dynamic) {}
			}
		var id:Dynamic = 0;
		var direction:Dynamic = 0;
		var noteType:Dynamic = '';
		var sustain:Dynamic = false;
		if (note != null) {
			try {
				// Psych passes the current notes.members slot, not FlxBasic.ID.
				// Lua callbacks such as getPropertyFromGroup('notes', id, ...)
				// index the live group, so use the supplied member snapshot when
				// the caller has one. Keep ID as the compatibility fallback for
				// callers that cannot provide the live group.
				if (livePsychNotes != null)
					id = livePsychNotes.indexOf(note);
				else {
					var rawId = Reflect.getProperty(note, 'ID');
					if (rawId != null)
						id = rawId;
				}
				var rawDirection = Reflect.getProperty(note, 'noteData');
				if (rawDirection != null)
					direction = Math.abs(Std.int(Std.parseFloat(Std.string(rawDirection))));
				var rawType = Reflect.getProperty(note, 'coolId');
				if (rawType == null)
					rawType = Reflect.getProperty(note, 'noteType');
				if (rawType == null) {
					var classes:Dynamic = Reflect.getProperty(note, 'classes');
					if (classes != null && Std.isOfType(classes, Array) && cast(classes, Array<Dynamic>).length > 0)
						rawType = cast(classes, Array<Dynamic>)[0];
				}
				if (rawType != null)
					noteType = rawType;
				var rawSustain = Reflect.getProperty(note, 'isSustainNote');
				if (rawSustain != null)
					sustain = rawSustain;
			} catch (_:Dynamic) {}
		} else if (args != null) {
			// noteMiss(direction, playerOne, note) has no Note for a plain
			// direction miss.  PlayState appends the direction as the third
			// argument so this adapter can preserve it without chart edits.
			for (value in args)
				if (value != null && (Std.isOfType(value, Int) || Std.isOfType(value, Float))) {
					direction = value;
					break;
				}
		}
		return [id, direction, noteType, sustain];
	}

	/** A Psych ghost miss has a direction but no live Note or note-miss ABI. */
	public static function psychMissPressArguments(name:String, args:Array<Dynamic>):Null<Array<Dynamic>> {
		if (canonicalCallback(name) != 'noteMiss' || args == null || args.length < 3
			|| args[0] != null || !Std.isOfType(args[1], Bool)
			|| (!Std.isOfType(args[2], Int) && !Std.isOfType(args[2], Float))) return null;
		return [args[2]];
	}

	/** Return the native hook name represented by a donor lifecycle spelling. */
	public static function canonicalCallback(name:String):String {
		if (name == null)
			return '';
		switch (name.toLowerCase()) {
			case 'oncreate' | 'start': return 'start';
			case 'oncreatepost' | 'createpost': return 'createPost';
			case 'onsongstart' | 'songstart': return 'songStart';
			case 'onupdate' | 'update': return 'update';
			case 'onupdatepost' | 'updatepost': return 'updatePost';
			case 'onbeathit' | 'beathit': return 'beatHit';
			case 'onstephit' | 'stephit': return 'stepHit';
			case 'onsectionhit' | 'sectionhit': return 'sectionHit';
			case 'oncountdowntick' | 'countdowntick': return 'countdownTick';
			case 'oncountdownstep' | 'countdownstep': return 'countdownStep';
			case 'oncountdownend' | 'countdownend': return 'countdownEnd';
			case 'onstartcountdown' | 'startcountdown': return 'startCountdown';
			case 'oncountdownstarted' | 'countdownstarted': return 'countdownStarted';
			case 'oncountdownstart' | 'countdownstart': return 'countdownStart';
			case 'oncustomsubstatecreate' | 'customsubstatecreate': return 'customSubstateCreate';
			case 'oncustomsubstatecreatepost' | 'customsubstatecreatepost': return 'customSubstateCreatePost';
			case 'oncustomsubstateupdate' | 'customsubstateupdate': return 'customSubstateUpdate';
			case 'oncustomsubstateupdatepost' | 'customsubstateupdatepost': return 'customSubstateUpdatePost';
			case 'oncustomsubstatedestroy' | 'customsubstatedestroy': return 'customSubstateDestroy';
			case 'ongoodnotehit' | 'goodnotehit': return 'goodNoteHit';
			case 'onopponentnotehit' | 'opponentnotehit': return 'opponentNoteHit';
			case 'onnotehit' | 'notehit': return 'noteHit';
			case 'onnoteincoming' | 'noteincoming': return 'noteIncoming';
			case 'onnotemiss' | 'notemiss' | 'onmissnote' | 'missnote': return 'noteMiss';
			case 'onnotemisspress' | 'notemisspress': return 'noteMissPress';
			case 'onrecalculaterating' | 'recalculaterating': return 'recalculateRating';
			case 'onopponentnotemiss' | 'opponentnotemiss': return 'opponentNoteMiss';
			case 'onnoteghostmiss' | 'noteghostmiss': return 'noteGhostMiss';
			case 'onsongend' | 'onendsong' | 'songend': return 'songEnd';
			case 'onsongretry' | 'songretry': return 'songRetry';
			case 'onsongevent' | 'songevent': return 'songEvent';
			case 'ontweencompleted' | 'tweencompleted': return 'tweenCompleted';
			case 'ontimercompleted' | 'timercompleted': return 'timerCompleted';
			case 'onpause' | 'pause': return 'pause';
			case 'onresume' | 'resume': return 'resume';
			case 'onpausesubstateopen' | 'pausesubstateopen': return 'subStateOpenEnd';
			case 'onpausesubstateclose' | 'pausesubstateclose': return 'subStateCloseBegin';
			case 'onsongloaded' | 'songloaded': return 'songLoaded';
			case 'onstatechangebegin' | 'statechangebegin': return 'stateChangeBegin';
			case 'onstatechangeend' | 'statechangeend': return 'stateChangeEnd';
			case 'onstateopenend' | 'stateopenend': return 'stateChangeEnd';
			case 'onsubstateclosebegin' | 'substateclosebegin': return 'subStateCloseBegin';
			case 'onsubstateopenend' | 'substateopenend': return 'subStateOpenEnd';
			case 'onsubstatecloseend' | 'substatecloseend': return 'subStateCloseEnd';
			case 'onplaystateenter' | 'playstateenter': return 'playStateEnter';
			case 'ondifficultyswitch' | 'difficultyswitch': return 'difficultySwitch';
			case 'oncapsuleselected' | 'capsuleselected': return 'capsuleSelected';
			case 'onfocusgained' | 'focusgained': return 'focusGained';
			case 'ongameover' | 'ongameoverstart' | 'gameover' | 'gameoverstart': return 'gameOver';
			case 'ondestroy' | 'destroy': return 'destroy';
			default: return name;
		}
	}

	/** Return canonical callback first, followed by known donor spellings. */
	public static function callbackNames(name:String):Array<String> {
		var result:Array<String> = [];
		if (name == null)
			return result;
		// `startCountdown` is also an engine helper seeded into every script
		// interpreter. It is not itself a donor lifecycle callback; treating that
		// helper as one makes a broadcast call the native PlayState method again
		// and recurse while the hook is being dispatched. Psych/Kade use the
		// explicit `onStartCountdown` spelling, so leave the helper out of the
		// callback candidate list and keep the call-site binding available to the
		// script through its normal interpreter variable.
		if (name.toLowerCase() != 'startcountdown')
			appendName(result, name);
		// PlayState still broadcasts a few legacy spellings (`onPause` and
		// `onResume` in particular). Include the canonical name before the rest
		// of the donor aliases so generated HXC callbacks are actually selected.
		var canonical = canonicalCallback(name);
		// PlayState emits the two historical donor spellings directly
		// (`onPause`/`onResume`), so those broadcasts need the reverse lookup.
		// Other lifecycle hooks are emitted canonically; resolving an `onX`
		// request back to `x` would invoke the same callback twice when a caller
		// forwards both spellings (countdownTick is the observable case).
		var reverseBroadcast = name.toLowerCase() == 'onpause'
			|| name.toLowerCase() == 'onresume';
		if (reverseBroadcast && canonical != '' && canonical != name)
			appendName(result, canonical);

			switch (name.toLowerCase()) {
			case 'start':
				appendName(result, 'onCreate');
			case 'createpost':
				appendName(result, 'onCreatePost');
			case 'songstart':
				appendName(result, 'onSongStart');
			case 'update':
				appendName(result, 'onUpdate');
			case 'updatepost':
				appendName(result, 'onUpdatePost');
			case 'beathit':
				appendName(result, 'onBeatHit');
			case 'stephit':
				appendName(result, 'onStepHit');
			case 'sectionhit':
				appendName(result, 'onSectionHit');
			case 'countdownend':
				appendName(result, 'onCountdownEnd');
				case 'countdowntick':
					appendName(result, 'onCountdownTick');
				case 'countdownstep':
					appendName(result, 'onCountdownStep');
			case 'startcountdown':
				appendName(result, 'onStartCountdown');
			case 'countdownstarted':
				appendName(result, 'onCountdownStarted');
			case 'goodnotehit':
				appendName(result, 'onGoodNoteHit');
			case 'opponentnotehit':
				appendName(result, 'onOpponentNoteHit');
			case 'notemiss':
				appendName(result, 'onNoteMiss');
				appendName(result, 'onMissNote');
			case 'notemisspress':
				appendName(result, 'onNoteMissPress');
			case 'recalculaterating':
				appendName(result, 'onRecalculateRating');
			case 'opponentnotemiss':
				appendName(result, 'onOpponentNoteMiss');
			case 'noteghostmiss':
				appendName(result, 'onNoteGhostMiss');
		case 'tweencompleted':
				appendName(result, 'onTweenCompleted');
			case 'timercompleted':
				appendName(result, 'onTimerCompleted');
			case 'destroy':
				appendName(result, 'onDestroy');
			case 'songend':
				appendName(result, 'onEndSong');
				appendName(result, 'onSongEnd');
			case 'songretry':
				appendName(result, 'onSongRetry');
			case 'countdownstart':
				appendName(result, 'onCountdownStart');
			case 'customsubstatecreate':
				appendName(result, 'onCustomSubstateCreate');
			case 'customsubstatecreatepost':
				appendName(result, 'onCustomSubstateCreatePost');
			case 'customsubstateupdate':
				appendName(result, 'onCustomSubstateUpdate');
			case 'customsubstateupdatepost':
				appendName(result, 'onCustomSubstateUpdatePost');
			case 'customsubstatedestroy':
				appendName(result, 'onCustomSubstateDestroy');
			case 'notehit':
				appendName(result, 'onNoteHit');
			case 'noteincoming':
				appendName(result, 'onNoteIncoming');
			case 'songevent':
				appendName(result, 'onSongEvent');
			case 'songloaded':
				appendName(result, 'onSongLoaded');
			case 'statechangebegin':
				appendName(result, 'onStateChangeBegin');
			case 'statechangeend':
				appendName(result, 'onStateChangeEnd');
				appendName(result, 'onStateOpenEnd');
				case 'substateclosebegin':
					appendName(result, 'onSubStateCloseBegin');
					appendName(result, 'onPauseSubstateClose');
				case 'substateopenend':
					appendName(result, 'onSubStateOpenEnd');
					appendName(result, 'onPauseSubstateOpen');
				case 'substatecloseend':
					appendName(result, 'onSubStateCloseEnd');
				case 'playstateenter':
					appendName(result, 'onPlayStateEnter');
			case 'difficultyswitch':
				appendName(result, 'onDifficultySwitch');
			case 'capsuleselected':
				appendName(result, 'onCapsuleSelected');
			case 'focusgained':
				appendName(result, 'onFocusGained');
			case 'gameover':
				appendName(result, 'onGameOver');
				appendName(result, 'onGameOverStart');
			// The old engine used both spellings for these two state hooks.
			case 'pause':
				appendName(result, 'onPause');
			case 'resume':
				appendName(result, 'onResume');
		}
		return result;
	}

	/**
		Adapt callback arguments where a donor lifecycle hook has no parameters.
		HScript currently tolerates extra arguments for ordinary functions, but
		trimming these two creation hooks also makes this safe for strict Lua/HXC
		bridges and preserves their documented signatures.
	*/
	public static function callbackArguments(canonical:String, selected:String,
		args:Array<Dynamic>, preferHxcPayload:Bool = false,
		?livePsychNotes:Array<Dynamic>):Array<Dynamic> {
		if (selected == 'onCreate' || selected == 'onCreatePost' || selected == 'onSongStart'
			|| selected == 'onBeatHit' || selected == 'onStepHit' || selected == 'onSectionHit'
			|| selected == 'onStartCountdown' || selected == 'onCountdownStarted')
			return [];
		if (selected == 'onCountdownTick')
			return args == null || args.length == 0 ? [] : [args[0]];
		if (selected == 'onTimerCompleted') {
			var timerArgs = args == null ? [] : args.copy();
			while (timerArgs.length < 3)
				timerArgs.push(null);
			return timerArgs;
		}
		// V-Slice/HXC song scripts receive one SongEventScriptEvent-like object,
		// while the native chart pump keeps the legacy four-string event ABI.  The
		// canonical songEvent hook is dispatched separately from Psych's onEvent,
		// so adapt only that hook here and keep ordinary onEvent scripts unchanged.
		if ((canonical != null && canonical.toLowerCase() == 'songevent')
			|| (selected != null && selected.toLowerCase() == 'onsongevent')) {
			// fireSongEvent shares one payload across all interpreters so an HXC
			// handler's cancel()/cancelEvent() can suppress the native event.
			if (args != null && args.length == 1 && isHxcSongEventPayload(args[0]))
				return args;
			return [hxcSongEventPayload(args)];
		}
		// V-Slice/HXC lifecycle callbacks receive mutable ScriptEvent-like
		// objects. HxcCompat emits canonical names (countdownStart/songEnd), so
		// recognize both the canonical and donor spellings here. Keeping the
		// object shared with PlayState lets event.cancel() affect the native pump.
		var selectedLower = selected == null ? '' : selected.toLowerCase();
		var canonicalLower = canonical == null ? '' : canonical.toLowerCase();
		// Psych custom-event scripts use a three-value event ABI.  The native
		// event row keeps a fourth slot for HXC/extended charts, but ordinary Lua
		// callbacks must not receive that extra value (all mounted donor scripts
		// declare exactly name, value1, value2).
		if (selectedLower == 'onevent') {
			var eventArgs:Array<Dynamic> = args == null ? [] : args.copy();
			if (eventArgs.length > 3)
				eventArgs.resize(3);
			return eventArgs;
		}
		// Kade/Psych's onMissNote is a one-argument spelling distinct from
		// Psych's four-argument onNoteMiss.  Keep the authored id/direction value
		// in slot one while the native miss route continues to use the full ABI.
		if (selectedLower == 'onmissnote' || selectedLower == 'missnote')
			return [psychNoteCallbackArguments(args, livePsychNotes)[0]];
		// Psych's onGameOverStart and onGameOver callbacks are gates/hooks with no
		// positional arguments. HXC's canonical gameOver callback alone receives
		// its mutable lifecycle object.
		if (selectedLower == 'ongameoverstart' || selectedLower == 'gameoverstart')
			return [];
		if (selectedLower == 'ongameover' || selectedLower == 'gameover'
			|| canonicalLower == 'gameover') {
			if (preferHxcPayload && args != null && args.length > 0
				&& isHxcLifecyclePayload(args[0]))
				return [args[0]];
			return [];
		}
		if (selectedLower == 'countdownstart' || selectedLower == 'oncountdownstart'
			|| canonicalLower == 'countdownstart') {
			if (args != null && args.length > 0 && isHxcLifecyclePayload(args[0]))
				return [args[0]];
			return [hxcLifecyclePayload('countdownStart')];
		}
		if (selectedLower == 'countdownend' || selectedLower == 'oncountdownend'
			|| canonicalLower == 'countdownend') {
			if (preferHxcPayload) {
				if (args != null && args.length > 0 && isHxcLifecyclePayload(args[0]))
					return [args[0]];
				return [hxcLifecyclePayload('countdownEnd', {countdownStep: 4})];
			}
			return [];
		}
		if (selectedLower == 'songend' || selectedLower == 'onsongend'
			|| canonicalLower == 'songend') {
			if (preferHxcPayload) {
				if (args != null && args.length > 0 && isHxcLifecyclePayload(args[0]))
					return [args[0]];
				return [hxcLifecyclePayload('songEnd')];
			}
			return [];
		}
		if (selectedLower == 'songretry' || selectedLower == 'onsongretry'
			|| canonicalLower == 'songretry') {
			// Restart callbacks have no native positional arguments. HXC gets the
			// same mutable lifecycle shape as the other V-Slice hooks; ordinary
			// HScript keeps its historical empty-argument ABI.
			if (preferHxcPayload) {
				if (args != null && args.length > 0 && isHxcLifecyclePayload(args[0]))
					return [args[0]];
				return [hxcLifecyclePayload('songRetry')];
			}
			return args == null ? [] : args.copy();
		}
		if (selectedLower == 'destroy' || selectedLower == 'ondestroy'
			|| canonicalLower == 'destroy') {
			if (preferHxcPayload) {
				if (args != null && args.length > 0 && isHxcLifecyclePayload(args[0]))
					return [args[0]];
				return [hxcLifecyclePayload('destroy')];
			}
			return args == null ? [] : args.copy();
		}
		if (selectedLower == 'pause' || selectedLower == 'onpause'
			|| selectedLower == 'resume' || selectedLower == 'onresume'
			|| canonicalLower == 'pause' || canonicalLower == 'resume') {
			if (preferHxcPayload) {
				if (args != null && args.length > 0 && isHxcLifecyclePayload(args[0]))
					return [args[0]];
				return [hxcLifecyclePayload(canonicalLower == 'resume' || selectedLower == 'resume' ? 'resume' : 'pause')];
			}
			return args == null ? [] : args.copy();
		}
		if (selectedLower == 'onpausesubstateopen' || selectedLower == 'pausesubstateopen'
			|| selectedLower == 'onpausesubstateclose' || selectedLower == 'pausesubstateclose'
			|| canonicalLower == 'substateopenend' || canonicalLower == 'substateclosebegin') {
			if (preferHxcPayload) {
				if (args != null && args.length > 0 && isHxcLifecyclePayload(args[0]))
					return [args[0]];
				var substateKind = canonicalLower == 'substateclosebegin'
					|| selectedLower.indexOf('close') >= 0 ? 'subStateCloseBegin' : 'subStateOpenEnd';
				return [hxcLifecyclePayload(substateKind, args == null || args.length == 0 ? {} : args[0])];
			}
			return args == null ? [] : args.copy();
		}
		if (selectedLower == 'difficultyswitch' || selectedLower == 'ondifficultyswitch'
			|| selectedLower == 'capsuleselected' || selectedLower == 'oncapsuleselected'
			|| canonicalLower == 'difficultyswitch' || canonicalLower == 'capsuleselected') {
			if (args != null && args.length > 0 && isHxcLifecyclePayload(args[0]))
				return [args[0]];
			var kind = canonicalLower == 'capsuleselected' || selectedLower == 'capsuleselected'
				? 'capsuleSelected' : 'difficultySwitch';
			return [hxcLifecyclePayload(kind, args == null || args.length == 0 ? {} : args[0])];
		}
		if (selectedLower == 'noteincoming' || selectedLower == 'onnoteincoming'
			|| canonicalLower == 'noteincoming') {
			var incomingArgs:Array<Dynamic> = args == null ? [] : args;
			for (value in incomingArgs)
				if (isHxcLifecyclePayload(value))
					return [value];
			var note:Dynamic = null;
			if (args != null)
				for (value in args)
					if (isNoteLike(value)) {
						note = value;
						break;
					}
			return [hxcNoteIncomingPayload(note)];
		}
		// HXC callbacks receive one mutable NoteScriptEvent-like object.  The
		// ordinary HScript/Psych bridge below intentionally keeps its historical
		// four-primitive ABI, so only interpreters loaded from an HXC source opt in
		// to the object adapter.
		if (preferHxcPayload && isHxcNoteCallback(selectedLower)) {
			// PlayState may pass one shared payload as an extra argument so the
			// native pump can observe cancel()/kill() after all HXC interpreters
			// return. Reuse it instead of creating a disconnected proxy.
			if (args != null)
				for (value in args)
					if (isHxcNotePayload(value))
						return [value];
		return [hxcNoteCallbackPayload(args, selectedLower)];
		}
		// Psych exposes note callbacks as primitive values while the native
		// Modding Plus hooks historically received the live Note object.  Route
		// both spellings through the same ABI adapter so an imported donor script
		// does not need a chart-side wrapper.  The adapter deliberately also
		// accepts the direct spellings (goodNoteHit/noteMiss): several Psych packs
		// use those names without the `on` prefix.
		switch (selected == null ? '' : selected.toLowerCase()) {
			case 'ongoodnotehit' | 'goodnotehit' | 'onopponentnotehit' | 'opponentnotehit'
				| 'onnotehit' | 'notehit' | 'onnotemiss' | 'notemiss' | 'onmissnote' | 'missnote'
				| 'onopponentnotemiss' | 'opponentnotemiss':
				return psychNoteCallbackArguments(args, livePsychNotes);
		}
		return args == null ? [] : args.copy();
	}

	static function isHxcNoteCallback(selectedLower:String):Bool {
		return switch (selectedLower == null ? '' : selectedLower) {
			case 'ongoodnotehit' | 'goodnotehit' | 'onopponentnotehit' | 'opponentnotehit'
				| 'onnotehit' | 'notehit' | 'onnotemiss' | 'notemiss'
				| 'onopponentnotemiss' | 'opponentnotemiss'
				| 'onnoteghostmiss' | 'noteghostmiss': true;
			default: false;
		};
	}

	/**
		Build the small, mutable event surface used by the HXC corpus.  This is
		intentionally a data adapter, not a donor class implementation: event
		names and the three legacy values remain authored by the chart, while the
		V-Slice fields (`eventData`, `value1`/`value2`, and cancellation methods)
		are supplied by the native runtime.
	*/
	public static function hxcSongEventPayload(args:Array<Dynamic>):Dynamic {
		var name = eventArgument(args, 0, '');
		var value1 = eventArgument(args, 1, '');
		var value2 = eventArgument(args, 2, '');
		var value3 = eventArgument(args, 3, '');
		var eventTime:Dynamic = args == null || args.length <= 4 ? null : args[4];
		var value:Dynamic = {value1: value1, value2: value2, value3: value3};
		// Unknown V-Slice events are preserved as a JSON object in value1.  Keep
		// that object available to an HXC event handler without changing the chart
		// row or making arbitrary donor classes executable.  A scalar parse
		// result (`"1"` -> 1) is not a payload object: replacing the anonymous
		// value with it would make every later typed-getter/native field write
		// throw on hxcpp, so only real objects take over.
		if (value2 == '' && value1 != null) {
			try {
				var parsed:Dynamic = Json.parse(Std.string(value1));
				if (parsed != null && Type.typeof(parsed) == TObject)
					value = parsed;
			} catch (_:Dynamic) {}
		}
		if (value == null)
			value = {};
		setEventValueIfMissing(value, 'value1', value1);
		setEventValueIfMissing(value, 'value2', value2);
		setEventValueIfMissing(value, 'value3', value3);
		// Common converted event aliases let the same HXC callback inspect the
		// named V-Slice fields even after the event has crossed the legacy ABI.
		mergeEventValueObject(value, value3);
		switch (eventName(name).toLowerCase()) {
			case 'change character':
				setEventValueIfMissing(value, 'character', value1);
				setEventValueIfMissing(value, 'newchar', value2);
			case 'change stage':
				setEventValueIfMissing(value, 'stageId', value1);
				setEventValueIfMissing(value, 'stageid', value1);
			case 'camera follow pos':
				setEventValueIfMissing(value, 'x', value1);
				setEventValueIfMissing(value, 'y', value2);
			case 'add camera zoom':
				setEventValueIfMissing(value, 'gamezoom', value1);
				setEventValueIfMissing(value, 'hudzoom', value2);
			case 'note swap':
				setEventValueIfMissing(value, 'strumline', value1);
				setEventValueIfMissing(value, 'notestyle', value2);
				setEventValueIfMissing(value, 'noteStyle', value2);
			case 'zoom camera':
				setEventValueIfMissing(value, 'zoom', value1);
				setEventValueIfMissing(value, 'duration', value2);
			case 'play video':
				setEventValueIfMissing(value, 'path', value1);
			case 'camera flash':
				setEventValueIfMissing(value, 'color', value1);
				setEventValueIfMissing(value, 'duration', value2);
			case 'vignette':
				setEventValueIfMissing(value, 'intensity', value1);
				setEventValueIfMissing(value, 'duration', value2);
			case 'markov popups':
				setEventValueIfMissing(value, 'x', value1);
				setEventValueIfMissing(value, 'y', value2);
			case 'camera fade':
				setEventValueIfMissing(value, 'shouldFadeIn', value1 == '1' || value1.toLowerCase() == 'true');
				setEventValueIfMissing(value, 'duration', value2);
			case 'lyrics':
				setEventValueIfMissing(value, 'text', value1);
				setEventValueIfMissing(value, 'duration', value2);
		}
		var eventData:Dynamic = {eventKind: name, value: value, activated: false, time: eventTime,
			nativeHandled: false, handled: false};
		var payload:Dynamic = {eventKind: name, eventData: eventData, eventCanceled: false,
			canceled: false, cancelled: false, nativeHandled: false, handled: false, value: value};
		Reflect.setField(payload, 'time', eventTime);
		var cancel = function() {
			Reflect.setField(payload, 'eventCanceled', true);
			Reflect.setField(payload, 'canceled', true);
			Reflect.setField(payload, 'cancelled', true);
			Reflect.setField(eventData, 'activated', true);
		};
		Reflect.setField(payload, 'cancel', cancel);
		Reflect.setField(payload, 'cancelEvent', cancel);
		var claimNative = function() {
			HxcCompatRuntime.markSongEventNativeHandled(payload);
		};
		Reflect.setField(payload, 'markNativeHandled', claimNative);
		Reflect.setField(payload, 'claimNative', claimNative);
		return hxcAttachPayload(payload);
	}

	/**
		Create the mutable ScriptEvent-like object used by V-Slice/HXC lifecycle
		hooks. The donor event classes expose several equivalent cancellation names;
		all aliases update one shared flag so the native PlayState pump can honor a
		callback's decision without executing donor classes.
	*/
	public static function hxcLifecyclePayload(kind:String, ?value:Dynamic):Dynamic {
		var eventValue:Dynamic = value == null ? {} : value;
		var eventData:Dynamic = {eventKind: kind == null ? '' : kind,
			value: eventValue, activated: false};
		var payload:Dynamic = {eventKind: eventData.eventKind, eventData: eventData,
			eventCanceled: false, canceled: false, cancelled: false};
		// ScriptEvent subclasses expose their common fields directly as well as
		// through eventData. Preserve that shallow data view for generic lifecycle
		// hooks such as onSongLoaded/events and onStateChangeEnd/targetState.
		try {
			for (field in Reflect.fields(eventValue))
				if (!Reflect.hasField(payload, field))
					Reflect.setField(payload, field, Reflect.field(eventValue, field));
		} catch (_:Dynamic) {}
		var cancel = function() {
			Reflect.setField(payload, 'eventCanceled', true);
			Reflect.setField(payload, 'canceled', true);
			Reflect.setField(payload, 'cancelled', true);
			Reflect.setField(eventData, 'activated', true);
		};
		Reflect.setField(payload, 'cancel', cancel);
		Reflect.setField(payload, 'cancelEvent', cancel);
		return hxcAttachPayload(payload);
	}

	/** Build the shared payload used by native Freeplay selection boundaries. */
	public static function hxcFreeplayPayload(kind:String, state:Dynamic,
		?capsule:Dynamic, ?difficulty:Dynamic, ?variation:Dynamic):Dynamic {
		return hxcLifecyclePayload(kind, {
			targetState: state,
			freeplayState: state,
			capsule: capsule,
			difficulty: difficulty,
			variation: variation
		});
	}

	/** Return the payload for an HXC countdown-start callback. */
	public static function hxcCountdownStartPayload():Dynamic {
		// PlayState resets native misses before loading HXC modules. Begin the
		// active tally here so retry/countdown cleanup cannot inherit another song.
		HxcCompatRuntime.beginActiveSong();
		return hxcLifecyclePayload('countdownStart', {countdownStep: 0});
	}

	/** Return the V-Slice countdown-step payload used by onCountdownStep modules. */
	public static function hxcCountdownStepPayload(step:Int):Dynamic {
		var label = switch (step) {
			case 0: 'THREE';
			case 1: 'TWO';
			case 2: 'ONE';
			case 3: 'GO';
			default: Std.string(step);
		};
		return hxcLifecyclePayload('countdownStep', {step: label, countdownStep: step});
	}

	/** Return the payload for an HXC song-end callback. */
	public static function hxcSongEndPayload(songPosition:Dynamic, songLength:Dynamic):Dynamic {
		return hxcLifecyclePayload('songEnd', {
			songPosition: songPosition,
			songLength: songLength
		});
	}

	/** Return the payload for a note entering the active strumline queue. */
	public static function hxcNoteIncomingPayload(note:Dynamic):Dynamic {
		// Seed/retain the active-song tally before the callback can remove a note.
		// The runtime observes the live note separately so lazy standalone calls do
		// not lose the first player note after it leaves the unspawn queue.
		HxcCompatRuntime.observeIncoming(note);
		// Incoming callbacks use the same NoteScriptEvent shape as hit/miss
		// callbacks. Keep the live Note separately for the native pump, while
		// `event.note` and `eventData.value.note` expose the normalized view.
		var view = hxcNoteView(note);
		var payload = hxcLifecyclePayload('noteIncoming', {note: view});
		Reflect.setField(payload, 'note', view);
		Reflect.setField(payload, 'nativeNote', note);
		return payload;
	}

	static function isHxcNotePayload(value:Dynamic):Bool {
		if (value == null)
			return false;
		try {
			return Reflect.hasField(value, 'nativeNote')
				&& Reflect.hasField(value, 'note')
				&& Reflect.hasField(value, 'eventData');
		} catch (_:Dynamic) {
			return false;
		}
	}

	static function isHxcLifecyclePayload(value:Dynamic):Bool {
		if (value == null)
			return false;
		try {
			return Reflect.hasField(value, 'eventData')
				&& Reflect.hasField(value, 'eventCanceled')
				&& Reflect.hasField(value, 'cancelEvent');
		} catch (_:Dynamic) {
			return false;
		}
	}

	static function isNoteLike(value:Dynamic):Bool {
		if (value == null)
			return false;
		try {
			// hxcpp's Reflect.hasField does not recognize ordinary class members.
			// Read the public properties instead; zero directions and false sustain
			// flags are valid values, so test against null rather than truthiness.
			return Reflect.getProperty(value, 'noteData') != null
				|| Reflect.getProperty(value, 'isSustainNote') != null;
		} catch (_:Dynamic) {
			return false;
		}
	}

	static function eventArgument(args:Array<Dynamic>, index:Int, fallback:String):String {
		if (args == null || index < 0 || index >= args.length || args[index] == null)
			return fallback;
		return Std.string(args[index]);
	}

	static function isHxcSongEventPayload(value:Dynamic):Bool {
		if (value == null)
			return false;
		try {
			return Reflect.hasField(value, 'eventData') && Reflect.hasField(value, 'eventCanceled');
		} catch (_:Dynamic) {
			return false;
		}
	}

	static function setEventValueIfMissing(value:Dynamic, field:String, fieldValue:Dynamic):Void {
		if (value == null || field == null || field == '')
			return;
		try {
			if (!Reflect.hasField(value, field))
				Reflect.setField(value, field, fieldValue);
		} catch (_:Dynamic) {}
	}

	/** Merge a packed V-Slice options object without replacing authored values. */
	static function mergeEventValueObject(value:Dynamic, packed:String):Void {
		if (value == null || packed == null || StringTools.trim(packed) == '')
			return;
		var parsed:Dynamic;
		try {
			parsed = Json.parse(packed);
		} catch (_:Dynamic) {
			return;
		}
		if (parsed == null)
			return;
		try {
			for (field in Reflect.fields(parsed))
				setEventValueIfMissing(value, field, Reflect.field(parsed, field));
		} catch (_:Dynamic) {}
	}

	/** Normalize a nested Psych/Kade property path to the native root names. */
	public static function propertyPath(path:Dynamic):String {
		if (path == null)
			return '';
		var value = StringTools.trim(Std.string(path));
		if (value == '')
			return value;
		value = StringTools.replace(value, '\\', '.');
		for (prefix in ['game.', 'currentPlayState.', 'PlayState.instance.', 'states.PlayState.instance.']) {
			if (value.startsWith(prefix)) {
				value = value.substr(prefix.length);
				break;
			}
		}
		if (value == 'states.PlayState' || value == 'PlayState.instance')
			return 'PlayState';
		// Psych exposes one `comboGroup` containing the floating rating/combo
		// sprites.  This fork keeps those judgements as transient sprites and
		// owns their visibility through `showRatings`; route the mounted donor's
		// visibility write to that native gate instead of dropping the unknown
		// group root.  Keep this narrow: other comboGroup members do not have a
		// deterministic native equivalent and must remain ordinary paths.
		if (value.toLowerCase() == 'combogroup.visible')
			return 'showRatings';
		var dot = value.indexOf('.');
		var root = dot < 0 ? value : value.substr(0, dot);
		var suffix = dot < 0 ? '' : value.substr(dot);
		var normalizedRoot = propertyRoot(root);
		return normalizedRoot + suffix;
	}

	/** Normalize a property root while preserving custom sprite names. */
	public static function propertyRoot(root:String):String {
		if (root == null)
			return '';
		switch (root.toLowerCase()) {
			case 'camother' | 'other':
				return 'camOther';
			case 'camgamehud':
				return 'camHUD';
			case 'camfollowpos' | 'camerafollowpos':
				return 'camFollow';
			case 'iscameraonforcedpos' | 'iscameraonforcedposition':
				return 'forceCamera';
			case 'opponentstrums' | 'opponentstrumline':
				return 'enemyStrums';
			case 'playerstrums' | 'playerstrumline':
				return 'playerStrums';
			case 'grpnotesplashes' | 'notesplashes':
				return 'noteSplashes';
			case 'cameraspeed':
				return 'camSpeed';
			case 'camzoomingmult':
				return 'camZoomIntensity';
			case 'camerabopmultiplier':
				// TAKEOVER/Psych spelling for the native beat-bop multiplier.
				return 'camZoomIntensity';
			case 'camzoomingdecay':
				return 'camZoomDecay';
			case 'shownotesplashes':
				return 'showNoteSplashes';
			case 'cpuscontrolled' | 'cpucontrolled':
				return 'cpuControlled';
			case 'songmisses':
				return 'misses';
			case 'songposition':
				return 'songPosition';
			// Psych's stock time text is named timeTxt; this engine exposes the
			// same live FlxText as timeBar.
			case 'timetxt':
				return 'timeBar';
			default:
				return root;
		}
	}

	/**
		Return Psych's three-component health colour array for a live actor.

		Psych stores this on Character, while this fork keeps authored colours on
		the matching HealthIcon and role defaults on Character.  Property scripts
		must see RGB components (not the packed FlxColor integer), so resolve the
		icon first and keep the conversion in this shared adapter.
	*/
	public static function psychHealthColorArray(actor:Dynamic, playerActor:Dynamic,
		opponentActor:Dynamic, girlfriendActor:Dynamic, playerIcon:Dynamic,
		opponentIcon:Dynamic):Array<Int> {
		if (actor == null)
			return [255, 255, 255];

		// Preserve a donor/native Character implementation if one already
		// provides the exact property. This also keeps the adapter future-proof
		// for imported actor subclasses.
		var direct:Dynamic = null;
		try direct = Reflect.field(actor, 'healthColorArray') catch (_:Dynamic) {}
		if (Std.isOfType(direct, Array)) {
			var values:Array<Dynamic> = cast direct;
			if (values.length >= 3) {
				var directResult:Array<Int> = [];
				for (index in 0...3) {
					var number = Std.parseFloat(Std.string(values[index]));
					directResult.push(Math.isNaN(number) ? 0 : Std.int(number));
				}
				return directResult;
			}
			if (values.length > 0)
				return psychColorComponents(values[0]);
		}

		var icon:Dynamic = null;
		if (actor == playerActor)
			icon = playerIcon;
		else if (actor == opponentActor)
			icon = opponentIcon;
		else if (actor == girlfriendActor)
			icon = null;
		if (icon != null) {
			var healthColors:Dynamic = null;
			try healthColors = Reflect.field(icon, 'healthColors') catch (_:Dynamic) {}
			if (Std.isOfType(healthColors, Array)) {
				var colors:Array<Dynamic> = cast healthColors;
				if (colors.length > 0)
					return psychColorComponents(colors[0]);
			}
		}

		// GF has no separate native HealthIcon in this fork. Use its authored
		// role colour before the white fallback, and retain player/enemy defaults
		// for actors whose icon is still loading.
		var roleField = actor == playerActor ? 'playerColor' : 'enemyColor';
		var roleColor:Dynamic = null;
		try roleColor = Reflect.field(actor, roleField) catch (_:Dynamic) {}
		if (roleColor != null)
			return psychColorComponents(roleColor);
		var genericColor:Dynamic = null;
		try genericColor = Reflect.field(actor, 'color') catch (_:Dynamic) {}
		return genericColor == null ? [255, 255, 255] : psychColorComponents(genericColor);
	}

	/** Convert a packed FlxColor (or a colour-like object) to RGB components. */
	public static function psychColorComponents(value:Dynamic):Array<Int> {
		if (value == null)
			return [255, 255, 255];
		var red:Dynamic = null;
		var green:Dynamic = null;
		var blue:Dynamic = null;
		try red = Reflect.getProperty(value, 'red') catch (_:Dynamic) {}
		try green = Reflect.getProperty(value, 'green') catch (_:Dynamic) {}
		try blue = Reflect.getProperty(value, 'blue') catch (_:Dynamic) {}
		if (red != null && green != null && blue != null)
			return [Std.int(red), Std.int(green), Std.int(blue)];
		try {
			var packed = Std.int(value);
			return [(packed >> 16) & 0xFF, (packed >> 8) & 0xFF, packed & 0xFF];
		} catch (_:Dynamic) {
			return [255, 255, 255];
		}
	}

	/** Return the native event spelling used by PlayState's switch. */
	public static function eventName(name:Dynamic):String {
		if (name == null)
			return '';
		var original = StringTools.trim(Std.string(name));
		switch (original.toLowerCase()) {
			// FPS Plus/Kade sidecars keep their event names in the old camel-case
			// vocabulary.  These are chart events (not Lua custom-event files), so
			// route them before PlayState's native switch sees the row.
			case 'camzoom':
				return 'Legacy Camera Zoom';
			case 'cammove' | 'camera move':
				return 'Camera Follow Pos';
			case 'togglecammovement' | 'toggle camera movement':
				return 'Toggle Camera Movement';
			case 'camera target' | 'cameratarget':
				return 'Camera Target';
			case 'camera zoom hold' | 'camerazoomhold':
				return 'Set Cam Zoom';
			case 'set cam zoomboom' | 'set cam zoomboomslow':
				return 'Legacy Camera Zoom';
			case 'clear lyrics' | 'clearlyrics':
				return 'Clear Lyrics';
			case 'second lyric line' | 'secondlyricline':
				return 'Second Lyric Line';
			case 'cam boom speed' | 'camboomspeed':
				return 'Cam Boom Speed';
			case 'cambopbig' | 'cam bop big':
				return 'Add Camera Zoom';
			case 'screenshakesimple' | 'screen shake simple':
				return 'Screen Shake';
			case 'change  scroll speed':
				return 'Change Scroll Speed';
			case 'playvideo' | 'play video' | 'playvideoevent':
				return 'Play Video';
			case 'cameraflashevent' | 'extra-events-cameraflashevent':
				return 'Camera Flash';
			case 'camerafadeevent' | 'extra-events-camerafadeevent':
				return 'Camera Fade';
			case 'addlyrics' | 'add lyrics' | 'addlyricsevent' | 'extra-events-addlyricsevent':
				return 'Lyrics';
			case 'zoomcamera' | 'zoom camera':
				return 'Zoom Camera';
			case 'addcamzoompsych' | 'add camera zoom psych' | 'addcamerazoom' | 'add camera zoom':
				return 'Add Camera Zoom';
			case 'noteswap' | 'noteswapevent' | 'note swap' | 'note style swap' | 'notestyleswap' | 'notestyle swapper':
				return 'Note Swap';
			case 'charchange' | 'changecharactercl':
				return 'Change Character';
			case 'camera follow position' | 'camera follow pos' | 'camera position':
				return 'Camera Follow Pos';
			case 'set default cam zoom' | 'set camera zoom' | 'setcamzoom' | 'change camera zoom' | 'cambiar zoom default':
				return 'Set Cam Zoom';
			case 'camera zoom event' | 'camerazoom':
				return 'Camera Zoom';
			case 'setproperty' | 'set property':
				return 'Set Property';
			case 'scrollspeed':
				return 'Change Scroll Speed';
			case 'setcamerabop':
				return 'Set Camera Bop';
			case 'screen shake event' | 'screenshake':
				return 'Screen Shake';
			case 'flash' | 'flash camera' | 'camera flash event' | 'cameraflash':
				return 'Camera Flash';
			case 'camera fade' | 'fade camera' | 'fade camera event' | 'camerafade':
				return 'Camera Fade';
			case 'lyrics event':
				return 'Lyrics';
			// V-Slice/HXC event classes are authored as ScriptedSongEvent
			// identities. Keep their names in this centralized table so both the
			// importer and the native event pump select the same implementation;
			// the donor event class/body is never instantiated at runtime.
			case 'vignevent' | 'vignetteevent' | 'extra-events-vignevent':
				return 'Vignette';
			case 'eyepopup' | 'markovpopupsevent' | 'markov popups' | 'markov pop ups':
				return 'Markov Popups';
			case 'playanimation' | 'play animation':
				return 'Play Animation';
			case 'sethealthicon' | 'set health icon':
				return 'Set Health Icon';
			case 'changecharacter' | 'change character cl':
				return 'Change Character';
			case 'focuscamera' | 'focus camera':
				return 'Focus Camera';
			case 'changestage' | 'change stage' | 'swapstage' | 'swap stage':
				return 'Change Stage';
			default:
				return original;
		}
	}

	/** Extract a static HXC event-sprite plan without running donor code. */
	public static function eventSpriteDescriptorFromSource(source:String):Dynamic {
		var descriptor = HxcEventSpriteDescriptor.extract(source);
		if (descriptor == null)
			return null;
		var sourceName:Dynamic = Reflect.field(descriptor, 'sourceName');
		var canonical = eventName(sourceName == null ? '' : Std.string(sourceName));
		Reflect.setField(descriptor, 'canonicalName', canonical);
		return HxcEventSpriteDescriptor.normalize(descriptor);
	}

	/**
		Find event-owned assets in one imported HXC source without executing it.
		This intentionally recognizes authored event/class identities, not song
		folders or chart names, so the import side can retain the same provenance
		boundary as the runtime adapter.
	*/
	public static function eventAssetNamesInSource(source:String):Array<String> {
		var result:Array<String> = [];
		var descriptor = eventSpriteDescriptorFromSource(source);
		if (descriptor == null)
			return result;
		var key:Dynamic = Reflect.field(descriptor, 'atlasKey');
		if (key != null && StringTools.trim(Std.string(key)) != '')
			result.push(Std.string(key));
		return result;
	}

	/**
		Normalize a legacy event and its values together.  A name-only alias is
		not enough for old FPS/Kade rows: `camZoom` and `Flash`, for example,
		store their duration/colour in the opposite slots from the native Psych
		events.  Keep this adapter data-only so donor charts stay untouched and
		PlayState remains the sole owner of the actual camera operation.
	*/
	public static function routeLegacyEvent(name:Dynamic, v1:Dynamic, v2:Dynamic,
			?v3:Dynamic):EngineCompatEventRoute {
		var original = name == null ? '' : StringTools.trim(Std.string(name));
		var route:EngineCompatEventRoute = {
			name: eventName(original),
			v1: v1 == null ? '' : Std.string(v1),
			v2: v2 == null ? '' : Std.string(v2),
			v3: v3 == null ? '' : Std.string(v3)
		};
		switch (original.toLowerCase()) {
			case 'addcamzoompsych':
				// TAKEOVER's Psych-named event writes the camera-bop multiplier
				// rather than immediately changing camGame. Keep the canonical
				// event identity, but carry this semantic variant in v3 so the
				// native pump can select the same operation without a chart edit.
				route.name = 'Add Camera Zoom';
				route.v3 = 'psych';
			case 'noteswap' | 'note swap' | 'note style swap' | 'notestyleswap' | 'notestyle swapper':
				route.name = 'Note Swap';
				route.v1 = StringTools.trim(route.v1) == '' ? 'both' : route.v1;
				route.v2 = StringTools.trim(route.v2) == '' ? 'normal' : route.v2;
			case 'flash':
				// PERFEXION's Flash.lua uses value1=duration and value2 as a
				// small palette id. Camera Flash uses value1=colour/value2=duration.
				route.name = 'Camera Flash';
				route.v1 = legacyFlashColour(route.v2);
				route.v2 = route.v1 == '' ? '' : (v1 == null ? '' : Std.string(v1));
			case 'screenshakesimple' | 'screen shake simple':
				// The donor custom event is a fixed, light shake gated by value1=1.
				// Preserve a disabled row as an inert native event instead of
				// inventing a chart-specific branch in PlayState.
				route.name = 'Screen Shake';
				if (StringTools.trim(route.v1) == '1') {
					route.v1 = '0.3,0.01';
					route.v2 = '0.3,0.01';
				} else {
					route.v1 = '';
					route.v2 = '';
				}
			case 'camera zoom hold':
				// FPS Plus uses this as an immediate/default zoom target.
				route.name = 'Set Cam Zoom';
			case 'set cam zoomboom' | 'set cam zoomboomslow' | 'camzoom':
				// These donor events tween in seconds (unlike V-Slice's step
				// duration), so keep a distinct native route.
				route.name = 'Legacy Camera Zoom';
			case 'cambopbig' | 'cam bop big':
				// FPS Plus emits this event without values for a larger ordinary
				// camera bop.  Add Camera Zoom is the native equivalent; use the
				// donor's apparent two-times stock pulse while preserving authored
				// values if a later exporter supplies them.
				route.name = 'Add Camera Zoom';
				if (StringTools.trim(route.v1) == '') route.v1 = '0.03';
				if (StringTools.trim(route.v2) == '') route.v2 = '0.06';
			case 'togglecammovement' | 'toggle camera movement':
				route.name = 'Toggle Camera Movement';
			case 'cammove' | 'camera move':
				route.name = 'Camera Follow Pos';
			case 'change  scroll speed':
				route.name = 'Change Scroll Speed';
			default:
		}
		// Converted V-Slice charts keep their authored event kinds verbatim (a
		// donor song script's own handlers key on those spellings), so resolve
		// the canonical name and value slots at dispatch time through the same
		// single mapping the importer consults. Only a real object payload
		// (V-Slice rows carry JSON in v1) takes over, so legacy spellings with
		// positional string slots - which the switch above may have already
		// adapted - keep their routing.
		{
			var vsliceValues:Dynamic = null;
			var raw:Dynamic = route.v1;
			if (raw == null || Std.string(raw).indexOf('{') != 0)
				raw = route.v3;
			if (raw != null && Std.string(raw).indexOf('{') == 0) {
				try vsliceValues = Json.parse(Std.string(raw)) catch (_:Dynamic) vsliceValues = null;
			}
			if (vsliceValues != null) {
				var vslice = routeVSliceEvent(original, vsliceValues);
				if (vslice != null && vslice.name != null) {
					// A legacy semantic marker (for example the Psych camera-bop
					// variant in v3) survives the payload adaptation.
					var marker = route.v3 == 'psych' && vslice.v3 == '' ? 'psych' : vslice.v3;
					route.name = vslice.name;
					route.v1 = vslice.v1;
					route.v2 = vslice.v2;
					route.v3 = marker;
				}
			}
		}
		return route;
	}

	/**
		A referenced Psych `custom_events/Flash.lua` owns the legacy `Flash`
		spelling when it is loaded for the selected chart. Keep the native alias
		as a fallback for charts without that script, and leave canonical
		`Camera Flash` events on the native path.
	*/
	public static function psychFlashScriptOwnsLegacyEvent(name:Dynamic,
		flashScriptLoaded:Bool):Bool {
		return flashScriptLoaded && name != null
			&& StringTools.trim(Std.string(name)).toLowerCase() == 'flash';
	}

	/**
		A referenced Psych custom-event script owns its non-built-in event when
		present; otherwise PlayState may run its native legacy fallback. Keep the
		exact built-in spellings from Psych 0.6.3 and 0.7.3 triggerEvent switches
		native so onEvent remains observational for those events. Compare before
		alias routing so a custom script named for a legacy alias can own it.
		Sources:
		https://github.com/ShadowMario/FNF-PsychEngine/blob/0.6.3/source/PlayState.hx#L3184-L3538
		https://github.com/ShadowMario/FNF-PsychEngine/blob/0.7.3/source/states/PlayState.hx#L1824-L2046
	*/
	public static function psychCustomEventOwnsNativeFallback(name:Dynamic,
		customScriptLoaded:Bool):Bool {
		if (!customScriptLoaded || name == null)
			return false;

		return switch (StringTools.trim(Std.string(name))) {
			case 'Dadbattle Spotlight' | 'Hey!' | 'Set GF Speed' | 'Philly Glow'
				| 'Kill Henchmen' | 'Add Camera Zoom' | 'Trigger BG Ghouls'
				| 'Play Animation' | 'Camera Follow Pos' | 'Alt Idle Animation'
				| 'Screen Shake' | 'Change Character' | 'BG Freaks Expression'
				| 'Change Scroll Speed' | 'Set Property' | 'Play Sound':
				false;
			default:
				true;
		};
	}

public static function lyricActor(value:Dynamic):String {
		if (value == null)
			return '';
		var raw = StringTools.trim(Std.string(value));
		return switch (raw.toLowerCase()) {
			case '' | 'none' | 'all': '';
			case 'boyfriend' | 'player1': 'bf';
			case 'opponent' | 'player2': 'dad';
			case 'girlfriend' | 'player3': 'gf';
			default: raw.toLowerCase();
		};
	}

	/** Accept legacy numeric lyric durations and Funkadelix actor ids. */
	public static function lyricDurationOrActor(value:Dynamic):Dynamic {
		var raw = value == null ? '' : StringTools.trim(Std.string(value));
		if (raw == '')
			return {duration: 0.0, actor: ''};
		var numeric = Std.parseFloat(raw);
		return Math.isNaN(numeric) ? {duration: 0.0, actor: raw} : {duration: numeric, actor: ''};
	}

	/** Convert PERFEXION's numeric flash palette to a native ARGB token. */
	static function legacyFlashColour(value:String):String {
		return switch (value == null ? '' : StringTools.trim(value)) {
			case '0': 'FF000000';
			case '1': 'FFFFFFFF';
			case '2': 'FFFF0000';
			case '3': 'FF00FF00';
			case '4': 'FF0000FF';
			case '5': 'FFCEC070';
			case '6': 'FF0000FF';
			case '7': 'FF8300FF';
			default: value == null ? '' : value;
		};
	}

	/**
		Normalize a V-Slice event and its object payload in one place.  The
		converter writes the returned native event row; PlayState consumes the same
		canonical names at runtime.  Keeping payload adaptation here is important:
		V-Slice uses named fields while the legacy chart event API has three strings.
	*/
	public static function routeVSliceEvent(name:String, values:Dynamic):EngineCompatEventRoute {
		if (name == null || StringTools.trim(name) == '')
			return null;
		var original = StringTools.trim(name);
		var canonical = eventName(original);
		var lower = canonical.toLowerCase();
		var route:EngineCompatEventRoute = {name: null, v1: '', v2: '', v3: ''};
			switch (lower) {
			case 'focus camera' | 'focuscamera':
				// FocusCamera is not a coordinate-only Camera Follow Pos event.
				// V-Slice's named payload can carry actor, coordinates, duration, and
				// easing independently. Keep coordinates in their native slots and
				// carry the full object in v3 for the PlayState FocusCamera adapter.
				route.name = 'Focus Camera';
				route.v1 = firstValue(values, ['x'], '0');
				route.v2 = firstValue(values, ['y'], '0');
				route.v3 = packEventOptions(values, ['char', 'duration', 'ease', 'easeDir']);
			case 'playanimation' | 'play animation':
				route.name = 'Play Animation';
				route.v1 = firstValue(values, ['anim', 'animation'], '');
				route.v2 = firstValue(values, ['target', 'character'], '');
			case 'set health icon':
				// V-Slice can replace either health icon without replacing the
				// underlying character. Keep the visual configuration in v3 so the
				// native HealthIcon remains the single renderer for imported icons.
				route.name = 'Set Health Icon';
				route.v1 = firstValue(values, ['char', 'character', 'target'], '0');
				route.v2 = firstValue(values, ['id', 'icon'], '');
				route.v3 = packEventOptions(values,
					['flipX', 'isPixel', 'offsetX', 'offsetY', 'scale', 'shouldBop']);
			case 'play video':
				route.name = 'Play Video';
				route.v1 = firstValue(values, ['path', 'video', 'file'], '');
				route.v2 = packEventOptions(values,
					['isCutscene', 'duration', 'mute', 'disableControl', 'resync', 'zIndex']);
			case 'change character':
				route.name = 'Change Character';
				// Scripted event variants use either `character`/`newchar` or
				// `target`/`char`. Choose from the payload schema, not the event
				// spelling, so aliases remain interchangeable.
				if (hasEventValue(values, 'target') || hasEventValue(values, 'char')) {
					route.v1 = firstValue(values, ['target', 'character'], 'dad');
					route.v2 = firstValue(values, ['char', 'newchar'], '');
				} else {
					route.v1 = firstValue(values, ['character', 'target'], 'dad');
					route.v2 = firstValue(values, ['newchar', 'char'], '');
				}
			case 'add camera zoom':
				route.name = 'Add Camera Zoom';
				route.v1 = firstValue(values, ['gamezoom', 'value1', 'x'], '');
				route.v2 = firstValue(values, ['hudzoom', 'value2', 'y'], '');
				if (original.toLowerCase() == 'addcamzoompsych')
					route.v3 = 'psych';
			case 'set cam zoom':
				route.name = 'Set Cam Zoom';
				route.v1 = firstValue(values, ['value', 'zoom', 'value1'], '');
			case 'zoom camera':
				// The existing Camera Zoom event is packed for an explicit
				// camera; Zoom Camera keeps its legacy two-value shape and
				// carries ease/mode in v3 for the runtime adapter.
				route.name = 'Zoom Camera';
				route.v1 = firstValue(values, ['zoom'], '1');
				route.v2 = firstValue(values, ['duration'], '4');
				route.v3 = packEventOptions(values, ['ease', 'easeDir', 'mode']);
			case 'change scroll speed':
				route.name = 'Change Scroll Speed';
				route.v1 = firstValue(values, ['scroll', 'speed'], '1');
				route.v2 = firstValue(values, ['duration'], '4');
				route.v3 = packEventOptions(values, ['ease', 'easeDir', 'absolute', 'strumline']);
			case 'set camera bop':
				route.name = 'Set Camera Bop';
				route.v1 = firstValue(values, ['rate'], '4');
				route.v2 = firstValue(values, ['intensity'], '1');
				route.v3 = packEventOptions(values, ['offset']);
			case 'vignette':
				// VignEvent's fields are authored as intensity/duration in steps
				// plus the donor's two-part FlxEase spelling. Keep the object
				// payload packed in v3 so the legacy chart row remains lossless.
				route.name = 'Vignette';
				route.v1 = firstValue(values, ['intensity'], '1');
				route.v2 = firstValue(values, ['duration'], '4');
				route.v3 = packEventOptions(values, ['ease', 'easeDir']);
			case 'markov popups':
				// Preserve the event's authored coordinate payload for the generic
				// manifest-scoped static sprite adapter.
				route.name = 'Markov Popups';
				route.v1 = firstValue(values, ['x'], '0');
				route.v2 = firstValue(values, ['y'], '0');
			case 'camera flash':
				route.name = 'Camera Flash';
				// V-Slice's extra-events camera flash uses a step-count duration,
				// whereas Psych/FPS rows use value1/value2 as color/duration in
				// seconds.  Keep the legacy `Flash`/`Flash Camera` spellings on
				// their old ABI; only an authored `duration` field carries the
				// V-Slice unit marker.  `applyToHud` is an exclusive target in
				// V-Slice, so route it as `hud` instead of flashing both cameras.
				var originalLower = original.toLowerCase();
				var hasVSliceDuration = hasEventValue(values, 'duration')
					&& originalLower != 'flash' && originalLower != 'flash camera';
				var applyToHud = firstValue(values, ['applyToHud'], '').toLowerCase();
				var hasColor = hasEventValue(values, 'color') || hasEventValue(values, 'value1');
				if (hasVSliceDuration && (applyToHud == 'true' || applyToHud == '1'))
					route.v1 = 'hud';
				else
					route.v1 = firstValue(values, ['value1', 'color'], hasVSliceDuration ? 'game' : '');
				if (hasVSliceDuration && !hasColor && applyToHud != 'true' && applyToHud != '1')
					route.v1 = 'game';
				route.v2 = firstValue(values, ['value2', 'duration'], '');
				route.v3 = packEventOptions(values, ['color', 'duration', 'applyToHud']);
				if (hasVSliceDuration)
					route.v3 = markDurationInSteps(route.v3);
			case 'camera fade':
				route.name = 'Camera Fade';
				route.v1 = firstValue(values, ['value1', 'shouldFadeIn', 'fadeIn'], '0');
				route.v2 = firstValue(values, ['value2', 'duration'], '');
				route.v3 = packEventOptions(values, ['color', 'duration', 'shouldFadeIn', 'applyToHud']);
			case 'lyrics':
				route.name = 'Lyrics';
				route.v1 = firstValue(values, ['text', 'value1'], '');
				route.v2 = firstValue(values, ['duration', 'value2'], '');
				route.v3 = packEventOptions(values,
					['text2nd', 'font', 'font2nd', 'fontSize', 'fontSize2nd', 'textColor', 'textColor2nd',
					'isItalic', 'isBold', 'hasAntiAliasing', 'isCentered', 'isCentered2nd',
					'opacity', 'letterSpacing', 'textBorderColor', 'borderSize',
					'isBehindStrumLines', 'isBehindStrumLines2nd']);
			case 'change stage':
				route.name = 'Change Stage';
				route.v1 = firstValue(values, ['stageid', 'stage', 'stageId', 'id', 'value'], '');
			case 'note swap' | 'noteswap' | 'noteswapevent' | 'note style swap' | 'notestyleswap' | 'notestyle swapper':
				route.name = 'Note Swap';
				route.v1 = firstValue(values, ['strumline', 'target', 'lane'], 'both');
				route.v2 = firstValue(values, ['notestyle', 'noteStyle', 'style', 'type'], 'normal');
		}
		return route.name == null ? null : route;
	}

	/**
		Decide whether a mounted HXC SongEvent's handleEvent operation is fully
		represented by the centralized native route.  This is intentionally a
		conservative lexical audit: it never executes donor code and it reports
		donor module calls/options as explicit gaps instead of silently claiming
		compatibility.
	*/
	public static function hxcEventBodyCoverage(source:String, identifier:String,
		canonicalName:String):EngineCompatEventBodyCoverage {
		var result:EngineCompatEventBodyCoverage = {covered:false, gaps:[]};
		var body = hxcEventHandleBody(source);
		var lower = body.toLowerCase();
		var canonical = canonicalName == null ? '' : canonicalName.toLowerCase();
		if (canonical == '' || body == '')
			return {covered:true, gaps:[]};

		switch (canonical) {
			case 'add camera zoom':
				result.covered = lower.indexOf('.zoom') >= 0 || lower.indexOf('camera zoom') >= 0;
				if (!result.covered)
					result.gaps.push('camera zoom mutation was not found');
				// Preferences.zoomCamera is represented by the native
				// OptionsHandler gate before this route mutates either camera.
			case 'note swap':
				result.covered = lower.indexOf('notestyle') >= 0
					&& (lower.indexOf('strumline') >= 0 || lower.indexOf('swap') >= 0);
				if (!result.covered)
					result.gaps.push('note-style/strumline payload semantics were not found');
			case 'change character':
				// Empty ChangeCharacterEvent bodies are deliberate no-op donor stubs;
				// ChangeCharacter/CL/charChange bodies are covered by switchCharacter,
				// including the generic trail cleanup/enable hook in PlayState.
				result.covered = lower.indexOf('characterdataparser') >= 0
					|| lower.indexOf('switchcharacter') >= 0
					|| lower.indexOf('newchar') >= 0
					|| lower.indexOf('charchange') < 0;
				if (!result.covered)
					result.gaps.push('character replacement payload semantics were not found');
			case 'markov popups':
				var spriteDescriptor = eventSpriteDescriptorFromSource(source);
				result.covered = spriteDescriptor != null
					&& StringTools.trim(Std.string(Reflect.field(spriteDescriptor, 'canonicalName'))).toLowerCase() == canonical;
				if (!result.covered)
					result.gaps.push('static HXC event-sprite semantics were not found');
			case 'vignette':
				result.covered = lower.indexOf('intensity') >= 0 && lower.indexOf('duration') >= 0;
				if (!result.covered)
					result.gaps.push('vignette intensity/duration payload semantics were not found');
				// Save.modOptions.isVignEnabled is represented by the native
				// OptionsHandler.vignetteEffects gate in PlayState.
			case 'camera flash':
				result.covered = lower.indexOf('.flash(') >= 0 || lower.indexOf('camera.flash(') >= 0;
				if (!result.covered)
					result.gaps.push('camera flash operation was not found');
				// Preferences.flashingLights is represented by the native
				// OptionsHandler gate and also stops an active flash when disabled.
			case 'camera fade':
				result.covered = lower.indexOf('.fade(') >= 0 || lower.indexOf('camera.fade(') >= 0;
				if (!result.covered)
					result.gaps.push('camera fade operation was not found');
			case 'lyrics':
				result.covered = lower.indexOf('createtext') >= 0 || lower.indexOf('lyric') >= 0;
				if (!result.covered)
					result.gaps.push('lyric text operation was not found');
				// The native route applies the module's two-line/style/options ABI
				// directly, including its lyric-enabled preference and strumline
				// insertion policy; no donor module call is required at runtime.
			case 'change stage':
				result.covered = lower.indexOf('swapstage') >= 0 || lower.indexOf('stageid') >= 0;
				if (!result.covered)
					result.gaps.push('stage replacement operation was not found');
			case 'play video':
				result.covered = lower.indexOf('createvideo') >= 0 || lower.indexOf('playvideo') >= 0;
				if (!result.covered)
					result.gaps.push('video playback operation was not found');
				// VideoModule's path, HUD fade mode/duration, mute, control gate,
				// timestamp resync, and display-list zIndex are handled by the
				// centralized native event-video owner.
			default:
				result.gaps.push('no native body coverage rule');
		}
		return result;
	}

	/** Extract one donor handleEvent body without evaluating HXC. */
	static function hxcEventHandleBody(source:String):String {
		if (source == null || source == '')
			return '';
		var marker = source.indexOf('handleEvent');
		if (marker < 0)
			return '';
		var open = source.indexOf('{', marker);
		if (open < 0)
			return '';
		var depth = 1;
		var quote = '';
		var lineComment = false;
		var blockComment = false;
		var escaped = false;
		var index = open + 1;
		while (index < source.length) {
			var current = source.charAt(index);
			var next = index + 1 < source.length ? source.charAt(index + 1) : '';
			if (lineComment) {
				if (current == '\n') lineComment = false;
				index++;
				continue;
			}
			if (blockComment) {
				if (current == '*' && next == '/') { blockComment = false; index += 2; }
				else index++;
				continue;
			}
			if (quote != '') {
				if (current == quote && !escaped) quote = '';
				if (current == '\\' && !escaped) escaped = true; else escaped = false;
				index++;
				continue;
			}
			if (current == '/' && next == '/') { lineComment = true; index += 2; continue; }
			if (current == '/' && next == '*') { blockComment = true; index += 2; continue; }
			if (current == '"' || current == "'") { quote = current; index++; continue; }
			if (current == '{') depth++;
			else if (current == '}') {
				depth--;
				if (depth == 0) return source.substr(open + 1, index - open - 1);
			}
			index++;
		}
		return source.substr(open + 1);
	}

	/** Decode an optional packed event-options field from a legacy chart row. */
	public static function eventOptions(value:Dynamic):Dynamic {
		if (value == null)
			return null;
		var text = StringTools.trim(Std.string(value));
		if (text == '')
			return null;
		try {
			return Json.parse(text);
		} catch (_:Dynamic) {
			return null;
		}
	}

	/**
		The common Psych/Lua bridge calls below are intentionally listed in one
		place.  Import scanners can use this as a compatibility allow-list and the
		HScript environment can expose the same names without chart rewrites.
	*/
	public static function knownScriptFunction(name:String):Bool {
		if (name == null)
			return false;
		switch (name.toLowerCase()) {
			case 'oncreate' | 'oncreatepost' | 'onsongstart' | 'onupdate' | 'onupdatepost'
				| 'onbeathit' | 'onstephit' | 'onsectionhit' | 'oncountdowntick'
				| 'oncountdownstart' | 'oncountdownend' | 'ongoodnotehit' | 'onopponentnotehit' | 'onnotehit'
				| 'onnoteincoming' | 'onnotemiss' | 'onmissnote' | 'onopponentnotemiss' | 'onsongend'
				| 'onnoteghostmiss' | 'onsubstateopenend' | 'onsubstateclosebegin'
				| 'onpausesubstateopen' | 'onpausesubstateclose'
				| 'ontweencompleted' | 'ontimercompleted' | 'onstartcountdown'
				| 'onendsong' | 'onsongretry' | 'onpause' | 'onresume' | 'onstateopenend'
				| 'ondifficultyswitch' | 'ongameover' | 'ongameoverstart'
				| 'oncapsuleselected' | 'ondestroy' | 'onevent':
				return true;
			case 'oncustomsubstatecreate' | 'oncustomsubstatecreatepost' | 'oncustomsubstateupdate'
				| 'oncustomsubstatedestroy':
				return true;
			case 'setproperty' | 'getproperty' | 'setpropertyfromgroup' | 'getpropertyfromgroup'
				| 'setpropertyfromclass' | 'getpropertyfromclass' | 'setobjectcamera'
				| 'setobjectorder' | 'getobjectorder' | 'screencenter' | 'scaleobject' | 'setblendmode'
				| 'setscrollfactor'
				| 'setluaspritescrollfactor' | 'addluasprite' | 'removeluasprite'
				| 'makeluasprite' | 'makeanimatedluasprite' | 'addanimation' | 'addanimationbyprefix'
				| 'addanimationbyindices' | 'objectplayanimation' | 'makeluatext'
				| 'addluatext' | 'getluaobject' | 'settextstring' | 'settextsize' | 'settextcolor'
				| 'settextborder' | 'settextfont' | 'setgraphicsize' | 'updatehitbox'
				| 'loadgraphic' | 'makegraphic' | 'dotweenx' | 'dotweeny' | 'dotweenalpha'
				| 'dotweenangle' | 'dotweenzoom' | 'dotweencolor' | 'runtimer'
				| 'canceltimer' | 'canceltween' | 'playsound' | 'getsongposition' | 'debugprint' | 'initluashader'
				| 'createruntimeshader' | 'setshaderfloat' | 'setspriteshader'
				| 'notetweenx' | 'notetweeny' | 'notetweenalpha' | 'notetweenangle'
				| 'getrandomint' | 'getrandomfloat' | 'keyboardjustpressed' | 'keyjustpressed'
				| 'getcolorfromhex' | 'precacheimage' | 'precachesound' | 'triggerevent'
					| 'camerashake' | 'swapstage' | 'changestage' | 'starttween'
					| 'setactorx' | 'setactory' | 'tweencamerazoom' | 'scaleluasprite'
					| 'settextalignment' | 'gettextfont' | 'gettextstring' | 'getrandombool'
					| 'characterdance'
					| 'getmousex' | 'getmousey' | 'getmouseclicked' | 'mouseclicked'
					| 'playmusic' | 'loadsong' | 'exitsong' | 'restartsong' | 'endsong'
				| 'startcountdown' | 'exitmenu' | 'close'
					| 'opencustomsubstate' | 'closecustomsubstate' | 'callmethodfromclass'
					| 'setfilters' | 'getactorx' | 'getactory'
					| 'setcamerashaderfilters' | 'clearcamerashaderfilters'
					| 'createruntimeshaderandstore' | 'setcamerashaderfiltersfromstored'
					| 'installshadercoordfix' | 'removeshadercoordfix'
					| 'tweencharactercolorrgb' | 'tweencharactercolorhex' | 'resetcharactercolor'
				| 'setstrumlinergbshader' | 'updatecameraangle'
				// V-Slice/HXC stage and character helpers.  These are seeded by
				// PlayState for every isolated HScript interpreter, so they must not
				// be reported as unknown Lua/HXC calls during import diagnostics.
				// Legacy stage HScript uses the same native scope for its default
				// camera zoom and actor lookup helpers.
				| 'setdefaultzoom' | 'gethaxeactor'
				| 'getdad' | 'getboyfriend' | 'getgirlfriend' | 'getopponent' | 'getnamedprop'
				| 'getcurrentanimation' | 'setanimationoffsets' | 'playanimation'
				| 'playsinganimation' | 'hasanimation' | 'issinging'
				| 'isanimationfinished' | 'getdataflipx'
				// Keep the common truncated spellings accepted by older ports too.
				| 'notweenx' | 'notweeny':
				return true;
			default:
				return false;
		}
	}

	/**
		Resolve standard stage ids shared by the base game and donor engines.

		The native stage scripts use one registry name plus `songData.stageID` to
		select an Erect variant. V-Slice instead appends `Erect` to the stage id,
		so resolving only the name would load the normal background. Keep these
		aliases in the engine compatibility layer so import, scan, stage events,
		and runtime stage creation all share one mapping. Unknown donor stage ids
		are intentionally left untouched and remain eligible for diagnostics.
	*/
	public static function resolveStageResolution(reference:String):EngineCompatStageResolution {
		if (reference == null)
			return {authored:null, nativeName:null, stageID:0, standard:false};
		var authored = StringTools.trim(reference);
		if (authored == '')
			return {authored:reference, nativeName:reference, stageID:0, standard:false};
		return switch (authored.toLowerCase()) {
			// V-Slice's shipped base-stage variant ids. Keep the table explicit so
			// a similarly named custom donor stage is never silently redirected.
			case 'schoolevilerect':
				{authored:reference, nativeName:'schoolEvil', stageID:1, standard:true};
			case 'schoolerect':
				{authored:reference, nativeName:'school', stageID:1, standard:true};
			case 'spookyerect':
				{authored:reference, nativeName:'spooky', stageID:1, standard:true};
			case 'phillyerect':
				{authored:reference, nativeName:'philly', stageID:1, standard:true};
			case 'limoerect':
				{authored:reference, nativeName:'limo', stageID:1, standard:true};
			case 'mallerect':
				{authored:reference, nativeName:'mall', stageID:1, standard:true};
			case 'tankerect':
				{authored:reference, nativeName:'tank', stageID:1, standard:true};
			// Psych Engine keeps this shipped stage's camelCase id, while this
			// runtime has a dashed stage script which can provide fallback visuals.
			// The compiled PhillyStreets class remains unsupported; the importer
			// reports that separately from this visual lookup alias.
			case 'phillystreets':
				{authored:reference, nativeName:'philly-streets', stageID:0, standard:false};
			case 'phillystreetserect' | 'philly-streets-erect':
				{authored:reference, nativeName:'philly-streets', stageID:1, standard:true};
			case 'stageerect':
				{authored:reference, nativeName:'stage', stageID:1, standard:true};
			case 'halloween':
				{authored:reference, nativeName:'spooky', stageID:0, standard:true};
			case 'mainstage':
				{authored:reference, nativeName:'stage', stageID:0, standard:true};
			default:
				{authored:reference, nativeName:reference, stageID:0,
					standard:isNativeStageName(authored)};
		};
	}

	/** Return the native name for one standard stage spelling. */
	public static function resolveStageAlias(reference:String):String {
		var resolved = resolveStageResolution(reference);
		return resolved == null ? reference : resolved.nativeName;
	}

	/** Return the native variant selector encoded by a donor stage id. */
	public static function stageVariantId(reference:String):Int {
		var resolved = resolveStageResolution(reference);
		return resolved == null ? 0 : resolved.stageID;
	}

	/** True when the authored id is a base-game stage or one of its aliases. */
	public static function isBuiltinStageReference(reference:String):Bool {
		var resolved = resolveStageResolution(reference);
		return resolved != null && resolved.standard;
	}

	static function isNativeStageName(reference:String):Bool {
		if (reference == null)
			return false;
		return switch (reference.toLowerCase()) {
			case 'stage' | 'spooky' | 'philly' | 'limo' | 'mall' | 'malleevil'
				| 'school' | 'schoolevil' | 'tank' | 'philly-streets': true;
			default: false;
		};
	}

	/** Return the authored stage id followed by its native alias, if any. */
	public static function stageLookupNames(reference:String):Array<String> {
		var result:Array<String> = [];
		if (reference == null)
			return result;
		var authored = StringTools.trim(reference);
		if (authored == '')
			return result;
		result.push(authored);
		var resolved = resolveStageAlias(authored);
		if (resolved != null && resolved.toLowerCase() != authored.toLowerCase())
			result.push(resolved);
		return result;
	}

	/**
		Map only the legacy base Boyfriend atlas roots to the native custom-char
		layout.  Do not map arbitrary `characters/boyfriend` or custom-char paths:
		those can describe donor-specific assets rather than the standard BF.
	*/
	public static function resolveLegacyAssetPath(path:String):String {
		if (path == null)
			return null;
		var value = StringTools.trim(StringTools.replace(path, '\\', '/'));
		while (StringTools.startsWith(value, './'))
			value = value.substr(2);
		var lower = value.toLowerCase();
		if (StringTools.startsWith(lower, 'assets/'))
			lower = lower.substr(7);
		return switch (lower) {
			case 'images/boyfriend.png' | 'shared/images/boyfriend.png'
				| 'shared/characters/boyfriend.png': 'assets/images/custom_chars/bf/char.png';
			case 'images/boyfriend.xml' | 'shared/images/boyfriend.xml'
				| 'shared/characters/boyfriend.xml': 'assets/images/custom_chars/bf/char.xml';
			default: path;
		};
	}

	/**
		Return the exact V-Slice logical character asset ids which may be
		provided by a destination-native character implementation.

		V-Slice's base-game content is allowed to omit those files from a mod
		because the original game supplies them from its shared library.  The
		importer must not turn that convention into a fuzzy basename search: an
		unrelated donor character with a similar name would be a much worse
		result than a visible diagnostic.  Keep the small logical-library map at
		the engine boundary, and let the importer validate each returned registry
		entry and its actual atlas prefixes before it accepts one.
	*/
	public static function vSliceNativeCharacterCandidates(assetPath:String):Array<String> {
		var result:Array<String> = [];
		if (assetPath == null)
			return result;
		var value = StringTools.trim(StringTools.replace(assetPath, '\\', '/'));
		while (value.startsWith('./'))
			value = value.substr(2);
		var lower = value.toLowerCase();
		if (lower.startsWith('assets/'))
			lower = lower.substr(7);
		// V-Slice uses `characters/<id>` for the base library.  Accept the
		// explicit shared/images spelling too, but do not accept a bare basename
		// or arbitrary nested path: those can belong to the importing mod.
		var logical:String = null;
		for (prefix in ['characters/', 'shared/characters/', 'shared/images/characters/'])
			if (lower.startsWith(prefix)) {
				logical = lower.substr(prefix.length);
				break;
			}
		if (logical == null || logical == '' || logical.indexOf('/') >= 0)
			return result;
		// Do not let an already-imported custom character become a source for a
		// later import merely because its id happens to match.  Only the known
		// base-game/V-Slice library ids may cross the import boundary here; the
		// registry and atlas checks below still have to prove that the destination
		// implementation is complete.
		if (!isVSliceBaseCharacterId(logical))
			return result;
		// First try the exact destination id.  This covers the ordinary base
		// character set (bf-pixel, pico, monster, etc.) without maintaining a
		// brittle list of every stock variant.  The aliases below cover only
		// documented donor spellings whose native registry id is different.
		result.push(logical);
		switch (logical) {
			case 'boyfriend':
				result.push('bf');
			case 'daddy':
				result.push('dad');
			case 'girlfriend':
				result.push('gf');
			case 'parents-christmas':
				result.push('parents');
			case 'senpai':
				// Senpai and Angry Senpai intentionally share V-Slice's one
				// logical atlas. Prefix validation selects the correct native
				// implementation for each definition.
				result.push('senpai-angry');
			default:
		}
		return result;
	}

	/** Exact destination-native V-Slice character ids which may fall back across
	 * an imported owner boundary when that owner has no character row. */
	public static function isVSliceBaseCharacterId(value:String):Bool {
		var normalized = StringTools.trim(value == null ? '' : value).toLowerCase();
		return switch (normalized) {
			case 'bf' | 'bf-car' | 'bf-christmas' | 'bf-holding-gf' | 'bf-pixel'
				| 'boyfriend' | 'dad' | 'daddy' | 'gf' | 'gf-car' | 'gf-christmas'
				| 'gf-pixel' | 'gf-tankmen' | 'girlfriend' | 'mom' | 'mom-car'
				| 'monster' | 'monster-christmas' | 'parents' | 'parents-christmas'
				| 'pico' | 'pico-christmas' | 'pico-dark' | 'pico-pixel' | 'pico-speaker'
				| 'senpai' | 'senpai-angry' | 'spirit' | 'tankman' | 'tankman-bloody': true;
			default: false;
		};
	}

	/**
		Rewrite legacy asset paths in quoted script literals before HScript runs.
		The importer calls `resolveLegacyAssetPath` for the same references when it
		builds its dependency candidates, keeping diagnostics and runtime lookup on
		one resolver without modifying donor scripts or charts.
	*/
	public static function rewriteLegacyAssetPaths(source:String):String {
		if (source == null || source == '')
			return source;
		var output = new StringBuf();
		var start = 0;
		var cursor = 0;
		while (cursor < source.length) {
			var quote = source.charAt(cursor);
			if (quote != "'" && quote != '"') {
				cursor++;
				continue;
			}
			var end = cursor + 1;
			var escaped = false;
			while (end < source.length) {
				var character = source.charAt(end);
				if (character == quote && !escaped)
					break;
				if (character == '\\' && !escaped)
					escaped = true;
				else
					escaped = false;
				end++;
			}
			if (end >= source.length) {
				cursor++;
				continue;
			}
			output.add(source.substr(start, cursor - start));
			output.add(quote);
			output.add(resolveLegacyAssetPath(source.substr(cursor + 1, end - cursor - 1)));
			output.add(quote);
			start = end + 1;
			cursor = start;
		}
		output.add(source.substr(start));
		return output.toString();
	}

	/**
		Normalize the narrow, safe subset of old-engine per-frame mutations.

		A number of donor HScript stages were authored for a fixed 60 FPS update
		loop and contain statements such as `red.alpha += 0.007`.  The native
		interpreter receives real elapsed seconds, so those statements must be
		scaled in memory before the script is parsed.  This adapter deliberately
		accepts only a direct decimal literal on a standalone `+=`/`-=` statement
		inside `function update(elapsed)`.  Integer counters, expressions which
		already mention elapsed/frameRateScale, calls, indexed assignments, and
		other ambiguous forms remain byte-for-byte unchanged and are reported.

		The donor source is never written back.  Returning diagnostics alongside
		the transformed source lets PlayState surface an actionable warning while
		still allowing an unrelated safe mutation in the same script to run.
	*/
	public static function normalizeLegacyFrameDeltas(source:String):LegacyFrameDeltaResult {
		var diagnostics:Array<LegacyFrameDeltaDiagnostic> = [];
		if (source == null || source == '')
			return {source: source, rewritten: 0, diagnostics: diagnostics};

		// Mask strings/comments without changing offsets.  All subsequent lexical
		// positions can therefore be applied directly to the original source.
		var masked = maskLegacyFrameDeltaSource(source);
		var replacements:Array<LegacyFrameDeltaReplacement> = [];
		var updatePattern = new EReg('\\bfunction\\s+update\\s*\\(([^)]*)\\)', 'g');
		var search = 0;
		while (search < masked.length && updatePattern.matchSub(masked, search)) {
			var functionPos = updatePattern.matchedPos();
			search = functionPos.pos + functionPos.len;
			if (!legacyElapsedUpdateArguments(updatePattern.matched(1)))
				continue;

			var bodyStart = masked.indexOf('{', search);
			var semicolon = masked.indexOf(';', search);
			if (bodyStart < 0 || (semicolon >= 0 && semicolon < bodyStart)) {
				addLegacyFrameDeltaDiagnostic(diagnostics, source, search,
					'legacy-frame-delta-no-body', 'The update(elapsed) hook has no braced body.');
				continue;
			}
			var bodyEnd = findLegacyFrameDeltaBodyEnd(masked, bodyStart);
			if (bodyEnd < 0) {
				addLegacyFrameDeltaDiagnostic(diagnostics, source, bodyStart,
					'legacy-frame-delta-unclosed-body', 'The update(elapsed) hook has an unclosed body.');
				continue;
			}
			collectLegacyFrameDeltaReplacements(source, masked, bodyStart, bodyEnd,
				replacements, diagnostics);
			search = bodyEnd + 1;
		}

		// Apply from right to left so a replacement never invalidates a later
		// source offset.  The returned text is the only mutable representation.
		replacements.sort(function(a:LegacyFrameDeltaReplacement, b:LegacyFrameDeltaReplacement):Int {
			return b.start - a.start;
		});
		var normalized = source;
		for (replacement in replacements)
			normalized = normalized.substr(0, replacement.start) + replacement.value
				+ normalized.substr(replacement.end);
		return {source: normalized, rewritten: replacements.length, diagnostics: diagnostics};
	}

	static function collectLegacyFrameDeltaReplacements(source:String, masked:String, bodyStart:Int, bodyEnd:Int,
			replacements:Array<LegacyFrameDeltaReplacement>, diagnostics:Array<LegacyFrameDeltaDiagnostic>):Void {
		var cursor = bodyStart + 1;
		while (cursor < bodyEnd) {
			var plus = masked.indexOf('+=', cursor);
			var minus = masked.indexOf('-=', cursor);
			var opStart = -1;
			if (plus >= 0 && plus < bodyEnd)
				opStart = plus;
			if (minus >= 0 && minus < bodyEnd && (opStart < 0 || minus < opStart))
				opStart = minus;
			if (opStart < 0)
				break;

			var target = readLegacyFrameDeltaTarget(masked, opStart, bodyStart);
			if (target == null) {
				addLegacyFrameDeltaDiagnostic(diagnostics, source, opStart,
					'legacy-frame-delta-ambiguous', 'A compound assignment inside update(elapsed) has an unsupported target.');
				cursor = opStart + 2;
				continue;
			}
			var rhsStart = skipLegacyFrameDeltaSpace(masked, opStart + 2, bodyEnd);
			var rhsEnd = findLegacyFrameDeltaStatementEnd(masked, rhsStart, bodyEnd);
			if (rhsStart >= rhsEnd) {
				addLegacyFrameDeltaDiagnostic(diagnostics, source, opStart,
					'legacy-frame-delta-ambiguous', 'A compound assignment inside update(elapsed) has no readable right-hand side.');
				cursor = opStart + 2;
				continue;
			}

			var rhs = StringTools.trim(masked.substr(rhsStart, rhsEnd - rhsStart));
			var standalone = legacyFrameDeltaIsStandalone(masked, target.start, bodyStart);
			if (standalone && isLegacyFrameDeltaDecimal(rhs)) {
				var literalStart = skipLegacyFrameDeltaSpace(masked, rhsStart, rhsEnd);
				var literal = source.substr(literalStart, rhs.length);
				replacements.push({
					start: literalStart,
					end: literalStart + rhs.length,
					value: literal + ' * frameRateScale(elapsed)'
				});
			} else if (!legacyFrameDeltaMentionsTiming(rhs) && !isLegacyFrameDeltaInteger(rhs)) {
				var reason = standalone ? 'the right-hand side is not a constant decimal literal'
					: 'the assignment is not a standalone statement';
				addLegacyFrameDeltaDiagnostic(diagnostics, source, opStart,
					'legacy-frame-delta-ambiguous', 'Could not safely normalize ' + target.name + ' (' + reason + ').');
			}
			cursor = rhsEnd + 1;
		}
	}

	static function readLegacyFrameDeltaTarget(masked:String, opStart:Int, bodyStart:Int):LegacyFrameDeltaRange {
		var cursor = opStart - 1;
		while (cursor > bodyStart && isLegacyFrameDeltaSpace(masked.charAt(cursor)))
			cursor--;
		var end = cursor + 1;
		if (cursor <= bodyStart || !isLegacyFrameDeltaIdentifierPart(masked.charAt(cursor)))
			return null;
		while (cursor > bodyStart && isLegacyFrameDeltaIdentifierPart(masked.charAt(cursor)))
			cursor--;
		var start = cursor + 1;
		while (true) {
			var dot = cursor;
			while (dot > bodyStart && isLegacyFrameDeltaSpace(masked.charAt(dot)))
				dot--;
			if (dot <= bodyStart || masked.charAt(dot) != '.')
				break;
			cursor = dot - 1;
			while (cursor > bodyStart && isLegacyFrameDeltaSpace(masked.charAt(cursor)))
				cursor--;
			if (cursor <= bodyStart || !isLegacyFrameDeltaIdentifierPart(masked.charAt(cursor)))
				return null;
			while (cursor > bodyStart && isLegacyFrameDeltaIdentifierPart(masked.charAt(cursor)))
				cursor--;
			start = cursor + 1;
		}
		return {start: start, end: end, name: StringTools.trim(masked.substr(start, end - start))};
	}

	static function legacyFrameDeltaIsStandalone(masked:String, targetStart:Int, bodyStart:Int):Bool {
		var cursor = targetStart - 1;
		while (cursor > bodyStart && isLegacyFrameDeltaSpace(masked.charAt(cursor)))
			cursor--;
		if (cursor <= bodyStart)
			return true;
		var previous = masked.charAt(cursor);
		return previous == '{' || previous == '}' || previous == ';' || previous == ')' || previous == '\n'
			|| previous == '\r';
	}

	static function findLegacyFrameDeltaStatementEnd(masked:String, start:Int, bodyEnd:Int):Int {
		var parentheses = 0;
		var brackets = 0;
		var cursor = start;
		while (cursor < bodyEnd) {
			var character = masked.charAt(cursor);
			switch (character) {
				case '(':
					parentheses++;
				case ')':
					if (parentheses > 0) parentheses--;
				case '[':
					brackets++;
				case ']':
					if (brackets > 0) brackets--;
				default:
					if (parentheses == 0 && brackets == 0
						&& (character == ';' || character == '\n' || character == '\r' || character == '}'))
						return cursor;
			}
			cursor++;
		}
		return bodyEnd;
	}

	static function findLegacyFrameDeltaBodyEnd(masked:String, bodyStart:Int):Int {
		var depth = 0;
		var cursor = bodyStart;
		while (cursor < masked.length) {
			switch (masked.charAt(cursor)) {
				case '{':
					depth++;
				case '}':
					depth--;
					if (depth == 0)
						return cursor;
				default:
			}
			cursor++;
		}
		return -1;
	}

	static function legacyElapsedUpdateArguments(arguments:String):Bool {
		if (arguments == null)
			return false;
		var value = StringTools.trim(arguments);
		if (value.indexOf(',') >= 0)
			return false;
		var colon = value.indexOf(':');
		if (colon >= 0)
			value = StringTools.trim(value.substr(0, colon));
		return value == 'elapsed';
	}

	static function isLegacyFrameDeltaDecimal(value:String):Bool {
		if (value == null || value == '')
			return false;
		var dot = false;
		var before = 0;
		var after = 0;
		var exponent = false;
		var exponentDigits = 0;
		var cursor = 0;
		if (value.charAt(0) == '+' || value.charAt(0) == '-')
			cursor++;
		while (cursor < value.length) {
			var character = value.charAt(cursor);
			if (character >= '0' && character <= '9') {
				if (exponent)
					exponentDigits++;
				else if (dot)
					after++;
				else
					before++;
			} else if (character == '.' && !dot && !exponent) {
				dot = true;
			} else if ((character == 'e' || character == 'E') && dot && !exponent && after > 0) {
				exponent = true;
				if (cursor + 1 < value.length && (value.charAt(cursor + 1) == '+' || value.charAt(cursor + 1) == '-'))
					cursor++;
			} else {
				return false;
			}
			cursor++;
		}
		return dot && before > 0 && after > 0 && (!exponent || exponentDigits > 0);
	}

	static function isLegacyFrameDeltaInteger(value:String):Bool {
		if (value == null || value == '')
			return false;
		var start = (value.charAt(0) == '+' || value.charAt(0) == '-') ? 1 : 0;
		if (start >= value.length)
			return false;
		for (cursor in start...value.length) {
			var character = value.charAt(cursor);
			if (character < '0' || character > '9')
				return false;
		}
		return true;
	}

	static function legacyFrameDeltaMentionsTiming(value:String):Bool {
		return value != null && (value.indexOf('elapsed') >= 0 || value.indexOf('frameRateScale') >= 0);
	}

	static function skipLegacyFrameDeltaSpace(value:String, start:Int, limit:Int):Int {
		var cursor = start;
		while (cursor < limit && isLegacyFrameDeltaSpace(value.charAt(cursor)))
			cursor++;
		return cursor;
	}

	static function isLegacyFrameDeltaSpace(value:String):Bool {
		return value == ' ' || value == '\t' || value == '\n' || value == '\r';
	}

	static function isLegacyFrameDeltaIdentifierPart(value:String):Bool {
		return (value >= 'a' && value <= 'z') || (value >= 'A' && value <= 'Z')
			|| (value >= '0' && value <= '9') || value == '_';
	}

	static function maskLegacyFrameDeltaSource(source:String):String {
		var chars = source.split('');
		var mode = 0; // 0=code, 1=single quote, 2=double quote, 3=line comment, 4=block comment
		var cursor = 0;
		while (cursor < chars.length) {
			var character = chars[cursor];
			if (mode == 0) {
				if (character == '/' && cursor + 1 < chars.length && chars[cursor + 1] == '/') {
					chars[cursor] = ' ';
					chars[cursor + 1] = ' ';
					mode = 3;
					cursor += 2;
				} else if (character == '/' && cursor + 1 < chars.length && chars[cursor + 1] == '*') {
					chars[cursor] = ' ';
					chars[cursor + 1] = ' ';
					mode = 4;
					cursor += 2;
				} else if (character == '\'') {
					chars[cursor] = ' ';
					mode = 1;
					cursor++;
				} else if (character == '"') {
					chars[cursor] = ' ';
					mode = 2;
					cursor++;
				} else {
					cursor++;
				}
			} else if (mode == 1 || mode == 2) {
				if (character == '\\') {
					chars[cursor] = ' ';
					if (cursor + 1 < chars.length && chars[cursor + 1] != '\n' && chars[cursor + 1] != '\r')
						chars[cursor + 1] = ' ';
					cursor += 2;
				} else {
					var closing = (mode == 1 && character == '\'') || (mode == 2 && character == '"');
					if (character != '\n' && character != '\r')
						chars[cursor] = ' ';
					if (closing)
						mode = 0;
					cursor++;
				}
			} else if (mode == 3) {
				if (character == '\n' || character == '\r')
					mode = 0;
				else
					chars[cursor] = ' ';
				cursor++;
			} else {
				if (character == '*' && cursor + 1 < chars.length && chars[cursor + 1] == '/') {
					chars[cursor] = ' ';
					chars[cursor + 1] = ' ';
					mode = 0;
					cursor += 2;
				} else {
					if (character != '\n' && character != '\r')
						chars[cursor] = ' ';
					cursor++;
				}
			}
		}
		return chars.join('');
	}

	static function addLegacyFrameDeltaDiagnostic(diagnostics:Array<LegacyFrameDeltaDiagnostic>, source:String,
			offset:Int, code:String, message:String):Void {
		var line = 1;
		var cursor = 0;
		while (cursor < offset && cursor < source.length) {
			if (source.charAt(cursor) == '\n')
				line++;
			cursor++;
		}
		diagnostics.push({severity: 'warning', code: code, message: message, line: line});
	}

	/**
		Route `Paths.*` calls in generated HXC programs through the interpreter's
		manifest-scoped path adapter.  HXC stage scripts are copied below
		`assets/imported_mods/<namespace>`; leaving their donor `Paths` calls
		untouched would silently resolve to the native shared asset tree (or make a
		missing companion prop look like an invalid stage).  The runtime seeds
		`hxcPaths` only for the isolated HXC interpreter, so ordinary native and
		legacy HScript keep the original `Paths` class semantics.
	*/
	public static function rewriteScopedAssetPaths(source:String):String {
		if (source == null || source == '')
			return source;
		var output = new EReg('\\bPaths\\s*\\.', 'g').replace(source, 'hxcPaths.');
		output = rewriteScopedSongTextReads(output);
		// OpenFL's `Assets` table only knows files embedded by Project.xml.  HXC
		// companions are imported after the build and their files live below the
		// song's manifest namespace, so route all static asset lookups through the
		// same runtime proxy as Paths.  The proxy falls back to FNFAssets for
		// packaged assets and reads imported files directly on native targets.
		return new EReg('\\bAssets\\s*\\.', 'g').replace(output, 'hxcAssets.');
	}

	/** Route HXC coolTextFile calls for V-Slice song-sidecar keys through the
		selected script's Paths proxy. Other text reads retain their existing root. */
	static function rewriteScopedSongTextReads(source:String):String {
		if (source == null || source == '')
			return source;
		var masked = maskLegacyFrameDeltaSource(source);
		// A donor may provide its own coolTextFile method (several V-Slice
		// scripts do). Keep those calls intact so their line filtering and other
		// authored semantics survive; the same pass still scopes Paths.txt inside
		// that helper. Only adapt calls which would otherwise reach the global
		// helper with an unscoped `songs/...` key.
		if (new EReg('function[ \\t\\r\\n]+coolTextFile[ \\t\\r\\n]*\\(', '').match(masked))
			return source;
		var output = new StringBuf();
		var cursor = 0;
		var scan = 0;
		while (scan < masked.length) {
			var start = masked.indexOf('coolTextFile', scan);
			if (start < 0)
				break;
			var endName = start + 'coolTextFile'.length;
			var before = start > 0 ? masked.charAt(start - 1) : '';
			var after = endName < masked.length ? masked.charAt(endName) : '';
			if (isLegacyFrameDeltaIdentifierPart(before) || isLegacyFrameDeltaIdentifierPart(after)
				|| before == '.') {
				scan = endName;
				continue;
			}
			var declarationStart = Std.int(Math.max(0, start - 24));
			var declarationPrefix = StringTools.trim(masked.substr(declarationStart, start - declarationStart));
			if (new EReg('function$', '').match(declarationPrefix)) {
				scan = endName;
				continue;
			}
			var open = endName;
			while (open < masked.length && isLegacyFrameDeltaSpace(masked.charAt(open)))
				open++;
			if (open >= masked.length || masked.charAt(open) != '(') {
				scan = endName;
				continue;
			}
			var depth = 0;
			var close = -1;
			for (index in open...masked.length) {
				switch (masked.charAt(index)) {
					case '(':
						depth++;
					case ')':
						depth--;
						if (depth == 0)
							close = index;
					default:
				}
				if (close >= 0)
					break;
			}
			if (close < 0) {
				scan = open + 1;
				continue;
			}
			var arguments = StringTools.trim(source.substr(open + 1, close - open - 1));
			if (!new EReg("^[\\\"']songs/", '').match(arguments)) {
				scan = close + 1;
				continue;
			}
			output.add(source.substr(cursor, start - cursor));
			output.add('CoolUtil.coolTextFile(hxcPaths.txt(');
			output.add(source.substr(open + 1, close - open - 1));
			output.add('))');
			cursor = close + 1;
			scan = close + 1;
		}
		if (cursor == 0)
			return source;
		output.add(source.substr(cursor));
		return output.toString();
	}

	/**
		Find function-call identifiers without trying to parse donor Lua/HXC.
		This deliberately stays a small lexical pass: import diagnostics need to
		identify engine API names, not validate a foreign language grammar.
	*/
	public static function scriptFunctionNames(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null)
			return result;
		var i = 0;
		while (i < source.length) {
			var first = source.charAt(i);
			if (!isIdentifierStart(first)) {
				i++;
				continue;
			}
			var start = i++;
			while (i < source.length && isIdentifierPart(source.charAt(i)))
				i++;
			var name = source.substr(start, i - start);
			var cursor = i;
			while (cursor < source.length && isWhitespace(source.charAt(cursor)))
				cursor++;
			var memberCall = start > 0 && (source.charAt(start - 1) == '.' || source.charAt(start - 1) == ':');
			if (!memberCall && cursor < source.length && source.charAt(cursor) == '(')
				appendName(result, name);
		}
		return result;
	}

	/**
		Return only unrecognised names which look like engine calls.  Ordinary
		mod-local helpers (for example `lerp` or `normalText`) are intentionally
		left alone so one script does not produce a wall of false positives.
	*/
	public static function unknownScriptFunctions(source:String):Array<String> {
		var result:Array<String> = [];
		for (name in scriptFunctionNames(source)) {
			if (knownScriptFunction(name) || !isEngineFunctionCandidate(name)
				|| isDeclaredScriptFunction(source, name) || isScriptBuiltin(name))
				continue;
			appendName(result, name);
		}
		return result;
	}

	static function appendName(result:Array<String>, name:String):Void {
		if (name != null && result.indexOf(name) == -1)
			result.push(name);
	}

	static function isIdentifierStart(value:String):Bool {
		if (value == null || value == '')
			return false;
		var code = value.charCodeAt(0);
		return (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || value == '_';
	}

	static function isIdentifierPart(value:String):Bool {
		if (isIdentifierStart(value))
			return true;
		if (value == null || value == '')
			return false;
		var code = value.charCodeAt(0);
		return code >= 48 && code <= 57;
	}

	static function isWhitespace(value:String):Bool {
		return value == ' ' || value == '\t' || value == '\r' || value == '\n';
	}

	static function isEngineFunctionCandidate(name:String):Bool {
		if (name == null)
			return false;
		var lower = name.toLowerCase();
		for (prefix in ['set', 'get', 'doTween', 'noteTween', 'makeLua', 'addLua', 'removeLua',
			'object', 'scale', 'screen', 'camera', 'keyboard', 'keyJust', 'precache', 'trigger',
			'playSound', 'runTimer', 'cancelTween', 'initLua', 'createRuntime', 'debugPrint',
			'getRandom', 'getColor', 'startCountdown', 'endSong', 'startTween', 'setActor',
			'tweenCamera', 'playMusic', 'loadSong', 'exitSong', 'restartSong', 'openCustom',
			'closeCustom', 'callMethod', 'setText', 'getText', 'mouse', 'getMouse', 'scaleLua',
			'tweenCharacterColor', 'resetCharacter',
			'setStrumLine', 'updateCamera'])
			if (StringTools.startsWith(lower, prefix.toLowerCase()))
				return true;
		return false;
	}

	static function isDeclaredScriptFunction(source:String, name:String):Bool {
		if (source == null || name == null)
			return false;
		return source.indexOf('function ' + name) >= 0
			|| source.indexOf('function\t' + name) >= 0
			|| source.indexOf('function\n' + name) >= 0;
	}

	static function isScriptBuiltin(name:String):Bool {
		if (name == null)
			return false;
		switch (name.toLowerCase()) {
			case 'setmetatable' | 'getmetatable' | 'getfenv' | 'tonumber' | 'tostring'
				| 'type' | 'pairs' | 'ipairs' | 'rawset' | 'rawget' | 'require':
				return true;
			default:
				return false;
		}
	}

	static function firstValue(values:Dynamic, names:Array<String>, fallback:String):String {
		if (values != null)
			for (name in names) {
				var value:Dynamic = null;
				try {
					value = Reflect.field(values, name);
				} catch (_:Dynamic) {}
				if (value != null)
					return Std.string(value);
			}
		return fallback;
	}

	static function hasEventValue(values:Dynamic, name:String):Bool {
		if (values == null || name == null)
			return false;
		try {
			return Reflect.hasField(values, name) && Reflect.field(values, name) != null;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Mark a packed V-Slice duration as steps without changing legacy rows. */
	static function markDurationInSteps(options:String):String {
		var packed:Dynamic = {};
		if (options != null && StringTools.trim(options) != '') {
			try {
				packed = Json.parse(options);
			} catch (_:Dynamic) {
				packed = {};
			}
		}
		Reflect.setField(packed, 'durationSteps', true);
		return Json.stringify(packed);
	}

	static function packEventOptions(values:Dynamic, names:Array<String>):String {
		if (values == null || names == null || names.length == 0)
			return '';
		var packed:Dynamic = {};
		var found = false;
		for (name in names) {
			var value:Dynamic = null;
			try {
				value = Reflect.field(values, name);
			} catch (_:Dynamic) {}
			if (value != null) {
				Reflect.setField(packed, name, value);
				found = true;
			}
		}
		return found ? Json.stringify(packed) : '';
	}
}
