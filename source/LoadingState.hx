import flixel.text.FlxText;
import flixel.FlxState;
import flixel.FlxG;
// Shared state routing with the song loading presentation.
class LoadingState extends FlxState {
	static function switchState(target:FlxState):Void {
		var action = function():Void {
			SongLoadingScreen.stateRequestStarted();
			if (CodenameMusicBeatTransition.switchStateForCurrentOwner(target)) {
				// openSubState is deferred by Flixel. The source already owns
				// this handoff, including an authored veto, before it is visible.
				SongLoadingScreen.cancel(); return;
			}
			CodenameRequestedStateCompat.switchToKnownTarget(target,
				function():Void FlxG.switchState(target));
		};
		if (Std.isOfType(target, PlayState) || Std.isOfType(FlxG.state, PlayState)
			|| SongLoadingScreen.preparing)
			SongLoadingScreen.queue(Std.isOfType(target, PlayState) ? 'LOADING YOUR TRACK' : 'LEAVING THE STAGE',
				PlayState.SONG == null ? 'Getting ready' : PlayState.SONG.song, action);
		else action();
	}

    /** Construct states that allocate graphics only after Flixel destroys the
        previous state and clears its bitmap cache. */
    public static function loadAndSwitchStateFactory(target:()->FlxState):Void {
		PlayerSettings.player1.controls.setKeyboardScheme(Solo(4));
		var action = function():Void {
			SongLoadingScreen.stateRequestStarted();
			FlxG.switchState(target);
		};
		if (Std.isOfType(FlxG.state, PlayState))
			SongLoadingScreen.queue('LEAVING THE STAGE', PlayState.SONG == null ? 'Getting ready' : PlayState.SONG.song, action);
		else action();
    }

	/** Defer chart preparation until the loading overlay has rendered. */
	public static function prepareSongTransition(song:String, prepare:Void->Void):Bool {
		return SongLoadingScreen.queue('LOADING YOUR TRACK', song, prepare, true);
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
