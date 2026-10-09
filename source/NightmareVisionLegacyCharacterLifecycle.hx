package;

using StringTools;

/** Historical source decisions around the shared native animation update. */
class NightmareVisionLegacyCharacterLifecycle {
	public static function beforeUpdate(actor:Character, elapsed:Float, stepCrochet:Float):Void {
		if (actor.debugMode || actor.animation == null || actor.animation.curAnim == null) return;
		if (actor.animTimer > 0) {
			actor.animTimer -= elapsed;
			if (actor.animTimer <= 0) {
				actor.animTimer = 0;
				actor.dance();
			}
		}
		if (actor.heyTimer > 0) {
			actor.heyTimer -= elapsed;
			if (actor.heyTimer <= 0) {
				if (actor.specialAnim && (actor.animation.curAnim.name == 'hey' || actor.animation.curAnim.name == 'cheer')) {
					actor.specialAnim = false;
					actor.dance();
				}
				actor.heyTimer = 0;
			}
		} else if (actor.specialAnim && actor.animation.curAnim.finished) {
			actor.specialAnim = false;
			actor.dance();
		}
		if (!actor.isPlayer) {
			if (actor.animation.curAnim.name.startsWith('sing')) actor.holdTimer += elapsed;
			if (actor.holdTimer >= stepCrochet * 0.0011 * actor.singDuration) {
				actor.dance();
				actor.holdTimer = 0;
			}
		}
		if (actor.animation.curAnim.finished && actor.animation.getByName(actor.animation.curAnim.name + '-loop') != null)
			actor.playAnim(actor.animation.curAnim.name + '-loop');
	}

	public static function afterUpdate(actor:Character):Void {
		if (actor.debugMode || actor.animation == null || actor.animation.curAnim == null) return;
		var name = actor.animation.curAnim.name;
		if (name.startsWith('hold') && name.endsWith('Start') && actor.animation.curAnim.finished) {
			var nextName = name.substring(0, name.length - 5);
			var singName = 'sing' + name.substring(3, name.length - 5);
			actor.playAnim(actor.animation.getByName(nextName) != null ? nextName : singName, true);
		}
	}
}
