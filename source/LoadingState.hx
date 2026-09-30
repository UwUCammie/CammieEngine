import flixel.text.FlxText;
import flixel.FlxState;
import flixel.FlxG;
// lol
// doesn't actually load anything except fixing menus
class LoadingState extends FlxState {
	static function switchState(target:FlxState):Void {
		if (CodenameMusicBeatTransition.switchStateForCurrentOwner(target)) return;
		CodenameRequestedStateCompat.switchToKnownTarget(target,
			function():Void FlxG.switchState(target));
	}

    /** Construct states that allocate graphics only after Flixel destroys the
        previous state and clears its bitmap cache. */
    public static function loadAndSwitchStateFactory(target:()->FlxState):Void {
		PlayerSettings.player1.controls.setKeyboardScheme(Solo(4));
		FlxG.switchState(target);
    }

    public static function loadAndSwitchState(target:FlxState) {

        PlayerSettings.player1.controls.setKeyboardScheme(Solo(4));
        if ((target is ChartingState)) {
			switchState(new LoadingState());
        } else {
			switchState(target);
        }
        
    }
    override function create() {
        FlxG.switchState(new ChartingState());
    }
}
