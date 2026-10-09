package;

/** Opt-in verification through an actual native historical Character.update. */
@:access(Character)
@:access(flixel.animation.FlxAnimation)
class RuntimeSmokeLegacyCharacterLifecycle {
	static var checked:Bool = false;

	public static function verify(state:PlayState):Void {
		#if sys
		if (checked || Sys.getEnv('CAMMIE_LEGACY_CHARACTER_SMOKE') != '1') return;
		checked = true;
		var actor = state.dad;
		if (actor == null || !actor.nightmareVisionLegacyActor || !actor.animation.exists('singLEFT')
			|| !actor.animation.exists('idle')) throw 'Historical lifecycle probe requires a native source actor';
		var saved = {debug:actor.debugMode, player:actor.isPlayer, special:actor.specialAnim, anim:actor.animTimer,
			hey:actor.heyTimer, hold:actor.holdTimer, skip:actor.skipDance, voice:actor.voicelining,
			danceIdle:actor.danceIdle, danced:actor.danced, suffix:actor.idleSuffix, canPlay:actor.canPlayAnimations,
			offsetX:actor.offset.x, offsetY:actor.offset.y, name:actor.animation.name, frame:actor.animation.curAnim.curFrame, finished:actor.animation.curAnim.finished};
		var failure:Dynamic = null;
		try {
			actor.skipDance = false;actor.voicelining = false;actor.danceIdle = false;actor.idleSuffix = '';
			actor.canPlayAnimations = true;actor.isPlayer = true;actor.animTimer = 0;actor.holdTimer = 0;
			actor.playAnim('singLEFT', true);actor.animation.finish();
			actor.debugMode = true;actor.heyTimer = 0.05;actor.specialAnim = true;
			actor.update(0.1);
			if (actor.heyTimer != 0.05 || !actor.specialAnim) throw 'Debug update consumed a source special timer';
			actor.debugMode = false;actor.update(0.1);
			if (actor.heyTimer != 0 || !actor.specialAnim || actor.animation.name != 'singLEFT')
				throw 'Historical positive Hey timer fell through to same-frame special completion';
			actor.update(0.01);
			if (actor.specialAnim || actor.animation.name != 'idle') throw 'Historical special did not resume idle next frame';
			actor.playAnim('singLEFT', true);actor.isPlayer = false;
			actor.holdTimer = Conductor.stepCrochet * 0.0011 * actor.singDuration - 0.005;
			actor.update(0.01);
			if (actor.holdTimer != 0 || actor.animation.name != 'idle') throw 'Historical opponent sing duration failed';
			actor.playAnim('singLEFT', true);actor.isPlayer = true;actor.holdTimer = 20;
			actor.update(0.01);
			if (actor.holdTimer != 20 || actor.animation.name != 'singLEFT') throw 'Opponent timeout leaked into player';
			actor.animTimer = 0.005;actor.update(0.01);
			if (actor.animTimer != 0 || actor.animation.name != 'idle') throw 'Source timed animation did not resume idle';
		} catch (error:Dynamic) failure = error;
		actor.debugMode = saved.debug;actor.isPlayer = saved.player;actor.skipDance = saved.skip;
		actor.voicelining = saved.voice;actor.danceIdle = saved.danceIdle;actor.idleSuffix = saved.suffix;
		actor.animation.play(saved.name, true, false, saved.frame);actor.animation.curAnim.finished = saved.finished;
		actor.specialAnim = saved.special;actor.animTimer = saved.anim;actor.heyTimer = saved.hey;
		actor.holdTimer = saved.hold;actor.danced = saved.danced;actor.canPlayAnimations = saved.canPlay;
		actor.offset.set(saved.offsetX, saved.offsetY);
		if (failure != null) throw failure;
		@:privateAccess RuntimeSmokeHarness.emit('legacy_character_lifecycle_native_verified', {
			debugGate:true, expiryOrdering:true, opponentDuration:true, playerIsolation:true, timedIdle:true});
		#end
	}
}
