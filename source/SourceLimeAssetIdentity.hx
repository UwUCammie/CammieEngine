package;

import PsychAssetProfile.PsychAssetProfileCandidate;
import PsychAssetProfile.PsychAssetProfileMappedFile;
#if sys
import sys.io.File;
import sys.FileSystem;
#end
using StringTools;

/** One receipt-owned Lime AssetLibrary entry. `ownerRelative` is a physical
	path under the selected imported owner; it is never derived from `id`. */
typedef SourceLimeAssetIdentityEntry = {
	var library:String;
	var id:String;
	var type:String;
	var ownerRelative:String;
	var size:Int;
	var sha256:String;
	var candidateOrder:Int;
	/** Effective Lime AssetHelper preload behavior for this source target. */
	var preloadState:String;
}

/** File-backed load contract for one actual Lime library namespace. Project
	configuration records with no runtime asset partition do not create entries. */
typedef SourceLimeAssetIdentityLibraryLoadProfile = {
	var library:String;
	/** standard-file, unknown, or unsupported. */
	var state:String;
	/** Source Project declaration order; -1 denotes an implicit Lime library. */
	var projectOrder:Int;
	/** known or unresolved, preserving the Project setting separately from the
		effective per-entry preload flags. */
	var projectPreloadState:String;
	/** Null is Lime's implicit/auto value; explicit false remains false. */
	var projectPreload:Null<Bool>;
	/** Lime's Project Library.embed setting; null is the parser default. */
	var projectEmbedState:String;
	var projectEmbed:Null<Bool>;
	var diagnostic:Null<String>;
}

/** Immutable persisted index metadata. Runtime transaction/generation values
	are intentionally supplied by the verified manifest loader, not serialized. */
typedef SourceLimeAssetIdentityIndex = {
	var version:Int;
	var owner:String;
	var engine:String;
	var scope:String;
	var namespace:String;
	var snapshotId:String;
	var rootRelative:String;
	var projectSha256:String;
	var complete:Bool;
	var libraries:Array<String>;
	var librariesComplete:Bool;
	/** Explicit Lime Platform value, or null when it was not captured. */
	var loadTarget:Null<String>;
	/** True only when all actual owner libraries have a safe load profile. */
	var loadProfileComplete:Bool;
	var libraryLoadProfiles:Array<SourceLimeAssetIdentityLibraryLoadProfile>;
	var entries:Array<SourceLimeAssetIdentityEntry>;
	@:optional var handoff:Null<SourceLimeAssetIdentityHandoff>;
}

/** Lime's `library:id` symbol, split at the first colon only. */
typedef SourceLimeAssetIdentityKey = {
	var library:String;
	var id:String;
}

/** Catalog-authorized provider-core materialization for one family receiver. */
typedef SourceLimeAssetIdentityHandoff = {
	var version:Int;
	var providerNamespace:String;
	var providerRootRelative:String;
	var providerProjectSha256:String;
	var receiverRootRelative:String;
	var catalogVersion:Int;
}

/** Staged sidecar value, committed through the ordinary import transaction. */
typedef SourceLimeAssetIdentityPublication = {
	var path:String;
	var content:String;
	var index:SourceLimeAssetIdentityIndex;
	var failed:Bool;
	var diagnostics:Array<String>;
}

typedef SourceLimeAssetIdentityPublicationInput = {
	var profile:Dynamic;
	var owner:String;
	var engine:String;
	var scope:String;
	var identityEvents:Array<Dynamic>;
	var blockedKeys:Array<SourceLimeAssetIdentityKey>;
	var blockAll:Bool;
	var complete:Bool;
	var librariesComplete:Bool;
}

/**
	Shared Lime AssetLibrary identity rules and validated sidecar schema.
	This type does not load files or trust importer ownership by itself. A runtime
	loader must verify the sidecar and each entry against the committed import
	manifest before using the returned index.
*/
class SourceLimeAssetIdentity {
	public static inline var VERSION:Int = 2;
	public static inline var SIDECAR_DIR:String = ".cammie-asset-identities";
	public static inline var PSYCH_FILE:String = "psych.json";
	public static inline var NIGHTMARE_VISION_PACKAGE_FILE:String = "nightmare-vision-package.json";
	public static inline var NIGHTMARE_VISION_CORE_FILE:String = "nightmare-vision-core.json";

	static final TYPES:Array<String> = [
		"BINARY", "BUNDLE", "FONT", "IMAGE", "MANIFEST", "MOVIE_CLIP", "MUSIC", "SOUND", "TEMPLATE", "TEXT"
	];
	/** Exact non-CUSTOM target values in the pinned Lime 8.3.2 Platform enum. */
	static final LOAD_TARGETS:Array<String> = [
		"air", "android", "blackberry", "console-pc", "firefox", "flash", "html5", "ios",
		"linux", "mac", "ps3", "ps4", "tizen", "vita", "webassembly", "windows", "webos",
		"wiiu", "xbox1", "emscripten", "tvos"
	];

	/** Lime maps a null or empty library to `default`, preserving every other
		library name exactly, including case. */
	public static function canonicalLibrary(library:Null<String>):String {
		return library == null || library == "" ? "default" : library;
	}

	/** Parse Lime's `library:id` symbol. No colon means the default library;
		when a colon is present, only the first one is structural. */
	public static function parseQualifiedId(value:String):SourceLimeAssetIdentityKey {
		if (value == null) return null;
		var separator = value.indexOf(":");
		if (separator < 0) return {library:"default", id:value};
		return {library:canonicalLibrary(value.substr(0, separator)), id:value.substr(separator + 1)};
	}

	public static function keyForEvent(event:PsychAssetProfileMappedFile):Null<SourceLimeAssetIdentityKey> {
		if (event == null) return null;
		var id = event.assetId;
		if (id == null) id = event.mappedPath;
		return id == null ? null : {library:canonicalLibrary(event.library), id:id};
	}

	/** Resolve the identity a candidate could claim at one enumerated source
		path. Returns null when an unresolved path or library prevents exactness. */
	public static function keyForProjection(candidate:PsychAssetProfileCandidate,
		sourceRelative:Null<String>):Null<SourceLimeAssetIdentityKey> {
		if (candidate == null) return null;
		var library = candidate.library == null || candidate.library == ""
			? "default" : candidate.library;
		if (hasSymbol(library)) return null;
		if (candidate.assetIdOverride == true) {
			if (candidate.assetId == null || hasSymbol(candidate.assetId)) return null;
			return {library:library, id:candidate.assetId};
		}
		if (sourceRelative == null || sourceRelative == "" || hasSymbol(sourceRelative)
			|| candidate.sourceRelative == null || candidate.targetRelative == null
			|| hasSymbol(candidate.sourceRelative) || hasSymbol(candidate.targetRelative)) return null;
		var base = StringTools.replace(candidate.sourceRelative, "\\", "/");
		var source = StringTools.replace(sourceRelative, "\\", "/");
		var suffix = source == base ? "" : StringTools.startsWith(source, base + "/")
			? source.substr(base.length + 1) : null;
		if (suffix == null) return null;
		var id = projectPath(candidate, suffix);
		return id == null || hasSymbol(id) ? null : {library:library, id:id};
	}

	/** Apply a concrete Project source-to-target rename without requiring the
		candidate to be enabled. This is used only to identify a deferred or
		disabled projection; it never authorizes reading or publishing the source. */
	public static function projectPath(candidate:PsychAssetProfileCandidate,
		sourceSuffix:String):Null<String> {
		if (candidate == null || sourceSuffix == null) return null;
		var target = normalizeLogical(candidate.targetRelative);
		var suffix = sourceSuffix == "" ? "" : normalizeRelative(sourceSuffix);
		if (target == null || (sourceSuffix != "" && suffix == null)) return null;
		var mapped = suffix == null || suffix == "" ? target : target + "/" + suffix;
		return normalizeLogical(mapped);
	}

	public static function targetForProjection(candidate:PsychAssetProfileCandidate,
		sourceRelative:Null<String>):Null<String> {
		if (candidate == null || candidate.sourceRelative == null || candidate.targetRelative == null
			|| hasSymbol(candidate.sourceRelative) || hasSymbol(candidate.targetRelative)
			|| sourceRelative == null || hasSymbol(sourceRelative)) return null;
		var base = StringTools.replace(candidate.sourceRelative, "\\", "/");
		var source = StringTools.replace(sourceRelative, "\\", "/");
		var suffix = source == base ? "" : StringTools.startsWith(source, base + "/")
			? source.substr(base.length + 1) : null;
		return suffix == null ? null : projectPath(candidate, suffix);
	}

	/** Runtime-owned path for a logical Lime target. Project `assets/` maps to
		its contents under an imported owner; other safe target roots stay intact. */
	public static function ownerRelativeForTarget(target:String):Null<String> {
		var clean = normalizeLogical(target);
		if (clean == null) return null;
		if (clean == "assets") return "";
		if (StringTools.startsWith(clean, "assets/")) clean = clean.substr("assets/".length);
		return normalizeOwnerRelative(clean);
	}

	public static function keyToken(key:SourceLimeAssetIdentityKey):Null<String> {
		if (key == null || key.library == null || key.id == null) return null;
		return Std.string(key.library.length) + ":" + key.library
			+ Std.string(key.id.length) + ":" + key.id;
	}

	/** Canonical Lime AssetType spelling, or null when Lime would not recognize
		an explicit Project type. `bytes` is Lime's alias for BINARY. */
	public static function normalizeType(value:Null<String>):Null<String> {
		if (value == null || value == "") return null;
		if (value == "bytes") return "BINARY";
		var upper = value.toUpperCase();
		return TYPES.indexOf(upper) >= 0 ? upper : null;
	}

	/** Reproduce Lime 8.3.2 Asset type inference, including hxp.System.isText's
		512-byte probe for extensions not listed by AssetHelper. The optional source
		path must be a verified snapshot file; without it, an unknown extension
		remains unresolved instead of guessing TEXT or BINARY. */
	public static function inferType(explicitType:Null<String>, sourceRelative:String,
		size:Int, ?sourcePath:String):Null<String> {
		var explicit = normalizeType(explicitType);
		if (explicit != null) return explicit;
		var extension = extensionOf(sourceRelative);
		var known = switch (extension) {
			case ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".jfif": "IMAGE";
			case ".otf", ".ttf": "FONT";
			case ".wav", ".wave": "SOUND";
			case ".mp3", ".mp2": "MUSIC";
			case ".exe", ".bin", ".so", ".pch", ".dll", ".zip", ".tar", ".gz", ".fla", ".swf", ".atf", ".psd", ".awd": "BINARY";
			case ".txt", ".text", ".xml", ".java", ".hx", ".cpp", ".c", ".h", ".cs", ".js", ".mm", ".hxml", ".html", ".json", ".css", ".gpe", ".pbxproj", ".plist", ".properties", ".ini", ".hxproj", ".nmml", ".lime", ".svg": "TEXT";
			case ".bundle": "MANIFEST";
			case ".ogg", ".m4a": size > 1024 * 1024 ? "MUSIC" : "SOUND";
			default: "";
		};
		if (known != "") return known;
		if (sourcePath == null || sourcePath == "") return null;
		var text = hxpIsText(sourcePath);
		return text == null ? null : text ? "TEXT" : "BINARY";
	}

	/** Reproduce hxp.System.isText classification. The file-size bound models its
		readByte EOF catch without requiring the eval target to instantiate haxe.io.Eof. */
	static function hxpIsText(sourcePath:Null<String>):Null<Bool> {
		#if sys
		if (sourcePath == null || !FileSystem.exists(sourcePath)) return false;
		var fileSize:Int;
		try fileSize = FileSystem.stat(sourcePath).size catch (_:Dynamic) return null;
		var input;
		try input = File.read(sourcePath, true) catch (_:Dynamic) return null;
		var numChars = 0;
		var numBytes = 0;
		var byteHeader:Null<Array<Int>> = [];
		var zeroBytes = 0;
		var bom = false;
		try {
			while (numBytes < 512 && numBytes < fileSize) {
				var byte = input.readByte();
				if (numBytes < 3) {
					byteHeader.push(byte);
				} else if (byteHeader != null) {
					if (byteHeader[0] == 0xFF && byteHeader[1] == 0xFE) bom = true;
					else if (byteHeader[0] == 0xFE && byteHeader[1] == 0xFF) bom = true;
					else if (byteHeader[0] == 0xEF && byteHeader[1] == 0xBB && byteHeader[2] == 0xBF) bom = true;
					byteHeader = null;
				}
				if (bom) break;
				numBytes++;
				if (byte == 0) zeroBytes++;
				if ((byte > 8 && byte < 16) || (byte > 32 && byte < 256) || byte > 287)
					numChars++;
			}
		} catch (_:Dynamic) {}
		input.close();
		if (bom) return true;
		if (numBytes == 0 || (numChars / numBytes) > 0.9
			|| ((zeroBytes / numBytes) < 0.015 && (numChars / numBytes) > 0.5)) return true;
		return false;
		#else
		return null;
		#end
	}

	/** Match Lime's native AssetLibrary.exists semantics. A null request and a
		BINARY request accept any stored native type; SOUND and MUSIC inter-match;
		stored BINARY satisfies TEXT. Flash-only IMAGE/TEXT permissiveness is not
		applied to this native runtime. */
	public static function typeMatches(actual:String, expected:Null<String>):Bool {
		var actualType = normalizeType(actual);
		if (actualType == null) return false;
		var expectedType = normalizeType(expected);
		if (expected == null || expectedType == "BINARY") return true;
		if (expectedType == null) return false;
		if (actualType == expectedType) return true;
		if ((actualType == "SOUND" || actualType == "MUSIC")
			&& (expectedType == "SOUND" || expectedType == "MUSIC")) return true;
		return actualType == "BINARY" && expectedType == "TEXT";
	}

	public static function sidecarFilename(engine:String, scope:String):Null<String> {
		var canonical = ImportRevision.normalizeEngine(engine);
		if (canonical == "Psych Engine" && scope == "package") return PSYCH_FILE;
		if (canonical == "Nightmare Vision" && scope == "package") return NIGHTMARE_VISION_PACKAGE_FILE;
		if (canonical == "Nightmare Vision" && scope == "core") return NIGHTMARE_VISION_CORE_FILE;
		return null;
	}

	/** Path relative to the owner root. */
	public static function sidecarRelativePath(engine:String, scope:String):Null<String> {
		var filename = sidecarFilename(engine, scope);
		return filename == null ? null : SIDECAR_DIR + "/" + filename;
	}

	public static function isReservedOwnerPath(path:String):Bool {
		var clean = normalizeOwnerRelative(path);
		if (clean == null) return false;
		var key = clean.toLowerCase();
		var reserved = SIDECAR_DIR.toLowerCase();
		return key == reserved || key.startsWith(reserved + "/");
	}

	/** Validate and copy a JSON-decoded index against independently captured
		owner identity. The caller still verifies the index and entry hashes against
		the committed manifest's owned-file table. */
	public static function validate(raw:Dynamic, expectedOwner:String, expectedEngine:String,
		expectedScope:String, expectedNamespace:String):Null<SourceLimeAssetIdentityIndex> {
		if (raw == null || !isRecord(raw)) return null;
		var version = intField(raw, "version");
		var owner = stringField(raw, "owner");
		var engine = stringField(raw, "engine");
		var scope = stringField(raw, "scope");
		var namespace = stringField(raw, "namespace");
		var snapshotId = stringField(raw, "snapshotId");
		var rootRelative = stringField(raw, "rootRelative");
		var projectSha256 = stringField(raw, "projectSha256");
		var complete = boolField(raw, "complete");
		var librariesComplete = boolField(raw, "librariesComplete");
		var loadTargetRaw:Dynamic = Reflect.field(raw, "loadTarget");
		var loadProfileCompleteRaw:Dynamic = Reflect.field(raw, "loadProfileComplete");
		var libraryLoadProfilesRaw:Dynamic = Reflect.field(raw, "libraryLoadProfiles");
		var handoffRaw:Dynamic = Reflect.field(raw, "handoff");
		var librariesRaw:Dynamic = Reflect.field(raw, "libraries");
		var entriesRaw:Dynamic = Reflect.field(raw, "entries");
		var expectedCanonicalEngine = ImportRevision.normalizeEngine(expectedEngine);
		if ((version != 1 && version != VERSION) || owner == null || expectedOwner == null || owner != expectedOwner
			|| !isSafeOwnerRoot(owner) || engine == null || expectedCanonicalEngine == ""
			|| ImportRevision.normalizeEngine(engine) != expectedCanonicalEngine
			|| scope == null || scope != expectedScope || namespace == null || namespace != expectedNamespace
			|| !isNamespace(namespace) || owner != "assets/imported_mods/" + namespace
			|| sidecarFilename(engine, scope) == null
			|| snapshotId == null || !isHex(snapshotId, 64)
			|| rootRelative == null || (rootRelative != "" && normalizeRelative(rootRelative) != rootRelative)
			|| projectSha256 == null || !isHex(projectSha256, 64)
			|| complete == null || librariesComplete == null
			|| !Std.isOfType(librariesRaw, Array) || !Std.isOfType(entriesRaw, Array)) return null;
		var handoff:Null<SourceLimeAssetIdentityHandoff> = null;
		if (handoffRaw != null) {
			if (version != VERSION || expectedCanonicalEngine != "Nightmare Vision" || expectedScope != "core") return null;
			var handoffVersion = intField(handoffRaw, "version");
			var providerNamespace = stringField(handoffRaw, "providerNamespace");
			var providerRootRelative = stringField(handoffRaw, "providerRootRelative");
			var providerProjectSha = stringField(handoffRaw, "providerProjectSha256");
			var receiverRootRelative = stringField(handoffRaw, "receiverRootRelative");
			var catalogVersion = intField(handoffRaw, "catalogVersion");
			if (handoffVersion != 1 || !isNamespace(providerNamespace)
				|| providerNamespace == namespace || providerRootRelative != ""
				|| providerProjectSha == null || !isHex(providerProjectSha, 64)
				|| providerProjectSha != providerProjectSha.toLowerCase()
				|| receiverRootRelative == null || !StringTools.startsWith(receiverRootRelative, "content/")
				|| normalizeRelative(receiverRootRelative) != receiverRootRelative || catalogVersion != 3
				|| rootRelative != providerRootRelative || projectSha256.toLowerCase() != providerProjectSha)
				return null;
			handoff = {version:1, providerNamespace:providerNamespace,
				providerRootRelative:providerRootRelative, providerProjectSha256:providerProjectSha,
				receiverRootRelative:receiverRootRelative, catalogVersion:3};
		}
		var legacyV1 = version == 1;
		var loadTarget:Null<String> = null;
		var loadProfileComplete = false;
		if (!legacyV1) {
			if (loadTargetRaw != null && !Std.isOfType(loadTargetRaw, String)) return null;
			loadTarget = cast loadTargetRaw;
			if (loadTarget != null && LOAD_TARGETS.indexOf(loadTarget) < 0) return null;
			if (!Std.isOfType(loadProfileCompleteRaw, Bool)
				|| !Std.isOfType(libraryLoadProfilesRaw, Array)) return null;
			loadProfileComplete = cast loadProfileCompleteRaw;
		} else if (loadTargetRaw != null || loadProfileCompleteRaw != null || libraryLoadProfilesRaw != null) {
			// A v1 document cannot smuggle unvalidated v2 load claims.
			return null;
		}

		var libraries:Array<String> = [];
		var seenLibraries:Map<String, Bool> = new Map();
		for (rawLibrary in (cast librariesRaw:Array<Dynamic>)) {
			if (!Std.isOfType(rawLibrary, String)) return null;
			var library:String = cast rawLibrary;
			if (library == "" || canonicalLibrary(library) != library || seenLibraries.exists(library)) return null;
			seenLibraries.set(library, true);
			libraries.push(library);
		}
		if (!seenLibraries.exists("default")) return null;

		var entries:Array<SourceLimeAssetIdentityEntry> = [];
		var seenKeys:Map<String, Bool> = new Map();
		for (rawEntry in (cast entriesRaw:Array<Dynamic>)) {
			if (!isRecord(rawEntry)) return null;
			var library = stringField(rawEntry, "library");
			var id = stringField(rawEntry, "id");
			var type = stringField(rawEntry, "type");
			var ownerRelative = stringField(rawEntry, "ownerRelative");
			var size = intField(rawEntry, "size");
			var sha256 = stringField(rawEntry, "sha256");
			var candidateOrder = intField(rawEntry, "candidateOrder");
			var preloadState = legacyV1 ? "unresolved" : stringField(rawEntry, "preloadState");
			if (library == null || library == "" || !validIdentityText(library, 1024) || !seenLibraries.exists(library)
				|| id == null || id == "" || !validIdentityText(id, 4096) || id.indexOf("$") >= 0
				|| type == null || normalizeType(type) != type
				|| ownerRelative == null || normalizeOwnerRelative(ownerRelative) != ownerRelative
				|| isReservedOwnerPath(ownerRelative) || size == null || size < 0
				|| sha256 == null || !isHex(sha256, 64) || sha256 != sha256.toLowerCase()
				|| candidateOrder == null || candidateOrder < 0
				|| (preloadState != "enabled" && preloadState != "disabled" && preloadState != "unresolved")) return null;
			var key = library + "\x00" + id;
			if (seenKeys.exists(key)) return null;
			seenKeys.set(key, true);
			entries.push({library:library, id:id, type:type, ownerRelative:ownerRelative,
				size:size, sha256:sha256, candidateOrder:candidateOrder, preloadState:preloadState});
		}
		var libraryLoadProfiles:Array<SourceLimeAssetIdentityLibraryLoadProfile> = [];
		if (!legacyV1) {
			var seenLoadProfiles:Map<String, Bool> = new Map();
			for (rawLoadProfile in (cast libraryLoadProfilesRaw:Array<Dynamic>)) {
				if (!isRecord(rawLoadProfile)) return null;
				var loadLibrary = stringField(rawLoadProfile, "library");
				var state = stringField(rawLoadProfile, "state");
				var projectOrder = intField(rawLoadProfile, "projectOrder");
				var projectPreloadState = stringField(rawLoadProfile, "projectPreloadState");
				var projectPreloadRaw:Dynamic = Reflect.field(rawLoadProfile, "projectPreload");
				var projectEmbedState = stringField(rawLoadProfile, "projectEmbedState");
				var projectEmbedRaw:Dynamic = Reflect.field(rawLoadProfile, "projectEmbed");
				var diagnosticRaw:Dynamic = Reflect.field(rawLoadProfile, "diagnostic");
				if (loadLibrary == null || !seenLibraries.exists(loadLibrary) || seenLoadProfiles.exists(loadLibrary)
					|| (state != "standard-file" && state != "unknown" && state != "unsupported")
					|| projectOrder == null || projectOrder < -1
					|| (projectPreloadState != "known" && projectPreloadState != "unresolved")
					|| (projectEmbedState != "known" && projectEmbedState != "unresolved")
					|| (projectPreloadRaw != null && !Std.isOfType(projectPreloadRaw, Bool))
					|| (projectEmbedRaw != null && !Std.isOfType(projectEmbedRaw, Bool))
					|| (diagnosticRaw != null && !Std.isOfType(diagnosticRaw, String))) return null;
				var diagnostic:Null<String> = cast diagnosticRaw;
				if ((state == "unknown" || state == "unsupported") && (diagnostic == null || diagnostic == "")) return null;
				if (state == "standard-file" && diagnostic != null && diagnostic != "") return null;
				var projectPreload:Null<Bool> = cast projectPreloadRaw;
				var projectEmbed:Null<Bool> = cast projectEmbedRaw;
				if (projectPreloadState == "unresolved" && projectPreload != null) return null;
				if (projectPreloadState == "known" && projectOrder >= 0 && projectPreload == null) return null;
				if (projectEmbedState == "unresolved" && projectEmbed != null) return null;
				seenLoadProfiles.set(loadLibrary, true);
				libraryLoadProfiles.push({library:loadLibrary, state:state, projectOrder:projectOrder,
					projectPreloadState:projectPreloadState, projectPreload:projectPreload,
					projectEmbedState:projectEmbedState, projectEmbed:projectEmbed, diagnostic:diagnostic});
			}
			if (libraryLoadProfiles.length != libraries.length) return null;
			for (library in libraries) if (!seenLoadProfiles.exists(library)) return null;
			if (loadProfileComplete) {
				if (loadTarget == null || !complete || !librariesComplete) return null;
				for (loadProfile in libraryLoadProfiles)
					if (loadProfile.state != "standard-file" || loadProfile.projectPreloadState != "known") return null;
				for (entry in entries) if (entry.preloadState == "unresolved") return null;
			}
		}
		entries.sort(function(a, b) {
			var order = Reflect.compare(a.candidateOrder, b.candidateOrder);
			if (order != 0) return order;
			var libraryOrder = Reflect.compare(a.library, b.library);
			return libraryOrder != 0 ? libraryOrder : Reflect.compare(a.id, b.id);
		});
		libraries.sort(Reflect.compare);
		return {
			version:version, owner:owner, engine:expectedCanonicalEngine, scope:scope,
			namespace:namespace, snapshotId:snapshotId, rootRelative:rootRelative,
			projectSha256:projectSha256, complete:complete, libraries:libraries,
			librariesComplete:librariesComplete, loadTarget:loadTarget,
			loadProfileComplete:loadProfileComplete, libraryLoadProfiles:libraryLoadProfiles,
			entries:entries, handoff:handoff
		};
	}

	static function capturedLoadTarget(profile:Dynamic):Null<String> {
		var target = stringField(profile, "buildTarget");
		if (target == null || target == "" || LOAD_TARGETS.indexOf(target) < 0) return null;
		return target;
	}

	/** Build profiles only for namespaces that Lime actually creates. Project
		configuration records with no corresponding asset partition are not runtime
		libraries and therefore are not claimed here. */
	static function buildLibraryLoadProfiles(profile:Dynamic, libraries:Array<String>, target:Null<String>,
		indexComplete:Bool, indexLibrariesComplete:Bool, diagnostics:Array<String>):Dynamic {
		var declarations:Dynamic = Reflect.field(profile, "libraries");
		var declarationByName:Map<String, Dynamic> = new Map();
		var unknownNames = !Std.isOfType(declarations, Array)
			|| Reflect.field(profile, "librariesComplete") != true;
		if (Std.isOfType(declarations, Array)) for (declaration in (cast declarations:Array<Dynamic>)) {
			if (declaration == null) {
				unknownNames = true;
				continue;
			}
			var state = stringField(declaration, "state");
			if (state == "disabled") continue;
			var name = stringField(declaration, "name");
			if (name == null || name == "" || hasSymbol(name) || !validIdentityText(name, 1024)) {
				unknownNames = true;
				continue;
			}
			// ProjectXMLParser appends declarations in order and AssetHelper's
			// library map assigns each name repeatedly, so the last declaration wins.
			declarationByName.set(canonicalLibrary(name), declaration);
		}

		var profiles:Array<SourceLimeAssetIdentityLibraryLoadProfile> = [];
		var byLibrary:Map<String, SourceLimeAssetIdentityLibraryLoadProfile> = new Map();
		var allComplete = target != null && indexComplete && indexLibrariesComplete && !unknownNames;
		for (library in libraries) {
			var declaration = declarationByName.get(library);
			var projectOrder = -1;
			var projectPreloadState = "known";
			var projectPreload:Null<Bool> = null;
			var projectEmbedState = "known";
			var projectEmbed:Null<Bool> = null;
			var state = "standard-file";
			var diagnostic:Null<String> = null;
			if (unknownNames || !indexLibrariesComplete) {
				state = "unknown";
				diagnostic = "The retained Project library declarations are incomplete or contain an unresolved namespace.";
			} else if (declaration != null) {
				var declaredOrder = intField(declaration, "order");
				projectOrder = declaredOrder == null ? 0 : cast declaredOrder;
				if (projectOrder < 0) projectOrder = 0;
				var declarationState = stringField(declaration, "state");
				projectPreloadState = stringField(declaration, "preloadState");
				if (projectPreloadState != "known" && projectPreloadState != "unresolved")
					projectPreloadState = "unresolved";
				projectEmbedState = stringField(declaration, "embedState");
				if (projectEmbedState != "known" && projectEmbedState != "unresolved")
					projectEmbedState = "unresolved";
				if (projectPreloadState == "known") {
					var rawPreload:Dynamic = Reflect.field(declaration, "preload");
					if (Std.isOfType(rawPreload, Bool)) projectPreload = cast rawPreload;
					else projectPreloadState = "unresolved";
				}
				if (projectEmbedState == "known") {
					var rawEmbed:Dynamic = Reflect.field(declaration, "embed");
					if (rawEmbed == null || Std.isOfType(rawEmbed, Bool)) projectEmbed = cast rawEmbed;
					else projectEmbedState = "unresolved";
				}
				if (declarationState != "enabled") {
					state = "unknown";
					diagnostic = "The effective Project library declaration is not fully resolved.";
				} else if (projectPreloadState == "unresolved" || projectEmbedState == "unresolved"
					|| stringField(declaration, "typeState") == "unresolved"
					|| stringField(declaration, "generateState") == "unresolved"
					|| stringField(declaration, "prefixState") == "unresolved") {
					state = "unknown";
					diagnostic = "A Project library load attribute is unresolved in the captured build context.";
				} else if (stringField(declaration, "sourcePath") != ""
					|| stringField(declaration, "type") != ""
					|| Reflect.field(declaration, "generate") == true
					|| stringField(declaration, "prefix") != "") {
					state = "unsupported";
					diagnostic = "This Project library uses sourcePath, a custom type, generation, or prefix semantics that a standard file-backed AssetManifest does not reproduce.";
				}
			}
			if (state != "standard-file" || projectPreloadState != "known") allComplete = false;
			var loadProfile:SourceLimeAssetIdentityLibraryLoadProfile = {
				library:library, state:state, projectOrder:projectOrder,
				projectPreloadState:projectPreloadState, projectPreload:projectPreload,
				projectEmbedState:projectEmbedState, projectEmbed:projectEmbed,
				diagnostic:diagnostic
			};
			profiles.push(loadProfile);
			byLibrary.set(library, loadProfile);
		}
		profiles.sort(function(left, right) return Reflect.compare(left.library, right.library));
		if (target == null) {
			allComplete = false;
			diagnostics.push("[lime-asset-identity] Load metadata needs an explicitly captured Lime target; no runtime host target is inferred.");
		}
		return {profiles:byLibrary, profilesArray:profiles, complete:allComplete};
	}

	static function preloadStateForEvent(target:Null<String>, event:PsychAssetProfileMappedFile,
		libraryProfile:Null<SourceLimeAssetIdentityLibraryLoadProfile>):String {
		if (event == null || libraryProfile == null || libraryProfile.state != "standard-file") return "unresolved";
		var type = inferType(event.type, event.sourceRelative, event.size, event.sourcePath);
		if (type == null) return "unresolved";
		var rawEmbed = event.embed;
		if (rawEmbed != null && hasSymbol(rawEmbed)) return "unresolved";
		var embedded = rawEmbed == null || rawEmbed == "" || rawEmbed == "true";
		var rawLibrary = event.library;
		if (rawLibrary != null && hasSymbol(rawLibrary)) return "unresolved";
		var assetHasLibrary = rawLibrary != null && rawLibrary != "";
		var effectiveLibraryPreload = libraryProfile.library == "default"
			? true : libraryProfile.projectPreload == true;
		function forTarget(platform:String):Null<Bool> {
			if (platform == "flash" || platform == "air") {
				return !embedded && assetHasLibrary ? effectiveLibraryPreload : false;
			}
			if (platform == "html5") {
				if (type == "FONT") return true;
				if (embedded) return true;
				return assetHasLibrary ? effectiveLibraryPreload : false;
			}
			if (platform == "webassembly") {
				if (embedded) return true;
				return assetHasLibrary ? effectiveLibraryPreload : false;
			}
			return false;
		}
		if (target != null) {
			var value = forTarget(target);
			return value == null ? "unresolved" : value ? "enabled" : "disabled";
		}
		var outcomes:Array<Bool> = [];
		for (platform in ["flash", "html5", "webassembly", "windows"]) {
			var value = forTarget(platform);
			if (value == null) return "unresolved";
			if (outcomes.indexOf(value) < 0) outcomes.push(value);
		}
		return outcomes.length == 1 ? outcomes[0] ? "enabled" : "disabled" : "unresolved";
	}

	static function html5AudioPathGroups(events:Map<String, PsychAssetProfileMappedFile>):Map<String, Int> {
		var groups:Map<String, Int> = new Map();
		for (token in events.keys()) {
			var event = events.get(token);
			if (event == null) continue;
			var key = html5AudioGroupKey(canonicalLibrary(event.library), event);
			if (key == null) continue;
			var count = groups.get(key);
			groups.set(key, count == null ? 1 : count + 1);
		}
		return groups;
	}

	static function html5AudioGroupKey(library:String, event:PsychAssetProfileMappedFile):Null<String> {
		if (event == null || (inferType(event.type, event.sourceRelative, event.size, event.sourcePath) != "SOUND"
			&& inferType(event.type, event.sourceRelative, event.size, event.sourcePath) != "MUSIC")) return null;
		var path = event.mappedPath;
		if (path == null || path == "") return null;
		path = StringTools.replace(path, "\\", "/");
		var slash = path.lastIndexOf("/");
		var dot = path.lastIndexOf(".");
		if (dot <= slash) return null;
		return library + "\x00" + path.substr(0, dot);
	}

	/** Convert the final collision-free shared publication plan to one
		transaction-owned sidecar. Every published entry points at an already
		planned physical file, and blocked IDs are omitted rather than guessed. */
	public static function preparePublication(profile:Dynamic, owner:String, engine:String,
		scope:String, identityEvents:Array<Dynamic>, blockedKeys:Array<SourceLimeAssetIdentityKey>,
		blockAll:Bool, complete:Bool, librariesComplete:Bool,
		?handoff:Dynamic):SourceLimeAssetIdentityPublication {
		var diagnostics:Array<String> = [];
		var canonicalEngine = ImportRevision.normalizeEngine(engine);
		var canonicalScope = scope == null || scope == "" ? "package" : scope;
		var namespace = stringField(profile, "namespace");
		var sidecar = sidecarRelativePath(canonicalEngine, canonicalScope);
		var rootRelative = stringField(profile, "rootRelative");
		var snapshotId = stringField(profile, "snapshotId");
		var projectSha256 = stringField(profile, "projectSha256");
		var ownerNamespace = owner != null && StringTools.startsWith(owner, "assets/imported_mods/")
			? owner.substr("assets/imported_mods/".length) : null;
		var handoffValue:Null<SourceLimeAssetIdentityHandoff> = null;
		if (handoff != null) {
			var handoffVersion = intField(handoff, "version");
			var receiverNamespace = stringField(handoff, "receiverNamespace");
			var providerNamespace = stringField(handoff, "providerNamespace");
			var providerRootRelative = stringField(handoff, "providerRootRelative");
			var providerProjectSha = stringField(handoff, "providerProjectSha256");
			var receiverRootRelative = stringField(handoff, "receiverRootRelative");
			var catalogVersion = intField(handoff, "catalogVersion");
			if (canonicalEngine != "Nightmare Vision" || canonicalScope != "core"
				|| handoffVersion != 1 || receiverNamespace != ownerNamespace
				|| !isNamespace(providerNamespace) || providerNamespace != namespace
				|| providerNamespace == ownerNamespace || providerRootRelative != ""
				|| providerProjectSha == null || !isHex(providerProjectSha, 64)
				|| providerProjectSha != providerProjectSha.toLowerCase()
				|| receiverRootRelative == null || !StringTools.startsWith(receiverRootRelative, "content/")
				|| normalizeRelative(receiverRootRelative) != receiverRootRelative || catalogVersion != 3
				|| rootRelative != providerRootRelative || projectSha256 == null
				|| projectSha256.toLowerCase() != providerProjectSha)
				return {path:"", content:"", index:null, failed:true,
					diagnostics:["[lime-asset-identity] The provider-to-receiver handoff is not authorized by this source profile."]};
			handoffValue = {version:1, providerNamespace:providerNamespace,
				providerRootRelative:providerRootRelative, providerProjectSha256:providerProjectSha,
				receiverRootRelative:receiverRootRelative, catalogVersion:3};
		}
		if (profile == null || owner == null || sidecar == null || namespace == ""
			|| (handoffValue == null && ownerNamespace != namespace)
			|| !isSafeOwnerRoot(owner) || snapshotId == null || !isHex(snapshotId, 64)
			|| projectSha256 == null || !isHex(projectSha256, 64)
			|| rootRelative == null || (rootRelative != "" && normalizeRelative(rootRelative) != rootRelative)) {
			return {path:"", content:"", index:null, failed:true,
				diagnostics:["[lime-asset-identity] The verified profile cannot be represented by a safe owner identity sidecar."]};
		}

		var libraries:Array<String> = ["default"];
		var knownLibrary:Map<String, Bool> = new Map();
		knownLibrary.set("default", true);
		var rawCandidates:Dynamic = Reflect.field(profile, "candidates");
		if (!Std.isOfType(rawCandidates, Array)) {
			librariesComplete = false;
			complete = false;
		} else for (candidate in (cast rawCandidates:Array<Dynamic>)) {
			if (candidate == null) {
				librariesComplete = false;
				complete = false;
				continue;
			}
			var candidateState = stringField(candidate, "state");
			if (candidateState == "disabled") continue;
			if (candidateState != "enabled") {
				librariesComplete = false;
				complete = false;
			}
			var rawLibrary = stringField(candidate, "library");
			if (candidateState != "enabled" || rawLibrary == null || hasSymbol(rawLibrary)
				|| !validIdentityText(rawLibrary, 1024)) {
				librariesComplete = false;
				complete = false;
			}
		}

		var blocked:Map<String, Bool> = new Map();
		if (blockedKeys != null) for (blockedKey in blockedKeys) {
			var token = keyToken(blockedKey);
			if (token != null) blocked.set(token, true);
			else blockAll = true;
		}
		var winners:Map<String, SourceLimeAssetIdentityEntry> = new Map();
		var winnerEvents:Map<String, PsychAssetProfileMappedFile> = new Map();
		if (identityEvents != null) for (rawEvent in identityEvents) {
			if (rawEvent == null) {
				complete = false;
				blockAll = true;
				continue;
			}
			var event:PsychAssetProfileMappedFile = cast Reflect.field(rawEvent, "event");
			var ownerRelative = normalizeOwnerRelative(stringField(rawEvent, "ownerRelative"));
			var key = keyForEvent(event);
			var token = keyToken(key);
			var type = event == null ? null : inferType(event.type, event.sourceRelative,
				event.size, event.sourcePath);
			if (key != null && key.library != null && key.library != ""
				&& validIdentityText(key.library, 1024))
				addLibrary(libraries, knownLibrary, key.library);
			if (key == null || token == null || key.id == "" || hasSymbol(key.id)
				|| !validIdentityText(key.id, 4096) || !validIdentityText(key.library, 1024)
				|| ownerRelative == null || type == null || type == "TEMPLATE" || type == "MANIFEST") {
				complete = false;
				if (token == null) {
					blockAll = true;
					librariesComplete = false;
				} else blocked.set(token, true);
				continue;
			}
			if (blocked.exists(token) || blockAll) continue;
			var entry:SourceLimeAssetIdentityEntry = {
				library:key.library, id:key.id, type:type, ownerRelative:ownerRelative,
				size:event.size, sha256:event.sha256.toLowerCase(), candidateOrder:event.candidateOrder,
				preloadState:"unresolved"
			};
			var prior = winners.get(token);
			if (prior == null || entry.candidateOrder > prior.candidateOrder) {
				winners.set(token, entry);
				winnerEvents.set(token, event);
			}
			else if (entry.candidateOrder == prior.candidateOrder
				&& (entry.ownerRelative != prior.ownerRelative || entry.sha256 != prior.sha256
					|| entry.size != prior.size || entry.type != prior.type)) {
				blocked.set(token, true);
				winners.remove(token);
				winnerEvents.remove(token);
				complete = false;
				diagnostics.push("[lime-asset-identity] Equal-order declarations conflict for one Lime library/id key; the key is unavailable.");
			}
		}
		if (blockAll) winners = new Map();
		for (token in blocked.keys()) {
			winners.remove(token);
			winnerEvents.remove(token);
		}

		var target = capturedLoadTarget(profile);
		if (target == null) diagnostics.push("[lime-asset-identity] The Lime build target was not captured as a supported Platform value; effective preload remains unresolved where target behavior differs.");
		var loadProfileInputs:Dynamic = buildLibraryLoadProfiles(profile, libraries, target,
			complete, librariesComplete, diagnostics);
		var loadByLibrary:Map<String, SourceLimeAssetIdentityLibraryLoadProfile> =
			cast Reflect.field(loadProfileInputs, "profiles");
		var libraryLoadProfiles:Array<SourceLimeAssetIdentityLibraryLoadProfile> =
			cast Reflect.field(loadProfileInputs, "profilesArray");
		var loadProfileComplete:Bool = Reflect.field(loadProfileInputs, "complete") == true;
		var pathGroups:Map<String, Int> = html5AudioPathGroups(winnerEvents);
		for (token in winners.keys()) {
			var entry = winners.get(token);
			var event = winnerEvents.get(token);
			var loadProfile = entry == null ? null : loadByLibrary.get(entry.library);
			var pathGroupKey = event == null ? null : html5AudioGroupKey(entry.library, event);
			if (target == "html5" && pathGroupKey != null && pathGroups.get(pathGroupKey) > 1) {
				entry.preloadState = "unresolved";
				loadProfileComplete = false;
				if (loadProfile != null && loadProfile.state == "standard-file") {
					loadProfile.state = "unsupported";
					loadProfile.diagnostic = "HTML5 groups same-stem sound and music entries in generated manifests; this index does not encode Lime pathGroup records.";
				}
			} else {
				entry.preloadState = preloadStateForEvent(target, event, loadProfile);
				if (entry.preloadState == "unresolved") loadProfileComplete = false;
			}
		}
		for (loadProfile in libraryLoadProfiles)
			if (loadProfile.state != "standard-file" || loadProfile.projectPreloadState != "known") loadProfileComplete = false;
		if (target == null || !complete || !librariesComplete) loadProfileComplete = false;

		var entries:Array<SourceLimeAssetIdentityEntry> = [];
		for (entry in winners) entries.push(entry);
		entries.sort(function(left, right) {
			var byOrder = Reflect.compare(left.candidateOrder, right.candidateOrder);
			if (byOrder != 0) return byOrder;
			var byLibrary = Reflect.compare(left.library, right.library);
			return byLibrary != 0 ? byLibrary : Reflect.compare(left.id, right.id);
		});
		libraries.sort(Reflect.compare);
		var index:SourceLimeAssetIdentityIndex = {
			version:VERSION, owner:owner, engine:canonicalEngine, scope:canonicalScope,
			namespace:ownerNamespace, snapshotId:snapshotId, rootRelative:rootRelative,
			projectSha256:projectSha256.toLowerCase(), complete:complete,
			libraries:libraries, librariesComplete:librariesComplete, loadTarget:target,
			loadProfileComplete:loadProfileComplete, libraryLoadProfiles:libraryLoadProfiles,
			entries:entries, handoff:handoffValue
		};
		var validated = validate(index, owner, canonicalEngine, canonicalScope,
		handoffValue == null ? namespace : ownerNamespace);
		if (validated == null) {
			diagnostics.push("[lime-asset-identity] Generated sidecar failed its own schema validation.");
			return {path:"", content:"", index:null, failed:true, diagnostics:diagnostics};
		}
		var relativeSidecar = sidecarRelativePath(canonicalEngine, canonicalScope);
		var fullPath = normalizeInstallRelative(owner + "/" + relativeSidecar);
		if (fullPath == null || fullPath != owner + "/" + relativeSidecar)
			return {path:"", content:"", index:null, failed:true,
				diagnostics:["[lime-asset-identity] The generated sidecar path is unsafe."]};
		return {path:fullPath, content:serialize(validated), index:validated,
			failed:false, diagnostics:diagnostics};
	}

	public static function serialize(index:SourceLimeAssetIdentityIndex):String {
		if (index == null) throw "A Lime asset identity index is required.";
		return UnicodeSafeJson.stringifyStandard(index) + "\n";
	}

	public static function normalizeOwnerRelative(path:String):Null<String> {
		if (path == null || path == "" || path.indexOf("\\") >= 0) return null;
		var clean = normalizeRelative(path);
		return clean == path ? clean : null;
	}

	static function hasSymbol(value:Null<String>):Bool {
		return value != null && value.indexOf("$") >= 0;
	}

	static function extensionOf(path:String):String {
		if (path == null) return "";
		var normalized = StringTools.replace(path, "\\", "/");
		var slash = normalized.lastIndexOf("/");
		var dot = normalized.lastIndexOf(".");
		if (dot <= slash || dot == normalized.length - 1) return "";
		return normalized.substr(dot).toLowerCase();
	}

	static function normalizeRelative(path:String):Null<String> {
		if (path == null || path == "" || path.startsWith("/") || path.indexOf(":") >= 0
			|| path.indexOf("\x00") >= 0) return null;
		var parts:Array<String> = [];
		for (part in path.split("/")) {
			if (part == "" || part == "." || part == "..") return null;
			parts.push(part);
		}
		return parts.join("/");
	}

	static function isSafeOwnerRoot(path:String):Bool {
		if (path == null || normalizeRelative(path) != path) return false;
		return path.startsWith("assets/imported_mods/") && path.substr("assets/imported_mods/".length) != "";
	}

	static function isNamespace(value:String):Bool {
		return value != null && value != "" && value.length <= 180
			&& ~/^[A-Za-z0-9][A-Za-z0-9._-]*$/.match(value);
	}

	static function isHex(value:String, length:Int):Bool {
		return value != null && value.length == length && ~/^[a-fA-F0-9]+$/.match(value);
	}

	static function isRecord(value:Dynamic):Bool {
		return value != null && !Std.isOfType(value, String) && !Std.isOfType(value, Array)
			&& Reflect.isObject(value);
	}

	static function addLibrary(output:Array<String>, seen:Map<String, Bool>, name:String):Void {
		if (name == null || name == "" || seen.exists(name)) return;
		seen.set(name, true);
		output.push(name);
	}

	static function validIdentityText(value:String, maximum:Int):Bool {
		if (value == null || value == "" || value.length > maximum) return false;
		for (index in 0...value.length) {
			var code = StringTools.unsafeCodeAt(value, index);
			if (code < 0x20 || (code >= 0x7F && code <= 0x9F)) return false;
		}
		return true;
	}

	static function normalizeLogical(path:String):Null<String> {
		if (path == null || path == "" || path.indexOf("\\") >= 0) return null;
		var clean = normalizeRelative(path);
		return clean == path ? clean : null;
	}

	static function normalizeInstallRelative(path:String):Null<String> {
		return normalizeLogical(path);
	}

	static function stringField(value:Dynamic, name:String):Null<String> {
		var field:Dynamic = Reflect.field(value, name);
		return Std.isOfType(field, String) ? cast field : null;
	}

	static function intField(value:Dynamic, name:String):Null<Int> {
		var field:Dynamic = Reflect.field(value, name);
		return Std.isOfType(field, Int) ? cast field : null;
	}

	static function boolField(value:Dynamic, name:String):Null<Bool> {
		var field:Dynamic = Reflect.field(value, name);
		return Std.isOfType(field, Bool) ? cast field : null;
	}
}
