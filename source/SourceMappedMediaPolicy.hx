package;

import PsychAssetProfile.PsychAssetProfileCandidate;
import PsychAssetProfile.PsychAssetProfileMappedFile;
import SourceMappedAssetPublisher.SourceMappedAssetDecision;
import SourceMappedAssetPublisher.SourceMappedAssetPolicy;
using StringTools;

/**
	Runtime-facing policy for receipt-bound Project media. The Project target
	remains authoritative; Lime's library and id metadata never rewrite it.
*/
class SourceMappedMediaPolicy {
	public static inline var PSYCH_LABEL:String = "psych-media";
	public static inline var NIGHTMARE_VISION_LABEL:String = "nightmare-vision-media";
	public static inline var NIGHTMARE_VISION_UNRESOLVED_LABEL:String = "nightmare-vision-media-unresolved";
	public static inline var PACKAGE_SCOPE:String = "package";
	public static inline var CORE_SCOPE:String = "core";
	public static inline var LIME_IDENTITY_LABEL:String = "lime-asset-identity";

	/** Raw owner files and Lime logical identity are planned in the same
		verified walk as specialized language/media outputs. */
	public static function limeIdentity(engine:String, scope:String):SourceMappedAssetPolicy {
		var normalizedEngine = ImportRevision.normalizeEngine(engine);
		if ((normalizedEngine != ImportEngine.PSYCH && normalizedEngine != ImportEngine.NIGHTMARE_VISION)
			|| (scope != PACKAGE_SCOPE && scope != CORE_SCOPE))
			throw "Lime identity publication requires a supported engine and authenticated package/core scope.";
		return {
			label:LIME_IDENTITY_LABEL + "-" + (normalizedEngine == ImportEngine.PSYCH ? "psych" : "nightmare-vision") + "-" + scope,
			beforeHash:function(sourceRelative:String, mappedPath:String):Bool return true,
			beforeHashCandidate:function(sourceRelative:String, mappedPath:String,
				candidate:PsychAssetProfileCandidate):Bool return true,
			classify:function(event:PsychAssetProfileMappedFile):SourceMappedAssetDecision {
				if (event == null) return {state:"defer", ownerRelative:"",
					reason:"A Lime asset event has no authenticated file identity."};
				var logical = normalizeLogical(event.mappedPath);
				var owner = SourceLimeAssetIdentity.ownerRelativeForTarget(logical);
				var routed = routeIdentityOwner(owner, scope);
				if (routed == null || routed == "" || SourceLimeAssetIdentity.isReservedOwnerPath(routed))
					return {state:"defer", ownerRelative:routed == null ? "" : routed,
						reason:"The Lime target is outside the safely publishable owner namespace."};
				var type = SourceLimeAssetIdentity.inferType(event.type, event.sourceRelative,
					event.size, event.sourcePath);
				if (type == null)
					return {state:"defer", ownerRelative:routed,
						reason:"Lime's build-tool text/binary probe is unavailable for this extension; no type was guessed."};
				if (type == "TEMPLATE" || type == "MANIFEST" || type == "BUNDLE")
					return {state:"defer", ownerRelative:routed,
						reason:"Lime template, manifest, and bundle identities require build-time transformation that is not reproduced by raw owner-file publication."};
				return {state:"accept", ownerRelative:routed};
			},
			managedOutputPredicate:function(ownerRelative:String):Bool
				return ownerRelative != null && ownerRelative != "",
			classifyProjection:function(sourceRelative:Null<String>, ownerRelative:Null<String>):Null<SourceMappedAssetDecision> {
				return {state:"defer", ownerRelative:"",
					reason:"An untyped Project projection may affect Lime asset identity."};
			},
			classifyProjectionCandidate:function(sourceRelative:Null<String>,
				ownerRelative:Null<String>, candidate:PsychAssetProfileCandidate):Null<SourceMappedAssetDecision> {
				if (candidate == null) return {state:"defer", ownerRelative:"",
					reason:"A Project identity projection has no candidate metadata."};
				var target = SourceLimeAssetIdentity.targetForProjection(candidate, sourceRelative);
				var mappedOwner = target == null ? null : SourceLimeAssetIdentity.ownerRelativeForTarget(target);
				if (mappedOwner == null && ownerRelative != null)
					mappedOwner = SourceLimeAssetIdentity.normalizeOwnerRelative(ownerRelative);
				var routed = routeIdentityOwner(mappedOwner, scope);
				if (routed == null || routed == "") routed = "";
				var type = SourceLimeAssetIdentity.inferType(candidate.type,
					sourceRelative == null ? candidate.sourceRelative : sourceRelative, 0);
				if (type == null || type == "TEMPLATE" || type == "MANIFEST" || type == "BUNDLE")
					return {state:"defer", ownerRelative:routed,
						reason:"The Project identity projection has unresolved or transformed Lime type semantics."};
				return {state:"defer", ownerRelative:routed};
			},
			limeIdentity:true,
			limeIdentityScope:scope
		};
	}

	/** Policy for an authenticated Psych owner namespace. */
	public static function psych(identityAliasesAvailable:Bool = false):SourceMappedAssetPolicy {
		return create(PSYCH_LABEL, "Psych Engine", null, false, identityAliasesAvailable);
	}

	/**
		Policy for an authenticated Nightmare Vision root. The caller must derive
		`scope` from the selected-root relationship, not a directory basename.
	*/
	public static function nightmareVision(scope:String, identityAliasesAvailable:Bool = false):SourceMappedAssetPolicy {
		if (scope != PACKAGE_SCOPE && scope != CORE_SCOPE)
			throw "Nightmare Vision mapped media requires an authenticated package or core scope.";
		return create(NIGHTMARE_VISION_LABEL + "-" + scope, "Nightmare Vision", scope, false,
			identityAliasesAvailable);
	}

	/**
		Use only for a receipt-bound NV profile whose package/core origin cannot
		be proved. Media events defer with no guessed destination, and the broad
		managed-output check makes the publisher stop if prior owner data exists.
	*/
	public static function nightmareVisionUnresolved():SourceMappedAssetPolicy {
		return create(NIGHTMARE_VISION_UNRESOLVED_LABEL, "Nightmare Vision", null, true, false);
	}

	static function create(label:String, engine:String, scope:Null<String>, unresolvedScope:Bool,
		identityAliasesAvailable:Bool):SourceMappedAssetPolicy {
		return {
			label:label,
			beforeHash:function(sourceRelative:String, mappedPath:String):Bool {
				return couldBeMediaPath(sourceRelative) || couldBeMediaPath(mappedPath);
			},
			beforeHashCandidate:function(sourceRelative:String, mappedPath:String,
				candidate:PsychAssetProfileCandidate):Bool {
				if (candidate != null && isNonRuntimeType(candidate.type))
					return couldBeMediaPath(sourceRelative) || couldBeMediaPath(mappedPath);
				return (candidate != null && mediaKindFromType(candidate.type) != null)
					|| couldBeMediaPath(sourceRelative) || couldBeMediaPath(mappedPath);
			},
			classify:function(event:PsychAssetProfileMappedFile):SourceMappedAssetDecision {
				if (event == null) return {state:"ignore"};
				var relative = mappedOwnerPath(event.mappedPath);
				if (relative == null || isDedicatedConversionPath(relative)
					|| isDedicatedConversionPath(event.sourceRelative)) return {state:"ignore"};
				if (isNonRuntimeType(event.type)) {
					if (!couldBeMediaPath(event.sourceRelative) && !couldBeMediaPath(event.mappedPath))
						return {state:"ignore"};
					if (unresolvedScope)
						return {state:"defer", ownerRelative:"",
							reason:"A media-shaped asset was declared as a Lime template or manifest; its runtime identity is unsupported."};
					var nonRuntimeOwner = routeOwnerPath(relative, scope);
					return {state:"defer", ownerRelative:nonRuntimeOwner == null ? relative : nonRuntimeOwner,
						reason:"A media-shaped asset was declared as a Lime template or manifest; its runtime identity is unsupported."};
				}
				var media = classifyMedia(relative, event.type, engine, event.sourceRelative);
				if (media.state == "ignore") return {state:"ignore"};
				if (unresolvedScope)
					return {state:"defer", ownerRelative:"",
						reason:"The authenticated Nightmare Vision root is not proven to be a package or the game core; mapped media cannot be assigned safely."};
				var routed = routeOwnerPath(relative, scope);
				if (routed == null)
					return {state:"defer", ownerRelative:relative,
						reason:"The mapped media path conflicts with the selected runtime owner scope."};
				if (media.state == "defer")
					return {state:"defer", ownerRelative:routed, reason:media.reason};
				if (!identityAliasesAvailable && (event.assetId == null || event.assetId != event.mappedPath))
					return {state:"defer", ownerRelative:routed,
						reason:"The Lime asset id differs from the authored target path; this standalone media policy has no verified id alias index."};
				return {state:"accept", ownerRelative:routed};
			},
			managedOutputPredicate:function(ownerRelative:String):Bool {
				if (unresolvedScope) return isSafeOwnerPath(ownerRelative);
				var relative = scopedOwnerPath(ownerRelative, scope);
				return relative != null && couldBeMediaPath(relative);
			},
			classifyProjection:function(sourceRelative:Null<String>, ownerRelative:Null<String>):Null<SourceMappedAssetDecision> {
				if (unresolvedScope) {
					if ((sourceRelative == null || sourceRelative == "")
						&& (ownerRelative == null || ownerRelative == ""))
						return {state:"defer", ownerRelative:"",
							reason:"The authenticated Nightmare Vision root is not proven to be a package or the game core."};
					return {state:"defer", ownerRelative:"",
						reason:"The authenticated Nightmare Vision root is not proven to be a package or the game core."};
				}
				if (ownerRelative != null) {
					if (ownerRelative == "") return {state:"defer", ownerRelative:""};
					var relative = projectionOwnerPath(ownerRelative, scope);
					if (relative == null) return {state:"ignore"};
					if (!couldBeMediaPath(relative)) return {state:"ignore"};
					var routed = routeOwnerPath(relative, scope);
					return routed == null ? {state:"defer", ownerRelative:ownerRelative}
						: {state:"defer", ownerRelative:routed};
				}
				if (sourceRelative != null) {
					if (sourceRelative == "") return {state:"defer", ownerRelative:""};
					if (couldBeMediaPath(sourceRelative)) return {state:"defer"};
				}
				return {state:"ignore"};
			},
			classifyProjectionCandidate:function(sourceRelative:Null<String>,
				ownerRelative:Null<String>, candidate:PsychAssetProfileCandidate):Null<SourceMappedAssetDecision> {
				if (candidate == null) return projectionDecision(sourceRelative, ownerRelative, scope,
					unresolvedScope);
				if (isDedicatedConversionPath(candidate.sourceRelative)) return {state:"ignore"};
				var nonRuntimeType = isNonRuntimeType(candidate.type);
				var explicitMediaType = mediaKindFromType(candidate.type) != null;
				var candidateMediaShaped = explicitMediaType || couldBeMediaPath(sourceRelative)
					|| couldBeMediaPath(ownerRelative) || couldBeMediaPath(candidate.targetRelative);
				if (nonRuntimeType && !candidateMediaShaped) return {state:"ignore"};
				var symbolicPath = (candidate.sourceRelative != null
					&& candidate.sourceRelative.indexOf("$") >= 0)
					|| (candidate.targetRelative != null && candidate.targetRelative.indexOf("$") >= 0);
				if (symbolicPath) {
					var mediaProjection = candidateMediaShaped || couldBeMediaPath(sourceRelative)
						|| couldBeMediaPath(ownerRelative);
					if (!mediaProjection) return {state:"ignore"};
					return {state:"defer", ownerRelative:"",
						reason:"The Project media source or target contains an unresolved variable; no literal owner path is assumed."};
				}
				var candidateTarget = normalizeRelative(candidate.targetRelative);
				if (candidateTarget == null || (candidateTarget != "assets"
					&& !candidateTarget.startsWith("assets/"))) return {state:"ignore"};
				var projected = ownerRelative == null
					? projectionTarget(candidate, sourceRelative) : normalizeRelative(ownerRelative);
				if (projected == null && explicitMediaType)
					return {state:"defer", ownerRelative:"",
						reason:"A typed media projection has no safe owner-relative target."};
				var relative = projected == "" ? "" : projected;
				var mediaProjection = candidateMediaShaped || couldBeMediaPath(sourceRelative)
					|| (relative != "" && couldBeMediaPath(relative));
				if (!mediaProjection) return {state:"ignore"};
				if (unresolvedScope)
					return {state:"defer", ownerRelative:"",
						reason:"The authenticated Nightmare Vision root is not proven to be a package or the game core; mapped media cannot be assigned safely."};
				if (relative == "") return {state:"defer", ownerRelative:""};
				var routed = routeOwnerPath(relative, scope);
				if (routed == null)
					return {state:"defer", ownerRelative:relative,
						reason:"The mapped media projection conflicts with the selected runtime owner scope."};
				if (nonRuntimeType)
					return {state:"defer", ownerRelative:routed,
						reason:"A media-shaped asset was declared as a Lime template or manifest; its runtime identity is unsupported."};
				var media = classifyMedia(relative, candidate.type, engine);
				return {state:"defer", ownerRelative:routed, reason:media.reason};
			},
		};
	}

	static function projectionDecision(sourceRelative:Null<String>, ownerRelative:Null<String>,
		scope:Null<String>, unresolvedScope:Bool):SourceMappedAssetDecision {
		if (unresolvedScope)
			return {state:"defer", ownerRelative:"",
				reason:"The authenticated Nightmare Vision root is not proven to be a package or the game core."};
		if (ownerRelative != null && ownerRelative != "") {
			var relative = projectionOwnerPath(ownerRelative, scope);
			if (relative == null || !couldBeMediaPath(relative)) return {state:"ignore"};
			var routed = routeOwnerPath(relative, scope);
			return {state:"defer", ownerRelative:routed == null ? ownerRelative : routed};
		}
		if (ownerRelative == "") return {state:"defer", ownerRelative:""};
		if (sourceRelative == "") return {state:"defer", ownerRelative:""};
		if (sourceRelative != null && couldBeMediaPath(sourceRelative)) return {state:"defer"};
		return {state:"ignore"};
	}

	static function classifyMedia(relative:String, type:String, engine:String,
		sourceRelative:Null<String> = null):SourceMappedAssetDecision {
		var typeKind = mediaKindFromType(type);
		var pathKind = mediaKindFromPath(relative);
		var targetExtension = extensionOf(relative);
		// Lime derives an explicit typed asset's format from its source file.
		// A rename may change the runtime key extension without transforming the
		// bytes, so source format and authored destination remain independent.
		var extension = typeKind != null && sourceRelative != null
			? extensionOf(sourceRelative) : targetExtension;
		var animationManifest = isAnimationManifest(relative)
			|| (sourceRelative != null && isAnimationManifest(sourceRelative));
		var extensionKind = animationManifest ? "animation" : mediaKindFromExtension(extension);
		var kind = typeKind != null ? typeKind : pathKind != null ? pathKind : extensionKind;
		if (kind == null) return {state:"ignore"};
		if (!extensionSupported(kind, extension, pathKind != null || typeKind != null, engine))
			return {state:"defer", reason:"The mapped media target has an extension that is not verified for its runtime asset class."};
		if (typeKind != null && !extensionCompatibleWithType(typeKind, extension, engine))
			return {state:"defer", reason:"The Project asset type conflicts with the mapped media file format."};
		if (pathKind != null && !extensionCompatibleWithType(pathKind, extension, engine))
			return {state:"defer", reason:"The mapped media directory conflicts with the file format."};
		return {state:"accept"};
	}

	static function mappedOwnerPath(mappedPath:String):Null<String> {
		if (mappedPath == null) return null;
		var clean = normalizeRelative(mappedPath);
		if (clean == null || !clean.startsWith("assets/")) return null;
		return clean.substr("assets/".length);
	}

	static function projectionTarget(candidate:PsychAssetProfileCandidate,
		sourceRelative:Null<String>):Null<String> {
		if (candidate == null) return null;
		var target = normalizeRelative(candidate.targetRelative);
		if (target == null || !target.startsWith("assets")) return null;
		var base = normalizeRelative(candidate.sourceRelative);
		var source = normalizeRelative(sourceRelative);
		if (base == null || source == null) return null;
		var suffix = "";
		if (source == base) suffix = "";
		else if (source.startsWith(base + "/")) suffix = source.substr(base.length + 1);
		else return null;
		var mapped = suffix == "" ? target : target + "/" + suffix;
		if (mapped == "assets") return "";
		return mappedOwnerPath(mapped);
	}

	static function routeOwnerPath(relative:String, scope:Null<String>):Null<String> {
		var clean = normalizeRelative(relative);
		if (clean == null) return null;
		if (scope == CORE_SCOPE) {
			if (clean == "__nmv_core" || clean.startsWith("__nmv_core/")) return clean;
			return "__nmv_core/" + clean;
		}
		if (scope == PACKAGE_SCOPE && (clean == "__nmv_core" || clean.startsWith("__nmv_core/")))
			return null;
		return clean;
	}

	static function projectionOwnerPath(relative:String, scope:Null<String>):Null<String> {
		if (relative == "") return "";
		var clean = normalizeRelative(relative);
		if (clean == null) return null;
		if (scope == CORE_SCOPE && clean.startsWith("__nmv_core/"))
			return clean.substr("__nmv_core/".length);
		if (scope == PACKAGE_SCOPE && (clean == "__nmv_core" || clean.startsWith("__nmv_core/")))
			return null;
		return clean;
	}

	static function scopedOwnerPath(relative:String, scope:Null<String>):Null<String> {
		if (relative == null || relative == "") return null;
		var clean = normalizeRelative(relative);
		if (clean == null) return null;
		if (scope == CORE_SCOPE) {
			if (!clean.startsWith("__nmv_core/")) return null;
			return clean.substr("__nmv_core/".length);
		}
		if (scope == PACKAGE_SCOPE && (clean == "__nmv_core" || clean.startsWith("__nmv_core/")))
			return null;
		return clean;
	}

	static function isNonRuntimeType(type:String):Bool {
		if (type == null) return false;
		return type.toLowerCase() == "template" || type.toLowerCase() == "manifest";
	}

	static function mediaKindFromType(type:String):Null<String> {
		if (type == null) return null;
		return switch (type.toLowerCase()) {
			case "image", "bitmap", "graphic": "image";
			case "sound", "audio": "sound";
			case "music": "music";
			case "font": "font";
			case "shader": "shader";
			case "video": "video";
			case "animation", "animate", "atlas": "animation";
			default: null;
		}
	}

	static function mediaKindFromPath(relative:String):Null<String> {
		var clean = normalizeRelative(relative);
		if (clean == null) return null;
		var found:Null<String> = null;
		for (piece in clean.toLowerCase().split("/")) {
			var current:Null<String> = switch (piece) {
				case "images": "image";
				case "animations", "animation": "animation";
				case "sounds": "sound";
				case "music": "music";
				case "fonts": "font";
				case "shaders": "shader";
				case "videos": "video";
				default: null;
			};
			if (current != null) {
				if (found != null && found != current) return "ambiguous";
				found = current;
			}
		}
		return found;
	}

	static function mediaKindFromExtension(extension:String):Null<String> {
		return switch (extension) {
			case ".png", ".jpg", ".jpeg", ".bmp", ".gif": "image";
			case ".ogg", ".mp3", ".wav": "sound";
			case ".ttf", ".otf": "font";
			case ".frag", ".vert": "shader";
			case ".mp4", ".mov", ".webm": "video";
			default: null;
		};
	}

	static function extensionSupported(kind:String, extension:String, allowMetadata:Bool,
		engine:String):Bool {
		if (kind == "ambiguous") return false;
		if (allowMetadata && (kind == "image" || kind == "animation")
			&& inList(extension, [".xml", ".txt", ".json"])) return true;
		return switch (kind) {
			case "image": inList(extension, [".png", ".jpg", ".jpeg", ".bmp", ".gif"]);
			case "animation": inList(extension, [".png", ".jpg", ".jpeg", ".json", ".xml", ".txt"]);
			case "sound", "music": inList(extension, [".ogg", ".mp3", ".wav"]);
			case "font": inList(extension, [".ttf", ".otf"]);
			case "shader": inList(extension, [".frag", ".vert"]);
			case "video": engine == "Psych Engine" ? extension == ".mp4"
				: inList(extension, [".mp4", ".mov", ".webm"]);
			default: false;
		};
	}

	static function extensionCompatibleWithType(kind:String, extension:String, engine:String):Bool {
		if (kind == "ambiguous") return false;
		if ((kind == "image" || kind == "animation")
			&& inList(extension, [".xml", ".txt", ".json"])) return true;
		if (kind == "sound" || kind == "music") return inList(extension, [".ogg", ".mp3", ".wav"]);
		if (kind == "animation") return extensionSupported(kind, extension, true, engine);
		return extensionSupported(kind, extension, false, engine);
	}

	static function couldBeMediaPath(path:String):Bool {
		var relative = mappedOwnerPath(path);
		if (relative == null) relative = normalizeRelative(path);
		if (relative == null || isDedicatedConversionPath(relative)) return false;
		if (mediaKindFromPath(relative) != null) return true;
		var extension = extensionOf(relative);
		if (mediaKindFromExtension(extension) != null) return true;
		return (extension == ".xml" || extension == ".txt" || extension == ".json")
			&& isAnimationManifest(relative);
	}

	static function isAnimationManifest(relative:String):Bool {
		var clean = normalizeRelative(relative);
		if (clean == null) return false;
		var name = clean.substr(clean.lastIndexOf("/") + 1).toLowerCase();
		return name == "animation.json" || name == "animation.xml" || name == "animation.txt";
	}

	static function isDedicatedConversionPath(relative:String):Bool {
		var clean = normalizeRelative(relative);
		if (clean == null) return false;
		for (piece in clean.toLowerCase().split("/"))
			if (piece == "songs" || piece == "charts" || piece == "scripts") return true;
		return false;
	}

	static function isSafeOwnerPath(path:String):Bool {
		return path != null && path != "" && normalizeRelative(path) != null;
	}

	static function extensionOf(path:String):String {
		if (path == null) return "";
		var extension = haxe.io.Path.extension(path.toLowerCase());
		return extension == null || extension == "" ? "" : "." + extension;
	}

	static function inList(value:String, values:Array<String>):Bool return values.indexOf(value) >= 0;

	static function normalizeRelative(value:String):Null<String> {
		if (value == null) return null;
		var clean = StringTools.replace(value, "\\", "/");
		if (clean == "" || clean.startsWith("/") || clean.indexOf(":") >= 0 || clean.indexOf("\x00") >= 0)
			return null;
		var output:Array<String> = [];
		for (piece in clean.split("/")) {
			if (piece == "" || piece == "." || piece == "..") return null;
			output.push(piece);
		}
		return output.join("/");
	}

	static function normalizeLogical(path:String):Null<String> {
		if (path == null || path == "" || path.indexOf("\\") >= 0) return null;
		var clean = StringTools.replace(path, "\\", "/");
		if (clean.startsWith("assets/")) {
			var suffix = normalizeRelative(clean.substr("assets/".length));
			return suffix == null ? null : "assets/" + suffix;
		}
		return normalizeRelative(clean);
	}

	static function routeIdentityOwner(ownerRelative:Null<String>, scope:String):Null<String> {
		if (ownerRelative == null || ownerRelative == "") return null;
		var clean = normalizeRelative(ownerRelative);
		if (clean == null) return null;
		if (scope == CORE_SCOPE) {
			if (clean == "__nmv_core" || clean.startsWith("__nmv_core/")) return clean;
			return "__nmv_core/" + clean;
		}
		if (scope == PACKAGE_SCOPE && (clean == "__nmv_core" || clean.startsWith("__nmv_core/")))
			return null;
		return clean;
	}
}
