package;

#if sys
import flixel.FlxG;
import flixel.text.FlxText;

/**
	Opens the neutral mod removal state for one installed owner while the
	import refresh keeps running, then logs what is on screen.

	`--smoke-removal-state <owner>` (for example assets/imported_mods/name)
	opens it from Freeplay after `--smoke-removal-state-after-ms <ms>` (default
	1000). It logs the state, the popup chain and every visible text every half
	second, and ends once a removal review is showing, or fails when the popup is
	missing, empty or has no choice. `--smoke-removal-state-back` then presses
	Back and requires Freeplay to return; `--smoke-removal-state-back-ms <ms>`
	presses Back that long after the screen opens, whatever the import work is
	doing, and requires Freeplay to return. `--smoke-removal-state-via-menu` opens
	it the way a player does (the song's Library actions, then its removal
	entry), `--smoke-removal-state-timeout-ms <ms>` bounds the wait and
	`--smoke-removal-state-shots` saves a framebuffer PNG whenever the popup's
	heading changes. Nothing is ever confirmed or removed.
**/
@:access(RuntimeSmokeHarness)
@:access(LibraryMenuSubState)
@:access(FreeplayState)
class RuntimeRemovalStateProbe {
	static var owner:String = '';
	static var afterMs:Float = 1000;
	static var timeoutMs:Float = 180000;
	static var back:Bool = false;
	static var viaMenu:Bool = false;
	static var backAfterMs:Float = -1;
	static var lastKey:String = '';
	static var lastBack:Float = 0;
	static var shots:Bool = false;
	static var shotCount:Int = 0;
	static var shotHeading:String = '-';
	static var parsed:Bool = false;
	static var phase:Int = 0;
	static var beganAt:Float = 0;
	static var openedAt:Float = 0;
	static var lastLog:Float = 0;
	static var blankSince:Float = -1;

	static function argument(name:String):Null<String> {
		var args = Sys.args();
		var index = args.indexOf(name);
		return index >= 0 && index + 1 < args.length ? args[index + 1] : null;
	}

	public static function enabled():Bool {
		if (!RuntimeSmokeHarness.enabled()) return false;
		if (!parsed) {
			parsed = true;
			var value = argument('--smoke-removal-state');
			owner = value == null ? '' : StringTools.trim(value);
			var delay = Std.parseFloat(argument('--smoke-removal-state-after-ms'));
			if (Math.isFinite(delay) && delay >= 0) afterMs = delay;
			var limit = Std.parseFloat(argument('--smoke-removal-state-timeout-ms'));
			if (Math.isFinite(limit) && limit > 0) timeoutMs = limit;
			back = Sys.args().indexOf('--smoke-removal-state-back') >= 0;
			viaMenu = Sys.args().indexOf('--smoke-removal-state-via-menu') >= 0;
			shots = Sys.args().indexOf('--smoke-removal-state-shots') >= 0;
			var backDelay = Std.parseFloat(argument('--smoke-removal-state-back-ms'));
			if (Math.isFinite(backDelay) && backDelay >= 0) backAfterMs = backDelay;
		}
		return owner != '';
	}

	static function popup():Null<LibraryMenuSubState> {
		var state:flixel.FlxState = FlxG.state;
		while (state != null && state.subState != null) state = state.subState;
		return Std.isOfType(state, LibraryMenuSubState) ? cast state : null;
	}

	/** Every non-empty visible text of the popup chain, as the player would read it. */
	static function visibleTexts(group:flixel.group.FlxGroup):Array<String> {
		var result:Array<String> = [];
		for (member in group.members) {
			var text = Std.downcast(member, FlxText);
			if (text != null && text.visible && text.alive && text.exists && text.alpha > 0 && StringTools.trim(text.text) != '')
				result.push(StringTools.trim(text.text).split('\n').join(' / '));
		}
		return result;
	}

	public static function tick():Void {
		if (RuntimeSmokeHarness.finished) return;
		FlxG.sound.muted = true;
		var now = Sys.time();
		try {
			if (phase == 0) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) return;
				if (beganAt == 0) beganAt = now;
				if (now - beganAt < afterMs / 1000) return;
				var refresh = ImportRefreshManager.browseTick();
				RuntimeSmokeHarness.emit('removal_state_opening', {owner: owner, refreshBusy: refresh.busy, refreshLabel: refresh.label});
				if (viaMenu) {
					// The real route: the song's Library actions popup, then its removal entry.
					var menu:FreeplayState = cast FlxG.state;
					var index = -1;
					for (i in 0...menu.songs.length) if (menu.libraryOwner(i) == owner) { index = i; break; }
					if (index < 0) throw 'No Freeplay song belongs to ' + owner;
					FreeplayState.curSelected = index; menu.changeSelection(0, false);
					menu.openLibraryActions(); openedAt = now; phase = 10; return;
				}
				var title = argument('--smoke-removal-state-title');
				LoadingState.loadAndSwitchState(new LibraryRemovalState(owner, title == null ? '' : title));
				openedAt = now; phase = 1; return;
			}
			if (phase == 10) {
				var actions = popup();
				if (actions == null || !Std.isOfType(actions, LibraryActionsSubState)) return;
				var entry = -1;
				for (i in 0...actions.actions.length) if (StringTools.startsWith(actions.actions[i].label, 'Remove installed mod')) entry = i;
				if (entry < 0) throw 'Library actions has no removal entry';
				actions.actions[entry].run(); openedAt = now; phase = 1; return;
			}
			if (now - openedAt > timeoutMs / 1000) throw 'Removal screen never reached a review';
			var menu = popup();
			var refresh = ImportRefreshManager.browseTick();
			var removal = ImportRemovalManager.poll();
			// With the popup gone, the state's own text (the return notice) is what the player reads.
			var texts = menu != null ? visibleTexts(menu) : Std.isOfType(FlxG.state, LibraryRemovalState) ? visibleTexts(FlxG.state) : [];
			var choices = menu == null ? 0 : menu.actions.length;
			if (phase >= 1 && Std.isOfType(FlxG.state, LibraryRemovalState)) {
				// The state is up; from here a missing, empty or choiceless popup for
				// more than a couple of seconds is the blank screen.
				var blank = texts.length == 0 || (menu != null && choices == 0);
				if (blank) { if (blankSince < 0) blankSince = now; } else blankSince = -1;
				if (blankSince >= 0 && now - blankSince > 3)
					throw 'Blank removal screen: popup=' + (menu == null ? 'none' : Type.getClassName(Type.getClass(menu))) + ' choices=' + choices + ' texts=' + texts.length;
			}
			var shown = {
					state: Type.getClassName(Type.getClass(FlxG.state)),
					popup: menu == null ? 'none' : Type.getClassName(Type.getClass(menu)),
					heading: menu == null || menu.heading == null ? '' : menu.heading.text,
					choices: menu == null ? [] : [for (action in menu.actions) action.label],
					texts: texts
				};
			var key = haxe.Json.stringify(shown) + removal.phase + removal.busy + refresh.busy;
			var headline = menu != null && menu.heading != null ? menu.heading.text : texts.length > 0 ? texts[0] : null;
			if (shots && headline != null && headline != shotHeading && shotCount < 8) {
				// Framebuffer of what the player sees whenever the popup's heading changes.
				shotHeading = headline;
				var image = lime.app.Application.current.window.readPixels();
				if (image != null) sys.io.File.saveBytes(RuntimeSmokeHarness.config().logPath + '.removal' + (shotCount++) + '.png', image.encode());
			}
			if (key != lastKey && now - lastLog >= .5) {
				lastKey = key; lastLog = now;
				RuntimeSmokeHarness.emit('removal_state_snapshot', {
					state: Type.getClassName(Type.getClass(FlxG.state)),
					popup: menu == null ? 'none' : Type.getClassName(Type.getClass(menu)),
					heading: menu == null || menu.heading == null ? '' : menu.heading.text,
					choices: menu == null ? [] : [for (action in menu.actions) action.label],
					texts: texts,
					refreshBusy: refresh.busy, refreshLabel: refresh.label, refreshFraction: refresh.fraction,
					removalPhase: removal.phase, removalBusy: removal.busy
				});
			}
			if (phase == 1 && backAfterMs >= 0 && now - openedAt >= backAfterMs / 1000 && menu != null) {
				RuntimeSmokeHarness.emit('removal_state_back', {heading: menu.heading.text, refreshBusy: refresh.busy});
				lastBack = now; menu.backAction(); phase = 2; openedAt = now; timeoutMs = Math.min(timeoutMs, 30000); return;
			}
			if (phase == 1) {
				if (menu == null || !Std.isOfType(menu, LibraryRemovalSubState) || refresh.busy) return;
				if (removal.phase != 'preview' && removal.phase != 'blocked') return;
				if (removal.busy) return;
				RuntimeSmokeHarness.emit('removal_state_review', {phase: removal.phase, choices: [for (action in menu.actions) action.label], texts: texts});
				if (!back) { RuntimeSmokeHarness.succeed(); return; }
				menu.backAction(); phase = 2; return;
			}
			if (phase == 2) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) {
					// A cancelled check leaves a Return choice behind; press Back again, as a player would.
					if (menu != null && choices > 0 && now - lastBack >= 1) { lastBack = now; RuntimeSmokeHarness.emit('removal_state_back', {heading: menu.heading.text, refreshBusy: refresh.busy}); menu.backAction(); }
					if (backAfterMs >= 0 && now - openedAt > 15) throw 'Back did not return to Freeplay: state=' + Type.getClassName(Type.getClass(FlxG.state)) + ' popup=' + (menu == null ? 'none' : Type.getClassName(Type.getClass(menu)));
					return;
				}
				RuntimeSmokeHarness.emit('removal_state_returned', {state: 'FreeplayState'});
				RuntimeSmokeHarness.succeed();
			}
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('removal-state', Std.string(error));
	}
}
#end
