package;

import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;

/** Opt-in, once-per-second native smoke observations; never changes gameplay. */
class RuntimeSmokeNVEffects {
	public static function snapshot(state:PlayState):Dynamic {
		var fields = @:privateAccess state.nightmareVisionFields;
		return {songPosition:Conductor.songPosition, fields:fields == null ? [] : [for (field in fields) if (field != null) {
			id:field.ID, skin:field._skin == null ? null : field._skin.name,
			texture:field._skin == null ? null : field._skin.noteTexture,
			notes:field.notes.length,
			layerAttached:state.members.indexOf(field.splashLayer) >= 0,
			taps:group(cast field.grpNoteSplashes), sustains:group(cast field.grpSusSplashes)
		}]};
	}
	static function group(pool:FlxTypedGroup<FlxSprite>):Dynamic {
		if (pool == null) return null;
		var alive=0, missing=0, finished=0;
		var examples:Array<Dynamic>=[];
		for (sprite in pool.members) if (sprite != null && sprite.alive) {
			alive++;
			var anim=sprite.animation.curAnim;
			if (anim == null) missing++;
			else if (anim.finished) finished++;
			if (examples.length < 2) examples.push({active:sprite.active, exists:sprite.exists,
				graphic:sprite.graphic == null ? null : sprite.graphic.key,
				animation:anim == null ? null : anim.name, frame:anim == null ? -1 : anim.curFrame,
				frames:anim == null ? 0 : anim.numFrames, fps:anim == null ? 0 : anim.frameRate,
				x:sprite.x,y:sprite.y,offsetX:sprite.offset.x,offsetY:sprite.offset.y});
		}
		return {slots:pool.length,alive:alive,missingAnimation:missing,finished:finished,active:pool.active,examples:examples};
	}
}
