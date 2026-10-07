package;

import SourceMappedAssetPublisher.SourceMappedAssetDecision;
import SourceMappedAssetPublisher.SourceMappedAssetPolicy;
import SourceMappedAssetPublisher.SourceMappedAssetPolicyView;
import SourceMappedAssetPublisher.SourceMappedAssetFile;
using StringTools;

/** Compatibility names retained for the language-only importer callers. */
typedef PsychLanguagePublicationFile = SourceMappedAssetFile;
typedef PsychLanguagePublicationPlan = SourceMappedAssetPolicyView;

/**
	Thin Psych language policy adapter over the shared receipt-bound publisher.
	Language files keep their Project target path; the shared publisher owns
	profile verification, conflict planning, cancellation, and publication.
*/
class PsychLanguagePublisher {
	public static inline var POLICY_LABEL:String = "psych-language";

	/** Return the policy so language and media can be planned in one walk. */
	public static function policy():SourceMappedAssetPolicy {
		return {
			label:POLICY_LABEL,
			beforeHash:function(sourceRelative:String, mappedPath:String):Bool {
				return isLanguagePath(sourceRelative) || isLanguagePath(mappedPath);
			},
			classify:function(event):SourceMappedAssetDecision {
				if (event == null || (!isLanguagePath(event.sourceRelative)
					&& !isLanguagePath(event.mappedPath))) return {state:"ignore"};
				if (event.ownerRelative == null || StringTools.trim(event.ownerRelative) == "")
					return {state:"defer", reason:"The mapped language path is outside the imported owner's assets tree."};
				return {state:"accept", ownerRelative:event.ownerRelative};
			},
			managedOutputPredicate:function(ownerRelative:String):Bool return isLanguagePath(ownerRelative),
			classifyProjection:function(sourceRelative:Null<String>, ownerRelative:Null<String>):Null<SourceMappedAssetDecision> {
				if (ownerRelative != null && (ownerRelative == "" || isLanguagePath(ownerRelative)))
					return {state:"defer", ownerRelative:ownerRelative};
				if (sourceRelative != null && (sourceRelative == "" || isLanguagePath(sourceRelative)))
					return {state:"defer", ownerRelative:ownerRelative};
				return {state:"ignore"};
			}
		};
	}

	/** Prepare a language-only compatibility view. Composite callers should use
		policy() with SourceMappedAssetPublisher.prepareMany instead. */
	public static function prepare(sourceRoot:String, engine:String, destinationRoot:String,
		?cancelled:Void->Bool):PsychLanguagePublicationPlan {
		return SourceMappedAssetPublisher.prepare(sourceRoot, engine, destinationRoot,
			policy(), cancelled);
	}

	public static function publish(plan:PsychLanguagePublicationPlan,
		copyFile:String->String->Void, ?cancelled:Void->Bool):Void {
		SourceMappedAssetPublisher.publishView(plan, copyFile, cancelled);
	}

	public static function skipLegacy(plan:PsychLanguagePublicationPlan,
		sourcePath:String, destinationPath:String):Bool {
		return SourceMappedAssetPublisher.skipLegacy(plan, sourcePath, destinationPath);
	}

	static function isLanguagePath(path:String):Bool {
		return path != null && StringTools.trim(path) != ""
			&& StringTools.trim(path).toLowerCase().endsWith(".lang");
	}
}
