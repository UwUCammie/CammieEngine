package;

import haxe.io.Path;
import SourceMappedAssetPublisher.SourceMappedAssetPlan;
import SourceMappedAssetPublisher.SourceMappedAssetPolicy;
import SourceMappedAssetPublisher.SourceMappedAssetPolicyView;
import SourceLimeAssetIdentity;
using StringTools;

/**
	Composite source-media plan used by Psych and Nightmare Vision imports.
	Psych language and media share one retained-profile walk so all mapped files
	and cross-class conflicts are known before a legacy or mapped copy begins.
*/
class SourceMappedMediaPublisher {
	public static inline var PSYCH_MEDIA_LABEL:String = SourceMappedMediaPolicy.PSYCH_LABEL;
	public static inline var PSYCH_LANGUAGE_LABEL:String = PsychLanguagePublisher.POLICY_LABEL;
	public static inline var NIGHTMARE_VISION_UNRESOLVED_LABEL:String = "nightmare-vision-media-unresolved";
	public static inline var PSYCH_IDENTITY_LABEL:String = SourceMappedMediaPolicy.LIME_IDENTITY_LABEL + "-psych-package";

	/** Build one union plan for a source root and its exact imported owner. An
		NV scope must be caller-authenticated as `package` or `core`; a bound root
		with no proven scope gets the conservative unresolved policy. */
	public static function prepare(sourceRoot:String, engine:String, destinationRoot:String,
		?nightmareVisionScope:String, ?cancelled:Void->Bool):SourceMappedAssetPlan {
		var normalizedEngine = ImportRevision.normalizeEngine(engine);
		var bound = hasProfileBinding(sourceRoot, engine);
		var policies:Array<SourceMappedAssetPolicy> = [];
			switch (normalizedEngine) {
			case ImportEngine.PSYCH:
				policies.push(PsychLanguagePublisher.policy());
				policies.push(SourceMappedMediaPolicy.psych(true));
				policies.push(SourceMappedMediaPolicy.limeIdentity("Psych Engine", SourceMappedMediaPolicy.PACKAGE_SCOPE));
			case ImportEngine.NIGHTMARE_VISION:
				if (nightmareVisionScope == SourceMappedMediaPolicy.PACKAGE_SCOPE
					|| nightmareVisionScope == SourceMappedMediaPolicy.CORE_SCOPE) {
					policies.push(SourceMappedMediaPolicy.nightmareVision(nightmareVisionScope, true));
					policies.push(SourceMappedMediaPolicy.limeIdentity("Nightmare Vision", nightmareVisionScope));
				} else if (bound)
					policies.push(SourceMappedMediaPolicy.nightmareVisionUnresolved());
		}
		return SourceMappedAssetPublisher.prepareMany(sourceRoot, engine, destinationRoot,
			policies, cancelled);
	}

	public static function policyView(plan:SourceMappedAssetPlan,
		label:String):SourceMappedAssetPolicyView {
		return SourceMappedAssetPublisher.policyView(plan, label);
	}

	public static function languageView(plan:SourceMappedAssetPlan):SourceMappedAssetPolicyView {
		return policyView(plan, PSYCH_LANGUAGE_LABEL);
	}

	public static function mediaLabel(engine:String, nightmareVisionScope:String):String {
		var normalizedEngine = ImportRevision.normalizeEngine(engine);
		if (normalizedEngine == ImportEngine.PSYCH) return PSYCH_MEDIA_LABEL;
		if (normalizedEngine == ImportEngine.NIGHTMARE_VISION) {
			if (nightmareVisionScope == SourceMappedMediaPolicy.PACKAGE_SCOPE
				|| nightmareVisionScope == SourceMappedMediaPolicy.CORE_SCOPE)
				return SourceMappedMediaPolicy.NIGHTMARE_VISION_LABEL + "-" + nightmareVisionScope;
			return NIGHTMARE_VISION_UNRESOLVED_LABEL;
		}
		return "";
	}

	public static function mediaPolicy(engine:String, nightmareVisionScope:String):Null<SourceMappedAssetPolicy> {
		var normalizedEngine = ImportRevision.normalizeEngine(engine);
		if (normalizedEngine == ImportEngine.PSYCH) return SourceMappedMediaPolicy.psych();
		if (normalizedEngine == ImportEngine.NIGHTMARE_VISION) {
			if (nightmareVisionScope == SourceMappedMediaPolicy.PACKAGE_SCOPE
				|| nightmareVisionScope == SourceMappedMediaPolicy.CORE_SCOPE)
				return SourceMappedMediaPolicy.nightmareVision(nightmareVisionScope);
			return SourceMappedMediaPolicy.nightmareVisionUnresolved();
		}
		return null;
	}

	public static function publish(plan:SourceMappedAssetPlan,
		copyFile:String->String->Void, ?cancelled:Void->Bool,
		?writeText:String->String->Void):Void {
		SourceMappedAssetPublisher.publish(plan, copyFile, cancelled, writeText);
	}

	/** A media-only owner collector can use its view directly because it already
		knows the destination is a runtime media path. */
	public static function skipLegacyOwner(view:SourceMappedAssetPolicyView,
		sourcePath:String, destinationPath:String):Bool {
		return SourceMappedAssetPublisher.skipLegacy(view, sourcePath, destinationPath);
	}

	/**
		Suppress a recognized media/language file from the broad `assets/` copy.
		Only that policy's class is subject to complete-profile authority. Explicit
		deferred/disabled/accepted path projections are checked first and can never
		be reintroduced by the global compatibility copy.
	*/
	public static function skipLegacyGlobal(profileSourceRoot:String, engine:String,
		destinationRoot:String, policy:SourceMappedAssetPolicy,
		view:SourceMappedAssetPolicyView, sourcePath:String, mappedPath:String):Bool {
		if (view == null) return false;
		if (SourceMappedAssetPublisher.isExplicitlyBlockedSource(view, sourcePath)) return true;
		var sourceRelative = profileRelativeSource(profileSourceRoot, engine, sourcePath);
		var logicalPath = normalizeLogicalPath(mappedPath);
		var relevant = false;
		try relevant = policy != null && policy.beforeHash != null
			&& policy.beforeHash(sourceRelative == null ? "" : sourceRelative,
				logicalPath == null ? "" : logicalPath) catch (_:Dynamic) return true;
		if (!relevant) return false;

		var ownerRelative = ownerRelativeFromLogical(logicalPath);
		if (policy != null && policy.classifyProjection != null) {
			try {
				var projection = policy.classifyProjection(sourceRelative, ownerRelative);
				if (projection != null && projection.ownerRelative != null)
					ownerRelative = normalizeOwnerRelative(projection.ownerRelative);
			} catch (_:Dynamic) return true;
		}
		if (ownerRelative != null && destinationRoot != null && StringTools.trim(destinationRoot) != "") {
			var ownerDestination = Path.normalize(Path.join([destinationRoot, ownerRelative]));
			if (SourceMappedAssetPublisher.isExplicitlyBlockedDestination(view, ownerDestination)) return true;
		}
		return SourceMappedAssetPublisher.blocksLegacySource(view, sourcePath)
			|| (ownerRelative != null && destinationRoot != null
				&& SourceMappedAssetPublisher.blocksLegacyDestination(view,
					Path.normalize(Path.join([destinationRoot, ownerRelative]))));
	}

	/**
		Suppress a raw global-tree copy only when Lime identity planning explicitly
		claimed this source or destination. This deliberately ignores the identity
		policy's authoritative/block-all flags so unrelated files and specialized
		converters keep their existing paths. The sidecar namespace is always
		reserved from donor raw copies.
	*/
	public static function skipIdentityLegacy(plan:SourceMappedAssetPlan,
		sourcePath:String, destinationPath:String):Bool {
		if (isReservedIdentityPath(sourcePath) || isReservedIdentityPath(destinationPath)) return true;
		if (plan == null || plan.identityScope == null || plan.identityScope == "") return false;
		var engine = ImportRevision.normalizeEngine(plan.identityEngine);
		var engineLabel = engine == ImportEngine.PSYCH ? "psych"
			: engine == ImportEngine.NIGHTMARE_VISION ? "nightmare-vision" : "";
		if (engineLabel == "") return false;
		var label = SourceMappedMediaPolicy.LIME_IDENTITY_LABEL + "-" + engineLabel + "-" + plan.identityScope;
		var view = SourceMappedAssetPublisher.policyView(plan, label);
		return SourceMappedAssetPublisher.isExplicitlyBlockedSource(view, sourcePath)
			|| SourceMappedAssetPublisher.isExplicitlyBlockedDestination(view, destinationPath);
	}

	static function isReservedIdentityPath(path:String):Bool {
		if (path == null || StringTools.trim(path) == "") return false;
		var clean = StringTools.replace(StringTools.trim(path), "\\", "/").toLowerCase();
		var reserved = SourceLimeAssetIdentity.SIDECAR_DIR.toLowerCase();
		for (segment in clean.split("/")) if (segment == reserved) return true;
		return false;
	}

	static function hasProfileBinding(sourceRoot:String, engine:String):Bool {
		#if sys
		var context = ImportIO.current();
		if (context == null || sourceRoot == null || StringTools.trim(sourceRoot) == "") return false;
		var binding = context.assetProfile(sourceRoot, engine);
		return binding != null && binding.profile != null;
		#else
		return false;
		#end
	}

	static function profileRelativeSource(sourceRoot:String, engine:String,
		sourcePath:String):Null<String> {
		#if sys
		var context = ImportIO.current();
		if (context == null || sourceRoot == null || sourcePath == null) return null;
		var binding = context.assetProfile(sourceRoot, engine);
		if (binding == null || binding.profile == null) return null;
		var contentRoot = Reflect.field(binding, "contentRoot");
		var rootRelative = Reflect.field(binding.profile, "rootRelative");
		if (contentRoot == null || rootRelative == null) return null;
		var selectedRoot = Path.normalize(Std.string(rootRelative) == ""
			? Std.string(contentRoot) : Path.join([Std.string(contentRoot), Std.string(rootRelative)]));
		return relativeWithin(sourcePath, selectedRoot);
		#else
		return null;
		#end
	}

	static function relativeWithin(path:String, root:String):Null<String> {
		if (path == null || root == null) return null;
		var normalizedPath = Path.normalize(path);
		var normalizedRoot = Path.normalize(root);
		var pathKey = pathKeyFor(normalizedPath);
		var rootKey = pathKeyFor(normalizedRoot);
		if (pathKey == rootKey) return "";
		var prefix = StringTools.endsWith(rootKey, "/") ? rootKey : rootKey + "/";
		if (!StringTools.startsWith(pathKey, prefix)) return null;
		return StringTools.replace(normalizedPath.substr(normalizedRoot.length + 1), "\\", "/");
	}

	static function normalizeLogicalPath(path:String):Null<String> {
		if (path == null) return null;
		var clean = StringTools.replace(StringTools.trim(path), "\\", "/");
		if (clean == "" || StringTools.startsWith(clean, "/") || clean.indexOf(":") >= 0
			|| clean.indexOf("\x00") >= 0) return null;
		var parts:Array<String> = [];
		for (part in clean.split("/")) {
			if (part == "" || part == ".") continue;
			if (part == "..") return null;
			parts.push(part);
		}
		return parts.length == 0 ? null : parts.join("/");
	}

	static function ownerRelativeFromLogical(path:Null<String>):Null<String> {
		if (path == null || !StringTools.startsWith(path, "assets/")) return null;
		return normalizeOwnerRelative(path.substr("assets/".length));
	}

	static function normalizeOwnerRelative(path:String):Null<String> {
		return normalizeLogicalPath(path);
	}

	static function pathKeyFor(path:String):String {
		var clean = StringTools.replace(Path.normalize(path), "\\", "/");
		#if windows
		return clean.toLowerCase();
		#else
		return clean;
		#end
	}
}
