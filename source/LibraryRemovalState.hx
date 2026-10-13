package;

import flixel.FlxG;
import flixel.FlxSprite;

/** Neutral host management state, created after the prior Freeplay teardown. */
class LibraryRemovalState extends MusicBeatState {
	var owner:String;
	var displayTitle:String;
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
		confirmation.closeCallback = function() LoadingState.loadAndSwitchState(new FreeplayState());
		openSubState(confirmation);
	}

	override function update(elapsed:Float):Void {
		#if sys
		ImportRefreshManager.browseTick();
		#end
		super.update(elapsed);
	}
}
