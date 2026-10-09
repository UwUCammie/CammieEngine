package;

import haxe.crypto.Sha256;
import haxe.io.Bytes;
import haxe.io.BytesBuffer;
import haxe.io.Path;
import ImportSourceSnapshot;
#if sys
import sys.FileSystem;
import sys.io.File;
#end
using StringTools;

typedef PsychAssetProfileFlag = {
	var name:String;
	/** One of enabled, disabled, or unresolved. */
	var state:String;
	/** Where the caller obtained this flag value. */
	@:optional var provenance:String;
}

typedef PsychAssetProfileBuild = {
	/** Informational only. The resolver does not infer flags from this string. */
	@:optional var target:String;
	/** Exact build flags supplied by the caller. Missing flags stay unresolved. */
	@:optional var flags:Array<PsychAssetProfileFlag>;
	/** Explicit string values from the selected build, never host environment values. */
	@:optional var values:Array<PsychAssetProfileValue>;
	/** Whether the explicit flag set accounts for every target define. Defaults to false. */
	@:optional var flagsComplete:Bool;
	/** Explicit Lime command token; null means it was not captured. */
	@:optional var command:Null<String>;
}

typedef PsychAssetProfileValue = {
	var name:String;
	var value:String;
	/** Where the caller obtained this string value. */
	@:optional var provenance:String;
}

typedef PsychAssetProfileInputFile = {
	/** Path relative to retained snapshot content, including the selected root. */
	var path:String;
	var size:Int;
	var sha256:String;
	/** Snapshot-relative path of the Project file that included this input. */
	var parentInclude:Null<String>;
	var order:Int;
}

/** One Lime <library>/<swf> declaration, including empty declarations.
	Disabled declarations are retained for diagnostics but do not claim a
	runtime library. An unresolved declaration makes the library table partial. */
typedef PsychAssetProfileLibrary = {
	var order:Int;
	var name:String;
	var state:String;
	var sourcePath:String;
	/** Lime's resolved Library.type; empty means the source field was null. */
	var type:String;
	var typeState:String;
	/** Null means Lime's Library.embed default, not an unresolved value. */
	var embed:Null<Bool>;
	var embedState:String;
	/** Lime's ProjectXMLParser default is false when the attribute is absent. */
	var preload:Bool;
	var preloadState:String;
	var generate:Bool;
	var generateState:String;
	var prefix:String;
	var prefixState:String;
	var conditions:Array<String>;
	@:optional var diagnostic:String;
}

typedef PsychAssetProfileCandidate = {
	var order:Int;
	/** Source directory or file relative to the authenticated Psych root. */
	var sourceRelative:String;
	/** Complete logical destination, such as assets/shared or mods. */
	var targetRelative:String;
	var includePatterns:Array<String>;
	var excludePatterns:Array<String>;
	var conditions:Array<String>;
	var state:String;
	var type:String;
	var embed:String;
	var library:String;
	/** Lime Asset.id for a single-file or nested entry when it overrides targetPath. */
	@:optional var assetId:String;
	/** Distinguishes authored id/name identity from Lime's targetPath default. */
	@:optional var assetIdOverride:Bool;
	@:optional var diagnostic:String;
}

typedef PsychAssetProfileResult = {
	/** Emitted Lime IDs are complete only for Assets, not arbitrary disk-based mod files. */
	@:optional var compiledManifests:Bool;
	var version:Int;
	/** receipt-bound, legacy-unverified, or invalid. */
	var provenance:String;
	var complete:Bool;
	var snapshotId:String;
	var rootRelative:String;
	var sourceEngine:String;
	var namespace:String;
	/** True when an unsupported Project input may hide asset mappings outside candidates. */
	var mappingScopeUnknown:Bool;
	var projectRelative:String;
	var projectSha256:String;
	var buildTarget:String;
	/** Exact explicit Lime command token, or null when it was not captured. */
	var buildCommand:Null<String>;
	var flags:Array<PsychAssetProfileFlag>;
	/** Explicit values supplied by the caller, before Project operations. */
	var buildValues:Array<PsychAssetProfileValue>;
	var buildFlagsComplete:Bool;
	/** Final known value map after Project files and includes are interpreted. */
	var values:Array<PsychAssetProfileValue>;
	var flagsComplete:Bool;
	var contextFingerprint:String;
	var inputFiles:Array<PsychAssetProfileInputFile>;
	/** Explicit Lime library declarations in source order, including empty ones. */
	var libraries:Array<PsychAssetProfileLibrary>;
	/** False if a declaration name/source or unsupported Project input can hide libraries. */
	var librariesComplete:Bool;
	var candidates:Array<PsychAssetProfileCandidate>;
	/** Macro/compiler inputs are recorded as opaque strings, never evaluated. */
	var opaqueBuildInputs:Array<String>;
	var diagnostics:Array<String>;
}

typedef PsychAssetProfileMappedFile = {
	var sourcePath:String;
	/** Path relative to the selected source root, preserving authored spelling. */
	var sourceRelative:String;
	/** Full logical asset path, including the assets/ prefix. */
	var mappedPath:String;
	/** Mapped path relative to an imported owner, or null outside assets/. */
	@:optional var ownerRelative:String;
	var candidateOrder:Int;
	var size:Int;
	var sha256:String;
	/** Resolved asset metadata from the selected Project candidate. */
	@:optional var type:String;
	@:optional var embed:String;
	@:optional var library:String;
	/** Lime Asset.id. Defaults to mappedPath when the Project did not override it. */
	@:optional var assetId:String;
	/** True when Lime used an authored id or nested name instead of targetPath. */
	@:optional var assetIdOverride:Bool;
}

typedef PsychAssetProfileMappedLanguageFile = PsychAssetProfileMappedFile;

/**
	A typed projection for mappings that cannot be emitted as a verified file.
	The candidate may be null when the unresolved scope has no safe declaration.
*/
typedef PsychAssetProfileProjection = {
	@:optional var candidate:PsychAssetProfileCandidate;
	var sourceRelative:Null<String>;
	var ownerRelative:Null<String>;
	var kind:String;
}

typedef PsychAssetProfileDiagnostic = {
	var code:String;
	var severity:String;
	var message:String;
}

typedef PsychAssetProfileWalkResult = {
	var status:String;
	var files:Int;
	var skipped:Int;
	var diagnostics:Array<PsychAssetProfileDiagnostic>;
	/** Root-relative source paths matched under unresolved candidates. */
	var deferredSourcePaths:Array<String>;
	/** Owner-relative targets matched under unresolved candidates. */
	var deferredOwnerPaths:Array<String>;
	/** Known disabled-source projections for legacy importer suppression. */
	var disabledSourcePaths:Array<String>;
	var disabledOwnerPaths:Array<String>;
	/** Destinations that receive distinct source paths. */
	var ambiguousOwnerPaths:Array<String>;
	/** True when an unresolved mapping cannot be safely enumerated. */
	var deferredScopeUnknown:Bool;
	/** Candidate-aware deferred, disabled, and ambiguous mapping projections. */
	var projections:Array<PsychAssetProfileProjection>;
}

private typedef PsychAssetProfileWalkContext = {
	var content:String;
	var selectedRoot:String;
	var receipt:Dynamic;
	var fileIndex:Map<String, Dynamic>;
	var receiptPaths:Array<String>;
	var receiptBytes:Float;
}

/**
	Reads bounded asset-map semantics from authenticated Psych-family Project
	inputs without executing Haxe macros. Callers must verify the complete source
	snapshot before using resolveRetained; this class does not publish mapped files.
*/
class PsychAssetProfile {
	public static inline var VERSION:Int = 4;
	public static inline var ENABLED:String = "enabled";
	public static inline var DISABLED:String = "disabled";
	public static inline var UNRESOLVED:String = "unresolved";
	public static inline var MAX_PROJECT_BYTES:Int = 4 * 1024 * 1024;
	public static inline var MAX_PROJECT_INPUT_FILES:Int = 64;
	public static inline var MAX_PROJECT_INPUT_BYTES:Float = 16 * 1024 * 1024;
	public static inline var MAX_PROJECT_INCLUDE_DEPTH:Int = 32;
	public static inline var MAX_PROJECT_TOTAL_DEPTH:Int = 64;
	public static inline var MAX_RECEIPT_BYTES:Int = 16 * 1024 * 1024;
	public static inline var MAX_XML_NODES:Int = 16384;
	public static inline var MAX_XML_DEPTH:Int = 48;
	public static inline var MAX_LANGUAGE_SCOPES:Int = 4096;
	public static inline var MAX_LANGUAGE_ENTRIES:Int = 16384;
	public static inline var MAX_LANGUAGE_DEPTH:Int = 10;
	public static inline var MAX_LANGUAGE_FILE_BYTES:Int = 4 * 1024 * 1024;
	public static inline var MAX_LANGUAGE_TOTAL_BYTES:Float = 64 * 1024 * 1024;
	public static inline var MAX_MAPPED_ENTRIES:Int = 262144;
	public static inline var MAX_MAPPED_DEPTH:Int = 64;
	public static inline var MAX_MAPPED_FILE_BYTES:Int = 2147483647;

	static final DEFAULT_EXCLUDES:Array<String> = [".*", "cvs", "thumbs.db", "desktop.ini", "*.fla", "*.hash"];
	static final RESERVED_LANGUAGE_ROOTS:Array<String> = [
		"shared", "mods", "mod", "imported_mods", "assets", "content", "source", "scripts",
		"songs", "data", "images", "sounds", "music", "videos", "fonts", "shaders",
		"animations", "plugins", "events", "characters", "stages"
	];

	/**
		Resolve one root recorded by ImportRefreshManager. The caller supplies its
		root.relative, engine, and namespace values from that record, plus the
		retained snapshot id. This method binds Project.xml bytes to receipt.json;
		it does not replace the manager's prior whole-snapshot verification.
	*/
	public static function resolveRetained(snapshotContentRoot:String, snapshotId:String,
		rootRelative:String, sourceEngine:String, namespace:String,
		?build:PsychAssetProfileBuild, ?cancelled:Void->Bool):PsychAssetProfileResult {
		var result = emptyResult("invalid", snapshotId, rootRelative, sourceEngine, namespace,
			build == null ? "" : build.target);
		#if sys
		checkpointProjectWork(cancelled);
		if (canonicalEngine(sourceEngine) == "")
			return fail(result, "engine-mismatch", "A recorded Psych Engine or Nightmare Vision source root is required.");
		if (!validNamespace(namespace))
			return fail(result, "invalid-namespace", "The recorded owner namespace is invalid.");
		var relative = normalizeRelative(rootRelative, true);
		if (relative == null)
			return fail(result, "invalid-root-relative", "The recorded source root is not a safe relative path.");
		var content = canonicalDirectory(snapshotContentRoot);
		if (content == "" || Path.withoutDirectory(Path.normalize(content)).toLowerCase() != "content")
			return fail(result, "invalid-snapshot-content", "The retained snapshot content directory is invalid.");
		if (!validSnapshotId(snapshotId)
			|| !samePath(Path.withoutDirectory(Path.directory(content)), snapshotId))
			return fail(result, "snapshot-id-mismatch", "The retained snapshot path does not match its recorded id.");
		var receipt = readSnapshotReceipt(content, snapshotId, result);
		if (receipt == null) return result;
		var selectedRoot = containedDirectory(content, relative);
		if (selectedRoot == "")
			return fail(result, "source-root-outside-snapshot", "The recorded source root is missing or leaves retained content.");
		var projectPath = directProjectFile(selectedRoot, result);
		if (projectPath == "") {
			if (result.diagnostics.length == 1 && StringTools.startsWith(result.diagnostics[0], "project-xml-missing:"))
				return SourceCompiledAssetProfile.resolve(content,selectedRoot,receipt,result,cancelled);
			return result;
		}
		var projectName = Path.withoutDirectory(projectPath);
		var projectRelative = joinRelative(relative, projectName);
		var fileEntry = receiptFile(receipt, projectRelative, result);
		if (fileEntry == null)
			return fail(result, "project-not-in-snapshot", "The selected root Project.xml is absent from the retained snapshot receipt.");
		var projectBytes = verifiedProjectBytes(projectPath, fileEntry, MAX_PROJECT_BYTES,
			result, "project-hash-mismatch");
		if (projectBytes == null) return result;
		result.provenance = "receipt-bound";
		result.complete = true;
		result.rootRelative = relative;
		result.projectRelative = projectRelative;
		result.projectSha256 = lower(Std.string(Reflect.field(fileEntry, "sha256")));
		result.flags = buildFlags(build);
		var values = buildValues(build, result);
		if (values == null) return result;
		result.buildValues = values;
		result.buildFlagsComplete = buildFlagsComplete(build);
		result.buildCommand = buildCommand(build, result);
		if (result.provenance == "invalid") return result;
		result.values = values.copy();
		result.flagsComplete = result.buildFlagsComplete;
		result.contextFingerprint = fingerprintBuildContext(result.flags, result.buildValues,
			result.buildFlagsComplete, result.buildCommand);
		result.inputFiles.push({path:projectRelative, size:projectBytes.length,
			sha256:result.projectSha256, parentInclude:null, order:0});
		parseProject(projectPath, selectedRoot, content, receipt, projectBytes, build, result, true, cancelled);
		updateCompleteness(result);
		return result;
		#else
		return fail(result, "unsupported-platform", "Psych asset profile resolution requires a sys filesystem target.");
		#end
	}

	/**
		Parse a direct Project.xml for migration diagnostics only. It is explicitly
		unverified, carries no snapshot provenance, and cannot be walked/published.
	*/
	public static function resolveUnverified(projectRoot:String, sourceEngine:String, namespace:String,
		?build:PsychAssetProfileBuild):PsychAssetProfileResult {
		var result = emptyResult("legacy-unverified", "", "", sourceEngine, namespace,
			build == null ? "" : build.target);
		#if sys
		if (canonicalEngine(sourceEngine) == "")
			return fail(result, "engine-mismatch", "A Psych Engine or Nightmare Vision label is required for Project.xml inspection.");
		if (!validNamespace(namespace))
			return fail(result, "invalid-namespace", "The recorded owner namespace is invalid.");
		var root = canonicalDirectory(projectRoot);
		if (root == "") return fail(result, "invalid-project-root", "The project root is missing.");
		var projectPath = directProjectFile(root, result);
		if (projectPath == "") return result;
		var projectBytes:Bytes;
		try {
			projectBytes = File.getBytes(projectPath);
			if (projectBytes.length > MAX_PROJECT_BYTES)
				return fail(result, "project-size-limit", "Project.xml exceeds the profile parser size limit.");
			result.projectSha256 = Sha256.make(projectBytes).toHex();
		} catch (error:Dynamic) {
			return fail(result, "project-read-failed", "Could not read Project.xml: " + Std.string(error));
		}
		result.provenance = "legacy-unverified";
		result.complete = true;
		result.projectRelative = Path.withoutDirectory(projectPath);
		result.flags = buildFlags(build);
		var values = buildValues(build, result);
		if (values == null) return result;
		result.buildValues = values;
		result.buildFlagsComplete = buildFlagsComplete(build);
		result.buildCommand = buildCommand(build, result);
		if (result.provenance == "invalid") return result;
		result.values = values.copy();
		result.flagsComplete = result.buildFlagsComplete;
		result.contextFingerprint = fingerprintBuildContext(result.flags, result.buildValues,
			result.buildFlagsComplete, result.buildCommand);
		parseProject(projectPath, root, "", null, projectBytes, build, result, false);
		updateCompleteness(result);
		return result;
		#else
		return fail(result, "unsupported-platform", "Psych asset profile resolution requires a sys filesystem target.");
		#end
	}

	/** Map a safe suffix below one candidate through its authored rename. */
	public static function mapPath(candidate:PsychAssetProfileCandidate, sourceSuffix:String):Null<String> {
		if (candidate == null || candidate.state != ENABLED) return null;
		return mapKnownCandidatePath(candidate, sourceSuffix);
	}

	/** Map a candidate suffix to an owner-relative path only when its rename is
	 * under the runtime assets/ root. Files renamed to mods/ or elsewhere have no
	 * imported-owner path. */
	public static function ownerRelative(candidate:PsychAssetProfileCandidate, sourceSuffix:String):Null<String> {
		var mapped = mapPath(candidate, sourceSuffix);
		return mapped == null ? null : ownerRelativePath(mapped);
	}

	/**
		Enumerate all ordinary files reachable through enabled Project.xml asset
		mappings. Events are receipt-bound and keep declaration/path order. The
		callback is a planning hook; callers should wait for the final status and
		collision projections before publishing any event.
	*/
	public static function walkMappedFiles(profile:PsychAssetProfileResult, snapshotContentRoot:String,
		?onFile:PsychAssetProfileMappedFile->Void,
		?onDiagnostic:PsychAssetProfileDiagnostic->Void,
		?cancelled:Void->Bool,
		?sourceFilter:String->String->Bool,
		?candidateFilter:PsychAssetProfileCandidate->String->String->Bool):PsychAssetProfileWalkResult {
		var result = newWalkResult();
		#if sys
		var context = prepareWalkContext(profile, snapshotContentRoot, result, onDiagnostic, "Mapped-file");
		if (context == null) return result;
		if (profile.mappingScopeUnknown) {
			markWalkIncomplete(result);
			result.deferredScopeUnknown = true;
			recordTypedProjection(result, null, null, null, "deferred");
			addWalkDiagnostic(result, onDiagnostic, "profile-mapping-scope-unknown", "error",
				"An unsupported or unavailable Project input may contain additional asset mappings.");
		}
		var counters = {entries:0, scopes:0, bytes:0.0, hashedBytes:0.0, hashes:new Map<String, Dynamic>()};
		var destinationSources:Map<String, String> = new Map();
		var destinationProjectionSources:Map<String, Dynamic> = new Map();
		var ambiguous:Map<String, Bool> = new Map();
		if (profile.candidates == null) {
			markWalkIncomplete(result);
			result.deferredScopeUnknown = true;
			addWalkDiagnostic(result, onDiagnostic, "candidate-list-invalid", "error",
				"The resolved asset profile has no candidate list.");
			return result;
		}
		for (candidate in profile.candidates) {
			if (walkCancelled(cancelled)) {
				result.status = "cancelled";
				return result;
			}
				if (candidate == null) {
					markWalkIncomplete(result);
					result.deferredScopeUnknown = true;
					recordTypedProjection(result, null, null, null, "deferred");
				addWalkDiagnostic(result, onDiagnostic, "candidate-invalid", "error",
					"The asset profile contains an empty mapping candidate.");
				continue;
			}
			var candidateState = candidate.state == ENABLED ? ENABLED
				: candidate.state == DISABLED ? DISABLED : UNRESOLVED;
			if (candidateState == UNRESOLVED) {
				markWalkIncomplete(result);
				result.skipped++;
				addWalkDiagnostic(result, onDiagnostic, "candidate-unresolved", "warning",
					"Skipped unresolved Project.xml asset mapping at declaration " + candidate.order + ".");
			}
			if (!candidateScopeIsSafe(candidate)) {
				recordScopeProjection(result, candidate, "", candidateState != DISABLED, true);
				if (candidateState != DISABLED) {
					markWalkIncomplete(result);
					result.deferredScopeUnknown = true;
					addWalkDiagnostic(result, onDiagnostic, "candidate-scope-unknown", "error",
						"An unresolved source, target, or filter expression cannot be safely enumerated.");
				}
				else {
					result.deferredScopeUnknown = true;
					addWalkDiagnostic(result, onDiagnostic, "disabled-scope-unknown", "warning",
						"A disabled mapping has a source or filter expression that cannot be safely enumerated.");
				}
				continue;
			}
			var candidatePath = containedSourcePath(context.selectedRoot, candidate.sourceRelative);
			if (candidatePath == "") {
				markWalkIncomplete(result);
				result.skipped++;
				recordScopeProjection(result, candidate, "", candidateState != DISABLED, true);
				addWalkDiagnostic(result, onDiagnostic, "candidate-source-escape", "error",
					"A mapped source candidate leaves its authenticated source root.");
				continue;
			}
			var candidateExists = false;
			try candidateExists = FileSystem.exists(candidatePath) catch (error:Dynamic) {
				markWalkIncomplete(result);
				result.skipped++;
				recordScopeProjection(result, candidate, "", candidateState != DISABLED, true);
				addWalkDiagnostic(result, onDiagnostic, "candidate-source-stat-failed", "error",
					"Could not inspect a mapped Project.xml source path: " + Std.string(error));
				continue;
			}
			if (!candidateExists) {
				markWalkIncomplete(result);
				result.skipped++;
				recordScopeProjection(result, candidate, "", candidateState != DISABLED, false);
				addWalkDiagnostic(result, onDiagnostic, "candidate-source-missing",
					candidateState == DISABLED ? "warning" : "error",
					"A mapped Project.xml source path is absent from the retained snapshot.");
				continue;
			}
			var candidateIsDirectory = false;
			try candidateIsDirectory = FileSystem.isDirectory(candidatePath) catch (error:Dynamic) {
				markWalkIncomplete(result);
				result.skipped++;
				recordScopeProjection(result, candidate, "", candidateState != DISABLED, true);
				addWalkDiagnostic(result, onDiagnostic, "candidate-source-stat-failed", "error",
					"Could not inspect a mapped Project.xml source path: " + Std.string(error));
				continue;
			}
			if (candidateIsDirectory && isBundleFile(candidatePath)) {
				result.skipped++;
				var bundleSource = candidateSourceRelative(candidate, "");
				var bundleTarget = mapKnownCandidatePath(candidate, "");
				if (candidateState == DISABLED) {
					appendUnique(result.disabledSourcePaths, bundleSource);
					appendUnique(result.disabledOwnerPaths, bundleTarget == null ? null : ownerRelativePath(bundleTarget));
					addWalkDiagnostic(result, onDiagnostic, "bundle-disabled", "warning",
						"A disabled Lime bundle mapping is recorded without flattening its contents.");
				} else {
					markWalkIncomplete(result);
					result.deferredScopeUnknown = true;
					appendUnique(result.deferredSourcePaths, bundleSource);
					appendUnique(result.deferredOwnerPaths, bundleTarget == null ? null : ownerRelativePath(bundleTarget));
					addWalkDiagnostic(result, onDiagnostic, "bundle-unsupported", "error",
						"Lime bundle mappings are not flattened until their native packaging policy is implemented.");
				}
				continue;
			}
			var seenSources:Map<String, Bool> = new Map();
			var filter = function(filename:String):Bool return matchesMappedFile(candidate, filename);
			var consume = function(sourcePath:String, suffix:String):Void {
				var sourceRelative = candidateSourceRelative(candidate, suffix);
				var mappedPath = mapKnownCandidatePath(candidate, suffix);
				if (sourceRelative == null || mappedPath == null) {
					markWalkIncomplete(result);
					result.deferredScopeUnknown = true;
					addWalkDiagnostic(result, onDiagnostic, "mapped-path-invalid", "error",
						"A mapped source or target path cannot be normalized for filtering.");
					return;
				}
				if (sourceFilter != null) {
					var included = false;
					try included = sourceFilter(sourceRelative, mappedPath) catch (error:Dynamic) {
						markWalkIncomplete(result);
						recordScopeProjection(result, candidate, suffix, candidateState != DISABLED, true);
						addWalkDiagnostic(result, onDiagnostic, "source-filter-failed", "error",
							"The mapped-file source filter failed: " + Std.string(error));
						return;
					}
					if (!included) return;
				}
				if (candidateFilter != null) {
					var included = false;
					try included = candidateFilter(candidate, sourceRelative, mappedPath) catch (error:Dynamic) {
						markWalkIncomplete(result);
						recordScopeProjection(result, candidate, suffix, candidateState != DISABLED, true);
						addWalkDiagnostic(result, onDiagnostic, "source-filter-failed", "error",
							"The mapped-file candidate filter failed: " + Std.string(error));
						return;
					}
					if (!included) return;
				}
				seenSources.set(pathKey(sourceRelative), true);
				if (candidateState == DISABLED) {
					noteNonEnabledMapping(profile, context, candidate, sourcePath, suffix,
						result, onDiagnostic, false);
					return;
				}
				var event = verifiedMappedFile(profile, context, candidate, sourcePath, suffix,
					counters, result, onDiagnostic, cancelled, MAX_MAPPED_FILE_BYTES,
					Math.POSITIVE_INFINITY, "mapped");
				if (event == null) {
					result.skipped++;
					recordScopeProjection(result, candidate, suffix, true, false);
					return;
				}
				if (candidateState == UNRESOLVED) {
					result.skipped++;
					recordTypedProjection(result, candidate, event.sourceRelative,
						event.ownerRelative, "deferred");
					appendUnique(result.deferredSourcePaths, event.sourceRelative);
					appendUnique(result.deferredOwnerPaths, event.ownerRelative);
					return;
				}
				result.files++;
				if (event.ownerRelative != null) {
					var destinationKey = pathKey(event.ownerRelative);
					var sourceKey = pathKey(event.sourcePath);
					if (destinationSources.exists(destinationKey)
						&& destinationSources.get(destinationKey) != sourceKey) {
						markWalkIncomplete(result);
						if (!ambiguous.exists(destinationKey)) {
							ambiguous.set(destinationKey, true);
							result.ambiguousOwnerPaths.push(event.ownerRelative);
							addWalkDiagnostic(result, onDiagnostic, "owner-path-collision", "error",
								"Distinct mapped sources target the same owner asset path: " + event.ownerRelative);
						}
						var previous:Dynamic = destinationProjectionSources.get(destinationKey);
						if (previous != null)
							recordTypedProjection(result,
								cast Reflect.field(previous, "candidate"),
								Reflect.field(previous, "sourceRelative"), event.ownerRelative, "ambiguous");
						recordTypedProjection(result, candidate, event.sourceRelative,
							event.ownerRelative, "ambiguous");
					} else if (!destinationSources.exists(destinationKey))
						destinationSources.set(destinationKey, sourceKey);
					if (!destinationProjectionSources.exists(destinationKey))
						destinationProjectionSources.set(destinationKey,
							{candidate:candidate, sourceRelative:event.sourceRelative});
				}
				if (onFile != null) onFile(event);
			};
			enumerateCandidateFiles(context.selectedRoot, candidate, candidatePath, "", counters,
				result, onDiagnostic, cancelled, MAX_MAPPED_ENTRIES, MAX_MAPPED_DEPTH,
				"mapped", filter, consume, new Map(), 0);
			if (result.status == "cancelled") return result;
			checkMissingReceiptFiles(profile, context, candidate, candidatePath, seenSources,
				result, onDiagnostic, cancelled, sourceFilter, candidateFilter);
			if (result.status == "cancelled") return result;
		}
		if (!profile.complete) markWalkIncomplete(result);
		return result;
		#else
		markWalkIncomplete(result);
		return result;
		#end
	}

	/**
		Enumerate .lang files only in Psych's conventional data scopes. The same
		candidate traversal and receipt-bound file verifier back walkMappedFiles.
	*/
	public static function walkLanguageFiles(profile:PsychAssetProfileResult, snapshotContentRoot:String,
		?onFile:PsychAssetProfileMappedLanguageFile->Void,
		?onDiagnostic:PsychAssetProfileDiagnostic->Void,
		?cancelled:Void->Bool):PsychAssetProfileWalkResult {
		var result = newWalkResult();
		#if sys
		var context = prepareWalkContext(profile, snapshotContentRoot, result, onDiagnostic, "Language");
		if (context == null) return result;
		if (profile.mappingScopeUnknown) {
			markWalkIncomplete(result);
			result.deferredScopeUnknown = true;
			addWalkDiagnostic(result, onDiagnostic, "profile-mapping-scope-unknown", "error",
				"An unsupported or unavailable Project input may contain additional asset mappings.");
		}
		var counters = {entries:0, scopes:0, bytes:0.0, hashedBytes:0.0, hashes:new Map<String, Dynamic>()};
		if (profile.candidates == null) {
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, "candidate-list-invalid", "error",
				"The resolved asset profile has no candidate list.");
			return result;
		}
		for (candidate in profile.candidates) {
			if (walkCancelled(cancelled)) {
				result.status = "cancelled";
				return result;
			}
			if (candidate == null || candidate.state == DISABLED) continue;
			if (candidate.state != ENABLED) {
				markWalkIncomplete(result);
				result.skipped++;
				addWalkDiagnostic(result, onDiagnostic, "candidate-unresolved", "warning",
					"Skipped unresolved Project.xml asset mapping at declaration " + candidate.order + ".");
				continue;
			}
			if (ownerRelativePath(candidate.targetRelative) == null) continue;
			if (!candidateScopeIsSafe(candidate)) {
				markWalkIncomplete(result);
				result.deferredScopeUnknown = true;
				addWalkDiagnostic(result, onDiagnostic, "candidate-scope-unknown", "error",
					"An enabled language mapping has a source, target, or filter that cannot be safely enumerated.");
				continue;
			}
			var candidatePath = containedSourcePath(context.selectedRoot, candidate.sourceRelative);
			if (candidatePath == "") {
				markWalkIncomplete(result);
				result.skipped++;
				addWalkDiagnostic(result, onDiagnostic, "candidate-source-escape", "error",
					"A mapped language candidate leaves its authenticated source root.");
				continue;
			}
			if (!FileSystem.exists(candidatePath)) {
				result.skipped++;
				continue;
			}
			var languageFilter = function(filename:String):Bool return matchesLanguageFile(candidate, filename);
			var processFile = function(sourcePath:String, suffix:String):Void {
				var event = verifiedMappedFile(profile, context, candidate, sourcePath, suffix,
					counters, result, onDiagnostic, cancelled, MAX_LANGUAGE_FILE_BYTES,
					MAX_LANGUAGE_TOTAL_BYTES, "language");
				if (event == null) {
					result.skipped++;
					return;
				}
				result.files++;
				if (onFile != null) onFile(event);
			};
			if (!FileSystem.isDirectory(candidatePath)) {
				enumerateCandidateFiles(context.selectedRoot, candidate, candidatePath, "", counters,
					result, onDiagnostic, cancelled, MAX_LANGUAGE_ENTRIES, MAX_LANGUAGE_DEPTH,
					"language", languageFilter, processFile, new Map(), 0);
				if (result.status == "cancelled") return result;
				continue;
			}
			var scopes = languageScopes(candidatePath, candidate, result, onDiagnostic);
			for (scope in scopes) {
				if (walkCancelled(cancelled)) {
					result.status = "cancelled";
					return result;
				}
				counters.scopes++;
				if (counters.scopes > MAX_LANGUAGE_SCOPES) {
					markWalkIncomplete(result);
					addWalkDiagnostic(result, onDiagnostic, "scope-limit", "error",
						"Psych language scope limit was reached.");
					return result;
				}
				var dataDirectory = uniqueChildDirectory(scope.path, "data", context.selectedRoot,
					result, onDiagnostic);
				if (dataDirectory == "") continue;
				var suffixParts:Array<String> = [];
				if (scope.suffix != "") suffixParts.push(scope.suffix);
				suffixParts.push("data");
				enumerateCandidateFiles(context.selectedRoot, candidate, dataDirectory,
					suffixParts.join("/"), counters, result, onDiagnostic, cancelled,
					MAX_LANGUAGE_ENTRIES, MAX_LANGUAGE_DEPTH, "language", languageFilter,
					processFile, new Map(), 0);
				if (result.status == "cancelled") return result;
			}
		}
		if (!profile.complete) markWalkIncomplete(result);
		return result;
		#else
		markWalkIncomplete(result);
		return result;
		#end
	}

	static function prepareWalkContext(profile:PsychAssetProfileResult, snapshotContentRoot:String,
		result:PsychAssetProfileWalkResult, onDiagnostic:PsychAssetProfileDiagnostic->Void,
		label:String):Null<PsychAssetProfileWalkContext> {
		if (profile == null || profile.provenance != "receipt-bound") {
			markWalkIncomplete(result);
			result.deferredScopeUnknown = true;
			addWalkDiagnostic(result, onDiagnostic, "unverified-profile", "error",
				label + " enumeration requires a retained, receipt-bound source profile.");
			return null;
		}
		var content = canonicalDirectory(snapshotContentRoot);
		if (content == "" || !samePath(Path.withoutDirectory(Path.normalize(content)), "content")
			|| !samePath(Path.withoutDirectory(Path.directory(content)), profile.snapshotId)) {
			markWalkIncomplete(result);
			result.deferredScopeUnknown = true;
			addWalkDiagnostic(result, onDiagnostic, "snapshot-id-mismatch", "error",
				label + " enumeration snapshot path does not match the resolved profile.");
			return null;
		}
		var receipt = readSnapshotReceipt(content, profile.snapshotId, null);
		if (receipt == null) {
			markWalkIncomplete(result);
			result.deferredScopeUnknown = true;
			addWalkDiagnostic(result, onDiagnostic, "snapshot-receipt-invalid", "error",
				label + " enumeration could not load the retained snapshot receipt.");
			return null;
		}
		var selectedRoot = containedDirectory(content, profile.rootRelative);
		if (selectedRoot == "") {
			markWalkIncomplete(result);
			result.deferredScopeUnknown = true;
			addWalkDiagnostic(result, onDiagnostic, "source-root-outside-snapshot", "error",
				"The resolved profile root is missing or leaves retained content.");
			return null;
		}
		var indexed = indexReceiptFiles(receipt, result, onDiagnostic);
		if (indexed == null) return null;
		return {content:content, selectedRoot:selectedRoot, receipt:receipt,
			fileIndex:indexed.index, receiptPaths:indexed.paths, receiptBytes:indexed.bytes};
	}

	static function indexReceiptFiles(receipt:Dynamic, result:PsychAssetProfileWalkResult,
		onDiagnostic:PsychAssetProfileDiagnostic->Void):Null<{index:Map<String, Dynamic>, bytes:Float, paths:Array<String>}> {
		var files:Dynamic = Reflect.field(receipt, "files");
		if (!Std.isOfType(files, Array)) {
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, "snapshot-file-table-invalid", "error",
				"The retained snapshot receipt has no valid file table.");
			result.deferredScopeUnknown = true;
			return null;
		}
		var index:Map<String, Dynamic> = new Map();
		var paths:Array<String> = [];
		var bytes:Float = 0;
		var count = 0;
		for (entry in (cast files:Array<Dynamic>)) {
			count++;
			if (count > MAX_MAPPED_ENTRIES) {
				markWalkIncomplete(result);
				result.deferredScopeUnknown = true;
				addWalkDiagnostic(result, onDiagnostic, "snapshot-file-table-limit", "error",
					"The retained snapshot receipt exceeds the mapped-file index limit.");
				return null;
			}
			var rawPath:Dynamic = entry == null ? null : Reflect.field(entry, "path");
			var rawSize:Dynamic = entry == null ? null : Reflect.field(entry, "size");
			var rawHash:Dynamic = entry == null ? null : Reflect.field(entry, "sha256");
			if (!Std.isOfType(rawPath, String) || !Std.isOfType(rawSize, Int)
				|| (cast rawSize:Int) < 0 || rawHash == null
				|| !~/^[0-9a-fA-F]{64}$/.match(Std.string(rawHash))) {
				markWalkIncomplete(result);
				result.deferredScopeUnknown = true;
				addWalkDiagnostic(result, onDiagnostic, "snapshot-file-entry-invalid", "error",
					"The retained snapshot receipt contains an invalid file record.");
				continue;
			}
			var cleanPath = normalizeRelative(Std.string(rawPath), false);
			if (cleanPath == null || cleanPath != StringTools.replace(Std.string(rawPath), "\\", "/")) {
				markWalkIncomplete(result);
				result.deferredScopeUnknown = true;
				addWalkDiagnostic(result, onDiagnostic, "snapshot-file-path-invalid", "error",
					"The retained snapshot receipt contains an unsafe file path.");
				continue;
			}
			var key = pathKey(cleanPath);
			if (index.exists(key)) {
				index.set(key, null);
				markWalkIncomplete(result);
				result.deferredScopeUnknown = true;
				addWalkDiagnostic(result, onDiagnostic, "snapshot-file-path-duplicate", "error",
					"The retained snapshot receipt contains duplicate file paths.");
				continue;
			}
			index.set(key, entry);
			paths.push(key);
			bytes += (cast rawSize:Int);
		}
		paths.sort(Reflect.compare);
		return {index:index, bytes:bytes, paths:paths};
	}

	static function enumerateCandidateFiles(selectedRoot:String, candidate:PsychAssetProfileCandidate,
		sourcePath:String, suffixPrefix:String, counters:Dynamic, result:PsychAssetProfileWalkResult,
		onDiagnostic:PsychAssetProfileDiagnostic->Void, cancelled:Void->Bool,
		maxEntries:Int, maxDepth:Int, diagnosticPrefix:String, extraFilter:String->Bool,
		onFile:String->String->Void, ancestry:Map<String, Bool>, depth:Int):Void {
		if (walkCancelled(cancelled)) {
			result.status = "cancelled";
			return;
		}
		if (depth > maxDepth) {
			markWalkIncomplete(result);
			recordTraversalProjection(result, candidate, suffixPrefix, true);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-depth-limit", "error",
				"The mapped source directory depth limit was reached.");
			return;
		}
		var sourceIsDirectory = false;
		try sourceIsDirectory = FileSystem.isDirectory(sourcePath) catch (error:Dynamic) {
			markWalkIncomplete(result);
			recordTraversalProjection(result, candidate, suffixPrefix, true);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-source-stat-failed", "error",
				"Could not inspect a mapped source path: " + Std.string(error));
			return;
		}
		if (!sourceIsDirectory) {
			counters.entries++;
			if (counters.entries > maxEntries) {
				markWalkIncomplete(result);
				recordTraversalProjection(result, candidate, suffixPrefix, true);
				addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-entry-limit", "error",
					"The mapped source entry limit was reached.");
				return;
			}
			var filename = Path.withoutDirectory(sourcePath);
			if (!validEntry(filename)) {
				markWalkIncomplete(result);
				recordTraversalProjection(result, candidate, suffixPrefix, true);
				addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-invalid-entry", "error",
					"An invalid filename was found in a mapped source tree.");
				return;
			}
			if (matchesMappedFile(candidate, filename) && (extraFilter == null || extraFilter(filename)))
				onFile(sourcePath, suffixPrefix);
			return;
		}
		var canonical = canonicalDirectory(sourcePath);
		if (canonical == "" || !isWithin(canonical, selectedRoot)) {
			markWalkIncomplete(result);
			recordTraversalProjection(result, candidate, suffixPrefix, true);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-source-escape", "error",
				"A mapped source directory leaves its authenticated source root.");
			return;
		}
		var directoryKey = pathKey(canonical);
		if (ancestry.exists(directoryKey)) {
			markWalkIncomplete(result);
			recordTraversalProjection(result, candidate, suffixPrefix, true);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-directory-cycle", "error",
				"A mapped source directory resolves back to an ancestor.");
			return;
		}
		var nextAncestry:Map<String, Bool> = new Map();
		for (key in ancestry.keys()) nextAncestry.set(key, true);
		nextAncestry.set(directoryKey, true);
		var entries:Array<String>;
		try {
			entries = FileSystem.readDirectory(canonical);
			entries.sort(Reflect.compare);
		} catch (error:Dynamic) {
			markWalkIncomplete(result);
			recordTraversalProjection(result, candidate, suffixPrefix, true);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-directory-read-failed", "error",
				"Could not inspect a mapped source directory: " + Std.string(error));
			return;
		}
		for (entry in entries) {
			if (walkCancelled(cancelled)) {
				result.status = "cancelled";
				return;
			}
			counters.entries++;
			if (counters.entries > maxEntries) {
				markWalkIncomplete(result);
				recordTraversalProjection(result, candidate, suffixPrefix, true);
				addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-entry-limit", "error",
					"The mapped source entry limit was reached.");
				return;
			}
			if (!validEntry(entry)) {
				markWalkIncomplete(result);
				recordTraversalProjection(result, candidate, suffixPrefix, true);
				addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-invalid-entry", "error",
					"An invalid filename was found in a mapped source tree.");
				continue;
			}
			var childPath = Path.join([canonical, entry]);
			var childCanonical = canonicalExistingPath(childPath);
			if (childCanonical == "" || !isWithin(childCanonical, selectedRoot)) {
				markWalkIncomplete(result);
				var childSuffix = joinRelative(suffixPrefix, entry);
				var childIsDirectory = false;
				try childIsDirectory = FileSystem.isDirectory(childPath) catch (_:Dynamic) {}
				recordTraversalProjection(result, candidate, childSuffix, childIsDirectory);
				addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-entry-escape", "error",
					"A mapped source entry leaves its authenticated source root.");
				continue;
			}
			if (FileSystem.isDirectory(childPath)) {
				if (isBundleFile(entry)) {
					result.skipped++;
					var bundleSuffix = joinRelative(suffixPrefix, entry);
					var bundleSource = candidateSourceRelative(candidate, bundleSuffix);
					var bundleTarget = mapKnownCandidatePath(candidate, bundleSuffix);
					if (candidate.state == DISABLED) {
						appendUnique(result.disabledSourcePaths, bundleSource);
						appendUnique(result.disabledOwnerPaths, bundleTarget == null ? null : ownerRelativePath(bundleTarget));
						addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-bundle-disabled", "warning",
							"A disabled Lime bundle directory is recorded without flattening its contents.");
					} else {
						markWalkIncomplete(result);
						result.deferredScopeUnknown = true;
						appendUnique(result.deferredSourcePaths, bundleSource);
						appendUnique(result.deferredOwnerPaths, bundleTarget == null ? null : ownerRelativePath(bundleTarget));
						addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-bundle-unsupported", "error",
							"A .bundle directory cannot be flattened into ordinary assets.");
					}
					continue;
				}
				if (isExcludedDirectory(candidate, entry)) continue;
				enumerateCandidateFiles(selectedRoot, candidate, childPath,
					joinRelative(suffixPrefix, entry), counters, result, onDiagnostic, cancelled,
					maxEntries, maxDepth, diagnosticPrefix, extraFilter, onFile,
					nextAncestry, depth + 1);
				if (result.status == "cancelled") return;
				continue;
			}
			if (matchesMappedFile(candidate, entry) && (extraFilter == null || extraFilter(entry)))
				onFile(childCanonical, joinRelative(suffixPrefix, entry));
			if (result.status == "cancelled") return;
		}
	}

	static function verifiedMappedFile(profile:PsychAssetProfileResult, context:PsychAssetProfileWalkContext,
		candidate:PsychAssetProfileCandidate, sourcePath:String, suffix:String, counters:Dynamic,
		result:PsychAssetProfileWalkResult, onDiagnostic:PsychAssetProfileDiagnostic->Void,
		cancelled:Void->Bool, maxFileBytes:Int, maxTotalBytes:Float,
		diagnosticPrefix:String):Null<PsychAssetProfileMappedFile> {
		var canonical = canonicalExistingPath(sourcePath);
		if (canonical == "" || !isWithin(canonical, context.selectedRoot)) {
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-source-escape", "error",
				"A mapped file leaves its authenticated source root.");
			return null;
		}
		var sourceRelative = candidateSourceRelative(candidate, suffix);
		var mappedPath = mapKnownCandidatePath(candidate, suffix);
		if (sourceRelative == null || mappedPath == null) {
			markWalkIncomplete(result);
			result.deferredScopeUnknown = true;
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-path-invalid", "error",
				"A mapped file has an invalid source or target path.");
			return null;
		}
		var snapshotRelative = joinRelative(profile.rootRelative, sourceRelative);
		var entry = indexedReceiptFile(context.fileIndex, snapshotRelative);
		if (entry == null) {
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-file-not-in-snapshot", "error",
				"A mapped file is not listed in the retained snapshot receipt.");
			return null;
		}
		var before:sys.FileStat;
		try before = FileSystem.stat(canonical) catch (error:Dynamic) {
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-file-stat-failed", "error",
				"Could not inspect a mapped file: " + Std.string(error));
			return null;
		}
		var expectedSize:Dynamic = Reflect.field(entry, "size");
		var expectedHash:Dynamic = Reflect.field(entry, "sha256");
		if (!Std.isOfType(expectedSize, Int) || before.size < 0 || before.size > maxFileBytes
			|| before.size != (cast expectedSize:Int)) {
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-file-hash-mismatch", "error",
				"A mapped file size differs from its receipt or walk limit.");
			return null;
		}
		if (counters.bytes + before.size > maxTotalBytes) {
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-byte-limit", "error",
				"Mapped source bytes exceeded the configured safety limit.");
			return null;
		}
		var cacheKey = pathKey(canonical);
		var cached:Dynamic = counters.hashes.get(cacheKey);
		var digest:String = null;
		if (cached != null) {
			if (Reflect.field(cached, "size") != before.size
				|| Reflect.field(cached, "modified") != before.mtime.getTime()) {
				markWalkIncomplete(result);
				addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-file-changed", "error",
					"A mapped file changed during the profile walk.");
				return null;
			}
			digest = Reflect.field(cached, "sha256");
		} else {
			if (counters.hashedBytes + before.size > context.receiptBytes) {
				markWalkIncomplete(result);
				addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-snapshot-byte-limit", "error",
					"Mapped file hashing exceeded the retained snapshot byte total.");
				return null;
			}
			try {
				digest = ImportSourceSnapshot.sha256File(canonical,
					ImportSourceSnapshot.DEFAULT_CHUNK_SIZE,
					function() return cancelled != null && cancelled());
			} catch (error:Dynamic) {
				if (cancelled != null && cancelled()) result.status = "cancelled";
				else {
					markWalkIncomplete(result);
					addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-file-hash-failed", "error",
						"Could not hash a mapped file: " + Std.string(error));
				}
				return null;
			}
			var after:sys.FileStat;
			try after = FileSystem.stat(canonical) catch (error:Dynamic) {
				markWalkIncomplete(result);
				addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-file-stat-failed", "error",
					"Could not recheck a mapped file: " + Std.string(error));
				return null;
			}
			if (after.size != before.size || after.mtime.getTime() != before.mtime.getTime()) {
				markWalkIncomplete(result);
				addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-file-changed", "error",
					"A mapped file changed while its receipt hash was checked.");
				return null;
			}
			counters.hashes.set(cacheKey, {size:before.size, modified:before.mtime.getTime(), sha256:digest});
			counters.hashedBytes += before.size;
		}
		if (digest != lower(Std.string(expectedHash))) {
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, diagnosticPrefix + "-file-hash-mismatch", "error",
				"A mapped file differs from its retained snapshot receipt.");
			return null;
		}
		counters.bytes += before.size;
		var ownerPath = ownerRelativePath(mappedPath);
		return {sourcePath:canonical, sourceRelative:sourceRelative, mappedPath:mappedPath,
			ownerRelative:ownerPath, candidateOrder:candidate.order, size:before.size, sha256:digest,
			type:candidate.type, embed:candidate.embed, library:candidate.library,
			assetId:candidate.assetIdOverride == true ? candidate.assetId : mappedPath,
			assetIdOverride:candidate.assetIdOverride == true};
	}

	static function noteNonEnabledMapping(profile:PsychAssetProfileResult,
		context:PsychAssetProfileWalkContext, candidate:PsychAssetProfileCandidate,
		sourcePath:String, suffix:String, result:PsychAssetProfileWalkResult,
		onDiagnostic:PsychAssetProfileDiagnostic->Void, deferred:Bool):Void {
		var canonical = canonicalExistingPath(sourcePath);
		var sourceRelative = candidateSourceRelative(candidate, suffix);
		var mappedPath = mapKnownCandidatePath(candidate, suffix);
		if (canonical == "" || !isWithin(canonical, context.selectedRoot)
			|| sourceRelative == null || mappedPath == null) {
			recordScopeProjection(result, candidate, suffix, deferred, true);
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, "non-enabled-path-invalid", "error",
				"A non-enabled mapping path could not be safely identified.");
			return;
		}
		recordScopeProjection(result, candidate, suffix, deferred, false);
		var snapshotRelative = joinRelative(profile.rootRelative, sourceRelative);
		var entry = indexedReceiptFile(context.fileIndex, snapshotRelative);
		if (entry == null) {
			markWalkIncomplete(result);
			if (deferred) result.deferredScopeUnknown = true;
			addWalkDiagnostic(result, onDiagnostic, "non-enabled-file-not-in-snapshot", "error",
				"A non-enabled mapped file is not listed in the retained snapshot receipt.");
			return;
		}
		var actualSize:Int;
		try {
			if (FileSystem.isDirectory(canonical)) throw "The mapped path is a directory.";
			actualSize = FileSystem.stat(canonical).size;
		} catch (error:Dynamic) {
			markWalkIncomplete(result);
			if (deferred) result.deferredScopeUnknown = true;
			addWalkDiagnostic(result, onDiagnostic, "non-enabled-file-stat-failed", "error",
				"Could not inspect a non-enabled mapped file: " + Std.string(error));
			return;
		}
		var size:Dynamic = Reflect.field(entry, "size");
		if (!Std.isOfType(size, Int) || actualSize != (cast size:Int)) {
			markWalkIncomplete(result);
			if (deferred) result.deferredScopeUnknown = true;
			addWalkDiagnostic(result, onDiagnostic, "non-enabled-file-size-mismatch", "error",
				"A non-enabled mapped file size differs from its snapshot receipt.");
			return;
		}
	}

	static function newWalkResult():PsychAssetProfileWalkResult {
		return {
			status:"complete", files:0, skipped:0, diagnostics:[],
			deferredSourcePaths:[], deferredOwnerPaths:[],
			disabledSourcePaths:[], disabledOwnerPaths:[], ambiguousOwnerPaths:[],
			deferredScopeUnknown:false, projections:[]
		};
	}

	static function markWalkIncomplete(result:PsychAssetProfileWalkResult):Void {
		if (result != null && result.status != "cancelled") result.status = "incomplete";
	}

	static function walkCancelled(cancelled:Void->Bool):Bool {
		if (!ImportWorkScheduler.cooperate(cancelled)) return true;
		return cancelled != null && cancelled();
	}

	static function appendUnique(items:Array<String>, value:Null<String>):Void {
		if (items == null || value == null || value == "") return;
		var key = pathKey(value);
		for (existing in items) if (existing != null && pathKey(existing) == key) return;
		items.push(value);
	}

	static function recordScopeProjection(result:PsychAssetProfileWalkResult,
		candidate:PsychAssetProfileCandidate, suffix:String, blocked:Bool, unknown:Bool):Void {
		if (candidate == null) {
			result.deferredScopeUnknown = true;
			recordTypedProjection(result, null, null, null, blocked ? "deferred" : "disabled");
			return;
		}
		var symbolicSource = candidate.sourceRelative != null && candidate.sourceRelative.indexOf("$") >= 0;
		var symbolicTarget = candidate.targetRelative != null && candidate.targetRelative.indexOf("$") >= 0;
		if (symbolicSource || symbolicTarget) {
			// A Project variable left unresolved is not a literal directory name.
			// Retain a known source for legacy suppression when possible, but leave
			// the owner projection unbounded so publication cannot protect the wrong
			// `${NAME}` path while overlooking the real prior destination.
			var knownSource = symbolicSource ? null : candidateSourceRelative(candidate, suffix);
			var kind = candidate.state == DISABLED && !blocked ? "disabled" : "deferred";
			if (knownSource != null) {
				if (kind == "disabled") appendUnique(result.disabledSourcePaths, knownSource);
				else appendUnique(result.deferredSourcePaths, knownSource);
			}
			result.deferredScopeUnknown = true;
			recordTypedProjection(result, candidate, knownSource, null, kind);
			return;
		}
		var sourceRelative = candidateSourceRelative(candidate, suffix);
		var mappedPath = mapKnownCandidatePath(candidate, suffix);
		if (sourceRelative == null || mappedPath == null) {
			result.deferredScopeUnknown = true;
			recordTypedProjection(result, candidate, sourceRelative, null,
				blocked ? "deferred" : "disabled");
			return;
		}
		var ownerPath = ownerRelativePath(mappedPath);
		// The empty owner-relative path represents the complete imported owner's
		// assets/ root. A source failure at this mapping must not disappear from
		// the projection just because empty relative paths are not stored in the
		// precise-path arrays.
		if (blocked && ownerPath == "") result.deferredScopeUnknown = true;
		if (candidate.state == DISABLED && !blocked) {
			appendUnique(result.disabledSourcePaths, sourceRelative);
			appendUnique(result.disabledOwnerPaths, ownerPath);
		} else {
			appendUnique(result.deferredSourcePaths, sourceRelative);
			appendUnique(result.deferredOwnerPaths, ownerPath);
		}
		recordTypedProjection(result, candidate, sourceRelative, ownerPath,
			candidate.state == DISABLED && !blocked ? "disabled" : "deferred");
		if (unknown) result.deferredScopeUnknown = true;
	}

	static function recordTypedProjection(result:PsychAssetProfileWalkResult,
		candidate:Null<PsychAssetProfileCandidate>, sourceRelative:Null<String>,
		ownerRelative:Null<String>, kind:String):Void {
		if (result == null) return;
		if (result.projections == null) result.projections = [];
		for (existing in result.projections) {
			if (existing == null || existing.kind != kind) continue;
			var existingOrder = existing.candidate == null ? null : existing.candidate.order;
			var candidateOrder = candidate == null ? null : candidate.order;
			if (existingOrder != candidateOrder) continue;
			if (projectionPathKey(existing.sourceRelative) != projectionPathKey(sourceRelative)
				|| projectionPathKey(existing.ownerRelative) != projectionPathKey(ownerRelative)) continue;
			return;
		}
		result.projections.push({candidate:candidate, sourceRelative:sourceRelative,
			ownerRelative:ownerRelative, kind:kind});
	}

	static function projectionPathKey(value:Null<String>):String {
		return value == null ? "<null>" : pathKey(value);
	}

	static function recordTraversalProjection(result:PsychAssetProfileWalkResult,
		candidate:PsychAssetProfileCandidate, suffix:String, unknown:Bool):Void {
		// A disabled mapping stays excluded from legacy fallback; its unknown
		// subtree still prevents treating the walk as a complete inventory.
		recordScopeProjection(result, candidate, suffix,
			candidate == null || candidate.state != DISABLED, unknown);
	}

	static function checkMissingReceiptFiles(profile:PsychAssetProfileResult,
		context:PsychAssetProfileWalkContext, candidate:PsychAssetProfileCandidate,
		candidatePath:String, seenSources:Map<String, Bool>, result:PsychAssetProfileWalkResult,
		onDiagnostic:PsychAssetProfileDiagnostic->Void, cancelled:Void->Bool,
		sourceFilter:String->String->Bool,
		candidateFilter:PsychAssetProfileCandidate->String->String->Bool):Void {
		var isDirectory:Bool;
		try isDirectory = FileSystem.isDirectory(candidatePath) catch (error:Dynamic) {
			markWalkIncomplete(result);
			recordScopeProjection(result, candidate, "", candidate.state != DISABLED, true);
			addWalkDiagnostic(result, onDiagnostic, "mapped-source-stat-failed", "error",
				"Could not recheck a mapped source after traversal: " + Std.string(error));
			return;
		}
		var snapshotCandidate = joinRelative(profile.rootRelative, candidate.sourceRelative);
		var candidateKey = pathKey(snapshotCandidate);
		var startKey = isDirectory ? candidateKey + "/" : candidateKey;
		var index = lowerBound(context.receiptPaths, startKey);
		while (index < context.receiptPaths.length) {
			if (walkCancelled(cancelled)) {
				result.status = "cancelled";
				return;
			}
			var receiptKey = context.receiptPaths[index++];
			var isExactFile = !isDirectory && receiptKey == candidateKey;
			if (isDirectory && !StringTools.startsWith(receiptKey, candidateKey + "/")) break;
			if (!isDirectory && !isExactFile) break;
			var entry = context.fileIndex.get(receiptKey);
			if (entry == null) {
				markWalkIncomplete(result);
				result.deferredScopeUnknown = true;
				continue;
			}
			var rawPath = Reflect.field(entry, "path");
			if (rawPath == null) {
				markWalkIncomplete(result);
				result.deferredScopeUnknown = true;
				continue;
			}
			var fullRelative = StringTools.replace(Std.string(rawPath), "\\", "/");
			var rootRelative = profile.rootRelative == null ? "" : profile.rootRelative;
			var sourceRelative = relativeBelow(rootRelative, fullRelative);
			if (sourceRelative == null) continue;
			var suffix = relativeSuffix(candidate.sourceRelative, sourceRelative);
			if (suffix == null || (isDirectory && suffix == "") || (!isDirectory && suffix != "")) continue;
			if (receiptPathInsideSkippedScope(candidate, suffix)) continue;
			var filename = suffix == "" ? Path.withoutDirectory(candidate.sourceRelative) : Path.withoutDirectory(suffix);
			if (!matchesMappedFile(candidate, filename)) continue;
			var mappedPath = mapKnownCandidatePath(candidate, suffix);
			if (mappedPath == null) {
				markWalkIncomplete(result);
				result.deferredScopeUnknown = true;
				continue;
			}
			if (sourceFilter != null) {
				var included = false;
				try included = sourceFilter(sourceRelative, mappedPath) catch (error:Dynamic) {
					markWalkIncomplete(result);
					recordScopeProjection(result, candidate, suffix, candidate.state != DISABLED, true);
					addWalkDiagnostic(result, onDiagnostic, "source-filter-failed", "error",
						"The mapped-file source filter failed while checking the retained receipt: " + Std.string(error));
					return;
				}
				if (!included) continue;
			}
			if (candidateFilter != null) {
				var included = false;
				try included = candidateFilter(candidate, sourceRelative, mappedPath) catch (error:Dynamic) {
					markWalkIncomplete(result);
					recordScopeProjection(result, candidate, suffix, candidate.state != DISABLED, true);
					addWalkDiagnostic(result, onDiagnostic, "source-filter-failed", "error",
						"The mapped-file candidate filter failed while checking the retained receipt: "
							+ Std.string(error));
					return;
				}
				if (!included) continue;
			}
			if (seenSources.exists(pathKey(sourceRelative))) continue;
			markWalkIncomplete(result);
			result.skipped++;
			recordScopeProjection(result, candidate, suffix, candidate.state != DISABLED, false);
			addWalkDiagnostic(result, onDiagnostic, "mapped-file-not-visited", "error",
				"The retained snapshot receipt lists a mapped source file that was not visited.");
		}
	}

	static function receiptPathInsideSkippedScope(candidate:PsychAssetProfileCandidate, suffix:String):Bool {
		var parts = suffix == "" ? [] : suffix.split("/");
		if (parts.length < 2) return false;
		for (i in 0...(parts.length - 1))
			if (isBundleFile(parts[i]) || isExcludedDirectory(candidate, parts[i])) return true;
		return false;
	}

	static function lowerBound(values:Array<String>, target:String):Int {
		var low = 0;
		var high = values == null ? 0 : values.length;
		while (low < high) {
			var middle = low + ((high - low) >> 1);
			if (Reflect.compare(values[middle], target) < 0) low = middle + 1;
			else high = middle;
		}
		return low;
	}

	static function relativeBelow(root:String, path:String):Null<String> {
		var rootParts = root == null || root == "" ? [] : root.split("/");
		var pathParts = path == null ? [] : path.split("/");
		if (pathParts.length <= rootParts.length) return null;
		for (index in 0...rootParts.length)
			if (pathKey(pathParts[index]) != pathKey(rootParts[index])) return null;
		return pathParts.slice(rootParts.length).join("/");
	}

	static function relativeSuffix(base:String, path:String):Null<String> {
		var baseParts = base == null ? [] : base.split("/");
		var pathParts = path == null ? [] : path.split("/");
		if (pathParts.length < baseParts.length) return null;
		for (index in 0...baseParts.length)
			if (pathKey(pathParts[index]) != pathKey(baseParts[index])) return null;
		if (pathParts.length == baseParts.length) return "";
		return pathParts.slice(baseParts.length).join("/");
	}

	static function indexedReceiptFile(index:Map<String, Dynamic>, relative:String):Dynamic {
		if (index == null || relative == null) return null;
		var clean = normalizeRelative(relative, false);
		if (clean == null) return null;
		var key = pathKey(clean);
		return index.exists(key) ? index.get(key) : null;
	}

	static function candidateSourceRelative(candidate:PsychAssetProfileCandidate, suffix:String):Null<String> {
		if (candidate == null) return null;
		return normalizeRelative(joinRelative(candidate.sourceRelative, suffix), false);
	}

	static function matchesMappedFile(candidate:PsychAssetProfileCandidate, filename:String):Bool {
		if (candidate == null || filename == null) return false;
		if (!matchesPatterns(filename, candidate.includePatterns, true)) return false;
		return !matchesPatterns(filename, candidate.excludePatterns, false);
	}

	static function candidateScopeIsSafe(candidate:PsychAssetProfileCandidate):Bool {
		if (candidate == null || candidate.sourceRelative == null || candidate.targetRelative == null
			|| candidate.sourceRelative.indexOf("$") >= 0 || candidate.targetRelative.indexOf("$") >= 0)
			return false;
		if (normalizeRelative(candidate.sourceRelative, false) == null
			|| normalizeRelative(candidate.targetRelative, false) == null)
			return false;
		return safeLimePatterns(candidate.includePatterns, true)
			&& safeLimePatterns(candidate.excludePatterns, false);
	}

	static function safeLimePatterns(patterns:Array<String>, include:Bool):Bool {
		if (patterns == null) return true;
		for (raw in patterns) {
			if (raw == null || raw.indexOf("$") >= 0) return false;
			var pattern = StringTools.trim(raw);
			if (pattern == "") continue;
			pattern = StringTools.replace(pattern, ".", "\\.");
			pattern = StringTools.replace(pattern, "*", ".*");
			try new EReg("^" + pattern + (include ? "" : "$"), "i") catch (_:Dynamic) return false;
		}
		return true;
	}

	static function isBundleFile(path:String):Bool {
		return path != null && Path.extension(path).toLowerCase() == "bundle";
	}

	static function languageScopes(candidateRoot:String, candidate:PsychAssetProfileCandidate,
		result:PsychAssetProfileWalkResult,
		onDiagnostic:PsychAssetProfileDiagnostic->Void):Array<{path:String, suffix:String}> {
		var scopes:Array<{path:String, suffix:String}> = [{path:candidateRoot, suffix:""}];
		var entries:Array<String>;
		try {
			entries = FileSystem.readDirectory(candidateRoot);
			entries.sort(Reflect.compare);
		} catch (error:Dynamic) {
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, "language-scope-read-failed", "error",
				"Could not inspect a language scope: " + Std.string(error));
			return scopes;
		}
		if (entries.length > 4096) {
			markWalkIncomplete(result);
			addWalkDiagnostic(result, onDiagnostic, "language-scope-limit", "error",
				"Psych language scope discovery limit was reached.");
			return scopes;
		}
		for (entry in entries) {
			if (!validEntry(entry)) continue;
			if (isExcludedDirectory(candidate, entry)) continue;
			var lowerName = entry.toLowerCase();
			if (lowerName == "shared") {
				var shared = Path.join([candidateRoot, entry]);
				if (FileSystem.isDirectory(shared)) scopes.push({path:shared, suffix:entry});
				continue;
			}
			if (RESERVED_LANGUAGE_ROOTS.indexOf(lowerName) >= 0) continue;
			var library = Path.join([candidateRoot, entry]);
			if (!FileSystem.isDirectory(library)) continue;
			scopes.push({path:library, suffix:entry});
			if (lowerName != "base_game" && lowerName != "library") continue;
			var children:Array<String>;
			try {
				children = FileSystem.readDirectory(library);
				children.sort(Reflect.compare);
			} catch (error:Dynamic) {
				markWalkIncomplete(result);
				addWalkDiagnostic(result, onDiagnostic, "language-scope-read-failed", "error",
					"Could not inspect a nested language scope: " + Std.string(error));
				continue;
			}
			if (children.length > 2048) {
				markWalkIncomplete(result);
				addWalkDiagnostic(result, onDiagnostic, "language-nested-scope-limit", "error",
					"Psych nested language scope discovery limit was reached.");
				continue;
			}
			for (childName in children) {
				if (!validEntry(childName)) continue;
				var child = Path.join([library, childName]);
				if (FileSystem.isDirectory(child)) scopes.push({path:child, suffix:entry + "/" + childName});
			}
		}
		return scopes;
	}

	static function parseProject(projectPath:String, projectRoot:String, contentRoot:String,
		receipt:Dynamic, projectBytes:Bytes, build:PsychAssetProfileBuild,
		result:PsychAssetProfileResult, receiptBound:Bool, ?cancelled:Void->Bool):Void {
		checkpointProjectWork(cancelled);
		if (projectBytes == null || projectBytes.length > MAX_PROJECT_BYTES) {
			fail(result, "project-size-limit", "Project.xml exceeds the profile parser size limit.");
			return;
		}
		var projectContext = SourceProjectContext.seed(cast result.flags, cast result.buildValues,
			result.buildFlagsComplete, result.buildCommand);
		var canonicalProject = canonicalExistingPath(projectPath);
		var projectKey = pathKey(canonicalProject);
		var state:Dynamic = {
			order:0,
			nodes:0,
			result:result,
			projectRoot:projectRoot,
			contentRoot:contentRoot,
			receipt:receipt,
			receiptBound:receiptBound,
			inputCount:result.inputFiles.length,
			inputBytes:projectBytes.length,
			cancelled:cancelled,
			activeInputs:[projectKey]
		};
		parseProjectDocument(projectPath, result.projectRelative, Path.withoutDirectory(projectPath), projectBytes,
			projectContext, state, ENABLED, [], 0);
		result.values = projectContext.valuesSnapshot();
		result.flagsComplete = projectContext.flagsComplete;
	}

	static function parseProjectDocument(projectPath:String, projectRelative:String,
		projectSourceRelative:String, bytes:Bytes,
		context:SourceProjectContext, state:Dynamic, inheritedState:String,
		inheritedConditions:Array<String>, includeDepth:Int):Void {
		var text = bytes.toString();
		var lowerText = text.toLowerCase();
		checkpointProjectWork(state.cancelled);
		if (lowerText.indexOf("<!doctype") >= 0 || lowerText.indexOf("<!entity") >= 0) {
			state.result.mappingScopeUnknown = true;
			fail(state.result, "unsafe-xml-declaration", "Project input DTD and entity declarations are not supported.");
			return;
		}
		var root:Xml;
		try root = Xml.parse(text).firstElement() catch (error:Dynamic) {
			state.result.mappingScopeUnknown = true;
			fail(state.result, "project-xml-invalid", "Project input could not be parsed: " + Std.string(error));
			return;
		}
		if (root == null || root.nodeType != Xml.Element) {
			state.result.mappingScopeUnknown = true;
			fail(state.result, "project-root-invalid", "A Project input must have an XML element root.");
			return;
		}
		checkpointProjectWork(state.cancelled);
		walkProjectChildren(root, inheritedState, inheritedConditions, state, context,
			projectPath, projectRelative, projectSourceRelative, includeDepth, 0);
		recordProjectContextDiagnostics(context, state.result);
	}

	static function walkProjectChildren(node:Xml, inheritedState:String, inheritedConditions:Array<String>,
		state:Dynamic, context:SourceProjectContext, projectPath:String,
		projectRelative:String, projectSourceRelative:String, includeDepth:Int, depth:Int):Void {
		if (depth > MAX_XML_DEPTH || depth + includeDepth > MAX_PROJECT_TOTAL_DEPTH) {
			markProjectIncomplete(state, "project-include-depth-limit",
				"Combined Project include and XML nesting exceeded the parser limit.", true);
			return;
		}
		for (child in node.elements()) {
			checkpointProjectWork(state.cancelled);
			state.nodes++;
			if (state.nodes > MAX_XML_NODES) {
				markProjectIncomplete(state, "project-xml-node-limit",
					"The combined Project input graph exceeded the parser node limit.", true);
				return;
			}
			var gate = nodeGate(child, inheritedState, inheritedConditions,
				state, context, projectRelative);
			var name = child.nodeName;
			switch (name) {
			case "section":
					walkProjectChildren(child, gate.state, gate.conditions, state, context,
						projectPath, projectRelative, projectSourceRelative, includeDepth, depth + 1);
				case "library", "swf":
					collectLibrary(child, gate, state, context, projectRelative, projectSourceRelative);
				case "assets":
					collectAssets(child, gate, state, context, projectRelative, projectSourceRelative);
				case "define", "set", "setenv":
					applyDefinition(child, gate.state, state, context, projectRelative);
				case "undefine", "unset":
					applyRemoval(child, gate.state, state, context, projectRelative);
				case "include":
					if (gate.state != DISABLED)
						processProjectInclude(child, gate, state, context, projectPath,
							projectRelative, projectSourceRelative, includeDepth);
				case "haxedef", "haxeflag", "macro", "haxelib":
					if (gate.state != DISABLED) {
						var raw = rawBuildInput(child);
						if (raw != "") {
							state.result.opaqueBuildInputs.push(gate.state + ":" + raw);
							state.result.complete = false;
						}
					}
				case "import":
					if (gate.state != DISABLED)
						markProjectIncomplete(state, "unresolved-project-import",
							"Project import directives are not evaluated: " + rawBuildInput(child), true);
				default:
			}
		}
	}

	static function processProjectInclude(node:Xml, gate:Dynamic, state:Dynamic,
		parentContext:SourceProjectContext, projectPath:String, projectRelative:String,
			projectSourceRelative:String, includeDepth:Int):Void {
		checkpointProjectWork(state.cancelled);
		var location = projectRelative + ":include";
		if (node.exists("haxelib")) {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "unsupported-haxelib-include",
				"Haxelib Project includes are not resolved: " + node.get("haxelib"), true);
			return;
		}
		if (!state.receiptBound) {
			markProjectIncomplete(state, "unverified-project-include",
				"Local Project includes require a verified retained snapshot.", true);
			return;
		}
		var raw = node.exists("path") ? node.get("path") : node.get("name");
		if (raw == "" && node.exists("noerror")) return;
		if (raw == null || raw == "") {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "project-include-missing-path",
				"A Project include has no local path or name.", true);
			return;
		}
		var resolution = parentContext.interpolate(raw, location);
		if (resolution == null || resolution.state != "known") {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "unresolved-project-include",
				"Project include path is unresolved: " + raw, true);
			return;
		}
		var includeRelative = normalizeIncludeRelative(Path.directory(projectSourceRelative), resolution.value);
		if (includeRelative == null || includeRelative == "") {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "unsafe-project-include",
				"A Project include path is absolute, malformed, or leaves the selected source root.", true);
			return;
		}
		if (includeDepth + 1 > MAX_PROJECT_INCLUDE_DEPTH) {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "project-include-depth-limit",
				"The nested Project include depth limit was reached.", true);
			return;
		}
		var includePath = findLocalInclude(Path.join([state.projectRoot, includeRelative]));
		if (includePath == "") {
			if (node.exists("noerror")) return;
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "project-include-missing",
				"No local Project input exists for include " + raw + ".", true);
			return;
		}
		var canonical = canonicalExistingPath(includePath);
		if (canonical == "" || !isWithin(canonical, state.projectRoot)) {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "unsafe-project-include",
				"A Project include resolves outside the selected source root.", true);
			return;
		}
		var key = pathKey(canonical);
		if (state.activeInputs.indexOf(key) >= 0) {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "project-include-cycle",
				"Project include cycle detected at " + includeRelative + ".", true);
			return;
		}
		var selectedRelative = relativeFileUnderRoot(state.projectRoot, canonical);
		if (selectedRelative == null) {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "unsafe-project-include",
				"A Project include cannot be represented relative to the selected source root.", true);
			return;
		}
		var snapshotRelative = joinRelative(state.result.rootRelative, selectedRelative);
		var receiptEntry = receiptFile(state.receipt, snapshotRelative, state.result);
		if (receiptEntry == null) {
			state.result.mappingScopeUnknown = true;
			fail(state.result, "project-include-not-in-snapshot",
				"Project include is not listed in the verified snapshot receipt: " + snapshotRelative + ".");
			return;
		}
		var listedSize:Dynamic = Reflect.field(receiptEntry, "size");
		if (!Std.isOfType(listedSize, Int) || Std.int(listedSize) < 0
			|| Std.int(listedSize) > MAX_PROJECT_BYTES) {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "project-include-size-limit",
				"Project include exceeds the per-file parser size limit: " + snapshotRelative + ".", true);
			return;
		}
		if (state.inputCount >= MAX_PROJECT_INPUT_FILES) {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "project-include-file-limit",
				"The combined Project input graph exceeded the file-count limit.", true);
			return;
		}
		if (state.inputBytes + Std.int(listedSize) > MAX_PROJECT_INPUT_BYTES) {
			parentContext.markMissingUnresolved(location);
			markProjectIncomplete(state, "project-include-byte-limit",
				"The combined Project input graph exceeded the byte limit.", true);
			return;
		}
		var bytes = verifiedProjectBytes(canonical, receiptEntry, MAX_PROJECT_BYTES,
			state.result, "project-include-hash-mismatch");
		if (bytes == null) {
			state.result.mappingScopeUnknown = true;
			return;
		}
		checkpointProjectWork(state.cancelled);
		state.inputCount++;
		state.inputBytes += bytes.length;
		state.result.inputFiles.push({path:snapshotRelative, size:bytes.length,
			sha256:Sha256.make(bytes).toHex(), parentInclude:projectRelative,
			order:state.result.inputFiles.length});
		var childContext = parentContext.clone();
		state.activeInputs.push(key);
		try {
			parseProjectDocument(canonical, snapshotRelative, selectedRelative, bytes, childContext, state,
				gate.state, gate.conditions, includeDepth + 1);
		} catch (error:Dynamic) {
			if (Std.isOfType(error, ImportWorkCancelled)) throw error;
			state.result.mappingScopeUnknown = true;
			fail(state.result, "project-include-parse-failed",
				"Could not parse retained Project include " + snapshotRelative + ": " + Std.string(error));
		}
		state.activeInputs.pop();
		checkpointProjectWork(state.cancelled);
		if (gate.state == ENABLED) parentContext.mergeNonOverwriting(childContext);
		else if (gate.state == UNRESOLVED) parentContext.mergeUnresolved(childContext);
	}

	/** Capture Lime library declarations independently from asset files. Empty
		libraries are meaningful, so they cannot be reconstructed from file events. */
	static function collectLibrary(node:Xml, gate:Dynamic, state:Dynamic,
		context:SourceProjectContext, projectRelative:String,
		projectSourceRelative:String):Void {
		// ProjectXMLParser skips disabled elements entirely, including handler
		// declarations. Do not let an inactive conversion handler taint the
		// retained library profile.
		if (gate.state == DISABLED && node.exists("handler")) return;
		// Lime's `handler` form registers a library type handler and creates no
		// Library object. It therefore does not claim a library name.
		if (node.exists("handler")) {
			state.result.librariesComplete = false;
			markProjectIncomplete(state, "unresolved-library-handler",
				"Lime library type handlers can transform asset identities and are not executed by this resolver.", true);
			return;
		}
		var declarationState:String = gate.state;
		var rawId = node.get("id");
		var rawName = rawId != null ? rawId : node.get("name");
		var rawPath = node.get("path");
		var name = "";
		var sourcePath = "";
		var diagnostic = "";
		var type = "";
		var typeState = "known";
		var embed:Null<Bool> = null;
		var embedState = "known";
		var preload = false;
		var preloadState = "known";
		var generate = false;
		var generateState = "known";
		var prefix = "";
		var prefixState = "known";
		var nameResolution:Dynamic = null;
		if (rawName != null && rawName != "") {
			nameResolution = projectAssetValue(rawName, declarationState, context, state,
				projectRelative + ":library-name");
			name = nameResolution.value;
			if (nameResolution.state != ENABLED) declarationState = UNRESOLVED;
		}
		if (rawPath != null && rawPath != "") {
			var pathResolution = projectAssetValue(rawPath, gate.state, context, state,
				projectRelative + ":library-path");
			var selectedPath = normalizeProjectAssetSource(projectSourceRelative, pathResolution.value);
			if (pathResolution.state != ENABLED || selectedPath == null) {
				if (gate.state != DISABLED) declarationState = UNRESOLVED;
				diagnostic = "The Lime library source path is unresolved or leaves the selected source root.";
			} else {
				sourcePath = selectedPath;
			}
		}
		if (gate.state != DISABLED) {
			var rawType = node.get("type");
			if (rawType != null) {
				var typeResolution = projectAssetValue(rawType, gate.state, context, state,
					projectRelative + ":library-type");
				type = typeResolution.value;
				if (typeResolution.state != ENABLED) typeState = "unresolved";
			}
			var rawEmbed = node.get("embed");
			if (rawEmbed != null) {
				var embedResolution = projectAssetValue(rawEmbed, gate.state, context, state,
					projectRelative + ":library-embed");
				if (embedResolution.state == ENABLED) embed = embedResolution.value == "true";
				else embedState = "unresolved";
			}
			var rawPreload = node.get("preload");
			if (rawPreload != null) {
				var preloadResolution = projectAssetValue(rawPreload, gate.state, context, state,
					projectRelative + ":library-preload");
				if (preloadResolution.state == ENABLED) preload = preloadResolution.value == "true";
				else preloadState = "unresolved";
			}
			var rawGenerate = node.get("generate");
			if (rawGenerate != null) {
				var generateResolution = projectAssetValue(rawGenerate, gate.state, context, state,
					projectRelative + ":library-generate");
				if (generateResolution.state == ENABLED) generate = generateResolution.value == "true";
				else generateState = "unresolved";
			}
			var rawPrefix = node.get("prefix");
			if (rawPrefix != null) {
				var prefixResolution = projectAssetValue(rawPrefix, gate.state, context, state,
					projectRelative + ":library-prefix");
				prefix = prefixResolution.value;
				if (prefixResolution.state != ENABLED) prefixState = "unresolved";
			}
		}
		// lime.tools.Library derives an empty name from the source file basename.
		// An explicit empty name/id follows the same constructor behavior.
		if (name == "") {
			if (sourcePath != "")
				name = Path.withoutDirectory(Path.withoutExtension(sourcePath));
			else if (gate.state != DISABLED) {
				declarationState = UNRESOLVED;
				diagnostic = "A Lime library has no resolvable name or source path.";
			}
		}
		if (declarationState == UNRESOLVED || (gate.state != DISABLED && name == "")) {
			state.result.librariesComplete = false;
			state.result.complete = false;
		}
		if (gate.state != DISABLED && (typeState == "unresolved" || embedState == "unresolved"
			|| preloadState == "unresolved" || generateState == "unresolved" || prefixState == "unresolved")) {
			state.result.complete = false;
			state.result.diagnostics.push("library-load-context-unresolved: A Project library loading attribute could not be resolved from the captured source build context.");
		}
		state.result.libraries.push({
			order:state.result.libraries.length,
			name:name,
			state:declarationState,
			sourcePath:sourcePath,
			type:type, typeState:typeState,
			embed:embed, embedState:embedState,
			preload:preload, preloadState:preloadState,
			generate:generate, generateState:generateState,
			prefix:prefix, prefixState:prefixState,
			conditions:gate.conditions.copy(),
			diagnostic:diagnostic
		});
	}

	static function collectAssets(node:Xml, gate:Dynamic, state:Dynamic,
		context:SourceProjectContext, projectRelative:String, projectSourceRelative:String):Void {
		var rawPath = node.get("path");
		if (rawPath == null || StringTools.trim(rawPath) == "") {
			if (gate.state == DISABLED) return;
			addUnresolvedAsset(state, gate, "asset-path-missing", "Project.xml assets declaration has no path.");
			return;
		}
		var sourceBase = projectAssetValue(rawPath, gate.state, context, state, projectRelative + ":assets");
		var targetRaw = node.get("rename");
		if (targetRaw == null || targetRaw == "") targetRaw = rawPath;
		var targetBase = projectAssetValue(targetRaw, gate.state, context, state, projectRelative + ":assets-rename");
		var sourceRelative = normalizeProjectAssetSource(projectSourceRelative, sourceBase.value);
		var targetRelative = normalizeRelative(targetBase.value, false);
		var candidateState = gate.state;
		var diagnostic = "";
		if (sourceBase.state != ENABLED || targetBase.state != ENABLED) candidateState = UNRESOLVED;
		if (sourceRelative == null || targetRelative == null) {
			candidateState = UNRESOLVED;
			diagnostic = "asset-path-invalid";
			state.result.diagnostics.push("asset-path-invalid: A Project.xml source or rename path is not a safe relative path.");
		} else if (!isInsideAssetRoot(targetRelative)) {
			// Non-assets mappings such as example_mods -> mods are retained as
			// candidates, but ownerRelative() will refuse to publish them as assets.
		}
		var rawType = node.get("type");
		var rawEmbed = node.get("embed");
		var rawLibrary = node.get("library");
		var baseTypeValue = rawType == null ? {value:"", state:ENABLED}
			: projectAssetValue(rawType, gate.state, context, state, projectRelative + ":assets-type");
		var baseEmbedValue = rawEmbed == null ? {value:"", state:ENABLED}
			: projectAssetValue(rawEmbed, gate.state, context, state, projectRelative + ":assets-embed");
		var baseLibraryValue = rawLibrary == null ? {value:"", state:ENABLED}
			: projectAssetValue(rawLibrary, gate.state, context, state, projectRelative + ":assets-library");
		var baseType = baseTypeValue.value;
		var baseEmbed = baseEmbedValue.value;
		var baseLibrary = baseLibraryValue.value;
		if (baseTypeValue.state != ENABLED || baseEmbedValue.state != ENABLED
			|| baseLibraryValue.state != ENABLED) candidateState = UNRESOLVED;
		if (baseLibraryValue.state != ENABLED) state.result.librariesComplete = false;
		var hasChildren = false;
		for (_ in node.elements()) hasChildren = true;
		if (!hasChildren) {
			var filters = parseFilters(node, state, context, projectRelative, gate.state);
			if (filters.state != ENABLED) candidateState = UNRESOLVED;
			var assetId:String = null;
			var assetIdOverride = false;
			var rawAssetId = node.get("id");
			if (rawAssetId != null) {
				// Lime only applies a top-level id when the path is a file. Directory
				// declarations ignore it and derive ids from each target path.
				var sourceIsDirectory = projectAssetIsDirectory(state.projectRoot, sourceRelative);
				if (sourceIsDirectory == false) {
					var idValue = projectAssetValue(rawAssetId, gate.state, context, state,
						projectRelative + ":assets-id");
					assetIdOverride = true;
					assetId = idValue.value;
					if (idValue.state != ENABLED) candidateState = UNRESOLVED;
				} else if (sourceIsDirectory == null) {
					candidateState = UNRESOLVED;
					assetIdOverride = true;
					state.result.diagnostics.push("asset-id-source-kind-unknown: Lime's file-only id could not be classified safely.");
				}
			}
			state.result.candidates.push({
				order:Std.int(state.order++), sourceRelative:sourceRelative == null ? sourceBase.value : sourceRelative,
				targetRelative:targetRelative == null ? targetBase.value : targetRelative,
				includePatterns:filters.include, excludePatterns:filters.exclude,
				conditions:gate.conditions.copy(), state:candidateState,
				type:baseType, embed:baseEmbed, library:baseLibrary,
				assetId:assetId, assetIdOverride:assetIdOverride, diagnostic:diagnostic
			});
			if (candidateState == UNRESOLVED) state.result.complete = false;
			return;
		}
		for (child in node.elements()) {
			state.nodes++;
			if (state.nodes > MAX_XML_NODES) {
				state.result.complete = false;
				state.result.diagnostics.push("project-xml-node-limit: Project.xml exceeded the parser node limit.");
				return;
			}
			var childGate = nodeGate(child, gate.state, gate.conditions, state,
				context, projectRelative);
			var childPath = child.get("path");
			if (childPath == null) childPath = child.get("name");
			if (childPath == null || childPath == "") {
				if (gate.state == DISABLED) continue;
				addUnresolvedAsset(state, childGate, "nested-asset-path-missing",
					"A nested Project.xml asset entry has no path or name.");
				continue;
			}
			var childSourceValue = projectAssetValue(childPath, childGate.state, context, state, projectRelative + ":nested-asset");
			var childSource = combineRelative(sourceBase.value, childSourceValue.value);
			var childTargetRaw = child.get("rename");
			if (childTargetRaw == null || childTargetRaw == "") childTargetRaw = childPath;
			var childTargetValue = projectAssetValue(childTargetRaw, childGate.state, context, state,
				projectRelative + ":nested-asset-rename");
			var childTarget = combineRelative(targetBase.value, childTargetValue.value);
			var childState = childGate.state;
			if (sourceBase.state != ENABLED || targetBase.state != ENABLED
				|| childSourceValue.state != ENABLED || childTargetValue.state != ENABLED)
				childState = UNRESOLVED;
			var childSourceClean = normalizeProjectAssetSource("", childSource);
			var childTargetClean = normalizeRelative(childTarget, false);
			var childDiagnostic = "";
			if (childSourceClean == null || childTargetClean == null) {
				childState = UNRESOLVED;
				childDiagnostic = "nested-asset-path-invalid";
				state.result.diagnostics.push("nested-asset-path-invalid: A nested asset mapping leaves its authored root.");
			}
			var childType = baseType;
			var childTypeState = baseTypeValue.state;
			 switch (child.nodeName) {
				case "image", "sound", "music", "font", "template": childType = child.nodeName;
				case "library", "manifest": childType = "manifest";
				default:
					if (child.get("type") != null) {
						var childTypeValue = projectAssetValue(child.get("type"), childGate.state,
							context, state, projectRelative + ":nested-asset-type");
						childType = childTypeValue.value;
						childTypeState = childTypeValue.state;
					}
			}
			var childEmbedValue = child.get("embed") == null ? baseEmbedValue
				: projectAssetValue(child.get("embed"), childGate.state, context, state,
					projectRelative + ":nested-asset-embed");
			var childLibraryValue = child.get("library") == null ? baseLibraryValue
				: projectAssetValue(child.get("library"), childGate.state, context, state,
					projectRelative + ":nested-asset-library");
			var childAssetId:String = null;
			var childAssetIdOverride = false;
			if (child.get("id") != null) {
				var childIdValue = projectAssetValue(child.get("id"), childGate.state, context, state,
					projectRelative + ":nested-asset-id");
				childAssetId = childIdValue.value;
				childAssetIdOverride = true;
				if (childIdValue.state != ENABLED) childState = UNRESOLVED;
			} else if (child.get("name") != null) {
				// Lime's nested parser uses name as both its source fallback and
				// Asset.id, even when rename changes the physical target path.
				childAssetId = childSourceValue.value;
				childAssetIdOverride = true;
			}
			if (childTypeState != ENABLED || childEmbedValue.state != ENABLED
				|| childLibraryValue.state != ENABLED) childState = UNRESOLVED;
			if (childLibraryValue.state != ENABLED) state.result.librariesComplete = false;
			state.result.candidates.push({
				order:Std.int(state.order++), sourceRelative:childSourceClean == null ? childSource : childSourceClean,
				targetRelative:childTargetClean == null ? childTarget : childTargetClean,
				includePatterns:["*"], excludePatterns:DEFAULT_EXCLUDES.copy(),
				conditions:childGate.conditions.copy(), state:childState,
				type:childType,
				embed:childEmbedValue.value,
				library:childLibraryValue.value,
				assetId:childAssetId,
				assetIdOverride:childAssetIdOverride,
				diagnostic:childDiagnostic
			});
			if (childState == UNRESOLVED) state.result.complete = false;
		}
	}

	static function parseFilters(node:Xml, state:Dynamic, context:SourceProjectContext,
		projectRelative:String, gateState:String):Dynamic {
		var includeRaw = node.get("include");
		var excludeRaw = node.get("exclude");
		if (gateState == DISABLED) return {
			include:includeRaw == null ? ["*"] : includeRaw.split("|"),
			exclude:excludeRaw == null ? DEFAULT_EXCLUDES.copy()
				: DEFAULT_EXCLUDES.concat(excludeRaw.split("|")), state:ENABLED
		};
		var includeResolution = includeRaw == null ? null
			: context.interpolate(includeRaw, projectRelative + ":assets-include");
		var excludeResolution = excludeRaw == null ? null
			: context.interpolate(excludeRaw, projectRelative + ":assets-exclude");
		var include:Array<String> = includeRaw == null ? ["*"]
			: (includeResolution == null ? includeRaw : includeResolution.value).split("|");
		var exclude = DEFAULT_EXCLUDES.copy();
		if (excludeRaw != null)
			exclude = exclude.concat((excludeResolution == null ? excludeRaw : excludeResolution.value).split("|"));
		var status = ENABLED;
		if ((includeResolution != null && includeResolution.state != "known")
			|| (excludeResolution != null && excludeResolution.state != "known")) status = UNRESOLVED;
		if (status == UNRESOLVED)
			markProjectIncomplete(state, "unresolved-asset-filter",
				"Project assets include/exclude uses an unresolved Project value.");
		return {include:include, exclude:exclude, state:status};
	}

	static function projectAssetValue(raw:String, gateState:String, context:SourceProjectContext,
		state:Dynamic, location:String):Dynamic {
		if (gateState == DISABLED) return {value:raw == null ? "" : raw, state:ENABLED};
		return substituteKnown(raw, context, state, location);
	}

	static function addUnresolvedAsset(state:Dynamic, gate:Dynamic, code:String, message:String):Void {
		state.result.candidates.push({
			order:state.order++, sourceRelative:"", targetRelative:"", includePatterns:["*"],
			excludePatterns:DEFAULT_EXCLUDES.copy(), conditions:gate.conditions.copy(), state:UNRESOLVED,
			type:"", embed:"", library:"", diagnostic:code
		});
		state.result.complete = false;
		state.result.diagnostics.push(code + ": " + message);
	}

	static function nodeGate(node:Xml, parentState:String, parentConditions:Array<String>,
		state:Dynamic, context:SourceProjectContext, projectRelative:String):Dynamic {
		var conditions = parentConditions.copy();
		var ifValue = node.get("if");
		var unlessValue = node.get("unless");
		if (parentState == DISABLED) {
			if (ifValue != null) conditions.push("if=" + ifValue);
			if (unlessValue != null) conditions.push("unless=" + unlessValue);
			return {state:DISABLED, conditions:conditions};
		}
		if (ifValue != null) conditions.push("if=" + ifValue);
		if (unlessValue != null) conditions.push("unless=" + unlessValue);
		var resolution = context.condition(ifValue, unlessValue,
			projectRelative + ":" + node.nodeName);
		var ownState = resolution.state != "known" ? UNRESOLVED
			: (resolution.boolValue == true ? ENABLED : DISABLED);
		if (ownState == UNRESOLVED) {
			markProjectIncomplete(state, "unresolved-project-condition",
				"Project condition inputs are unresolved at " + projectRelative + ".");
			recordProjectContextDiagnostics(context, state.result);
		}
		return {state:andState(parentState, ownState), conditions:conditions};
	}

	static function applyDefinition(node:Xml, gateState:String, state:Dynamic,
		context:SourceProjectContext, projectRelative:String):Void {
		if (gateState == DISABLED) return;
		var rawName = node.get("name");
		var location = projectRelative + ":" + node.nodeName;
		var name = rawName;
		if (node.nodeName == "setenv") {
			var nameResolution = context.interpolate(rawName, location);
			if (nameResolution == null || nameResolution.state != "known") name = null;
			else name = nameResolution.value;
		}
		if (name == null || name == "" || !validContextName(name)) {
			context.markAllUnresolved(location);
			markProjectIncomplete(state, "unresolved-project-define",
				"Project.xml has a missing, unsafe, or unresolved define name at " + projectRelative + ".");
			recordProjectContextDiagnostics(context, state.result);
			return;
		}
		if (gateState == UNRESOLVED) {
			context.markUnresolved(name, location);
			markProjectIncomplete(state, "unresolved-project-define-branch",
				"A conditional Project define may or may not apply: " + name + ".");
			return;
		}
		var rawValue = node.get("value");
		if (node.nodeName == "setenv" && !node.exists("value")) rawValue = "1";
		if (rawValue == null) rawValue = "";
		var valueResolution = context.interpolate(rawValue, location);
		if (valueResolution.state == "known") context.apply(node.nodeName, name, valueResolution.value, location);
		else {
			context.apply(node.nodeName, name, null, location);
			context.markValueUnresolved(name, location);
			markProjectIncomplete(state, "unresolved-project-value",
				"Project define value is unresolved for " + name + ".");
		}
	}

	static function applyRemoval(node:Xml, gateState:String, state:Dynamic,
		context:SourceProjectContext, projectRelative:String):Void {
		if (gateState == DISABLED) return;
		var rawName = node.get("name");
		var location = projectRelative + ":" + node.nodeName;
		if (rawName == null || rawName == "" || !validContextName(rawName)) {
			context.markAllUnresolved(location);
			markProjectIncomplete(state, "unresolved-project-undefine",
				"Project.xml has a missing or invalid removal name at " + projectRelative + ".");
			return;
		}
		if (gateState == UNRESOLVED) {
			context.markUnresolved(rawName, location);
			markProjectIncomplete(state, "unresolved-project-removal-branch",
				"A conditional Project removal may or may not apply: " + rawName + ".");
		} else context.apply(node.nodeName, rawName, null, location);
	}

	static function substituteKnown(raw:String, context:SourceProjectContext,
		state:Dynamic, location:String):Dynamic {
		if (raw == null) return {value:"", state:UNRESOLVED};
		var resolution = context.interpolate(raw, location);
		if (resolution.state != "known") {
			markProjectIncomplete(state, "unresolved-project-variable",
				"Project value could not be resolved at " + location + ": " + raw);
			recordProjectContextDiagnostics(context, state.result);
			return {value:resolution.value, state:UNRESOLVED};
		}
		return {value:resolution.value, state:ENABLED};
	}

	static function rawBuildInput(node:Xml):String {
		var parts:Array<String> = [node.nodeName];
		for (name in ["name", "value", "path", "version", "if", "unless"])
			if (node.get(name) != null) parts.push(name + "=" + node.get(name));
		return parts.join(" ");
	}

	static function checkpointProjectWork(cancelled:Null<Void->Bool>):Void {
		if (cancelled != null && cancelled()) throw new ImportWorkCancelled();
		if (!ImportWorkScheduler.cooperate(cancelled)) throw new ImportWorkCancelled();
	}

	static function markProjectIncomplete(state:Dynamic, code:String, message:String,
		scopeUnknown:Bool = false):Void {
		state.result.complete = false;
		if (scopeUnknown) {
			state.result.mappingScopeUnknown = true;
			state.result.librariesComplete = false;
		}
		var entry = code + ": " + message;
		if (state.result.diagnostics.indexOf(entry) < 0) state.result.diagnostics.push(entry);
	}

	static function recordProjectContextDiagnostics(context:SourceProjectContext,
		result:PsychAssetProfileResult):Void {
		if (context == null || context.diagnostics == null) return;
		for (item in context.diagnostics) {
			if (item == null) continue;
			var entry = "project-context-" + item.code + ": " + item.message;
			if (result.diagnostics.indexOf(entry) < 0) result.diagnostics.push(entry);
			result.complete = false;
		}
		if (context.opaque != null) for (item in context.opaque) {
			if (item == null) continue;
			var raw = "project-context-opaque " + item.operation + " " + item.name
				+ (item.value == null ? "" : "=" + item.value);
			if (result.opaqueBuildInputs.indexOf(raw) < 0) result.opaqueBuildInputs.push(raw);
			result.complete = false;
		}
	}

	static function normalizeIncludeRelative(baseRelative:String, requested:String):Null<String> {
		if (requested == null || requested == "") return null;
		var value = StringTools.replace(requested, "\\", "/");
		if (StringTools.startsWith(value, "/") || StringTools.startsWith(value, "~")
			|| value.indexOf(":") >= 0 || value.indexOf("\u0000") >= 0) return null;
		var pieces:Array<String> = [];
		if (baseRelative != null && baseRelative != "" && baseRelative != ".") {
			for (piece in StringTools.replace(baseRelative, "\\", "/").split("/")) {
				if (piece == "" || piece == ".") continue;
				if (piece == "..") return null;
				pieces.push(piece);
			}
		}
		for (piece in value.split("/")) {
			if (piece == "" || piece == ".") continue;
			if (piece == "..") {
				if (pieces.length == 0) return null;
				pieces.pop();
			} else pieces.push(piece);
		}
		return pieces.length == 0 ? null : pieces.join("/");
	}

	static function normalizeProjectAssetSource(projectSourceRelative:String,
		requested:String):Null<String> {
		var base = projectSourceRelative == null || projectSourceRelative == ""
			? "" : Path.directory(projectSourceRelative);
		return normalizeIncludeRelative(base, requested);
	}

	static function projectAssetIsDirectory(projectRoot:String,
		sourceRelative:Null<String>):Null<Bool> {
		#if sys
		if (projectRoot == null || sourceRelative == null) return null;
		var sourcePath = containedSourcePath(projectRoot, sourceRelative);
		if (sourcePath == "" || !FileSystem.exists(sourcePath)) return null;
		try return FileSystem.isDirectory(sourcePath) catch (_:Dynamic) return null;
		#else
		return null;
		#end
	}

	static function findLocalInclude(base:String):String {
		#if sys
		if (base == null || base == "" || !FileSystem.exists(base)) return "";
		if (!FileSystem.isDirectory(base)) return base;
		for (name in ["include.lime", "include.nmml", "include.xml"]) {
			var candidate = Path.join([base, name]);
			if (FileSystem.exists(candidate) && !FileSystem.isDirectory(candidate)) return candidate;
		}
		return "";
		#else
		return "";
		#end
	}

	static function relativeFileUnderRoot(root:String, path:String):Null<String> {
		if (root == null || path == null || !isWithin(path, root) || samePath(root, path)) return null;
		var normalizedRoot = StringTools.replace(Path.normalize(root), "\\", "/");
		var normalizedPath = StringTools.replace(Path.normalize(path), "\\", "/");
		if (!StringTools.endsWith(normalizedRoot, "/")) normalizedRoot += "/";
		if (!StringTools.startsWith(pathKey(normalizedPath), pathKey(normalizedRoot))) return null;
		return normalizeRelative(normalizedPath.substr(normalizedRoot.length), false);
	}

	static function matchesLanguageFile(candidate:PsychAssetProfileCandidate, filename:String):Bool {
		if (filename == null || !filename.toLowerCase().endsWith(".lang")) return false;
		if (!matchesPatterns(filename, candidate.includePatterns, true)) return false;
		if (matchesPatterns(filename, candidate.excludePatterns, false)) return false;
		return true;
	}

	static function isExcludedDirectory(candidate:PsychAssetProfileCandidate, name:String):Bool {
		return matchesPatterns(name, candidate.excludePatterns, false);
	}

	static function matchesPatterns(text:String, patterns:Array<String>, any:Bool):Bool {
		if (patterns == null || patterns.length == 0) return any;
		for (patternValue in patterns) {
			var pattern = StringTools.trim(patternValue);
			if (pattern == "") continue;
			// Lime HXProject.filter escapes dots and expands asterisks, then
			// prefix-matches includes and full-matches excludes.
			var limePattern = StringTools.replace(pattern, ".", "\\.");
			limePattern = StringTools.replace(limePattern, "*", ".*");
			var expression = "^" + limePattern + (any ? "" : "$");
			try {
				if (new EReg(expression, "i").match(text)) return true;
			} catch (_:Dynamic) {
				// Invalid regex syntax cannot safely select files.
			}
		}
		return false;
	}

	static function readSnapshotReceipt(content:String, snapshotId:String,
		?profile:PsychAssetProfileResult):Null<Dynamic> {
		#if sys
		var receiptPath = Path.join([Path.directory(content), "receipt.json"]);
		try {
			if (!FileSystem.exists(receiptPath) || FileSystem.isDirectory(receiptPath))
				throw "Snapshot receipt is missing.";
			var size = FileSystem.stat(receiptPath).size;
			if (size < 0 || size > MAX_RECEIPT_BYTES) throw "Snapshot receipt exceeds the parser size limit.";
			var receipt:Dynamic = haxe.Json.parse(File.getContent(receiptPath));
			var schemaValue:Dynamic = receipt == null ? null : Reflect.field(receipt, "snapshotSchemaVersion");
			if (receipt == null || !Std.isOfType(schemaValue, Int)
				|| (cast schemaValue:Int) < 1
				|| (cast schemaValue:Int) > ImportSourceSnapshot.RECEIPT_SCHEMA_VERSION
				|| Reflect.field(receipt, "snapshotId") != snapshotId
				|| Reflect.field(receipt, "contentRoot") != "content"
				|| !Std.isOfType(Reflect.field(receipt, "files"), Array))
				throw "Snapshot receipt identity or file table is invalid.";
			return receipt;
		} catch (error:Dynamic) {
			var message = "snapshot-receipt-invalid: " + Std.string(error);
			if (profile != null) fail(profile, "snapshot-receipt-invalid", message);
			return null;
		}
		#else
		return null;
		#end
	}

	static function receiptFile(receipt:Dynamic, relative:String, ?profile:PsychAssetProfileResult):Null<Dynamic> {
		var files:Dynamic = receipt == null ? null : Reflect.field(receipt, "files");
		if (!Std.isOfType(files, Array)) return null;
		var found:Dynamic = null;
		for (entry in (cast files:Array<Dynamic>)) {
			if (entry == null) continue;
			var path:Dynamic = Reflect.field(entry, "path");
			if (path == null || !samePath(Std.string(path), relative)) continue;
			if (found != null) {
				if (profile != null) fail(profile, "snapshot-receipt-duplicate-path",
					"Snapshot receipt has duplicate entries for " + relative + ".");
				return null;
			}
			found = entry;
		}
		return found;
	}

	static function verifiedProjectBytes(path:String, entry:Dynamic, maxBytes:Int,
		profile:PsychAssetProfileResult, code:String):Null<Bytes> {
		#if sys
		try {
			if (entry == null) throw "The file is absent from the snapshot receipt.";
			var bytes = File.getBytes(path);
			if (bytes.length > maxBytes || !Std.isOfType(Reflect.field(entry, "size"), Int)
				|| Std.int(Reflect.field(entry, "size")) != bytes.length)
				throw "The file size does not match the snapshot receipt.";
			var expected:Dynamic = Reflect.field(entry, "sha256");
			if (expected == null || !~/^[0-9a-fA-F]{64}$/.match(Std.string(expected)))
				throw "The receipt file hash is invalid.";
			if (Sha256.make(bytes).toHex() != lower(Std.string(expected)))
				throw "The file bytes do not match the snapshot receipt.";
			return bytes;
		} catch (error:Dynamic) {
			fail(profile, code, "Receipt-bound file verification failed: " + Std.string(error));
			return null;
		}
		#else
		return null;
		#end
	}

	static function verifyReceiptFile(path:String, entry:Dynamic, maxBytes:Int,
		profile:PsychAssetProfileResult, code:String):Bool {
		#if sys
		try {
			if (entry == null) return false;
			var stat = FileSystem.stat(path);
			if (stat.size < 0 || stat.size > maxBytes
				|| !Std.isOfType(Reflect.field(entry, "size"), Int)
				|| Std.int(Reflect.field(entry, "size")) != stat.size)
				throw "The file size does not match the snapshot receipt.";
			var expected:Dynamic = Reflect.field(entry, "sha256");
			if (expected == null || !~/^[0-9a-fA-F]{64}$/.match(Std.string(expected)))
				throw "The receipt file hash is invalid.";
			var actual = Sha256.make(File.getBytes(path)).toHex();
			if (actual != lower(Std.string(expected))) throw "The file bytes do not match the snapshot receipt.";
			return true;
		} catch (error:Dynamic) {
			fail(profile, code, "Receipt-bound file verification failed: " + Std.string(error));
			return false;
		}
		#else
		return false;
		#end
	}

	static function verifyWalkReceiptFile(path:String, entry:Dynamic, maxBytes:Int,
		result:PsychAssetProfileWalkResult,
		onDiagnostic:PsychAssetProfileDiagnostic->Void, code:String):Bool {
		#if sys
		try {
			if (entry == null) throw "The file is absent from the snapshot receipt.";
			var stat = FileSystem.stat(path);
			if (stat.size < 0 || stat.size > maxBytes
				|| !Std.isOfType(Reflect.field(entry, "size"), Int)
				|| Std.int(Reflect.field(entry, "size")) != stat.size)
				throw "The file size does not match the snapshot receipt.";
			var expected:Dynamic = Reflect.field(entry, "sha256");
			if (expected == null || !~/^[0-9a-fA-F]{64}$/.match(Std.string(expected)))
				throw "The receipt file hash is invalid.";
			var actual = Sha256.make(File.getBytes(path)).toHex();
			if (actual != lower(Std.string(expected))) throw "The file bytes do not match the snapshot receipt.";
			return true;
		} catch (error:Dynamic) {
			addWalkDiagnostic(result, onDiagnostic, code, "error",
				"Receipt-bound file verification failed: " + Std.string(error));
			return false;
		}
		#else
		return false;
		#end
	}

	static function directProjectFile(root:String, result:PsychAssetProfileResult):String {
		#if sys
		var entries:Array<String>;
		try {
			entries = FileSystem.readDirectory(root);
			entries.sort(Reflect.compare);
		} catch (error:Dynamic) {
			fail(result, "project-root-unreadable", "Could not inspect the selected source root: " + Std.string(error));
			return "";
		}
		var projects:Array<String> = [];
		for (entry in entries) if (entry.toLowerCase() == "project.xml") {
			var candidate = Path.join([root, entry]);
			if (!FileSystem.isDirectory(candidate)) projects.push(candidate);
		}
		if (projects.length != 1) {
			fail(result, projects.length == 0 ? "project-xml-missing" : "project-xml-ambiguous",
				projects.length == 0 ? "The selected Psych root has no direct Project.xml."
					: "The selected Psych root has ambiguous case variants of Project.xml.");
			return "";
		}
		var canonical = canonicalExistingPath(projects[0]);
		if (canonical == "" || !isWithin(canonical, root)) {
			fail(result, "project-xml-outside-root", "Project.xml leaves the selected source root.");
			return "";
		}
		return canonical;
		#else
		return "";
		#end
	}

	static function containedDirectory(base:String, relative:String):String {
		#if sys
		var clean = normalizeRelative(relative, true);
		if (clean == null) return "";
		var path = clean == "" ? base : Path.join([base, clean]);
		if (!FileSystem.exists(path) || !FileSystem.isDirectory(path)) return "";
		var canonical = canonicalExistingPath(path);
		return canonical != "" && isWithin(canonical, base) ? canonical : "";
		#else
		return "";
		#end
	}

	static function containedSourcePath(base:String, relative:String):String {
		#if sys
		var clean = normalizeRelative(relative, false);
		if (clean == null) return "";
		var path = Path.join([base, clean]);
		if (!FileSystem.exists(path)) return path;
		var canonical = canonicalExistingPath(path);
		return canonical != "" && isWithin(canonical, base) ? canonical : "";
		#else
		return "";
		#end
	}

	static function uniqueChildDirectory(root:String, requestedName:String, sourceRoot:String,
		result:PsychAssetProfileWalkResult,
		onDiagnostic:PsychAssetProfileDiagnostic->Void):String {
		var matches:Array<String> = [];
		try {
			for (entry in FileSystem.readDirectory(root)) if (entry.toLowerCase() == requestedName.toLowerCase()) {
				var path = Path.join([root, entry]);
				if (FileSystem.isDirectory(path)) matches.push(path);
			}
		} catch (error:Dynamic) {
			result.status = "incomplete";
			addWalkDiagnostic(result, onDiagnostic, "language-scope-read-failed", "error",
				"Could not inspect an authenticated language scope: " + Std.string(error));
			return "";
		}
		if (matches.length > 1) {
			result.status = "incomplete";
			addWalkDiagnostic(result, onDiagnostic, "language-scope-ambiguous", "error",
				"A data scope has ambiguous case variants under " + root + ".");
			return "";
		}
		if (matches.length == 0) return "";
		var canonical = canonicalExistingPath(matches[0]);
		if (canonical == "" || !isWithin(canonical, sourceRoot)) {
			result.status = "incomplete";
			addWalkDiagnostic(result, onDiagnostic, "language-scope-escape", "error",
				"A data scope leaves the authenticated Psych root.");
			return "";
		}
		return canonical;
	}

	static function addWalkDiagnostic(result:PsychAssetProfileWalkResult,
		onDiagnostic:PsychAssetProfileDiagnostic->Void, code:String, severity:String, message:String):Void {
		var item:PsychAssetProfileDiagnostic = {code:code, severity:severity, message:message};
		result.diagnostics.push(item);
		if (onDiagnostic != null) onDiagnostic(item);
	}

	static function emptyResult(provenance:String, snapshotId:String, rootRelative:String,
		sourceEngine:String, namespace:String, target:String):PsychAssetProfileResult {
		return {
			version:VERSION, provenance:provenance, complete:false,
			snapshotId:snapshotId == null ? "" : snapshotId,
			rootRelative:rootRelative == null ? "" : rootRelative,
			sourceEngine:sourceEngine == null ? "" : sourceEngine,
			namespace:namespace == null ? "" : namespace,
			projectRelative:"", projectSha256:"", buildTarget:target == null ? "" : target,
			mappingScopeUnknown:false, buildCommand:null,
			flags:[], buildValues:[], buildFlagsComplete:false, values:[], flagsComplete:false,
			contextFingerprint:"", inputFiles:[],
			libraries:[], librariesComplete:true,
			candidates:[], opaqueBuildInputs:[], diagnostics:[]
		};
	}

	static function updateCompleteness(result:PsychAssetProfileResult):Void {
		for (candidate in result.candidates) if (candidate.state == UNRESOLVED) result.complete = false;
		if (result.opaqueBuildInputs.length > 0 || result.diagnostics.length > 0) result.complete = false;
	}

	static function fail(result:PsychAssetProfileResult, code:String, message:String):PsychAssetProfileResult {
		result.provenance = "invalid";
		result.complete = false;
		result.diagnostics.push(code + ": " + message);
		return result;
	}

	static function buildFlags(build:PsychAssetProfileBuild):Array<PsychAssetProfileFlag> {
		var output:Array<PsychAssetProfileFlag> = [];
		if (build != null && build.flags != null) for (flag in build.flags) if (flag != null)
			output.push({name:flag.name, state:normalizeState(flag.state), provenance:flag.provenance});
		output.sort(function(a, b) return Reflect.compare(a.name, b.name));
		return output;
	}

	static function buildFlagsComplete(build:PsychAssetProfileBuild):Bool {
		return build != null && build.flagsComplete == true;
	}

	static function buildCommand(build:PsychAssetProfileBuild,
		result:PsychAssetProfileResult):Null<String> {
		if (build == null) return null;
		var command:Dynamic = Reflect.field(build, "command");
		if (command == null) return null;
		if (!Std.isOfType(command, String)) {
			fail(result, "build-context-command-invalid",
				"An explicit Project command must be a string or null.");
			return null;
		}
		return cast command;
	}

	static function buildValues(build:PsychAssetProfileBuild,
		result:PsychAssetProfileResult):Null<Array<PsychAssetProfileValue>> {
		var output:Array<PsychAssetProfileValue> = [];
		var seen:Map<String, Bool> = new Map();
		if (build == null || build.values == null) return output;
		for (value in build.values) {
			if (value == null || value.name == null || !validContextName(value.name)
				|| value.value == null) {
				fail(result, "build-context-value-invalid",
					"An explicit Project string value must have a safe name and string value.");
				return null;
			}
			if (seen.exists(value.name)) {
				fail(result, "build-context-value-conflict",
					"The explicit Project build context contains duplicate value " + value.name + ".");
				return null;
			}
			seen.set(value.name, true);
			for (flag in result.flags) if (flag.name == value.name && flag.state != ENABLED) {
				fail(result, "build-context-value-conflict",
					"An explicit Project value conflicts with a non-enabled flag " + value.name + ".");
				return null;
			}
			output.push({name:value.name, value:value.value, provenance:value.provenance});
		}
		output.sort(function(a, b) return Reflect.compare(a.name, b.name));
		return output;
	}

	static function fingerprintBuildContext(flags:Array<PsychAssetProfileFlag>,
		values:Array<PsychAssetProfileValue>, flagsComplete:Bool, command:Null<String>):String {
		var buffer = new BytesBuffer();
		appendFingerprintField(buffer, "PsychAssetProfile:" + VERSION);
		appendFingerprintField(buffer, flagsComplete ? "flags-complete" : "flags-partial");
		appendFingerprintField(buffer, command == null ? "command-unknown" : "command-known");
		if (command != null) appendFingerprintField(buffer, command);
		for (flag in flags) {
			appendFingerprintField(buffer, "flag");
			appendFingerprintField(buffer, flag.name);
			appendFingerprintField(buffer, normalizeState(flag.state));
			appendFingerprintField(buffer, flag.provenance);
		}
		for (value in values) {
			appendFingerprintField(buffer, "value");
			appendFingerprintField(buffer, value.name);
			appendFingerprintField(buffer, value.value);
			appendFingerprintField(buffer, value.provenance);
		}
		return Sha256.make(buffer.getBytes()).toHex();
	}

	static function appendFingerprintField(buffer:BytesBuffer, value:String):Void {
		var bytes = Bytes.ofString(value == null ? "" : value);
		buffer.addString(Std.string(bytes.length));
		buffer.addByte(58);
		buffer.add(bytes);
		buffer.addByte(10);
	}

	static function validContextName(name:String):Bool {
		return name != null && name.length > 0 && name.length <= SourceProjectContext.MAX_NAME_LENGTH
			&& ~/^[A-Za-z0-9_][A-Za-z0-9_.-]*$/.match(name);
	}

	static function normalizeState(state:String):String {
		return switch (state == null ? "" : state.toLowerCase()) {
			case "enabled", "defined", "true": ENABLED;
			case "disabled", "undefined", "false": DISABLED;
			default: UNRESOLVED;
		};
	}

	static function andState(left:String, right:String):String {
		if (left == DISABLED || right == DISABLED) return DISABLED;
		if (left == ENABLED && right == ENABLED) return ENABLED;
		return UNRESOLVED;
	}

	static function negateState(value:String):String {
		return value == ENABLED ? DISABLED : value == DISABLED ? ENABLED : UNRESOLVED;
	}

	static function canonicalEngine(engine:String):String {
		var value = ImportRevision.normalizeEngine(engine);
		return value == "Psych Engine" || value == "Nightmare Vision" ? value : "";
	}

	static function mapKnownCandidatePath(candidate:PsychAssetProfileCandidate,
		sourceSuffix:String):Null<String> {
		if (candidate == null) return null;
		var target = normalizeRelative(candidate.targetRelative, false);
		var suffix = normalizeRelative(sourceSuffix, true);
		if (target == null || suffix == null) return null;
		return joinRelative(target, suffix);
	}

	static function validNamespace(namespace:String):Bool {
		return namespace != null && ~/^[A-Za-z0-9._-]+$/.match(namespace)
			&& namespace != "." && namespace != "..";
	}

	static function validSnapshotId(snapshotId:String):Bool {
		return snapshotId != null && ~/^[0-9a-fA-F]{64}$/.match(snapshotId);
	}

	static function normalizeRelative(path:String, allowEmpty:Bool):Null<String> {
		if (path == null) return null;
		var value = StringTools.replace(StringTools.trim(path), "\\", "/");
		if (value == "") return allowEmpty ? "" : null;
		if (StringTools.startsWith(value, "/") || StringTools.startsWith(value, "~")
			|| value.indexOf(":") >= 0 || value.indexOf("\u0000") >= 0)
			return null;
		var pieces:Array<String> = [];
		for (piece in value.split("/")) {
			if (piece == "" || piece == ".") continue;
			if (piece == "..") return null;
			pieces.push(piece);
		}
		if (pieces.length == 0) return allowEmpty ? "" : null;
		return pieces.join("/");
	}

	static function combineRelative(base:String, child:String):String {
		if (base == null || base == "") return child == null ? "" : child;
		if (child == null || child == "") return base;
		return base + "/" + child;
	}

	static function joinRelative(base:String, child:String):String {
		if (base == null || base == "") return child == null ? "" : child;
		if (child == null || child == "") return base;
		return base + "/" + child;
	}

	static function ownerRelativePath(mappedPath:String):Null<String> {
		var clean = normalizeRelative(mappedPath, false);
		if (clean == null) return null;
		if (clean == "assets") return "";
		if (!StringTools.startsWith(clean, "assets/")) return null;
		return clean.substr("assets/".length);
	}

	static function isInsideAssetRoot(path:String):Bool {
		var clean = normalizeRelative(path, false);
		return clean == "assets" || (clean != null && StringTools.startsWith(clean, "assets/"));
	}

	static function samePath(left:String, right:String):Bool {
		if (left == null || right == null) return false;
		#if windows
		return StringTools.replace(Path.normalize(left), "\\", "/").toLowerCase()
			== StringTools.replace(Path.normalize(right), "\\", "/").toLowerCase();
		#else
		return StringTools.replace(Path.normalize(left), "\\", "/")
			== StringTools.replace(Path.normalize(right), "\\", "/");
		#end
	}

	static function pathKey(path:String):String {
		#if windows
		return path.toLowerCase();
		#else
		return path;
		#end
	}

	static function canonicalDirectory(path:String):String {
		#if sys
		try {
			if (path == null || !FileSystem.exists(path) || !FileSystem.isDirectory(path)) return "";
			return FileSystem.fullPath(Path.normalize(path));
		} catch (_:Dynamic) return "";
		#else
		return "";
		#end
	}

	static function canonicalExistingPath(path:String):String {
		#if sys
		try {
			if (path == null || !FileSystem.exists(path)) return "";
			return FileSystem.fullPath(Path.normalize(path));
		} catch (_:Dynamic) return "";
		#else
		return "";
		#end
	}

	static function isWithin(path:String, root:String):Bool {
		var pathKeyValue = pathKey(StringTools.replace(Path.normalize(path), "\\", "/"));
		var rootKey = pathKey(StringTools.replace(Path.normalize(root), "\\", "/"));
		if (pathKeyValue == rootKey) return true;
		if (!StringTools.endsWith(rootKey, "/")) rootKey += "/";
		return StringTools.startsWith(pathKeyValue, rootKey);
	}

	static function validEntry(name:String):Bool {
		return name != null && name != "" && name != "." && name != ".."
			&& name.indexOf("/") < 0 && name.indexOf("\\") < 0 && name.indexOf(":") < 0
			&& name.indexOf("\u0000") < 0;
	}

	static function lower(value:String):String return value == null ? "" : value.toLowerCase();
}
