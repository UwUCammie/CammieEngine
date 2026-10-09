package;

import flixel.math.FlxPoint;

/** Native character offsets shared by state-owned and group-owned NV caches. */
class NightmareVisionCharacterPlacement {
	public static function apply(actor:Character,gfCheck:Bool,gfPosition:FlxPoint):Void {
		if(gfCheck && StringTools.startsWith(actor.curCharacter,'gf')) {
			actor.setPosition(gfPosition==null?0:gfPosition.x,gfPosition==null?0:gfPosition.y);
			actor.scrollFactor.set(0.95,0.95);actor.danceEveryNumBeats=2;
		}
		if(actor.positionArray==null) throw '[nightmare-vision-character-group] Missing startPos positionArray';
		actor.x+=actor.positionArray[0];actor.y+=actor.positionArray[1];
	}
}
