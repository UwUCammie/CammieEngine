package;

import flixel.FlxG;
import flixel.FlxState;

/** Compatibility view for the old FlxGame `_requestedState` field.
	HaxeFlixel 6 accepts both concrete FlxState instances and lazy factories in
	`_nextState`. Imported legacy globals expect to inspect a concrete state.
	Known switch call sites can lease their target for the exact native request;
	unknown factories stay opaque and are never invoked here.
*/
class CodenameRequestedStateCompat {
	static var leasedGame:Dynamic;
	static var leasedFromState:Dynamic;
	static var leasedTarget:Dynamic;
	static var leasedRequest:Dynamic;
	static var previousRequest:Dynamic;
	static var hasLease:Bool = false;
	static var hasBoundRequest:Bool = false;
	static var leaseGeneration:Int = 0;
	static var postSwitchCleanup:Void->Void;

	/** Run a native switch while associating its concrete target with the exact
		request value Flixel records. The lease is useful if that value is a
		factory, and is ignored if the request changes before preStateSwitch.
	*/
	public static function switchToKnownTarget(target:FlxState, request:Void->Void):Void {
		if (target == null || request == null || FlxG.game == null || FlxG.state == null) {
			if (request != null) request();
			return;
		}
		beginKnownTarget(target);
		var game = leasedGame;
		try request() catch (error:Dynamic) {
			clear();
			throw error;
		}
		var requestAfterCall = Reflect.field(game, '_nextState');
		// A Codename outro can defer Flixel's assignment until its completion
		// callback. Keep the unbound lease for that callback; never guess from a
		// request which was already pending before this call.
		if (requestAfterCall != null && (requestAfterCall == target
			|| requestAfterCall != previousRequest)) bindRequest(requestAfterCall);
	}

	/** Start a concrete-target lease before a native switch call. */
	public static function beginKnownTarget(target:FlxState):Void {
		clear();
		if (target == null || FlxG.game == null || FlxG.state == null) return;
		leasedGame = FlxG.game;
		leasedFromState = FlxG.state;
		leasedTarget = target;
		previousRequest = Reflect.field(leasedGame, '_nextState');
		hasLease = true;
		installPostSwitchCleanup();
	}

	/** Bind after FlxG's known `onOutroComplete` closure has written its request. */
	public static function bindKnownTargetRequest(target:FlxState):Void {
		if (!hasLease || target != leasedTarget) return;
		if (FlxG.game != leasedGame || FlxG.state != leasedFromState) {
			clear();
			return;
		}
		var request = Reflect.field(leasedGame, '_nextState');
		if (request == null) {
			clear();
			return;
		}
		bindRequest(request);
	}

	static function bindRequest(request:Dynamic):Void {
		if (!hasLease || request == null || FlxG.game != leasedGame
			|| FlxG.state != leasedFromState) {
			clear();
			return;
		}
		leasedRequest = request;
		hasBoundRequest = true;
	}

	static function installPostSwitchCleanup():Void {
		leaseGeneration++;
		var generation = leaseGeneration;
		postSwitchCleanup = function():Void {
			if (generation == leaseGeneration) clear();
		};
		FlxG.signals.postStateSwitch.addOnce(postSwitchCleanup);
	}

	/** Read the old source-facing field without evaluating a Flixel factory. */
	public static function getRequestedState(game:Dynamic):Dynamic {
		var request = game == null ? null : Reflect.field(game, '_nextState');
		if (hasLease && hasBoundRequest && game == leasedGame && FlxG.state == leasedFromState
			&& request != null && request == leasedRequest)
			return leasedTarget;
		return request;
	}

	/** Preserve old field-assignment behavior: write the supplied value directly
		and return it. A script assignment supersedes any known-target lease.
	*/
	public static function setRequestedState(game:Dynamic, value:Dynamic):Dynamic {
		if (game != null) Reflect.setProperty(game, '_nextState', value);
		clear(game);
		return value;
	}

	/** Drop a known target when its deferred transition is cancelled. */
	public static function clearKnownTarget(target:FlxState):Void {
		if (hasLease && (target == null || target == leasedTarget)) clear();
	}

	public static function clear(?game:Dynamic):Void {
		if (game != null && hasLease && game != leasedGame) return;
		leaseGeneration++;
		if (postSwitchCleanup != null) {
			FlxG.signals.postStateSwitch.remove(postSwitchCleanup);
			postSwitchCleanup = null;
		}
		leasedGame = null;
		leasedFromState = null;
		leasedTarget = null;
		leasedRequest = null;
		previousRequest = null;
		hasLease = false;
		hasBoundRequest = false;
	}
}
