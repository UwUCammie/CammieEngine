package;

import haxe.Json;
import haxe.io.Path;

#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** A non-fatal finding produced while translating Codename Engine content.
	Structurally identical to the V-Slice finding so the shared importer
	appenders can format both without a bridge layer. */
typedef CodenameDiagnostic = {
	var severity:String;
	var code:String;
	var message:String;
	@:optional var path:String;
	@:optional var difficulty:String;
}

/** One native chart produced from a Codename charts/<difficulty>.json file. */
typedef CodenameConvertedChart = {
	var difficulty:String;
	var fileName:String;
	var chart:Dynamic;
	/** Authored Codename type table, kept difficulty-local for note-script loading. */
	@:optional var noteTypes:Array<Dynamic>;
	/** Section-based charts carry their own authored song title. */
	@:optional var authoredSongTitle:Bool;
	/** Indexed authored strumlines used by Codename's live camera target. */
	@:optional var cameraLines:Array<Dynamic>;
	var diagnostics:Array<CodenameDiagnostic>;
}

/** Result of converting one Codename meta.json + charts/<diff>.json pair. */
typedef CodenameConversionResult = {
	var songName:String;
	var displayName:String;
	/** Complete data-only meta.json object; owner sidecar retains custom fields. */
	var originalMeta:Dynamic;
	var sourcePath:String;
	var charts:Array<CodenameConvertedChart>;
	/** Native noteInfo definitions for authored note kinds with no built-in
		equivalent.  Identity-only preservation, shared by every difficulty. */
	var noteDefinitions:Array<Dynamic>;
	var diagnostics:Array<CodenameDiagnostic>;
}

/** Pure conversion output for one Codename data/characters/<name>.xml definition. */
typedef CodenameCharacterConversion = {
	var name:String;
	var registryEntry:Dynamic;
	var hscript:String;
	var assets:Array<Dynamic>;
	var diagnostics:Array<CodenameDiagnostic>;
	/** Codename conversion keeps the existing import behavior. The shared visual
	 * materializer consults this only to reject explicitly unsupported V-Slice
	 * conversions, which Codename does not currently produce. */
	@:optional var supported:Bool;
}

/** Pure conversion output for one Codename data/stages/<name>.xml definition. */
typedef CodenameStageConversion = {
	var name:String;
	var registryValue:String;
	var hscript:String;
	var assets:Array<Dynamic>;
	var diagnostics:Array<CodenameDiagnostic>;
}

/**
	Codename Engine chart/metadata conversion.

	This class intentionally has no dependency on the in-game importer.  It is a
	pure data converter so discovery can plan work without loading Flixel
	objects or writing to the destination asset tree.

	A Codename song folder is shaped:

		songs/<song>/meta.json            {color, icon, difficulties, displayName, bpm, ...}
		songs/<song>/charts/<diff>.json   {codenameChart: true, scrollSpeed, stage, strumLines, noteTypes, events}
		songs/<song>/song/Inst.ogg        plus Voices-Player.ogg / Voices-Opponent.ogg
		songs/<song>/events.json          optional shared event sidecar

	Each charts/<diff>.json becomes one native difficulty.  Codename keeps one
	note list per strum line, so conversion classifies every line
	(opponent/player/girlfriend) and maps its lanes into the native 0-7 block:
	player lanes 0-3, opponent lanes 4-7.  Lines which are neither player nor
	opponent (Codename girlfriend lines, custom positions) have no native
	gameplay lane; their original records are retained separately with their
	line and note ordinals while the native lane omission is diagnosed.

	Codename times and sustain lengths are milliseconds and are copied to the
	native note rows unchanged.
*/
class CodenameImporter {
	public static inline var ENGINE_NAME:String = 'Codename Engine';

	static inline var EPSILON:Float = 0.0001;
	static inline var DEFAULT_BPM:Float = 100;
	static inline var DEFAULT_SECTION_STEPS:Int = 16;
	static inline var MAX_KEY_LANES:Int = 4;

	/** Returns true for Codename song meta.json documents.  The shape is
		deliberately checked against the fields every Codename version writes
		(difficulties + bpm + stepsPerBeat); a loose `meta.json` marker alone
		would collide with FPS Plus metadata. */
	public static function isCodenameMeta(data:Dynamic):Bool {
		if (data == null)
			return false;
		var difficulties = field(data, 'difficulties');
		if (!Std.isOfType(difficulties, Array))
			return false;
		var bpm = numberValue(field(data, 'bpm'), Math.NaN);
		var steps = numberValue(field(data, 'stepsPerBeat'), Math.NaN);
		return !Math.isNaN(bpm) && bpm > 0 && !Math.isNaN(steps) && steps > 0;
	}

	/** Returns true for Codename chart documents.  `codenameChart: true` is the
		explicit marker; older exports still carry chartVersion + strumLines. */
	public static function isCodenameChart(data:Dynamic):Bool {
		if (data == null)
			return false;
		if (field(data, 'codenameChart') == true)
			return true;
		var version = stringValue(field(data, 'chartVersion'), '');
		return version != '' && Std.isOfType(field(data, 'strumLines'), Array);
	}

	/** Some Codename packs retain earlier section-based charts beside their
	 * strumline charts. These rows already use the native lane and timing model.
	 * Copy them in memory, translating only the section length and girlfriend
	 * field spellings; the donor JSON and its note/event payload stay intact. */
	public static function isEmbeddedSectionChart(data:Dynamic):Bool {
		if (isCodenameChart(data)) return false;
		var song = field(data, 'song');
		var sections = field(song, 'notes');
		if (!Std.isOfType(sections, Array)) return false;
		for (section in (cast sections:Array<Dynamic>)) {
			if (section == null || !Std.isOfType(field(section, 'sectionNotes'), Array)
				|| field(section, 'mustHitSection') == null) return false;
			for (row in (cast field(section, 'sectionNotes'):Array<Dynamic>)) {
				if (!Std.isOfType(row, Array)) return false;
				var values:Array<Dynamic> = cast row;
				if (values.length < 3 || Math.isNaN(numberValue(values[0], Math.NaN))
					|| Math.isNaN(numberValue(values[1], Math.NaN))) return false;
			}
		}
		return true;
	}

	public static function convertEmbeddedSectionChart(data:Dynamic, difficulty:String,
		?sidecar:Dynamic, ?origin:String):CodenameConvertedChart {
		if (!isEmbeddedSectionChart(data)) throw 'Expected a section-based song chart';
		var copy:Dynamic = Json.parse(Json.stringify(data));
		var song:Dynamic = field(copy, 'song');
		var findings:Array<CodenameDiagnostic> = [];
		var diff = difficulty == null || difficulty.trim() == '' ? 'normal' : difficulty.trim();
		var cameraLines:Array<Dynamic> = null;
		try cameraLines = cameraLegacyStrumlines(song)
		catch (error:Dynamic) findings.push(makeDiagnostic('warning', 'invalid-camera-strumlines',
			'Legacy character lines could not be preserved: ' + Std.string(error),
			origin == null ? '' : origin, diff));
		if (field(song, 'gf') == null) {
			var girlfriend = field(song, 'gfVersion');
			if (girlfriend == null) girlfriend = field(song, 'player3');
			if (girlfriend != null) Reflect.setField(song, 'gf', girlfriend);
		}
		for (section in (cast field(song, 'notes'):Array<Dynamic>)) {
			if (field(section, 'lengthInSteps') != null) continue;
			var beats = numberValue(field(section, 'sectionBeats'), 4);
			if (Math.isNaN(beats) || beats <= 0) beats = 4;
			Reflect.setField(section, 'lengthInSteps', Std.int(beats * 4));
		}
		var shared = sidecarEvents(sidecar);
		if (shared.length > 0) {
			var events:Dynamic = field(song, 'events');
			var groups:Array<Dynamic> = Std.isOfType(events, Array) ? cast events : [];
			for (group in convertEvents(shared, findings, origin == null ? '' : origin, diff, 0))
				groups.push(group);
			Reflect.setField(song, 'events', groups);
		}
		return {difficulty:diff, fileName:diff + '.json', chart:copy,
			authoredSongTitle:true,
			cameraLines:cameraLines, diagnostics:findings};
	}

	/** Codename's legacy parser constructs these three authored line slots from
	 * section charts before stage placement and camera events are evaluated. */
	public static function cameraLegacyStrumlines(song:Dynamic):Array<Dynamic> {
		var opponent:Dynamic = field(song, 'player2');
		var player:Dynamic = field(song, 'player1');
		if (!Std.isOfType(opponent, String) || !Std.isOfType(player, String))
			throw 'Legacy chart needs player1 and player2 character IDs';
		var girlfriend:Dynamic = field(song, 'gf');
		if (girlfriend == null) girlfriend = field(song, 'gfVersion');
		if (girlfriend == null) girlfriend = field(song, 'player3');
		if (girlfriend == null) girlfriend = 'gf';
		if (!Std.isOfType(girlfriend, String)) throw 'Invalid legacy girlfriend character ID';
		var opponentIsGirlfriend = (cast opponent:String).startsWith('gf');
		var lines:Array<Dynamic> = [
			{type:0, position:opponentIsGirlfriend ? 'girlfriend' : 'dad', characters:[opponent]},
			{type:1, position:'boyfriend', characters:[player]}
		];
		if (!opponentIsGirlfriend && girlfriend != 'none')
			lines.push({type:2, position:'girlfriend', characters:[girlfriend], visible:false});
		return cameraStrumlines({strumLines:lines});
	}

	/** Parse and convert JSON strings without touching the filesystem. */
	public static function convertJson(metaJson:String, chartJson:String, ?difficulty:String,
		?sourcePath:String, ?sidecar:Dynamic, ?noteDefinitions:Array<Dynamic>,
		?noteKindIndexes:Map<String, Int>):CodenameConversionResult {
		if (metaJson == null || chartJson == null)
			throw 'Codename meta and chart JSON are both required';
		var meta:Dynamic;
		var chart:Dynamic;
		try {
			meta = Json.parse(metaJson);
		} catch (e:Dynamic) {
			throw 'Unable to parse Codename meta.json: ' + Std.string(e);
		}
		try {
			chart = Json.parse(chartJson);
		} catch (e:Dynamic) {
			throw 'Unable to parse Codename chart: ' + Std.string(e);
		}
		return convert(meta, chart, difficulty, sourcePath, sidecar, noteDefinitions, noteKindIndexes);
	}

	/** Read a meta/chart pair and convert them.  Kept separate from
		`convertJson` so callers that already have a scan plan stay read-only.
		`noteDefinitions`/`noteKindIndexes` are shared across every difficulty of
		one song so a kind keeps the same custom-note marker in each chart. */
	#if sys
	public static function convertFiles(metaPath:String, chartPath:String, ?difficulty:String,
		?sourcePath:String, ?sidecar:Dynamic, ?noteDefinitions:Array<Dynamic>,
		?noteKindIndexes:Map<String, Int>, ?resolvedMeta:Dynamic):CodenameConversionResult {
		var meta = File.getContent(metaPath);
		var chart = File.getContent(chartPath);
		var origin = sourcePath == null || sourcePath.trim() == '' ? metaPath : sourcePath;
		if (resolvedMeta != null) {
			var converted = convert(resolvedMeta, Json.parse(chart), difficulty, origin, sidecar,
				noteDefinitions, noteKindIndexes);
			converted.originalMeta = Json.parse(meta);
			return converted;
		}
		return convertJson(meta, chart, difficulty, origin, sidecar, noteDefinitions, noteKindIndexes);
	}
	#end

	/**
		Convert one meta/chart pair.  `difficulty` is the authored difficulty id
		the chart file represents (Codename keeps one chart file per difficulty;
		discovery derives it from the chart file stem).  `sidecar` carries the
		song's shared events.json payload which Codename merges with every
		difficulty's own events; identical rows are deduplicated at runtime by
		the native event collector.
	*/
	public static function convert(meta:Dynamic, chart:Dynamic, ?difficulty:String,
		?sourcePath:String, ?sidecar:Dynamic, ?sharedNoteDefinitions:Array<Dynamic>,
		?sharedNoteKindIndexes:Map<String, Int>):CodenameConversionResult {
		var findings:Array<CodenameDiagnostic> = [];
		var origin = sourcePath == null ? '' : sourcePath;
		if (!isCodenameMeta(meta))
			findings.push(makeDiagnostic('warning', 'metadata-version',
				'Metadata is not recognised as a Codename song meta.json document.', origin));
		if (!isCodenameChart(chart))
			findings.push(makeDiagnostic('warning', 'chart-version',
				'Chart is not recognised as a Codename chart document.', origin));

		var displayName = stringValue(field(meta, 'displayName'), '');
		var songName = displayName == '' ? 'codename-song' : displayName;
		var diff = difficulty == null || difficulty.trim() == '' ? defaultDifficulty(meta) : difficulty.trim();

		var bpm = numberValue(field(meta, 'bpm'), DEFAULT_BPM);
		if (bpm <= 0) {
			bpm = DEFAULT_BPM;
			findings.push(makeDiagnostic('warning', 'invalid-bpm',
				'Codename meta did not provide a positive BPM; using ' + DEFAULT_BPM + '.', origin, diff));
		}
		var stepsPerBeat = Std.int(numberValue(field(meta, 'stepsPerBeat'), 4));
		if (stepsPerBeat <= 0)
			stepsPerBeat = 4;
		var beatsPerMeasure = Std.int(numberValue(field(meta, 'beatsPerMeasure'),
			numberValue(field(meta, 'beatsPerBeat'), 4)));
		if (beatsPerMeasure <= 0)
			beatsPerMeasure = 4;
		var sectionSteps = stepsPerBeat * beatsPerMeasure;
		if (sectionSteps != DEFAULT_SECTION_STEPS)
			findings.push(makeDiagnostic('warning', 'nonstandard-section-length',
				'Codename stepsPerBeat x beatsPerMeasure = ' + sectionSteps
				+ ' steps per section; the native section length follows the authored value.', origin, diff));

		var speed = numberValue(field(chart, 'scrollSpeed'), 1);
		if (speed <= 0 || Math.isNaN(speed)) {
			speed = 1;
			findings.push(makeDiagnostic('warning', 'invalid-scroll-speed',
				'Codename scrollSpeed was not positive; using 1.', origin, diff));
		}

		var authoredStage = stringValue(field(chart, 'stage'), '');
		var chartEvents:Dynamic = field(chart, 'events');
		var sharedEvents = sidecarEvents(sidecar);
		var convertedEvents = convertEvents(
			mergeEventSources(chartEvents, sharedEvents), findings, origin, diff,
			Std.isOfType(chartEvents, Array) ? (cast chartEvents:Array<Dynamic>).length : 0);

		// Note definitions are shared across one song's difficulties so a kind
		// keeps the same custom-note marker in every chart.
		var noteDefinitions:Array<Dynamic> = sharedNoteDefinitions != null ? sharedNoteDefinitions : [];
		var noteKindIndexes:Map<String, Int> = sharedNoteKindIndexes != null ? sharedNoteKindIndexes : new Map<String, Int>();
		var strumLines:Dynamic = field(chart, 'strumLines');
		var lineList:Array<Dynamic> = Std.isOfType(strumLines, Array) ? (cast strumLines:Array<Dynamic>) : [];
		if (!Std.isOfType(strumLines, Array))
			findings.push(makeDiagnostic('error', 'invalid-strum-lines',
				'Codename chart has no strumLines array; an empty chart was emitted.', origin, diff));
		var noteTypes:Dynamic = field(chart, 'noteTypes');
		var authoredNoteTypes:Array<Dynamic> = Std.isOfType(noteTypes, Array)
			? (cast noteTypes:Array<Dynamic>).copy() : [];

		var playerCharacter = '';
		var opponentCharacter = '';
		var girlfriendCharacter = '';
		var noteRows:Array<Dynamic> = [];
		var maxTime:Float = 0;
		var extraLineCount = 0;
		var extraLineNotes = 0;
		var gfLineNotes = 0;
		// Keep source rows and ordinals for every non-player line, including GF
		// rows projected to the native CPU lane. This preserves original payloads
		// for per-line callbacks and future adapters without mutating the donor.
		var unsupportedNotes:Array<Dynamic> = [];

		for (lineIndex in 0...lineList.length) {
			var line = lineList[lineIndex];
			if (line == null)
				continue;
			var side = strumLineSide(line, lineIndex);
			var lineCharacters = lineCharacterReferences(line);
			if (side == 'player') {
				if (playerCharacter == '' && lineCharacters.length > 0)
					playerCharacter = lineCharacters[0];
			} else if (side == 'opponent') {
				if (opponentCharacter == '' && lineCharacters.length > 0)
					opponentCharacter = lineCharacters[0];
			} else if (side == 'gf') {
				if (girlfriendCharacter == '' && lineCharacters.length > 0)
					girlfriendCharacter = lineCharacters[0];
			} else {
				extraLineCount++;
				findings.push(makeDiagnostic('warning', 'unsupported-strum-line',
					'Codename strum line ' + lineIndex + ' (' + strumLineLabel(line)
					+ ') has no native player/opponent lane; its notes cannot be converted.', origin, diff));
			}

			var keyCountValue = numberValue(field(line, 'keyCount'), 4);
			var keyCount = !Math.isFinite(keyCountValue) || keyCountValue < 1
				|| keyCountValue != Math.floor(keyCountValue) ? 4 : Std.int(keyCountValue);
			if (keyCount > MAX_KEY_LANES)
				findings.push(makeDiagnostic('warning', 'unsupported-key-count',
					'Codename strum line ' + lineIndex + ' declares ' + keyCount
					+ ' keys; only the first ' + MAX_KEY_LANES + ' lanes exist natively and extra lanes were skipped.', origin, diff));
			if (keyCount > MAX_KEY_LANES)
				findings.push(makeDiagnostic('warning', 'codename-strumline-unsupported',
					'Codename strum line ' + lineIndex + ' declares ' + keyCount
					+ ' keys; this host materializes only ' + MAX_KEY_LANES
					+ ' receptors, so source lanes ' + MAX_KEY_LANES + ' and above are unavailable.', origin, diff));

			var notes = field(line, 'notes');
			if (!Std.isOfType(notes, Array))
				continue;
			var laneOffset = side == 'opponent' || side == 'gf' ? MAX_KEY_LANES : 0;
			var lineHasNativeRows = side == 'player' || side == 'opponent' || side == 'gf';
			var lineTypeValue:Dynamic = field(line, 'type');
			var lineType:Null<Int> = Std.isOfType(lineTypeValue, Int) ? cast lineTypeValue : null;
			var noteList:Array<Dynamic> = cast notes;
			for (noteIndex in 0...noteList.length) {
				var rawNote = noteList[noteIndex];
				if (side == 'gf' || !lineHasNativeRows)
					unsupportedNotes.push({lineIndex:lineIndex, noteIndex:noteIndex,
						lineType:lineType, role:side, note:Json.parse(Json.stringify(rawNote))});
				if (rawNote == null)
					continue;
				var time = numberValue(field(rawNote, 'time'), Math.NaN);
				if (Math.isNaN(time)) {
					findings.push(makeDiagnostic('warning', 'invalid-note-time',
						'A Codename note has no numeric time (milliseconds) and was skipped.', origin, diff));
					continue;
				}
				if (time < 0) {
					findings.push(makeDiagnostic('warning', 'negative-note-time',
						'A Codename note occurred before zero and was clamped to zero.', origin, diff));
					time = 0;
				}
				if (!lineHasNativeRows) {
					extraLineNotes++;
					continue;
				}
				var laneFloat = numberValue(field(rawNote, 'id'), Math.NaN);
				if (Math.isNaN(laneFloat) || laneFloat != Math.floor(laneFloat)) {
					findings.push(makeDiagnostic('warning', 'invalid-note-lane',
						'A Codename note has no integer id lane and was skipped.', origin, diff));
					continue;
				}
				var lane = Std.int(laneFloat);
				if (lane < 0 || lane >= keyCount) {
					findings.push(makeDiagnostic('warning', 'invalid-note-lane',
						'A Codename note id ' + lane + ' is outside its strum line keyCount '
						+ keyCount + ' and was skipped.', origin, diff));
					continue;
				}
				if (lane >= MAX_KEY_LANES) {
					findings.push(makeDiagnostic('warning', 'unsupported-note-lane',
						'Codename lane ' + lane + ' is outside the native ' + MAX_KEY_LANES
						+ '-key line and was skipped.', origin, diff));
					continue;
				}
				if (side == 'gf')
					gfLineNotes++;
				var sustain = numberValue(field(rawNote, 'sLen'), 0);
				if (Math.isNaN(sustain) || sustain < 0)
					sustain = 0;
				var kind = noteKind(rawNote, noteTypes, findings, origin, diff,
					noteDefinitions, noteKindIndexes);
				// Native custom notes use a 4-key block starting at
				// lane + (customIndex + 5) * 8, the same marker convention the
				// V-Slice converter emits so one runtime bridge serves both engines.
				var nativeLane = lane + laneOffset;
				if (kind.customIndex >= 0)
					nativeLane += (kind.customIndex + 5) * 8;
				var row:Array<Dynamic> = [time, nativeLane, sustain];
				if (kind.alt > 0)
					row.push(kind.alt);
				row = CodenameNoteMetadata.apply(row,
					CodenameNoteMetadata.create(lineIndex, noteIndex, lineType,
						 side == 'player' ? 0 : 1));
				noteRows.push({time: time, row: row, sustainEnd: time + sustain});
				if (time + sustain > maxTime)
					maxTime = time + sustain;
			}
		}
		if (extraLineCount > 0 && extraLineNotes > 0)
			findings.push(makeDiagnostic('warning', 'extra-strumline-notes',
				extraLineNotes + ' note(s) on non-player/opponent Codename strum line(s) were skipped; '
				+ 'the native chart schema has no third gameplay lane.', origin, diff));
		if (gfLineNotes > 0)
			findings.push(makeDiagnostic('info', 'gf-strumline-notes-routed',
				gfLineNotes + ' Codename girlfriend-line note(s) were projected onto the non-playable native side '
				+ 'with authored line/note identity preserved for CPU callback and GF-singing dispatch.', origin, diff));

		var cameraLines:Array<Dynamic> = null;
		try cameraLines = cameraStrumlines(chart)
		catch (error:Dynamic) findings.push(makeDiagnostic('warning', 'invalid-camera-strumlines',
			'Authored camera strumlines could not be preserved: ' + Std.string(error), origin, diff));
		findings = deduplicateDiagnostics(findings);
		for (event in convertedEvents) {
			var eventTime:Float = event[0];
			if (eventTime > maxTime)
				maxTime = eventTime;
		}

		var sections = buildSections(noteRows, maxTime, bpm, sectionSteps);
		var songData:Dynamic = {
			song: songName,
			notes: sections,
			bpm: bpm,
			needsVoices: field(meta, 'needsVoices') == true,
			speed: speed,
			player1: playerCharacter == '' ? 'bf' : playerCharacter,
			player2: opponentCharacter == '' ? 'dad' : opponentCharacter,
			gf: girlfriendCharacter == '' ? 'gf' : girlfriendCharacter,
			stage: authoredStage == '' ? 'stage' : authoredStage,
			stageID: 0,
			uiType: 'normal',
			cutsceneType: 'none',
			isMoody: false,
			isSpooky: false,
			isHey: false,
			isCheer: false,
			preferredNoteAmount: 4,
			mania: 0,
			forceJudgements: false,
			convertMineToNuke: false
		};
		// Keep the original type table on the selected native chart. This is the
		// source identity used to load owner-scoped Codename data/notes scripts.
		songData.codenameNoteTypes = authoredNoteTypes.copy();
		if (convertedEvents.length > 0)
			songData.events = convertedEvents;
		if (unsupportedNotes.length > 0)
			Reflect.setField(songData, 'codenameUnsupportedNotes', unsupportedNotes);

		return {
			songName: songName,
			displayName: displayName,
			originalMeta: Json.parse(Json.stringify(meta)),
			sourcePath: origin,
			charts: [{
				difficulty: diff,
				fileName: nativeFileName(songName, diff),
				chart: {song: songData},
				noteTypes: authoredNoteTypes,
				cameraLines: cameraLines,
				diagnostics: findings
			}],
			noteDefinitions: noteDefinitions,
			diagnostics: findings
		};
	}

	/** Preserve every authored index and character occurrence, including
	 * camera-only strumlines whose notes cannot enter the native chart. */
	public static function cameraStrumlines(chart:Dynamic):Array<Dynamic> {
		var raw:Dynamic = field(chart, 'strumLines');
		if (!Std.isOfType(raw, Array)) throw 'Chart has no strumLines array';
		var result:Array<Dynamic> = [];
		for (index in 0...(cast raw:Array<Dynamic>).length) {
			var line:Dynamic = (cast raw:Array<Dynamic>)[index];
			// Codename skips null entries while retaining their array indices.
			if (line == null) {
				result.push(null);
				continue;
			}
			var rawType:Dynamic = field(line, 'type');
			var type:Null<Int> = null;
			if (rawType != null) {
				var parsed = numberValue(rawType, Math.NaN);
				if (!Math.isFinite(parsed) || parsed < 0 || parsed != Math.floor(parsed))
					throw 'Invalid strumline type at ' + index;
				type = Std.int(parsed);
			}
			var position:Dynamic = field(line, 'position');
			if (position != null && !Std.isOfType(position, String))
				throw 'Invalid strumline position at ' + index;
			var ids:Array<String> = [];
			var rawIds:Dynamic = field(line, 'characters');
			if (rawIds != null && !Std.isOfType(rawIds, Array))
				throw 'Invalid character list at strumline ' + index;
			if (Std.isOfType(rawIds, Array)) for (id in (cast rawIds:Array<Dynamic>)) {
				if (!Std.isOfType(id, String) || !CodenameScriptDiscovery.safeRelativeName(cast id)
					|| StringTools.trim(cast id) == '')
					throw 'Unsafe character id at strumline ' + index;
				ids.push(cast id);
			}
			var role = strumLineSide(line, index);
			var keyCountValue = numberValue(field(line, 'keyCount'), 4);
			var keyCount = !Math.isFinite(keyCountValue) || keyCountValue < 1
				|| keyCountValue != Math.floor(keyCountValue) ? 4 : Std.int(keyCountValue);
			var linePosDefault = CodenameStrumlineLayout.defaultLinePosition(type);
			var linePos = numberValue(field(line, 'strumLinePos'), linePosDefault);
			if (!Math.isFinite(linePos)) linePos = linePosDefault;
			var strumScale = numberValue(field(line, 'strumScale'), 1);
			if (!Math.isFinite(strumScale) || strumScale <= 0) strumScale = 1;
			var strumSpacing = numberValue(field(line, 'strumSpacing'), 1);
			if (!Math.isFinite(strumSpacing) || strumSpacing <= 0) strumSpacing = 1;
			var strumPos:Array<Float> = [0, 50];
			var rawStrumPos = field(line, 'strumPos');
			if (Std.isOfType(rawStrumPos, Array)) {
				var authoredPos:Array<Dynamic> = cast rawStrumPos;
				if (authoredPos.length >= 2) {
					var posX = numberValue(authoredPos[0], Math.NaN);
					var posY = numberValue(authoredPos[1], Math.NaN);
					if (Math.isFinite(posX) && Math.isFinite(posY)) strumPos = [posX, posY];
				}
			}
			result.push({role:role, type:type,
				position:position,
				visible:field(line, 'visible') != false, characters:ids,
				keyCount:keyCount, strumLinePos:linePos, strumPos:strumPos,
				strumScale:strumScale, strumSpacing:strumSpacing});
		}
		return result;
	}

	static function cameraXmlNumber(element:Xml, name:String):Float {
		var raw = xmlAttr(element, name, '0');
		var number = Std.parseFloat(raw);
		if (!Math.isFinite(number)) throw 'Invalid Codename camera XML attribute ' + name;
		return number;
	}

	/** Source character x/y are animation/global offsets; camx/camy are the
	 * additional camera offsets consumed by Character.getCameraPosition(). XML
	 * isPlayer controls playerOffsets, not the actor's constructor camera role. */
	public static function cameraCharacterOffsets(xmlText:String):Dynamic {
		var root = parseDefinitionXml(xmlText, 'character');
		if (xmlNodeName(root) != 'character') throw 'Camera character XML has no character root';
		var centered:Null<Bool> = null;
		if (root.exists('centercam')) {
			var authored = root.get('centercam');
			if (authored != 'true' && authored != 'false') throw 'Invalid Codename centercam attribute';
			centered = authored == 'true';
		}
		var playerOffsets:Null<Bool> = null;
		if (root.exists('isPlayer')) {
			var authoredPlayer = root.get('isPlayer');
			if (authoredPlayer != 'true' && authoredPlayer != 'false') throw 'Invalid Codename isPlayer attribute';
			playerOffsets = authoredPlayer == 'true';
		}
		return {globalX:cameraXmlNumber(root, 'x'), globalY:cameraXmlNumber(root, 'y'),
			cameraX:cameraXmlNumber(root, 'camx'), cameraY:cameraXmlNumber(root, 'camy'),
			centeredCamera:centered, playerOffsets:playerOffsets};
	}

	/** Stage character placeholders add these offsets to cameraOffset. */
	public static function cameraStageOffsets(xmlText:String):Dynamic {
		return Reflect.field(cameraStageInfo(xmlText), 'offsets');
	}

	/** An absent startCamPos axis is distinct from an authored zero axis. */
	public static function cameraStageInfo(xmlText:String):Dynamic {
		var model = CodenameStagePlacement.parse(xmlText);
		var result:Dynamic = {};
		for (name in ['dad', 'boyfriend', 'girlfriend']) {
			var slot = model.slots.get(name);
			var role = name == 'boyfriend' ? 'bf' : (name == 'girlfriend' ? 'gf' : 'dad');
			Reflect.setField(result, role, {cameraX:slot.cameraX, cameraY:slot.cameraY});
		}
		return {offsets:result, startCamera:model.startCamera,
			placement:CodenameStagePlacement.toData(model)};
	}

	/** Suggested native filename for one converted Codename difficulty. */
	public static function nativeFileName(songName:String, difficulty:String):String {
		return VSliceImporter.nativeFileName(songName, difficulty);
	}

	/** First authored difficulty, or normal when the meta lists none. */
	public static function defaultDifficulty(meta:Dynamic):String {
		var difficulties = field(meta, 'difficulties');
		if (Std.isOfType(difficulties, Array)) {
			for (entry in (cast difficulties:Array<Dynamic>)) {
				var value = stringValue(entry, '');
				if (value != '')
					return value;
			}
		}
		return 'normal';
	}

	/** Authored difficulty ids in stable order. */
	public static function difficultyNames(meta:Dynamic):Array<String> {
		var result:Array<String> = [];
		var difficulties = field(meta, 'difficulties');
		if (Std.isOfType(difficulties, Array))
			for (entry in (cast difficulties:Array<Dynamic>)) {
				var value = stringValue(entry, '');
				if (value != '' && result.indexOf(value) < 0)
					result.push(value);
			}
		return result;
	}

	/** Classify one authored strum line: opponent, player, gf, or extra.
		The explicit Codename `type` marker wins (0=opponent, 1=player, 2=gf),
		then the position token, then document order.  Bully-mod's player line
		authored `position: "dad"` with `type: 1`, so the order matters. */
	public static function strumLineSide(line:Dynamic, index:Int):String {
		var typeValue = field(line, 'type');
		if (typeValue != null && !Std.isOfType(typeValue, String)) {
			var type = Std.parseFloat(Std.string(typeValue));
			if (!Math.isNaN(type)) {
				if (type == 0) return 'opponent';
				if (type == 1) return 'player';
				if (type == 2) return 'gf';
				return 'extra';
			}
		}
		var position = stringValue(field(line, 'position'), '').toLowerCase();
		if (position != '') {
			// A pure number is a custom screen position, not a side token.
			var numeric = Std.parseFloat(position);
			if (Math.isNaN(numeric)) {
				switch (position) {
					case 'dad' | 'opponent' | 'enemy':
						return 'opponent';
					case 'bf' | 'boyfriend' | 'player':
						return 'player';
					case 'gf' | 'girlfriend':
						return 'gf';
				}
			}
		}
		return index == 0 ? 'opponent' : (index == 1 ? 'player' : 'extra');
	}

	static function strumLineLabel(line:Dynamic):String {
		var position = stringValue(field(line, 'position'), '');
		var label = position == '' ? 'index-only' : 'position ' + position;
		var characters = lineCharacterReferences(line);
		if (characters.length > 0)
			label += ', character ' + characters.join('/');
		return label;
	}

	static function lineCharacterReferences(line:Dynamic):Array<String> {
		var result:Array<String> = [];
		var characters = field(line, 'characters');
		if (!Std.isOfType(characters, Array))
			return result;
		for (entry in (cast characters:Array<Dynamic>)) {
			var value = stringValue(entry, '');
			if (value != '' && result.indexOf(value) < 0)
				result.push(value);
		}
		return result;
	}

	/**
		Resolve one authored note kind.  Codename notes store `type` as either a
		string kind or an index into the chart's `noteTypes` table (0 is the
		implicit default).  Unknown kinds become native custom-note definitions
		which preserve identity only, matching the V-Slice contract.
	*/
	static function noteKind(note:Dynamic, noteTypes:Dynamic, findings:Array<CodenameDiagnostic>,
		origin:String, difficulty:String, noteDefinitions:Array<Dynamic>,
		noteKindIndexes:Map<String, Int>):{alt:Int, customIndex:Int} {
		if (field(note, 'alt') == true)
			return {alt: 1, customIndex: -1};
		var raw:Dynamic = field(note, 'type');
		if (raw == null)
			return {alt: 0, customIndex: -1};
		var kind = '';
		if (Std.isOfType(raw, String)) {
			kind = StringTools.trim(raw);
			// A numeric string is an index into noteTypes, not a kind name.
			var asNumber = Std.parseFloat(kind);
			if (!Math.isNaN(asNumber) && Std.string(Std.int(asNumber)) == kind)
				kind = lookupNoteType(Std.int(asNumber), noteTypes);
		} else {
			var index = Std.int(numberValue(raw, Math.NaN));
			if (Math.isNaN(index))
				return {alt: 0, customIndex: -1};
			kind = lookupNoteType(index, noteTypes);
		}
		if (kind == '' || kind.toLowerCase() == 'default' || kind.toLowerCase() == 'normal')
			return {alt: 0, customIndex: -1};
		var normalized = kind.toLowerCase().trim();
		if (normalized == 'alt-anim' || normalized == 'alt' || normalized == 'alt-animation')
			return {alt: 1, customIndex: -1};
		var customIndex = noteKindIndexes.get(normalized);
		if (customIndex == null) {
			customIndex = noteDefinitions.length;
			noteKindIndexes.set(normalized, customIndex);
			var kindId = safeIdentifier(kind);
			var definition:Dynamic = {
				noteName: 'Codename ' + kind,
				animNames: ['purple', 'blue', 'green', 'red'],
				animInt: [4, 5, 6, 7],
				// Identity-only preservation, exactly like the V-Slice converter:
				// the donor engine's hit/miss semantics are not guessed here.
				classes: ['codename', 'codename-kind:' + kindId],
				id: 'codename:' + kindId + ':' + customIndex,
				sourceKind: kind,
				sourceEngine: ENGINE_NAME
			};
			noteDefinitions.push(definition);
			if (NoteTypeCompat.applyVSliceKind(definition, kind)) {
				findings.push(makeDiagnostic('info', 'note-kind-native',
					'Codename note kind ' + kind + ' uses the centralized native '
					+ Std.string(Reflect.field(definition, 'sourceNoteType')) + ' behavior adapter.',
					origin, difficulty));
			} else {
				findings.push(makeDiagnostic('warning', 'note-kind-generic',
					'Codename note kind ' + kind + ' was preserved as a native custom note identity; '
					+ 'donor-specific hit/miss behavior remains unsupported until a script bridge is available.',
					origin, difficulty));
			}
		}
		return {alt: 0, customIndex: customIndex};
	}

	static function lookupNoteType(index:Int, noteTypes:Dynamic):String {
		if (!Std.isOfType(noteTypes, Array))
			return '';
		var list:Array<Dynamic> = cast noteTypes;
		// Codename's table lists authored kinds after the implicit default, so
		// index 0 is always the default kind and index 1 reads entry 0.
		if (index >= 1 && index <= list.length)
			return stringValue(list[index - 1], '');
		return '';
	}

	/**
		Convert Codename event objects into native event groups.  Codename keeps
		positioned `params` arrays rather than named fields, so the recognized
		kinds route explicitly; anything else is preserved whole for the runtime
		foreign-event dispatch (the same contract as V-Slice imports).
	*/
	public static function convertEvents(source:Dynamic, findings:Array<CodenameDiagnostic>,
		origin:String, difficulty:String, ?chartCount:Null<Int>):Array<Dynamic> {
		var converted:Array<Dynamic> = [];
		if (!Std.isOfType(source, Array))
			return converted;
		var authored:Array<Dynamic> = cast source;
		for (index in 0...authored.length) {
			var event = authored[index];
			if (event == null)
				continue;
			var time = numberValue(field(event, 'time'), Math.NaN);
			var name = stringValue(field(event, 'name'), '');
			if (Math.isNaN(time) || name == '') {
				findings.push(makeDiagnostic('warning', 'invalid-event',
					'Codename event is missing a numeric time or event name and was skipped.', origin, difficulty));
				continue;
			}
			var params:Dynamic = field(event, 'params');
			var values:Array<Dynamic> = Std.isOfType(params, Array) ? (cast params:Array<Dynamic>) : [];
			var isShared = chartCount != null && index >= chartCount;
			var sourceKind = isShared ? 'shared' : 'chart';
			var sourceOrder = isShared ? index - chartCount : index;
			var authoredGlobal:Dynamic = field(event, 'global');
			var global = Std.isOfType(authoredGlobal, Bool) ? authoredGlobal : isShared;
			var route = routeCodenameEvent(name, values);
			if (route == null) {
				var payload:Dynamic = {engine: 'codename', name: name};
				if (values.length > 0)
					Reflect.setField(payload, 'params', values);
				var row:Array<Dynamic> = [name, Json.stringify(payload), '', ''];
				row.push(CodenameEventMetadata.create(name, time, values,
					sourceKind, sourceOrder, global, row));
				appendEvent(converted, time, row);
				findings.push(makeDiagnostic('info', 'foreign-event-preserved',
					'Codename event ' + name + ' was preserved for runtime compatibility dispatch.', origin, difficulty));
				continue;
			}
			var row:Array<Dynamic> = [route.name, route.v1, route.v2, route.v3];
			row.push(CodenameEventMetadata.create(name, time, values,
				sourceKind, sourceOrder, global, row));
			appendEvent(converted, time, row);
		}
		// hxcpp's native Array.sort corrupts these mixed Dynamic groups (the
		// V-Slice converter documents the same failure), so sort by hand.
		var sorted:Array<Dynamic> = [];
		for (group in converted) {
			var time:Float = group[0];
			var index = sorted.length;
			while (index > 0) {
				var prior:Dynamic = sorted[index - 1];
				if ((prior[0]:Float) <= time)
					break;
				sorted[index] = prior;
				index--;
			}
			sorted[index] = group;
		}
		return sorted;
	}

	/** Merge one chart's own events with the song's shared events.json rows. */
	public static function mergeEventSources(chartEvents:Dynamic, sidecarRows:Dynamic):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (Std.isOfType(chartEvents, Array))
			for (entry in (cast chartEvents:Array<Dynamic>))
				result.push(entry);
		if (Std.isOfType(sidecarRows, Array))
			for (entry in (cast sidecarRows:Array<Dynamic>))
				result.push(entry);
		return result;
	}

	/** Unwrap a Codename events.json sidecar into its event array. */
	public static function sidecarEvents(value:Dynamic):Array<Dynamic> {
		if (value == null)
			return [];
		var events = field(value, 'events');
		if (Std.isOfType(events, Array))
			return cast events;
		if (Std.isOfType(value, Array))
			return cast value;
		return [];
	}

	/**
		Route one Codename event to its native row.  Codename orders camera
		character indexes dad(0), bf(1), gf(2) while the native Focus Camera
		order is bf(0), dad(1), gf(2), so integer targets are remapped and named
		targets pass through.  Returns null for kinds with no native equivalent
		so the caller preserves the authored row.
	*/
	public static function routeCodenameEvent(name:String, params:Array<Dynamic>):Null<EngineCompat.EngineCompatEventRoute> {
		var canonical = name == null ? '' : StringTools.trim(name);
		if (canonical == '')
			return null;
		var param = function(index:Int, fallback:String):String {
			if (params == null || index < 0 || index >= params.length || params[index] == null)
				return fallback;
			return Std.string(params[index]);
		};
		switch (canonical.toLowerCase()) {
			case 'camera zoom':
				// params: [enabled, zoom, camera, durationSteps, ease, easeDir, mode, ...]
				// The native 'Camera Zoom' handler splits v1/v2 by comma with this
				// exact layout; a leading false is an authored disabled row there too.
				var route:EngineCompat.EngineCompatEventRoute = {name: 'Camera Zoom', v1: '', v2: '', v3: ''};
				route.v1 = [param(0, 'true'), param(1, '1'), param(2, 'camGame'), param(3, '4')].join(',');
				route.v2 = [param(4, ''), param(5, ''), param(6, 'direct'), param(7, '')].join(',');
				return route;
			case 'camera position':
				// params: [x, y, cancelMovement, durationSteps, ease, easeDir, ...]
				// An absolute camera target names no character, so route char=-1
				// (the native "no character focus" sentinel) instead of letting the
				// runtime default -2 trace a failed character lookup.
				var route:EngineCompat.EngineCompatEventRoute = {name: 'Focus Camera', v1: '', v2: '', v3: ''};
				route.v1 = param(0, '0');
				route.v2 = param(1, '0');
				route.v3 = packEventOptions(params, 2, ['cancelMovement', 'duration', 'ease', 'easeDir']);
				route.v3 = packWithChar(route.v3, '-1');
				return route;
			case 'camera movement':
				// params: [character, forced, durationSteps, ease, easeDir]
				// Codename orders characters dad(0)/bf(1)/gf(2); the native Focus
				// Camera expects bf(0)/dad(1)/gf(2), so integer targets remap.
				var route:EngineCompat.EngineCompatEventRoute = {name: 'Focus Camera', v1: '0', v2: '0', v3: ''};
				route.v3 = packEventOptions([codenameFocusChar(param(0, '0')), param(1, ''),
					param(2, ''), param(3, ''), param(4, '')], 0,
					['char', 'forced', 'duration', 'ease', 'easeDir']);
				return route;
			case 'play animation':
				// params: [character, animation, forced, status]
				var route:EngineCompat.EngineCompatEventRoute = {name: 'Play Animation', v1: '', v2: '', v3: ''};
				route.v1 = param(1, '');
				route.v2 = codenameActorToken(param(0, '0'));
				return route;
			case 'change character':
				// params: [character slot, new character id]
				var route:EngineCompat.EngineCompatEventRoute = {name: 'Change Character', v1: '', v2: '', v3: ''};
				route.v1 = codenameActorToken(param(0, 'dad'));
				route.v2 = param(1, '');
				return route;
			case 'change scroll speed':
				// params: [speed, durationSteps, ...]
				var route:EngineCompat.EngineCompatEventRoute = {name: 'Change Scroll Speed', v1: '', v2: '', v3: ''};
				route.v1 = param(0, '1');
				route.v2 = param(1, '4');
				return route;
			case 'camera flash':
				// Codename's built-in schema is [reversed, color, durationSteps, camera].
				// A regular row maps onto the native flash event. A reversed row fades
				// into the authored color, so use the native fade event instead of
				// silently turning it into a flash. Encode ColorWheel Ints as full ARGB
				// strings: decimal palette ids are not equivalent to signed color ints.
				var camera = codenameCameraToken(param(3, 'camGame'));
				var duration = param(2, '4');
				var color = codenameColorToken(params != null && params.length > 1 ? params[1] : null,
					'#FFFFFFFF');
				if (codenameBoolValue(params != null && params.length > 0 ? params[0] : null, false)) {
					var route:EngineCompat.EngineCompatEventRoute = {name: 'Camera Fade', v1: 'false', v2: duration, v3: ''};
					route.v3 = Json.stringify({color: color, duration: duration, shouldFadeIn: false,
						applyToHud: camera == 'camHUD', applyToOther: camera == 'camOther'});
					return route;
				}
				var route:EngineCompat.EngineCompatEventRoute = {name: 'Camera Flash',
					v1: camera == 'camHUD' ? 'hud' : camera == 'camOther' ? 'other' : 'game', v2: '', v3: ''};
				route.v3 = Json.stringify({color: color, duration: duration, durationSteps: true});
				return route;
			default:
				return null;
		}
	}

	/** Preserve Codename's Bool event parameters across JSON and older chart encodings. */
	static function codenameBoolValue(value:Dynamic, fallback:Bool):Bool {
		if (Std.isOfType(value, Bool))
			return cast value;
		if (value == null)
			return fallback;
		var text = StringTools.trim(Std.string(value)).toLowerCase();
		return text == 'true' || text == '1';
	}

	/** Convert a Codename ColorWheel Int to the exact alpha/color token FlxColor parses. */
	static function codenameColorToken(value:Dynamic, fallback:String):String {
		if (value == null)
			return fallback;
		var text = StringTools.trim(Std.string(value));
		if (text == '')
			return fallback;
		var numeric = Std.parseInt(text);
		if (numeric != null)
			return '#' + StringTools.hex(numeric, 8);
		if ((text.length == 6 || text.length == 8) && ~/^[0-9a-fA-F]+$/.match(text))
			return '#' + text;
		return text;
	}

	/** Normalize Codename's named camera choices for the native flash/fade handlers. */
	static function codenameCameraToken(value:String):String {
		var clean = value == null ? '' : StringTools.trim(value).toLowerCase();
		return switch (clean) {
			case 'hud' | 'camhud': 'camHUD';
			case 'other' | 'camother': 'camOther';
			case 'game' | 'camgame' | '': 'camGame';
			default: value == null ? 'camGame' : StringTools.trim(value);
		};
	}

	/** Map a Codename actor token (0=dad, 1=bf, 2=gf, or a name) onto the
		native event target vocabulary. */
	static function codenameActorToken(value:String):String {
		var clean = value == null ? '' : StringTools.trim(value);
		var lower = clean.toLowerCase();
		return switch (lower) {
			case '0' | 'dad' | 'opponent': 'dad';
			case '1' | 'bf' | 'boyfriend' | 'player': 'bf';
			case '2' | 'gf' | 'girlfriend': 'gf';
			default: clean;
		};
	}

	/** Remap a Codename camera character index onto the native Focus Camera
		character order (bf=0, dad=1, gf=2). */
	static function codenameFocusChar(value:String):String {
		return switch (codenameActorToken(value)) {
			case 'dad': '1';
			case 'bf': '0';
			case 'gf': '2';
			default: value;
		};
	}

	/** Set (or add) the native character slot inside one event-options JSON. */
	static function packWithChar(optionsJson:String, char:String):String {
		var payload:Dynamic = {};
		if (optionsJson != null && StringTools.trim(optionsJson) != '') {
			try {
				payload = Json.parse(optionsJson);
			} catch (_:Dynamic) {
				payload = {};
			}
		}
		Reflect.setField(payload, 'char', char);
		return Json.stringify(payload);
	}

	/** Pack Codename params into the native event-options JSON. */
	static function packEventOptions(params:Array<Dynamic>, from:Int, names:Array<String>):String {		var payload:Dynamic = {};
		var packed = false;
		for (offset in 0...names.length) {
			var index = from + offset;
			var value:Dynamic = params != null && index >= 0 && index < params.length ? params[index] : null;
			if (value == null)
				continue;
			Reflect.setField(payload, names[offset], value);
			packed = true;
		}
		// Keep the authored row lossless: the native event pump ignores unknown
		// option fields, so the full params array rides along untouched.
		if (params != null && params.length > 0) {
			Reflect.setField(payload, 'codenameParams', params);
			packed = true;
		}
		return packed ? Json.stringify(payload) : '';
	}

	#if sys
	/**
		Convert one Codename character XML into the native custom-character
		shape.  The donor atlas is copied as char.png/char.xml and the health
		icon (a single donor PNG, not the native four-cell strip) lands as a
		one-cell icons.png; HealthIcon clamps registry slots onto short strips.
	*/
	public static function convertCharacterXml(xmlPath:String, ?sourceRoot:String,
		?nativeName:String, ?healthIconRequired:Bool = true, ?fallbackColor:String,
		?authoredId:String):CodenameCharacterConversion {
		var xmlText = '';
		try {
			xmlText = File.getContent(xmlPath);
		} catch (error:Dynamic) {
			throw 'Unable to read Codename character XML ' + xmlPath + ': ' + Std.string(error);
		}
		return parseCharacterXml(xmlText, sourceRoot, nativeName, healthIconRequired,
			fallbackColor, xmlPath, authoredId);
	}
	#end

	public static function parseCharacterXml(xmlText:String, ?sourceRoot:String, ?nativeName:String,
		?healthIconRequired:Bool = true, ?fallbackColor:String, ?sourcePath:String,
		?authoredId:String):CodenameCharacterConversion {
		var findings:Array<CodenameDiagnostic> = [];
		var root = normalizeSourceRoot(sourceRoot);
		var diagnosticPath = sourcePath == null || StringTools.trim(sourcePath) == '' ? root : sourcePath;
		var document:Xml = null;
		try {
			document = parseDefinitionXml(xmlText, 'character');
		} catch (error:Dynamic) {
			throw 'Unable to parse Codename character XML: ' + Std.string(error);
		}
		var requestedName = nativeName == null || nativeName.trim() == ''
			? xmlAttr(document, 'name', 'codename-character') : nativeName;
		var name = safeStem(requestedName);
		if (name == 'song')
			name = 'codename-character';

		var spriteAttr = xmlAttr(document, 'sprite', '');
		var assetStem = spriteAttr == '' && CodenameScriptDiscovery.safeRelativeName(authoredId)
			? authoredId : (spriteAttr == '' ? name : spriteAttr);
		var assets:Array<Dynamic> = [];
	var atlasPng = '';
	var atlasXmlPath = '';
	var animateAtlas = false;
	var sparrowPageCount = 0;
	var atlasFiles:Array<Dynamic> = [];
	#if sys
	var atlas = CodenameCharacterAtlas.resolve(root, assetStem);
	if (atlas != null) {
		animateAtlas = atlas.mode == 'animate';
		sparrowPageCount = atlas.mode == 'pages' ? atlas.files.length >> 1 : 0;
		atlasFiles = atlas.files;
		if (animateAtlas || sparrowPageCount > 0) {
			for (file in atlasFiles)
				assets.push({source:file.source, destination:'char/' + file.relative,
					kind:'character-atlas', supported:true});
		} else {
			for (file in atlasFiles) {
				if (file.relative == '.png') atlasPng = file.source;
				if (file.relative == '.xml') atlasXmlPath = file.source;
			}
		}
	}
	#end
	if (!animateAtlas && sparrowPageCount == 0 && atlasPng == '') {
			findings.push(makeDiagnostic('warning', 'missing-character-asset',
				'Codename character ' + name + ' has no Sparrow or Animate atlas at images/characters/'
				+ assetStem + ' under the selected source root.', diagnosticPath));
	} else if (!animateAtlas && sparrowPageCount == 0) {
			assets.push({source: atlasPng, destination: 'char.png', kind: 'character-atlas', supported: true});
			if (atlasXmlPath != '')
				assets.push({source: atlasXmlPath, destination: 'char.xml', kind: 'character-atlas', supported: true});
			else
				findings.push(makeDiagnostic('warning', 'missing-character-atlas-xml',
					'Codename character ' + name + ' has no images/characters/' + assetStem
					+ '.xml frame data; the sprite cannot be registered without it.', diagnosticPath));
		}

		var animations:Array<Dynamic> = [];
		var hasIdle = false;
		var hasDancePair = false;
		var hasDanceLeft = false;
		var hasDanceRight = false;
		for (element in xmlElements(document)) {
			if (xmlNodeName(element) != 'anim')
				continue;
			xmlDiagnoseUnknownAttributes(element,
				['name', 'anim', 'fps', 'indices', 'loop', 'offsets', 'x', 'y', 'flipx', 'flipy',
					'scale', 'next', 'alpha', 'forced'], 'anim', name, findings, diagnosticPath);
			var animName = xmlAttr(element, 'name', '');
			var prefix = xmlAttr(element, 'anim', animName);
			if (animName == '' || prefix == '')
				continue;
			var fps = Std.int(numberValue(xmlAttr(element, 'fps', '24'), 24));
			if (fps <= 0)
				fps = 24;
			var loop = xmlAttr(element, 'loop', 'false').toLowerCase() == 'true';
			var indices = parseIndices(xmlAttr(element, 'indices', ''));
			var offsetsValue = xmlAttr(element, 'offsets', '');
			var offsetX = offsetsValue == ''
				? numberValue(xmlAttr(element, 'x', '0'), 0)
				: parsePositionPart(offsetsValue, 0);
			var offsetY = offsetsValue == ''
				? numberValue(xmlAttr(element, 'y', '0'), 0)
				: parsePositionPart(offsetsValue, 1);
			animations.push({
				name: animName,
				prefix: prefix,
				fps: fps,
				loop: loop,
				indices: indices,
				offsetX: offsetX,
				offsetY: offsetY
			});
			if (animName == 'danceLeft')
				hasDanceLeft = true;
			if (animName == 'danceRight')
				hasDanceRight = true;
			if (animName == 'idle')
				hasIdle = true;
		}
		hasDancePair = hasDanceLeft && hasDanceRight;
		if (animations.length == 0)
			findings.push(makeDiagnostic('warning', 'missing-idle-animation',
				'Codename character ' + name + ' has no anim entries; the generated character will be static.', diagnosticPath));

		// Codename icons may be flat PNGs or an icon.png within an icon-id folder.
		// Native ids stay destination-owned; otherwise resolve from the selected
		// mod or its installation's common assets.
		var iconId = xmlAttr(document, 'icon', xmlAttr(document, 'healthicon', ''));
		var iconResolved = false;
		#if sys
		iconResolved = appendCodenameIconBundle(root, iconId, assets) != false;
		#end
		if (!iconResolved && iconId != '' && !isNativeHealthIcon(iconId))
			findings.push(makeDiagnostic('warning', healthIconRequired ? 'missing-health-icon' : 'icon-unresolved',
				'Codename health icon ' + iconId + ' could not be resolved under images/icons/ in the selected mod or its installation base.', diagnosticPath));

		var color = xmlAttr(document, 'color', fallbackColor == null ? '' : fallbackColor);
		var registryEntry:Dynamic = {
			like: name,
			icons: [0, 0, 0, 0],
			colors: [healthbarColorString(color)],
			codenameCharacter: {
				x: numberValue(xmlAttr(document, 'x', '0'), 0),
				y: numberValue(xmlAttr(document, 'y', '0'), 0),
				playerOffsets: xmlAttr(document, 'isPlayer', 'false') == 'true',
				flipX: xmlAttr(document, 'flipX', 'false') == 'true',
				icon: iconId,
				animateAtlas: animateAtlas
			}
		};
		var hscript = generateCharacterHScript(name, animations, hasIdle, hasDancePair,
			xmlAttr(document, 'antialiasing', 'true').toLowerCase() != 'false', animateAtlas, sparrowPageCount);
		return {name: name, registryEntry: registryEntry, hscript: hscript, assets: assets,
			diagnostics: findings, supported: true};
	}

	#if sys
	/** Resolve the supported Codename character atlas forms. Relative paths in
	 * the result are owner-relative, so the exact same resolver drives the
	 * importer preview and the live selected-owner asset namespace. */
	public static function characterAtlasFiles(root:String, sprite:String):Array<Dynamic>
		return CodenameCharacterAtlas.files(root, sprite);

	/** Copy the donor icon PNG beside the native character folder. Flat legacy
	 * files, nested per-icon folders and installation-owned icons are supported. */
	static function appendCodenameIconBundle(root:String, iconId:String, assets:Array<Dynamic>):Bool {
		var id = iconId == null ? '' : iconId.trim();
		if (id == '' || id.toLowerCase() == 'none' || id.toLowerCase() == 'null')
			return true;
		var pngPath = findCodenameIcon(root, id);
		if (pngPath == '') {
			var baseRoot = codenameInstallationAssetRoot(root);
			if (baseRoot != '')
				pngPath = findCodenameIcon(baseRoot, id);
		}
		if (pngPath == '') return isNativeHealthIcon(id);
		assets.push({source: pngPath, destination: 'icons.png', kind: 'health-icon', supported: true});
		return true;
	}

	static function findCodenameIcon(root:String, id:String):String {
		for (candidate in [
			'images/icons/' + id + '/icon.png',
			'images/icons/icon-' + id + '.png',
			'images/icons/' + id + '.png'
		]) {
			var resolved = resolveAsset(root, candidate);
			if (resolved != '') return resolved;
		}
		return findIconByFolderScan(root, id);
	}

	/** For a source Codename mod stored under <installation>/mods/<name>, expose
	 * the installation's common assets as a second dependency root. */
	static function codenameInstallationAssetRoot(root:String):String {
		if (root == null || root == '') return '';
		var mods = Path.directory(root);
		if (mods == null || Path.withoutDirectory(mods).toLowerCase() != 'mods') return '';
		var installation = Path.directory(mods);
		if (installation == null || installation == '') return '';
		var assetsRoot = Path.join([installation, 'assets']);
		return CodenameInstallationAssetOverlay.isInstallationAssetsRoot(assetsRoot)
			&& CodenameScriptDiscovery.withinRoot(installation, assetsRoot) ? assetsRoot : '';
	}

	static function findIconByFolderScan(root:String, id:String):String {
		var iconsFolder = Path.join([root, 'images', 'icons']);
		if (!FileSystem.isDirectory(iconsFolder))
			return '';
		var wanted = id.toLowerCase();
		var matches:Array<String> = [];
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(iconsFolder));
		} catch (_:Dynamic) {
			return '';
		}
		for (entry in entries) {
			var lower = entry.toLowerCase();
			if (!lower.endsWith('.png'))
				continue;
			var stem = lower.substr(0, lower.length - 4);
			if (stem == 'icon-' + wanted || stem == wanted)
				matches.push(Path.join([iconsFolder, entry]));
		}
		return matches.length == 1 ? matches[0] : '';
	}

	/**
		Convert one Codename stage XML into the native custom-stage shape.
		`characterOffsets` carries each converted character's own XML x/y so the
		generated placement retains the current native character representation.
		`cameraLines` identifies the authored primary instances and position slots;
		full donor global-offset flipping still needs the character adapter.
	*/
	public static function convertStageXml(xmlPath:String, ?sourceRoot:String, ?nativeName:String,
		?characterOffsets:Map<String, Array<Float>>, ?cameraLines:Array<Dynamic>,
		?characterPlayerOffsets:Map<String, Bool>):CodenameStageConversion {
		var xmlText = '';
		try {
			xmlText = File.getContent(xmlPath);
		} catch (error:Dynamic) {
			throw 'Unable to read Codename stage XML ' + xmlPath + ': ' + Std.string(error);
		}
		return parseStageXml(xmlText, sourceRoot, nativeName, characterOffsets, xmlPath, cameraLines, characterPlayerOffsets);
	}
	#end

	public static function parseStageXml(xmlText:String, ?sourceRoot:String, ?nativeName:String,
		?characterOffsets:Map<String, Array<Float>>, ?sourcePath:String, ?cameraLines:Array<Dynamic>,
		?characterPlayerOffsets:Map<String, Bool>):CodenameStageConversion {
		var findings:Array<CodenameDiagnostic> = [];
		var root = normalizeSourceRoot(sourceRoot);
		var diagnosticPath = sourcePath == null || StringTools.trim(sourcePath) == '' ? root : sourcePath;
		var document:Xml = null;
		try {
			document = parseDefinitionXml(xmlText, 'stage');
		} catch (error:Dynamic) {
			throw 'Unable to parse Codename stage XML: ' + Std.string(error);
		}
		var requestedName = nativeName == null || nativeName.trim() == ''
			? xmlAttr(document, 'name', 'codename-stage') : nativeName;
		var name = safeStem(requestedName);
		if (name == 'song')
			name = 'codename-stage';
		var folder = xmlAttr(document, 'folder', '');
		while (folder.startsWith('/'))
			folder = folder.substr(1);
		while (folder.endsWith('/'))
			folder = folder.substr(0, folder.length - 1);

		var assets:Array<Dynamic> = [];
		var lines:Array<String> = [];
		var placementModel = CodenameStagePlacement.parse(xmlText);
		lines.push('// Generated by the Codename importer from the donor stage XML ("' + name + '").');
		lines.push('function start(song) {');
		// Publish the selected stage's whole model before any stage objects are
		// installed. HScript receives a JSON string so arbitrary authored slot
		// names need no generated HScript identifier or object-literal syntax.
		lines.push('    stage.setCodenamePlacement('
			+ Json.stringify(Json.stringify(CodenameStagePlacement.toData(placementModel))) + ');');
		var zoom = numberValue(xmlAttr(document, 'zoom', '1'), 1);
		if (zoom <= 0 || Math.isNaN(zoom)) {
			zoom = 1;
			findings.push(makeDiagnostic('warning', 'invalid-stage-zoom',
				'Codename stage zoom was not positive; using 1.', diagnosticPath));
		}
		lines.push('    setDefaultZoom(' + formatNumber(zoom) + ');');

		// Keep donor XML child ordinals so the runtime can insert actors at the
		// exact anchor following each prop/character node.
		var childOrdinal = 0;
		var xmlAnchorKeys:Map<String, Bool> = new Map();
		var propIndex = 0;
		for (element in xmlElements(document)) {
			var ordinal = childOrdinal++;
			var node = xmlNodeName(element);
			var anchorKey:Null<String> = CodenameStagePlacement.slotKey(element);
			if (anchorKey != null) {
				lines.push('    stage.addCodenameAnchor(' + hscriptQuote(anchorKey) + ', ' + ordinal + ');');
				xmlAnchorKeys.set(anchorKey, true);
				continue;
			}
			if (node != 'sprite') {
				findings.push(makeDiagnostic('warning', 'unsupported-stage-element',
					'Codename stage element <' + node + '> has no native equivalent and was omitted.', diagnosticPath));
				continue;
			}
			xmlDiagnoseUnknownAttributes(element,
				['x', 'y', 'name', 'sprite', 'scale', 'scalex', 'scaley', 'alpha', 'scroll',
					'scrollx', 'scrolly', 'antialiasing', 'angle', 'flipx', 'flipy',
					'visible', 'blend', 'front'], 'sprite', name, findings, diagnosticPath);
			var spriteAttr = xmlAttr(element, 'sprite', '');
			// Codename requires both attributes for an image prop. Color-only
			// shorthand was a native approximation, not donor XML behavior.
			if (!element.exists('sprite') || !element.exists('name')) {
				propIndex++;
				continue;
			}
			var identifier = 'codenameProp_' + safeIdentifier(xmlAttr(element, 'name', 'prop' + propIndex)) + '_' + propIndex;
			var x = numberValue(xmlAttr(element, 'x', '0'), 0);
			var y = numberValue(xmlAttr(element, 'y', '0'), 0);
			var propDestination = 'prop-' + propIndex + '.png';
			#if sys
			var propAsset = 'images/' + (folder == '' ? '' : folder + '/') + spriteAttr + '.png';
			var pngPath = resolveAsset(root, propAsset);
			if (pngPath == '') {
				findings.push(makeDiagnostic('warning', 'missing-prop-asset',
					'Codename stage sprite "' + xmlAttr(element, 'name', 'prop' + propIndex)
					+ '" references ' + propAsset + ', which was not found under the selected source root; the prop was omitted.', diagnosticPath));
				propIndex++;
				continue;
			}
			assets.push({source: pngPath, destination: propDestination, kind: 'stage-image', supported: true});
			#end
			lines.push('    var ' + identifier + ' = new FlxSprite(' + formatNumber(x) + ', ' + formatNumber(y)
				+ ').loadGraphic(hscriptPath + ' + hscriptQuote(propDestination) + ');');
			if (xmlAttr(element, 'antialiasing', '').toLowerCase() == 'false')
				lines.push('    ' + identifier + '.antialiasing = false;');
			var scaleX = numberValue(xmlAttr(element, 'scalex', xmlAttr(element, 'scale', '1')), 1);
			var scaleY = numberValue(xmlAttr(element, 'scaley', xmlAttr(element, 'scale', '1')), 1);
			if (scaleX != 1 || scaleY != 1) {
				lines.push('    ' + identifier + '.scale.set(' + formatNumber(scaleX) + ', ' + formatNumber(scaleY) + ');');
				lines.push('    ' + identifier + '.updateHitbox();');
			}
			if (xmlAttr(element, 'alpha', '') != '')
				lines.push('    ' + identifier + '.alpha = ' + formatNumber(numberValue(xmlAttr(element, 'alpha', '1'), 1)) + ';');
			if (xmlAttr(element, 'angle', '') != '')
				lines.push('    ' + identifier + '.angle = ' + formatNumber(numberValue(xmlAttr(element, 'angle', '0'), 0)) + ';');
			if (xmlAttr(element, 'visible', '').toLowerCase() == 'false')
				lines.push('    ' + identifier + '.visible = false;');
			var scrollX = numberValue(xmlAttr(element, 'scrollx', xmlAttr(element, 'scroll', '1')), 1);
			var scrollY = numberValue(xmlAttr(element, 'scrolly', xmlAttr(element, 'scroll', '1')), 1);
			if (scrollX != 1 || scrollY != 1)
				lines.push('    ' + identifier + '.scrollFactor.set(' + formatNumber(scrollX) + ', ' + formatNumber(scrollY) + ');');
			if (xmlAttr(element, 'flipx', '').toLowerCase() == 'true')
				lines.push('    ' + identifier + '.flipX = true;');
			if (xmlAttr(element, 'flipy', '').toLowerCase() == 'true')
				lines.push('    ' + identifier + '.flipY = true;');
			lines.push('    stage.addCodenameProp(' + identifier + ', ' + ordinal + ');');
			var elementName = xmlAttr(element, 'name', 'prop' + propIndex);
			lines.push('    stage.addElement(' + hscriptQuote(elementName) + ', ' + identifier + ');');
			propIndex++;
		}

		for (unsupported in placementModel.unsupported)
			findings.push(makeDiagnostic('warning', 'unsupported-stage-placement',
				'Codename stage placement requires runtime support for ' + unsupported + '.', diagnosticPath));
		// Upstream appends absent built-in anchors after XML children in this
		// order. An authored named slot with the same key also suppresses the
		// default anchor, matching the donor's last-wins characterPoses map.
		for (role in ['girlfriend', 'dad', 'boyfriend']) if (!xmlAnchorKeys.exists(role)) {
			lines.push('    stage.addCodenameAnchor(' + hscriptQuote(role) + ', ' + childOrdinal + ');');
			childOrdinal++;
		}
		// Select authored instances before mapping them to the native primary roles.
		// Named character placeholders take priority over chart position slots.
		var roleLines:Map<String, Dynamic> = new Map();
		var authoredRoleOrder:Array<String> = [];
		if (cameraLines != null) for (line in cameraLines) {
			// Match convertChart's primary actor selection: a receptor-only
			// line cannot supply the placement of a later line's character.
			var ids:Dynamic = Reflect.field(line, 'characters');
			if (!Std.isOfType(ids, Array) || (cast ids:Array<Dynamic>).length == 0) continue;
			var slot = switch (Std.string(Reflect.field(line, 'role'))) {
				case 'player': 'bf';
				case 'opponent': 'dad';
				case 'gf': 'gf';
				default: '';
			};
			if (slot != '' && !roleLines.exists(slot)) {
				roleLines.set(slot, line);
				authoredRoleOrder.push(slot);
			}
		}
		var roleSlotKeys:Map<String, String> = new Map();
		for (slot in ['dad', 'bf', 'gf']) {
			var type = slot == 'bf' ? 1 : (slot == 'gf' ? 2 : 0);
			var actorId:Null<String> = null;
			var position:String = null;
			var line = roleLines.get(slot);
			if (line != null) {
				var ids:Dynamic = Reflect.field(line, 'characters');
				if (Std.isOfType(ids, Array) && (cast ids:Array<Dynamic>).length > 0)
					actorId = Std.string((cast ids:Array<Dynamic>)[0]);
				position = Reflect.field(line, 'position');
			}
			var placement = CodenameStagePlacement.select(placementModel, actorId, type, position, 0);
			roleSlotKeys.set(slot, placement.slotKey);
			if (placement.zoomFactor != 1)
				findings.push(makeDiagnostic('warning', 'unsupported-stage-character-presentation',
					'Codename placement ' + placement.slotKey + ' for ' + slot
					+ ' requires per-character zoomFactor presentation support.', diagnosticPath));
			var actor = slot == 'bf' ? 'boyfriend' : slot;
			var ownOffset:Null<Array<Float>> = characterOffsets == null ? null : characterOffsets.get(slot);
			var playerOffsets = characterPlayerOffsets != null && characterPlayerOffsets.get(slot) == true;
			var globalSign = placement.isPlayer == playerOffsets ? 1 : -1;
			var finalX = placement.x + (ownOffset == null ? 0 : globalSign * ownOffset[0]);
			var finalY = placement.y + (ownOffset == null ? 0 : ownOffset[1]);
			// Donor playAnim subtracts global X from the sprite when constructor
			// isPlayer and XML playerOffsets differ; Y always adds. This native
			// representation bakes that visual translation into world placement.
			lines.push('    stage.setOffsets(' + hscriptQuote(slot) + ', ' + formatNumber(finalX) + ', ' + formatNumber(finalY) + ', false);');
			lines.push('    ' + actor + '.x = ' + formatNumber(finalX) + ';');
			lines.push('    ' + actor + '.y = ' + formatNumber(finalY) + ';');
			lines.push('    stage.setScrollFactor(' + hscriptQuote(slot) + ', ' + formatNumber(placement.scrollX) + ', ' + formatNumber(placement.scrollY) + ');');
			lines.push('    ' + actor + '.scrollFactor.set(' + formatNumber(placement.scrollX) + ', ' + formatNumber(placement.scrollY) + ');');
		}
		// Reorder the existing native primary actors by their first authored
		// strumline occurrence. Roles with no matching primary line retain the
		// explicit GF/dad/BF fallback order; extra occurrences need distinct
		// Character instances and remain outside this converter.
		var placedRoles:Map<String, Bool> = new Map();
		for (slot in authoredRoleOrder) {
			var actor = slot == 'bf' ? 'boyfriend' : slot;
			lines.push('    stage.placeCodenameActor(' + actor + ', ' + hscriptQuote(roleSlotKeys.get(slot)) + ');');
			placedRoles.set(slot, true);
		}
		for (slot in ['gf', 'dad', 'bf']) if (!placedRoles.exists(slot)) {
			var actor = slot == 'bf' ? 'boyfriend' : slot;
			lines.push('    stage.placeCodenameActor(' + actor + ', ' + hscriptQuote(roleSlotKeys.get(slot)) + ');');
		}
		lines.push('}');
		lines.push('');
		lines.push('function beatHit(beat) {}');
		lines.push('function update(elapsed) {}');
		lines.push('function stepHit(step) {}');
		lines.push('function playerTwoTurn() {}');
		lines.push('function playerTwoMiss() {}');
		lines.push('function playerTwoSing() {}');
		lines.push('function playerOneTurn() {}');
		lines.push('function playerOneMiss() {}');
		lines.push('function playerOneSing() {}');
		return {name: name, registryValue: name, hscript: lines.join('\n') + '\n', assets: assets, diagnostics: findings};
	}

	static function generateCharacterHScript(name:String, animations:Array<Dynamic>, hasIdle:Bool,
		dancesLikeGf:Bool, antialiasing:Bool, animateAtlas:Bool = false,
		sparrowPageCount:Int = 0):String {
		var initialAnimation = hasIdle || animations.length == 0 ? 'idle'
			: (dancesLikeGf ? 'danceLeft' : animations[0].name);
		var lines:Array<String> = [
			'// Generated by the Codename importer from the donor character XML ("' + name + '").',
			'function init(char) {'
		];
		if (animateAtlas)
			lines.push("    char.loadTextureAtlas(hscriptPath + 'char');");
		else if (sparrowPageCount > 0) {
			lines.push("    char.frames = FlxAtlasFrames.fromSparrow(hscriptPath + 'char/1.png', hscriptPath + 'char/1.xml');");
			for (page in 2...sparrowPageCount + 1)
				lines.push('    char.frames.addAtlas(FlxAtlasFrames.fromSparrow(hscriptPath + '
					+ hscriptQuote('char/' + page + '.png') + ', hscriptPath + '
					+ hscriptQuote('char/' + page + '.xml') + '));');
		} else
			lines.push("    char.frames = FlxAtlasFrames.fromSparrow(hscriptPath + 'char.png', hscriptPath + 'char.xml');");
		for (animation in animations) {
			if (animateAtlas) {
				var rendered:Array<String> = [];
				if (animation.indices != null)
					for (index in (cast animation.indices:Array<Dynamic>))
						rendered.push(Std.string(index));
				if (rendered.length > 0)
					lines.push('    char.animation.addBySymbolIndices(' + hscriptQuote(animation.name) + ', '
						+ hscriptQuote(animation.prefix) + ', [' + rendered.join(',') + '], '
						+ animation.fps + ', ' + animation.loop + ');');
				else
					lines.push('    char.animation.addBySymbol(' + hscriptQuote(animation.name) + ', '
						+ hscriptQuote(animation.prefix) + ', ' + animation.fps + ', ' + animation.loop + ');');
			} else if (animation.indices != null && animation.indices.length > 0) {
				var rendered:Array<String> = [];
				for (index in (cast animation.indices:Array<Dynamic>))
					rendered.push(Std.string(index));
				lines.push('    char.animation.addByIndices(' + hscriptQuote(animation.name) + ', '
					+ hscriptQuote(animation.prefix) + ', [' + rendered.join(',') + "], '', "
					+ animation.fps + ', ' + animation.loop + ');');
			} else {
				lines.push('    char.animation.addByPrefix(' + hscriptQuote(animation.name) + ', '
					+ hscriptQuote(animation.prefix) + ', ' + animation.fps + ', ' + animation.loop + ');');
			}
			if (animation.offsetX != 0 || animation.offsetY != 0)
				lines.push('    char.addOffset(' + hscriptQuote(animation.name) + ', '
					+ formatNumber(animation.offsetX) + ', ' + formatNumber(animation.offsetY) + ');');
		}
		lines.push('    char.antialiasing = ' + (antialiasing ? 'true' : 'false') + ';');
		lines.push('    char.noFlip = ' + (dancesLikeGf ? 'true' : 'false') + ';');
		lines.push('    char.playAnim(' + hscriptQuote(initialAnimation) + ');');
		lines.push('}');
		lines.push('portraitOffset = [0, 0];');
		lines.push('dadVar = 4.0;');
		lines.push('isPixel = false;');
		lines.push('function sing(direction, miss, alt, char) {}');
		lines.push('function update(elapsed, char) {}');
		lines.push('var danced = false;');
		lines.push('function dance(char) {');
		lines.push(dancesLikeGf
			? "    danced = !danced;\n\n    if (danced)\n        char.playAnim('danceRight');\n    else\n        char.playAnim('danceLeft');"
			: '    char.playAnim(' + hscriptQuote(initialAnimation) + ');');
		lines.push('}');
		return lines.join('\n') + '\n';
	}

	static function isNativeHealthIcon(value:String):Bool {
		if (value == null)
			return false;
		return switch (StringTools.trim(value).toLowerCase()) {
			case 'gf' | 'bf' | 'dad' | 'none' | 'null' | '': true;
			default: false;
		};
	}

	#if sys
	/** Resolve one asset under a selected Codename content root. Exact spelling
	 * wins; each case-insensitive fallback must be unique and remain in root. */
	public static function resolveAsset(root:String, relative:String):String {
		if (root == null || root == '' || relative == null || relative == '')
			return '';
		var clean = StringTools.replace(relative.trim(), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		var resolved = CodenameScriptDiscovery.resolveScopedRelative(root, clean);
		return resolved == null ? '' : Path.join([root, resolved]);
	}
	#end

	/** Minimal bounded XML reader for Codename definitions.  Kept local so the
		pure converter stays engine-agnostic and fixtures can pin its behavior. */
	static function parseDefinitionXml(xmlText:String, kind:String):Xml {
		var document = Xml.parse(xmlText);
		var element = document.firstElement();
		if (element == null)
			throw 'Codename ' + kind + ' XML has no root element';
		var rootName = element.nodeName.toLowerCase();
		if (rootName != 'character' && rootName != 'stage')
			throw 'Codename ' + kind + ' XML root element is <' + element.nodeName + '>';
		return element;
	}

	static function xmlNodeName(element:Xml):String {
		return element.nodeName.toLowerCase();
	}

	static function xmlAttr(element:Xml, name:String, fallback:String):String {
		var value:String = element.get(name);
		if (value == null) {
			// Codename attribute spellings are case-insensitive in practice.
			for (actual in element.attributes()) {
				if (actual.toLowerCase() == name.toLowerCase()) {
					value = element.get(actual);
					break;
				}
			}
		}
		return value == null ? fallback : value;
	}

	static function xmlElements(element:Xml):Array<Xml> {
		var result:Array<Xml> = [];
		for (child in element.elements())
			result.push(child);
		return result;
	}

	static function xmlDiagnoseUnknownAttributes(element:Xml, known:Array<String>, node:String,
		owner:String, findings:Array<CodenameDiagnostic>, diagnosticPath:String):Void {
		for (actual in element.attributes()) {
			var matched = false;
			for (name in known)
				if (name.toLowerCase() == actual.toLowerCase()) {
					matched = true;
					break;
				}
			if (!matched)
				findings.push(makeDiagnostic('warning', 'unsupported-attribute',
					'Codename ' + node + ' attribute "' + actual + '" on "' + owner
					+ '" is not represented by the native stage/character API.', diagnosticPath));
		}
	}

	static function parseIndices(value:String):Null<Array<Int>> {
		var clean = value == null ? '' : StringTools.trim(value);
		if (clean == '')
			return null;
		var result:Array<Int> = [];
		for (part in clean.split(',')) {
			var parsed = Std.parseFloat(StringTools.trim(part));
			if (!Math.isNaN(parsed))
				result.push(Std.int(parsed));
		}
		return result.length == 0 ? null : result;
	}

	static function parsePositionPart(value:String, index:Int):Float {
		var parts = value == null ? [] : value.split(',');
		if (parts.length <= index)
			return 0;
		var parsed = Std.parseFloat(StringTools.trim(parts[index]));
		return Math.isNaN(parsed) ? 0 : parsed;
	}

	static function buildSections(noteRows:Array<Dynamic>, maxTime:Float, bpm:Float,
		sectionSteps:Int):Array<Dynamic> {
		var sections:Array<Dynamic> = [];
		if (sectionSteps <= 0)
			sectionSteps = DEFAULT_SECTION_STEPS;
		var cursor:Float = 0;
		var guard:Int = 0;
		if (bpm <= 0)
			bpm = DEFAULT_BPM;
		var stepMs = 60000.0 / bpm / 4.0;
		// Include notes exactly on a section boundary. The previous interval is
		// half-open, so a final note at maxTime needs one final section.
		while ((cursor <= maxTime + EPSILON || sections.length == 0) && guard++ < 100000) {
			var next = cursor + stepMs * sectionSteps;
			var sectionNotes:Array<Dynamic> = [];
			for (entry in noteRows) {
				var time:Float = entry.time;
				if (time >= cursor - EPSILON && time < next - EPSILON)
					sectionNotes.push(entry.row);
			}
			// Keep mixed rows dynamic: hxcpp otherwise infers Array<Int> from
			// this comparison and coerces timestamps, nulls and metadata in place.
			sectionNotes.sort(function(a:Array<Dynamic>, b:Array<Dynamic>)
				return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
			sections.push({
				sectionNotes: sectionNotes,
				lengthInSteps: sectionSteps,
				mustHitSection: true,
				bpm: bpm,
				changeBPM: false,
				altAnim: false,
				altAnimNum: 0
			});
			cursor = next;
			if (cursor <= 0)
				break;
		}
		return sections;
	}

	static function appendEvent(events:Array<Dynamic>, time:Float, event:Array<Dynamic>):Void {
		for (group in events) {
			if (group[0] == time) {
				group[1].push(event);
				return;
			}
		}
		events.push([time, [event]]);
	}

	static function deduplicateDiagnostics(findings:Array<CodenameDiagnostic>):Array<CodenameDiagnostic> {
		if (findings == null || findings.length < 2)
			return findings == null ? [] : findings;
		var result:Array<CodenameDiagnostic> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (finding in findings) {
			if (finding == null)
				continue;
			var key = (finding.severity == null ? '' : finding.severity) + '|'
				+ (finding.code == null ? '' : finding.code) + '|'
				+ (finding.message == null ? '' : finding.message) + '|'
				+ (finding.path == null ? '' : finding.path) + '|'
				+ (finding.difficulty == null ? '' : finding.difficulty);
			if (seen.exists(key))
				continue;
			seen.set(key, true);
			result.push(finding);
		}
		return result;
	}

	static function healthbarColorString(value:String):String {
		var clean = value == null ? '' : StringTools.trim(value);
		if (clean == '')
			return '#FFFFFFFF';
		if (clean.charCodeAt(0) == '#'.code)
			clean = clean.substr(1);
		// Native registry colors carry a full ARGB literal; expand authored RGB.
		if (clean.length == 6)
			clean = 'FF' + clean;
		return '#' + clean.toUpperCase();
	}

	static function makeDiagnostic(severity:String, code:String, message:String,
		path:String, ?difficulty:String):CodenameDiagnostic {
		var diagnostic:CodenameDiagnostic = {severity: severity, code: code, message: message};
		if (path != null && path != '')
			diagnostic.path = path;
		if (difficulty != null && difficulty != '')
			diagnostic.difficulty = difficulty;
		return diagnostic;
	}

	static function normalizeSourceRoot(value:String):String {
		var clean = value == null ? '' : StringTools.replace(StringTools.trim(value), '\\', '/');
		while (clean.endsWith('/'))
			clean = clean.substr(0, clean.length - 1);
		return clean;
	}

	static function safeStem(value:String):String {
		var clean = value == null ? '' : StringTools.trim(value);
		clean = StringTools.replace(clean, '\\', '/');
		if (clean.indexOf('/') >= 0)
			clean = clean.substr(clean.lastIndexOf('/') + 1);
		clean = Path.withoutExtension(clean);
		var output:Array<String> = [];
		for (i in 0...clean.length) {
			var c = clean.charAt(i);
			if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
				|| c == '-' || c == '_' || c == ' ' || c == '.')
				output.push(c == ' ' ? '-' : c);
		}
		var result = output.join('');
		return StringTools.trim(result) == '' ? 'codename-content' : result;
	}

	static function safeIdentifier(value:String):String {
		var clean = value == null ? '' : StringTools.trim(value);
		var output:Array<String> = [];
		for (i in 0...clean.length) {
			var c = clean.charAt(i);
			var isStart = i == 0;
			var valid = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
				|| c == '_' || (!isStart && c >= '0' && c <= '9');
			output.push(valid ? c : '_');
		}
		var result = output.join('');
		if (result == '' || ~/^[0-9]/.match(result))
			result = '_' + result;
		return result;
	}

	static function hscriptQuote(value:String):String {
		return '"' + StringTools.replace(value == null ? '' : value, '"', '\\"') + '"';
	}

	static function formatNumber(value:Float):String {
		if (value == Math.floor(value) && Math.abs(value) < 1000000000)
			return Std.string(Std.int(value));
		return Std.string(value);
	}

	static function field(value:Dynamic, name:String):Dynamic {
		if (value == null)
			return null;
		return Reflect.field(value, name);
	}

	static function stringValue(value:Dynamic, fallback:String):String {
		if (value == null)
			return fallback;
		return Std.string(value);
	}

	static function numberValue(value:Dynamic, fallback:Float):Float {
		if (value == null || Std.isOfType(value, Bool))
			return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? fallback : parsed;
	}
}
