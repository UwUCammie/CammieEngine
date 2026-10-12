package;

import flixel.FlxG;

/** Explicit, muted checks of the real Freeplay rows and both launch guards. */
@:access(FreeplayState)
@:access(FreeplayBrowserRow)
@:access(flixel.text.FlxText)
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
	static var previousSorting:Dynamic;

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
				FreeplayState.curSelected = row; menu.changeSelection(0, true);
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
				if (menu.denseBrowser) { verifyExpandedRows(); phase = 3; phaseAt = haxe.Timer.stamp(); return; }
				beginBlockedDifficultyCheck(supported);
			} else if (phase == 4) {
				beginBlockedDifficultyCheck(DifficultyManager.getSupportedDiffs(menu.songs[row].songName));
			} else if (phase == 1 && haxe.Timer.stamp() - phaseAt >= 0.3) {
				if (ordinaryRejections == 0) throw 'Ordinary missing-chart guard was not exercised';
				menu.changeDiff(0);
				phaseAt = haxe.Timer.stamp();
				phase = 2;
			}
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('freeplay-difficulty-probe', Std.string(error));
	}

	static function beginBlockedDifficultyCheck(supported:Array<Int>):Void {
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
	}

	static function verifyExpandedRows():Void {
		var previous = UserLibrary.data().sorting(); previousSorting = previous;
		try {
			UserLibrary.change(function(data) data.setSorting('flat', 'default', 'npsHigh'));
			menu.libraryOrderKey = ''; menu.applySearchFilter(); menu.changeSelection(0, true);
			var visible = menu.visibleChartRows(); var expected = 0;
			for (i in 0...menu.songs.length) if (menu.songMatches(i)) {
				var diffs = DifficultyManager.getSupportedDiffs(menu.songs[i].songName);
				expected += Std.int(Math.max(1, diffs.length));
			}
			if (visible.length != expected) throw 'Expanded sort did not produce one row per difficulty';
			var selectedSong = FreeplayState.curSelected;
			var selectedCard:FreeplayBrowserRow = cast menu.songRows[selectedSong];
			selectedCard.present(true, true, menu.iconArray[selectedSong] != null, false, menu.selectedCardHeight());
			if (selectedCard.title._regen || selectedCard.title.offset.x != 0 || selectedCard.title.origin.x != 0)
				throw 'Disabled title color did not flush pending regeneration before its left anchor';
			selectedCard.present(true, false, menu.iconArray[selectedSong] != null, false, menu.selectedCardHeight());
			if (selectedCard.title._regen || selectedCard.title.offset.x != 0 || selectedCard.title.origin.x != 0)
				throw 'Ready title color did not flush pending regeneration before its left anchor';
			for (change in [1, 1, -1]) {
				menu.changeDiff(change);
				var id = menu.selectedChartRow(menu.visibleChartRows());
				if (id < 0 || menu.chartRows[id].song != selectedSong
					|| menu.chartRows[id].difficulty != FreeplayState.curDifficulty)
					throw 'Difficulty change did not jump to its own presentation row';
				if (menu.chartPage.indexOf(id) < 0) throw 'Selected chart is outside its centered page';
				var expectedY = FreeplayBrowserLayout.centeredRowY(menu.chartPage.indexOf(id), menu.chartPage.indexOf(id), FlxG.height, menu.selectedCardHeight());
				if (Math.abs(menu.songRows[selectedSong].y - expectedY) > 0.01) throw 'Difficulty jump animated instead of snapping immediately';
			}
			var retained:Map<String, FreeplayBrowserRow> = [];
			for (key in menu.chartDisplay.keys()) retained.set(key, menu.chartDisplay.get(key));
			var names = [for (entry in menu.chartRows) menu.songs[entry.song].songName + ':' + entry.difficulty];
			menu.libraryOrderKey = ''; menu.applySearchFilter();
			if ([for (entry in menu.chartRows) menu.songs[entry.song].songName + ':' + entry.difficulty].join('|') != names.join('|'))
				throw 'Live ordering rebuild changed chart identities';
			for (key in retained.keys()) if (menu.chartDisplay.exists(key) && menu.chartDisplay.get(key) != retained.get(key))
				throw 'Unchanged compact chart row was recreated during refresh';
			#if sys
			menu.refreshImportAvailability(true);
			for (id in menu.chartPage) {
				var entry = menu.chartRows[id]; var compact = menu.chartDisplay.get(entry.key);
				if (compact != null && compact.disabled != FreeplaySongAvailability.rowIsDisabled(menu.rowAvailabilityDecision(entry.song)))
					throw 'Availability-only refresh left a compact chart lock stale';
			}
			if (Sys.args().indexOf('--freeplay-expanded-difficulty-probe') >= 0) {
				var apart = false; var sorted = menu.visibleChartRows();
				for (a in 0...sorted.length) for (b in (a + 2)...sorted.length) {
					var first = menu.chartRows[sorted[a]]; var second = menu.chartRows[sorted[b]];
					if (first.song == second.song && first.difficulty != second.difficulty && first.sort.metric != null
						&& second.sort.metric != null && first.sort.metric.value != second.sort.metric.value) apart = true;
				}
				if (!apart) throw 'Expanded probe fixture needs one song with difficulties separated by another rated chart';
			}
			#end
			RuntimeSmokeHarness.emit('freeplay_expanded_difficulty_verified', {song:menu.songs[selectedSong].songName, rows:visible.length, jump:true, snap:true, refresh:true, order:[for(id in menu.visibleChartRows()) {key:menu.chartRows[id].key, metric:menu.chartRows[id].sort.metric}]});
		} catch (error:Dynamic) {
			UserLibrary.change(function(data) data.setSorting(previous.grouping, previous.groups, previous.charts));
			menu.libraryOrderKey = ''; menu.applySearchFilter(); throw error;
		}

	}

	static function capture():Void {
		#if sys
		if (RuntimeSmokeHarness.finished) return;
		if (phase == 3) {
			var card:FreeplayBrowserRow = cast menu.songRows[FreeplayState.curSelected];
			if (card != null && (Math.abs(card.title.offset.x) > 0.01 || Math.abs(card.title.origin.x) > 0.01)) {
				RuntimeSmokeHarness.fail('freeplay-expanded-first-draw', 'Text regeneration moved the scaled title under its icon'); return;
			}
		}
		if (phase == 3 && haxe.Timer.stamp() - phaseAt >= 0.4) {
			try {
				var path = RuntimeSmokeHarness.config().logPath + '.expanded-' + row + '.png';
				var image = lime.app.Application.current.window.readPixels();
				if (image == null || image.width <= 0 || image.height <= 0) throw 'Empty expanded chart framebuffer';
				RuntimeSmokeHarness.ensureParent(path); sys.io.File.saveBytes(path, image.encode());
				var selected = menu.selectedChartRow(menu.visibleChartRows());
				var expectedY = FreeplayBrowserLayout.centeredRowY(menu.chartPage.indexOf(selected), menu.chartPage.indexOf(selected), FlxG.height, menu.selectedCardHeight());
				if (Math.abs(menu.songRows[FreeplayState.curSelected].y - expectedY) > 0.01) throw 'Difficulty jump drifted after draw';
				RuntimeSmokeHarness.emit('freeplay_expanded_difficulty_frame', {song:menu.songs[row].songName, screenshot:path, snapAfterDraw:true});
				UserLibrary.change(function(data) data.setSorting(previousSorting.grouping, previousSorting.groups, previousSorting.charts));
				menu.libraryOrderKey = ''; menu.applySearchFilter();
				if (menu.orderedVisibleSongs().length != menu.songs.length) throw 'Normal sort retained expanded rows';
				phase = 4;
			} catch (error:Dynamic) RuntimeSmokeHarness.fail('freeplay-expanded-difficulty-readback', Std.string(error));
			return;
		}
		if (phase != 2 || haxe.Timer.stamp() - phaseAt < 0.8) return;
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
