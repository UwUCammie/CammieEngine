package;

import RuntimeOwnerAssetIdentity.RuntimeOwnerAssetIdentityResult;

typedef SourceOwnerAssetContextLookup = {
	var identity:RuntimeOwnerAssetIdentity;
	var result:RuntimeOwnerAssetIdentityResult;
}

/**
	Authenticated owner tuple for the shared Lime/OpenFL Assets facades.

	The tuple is a routing context, not proof by itself. Each facade lookup still
	acquires the matching receipt-bound RuntimeOwnerAssetIdentity before using an
	indexed ID. Nightmare Vision package and core contexts are intentionally
	separate and never fall back to the host asset registry.
*/
@:keep
class SourceOwnerAssetContext {
	public final ownerRoot:String;
	public final engine:String;
	public final scope:String;
	public final allowNativeFallback:Bool;
	/** Raw owner files not represented by a committed asset identity are only
		available to the legacy Psych facade, not the compiled NV Assets surface. */
	public final allowOwnerPathFallback:Bool;
	/** Exact identity scopes, in source precedence order. */
	public final identityScopes:Array<String>;
	public final cacheScope:String;
	public final composite:Bool;
	/** Physical root used for owner-relative file reads. */
	public final pathRoot:String;
	/** Relative subtree excluded from this scope, if any. */
	public final excludedSubtree:String;

	private function new(ownerRoot:String, engine:String, scope:String,
		identityScopes:Array<String>, pathRoot:String, excludedSubtree:String,
		allowOwnerPathFallback:Bool) {
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		var selectedEngine = ImportRevision.normalizeEngine(engine);
		if (owner == '') throw '[psych-assets] A valid selected import owner root is required';
		if (selectedEngine == '') throw '[source-assets] A valid source engine is required';
		if (selectedEngine == 'Psych Engine' && scope != 'package')
			throw '[source-assets] Psych assets require the package scope';
		var validComposite = selectedEngine == 'Nightmare Vision' && scope == 'composite'
			&& identityScopes != null && identityScopes.length == 2
			&& identityScopes[0] == 'package' && identityScopes[1] == 'core';
		if (selectedEngine == 'Nightmare Vision' && scope != 'package' && scope != 'core'
			&& !validComposite)
			throw '[source-assets] Nightmare Vision assets require an authenticated package or core scope';
		if (selectedEngine != 'Psych Engine' && selectedEngine != 'Nightmare Vision')
			throw '[source-assets] This owner Assets facade does not support the selected source engine';

		if (identityScopes == null || identityScopes.length == 0)
			throw '[source-assets] At least one authenticated identity scope is required';
		for (identityScope in identityScopes) {
			if (selectedEngine == 'Psych Engine' && identityScope != 'package')
				throw '[source-assets] Psych identity scope must be package';
			if (selectedEngine == 'Nightmare Vision'
				&& identityScope != 'package' && identityScope != 'core')
				throw '[source-assets] Nightmare Vision identity scope must be package or core';
		}

		this.ownerRoot = owner;
		this.engine = selectedEngine;
		this.scope = scope;
		allowNativeFallback = selectedEngine == 'Psych Engine';
		this.allowOwnerPathFallback = selectedEngine == 'Psych Engine' && allowOwnerPathFallback;
		this.identityScopes = identityScopes.copy();
		composite = identityScopes.length > 1;
		cacheScope = composite ? 'package' : identityScopes[0];
		this.pathRoot = pathRoot;
		this.excludedSubtree = excludedSubtree;
	}

	/** Existing Psych compiled-stage behavior: owner first, then shared native assets. */
	public static function psych(ownerRoot:String):SourceOwnerAssetContext
		return new SourceOwnerAssetContext(ownerRoot, 'Psych Engine', 'package', ['package'],
			PsychOwnerAssetPath.normalizeOwner(ownerRoot), '', true);

	/** One authenticated Nightmare Vision package or engine/core scope. */
	public static function nightmareVision(ownerRoot:String, scope:String):SourceOwnerAssetContext
		return new SourceOwnerAssetContext(ownerRoot, 'Nightmare Vision', scope, [scope],
			scope == 'core' ? PsychOwnerAssetPath.normalizeOwner(ownerRoot) + '/__nmv_core'
				: PsychOwnerAssetPath.normalizeOwner(ownerRoot),
			scope == 'package' ? '__nmv_core' : '', false);

	/** The donor's compiled Assets surface includes core entries followed by
		content/package entries. Package is later in Project order and therefore
		wins a duplicate `(library,id)`. Both identities must remain exact and
		receipt-backed; this composite never reaches a host/global registry. */
	public static function nightmareVisionAssets(ownerRoot:String):SourceOwnerAssetContext {
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		return new SourceOwnerAssetContext(owner, 'Nightmare Vision', 'composite',
			['package', 'core'], owner, '', false);
	}

	/** Resolve an ID only through this context's selected owner identities. */
	public function lookupAsset(id:String, expectedType:Null<String>):SourceOwnerAssetContextLookup {
		refreshCompositeCache();
		var last:SourceOwnerAssetContextLookup = null;
		for (identityScope in identityScopes) {
			var identity = RuntimeOwnerAssetIdentity.acquire(ownerRoot, engine, identityScope);
			var result = identity.resolve(id, expectedType);
			var selected:SourceOwnerAssetContextLookup = {identity:identity, result:result};
			last = selected;
			if (result.state == 'found') {
				var selectedPathRoot = engine == 'Nightmare Vision' && identityScope == 'core'
					? ownerRoot + '/__nmv_core' : ownerRoot;
				var selectedExcluded = engine == 'Nightmare Vision' && identityScope == 'package'
					? '__nmv_core' : '';
				if (!PsychOwnerAssetPath.pathInScope(ownerRoot, result.path,
					selectedPathRoot, selectedExcluded))
					return {identity:identity, result:copyResult(result, 'unknown', null)};
				return selected;
			}
			if (!composite || (result.state != 'missing' && result.state != 'unclaimed'
				&& result.state != 'no-index'))
				return selected;
		}
		return last;
	}

	/** Merge owner-listed IDs while keeping the source's package-over-core
		precedence for duplicate `(library,id)` entries. */
	public function listAssets(?library:String, ?expectedType:String):Array<String> {
		refreshCompositeCache();
		if (!composite) {
			var identity = RuntimeOwnerAssetIdentity.acquire(ownerRoot, engine, identityScopes[0]);
			return identity.list(library, expectedType);
		}
		var identities:Array<RuntimeOwnerAssetIdentity> = [];
		for (identityScope in identityScopes) {
			var identity = RuntimeOwnerAssetIdentity.acquire(ownerRoot, engine, identityScope);
			if (identity.bindingState != 'ready') {
				if (identity.bindingState == 'no-index') continue;
				return [];
			}
			if (!identity.complete || !identity.librariesComplete) return [];
			identities.push(identity);
		}
		var output:Array<String> = [];
		var seen:Map<String, Bool> = new Map();
		for (identity in identities) for (entry in identity.entries) {
			if (library != null && entry.library != SourceLimeAssetIdentity.canonicalLibrary(library)) continue;
			var key = entry.library + '\x00' + entry.id;
			if (seen.exists(key)) continue;
			seen.set(key, true);
			var selected = lookupAsset(entry.library + ':' + entry.id, expectedType);
			if (selected != null && selected.result.state == 'found') output.push(entry.id);
		}
		return output;
	}

	public function libraryState(library:String):String {
		refreshCompositeCache();
		var declared = false;
		for (identityScope in identityScopes) {
			var identity = RuntimeOwnerAssetIdentity.acquire(ownerRoot, engine, identityScope);
			if (identity.bindingState != 'ready') {
				if (!composite) return identity.libraryState(library);
				if (identity.bindingState == 'no-index') continue;
				return 'unknown';
			}
			var state = identity.libraryState(library);
			if (state == 'unknown') return 'unknown';
			if (state == 'declared') declared = true;
		}
		return declared ? 'declared' : 'unclaimed';
	}

	/** Capture the complete scope proof plus the current winning identity for an
		asynchronous or cached operation. An unchanged core identity is stale for
		this facade if a later package identity now shadows the same ID. */
	public function selectionGuard(id:String, expectedType:Null<String>,
		selectedIdentity:RuntimeOwnerAssetIdentity):Void->Bool {
		var capturedProof = proofSignature();
		return function():Bool {
			try {
				if (proofSignature() != capturedProof) return false;
				var selected = lookupAsset(id, expectedType);
				return selected != null && selected.result.state == 'found'
					&& selected.identity == selectedIdentity;
			} catch (_:Dynamic) {
				return false;
			}
		};
	}

	public function proofSignature():String {
		var identities:Array<RuntimeOwnerAssetIdentity> = [];
		for (identityScope in identityScopes)
			identities.push(RuntimeOwnerAssetIdentity.acquire(ownerRoot, engine, identityScope));
		if (composite) SourceOwnerAssetContextCache.refresh(this, identities);
		return SourceOwnerAssetContextCache.proofSignature(this, identities);
	}

	/** Return authenticated identities that actually claim this library. */
	public function identitiesForLibrary(library:String):Array<RuntimeOwnerAssetIdentity> {
		refreshCompositeCache();
		var output:Array<RuntimeOwnerAssetIdentity> = [];
		for (identityScope in identityScopes) {
			var identity = RuntimeOwnerAssetIdentity.acquire(ownerRoot, engine, identityScope);
			if (identity.bindingState != 'ready') {
				if (composite && identity.bindingState == 'no-index') continue;
				if (composite) throw '[source-assets] Composite owner asset identity is incomplete';
				continue;
			}
			var state = identity.libraryState(library);
			if (state == 'unknown') throw '[source-assets] Owner library identity is incomplete';
			if (state == 'declared') output.push(identity);
		}
		return output;
	}

	function refreshCompositeCache():Void {
		if (!composite) return;
		var identities:Array<RuntimeOwnerAssetIdentity> = [];
		for (identityScope in identityScopes)
			identities.push(RuntimeOwnerAssetIdentity.acquire(ownerRoot, engine, identityScope));
		SourceOwnerAssetContextCache.refresh(this, identities);
	}

	static function copyResult(source:RuntimeOwnerAssetIdentityResult,
		state:String, path:Null<String>):RuntimeOwnerAssetIdentityResult {
		return {state:state, owner:source.owner, library:source.library, id:source.id,
			expectedType:source.expectedType, entry:source.entry, path:path};
	}
}
