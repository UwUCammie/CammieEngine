package;

#if sys
import flixel.FlxG;
import flixel.FlxSprite;
import lime.app.Application;
import sys.io.File;

/**
	Opt-in native check of the main menu Import entry (`--verify-main-menu-import
	[--main-menu-capture <path stem>]`, run together with `--smoke-freeplay`).

	It opens the real MainMenuState, reports every native row's bounds, checks
	that Import sits directly under Options and every row is on screen, captures
	the menu with Import idle and then selected (moved there with real DOWN key
	events), accepts it with a real ENTER key event, and captures the importer
	screen it opens.  It then sends a real ESCAPE key event and requires the
	importer to return to a MainMenuState that still has Import selected, and
	captures that menu.  Screenshots are framebuffer reads from the hidden window.
*/
@:access(MainMenuState)
@:access(RuntimeSmokeHarness)
class RuntimeMainMenuImportProbe {
	static var phase:Int = 0;
	static var at:Float = 0;
	static var began:Float = 0;
	static var capturePending:String = null;
	static var captureHooked:Bool = false;
	static var importIndex:Int = -1;

	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.args().indexOf('--verify-main-menu-import') >= 0;

	static function check(value:Bool, message:String):Void
		if (!value) throw message;

	static function captureStem():String {
		var args = Sys.args();
		var index = args.indexOf('--main-menu-capture');
		if (index < 0 || index + 1 >= args.length) throw 'Main menu probe needs --main-menu-capture <path stem>';
		return args[index + 1];
	}

	static function rows(menu:MainMenuState):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		menu.menuItems.forEach(function(card:MenuCard) {
			result.push({id: card.ID, item: menu.optionShit[card.ID], x: Math.round(card.x), y: Math.round(card.y),
				width: card.cardWidth, height: Math.round(card.motion.height), selected: card.selected});
		});
		return result;
	}

	static function checkOnScreen(menu:MainMenuState):Void {
		menu.menuItems.forEach(function(card:MenuCard) {
			var label = menu.optionShit[card.ID];
			check(card.x >= 0 && card.x + card.cardWidth <= FlxG.width, label + ' row leaves the screen horizontally');
			check(card.y >= 0 && card.y + card.motion.height <= FlxG.height, label + ' row leaves the screen vertically');
		});
	}

	public static function tick():Void {
		if (!enabled() || RuntimeSmokeHarness.finished) return;
		try {
			var now = haxe.Timer.stamp();
			if (began == 0) began = now;
			check(now - began < 90, 'Main menu probe timed out in phase ' + phase);
			if (capturePending != null) return;
			FlxG.sound.muted = true;
			switch (phase) {
				case 0:
					if (!Std.isOfType(FlxG.state, FreeplayState)) return;
					LoadingState.loadAndSwitchState(new MainMenuState());
					phase = 1; at = 0;
				case 1:
					if (!Std.isOfType(FlxG.state, MainMenuState)) return;
					if (at == 0) at = now;
					if (now - at < 1.5) return;
					var menu:MainMenuState = cast FlxG.state;
					var options = menu.optionShit.indexOf('options');
					importIndex = menu.optionShit.indexOf('import');
					check(options >= 0 && importIndex == options + 1, 'Import is not directly beneath Options');
					check(menu.menuItems.length == menu.optionShit.length, 'A native row is missing');
					checkOnScreen(menu);
					var optionsRow = menu.menuItems.members[options];
					var importRow = menu.menuItems.members[importIndex];
					check(importRow.y > optionsRow.y, 'Import is not below Options');
					check(importRow.cardWidth == optionsRow.cardWidth, 'Import is a different size');
					if (MainMenuState.curSelected == importIndex) {
						MainMenuState.curSelected = 0;
						menu.changeItem();
					}
					RuntimeSmokeHarness.emit('main_menu_rows', {rows: rows(menu), selected: MainMenuState.curSelected,
						viewportWidth: FlxG.width, viewportHeight: FlxG.height});
					capturePending = 'unselected'; hookCapture(); phase = 2; at = now;
				case 2:
					if (now - at < 0.4) return;
					if (MainMenuState.curSelected != importIndex) {
						RuntimeSmokeHarness.simulateKey('down');
						at = now;
						return;
					}
					if (now - at < 0.9) return;
					var menu:MainMenuState = cast FlxG.state;
					var row = menu.menuItems.members[importIndex];
					check(row.selected, 'Import is not drawn as the selected card');
					checkOnScreen(menu);
					RuntimeSmokeHarness.emit('main_menu_rows', {rows: rows(menu), selected: MainMenuState.curSelected,
						viewportWidth: FlxG.width, viewportHeight: FlxG.height});
					capturePending = 'selected'; hookCapture(); phase = 3; at = now;
				case 3:
					RuntimeSmokeHarness.simulateKey('enter');
					phase = 4; at = now;
				case 4:
					if (!Std.isOfType(FlxG.state, ImportSettingsState)) return;
					if (now - at < 2.0) return;
					capturePending = 'import-screen'; hookCapture(); phase = 5; at = now;
				case 5:
					if (now - at < 0.4) return;
					RuntimeSmokeHarness.simulateKey('escape');
					phase = 6; at = now;
				case 6:
					if (!Std.isOfType(FlxG.state, MainMenuState)) {
						if (now - at > 8) throw 'Leaving the importer did not return to the main menu';
						return;
					}
					if (now - at < 2.0) return;
					var menu:MainMenuState = cast FlxG.state;
					check(MainMenuState.curSelected == importIndex, 'Import is not selected after returning from the importer');
					var row = menu.menuItems.members[importIndex];
					check(row.selected, 'Import is not drawn selected after returning');
					check(row.alive && row.exists && row.visible && row.opacity > 0.99, 'Import row is hidden after returning');
					checkOnScreen(menu);
					capturePending = 'returned'; hookCapture(); phase = 7;
				default:
			}
		} catch (error:Dynamic) {
			RuntimeSmokeHarness.fail('main-menu-import', Std.string(error));
		}
	}

	static function hookCapture():Void {
		if (captureHooked) return;
		captureHooked = true;
		Application.current.window.onRender.add(onRendered, false, -1000);
	}

	static function onRendered(context:lime.graphics.RenderContext):Void {
		if (capturePending == null || RuntimeSmokeHarness.finished) return;
		try {
			var kind = capturePending;
			var image = Application.current.window.readPixels();
			if (image == null || image.width <= 0 || image.height <= 0) throw 'Empty native main menu framebuffer';
			var path = captureStem() + '-' + kind + '.png';
			RuntimeSmokeHarness.ensureParent(path);
			File.saveBytes(path, image.encode());
			RuntimeSmokeHarness.emit('main_menu_capture', {kind: kind, path: path, width: image.width, height: image.height,
				state: Type.getClassName(Type.getClass(FlxG.state)), selected: MainMenuState.curSelected});
			capturePending = null;
			if (kind == 'returned') {
				Application.current.window.onRender.remove(onRendered);
				RuntimeSmokeHarness.emit('main_menu_import_verified', {importIndex: importIndex});
				RuntimeSmokeHarness.succeed();
			}
		} catch (error:Dynamic) {
			Application.current.window.onRender.remove(onRendered);
			RuntimeSmokeHarness.fail('main-menu-import-render', Std.string(error));
		}
	}
}
#end
