package;

/** Owner- and field-scoped leases for source character hold animation state. */
typedef SourceCharacterHoldClaim = {
	final owner:String;
	final field:Dynamic;
	final role:Dynamic;
	final actor:Dynamic;
	final noteOwnerOverride:Bool;
}

class SourceCharacterHoldLedger {
	final claims:Array<SourceCharacterHoldClaim> = [];

	public function new() {}

	/** A character is held once per field even when several notes hit in a row. */
	public function retain(owner:String, field:Dynamic, role:Dynamic, actor:Dynamic,
		noteOwnerOverride:Bool = false):Bool {
		if (owner == null || owner == '' || field == null || role == null || actor == null) return false;
		for (claim in claims) if (claim.owner == owner && claim.field == field && claim.actor == actor) {
			// A role reassignment is valid only after PlayState has verified the
			// actor against its live source group; keep the lease's current role.
			if (claim.role != role || claim.noteOwnerOverride != noteOwnerOverride)
				replaceRole(claim, role, noteOwnerOverride);
			return false;
		}
		claims.push({owner:owner, field:field, role:role, actor:actor, noteOwnerOverride:noteOwnerOverride});
		return true;
	}

	function replaceRole(claim:SourceCharacterHoldClaim, role:Dynamic, noteOwnerOverride:Bool):Void {
		var index = claims.indexOf(claim);
		if (index >= 0) claims[index] = {owner:claim.owner, field:claim.field, role:role,
			actor:claim.actor, noteOwnerOverride:noteOwnerOverride};
	}

	public function clearField(owner:String, field:Dynamic):Array<Dynamic>
		return removeWhere(function(claim) return claim.owner == owner && claim.field == field);
	public function clearFieldAll(field:Dynamic):Array<Dynamic>
		return removeWhere(function(claim) return claim.field == field);

	public function clearActor(owner:String, actor:Dynamic):Array<Dynamic>
		return removeWhere(function(claim) return claim.owner == owner && claim.actor == actor);

	public function clearOwner(owner:String):Array<Dynamic>
		return removeWhere(function(claim) return claim.owner == owner);

	public function clearAll():Array<Dynamic>
		return removeWhere(function(_) return true);

	/** Drop invalid role/field leases while preserving actors still held elsewhere. */
	public function prune(isValid:SourceCharacterHoldClaim->Bool):Array<Dynamic> {
		return removeWhere(function(claim) return isValid == null || !isValid(claim));
	}

	function removeWhere(shouldRemove:SourceCharacterHoldClaim->Bool):Array<Dynamic> {
		var touched:Array<Dynamic> = [];
		var kept:Array<SourceCharacterHoldClaim> = [];
		for (claim in claims) {
			if (shouldRemove != null && shouldRemove(claim)) {
				if (touched.indexOf(claim.actor) < 0) touched.push(claim.actor);
			} else kept.push(claim);
		}
		claims.resize(0);
		for (claim in kept) claims.push(claim);
		var releasable:Array<Dynamic> = [];
		for (actor in touched) if (!hasActorClaim(actor)) releasable.push(actor);
		return releasable;
	}

	public function hasActorClaim(actor:Dynamic):Bool {
		for (claim in claims) if (claim.actor == actor) return true;
		return false;
	}

	/** Avoid scanning input and rebuilding prune buffers from the uncapped update
	 * loop when no manual NV singer currently has a hold lease. */
	public inline function hasClaims():Bool return claims.length > 0;

	public function hasClaim(owner:String, field:Dynamic, actor:Dynamic):Bool {
		for (claim in claims) if (claim.owner == owner && claim.field == field && claim.actor == actor) return true;
		return false;
	}

	public function snapshot():Array<SourceCharacterHoldClaim> return claims.copy();
}
