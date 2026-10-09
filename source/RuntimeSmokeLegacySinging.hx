package;

import flixel.FlxSprite;
import flixel.tweens.FlxTween;

/** Opt-in real atlas, animation-controller, tween and draw integration check. */
@:access(flixel.tweens.FlxTween)
@:access(PlayState)
class RuntimeSmokeLegacySinging {
	static var prepared:Bool = false;
	static var actor:Character;
	static var savedGhosts:Array<FlxSprite>;
	static var savedTweens:Array<FlxTween>;
	static var selected:String;
	static var startX:Float;
	static var startY:Float;

	public static function prepare(state:PlayState):Void {
		#if sys
		if (prepared || Sys.getEnv('CAMMIE_LEGACY_SINGING_SMOKE') != '1') return;
		prepared = true;
		actor = state.dad;
		if (actor == null || actor.frames == null || !actor.nightmareVisionLegacyActor)
			throw 'Historical ghost probe requires an actual source actor atlas';
		selected = 'singLEFT';
		if (!actor.animation.exists(selected)) throw 'Historical ghost probe requires singLEFT';
		savedGhosts = actor.doubleGhosts;savedTweens = actor.ghostTweenGRP;
		actor.doubleGhosts = SourceCharacterGhosts.create();actor.ghostTweenGRP = [];
		startX = actor.x;startY = actor.y;
		var originalAnimation = actor.animation.name;
		actor.playGhostAnim(0, selected, true);
		var ghost = actor.doubleGhosts[0];
		if (ghost.frames != actor.frames || ghost.animation == actor.animation || ghost.animation.name != selected
			|| actor.animation.name != originalAnimation || ghost.shader != null)
			throw 'Historical ghost did not preserve atlas/controller ownership';
		actor.ghostTweenGRP[0].update(0.375);
		if (Math.abs(ghost.x - startX + 22.5) > 0.001 || Math.abs(ghost.y - startY) > 0.001
			|| Math.abs(ghost.alpha - actor.alpha * 0.3) > 0.001)
			throw 'Historical ghost half-time trajectory mismatch';
		var grouped = 0;
		for (side in state.noteRows) for (row in side) if (row != null) for (note in row)
			if (note != null) grouped++;
		if (grouped == 0) throw 'Historical source note rows were not generated';
		@:privateAccess RuntimeSmokeHarness.emit('legacy_singing_native_prepared', {groupedHeads:grouped,sharedAtlas:true,independentAnimation:true,halfTime:true});
		#end
	}

	public static function verify():Void {
		#if sys
		if (Sys.getEnv('CAMMIE_LEGACY_SINGING_SMOKE') != '1') return;
		if (!prepared || actor == null) throw 'Historical ghost was not prepared before drawing';
		var ghost = actor.doubleGhosts[0];
		var tween = actor.ghostTweenGRP[0];
		if (ghost == null || !ghost.visible || tween == null) throw 'Historical ghost missing during native draw';
		tween.update(0.375);tween.finish();
		if (ghost.visible || actor.ghostTweenGRP[0] != null || tween.manager != null)
			throw 'Historical ghost completion retained its sprite or tween';
		SourceCharacterGhosts.destroy(actor.doubleGhosts, actor.ghostTweenGRP);
		actor.doubleGhosts = savedGhosts;actor.ghostTweenGRP = savedTweens;
		if (actor.graphic == null || actor.graphic.bitmap == null) throw 'Ghost teardown destroyed the shared actor atlas';
		@:privateAccess RuntimeSmokeHarness.emit('legacy_singing_native_verified', {renderedGhost:true,tweenCompletion:true,sharedAtlasSurvives:true,ownerStateRestored:true});
		actor = null;savedGhosts = null;savedTweens = null;
		#end
	}
}
