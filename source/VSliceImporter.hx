package;

import haxe.Json;
import haxe.io.Path;
import VSliceAstcAdapter.VSliceAstcHeader;

#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** A non-fatal finding produced while translating V-Slice content. */
typedef VSliceDiagnostic = {
	var severity:String;
	var code:String;
	var message:String;
	@:optional var path:String;
	@:optional var difficulty:String;
}

/** One native chart produced from a V-Slice difficulty. */
typedef VSliceConvertedChart = {
	var difficulty:String;
	var fileName:String;
	var chart:Dynamic;
	var diagnostics:Array<VSliceDiagnostic>;
}

/** The native note row marker and optional custom-note definition selected for
	 * one authored V-Slice kind. `customIndex` is -1 for normal/alt notes. */
typedef VSliceNoteKind = {
	var alt:Int;
	var customIndex:Int;
}

/** Matching HXC note script discovered beside a V-Slice import. */
private typedef VSliceHxcNoteAdapter = {
	var path:String;
	var result:HxcCompat.HxcCompatResult;
	var generic:Bool;
	var donorState:Bool;
	@:optional var noteStyleId:String;
}

/** One custom NoteKind style whose atlas must be materialized with the song. */
typedef VSliceNoteKindStyleConversion = {
	var reference:String;
	var source:String;
	var conversion:VSliceNoteStyleConversion;
}

/** Result of converting one V-Slice song's metadata and chart file. */
typedef VSliceConversionResult = {
	var songName:String;
	var sourcePath:String;
	var charts:Array<VSliceConvertedChart>;
	/** Every character id referenced by a converted Change Character event. */
	@:optional var eventCharacterReferences:Array<String>;
	/** Character ids and native slots referenced by Change Character events. */
	@:optional var eventCharacterSlots:Array<Dynamic>;
	/** Native `noteInfo.json` entries for authored kinds with no built-in
	 * equivalent. Matching HXC note adapters are recorded on the entry; kinds
	 * without one retain identity-only behavior. These are shared by every
	 * converted difficulty. */
	var noteDefinitions:Array<Dynamic>;
	/** Per-kind V-Slice NoteStyle conversions referenced by scripted NoteKinds. */
	@:optional var noteStyleConversions:Array<VSliceNoteKindStyleConversion>;
	var diagnostics:Array<VSliceDiagnostic>;
}

/** Diagnostics for files which the native asset layer cannot consume directly. */
typedef VSliceAssetDiagnostics = {
	var diagnostics:Array<VSliceDiagnostic>;
	var extraVocalStems:Array<String>;
	var astcOnly:Array<String>;
}

/** A source-to-destination mapping for an imported V-Slice asset. */
typedef VSliceAssetMapping = {
	var source:String;
	var destination:String;
	var kind:String;
	var supported:Bool;
	/** True when `source` is compressed ASTC and must be decoded before the
	 * destination PNG is materialized. */
	@:optional var requiresConversion:Bool;
}

/** Pure conversion output for one V-Slice character definition. */
typedef VSliceCharacterConversion = {
	var name:String;
	var registryEntry:Dynamic;
	var hscript:String;
	var assets:Array<VSliceAssetMapping>;
	var diagnostics:Array<VSliceDiagnostic>;
	/** False when a required atlas/animation is unavailable. Kept optional so
	 * existing engine-neutral Codename conversion records remain structurally
	 * compatible with the shared visual materializer. */
	@:optional var supported:Bool;
}

/** Pure conversion output for one V-Slice stage definition. */
typedef VSliceStageConversion = {
	var name:String;
	var registryValue:String;
	var hscript:String;
	var assets:Array<VSliceAssetMapping>;
	var diagnostics:Array<VSliceDiagnostic>;
}

/** Pure conversion output for one V-Slice data/notestyles definition. */
typedef VSliceNoteStyleConversion = {
	/** Destination UI registry key.  It is namespaced to avoid donor ids
		colliding with existing Modding Plus packs. */
	var name:String;
	var authoredName:String;
	var registryEntry:Dynamic;
	/** Native NoteKeys-compatible definitions generated from the V-Slice
		per-lane prefix maps. */
	var preset:Dynamic;
	var assets:Array<VSliceAssetMapping>;
	var diagnostics:Array<VSliceDiagnostic>;
	var supported:Bool;
}

/**
	V-Slice (version 2) chart/metadata conversion.

	This class intentionally has no dependency on the in-game importer.  It is a
	pure data converter so the importer UI can discover/plan work without loading
	Flixel objects or writing to the destination asset tree.  Each V-Slice
	difficulty becomes a separate native chart in the form expected by Song.hx:

		{ "song": { "song": ..., "notes": [...], ... } }

	V-Slice times and sustain lengths are milliseconds.  They are copied to the
	native note rows without converting through a frame rate or truncating them.
	The V-Slice lane numbering is retained (0-3 player, 4-7 opponent), matching
	the native chart lane convention when `mustHitSection` is true.
*/
class VSliceImporter {
	public static inline var ENGINE_NAME:String = 'V-Slice';
	public static inline var DEFAULT_DIFFICULTY:String = 'normal';

	static inline var EPSILON:Float = 0.0001;
	static inline var DEFAULT_BPM:Float = 100;
	static inline var DEFAULT_SECTION_STEPS:Int = 16;

	/** Returns true for V-Slice version-2 metadata documents. */
	public static function isVSliceMetadata(data:Dynamic):Bool {
		if (data == null)
			return false;
		var version = stringValue(field(data, 'version'), '');
		var playData = field(data, 'playData');
		// timeChanges is present in current V-Slice exports, but it is optional
		// in a few hand-authored/older v2 metadata files.  `playData` plus the
		// explicit v2 version is the stable format marker; conversion supplies a
		// sensible BPM fallback when the tempo array is absent.
		return version.startsWith('2') && playData != null;
	}

	/** Returns true for V-Slice version-2 chart documents. */
	public static function isVSliceChart(data:Dynamic):Bool {
		if (data == null || field(data, 'notes') == null)
			return false;
		var version = stringValue(field(data, 'version'), '2');
		return version == '' || version.startsWith('2');
	}

	/** Parse and convert JSON strings without touching the filesystem. */
	public static function convertJson(metadataJson:String, chartJson:String, ?sourcePath:String):VSliceConversionResult {
		if (metadataJson == null || chartJson == null)
			throw 'V-Slice metadata and chart JSON are both required';
		var metadata:Dynamic;
		var chart:Dynamic;
		try {
			metadata = Json.parse(metadataJson);
		} catch (e:Dynamic) {
			throw 'Unable to parse V-Slice metadata: ' + Std.string(e);
		}
		try {
			chart = Json.parse(chartJson);
		} catch (e:Dynamic) {
			throw 'Unable to parse V-Slice chart: ' + Std.string(e);
		}
		return convert(metadata, chart, sourcePath);
	}

	/**
		Read a pair of V-Slice files and convert them.  This is kept separate from
		`convertJson` so callers that already have a scan plan can remain read-only.
	*/
	#if sys
	public static function convertFiles(metadataPath:String, chartPath:String, ?sourcePath:String):VSliceConversionResult {
		var metadata = File.getContent(metadataPath);
		var chart = File.getContent(chartPath);
		var origin = sourcePath == null || sourcePath.trim() == '' ? metadataPath : sourcePath;
		return convertJson(metadata, chart, origin);
	}
	#end

	/**
		Return safe character definition ids found in the selected owner's
		definition folders. V-Slice scripts can choose a character at runtime
		(from menus or costume selectors), so chart/event references alone are
		not a complete import dependency list. This scans only the small JSON
		definition directories supplied by the owner resolver; it never walks
		image or audio trees.
	*/
	public static function characterDefinitionNames(folders:Array<String>):Array<String> {
		var result:Array<String> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		#if sys
		if (folders == null)
			return result;
		for (folder in folders) {
			if (folder == null)
				continue;
			try {
				if (!FileSystem.exists(folder) || !FileSystem.isDirectory(folder))
					continue;
			} catch (_:Dynamic) {
				continue;
			}
			var entries:Array<String>;
			try {
				entries = FileSystem.readDirectory(folder);
			} catch (_:Dynamic) {
				continue;
			}
			entries.sort(function(a, b) {
				var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return lower == 0 ? Reflect.compare(a, b) : lower;
			});
			for (entry in entries) {
				if (entry == null || !entry.toLowerCase().endsWith('.json'))
					continue;
				var name = entry.substr(0, entry.length - '.json'.length);
				if (!isSafeCharacterDefinitionName(name))
					continue;
				var path = Path.join([folder, entry]);
				if (!FileSystem.exists(path) || FileSystem.isDirectory(path)
					|| !CodenameScriptDiscovery.withinRoot(folder, path))
					continue;
				var key = name.toLowerCase();
				if (seen.exists(key))
					continue;
				seen.set(key, true);
				result.push(name);
			}
		}
		#end
		return result;
	}

	static function isSafeCharacterDefinitionName(value:String):Bool {
		if (value == null || value == '' || value == '.' || value == '..')
			return false;
		return new EReg('^[A-Za-z0-9_-]+$', '').match(value);
	}

	/** Existing global character ids belong to their first registered owner. */
	public static function characterOwnerCollides(existingEntry:Dynamic, incomingOwner:String):Bool {
		if (existingEntry == null)
			return false;
		var registeredOwner = stringValue(field(existingEntry, 'vSliceSourceOwner'), '');
		var incoming = incomingOwner == null ? '' : StringTools.trim(incomingOwner);
		return registeredOwner == '' || incoming == '' || registeredOwner != incoming;
	}

	/**
		Convert all difficulties present in the metadata/chart pair.  No files are
		written; `fileName` is the suggested native chart name for the caller's
		copy phase.
	*/
	public static function convert(metadata:Dynamic, chart:Dynamic, ?sourcePath:String):VSliceConversionResult {
		var diagnostics:Array<VSliceDiagnostic> = [];
		var origin = sourcePath == null ? '' : sourcePath;
		if (!isVSliceMetadata(metadata))
			diagnostics.push(makeDiagnostic('warning', 'metadata-version',
				'Metadata is not recognised as a V-Slice version 2 document.', origin));
		if (!isVSliceChart(chart))
			diagnostics.push(makeDiagnostic('warning', 'chart-version',
				'Chart is not recognised as a V-Slice version 2 document.', origin));

		var songName = stringValue(field(metadata, 'songName'), '');
		if (songName == '')
			songName = stringValue(field(metadata, 'song'), '');
		if (songName == '')
			songName = stringValue(field(chart, 'songName'), '');
		if (songName == '') {
			songName = 'v-slice-song';
			diagnostics.push(makeDiagnostic('warning', 'missing-song-name',
				'Metadata has no songName; using v-slice-song.', origin));
		}

		var names = difficultyNames(metadata, chart);
		if (names.length == 0) {
			names.push(DEFAULT_DIFFICULTY);
			diagnostics.push(makeDiagnostic('warning', 'missing-difficulties',
				'No V-Slice difficulties were listed; an empty normal chart was emitted.', origin));
		}

		var charts:Array<VSliceConvertedChart> = [];
		// Keep one deterministic definition/index table for all difficulties. A
		// V-Slice chart may author the same kind in normal and hard; separate
		// per-difficulty indexes would make the native row marker point at the
		// wrong definition when a difficulty is selected at runtime.
		var noteDefinitions:Array<Dynamic> = [];
		var noteKindIndexes:Map<String, Int> = new Map<String, Int>();
		var noteStyleConversions:Array<VSliceNoteKindStyleConversion> = [];
		for (difficulty in names) {
			var converted = convertDifficulty(metadata, chart, songName, difficulty, origin,
				noteDefinitions, noteKindIndexes, noteStyleConversions);
			charts.push(converted);
			for (finding in converted.diagnostics)
				diagnostics.push(finding);
		}
		diagnostics = deduplicateDiagnostics(diagnostics);

		return {
			songName: songName,
			sourcePath: origin,
			charts: charts,
			eventCharacterReferences: eventCharacterReferences(charts),
			eventCharacterSlots: eventCharacterSlots(charts),
			noteDefinitions: noteDefinitions,
			noteStyleConversions: noteStyleConversions,
			diagnostics: diagnostics
		};
	}

	/**
		Collect character ids used by converted V-Slice character-change events.
		These definitions are not necessarily the song's initial opponent/player,
		but they still need a native registry entry before a runtime event can
		switch to them.
	*/
	public static function eventCharacterReferences(charts:Array<VSliceConvertedChart>):Array<String> {
		var result:Array<String> = [];
		if (charts == null)
			return result;
		for (converted in charts) {
			if (converted == null || converted.chart == null)
				continue;
			var song:Dynamic = field(converted.chart, 'song');
			var events:Dynamic = field(song, 'events');
			appendEventCharacterReferences(events, result);
		}
		return result;
	}

	/**
		Collect the slot for every converted Change Character event.  V-Slice
		allows a character definition to be introduced by an event rather than
		by the song metadata (Markov's `gf-markov` is one example).  Keeping the
		slot beside the reference lets the import planner distinguish a
		girlfriend-only actor from a player/opponent actor when deciding whether
		a health icon is a required dependency.
	*/
	public static function eventCharacterSlots(charts:Array<VSliceConvertedChart>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		if (charts == null)
			return result;
		for (converted in charts) {
			if (converted == null || converted.chart == null)
				continue;
			var song:Dynamic = field(converted.chart, 'song');
			var events:Dynamic = field(song, 'events');
			if (!Std.isOfType(events, Array))
				continue;
			for (group in (cast events:Array<Dynamic>)) {
				var rows:Dynamic = group == null ? null : group[1];
				if (!Std.isOfType(rows, Array))
					continue;
				for (row in (cast rows:Array<Dynamic>)) {
					if (!Std.isOfType(row, Array) || row.length < 3)
						continue;
					var pair = changeCharacterRowReference(cast row);
					if (pair == null)
						continue;
					if (pair.reference != '') {
						var key = pair.reference.toLowerCase() + '|' + pair.slot.toLowerCase();
						if (!seen.exists(key)) {
							seen.set(key, true);
							result.push({reference: pair.reference, slot: pair.slot});
						}
					}
				}
			}
		}
		return result;
	}


	/** Slot/new-character pair from a converted ChangeCharacter row.  V-Slice
	 * rows keep the authored kind with their JSON payload in v1 (routed here
	 * through the same single mapping the runtime uses); rows from other
	 * importers keep the native name with slot/character in v1/v2. */
	static function changeCharacterRowReference(row:Array<Dynamic>):{slot:String, reference:String} {
		var eventName = stringValue(row[0], '');
		var slot = stringValue(row[1], '');
		var reference = stringValue(row[2], '');
		var values:Dynamic = null;
		if (slot.indexOf('{') == 0) {
			try values = Json.parse(slot) catch (_:Dynamic) values = null;
		}
		var route = EngineCompat.routeVSliceEvent(eventName, values);
		if (route != null && route.name == 'Change Character') {
			var routeSlot = stringValue(route.v1, '');
			var routeReference = stringValue(route.v2, '');
			if (routeReference != '')
				return {slot: routeSlot, reference: routeReference};
		}
		if (EngineCompat.eventName(eventName) != 'Change Character')
			return null;
		return {slot: slot, reference: reference};
	}

	/** Stage ids referenced only by Change Stage events; the chart itself may
	 * never start on these, but mid-song swaps need them registered. */
	public static function foreignStageReferences(chart:Dynamic):Array<String> {
		var result:Array<String> = [];
		var source = field(chart, 'events');
		if (!Std.isOfType(source, Array))
			return result;
		for (event in (cast source:Array<Dynamic>)) {
			var kind = stringValue(field(event, 'e'), '').toLowerCase();
			if (kind.indexOf('changestage') < 0)
				continue;
			var values = field(event, 'v');
			var id = stringValue(field(values, 'stageid'), stringValue(field(values, 'stage'), ''));
			if (id != '' && result.indexOf(id) < 0)
				result.push(id);
		}
		return result;
	}

	/** Video names referenced by Play Video events. */
	public static function foreignVideoReferences(chart:Dynamic):Array<String> {
		var result:Array<String> = [];
		var source = field(chart, 'events');
		if (!Std.isOfType(source, Array))
			return result;
		for (event in (cast source:Array<Dynamic>)) {
			var kind = stringValue(field(event, 'e'), '').toLowerCase();
			if (kind.indexOf('playvideo') < 0)
				continue;
			var values = field(event, 'v');
			var name = stringValue(field(values, 'path'),
				stringValue(field(values, 'video'), stringValue(field(values, 'file'), '')));
			if (name != '' && result.indexOf(name) < 0)
				result.push(name);
		}
		return result;
	}

	static function appendEventCharacterReferences(events:Dynamic, result:Array<String>):Void {
		if (!Std.isOfType(events, Array) || result == null)
			return;
		for (group in (cast events:Array<Dynamic>)) {
			var rows:Dynamic = group == null ? null : group[1];
			if (!Std.isOfType(rows, Array))
				continue;
			for (row in (cast rows:Array<Dynamic>)) {
				if (!Std.isOfType(row, Array) || row.length < 3)
					continue;
				var pair = changeCharacterRowReference(cast row);
				if (pair == null)
					continue;
				if (pair.reference != '' && result.indexOf(pair.reference) < 0)
					result.push(pair.reference);
			}
		}
	}

	/**
		Collect character companions from the authored V-Slice event objects too.

		`convertEvents` intentionally routes only the events that have a native
		name.  Several donor packs use names such as `ChangeCharacterCL`, though,
		and the native event route is allowed to preserve those as foreign events.
		The `newchar` payload is still authoritative for dependency discovery, so
		we must not make HXC note-kind lookup depend on an event alias being
		recognized first.
	*/
	static function appendRawEventCharacterReferences(chart:Dynamic, result:Array<String>):Void {
		if (chart == null || result == null)
			return;
		var events = field(chart, 'events');
		if (!Std.isOfType(events, Array))
			return;
		for (event in (cast events:Array<Dynamic>)) {
			var eventName = stringValue(field(event, 'e'), '').toLowerCase();
			var normalized = StringTools.replace(StringTools.replace(StringTools.replace(eventName,
				' ', ''), '_', ''), '-', '');
			if (normalized.indexOf('changecharacter') < 0 && normalized.indexOf('charchange') < 0)
				continue;
			var values = field(event, 'v');
			var reference = stringValue(field(values, 'newchar'), '');
			if (reference == '')
				reference = stringValue(field(values, 'newCharacter'), '');
			if (reference == '')
				reference = stringValue(field(values, 'newChar'), '');
			if (reference != '' && result.indexOf(reference) < 0)
				result.push(reference);
		}
	}

	/**
		Convert a V-Slice character JSON document into the native character
		registry shape plus a self-contained HScript implementation.  The method
		only returns text and source/destination mappings; it never copies an
		asset or edits custom_chars.jsonc.
	*/
	public static function convertCharacter(data:Dynamic, ?sourceRoot:String, ?nativeName:String,
		?healthIconRequired:Bool = true, ?sourcePath:String):VSliceCharacterConversion {
		var findings:Array<VSliceDiagnostic> = [];
		var root = normalizeSourceRoot(sourceRoot);
		// Discovery knows the definition file which supplied `data`, while the
		// pure converter is also used by fixtures which only provide a source
		// root. Prefer the exact definition path when it is available so an asset
		// gap can be traced back to the authored JSON rather than only its root.
		var diagnosticPath = sourcePath == null || StringTools.trim(sourcePath) == '' ? root : sourcePath;
		var requestedName = nativeName == null || nativeName.trim() == '' ? stringValue(field(data, 'name'), 'v-slice-character') : nativeName;
		var name = safeStem(requestedName);
		if (name == 'song')
			name = 'v-slice-character';
		var assetPath = stringValue(field(data, 'assetPath'), '');
		var renderType = stringValue(field(data, 'renderType'), 'sparrow').toLowerCase();
		var isMultiSparrow = renderType == 'multisparrow';
		var isPacker = isSpriteSheetPackerType(renderType);
		if (renderType != 'sparrow' && !isMultiSparrow && !isPacker) {
			findings.push(makeDiagnostic('warning', 'unsupported-character-render-type',
				'V-Slice character ' + name + ' uses unsupported renderType ' + renderType
				+ '; the converter will use the single-atlas Sparrow path.', root));
		}
		for (fieldName in safeFields(data)) {
			if (!containsString(['version', 'name', 'assetPath', 'singTime', 'isPixel', 'cameraOffsets', 'offsets',
				'scale', 'healthIcon', 'animations', 'flipX', 'startingAnimation', 'danceEvery',
				'no_antialiasing', 'healthbar_colors', 'renderType', 'death', 'camera_position', 'position',
				'costumes', 'costumelist', 'doesLoop',
				'Made_With'], fieldName))
				findings.push(makeDiagnostic('warning', 'unsupported-character-field',
					'V-Slice character field ' + fieldName + ' is not represented by the native character API.', root));
		}
		var assets:Array<VSliceAssetMapping> = [];
		var mainBundle:Dynamic = null;
		var atlasBundles:Array<Dynamic> = [];
		var animationAssets:Array<Dynamic> = [];
		var unavailableAnimations:Array<String> = [];
		var animations:Dynamic = field(data, 'animations');
		if (!Std.isOfType(animations, Array)) {
			findings.push(makeDiagnostic('error', 'invalid-character-animations',
				'V-Slice character ' + name + ' has no animation array.', root));
			animations = [];
		}
		// Native fallback validation applies only to animations which use the
		// primary asset.  A multisparrow secondary atlas is allowed to introduce
		// its own prefixes; requiring those on the destination-native primary
		// atlas would reject an otherwise valid mixed-root combination.
		var requiredPrefixes = vSliceAnimationPrefixes(animations, assetPath);
		if (assetPath == '') {
			findings.push(makeDiagnostic('warning', 'missing-character-asset',
				'V-Slice character ' + name + ' has no assetPath.', root));
		} else {
			mainBundle = appendAssetBundle(root, assetPath, 'char', 'character', assets, findings, true,
				isPacker ? '.txt' : '.xml', requiredPrefixes, diagnosticPath);
			if (mainBundle != null && atlasSupported(mainBundle, isPacker))
				atlasBundles.push(mainBundle);
			else if (isMultiSparrow && (mainBundle == null || mainBundle.astcOnly != true))
				findings.push(makeDiagnostic('warning', 'multisparrow-primary-not-combined',
					'V-Slice multisparrow character ' + name
					+ ' has no usable primary Sparrow atlas; its authored atlas parts cannot be combined. '
					+ (mainBundle == null
						? 'The authored primary source is absent.'
						: 'The authored primary atlas metadata is incomplete.'), diagnosticPath));
		}

		var mainAssetKey = stripAssetExtension(assetPath).toLowerCase();
		var primaryAtlasUsable = mainBundle != null && atlasSupported(mainBundle, isPacker);
		// A destination-native primary atlas may cover fewer authored frame labels
		// than the donor wrote (base atlases drift across game versions).  Mark the
		// affected primary animations unavailable before the loop below so the
		// generated script never registers a zero-frame alias for them.  Donor-backed
		// atlases are always used verbatim and never carry missingPrefixes.
		markUnavailableForMissingPrefixes(animations, mainBundle, mainAssetKey, true, unavailableAnimations);
		var alternateAssetKeys = new Map<String, Bool>();
		var deathAssetCount = 0;
		for (animation in (cast animations:Array<Dynamic>)) {
			var animationAsset = stringValue(field(animation, 'assetPath'), '');
			var animationName = stringValue(field(animation, 'name'), 'animation');
			if (animationAsset == '' || stripAssetExtension(animationAsset).toLowerCase() == mainAssetKey) {
				// A multisparrow definition cannot use its primary animation table
				// until the primary image/XML pair is available.  Do not leave a
				// zero-frame alias behind when the source is genuinely absent or
				// ASTC conversion is unavailable; GameOverSubstate treats such an
				// alias as playable and can wait forever for frames that do not exist.
				if (isMultiSparrow && !primaryAtlasUsable && animationName != ''
					&& unavailableAnimations.indexOf(animationName) < 0)
					unavailableAnimations.push(animationName);
				continue;
			}
			var alternateKey = stripAssetExtension(animationAsset).toLowerCase();
			if (alternateAssetKeys.exists(alternateKey))
				continue;
			alternateAssetKeys.set(alternateKey, true);
			var isDeath = animationName.toLowerCase().startsWith('death') || animationName.toLowerCase() == 'firstdeath';
			var animationIndices = animationFrameIndices(animation);
			var hasIndices = Std.isOfType(animationIndices, Array) && (cast animationIndices:Array<Dynamic>).length > 0;
			var destination = isDeath && deathAssetCount == 0 ? 'dead' : 'alternate-' + safeIdentifier(animationName);
			if (isDeath)
				deathAssetCount++;
			// The native fallback must prove every prefix authored against this
			// secondary atlas (a later animation sharing the key adds its own).
			var alternatePrefixes = vSliceAnimationPrefixes(animations, animationAsset, true);
			var animationBundle = appendAssetBundle(root, animationAsset, destination, 'character-animation', assets, findings, true,
				isPacker ? '.txt' : '.xml', alternatePrefixes, diagnosticPath);
			markUnavailableForMissingPrefixes(animations, animationBundle, alternateKey, false, unavailableAnimations);
			if (isMultiSparrow) {
					if (primaryAtlasUsable && animationBundle != null && animationBundle.xmlSupported == true)
						atlasBundles.push(animationBundle);
					else if (!primaryAtlasUsable) {
						if (unavailableAnimations.indexOf(animationName) < 0)
							unavailableAnimations.push(animationName);
					} else if (animationBundle == null || (animationBundle.astcOnly != true && animationBundle.xmlSupported != true)) {
						unavailableAnimations.push(animationName);
						findings.push(makeDiagnostic('warning', 'multisparrow-subatlas-not-combined',
							'V-Slice multisparrow animation ' + animationName + ' references ' + animationAsset
							+ ', but that Sparrow atlas could not be combined; the animation may be unavailable.', diagnosticPath));
					} else if (animationBundle != null && animationBundle.astcOnly == true)
						// ASTC is present, but this process has no usable decoder.  The
						// astc-only finding already carries the exact source/recovery
						// diagnostic; do not add a misleading "missing atlas" warning.
						unavailableAnimations.push(animationName);
				} else
			{
				if (animationBundle != null && animationBundle.astcOnly != true) {
					// Preserve the authored per-animation atlas. Character's shared
					// runtime adapter re-registers the animation against the selected
					// atlas whenever playAnim() switches to it.
					animationAssets.push({
						name: animationName,
						bundle: animationBundle,
						prefix: stringValue(field(animation, 'prefix'), ''),
						indices: hasIndices ? animationIndices : [],
						fps: animationFrameRate(animation),
						loop: animationLoops(animationName, animation)
					});
				} else {
					unavailableAnimations.push(animationName);
					var switchReason = animationBundle == null
						? ('no PNG, ASTC, or validated destination-native fallback was found for the authored atlas '
							+ animationAsset + ' under the selected V-Slice source root')
						: ('the authored atlas ' + animationAsset
							+ ' is present but cannot be used as a native image until its ASTC decoder dependency is available');
					findings.push(makeDiagnostic('warning', 'animation-asset-switch',
						'Animation ' + animationName + ' uses a different V-Slice atlas (' + animationAsset + '), but '
							+ switchReason + '; the authored switch remains unavailable. Search root: ' + root + '.', diagnosticPath));
				}
			}
		}

		var icon:Dynamic = field(data, 'healthIcon');
		var authoredIconId = stringValue(field(icon, 'id'), '');
		// V-Slice itself falls back to the character id when healthIcon is
		// omitted.  A large number of otherwise complete mods rely on that
		// convention, so resolve the same icon instead of manufacturing Dad's
		// icon or reporting a false missing dependency.
		var iconId = authoredIconId == '' ? name : authoredIconId;
		// V-Slice commonly omits the healthIcon object for pixel characters.  The
		// character's own isPixel flag still selects the pixel/freeplay icon
		// namespace; losing it here makes an otherwise recoverable icon look
		// missing and can make case/variant matching ambiguous.
		var iconIsPixel = field(icon, 'isPixel') == true || field(data, 'isPixel') == true;
		var iconBundle = appendHealthIconBundle(root, iconId, iconIsPixel,
			assetPath, 'icons', assets, findings);
		if (iconBundle == null) {
			if (healthIconRequired) {
				var iconDescription = authoredIconId == ''
					? 'V-Slice character ' + name + ' has no healthIcon.id and its conventional icon-' + name + ' fallback could not be resolved.'
					: 'V-Slice health icon ' + iconId + ' could not be resolved.';
				findings.push(makeDiagnostic('warning', 'missing-health-icon', iconDescription, diagnosticPath));
			}
		} else if (iconBundle.astcOnly != true && iconBundle.fallback != null) {
			// Keep the report useful when an icon was found under a documented
			// V-Slice alias (for example a pixel/freeplay stem).  This is a
			// donor-backed path resolution, not a generated or substituted icon.
			findings.push(makeDiagnostic('info', 'health-icon-alias',
				'V-Slice health icon ' + iconId + ' was resolved from donor asset ' + iconBundle.fallback + '.', iconBundle.fallback));
		}
		if (icon != null && numberValue(field(icon, 'scale'), 1) != 1)
			findings.push(makeDiagnostic('warning', 'health-icon-scale',
				'Health-icon scale is retained in conversion metadata but native HealthIcon does not apply it.', root));
		if (icon != null && field(icon, 'flipX') != null && field(icon, 'flipX') == true)
			findings.push(makeDiagnostic('warning', 'health-icon-flip',
				'Health-icon flipX is retained in conversion metadata but native HealthIcon does not expose it.', root));

		var healthbarColor = healthbarColorString(field(data, 'healthbar_colors'), findings);
		var authoredCostumes:Dynamic = field(data, 'costumes');
		var authoredCostumeList:Dynamic = field(data, 'costumelist');
		var authoredDoesLoop:Bool = field(data, 'doesLoop') == true;
		var registryEntry:Dynamic = {
			like: name,
			icons: [0, 1, 2, 3],
			colors: healthbarColor == null ? ['#FFFFFFFF'] : [healthbarColor],
			vSliceHealthIcon: icon,
			vSliceHealthIconRequired: healthIconRequired,
			// Keep V-Slice costume metadata in the destination registry.  It is
			// consumed by the generic character/HXC bridge; dropping it here would
			// make CostumeSwapper fall back to the base character silently.
			vSliceCostumes: authoredCostumes,
			vSliceCostumeList: authoredCostumeList == null ? [] : authoredCostumeList,
			vSliceDoesLoop: authoredDoesLoop
		};
		// A character whose primary atlas resolved to a base-library character
		// (the donor ships no sheet because the engine owns it) also inherits
		// that character's health icon: the donor's icon-<id> convention cannot
		// resolve for an id the base game never drew.
		if (mainBundle != null && mainBundle.native == true
			&& Std.string(Reflect.field(mainBundle, 'name')).trim() != '') {
			Reflect.setField(registryEntry, 'nativeIconIdentity',
				Std.string(Reflect.field(mainBundle, 'name')));
		}
		var hscript = generateCharacterHScript(data, name, mainBundle, atlasBundles, animationAssets,
			unavailableAnimations, isMultiSparrow, isPacker, findings);
		var availableAnimationCount = 0;
		for (animation in (cast animations:Array<Dynamic>)) {
			var animationName = stringValue(field(animation, 'name'), '');
			if (animationName != '' && unavailableAnimations.indexOf(animationName) < 0)
				availableAnimationCount++;
		}
		// A missing secondary sheet (commonly an optional game-over set) is
		// diagnosed above and its animations are omitted from the generated
		// script. Keep the complete primary atlas and playable animations; making
		// the whole character unsupported also loses normal gameplay art.
		var supported = primaryAtlasUsable && availableAnimationCount > 0;
		return {name: name, registryEntry: registryEntry, hscript: hscript, assets: assets,
			diagnostics: findings, supported: supported};
	}

	/** Convert one V-Slice stage definition into native stage registry/HScript text. */
	public static function convertStage(data:Dynamic, ?sourceRoot:String, ?nativeName:String,
		?sourcePath:String):VSliceStageConversion {
		var findings:Array<VSliceDiagnostic> = [];
		var root = normalizeSourceRoot(sourceRoot);
		var diagnosticPath = sourcePath == null || StringTools.trim(sourcePath) == '' ? root : sourcePath;
		var requestedName = nativeName == null || nativeName.trim() == '' ? stringValue(field(data, 'name'), 'v-slice-stage') : nativeName;
		var name = safeStem(requestedName);
		if (name == 'song')
			name = 'v-slice-stage';
		var assets:Array<VSliceAssetMapping> = [];
		var zoom = numberValue(field(data, 'cameraZoom'), 1.05);
		if (zoom <= 0) {
			zoom = 1.05;
			findings.push(makeDiagnostic('warning', 'invalid-stage-zoom',
				'V-Slice stage cameraZoom was not positive; using 1.05.', root));
		}

		var characterData = field(data, 'characters');
		for (fieldName in safeFields(data)) {
			// `directory` selects a V-Slice asset library (most often `shared`).
			// resolveVSliceAsset already probes both images/ and shared/images/, so
			// retaining it as recognized metadata requires no chart-specific path.
			if (!containsString(['props', 'cameraZoom', 'version', 'characters', 'name', 'directory'], fieldName))
				findings.push(makeDiagnostic('warning', 'unsupported-stage-field',
					'V-Slice stage field ' + fieldName + ' is not represented by the native stage API.', root));
		}
		var characterZ:Map<String, Float> = new Map<String, Float>();
		for (slot in ['bf', 'dad', 'gf']) {
			var info = field(characterData, slot);
			if (info == null)
				continue;
			characterZ.set(slot, numberValue(field(info, 'zIndex'), defaultCharacterZ(slot)));
		}
		for (slot in safeFields(characterData)) {
			if (slot != 'bf' && slot != 'dad' && slot != 'gf')
				findings.push(makeDiagnostic('warning', 'unsupported-stage-character',
					'V-Slice stage character slot ' + slot + ' is not a native bf/dad/gf slot.', root));
		}

		var declarations:Array<String> = [];
		var danceLines:Array<String> = [];
		var lines:Array<String> = [];
		lines.push('function start(song) {');
		lines.push('    setDefaultZoom(' + formatNumber(zoom) + ');');
		appendStageCharacterLines(lines, 'bf', field(characterData, 'bf'), findings, root);
		appendStageCharacterLines(lines, 'dad', field(characterData, 'dad'), findings, root);
		appendStageCharacterLines(lines, 'gf', field(characterData, 'gf'), findings, root);
		// A V-Slice prop may be intentionally left without an assetPath when the
		// companion Stage HXC constructs the sprite itself.  Keep the JSON
		// converter conservative: only a prop proven by the same generated HScript
		// that PlayState will execute, with a real donor-backed graphic/atlas and a
		// visible add operation, is considered script-owned.
		var scriptOwnedProps = scriptOwnedStageProps(root, name);

		var props:Dynamic = field(data, 'props');
		var propList:Array<Dynamic> = Std.isOfType(props, Array) ? (cast props:Array<Dynamic>).copy() : [];
		if (props != null && !Std.isOfType(props, Array))
			findings.push(makeDiagnostic('warning', 'invalid-stage-props',
				'V-Slice stage props is not an array; no props were emitted.', root));
		propList.sort(function(a, b) {
			var za = numberValue(field(a, 'zIndex'), 0);
			var zb = numberValue(field(b, 'zIndex'), 0);
			return za < zb ? -1 : za > zb ? 1 : 0;
		});
		var propIndex = 0;
		for (prop in propList) {
			for (fieldName in safeFields(prop)) {
				if (!containsString(['zIndex', 'position', 'scale', 'animType', 'name', 'isPixel', 'startingAnimation',
					'assetPath', 'scroll', 'animations', 'alpha', 'blend', 'blendMode', 'flipX', 'flipY', 'angle',
					'color', 'danceEvery'], fieldName))
					findings.push(makeDiagnostic('warning', 'unsupported-stage-prop-field',
						'V-Slice stage prop field ' + fieldName + ' is not represented by the native stage API.', root));
			}
			var propName = stringValue(field(prop, 'name'), 'prop' + propIndex);
			var identifier = 'vSliceProp_' + safeIdentifier(propName) + '_' + propIndex;
			var propAsset = stringValue(field(prop, 'assetPath'), '');
			if (propAsset == '') {
				if (scriptOwnedProps.exists(propName.toLowerCase())) {
					propIndex++;
					continue;
				}
				findings.push(makeDiagnostic('warning', 'missing-prop-asset',
					'V-Slice stage prop ' + propName + ' has no assetPath and was omitted; no matching runtime HXC sprite with a donor-backed graphic was found.', diagnosticPath));
				propIndex++;
				continue;
			}
			var solidColor:Null<String> = null;
			var normalizedPropAsset = propAsset.toLowerCase();
			if (propAsset.startsWith('#') || normalizedPropAsset.startsWith('0x'))
				solidColor = colorLiteral(propAsset);
			var bundle:Dynamic = null;
			if (solidColor != null)
				bundle = {destinationBase: '', xmlSupported: false, solidColor: solidColor};
			else {
				var propAnimations = field(prop, 'animations');
				var propAnimType = stringValue(field(prop, 'animType'), 'sparrow').toLowerCase();
				var expectsAtlas = propAnimType != 'none'
					&& Std.isOfType(propAnimations, Array) && (cast propAnimations:Array<Dynamic>).length > 0;
				bundle = appendAssetBundle(root, propAsset, 'prop-' + safeIdentifier(propName) + '-' + propIndex,
					'stage-prop', assets, findings, expectsAtlas,
					isSpriteSheetPackerType(propAnimType) ? '.txt' : '.xml', null, diagnosticPath);
			}
			if (bundle == null) {
				propIndex++;
				continue;
			}
			appendStagePropLines(lines, declarations, danceLines, prop, identifier, bundle, characterZ, findings, root);
			propIndex++;
		}
		lines.push('}');
		lines.push('');
		lines.push('function beatHit(beat) {');
		for (danceLine in danceLines)
			lines.push(danceLine);
		lines.push('}');
		lines.push('function update(elapsed) {}');
		lines.push('function stepHit(step) {}');
		lines.push('function playerTwoTurn() {}');
		lines.push('function playerTwoMiss() {}');
		lines.push('function playerTwoSing() {}');
		lines.push('function playerOneTurn() {}');
		lines.push('function playerOneMiss() {}');
		lines.push('function playerOneSing() {}');

		declarations.push('');
		declarations = declarations.concat(lines);
		return {name: name, registryValue: name, hscript: declarations.join('\n') + '\n', assets: assets, diagnostics: findings};
	}

	static function generateCharacterHScript(data:Dynamic, name:String, mainBundle:Dynamic,
		atlasBundles:Array<Dynamic>, animationAssets:Array<Dynamic>, unavailableAnimations:Array<String>, isMultiSparrow:Bool,
		isPacker:Bool,
		findings:Array<VSliceDiagnostic>):String {
		var lines:Array<String> = [];
		var isPixel = field(data, 'isPixel') == true;
		var scale = numberValue(field(data, 'scale'), 1);
		if (scale <= 0) {
			scale = 1;
			findings.push(makeDiagnostic('warning', 'invalid-character-scale',
				'V-Slice character scale was not positive; using 1.', ''));
		}
		var singTime = numberValue(field(data, 'singTime'), 4);
		if (singTime <= 0)
			singTime = 4;
		var flipX = field(data, 'flipX') == true;
		var startingAnimation = stringValue(field(data, 'startingAnimation'), '');
		var danceEvery = numberValue(field(data, 'danceEvery'), 1);
		var hasDanceEvery = field(data, 'danceEvery') != null;
		if (hasDanceEvery && (danceEvery < 0 || danceEvery != Math.floor(danceEvery))) {
			findings.push(makeDiagnostic('warning', 'invalid-character-dance-every',
				'V-Slice character danceEvery must be a non-negative whole number; using the default cadence.', ''));
			danceEvery = 1;
		}
		var noAntialiasing = field(data, 'no_antialiasing');
		var antialiasing = noAntialiasing == null ? !isPixel : noAntialiasing != true;
		var cameraOffsets = numberPair(field(data, 'cameraOffsets'));
		if (cameraOffsets == null)
			cameraOffsets = numberPair(field(data, 'camera_position'));
		var offsets = numberPair(field(data, 'offsets'));
		if (offsets == null)
			offsets = numberPair(field(data, 'position'));
		var death = field(data, 'death');
		var deathCameraOffsets = numberPair(field(death, 'cameraOffsets'));
		var deathCameraZoom = numberValue(field(death, 'cameraZoom'), 0);
		var animations:Array<Dynamic> = Std.isOfType(field(data, 'animations'), Array)
			? (cast field(data, 'animations'):Array<Dynamic>) : [];
		var hasIdle = false;
		var firstAvailableAnimation = '';
		for (animation in animations) {
			var animName = stringValue(field(animation, 'name'), '');
			if (animName == '')
				continue;
			var unavailable = unavailableAnimations != null && unavailableAnimations.indexOf(animName) >= 0;
			if (!unavailable && firstAvailableAnimation == '')
				firstAvailableAnimation = animName;
			if (!unavailable && animName == 'idle')
				hasIdle = true;
		}
		if (startingAnimation != '') {
			var startingFound = false;
			for (animation in animations)
				if (stringValue(field(animation, 'name'), '') == startingAnimation
					&& (unavailableAnimations == null || unavailableAnimations.indexOf(startingAnimation) < 0))
					startingFound = true;
			if (!startingFound)
				findings.push(makeDiagnostic('warning', 'invalid-character-starting-animation',
					'V-Slice character startingAnimation ' + startingAnimation + ' was not present in its animation list.', ''));
		}
		if (!hasIdle && animations.length == 0)
			findings.push(makeDiagnostic('warning', 'missing-idle-animation',
				'V-Slice character has no animations; the generated character will be static.', ''));

		// Donor Bopper.dance() flips between danceLeft and danceRight on every
		// dance tick when the definition has a danceLeft animation.  A donor
		// idle authored as the pair is one continuous cycle split in halves
		// (for example the Tricky girlfriend's [30, 0..14] / [15..29] rows), so
		// replaying a single half looped mid-swing and read as too fast / cut
		// off.  Availability uses the same unavailable filter as the
		// registrations below so a missing alias can never be played.
		var hasDanceLeft = false;
		var hasDanceRight = false;
		for (animation in animations) {
			var danceName = stringValue(field(animation, 'name'), '');
			if (danceName == '' || (unavailableAnimations != null && unavailableAnimations.indexOf(danceName) >= 0))
				continue;
			if (danceName == 'danceLeft')
				hasDanceLeft = true;
			else if (danceName == 'danceRight')
				hasDanceRight = true;
		}
		var hasDancePair = hasDanceLeft && hasDanceRight;

		// The donor opening pose is whatever BaseCharacter.onCreate's
		// dance(true) lands on: danceLeft when a danceLeft animation exists,
		// otherwise idle (verified against the 0.7.3/0.8.1 engine sources -
		// CharacterData.startingAnimation is parsed but never consumed for
		// characters, only for stage props).  Anchoring and the donor camera
		// focus are measured against this pose's frame, so the generated
		// character must open on the same animation the donor plants.
		var initialAnimation = hasDancePair ? 'danceLeft' : (hasIdle ? 'idle' : (firstAvailableAnimation == '' ? 'idle' : firstAvailableAnimation));
		var danceAnimation = hasIdle ? 'idle' : (firstAvailableAnimation == '' ? 'idle' : firstAvailableAnimation);

		lines.push('isPixel = ' + (isPixel ? 'true' : 'false') + ';');
		lines.push('dadVar = ' + formatNumber(singTime) + ';');
		if (hasDancePair)
			lines.push('vSliceHasDanced = false;');
		lines.push('function init(char) {');
		if (hasDanceEvery)
			lines.push('    char.danceEvery = ' + Std.string(Std.int(danceEvery)) + ';');
		if (isMultiSparrow && atlasBundles != null && atlasBundles.length > 0) {
			lines.push('    var vSliceAtlases = [];');
			for (bundle in atlasBundles) {
				var nativeRoot = stringValue(field(bundle, 'nativeRoot'), '');
				var rootExpression = nativeRoot == '' ? 'hscriptPath' : '"' + hscriptQuote(nativeRoot) + '"';
				lines.push('    vSliceAtlases.push([' + rootExpression + ' + "' + hscriptQuote(bundle.destinationBase) + '.png", '
					+ rootExpression + ' + "' + hscriptQuote(bundle.destinationBase) + '.xml"]);');
			}
			lines.push('    char.frames = FlxAtlasFrames.combineSparrow(vSliceAtlases);');
		} else {
			var nativeRoot = mainBundle == null ? null : stringValue(field(mainBundle, 'nativeRoot'), '');
			if (nativeRoot != '') {
				// The destination-native atlas is not copied into the generated
				// character folder.  Keep its canonical scoped path in the generated
				// adapter so runtime lookup is identical on Linux and Windows.
				lines.push('    var vSliceNativeRoot = "' + hscriptQuote(nativeRoot) + '";');
				lines.push('    var vSliceSuffix = char.isDie && FNFAssets.exists(vSliceNativeRoot + "dead.png") ? "dead" : "char";');
				lines.push('    var vSlicePng = vSliceNativeRoot + vSliceSuffix + ".png";');
			} else {
				// V-Slice death animations usually live on the primary atlas; only
				// switch sheets when the donor actually shipped a dead one. Without
				// this guard a missing dead.png crashes game over.
				lines.push('    var vSliceSuffix = char.isDie && FNFAssets.exists(hscriptPath + "dead.png") ? "dead" : "char";');
				lines.push('    var vSlicePng = hscriptPath + vSliceSuffix + ".png";');
			}
			var atlasExtension = isPacker ? '.txt' : '.xml';
			if (mainBundle != null && atlasSupported(mainBundle, isPacker)) {
				var atlasRoot = nativeRoot == '' ? 'hscriptPath' : 'vSliceNativeRoot';
				lines.push('    if (FNFAssets.exists(' + atlasRoot + ' + vSliceSuffix + "' + atlasExtension + '"))');
				if (isPacker)
					lines.push('        char.frames = FlxAtlasFrames.fromSpriteSheetPacker(vSlicePng, ' + atlasRoot + ' + vSliceSuffix + "' + atlasExtension + '");');
				else
					lines.push('        char.frames = FlxAtlasFrames.fromSparrow(vSlicePng, ' + atlasRoot + ' + vSliceSuffix + "' + atlasExtension + '");');
				lines.push('    else');
				lines.push('        char.loadGraphic(vSlicePng);');
			} else {
				lines.push('    char.loadGraphic(vSlicePng);');
			}
		}
		lines.push('    char.scale.set(' + formatNumber(scale) + ', ' + formatNumber(scale) + ');');
		lines.push('    char.updateHitbox();');
		lines.push('    char.flipX = ' + (flipX ? 'true' : 'false') + ';');
		lines.push('    char.antialiasing = ' + (antialiasing ? 'true' : 'false') + ';');
		lines.push('    char.like = "' + hscriptQuote(name) + '";');
		// These fields are intentionally emitted into the runtime character as
		// well as the registry entry.  Foreign HXC modules can therefore query
		// the active metadata after a character swap without reading donor paths.
		var costumeRoot = stringValue(field(data, 'costumes'), '');
		var costumeList:Dynamic = field(data, 'costumelist');
		if (!Std.isOfType(costumeList, Array))
			costumeList = [];
		lines.push('    char.vSliceCostumes = ' + hscriptDynamic(costumeRoot) + ';');
		lines.push('    char.costumes = char.vSliceCostumes;');
		lines.push('    char.vSliceCostumeList = ' + hscriptDynamic(costumeList) + ';');
		lines.push('    char.costumelist = char.vSliceCostumeList;');
		lines.push('    char.vSliceDoesLoop = ' + (field(data, 'doesLoop') == true ? 'true' : 'false') + ';');
		lines.push('    char.doesLoop = char.vSliceDoesLoop;');
		if (deathCameraOffsets != null) {
			lines.push('    char.deathCameraOffsetX = ' + formatNumber(deathCameraOffsets[0]) + ';');
			lines.push('    char.deathCameraOffsetY = ' + formatNumber(deathCameraOffsets[1]) + ';');
		}
		if (deathCameraZoom > 0)
			lines.push('    char.deathCameraZoom = ' + formatNumber(deathCameraZoom) + ';');
		if (offsets != null) {
			lines.push('    char.vSliceGlobalOffsetX = ' + formatNumber(offsets[0]) + ';');
			lines.push('    char.vSliceGlobalOffsetY = ' + formatNumber(offsets[1]) + ';');
			lines.push('    char.vSliceGlobalOffsetsAuthored = true;');
			lines.push('    char.playerOffsetX = ' + formatNumber(offsets[0]) + ';');
			lines.push('    char.playerOffsetY = ' + formatNumber(offsets[1]) + ';');
			lines.push('    char.enemyOffsetX = ' + formatNumber(offsets[0]) + ';');
			lines.push('    char.enemyOffsetY = ' + formatNumber(offsets[1]) + ';');
			lines.push('    char.gfOffsetX = ' + formatNumber(offsets[0]) + ';');
			lines.push('    char.gfOffsetY = ' + formatNumber(offsets[1]) + ';');
		}
		if (cameraOffsets != null) {
			lines.push('    char.followCamX += ' + formatNumber(cameraOffsets[0]) + ';');
			lines.push('    char.followCamY += ' + formatNumber(cameraOffsets[1]) + ';');
			// Authored character-level camera offsets in the donor's absolute
			// convention.  Imported stage scripts zero followCamX/Y (they cancel
			// the classic 150/-100 defaults AND this accumulation) and let
			// stage.setCamOffsets recompose stage + character offsets, so the
			// authored values survive here for StageHelper to reapply.
			lines.push('    char.vSliceCamOffsetX = ' + Std.string(Std.int(Math.round(cameraOffsets[0]))) + ';');
			lines.push('    char.vSliceCamOffsetY = ' + Std.string(Std.int(Math.round(cameraOffsets[1]))) + ';');
		}
		lines.push('    char.rememberVSliceBaseFrames();');
		// Preserve the primary atlas's animation definitions so the runtime can
		// restore them after a secondary asset has been used.
		for (animation in animations) {
			var animName = stringValue(field(animation, 'name'), '');
			var prefix = stringValue(field(animation, 'prefix'), '');
			var indices = animationFrameIndices(animation);
			var hasIndices = Std.isOfType(indices, Array) && (cast indices:Array<Dynamic>).length > 0;
			if (animName == '' || (prefix == '' && !hasIndices)) {
				findings.push(makeDiagnostic('warning', 'invalid-character-animation',
					'V-Slice character animation is missing name or frame indices and was skipped.', ''));
				continue;
			}
			// Do not register an animation whose atlas could not be resolved.  A
			// zero-frame FlxAnimation still reports `exists(name)` and makes
			// GameOverSubstate wait forever instead of taking its normal no-death
			// fallback.  The authored definition remains in the diagnostic and the
			// source-side import plan; the destination simply omits this unavailable
			// runtime alias until a real atlas is supplied.
			if (unavailableAnimations != null && unavailableAnimations.indexOf(animName) >= 0)
				continue;
			var frameRate = animationFrameRate(animation);
			if (frameRate <= 0)
				frameRate = 24;
			var loop = animationLoops(animName, animation);
			if (hasIndices) {
				lines.push('    char.animation.addByIndices("' + hscriptQuote(animName) + '", "' + hscriptQuote(prefix) + '", '
					+ hscriptIntArray(cast indices) + ', "", ' + formatNumber(frameRate) + ', ' + (loop ? 'true' : 'false') + ');');
			} else if (prefix == '') {
				findings.push(makeDiagnostic('warning', 'invalid-character-animation',
					'V-Slice character animation ' + animName + ' is missing a prefix and frame indices and was skipped.', ''));
			} else {
				lines.push('    char.animation.addByPrefix("' + hscriptQuote(animName) + '", "' + hscriptQuote(prefix) + '", '
					+ formatNumber(frameRate) + ', ' + (loop ? 'true' : 'false') + ');');
			}
			lines.push('    char.registerVSliceAnimationAsset("' + hscriptQuote(animName) + '", "", "", "'
				+ hscriptQuote(prefix) + '", ' + (hasIndices ? hscriptIntArray(cast indices) : '[]') + ', '
				+ formatNumber(frameRate) + ', ' + (loop ? 'true' : 'false') + ');');
			var animOffsets = numberPair(field(animation, 'offsets'));
			if (animOffsets == null)
				animOffsets = [0, 0];
			lines.push('    char.addOffset("' + hscriptQuote(animName) + '", ' + formatNumber(animOffsets[0]) + ', ' + formatNumber(animOffsets[1]) + ');');
		}
		if (!isMultiSparrow && animationAssets != null)
			for (asset in animationAssets) {
				if (asset == null || field(asset, 'bundle') == null)
					continue;
				var bundle:Dynamic = field(asset, 'bundle');
				var animName = stringValue(field(asset, 'name'), 'animation');
				var prefix = stringValue(field(asset, 'prefix'), '');
				var indices:Dynamic = field(asset, 'indices');
				// A secondary atlas which the destination owns natively keeps its
				// canonical scoped path; donor-backed ones stay beside the generated
				// script.  The runtime adapter resolves either spelling through the
				// same asset layer.
				var animationNativeRoot = stringValue(field(bundle, 'nativeRoot'), '');
				var assetRoot = animationNativeRoot == '' ? 'hscriptPath' : '"' + hscriptQuote(animationNativeRoot) + '"';
				var xml = bundle.xmlSupported == true ? assetRoot + ' + "' + hscriptQuote(bundle.destinationBase) + '.xml"' : '""';
				var txt = bundle.txtSupported == true ? assetRoot + ' + "' + hscriptQuote(bundle.destinationBase) + '.txt"' : '""';
				lines.push('    char.registerVSliceAnimationAsset("' + hscriptQuote(animName) + '", ' + assetRoot + ' + "'
					+ hscriptQuote(bundle.destinationBase) + '.png", ' + xml + ', "' + hscriptQuote(prefix) + '", '
					+ (Std.isOfType(indices, Array) ? hscriptIntArray(indices) : '[]') + ', '
					+ formatNumber(numberValue(field(asset, 'fps'), 24)) + ', '
					+ (field(asset, 'loop') == true ? 'true' : 'false') + ', ' + txt + ');');
			}
		lines.push('    char.playAnim("' + hscriptQuote(initialAnimation) + '");');
		// Donor resetCharacter(): dance first, then updateHitbox so width and
		// height describe the opening pose's frame.  Imported stage scripts
		// anchor characters at position - origin (feet), so the hitbox must be
		// the opening animation's box, not the atlas's first frame.
		lines.push('    char.updateHitbox();');
		lines.push('}');
		lines.push('function update(elapsed, char) {}');
		lines.push('function dance(char) {');
		if (hasDancePair) {
			// Mirror the donor dance tick: alternate the pair and force-restart
			// it (donor Bopper passes shouldBop=true from onStepHit), so each
			// half plays from its first frame and holds finished until the
			// next tick on slow songs, exactly like the donor engine.
			lines.push('    if (vSliceHasDanced)');
			lines.push('        char.playAnim("danceRight", true);');
			lines.push('    else');
			lines.push('        char.playAnim("danceLeft", true);');
			lines.push('    vSliceHasDanced = !vSliceHasDanced;');
		} else {
			lines.push('    char.playAnim("' + hscriptQuote(danceAnimation) + '");');
		}
		lines.push('}');
		return lines.join('\n') + '\n';
	}

	static function appendStageCharacterLines(lines:Array<String>, slot:String, info:Dynamic,
		findings:Array<VSliceDiagnostic>, root:String):Void {
		if (info == null)
			return;
		var actor = slot == 'bf' ? 'boyfriend' : slot;
		var pos = numberPair(field(info, 'position'));
		var scale = numberPair(field(info, 'scale'));
		var scroll = numberPair(field(info, 'scroll'));
		var camera = numberPair(field(info, 'cameraOffsets'));
		var presentationCamera:Array<Float> = camera == null ? [0.0, 0.0] : camera;
		if (scale == null) scale = [1, 1];
		if (scroll == null) scroll = [1, 1];
		if (pos != null)
			lines.push('    stage.setVSliceCharacterPresentation("' + slot + '", '
				+ formatNumber(pos[0]) + ', ' + formatNumber(pos[1]) + ', '
				+ formatNumber(scale[0]) + ', ' + formatNumber(scale[1]) + ', '
				+ formatNumber(scroll[0]) + ', ' + formatNumber(scroll[1]) + ', '
				+ formatNumber(numberValue(field(info, 'alpha'), 1)) + ', '
				+ formatNumber(numberValue(field(info, 'angle'), 0)) + ', '
				+ Std.string(Std.int(Math.round(presentationCamera[0]))) + ', '
				+ Std.string(Std.int(Math.round(presentationCamera[1]))) + ');');
		// V-Slice applies stage character scale multiplicatively on top of the
		// character's own base scale (funkin Stage.addCharacter: baseScale *
		// stageCharData.scale).  Apply it BEFORE positioning: funkin anchors a
		// stage position at the character's FEET (characterOrigin = width/2,
		// height; corner = position - origin), so the hitbox must be final for
		// the anchor conversion below to land where the donor plants them.
		if (scale != null && (scale[0] != 1 || scale[1] != 1)) {
			lines.push('    ' + actor + '.scale.set(' + actor + '.scale.x * ' + formatNumber(scale[0]) + ', '
				+ actor + '.scale.y * ' + formatNumber(scale[1]) + ');');
			lines.push('    ' + actor + '.updateHitbox();');
		}
		if (pos != null) {
			// funkin Stage.addCharacter: character.x = position[0] - characterOrigin.x,
			// with characterOrigin recomputed from the live hitbox (horizontal
			// center, vertical bottom).  BaseCharacter.setScale then re-adds the
			// character's authored globalOffsets (CharacterData.offsets, carried
			// on the runtime character as the per-slot offset fields), so the
			// authored feet coordinates keep their donor meaning.  Emit the same
			// conversion at runtime so it lands for any sheet scale, and keep
			// StageHelper's persistent slot info in sync for later swaps.
			var globalOffsetField = slot == 'bf' ? 'playerOffset' : (slot == 'gf' ? 'gfOffset' : 'enemyOffset');
			lines.push('    stage.setOffsets("' + slot + '", ' + formatNumber(pos[0]) + ' - ' + actor + '.width / 2 + ' + actor + '.' + globalOffsetField + 'X, '
				+ formatNumber(pos[1]) + ' - ' + actor + '.height + ' + actor + '.' + globalOffsetField + 'Y, false);');
			lines.push('    ' + actor + '.x = ' + formatNumber(pos[0]) + ' - ' + actor + '.width / 2 + ' + actor + '.' + globalOffsetField + 'X;');
			lines.push('    ' + actor + '.y = ' + formatNumber(pos[1]) + ' - ' + actor + '.height + ' + actor + '.' + globalOffsetField + 'Y;');
		} else {
			findings.push(makeDiagnostic('warning', 'missing-stage-character-position',
				'V-Slice stage character ' + slot + ' has no numeric position.', root));
		}
		// The native focus math adds Character.followCamX/Y (classic defaults
		// 150/-100) AND the StageHelper camOffsets. V-Slice cameraOffsets are
		// absolute authored offsets, so zero the followCam fields and let
		// setCamOffsets be the single carrier — emitting both doubled every
		// offset and pushed imported cameras off their authored framing.
		lines.push('    ' + actor + '.followCamX = 0;');
		lines.push('    ' + actor + '.followCamY = 0;');
		if (camera != null) {
			lines.push('    stage.setCamOffsets("' + slot + '", ' + Std.string(Std.int(Math.round(camera[0]))) + ', '
				+ Std.string(Std.int(Math.round(camera[1]))) + ', false);');
		}
		// funkin sorts the whole stage (props AND characters) by zIndex.  The
		// authored character zIndex is what keeps props with huge donor z
		// values (crowd layers, gradients) from drawing over the actors in
		// the donor; without it a z-sorted display list buries every actor
		// under the stage art.
		var zValue = numberValue(field(info, 'zIndex'), Math.NaN);
		if (!Math.isNaN(zValue))
			lines.push('    stage.setCharacterZ("' + slot + '", ' + Std.string(Std.int(zValue)) + ');');
		// Alpha and angle are set directly; flip stays character-owned, so it
		// is deliberately not emitted here.
		if (field(info, 'alpha') != null)
			lines.push('    ' + actor + '.alpha = ' + formatNumber(numberValue(field(info, 'alpha'), 1)) + ';');
		if (field(info, 'angle') != null)
			lines.push('    ' + actor + '.angle = ' + formatNumber(numberValue(field(info, 'angle'), 0)) + ';');
	}

	static function appendStagePropLines(lines:Array<String>, declarations:Array<String>, danceLines:Array<String>, prop:Dynamic,
		identifier:String, bundle:Dynamic, characterZ:Map<String, Float>, findings:Array<VSliceDiagnostic>, root:String):Void {
		var position = numberPair(field(prop, 'position'));
		if (position == null)
			position = [0, 0];
		var scale = numberPair(field(prop, 'scale'));
		if (scale == null)
			scale = [1, 1];
		var scroll = numberPair(field(prop, 'scroll'));
		if (scroll == null)
			scroll = [1, 1];
		var alpha = numberValue(field(prop, 'alpha'), 1);
		var isPixel = field(prop, 'isPixel') == true;
		var animType = stringValue(field(prop, 'animType'), 'sparrow').toLowerCase();
		var isPacker = isSpriteSheetPackerType(animType);
		var atlasExtension = isPacker ? '.txt' : '.xml';
		var assetName = bundle.destinationBase;
		declarations.push('var ' + identifier + ';');
		lines.push('    ' + identifier + ' = new FlxSprite();');
		if (bundle.solidColor != null) {
			lines.push('    ' + identifier + '.makeGraphic(1, 1, ' + Std.string(bundle.solidColor) + ');');
		} else if (atlasSupported(bundle, isPacker) && animType != 'none') {
			if (isPacker)
				lines.push('    ' + identifier + '.frames = FlxAtlasFrames.fromSpriteSheetPacker(hscriptPath + "' + hscriptQuote(assetName) + '.png", hscriptPath + "' + hscriptQuote(assetName) + atlasExtension + '");');
			else
				lines.push('    ' + identifier + '.frames = FlxAtlasFrames.fromSparrow(hscriptPath + "' + hscriptQuote(assetName) + '.png", hscriptPath + "' + hscriptQuote(assetName) + atlasExtension + '");');
		} else {
			lines.push('    ' + identifier + '.loadGraphic(hscriptPath + "' + hscriptQuote(assetName) + '.png");');
		}
		lines.push('    ' + identifier + '.scale.set(' + formatNumber(scale[0]) + ', ' + formatNumber(scale[1]) + ');');
		// V-Slice updates the hitbox after scaling, then assigns the authored
		// position. Without this, Flixel renders a scaled prop around its old
		// frame center and shifts the visible background by half the scale delta.
		lines.push('    ' + identifier + '.updateHitbox();');
		lines.push('    ' + identifier + '.x = ' + formatNumber(position[0]) + ';');
		lines.push('    ' + identifier + '.y = ' + formatNumber(position[1]) + ';');
		lines.push('    ' + identifier + '.scrollFactor.set(' + formatNumber(scroll[0]) + ', ' + formatNumber(scroll[1]) + ');');
		lines.push('    ' + identifier + '.alpha = ' + formatNumber(alpha) + ';');
		lines.push('    ' + identifier + '.antialiasing = ' + (isPixel ? 'false' : 'true') + ';');
		if (field(prop, 'flipX') != null)
			lines.push('    ' + identifier + '.flipX = ' + (field(prop, 'flipX') == true ? 'true' : 'false') + ';');
		if (field(prop, 'flipY') != null)
			lines.push('    ' + identifier + '.flipY = ' + (field(prop, 'flipY') == true ? 'true' : 'false') + ';');
		if (field(prop, 'angle') != null)
			lines.push('    ' + identifier + '.angle = ' + formatNumber(numberValue(field(prop, 'angle'), 0)) + ';');
		if (field(prop, 'color') != null) {
			var propColor = colorLiteral(field(prop, 'color'));
			if (propColor == null)
				findings.push(makeDiagnostic('warning', 'invalid-stage-prop-color',
					'V-Slice stage prop ' + stringValue(field(prop, 'name'), identifier) + ' has an invalid color and kept the default tint.', root));
			else
				lines.push('    ' + identifier + '.color = ' + propColor + ';');
		}
		var blend = stringValue(field(prop, 'blend'), stringValue(field(prop, 'blendMode'), ''));
		if (blend != '')
			lines.push('    ' + identifier + '.blend = blendModeFromString("' + hscriptQuote(blend) + '");');
		var animations = field(prop, 'animations');
		var animationNames:Array<String> = [];
		if (Std.isOfType(animations, Array)) {
			for (animation in (cast animations:Array<Dynamic>)) {
				var animName = stringValue(field(animation, 'name'), '');
				var prefix = stringValue(field(animation, 'prefix'), '');
				var indices = animationFrameIndices(animation);
				var hasIndices = Std.isOfType(indices, Array) && (cast indices:Array<Dynamic>).length > 0;
				if (animName == '' || (prefix == '' && !hasIndices)) {
					findings.push(makeDiagnostic('warning', 'invalid-stage-animation',
						'V-Slice stage prop animation is missing name or frame indices and was skipped.', root));
					continue;
				}
				var fps = animationFrameRate(animation);
				var loop = animationLoopValue(animation, false);
				animationNames.push(animName);
				if (hasIndices)
					lines.push('    ' + identifier + '.animation.addByIndices("' + hscriptQuote(animName) + '", "' + hscriptQuote(prefix) + '", '
						+ hscriptIntArray(cast indices) + ', "", ' + formatNumber(fps) + ', ' + (loop ? 'true' : 'false') + ');');
				else
					lines.push('    ' + identifier + '.animation.addByPrefix("' + hscriptQuote(animName) + '", "' + hscriptQuote(prefix) + '", '
						+ formatNumber(fps) + ', ' + (loop ? 'true' : 'false') + ');');
			}
		}
		var startAnimation = stringValue(field(prop, 'startingAnimation'), '');
		if (startAnimation != '')
			lines.push('    ' + identifier + '.animation.play("' + hscriptQuote(startAnimation) + '", true);');
		appendStageDanceLines(danceLines, prop, identifier, animationNames, findings, root);
		var zIndex = numberValue(field(prop, 'zIndex'), 0);
		// The state-level refresh sorts props and actors together. Keep the
		// authored numeric depth, not only the coarse addSprite actor layer.
		lines.push('    stage.setZIndex(' + identifier + ', ' + Std.string(Std.int(zIndex)) + ');');
		lines.push('    addSprite(' + identifier + ', ' + stageLayerForZ(zIndex, characterZ) + ');');
		// Stage HXC addresses JSON props by their authored names, which need not
		// match the sanitized local identifiers used by generated HScript.
		lines.push('    stage.elements.set("' + hscriptQuote(stringValue(field(prop, 'name'), identifier))
			+ '", ' + identifier + ');');
	}

	static function appendStageDanceLines(danceLines:Array<String>, prop:Dynamic, identifier:String,
		animationNames:Array<String>, findings:Array<VSliceDiagnostic>, root:String):Void {
		if (danceLines == null || prop == null || animationNames == null || animationNames.length == 0)
			return;
		if (field(prop, 'danceEvery') == null)
			return;
		var rawEvery = numberValue(field(prop, 'danceEvery'), Math.NaN);
		if (Math.isNaN(rawEvery) || rawEvery < 0 || rawEvery != Math.floor(rawEvery)) {
			findings.push(makeDiagnostic('warning', 'invalid-stage-prop-dance-every',
				'V-Slice stage prop danceEvery must be a non-negative whole number; the authored cadence was not applied.', root));
			return;
		}
		var every = Std.int(rawEvery);
		if (every <= 0)
			return;
		var left:String = null;
		var right:String = null;
		for (name in animationNames) {
			if (name.toLowerCase() == 'danceleft')
				left = name;
			else if (name.toLowerCase() == 'danceright')
				right = name;
		}
		danceLines.push('    if (beat % ' + every + ' == 0) {');
		if (left != null && right != null) {
			danceLines.push('        if (Std.int(beat / ' + every + ') % 2 == 0)');
			danceLines.push('            ' + identifier + '.animation.play("' + hscriptQuote(left) + '", true);');
			danceLines.push('        else');
			danceLines.push('            ' + identifier + '.animation.play("' + hscriptQuote(right) + '", true);');
		} else {
			danceLines.push('        ' + identifier + '.animation.play("' + hscriptQuote(animationNames[0]) + '", true);');
		}
		danceLines.push('    }');
	}

	static function appendAssetBundle(root:String, assetPath:String, destinationBase:String, kind:String,
		assets:Array<VSliceAssetMapping>, findings:Array<VSliceDiagnostic>, expectsAtlas:Bool = true,
		atlasExtension:String = '.xml', ?requiredPrefixes:Array<String>, ?diagnosticPath:String):Dynamic {
		var findingPath = diagnosticPath == null || StringTools.trim(diagnosticPath) == '' ? root : diagnosticPath;
		// The authored loader selects the atlas format (`.xml` for Sparrow or
		// `.txt` for SpriteSheetPacker). Resolve and preserve both companions when
		// present, while exposing the selected format to generated runtime code.
		var normalizedAsset = stripAssetExtension(assetPath);
		if (normalizedAsset == '')
			return null;
		var png = resolveVSliceAsset(root, normalizedAsset, '.png');
		var xml = resolveVSliceAsset(root, normalizedAsset, '.xml');
		var txt = resolveVSliceAsset(root, normalizedAsset, '.txt');
		var astc = resolveVSliceAsset(root, normalizedAsset, '.astc');
		if (!png.found && root != '') {
			if (astc.found)
				return appendAstcBundle(astc.path, destinationBase, kind, assets, findings,
					xml.found ? xml.path : null, txt.found ? txt.path : null, atlasExtension);
			// Donor precedence: this branch only runs when the donor root has no
			// PNG for the authored path.  V-Slice omits base-game atlases from mods
			// because the original game owns them, so both a character's primary
			// atlas and one of its per-animation atlases may resolve to a
			// destination-native implementation instead of a copied file.
			if ((kind == 'character' || kind == 'character-animation') && expectsAtlas) {
				var native = resolveNativeCharacterAtlas(normalizedAsset, requiredPrefixes);
				if (native != null) {
					findings.push(makeDiagnostic('info', 'native-character-asset',
						'V-Slice character asset ' + assetPath + ' was resolved to the destination-native '
						+ native.name + ' atlas after validating the authored animation prefixes.',
						native.xml));
					var nativeMissing:Array<String> = Reflect.field(native, 'missingPrefixes');
					if (nativeMissing != null && nativeMissing.length > 0)
						findings.push(makeDiagnostic('warning', 'native-atlas-missing-prefixes',
							'The destination-native ' + native.name + ' atlas does not provide the authored '
							+ 'prefix(es) ' + nativeMissing.join(', ')
							+ '; animations which use only those prefixes stay unavailable instead of '
							+ 'becoming zero-frame aliases.', native.xml));
					return native;
				}
			}
			findings.push(makeDiagnostic('warning', 'missing-asset',
				'V-Slice ' + kind + ' PNG could not be found for ' + assetPath
				+ '. Search root: ' + root + '.', findingPath));
			return null;
		}
		assets.push({source: png.path, destination: destinationBase + '.png', kind: kind, supported: true});
		var atlasIsTxt = atlasExtension.toLowerCase() == '.txt';
		var atlas = atlasIsTxt ? txt : xml;
		var atlasSupported = atlas.found || root == '';
		var xmlSupported = xml.found || root == '';
		var txtSupported = txt.found || root == '';
		if (xml.found)
			assets.push({source: xml.path, destination: destinationBase + '.xml', kind: kind, supported: true});
		if (txt.found)
			assets.push({source: txt.path, destination: destinationBase + '.txt', kind: kind, supported: true});
		else if (kind != 'health-icon' && expectsAtlas && !atlasSupported)
			findings.push(makeDiagnostic('warning', 'missing-atlas-data',
				'V-Slice ' + kind + ' has a PNG but no ' + (atlasIsTxt ? 'SpriteSheetPacker TXT' : 'Sparrow XML')
				+ '; it will load as a static graphic.', png.path));
		return {destinationBase: destinationBase, xmlSupported: xmlSupported, txtSupported: txtSupported,
			atlasSupported: atlasSupported, atlasExtension: atlasExtension, png: png.path,
			xml: xml.path, txt: txt.path};
	}

	/**
		Collect the authored animation prefixes which the native fallback must
		actually provide.  Empty prefixes are intentionally omitted: an index-only
		animation cannot prove that a destination atlas is semantically compatible.

		With `exactAsset` the collection is limited to animations which name
		`primaryAssetPath` as their own atlas; animations without an assetPath
		belong to the primary atlas and must never widen a secondary atlas's
		validation.
	*/
	static function vSliceAnimationPrefixes(animations:Dynamic, ?primaryAssetPath:String,
		?exactAsset:Bool = false):Array<String> {
		var result:Array<String> = [];
		if (!Std.isOfType(animations, Array))
			return result;
		var primaryKey = stripAssetExtension(primaryAssetPath == null ? '' : primaryAssetPath).toLowerCase();
		for (animation in (cast animations:Array<Dynamic>)) {
			var animationAsset = stringValue(field(animation, 'assetPath'), '');
			var animationKey = stripAssetExtension(animationAsset).toLowerCase();
			if (exactAsset) {
				if (animationAsset == '' || animationKey != primaryKey)
					continue;
			} else if (primaryAssetPath != null && animationAsset != '' && animationKey != primaryKey)
				continue;
			var prefix = stringValue(field(animation, 'prefix'), '');
			if (prefix != '' && result.indexOf(prefix) < 0)
				result.push(prefix);
		}
		return result;
	}

	/**
		Keep the animations whose authored prefixes a destination-native fallback
		atlas cannot provide out of the generated script.  A native atlas is the
		same logical asset the donor referenced, but base atlases drift across game
		versions; unavailable marking beats a zero-frame alias, which
		GameOverSubstate and other waiters treat as playable forever.  Donor-backed
		atlases never carry `missingPrefixes`, so this is a no-op for them.
	*/
	static function markUnavailableForMissingPrefixes(animations:Dynamic, bundle:Dynamic,
		assetKey:String, primaryOnly:Bool, unavailable:Array<String>):Void {
		if (bundle == null || unavailable == null || !Std.isOfType(animations, Array))
			return;
		var missing:Dynamic = Reflect.field(bundle, 'missingPrefixes');
		if (missing == null || !Std.isOfType(missing, Array))
			return;
		var missingPrefixes:Array<String> = cast missing;
		if (missingPrefixes.length == 0)
			return;
		for (animation in (cast animations:Array<Dynamic>)) {
			var animationName = stringValue(field(animation, 'name'), '');
			var prefix = stringValue(field(animation, 'prefix'), '');
			if (animationName == '' || prefix == '' || missingPrefixes.indexOf(prefix) < 0
				|| unavailable.indexOf(animationName) >= 0)
				continue;
			var animationAsset = stringValue(field(animation, 'assetPath'), '');
			var animationKey = stripAssetExtension(animationAsset).toLowerCase();
			// The primary bundle covers animations with no assetPath of their own;
			// a secondary bundle only owns animations which name it exactly.
			var onThisAtlas = primaryOnly
				? (animationAsset == '' || animationKey == assetKey)
				: (animationAsset != '' && animationKey == assetKey);
			if (onThisAtlas)
				unavailable.push(animationName);
		}
	}

	/**
		Resolve one of the destination engine's registered base character atlases.

		This is deliberately stricter than `findVSliceAssetByBasename`: the
		logical V-Slice path must be an exact known base-library alias, the native
		registry must point at a real implementation, both atlas files must exist,
		and at least one authored prefix must be present in that atlas.  No donor
		files are copied and no arbitrary similarly named character can leak across
		an import root.

		Base atlases evolve across game versions, so a handful of authored frame
		labels may be absent from the destination implementation.  Those are
		reported as `missingPrefixes` on the bundle and the caller keeps the
		affected animations unavailable instead of rejecting the whole atlas or
		emitting zero-frame aliases.
	*/
	#if sys
	static function resolveNativeCharacterAtlas(assetPath:String, requiredPrefixes:Array<String>):Dynamic {
		var candidates = EngineCompat.vSliceNativeCharacterCandidates(assetPath);
		if (candidates == null || candidates.length == 0)
			return null;
		// Without any authored frame label there is no way to prove that the
		// native implementation is semantically the atlas the donor referenced;
		// stay conservative exactly as before.
		if (requiredPrefixes == null || requiredPrefixes.length == 0)
			return null;
		var registry:Dynamic = readNativeCharacterRegistry();
		if (registry == null)
			return null;
		for (candidate in candidates) {
			var entry = registryEntryCaseInsensitive(registry, candidate);
			if (entry == null)
				continue;
			var like = stringValue(field(entry, 'like'), candidate);
			if (like == '' || !isSafeNativeCharacterName(like))
				continue;
			var folder = Path.join(['assets', 'images', 'custom_chars', like]);
			var pngPath = Path.join([folder, 'char.png']);
			var xmlPath = Path.join([folder, 'char.xml']);
			if (!FileSystem.exists(pngPath) || FileSystem.isDirectory(pngPath)
				|| !FileSystem.exists(xmlPath) || FileSystem.isDirectory(xmlPath))
				continue;
			var missingPrefixes = atlasMissingPrefixes(xmlPath, requiredPrefixes);
			if (missingPrefixes.length >= requiredPrefixes.length)
				continue;
			return {
				name: candidate,
				native: true,
				nativeRoot: folder + '/',
				destinationBase: 'char',
				xmlSupported: true,
				txtSupported: false,
				atlasSupported: true,
				atlasExtension: '.xml',
				png: pngPath,
				xml: xmlPath,
				fallbackRegistry: candidate,
				missingPrefixes: missingPrefixes
			};
		}
		return null;
	}

	static function readNativeCharacterRegistry():Dynamic {
		for (path in ['assets/images/custom_chars/custom_chars.jsonc',
			'assets/images/custom_chars/custom_chars.json']) {
			if (!FileSystem.exists(path) || FileSystem.isDirectory(path))
				continue;
			try {
				return Json.parse(File.getContent(path));
			} catch (_:Dynamic) {}
		}
		return null;
	}

	static function registryEntryCaseInsensitive(registry:Dynamic, name:String):Dynamic {
		if (registry == null || name == null)
			return null;
		var direct = Reflect.field(registry, name);
		if (direct != null)
			return direct;
		var lower = name.toLowerCase();
		for (fieldName in Reflect.fields(registry))
			if (fieldName.toLowerCase() == lower)
				return Reflect.field(registry, fieldName);
		return null;
	}

	static function isSafeNativeCharacterName(value:String):Bool {
		if (value == null || value == '')
			return false;
		for (i in 0...value.length) {
			var c = value.charAt(i);
			if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
				|| (c >= '0' && c <= '9') || c == '_' || c == '-'))
				return false;
		}
		return true;
	}

	/** Return the subset of `prefixes` whose frames `xmlPath` does not provide. */
	static function atlasMissingPrefixes(xmlPath:String, prefixes:Array<String>):Array<String> {
		var missing:Array<String> = [];
		if (prefixes == null || prefixes.length == 0)
			return missing;
		var frameNames:Array<String> = [];
		try {
			var root = Xml.parse(File.getContent(xmlPath)).firstElement();
			if (root == null)
				return prefixes.copy();
			for (node in root.elements()) {
				var frame = node.get('name');
				if (frame != null && frame != '')
					frameNames.push(frame);
			}
		} catch (_:Dynamic) {
			return prefixes.copy();
		}
		for (prefix in prefixes) {
			var found = false;
			for (frame in frameNames)
				if (StringTools.startsWith(frame, prefix)) {
					found = true;
					break;
				}
			if (!found)
				missing.push(prefix);
		}
		return missing;
	}
	#end

	/**
		Plan an ASTC mapping without copying or rewriting the donor.  When a
		validated astcenc executable is available, the mapping points at the
		destination PNG and the import phase performs the conversion.  Otherwise
		it remains an explicitly unsupported `.astc` mapping so a raw compressed
		file can never be mistaken for a native image.
	*/
	static function appendAstcBundle(source:String, destinationBase:String, kind:String,
		assets:Array<VSliceAssetMapping>, findings:Array<VSliceDiagnostic>, ?xmlPath:String,
		?txtPath:String, atlasExtension:String = '.xml'):Dynamic {
		var header:VSliceAstcHeader = null;
		var decoderAvailable = false;
		var decoderName = '';
		#if sys
		header = VSliceAstcAdapter.inspectFile(source);
		if (header.valid && header.payloadMatches) {
			var probe = VSliceAstcAdapter.probe();
			decoderAvailable = probe.available;
			decoderName = probe.executable;
		}
		#end
		if (decoderAvailable) {
			assets.push({source: source, destination: destinationBase + '.png', kind: kind,
				supported: true, requiresConversion: true});
			var atlasIsTxt = atlasExtension.toLowerCase() == '.txt';
			var atlasPath = atlasIsTxt ? txtPath : xmlPath;
			var atlasSupported = atlasPath != null && StringTools.trim(atlasPath) != '';
			if (xmlPath != null && StringTools.trim(xmlPath) != '')
				assets.push({source: xmlPath, destination: destinationBase + '.xml', kind: kind, supported: true});
			if (txtPath != null && StringTools.trim(txtPath) != '')
				assets.push({source: txtPath, destination: destinationBase + '.txt', kind: kind, supported: true});
			findings.push(makeDiagnostic('info', 'astc-decoder-ready',
				'V-Slice ' + kind + ' ASTC will be decoded to PNG during import by ' + decoderName + '.', source));
			return {destinationBase: destinationBase, xmlSupported: !atlasIsTxt && atlasSupported,
				txtSupported: atlasIsTxt && atlasSupported, atlasSupported: atlasSupported,
				atlasExtension: atlasExtension, png: source,
				xml: !atlasIsTxt && atlasSupported ? xmlPath : null,
				txt: atlasIsTxt && atlasSupported ? txtPath : null, astcOnly: false, astcConverted: true};
		}
		assets.push({source: source, destination: destinationBase + '.astc', kind: kind,
			supported: false, requiresConversion: true});
		var detail = VSliceAstcAdapter.diagnostic(source, header);
		findings.push(makeDiagnostic('warning', 'astc-only',
			'V-Slice ' + kind + ' cannot be imported as a native PNG: ' + detail, source));
		return {destinationBase: destinationBase, xmlSupported: false, astcOnly: true,
			astcConverted: false};
	}

	/**
		Resolve a health icon using the naming variants emitted by V-Slice
		versions in the wild.  The primary `images/icons/icon-<id>.png` spelling
		is still preferred.  Pixel/freeplay icons and punctuation-only aliases
		are accepted only when a real donor PNG exists; no placeholder is ever
		created here.
	*/
	static function appendHealthIconBundle(root:String, iconId:String, isPixel:Bool,
		characterAssetPath:String, destinationBase:String, assets:Array<VSliceAssetMapping>,
		findings:Array<VSliceDiagnostic>):Dynamic {
		// These are V-Slice's explicit no-icon/native-character sentinels.  The
		// destination engine owns their health icons (or intentionally has no
		// icon for nogf), so requiring a donor PNG would report a false missing
		// dependency and could overwrite a built-in icon during import.
		if (isNativeHealthIcon(iconId))
			return {destinationBase: destinationBase, native: true, astcOnly: false};
		var candidates:Array<String> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		var addCandidate = function(value:String):Void {
			if (value == null)
				return;
			var clean = StringTools.replace(value.trim(), '\\', '/');
			while (clean.startsWith('./'))
				clean = clean.substr(2);
			if (clean == '')
				return;
			var key = clean.toLowerCase();
			if (!seen.exists(key)) {
				seen.set(key, true);
				candidates.push(clean);
			}
		};
		var id = iconId == null ? '' : iconId.trim();
		if (id != '') {
			addCandidate('icons/icon-' + id);
			addCandidate('icons/' + id);
			for (alias in iconAliases(id)) {
				addCandidate('icons/icon-' + alias);
				addCandidate('icons/' + alias);
			}
			if (isPixel) {
				addCandidate('freeplay/icons/' + id + (id.toLowerCase().endsWith('pixel') ? '' : 'pixel'));
				var compactId = compactIconName(id);
				if (compactId != id.toLowerCase())
					addCandidate('freeplay/icons/' + compactId + (compactId.endsWith('pixel') ? '' : 'pixel'));
			}
		}
		// A few V-Slice definitions leave healthIcon.id out while their icon
		// follows the character asset stem rather than the chart reference.
		// Try that stem only after the authored/reference identity.
		var assetStem = '';
		if (characterAssetPath != null)
			assetStem = Path.withoutDirectory(stripAssetExtension(characterAssetPath));
		if (assetStem != null && assetStem != '') {
			addCandidate('icons/icon-' + assetStem);
			addCandidate('icons/' + assetStem);
			if (isPixel)
				addCandidate('freeplay/icons/' + assetStem + (assetStem.toLowerCase().endsWith('pixel') ? '' : 'pixel'));
			// Some V-Slice exports name a character's asset after a visual
			// presentation rather than its health-icon id (for example
			// SilhouetteMonikaPixel -> monikapixel).  Prefer an exact donor-backed
			// stem alias before the bounded fuzzy scan below.  This is intentionally
			// limited to known presentation prefixes and never substitutes a
			// merely similarly named character.
			for (alias in iconAssetStemAliases(assetStem)) {
				if (isPixel)
					addCandidate('freeplay/icons/' + alias + (alias.toLowerCase().endsWith('pixel') ? '' : 'pixel'));
				addCandidate('icons/icon-' + alias);
				addCandidate('icons/' + alias);
			}
		}

		var astcPath:String = null;
		var astcXmlPath:String = null;
		for (candidate in candidates) {
			var png = resolveVSliceAsset(root, candidate, '.png');
			if (!png.found) {
				var astc = resolveVSliceAsset(root, candidate, '.astc');
				if (astc.found && astcPath == null) {
					astcPath = astc.path;
					var astcXml = resolveVSliceAsset(root, candidate, '.xml');
					if (astcXml.found)
						astcXmlPath = astcXml.path;
				}
				continue;
			}
			return finishHealthIconBundle(root, candidate, png, destinationBase, assets, findings, null);
		}

		// Filename punctuation and the pixel suffix vary between V-Slice's
		// `images/icons` and `images/freeplay/icons` exports.  Directory matching
		// is deliberately constrained to those icon folders and requires a unique
		// best match, so a generic character image can never be selected by name.
		var scanned = findVSliceIconPng(root, id, isPixel);
		if (scanned != null)
			return finishHealthIconBundle(root, scanned.stem, scanned.png, destinationBase, assets, findings, scanned.fallback);

		if (astcPath != null) {
			return appendAstcBundle(astcPath, destinationBase, 'health-icon', assets, findings, astcXmlPath);
		}
		return null;
	}

	/** Resolve an HXC script's literal HealthIcon id into files owned by the
	 * selected V-Slice import. `null` means the engine already owns a native
	 * icon id; an empty array means the requested donor asset was not found. */
	public static function hxcHealthIconMappings(root:String, iconId:String):Null<Array<VSliceAssetMapping>> {
		var id = iconId == null ? '' : StringTools.trim(iconId);
		if (id == '' || !new EReg('^[A-Za-z0-9_-]+$', '').match(id))
			return [];
		if (isNativeHealthIcon(id))
			return null;
		var assets:Array<VSliceAssetMapping> = [];
		appendHealthIconBundle(root, id, false, '', 'images/icons/icon-' + id, assets, []);
		var supported:Array<VSliceAssetMapping> = [];
		for (asset in assets)
			if (asset != null && asset.supported)
				supported.push(asset);
		return supported;
	}

	static function finishHealthIconBundle(root:String, candidate:String, png:Dynamic, destinationBase:String,
		assets:Array<VSliceAssetMapping>, findings:Array<VSliceDiagnostic>, ?fallback:String):Dynamic {
		var stem = candidate;
		if (png != null && png.path != null)
			stem = Path.withoutExtension(StringTools.replace(png.path, '\\', '/'));
		var xml = resolveVSliceAsset(root, stem, '.xml');
		assets.push({source: png.path, destination: destinationBase + '.png', kind: 'health-icon', supported: true});
		if (xml.found)
			assets.push({source: xml.path, destination: destinationBase + '.xml', kind: 'health-icon', supported: true});
		return {destinationBase: destinationBase, xmlSupported: xml.found, png: png.path,
			xml: xml.path, fallback: fallback};
	}

	/** Normalize icon stems for punctuation-only aliases (`gf-doki`/`gfdoki`). */
	static function compactIconName(value:String):String {
		if (value == null)
			return '';
		var clean = value.toLowerCase();
		if (clean.startsWith('icon-'))
			clean = clean.substr(5);
		var output:Array<String> = [];
		for (i in 0...clean.length) {
			var c = clean.charAt(i);
			if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'))
				output.push(c);
		}
		return output.join('');
	}

	static function isNativeHealthIcon(value:String):Bool {
		if (value == null)
			return false;
		return switch (compactIconName(value)) {
			case 'gf' | 'bf' | 'dad' | 'nogf' | 'nogfpixel' | 'none' | 'null': true;
			default: false;
		};
	}

	/** Common V-Slice aliases emitted by converted speaker/pixel characters. */
	static function iconAliases(value:String):Array<String> {
		var result:Array<String> = [];
		if (value == null)
			return result;
		var compact = compactIconName(value);
		var variants:Array<String> = [compact];
		if (compact.indexOf('speaker') >= 0)
			variants.push(StringTools.replace(compact, 'speaker', ''));
		// Apply the speaker/punctuation reduction before the Sayori spelling
		// alias.  `sayo-speaker` therefore probes both `sayo` and the real donor
		// icon `sayori`, rather than the non-existent `sayorispeaker`.
		for (variant in variants.copy()) {
			if (variant.startsWith('sayo'))
				variants.push('sayori' + variant.substr(4));
			if (variant.startsWith('sayori'))
				variants.push('sayo' + variant.substr(6));
		}
		for (variant in variants)
			if (variant != compact)
			result.push(variant);
		var unique:Array<String> = [];
		for (alias in result)
			if (alias != '' && unique.indexOf(alias) < 0)
				unique.push(alias);
		return unique;
	}

	/**
		Return exact health-icon stems derived from a V-Slice character asset
		name.  These aliases are deliberately narrower than iconVariantName(),
		which is used only for a bounded discovery scan and can be ambiguous.
	*/
	static function iconAssetStemAliases(value:String):Array<String> {
		var result:Array<String> = [];
		var compact = compactIconName(value);
		if (compact == '')
			return result;
		for (prefix in ['silhouette', 'shadow']) {
			if (compact.startsWith(prefix) && compact.length > prefix.length) {
				var alias = compact.substr(prefix.length);
				if (result.indexOf(alias) < 0)
					result.push(alias);
			}
		}
		return result;
	}

	static function iconVariantName(value:String):String {
		var compact = compactIconName(value);
		for (token in ['silhouette', 'shadow'])
			if (compact.startsWith(token) && compact.length > token.length)
				compact = compact.substr(token.length);
		for (token in ['real', 'angry', 'gore', 'closet', 'new', 'be', 'bar', 'speaker'])
			compact = StringTools.replace(compact, token, '');
		if (compact.startsWith('sayo'))
			compact = 'sayori' + compact.substr(4);
		return compact;
	}

	static function iconNameMatches(actual:String, desired:String, isPixel:Bool):Int {
		var a = compactIconName(actual);
		var d = compactIconName(desired);
		if (a == '' || d == '')
			return -1;
		if (a == d)
			return 100;
		if (isPixel && a == d + 'pixel')
			return 95;
		if (isPixel && d.endsWith('pixel') && a == d.substr(0, d.length - 5))
			return 90;
		var av = iconVariantName(actual);
		var dv = iconVariantName(desired);
		if (av == dv)
			return isPixel && a.endsWith('pixel') ? 80 : 70;
		if (isPixel && av == dv + 'pixel')
			return 85;
		return -1;
	}

	#if sys
	/** Find a unique best icon PNG in V-Slice's icon-only directories. */
	static function findVSliceIconPng(root:String, iconId:String, isPixel:Bool):Dynamic {
		if (root == null || StringTools.trim(root) == '')
			return null;
		var folders = ['images/icons', 'shared/images/icons', 'images/freeplay/icons', 'shared/images/freeplay/icons'];
		var best:Dynamic = null;
		var bestScore = -1;
		var tied = false;
		for (relative in folders) {
			var folder = joinPath(root, relative);
			if (!FileSystem.isDirectory(folder)) {
				var insensitiveFolder = caseInsensitivePath(folder);
				if (insensitiveFolder == null || !FileSystem.isDirectory(insensitiveFolder))
					continue;
				folder = insensitiveFolder;
			}
			var entries:Array<String>;
			try {
				entries = FileSystem.readDirectory(folder);
			} catch (_:Dynamic) {
				continue;
			}
			entries.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
			for (entry in entries) {
				if (!entry.toLowerCase().endsWith('.png'))
					continue;
				var path = Path.join([folder, entry]);
				if (FileSystem.isDirectory(path))
					continue;
				var stem = Path.withoutExtension(entry);
				var score = iconNameMatches(stem, iconId, isPixel);
				if (score < 0)
					continue;
				if (score > bestScore) {
					bestScore = score;
					best = {png: {path: path, found: true}, stem: Path.withoutExtension(path),
						fallback: path};
					tied = false;
				} else if (score == bestScore && best != null
					&& StringTools.replace(best.png.path, '\\', '/').toLowerCase() != path.toLowerCase())
					tied = true;
			}
		}
		return tied ? null : best;
	}

	/** Resolve one path component at a time for donor trees made on Windows. */
	static function caseInsensitivePath(path:String):String {
		if (path == null || StringTools.trim(path) == '')
			return null;
		var clean = Path.normalize(StringTools.replace(path, '\\', '/'));
		if (FileSystem.exists(clean))
			return clean;
		var remaining = clean;
		var current = '';
		if (clean.startsWith('/')) {
			current = '/';
			remaining = clean.substr(1);
		} else if (clean.length > 1 && clean.charAt(1) == ':') {
			current = clean.substr(0, 2) + '/';
			remaining = clean.length > 3 ? clean.substr(3) : '';
		}
		for (part in remaining.split('/')) {
			if (part == '' || part == '.')
				continue;
			if (part == '..') {
				current = Path.normalize(Path.join([current == '' ? '.' : current, '..']));
				continue;
			}
			var parent = current == '' ? '.' : current;
			var found:String = null;
			var entries:Array<String>;
			try {
				entries = FileSystem.readDirectory(parent);
			} catch (_:Dynamic) {
				return null;
			}
			entries.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
			for (entry in entries)
				if (entry.toLowerCase() == part.toLowerCase()) {
					found = entry;
					break;
				}
			if (found == null)
				return null;
			current = current == '' ? found : Path.join([current, found]);
		}
		return FileSystem.exists(current) ? current : null;
	}
	#end

	static function resolveVSliceAsset(root:String, assetPath:String, extension:String):Dynamic {
		var clean = assetPath == null ? '' : StringTools.trim(StringTools.replace(assetPath, '\\', '/'));
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		// V-Slice logical asset ids use a library prefix (`shared:foo` or
		// `default:foo`) rather than a filesystem separator.  The donor export
		// stores the shared library below `shared/images`, so normalize the
		// authored namespace before applying the normal images/shared-images
		// probes.  Keeping the namespace in the relative path also prevents an
		// unrelated song-local `images/foo` from shadowing a shared asset.
		var namespaceSeparator = clean.indexOf(':');
		if (namespaceSeparator > 0) {
			var namespace = clean.substr(0, namespaceSeparator).toLowerCase();
			var namespacePath = clean.substr(namespaceSeparator + 1);
			if (namespace == 'shared')
				clean = 'shared/' + namespacePath;
			else if (namespace == 'default')
				// `default:` addresses the base images library in a V-Slice
				// export; the normal unprefixed branch probes images/.
				clean = namespacePath;
		}
		var candidates:Array<String> = [];
		if (isAbsolutePath(clean)) {
			candidates.push(clean + extension);
		} else {
			var lowerClean = clean.toLowerCase();
			var hasImagesPrefix = lowerClean.startsWith('images/') || lowerClean.startsWith('shared/images/');
			if (root != '') {
				if (lowerClean.startsWith('shared/images/')) {
					candidates.push(joinPath(root, clean + extension));
					candidates.push(joinPath(root, 'images/' + clean.substr('shared/images/'.length) + extension));
				} else if (lowerClean.startsWith('images/')) {
					candidates.push(joinPath(root, clean + extension));
					candidates.push(joinPath(root, 'shared/images/' + clean.substr('images/'.length) + extension));
				} else if (lowerClean.startsWith('shared/')) {
					candidates.push(joinPath(root, clean + extension));
					candidates.push(joinPath(root, 'shared/images/' + clean.substr('shared/'.length) + extension));
					candidates.push(joinPath(root, 'images/' + clean.substr('shared/'.length) + extension));
				} else {
					candidates.push(joinPath(root, 'images/' + clean + extension));
					candidates.push(joinPath(root, 'shared/images/' + clean + extension));
				}
			}
			if (hasImagesPrefix || lowerClean.startsWith('shared/'))
				candidates.push(clean + extension);
			else
				candidates.push('images/' + clean + extension);
		}
		#if sys
		for (candidate in candidates) {
			if (FileSystem.exists(candidate) && !FileSystem.isDirectory(candidate))
				return {path: candidate, found: true};
			var insensitive = caseInsensitivePath(candidate);
			if (insensitive != null && !FileSystem.isDirectory(insensitive))
				return {path: insensitive, found: true};
		}
		// V-Slice assetPath is logical rather than necessarily filesystem
		// relative.  A few shipped packs put a character atlas one directory
		// below that logical path (for example
		// `characters/BOYFRIEND` -> `characters/boyfriend/BOYFRIEND.astc`) or
		// pluralize a shared prop (`scanline` -> `credits/scanlines.png`).
		// Resolve only a unique exact basename (or a unique trailing-`s`
		// variant) inside the corresponding images tree.  This keeps the lookup
		// donor-backed and deterministic; ambiguous fuzzy matches stay genuine
		// missing-asset findings.
		var fallback = findVSliceAssetByBasename(root, clean, extension);
		if (fallback != null)
			return {path: fallback, found: true};
		#end
		var logical = candidates.length > 0 ? candidates[candidates.length - 1] : clean + extension;
		return {path: logical, found: root == ''};
	}

	/** Resolve V-Slice's shared/default logical audio namespaces. */
	static function resolveVSliceAudio(root:String, assetPath:String, extension:String):Dynamic {
		var clean = assetPath == null ? '' : StringTools.trim(StringTools.replace(assetPath, '\\', '/'));
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		var separator = clean.indexOf(':');
		if (separator > 0) {
			var namespace = clean.substr(0, separator).toLowerCase();
			var namespacePath = clean.substr(separator + 1);
			if (namespace == 'shared')
				clean = 'shared/' + namespacePath;
			else if (namespace == 'default')
				clean = namespacePath;
		}
		var candidates:Array<String> = [];
		var cleanExtension = extension == null ? '' : extension;
		var lower = clean.toLowerCase();
		if (root != '') {
			if (lower.startsWith('shared/')) {
				var sharedPath = clean.substr('shared/'.length);
				candidates.push(joinPath(root, 'shared/sounds/' + sharedPath + cleanExtension));
				candidates.push(joinPath(root, 'shared/music/' + sharedPath + cleanExtension));
				candidates.push(joinPath(root, 'sounds/' + sharedPath + cleanExtension));
				candidates.push(joinPath(root, 'music/' + sharedPath + cleanExtension));
			} else if (lower.startsWith('default/')) {
				var defaultPath = clean.substr('default/'.length);
				candidates.push(joinPath(root, 'sounds/' + defaultPath + cleanExtension));
				candidates.push(joinPath(root, 'music/' + defaultPath + cleanExtension));
			} else {
				candidates.push(joinPath(root, 'sounds/' + clean + cleanExtension));
				candidates.push(joinPath(root, 'music/' + clean + cleanExtension));
			}
		}
		#if sys
		for (candidate in candidates) {
			if (FileSystem.exists(candidate) && !FileSystem.isDirectory(candidate))
				return {path: candidate, found: true};
			var insensitive = caseInsensitivePath(candidate);
			if (insensitive != null && !FileSystem.isDirectory(insensitive))
				return {path: insensitive, found: true};
		}
		#end
		var logical = candidates.length > 0 ? candidates[0] : clean + cleanExtension;
		return {path: logical, found: root == ''};
	}

	#if sys
	static function findVSliceAssetByBasename(root:String, assetPath:String, extension:String):String {
		if (root == null || StringTools.trim(root) == '' || assetPath == null || StringTools.trim(assetPath) == '')
			return null;
		var clean = StringTools.replace(assetPath, '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		var slash = clean.lastIndexOf('/');
		var relativeFolder = slash >= 0 ? clean.substr(0, slash) : '';
		var requested = Path.withoutExtension(slash >= 0 ? clean.substr(slash + 1) : clean).toLowerCase();
		if (requested == '')
			return null;
		var names:Map<String, Int> = new Map<String, Int>();
		names.set(requested, 100);
		if (!requested.endsWith('s'))
			names.set(requested + 's', 90);
		else if (requested.length > 1)
			names.set(requested.substr(0, requested.length - 1), 90);
		var roots:Array<String> = [];
		for (imageRoot in [joinPath(root, 'images'), joinPath(root, 'shared/images')]) {
			var candidate = relativeFolder == '' ? imageRoot : joinPath(imageRoot, relativeFolder);
			var resolved = FileSystem.isDirectory(candidate) ? candidate : caseInsensitivePath(candidate);
			if (resolved != null && FileSystem.isDirectory(resolved) && roots.indexOf(resolved) < 0)
				roots.push(resolved);
		}
		// A bare logical name such as `scanline` is allowed to refer to a
		// shared image folder (credits/stage/etc.); nested logical paths remain
		// constrained to their authored folder above.
		if (roots.length == 0 && relativeFolder != '')
			return null;
		if (roots.length == 0)
			for (imageRoot in [joinPath(root, 'images'), joinPath(root, 'shared/images')]) {
				var resolved = FileSystem.isDirectory(imageRoot) ? imageRoot : caseInsensitivePath(imageRoot);
				if (resolved != null && FileSystem.isDirectory(resolved) && roots.indexOf(resolved) < 0)
					roots.push(resolved);
			}
		var matches:Array<Dynamic> = [];
		var budget:Array<Int> = [12000];
		for (folder in roots)
			collectVSliceAssetBasenameMatches(folder, extension.toLowerCase(), names, matches, budget, 0);
		var bestScore = -1;
		var bestPath:String = null;
		var tied = false;
		for (match in matches) {
			var score:Int = cast Reflect.field(match, 'score');
			var path:String = Std.string(Reflect.field(match, 'path'));
			if (score > bestScore) {
				bestScore = score;
				bestPath = path;
				tied = false;
			} else if (score == bestScore && bestPath != null
				&& StringTools.replace(bestPath, '\\', '/').toLowerCase()
					!= StringTools.replace(path, '\\', '/').toLowerCase())
				tied = true;
		}
		return tied ? null : bestPath;
	}

	static function collectVSliceAssetBasenameMatches(folder:String, extension:String, names:Map<String, Int>,
		matches:Array<Dynamic>, budget:Array<Int>, depth:Int):Void {
		if (folder == null || !FileSystem.isDirectory(folder) || budget[0] <= 0 || depth > 6)
			return;
		var entries:Array<String>;
		try {
			entries = FileSystem.readDirectory(folder);
		} catch (_:Dynamic) {
			return;
		}
		entries.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
		for (entry in entries) {
			if (budget[0]-- <= 0)
				return;
			var path = Path.join([folder, entry]);
			if (FileSystem.isDirectory(path)) {
				collectVSliceAssetBasenameMatches(path, extension, names, matches, budget, depth + 1);
				continue;
			}
			var lower = entry.toLowerCase();
			if (!lower.endsWith(extension))
				continue;
			var stem = lower.substr(0, lower.length - extension.length);
			if (names.exists(stem))
				matches.push({path: path, score: names.get(stem)});
		}
	}
	#end

	static function stageLayerForZ(zIndex:Float, characterZ:Map<String, Float>):String {
		var minimum = Math.POSITIVE_INFINITY;
		for (slot in ['gf', 'dad', 'bf'])
			if (characterZ.exists(slot) && characterZ.get(slot) < minimum)
				minimum = characterZ.get(slot);
		if (minimum != Math.POSITIVE_INFINITY && zIndex <= minimum)
			return 'BEHIND_ALL';
		var nearest:String = null;
		var nearestZ = Math.POSITIVE_INFINITY;
		for (slot in ['gf', 'dad', 'bf']) {
			if (!characterZ.exists(slot))
				continue;
			var value = characterZ.get(slot);
			if (value >= zIndex && value < nearestZ) {
				nearest = slot;
				nearestZ = value;
			}
		}
		if (nearest == null)
			return 'BEHIND_NONE';
		return switch (nearest) {
			case 'gf': 'BEHIND_GF';
			case 'dad': 'BEHIND_DAD';
			default: 'BEHIND_BF';
		};
	}

	static function defaultCharacterZ(slot:String):Float {
		return switch (slot) {
			case 'gf': 100;
			case 'dad': 200;
			default: 300;
		};
	}

	static function animationLoops(name:String, animation:Dynamic):Bool {
		return animationLoopValue(animation, false);
	}

	/**
		V-Slice 2.2 character exports use `frameRate`/`frameIndices`, older
		engine releases spell the same fields `rate`/`indices`, and older
		converter output (including the mounted TAKEOVER big-sayori
		definition) uses the equivalent `fps`/`indices` spellings.  Keep the
		alias at the importer boundary so every generated animation path uses
		the authored timing and frame selection instead of silently defaulting
		to 24 FPS or a prefix-wide animation.
	*/
	static function animationFrameRate(animation:Dynamic):Float {
		var value = field(animation, 'frameRate');
		if (value == null)
			value = field(animation, 'rate');
		if (value == null)
			value = field(animation, 'fps');
		var result = numberValue(value, 24);
		return result <= 0 ? 24 : result;
	}

	static function animationFrameIndices(animation:Dynamic):Dynamic {
		var value = field(animation, 'frameIndices');
		return value == null ? field(animation, 'indices') : value;
	}

	/** V-Slice uses `packer` today, but a few exports spell the same atlas
	 * family as `spriteSheetPacker`.  Keep the format test centralized so asset
	 * resolution and generated runtime code cannot disagree. */
	static function isSpriteSheetPackerType(value:String):Bool {
		if (value == null)
			return false;
		var normalized = StringTools.replace(StringTools.replace(value.toLowerCase(), '-', ''), '_', '');
		normalized = StringTools.replace(normalized, ' ', '');
		return normalized == 'packer' || normalized == 'spritesheetpacker';
	}

	static function atlasSupported(bundle:Dynamic, packer:Bool):Bool {
		if (bundle == null)
			return false;
		return packer ? Reflect.field(bundle, 'txtSupported') == true
			: Reflect.field(bundle, 'xmlSupported') == true;
	}

	static function animationLoopValue(animation:Dynamic, fallback:Bool):Bool {
		var loop = field(animation, 'loop');
		if (loop == null)
			loop = field(animation, 'looped');
		if (loop != null)
			return loop == true || (Std.isOfType(loop, String) && stringValue(loop, '').toLowerCase() == 'true');
		// AnimationData defaults to non-looping for both characters and props.
		// A dance name does not override the authored/default playback mode.
		return fallback;
	}

	static function numberPair(value:Dynamic):Null<Array<Float>> {
		if (!Std.isOfType(value, Array)) {
			// V-Slice Scale/Scroll fields accept a lone number meaning "uniform
			// on both axes" (wacky-world props ship "scale": 1.9 this way).
			var uniform = numberValue(value, Math.NaN);
			if (Math.isNaN(uniform))
				return null;
			return [uniform, uniform];
		}
		var values:Array<Dynamic> = cast value;
		if (values.length < 2)
			return null;
		var x = numberValue(values[0], Math.NaN);
		var y = numberValue(values[1], Math.NaN);
		if (Math.isNaN(x) || Math.isNaN(y))
			return null;
		return [x, y];
	}

	static function hscriptIntArray(value:Dynamic):String {
		if (!Std.isOfType(value, Array))
			return '[]';
		var output:Array<String> = [];
		for (entry in (cast value:Array<Dynamic>)) {
			var number = numberValue(entry, Math.NaN);
			if (Math.isNaN(number))
				continue;
			output.push(Std.string(Std.int(number)));
		}
		return '[' + output.join(', ') + ']';
	}

	static function hscriptQuote(value:String):String {
		if (value == null)
			return '';
		return StringTools.replace(StringTools.replace(StringTools.replace(value, '\\', '\\\\'), '"', '\\"'), '\n', '\\n');
	}

	/** Serialize JSON-shaped V-Slice metadata into a safe HScript literal. */
	static function hscriptDynamic(value:Dynamic):String {
		if (value == null)
			return 'null';
		if (Std.isOfType(value, String))
			return '"' + hscriptQuote(Std.string(value)) + '"';
		if (Std.isOfType(value, Bool))
			return value == true ? 'true' : 'false';
		if (Std.isOfType(value, Array)) {
			var values:Array<String> = [];
			for (entry in (cast value:Array<Dynamic>))
				values.push(hscriptDynamic(entry));
			return '[' + values.join(', ') + ']';
		}
		if (Std.isOfType(value, Int) || Std.isOfType(value, Float))
			return Std.string(value);
		var fields = safeFields(value);
		fields.sort(function(a, b) return Reflect.compare(a, b));
		var pairs:Array<String> = [];
		for (fieldName in fields) {
			var key = fieldName;
			var valid = key != '';
			for (i in 0...key.length) {
				var c = key.charAt(i);
				if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9' && i > 0) || c == '_')) {
					valid = false;
					break;
				}
			}
			var literalKey = valid ? key : '"' + hscriptQuote(key) + '"';
			pairs.push(literalKey + ': ' + hscriptDynamic(Reflect.field(value, fieldName)));
		}
		return '{' + pairs.join(', ') + '}';
	}

	static function formatNumber(value:Float):String {
		if (Math.isNaN(value))
			return '0';
		var rounded = Math.round(value);
		if (Math.abs(value - rounded) < EPSILON)
			return Std.string(rounded);
		return Std.string(value);
	}

	static function safeIdentifier(value:String):String {
		var input = value == null ? '' : value;
		var chars:Array<String> = [];
		for (i in 0...input.length) {
			var c = input.charAt(i).toLowerCase();
			if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')
				chars.push(c);
			else
				chars.push('_');
		}
		var output = chars.join('');
		if (output == '')
			output = 'asset';
		if (output.charAt(0) >= '0' && output.charAt(0) <= '9')
			output = '_' + output;
		return output;
	}

	static function stripAssetExtension(value:String):String {
		if (value == null)
			return '';
		var result = StringTools.replace(value.trim(), '\\', '/');
		for (extension in ['.png', '.xml', '.txt', '.astc', '.json'])
			if (result.toLowerCase().endsWith(extension))
				return result.substr(0, result.length - extension.length);
		return result;
	}

	static function normalizeSourceRoot(value:String):String {
		if (value == null)
			return '';
		var result = StringTools.replace(value.trim(), '\\', '/');
		while (result.length > 1 && result.endsWith('/'))
			result = result.substr(0, result.length - 1);
		return result;
	}

	/**
		Map V-Slice's stock note-style ids to the destination UI vocabulary.
		`funkin` and `pixel` are engine-defined styles in V-Slice; silently
		turning every `pixel` chart into `normal` changes note graphics and
		judgement scale. Custom V-Slice styles still use the native normal
		fallback for now, but remain an explicit diagnostic rather than being
		claimed as an exact visual import.
	*/
	static function nativeUiType(metadata:Dynamic, findings:Array<VSliceDiagnostic>, origin:String,
		difficulty:String):String {
		var playData = field(metadata, 'playData');
		var authored = stringValue(field(playData, 'noteStyle'), 'funkin');
		var normalized = authored.trim().toLowerCase();
		switch (normalized) {
			case '' | 'funkin' | 'normal' | 'default':
				return 'normal';
			case 'pixel' | 'pixelated':
				return 'pixel';
			default:
				findings.push(makeDiagnostic('info', 'unsupported-note-style',
					'V-Slice noteStyle "' + authored + '" has no exact native UI pack; using normal graphics.',
					origin, difficulty));
				return 'normal';
		}
	}

	/**
		Convert a V-Slice `data/notestyles/*.json` definition into the small
		descriptor understood by the native UI renderer.  V-Slice deliberately
		keeps note, receptor, sustain and splash atlases separate; flattening all
		four into the normal UI pack loses the authored graphics.  The conversion
		keeps those assets in one generated pack and writes a NoteKeys-compatible
		preset so the existing note construction path can use the authored
		prefixes.  It only returns mappings/text and never writes donor or
		destination files.
	*/
	public static function convertNoteStyle(data:Dynamic, sourceRoot:String, ?authoredName:String):VSliceNoteStyleConversion {
		var findings:Array<VSliceDiagnostic> = [];
		var root = normalizeSourceRoot(sourceRoot);
		var requested = authoredName == null || authoredName.trim() == ''
			? stringValue(field(data, 'name'), 'v-slice-style') : authoredName.trim();
		var nativeName = 'vslice-' + safeStem(requested);
		var assets:Array<VSliceAssetMapping> = [];
		var styleAssets = field(data, 'assets');
		var note = field(styleAssets, 'note');
		var strumline = field(styleAssets, 'noteStrumline');
		var hold = field(styleAssets, 'holdNote');
		var splash = field(styleAssets, 'noteSplash');
		var holdCover = field(styleAssets, 'holdNoteCover');
		var notePath = stringValue(field(note, 'assetPath'), '');
		var strumlinePath = stringValue(field(strumline, 'assetPath'), '');
		var holdPath = stringValue(field(hold, 'assetPath'), '');
		var splashPath = stringValue(field(splash, 'assetPath'), '');
		var noteBundle:Dynamic = null;
		var strumlineBundle:Dynamic = null;
		var holdBundle:Dynamic = null;
		var splashBundle:Dynamic = null;
		var nativeFallbacks:Array<String> = [];
		var trackNativeFallback = function(bundle:Dynamic, resource:Dynamic, kind:String):Void {
			if (bundle == null || field(bundle, 'native') != true || resource == null)
				return;
			var assetPath = stringValue(field(resource, 'assetPath'), '');
			var fallback = nativeNoteStyleFallback(assetPath, kind);
			if (fallback != '' && nativeFallbacks.indexOf(fallback) < 0)
				nativeFallbacks.push(fallback);
		};
		if (notePath == '') {
			findings.push(makeDiagnostic('warning', 'missing-note-style-asset',
				'V-Slice note style ' + requested + ' has no note assetPath.', root));
		} else {
			noteBundle = appendAssetBundle(root, notePath, 'NOTE_assets', 'note-style-note', assets, findings, true, '.xml');
		}
		if (strumlinePath == '') {
			findings.push(makeDiagnostic('warning', 'missing-note-style-asset',
				'V-Slice note style ' + requested + ' has no noteStrumline assetPath.', root));
		} else {
			strumlineBundle = appendAssetBundle(root, strumlinePath, 'strumline', 'note-style-strumline', assets, findings, true, '.xml');
		}
		if (holdPath != '')
			holdBundle = appendAssetBundle(root, holdPath, 'hold', 'note-style-hold', assets, findings, false, '.xml');
		if (splashPath != '') {
			splashBundle = appendNoteStyleImage(root, splash, 'noteSplashes', 'note-style-splash', assets, findings);
			trackNativeFallback(splashBundle, splash, 'note-style-splash');
		}

		// V-Slice keeps hold-cover graphics separate from the hold trail and
		// provides one Sparrow atlas per lane.  Preserve those exact atlases and
		// prefixes in the generated pack when the style enables the layer; a
		// disabled cover definition must not create a false missing-asset finding.
		var holdCoverEnabled = false;
		var holdCoverAssets:Array<String> = [];
		var holdCoverAssetXml:Array<Bool> = [];
		var holdCoverStartPrefixes:Array<String> = [];
		var holdCoverHoldPrefixes:Array<String> = [];
		var holdCoverEndPrefixes:Array<String> = [];
		var holdCoverData = holdCover == null ? null : field(holdCover, 'data');
		if (holdCoverData != null && field(holdCoverData, 'enabled') == true) {
			holdCoverEnabled = true;
			var coverDirections:Array<String> = ['left', 'down', 'up', 'right'];
			for (index in 0...coverDirections.length) {
				var direction = coverDirections[index];
				var cover = field(holdCoverData, direction);
				var coverPath = stringValue(field(cover, 'assetPath'), '');
				var destination = 'holdCover' + direction.substr(0, 1).toUpperCase() + direction.substr(1);
				var coverBundle:Dynamic = null;
				if (coverPath == '') {
					findings.push(makeDiagnostic('warning', 'missing-note-style-hold-cover',
						'V-Slice note style ' + requested + ' enables a hold cover for ' + direction
						+ ' but provides no assetPath.', root));
				} else {
					coverBundle = appendAssetBundle(root, coverPath, destination,
						'note-style-hold-cover', assets, findings, true, '.xml');
					if (coverBundle == null || field(coverBundle, 'xmlSupported') != true)
						findings.push(makeDiagnostic('warning', 'missing-note-style-hold-cover',
							'V-Slice note style ' + requested + ' hold cover for ' + direction
							+ ' has no usable Sparrow atlas for ' + coverPath + '.', root));
				}
				holdCoverAssets.push(coverBundle == null ? '' : destination);
				holdCoverAssetXml.push(coverBundle != null && field(coverBundle, 'xmlSupported') == true);
				holdCoverStartPrefixes.push(stringValue(field(field(cover, 'start'), 'prefix'), ''));
				holdCoverHoldPrefixes.push(stringValue(field(field(cover, 'hold'), 'prefix'), ''));
				holdCoverEndPrefixes.push(stringValue(field(field(cover, 'end'), 'prefix'), ''));
			}
		}

		var preset = buildNoteStylePreset(note, strumline, splash);
		var noteScale = positiveNumber(field(note, 'scale'), 0.7);
		var strumlineScale = positiveNumber(field(strumline, 'scale'), noteScale);
		var holdScale = positiveNumber(field(hold, 'scale'), noteScale);
		var splashScale = positiveNumber(field(splash, 'scale'), 1);
		var splashAlpha = numberValue(field(splash, 'alpha'), 0.6);
		if (splashAlpha < 0) splashAlpha = 0;
		if (splashAlpha > 1) splashAlpha = 1;
		var strumlineOffsets = numberPair(field(strumline, 'offsets'));
		var noteOffsets = numberPair(field(note, 'offsets'));
		var splashOffsets = numberPair(field(splash, 'offsets'));
		var isPixel = field(data, 'isPixel') == true || field(note, 'isPixel') == true;
		var noteXml = noteBundle != null && field(noteBundle, 'xmlSupported') == true;
		var strumlineXml = strumlineBundle != null && field(strumlineBundle, 'xmlSupported') == true;
		var holdXml = holdBundle != null && field(holdBundle, 'xmlSupported') == true;
		var splashXml = splashBundle != null && field(splashBundle, 'xmlSupported') == true;
		if (noteBundle != null && !noteXml)
			findings.push(makeDiagnostic('warning', 'missing-note-style-atlas',
				'V-Slice note style ' + requested + ' note asset has no Sparrow XML.', root));
		if (strumlineBundle != null && !strumlineXml)
			findings.push(makeDiagnostic('warning', 'missing-note-style-atlas',
				'V-Slice note style ' + requested + ' strumline asset has no Sparrow XML.', root));
		var splashData = field(splash, 'data');
		if (splashPath != '' && field(splashData, 'enabled') == false)
			findings.push(makeDiagnostic('info', 'note-style-splash-disabled',
				'V-Slice note style ' + requested + ' disables note splashes.', root));
		// The note-style document also owns countdown and popup resources.  Copy
		// every source-backed PNG into the generated UI pack so a style can use
		// its authored judgement/combo art when the donor actually ships it.  A
		// missing base/shared resource remains an explicit dependency finding and
		// falls back to the destination's normal art; it never makes the style
		// look complete by silently dropping the reference.
		var judgementResources:Array<String> = ['judgementSick', 'judgementGood', 'judgementBad', 'judgementShit'];
		var judgementDestinations:Array<String> = ['sick', 'good', 'bad', 'shit'];
		var judgementFound = 0;
		for (index in 0...judgementResources.length) {
			var judgement = field(styleAssets, judgementResources[index]);
			var judgementBundle = appendNoteStyleImage(root, judgement, judgementDestinations[index], 'note-style-judgement', assets, findings);
			trackNativeFallback(judgementBundle, judgement, 'note-style-judgement');
			if (judgementBundle != null && field(judgementBundle, 'native') != true)
				judgementFound++;
		}
		var comboFound = 0;
		for (index in 0...10) {
			var combo = field(styleAssets, 'comboNumber' + index);
			var comboBundle = appendNoteStyleImage(root, combo, 'num' + index, 'note-style-combo', assets, findings);
			trackNativeFallback(comboBundle, combo, 'note-style-combo');
			if (comboBundle != null && field(comboBundle, 'native') != true)
				comboFound++;
		}
		var countdownResources:Array<String> = ['countdownTwo', 'countdownOne', 'countdownGo'];
		var countdownDestinations:Array<String> = ['ready', 'set', 'go'];
		var countdownFound = 0;
		for (index in 0...countdownResources.length) {
			var countdown = field(styleAssets, countdownResources[index]);
			if (appendNoteStyleImage(root, countdown, countdownDestinations[index], 'note-style-countdown', assets, findings) != null)
				countdownFound++;
		}
		var countdownAudioResources:Array<String> = ['countdownThree', 'countdownTwo', 'countdownOne', 'countdownGo'];
		var countdownAudioDestinations:Array<String> = ['intro3.ogg', 'intro2.ogg', 'intro1.ogg', 'introGo.ogg'];
		var countdownAudioFound = 0;
		for (index in 0...countdownAudioResources.length) {
			var countdownAudio = field(styleAssets, countdownAudioResources[index]);
			if (appendNoteStyleAudio(root, countdownAudio, countdownAudioDestinations[index],
				'note-style-countdown-audio', assets, findings) != null)
				countdownAudioFound++;
		}
		var registryBuiltInJudgement = judgementFound == judgementResources.length && comboFound == 10;
		var judgementScale = positiveNumber(field(field(styleAssets, 'judgementSick'), 'scale'), 0.7);
		var comboScale = positiveNumber(field(field(styleAssets, 'comboNumber0'), 'scale'), 0.5);

		var registryEntry:Dynamic = {
			isPixel: isPixel,
			builtInJudgement: registryBuiltInJudgement,
			uses: nativeName,
			vSliceAlias: requested,
				noteAsset: 'NOTE_assets',
				strumlineAsset: 'strumline',
				holdAsset: holdBundle == null ? '' : 'hold',
				holdAssetXml: holdXml,
				noteSplashAsset: splashBundle == null || field(splashBundle, 'native') == true ? '' : 'noteSplashes',
			noteSplashAssetXml: splashXml,
			noteScale: noteScale,
			strumlineScale: strumlineScale,
			holdScale: holdScale,
			holdFramesPerLane: holdBundle == null ? 1 : 2,
			splashScale: splashScale,
			splashAlpha: splashAlpha,
			judgementScale: judgementScale,
			comboScale: comboScale,
			strumlineOffsetX: strumlineOffsets == null ? 0 : strumlineOffsets[0],
			strumlineOffsetY: strumlineOffsets == null ? 0 : strumlineOffsets[1],
			noteOffsetX: noteOffsets == null ? 0 : noteOffsets[0],
			noteOffsetY: noteOffsets == null ? 0 : noteOffsets[1],
			holdOffsetX: numberPair(field(hold, 'offsets')) == null ? 0 : numberPair(field(hold, 'offsets'))[0],
			holdOffsetY: numberPair(field(hold, 'offsets')) == null ? 0 : numberPair(field(hold, 'offsets'))[1],
			holdCoverEnabled: holdCoverEnabled && holdCoverAssets.length == 4
				&& holdCoverAssets.indexOf('') < 0 && holdCoverAssetXml.length == 4
				&& holdCoverAssetXml.indexOf(false) < 0,
			holdCoverAssets: holdCoverAssets,
			holdCoverAssetXml: holdCoverAssetXml,
			holdCoverStartPrefixes: holdCoverStartPrefixes,
			holdCoverHoldPrefixes: holdCoverHoldPrefixes,
			holdCoverEndPrefixes: holdCoverEndPrefixes,
			holdCoverScale: positiveNumber(field(holdCover, 'scale'), 1),
			holdCoverOffsetX: numberPair(field(holdCover, 'offsets')) == null ? 0 : numberPair(field(holdCover, 'offsets'))[0],
			holdCoverOffsetY: numberPair(field(holdCover, 'offsets')) == null ? 0 : numberPair(field(holdCover, 'offsets'))[1],
			splashOffsetX: splashOffsets == null ? 0 : splashOffsets[0],
			splashOffsetY: splashOffsets == null ? 0 : splashOffsets[1]
		};
		if (countdownFound < countdownResources.length)
			findings.push(makeDiagnostic('info', 'note-style-countdown-fallback',
				'V-Slice note style ' + requested + ' references countdown images that are not packaged by the donor; the destination-native countdown fallback remains active.', root));
		if (countdownAudioFound < countdownAudioResources.length)
			findings.push(makeDiagnostic('info', 'note-style-countdown-audio-fallback',
				'V-Slice note style ' + requested + ' references V-Slice base/shared countdown audio that is not packaged by the donor; the destination-native countdown audio fallback remains active.', root));
		if (nativeFallbacks.length > 0)
			findings.push(makeDiagnostic('info', 'note-style-native-fallback',
				'V-Slice note style ' + requested + ' references ' + nativeFallbacks.length
				+ ' stock note-style image resource(s) absent from the donor; destination-native UI fallbacks remain active.', root));
		var supported = noteBundle != null && strumlineBundle != null && noteXml && strumlineXml;
		if (!supported)
			findings.push(makeDiagnostic('warning', 'unsupported-note-style',
				'V-Slice note style "' + requested + '" is missing a usable note or strumline atlas; using normal graphics.', root));
		return {
			name: nativeName,
			authoredName: requested,
			registryEntry: registryEntry,
			preset: preset,
			assets: assets,
			diagnostics: deduplicateDiagnostics(findings),
			supported: supported
		};
	}

	/**
		Resolve stock V-Slice popup/splash ids to assets already owned by the
		destination engine.  V-Slice note styles frequently retain references to
		base/shared resources which are intentionally omitted from a mod export.
		Those references are not donor omissions: the native Judgement,
		PlayState combo, and NoteSplash routes already provide the exact `funkin`
		fallbacks.  Keep custom paths on the normal source-backed path so a real
		missing asset remains actionable.
	*/
	static function nativeNoteStyleFallback(assetPath:String, kind:String):String {
		if (assetPath == null || kind == null)
			return '';
		var normalized = stripAssetExtension(StringTools.replace(assetPath.trim(), '\\', '/')).toLowerCase();
		var separator = normalized.indexOf(':');
		if (separator <= 0)
			return '';
		var namespace = normalized.substr(0, separator);
		if (namespace != 'shared' && namespace != 'default')
			return '';
		var logical = normalized.substr(separator + 1);
		while (logical.startsWith('./'))
			logical = logical.substr(2);
		if (kind == 'note-style-splash') {
			if (logical == 'notesplashes' || logical == 'ui/notesplashes')
				return 'assets/images/custom_ui/ui_packs/normal/noteSplashes.png';
			return '';
		}
		var popupPrefix = 'ui/popup/funkin/';
		if (!logical.startsWith(popupPrefix))
			return '';
		var stem = logical.substr(popupPrefix.length);
		if (kind == 'note-style-judgement') {
			return switch (stem) {
				case 'sick' | 'good' | 'bad' | 'shit':
					'assets/images/judgements/normal/' + stem + '.png';
				default: '';
			};
		}
		if (kind == 'note-style-combo' && stem.length == 4 && stem.startsWith('num')) {
			var digit = stem.charCodeAt(3);
			if (digit >= '0'.code && digit <= '9'.code)
				return 'assets/images/num' + stem.charAt(3) + '.png';
		}
		return '';
	}

	/** Copy one optional image resource from the authored style document. */
	static function appendNoteStyleImage(root:String, resource:Dynamic, destination:String,
		kind:String, assets:Array<VSliceAssetMapping>, findings:Array<VSliceDiagnostic>):Dynamic {
		if (resource == null)
			return null;
		var assetPath = stringValue(field(resource, 'assetPath'), '');
		if (assetPath == '')
			return null;
		var nativeFallback = nativeNoteStyleFallback(assetPath, kind);
		if (nativeFallback != '') {
			// Preserve a donor-supplied PNG or ASTC resource even when it uses a
			// stock logical id.  The native fallback is only valid when the
			// source library truly omitted the resource.
			var sourcePng = resolveVSliceAsset(root, assetPath, '.png');
			var sourceAstc = resolveVSliceAsset(root, assetPath, '.astc');
			if (!sourcePng.found && !sourceAstc.found)
				return {native: true, fallback: nativeFallback};
		}
		// V-Slice's stock countdown images live in the base/shared library and
		// are intentionally omitted from many mod exports.  The native pack has
		// an exact destination fallback, so do not report those donor-optional
		// references as missing source assets.  A custom countdown path still
		// follows the normal warning path below.
		if (kind == 'note-style-countdown' && isVSliceBaseCountdownImage(assetPath)) {
			var baseImage = resolveVSliceAsset(root, assetPath, '.png');
			if (!baseImage.found)
				return null;
		}
		return appendAssetBundle(root, assetPath, destination, kind, assets, findings,
			kind == 'note-style-splash', '.xml');
	}

	/** Copy a V-Slice countdown sound when the donor carries the logical file. */
	static function appendNoteStyleAudio(root:String, resource:Dynamic, destination:String,
		kind:String, assets:Array<VSliceAssetMapping>, findings:Array<VSliceDiagnostic>):Dynamic {
		if (resource == null)
			return null;
		var assetPath = stringValue(field(field(resource, 'data'), 'audioPath'), '');
		if (assetPath == '')
			return null;
		var audio = resolveVSliceAudio(root, assetPath, '.ogg');
		if (!audio.found) {
			// These are V-Slice's base-game countdown sounds, not assets owned by
			// the mounted mod.  PlayState already resolves them through the native
			// UI-pack fallback, so retain only the aggregate fallback diagnostic.
			if (isVSliceBaseCountdownAudio(assetPath))
				return null;
			findings.push(makeDiagnostic('warning', 'missing-note-style-audio',
				'V-Slice ' + kind + ' could not find authored audio ' + assetPath + '.', root));
			return null;
		}
		assets.push({source: audio.path, destination: destination, kind: kind, supported: true});
		return audio;
	}

	static function isVSliceBaseCountdownImage(assetPath:String):Bool {
		return isVSliceBaseLibraryResource(assetPath, 'ui/countdown/');
	}

	static function isVSliceBaseCountdownAudio(assetPath:String):Bool {
		return isVSliceBaseLibraryResource(assetPath, 'gameplay/countdown/');
	}

	/** A missing resource in a V-Slice base/shared library uses the native pack fallback. */
	static function isVSliceBaseLibraryResource(assetPath:String, resourcePrefix:String):Bool {
		if (assetPath == null)
			return false;
		var normalized = StringTools.replace(assetPath.trim(), '\\', '/').toLowerCase();
		var separator = normalized.indexOf(':');
		if (separator <= 0)
			return false;
		var namespace = normalized.substr(0, separator);
		if (namespace != 'shared' && namespace != 'default')
			return false;
		var logicalPath = normalized.substr(separator + 1);
		while (logicalPath.startsWith('./'))
			logicalPath = logicalPath.substr(2);
		if (!logicalPath.startsWith(resourcePrefix)
			|| logicalPath.substr(resourcePrefix.length) == '')
			return false;
		for (segment in logicalPath.split('/'))
			if (segment == '..')
				return false;
		return true;
	}

	static function buildNoteStylePreset(note:Dynamic, strumline:Dynamic, splash:Dynamic):Dynamic {
		var definitions:Dynamic = {};
		var directions:Array<String> = ['left', 'down', 'up', 'right'];
		var sings:Array<String> = ['singLEFT', 'singDOWN', 'singUP', 'singRIGHT'];
		for (index in 0...directions.length) {
			var direction = directions[index];
			var noteData = field(field(note, 'data'), direction);
			var strumData = field(field(strumline, 'data'), direction + 'Static');
			var pressData = field(field(strumline, 'data'), direction + 'Press');
			var confirmData = field(field(strumline, 'data'), direction + 'Confirm');
			var authoredNote = stringValue(field(noteData, 'prefix'), '');
			// Native Note adds the frame-zero suffix to the note name. V-Slice
			// style definitions conventionally include that suffix in `prefix`.
			if (authoredNote.endsWith('0'))
				authoredNote = authoredNote.substr(0, authoredNote.length - 1);
			if (authoredNote == '')
				authoredNote = ['purple', 'blue', 'green', 'red'][index];
			var splashPrefixes:Array<String> = [];
			var splashValues = field(field(splash, 'data'), direction + 'Splashes');
			if (Std.isOfType(splashValues, Array))
				for (entry in (cast splashValues:Array<Dynamic>)) {
					var prefix = stringValue(field(entry, 'prefix'), '');
					if (prefix != '') splashPrefixes.push(prefix);
				}
			Reflect.setField(definitions, direction, {
				note: authoredNote,
				idle: stringValue(field(strumData, 'prefix'), 'arrow' + direction.toUpperCase()),
				pressed: stringValue(field(pressData, 'prefix'), direction + ' press'),
				confirm: stringValue(field(confirmData, 'prefix'), direction + ' confirm'),
				confirmHold: stringValue(field(field(field(strumline, 'data'), direction + 'ConfirmHold'), 'prefix'), ''),
				sing: sings[index],
				splashes: splashPrefixes
			});
		}
		return {definitions: definitions, key4: directions};
	}

	static function positiveNumber(value:Dynamic, fallback:Float):Float {
		var result = numberValue(value, fallback);
		return result > 0 ? result : fallback;
	}

	static function joinPath(root:String, relative:String):String {
		if (root == null || root == '')
			return StringTools.replace(relative, '\\', '/');
		return normalizeSourceRoot(root) + '/' + StringTools.replace(relative, '\\', '/');
	}

	static function isAbsolutePath(value:String):Bool {
		return value != null && (value.startsWith('/') || (value.length > 1 && value.charAt(1) == ':'));
	}

	/**
		Convert just one difficulty.  A missing requested difficulty is still
		represented by an empty native chart and a diagnostic, which lets a scan
		report the issue instead of silently importing a different difficulty.
	*/
	public static function convertDifficulty(metadata:Dynamic, chart:Dynamic, ?songName:String,
		?difficulty:String, ?sourcePath:String, ?noteDefinitions:Array<Dynamic>,
		?noteKindIndexes:Map<String, Int>,
		?noteStyleConversions:Array<VSliceNoteKindStyleConversion>):VSliceConvertedChart {
		var findings:Array<VSliceDiagnostic> = [];
		if (noteDefinitions == null)
			noteDefinitions = [];
		if (noteKindIndexes == null) {
			noteKindIndexes = new Map<String, Int>();
			for (i in 0...noteDefinitions.length) {
				var existing = noteDefinitions[i];
				var existingKind = stringValue(field(existing, 'sourceKind'), '');
				if (existingKind != '')
					noteKindIndexes.set(existingKind.toLowerCase().trim(), i);
			}
		}
		if (noteStyleConversions == null)
			noteStyleConversions = [];
		var origin = sourcePath == null ? '' : sourcePath;
		var name = songName == null || songName.trim() == '' ? stringValue(field(metadata, 'songName'), 'v-slice-song') : songName;
		if (name.trim() == '')
			name = 'v-slice-song';
		var diff = difficulty == null || difficulty.trim() == '' ? DEFAULT_DIFFICULTY : difficulty.trim();
		var notesByDifficulty = field(chart, 'notes');
		var noteList:Dynamic = notesByDifficulty == null ? null : field(notesByDifficulty, diff);
		if (noteList == null && notesByDifficulty != null) {
			// V-Slice difficulty keys are case-sensitive in files, but user-facing
			// selection is commonly case-insensitive.
			for (candidate in safeFields(notesByDifficulty)) {
				if (candidate.toLowerCase() == diff.toLowerCase()) {
					diff = candidate;
					noteList = field(notesByDifficulty, candidate);
					break;
				}
			}
		}
		if (noteList == null) {
			findings.push(makeDiagnostic('warning', 'missing-difficulty',
				'No notes were found for V-Slice difficulty ' + diff + '.', origin, diff));
			noteList = [];
		}
		if (!Std.isOfType(noteList, Array)) {
			findings.push(makeDiagnostic('error', 'invalid-notes',
				'V-Slice difficulty ' + diff + ' does not contain a note array.', origin, diff));
			noteList = [];
		}

		var changes = readTimeChanges(metadata, chart, findings, origin, diff);
		var playData = field(metadata, 'playData');
		var characters = field(playData, 'characters');
		var player = stringValue(field(characters, 'player'), 'bf');
		var opponent = stringValue(field(characters, 'opponent'), 'dad');
		// V-Slice calls the girlfriend slot `girlfriend`; retain the authored
		// character instead of silently replacing it with the native default. An
		// explicitly blank slot means that the stage has no girlfriend, while a
		// completely absent field retains the legacy native `gf` default.
		var girlfriendValue:Dynamic = field(characters, 'girlfriend');
		if (girlfriendValue == null)
			girlfriendValue = field(characters, 'gf');
		// V-Slice renders no girlfriend unless the playData explicitly names one
		// (fantasy-girl-01 omits the key and its reference video has no gf), so
		// both an absent and a blank field mean no-gf — never the native default.
		var girlfriend = girlfriendValue == null
			? 'no-gf'
			: (StringTools.trim(Std.string(girlfriendValue)) == '' ? 'no-gf' : Std.string(girlfriendValue).trim());
		// V-Slice folds the standard Erect stage variant into the stage id
		// (`schoolEvilErect`), while native stage scripts select that variant via
		// chart `stageID`. Resolve the shared engine vocabulary here so every
		// converted difficulty gets the correct native stage and variant without
		// changing the donor metadata/chart.
		var authoredStage = stringValue(field(playData, 'stage'), 'stage');
		var stageResolution = EngineCompat.resolveStageResolution(authoredStage);
		var stage = stageResolution == null || stageResolution.nativeName == null
			? authoredStage : stageResolution.nativeName;
		var stageID = stageResolution == null ? 0 : stageResolution.stageID;
		var uiType = nativeUiType(metadata, findings, origin, diff);
		var songArtist = stringValue(field(metadata, 'artist'), stringValue(field(metadata, 'songArtist'), ''));
		var album = stringValue(field(playData, 'album'), stringValue(field(metadata, 'album'), ''));
		var baseBpm:Float = changes.length == 0 ? numberValue(field(chart, 'bpm'), DEFAULT_BPM) : changes[0].bpm;
		if (baseBpm <= 0) {
			baseBpm = DEFAULT_BPM;
			findings.push(makeDiagnostic('warning', 'invalid-bpm',
				'V-Slice did not provide a positive BPM; using ' + DEFAULT_BPM + '.', origin, diff));
		}
		var speed = readScrollSpeed(chart, diff);
		var needsVoices = hasVocalMetadata(characters);
		var convertedEvents = convertEvents(chart, findings, origin, diff);
		var characterIds = [player, opponent, girlfriend];
		appendRawEventCharacterReferences(chart, characterIds);
		appendEventCharacterReferences(convertedEvents, characterIds);

		var noteRows:Array<Dynamic> = [];
		// V-Slice charts can author additional strumlines beyond the two that its
		// gameplay state routes to receptors. Keep those source rows in the chart
		// envelope for editor round-trips, but never add them to native `notes`.
		var unroutedNotes:Array<Dynamic> = [];
		var maxTime:Float = 0;
		for (rawNote in (cast noteList:Array<Dynamic>)) {
			if (rawNote == null)
				continue;
			var laneFloat = numberValue(field(rawNote, 'd'), Math.NaN);
			if (!Math.isNaN(laneFloat) && laneFloat == Math.floor(laneFloat)
				&& (laneFloat < 0 || laneFloat > 7)) {
				// Deep-copy the JSON payload so later native conversion/editor edits
				// cannot mutate the authored row. Array order is the source note order.
				unroutedNotes.push(Json.parse(Json.stringify(rawNote)));
			}
			var time = numberValue(field(rawNote, 't'), Math.NaN);
			if (Math.isNaN(time)) {
				findings.push(makeDiagnostic('warning', 'invalid-note-time',
					'A V-Slice note has no numeric t (milliseconds) and was skipped.', origin, diff));
				continue;
			}
			if (time < 0) {
				findings.push(makeDiagnostic('warning', 'negative-note-time',
					'A V-Slice note occurred before zero and was clamped to zero.', origin, diff));
				time = 0;
			}
			if (Math.isNaN(laneFloat) || laneFloat != Math.floor(laneFloat)) {
				findings.push(makeDiagnostic('warning', 'invalid-note-lane',
					'A V-Slice note has no integer d lane and was skipped.', origin, diff));
				continue;
			}
			var lane = Std.int(laneFloat);
			if (lane < 0 || lane > 7) {
				findings.push(makeDiagnostic('warning', 'unsupported-note-lane',
					'V-Slice lane ' + lane + ' is outside the native 0-7 lane range and was skipped.', origin, diff));
				continue;
			}
			var sustain = numberValue(field(rawNote, 'l'), 0);
			if (Math.isNaN(sustain) || sustain < 0)
				sustain = 0;
			var kind = noteKind(rawNote, findings, origin, diff, noteDefinitions, noteKindIndexes,
				name, characterIds, noteStyleConversions);
			// Native custom notes use a 4-key block starting at NOTE_AMOUNT * 10.
			// Keep the authored lane inside that block so the existing PlayState
			// side test (`noteData % (NOTE_AMOUNT * 2)`) still distinguishes player
			// and opponent notes without changing the chart's lane or section data.
			var nativeLane = kind.customIndex < 0 ? lane : lane + (kind.customIndex + 5) * 8;
			var row:Array<Dynamic> = [time, nativeLane, sustain];
			if (kind.alt > 0)
				row.push(kind.alt);
			noteRows.push({time: time, row: row, sustainEnd: time + sustain});
			if (time + sustain > maxTime)
				maxTime = time + sustain;
		}

		findings = deduplicateDiagnostics(findings);
		for (event in convertedEvents) {
			var eventTime:Float = event[0];
			if (eventTime > maxTime)
				maxTime = eventTime;
		}

		var sections = buildSections(noteRows, maxTime, changes);
		var events = convertedEvents;
		var songData:Dynamic = {
			song: name,
			notes: sections,
			bpm: baseBpm,
			needsVoices: needsVoices,
			speed: speed,
			player1: player,
			player2: opponent,
			gf: girlfriend,
			stage: stage,
			stageID: stageID,
			uiType: uiType,
			cutsceneType: 'none',
			isMoody: false,
			isSpooky: false,
			isHey: false,
			isCheer: false,
			preferredNoteAmount: 4,
			mania: 0,
			forceJudgements: false,
			convertMineToNuke: false,
			vSliceUnroutedNotes: unroutedNotes
		};
			if (songArtist != '')
				songData.songArtist = songArtist;
			if (album != '')
				songData.album = album;
			var vocalStems = vocalStemMetadata(metadata);
			if (vocalStems.length > 0)
				songData.vocalStems = vocalStems;
			if (events.length > 0)
				songData.events = events;

		return {
			difficulty: diff,
			fileName: nativeFileName(name, diff),
			chart: {song: songData},
			diagnostics: findings
		};
	}

	/** Suggested native filename for a converted V-Slice difficulty. */
	public static function nativeFileName(songName:String, difficulty:String):String {
		var safeSong = safeStem(songName);
		var safeDifficulty = safeStem(difficulty);
		return safeDifficulty.toLowerCase() == DEFAULT_DIFFICULTY ? safeSong + '.json' : safeSong + '-' + safeDifficulty + '.json';
	}

	/**
		Return the authored V-Slice vocal slots in stable order.  The metadata
		stores character ids rather than paths, so conversion emits a deterministic
		native filename which the importer may later replace with the exact source
		extension it found.  Keeping the id and role in the chart lets PlayState
		load a split-stem song without consulting the donor metadata at runtime.
	*/
	public static function vocalStemMetadata(metadata:Dynamic):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		var characters = field(field(metadata, 'playData'), 'characters');
		appendVocalMetadataValues(result, seen, field(characters, 'opponentVocals'), 'opponent');
		appendVocalMetadataValues(result, seen, field(characters, 'playerVocals'), 'player');
		appendVocalMetadataValues(result, seen, field(characters, 'vocals'), 'shared');
		return result;
	}

	/**
		Return the variation ids declared by a V-Slice song's base metadata.
		Those ids name sibling `-metadata-<id>` / `-chart-<id>` pairs.  The
		importer uses them to expose each authored variation without treating a
		missing sibling file as another difficulty or silently substituting the
		base chart.
	*/
	public static function songVariationReferences(metadata:Dynamic):Array<String> {
		var result:Array<String> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		var values = field(field(metadata, 'playData'), 'songVariations');
		if (!Std.isOfType(values, Array))
			return result;
		for (entry in (cast values:Array<Dynamic>)) {
			var value = stringValue(entry, '').trim();
			var key = value.toLowerCase();
			if (value != '' && !seen.exists(key)) {
				seen.set(key, true);
				result.push(value);
			}
		}
		return result;
	}

	/**
		V-Slice can spell vocal files explicitly with `playerVocals` and
		`opponentVocals`, or rely on the song's character ids as stem ids.  Keep
		that fallback role-aware so the package importer can match `voices-<id>`
		and suffixed ids such as `voices-yuri-alt` to the selected variation.
	*/
	public static function vocalStemReferences(metadata:Dynamic):Array<Dynamic> {
		var authored = vocalStemMetadata(metadata);
		if (authored.length > 0)
			return authored;

		var result:Array<Dynamic> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		var characters = field(field(metadata, 'playData'), 'characters');
		appendVocalMetadataValues(result, seen, field(characters, 'opponent'), 'opponent');
		appendVocalMetadataValues(result, seen, field(characters, 'player'), 'player');
		return result;
	}

	/** Deterministic destination basename for a V-Slice stem id. */
	public static function nativeVocalStemFile(id:String, ?extension:String):String {
		var ext = extension == null || StringTools.trim(extension) == '' ? '.ogg' : StringTools.trim(extension).toLowerCase();
		if (!ext.startsWith('.'))
			ext = '.' + ext;
		return 'Voices-' + safeStem(id) + ext;
	}

	static function appendVocalMetadataValues(result:Array<Dynamic>, seen:Map<String, Bool>, value:Dynamic, role:String):Void {
		if (value == null)
			return;
		if (Std.isOfType(value, Array)) {
			for (entry in (cast value:Array<Dynamic>))
				appendVocalMetadataValues(result, seen, entry, role);
			return;
		}
		var id = Std.isOfType(value, String) ? stringValue(value, '') : stringValue(field(value, 'id'), '');
		if (id == '' && !Std.isOfType(value, String))
			id = stringValue(field(value, 'name'), stringValue(field(value, 'character'), ''));
		if (id == '')
			return;
		var key = id.toLowerCase().trim();
		if (seen.exists(key))
			return;
		seen.set(key, true);
		result.push({
			id: id,
			role: role,
			file: nativeVocalStemFile(id)
		});
	}

	/**
		Inspect an already enumerated asset list.  This is deliberately path-only:
		the importer can use its existing non-blocking scanner and feed paths here.
	*/
	public static function diagnoseAssets(paths:Array<String>, ?metadata:Dynamic):VSliceAssetDiagnostics {
		var result:VSliceAssetDiagnostics = {diagnostics: [], extraVocalStems: [], astcOnly: []};
		if (paths == null)
			paths = [];
		var normalized = new Map<String, String>();
		for (path in paths) {
			if (path == null)
				continue;
			var value = StringTools.replace(path, '\\', '/');
			var key = value.toLowerCase();
			normalized.set(key, value);
		}
		for (path in paths) {
			if (path == null)
				continue;
			var normalizedPath = StringTools.replace(path, '\\', '/');
			var lower = normalizedPath.toLowerCase();
			if (lower.endsWith('.astc')) {
				var base = lower.substr(0, lower.length - 5);
				if (!normalized.exists(base + '.png')) {
					var header:VSliceAstcHeader = null;
					var decoderAvailable = false;
					#if sys
					if (FileSystem.exists(path) && !FileSystem.isDirectory(path)) {
						header = VSliceAstcAdapter.inspectFile(path);
						if (header.valid && header.payloadMatches)
							decoderAvailable = VSliceAstcAdapter.probe().available;
					}
					#end
					if (decoderAvailable) {
						result.diagnostics.push(makeDiagnostic('info', 'astc-decoder-ready',
							'V-Slice ASTC asset will be decoded to PNG during import: ' + normalizedPath, normalizedPath));
					} else {
						result.astcOnly.push(normalizedPath);
						result.diagnostics.push(makeDiagnostic('warning', 'astc-only',
							VSliceAstcAdapter.diagnostic(normalizedPath, header), normalizedPath));
					}
				}
			}
				if (isVocalStem(lower) && !lower.endsWith('/voices.ogg') && !lower.endsWith('/voices.wav') && !lower.endsWith('/voices.mp3')) {
					result.extraVocalStems.push(normalizedPath);
					result.diagnostics.push(makeDiagnostic('info', 'extra-vocal-stem',
						'V-Slice split vocal stem will be copied and played with the other native vocal tracks: ' + normalizedPath, normalizedPath));
				}
		}
		if (metadata != null) {
			var characters = field(field(metadata, 'playData'), 'characters');
			var vocalCount = vocalArrayCount(characters);
			if (vocalCount > 1 && result.extraVocalStems.length == 0) {
				result.diagnostics.push(makeDiagnostic('info', 'extra-vocal-stems',
					'Metadata lists multiple vocal stems; all discovered stems will be loaded in lockstep.', ''));
			}
		}
		return result;
	}

	/** Read and inspect all files below a root on native desktop targets. */
	#if sys
	public static function diagnoseAssetRoot(root:String, ?metadata:Dynamic):VSliceAssetDiagnostics {
		var paths:Array<String> = [];
		collectFiles(root, root, paths);
		return diagnoseAssets(paths, metadata);
	}
	#end

	static function difficultyNames(metadata:Dynamic, chart:Dynamic):Array<String> {
		var result:Array<String> = [];
		var playData = field(metadata, 'playData');
		var listed = field(playData, 'difficulties');
		if (Std.isOfType(listed, Array)) {
			for (value in (cast listed:Array<Dynamic>)) {
				var name = stringValue(value, '');
				if (name != '' && result.indexOf(name) < 0)
					result.push(name);
			}
		}
		// Metadata is the authoritative list of difficulties for this chart pair.
		// Variation charts can contain empty placeholder keys for other variants
		// (for example, an alt chart with `normal: []` beside populated `alt`
		// notes). Importing the union makes that placeholder a selectable empty
		// chart and lets the sibling variant leak into this pair's difficulty set.
		if (result.length > 0)
			return result;
		var noteMap = field(chart, 'notes');
		if (noteMap != null) {
			for (name in safeFields(noteMap)) {
				if (result.indexOf(name) < 0)
					result.push(name);
			}
		}
		return result;
	}

	static function readScrollSpeed(chart:Dynamic, difficulty:String):Float {
		var speeds = field(chart, 'scrollSpeed');
		var value:Dynamic = speeds == null ? null : field(speeds, difficulty);
		if (value == null && speeds != null) {
			for (candidate in safeFields(speeds)) {
				if (candidate.toLowerCase() == difficulty.toLowerCase()) {
					value = field(speeds, candidate);
					break;
				}
			}
		}
		if (value == null && speeds != null) {
			// A V-Slice chart normally stores a difficulty map, but a few tools
			// emit one scalar scrollSpeed.  Reflect.fields is safe for the JSON
			// scalar/object values used here and avoids depending on a target-
			// specific numeric class name.
			var speedFields:Array<String> = safeFields(speeds);
			if (speedFields.length == 0)
				value = speeds;
		}
		var speed = numberValue(value, 1);
		return speed <= 0 ? 1 : speed;
	}

	static function readTimeChanges(metadata:Dynamic, chart:Dynamic, findings:Array<VSliceDiagnostic>, origin:String, difficulty:String):Array<Dynamic> {
		var source = field(metadata, 'timeChanges');
		if (source == null)
			source = field(chart, 'timeChanges');
		var result:Array<Dynamic> = [];
		if (!Std.isOfType(source, Array)) {
			var fallback = numberValue(field(chart, 'bpm'), DEFAULT_BPM);
			if (fallback > 0)
				result.push({t: 0.0, bpm: fallback});
			return result;
		}
		for (entry in (cast source:Array<Dynamic>)) {
			var time = numberValue(field(entry, 't'), Math.NaN);
			var bpm = numberValue(field(entry, 'bpm'), Math.NaN);
			if (Math.isNaN(time) || Math.isNaN(bpm) || bpm <= 0) {
				findings.push(makeDiagnostic('warning', 'invalid-time-change',
					'V-Slice timeChanges contains an entry without a positive t/bpm pair.', origin, difficulty));
				continue;
			}
			if (time < 0)
				time = 0;
			result.push({t: time, bpm: bpm});
		}
		result.sort(function(a, b) return a.t < b.t ? -1 : a.t > b.t ? 1 : 0);
		if (result.length == 0)
			result.push({t: 0.0, bpm: DEFAULT_BPM});
		return result;
	}

	static function buildSections(noteRows:Array<Dynamic>, maxTime:Float, changes:Array<Dynamic>):Array<Dynamic> {
		var sections:Array<Dynamic> = [];
		var cursor:Float = 0;
		var guard:Int = 0;
		while ((cursor < maxTime - EPSILON || sections.length == 0) && guard++ < 100000) {
			var bpm = bpmAt(changes, cursor);
			if (bpm <= 0)
				bpm = DEFAULT_BPM;
			var stepMs = 60000.0 / bpm / 4.0;
			var next = cursor + stepMs * DEFAULT_SECTION_STEPS;
			for (change in changes) {
				if (change.t > cursor + EPSILON && change.t < next - EPSILON) {
					next = change.t;
					break;
				}
			}
			var length = Std.int(Math.round((next - cursor) / stepMs));
			if (length < 1)
				length = 1;
			var actualEnd = cursor + length * stepMs;
			var sectionNotes:Array<Dynamic> = [];
			for (entry in noteRows) {
				var time:Float = entry.time;
				if (time >= cursor - EPSILON && (time < next - EPSILON || next >= maxTime - EPSILON))
					sectionNotes.push(entry.row);
			}
			// Explicit mixed rows prevent hxcpp from coercing the whole note
			// to Array<Int> while comparing timestamps (including optional data).
			sectionNotes.sort(function(a:Array<Dynamic>, b:Array<Dynamic>)
				return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
			var previousBpm:Float = sections.length == 0 ? bpm : sections[sections.length - 1].bpm;
			sections.push({
				sectionNotes: sectionNotes,
				lengthInSteps: length,
				mustHitSection: true,
				bpm: bpm,
				changeBPM: sections.length > 0 && Math.abs(previousBpm - bpm) > EPSILON,
				altAnim: false,
				altAnimNum: 0
			});
			cursor = actualEnd;
			// A BPM boundary can be a fractional step.  Keep the next segment at
			// that boundary so native `changeBPM` still receives the authored tempo.
			if (next < actualEnd - EPSILON)
				cursor = next;
			if (cursor <= 0)
				break;
		}
		return sections;
	}

	static function bpmAt(changes:Array<Dynamic>, time:Float):Float {
		var bpm = DEFAULT_BPM;
		for (change in changes) {
			if (change.t <= time + EPSILON)
				bpm = change.bpm;
			else
				break;
		}
		return bpm;
	}

	static function noteKind(note:Dynamic, findings:Array<VSliceDiagnostic>, origin:String, difficulty:String,
		noteDefinitions:Array<Dynamic>, noteKindIndexes:Map<String, Int>, songName:String,
		characterIds:Array<String>, noteStyleConversions:Array<VSliceNoteKindStyleConversion>):VSliceNoteKind {
		var kind = stringValue(field(note, 'k'), '');
		if (kind == '')
			kind = stringValue(field(note, 'kind'), '');
		if (kind == '')
			return {alt: 0, customIndex: -1};
		var normalized = kind.toLowerCase().trim();
		switch (normalized) {
			case 'alt-anim' | 'alt' | 'alt-animation':
				return {alt: 1, customIndex: -1};
			case 'normal':
				return {alt: 0, customIndex: -1};
			default:
				var customIndex = noteKindIndexes.get(normalized);
				if (customIndex == null) {
					customIndex = noteDefinitions.length;
					noteKindIndexes.set(normalized, customIndex);
					var kindId = safeIdentifier(kind);
					var definition:Dynamic = {
						noteName: 'V-Slice ' + kind,
						animNames: ['purple', 'blue', 'green', 'red'],
						animInt: [4, 5, 6, 7],
						// These fields deliberately preserve identity only. The donor
						// engine's hit/miss semantics are not guessed here; a future
						// script bridge can dispatch on sourceKind/classes/id.
						classes: ['vslice', 'vslice-kind:' + kindId],
							id: 'vslice:' + kindId + ':' + customIndex,
							sourceKind: kind,
							sourceEngine: ENGINE_NAME
						};
						noteDefinitions.push(definition);
						var nativeKindRouted = NoteTypeCompat.applyVSliceKind(definition, kind);
						var hxcAdapter = findHxcNoteAdapter(kind, origin, songName, characterIds);
						if (hxcAdapter != null && hxcAdapter.result.kind == 'note-kind'
							&& hxcAdapter.result.noteBehaviorPatterns.indexOf('avoid-auto-hit') >= 0)
							Reflect.setField(definition, 'avoidAutoHit', true);
						var noteStyleId = hxcAdapter == null || hxcAdapter.noteStyleId == null
							? '' : hxcAdapter.noteStyleId;
						if (noteStyleId == '')
							noteStyleId = findVSliceNoteKindStyleId(origin, kind);
						if (hxcAdapter != null) {
							Reflect.setField(definition, 'sourceAdapter', 'HXC');
							Reflect.setField(definition, 'sourceAdapterPath', hxcAdapter.path);
							Reflect.setField(definition, 'sourceAdapterClass', hxcAdapter.result.className);
							Reflect.setField(definition, 'sourceCallbacks', hxcAdapter.result.canonicalCallbacks);
							Reflect.setField(definition, 'genericBehaviorRouted', hxcAdapter.generic);
							if (hxcAdapter.generic) {
								findings.push(makeDiagnostic('info', 'note-kind-adapter',
									'V-Slice note kind ' + kind + ' matched HXC note adapter '
									+ hxcAdapter.result.className + '; generic note lifecycle/graphics callbacks are routed through the native HXC bridge.',
									origin, difficulty));
								if (hxcAdapter.donorState)
									findings.push(makeDiagnostic('warning', 'note-kind-state',
										'V-Slice note kind ' + kind + ' still references donor-specific save/tally state; only the generic HXC behavior is routed.',
										origin, difficulty));
							} else {
								findings.push(makeDiagnostic('warning', 'note-kind-generic',
									'V-Slice note kind ' + kind + ' matched an HXC class, but no safe generic callback body was generated; identity is preserved only.',
									origin, difficulty));
							}
						} else if (nativeKindRouted) {
							findings.push(makeDiagnostic('info', 'note-kind-native',
								'V-Slice note kind ' + kind + ' uses the centralized native '
								+ Std.string(Reflect.field(definition, 'sourceNoteType')) + ' behavior adapter.',
								origin, difficulty));
						} else {
							findings.push(makeDiagnostic('warning', 'note-kind-generic',
								'V-Slice note kind ' + kind + ' was preserved as a native custom note identity; donor-specific hit/miss behavior remains unsupported until a script bridge is available.',
								origin, difficulty));
						}
						if (noteStyleId != '')
							applyVSliceNoteKindStyle(definition, noteStyleId, origin,
								noteStyleConversions, findings, difficulty);
					}
					return {alt: 0, customIndex: customIndex};
		}
	}

	/** Resolve the literal NoteKind style selected by its V-Slice HXC adapter. */
	static function applyVSliceNoteKindStyle(definition:Dynamic, styleId:String, origin:String,
		conversions:Array<VSliceNoteKindStyleConversion>, findings:Array<VSliceDiagnostic>, difficulty:String):Void {
		#if sys
		var stylePath = findVSliceNoteStyleFile(origin, styleId);
		if (stylePath == null) {
			findings.push(makeDiagnostic('warning', 'unsupported-note-kind-style',
				'V-Slice NoteKind references note style "' + styleId
				+ '", but no data/notestyles definition was found under the selected source root.', origin, difficulty));
			return;
		}
		try {
			var data:Dynamic = Json.parse(File.getContent(stylePath));
			var conversion = convertNoteStyle(data, findVSliceContentRoot(origin), styleId);
			var noteAtlasReady = hasVSliceNoteStyleAtlas(conversion, 'NOTE_assets');
			for (finding in conversion.diagnostics) {
				// A scripted NoteKind uses only the note atlas. Its V-Slice style
				// commonly inherits the game-owned strumline and popup assets, so a
				// missing complete-UI warning does not invalidate this note graphic.
				if (noteAtlasReady && (finding.code == 'unsupported-note-style'
					|| (finding.code == 'missing-note-style-asset'
						&& finding.message.indexOf('noteStrumline') >= 0)))
					continue;
				var copy:VSliceDiagnostic = {
					severity: finding.severity,
					code: finding.code,
					message: finding.message,
					path: finding.path == null || finding.path == '' ? stylePath : finding.path,
					difficulty: difficulty
				};
				findings.push(copy);
			}
			if (!noteAtlasReady)
				return;
			var packRoot = 'assets/images/custom_ui/ui_packs/' + conversion.name + '/';
			var presetDefinitions = field(conversion.preset, 'definitions');
			var directions:Array<String> = ['left', 'down', 'up', 'right'];
			var prefixes:Array<String> = [];
			for (direction in directions) {
				var directionData = field(presetDefinitions, direction);
				prefixes.push(stringValue(field(directionData, 'note'), direction));
			}
			Reflect.setField(definition, 'animNames', prefixes);
			Reflect.setField(definition, 'customNotePath', packRoot + 'NOTE_assets');
			Reflect.setField(definition, 'customNoteIsPixel', field(conversion.registryEntry, 'isPixel') == true);
			Reflect.setField(definition, 'customNoteScale', positiveNumber(field(conversion.registryEntry, 'noteScale'), 0.7));
			Reflect.setField(definition, 'customNoteOffsetX', numberValue(field(conversion.registryEntry, 'noteOffsetX'), 0));
			Reflect.setField(definition, 'customNoteOffsetY', numberValue(field(conversion.registryEntry, 'noteOffsetY'), 0));
			if (hasVSliceNoteStyleAtlas(conversion, 'hold'))
				Reflect.setField(definition, 'customSustainPath', packRoot
					+ stringValue(field(conversion.registryEntry, 'holdAsset'), 'hold'));
			Reflect.setField(definition, 'sourceNoteStyle', styleId);
			var exists = false;
			if (conversions != null)
				for (entry in conversions)
					if (entry != null && entry.conversion != null
						&& entry.conversion.name.toLowerCase() == conversion.name.toLowerCase())
						exists = true;
			if (!exists && conversions != null)
				conversions.push({reference: styleId, source: stylePath, conversion: conversion});
		} catch (error:Dynamic) {
			findings.push(makeDiagnostic('warning', 'unsupported-note-kind-style',
				'V-Slice NoteKind note style "' + styleId + '" could not be converted: '
				+ Std.string(error), stylePath, difficulty));
		}
		#end
	}

	static function hasVSliceNoteStyleAtlas(conversion:VSliceNoteStyleConversion, base:String):Bool {
		if (conversion == null || conversion.assets == null || base == null || base == '')
			return false;
		var png = false;
		var xml = false;
		for (mapping in conversion.assets) {
			if (mapping == null || !mapping.supported || mapping.kind != (base == 'NOTE_assets'
				? 'note-style-note' : 'note-style-hold'))
				continue;
			if (mapping.destination.toLowerCase() == (base + '.png').toLowerCase()) png = true;
			if (mapping.destination.toLowerCase() == (base + '.xml').toLowerCase()) xml = true;
		}
		return png && xml;
	}

	#if sys
	/** Find a matching HXC note class in the imported root without scanning media. */
	static function findHxcNoteAdapter(kind:String, origin:String, songName:String,
		characterIds:Array<String>):Null<VSliceHxcNoteAdapter> {
		if (kind == null || StringTools.trim(kind) == '' || origin == null || StringTools.trim(origin) == '')
			return null;
		var current = origin;
		if (!FileSystem.isDirectory(current))
			current = Path.directory(current);
		// V-Slice metadata carries a display title (`songName`) which does not
		// always match the source folder or its HXC companion. Keep the exact
		// imported folder stem as a second engine-level lookup key so a chart
		// cannot lose a song-owned note adapter merely because its title uses
		// spaces or different punctuation.
		var sourceFolder = current == null ? '' : Path.withoutDirectory(Path.normalize(current));
		var inspected:Map<String, Bool> = new Map<String, Bool>();
		for (_ in 0...12) {
			if (current == null || current == '' || !FileSystem.isDirectory(current))
				break;
			for (relative in [['scripts', 'notes'], ['scripts', 'notekinds']]) {
				var directory = Path.join([current, relative[0], relative[1]]);
				if (!FileSystem.isDirectory(directory))
					continue;
				var scripts:Array<String> = [];
				try scripts = FileSystem.readDirectory(directory) catch (_:Dynamic) {}
				scripts = scripts.filter(function(name) return name.toLowerCase().endsWith('.hxc'));
				scripts.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
				// The authored NoteKind id comes from its constructor, not the
				// script filename. Inspect this small script directory before
				// falling back to a song/character callback.
				for (entry in scripts) {
					var script = Path.join([directory, entry]);
					if (!FileSystem.exists(script) || FileSystem.isDirectory(script))
						continue;
					try {
						inspected.set(script.toLowerCase(), true);
						var source = File.getContent(script);
						if (hxcNoteStyleId(source, kind) == ''
							&& source.toLowerCase().indexOf(kind.toLowerCase()) < 0)
							continue;
						var result = HxcCompat.analyze(source, script);
						var matchesKind = false;
						for (authoredKind in result.noteKinds)
							if (authoredKind.toLowerCase().trim() == kind.toLowerCase().trim())
								matchesKind = true;
						if (!matchesKind || result.nativeNoteDefinitions.length == 0)
							continue;
						var generic = false;
						for (callback in result.callbackAdapters)
							if (callback != null && callback.safe
								&& (callback.canonicalName == 'noteHit' || callback.canonicalName == 'noteMiss'
									|| callback.canonicalName == 'noteIncoming' || callback.canonicalName == 'opponentNoteHit'
									|| callback.canonicalName == 'opponentNoteMiss'))
								generic = true;
						return {
							path: script,
							result: result,
							generic: generic,
							donorState: result.noteBehaviorPatterns.indexOf('donor-state') >= 0,
							noteStyleId: hxcNoteStyleId(source, kind)
						};
					} catch (_:Dynamic) {}
				}
			}
			// A note kind can be owned by the active song or character instead of a
			// ScriptedNoteKind class. Those companions are already selected by the
			// manifest runtime; recognize them only when a safe note callback contains
			// the authored kind as an exact string literal. This keeps diagnostics
			// honest without guessing behavior from an unrelated script in the pack.
			var companions:Array<String> = [];
			// Character callbacks own actor-local note animation/handling, so prefer
			// an active character companion over a song companion when both safely
			// claim the same authored kind. Dedicated note-kind scripts above remain
			// the strongest match; the song companion is a generic fallback for kinds
			// with no active character owner.
			appendDeclaredHxcCharacterCompanions(companions, current, characterIds);
			appendHxcCompanionCandidate(companions, current, 'songs', songName);
			if (sourceFolder != '' && sourceFolder != '.')
				appendHxcCompanionCandidate(companions, current, 'songs', sourceFolder);
			for (script in companions) {
				var key = script.toLowerCase();
				if (inspected.exists(key))
					continue;
				inspected.set(key, true);
				try {
					var result = HxcCompat.analyze(File.getContent(script), script);
					var generic = false;
					for (callback in result.callbackAdapters)
						if (callback != null && callback.safe && isHxcNoteCallback(callback.canonicalName)
							&& bodyReferencesLiteral(callback.body, kind))
							generic = true;
					if (generic)
						return {
							path: script,
							result: result,
							generic: true,
							donorState: result.noteBehaviorPatterns.indexOf('donor-state') >= 0
						};
				} catch (_:Dynamic) {}
			}
			var parent = Path.directory(current);
			if (parent == current || parent == null || parent == '')
				break;
			current = parent;
		}
		return null;
	}

	/** Use the same declared character identity as runtime discovery. A wrapper
	 * may live in stages/ and have a class filename unrelated to its actor id.
	 * Start in script/data families, without walking root image/audio trees. */
	static function appendDeclaredHxcCharacterCompanions(result:Array<String>, root:String,
		characterIds:Array<String>):Void {
		if (result == null || root == null || characterIds == null || characterIds.length == 0)
			return;
		var paths:Array<String> = [];
		for (character in characterIds)
			appendHxcCompanionCandidate(paths, root, 'characters', character);
		// Runtime discovery owns the full imported root, including its V-Slice
		// shared library. Mirror the known character-bearing HXC families there
		// (`scripts`, `data`, `stages`, and `characters`); shared/stages is also an
		// explicit V-Slice stage-script location. Scanning `shared` itself would
		// walk images/audio and other package media.
		for (relative in [
			'scripts', 'data/characters', 'data/stages', 'stages', 'characters',
			'shared/scripts', 'shared/data', 'shared/stages', 'shared/characters'
		]) {
			var directory = Path.join([root, relative]);
			if (!FileSystem.isDirectory(directory))
				continue;
			// A diagnostic lookup must not stop at the discovery batch default.
			for (path in HxcScriptDiscovery.discoverRoot(directory, null, 0x7FFFFFFF).all)
				if (paths.indexOf(path) < 0)
					paths.push(path);
		}
		for (path in HxcScriptDiscovery.selectCharacterPaths(paths, characterIds, [root], root))
			if (result.indexOf(path) < 0)
				result.push(path);
	}

	static function appendHxcCompanionCandidate(result:Array<String>, root:String,
		family:String, name:String):Void {
		if (result == null || root == null || name == null || StringTools.trim(name) == '')
			return;
		var clean = StringTools.replace(StringTools.trim(name), '\\', '/');
		var nested = Path.directory(clean);
		var directory = Path.join([root, 'scripts', family]);
		if (nested != null && nested != '' && nested != '.')
			directory = Path.join([directory, nested]);
		var path = findCaseInsensitiveHxc(directory, Path.withoutDirectory(clean));
		if (path != null && result.indexOf(path) == -1)
			result.push(path);
	}

	static function isHxcNoteCallback(name:String):Bool {
		return name == 'noteHit' || name == 'noteMiss' || name == 'noteIncoming'
			|| name == 'opponentNoteHit' || name == 'opponentNoteMiss'
			|| name == 'goodNoteHit';
	}

	/** Compare authored string literals without treating comments or arbitrary
	 * identifier substrings as a note-kind implementation claim. */
	static function bodyReferencesLiteral(body:String, expected:String):Bool {
		if (body == null || expected == null)
			return false;
		var wanted = expected.toLowerCase().trim();
		var quote = '';
		var value = new StringBuf();
		var escaped = false;
		for (index in 0...body.length) {
			var current = body.charAt(index);
			if (quote == '') {
				if (current == '"' || current == "'") {
					quote = current;
					value = new StringBuf();
				}
				continue;
			}
			if (escaped) {
				value.add(current);
				escaped = false;
				continue;
			}
			if (current == '\\') {
				escaped = true;
				continue;
			}
			if (current == quote) {
				if (value.toString().toLowerCase().trim() == wanted)
					return true;
				quote = '';
				continue;
			}
			value.add(current);
		}
		return false;
	}

	static function findCaseInsensitiveHxc(directory:String, kind:String):String {
		if (directory == null || !FileSystem.isDirectory(directory))
			return null;
		var wanted = kind.toLowerCase().trim() + '.hxc';
		try {
			for (entry in FileSystem.readDirectory(directory))
				if (entry.toLowerCase() == wanted)
					return Path.join([directory, entry]);
		} catch (_:Dynamic) {}
		return null;
	}

	/** Read only the literal third argument passed by a ScriptedNoteKind to `super`. */
	static function hxcNoteStyleId(source:String, expectedKind:String):String {
		if (source == null || expectedKind == null
			|| source.toLowerCase().indexOf('extends notekind') < 0
			&& source.toLowerCase().indexOf('extends scriptednotekind') < 0)
			return '';
		var cursor = 0;
		while (cursor < source.length) {
			var at = source.indexOf('super', cursor);
			if (at < 0)
				break;
			cursor = at + 5;
			if (at > 0 && isIdentifierCharacter(source.charAt(at - 1)))
				continue;
			while (cursor < source.length && isWhitespace(source.charAt(cursor))) cursor++;
			if (cursor >= source.length || source.charAt(cursor) != '(')
				continue;
			var arguments = hxcCallArguments(source, cursor);
			if (arguments == null || arguments.length < 3)
				continue;
			var kind = hxcStringLiteral(arguments[0]);
			var styleId = hxcStringLiteral(arguments[2]);
			if (kind != null && kind.toLowerCase() == expectedKind.toLowerCase()
				&& styleId != null && StringTools.trim(styleId) != '')
				return StringTools.trim(styleId);
		}
		return '';
	}

	/** NoteKind script ids need not match their note kind ids or file names. */
	static function findVSliceNoteKindStyleId(origin:String, kind:String):String {
		if (origin == null || kind == null || StringTools.trim(kind) == '')
			return '';
		var current = FileSystem.isDirectory(origin) ? origin : Path.directory(origin);
		for (_ in 0...12) {
			if (current == null || current == '' || !FileSystem.isDirectory(current))
				break;
			var found = noteKindStyleIdInRoot(current, kind);
			if (found != '')
				return found;
			var parent = Path.directory(current);
			if (parent == current || parent == null || parent == '')
				break;
			current = parent;
		}
		return '';
	}

	/** Read only ScriptedNoteKind constructor literals in one selected root. */
	public static function noteKindStyleIdInRoot(root:String, kind:String):String {
		if (root == null || kind == null || !FileSystem.isDirectory(root))
			return '';
		var found = '';
		for (folderName in ['notekinds', 'notes']) {
			var folder = Path.join([root, 'scripts', folderName]);
			if (!FileSystem.isDirectory(folder))
				continue;
			var entries:Array<String> = [];
			try entries = FileSystem.readDirectory(folder) catch (_:Dynamic) {}
			entries.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
			for (entry in entries) {
				if (!entry.toLowerCase().endsWith('.hxc'))
					continue;
				var script = Path.join([folder, entry]);
				if (!FileSystem.exists(script) || FileSystem.isDirectory(script))
					continue;
				try {
					var candidate = hxcNoteStyleId(File.getContent(script), kind);
					if (candidate == '')
						continue;
					if (found != '' && found.toLowerCase() != candidate.toLowerCase())
						return '';
					found = candidate;
				} catch (_:Dynamic) {}
			}
		}
		return found;
	}

	/**
	 * Restore visual metadata for older imports from their selected script
	 * namespace. Only absent fields are filled; neither charts nor noteInfo
	 * are rewritten, and another imported root cannot provide the atlas.
	 */
	public static function applyRuntimeNoteKindPolicies(definitions:Array<Dynamic>, root:String):Int {
		if (definitions == null || root == null || !FileSystem.isDirectory(root)) return 0;
		var hazardous:Map<String, Bool> = new Map();
		for (folder in [Path.join([root, 'scripts', 'notekinds']), Path.join([root, 'scripts', 'notes'])]) {
			if (!FileSystem.isDirectory(folder)) continue;
			for (entry in FileSystem.readDirectory(folder)) {
				if (!entry.toLowerCase().endsWith('.hxc')) continue;
				var path = Path.join([folder, entry]);
				if (FileSystem.isDirectory(path)) continue;
				try {
					var source = File.getContent(path);
					if (!HxcCompat.noteKindAvoidsHits(source)) continue;
					var adapter = HxcCompat.analyze(source, path);
					if (adapter.kind != 'note-kind') continue;
					for (kind in adapter.noteKinds) hazardous.set(kind.toLowerCase(), true);
				} catch (_:Dynamic) {}
			}
		}
		var applied = 0;
		for (definition in definitions) {
			if (definition == null || stringValue(field(definition, 'sourceEngine'), '') != ENGINE_NAME
				|| field(definition, 'avoidAutoHit') != null) continue;
			if (hazardous.exists(stringValue(field(definition, 'sourceKind'), '').toLowerCase())) {
				Reflect.setField(definition, 'avoidAutoHit', true);
				applied++;
			}
		}
		return applied;
	}

	public static function applyRuntimeNoteKindStyles(definitions:Array<Dynamic>, root:String):Int {
		if (definitions == null || root == null || !FileSystem.isDirectory(root))
			return 0;
		var applied = 0;
		for (definition in definitions) {
			if (definition == null || stringValue(field(definition, 'sourceEngine'), '') != ENGINE_NAME
				|| stringValue(field(definition, 'customNotePath'), '') != '')
				continue;
			var kind = stringValue(field(definition, 'sourceKind'), '');
			var styleId = noteKindStyleIdInRoot(root, kind);
			if (styleId == '' || !new EReg('^[A-Za-z0-9_-]+$', '').match(styleId))
				continue;
			var stylePath = Path.join([root, 'data', 'notestyles', styleId + '.json']);
			if (!FileSystem.exists(stylePath))
				continue;
			try {
				var style:Dynamic = Json.parse(File.getContent(stylePath));
				var note = field(field(style, 'assets'), 'note');
				var asset = stringValue(field(note, 'assetPath'), '');
				var colon = asset.indexOf(':');
				if (colon >= 0)
					asset = asset.substr(colon + 1);
				if (asset == '' || asset.startsWith('/') || asset.indexOf('..') >= 0
					|| !new EReg('^[A-Za-z0-9_./-]+$', '').match(asset))
					continue;
				var atlas = Path.join([root, 'images', asset]);
				if (!FileSystem.exists(atlas + '.png') || !FileSystem.exists(atlas + '.xml'))
					continue;
				var noteData = field(note, 'data');
				var prefixes:Array<String> = [];
				for (direction in ['left', 'down', 'up', 'right']) {
					var prefix = stringValue(field(field(noteData, direction), 'prefix'), '');
					if (prefix.endsWith('0'))
						prefix = prefix.substr(0, prefix.length - 1);
					if (prefix == '') {
						prefixes = [];
						break;
					}
					prefixes.push(prefix);
				}
				if (prefixes.length != 4)
					continue;
				var existingNames:Dynamic = field(definition, 'animNames');
				var defaultNames = existingNames == null;
				if (Std.isOfType(existingNames, Array)) {
					var names:Array<Dynamic> = cast existingNames;
					defaultNames = names.length == 4
						&& names[0] == 'purple' && names[1] == 'blue'
						&& names[2] == 'green' && names[3] == 'red';
				}
				if (!defaultNames)
					continue;
				Reflect.setField(definition, 'customNotePath', atlas);
				Reflect.setField(definition, 'animNames', prefixes);
				if (field(definition, 'customNoteIsPixel') == null)
					Reflect.setField(definition, 'customNoteIsPixel', field(note, 'isPixel') == true);
				if (field(definition, 'customNoteScale') == null)
					Reflect.setField(definition, 'customNoteScale', positiveNumber(field(note, 'scale'), 0.7));
				var offsets:Dynamic = field(note, 'offsets');
				if (Std.isOfType(offsets, Array)) {
					var values:Array<Dynamic> = cast offsets;
					if (field(definition, 'customNoteOffsetX') == null && values.length > 0)
						Reflect.setField(definition, 'customNoteOffsetX', numberValue(values[0], 0));
					if (field(definition, 'customNoteOffsetY') == null && values.length > 1)
						Reflect.setField(definition, 'customNoteOffsetY', numberValue(values[1], 0));
				}
				if (field(definition, 'sourceNoteStyle') == null)
					Reflect.setField(definition, 'sourceNoteStyle', styleId);
				applied++;
			} catch (_:Dynamic) {}
		}
		return applied;
	}

	static function hxcCallArguments(source:String, openParen:Int):Null<Array<String>> {
		var args:Array<String> = [];
		var start = openParen + 1;
		var parens = 1;
		var brackets = 0;
		var braces = 0;
		var quote = '';
		var escaped = false;
		var lineComment = false;
		var blockComment = false;
		var index = start;
		while (index < source.length) {
			var current = source.charAt(index);
			var next = index + 1 < source.length ? source.charAt(index + 1) : '';
			if (lineComment) {
				if (current == '\n') lineComment = false;
				index++;
				continue;
			}
			if (blockComment) {
				if (current == '*' && next == '/') { blockComment = false; index += 2; continue; }
				index++;
				continue;
			}
			if (quote != '') {
				if (escaped) escaped = false;
				else if (current == '\\') escaped = true;
				else if (current == quote) quote = '';
				index++;
				continue;
			}
			if (current == '/' && next == '/') { lineComment = true; index += 2; continue; }
			if (current == '/' && next == '*') { blockComment = true; index += 2; continue; }
			if (current == '"' || current == "'") quote = current;
			else if (current == '(') parens++;
			else if (current == ')') {
				parens--;
				if (parens == 0) {
					args.push(StringTools.trim(source.substring(start, index)));
					return args;
				}
			} else if (current == '[') brackets++;
			else if (current == ']') brackets--;
			else if (current == '{') braces++;
			else if (current == '}') braces--;
			else if (current == ',' && parens == 1 && brackets == 0 && braces == 0) {
				args.push(StringTools.trim(source.substring(start, index)));
				start = index + 1;
			}
			index++;
		}
		return null;
	}

	static function hxcStringLiteral(value:String):Null<String> {
		if (value == null || value.length < 2)
			return null;
		var quote = value.charAt(0);
		if ((quote != '"' && quote != "'") || value.charAt(value.length - 1) != quote)
			return null;
		var output = new StringBuf();
		var escaped = false;
		for (index in 1...(value.length - 1)) {
			var current = value.charAt(index);
			if (escaped) {
				output.add(current);
				escaped = false;
			} else if (current == '\\')
				escaped = true;
			else
				output.add(current);
		}
		if (escaped)
			return null;
		return output.toString();
	}

	static function isIdentifierCharacter(value:String):Bool {
		if (value == null || value.length == 0)
			return false;
		var c = value.charAt(0);
		return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
			|| (c >= '0' && c <= '9') || c == '_';
	}

	static function isWhitespace(value:String):Bool {
		return value == ' ' || value == '\t' || value == '\n' || value == '\r';
	}

	static function findVSliceNoteStyleFile(origin:String, reference:String):String {
		if (origin == null || reference == null || StringTools.trim(reference) == '')
			return null;
		var current = FileSystem.isDirectory(origin) ? origin : Path.directory(origin);
		var wanted = StringTools.trim(reference).toLowerCase();
		for (_ in 0...12) {
			if (current == null || current == '' || !FileSystem.isDirectory(current))
				break;
			for (base in [Path.join([current, 'data', 'notestyles']), Path.join([current, 'notestyles'])]) {
				if (!FileSystem.isDirectory(base))
					continue;
				var entries:Array<String> = [];
				try entries = FileSystem.readDirectory(base) catch (_:Dynamic) {}
				entries.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
				for (entry in entries) {
					var lower = entry.toLowerCase();
					if (!lower.endsWith('.json') && !lower.endsWith('.jsonc'))
					continue;
				var dot = entry.lastIndexOf('.');
				if (dot <= 0 || entry.substr(0, dot).toLowerCase() != wanted)
					continue;
				var candidate = Path.join([base, entry]);
				if (FileSystem.exists(candidate) && !FileSystem.isDirectory(candidate))
					return candidate;
				}
			}
			var parent = Path.directory(current);
			if (parent == current || parent == null || parent == '')
				break;
			current = parent;
		}
		return null;
	}

	static function findVSliceContentRoot(origin:String):String {
		if (origin == null || StringTools.trim(origin) == '')
			return '';
		var current = FileSystem.isDirectory(origin) ? origin : Path.directory(origin);
		for (_ in 0...12) {
			if (current == null || current == '' || !FileSystem.isDirectory(current))
				break;
			if (FileSystem.isDirectory(Path.join([current, 'shared']))
				|| FileSystem.isDirectory(Path.join([current, 'images'])))
				return current;
			var parent = Path.directory(current);
			if (parent == current || parent == null || parent == '')
				break;
			current = parent;
		}
		return FileSystem.isDirectory(origin) ? origin : Path.directory(origin);
	}
	#else
	static function findHxcNoteAdapter(kind:String, origin:String, songName:String,
		characterIds:Array<String>):Null<VSliceHxcNoteAdapter> {
		return null;
	}
	#end

	/**
		Return the stage props which the runtime HXC adapter actually constructs.

		This deliberately inspects HxcCompat's generated HScript rather than
		searching donor source for a matching field name.  A class-level `var teto`
		declaration, an un-emitted unsafe callback, or a sprite with no resolvable
		graphic is not enough to replace the V-Slice JSON asset dependency.
	*/
	static function scriptOwnedStageProps(root:String, stageName:String):Map<String, Bool> {
		var result:Map<String, Bool> = new Map<String, Bool>();
		#if sys
		if (root == null || StringTools.trim(root) == '' || stageName == null || StringTools.trim(stageName) == '')
			return result;
		var script = findVSliceStageScript(root, stageName);
		if (script == null)
			return result;
		try {
			var compat = HxcCompat.analyze(File.getContent(script), script);
			if (compat == null || compat.kind != 'stage' || compat.generatedHscript == null
				|| StringTools.trim(compat.generatedHscript) == '')
				return result;
			var startBody = hxcFunctionBody(compat.generatedHscript, 'start');
			if (startBody == null || StringTools.trim(startBody) == '')
				return result;
			// Keep this reflection-based for older standalone importer fixtures which
			// provide the pre-constructor HxcCompatResult typedef.  Native builds use
			// the optional field directly through the current HxcCompat result.
			var stageConstructor:Dynamic = Reflect.field(compat, 'stageConstructorBody');
			var constructorOwned = stageConstructor != null
				&& StringTools.trim(Std.string(stageConstructor)) != '';
			var startOwned = constructorOwned;
			for (callback in compat.callbackAdapters)
				if (callback != null && callback.canonicalName == 'start' && callback.safe == true) {
					startOwned = true;
					break;
				}
			if (startOwned)
				for (propName in hxcConstructedSpriteNames(startBody))
					if (hxcRuntimeOwnsSprite(startBody, propName, root))
						result.set(propName.toLowerCase(), true);
		} catch (_:Dynamic) {
			// A malformed/unreadable optional HXC must leave the JSON dependency
			// visible.  The importer never turns an analysis failure into a claim
			// that a graphic exists.
		}
		#end
		return result;
	}

	#if sys
	/** Locate the exact stage HXC companion without crawling media trees. */
	static function findVSliceStageScript(root:String, stageName:String):String {
		var current = normalizeSourceRoot(root);
		if (current == '' || !FileSystem.isDirectory(current))
			return null;
		var requested = Path.withoutExtension(Path.withoutDirectory(stageName));
		for (_ in 0...12) {
			for (relative in [
				['scripts', 'stages'], ['data', 'stages'], ['shared', 'stages'], ['stages']
			]) {
				var directory = relative.length == 1
					? Path.join([current, relative[0]])
					: Path.join([current, relative[0], relative[1]]);
				var script = findCaseInsensitiveHxc(directory, requested);
				if (script != null)
					return script;
			}
			var parent = Path.directory(current);
			if (parent == current || parent == null || parent == '')
				break;
			current = parent;
		}
		return null;
	}

	/** Return only names assigned a concrete FlxSprite in the emitted start hook. */
	static function hxcConstructedSpriteNames(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || source == '')
			return result;
		var expression = new EReg('(?:^|[;{}\\n])\\s*(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*(?:new\\s+(?:[A-Za-z_][A-Za-z0-9_]*\\.)*FlxSprite\\s*\\(|HxcCompatRuntime\\s*\\.\\s*create(?:BGSprite|FunkinSprite)\\s*\\()', 'gm');
		var offset = 0;
		while (offset < source.length) {
			var remaining = source.substr(offset);
			if (!expression.match(remaining))
				break;
			var position = expression.matchedPos();
			appendUniqueStagePropName(result, expression.matched(1));
			offset += position.pos + (position.len > 0 ? position.len : 1);
		}
		return result;
	}

	/**
		Prove one script-owned sprite is usable on the native runtime.  Paths.image
		requires a PNG; Paths.getSparrowAtlas additionally requires its XML atlas.
		Both checks use the same case-tolerant V-Slice resolver as JSON props.
	*/
	static function hxcRuntimeOwnsSprite(source:String, propName:String, root:String):Bool {
		if (!isStagePropIdentifier(propName) || source == null || root == null || StringTools.trim(root) == '')
			return false;
		var escaped = regexLiteral(propName);
		var loader = new EReg('\\b' + escaped + '\\s*\\.\\s*frames\\s*=\\s*Paths\\s*\\.\\s*getSparrowAtlas\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*\\)', 'm');
		var atlasPath:String = null;
		var imagePath:String = null;
		if (loader.match(source))
			atlasPath = loader.matched(1);
		else {
			var imageLoader = new EReg('\\b' + escaped + '\\s*\\.\\s*loadGraphic\\s*\\(\\s*Paths\\s*\\.\\s*image\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*\\)\\s*\\)', 'm');
			if (imageLoader.match(source))
				imagePath = imageLoader.matched(1);
		}
		// Constructor-only FPS Plus stages are emitted through the native runtime
		// factories rather than retaining a donor `loadGraphic` expression.  The
		// selected root is still required for the literal media key; native shared
		// assets are resolved by the same importer-owned resolver at runtime.
		var bgFactory = new EReg('HxcCompatRuntime\\s*\\.\\s*createBGSprite\\s*\\(\\s*hxcAssetRoot\\s*,\\s*["\\\']([^"\\\']+)["\\\']', 'm');
		if (bgFactory.match(source))
			imagePath = bgFactory.matched(1);
		else {
			var nativeFactory = new EReg('HxcCompatRuntime\\s*\\.\\s*createFunkinSprite\\s*\\(\\s*hxcAssetRoot[\\s\\S]*?Paths\\s*\\.\\s*image\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'm');
			if (nativeFactory.match(source))
				imagePath = nativeFactory.matched(1);
		}
		if (atlasPath == null && imagePath == null)
			return false;
		if (atlasPath != null) {
			var png = resolveVSliceAsset(root, stripAssetExtension(atlasPath), '.png');
			var xml = resolveVSliceAsset(root, stripAssetExtension(atlasPath), '.xml');
			if (png == null || Reflect.field(png, 'found') != true || xml == null || Reflect.field(xml, 'found') != true)
				return false;
		} else {
			var image = resolveVSliceAsset(root, stripAssetExtension(imagePath), '.png');
			if (image == null || Reflect.field(image, 'found') != true)
				return false;
		}
		var directAdd = new EReg('\\b(?:add|addSprite|game\\s*\\.\\s*add|currentPlayState\\s*\\.\\s*add|PlayState\\s*\\.\\s*instance\\s*\\.\\s*add)\\s*\\(\\s*' + escaped + '\\b', 'm');
		if (directAdd.match(source))
			return true;
		var namedAdd = new EReg('\\b(?:stage|curStage|currentStage)\\s*\\.\\s*addElement\\s*\\(\\s*["\\\']' + escaped + '["\\\']\\s*,\\s*' + escaped + '\\b', 'm');
		return namedAdd.match(source);
	}

	static function hxcFunctionBody(source:String, name:String):Null<String> {
		if (source == null || name == null || name == '')
			return null;
		var expression = new EReg('\\bfunction\\s+' + regexLiteral(name) + '\\s*\\([^)]*\\)\\s*\\{', 'm');
		if (!expression.match(source))
			return null;
		var position = expression.matchedPos();
		var open = source.indexOf('{', position.pos);
		if (open < 0)
			return null;
		var close = matchingStageBrace(source, open);
		return close < 0 ? null : source.substr(open + 1, close - open - 1);
	}

	static function matchingStageBrace(source:String, start:Int):Int {
		var depth = 0;
		var quote = '';
		var escaped = false;
		var lineComment = false;
		var blockComment = false;
		var index = start;
		while (index < source.length) {
			var current = source.charAt(index);
			var next = index + 1 < source.length ? source.charAt(index + 1) : '';
			if (lineComment) {
				if (current == '\n')
					lineComment = false;
				index++;
				continue;
			}
			if (blockComment) {
				if (current == '*' && next == '/') {
					blockComment = false;
					index += 2;
				} else
					index++;
				continue;
			}
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if ((current == '/' && next == '/')) {
				lineComment = true;
				index += 2;
				continue;
			}
			if ((current == '/' && next == '*')) {
				blockComment = true;
				index += 2;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			if (current == '{')
				depth++;
			else if (current == '}') {
				depth--;
				if (depth == 0)
					return index;
			}
			index++;
		}
		return -1;
	}

	static function appendUniqueStagePropName(values:Array<String>, value:String):Void {
		if (values == null || value == null || value == '' || values.indexOf(value) >= 0)
			return;
		values.push(value);
	}

	static function isStagePropIdentifier(value:String):Bool {
		if (value == null || value == '' || !isStagePropIdentifierStart(value.charAt(0)))
			return false;
		for (index in 1...value.length)
			if (!isStagePropIdentifierPart(value.charAt(index)))
				return false;
		return true;
	}

	static function isStagePropIdentifierStart(value:String):Bool {
		if (value == null || value == '')
			return false;
		var code = value.charCodeAt(0);
		return (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || value == '_';
	}

	static function isStagePropIdentifierPart(value:String):Bool {
		if (isStagePropIdentifierStart(value))
			return true;
		if (value == null || value == '')
			return false;
		var code = value.charCodeAt(0);
		return code >= 48 && code <= 57;
	}

	static function regexLiteral(value:String):String {
		var result = value == null ? '' : value;
		for (character in ['\\', '.', '^', '$', '*', '+', '?', '(', ')', '[', ']', '{', '}', '|'])
			result = StringTools.replace(result, character, '\\' + character);
		return result;
	}

	#end

	static function convertEvents(chart:Dynamic, findings:Array<VSliceDiagnostic>, origin:String, difficulty:String):Array<Dynamic> {
		var source = field(chart, 'events');
		var converted:Array<Dynamic> = [];
		if (!Std.isOfType(source, Array))
			return converted;
		for (event in (cast source:Array<Dynamic>)) {
			var time = numberValue(field(event, 't'), Math.NaN);
			var original = stringValue(field(event, 'e'), '');
			if (Math.isNaN(time) || original == '') {
				findings.push(makeDiagnostic('warning', 'invalid-event',
					'V-Slice event is missing a numeric t or event name and was skipped.', origin, difficulty));
				continue;
			}
			var values = field(event, 'v');
			// Keep every authored kind verbatim with its complete object payload.
			// Donor song scripts key their own handlers on the authored spelling
			// (Expurgation's FocusCamera zoom tweens), so renaming at import breaks
			// them; the runtime router (EngineCompat.routeLegacyEvent ->
			// routeVSliceEvent) resolves canonical names and value slots at
			// dispatch time through the same single mapping that used to be
			// applied here.
			var route = EngineCompat.routeVSliceEvent(original, values);
			var payload = values == null ? '' : Json.stringify(values);
			appendEvent(converted, time, [original, payload, '', '']);
			if (route == null)
				findings.push(makeDiagnostic('info', 'foreign-event-preserved',
					'V-Slice event ' + original + ' was preserved for runtime compatibility dispatch.', origin, difficulty));
		}
		// hxcpp's native Array.sort corrupts these mixed Dynamic groups (each
		// group's payload array comes back as the integer 0), silently turning
		// every imported V-Slice event into a bare [time, 0] row.  Sort by hand.
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

	static function appendEvent(events:Array<Dynamic>, time:Float, event:Array<Dynamic>):Void {
		for (group in events) {
			if (Math.abs(group[0] - time) <= EPSILON) {
				group[1].push(event);
				return;
			}
		}
		events.push([time, [event]]);
	}

	/** Keep one report row per distinct finding, not one row per chart event. */
	static function deduplicateDiagnostics(findings:Array<VSliceDiagnostic>):Array<VSliceDiagnostic> {
		if (findings == null || findings.length < 2)
			return findings == null ? [] : findings;
		var result:Array<VSliceDiagnostic> = [];
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

	static function hasVocalMetadata(characters:Dynamic):Bool {
		return vocalArrayCount(characters) > 0;
	}

	static function vocalArrayCount(characters:Dynamic):Int {
		if (characters == null)
			return 0;
		var count = 0;
		for (key in ['opponentVocals', 'playerVocals', 'vocals']) {
			var value = field(characters, key);
			if (Std.isOfType(value, Array))
				count += (cast value:Array<Dynamic>).length;
			else if (value != null && stringValue(value, '') != '')
				count++;
		}
		return count;
	}

	static function isVocalStem(path:String):Bool {
		var file = path.substr(path.lastIndexOf('/') + 1);
		return (file.startsWith('voices-') || file.startsWith('voices_'))
			&& (file.endsWith('.ogg') || file.endsWith('.wav') || file.endsWith('.mp3'));
	}

	static function safeStem(value:String):String {
		var result = value == null ? '' : value.trim().toLowerCase();
		result = result.replace(' ', '-');
		var chars = [];
		for (i in 0...result.length) {
			var c = result.charAt(i);
			if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' || c == '_')
				chars.push(c);
		}
		return chars.join('') == '' ? 'song' : chars.join('');
	}

	static function field(value:Dynamic, name:String):Dynamic {
		if (value == null)
			return null;
		try {
			if (!Reflect.hasField(value, name))
				return null;
			return Reflect.field(value, name);
		} catch (e:Dynamic) {
			// JSON scalars are valid values for a few optional fields (notably
			// scrollSpeed), but Reflect.hasField throws on some native targets
			// when handed an int/float.  Treat those as absent fields.
			return null;
		}
	}

	static function safeFields(value:Dynamic):Array<String> {
		if (value == null)
			return [];
		try {
			return Reflect.fields(value);
		} catch (e:Dynamic) {
			return [];
		}
	}

	static function containsString(values:Array<String>, value:String):Bool {
		for (candidate in values)
			if (candidate == value)
				return true;
		return false;
	}

	static function stringValue(value:Dynamic, fallback:String):String {
		if (value == null)
			return fallback;
		var result = Std.string(value).trim();
		return result == '' ? fallback : result;
	}

	static function numberValue(value:Dynamic, fallback:Float):Float {
		if (value == null)
			return fallback;
		var result = Std.parseFloat(Std.string(value));
		return Math.isNaN(result) ? fallback : result;
	}

	/** Return a Haxe ARGB literal for a V-Slice HTML/hex colour value. */
	static function colorLiteral(value:Dynamic):Null<String> {
		if (value == null)
			return null;
		if (Std.isOfType(value, String)) {
			var text = StringTools.trim(Std.string(value));
			if (text.startsWith('#')) {
				var digits = text.substr(1);
				if (digits.length == 6)
					return '0xFF' + digits.toUpperCase();
				if (digits.length == 8)
					return '0x' + digits.toUpperCase();
			}
			if (text.toLowerCase().startsWith('0x')) {
				var hexDigits = text.substr(2);
				if (hexDigits.length == 6)
					return '0xFF' + hexDigits.toUpperCase();
				if (hexDigits.length == 8)
					return '0x' + hexDigits.toUpperCase();
			}
		}
		var parsed = Std.parseInt(Std.string(value));
		if (parsed == null)
			return null;
		var hex = StringTools.hex(parsed, 8).toUpperCase();
		if (hex.length > 8)
			hex = hex.substr(hex.length - 8);
		if (hex.length == 6)
			hex = 'FF' + hex;
		while (hex.length < 8)
			hex = '0' + hex;
		return '0x' + hex;
	}

	/** Convert Psych/V-Slice RGB healthbar metadata to the native registry form. */
	static function healthbarColorString(value:Dynamic, findings:Array<VSliceDiagnostic>):Null<String> {
		if (value == null)
			return null;
		if (Std.isOfType(value, Array)) {
			var values:Array<Dynamic> = cast value;
			if (values.length >= 3) {
				var rgb:Array<String> = [];
				for (index in 0...3) {
					var component = numberValue(values[index], Math.NaN);
					if (Math.isNaN(component)) {
						findings.push(makeDiagnostic('warning', 'invalid-healthbar-colors',
							'V-Slice healthbar_colors must contain numeric red, green and blue components.', ''));
						return null;
					}
					component = Math.max(0, Math.min(255, Math.round(component)));
					var componentHex = StringTools.hex(Std.int(component), 2).toUpperCase();
					if (componentHex.length < 2)
						componentHex = '0' + componentHex;
					rgb.push(componentHex);
				}
				return '#' + rgb.join('');
			}
		}
		var literal = colorLiteral(value);
		if (literal != null) {
			var digits = literal.substr(2);
			return '#' + digits.substr(digits.length - 6);
		}
		findings.push(makeDiagnostic('warning', 'invalid-healthbar-colors',
			'V-Slice healthbar_colors could not be converted to the native character registry.', ''));
		return null;
	}

	static function makeDiagnostic(severity:String, code:String, message:String, path:String, ?difficulty:String):VSliceDiagnostic {
		var result:VSliceDiagnostic = {severity: severity, code: code, message: message};
		if (path != null && path != '')
			result.path = path;
		if (difficulty != null && difficulty != '')
			result.difficulty = difficulty;
		return result;
	}

	#if sys
	static function collectFiles(root:String, current:String, output:Array<String>):Void {
		if (root == null || current == null || !FileSystem.exists(current) || !FileSystem.isDirectory(current))
			return;
		for (entry in FileSystem.readDirectory(current)) {
			var path = Path.join([current, entry]);
			if (FileSystem.isDirectory(path))
				collectFiles(root, path, output);
			else
				output.push(path);
		}
	}
	#end
}
