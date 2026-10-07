package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxEase;
import flixel.util.FlxAxes;

/** The source fallback screen retains the selected owner's assets and callback. */
@:keep
class NightmareVisionFallbackState extends NightmareVisionMusicBeatState {
	final warningMessage:String;
	final continueCallback:Void->Void;
	final session:NightmareVisionStateSession;
	var errorTween:FlxTween;
	public function new(message:String, next:Void->Void, session:NightmareVisionStateSession) {
		super(session.stateHost()); warningMessage = message; continueCallback = next; this.session = session;
	}
	public override function create():Void {
		var bg = new FlxSprite().loadGraphic(session.paths.image('uhoh'));
		bg.setGraphicSize(FlxG.width, FlxG.height); bg.updateHitbox(); add(bg);
		var error = new FlxText(0, 0, 0, 'ERROR', 46);
		error.setFormat(session.paths.DEFAULT_FONT, 46, 0xFFFF0000, LEFT, OUTLINE, 0xFF000000);
		error.screenCenter(FlxAxes.X); error.y = 25; add(error);
		errorTween = FlxTween.tween(error, {y:error.y + 45}, 2, {ease:FlxEase.sineInOut, type:PINGPONG});
		var text = new FlxText(25, 0, FlxG.width - 50, warningMessage, 32);
		text.setFormat(session.paths.DEFAULT_FONT, 32, 0xFFFFFFFF, CENTER, OUTLINE, 0xFF000000);
		add(text); text.screenCenter(FlxAxes.Y);
		var confirm = new FlxText(0, FlxG.height - 25 - 32, FlxG.width, 'Press Confirm to continue.', 32);
		confirm.setFormat(session.paths.DEFAULT_FONT, 32, 0xFFFFFFFF, CENTER, OUTLINE, 0xFF000000); add(confirm);
		super.create();
	}
	public override function update(elapsed:Float):Void {
		super.update(elapsed);
		if (controls.ACCEPT) {persistentUpdate = false; continueCallback();}
	}
	public override function destroy():Void {if (errorTween != null) errorTween.cancel(); super.destroy();}
}
