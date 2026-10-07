package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.effects.FlxFlicker;
import flixel.tweens.FlxTween;
import flixel.util.FlxTimer;
import flixel.util.FlxAxes;

/** Donor flashing-choice flow, with preferences stored in the captured owner. */
@:keep
class NightmareVisionFlashingState extends NightmareVisionMusicBeatState {
	final session:NightmareVisionStateSession;
	var warnText:FlxText;
	var waitTimer:FlxTimer;
	var fade:FlxTween;
	public function new(session:NightmareVisionStateSession) {super(session.stateHost()); this.session = session;}
	public override function create():Void {
		super.create();
		add(new FlxSprite().makeGraphic(FlxG.width, FlxG.height, 0xFF000000));
		warnText = new FlxText(0, 0, FlxG.width, 'Hey, watch out!\n\nThis Mod contains some flashing lights!\n\nPress ENTER to disable them now or go to Options Menu.\n\nPress ESCAPE to ignore this message.\n\nYou\'ve been warned!', 32);
		warnText.setFormat(session.paths.DEFAULT_FONT, 32, 0xFFFFFFFF, CENTER);
		warnText.screenCenter(FlxAxes.Y); add(warnText);
	}
	public override function update(elapsed:Float):Void {
		if (!session.flashingLeftState && (controls.ACCEPT || controls.BACK)) {
			session.flashingLeftState = true; session.setTransSkip();
			var back:Bool = controls.BACK;
			session.prefs.view.flashing = back; session.prefs.flush();
			var save = new CodenameOwnerSaveData(session.paths.root);
			save.setField('flashing', back); save.flush();
			FlxG.sound.play(session.paths.sound(back ? 'cancelMenu' : 'confirmMenu'));
			if (back) fade = FlxTween.tween(warnText, {alpha:0}, 1, {onComplete:function(_) goTitle()});
			else FlxFlicker.flicker(warnText, 1, 0.1, false, true, function(_) {
				waitTimer = new FlxTimer().start(0.5, function(_) goTitle());
			});
		}
		super.update(elapsed);
	}
	function goTitle():Void session.switchState(session.createStateFactory('TitleState'));
	public override function destroy():Void {
		if (waitTimer != null) waitTimer.cancel();
		if (fade != null) fade.cancel();
		super.destroy();
	}
}
