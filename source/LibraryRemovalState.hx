package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;

/** Neutral host management state, created after the prior Freeplay teardown. */
class LibraryRemovalState extends MusicBeatState {
	var owner:String;
	var displayTitle:String;
	var leaving:Bool = false;
	var forced:Bool = false;
	var leavingFor:Float = 0;
	var bareFor:Float = 0;
	public function new(owner:String, displayTitle:String = '') {
		super(); this.owner = owner; this.displayTitle = displayTitle;
	}
	override function create():Void {
		super.create();
		// Flixel destroys the departed Freeplay before this create call. Its
		// owned script resources and module leases must be disposed there first.
		ImportedMenuEntry.release();
		add(new FlxSprite().makeGraphic(FlxG.width,FlxG.height,0xFF101522));
		var confirmation = new LibraryRemovalSubState(owner,null,displayTitle);
		confirmation.closeCallback = leave;
		openSubState(confirmation);
	}

	/** Back to Freeplay. Building it can take seconds while import work runs, so
		the screen says so instead of showing a bare backdrop meanwhile. */
	function leave():Void {
		if (leaving) return;
		leaving = true;
		var note = new FlxText(0, FlxG.height / 2 - 14, FlxG.width, 'Returning to Freeplay...', 28);
		note.setFormat('assets/fonts/vcr.ttf', 28, 0xFFFFF4DC, CENTER); add(note);
		LoadingState.loadAndSwitchState(new FreeplayState());
	}

	/** A check, recovery or removal is running. Its screen is never abandoned by the safety exits below. */
	function removalRunning():Bool {
		#if sys
		return ImportRemovalManager.poll().busy;
		#else
		return false;
		#end
	}

	override function update(elapsed:Float):Void {
		#if sys
		ImportRefreshManager.browseTick();
		#end
		super.update(elapsed);
		if (leaving) {
			// Still here, with nothing else showing, while frames keep running: the requested switch never started.
			leavingFor += elapsed;
			if (!forced && leavingFor > 4 && subState == null && !removalRunning()) { forced = true; FlxG.switchState(new FreeplayState()); }
		} else if (subState == null) {
			// The popup is the only thing this state shows. Without it, leave.
			bareFor += elapsed;
			if (bareFor > 1.5 && !removalRunning()) leave();
		} else bareFor = 0;
	}
}
