package;

import haxe.io.Path;
import PsychAssetProfile.PsychAssetProfileCandidate;
import PsychAssetProfile.PsychAssetProfileMappedFile;
import PsychAssetProfile.PsychAssetProfileProjection;
import PsychAssetProfile.PsychAssetProfileWalkResult;
import SourceLimeAssetIdentity.SourceLimeAssetIdentityKey;
import SourceLimeAssetIdentity.SourceLimeAssetIdentityPublication;
using StringTools;

/** A policy's decision for one receipt-verified file or scope projection. */
typedef SourceMappedAssetDecision = {
	/** accept publishes the event, ignore leaves it to other consumers, defer suppresses unsafe legacy fallback. */
	var state:String;
	/** Runtime owner-relative path. For accepted events this overrides the Project target. */
	@:optional var ownerRelative:String;
	@:optional var reason:String;
}

/** Engine-specific rules. The publisher owns receipt verification, planning and conflicts. */
typedef SourceMappedAssetPolicy = {
	var label:String;
	/** Select possible files before receipt hashing. Policies are unioned in prepareMany. */
	@:optional var beforeHash:String->String->Bool;
	/** Candidate-aware prehash selection. Takes priority over beforeHash for this policy. */
	@:optional var beforeHashCandidate:String->String->PsychAssetProfileCandidate->Bool;
	/** Classify a verified file; accepted ownerRelative may apply runtime library routing. */
	var classify:PsychAssetProfileMappedFile->SourceMappedAssetDecision;
	/** Select prior manifest outputs belonging to this runtime class. */
	var managedOutputPredicate:String->Bool;
	/** Optional class-aware projection handling for unresolved/disabled scopes. */
	@:optional var classifyProjection:String->Null<String>->SourceMappedAssetDecision;
	/** Candidate-aware projection handling for unresolved/disabled typed assets. */
	@:optional var classifyProjectionCandidate:Null<String>->Null<String>->PsychAssetProfileCandidate->SourceMappedAssetDecision;
	/** This policy contributes Lime AssetLibrary identity and owner-file outputs. */
	@:optional var limeIdentity:Bool;
	/** Lime identity namespace carried by this policy, normally package/core. */
	@:optional var limeIdentityScope:String;
}

typedef SourceMappedAssetIdentityEvent = {
	var event:PsychAssetProfileMappedFile;
	var ownerRelative:String;
}

/** One verified physical source copied to one runtime owner path. */
typedef SourceMappedAssetFile = {
	var sourcePath:String;
	var destinationPath:String;
	var sourceRelative:String;
	var ownerRelative:String;
	var candidateOrder:Int;
	var size:Int;
	var sha256:String;
	var policyLabels:Array<String>;
	var event:PsychAssetProfileMappedFile;
	var identityEvents:Array<SourceMappedAssetIdentityEvent>;
}

/** Legacy suppression and diagnostics for one policy in a composite plan. */
typedef SourceMappedAssetPolicyPlan = {
	var label:String;
	var authoritative:Bool;
	var legacyAllowed:Bool;
	var blockAllLegacy:Bool;
	var failed:Bool;
	var cancelled:Bool;
	var suppressAllMapped:Bool;
	var files:Array<SourceMappedAssetFile>;
	var diagnostics:Array<String>;
	var blockedSources:Map<String, Bool>;
	var blockedDestinations:Map<String, Bool>;
	var suppressedMappedSources:Map<String, Bool>;
	var suppressedMappedDestinations:Map<String, Bool>;
	var ambiguousDestinations:Map<String, Bool>;
}

/** The complete shared plan. Nothing is copied until every policy has been checked. */
typedef SourceMappedAssetPlan = {
	var profileBound:Bool;
	var authoritative:Bool;
	var failed:Bool;
	var cancelled:Bool;
	var files:Array<SourceMappedAssetFile>;
	var diagnostics:Array<String>;
	var policies:Map<String, SourceMappedAssetPolicyPlan>;
	/** Identity events are filtered to final accepted files after collisions. */
	var identityEvents:Array<SourceMappedAssetIdentityEvent>;
	var identityBlockedKeys:Array<SourceLimeAssetIdentityKey>;
	var identityBlockAll:Bool;
	var identityComplete:Bool;
	var identityLibrariesComplete:Bool;
	var identityOwner:String;
	var identityEngine:String;
	var identityScope:String;
	/** Present only for a retained v3 NV provider-core receiver edge. */
	@:optional var identityHandoff:Dynamic;
	var identityPublication:Null<SourceLimeAssetIdentityPublication>;
}

/** A policy-scoped view used by the existing conventional collectors. */
typedef SourceMappedAssetPolicyView = {
	var label:String;
	var profileBound:Bool;
	var authoritative:Bool;
	var legacyAllowed:Bool;
	var blockAllLegacy:Bool;
	var failed:Bool;
	var cancelled:Bool;
	var suppressAllMapped:Bool;
	var files:Array<SourceMappedAssetFile>;
	var diagnostics:Array<String>;
	var blockedSources:Map<String, Bool>;
	var blockedDestinations:Map<String, Bool>;
	var suppressedMappedSources:Map<String, Bool>;
	var suppressedMappedDestinations:Map<String, Bool>;
	var ambiguousDestinations:Map<String, Bool>;
}

/**
	Shared receipt-bound asset mapping planner for Psych-family owner runtime
	classes. It performs one verified walk for all policies, then resolves
	collisions before any consumer writes files.
*/
class SourceMappedAssetPublisher {
	public static function prepare(sourceRoot:String, engine:String, destinationRoot:String,
		policy:SourceMappedAssetPolicy, ?cancelled:Void->Bool):SourceMappedAssetPolicyView {
		var batch = prepareMany(sourceRoot, engine, destinationRoot,
			policy == null ? [] : [policy], cancelled);
		return policy == null ? emptyView("", batch) : policyView(batch, policy.label);
	}

	public static function prepareMany(sourceRoot:String, engine:String, destinationRoot:String,
		policies:Array<SourceMappedAssetPolicy>, ?cancelled:Void->Bool):SourceMappedAssetPlan {
		var plan:SourceMappedAssetPlan = {
			profileBound:false, authoritative:false, failed:false, cancelled:false,
			files:[], diagnostics:[], policies:new Map(), identityEvents:[],
			identityBlockedKeys:[], identityBlockAll:false, identityComplete:true,
			identityLibrariesComplete:true, identityOwner:"", identityEngine:"",
			identityScope:"", identityHandoff:null, identityPublication:null
		};
		if (policies == null) policies = [];
		var policyByLabel:Map<String, SourceMappedAssetPolicy> = new Map();
		for (policy in policies) {
			if (policy == null || policy.label == null || StringTools.trim(policy.label) == ""
				|| (policy.beforeHash == null && policy.beforeHashCandidate == null)
				|| policy.classify == null || policy.managedOutputPredicate == null) {
				plan.failed = true;
				plan.diagnostics.push("[source-mapped-assets] A mapping policy is incomplete.");
				continue;
			}
			if (policyByLabel.exists(policy.label)) {
				plan.failed = true;
				plan.diagnostics.push("[source-mapped-assets] Duplicate mapping policy label: " + policy.label);
				continue;
			}
			policyByLabel.set(policy.label, policy);
			plan.policies.set(policy.label, newPolicyPlan(policy.label));
		}
		if (plan.failed || sourceRoot == null || destinationRoot == null
			|| StringTools.trim(sourceRoot) == "" || StringTools.trim(destinationRoot) == ""
			|| policies.length == 0) return plan;
		#if sys
		var context = ImportIO.current();
		if (context == null) return plan;
		var binding = context.assetProfile(sourceRoot, engine);
		if (binding == null || binding.profile == null) return plan;
		plan.profileBound = true;
		var profile:Dynamic = binding.profile;
		var contentRoot = binding.contentRoot;
		var expectedEngine = ImportRevision.normalizeEngine(engine);
		var recordedEngine = ImportRevision.normalizeEngine(fieldString(profile, "sourceEngine"));
		var rootRelative = safeRelative(fieldString(profile, "rootRelative"), true);
		var profileNamespace = fieldString(profile, "namespace");
		var hasIdentityPolicy = false;
		for (policy in policyByLabel) if (policy.limeIdentity == true) {
			if (hasIdentityPolicy && policy.limeIdentityScope != plan.identityScope) {
				failAll(plan, "[lime-asset-identity] One combined plan cannot publish multiple identity scopes to the same owner.");
				return plan;
			}
			hasIdentityPolicy = true;
			plan.identityScope = policy.limeIdentityScope == null || policy.limeIdentityScope == ""
				? "package" : policy.limeIdentityScope;
		}
		var safeNamespace = safeRelative(profileNamespace, false);
		var expectedDestinationRoot = safeNamespace == null || safeNamespace != profileNamespace
			|| profileNamespace.indexOf("/") >= 0 || profileNamespace.indexOf("\\") >= 0
			? null : Path.normalize(Path.join([CompatScriptManifest.ROOT_PREFIX, profileNamespace]));
		var handoff:Dynamic = hasIdentityPolicy && expectedEngine == "Nightmare Vision"
			&& plan.identityScope == "core" ? context.assetProfileHandoff(sourceRoot, engine, destinationRoot) : null;
		var handoffNamespace:Dynamic = handoff == null ? null : Reflect.field(handoff, "receiverNamespace");
		var handoffRelative:Dynamic = handoff == null ? null : Reflect.field(handoff, "receiverRootRelative");
		var handoffSafe = handoff != null && Reflect.field(handoff, "version") == 1
			&& Reflect.field(handoff, "catalogVersion") == 3
			&& Reflect.field(handoff, "providerNamespace") == profileNamespace
			&& Reflect.field(handoff, "providerRootRelative") == rootRelative
			&& Reflect.field(handoff, "providerProjectSha256") == fieldString(profile, "projectSha256")
			&& handoffNamespace != null && handoffNamespace != ""
			&& handoffRelative != null && safeRelative(Std.string(handoffRelative), false) == handoffRelative
			&& Path.normalize(destinationRoot) == Path.normalize(Path.join([CompatScriptManifest.ROOT_PREFIX,
				Std.string(handoffNamespace)]));
		if (Reflect.field(profile, "provenance") != "receipt-bound"
			|| expectedEngine == "" || recordedEngine != expectedEngine
			|| profileNamespace == "" || expectedDestinationRoot == null
			|| (!handoffSafe && !samePath(Path.normalize(destinationRoot), expectedDestinationRoot))
			|| rootRelative == null || !samePath(selectedRoot(contentRoot, rootRelative), sourceRoot)) {
			failAll(plan, "[source-mapped-assets] The receipt-bound profile no longer matches this source root, engine, or exact owner destination; refresh stopped to preserve prior owner data.");
			return plan;
		}
		// Compiled catalogs declare Assets IDs but omit disk-based mod files.
		// Keep the latter eligible for the existing raw media collection.
		plan.authoritative = Reflect.field(profile, "complete") == true
			&& Reflect.field(profile, "compiledManifests") != true;
		if (hasIdentityPolicy) {
			plan.identityComplete = Reflect.field(profile, "complete") == true;
			plan.identityLibrariesComplete = Reflect.field(profile, "librariesComplete") == true;
			plan.identityOwner = destinationRoot;
			plan.identityEngine = expectedEngine;
			plan.identityHandoff = handoffSafe ? handoff : null;
		}
		for (state in plan.policies) {
			state.authoritative = plan.authoritative;
			state.legacyAllowed = !plan.authoritative;
		}

		var events:Array<PsychAssetProfileMappedFile> = [];
		var walk:PsychAssetProfileWalkResult = PsychAssetProfile.walkMappedFiles(
			cast profile, contentRoot,
			function(event:PsychAssetProfileMappedFile):Void events.push(event),
			null, cancelled, null,
			function(candidate:PsychAssetProfileCandidate, sourceRelative:String, mappedPath:String):Bool {
				for (policy in policyByLabel) {
					if (policy.beforeHashCandidate != null) {
						if (policy.beforeHashCandidate(sourceRelative, mappedPath, candidate)) return true;
					} else if (policy.beforeHash != null && policy.beforeHash(sourceRelative, mappedPath)) return true;
				}
				return false;
			});
		if (walk == null) {
			failAll(plan, "[source-mapped-assets] The retained asset profile returned no walk result; refresh stopped to preserve prior owner data.");
			addDiagnostic(plan, null, "[source-mapped-assets] The retained asset profile could not be enumerated; no profile-backed files were planned.");
			return plan;
		}
		if (walk.status == "cancelled") {
			cancelAll(plan);
			return plan;
		}
		if (hasIdentityPolicy && walk.status != "complete") plan.identityComplete = false;
		if (hasIdentityPolicy && walk.deferredScopeUnknown) {
			plan.identityComplete = false;
			plan.identityLibrariesComplete = false;
			plan.identityBlockAll = true;
		}
		if (hasIdentityPolicy && walk.projections != null) for (projection in walk.projections) {
			if (projection == null || projection.kind == "disabled") continue;
			plan.identityComplete = false;
			var key = SourceLimeAssetIdentity.keyForProjection(projection.candidate, projection.sourceRelative);
			if (key == null) {
				plan.identityBlockAll = true;
				plan.identityLibrariesComplete = false;
			} else addIdentityBlockedKey(plan, key);
			if (projection.kind == "deferred") plan.identityLibrariesComplete = false;
		}
		if (checkCancelled(plan, cancelled)) return plan;
		if (walk.diagnostics != null)
			for (diagnostic in walk.diagnostics) {
				if (checkCancelled(plan, cancelled)) return plan;
				if (diagnostic == null) continue;
				var message = fieldString(diagnostic, "message");
				var code = fieldString(diagnostic, "code");
				if (isWalkIntegrityFailure(code))
					failAll(plan, "[source-mapped-assets] Receipt verification or canonical walk integrity failed (" + code + "); refresh stopped to preserve prior owner data.");
				if (message != "") addDiagnostic(plan, null, "[source-mapped-assets:" + code + "] " + message);
			}
		if (plan.failed) return plan;

		// Unknown mappings cannot be enumerated. Preserve only prior outputs that
		// a policy explicitly owns, rather than blocking unrelated owner files.
		if (walk.deferredScopeUnknown) {
			for (label in plan.policies.keys()) {
				if (checkCancelled(plan, cancelled)) return plan;
				var state = plan.policies.get(label);
				state.blockAllLegacy = true;
				state.legacyAllowed = false;
				if (hasManagedOutputUnder(context, destinationRoot, "", policyByLabel.get(label))) {
					state.failed = true;
					plan.failed = true;
					addDiagnostic(plan, state, "[source-mapped-assets] An unresolved mapping has an unenumerable " + label + " scope overlapping prior managed output; refresh stopped to preserve it.");
				}
			}
		}

		processProjectionList(plan, context, policyByLabel, sourceRoot, contentRoot, rootRelative,
			destinationRoot, walk.deferredSourcePaths, true, false, cancelled, false, walk.projections);
		processProjectionList(plan, context, policyByLabel, sourceRoot, contentRoot, rootRelative,
			destinationRoot, walk.disabledSourcePaths, false, false, cancelled, false, walk.projections);
		processProjectionList(plan, context, policyByLabel, sourceRoot, contentRoot, rootRelative,
			destinationRoot, walk.deferredOwnerPaths, true, true, cancelled, false, walk.projections);
		processProjectionList(plan, context, policyByLabel, sourceRoot, contentRoot, rootRelative,
			destinationRoot, walk.disabledOwnerPaths, false, true, cancelled, false, walk.projections);
		if (plan.cancelled) return plan;

		var destinationFiles:Map<String, SourceMappedAssetFile> = new Map();
		for (event in events) {
			if (checkCancelled(plan, cancelled)) return plan;
			if (event == null) continue;
			var sourceRelative = safeRelative(event.sourceRelative, false);
			var expectedSource = sourceRelative == null ? null : safeSource(contentRoot, rootRelative, sourceRelative);
			if (expectedSource == null || !samePath(expectedSource, event.sourcePath)) {
				plan.failed = true;
				for (state in plan.policies) state.failed = true;
				addDiagnostic(plan, null, "[source-mapped-assets] A receipt-verified event did not match the selected source root; it was skipped.");
				return plan;
			}
			for (label in policyByLabel.keys()) {
				if (checkCancelled(plan, cancelled)) return plan;
				var policy = policyByLabel.get(label);
				var state = plan.policies.get(label);
				var decision:SourceMappedAssetDecision = null;
				try decision = policy.classify(event) catch (error:Dynamic) {
					state.failed = true;
					plan.failed = true;
					blockSource(state, event.sourcePath);
					addDiagnostic(plan, state, "[source-mapped-assets:" + label + "] Mapping classification failed: " + Std.string(error));
					continue;
				}
				if (decision == null || decision.state == null) {
					state.failed = true;
					plan.failed = true;
					addDiagnostic(plan, state, "[source-mapped-assets:" + label + "] The mapping policy returned no classification.");
					continue;
				}
				switch (decision.state) {
					case "ignore":
						continue;
					case "defer":
						if (hasIdentityPolicy) {
							plan.identityComplete = false;
							var identityKey = SourceLimeAssetIdentity.keyForEvent(event);
							if (identityKey == null) {
								plan.identityBlockAll = true;
								plan.identityLibrariesComplete = false;
							} else addIdentityBlockedKey(plan, identityKey);
						}
						deferEvent(plan, context, state, policy, destinationRoot, event, sourceRelative,
							decision.ownerRelative, decision.reason);
						continue;
					case "accept":
						var ownerRelative = safeRelative(decision.ownerRelative == null
							? event.ownerRelative : decision.ownerRelative, false);
						if (ownerRelative == null) {
							state.failed = true;
							plan.failed = true;
							deferEvent(plan, context, state, policy, destinationRoot, event, sourceRelative,
								event.ownerRelative, decision.reason == null ? "accepted mapping has no safe owner path" : decision.reason);
							addDiagnostic(plan, state, "[source-mapped-assets:" + label + "] Accepted mapping returned an unsafe or missing owner-relative path.");
							continue;
						}
						var destination = safeDestination(destinationRoot, ownerRelative);
						if (destination == null) {
							state.failed = true;
							plan.failed = true;
							deferEvent(plan, context, state, policy, destinationRoot, event, sourceRelative,
								ownerRelative, "mapped owner path is unsafe");
							continue;
						}
						if (SourceLimeAssetIdentity.isReservedOwnerPath(ownerRelative)) {
							state.failed = true;
							plan.failed = true;
							if (policy.limeIdentity == true) plan.identityComplete = false;
							addDiagnostic(plan, state, "[source-mapped-assets] A Project mapping collides with the reserved Lime identity sidecar directory; refresh stopped.");
							continue;
						}
						if (state.suppressAllMapped || isPathBlocked(ownerRelative, state.suppressedMappedDestinations)) {
							if (hasIdentityPolicy) {
								plan.identityComplete = false;
								addIdentityBlockedKey(plan, SourceLimeAssetIdentity.keyForEvent(event));
							}
							continue;
						}
						// Accepted mappings own this source for the current runtime class;
						// keep the legacy walker from copying it to a second inferred path.
						blockSource(state, event.sourcePath);
						var destinationKey = pathKey(destination);
						var file = destinationFiles.get(destinationKey);
						if (file == null) {
							file = {
								sourcePath:event.sourcePath, destinationPath:destination,
								sourceRelative:sourceRelative, ownerRelative:ownerRelative,
								candidateOrder:event.candidateOrder, size:event.size, sha256:event.sha256,
								policyLabels:[], event:event, identityEvents:[]
							};
							destinationFiles.set(destinationKey, file);
							plan.files.push(file);
						} else if (!samePath(file.sourcePath, event.sourcePath)) {
							markCollision(plan, context, destination, ownerRelative, file,
								file.policyLabels, label, policyByLabel, event);
							continue;
						}
						if (file.policyLabels.indexOf(label) < 0) file.policyLabels.push(label);
						if (policy.limeIdentity == true) addIdentityEvent(file, event, ownerRelative);
					default:
						state.failed = true;
						plan.failed = true;
						addDiagnostic(plan, state, "[source-mapped-assets:" + label + "] Unsupported policy decision: " + decision.state);
				}
			}
		}
		// Apply walker-level ambiguity projections after event classification. This
		// keeps an unresolved competitor from hiding the enabled event before the
		// relevant policy has a chance to classify its actual file type.
		processProjectionList(plan, context, policyByLabel, sourceRoot, contentRoot, rootRelative,
			destinationRoot, walk.ambiguousOwnerPaths, true, true, cancelled, true, walk.projections);
		processTypedProjectionList(plan, context, policyByLabel, contentRoot, rootRelative,
			destinationRoot, walk.projections, cancelled);
		if (plan.cancelled) return plan;

		// Remove any shared output that collided after policy-specific routing.
		var ambiguous:Map<String, Bool> = new Map();
		var deferredDestinations:Map<String, Bool> = new Map();
		for (state in plan.policies)
			for (key in state.ambiguousDestinations.keys()) ambiguous.set(key, true);
		for (state in plan.policies)
			for (key in state.suppressedMappedDestinations.keys()) deferredDestinations.set(key, true);
		var kept:Array<SourceMappedAssetFile> = [];
		for (file in plan.files) {
			if (checkCancelled(plan, cancelled)) return plan;
			var ownerKey = pathKey(file.ownerRelative);
			if (ambiguous.exists(pathKey(file.destinationPath)) || deferredDestinations.exists(ownerKey)) {
				if (file.identityEvents != null && file.identityEvents.length > 0) {
					plan.identityComplete = false;
					for (identityEvent in file.identityEvents)
						addIdentityBlockedKey(plan, SourceLimeAssetIdentity.keyForEvent(identityEvent.event));
				}
				continue;
			}
			var labels:Array<String> = [];
			for (label in file.policyLabels) {
				var state = plan.policies.get(label);
				if (state != null && !state.suppressAllMapped) labels.push(label);
			}
			file.policyLabels = labels;
			if (labels.length > 0) kept.push(file);
			else if (file.identityEvents != null && file.identityEvents.length > 0) {
				plan.identityComplete = false;
				for (identityEvent in file.identityEvents)
					addIdentityBlockedKey(plan, SourceLimeAssetIdentity.keyForEvent(identityEvent.event));
			}
		}
		plan.files = kept;
		for (state in plan.policies) {
			state.files = [];
			for (file in plan.files)
				if (file.policyLabels.indexOf(state.label) >= 0) state.files.push(file);
		}
		plan.identityEvents = [];
		for (file in plan.files) if (file.identityEvents != null)
			for (identityEvent in file.identityEvents) plan.identityEvents.push(identityEvent);
		if (hasIdentityPolicy && !plan.failed && !plan.cancelled) {
			plan.identityPublication = SourceLimeAssetIdentity.preparePublication(profile,
				destinationRoot, expectedEngine, plan.identityScope, plan.identityEvents,
				plan.identityBlockedKeys, plan.identityBlockAll, plan.identityComplete,
				plan.identityLibrariesComplete, plan.identityHandoff);
			if (plan.identityPublication.failed) {
				plan.failed = true;
				addDiagnostic(plan, null, "[lime-asset-identity] The owner identity sidecar could not be prepared.");
			}
			for (diagnostic in plan.identityPublication.diagnostics) addDiagnostic(plan, null, diagnostic);
		}
		return plan;
		#else
		return plan;
		#end
	}

	/** Return a policy-only view without rescanning or rehashing the snapshot. */
	public static function policyView(plan:SourceMappedAssetPlan, label:String):SourceMappedAssetPolicyView {
		if (plan == null) return emptyView(label == null ? "" : label, null);
		var state = label == null ? null : plan.policies.get(label);
		if (state == null) return emptyView(label == null ? "" : label, plan);
		return {
			label:label, profileBound:plan.profileBound, authoritative:plan.authoritative,
			legacyAllowed:state.legacyAllowed, blockAllLegacy:state.blockAllLegacy,
			failed:state.failed || plan.failed, cancelled:state.cancelled || plan.cancelled,
			suppressAllMapped:state.suppressAllMapped,
			files:state.suppressAllMapped ? [] : state.files.copy(),
			diagnostics:mergeDiagnostics(plan.diagnostics, state.diagnostics),
			blockedSources:cloneMap(state.blockedSources),
			blockedDestinations:cloneMap(state.blockedDestinations),
			suppressedMappedSources:cloneMap(state.suppressedMappedSources),
			suppressedMappedDestinations:cloneMap(state.suppressedMappedDestinations),
			ambiguousDestinations:cloneMap(state.ambiguousDestinations)
		};
	}

	/** Publish the union once, after all policy and cross-class conflicts are known. */
	public static function publish(plan:SourceMappedAssetPlan,
		copyFile:String->String->Void, ?cancelled:Void->Bool,
		?writeText:String->String->Void):Void {
		if (plan == null || plan.failed || plan.cancelled) return;
		if (plan.identityPublication != null && !plan.identityPublication.failed && writeText == null)
			throw "A Lime identity plan requires a transaction-scoped sidecar writer.";
		if (plan.files.length > 0 && copyFile == null)
			throw "A mapped asset plan requires a file writer.";
		for (file in plan.files) {
			if (publicationCancelled(cancelled)) {
				cancelAll(plan);
				return;
			}
			copyFile(file.sourcePath, file.destinationPath);
		}
		if (plan.identityPublication != null && !plan.identityPublication.failed) {
			if (publicationCancelled(cancelled)) {
				cancelAll(plan);
				return;
			}
			writeText(plan.identityPublication.path, plan.identityPublication.content);
		}
	}

	/** Publish one compatibility view returned by prepare(). */
	public static function publishView(view:SourceMappedAssetPolicyView,
		copyFile:String->String->Void, ?cancelled:Void->Bool):Void {
		if (view == null || view.failed || view.cancelled || copyFile == null) return;
		for (file in view.files) {
			if (publicationCancelled(cancelled)) {
				view.cancelled = true;
				return;
			}
			copyFile(file.sourcePath, file.destinationPath);
		}
	}

	/** Whether one conventional collector should omit a legacy source or destination. */
	public static function skipLegacy(view:SourceMappedAssetPolicyView,
		sourcePath:String, destinationPath:String):Bool {
		if (view == null) return false;
		if (!view.legacyAllowed || view.blockAllLegacy) return true;
		return blocksLegacySource(view, sourcePath) || blocksLegacyDestination(view, destinationPath);
	}

	/** Policy-scoped source check for legacy importers without a target path yet. */
	public static function blocksLegacySource(view:SourceMappedAssetPolicyView, sourcePath:String):Bool {
		if (view == null) return false;
		return !view.legacyAllowed || view.blockAllLegacy
			|| isPathBlocked(sourcePath, view.blockedSources);
	}

	/** Policy-scoped destination check for legacy importers after target resolution. */
	public static function blocksLegacyDestination(view:SourceMappedAssetPolicyView, destinationPath:String):Bool {
		if (view == null) return false;
		return !view.legacyAllowed || view.blockAllLegacy
			|| isPathBlocked(destinationPath, view.blockedDestinations);
	}

	/** Explicit source projections only, excluding authoritative/blockAll policy state. */
	public static function isExplicitlyBlockedSource(view:SourceMappedAssetPolicyView, sourcePath:String):Bool {
		return view != null && isPathBlocked(sourcePath, view.blockedSources);
	}

	/** Explicit destination projections only, excluding authoritative/blockAll policy state. */
	public static function isExplicitlyBlockedDestination(view:SourceMappedAssetPolicyView, destinationPath:String):Bool {
		return view != null && isPathBlocked(destinationPath, view.blockedDestinations);
	}

	static function newPolicyPlan(label:String):SourceMappedAssetPolicyPlan {
		return {
			label:label, authoritative:false, legacyAllowed:true, blockAllLegacy:false,
			failed:false, cancelled:false, suppressAllMapped:false, files:[], diagnostics:[],
			blockedSources:new Map(), blockedDestinations:new Map(),
			suppressedMappedSources:new Map(), suppressedMappedDestinations:new Map(),
			ambiguousDestinations:new Map()
		};
	}

	static function isWalkIntegrityFailure(code:String):Bool {
		if (code == null || code == "") return false;
		return code == "unverified-profile" || code == "snapshot-id-mismatch"
			|| code == "snapshot-receipt-invalid" || code == "source-root-outside-snapshot"
			|| code == "snapshot-file-table-invalid" || code == "candidate-list-invalid"
			|| code == "candidate-invalid" || code == "candidate-source-escape"
			|| code == "mapped-path-invalid" || code == "mapped-source-escape"
			|| code == "mapped-source-stat-failed" || code == "source-filter-failed"
			|| code == "candidate-filter-failed" || code == "mapped-file-not-visited"
			|| StringTools.startsWith(code, "snapshot-file-")
			|| (StringTools.startsWith(code, "mapped-file-")
				&& (code.indexOf("-not-in-snapshot") >= 0 || code.indexOf("-source-escape") >= 0
					|| code.indexOf("-path-invalid") >= 0 || code.indexOf("-stat-failed") >= 0
					|| code.indexOf("-hash-mismatch") >= 0 || code.indexOf("-changed") >= 0
					|| code.indexOf("-hash-failed") >= 0 || code.indexOf("-byte-limit") >= 0));
	}

	static function emptyView(label:String, plan:Null<SourceMappedAssetPlan>):SourceMappedAssetPolicyView {
		return {label:label, profileBound:plan != null && plan.profileBound,
			authoritative:plan != null && plan.authoritative, legacyAllowed:true,
			blockAllLegacy:false, failed:plan != null && plan.failed,
			cancelled:plan != null && plan.cancelled, suppressAllMapped:false,
			files:[], diagnostics:[],
			blockedSources:new Map(), blockedDestinations:new Map(),
			suppressedMappedSources:new Map(), suppressedMappedDestinations:new Map(),
			ambiguousDestinations:new Map()};
	}

	static function processProjectionList(plan:SourceMappedAssetPlan, context:ImportIO,
		policies:Map<String, SourceMappedAssetPolicy>, sourceRoot:String, contentRoot:String,
		rootRelative:String, destinationRoot:String, relatives:Array<String>, deferred:Bool,
		ownerPaths:Bool, cancelled:Void->Bool, ambiguous:Bool = false,
		projections:Array<PsychAssetProfileProjection>):Void {
		if (relatives == null) return;
		for (relative in relatives) {
			if (checkCancelled(plan, cancelled)) return;
			var clean = safeRelative(relative, true);
			if (clean == null) continue;
			for (label in policies.keys()) {
				if (checkCancelled(plan, cancelled)) return;
				var policy = policies.get(label);
				var state = plan.policies.get(label);
				// Candidate-aware policies consume the richer projection record once
				// below. Keep the old path-only route for direct walker projections
				// that have no matching typed record.
				if (policy.classifyProjectionCandidate != null
					&& hasTypedProjectionPath(projections, clean, ownerPaths)) continue;
				var sourceRelative = ownerPaths ? null : clean;
				var ownerRelative = ownerPaths ? clean : null;
				var decision:SourceMappedAssetDecision = null;
				try decision = projectionDecision(policy, sourceRelative, ownerRelative) catch (error:Dynamic) {
					state.failed = true;
					plan.failed = true;
					blockAllLegacy(state);
					addDiagnostic(plan, state, "[source-mapped-assets:" + label + "] Scope classification failed: " + Std.string(error));
					continue;
				}
				if (decision == null) {
					state.failed = true;
					plan.failed = true;
					blockAllLegacy(state);
					addDiagnostic(plan, state, "[source-mapped-assets:" + label + "] Scope classification returned no decision.");
					continue;
				}
				if (decision.state == "ignore") continue;
				if (decision.state != "defer" && decision.state != "accept") {
					state.failed = true;
					plan.failed = true;
					blockAllLegacy(state);
					addDiagnostic(plan, state, "[source-mapped-assets:" + label + "] Unsupported scope decision: " + decision.state);
					continue;
				}
				if (policy.limeIdentity == true && (deferred || ambiguous)) {
					plan.identityComplete = false;
					// A legacy path-only projection has lost the Lime library/id
						// metadata needed to block just one key. Close only this identity
						// index unless the richer typed path below supplied exact identity.
					plan.identityBlockAll = true;
					plan.identityLibrariesComplete = false;
				}
				var deferredOwner = safeRelative(decision.ownerRelative == null ? ownerRelative : decision.ownerRelative, true);
				if (sourceRelative != null) {
					var source = safeSource(contentRoot, rootRelative, sourceRelative);
					if (source != null) blockSource(state, source);
				}
				if (deferredOwner != null) {
					if (deferredOwner == "") {
						blockAllLegacy(state);
						if (deferred || ambiguous) state.suppressAllMapped = true;
						if (ambiguous) state.ambiguousDestinations.set(pathKey(destinationRoot), true);
						if (deferred && hasManagedOutputUnder(context, destinationRoot, "", policy)) {
							state.failed = true;
							plan.failed = true;
							addDiagnostic(plan, state, "[source-mapped-assets] An unresolved " + label + " mapping overlaps prior managed output; refresh stopped to preserve it.");
						}
					} else {
						var destination = safeDestination(destinationRoot, deferredOwner);
						if (destination != null) {
							blockDestination(state, destination);
						if (deferred || ambiguous) {
							// The mapped-plan mask is owner-relative; legacy suppression is absolute.
							suppressMappedDestination(state, deferredOwner);
						}
						if (ambiguous) state.ambiguousDestinations.set(pathKey(destination), true);
						if (deferred && hasManagedOutputUnder(context, destinationRoot, deferredOwner, policy)) {
							state.failed = true;
							plan.failed = true;
							addDiagnostic(plan, state, "[source-mapped-assets] An unresolved " + label + " mapping overlaps prior managed output; refresh stopped to preserve it: " + deferredOwner);
						}
						}
					}
				}
				if (!ownerPaths && deferredOwner == null && decision.state == "defer"
					&& sourceRelative == "") {
					// An empty source projection has no narrower legacy path to close.
					blockAllLegacy(state);
				}
				if (deferred && decision.reason != null && decision.reason != "")
					addDiagnostic(plan, state, "[source-mapped-assets:" + label + "] " + decision.reason);
			}
		}
	}

	static function processTypedProjectionList(plan:SourceMappedAssetPlan, context:ImportIO,
		policies:Map<String, SourceMappedAssetPolicy>, contentRoot:String, rootRelative:String,
		destinationRoot:String, projections:Array<PsychAssetProfileProjection>,
		cancelled:Void->Bool):Void {
		if (projections == null) return;
		for (projection in projections) {
			if (checkCancelled(plan, cancelled)) return;
			if (projection == null) continue;
			var sourceRelative = safeRelative(projection.sourceRelative, true);
			var ownerRelative = safeRelative(projection.ownerRelative, true);
			for (label in policies.keys()) {
				if (checkCancelled(plan, cancelled)) return;
				var policy = policies.get(label);
				if (policy.classifyProjectionCandidate == null) continue;
				var state = plan.policies.get(label);
				var decision:SourceMappedAssetDecision = null;
				try {
					decision = projection.candidate == null
						? projectionDecision(policy, sourceRelative, ownerRelative)
						: policy.classifyProjectionCandidate(sourceRelative, ownerRelative, projection.candidate);
				} catch (error:Dynamic) {
					state.failed = true;
					plan.failed = true;
					blockAllLegacy(state);
					addDiagnostic(plan, state, "[source-mapped-assets:" + label
						+ "] Candidate projection classification failed: " + Std.string(error));
					continue;
				}
				if (decision == null || decision.state == null) {
					state.failed = true;
					plan.failed = true;
					blockAllLegacy(state);
					addDiagnostic(plan, state, "[source-mapped-assets:" + label
						+ "] Candidate projection classification returned no decision.");
					continue;
				}
				if (decision.state == "ignore") continue;
				if (decision.state != "defer" && decision.state != "accept") {
					state.failed = true;
					plan.failed = true;
					blockAllLegacy(state);
					addDiagnostic(plan, state, "[source-mapped-assets:" + label
						+ "] Unsupported candidate projection decision: " + decision.state);
					continue;
				}

				var kind = projection.kind == null ? "deferred" : projection.kind.toLowerCase();
				var protectedProjection = kind == "deferred" || kind == "ambiguous";
				var ambiguous = kind == "ambiguous";
				if (policy.limeIdentity == true && protectedProjection) {
					plan.identityComplete = false;
					var identityKey = SourceLimeAssetIdentity.keyForProjection(
						projection.candidate, sourceRelative);
					if (identityKey == null) {
						plan.identityBlockAll = true;
						plan.identityLibrariesComplete = false;
					} else addIdentityBlockedKey(plan, identityKey);
				}
				if (!protectedProjection && kind != "disabled") {
					state.failed = true;
					plan.failed = true;
					blockAllLegacy(state);
					addDiagnostic(plan, state, "[source-mapped-assets:" + label
						+ "] Unsupported candidate projection kind: " + kind);
					continue;
				}

				if (sourceRelative != null && sourceRelative != "") {
					var source = safeSource(contentRoot, rootRelative, sourceRelative);
					if (source != null) blockSource(state, source);
				}
				var rawProjectedOwner:Dynamic = decision.ownerRelative == null
					? ownerRelative : decision.ownerRelative;
				var symbolicTarget = projection.candidate != null
					&& projection.candidate.targetRelative != null
					&& projection.candidate.targetRelative.indexOf("$") >= 0;
				var projectedOwner = symbolicTarget || (rawProjectedOwner != null
					&& Std.string(rawProjectedOwner).indexOf("$") >= 0)
					? "" : safeRelative(rawProjectedOwner, true);
				if (projectedOwner == null || projectedOwner == "") {
					blockAllLegacy(state);
					if (protectedProjection) state.suppressAllMapped = true;
					if (policy.limeIdentity == true && protectedProjection) {
						plan.identityBlockAll = true;
						plan.identityLibrariesComplete = false;
					}
					if (ambiguous) state.ambiguousDestinations.set(pathKey(destinationRoot), true);
					var hasPriorOutput = projection.candidate != null
						&& decision.state == "defer"
						? hasAnyOwnedOutputUnder(context, destinationRoot)
						: hasManagedOutputUnder(context, destinationRoot, "", policy);
					if (protectedProjection && hasPriorOutput) {
						state.failed = true;
						plan.failed = true;
						addDiagnostic(plan, state, "[source-mapped-assets] An unresolved " + label
							+ " mapping overlaps prior managed output; refresh stopped to preserve it.");
					}
				} else {
					var destination = safeDestination(destinationRoot, projectedOwner);
					if (destination == null) {
						state.failed = true;
						plan.failed = true;
						blockAllLegacy(state);
						addDiagnostic(plan, state, "[source-mapped-assets:" + label
							+ "] Candidate projection returned an unsafe owner path.");
						continue;
					}
					blockDestination(state, destination);
					if (protectedProjection) suppressMappedDestination(state, projectedOwner);
					if (ambiguous) state.ambiguousDestinations.set(pathKey(destination), true);
					// `hasOwnedPath` covers every manifest leaf below a projected
					// prefix and exact leaves regardless of extension/type policy.
					if (protectedProjection && context.hasOwnedPath(destination)) {
						state.failed = true;
						plan.failed = true;
						addDiagnostic(plan, state, "[source-mapped-assets] An unresolved " + label
							+ " mapping overlaps prior managed output; refresh stopped to preserve it: "
							+ projectedOwner);
					}
				}
				if (decision.reason != null && decision.reason != "")
					addDiagnostic(plan, state, "[source-mapped-assets:" + label + "] " + decision.reason);
			}
		}
	}

	static function hasTypedProjectionPath(projections:Array<PsychAssetProfileProjection>,
		relative:String, ownerPaths:Bool):Bool {
		if (projections == null || relative == null) return false;
		var expected = pathKey(relative);
		for (projection in projections) {
			if (projection == null) continue;
			var value = ownerPaths ? projection.ownerRelative : projection.sourceRelative;
			if (value != null && pathKey(value) == expected) return true;
		}
		return false;
	}

	static function projectionDecision(policy:SourceMappedAssetPolicy, sourceRelative:Null<String>,
		ownerRelative:Null<String>):Null<SourceMappedAssetDecision> {
		if (policy.classifyProjection != null) return policy.classifyProjection(sourceRelative, ownerRelative);
		if (ownerRelative != null && policy.managedOutputPredicate(ownerRelative))
			return {state:"defer", ownerRelative:ownerRelative};
		if (sourceRelative != null && policy.beforeHash(sourceRelative,
			ownerRelative == null ? sourceRelative : ownerRelative))
			return {state:"defer", ownerRelative:ownerRelative};
		if (sourceRelative == "" && ownerRelative == "") return {state:"defer"};
		return {state:"ignore"};
	}

	static function deferEvent(plan:SourceMappedAssetPlan, context:ImportIO,
		state:SourceMappedAssetPolicyPlan, policy:SourceMappedAssetPolicy, destinationRoot:String,
		event:PsychAssetProfileMappedFile, sourceRelative:String, projectedOwner:Dynamic,
		reason:Null<String>):Void {
		blockSource(state, event.sourcePath);
		if (policy.limeIdentity == true) {
			plan.identityComplete = false;
			var identityKey = SourceLimeAssetIdentity.keyForEvent(event);
			if (identityKey == null) {
				plan.identityBlockAll = true;
				plan.identityLibrariesComplete = false;
			} else addIdentityBlockedKey(plan, identityKey);
		}
		var rawOwner:Dynamic = projectedOwner == null ? event.ownerRelative : projectedOwner;
		if (rawOwner == null || rawOwner == "") {
			// The caller cannot tell which physical runtime subtree owns this
			// mapping. Close this policy's legacy path and preserve any prior
			// managed output anywhere in its authenticated owner namespace.
			blockAllLegacy(state);
			state.suppressAllMapped = true;
			if (hasManagedOutputUnder(context, destinationRoot, "", policy)) {
				state.failed = true;
				plan.failed = true;
				addDiagnostic(plan, state, "[source-mapped-assets] A deferred " + state.label
					+ " mapping has no safely enumerable owner scope and overlaps prior managed output; refresh stopped to preserve it.");
			}
			if (reason != null && reason != "")
				addDiagnostic(plan, state, "[source-mapped-assets:" + state.label + "] " + reason);
			return;
		}
		var ownerRelative = safeRelative(rawOwner, false);
		if (ownerRelative != null) {
			var destination = safeDestination(destinationRoot, ownerRelative);
			if (destination != null) {
				blockDestination(state, destination);
				suppressMappedDestination(state, ownerRelative);
				// An exact deferred leaf can collide with output owned by another
				// runtime class (or use an extension this policy cannot classify).
				// The predicate is reserved for unenumerable subtree protection.
				if (context.hasOwnedPath(destination)) {
					state.failed = true;
					plan.failed = true;
					addDiagnostic(plan, state, "[source-mapped-assets] A deferred " + state.label + " mapping overlaps prior managed output; refresh stopped to preserve it: " + ownerRelative);
				}
			}
		} else {
			blockAllLegacy(state);
			state.suppressAllMapped = true;
			state.failed = true;
			plan.failed = true;
			addDiagnostic(plan, state, "[source-mapped-assets:" + state.label
				+ "] Deferred mapping returned an unsafe owner path; refresh stopped to preserve prior data.");
		}
		if (reason != null && reason != "")
			addDiagnostic(plan, state, "[source-mapped-assets:" + state.label + "] " + reason);
	}

	static function markCollision(plan:SourceMappedAssetPlan, context:ImportIO,
		destination:String, ownerRelative:String, existingFile:SourceMappedAssetFile,
		existingLabels:Array<String>, currentLabel:String,
		policies:Map<String, SourceMappedAssetPolicy>, incoming:PsychAssetProfileMappedFile):Void {
		if (plan.identityEngine != "") {
			plan.identityComplete = false;
			if (existingFile != null) {
				if (existingFile.identityEvents != null) for (identityEvent in existingFile.identityEvents)
					addIdentityBlockedKey(plan, SourceLimeAssetIdentity.keyForEvent(identityEvent.event));
				addIdentityBlockedKey(plan, SourceLimeAssetIdentity.keyForEvent(existingFile.event));
			}
			addIdentityBlockedKey(plan, SourceLimeAssetIdentity.keyForEvent(incoming));
		}
		var key = pathKey(destination);
		var affected:Map<String, Bool> = new Map();
		if (existingLabels != null) for (label in existingLabels) affected.set(label, true);
		affected.set(currentLabel, true);
		for (label in affected.keys()) {
			var state = plan.policies.get(label);
			var policy = policies.get(label);
			if (state == null || policy == null) continue;
			state.ambiguousDestinations.set(key, true);
			blockDestination(state, destination);
			suppressMappedDestination(state, ownerRelative);
			if (context.hasOwnedPath(destination)) {
				state.failed = true;
				plan.failed = true;
				addDiagnostic(plan, state, "[source-mapped-assets] Distinct sources map to a previously managed " + state.label + " output; refresh stopped to preserve it: " + ownerRelative);
			} else addDiagnostic(plan, state, "[source-mapped-assets] Distinct sources map to the same owner output: " + ownerRelative);
		}
	}

	static function hasManagedOutputUnder(context:ImportIO, destinationRoot:String,
		ownerPrefix:String, policy:SourceMappedAssetPolicy):Bool {
		if (context == null || policy == null) return false;
		var prefix = safeRelative(ownerPrefix, true);
		if (prefix == null) return false;
		var outputs = context.ownedOutputPathsUnder(destinationRoot, "");
		if (outputs == null) return false;
		for (output in outputs) {
			var relative = ownerRelativeFromOutput(destinationRoot, output);
			if (relative == null || !isPathUnder(relative, prefix)) continue;
			if (policy.managedOutputPredicate(relative)) return true;
		}
		return false;
	}

	static function hasAnyOwnedOutputUnder(context:ImportIO, destinationRoot:String):Bool {
		if (context == null || destinationRoot == null) return false;
		var outputs = context.ownedOutputPathsUnder(destinationRoot, "");
		return outputs != null && outputs.length > 0;
	}

	static function ownerRelativeFromOutput(destinationRoot:String, installRelative:String):Null<String> {
		var root = safeRelative(destinationRoot, false);
		var output = safeRelative(installRelative, false);
		if (root == null || output == null) return null;
		var normalizedRoot = pathKey(root);
		var normalizedOutput = pathKey(output);
		var prefix = normalizedRoot + "/";
		if (!StringTools.startsWith(normalizedOutput, prefix)) return null;
		return output.substr(root.length + 1);
	}

	static function isPathUnder(path:String, prefix:String):Bool {
		var key = pathKey(path);
		var parent = pathKey(prefix);
		return key == parent || parent == "" || StringTools.startsWith(key,
			StringTools.endsWith(parent, "/") ? parent : parent + "/");
	}

	static function blockSource(state:SourceMappedAssetPolicyPlan, source:String):Void {
		if (source != null && source != "") state.blockedSources.set(pathKey(source), true);
	}
	static function addIdentityBlockedKey(plan:SourceMappedAssetPlan,
		key:Null<SourceLimeAssetIdentityKey>):Void {
		if (plan == null || key == null) return;
		var token = SourceLimeAssetIdentity.keyToken(key);
		if (token == null) {
			plan.identityBlockAll = true;
			plan.identityLibrariesComplete = false;
			return;
		}
		for (existing in plan.identityBlockedKeys)
			if (SourceLimeAssetIdentity.keyToken(existing) == token) return;
		plan.identityBlockedKeys.push({library:key.library, id:key.id});
	}

	static function addIdentityEvent(file:SourceMappedAssetFile,
		event:PsychAssetProfileMappedFile, ownerRelative:String):Void {
		if (file == null || event == null || ownerRelative == null) return;
		if (file.identityEvents == null) file.identityEvents = [];
		for (existing in file.identityEvents) {
			var existingKey = SourceLimeAssetIdentity.keyForEvent(existing.event);
			var nextKey = SourceLimeAssetIdentity.keyForEvent(event);
			if (SourceLimeAssetIdentity.keyToken(existingKey) == SourceLimeAssetIdentity.keyToken(nextKey)
				&& existing.ownerRelative == ownerRelative
				&& existing.event.sha256 == event.sha256) return;
		}
		file.identityEvents.push({event:event, ownerRelative:ownerRelative});
	}
	static function blockDestination(state:SourceMappedAssetPolicyPlan, destination:String):Void {
		if (destination != null && destination != "") state.blockedDestinations.set(pathKey(destination), true);
	}
	static function suppressMappedSource(state:SourceMappedAssetPolicyPlan, source:String):Void {
		if (source != null && source != "") state.suppressedMappedSources.set(pathKey(source), true);
	}
	static function suppressMappedDestination(state:SourceMappedAssetPolicyPlan, destination:String):Void {
		if (destination != null && destination != "") state.suppressedMappedDestinations.set(pathKey(destination), true);
	}
	static function blockAllLegacy(state:SourceMappedAssetPolicyPlan):Void {
		state.blockAllLegacy = true;
		state.legacyAllowed = false;
	}

	static function checkCancelled(plan:SourceMappedAssetPlan, cancelled:Void->Bool):Bool {
		if (!publicationCancelled(cancelled)) return false;
		cancelAll(plan);
		return true;
	}
	static function cancelAll(plan:SourceMappedAssetPlan):Void {
		plan.cancelled = true;
		for (state in plan.policies) state.cancelled = true;
	}
	static function failAll(plan:SourceMappedAssetPlan, message:String):Void {
		plan.failed = true;
		addDiagnostic(plan, null, message);
	}
	static function addDiagnostic(plan:SourceMappedAssetPlan,
		state:Null<SourceMappedAssetPolicyPlan>, message:String):Void {
		plan.diagnostics.push(message);
		if (state != null) state.diagnostics.push(message);
	}
	static function mergeDiagnostics(left:Array<String>, right:Array<String>):Array<String> {
		var result:Array<String> = [];
		if (left != null) for (message in left) if (result.indexOf(message) < 0) result.push(message);
		if (right != null) for (message in right) if (result.indexOf(message) < 0) result.push(message);
		return result;
	}
	static function cloneMap(source:Map<String, Bool>):Map<String, Bool> {
		var result:Map<String, Bool> = new Map();
		if (source != null) for (key in source.keys()) result.set(key, source.get(key));
		return result;
	}
	static function isPathBlocked(path:String, blocked:Map<String, Bool>):Bool {
		if (path == null || blocked == null) return false;
		var key = pathKey(path);
		if (key == "") return false;
		for (prefix in blocked.keys())
			if (key == prefix || StringTools.startsWith(key, StringTools.endsWith(prefix, "/")
				? prefix : prefix + "/")) return true;
		return false;
	}
	static function safeSource(contentRoot:String, rootRelative:String, relative:Dynamic):Null<String> {
		var clean = safeRelative(relative, false);
		if (clean == null) return null;
		var selected = selectedRoot(contentRoot, rootRelative);
		return selected == "" ? null : Path.normalize(Path.join([selected, clean]));
	}
	static function selectedRoot(contentRoot:String, rootRelative:String):String {
		if (contentRoot == null || rootRelative == null) return "";
		return Path.normalize(rootRelative == "" ? contentRoot : Path.join([contentRoot, rootRelative]));
	}
	static function safeDestination(root:String, relative:String):Null<String> {
		var clean = safeRelative(relative, false);
		if (root == null || StringTools.trim(root) == "" || clean == null) return null;
		return Path.normalize(Path.join([root, clean]));
	}
	static function safeRelative(value:Dynamic, allowEmpty:Bool):Null<String> {
		if (value == null) return null;
		var clean = StringTools.replace(StringTools.trim(Std.string(value)), "\\", "/");
		if (clean == "") return allowEmpty ? "" : null;
		if (StringTools.startsWith(clean, "/") || StringTools.startsWith(clean, "~")
			|| clean.indexOf(":") >= 0 || clean.indexOf("\u0000") >= 0) return null;
		var pieces:Array<String> = [];
		for (piece in clean.split("/")) {
			if (piece == "" || piece == ".") continue;
			if (piece == "..") return null;
			pieces.push(piece);
		}
		if (pieces.length == 0) return allowEmpty ? "" : null;
		return pieces.join("/");
	}
	static function publicationCancelled(cancelled:Void->Bool):Bool {
		#if sys
		if (!ImportWorkScheduler.cooperate(cancelled)) return true;
		#end
		return cancelled != null && cancelled();
	}
	static function fieldString(value:Dynamic, name:String):String {
		var field = value == null ? null : Reflect.field(value, name);
		return field == null ? "" : Std.string(field);
	}
	static function samePath(left:String, right:String):Bool {
		return left != null && right != null && pathKey(Path.normalize(left)) == pathKey(Path.normalize(right));
	}
	static function pathKey(path:String):String {
		if (path == null) return "";
		var clean = StringTools.replace(Path.normalize(path), "\\", "/");
		#if windows
		return clean.toLowerCase();
		#else
		return clean;
		#end
	}
}
