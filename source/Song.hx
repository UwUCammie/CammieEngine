package;

import Section.SwagSection;
import CompatScriptManifest.CompatScriptManifestData;
import flixel.FlxG;
import haxe.Json;
import haxe.format.JsonParser;
import lime.utils.Assets;
import tjson.TJSON;
import FNFAssets.Extensions;
#if sys
import sys.io.File;
import sys.FileSystem;
import lime.system.System;
import haxe.io.Path;
#end
using StringTools;

/**
	The concrete native visual selected for an authored character id.  The
	requested/registry fields deliberately remain separate from the selected
	implementation: imported charts may keep an id such as `miku` while a
	complete sibling (`mikuv2`) supplies the atlas and shared animation script.
*/
typedef CharacterVisualResolution = {
	var requested:String;
	var registryName:String;
	var selectedRegistryName:String;
	var likeName:String;
	var implementationName:String;
	var assetName:String;
	var implementationPath:String;
	var assetPath:String;
	var assetRootPath:String;
	var complete:Bool;
	var diagnosticCode:String;
	var diagnostic:String;
}

typedef SwagSong = {
	var song:String;
	/** Optional imported metadata used by generic credits/title modules. */
	@:optional var songArtist:String;
	/** Optional imported album identity used by generic HXC/RPC modules. */
	@:optional var album:String;
	/** Full FPS Plus difficulty-rating list shared by authored difficulties. */
	@:optional var difficultyRatings:Array<Dynamic>;
	/** Rating for this authored difficulty when the importer can align it. */
	@:optional var difficultyRating:Float;
	/** Parsed foreign metadata/provenance; unknown keys remain lossless here. */
	@:optional var compatMetadata:Dynamic;
	/** Authored chart format; controls note-side semantics when declared. */
	@:optional var format:String;
	/** Authored Nightmare Vision playfield layout, owned by this difficulty. */
	@:optional var keys:Int;
	@:optional var lanes:Int;
	@:optional var arrowSkins:Array<String>;
	@:optional var trackSwap:Bool;
	/** Keep an imported author's title spelling in the gameplay HUD. */
	@:optional var compatPreserveSongTitle:Bool;
	/** Optional native view of authored vocal timing offsets. */
	@:optional var offsets:SongVocalOffsets;
	/** Raw offset metadata retained when an importer provides it. */
	@:optional var vocalOffsets:Dynamic;
	/** Optional V-Slice/TAKEOVER chart sticker identity. */
	@:optional var stickerPack:String;
	/** Runtime-only accessor attached to charts loaded from a known song folder. */
	@:optional var getDifficulty:Dynamic;
	/** Native data/audio folder; can differ from the authored song title when two imports share a title. */
	@:optional var compatStorageFolder:String;
	/** Runtime-only exact Freeplay row id used to save this selected chart's score. */
	@:optional var compatScoreSongId:String;
	/** Native chart filename selected by the loader, retained for editor reload/save. */
	@:optional var compatChartFileName:String;
	/** Runtime provenance only: the selected chart/default supplied a usable stage id. */
	@:optional var compatStageAuthored:Bool;
	var notes:Array<SwagSection>;
	var bpm:Float;
	var needsVoices:Bool;
	var speed:Float;
	// psych-format charts embed events as [[time, [[name, v1, v2], ...]], ...]
	@:optional var events:Array<Dynamic>;
	/** Authored Codename notes whose strumlines are not yet playable natively. */
	@:optional var codenameUnsupportedNotes:Array<Dynamic>;
	/** Authored Codename note type table for owner-scoped note script loading. */
	@:optional var codenameNoteTypes:Array<Dynamic>;
	/** Raw V-Slice notes from strumlines the source gameplay runtime does not route.
	 * Kept for owner chart/editor round-trips; never included in gameplay `notes`. */
	@:optional var vSliceUnroutedNotes:Array<Dynamic>;
	/** V-Slice imports may retain one file per authored vocal stem. */
	@:optional var vocalStems:Array<Dynamic>;
	/** Imported FPS/Kade cutscene metadata stays in the native chart envelope. */
	@:optional var cutsceneScript:String;
	@:optional var cutsceneStoryOnly:Bool;
	@:optional var cutscenePlayOnce:Bool;

	var player1:String;
	var player2:String;
	var stage:String;
	var gf:String;
	var isMoody:Null<Bool>;
	var cutsceneType:String;
	var uiType:String;
	/** Psych skin identity; an empty value explicitly selects the source default. */
	@:optional var arrowSkin:String;
	@:optional var splashSkin:String;
	@:optional var disableNoteRGB:Bool;
	var isSpooky:Null<Bool>;
	var isHey:Null<Bool>;
	var isCheer:Null<Bool>;
	var preferredNoteAmount:Null<Int>;
	var forceJudgements:Null<Bool>;
	var forceLayout:Null<String>;
	@:optional var uiLayoutType:Null<String>;
	var convertMineToNuke:Null<Bool>;
	var mania:Null<Int>;
	var stageID:Null<Int>;
}

class Song {
	/** Keep owner-qualified imports in their selected data/audio folder while
	 * leaving the chart's authored song name available to scripts and UI. */
	public static function storageFolder(chart:Dynamic):String {
		if (chart == null) return '';
		var stored:Dynamic = Reflect.field(chart, 'compatStorageFolder');
		var candidate = stored == null ? '' : StringTools.trim(Std.string(stored)).toLowerCase();
		if (validStorageKey(candidate)) return candidate;
		var title:Dynamic = Reflect.field(chart, 'song');
		candidate = title == null ? '' : StringTools.trim(Std.string(title)).toLowerCase();
		return validStorageKey(candidate) ? candidate : '';
	}

	/** Attach the exact selected Freeplay row id only when it names this chart's folder. */
	public static function attachFreeplayScoreSongId(chart:Dynamic, songId:String):Bool {
		if (chart == null || songId == null)
			return false;
		var selected = StringTools.trim(songId);
		var storage = storageFolder(chart);
		if (!validStorageKey(selected.toLowerCase()) || storage == ''
			|| selected.toLowerCase() != storage.toLowerCase())
			return false;
		Reflect.setField(chart, 'compatScoreSongId', selected);
		return true;
	}

	static function validStorageKey(value:String):Bool {
		return value != null && value != '' && value != '.' && value != '..'
			&& value.indexOf('/') < 0 && value.indexOf('\\') < 0
			&& value.indexOf(':') < 0 && value.indexOf('\u0000') < 0;
	}

	// Gameplay data belongs to the selected chart. Visual/identity data is
	// sparse in many imported difficulty files, so it is merged separately.
	// `events` is chart content too: a psych event list must not disappear when
	// its difficulty inherits the normal chart's metadata.
	static var gameplayFields:Array<String> = [
		'song', 'notes', 'bpm', 'needsVoices', 'speed', 'format', 'events', 'vocalStems', 'offsets', 'vocalOffsets', 'mania',
		'codenameNoteTypes',
		'preferredNoteAmount', 'forceJudgements', 'convertMineToNuke',
		'keys', 'lanes', 'arrowSkins', 'trackSwap'
	];
	static var visualFields:Array<String> = [
		'player1', 'player2', 'gf', 'stage', 'songArtist', 'album', 'difficultyRatings',
		'difficultyRating', 'compatMetadata', 'compatPreserveSongTitle', 'stickerPack', 'uiType', 'cutsceneType',
		'isMoody', 'isSpooky', 'isHey', 'isCheer', 'forceLayout',
		'uiLayoutType', 'cutsceneScript', 'cutsceneStoryOnly', 'cutscenePlayOnce',
		'arrowSkin', 'splashSkin', 'disableNoteRGB'
	];
	// These are the fields that require another chart before the normal
	// built-in defaults can make the result playable. Limiting the early-stop
	// check avoids parsing every (potentially large) sibling chart when the
	// selected chart already has its own complete identity.
	static var graphicFields:Array<String> = ['player1', 'player2', 'gf', 'stage'];
	static var registryCache:Map<String, Dynamic> = new Map<String, Dynamic>();
	static var registryLoaded:Map<String, Bool> = new Map<String, Bool>();

	/**
	 * Drop the cached visual registries after an in-session import updates them.
	 *	The importer writes registry files while the game is still running, so a
	 * chart loaded before that write must be able to resolve the new graphics
	 * without requiring a process restart.
	 */
	public static function invalidateVisualRegistryCache():Void {
		registryCache.clear();
		registryLoaded.clear();
	}

	public var song:String;
	public var notes:Array<SwagSection>;
	public var bpm:Int;
	public var needsVoices:Bool = true;
	public var speed:Float = 1;

	public var player1:String = 'bf';
	public var player2:String = 'dad';
	public var stage:String = 'stage';
	public var gf:String = 'gf';
	public var isMoody:Null<Bool> = false;
	public var isSpooky:Null<Bool> = false;
	public var cutsceneType:String = "none";
	public var uiType:String = 'normal';
	public var isHey:Null<Bool> = false;
	public var isCheer:Null<Bool> = false;
	public function new(song, notes, bpm) {
		this.song = song;
		this.notes = notes;
		this.bpm = bpm;
	}

	static function chartHasValue(chart:Dynamic, field:String):Bool {
		if (chart == null || !Reflect.hasField(chart, field))
			return false;
		var value:Dynamic = Reflect.field(chart, field);
		if (value == null)
			return false;
		// Empty source skin IDs are an authored reset to the engine default.
		if (field == 'arrowSkin' || field == 'splashSkin') return value is String;
		return !(value is String) || StringTools.trim(Std.string(value)) != '';
	}

	static function readRegistry(path:String):Dynamic {
		if (registryLoaded.exists(path))
			return registryCache.get(path);
		registryLoaded.set(path, true);
		try {
			var raw = FNFAssets.getJson(path);
			if (raw != null)
				registryCache.set(path, CoolUtil.parseJson(raw));
		} catch (e:Dynamic) {
			trace('Unable to read visual registry ' + path + ': ' + e);
		}
		return registryCache.get(path);
	}

	/**
	 * Registry keys are authored by donor engines, so their case is not a
	 * reliable part of the chart ABI.  Windows hides that mistake while a
	 * native Linux build would otherwise reject the same character/stage/UI.
	 */
	static function registryKey(registry:Dynamic, requested:String):String {
		if (registry == null || requested == null)
			return null;
		var direct = StringTools.trim(requested);
		if (direct == '')
			return null;
		if (Reflect.hasField(registry, direct))
			return direct;
		var wanted = direct.toLowerCase();
		for (key in Reflect.fields(registry))
			if (key.toLowerCase() == wanted)
				return key;
		return null;
	}

	static function registryValue(registry:Dynamic, requested:String):Dynamic {
		var key = registryKey(registry, requested);
		return key == null ? null : Reflect.field(registry, key);
	}

	#if sys
	/** Resolve an authored asset path without changing its spelling in the chart.
	 * This is only a validation helper; the canonical registry key is written to
	 * the runtime chart below so Character/PlayState use the concrete path. */
	static function caseInsensitivePath(path:String):String {
		if (path == null || StringTools.trim(path) == '')
			return path;
		var normalized = Path.normalize(path);
		if (FileSystem.exists(normalized))
			return normalized;
		var parent = Path.directory(normalized);
		var name = Path.withoutDirectory(normalized);
		if (parent == null || parent == '' || parent == normalized || name == null || name == '')
			return normalized;
		var resolvedParent = caseInsensitivePath(parent);
		if (!FileSystem.isDirectory(resolvedParent))
			return normalized;
		try {
			for (entry in FileSystem.readDirectory(resolvedParent))
				if (entry.toLowerCase() == name.toLowerCase())
					return Path.join([resolvedParent, entry]);
		} catch (_:Dynamic) {}
		return normalized;
	}
	#end

	/**
		Resolve one asset path using both the loaded Lime manifest and the native
		filesystem.  FNFAssets already knows how to answer manifest-backed paths;
		the case-folded probe is the small Linux-only bridge for donor charts whose
		registry spelling differs from the imported file spelling.
	*/
	static function resolvedAssetPath(path:String, ?extension:Extensions):String {
		if (path == null || StringTools.trim(path) == '')
			return null;
		var candidates:Array<String> = [path];
		switch (extension) {
			case Json:
				candidates = [path + '.json', path + '.jsonc'];
			case Hscript:
				candidates = [path + '.hscript', path + '.hxs'];
			default:
		}
		for (candidate in candidates) {
			if (FNFAssets.exists(candidate))
				return candidate;
			#if sys
			var resolved = caseInsensitivePath(candidate);
			if (resolved != candidate && (FNFAssets.exists(resolved) || FileSystem.exists(resolved)))
				return resolved;
			#end
		}
		return null;
	}

	static function assetExists(path:String, ?extension:Extensions):Bool {
		return resolvedAssetPath(path, extension) != null;
	}

	/**
		Pure registry/completeness resolver used by the live loader and by the
		read-only importer tests. `probe` receives a fully-qualified relative path
		and must report whether that exact file/folder is available. Keeping the
		selection logic here prevents Song and Character from disagreeing about an
		alias on case-sensitive targets.
	*/
	public static function resolveCharacterVisualFromData(requested:String, registry:Dynamic,
		probe:Dynamic, ?characterRoot:String):CharacterVisualResolution {
		var clean = requested == null ? '' : StringTools.trim(requested);
		var result:CharacterVisualResolution = {
			requested: clean,
			registryName: null,
			selectedRegistryName: null,
			likeName: null,
			implementationName: null,
			assetName: null,
			implementationPath: null,
			assetPath: null,
			assetRootPath: null,
			complete: false,
			diagnosticCode: '',
			diagnostic: ''
		};
		// Modding Plus preload.txt entries use `character:role` to tell the
		// donor engine which slot will consume a warmed character.  The part
		// after the colon is not part of the character id (for example,
		// `fleetway-extras:dad` means the `fleetway-extras` character in the
		// opponent slot).  Resolve that legacy spelling at the shared engine
		// boundary so preload swaps and chart events do not need chart-specific
		// rewrites.  Keep the authored spelling in result.requested/charName.
		var roleSeparator = clean.lastIndexOf(':');
		if (roleSeparator > 0 && roleSeparator < clean.length - 1) {
			var role = clean.substr(roleSeparator + 1).toLowerCase();
			switch (role) {
				case 'bf' | 'boyfriend' | 'player' | 'player1'
					| 'dad' | 'opponent' | 'player2'
					| 'gf' | 'girlfriend' | 'player3':
					clean = StringTools.trim(clean.substr(0, roleSeparator));
				default:
			}
		}
		var fail = function(code:String, message:String):CharacterVisualResolution {
			result.diagnosticCode = code;
			result.diagnostic = message;
			return result;
		};
		if (clean == '')
			return fail('character-id-empty', 'Character id is empty.');
		var normalized = clean.toLowerCase();
		if (normalized == 'nogf' || normalized == 'no-gf' || normalized == 'no_gf') {
			result.registryName = 'gf';
			result.selectedRegistryName = 'gf';
			result.likeName = 'gf';
			result.implementationName = 'gf';
			result.assetName = 'gf';
			result.complete = true;
			return result;
		}
		var root = characterRoot == null || StringTools.trim(characterRoot) == ''
			? 'assets/images/custom_chars/' : StringTools.replace(StringTools.trim(characterRoot), '\\', '/');
		if (!root.endsWith('/'))
			root += '/';
		var implementationFor = function(name:String):String {
			if (name == null || StringTools.trim(name) == '' || probe == null)
				return null;
			for (extension in ['hscript', 'hxs', 'json', 'jsonc']) {
				var path = root + StringTools.trim(name) + '.' + extension;
				if (probe(path) == true)
					return path;
			}
			return null;
		};
		var assetFor = function(name:String):String {
			if (name == null || StringTools.trim(name) == '' || probe == null)
				return null;
			var base = root + StringTools.trim(name);
			for (suffix in ['/char.png', '/char.xml', '/char.json', '/char.txt'])
				if (probe(base + suffix) == true)
					return base + suffix;
			// Some legacy HScripts build a custom atlas path themselves. Their
			// folder may be the only asset root, but an empty folder is never a
			// drawable visual. Importers can leave one behind when the source
			// character refers to media supplied by its original engine.
			#if sys
			if (probe(base) == true && sys.FileSystem.isDirectory(base)) {
				try {
					if (sys.FileSystem.readDirectory(base).length > 0)
						return base;
				} catch (_:Dynamic) {}
			}
			#else
			if (probe(base) == true)
				return base;
			#end
			return null;
		};
		var choose = function(selectedName:String, selectedLike:String,
			implementationName:String, assetName:String, implementationPath:String,
			assetPath:String):Bool {
			if (implementationPath == null || assetPath == null)
				return false;
			result.selectedRegistryName = selectedName;
			result.likeName = selectedLike;
			result.implementationName = implementationName;
			result.assetName = assetName;
			result.implementationPath = implementationPath;
			result.assetPath = assetPath;
			result.assetRootPath = root + assetName;
			result.complete = true;
			result.diagnosticCode = '';
			result.diagnostic = '';
			return true;
		};
		// Legacy Modding Plus packs occasionally carry a complete character
		// implementation without a custom_chars registry row. Accept that local
		// id only when both its implementation and native atlas root are present;
		// never turn an authored id into an arbitrary filesystem path.
		var tryDirect = function(name:String):Bool {
			if (name == null || StringTools.trim(name) == '')
				return false;
			var safe = StringTools.trim(name);
			if (safe.indexOf('/') >= 0 || safe.indexOf('\\') >= 0
				|| safe.indexOf('..') >= 0 || safe.indexOf(':') >= 0)
				return false;
			var implementation = implementationFor(safe);
			var asset = assetFor(safe);
			return implementation != null && asset != null
				&& choose(safe, safe, safe, safe, implementation, asset);
		};
		if (registry == null) {
			if (tryDirect(clean))
				return result;
			return fail('character-registry-missing',
				'Character "' + clean + '" cannot resolve because custom_chars registry is unavailable.');
		}
		var registryName = registryKey(registry, clean);
		if (registryName == null) {
			if (tryDirect(clean))
				return result;
			return fail('character-registry-entry-missing',
				'Character "' + clean + '" has no case-insensitive custom_chars registry entry.');
		}
		result.registryName = registryName;
		var tryEntry = function(selectedName:String, entry:Dynamic):Bool {
			if (entry == null)
				return false;
			var selectedLikeValue:Dynamic = Reflect.field(entry, 'like');
			if (selectedLikeValue == null || StringTools.trim(Std.string(selectedLikeValue)) == '')
				return false;
			var selectedLike = StringTools.trim(Std.string(selectedLikeValue));
			var namedImplementation = implementationFor(selectedName);
			var namedAsset = assetFor(selectedName);
			// A name-specific script is authoritative. If its matching asset root
			// is missing, do not silently replace that authored definition with the
			// `like` character; a complete sibling may still be selected below.
			if (namedImplementation != null)
				return namedAsset != null && choose(selectedName, selectedLike, selectedName,
					selectedName, namedImplementation, namedAsset);
			var sharedImplementation = implementationFor(selectedLike);
			if (sharedImplementation == null)
				return false;
			if (namedAsset != null)
				return choose(selectedName, selectedLike, selectedLike, selectedName,
					sharedImplementation, namedAsset);
			var sharedAsset = assetFor(selectedLike);
			return sharedAsset != null && choose(selectedName, selectedLike, selectedLike,
				selectedLike, sharedImplementation, sharedAsset);
		};

		var entry:Dynamic = Reflect.field(registry, registryName);
		if (entry == null)
			return fail('character-registry-entry-invalid',
				'Character "' + clean + '" registry entry "' + registryName + '" is null.');
		var selected = tryEntry(registryName, entry);
		if (!selected && tryDirect(clean))
			return result;
		var siblingNames:Array<String> = [];
		if (!selected) {
			for (candidate in Reflect.fields(registry)) {
				if (candidate.toLowerCase() == registryName.toLowerCase())
					continue;
				var candidateEntry:Dynamic = Reflect.field(registry, candidate);
				if (candidateEntry == null)
					continue;
				var candidateLike:Dynamic = Reflect.field(candidateEntry, 'like');
				if (candidateLike != null && StringTools.trim(Std.string(candidateLike)).toLowerCase()
					== registryName.toLowerCase())
					siblingNames.push(candidate);
			}
			siblingNames.sort(function(a:String, b:String):Int {
				var wanted = clean.toLowerCase();
				var aPrefix = a.toLowerCase().indexOf(wanted) == 0;
				var bPrefix = b.toLowerCase().indexOf(wanted) == 0;
				if (aPrefix != bPrefix)
					return aPrefix ? -1 : 1;
				return a.toLowerCase() < b.toLowerCase() ? -1 : (a.toLowerCase() > b.toLowerCase() ? 1 : 0);
			});
			for (candidate in siblingNames) {
				if (tryEntry(candidate, Reflect.field(registry, candidate))) {
					selected = true;
					break;
				}
			}
		}
		if (selected)
			return result;

		var requestedLike:Dynamic = Reflect.field(entry, 'like');
		var likeName = requestedLike == null ? '' : StringTools.trim(Std.string(requestedLike));
		result.likeName = likeName;
		if (likeName == '')
			return fail('character-registry-like-missing',
				'Character "' + clean + '" (registry "' + registryName + '") has no usable like/implementation alias.');
		var namedImplementation = implementationFor(registryName);
		var namedAsset = assetFor(registryName);
		var diagnosticCode = namedImplementation != null && namedAsset == null
			? 'character-asset-missing'
			: namedImplementation == null && implementationFor(likeName) == null
			? 'character-implementation-missing'
			: siblingNames.length > 0
			? 'character-sibling-incomplete'
			: 'character-asset-missing';
		var checked = siblingNames.length == 0 ? '' : ' Checked sibling aliases: ' + siblingNames.join(', ') + '.';
		return fail(diagnosticCode,
			'Character "' + clean + '" (registry "' + registryName + '") is incomplete: '
			+ (namedImplementation == null ? 'missing animation implementation' : 'missing character asset root')
			+ (likeName == '' ? '' : '; like="' + likeName + '".') + checked);
	}

	/**
		Resolve a character only from the selected imported manifest root. The
		optional global fallback is explicit because the ordinary custom-character
		registry is shared by every import and cannot distinguish sibling owners.
	*/
	public static function resolveCharacterVisualInManifest(name:String, manifestRoot:String,
		allowNativeFallback:Bool = false, ?ownerEngine:String):CharacterVisualResolution {
		var cleanRoot = safeCharacterManifestRoot(manifestRoot);
		if (cleanRoot == '') {
			var invalid = resolveCharacterVisualFromData(name, null,
				function(_path:String):Bool return false,
				'assets/imported_mods/invalid/images/custom_chars/');
			invalid.complete = false;
			invalid.diagnosticCode = 'character-manifest-root-invalid';
			invalid.diagnostic = 'Character "' + (name == null ? '' : name)
				+ '" cannot resolve because its imported manifest root is invalid.';
			return invalid;
		}
		if (ownerEngine != null && ownerEngine.toLowerCase() == ImportEngine.NIGHTMARE_VISION.toLowerCase()) {
			var definition = NightmareVisionCharacterData.load(cleanRoot, name);
			var imageRoot = definition == null ? null
				: NightmareVisionCharacterData.imageRoot(cleanRoot, definition);
			if (definition != null && imageRoot != null) {
				var owned = resolveCharacterVisualFromData(name, null,
					function(_path:String):Bool return false, cleanRoot + '/images/characters/');
				owned.registryName = name;
				owned.selectedRegistryName = name;
				owned.implementationName = name;
				owned.assetName = name;
				owned.implementationPath = NightmareVisionCharacterData.definitionPath(cleanRoot, name);
				owned.assetPath = imageRoot;
				owned.assetRootPath = imageRoot;
				owned.complete = true;
				owned.diagnosticCode = '';
				owned.diagnostic = '';
				return owned;
			}
			// Source base actors may come from the bundled core. A missing custom
			// actor must never borrow the same id from another imported package.
			if (definition == null && allowNativeFallback
				&& (name == 'bf' || name == 'dad' || name == 'gf'))
				return resolveCharacterVisual(name);
			var missing = resolveCharacterVisualFromData(name, null,
				function(_path:String):Bool return false, cleanRoot + '/images/characters/');
			missing.complete = false;
			missing.diagnosticCode = definition == null ? 'nightmare-vision-character-missing'
				: 'nightmare-vision-character-image-missing';
			missing.diagnostic = 'Nightmare Vision character "' + name
				+ '" is missing its owner definition or image atlas in ' + cleanRoot + '.';
			return missing;
		}

		var characterRoot = cleanRoot + '/images/custom_chars/';
		var registry:Dynamic = readCharacterRegistryInManifest(cleanRoot);
		var scoped = resolveCharacterVisualFromData(name, registry,
			function(path:String):Bool {
				return path != null && path.startsWith(cleanRoot + '/')
					&& FNFAssets.exists(path);
			}, characterRoot);
		if (scoped.complete || !allowNativeFallback)
			return scoped;
		// Codename mod folders commonly reference characters whose atlases ship
		// with Codename itself (for example its base playable cast). The imported
		// XML still owns camera/flip metadata, but an empty generated visual must
		// use an exact native character when one is available. Keep other scoped
		// rows authoritative: a similarly named global mod cannot stand in for
		// missing Psych or custom Codename art.
		var scopedName = registryKey(registry, name);
		if (scopedName != null) {
			var row:Dynamic = Reflect.field(registry, scopedName);
			if (row != null && Reflect.field(row, 'codenameCharacter') != null
				&& scoped.diagnosticCode == 'character-asset-missing') {
				var native = resolveCharacterVisual(name);
				var wanted = StringTools.trim(name == null ? '' : name).toLowerCase();
				if (native.complete && native.selectedRegistryName != null
					&& Std.string(native.selectedRegistryName).toLowerCase() == wanted
					&& native.implementationName != null
					&& Std.string(native.implementationName).toLowerCase() == wanted
					&& native.assetName != null && Std.string(native.assetName).toLowerCase() == wanted
					&& native.assetRootPath != null
					&& Std.string(native.assetRootPath).startsWith('assets/images/custom_chars/'))
					return native;
			}
			return scoped;
		}
		// V-Slice package ids can collide with another imported mod's global
		// custom_chars row. When the selected owner has no row, only allow the
		// exact destination-native character library ids to cross that boundary.
		// Custom/missing package ids stay explicit instead of borrowing a global
		// character which may belong to an unrelated import.
		if (ownerEngine != null && ownerEngine.toLowerCase() == 'v-slice')
			return isVSliceBaseCharacterReference(name) ? resolveCharacterVisual(name) : scoped;
		return resolveCharacterVisual(name);
	}

	static function isVSliceBaseCharacterReference(name:String):Bool {
		var clean = StringTools.trim(name == null ? '' : name);
		var separator = clean.lastIndexOf(':');
		if (separator > 0 && separator < clean.length - 1)
			clean = StringTools.trim(clean.substr(0, separator));
		return EngineCompat.isVSliceBaseCharacterId(clean);
	}

	/** Return the registry row owned by one safe imported manifest root. */
	public static function characterVisualRegistryEntryInManifest(name:String,
		manifestRoot:String):Dynamic {
		var cleanRoot = safeCharacterManifestRoot(manifestRoot);
		if (cleanRoot == '')
			return null;
		var registry = readCharacterRegistryInManifest(cleanRoot);
		var key = registryKey(registry, name);
		return key == null ? null : Reflect.field(registry, key);
	}

	static function readCharacterRegistryInManifest(cleanRoot:String):Dynamic {
		if (cleanRoot == '')
			return null;
		var characterRoot = cleanRoot + '/images/custom_chars/';
		for (extension in ['.jsonc', '.json']) {
			var registryPath = characterRoot + 'custom_chars' + extension;
			if (!FNFAssets.exists(registryPath))
				continue;
			try {
				var source = FNFAssets.getText(registryPath);
				if (source != null)
					return CoolUtil.parseJson(source);
			} catch (_:Dynamic) {}
		}
		return null;
	}

	/** Only the selected owner may supply scoped character assets. */
	public static function characterRootForSong(songName:String, ?requiredEngine:String):String {
		#if sys
		if (songName == null || StringTools.trim(songName) == '' || songName.indexOf('/') >= 0
			|| songName.indexOf('\\') >= 0 || songName.indexOf('..') >= 0 || songName.indexOf(':') >= 0)
			return '';
		var manifestPath = 'assets/data/' + songName.toLowerCase() + '/'
			+ CompatScriptManifest.FILE_NAME;
		if (!FNFAssets.exists(manifestPath))
			return '';
		try {
			var manifest = CompatScriptManifest.parse(FNFAssets.getText(manifestPath));
			var selected = safeCharacterManifestRoot(CompatScriptManifest.selectedRoot(manifest));
			if (selected == '')
				return '';
			for (root in CompatScriptManifest.rootsInPrecedence(manifest))
				if (root != null && root.path == selected && root.engine != null) {
					var engine = root.engine.toLowerCase();
					var supportedOwnerEngine = engine == ImportEngine.PSYCH.toLowerCase()
						|| engine == ImportEngine.CODENAME.toLowerCase()
						|| engine == ImportEngine.MODDING_PLUS.toLowerCase()
						|| engine == ImportEngine.NIGHTMARE_VISION.toLowerCase()
						|| engine == ImportEngine.V_SLICE.toLowerCase();
					if (supportedOwnerEngine
						&& (requiredEngine == null || engine == requiredEngine.toLowerCase()))
						return selected;
				}
		} catch (_:Dynamic) {}
		#end
		return '';
	}

	static function psychCharacterRootForSong(songName:String):String {
		return characterRootForSong(songName, ImportEngine.PSYCH);
	}

	public static function currentCharacterRoot():String {
		if (PlayState.instance == null || FlxG.state != PlayState.instance || PlayState.SONG == null)
			return '';
		return characterRootForSong(storageFolder(PlayState.SONG));
	}

	/** Engine identity for the selected character owner, used to keep fallback
	 * rules source-safe when multiple imports use the same character id. */
	public static function characterOwnerEngineForSong(songName:String):String {
		#if sys
		if (songName == null || StringTools.trim(songName) == '' || songName.indexOf('/') >= 0
			|| songName.indexOf('\\') >= 0 || songName.indexOf('..') >= 0 || songName.indexOf(':') >= 0)
			return '';
		var manifestPath = 'assets/data/' + songName.toLowerCase() + '/'
			+ CompatScriptManifest.FILE_NAME;
		if (!FNFAssets.exists(manifestPath))
			return '';
		try {
			var manifest = CompatScriptManifest.parse(FNFAssets.getText(manifestPath));
			var selected = safeCharacterManifestRoot(CompatScriptManifest.selectedRoot(manifest));
			if (selected == '')
				return '';
			for (root in CompatScriptManifest.rootsInPrecedence(manifest))
				if (root != null && root.path == selected && root.engine != null)
					return root.engine;
		} catch (_:Dynamic) {}
		#end
		return '';
	}

	/** Selected Psych assets apply only while their owning PlayState is active. */
	public static function currentPsychCharacterRoot():String {
		if (PlayState.instance == null || FlxG.state != PlayState.instance || PlayState.SONG == null)
			return '';
		return psychCharacterRootForSong(storageFolder(PlayState.SONG));
	}

	/** Gameplay visuals prefer their selected owner and keep native fallback. */
	public static function resolveCharacterVisualForCurrentSong(name:String):CharacterVisualResolution {
		var root = currentCharacterRoot();
		return root == '' ? resolveCharacterVisual(name)
			: resolveCharacterVisualInManifest(name, root, true,
				characterOwnerEngineForSong(storageFolder(PlayState.SONG)));
	}

	/** Registry metadata follows the same selected owner as the gameplay atlas. */
	public static function characterVisualRegistryEntryForCurrentSong(name:String):Dynamic {
		var root = currentCharacterRoot();
		if (root != '') {
			if (characterOwnerEngineForSong(storageFolder(PlayState.SONG)).toLowerCase()
				== ImportEngine.NIGHTMARE_VISION.toLowerCase())
				return NightmareVisionCharacterData.load(root, name);
			var scoped = characterVisualRegistryEntryInManifest(name, root);
			if (scoped != null)
				return scoped;
		}
		var registry = readRegistry('assets/images/custom_chars/custom_chars');
		var key = registryKey(registry, name);
		return key == null ? null : Reflect.field(registry, key);
	}

	static function safeCharacterManifestRoot(root:String):String {
		if (root == null)
			return '';
		var clean = StringTools.replace(StringTools.trim(root), '\\', '/');
		while (clean.endsWith('/'))
			clean = clean.substr(0, clean.length - 1);
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0)
			return '';
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..')
				return '';
		var prefix = CompatScriptManifest.ROOT_PREFIX + '/';
		return clean.startsWith(prefix) ? clean : '';
	}

	/** Ensure an injected visual descriptor belongs to the requested character. */
	public static function characterVisualResolutionMatches(name:String,
		resolution:Dynamic):Bool {
		if (resolution == null || Reflect.field(resolution, 'complete') != true)
			return false;
		var requested:Dynamic = Reflect.field(resolution, 'requested');
		return characterVisualIdentity(name) == characterVisualIdentity(
			requested == null ? '' : Std.string(requested));
	}

	static function characterVisualIdentity(value:String):String {
		var clean = StringTools.trim(value == null ? '' : value);
		var separator = clean.lastIndexOf(':');
		if (separator > 0 && separator < clean.length - 1) {
			var role = clean.substr(separator + 1).toLowerCase();
			switch (role) {
				case 'bf' | 'boyfriend' | 'player' | 'player1'
					| 'dad' | 'opponent' | 'player2' | 'gf' | 'girlfriend' | 'player3':
					clean = StringTools.trim(clean.substr(0, separator));
				default:
			}
		}
		var normalized = clean.toLowerCase();
		return normalized == 'nogf' || normalized == 'no-gf' || normalized == 'no_gf'
			? 'gf' : normalized;
	}

	/** Resolve a live registry entry through the manifest-aware path probe. */
	public static function resolveCharacterVisual(name:String):CharacterVisualResolution {
		var root = 'assets/images/custom_chars/';
		var result = resolveCharacterVisualFromData(name, readRegistry(root + 'custom_chars'),
			function(path:String):Bool return resolvedAssetPath(path) != null);
		if (!result.complete)
			return result;
		if (result.requested != null) {
			var normalized = result.requested.toLowerCase();
			if (normalized == 'nogf' || normalized == 'no-gf' || normalized == 'no_gf')
				return result;
		}
		if (result.implementationPath != null)
			result.implementationPath = resolvedAssetPath(result.implementationPath);
		if (result.assetPath != null)
			result.assetPath = resolvedAssetPath(result.assetPath);
		#if sys
		var candidateRoot = caseInsensitivePath(root + result.assetName);
		if (candidateRoot != null && FileSystem.isDirectory(candidateRoot))
			result.assetRootPath = candidateRoot;
		#end
		if (result.assetRootPath == null || StringTools.trim(result.assetRootPath) == '') {
			if (result.assetPath != null) {
				var slash = result.assetPath.lastIndexOf('/');
				result.assetRootPath = slash > 0 ? result.assetPath.substr(0, slash) : root + result.assetName;
			}
		}
		if (result.implementationPath == null || result.assetPath == null) {
			result.complete = false;
			result.diagnosticCode = 'character-path-resolution-failed';
			result.diagnostic = 'Character "' + result.requested + '" selected registry "'
				+ result.selectedRegistryName + '" but its manifest/filesystem paths could not be resolved.';
		}
		return result;
	}

	static function validCharacter(name:String):Bool {
		return resolveCharacterVisual(name).complete;
	}

	static function validStage(name:String):Bool {
		if (name == null || StringTools.trim(name) == '')
			return false;
		var stages = readRegistry('assets/images/custom_stages/custom_stages');
		var registryName = registryKey(stages, name);
		// Legacy Modding Plus packs sometimes ship a stage implementation and
		// its hscriptPath asset folder without adding the authored id to the
		// registry.  The importer already discovers/copies that direct script;
		// accept only a plain local id here so the chart can retain its authored
		// stage without turning this validator into an arbitrary script loader.
		if (registryName == null) {
			var directName = StringTools.trim(name);
			if (directName.indexOf('/') >= 0 || directName.indexOf('\\') >= 0
				|| directName.indexOf('..') >= 0 || directName.indexOf(':') >= 0)
				return false;
			return assetExists('assets/images/custom_stages/' + directName, Extensions.Hscript);
		}
		var script:Dynamic = Reflect.field(stages, registryName);
		if (script == null || StringTools.trim(Std.string(script)) == '')
			return false;
		var scriptName = Std.string(script);
		if (scriptName.toLowerCase().endsWith('.hscript'))
			scriptName = scriptName.substr(0, scriptName.length - 8);
		return assetExists('assets/images/custom_stages/' + scriptName, Extensions.Hscript);
	}

	/** Accept a Psych stage only when this song's manifest owns a direct stage script. */
	static function validImportedPsychStage(name:String, folder:String):Bool {
		if (name == null || folder == null)
			return false;
		var stageName = StringTools.trim(name);
		var songFolder = StringTools.trim(folder).toLowerCase();
		if (stageName == '' || songFolder == '' || stageName.indexOf('/') >= 0
			|| stageName.indexOf('\\') >= 0 || stageName.indexOf('..') >= 0 || stageName.indexOf(':') >= 0)
			return false;
		#if sys
		try {
			var manifestPath = 'assets/data/' + songFolder + '/' + CompatScriptManifest.FILE_NAME;
			if (!FNFAssets.exists(manifestPath))
				return false;
			var manifest:CompatScriptManifestData = CompatScriptManifest.parse(FNFAssets.getText(manifestPath));
			var chart:Dynamic = {song: songFolder, stage: stageName};
			for (root in CompatScriptManifest.rootsInPrecedence(manifest)) {
				if (root == null || root.path == null || root.engine == null
					|| root.engine.toLowerCase().indexOf('psych') < 0
					|| !FileSystem.isDirectory(root.path))
					continue;
				var plan = PsychScriptDiscovery.discover(root.path, songFolder, chart);
				for (entry in plan.scripts)
					if (entry != null && entry.scope == PsychScriptDiscovery.STAGE
						&& entry.path != null && FileSystem.exists(entry.path))
						return true;
			}
		} catch (_:Dynamic) {
			// Bad optional compatibility metadata must not make chart loading fail.
			return false;
		}
		#end
		return false;
	}

	static function validUIType(name:String):Bool {
		if (name == null || StringTools.trim(name) == '')
			return false;
		var ui = readRegistry('assets/images/custom_ui/ui_packs/ui');
		var registryName = registryKey(ui, name);
		if (registryName == null)
			return false;
		var entry:Dynamic = Reflect.field(ui, registryName);
		var uses:Dynamic = entry == null ? null : Reflect.field(entry, 'uses');
		if (uses == null || StringTools.trim(Std.string(uses)) == '')
			return false;
		var pack = 'assets/images/custom_ui/ui_packs/' + Std.string(uses) + '/';
		// Strumline can use either the regular or pixel sheet. Checking one
		// concrete asset catches stale registry entries without walking packs.
		return assetExists(pack + 'NOTE_assets.png')
			|| assetExists(pack + 'arrows-pixels.png');
	}

	static function validCutscene(name:String):Bool {
		if (name == null || StringTools.trim(name) == '')
			return false;
		var normalized = StringTools.trim(name);
		if (normalized.toLowerCase() == 'none' || normalized.toLowerCase() == 'senpai' || normalized.toLowerCase() == 'angry-senpai')
			return true;
		var cutscenes = readRegistry('assets/images/custom_cutscenes/cutscenes');
		var registryName = registryKey(cutscenes, normalized);
		if (registryName == null)
			return false;
		var script:Dynamic = Reflect.field(cutscenes, registryName);
		if (script == null || StringTools.trim(Std.string(script)) == '')
			return false;
		var scriptName = Std.string(script);
		if (scriptName.toLowerCase().endsWith('.hscript'))
			scriptName = scriptName.substr(0, scriptName.length - 8);
		return assetExists('assets/images/custom_cutscenes/' + scriptName, Extensions.Hscript);
	}

	static function validLayout(name:String):Bool {
		if (name == null || StringTools.trim(name) == '')
			return false;
		var normalized = StringTools.trim(name);
		if (normalized == 'none' || normalized == 'normal')
			return true;
		return assetExists('assets/images/custom_ui/ui_layouts/' + normalized + '/' + normalized, Extensions.Hscript)
			|| assetExists('assets/images/custom_ui/ui_layouts/' + normalized, Extensions.Hscript);
	}

	static function isValidVisualValue(field:String, value:Dynamic):Bool {
		if (field == 'arrowSkin' || field == 'splashSkin') return value is String;
		if (field == 'disableNoteRGB') return value == true || value == false;
		if (value == null || ((value is String) && StringTools.trim(Std.string(value)) == ''))
			return false;
		return switch (field) {
			case 'player1' | 'player2' | 'gf': validCharacter(Std.string(value));
			case 'stage': validStage(Std.string(value));
			case 'uiType': validUIType(Std.string(value));
			case 'cutsceneType': validCutscene(Std.string(value));
			case 'forceLayout' | 'uiLayoutType': validLayout(Std.string(value));
			case 'stageID': value >= 0;
			case 'isMoody' | 'isSpooky' | 'isHey' | 'isCheer': value == true || value == false;
			default: true;
		};
	}

	// Merge a selected chart with visual candidates. The optional validity map
	// exists for extract-and-interpret regression tests; the live loader uses
	// the registry-backed validator above. A requested visual normally wins
	// when it is present and resolvable. Imported Psych charts keep explicit
	// actor/stage IDs even when their media is missing, so the runtime reports
	// the missing source dependency instead of silently borrowing a sibling.
	public static function resolveChartData(requested:Dynamic, fallbackCharts:Array<Dynamic>, ?baseChart:Dynamic,
		?validity:Map<String, Bool>, ?preserveAuthoredGraphics:Bool = false):Dynamic {
		var result:Dynamic = baseChart == null ? requested : baseChart;
		if (result == null)
			result = {};
		for (field in gameplayFields) {
			if (chartHasValue(requested, field))
				Reflect.setField(result, field, Reflect.field(requested, field));
		}
		// Retained source notes belong exclusively to this difficulty, including
		// an absent list. Never borrow unsupported actors' notes from a sibling.
		if (chartHasValue(requested, 'codenameUnsupportedNotes'))
			Reflect.setField(result, 'codenameUnsupportedNotes', Reflect.field(requested, 'codenameUnsupportedNotes'));
		else
			Reflect.deleteField(result, 'codenameUnsupportedNotes');
		// V-Slice source-only rows are difficulty-owned editor metadata, just like
		// Codename's retained unsupported line rows. Explicit empty arrays clear
		// inherited data; an absent field must not borrow a sibling's rows.
		if (chartHasValue(requested, 'vSliceUnroutedNotes'))
			Reflect.setField(result, 'vSliceUnroutedNotes', Reflect.field(requested, 'vSliceUnroutedNotes'));
		else
			Reflect.deleteField(result, 'vSliceUnroutedNotes');
		var stageAuthored = false;
		for (field in visualFields) {
			var selected:Dynamic = null;
			var found = false;
			var selectedStageAuthored = false;
			if (chartHasValue(requested, field)
				&& ((preserveAuthoredGraphics && graphicFields.indexOf(field) >= 0)
					|| visualValueIsValid(field, Reflect.field(requested, field), validity))) {
				selected = Reflect.field(requested, field);
				found = true;
				selectedStageAuthored = field == 'stage';
			} else if (chartHasValue(result, field) && visualValueIsValid(field, Reflect.field(result, field), validity)) {
				selected = Reflect.field(result, field);
				found = true;
				selectedStageAuthored = field == 'stage' && baseChart != null;
			} else if (fallbackCharts != null) {
				for (candidate in fallbackCharts) {
					if (chartHasValue(candidate, field) && visualValueIsValid(field, Reflect.field(candidate, field), validity)) {
						selected = Reflect.field(candidate, field);
						found = true;
						break;
					}
				}
			}
			if (found)
				Reflect.setField(result, field, selected);
			if (found && field == 'stage') stageAuthored = selectedStageAuthored;
		}
		// This is set from the merge decision, rather than trusted from source
		// JSON, so an inferred legacy stage can be distinguished from a chart or
		// selected default that actually authored its stage identity.
		Reflect.setField(result, 'compatStageAuthored', stageAuthored);
		// Stage IDs select difficulty-specific stage variants (for example the
		// erect background). They must come from the selected chart or the
		// difficulty's runtime default; borrowing one from any sibling lets a
		// higher-difficulty chart change the visuals of hard/easy charts.
		if (chartHasValue(requested, 'stageID')
			&& visualValueIsValid('stageID', Reflect.field(requested, 'stageID'), validity))
			Reflect.setField(result, 'stageID', Reflect.field(requested, 'stageID'));
		else if (baseChart != null)
			Reflect.deleteField(result, 'stageID');
		return result;
	}

	static function visualValueIsValid(field:String, value:Dynamic, validity:Map<String, Bool>):Bool {
		if (validity != null)
			return validity.exists(field + '=' + Std.string(value)) && validity.get(field + '=' + Std.string(value)) == true;
		return isValidVisualValue(field, value);
	}

	/** Precompute chart-local validity so Psych stage scripts remain scoped to
	 * the selected chart/default chart and never become a broad filesystem lookup. */
	static function chartVisualValidity(folder:String, requested:Dynamic, fallbackCharts:Array<Dynamic>,
		baseChart:Dynamic):Map<String, Bool> {
		var validity:Map<String, Bool> = new Map<String, Bool>();
		var ownerRoot = characterRootForSong(folder);
		var nightmareVisionOwner = characterOwnerEngineForSong(folder).toLowerCase()
			== ImportEngine.NIGHTMARE_VISION.toLowerCase();
		var ownedCharacters = readCharacterRegistryInManifest(ownerRoot);
		var candidates:Array<Dynamic> = [];
		if (requested != null)
			candidates.push(requested);
		if (fallbackCharts != null)
			for (candidate in fallbackCharts)
				if (candidate != null && candidates.indexOf(candidate) < 0)
					candidates.push(candidate);
		if (baseChart != null && candidates.indexOf(baseChart) < 0)
			candidates.push(baseChart);
		for (candidate in candidates) {
			var mayUseImportedStage = candidate == requested || candidate == baseChart;
			for (field in visualFields) {
				if (!chartHasValue(candidate, field))
					continue;
				var value:Dynamic = Reflect.field(candidate, field);
				var valid = isValidVisualValue(field, value);
				// An owned definition keeps its authored identity even if its media
				// is incomplete; Character reports that dependency at resolution.
				if (['player1', 'player2', 'gf'].indexOf(field) >= 0
					&& registryKey(ownedCharacters, Std.string(value)) != null) valid = true;
				if (!valid && nightmareVisionOwner && ['player1', 'player2', 'gf'].indexOf(field) >= 0
					&& NightmareVisionCharacterData.load(ownerRoot, Std.string(value)) != null) valid = true;
				if (field == 'stage' && ownedStageEntry(folder, Std.string(value)) != null)
					valid = true;
				if (!valid && nightmareVisionOwner && field == 'stage') {
					try valid = NightmareVisionStageData.getStageFile(ownerRoot, Std.string(value)) != null
					catch (error:Dynamic)
						trace('[nightmare-vision-stage-data-error] ' + Std.string(value) + ': ' + Std.string(error));
				}
				if (field == 'cutsceneType' && ownedCutsceneEntry(folder, Std.string(value)) != null)
					valid = true;
				if (!valid && field == 'stage' && mayUseImportedStage)
					valid = validImportedPsychStage(Std.string(value), folder);
				if (valid)
					validity.set(field + '=' + Std.string(value), true);
			}
			if (chartHasValue(candidate, 'stageID')) {
				var stageID:Dynamic = Reflect.field(candidate, 'stageID');
				if (isValidVisualValue('stageID', stageID))
					validity.set('stageID=' + Std.string(stageID), true);
			}
		}
		return validity;
	}

	static function ownedStageEntry(folder:String, name:String):Dynamic {
		return ImportedStageRegistry.resolve(folder, name,
			function(path) return FNFAssets.exists(path),
			function(path) return FNFAssets.getText(path),
			function(text) return CoolUtil.parseJson(text));
	}

	static function ownedCutsceneEntry(folder:String, name:String):Dynamic {
		return ImportedCutsceneRegistry.resolve(folder, name,
			function(path) return FNFAssets.exists(path),
			function(path) return FNFAssets.getText(path),
			function(text) return CoolUtil.parseJson(text));
	}

	/** Replace a case variant with the concrete registry spelling used by the
	 * runtime.  The source chart remains untouched; this only makes the loaded
	 * native object safe for Character/PlayState path lookups on Linux. */
	static function normalizeVisualFields(chart:Dynamic, ?folder:String):Void {
		if (chart == null)
			return;
		var ownerRoot = characterRootForSong(folder);
		var ownedCharacters:Dynamic = ownerRoot == '' ? null
			: readCharacterRegistryInManifest(ownerRoot);
		var nativeCharacters = readRegistry('assets/images/custom_chars/custom_chars');
		for (field in visualFields) {
			if (!chartHasValue(chart, field))
				continue;
			var value = StringTools.trim(Std.string(Reflect.field(chart, field)));
			var normalized:String = null;
			switch (field) {
				case 'player1' | 'player2' | 'gf':
					var lower = value.toLowerCase();
					if (lower == 'nogf' || lower == 'no-gf' || lower == 'no_gf')
						normalized = 'no-gf';
					else
						normalized = registryKey(ownedCharacters, value);
					if (normalized == null)
						normalized = registryKey(nativeCharacters, value);
				case 'stage':
					var owned = ownedStageEntry(folder, value);
					normalized = owned == null
						? registryKey(readRegistry('assets/images/custom_stages/custom_stages'), value) : owned.name;
				case 'uiType':
					normalized = registryKey(readRegistry('assets/images/custom_ui/ui_packs/ui'), value);
				case 'cutsceneType':
					var lowerCutscene = value.toLowerCase();
					if (lowerCutscene == 'none')
						normalized = 'none';
					else if (lowerCutscene == 'senpai')
						normalized = 'senpai';
					else if (lowerCutscene == 'angry-senpai')
						normalized = 'angry-senpai';
					else {
						var ownedCutscene = ownedCutsceneEntry(folder, value);
						normalized = ownedCutscene == null
							? registryKey(readRegistry('assets/images/custom_cutscenes/cutscenes'), value)
							: ownedCutscene.name;
					}
				default:
			}
			if (normalized != null && normalized != '')
				Reflect.setField(chart, field, normalized);
		}
	}

	static function hasGraphicVisuals(chart:Dynamic):Bool {
		if (chart == null)
			return false;
		for (field in graphicFields) {
			if (!chartHasValue(chart, field) || !isValidVisualValue(field, Reflect.field(chart, field)))
				return false;
		}
		return true;
	}

	static function readChart(folder:String, chartName:String):Dynamic {
		var path = 'assets/data/' + folder + '/' + chartName + '.json';
		if (!FNFAssets.exists(path))
			return null;
		try {
			var rawJson = FNFAssets.getText(path).trim();
			while (rawJson.length > 0 && !rawJson.endsWith('}'))
				rawJson = rawJson.substr(0, rawJson.length - 1);
			if (rawJson.length == 0)
				return null;
			return parseJSONshit(rawJson);
		} catch (e:Dynamic) {
			trace('Unable to read chart ' + path + ': ' + e);
			return null;
		}
	}

	/**
		Return the engine that supplied an imported chart, when the destination
		compatibility manifest records one.  The chart itself remains the source
		of gameplay data; this small provenance lookup only selects an engine-level
		ABI adapter for legacy anonymous note kinds.
	*/
	#if sys
	static function compatibilityEngine(folder:String, chart:Dynamic):String {
		var read = function(value:Dynamic):String {
			if (value == null)
				return '';
			var text = StringTools.trim(Std.string(value));
			return text.toLowerCase() == 'null' ? '' : text;
		};
		var metadata:Dynamic = chart == null ? null : Reflect.field(chart, 'compatMetadata');
		var engine = read(metadata == null ? null : Reflect.field(metadata, 'engine'));
		if (engine == '')
			engine = read(chart == null ? null : Reflect.field(chart, 'engine'));
		if (engine != '')
			return engine;
		if (folder == null || StringTools.trim(folder) == '')
			return '';
		var manifestPath = 'assets/data/' + folder + '/' + CompatScriptManifest.FILE_NAME;
		if (!FNFAssets.exists(manifestPath))
			return '';
		try {
			var manifest = CompatScriptManifest.parse(FNFAssets.getText(manifestPath));
			for (root in CompatScriptManifest.rootsInPrecedence(manifest))
				if (root != null && root.engine != null && StringTools.trim(root.engine) != '')
					return StringTools.trim(root.engine);
		} catch (error:Dynamic) {
			trace('Unable to read chart compatibility manifest ' + manifestPath + ': ' + error);
		}
		return '';
	}
	#end

	static function addChartCandidate(names:Array<String>, name:String):Void {
		if (name != null && StringTools.trim(name) != '' && !names.contains(name))
			names.push(name);
	}

	static function getChartCandidates(folder:String, input:String, diffName:String):Array<String> {
		var names:Array<String> = [];
		var defaultName = '';
		try {
			defaultName = DifficultyManager.getDefaultFromName(diffName);
		} catch (e:Dynamic) {
			// The loader is also used by lightweight tools before the title state
			// initializes DifficultyManager; normal/sibling fallback still works.
		}
		if (defaultName != null && StringTools.trim(defaultName) != '')
			addChartCandidate(names, folder + '-' + defaultName.toLowerCase());
		addChartCandidate(names, folder);

		#if sys
		var chartDir = 'assets/data/' + folder;
		if (FileSystem.exists(chartDir)) {
			try {
				for (entry in FileSystem.readDirectory(chartDir)) {
					var lower = entry.toLowerCase();
					if (!lower.endsWith('.json'))
						continue;
					var stem = lower.substr(0, lower.length - 5);
					if (stem == folder || stem.startsWith(folder + '-'))
						addChartCandidate(names, stem);
				}
			} catch (e:Dynamic) {
				trace('Unable to enumerate chart candidates for ' + folder + ': ' + e);
			}
			}
		#else
			for (difficulty in DifficultyManager.getDifficultyNames()) {
				addChartCandidate(names, folder + '-' + difficulty.toLowerCase());
			}
		#end
		// The requested file is always parsed separately and must not become its
		// own fallback/base candidate.
		names.remove(input);
		return names;
	}

	public static function loadFromJson(jsonInput:String, ?folder:String):SwagSong {
		if (folder == null || StringTools.trim(folder) == '')
			folder = jsonInput;
		var folderLower = folder.toLowerCase();
		var inputLower = jsonInput.toLowerCase();
		var diffName = inputLower == folderLower ? 'normal' : inputLower.startsWith(folderLower + '-')
			? inputLower.substr(folderLower.length + 1) : inputLower.split('-').pop();
		var requestedJson:Dynamic = readChart(folderLower, inputLower);
		if (requestedJson == null)
			throw 'Song chart does not exist or could not be parsed: assets/data/' + folderLower + '/' + inputLower + '.json';

		var fallbackCharts:Array<Dynamic> = [];
		var baseChart:Dynamic = null;
		var isNormalChart = inputLower == folderLower;
		for (candidateName in getChartCandidates(folderLower, inputLower, diffName)) {
			var candidate = readChart(folderLower, candidateName);
			if (candidate == null)
				continue;
			fallbackCharts.push(candidate);
			if (!isNormalChart && baseChart == null)
				baseChart = candidate;
		}
		var validity = chartVisualValidity(folderLower, requestedJson, fallbackCharts, baseChart);
		var preserveAuthoredGraphics = false;
		#if sys
		var compatibility = compatibilityEngine(folderLower, requestedJson).toLowerCase();
		preserveAuthoredGraphics = compatibility.indexOf('psych') >= 0
			|| compatibility == ImportEngine.NIGHTMARE_VISION.toLowerCase();
		#end
		var parsedJson:Dynamic = resolveChartData(requestedJson, fallbackCharts, baseChart,
			validity, preserveAuthoredGraphics);
		var parsedSongName = chartHasValue(parsedJson, 'song') ? Std.string(parsedJson.song) : folderLower;
		if ((!chartHasValue(parsedJson, 'stage')
			|| !visualValueIsValid('stage', parsedJson.stage, validity))
			&& !(preserveAuthoredGraphics && chartHasValue(requestedJson, 'stage'))) {
			// sw-switch case :fuckboy:
			parsedJson.stage = switch (parsedSongName.toLowerCase()) {
				case 'spookeez' | 'monster' | 'south':
					'spooky';
				case 'philly' | 'pico' | 'blammed':
					'philly';
				case 'milf' | 'high' | 'satin-panties':
					'limo';
				case 'cocoa' | 'eggnog':
					'mall';
				case 'winter-horrorland':
					'mallEvil';
				case 'senpai' | 'roses':
					'school';
				case 'thorns':
					'schoolEvil';
				case 'ugh' | 'stress' | 'guns':
					'tank';
				case 'darnell' | 'lit-up' | '2hot':
					'philly-streets';
				default:
					'stage';
			}
		}
		// Validity keys use the chart's authored spelling. A registry stage such
		// as auditorHell normalizes to auditorhell on Linux; checking the old
		// validity map after normalization would replace it with the default.
		normalizeVisualFields(parsedJson, folderLower);
		// Keep an authored character id intact when its visual dependency is
		// incomplete. Character owns the final safe bootstrap and emits the
		// precise dependency diagnostic; replacing the id here would erase the
		// chart's provenance before that resolver can select a sibling alias.
		if (!chartHasValue(parsedJson, 'player1'))
			parsedJson.player1 = 'bf';
		if (!chartHasValue(parsedJson, 'player2'))
			parsedJson.player2 = 'dad';
		if (parsedJson.isHey == null) {
			parsedJson.isHey = false;
			if (parsedSongName.toLowerCase() == 'bopeebo')
				parsedJson.isHey = true;
		}
		if (parsedJson.isCheer == null) {
			parsedJson.isCheer = false;
			if (parsedSongName.toLowerCase() == "tutorial")
				parsedJson.isCheer = true;
		}

		var ownerRoot = characterRootForSong(folderLower);
		var ownedGirlfriend = characterVisualRegistryEntryInManifest(Std.string(parsedJson.gf), ownerRoot) != null;
		if (!ownedGirlfriend && characterOwnerEngineForSong(folderLower).toLowerCase()
			== ImportEngine.NIGHTMARE_VISION.toLowerCase())
			ownedGirlfriend = NightmareVisionCharacterData.load(ownerRoot, Std.string(parsedJson.gf)) != null;
		if (!ownedGirlfriend && !isValidVisualValue('gf', parsedJson.gf)
			&& !(preserveAuthoredGraphics && chartHasValue(requestedJson, 'gf'))) {
			switch (parsedJson.stage) {
				case 'limo':
					parsedJson.gf = 'gf-car';
				case 'mall' | 'mallEvil':
					parsedJson.gf = 'gf-christmas';
				case 'school' | 'schoolEvil':
					parsedJson.gf = 'gf-pixel';
				case 'tank':
					parsedJson.gf = 'gf-tankmen';
					if (parsedSongName.toLowerCase() == "stress")
						parsedJson.gf = "pico-speaker";
				default:
					parsedJson.gf = 'gf';
			}
			if (!isValidVisualValue('gf', parsedJson.gf))
				parsedJson.gf = 'gf';
		}
		if (parsedJson.isMoody == null) {
			if (parsedSongName.toLowerCase() == 'roses')
				parsedJson.isMoody = true;
			else
				parsedJson.isMoody = false;
		}
		// is spooky means trails on spirit
		if (parsedJson.isSpooky == null) {
			if (parsedJson.stage.toLowerCase() == 'schoolevil')
				parsedJson.isSpooky = true;
			else
				parsedJson.isSpooky = false;
		}
		if (parsedSongName.toLowerCase() == 'winter-horrorland' && !chartHasValue(parsedJson, 'cutsceneType'))
			parsedJson.cutsceneType = "monster";

		if (parsedJson.forceJudgements == null)
			parsedJson.forceJudgements = false;

		if (!isValidVisualValue('forceLayout', parsedJson.forceLayout)) {
			var legacyLayout:String = parsedJson.uiLayoutType;
			parsedJson.forceLayout = legacyLayout != null && isValidVisualValue('uiLayoutType', legacyLayout)
				? legacyLayout : 'none';
		}
		if (parsedJson.forceLayout == 'normal')
			parsedJson.forceLayout = 'none';

		if (!isValidVisualValue('cutsceneType', parsedJson.cutsceneType)) {
			parsedJson.cutsceneType = switch (parsedSongName.toLowerCase()) {
				case 'roses':
					"angry-senpai";
				case 'senpai':
					"senpai";
				case 'thorns':
					'spirit';
				case 'winter-horrorland':
					'monster';
				default:
					'none';
			}
		}
		if (parsedJson.convertMineToNuke == null) {
			var chartEngine:String = '';
			#if sys
			chartEngine = compatibilityEngine(folderLower, parsedJson);
			#end
			parsedJson.convertMineToNuke = EngineCompat.inferMineToNuke(parsedJson,
				parsedJson.preferredNoteAmount == null ? 4 : Std.int(parsedJson.preferredNoteAmount),
				chartEngine);
		}
		if (!isValidVisualValue('uiType', parsedJson.uiType)) {
			parsedJson.uiType = switch (parsedSongName.toLowerCase()) {
				case 'roses' | 'senpai' | 'thorns':
					'pixel';
				default:
					'normal';
			}
		}
		if (!isValidVisualValue('stageID', parsedJson.stageID)) {
			parsedJson.stageID = switch(diffName.toLowerCase()) {
				case 'erect' | 'nightmare' | 'pico':
					1;
				default:
					0;
			}
			
		}
		if (parsedJson.needsVoices == null)
			parsedJson.needsVoices = true;
		if (parsedJson.speed == null)
			parsedJson.speed = 1;
		if (parsedJson.preferredNoteAmount == null) {
			parsedJson.preferredNoteAmount =  switch (parsedJson.mania) {
				case 1:
					6;
				case 2:
					9;
				default:
					4;
			}
		}
		if (parsedJson.mania == null) {
			parsedJson.mania = switch (parsedJson.preferredNoteAmount) {
				case 6:
					1;
				case 9:
					2;
				default:
					0;
			}
		}
		if (parsedJson.player1 == "bf-pixel" && OptionsHandler.options.stressTankmen)
			parsedJson.player1 = "bulb-pixel";
		// This id is attached only from the selected native Freeplay row. Treat a
		// same-named donor field as untrusted chart data and discard it on load.
		Reflect.deleteField(parsedJson, 'compatScoreSongId');
		// Modding Plus keeps lift notes in sectionNotes[4] instead of the native
		// note-data block. Resolve that legacy marker only on the in-memory chart;
		// imported/source JSON retains its original fifth value for chart tools and
		// repair diagnostics.
		// The fifth row value is a lift marker in Modding Plus. Other source
		// engines may store their own metadata there, so only apply this ABI
		// conversion to Modding Plus or charts with no declared provenance.
		#if sys
		if (compatibility == '' || compatibility == ImportEngine.MODDING_PLUS.toLowerCase())
		#end
			EngineCompat.normalizeLegacyNoteRows(parsedJson,
				parsedJson.preferredNoteAmount == null ? 4 : Std.int(parsedJson.preferredNoteAmount));
		Reflect.setField(parsedJson, 'compatStorageFolder', folderLower);
		Reflect.setField(parsedJson, 'compatChartFileName', inputLower);
		attachCompatChartAccessors(parsedJson, folderLower, diffName);

		return parsedJson;
	}

	public static function parseJSONshit(rawJson:String, ?preserveStageProvenance:Bool = false):SwagSong {
		var swagShit:SwagSong = cast CoolUtil.parseJson(rawJson).song;
		// Only the chart editor's own autosave path may restore this transient
		// bit. Ordinary imported/source JSON is user data and cannot spoof it.
		var storedStageProvenance:Dynamic = Reflect.field(swagShit, 'compatStageAuthored');
		var stageAuthored = preserveStageProvenance && Std.isOfType(storedStageProvenance, Bool)
			? storedStageProvenance == true : chartHasValue(swagShit, 'stage');
		Reflect.setField(swagShit, 'compatStageAuthored', stageAuthored);
		attachCompatChartAccessors(swagShit, null, 'normal');
		return swagShit;
	}

	/**
	 * Attach only data-backed chart views.  `getDifficulty` resolves a sibling
	 * native chart through Song.loadFromJson, while offsets/sticker metadata stay
	 * on the in-memory chart and never probe donor files or construct a donor
	 * Song object graph.
	 */
	static function attachCompatChartAccessors(chart:Dynamic, folder:String, difficulty:String):Void {
		if (chart == null)
			return;
		var activeDifficulty = difficulty == null || StringTools.trim(difficulty) == ''
			? 'normal' : StringTools.trim(difficulty).toLowerCase();
		var activeChart:Dynamic = chart;
		Reflect.setField(chart, 'getDifficulty', function(requested:Dynamic):Dynamic {
			var name = requested == null ? 'normal' : StringTools.trim(Std.string(requested)).toLowerCase();
			if (name == '') name = 'normal';
			var resolved:Dynamic = null;
			if (name == activeDifficulty)
				resolved = activeChart;
			else {
				if (folder == null || StringTools.trim(folder) == '')
					return null;
				var input = name == 'normal' ? folder : folder + '-' + name;
				try {
					resolved = loadCompatDifficulty(input, folder);
				} catch (error:Dynamic) {
					trace('Unable to resolve chart difficulty ' + name + ' for ' + folder + ': ' + error);
					return null;
				}
			}
			// HXC's SongDifficulty.notes is a flat, read-only SongNoteData list,
			// while native PlayState owns section rows.  Return the bounded view for
			// every requested sibling without replacing the chart used by gameplay.
			return ExtraStrumlineAdapter.chartView(resolved);
		});
		var rawOffsets:Dynamic = Reflect.field(chart, 'vocalOffsets');
		if (rawOffsets == null) {
			var metadata:Dynamic = Reflect.field(chart, 'compatMetadata');
			rawOffsets = metadata == null ? null : Reflect.field(metadata, 'vocalOffsets');
		}
		var offsets:Dynamic = Reflect.field(chart, 'offsets');
		if (offsets == null || !Std.isOfType(offsets, SongVocalOffsets))
			Reflect.setField(chart, 'offsets', new SongVocalOffsets(rawOffsets == null ? offsets : rawOffsets));
		if (!Reflect.hasField(chart, 'stickerPack'))
			Reflect.setField(chart, 'stickerPack', '');
	}

	/**
	 * Keep sibling difficulty resolution behind one native, data-only boundary.
	 * HXC callers receive the read-only view produced by the accessor above;
	 * they never receive a donor Song object or a mutable gameplay owner.
	 */
	static function loadCompatDifficulty(input:String, folder:String):Dynamic {
		return Song.loadFromJson(input, folder);
	}
}

/**
	 * Read-only vocal timing view used by imported chart scripts.  Native split
	 * vocal tracks start from the same conductor clock, so missing authored data
	 * correctly resolves to zero instead of fabricating a donor offset model.
	 */
class SongVocalOffsets {
	var values:Map<String, Float> = new Map<String, Float>();

	public function new(?raw:Dynamic) {
		collect('', raw);
	}

	public function getVocalOffset(character:Dynamic, ?instrumental:Dynamic):Float {
		var charName = normalize(character);
		var instName = normalize(instrumental);
		var keys = [
			charName + '|' + instName,
			charName + ':' + instName,
			charName + '_' + instName,
			charName,
			instName,
			'default'
		];
		for (key in keys)
			if (key != '' && values.exists(key))
				return values.get(key);
		return 0;
	}

	function collect(prefix:String, value:Dynamic):Void {
		if (value == null)
			return;
		if (Std.isOfType(value, Int) || Std.isOfType(value, Float)) {
			var number = Std.parseFloat(Std.string(value));
			if (!Math.isNaN(number) && prefix != '')
				values.set(normalize(prefix), number);
			return;
		}
		if (Std.isOfType(value, String)) {
			var parsed = Std.parseFloat(StringTools.trim(Std.string(value)));
			if (!Math.isNaN(parsed) && prefix != '')
				values.set(normalize(prefix), parsed);
			return;
		}
		if (Std.isOfType(value, Bool))
			return;
		for (field in Reflect.fields(value)) {
			var next = prefix == '' ? field : prefix + '|' + field;
			collect(next, Reflect.field(value, field));
		}
	}

	static function normalize(value:Dynamic):String {
		if (value == null)
			return '';
		return StringTools.trim(Std.string(value)).toLowerCase();
	}
}
