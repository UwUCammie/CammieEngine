package;

import flixel.FlxCamera;
import flixel.addons.transition.FlxTransitionableState;

/** Small live PlayState view used by owner-scoped substate scripts.
	Codename substates use `game` for parent-game members; they must not see the
	PauseSubState/GameOverSubstate host under that name.
*/
class CodenameModPlayStateFacade {
	final state:PlayState;

	public function new(state:PlayState) this.state = state;

	public var camHUD(get, never):FlxCamera;
	inline function get_camHUD():FlxCamera return state == null ? null : state.camHUD;
	public var camGame(get, never):FlxCamera;
	inline function get_camGame():FlxCamera return state == null ? null : state.camGame;
	public var camOther(get, never):FlxCamera;
	inline function get_camOther():FlxCamera return state == null ? null : state.camOther;

	/** The source method snapshots camera motion and suppresses both transitions.
		This fork has no matching camera-snapshot transition system, so preserve
		the restart intent by suppressing the ordinary transitions and say clearly
		which visual part cannot be reproduced.
	*/
	public function registerSmoothTransition():Void {
		FlxTransitionableState.skipNextTransOut = true;
		FlxTransitionableState.skipNextTransIn = true;
		trace('[codename-unsupported-api] game.registerSmoothTransition: camera snapshot reuse is unavailable; state transitions were skipped.');
	}

	/** The charter save-warning UI has no equivalent in this fork. */
	public function saveWarn(?closingWindow:Bool = true):Void
		trace('[codename-unsupported-api] game.saveWarn is unavailable in this fork.');
}
