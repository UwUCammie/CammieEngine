package;

import flixel.FlxG;

/** Explicit, muted checks of the real Freeplay rows and both launch guards. */
@:access(FreeplayState)
@:access(RuntimeSmokeHarness)
class RuntimeFreeplayDifficultyProbe {
	static var installed:Bool = false;
	static var menu:FreeplayState;
	static var row:Int = 0;
	static var phase:Int = 0;
	static var phaseAt:Float = 0;
	static var checks:Int = 0;
	static var blockedDifficulty:Int = -1;
	static var ordinaryRejections:Int = 0;

	public static function ordinaryRejectedSelection(song:String, difficulty:Int):Void {
		if (installed && menu != null && phase == 1 && menu.songs[row].songName == song
			&& blockedDifficulty == difficulty) ordinaryRejections++;
	}

	public static function install():Void {
		#if sys
		if (installed || !RuntimeSmokeHarness.enabled() || !RuntimeSmokeHarness.config().freeplay
			|| Sys.args().indexOf('--freeplay-difficulty-regression-probe') < 0) return;
		installed = true;
		FlxG.signals.postUpdate.add(observe);
		FlxG.signals.postDraw.add(capture);
		#end
	}

	static function observe():Void {
		if (RuntimeSmokeHarness.finished) return;
		try {
			if (menu == null) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) return;
				menu = cast FlxG.state;
				if (menu.songs.length == 0 || menu.songs.length > 8)
					throw 'Use a private category with one to eight rows';
			}
			if (FlxG.state != menu) throw 'Unavailable difficulty left Freeplay';
			#if sys
			if (ImportRefreshManager.browseTick().busy) return;
			#end
			if (phase == 0) {
				menu.changeSelection(row - FreeplayState.curSelected);
				menu.buildIconFor(row);
				var song = menu.songs[row].songName;
				var supported = DifficultyManager.getSupportedDiffs(song);
				for (change in [0, 1, 1, 1, -1, -1, -1, 2, -2, 4, -4]) {
					menu.changeDiff(change);
					if (supported.length > 0 && supported.indexOf(FreeplayState.curDifficulty) < 0)
						throw 'Navigation selected a missing difficulty for ' + song;
					if (supported.length == 0 && menu.diffText.text != 'UNAVAILABLE')
						throw 'Empty difficulty list was offered as playable';
					checks++;
				}
				var stars = menu.starArray[row];
				if (stars == null || stars.length != supported.length) throw 'Rank-star count differs from support';
				for (i in 0...supported.length)
					if (stars[i].diff != supported[i]) throw 'Rank-star difficulty differs from support';
				blockedDifficulty = -1;
				for (i in 0...DifficultyManager.getDifficultyNames().length)
					if (supported.indexOf(i) < 0) { blockedDifficulty = i; break; }
				if (blockedDifficulty < 0) throw 'Private category needs an unavailable difficulty';
				FreeplayState.curDifficulty = blockedDifficulty;
				if (menu.hxcLaunchCurrentSelection()) throw 'HXC launched a missing chart';
				ordinaryRejections = 0;
				phaseAt = haxe.Timer.stamp();
				phase = 1;
				RuntimeSmokeHarness.simulateAccept();
			} else if (phase == 1 && haxe.Timer.stamp() - phaseAt >= 0.3) {
				if (ordinaryRejections == 0) throw 'Ordinary missing-chart guard was not exercised';
				menu.changeDiff(0);
				phaseAt = haxe.Timer.stamp();
				phase = 2;
			}
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('freeplay-difficulty-probe', Std.string(error));
	}

	static function capture():Void {
		#if sys
		if (RuntimeSmokeHarness.finished || phase != 2 || haxe.Timer.stamp() - phaseAt < 0.8) return;
		try {
			var path = RuntimeSmokeHarness.config().logPath + '.difficulty-' + row + '.png';
			var image = lime.app.Application.current.window.readPixels();
			if (image == null || image.width <= 0 || image.height <= 0) throw 'Empty Freeplay framebuffer';
			RuntimeSmokeHarness.ensureParent(path);
			sys.io.File.saveBytes(path, image.encode());
			var song = menu.songs[row].songName;
			RuntimeSmokeHarness.emit('freeplay_difficulty_verified', {
				song:song, supported:DifficultyManager.getSupportedDiffs(song),
				stars:[for (star in menu.starArray[row]) star.diff],
				blockedDifficulty:blockedDifficulty, ordinaryLaunchBlocked:true,
				ordinaryRejections:ordinaryRejections,
				hxcLaunchBlocked:true, screenshot:path
			});
			row++;
			phase = 0;
			if (row == menu.songs.length) {
				RuntimeSmokeHarness.emit('freeplay_difficulty_probe_complete', {rows:row, navigationChecks:checks});
				RuntimeSmokeHarness.succeed();
			}
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('freeplay-difficulty-readback', Std.string(error));
		#end
	}
}
