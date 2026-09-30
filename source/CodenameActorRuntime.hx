package;

import CodenameActorPlan.CodenameActorOccurrence;

typedef CodenameLiveActor<T> = {
	var occurrence:CodenameActorOccurrence;
	var actor:T;
	/** Native role actors belong to PlayState; only newly constructed actors
	 * belong to this runtime. */
	var owned:Bool;
}

typedef CodenameActorDiagnostic = {
	var code:String;
	var lineIndex:Int;
	var occurrenceIndex:Int;
	var role:String;
	var lineType:Null<Int>;
	var authoredId:String;
	var nativeName:Null<String>;
}

/** Live character identities for one selected Codename actor plan.
 * Construction, presentation and destruction stay with the caller so this
 * collection does not depend on PlayState or a particular sprite class. */
class CodenameActorRuntime<T> {
	public var diagnostics(default, null):Array<String> = [];
	/** Machine-readable details accompany the stable human-readable diagnostics. */
	public var structuredDiagnostics(default, null):Array<CodenameActorDiagnostic> = [];
	public var bindings(default, null):Array<CodenameLiveActor<T>> = [];
	var plan:CodenameActorPlan;
	var create:CodenameActorOccurrence->Null<T>;
	var place:(T, CodenameActorOccurrence)->Void;
	var destroy:T->Void;
	var borrowed:Map<String, T> = new Map();
	/** Hidden actors retained by source character-switch scripts stay owned
	 * until song teardown, even after the active occurrence changes. */
	var retiredOwned:Array<T> = [];
	var started:Bool = false;
	var released:Bool = false;

	public function new(plan:CodenameActorPlan, create:CodenameActorOccurrence->Null<T>,
		place:(T, CodenameActorOccurrence)->Void, destroy:T->Void) {
		if (plan == null || create == null || place == null || destroy == null)
			throw 'Invalid Codename actor runtime';
		this.plan = plan;
		this.create = create;
		this.place = place;
		this.destroy = destroy;
	}

	static function key(lineIndex:Int, occurrenceIndex:Int):String
		return lineIndex + ':' + occurrenceIndex;

	/** Only the converter's exact first occurrence for a role can borrow its
	 * existing native actor. Never search a later equal ID. */
	public function bindPrimary(role:String, nativeName:String, actor:T):Bool {
		if (started || released || actor == null) return false;
		var occurrence = plan.primaryFor(role, nativeName);
		if (occurrence == null) return false;
		var id = key(occurrence.lineIndex, occurrence.occurrenceIndex);
		if (borrowed.exists(id)) return borrowed.get(id) == actor;
		for (other in borrowed) if (other == actor) return false;
		borrowed.set(id, actor);
		return true;
	}

	/** Transfer an exact native-primary alias after a character swap. Neither
	 * the old nor the new actor becomes owned by this collection. */
	public function rebindBorrowed(previous:T, replacement:T):Bool {
		if (released || previous == null || replacement == null) return false;
		var target:String = null;
		for (id in borrowed.keys()) if (borrowed.get(id) == previous) {
			target = id;
			break;
		}
		if (target == null) return false;
		for (id in borrowed.keys())
			if (id != target && borrowed.get(id) == replacement) return false;
		for (binding in bindings)
			if (binding.actor == replacement && binding.actor != previous) return false;
		borrowed.set(target, replacement);
		for (binding in bindings) if (!binding.owned && binding.actor == previous)
			binding.actor = replacement;
		return true;
	}

	/** Replace one active line occurrence after a source script mutates its
	 * `strumLines.members[].characters[]` view. Hidden cached instances remain
	 * owned until teardown and may be reattached by a later event. */
	public function replaceActor(lineIndex:Int, occurrenceIndex:Int, replacement:T,
		?replacementOwned:Bool = true):Bool {
		if (released || replacement == null || lineIndex < 0 || occurrenceIndex < 0) return false;
		var target = find(lineIndex, occurrenceIndex);
		if (target == null) {
			var occurrence:CodenameActorOccurrence = null;
			for (candidate in plan.occurrences)
				if (candidate.lineIndex == lineIndex && candidate.occurrenceIndex == occurrenceIndex) {
					occurrence = candidate;
					break;
				}
			if (occurrence == null) return false;
			for (binding in bindings) if (binding.actor == replacement) return false;
			var id = key(lineIndex, occurrenceIndex);
			retiredOwned.remove(replacement);
			if (replacementOwned) {
				borrowed.remove(id);
			} else borrowed.set(id, replacement);
			var insertion = bindings.length;
			for (index in 0...bindings.length) {
				var existing = bindings[index].occurrence;
				if (existing.lineIndex > lineIndex
					|| (existing.lineIndex == lineIndex && existing.occurrenceIndex > occurrenceIndex)) {
					insertion = index;
					break;
				}
			}
			bindings.insert(insertion, {occurrence:occurrence, actor:replacement,
				owned:replacementOwned});
			return true;
		}
		if (target.actor == replacement) return true;
		for (binding in bindings)
			if (binding != target && binding.actor == replacement) return false;
		var id = key(lineIndex, occurrenceIndex);
		if (target.owned && target.actor != null && retiredOwned.indexOf(target.actor) < 0)
			retiredOwned.push(target.actor);
		retiredOwned.remove(replacement);
		target.actor = replacement;
		target.owned = replacementOwned;
		if (replacementOwned) borrowed.remove(id); else borrowed.set(id, replacement);
		return true;
	}

	/** Remove one live occurrence while preserving its authored slot. Owned
	 * instances stay alive but detached until cleanup, matching character swaps. */
	public function removeActor(lineIndex:Int, occurrenceIndex:Int):Bool {
		if (released) return false;
		var target = find(lineIndex, occurrenceIndex);
		if (target == null) return false;
		bindings.remove(target);
		if (target.owned && target.actor != null && retiredOwned.indexOf(target.actor) < 0)
			retiredOwned.push(target.actor);
		borrowed.remove(key(lineIndex, occurrenceIndex));
		return true;
	}

	/** Materialize in source line and occurrence order. An unresolved mapping
	 * stays absent rather than acquiring a native role or similarly named actor. */
	public function materialize():Void {
		if (started || released) return;
		started = true;
		for (occurrence in plan.occurrences) {
			var id = key(occurrence.lineIndex, occurrence.occurrenceIndex);
			if (occurrence.nativeName == null) {
				diagnostics.push('unresolved-character:' + id + ':' + occurrence.authoredId);
				structuredDiagnostics.push({code:'unresolved-character',
					lineIndex:occurrence.lineIndex, occurrenceIndex:occurrence.occurrenceIndex,
					role:occurrence.role, lineType:occurrence.lineType,
					authoredId:occurrence.authoredId, nativeName:occurrence.nativeName});
				continue;
			}
			if (!occurrence.placement.supported) {
				diagnostics.push('unsupported-placement:' + id);
				// Keep an exact native primary identity available to scripts, but
				// do not create an extra actor at an invented position.
				if (borrowed.exists(id))
					bindings.push({occurrence:occurrence, actor:borrowed.get(id), owned:false});
				continue;
			}
			var owned = !borrowed.exists(id);
			var actor:Null<T> = null;
			try actor = owned ? create(occurrence) : borrowed.get(id)
			catch (error:Dynamic) {
				diagnostics.push('construction-failed:' + id + ':' + Std.string(error));
				continue;
			}
			if (actor == null) {
				diagnostics.push('construction-failed:' + id);
				continue;
			}
			var duplicate = false;
			for (binding in bindings) if (binding.actor == actor) {
				duplicate = true;
				break;
			}
			if (duplicate) {
				diagnostics.push('duplicate-instance:' + id);
				continue;
			}
			var live:CodenameLiveActor<T> = {occurrence:occurrence, actor:actor, owned:owned};
			bindings.push(live);
			try place(actor, occurrence)
			catch (error:Dynamic) {
				diagnostics.push('placement-failed:' + id + ':' + Std.string(error));
				if (owned) {
					bindings.pop();
					try destroy(actor) catch (cleanupError:Dynamic)
						diagnostics.push('cleanup-failed:' + id + ':' + Std.string(cleanupError));
				}
			}
		}
	}

	public function contains(actor:T):Bool {
		for (binding in bindings) if (binding.actor == actor) return true;
		return false;
	}

	public function find(lineIndex:Int, occurrenceIndex:Int):Null<CodenameLiveActor<T>> {
		for (binding in bindings)
			if (binding.occurrence.lineIndex == lineIndex
				&& binding.occurrence.occurrenceIndex == occurrenceIndex)
				return binding;
		return null;
	}

	/** A copy protects the occurrence order from callers editing the registry. */
	public function lineCharacters(lineIndex:Int):Array<Null<T>> {
		var result:Array<Null<T>> = [];
		for (occurrence in plan.occurrences) if (occurrence.lineIndex == lineIndex)
			while (result.length <= occurrence.occurrenceIndex) result.push(null);
		for (binding in bindings)
			if (binding.occurrence.lineIndex == lineIndex)
				result[binding.occurrence.occurrenceIndex] = binding.actor;
		return result;
	}

	/** Release extra instances once. Native primaries remain caller-owned. */
	public function cleanup():Void {
		if (released) return;
		released = true;
		for (actor in retiredOwned)
			try destroy(actor) catch (diagnostic:Dynamic)
				diagnostics.push('cleanup-failed:retired:' + Std.string(diagnostic));
		retiredOwned.resize(0);
		for (binding in bindings) if (binding.owned)
			try destroy(binding.actor) catch (error:Dynamic)
				diagnostics.push('cleanup-failed:' + key(binding.occurrence.lineIndex,
					binding.occurrence.occurrenceIndex) + ':' + Std.string(error));
		bindings.resize(0);
		borrowed = new Map();
	}
}
