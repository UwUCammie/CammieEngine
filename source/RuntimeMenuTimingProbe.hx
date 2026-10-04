package;

import flixel.FlxG;
import openfl.events.KeyboardEvent;

/** Opt-in muted native check of the real options input and menu-row update. */
@:access(SaveDataState)
@:access(RuntimeSmokeHarness)
class RuntimeMenuTimingProbe {
	static var installed:Bool = false;
	static var phase:Int = 0;
	static var observedSeconds:Float = 0;
	static var heldSeconds:Float = 0;
	static var firstHeldFrame:Bool = true;
	static var menu:SaveDataState;
	static var transition:Alphabet;
	static var transitionSeconds:Float = 0;
	static var offset:Float = 0;
	static var fps:Float = 0;
	static var categoryStep:Int = 0;
	static var readbacks:Map<String, Bool> = new Map();

	public static function install():Void {
		#if sys
		if (installed || !RuntimeSmokeHarness.enabled() || Sys.args().indexOf('--menu-timing-regression-probe') < 0)
			return;
		installed = true;
		FlxG.signals.postUpdate.add(observe);
		if (Sys.args().indexOf('--menu-timing-render-readback') >= 0)
			FlxG.signals.postDraw.add(captureMenu);
		#end
	}

	static function key(code:Int, down:Bool):Void {
		FlxG.stage.dispatchEvent(new KeyboardEvent(down ? KeyboardEvent.KEY_DOWN : KeyboardEvent.KEY_UP,
			true, false, code, code));
	}

	static function select(field:String, value:Float):Void {
		menu.categorySelected = OptionsCategories.names().indexOf(OptionsCategories.sectionFor(field));
		menu.openOptionCategory();
		for (i in 0...SaveDataState.optionList.length) {
			if (SaveDataState.optionList[i].intName != field) continue;
			menu.optionsSelected = i;
			menu.numberDisplays[i].value = value;
			SaveDataState.optionList[i].amount = value;
			menu.changeSelection();
			return;
		}
		RuntimeSmokeHarness.fail('menu-timing-probe', 'Missing numeric option: ' + field);
	}

	static function observe():Void {
		if (phase == 9) return;
		if (phase == 0) {
			if (!Std.isOfType(FlxG.state, FreeplayState)) return;
			observedSeconds += FlxG.elapsed;
			if (observedSeconds < 1.2) return;
			RuntimeSmokeHarness.emit('menu_fps_observation', {
				currentFPS: Main.fpsCounter.currentFPS, averageFPS: Main.fpsCounter.averageFPS,
				backendFrameRate: FlxG.stage.frameRate, muted: FlxG.sound.muted});
			phase = 1;
			LoadingState.loadAndSwitchState(new SaveDataState());
			return;
		}
		if (!Std.isOfType(FlxG.state, SaveDataState)) return;
		if (menu == null) {
			menu = cast FlxG.state;
			menu.inOptionsMenu = true;
			observedSeconds = 0;
			return;
		}
		if (phase == 1) {
			observedSeconds += FlxG.elapsed;
			if (observedSeconds < 1.2) return;
			// Exercise real menu keys, including wrapping and returning to the
			// same section, before the numeric timing checks.
			switch (categoryStep++) {
				case 0: key(38, true); return;
				case 1:
					if (menu.categorySelected != OptionsCategories.names().length - 1) {
						RuntimeSmokeHarness.fail('menu-category-probe', 'Section selection did not wrap upward.');
						return;
					}
					for (i in 0...menu.categoryRows.length) {
						var row = menu.categoryRows.members[i];
						if (!row.isMenuItem || row.targetY != i - menu.categorySelected || row.menuRowSpacing != 96) {
							RuntimeSmokeHarness.fail('menu-category-probe', 'Section rows do not use shared scrolling selection.');
							return;
						}
					}
					key(38, false); return;
				case 2: key(13, true); return;
				case 3:
					if (!menu.inOptionCategory || menu.categoryRows.visible) {
						RuntimeSmokeHarness.fail('menu-category-probe', 'Confirm did not open the selected section.');
						return;
					}
					key(13, false); return;
				case 4: key(27, true); return;
				case 5:
					if (menu.inOptionCategory || !menu.categoryRows.visible || menu.categorySelected != OptionsCategories.names().length - 1) {
						RuntimeSmokeHarness.fail('menu-category-probe', 'Back did not restore section selection.');
						return;
					}
					key(27, false); return;
				case 6: key(40, true); return;
				case 7:
					if (menu.categorySelected != 0) {
						RuntimeSmokeHarness.fail('menu-category-probe', 'Section selection did not wrap downward.');
						return;
					}
					key(40, false);
					RuntimeSmokeHarness.emit('menu_category_probe_success', {spacing: 96, muted: FlxG.sound.muted});
					return;
				default:
			}
			select('offset', 0);
			transition = new Alphabet(0, 0, '', true, false, false);
			transition.itemType = 'Vertical';
			transition.isMenuItem = true;
			transition.menuMotionRate = 2;
			transition.targetY = 1;
			menu.add(transition);
			key(17, true);
			key(39, true);
			phase = 2;
			return;
		}
		transitionSeconds += FlxG.elapsed;
		var target = 1.3 * 120 + FlxG.height * 0.5;
		var expected = target * (1 - Math.pow(0.84, transitionSeconds * 120));
		if (!Math.isFinite(transition.y) || Math.abs(transition.y - expected) > 0.05) {
			RuntimeSmokeHarness.fail('menu-timing-probe', 'Menu row did not follow elapsed time: '
				+ transition.y + ', expected ' + expected);
			return;
		}
		if (phase == 2 || phase == 4) {
			// The first update observes the press. Its elapsed interval predates
			// that event and can include creation of the options screen.
			if (firstHeldFrame) firstHeldFrame = false;
			else heldSeconds += FlxG.elapsed;
			if (heldSeconds < 0.25) return;
			var value = menu.numberDisplays[menu.optionsSelected].value;
			var step = phase == 2 ? 0.1 : 1.0;
			var initial = phase == 2 ? 0.0 : 1001.0;
			var changes = (value - initial) / step;
			var expectedChanges = 1 + Math.floor((heldSeconds + 0.000000001) * 60);
			if (Math.abs(changes - expectedChanges) > 0.0001) {
				RuntimeSmokeHarness.fail('menu-timing-probe', 'Held changes depend on render count: ' + changes
					+ ', seconds ' + heldSeconds);
				return;
			}
			if (phase == 2) offset = value; else fps = value;
			key(39, false);
			phase++;
			return;
		}
		if (phase == 3) {
			select('fpsCap', 1001);
			heldSeconds = 0;
			firstHeldFrame = true;
			key(39, true);
			phase = 4;
			return;
		}
		if (phase == 5) {
			key(17, false);
			key(16, true);
			key(39, true);
			phase = 6;
			return;
		}
		if (phase == 6) {
			if (menu.numberDisplays[menu.optionsSelected].value != fps + 20) {
				RuntimeSmokeHarness.fail('menu-timing-probe', 'Shift FPS adjustment did not add 20.');
				return;
			}
			key(39, false);
			select('offset', 1.26);
			phase = 7;
			return;
		}
		if (phase == 7) {
			key(39, true);
			phase = 8;
			return;
		}
		if (Math.abs(menu.numberDisplays[menu.optionsSelected].value - 21.3) > 0.00001) {
			RuntimeSmokeHarness.fail('menu-timing-probe', 'Shift offset adjustment did not add 20 and snap to a tenth.');
			return;
		}
		key(39, false);
		key(16, false);
		phase = 9;
		RuntimeSmokeHarness.emit('menu_timing_probe_success', {offset: offset, fpsCap: fps,
			shiftFpsCap: fps + 20, shiftOffset: menu.numberDisplays[menu.optionsSelected].value,
			heldSeconds: heldSeconds, transitionSeconds: transitionSeconds, transitionY: transition.y,
			backendFrameRate: FlxG.stage.frameRate, muted: FlxG.sound.muted});
	}

	static function captureMenu():Void {
		#if sys
		var name = phase == 0 && observedSeconds > 0.8 ? 'freeplay'
			: phase == 1 && menu != null && observedSeconds > 1 ? 'sections'
			: phase == 4 && heldSeconds > 0.2 ? 'graphics' : '';
		if (name == '' || readbacks.exists(name)) return;
		readbacks.set(name, true);
		try {
			var window = lime.app.Application.current.window;
			var image = window.readPixels();
			if (image == null) throw 'No native framebuffer.';
			var path = 'options-menu-' + name + '.png';
			sys.io.File.saveBytes(path, image.encode());
			RuntimeSmokeHarness.emit('menu_render_readback', {path: path, muted: FlxG.sound.muted,
				heading: menu == null ? null : menu.categoryHeading.text,
				headingVisible: menu != null && menu.categoryHeading.visible,
				headingX: menu == null ? null : menu.categoryHeading.x,
				headingY: menu == null ? null : menu.categoryHeading.y});
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('menu-render-readback', Std.string(error));
		#end
	}
}
