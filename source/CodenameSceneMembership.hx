package;

private typedef CodenameScenePlacement<T> = {
	var owner:Dynamic;
	var index:Null<Int>;
	var before:T;
	var after:T;
}

private typedef CodenameSceneNode<T> = {
	var node:T;
	var initial:CodenameScenePlacement<T>;
	var actions:Array<CodenameScenePlacement<T>>;
}

/** Reversible borrowed scene membership shared by every Codename scope.
 * Nodes are never destroyed here. `index` is measured after removing `node`
 * from the current member list; null means detach it. */
class CodenameSceneMembership<T> {
	final getMembers:Void->Array<T>;
	final detach:T->Void;
	final insert:(Int, T)->Void;
	final nodes:Array<CodenameSceneNode<T>> = [];

	public function new(getMembers:Void->Array<T>, detach:T->Void, insert:(Int, T)->Void) {
		this.getMembers = getMembers;
		this.detach = detach;
		this.insert = insert;
	}

	function stateFor(node:T):CodenameSceneNode<T> {
		for (state in nodes)
			if (state.node == node) return state;
		return null;
	}

	function without(node:T):Array<T> {
		var members = getMembers().copy();
		members.remove(node);
		return members;
	}

	function placement(owner:Dynamic, node:T, index:Null<Int>):CodenameScenePlacement<T> {
		var members = without(node);
		if (index == null) return {owner:owner, index:null, before:null, after:null};
		var at = index < 0 ? 0 : (index > members.length ? members.length : index);
		return {owner:owner, index:at,
			before:at > 0 ? members[at - 1] : null,
			after:at < members.length ? members[at] : null};
	}

	function apply(node:T, target:CodenameScenePlacement<T>):Void {
		detach(node);
		if (target.index == null) return;
		var members = getMembers();
		var at = target.index;
		if (target.after != null && members.indexOf(target.after) >= 0)
			at = members.indexOf(target.after);
		else if (target.before != null && members.indexOf(target.before) >= 0)
			at = members.indexOf(target.before) + 1;
		if (at < 0) at = 0;
		if (at > members.length) at = members.length;
		insert(at, node);
	}

	public function place(owner:Dynamic, node:T, index:Null<Int>):Void {
		if (owner == null || node == null) throw '[codename-scene] Missing owner or node';
		// FlxGroup.insert/add are no-ops for a node that already belongs to the
		// group. Keep the existing placement and ownership journal in that case.
		if (index != null && getMembers().indexOf(node) >= 0) return;
		var state = stateFor(node);
		if (state == null) {
			var current = getMembers();
			var original = current.indexOf(node);
			state = {node:node,
				initial:original < 0 ? {owner:null, index:null, before:null, after:null}
					: placement(null, node, original),
				actions:[]};
			nodes.push(state);
		}
		var action = placement(owner, node, index);
		// Only the latest placement from each owner can become active again.
		// Repeated update hooks must not grow this journal every frame.
		var i = state.actions.length - 1;
		while (i >= 0) {
			if (state.actions[i].owner == owner) state.actions.splice(i, 1);
			i--;
		}
		state.actions.push(action);
		apply(node, action);
	}

	public function release(owner:Dynamic):Void {
		if (owner == null) return;
		var i = nodes.length - 1;
		while (i >= 0) {
			var state = nodes[i];
			var previous = state.actions.length > 0
				? state.actions[state.actions.length - 1] : state.initial;
			var changed = false;
			var j = state.actions.length - 1;
			while (j >= 0) {
				if (state.actions[j].owner == owner) {
					state.actions.splice(j, 1);
					changed = true;
				}
				j--;
			}
			if (changed) {
				var active = state.actions.length > 0
					? state.actions[state.actions.length - 1] : state.initial;
				if (previous != active) apply(state.node, active);
				if (state.actions.length == 0) nodes.splice(i, 1);
			}
			i--;
		}
	}
}
