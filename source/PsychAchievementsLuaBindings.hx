package;

import hscript.Interp;

/** Registers Psych 1.0.4's Lua achievement callbacks on one translated Lua
	scope, delegating all state and persistence to the captured owner service. */
@:keep
class PsychAchievementsLuaBindings {
	public static function install(interp:Interp, service:PsychAchievements,
		report:String->Void):Void {
		if (interp == null || service == null || report == null)
			throw '[psych-achievements] Lua callbacks require an interpreter, owner service, and diagnostic callback';

		interp.variables.set('getAchievementScore', function(name:String):Float {
			if (!service.exists(name)) {
				report('getAchievementScore: Couldnt find achievement: $name');
				return -1;
			}
			return service.getScore(name);
		});
		interp.variables.set('setAchievementScore', function(name:String,
			?value:Float = 0, ?saveIfNotUnlocked:Bool = true):Float {
			if (!service.exists(name)) {
				report('setAchievementScore: Couldnt find achievement: $name');
				return -1;
			}
			return service.setScore(name, value, saveIfNotUnlocked);
		});
		interp.variables.set('addAchievementScore', function(name:String,
			?value:Float = 1, ?saveIfNotUnlocked:Bool = true):Float {
			if (!service.exists(name)) {
				report('addAchievementScore: Couldnt find achievement: $name');
				return -1;
			}
			return service.addScore(name, value, saveIfNotUnlocked);
		});
		interp.variables.set('unlockAchievement', function(name:String):Dynamic {
			if (!service.exists(name)) {
				report('unlockAchievement: Couldnt find achievement: $name');
				return null;
			}
			return service.unlock(name);
		});
		interp.variables.set('isAchievementUnlocked', function(name:String):Dynamic {
			if (!service.exists(name)) {
				report('isAchievementUnlocked: Couldnt find achievement: $name');
				return null;
			}
			return service.isUnlocked(name);
		});
		interp.variables.set('achievementExists', function(name:String):Bool {
			return service.exists(name);
		});
	}
}
