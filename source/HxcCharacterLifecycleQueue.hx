/**
 * Holds HXC character onAdd notifications until PlayState has a live stage.
 * Character actors are constructed before chart stage setup, but imported
 * companions may add stage props from onAdd. This queue keeps that callback
 * ordering intact without making character or stage content special cases.
 */
typedef HxcCharacterLifecycleCall = {
	var actor:Dynamic;
	var role:String;
	var actorOverride:Dynamic;
}

class HxcCharacterLifecycleQueue {
	var pending:Array<HxcCharacterLifecycleCall> = [];

	public function new() {}

	public var length(get, never):Int;
	function get_length():Int return pending.length;

	/** Keep one onAdd notification per actor/role pair. Initial character
	 * construction may notify once while loading the companion and again after
	 * the actor is installed in PlayState. Prefer the explicit construction-time
	 * actor override when both calls are queued before stage setup. */
	public function enqueue(actor:Dynamic, role:String, actorOverride:Dynamic):Void {
		if (actor == null)
			return;
		var callbackRole = role == null ? '' : role;
		for (index in 0...pending.length) {
			var queued = pending[index];
			if (queued.actor == actor && queued.role == callbackRole) {
				if (queued.actorOverride == null && actorOverride != null)
					pending[index] = {actor: actor, role: callbackRole, actorOverride: actorOverride};
				return;
			}
		}
		pending.push({actor: actor, role: callbackRole, actorOverride: actorOverride});
	}

	/** Drain a snapshot so notifications queued by a callback wait for the next
	 * stage-ready boundary instead of being dispatched recursively. */
	public function drain(callback:HxcCharacterLifecycleCall->Void):Int {
		if (callback == null || pending.length == 0)
			return 0;
		var ready = pending;
		pending = [];
		for (entry in ready)
			callback(entry);
		return ready.length;
	}
}
