package;

import flixel.FlxG;

/** Two fresh native processes exercise category UI against a private smoke save. */
@:access(FreeplayState)
@:access(UserLibrary)
@:access(RuntimeSmokeHarness)
@:access(LibraryMenuSubState)
@:access(LibraryNameSubState)
class RuntimeLibraryCategoryProbe {
	public static var active(default, null):Bool = false;
	static var reader:Bool;
	static var phase:Int = 0;
	static var at:Float = 0;
	static var frames:Int = 0;
	static var held:Int = 0;
	static var menu:FreeplayState;
	static var context:Dynamic;
	static var original:Dynamic;
	static var backup:String = 'tmp/library-category-backup.json';
	static var captureName:String = '';
	static var captureFrames:Int = 0;
	static var id:String;
	static var owner:String;
	static var key:String;
	static var memberIndex:Int;

	public static function install():Void {
		#if sys
		if (!RuntimeSmokeHarness.enabled() || Sys.args().indexOf('--verify-library-categories') < 0) return;
		if (Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') == null) throw 'Category probe requires an isolated smoke save';
		reader = Sys.args().indexOf('--library-category-read') >= 0;
		active = true; FlxG.signals.postUpdate.add(update); FlxG.signals.postDraw.add(capture);
		#end
	}
	static function check(value:Bool, message:String):Void if (!value) throw message;
	static function event(code:Int, down:Bool, charCode:Int = 0):Void {
		FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(down ? openfl.events.KeyboardEvent.KEY_DOWN
			: openfl.events.KeyboardEvent.KEY_UP, true, false, charCode, code));
	}
	static function press(code:Int):Void { event(code, true); held = code; }
	static function popup():flixel.FlxSubState {
		var result = menu.subState;
		while (result != null && result.subState != null) result = result.subState;
		return result;
	}
	static function choose(index:Int, expected:Class<Dynamic>):Void {
		check(Std.isOfType(popup(), expected), 'Unexpected popup at phase ' + phase + ': ' + (popup() == null ? 'none' : Type.getClassName(Type.getClass(popup()))));
		var state:LibraryMenuSubState = cast popup();
		check(index >= 0 && index < state.actions.length, 'Missing action');
		state.selected = index; state.render(); press(13);
	}
	static function typeName(value:String):Void {
		check(Std.isOfType(popup(), LibraryNameSubState), 'Missing name editor');
		var state:LibraryNameSubState = cast popup();
		while (state.input.text.length > 0) { event(8, true); event(8, false); }
		for (i in 0...value.length) {
			var code = value.charCodeAt(i); var keyCode = value.charAt(i).toUpperCase().charCodeAt(0);
			event(keyCode, true, code); event(keyCode, false, code);
		}
		check(state.input.text == value, 'Text entry changed the name');
		captureName = 'name';
	}
	static function restore():Void {
		if (UserLibrary.storage == null) return;
		Reflect.setField(UserLibrary.storage.data, 'library', original);
		UserLibrary.storage.flush(); UserLibrary.current = null;
	}
	static function update():Void {
		#if sys
		if (!active || RuntimeSmokeHarness.finished) return;
		FlxG.sound.muted = true;
		if (held != 0) { event(held, false); held = 0; }
		if (captureName != '' || ++frames < 3 || haxe.Timer.stamp() - at < 0.25) return;
		try {
			if (menu == null) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) return;
				menu = cast FlxG.state; UserLibrary.data();
				if (reader) {
					context = haxe.Json.parse(sys.io.File.getContent(backup));
					original = context.original; id = context.id; owner = context.owner; key = context.key;
				} else {
					original = Reflect.field(UserLibrary.storage.data, 'library');
					Reflect.setField(UserLibrary.storage.data, 'library', null); UserLibrary.storage.flush(); UserLibrary.current = null;
					FreeplayState.categoryFilters = []; FreeplayState.favoritesOnly = false;
				}
			}
			check(FlxG.state == menu, 'Category action left Freeplay');
			RuntimeSmokeHarness.emit('library_category_step', {phase:phase, reader:reader});
			if (reader) readStep(); else writeStep();
			phase++; frames = 0; at = haxe.Timer.stamp();
		} catch (error:Dynamic) { restore(); RuntimeSmokeHarness.fail('library-category-probe', Std.string(error)); }
		#end
	}
	static function writeStep():Void {
		#if sys
		switch (phase) {
			case 0:
				var row = 0;
				while (row < menu.songs.length && (menu.libraryOwner(row) == '' || menu.libraryChartKey(row) == '')) row++;
				check(row < menu.songs.length, 'No imported chart in fixture');
				FreeplayState.curSelected = row; menu.changeSelection(0, true);
				owner = menu.libraryOwner(row); key = menu.libraryChartKey(row);
				var receiptPath = 'assets/data/' + menu.songs[row].songName.toLowerCase() + '/importProvenance.json';
				context = {receiptPath:receiptPath, receipt:sys.io.File.getContent(receiptPath)};
				check(UserLibrary.change(function(data) data.setFavorite(key, true)), UserLibrary.error);
				press(9);
			case 1: choose(2, LibraryActionsSubState);
			case 2: choose(0, LibraryCategoriesSubState);
			case 3: typeName('Private category');
			case 4: press(13);
			case 5:
				check(UserLibrary.data().categoryList().length == 1, 'Category creation failed');
				id = UserLibrary.data().categoryList()[0].id; choose(2, LibraryCategoriesSubState);
			case 6: choose(1, LibraryCategoriesSubState);
			case 7:
				check(UserLibrary.data().hasMod(id, owner), 'Selected mod membership failed'); choose(3, LibraryCategoriesSubState);
			case 8: typeName('Renamed category');
			case 9: press(13);
			case 10:
				check(UserLibrary.data().categoryList()[0].name == 'Renamed category', 'Rename failed'); choose(2, LibraryCategoriesSubState);
			case 11:
				var state:LibraryMenuSubState = cast popup(); memberIndex = -1;
				for (i in 0...state.actions.length) if (StringTools.startsWith(state.actions[i].label, '[x]')) memberIndex = i;
				check(memberIndex >= 0, 'Membership list missing selected mod');
				captureName = 'members';
			case 12: choose(memberIndex, LibraryCategoriesSubState);
			case 13:
				check(!UserLibrary.data().hasMod(id, owner), 'Removing membership failed'); choose(memberIndex, LibraryCategoriesSubState);
			case 14:
				check(UserLibrary.data().hasMod(id, owner), 'Restoring membership failed'); press(27);
			case 15: choose(0, LibraryCategoriesSubState);
			case 16: check(FreeplayState.categoryFilters.indexOf(id) >= 0, 'Category filter callback failed'); press(27);
			case 17: press(27);
			case 18: press(27);
			case 19:
				check(menu.subState == null && menu.anyVisible(), 'Filtered view empty or still covered');
				for (i in 0...menu.songs.length) if (menu.songMatches(i)) check(UserLibraryData.ownerKey(menu.libraryOwner(i)) == UserLibraryData.ownerKey(owner), 'Filter leaked another mod');
				captureName = 'filtered';
			case 20:
				Reflect.setField(context, 'original', original); Reflect.setField(context, 'id', id);
				Reflect.setField(context, 'owner', owner); Reflect.setField(context, 'key', key);
				sys.io.File.saveContent(backup, haxe.Json.stringify(context));
				RuntimeSmokeHarness.emit('library_category_written', {membership:true, renamed:true, filter:true}); RuntimeSmokeHarness.succeed();
		}
		#end
	}
	static function readStep():Void {
		switch (phase) {
			case 0:
				check(UserLibrary.data().categoryList().length == 1 && UserLibrary.data().categoryList()[0].name == 'Renamed category', 'Fresh process lost category');
				check(UserLibrary.data().hasMod(id, owner) && UserLibrary.data().isFavorite(key), 'Fresh process lost membership/favorite'); press(9);
			case 1: choose(2, LibraryActionsSubState);
			case 2: captureName = 'restarted';
			case 3: choose(2, LibraryCategoriesSubState);
			case 4: choose(4, LibraryCategoriesSubState);
			case 5: captureName = 'delete-confirmation';
			case 6: choose(0, LibraryCategoriesSubState);
			case 7:
				check(UserLibrary.data().categoryList().length == 1, 'Cancel deleted category'); choose(4, LibraryCategoriesSubState);
			case 8: choose(1, LibraryCategoriesSubState);
			case 9:
				check(UserLibrary.data().categoryList().length == 0 && UserLibrary.data().isFavorite(key), 'Category delete removed favorite');
				#if sys
				check(sys.io.File.getContent(context.receiptPath) == context.receipt, 'Category delete changed import receipt');
				#end
				restore(); RuntimeSmokeHarness.emit('library_category_verified', {freshProcess:true, deletion:true, cancellation:true, favoritePreserved:true}); RuntimeSmokeHarness.succeed();
		}
	}
	static function capture():Void {
		#if sys
		if (captureName == '' || ++captureFrames < 3 || haxe.Timer.stamp() - at < 0.35) return;
		captureFrames = 0; var name = captureName; captureName = '';
		try {
			var image = lime.app.Application.current.window.readPixels();
			if (image == null) throw 'Empty category framebuffer';
			sys.io.File.saveBytes(RuntimeSmokeHarness.config().logPath + '.category-' + name + '.png', image.encode());
		} catch (error:Dynamic) { restore(); RuntimeSmokeHarness.fail('library-category-capture', Std.string(error)); }
		#end
	}
}
