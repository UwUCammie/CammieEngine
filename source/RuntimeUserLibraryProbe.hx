package;

import flixel.FlxG;

/** Opt-in verification on an isolated smoke save and private desktop. */
@:access(FreeplayState)
@:access(UserLibrary)
@:access(RuntimeSmokeHarness)
class RuntimeUserLibraryProbe {
	public static var active(default, null):Bool = false;
	static var phase:Int = 0;
	static var at:Float = 0;
	static var phaseFrames:Int = 0;
	static var key:String;
	static var original:Dynamic;
	static var captureName:String = '';
	static var captureFrames:Int = 0;
	static var afterCaptureKey:Int = 0;
	static var menu:FreeplayState;

	public static function install():Void {
		#if sys
		if (!RuntimeSmokeHarness.enabled() || Sys.args().indexOf('--verify-user-library') < 0) return;
		active = true;
		FlxG.signals.postUpdate.add(update);
		FlxG.signals.postDraw.add(capture);
		#end
	}
	static function press(code:Int, down:Bool):Void {
		FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(down ? openfl.events.KeyboardEvent.KEY_DOWN
			: openfl.events.KeyboardEvent.KEY_UP, true, false, code, code));
	}
	static function check(value:Bool, message:String):Void if (!value) throw message;
	static function update():Void {
		if (!active || RuntimeSmokeHarness.finished || captureName != '') return;
		FlxG.sound.muted = true;
		try {
			if (menu == null) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) return;
				menu = cast FlxG.state;
				UserLibrary.data();
				original = Reflect.field(UserLibrary.storage.data, 'library');
			}
			if (++phaseFrames < 3 || haxe.Timer.stamp() - at < 0.2) return;
			check(FlxG.state == menu, 'Library action left Freeplay at phase ' + phase + ': ' + Type.getClassName(Type.getClass(FlxG.state)));
			RuntimeSmokeHarness.emit('user_library_step', {phase:phase, popup:menu.subState != null});
			switch (phase) {
				case 0:
					var row = 0;
					while (row < menu.songs.length && menu.libraryChartKey(row) == '') row++;
					check(row < menu.songs.length, 'No installed chart in fixture');
					FreeplayState.curSelected = row; menu.changeSelection(0, true);
					key = menu.libraryChartKey(row);
					check(UserLibrary.change(function(data) data.setFavorite(key, false)), UserLibrary.error);
					captureName = 'before';
				case 1: press(9, true);
				case 2:
					press(9, false); check(Std.isOfType(menu.subState, LibraryActionsSubState), 'Tab did not open actions');
					captureName = 'actions'; afterCaptureKey = 13;
				case 3:
					press(13, false); check(UserLibrary.data().isFavorite(key), 'Accept did not favorite'); press(27, true);
				case 4:
					press(27, false); check(menu.subState == null, 'Back did not close actions');
					UserLibrary.current = null;
					check(UserLibrary.data().isFavorite(key), 'Favorite did not persist after reopening storage');
					var subtitle = menu.sourceRows[FreeplayState.curSelected];
					check(subtitle != null && subtitle.text.indexOf('[FAVORITE]') >= 0, 'Missing favorite marker');
					captureName = 'favorite'; afterCaptureKey = 9;
				case 5: press(9, false); press(40, true);
				case 6: press(40, false); press(13, true);
				case 7:
					press(13, false); check(FreeplayState.favoritesOnly && menu.anyVisible(), 'Favorites filter failed');
					captureName = 'filtered'; afterCaptureKey = 9;
				case 8: press(9, false); press(13, true);
				case 9:
					press(13, false); check(!UserLibrary.data().isFavorite(key), 'Unfavorite failed'); press(27, true);
				case 10:
					press(27, false); check(!menu.anyVisible(), 'Empty favorites retained stale rows');
					check(menu.diffText.text == 'NO MATCHING FAVORITES', 'Empty favorites status missing');
					check(!menu.scoreText.visible && (menu.infoPanel == null || !menu.infoPanel.visible), 'Stale score details in empty view');
					captureName = 'empty'; afterCaptureKey = 13;
				case 11: press(13, false); press(9, true);
				case 12: press(9, false); press(40, true);
				case 13: press(40, false); press(13, true);
				case 14:
					press(13, false); check(!FreeplayState.favoritesOnly && menu.anyVisible(), 'Restoring all songs failed');
					restore();
					RuntimeSmokeHarness.emit('user_library_verified', {persisted:true, filter:true, emptyView:true, noAccidentalLaunch:true});
					RuntimeSmokeHarness.succeed();
			}
			phase++; phaseFrames = 0; at = haxe.Timer.stamp();
		} catch (error:Dynamic) {
			restore();
			RuntimeSmokeHarness.fail('user-library-probe', Std.string(error));
		}
	}
	static function restore():Void {
		if (UserLibrary.storage != null) {
			Reflect.setField(UserLibrary.storage.data, 'library', original);
			UserLibrary.storage.flush();
			UserLibrary.current = null;
		}
	}
	static function capture():Void {
		#if sys
		if (captureName == '' || ++captureFrames < 2) return;
		captureFrames = 0;
		var name = captureName; captureName = '';
		var path = RuntimeSmokeHarness.config().logPath + '.library-' + name + '.png';
		try {
			var image = lime.app.Application.current.window.readPixels();
			if (image == null) throw 'Empty library framebuffer';
			RuntimeSmokeHarness.ensureParent(path);
			sys.io.File.saveBytes(path, image.encode());
			if (afterCaptureKey != 0) { press(afterCaptureKey, true); afterCaptureKey = 0; }
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('user-library-capture', Std.string(error));
		#end
	}
}
