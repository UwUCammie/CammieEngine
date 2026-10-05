package;

/** Explicit native regression for source editor/test-play transitions. */
@:access(PlayState)
@:access(ChartingState)
class RuntimeSourceChartingProbe {
	static var requested:Null<Bool> = null;
	static var phase:Int = 0;
	static var enteredAt:Float = 0;
	static var songFolder:String = '';
	static var ownerRoot:String = '';
	static var playlist:String = '';

	static function enabled():Bool {
		if (requested == null) {
			requested = false;
			#if sys
			for (argument in Sys.args()) if (argument == '--source-charting-probe') requested = true;
			#end
		}
		return requested && RuntimeSmokeHarness.enabled();
	}

	static function check(condition:Bool, message:String):Void {
		if (condition) return;
		RuntimeSmokeHarness.markStep('source-charting-probe:failed ' + message);
		#if sys
		Sys.exit(1);
		#end
	}

	static function advance(next:Int):Void {
		phase = next;
		enteredAt = haxe.Timer.stamp();
		RuntimeSmokeHarness.markStep('source-charting-probe:phase=' + next);
	}

	public static function updateGameplay(play:PlayState):Void {
		if (!enabled() || flixel.FlxG.state != play) return;
		if (phase == 0) {
			ownerRoot = PlayState.psychChartingOwnerRoot();
			check(ownerRoot != '', 'requires selected Psych owner');
			songFolder = Song.storageFolder(PlayState.SONG);
			playlist = PlayState.storyPlaylist == null ? '' : PlayState.storyPlaylist.join('\u0000');
			check(!PlayState.chartingMode, 'initial charting flag leaked');
			advance(1);
			play.openChartEditor();
		} else if (phase == 2) {
			check(PlayState.chartingMode && PlayState.psychChartingOwnerRoot() == ownerRoot,
				'editor test-play lost live owner flag');
			check(Song.storageFolder(PlayState.SONG) == songFolder, 'test-play changed chart identity');
			check(play.compatGetPropertyFromClass('states.PlayState', 'chartingMode') == true,
				'class reflection lost direct flag');
			advance(3);
			play.endSong();
		} else if (phase == 3 && haxe.Timer.stamp() - enteredAt > 8) {
			check(false, 'song-end did not return to editor');
		}
	}

	public static function updateEditor(editor:ChartingState):Void {
		if (!enabled() || flixel.FlxG.state != editor) return;
		if (phase == 1) {
			check(PlayState.chartingMode && PlayState.psychChartingOwnerRoot() == ownerRoot,
				'editor entry lost source context');
			check(Song.storageFolder(PlayState.SONG) == songFolder, 'editor entry changed chart identity');
			advance(2);
			editor.beginTestPlay(false);
		} else if (phase == 3) {
			check(PlayState.chartingMode, 'song-end editor lost live flag');
			check((PlayState.storyPlaylist == null ? '' : PlayState.storyPlaylist.join('\u0000')) == playlist,
				'editor return mutated story progression');
			advance(4);
			check(editor.exitPsychChartEditor(), 'explicit editor exit rejected');
		}
	}

	public static function updateFreeplay():Void {
		if (!enabled() || phase != 4) return;
		check(!PsychOwnerChartingMode.get(ownerRoot) && !PlayState.chartingMode,
			'editor exit leaked charting context');
		check(Song.storageFolder(PlayState.SONG) == songFolder, 'menu handoff changed selected chart');
		RuntimeSmokeHarness.markStep('source-charting-probe:completed editor-test-play-editor-menu');
		phase = 5;
		#if sys
		Sys.exit(0);
		#end
	}
}
