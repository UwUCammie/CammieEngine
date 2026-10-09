package;

import flixel.FlxSprite;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxEase;
import flixel.util.FlxColor;
using StringTools;

/** Animated source afterimages reuse the live atlas and Flixel's animation/tween services. */
class SourceCharacterGhosts {
	public static function create():Array<FlxSprite> {
		return [for (_ in 0...4) { var ghost = new FlxSprite(); ghost.visible = false; ghost.alpha = 0.6; ghost; }];
	}

	public static function play(actor:Character, id:Int, name:String, force:Bool, reversed:Bool, frame:Int):Void {
		var ghosts = actor.doubleGhosts;
		var ghost = id < 0 || id >= ghosts.length ? null : ghosts[id];
		if (ghost == null) throw '[character-ghost] Missing ghost slot ' + id;
		ghost.scale.copyFrom(actor.scale);
		ghost.frames = actor.frames;
		ghost.animation.copyFrom(actor.animation);
		ghost.setPosition(actor.x, actor.y);
		ghost.flipX = actor.flipX; ghost.flipY = actor.flipY;
		ghost.alpha = actor.alpha * 0.6;
		ghost.antialiasing = actor.antialiasing;
		ghost.visible = true;
		var colors = actor.healthColorArray;
		ghost.color = FlxColor.fromRGB(colors[0], colors[1], colors[2]);
		ghost.animation.play(name, force, reversed, frame);
		var previous = actor.ghostTweenGRP[id];
		if (previous != null) previous.cancel();
		var direction = name.substr(4);
		var delta = switch (direction) {
			case 'UP' | 'UP-alt': [0, -45];
			case 'DOWN' | 'DOWN-alt': [0, 45];
			case 'LEFT' | 'LEFT-alt': [-45, 0];
			case 'RIGHT' | 'RIGHT-alt': [45, 0];
			default: throw '[character-ghost] Unsupported animation direction ' + direction;
		};
		actor.ghostTweenGRP[id] = FlxTween.tween(ghost, {alpha:0, x:actor.x + delta[0], y:actor.y + delta[1]}, 0.75, {
			ease:FlxEase.linear,
			onComplete:function(tween) {
				ghost.visible = false;
				// The ONESHOT manager removes and destroys it after this callback.
				actor.ghostTweenGRP[id] = null;
			}
		});
		var offsets = actor.animOffsets.get(name);
		if (offsets != null) ghost.offset.set(offsets[0], offsets[1]);
		else ghost.offset.set(0, 0);
	}

	public static function destroy(ghosts:Array<FlxSprite>, tweens:Array<FlxTween>):Void {
		for (tween in tweens) if (tween != null) {tween.cancel(); tween.destroy();}
		for (ghost in ghosts) if (ghost != null) ghost.destroy();
		tweens.resize(0); ghosts.resize(0);
	}
}
