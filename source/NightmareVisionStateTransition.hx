package;

import flixel.FlxG;
import flixel.FlxSubState;
import flixel.FlxSprite;
import flixel.system.FlxBGSprite;
import flixel.util.FlxGradient;
import flixel.util.FlxTimer;
import flixel.tweens.FlxTween;
import flixel.util.FlxAxes;

/** Native source swipe/fade and owner-selected scripted transition execution. */
@:keep
class NightmareVisionStateTransition extends NightmareVisionMusicBeatSubstate {
	public var finishCallback:Void->Void;
	public final status:flixel.addons.transition.FlxTransitionSprite.TransitionStatus;
	final session:NightmareVisionStateSession;
	final transition:NightmareVisionModTransition;
	final incoming:Bool;
	var gradient:FlxSprite;
	var gradientFill:FlxSprite;
	var tween:FlxTween;
	var closeTimer:FlxTimer;
	var finished:Bool = false;

	public function new(session:NightmareVisionStateSession, transition:NightmareVisionModTransition,
		incoming:Bool, ?complete:Void->Void) {
		super(session.substateHost()); this.session = session; this.transition = transition; this.incoming = incoming;
		status = incoming ? OUT : IN; finishCallback = complete;
	}
	public override function create():Void {
		camera = FlxG.cameras.list[FlxG.cameras.list.length - 1];
		var selected = transition == ENGINE_DEFAULT ? NightmareVisionModTransition.SWIPE : transition;
		switch (selected) {
			case SCRIPTED(key):
				if (session.paths.resolveScript('scripts/transitions/' + key) == null) {
					trace('[nightmare-vision-transition] scripted Transition [' + key + '] not found; using source swipe.');
					selected = SWIPE;
				}
			default:
		}
		switch (selected) {
			case SCRIPTED(key):
				scriptPrefix = 'transitions'; initStateScript(key, false);
				super.create(); scriptGroup.call('onLoad', []); return;
			case FADE:
				var sprite = new FlxBGSprite(); sprite.color = 0xFF000000; add(sprite);
				sprite.alpha = incoming ? 1 : 0;
				tween = FlxTween.tween(sprite, {alpha:incoming ? 0 : 1}, incoming ? 0.8 : 0.48,
					{onComplete:function(_) dispatchFinish()});
			default:
				gradient = FlxGradient.createGradientFlxSprite(1, Math.round(camera.viewHeight),
					[0xFF000000, 0x00000000], 1, incoming ? 270 : 90);
				gradient.scale.x = camera.viewWidth + 5; gradient.scrollFactor.set();
				gradient.screenCenter(FlxAxes.X); gradient.y = -camera.viewHeight;
				gradientFill = new FlxSprite().makeGraphic(Math.ceil(camera.viewWidth + 5), Math.ceil(camera.viewHeight), 0xFF000000);
				gradientFill.screenCenter(FlxAxes.X); gradientFill.scrollFactor.set();
				add(gradientFill); add(gradient);
				tween = FlxTween.tween(gradient, {y:camera.viewHeight}, incoming ? 0.6 : 0.48,
					{onComplete:function(_) dispatchFinish()});
		}
		super.create();
	}
	public function dispatchFinish():Void {
		if (finished) return; finished = true;
		if (finishCallback != null) finishCallback();
		closeTimer = new FlxTimer().start(0, function(_) close());
	}
	public override function update(elapsed:Float):Void {
		if (gradient != null && gradientFill != null)
			gradientFill.y = incoming ? gradient.y + gradient.height : gradient.y - gradient.height;
		super.update(elapsed);
	}
	public override function destroy():Void {
		if (tween != null) tween.cancel(); if (closeTimer != null) closeTimer.cancel();
		finishCallback = null; super.destroy();
	}
}
