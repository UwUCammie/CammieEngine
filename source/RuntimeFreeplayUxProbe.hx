package;

import flixel.FlxG;

/** Opt-in muted native validation with private saves and an isolated tiny category. */
@:access(FreeplayState)
@:access(FreeplayBrowserRow)
@:access(RuntimeSmokeHarness)
class RuntimeFreeplayUxProbe {
	static var menu:FreeplayState;
	static var phase:Int = 0;
	static var at:Float = 0;
	static var release:Int = 0;
	static var chordRelease:Bool = false;
	static var chordChecked:Bool = false;
	static var actualAudioVolume:Float = 0;
	static var nativeChordAt:Float = 0;
	static var quickChordChecked:Bool = false;
	static var audioKeyPhase:Int = 0;
	static var savedSorting:Dynamic;
	static var savedAvailability:Dynamic;
	static var pendingCaptured:Bool = false;
	static var savedFavorite:Bool;
	static var favoriteKey:String;
	static var samples:Int = 0;
	static var largestEnvelope:Float = 0;
	public static function install(state:FreeplayState):Void {
		#if sys
		if (!RuntimeSmokeHarness.enabled() || Sys.args().indexOf('--verify-freeplay-ux') < 0 || menu != null) return;
		if (Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') == null) throw 'Freeplay UX probe requires a private save';
		menu = state; FlxG.signals.postUpdate.add(update); FlxG.signals.postDraw.add(capture);
		#end
	}
	static function check(ok:Bool, message:String):Void if (!ok) throw message;
	static function key(code:Int, down:Bool):Void {
		FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(down ? openfl.events.KeyboardEvent.KEY_DOWN : openfl.events.KeyboardEvent.KEY_UP, true, false, code, code));
		if (code == 17) recordCtrl('dispatch-' + (down ? 'down' : 'up'));
	}
	public static function recordCtrl(at:String):Void {
		if (menu == null || RuntimeSmokeHarness.finished) return;
		RuntimeSmokeHarness.emit('freeplay_ux_ctrl_trace', {at:at, phase:phase, timeSincePhase:haxe.Timer.stamp() - RuntimeFreeplayUxProbe.at,
			state:Type.getClassName(Type.getClass(FlxG.state)), subState:menu.subState == null ? '' : Type.getClassName(Type.getClass(menu.subState)),
			focus:menu.searchFocused, nativeFocus:menu.searchInput.hasFocus, used:menu.searchControlUsed,
			pressed:FlxG.keys.pressed.CONTROL, justPressed:FlxG.keys.justPressed.CONTROL, justReleased:FlxG.keys.justReleased.CONTROL,
			enabled:FlxG.keys.enabled, down:[for (key in FlxG.keys.getIsDown()) {id:(key.ID:Int), justPressed:key.justPressed}]});
	}
	static function tap(code:Int):Void { key(code, true); release = code; }
	static function next():Void { phase++; at = haxe.Timer.stamp(); }
	static function update():Void {
		if (menu == null || RuntimeSmokeHarness.finished) return;
		var observedMute = FlxG.sound.muted;
		FlxG.sound.muted = true;
		if (release != 0) { key(release, false); release = 0; }
		if (chordRelease) { key(65, false); key(17, false); chordRelease = false; }
		var dt = haxe.Timer.stamp() - at;
		try switch (phase) {
			case 0:
				if (menu.subState != null) return;
				#if sys
				if (ImportRefreshManager.browseTick().busy) return;
				#end
				check(menu.denseBrowser && menu.songs.length > 1 && menu.songs.length < 9, 'Use a tiny private category');
				check(!menu.searchFocused, 'Search must begin unfocused');
				savedSorting = UserLibrary.data().sorting(); favoriteKey = menu.libraryChartKey(0);
				savedFavorite = UserLibrary.data().isFavorite(favoriteKey);
				UserLibrary.change(function(data) { data.setFavorite(favoriteKey, true); data.setSorting('flat', 'default', 'za'); });
				menu.libraryOrderKey = ''; menu.applySearchFilter();
				var visible = menu.visibleChartRows(); var copies = 0;
				for (id in visible) if (menu.chartRows[id].song == 0) copies++;
				check(copies == 2 && StringTools.startsWith(menu.chartRows[visible[0]].key, '@favorite:'), 'Favorite must occur in both sections');
				for (card in menu.chartDisplay) if (!card.disabled)
					check(card.chartStars.length == DifficultyManager.getSupportedDiffs(menu.songs[card.presentationSong].songName).length, 'Compact ordinary card lost difficulty stars');
				FreeplayState.curSelected = 0; menu.selectedPresentationKey = menu.chartRows[0].key; menu.changeSelection(0);
				var retained = menu.selectedPresentationKey; menu.libraryOrderKey = ''; menu.applySearchFilter();
				check(menu.chartRows[menu.selectedChartRow(menu.visibleChartRows())].key == retained, 'Refresh lost regular favorite occurrence');
				UserLibrary.change(function(data) data.setSorting('flat', 'default', 'npsHigh'));
				menu.libraryOrderKey = ''; menu.applySearchFilter();
				var expected = DifficultyManager.getSupportedDiffs(menu.songs[0].songName).length;
				var pinned = 0; var ordinary = 0;
				for (id in menu.visibleChartRows()) if (menu.chartRows[id].song == 0) {
					if (StringTools.startsWith(menu.chartRows[id].key, '@favorite:')) pinned++; else ordinary++;
				}
				check(pinned == expected && ordinary == expected, 'Favorites lost named difficulty occurrences');
				for (card in menu.chartDisplay) if (!card.disabled) check(card.chartStars.length == 1, 'Expanded chart card must own its single difficulty star');
				UserLibrary.change(function(data) data.setSorting('flat', 'default', 'za'));
				savedAvailability = menu.songs[0].cachedAvailability;
				menu.songs[0].cachedAvailability = {ready:false, state:'pending', reason:'Private pending publication fixture'};
				menu.songs[0].availabilityRevision = menu.importAvailabilityRevision;
				menu.libraryOrderKey = ''; menu.applySearchFilter();
				var pendingRows = menu.visibleChartRows();
				check(menu.chartRows[pendingRows[pendingRows.length - 1]].song == 0, 'Unavailable favorite escaped bottom');
				check(!StringTools.startsWith(menu.chartRows[pendingRows[0]].key, '@favorite:'), 'Unavailable favorite pinned');
				FreeplayState.curSelected = 1; menu.selectedPresentationKey = ''; menu.changeSelection(0, true); next();
			case 1 if (dt > 0.5 && pendingCaptured):
				menu.songs[0].cachedAvailability = savedAvailability;
				menu.songs[0].availabilityRevision = -1;
				menu.libraryOrderKey = ''; menu.applySearchFilter();
				var readyRows = menu.visibleChartRows();
				check(menu.chartRows[readyRows[0]].song == 0 && StringTools.startsWith(menu.chartRows[readyRows[0]].key, '@favorite:'), 'Ready favorite did not return to pinned section');
				FreeplayState.curSelected = 0; menu.selectedPresentationKey = menu.chartRows[0].key; menu.changeSelection(0);
				tap(17); next();
			case 2 if (dt > 0.08):
				if (!menu.searchFocused || !menu.searchInput.hasFocus) recordCtrl('before-bare-focus-assert');
				check(menu.searchFocused && menu.searchInput.hasFocus, 'Bare Ctrl did not focus native search');
				if (!chordChecked) {
					actualAudioVolume = FlxG.sound.volume;
					recordCtrl('bare-focus-accepted');
					key(17, true);
					FlxG.stage.window.onKeyDown.dispatch(lime.ui.KeyCode.A, lime.ui.KeyModifier.CTRL);
					chordRelease = true; chordChecked = true; nativeChordAt = haxe.Timer.stamp(); return;
				}
				if (haxe.Timer.stamp() - nativeChordAt < 0.12) return;
				check(menu.searchFocused, 'Same-frame Ctrl+A chord exited search');
				if (!quickChordChecked) {
					// Complete the entire chord within this postUpdate callback.
					key(17, true); key(65, true); key(65, false); key(17, false);
					quickChordChecked = true; nativeChordAt = haxe.Timer.stamp(); return;
				}
				check(menu.searchFocused && menu.searchInput.hasFocus, 'Between-update Ctrl+A chord exited search');
				check(observedMute && FlxG.sound.volume == actualAudioVolume, 'Actual audio shortcut changed output while search was focused');
				if (audioKeyPhase < 3) {
					var code = [48, 187, 189][audioKeyPhase++]; tap(code); return;
				}
				check(FlxG.sound.muted && FlxG.sound.volume == actualAudioVolume, 'Search audio key released into global mute or volume handler');
				FlxG.stage.dispatchEvent(new openfl.events.TextEvent(openfl.events.TextEvent.TEXT_INPUT, true, false, '+-0 \u00e9\u65e5'));
				check(menu.searchString == '+-0 \u00e9\u65e5', 'Native search rejected punctuation or Unicode');
				check(!menu.anyVisible(), 'Unicode/symbol search collapsed to a match-all empty query');
				check(FlxG.sound.muteKeys.length == 0 && FlxG.sound.volumeUpKeys.length == 0, 'Search did not own global audio shortcuts');
				menu.searchInput.text = ''; menu.searchString = ''; menu.applySearchFilter();
				tap(17); next();
			case 3 if (dt > 0.08):
				check(!menu.searchFocused && !menu.searchInput.hasFocus, 'Ctrl did not end search');
				check(observedMute && FlxG.sound.volume == actualAudioVolume, 'Audio key release leaked after search ended');
				check(FlxG.sound.muteKeys.length > 0, 'Search failed to restore audio shortcuts');
				menu.startPreview(); next();
			case 4:
				if (menu.previewSound != null && menu.previewSound.playing) {
					for (value in menu.browserEnvelope.levels) largestEnvelope = Math.max(largestEnvelope, value);
					samples++;
				}
				if (dt > 8 && samples > 5 && largestEnvelope > 0) next();
				if (dt > 30) throw 'Muted playing PCM envelope never became nonzero';
			default:
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('freeplay-ux', Std.string(error));
	}
	static function capture():Void {
		#if sys
		if (phase == 1 && haxe.Timer.stamp() - at > 0.5 && !pendingCaptured) {
			var pendingImage = lime.app.Application.current.window.readPixels();
			if (pendingImage != null) {
				var pendingPath = RuntimeSmokeHarness.config().logPath + '.pending.png';
				RuntimeSmokeHarness.ensureParent(pendingPath); sys.io.File.saveBytes(pendingPath, pendingImage.encode());
				pendingCaptured = true; RuntimeSmokeHarness.emit('freeplay_ux_pending_frame', {screenshot:pendingPath});
			}
		}
		if (phase != 5 || RuntimeSmokeHarness.finished) return;
		try {
			var card:FreeplayBrowserRow = cast menu.songRows[FreeplayState.curSelected];
			check(card != null && card.trails.length == 6, 'Trail pool missing');
			var selected = FreeplayState.curSelected;
			check(menu.iconArray[selected] != null && menu.iconArray[selected].visible, 'Selected icon absent after empty search recovery');
			check(menu.starArray[selected] != null && menu.starArray[selected].length == DifficultyManager.getSupportedDiffs(menu.songs[selected].songName).length, 'Selected difficulty stars absent after empty search recovery');
			for (star in menu.starArray[selected]) check(star.visible, 'Selected difficulty star is hidden');
			check(!card.placeholder.visible, 'Selected card retained fallback question mark');
			for (compact in menu.chartDisplay) if (!compact.disabled) {
				check(compact.chartIcon != null && compact.chartIcon.visible && !compact.placeholder.visible, 'Compact card lost icon');
				check(compact.chartStars.length > 0, 'Compact card lost difficulty stars');
				for (star in compact.chartStars) check(star.visible, 'Compact difficulty star hidden');
			}
			for (star in card.trails) if (star.visible) {
				check(star.clipRect != null && star.clipRect.x >= 0 && star.clipRect.y >= 0, 'Trail escapes card window');
				check(star.clipRect.width <= 18 && star.clipRect.height <= 18, 'Trail clipping bounds wrong');
			}
			check(FreeplayStarTrail.opacity(1 / 3) == 0, 'Trail survives first third');
			var path = RuntimeSmokeHarness.config().logPath + '.ux.png';
			var image = lime.app.Application.current.window.readPixels();
			check(image != null, 'Missing UX framebuffer'); RuntimeSmokeHarness.ensureParent(path); sys.io.File.saveBytes(path, image.encode());
			UserLibrary.change(function(data) { data.setFavorite(favoriteKey, savedFavorite); data.setSorting(savedSorting.grouping, savedSorting.groups, savedSorting.charts); });
			RuntimeSmokeHarness.emit('freeplay_ux_verified', {duplicates:true, allDifficulties:true, pendingToReady:true, regularOccurrence:true, ctrlFocus:true, sameFrameCtrlChord:true, betweenUpdateCtrlChord:true, actualAudioKeyReleases:true, selectedArtwork:true, compactArtwork:true, punctuation:true, unicode:true, audioKeys:true, mutedPcm:true, envelope:largestEnvelope, trailPool:6, screenshot:path});
			RuntimeSmokeHarness.succeed(); phase = 5;
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('freeplay-ux-capture', Std.string(error));
		#end
	}
}
