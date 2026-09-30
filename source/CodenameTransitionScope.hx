package;

import haxe.io.Path;
using StringTools;

/** Small per-owner store for the shared Codename MusicBeatTransition module.
	Kept separate from Flixel so owner scoping and static-script lifetime can be
	verified without opening a game state or loading assets.
*/
class CodenameTransitionScope {
	static var selectedScripts:Map<String, String> = new Map();
	static var pendingIncoming:Map<String, String> = new Map();
	static var pendingStateTargets:Map<String, Dynamic> = new Map();
	static var pendingStateOwner:String = '';
	static var executingTransitionOwners:Array<String> = [];
	static var staticVariables:Map<String, Map<String, Dynamic>> = new Map();

	static function ownerKey(ownerRoot:String):String {
		if (ownerRoot == null || StringTools.trim(ownerRoot) == '') return '';
		return Path.normalize(ownerRoot.replace('\\', '/'));
	}

	public static function sameOwner(first:String, second:String):Bool
		return ownerKey(first) != '' && ownerKey(first) == ownerKey(second);

	/** Carry the concrete destination through FlxG's synchronous startOutro
		request so the source transition interpreter can see it as `newState`.
		The value is consumed once by the same selected owner. */
	public static function queueStateTarget(ownerRoot:String, target:Dynamic):Bool {
		var key = ownerKey(ownerRoot);
		if (key == '' || target == null) return false;
		pendingStateTargets.set(key, target);
		return true;
	}

	public static function takeStateTarget(ownerRoot:String):Dynamic {
		var key = ownerKey(ownerRoot);
		if (key == '' || !pendingStateTargets.exists(key)) return null;
		var target = pendingStateTargets.get(key);
		pendingStateTargets.remove(key);
		return target;
	}

	public static function clearPendingStateTarget(ownerRoot:String):Void {
		var key = ownerKey(ownerRoot);
		if (key != '') pendingStateTargets.remove(key);
	}

	static function moduleKey(ownerRoot:String, scriptPath:String):String {
		return ownerKey(ownerRoot) + '\n' + (scriptPath == null ? '' : scriptPath.replace('\\', '/'));
	}

	public static function script(ownerRoot:String):String {
		var key = ownerKey(ownerRoot);
		return key == '' || !selectedScripts.exists(key) ? '' : selectedScripts.get(key);
	}

	public static function setScript(ownerRoot:String, scriptPath:String):String {
		var key = ownerKey(ownerRoot);
		if (key == '') return scriptPath;
		selectedScripts.set(key, scriptPath == null ? '' : scriptPath);
		return scriptPath;
	}

	/** Prefer the owner named by the live chart; the explicit imported-mod
		session is a fallback for menu/state scripts without an active chart. */
	public static function resolveOwner(chartOwner:String, activeOwner:String):String {
		return ownerKey(chartOwner) != '' ? chartOwner : activeOwner;
	}

	/** Allow lifecycle callbacks for the chart owner, explicit owner session,
		or the owner carried across an outgoing state transition. */
	public static function canRunOwner(ownerRoot:String, chartOwner:String,
		activeOwner:String):Bool {
		var key = ownerKey(ownerRoot);
		return key != '' && (key == ownerKey(chartOwner) || key == ownerKey(activeOwner)
			|| key == ownerKey(pendingStateOwner));
	}

	/** Lifecycle transitions may run only for the owner which selected them. */
	public static function canRun(ownerRoot:String, activeOwnerRoot:String):Bool {
		var key = ownerKey(ownerRoot);
		return key != '' && key == ownerKey(activeOwnerRoot) && script(ownerRoot) != '';
	}

	/** An outgoing transition schedules one same-owner incoming transition. */
	public static function markOutgoingFinished(ownerRoot:String,
		stateHandoff:Bool = false, ?outgoingScript:String):Void {
		var key = ownerKey(ownerRoot);
		if (key == '') return;
		// State handoffs preserve the source's live selector semantics. A pause
		// lifecycle instead pairs with the script that actually closed over it.
		var selected = stateHandoff || outgoingScript == null
			? script(ownerRoot) : outgoingScript;
		if (selected == '') pendingIncoming.remove(key);
		else pendingIncoming.set(key, selected);
		if (stateHandoff && selected != '') pendingStateOwner = key;
		else if (pendingStateOwner == key) pendingStateOwner = '';
	}

	/** Owner for the incoming half of a real FlxG state switch, if its selected
		script still matches the path captured by the outgoing half. */
	public static function pendingIncomingOwner():String {
		var key = ownerKey(pendingStateOwner);
		if (key == '' || !pendingIncoming.exists(key)) return '';
		if (script(key) != pendingIncoming.get(key)) {
			pendingIncoming.remove(key);
			pendingStateOwner = '';
			return '';
		}
		return key;
	}

	public static function hasStateHandoff(ownerRoot:String):Bool
		return ownerKey(ownerRoot) != '' && ownerKey(ownerRoot) == ownerKey(pendingStateOwner);

	/** The outgoing/incoming pair keeps its selected owner while the old chart
		is gone and the destination state is being created. */
	public static function stateHandoffOwner():String
		return pendingStateOwner != '' && script(pendingStateOwner) != '' ? pendingStateOwner : '';

	/** Owner of the transition callback currently executing on this thread. */
	public static function pushExecutingTransition(ownerRoot:String):Void {
		var key = ownerKey(ownerRoot);
		if (key != '') executingTransitionOwners.push(key);
	}

	public static function popExecutingTransition(ownerRoot:String):Void {
		var key = ownerKey(ownerRoot);
		if (key == '' || executingTransitionOwners.length == 0) return;
		var last = executingTransitionOwners.length - 1;
		if (executingTransitionOwners[last] == key) {
			executingTransitionOwners.pop();
			return;
		}
		// Keep nested script execution safe if a callback tears down a scope
		// while another owner is still on the stack.
		for (index in 0...executingTransitionOwners.length)
			if (executingTransitionOwners[index] == key) {
				executingTransitionOwners.splice(index, 1);
				return;
			}
	}

	public static function executingTransitionOwner():String
		return executingTransitionOwners.length == 0 ? ''
			: executingTransitionOwners[executingTransitionOwners.length - 1];

	/** Assets requested by a running transition stay with that script's owner,
		then fall back to the live chart/session and finally a pending handoff. */
	public static function resolveStickerOwner(executingOwner:String,
		currentOwner:String, handoffOwner:String):String {
		if (ownerKey(executingOwner) != '') return executingOwner;
		if (ownerKey(currentOwner) != '') return currentOwner;
		return handoffOwner;
	}

	/** A loading wrapper is transient and will hand creation to a real game
		state; other non-music states cannot consume the transition half. */
	public static function shouldAbandonIncoming(isMusicBeatState:Bool,
		isLoadingWrapper:Bool):Bool
		return !isMusicBeatState && !isLoadingWrapper;

	/** Finish the owner lease after the incoming half. */
	public static function completeIncoming(ownerRoot:String):Void {
		var key = ownerKey(ownerRoot);
		if (key == '') return;
		pendingIncoming.remove(key);
		if (ownerKey(pendingStateOwner) == key) pendingStateOwner = '';
	}

	/** Drop an outgoing lease when its incoming half cannot be opened. */
	public static function abandonIncoming(ownerRoot:String):Void
		completeIncoming(ownerRoot);

	/** Consume once, and require the currently selected script to still match. */
	public static function consumeIncoming(ownerRoot:String):String {
		var key = ownerKey(ownerRoot);
		if (key == '' || !pendingIncoming.exists(key)) return '';
		var pending = pendingIncoming.get(key);
		pendingIncoming.remove(key);
		return script(ownerRoot) == pending ? pending : '';
	}

	/** Pause/resume uses the outgoing half's script even if a callback changed
		the selector while the pause substate was open. When no outgoing half was
		queued, keep the current selector behavior. */
	public static function consumeLifecycleResumeScript(ownerRoot:String):String {
		var key = ownerKey(ownerRoot);
		if (key == '' || !pendingIncoming.exists(key)) return script(ownerRoot);
		var incoming = pendingIncoming.get(key);
		pendingIncoming.remove(key);
		return incoming == null || incoming == '' ? script(ownerRoot) : incoming;
	}

	public static function captureStaticVariables(ownerRoot:String, scriptPath:String,
		names:Array<String>, variables:Map<String, Dynamic>):Void {
		if (names == null || variables == null) return;
		var key = moduleKey(ownerRoot, scriptPath);
		var stored = staticVariables.get(key);
		if (stored == null) stored = new Map();
		for (name in names)
			if (variables.exists(name)) stored.set(name, variables.get(name));
		staticVariables.set(key, stored);
	}

	public static function restoreStaticVariables(ownerRoot:String, scriptPath:String,
		names:Array<String>, variables:Map<String, Dynamic>):Void {
		if (names == null || variables == null) return;
		var stored = staticVariables.get(moduleKey(ownerRoot, scriptPath));
		if (stored == null) return;
		for (name in names)
			if (stored.exists(name)) variables.set(name, stored.get(name));
	}

	public static function clearOwner(ownerRoot:String):Void {
		var key = ownerKey(ownerRoot);
		if (key == '') return;
		selectedScripts.remove(key);
		pendingIncoming.remove(key);
		pendingStateTargets.remove(key);
		if (ownerKey(pendingStateOwner) == key) pendingStateOwner = '';
		var prefix = key + '\n';
		var toRemove:Array<String> = [];
		for (module in staticVariables.keys())
			if (module.startsWith(prefix)) toRemove.push(module);
		for (module in toRemove) staticVariables.remove(module);
	}
}
