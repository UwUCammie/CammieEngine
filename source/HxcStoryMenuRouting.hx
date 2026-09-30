package;

import haxe.io.Path;

using StringTools;

/** Pure routing decisions for owner-scoped HXC StoryMenu modules. */
class HxcStoryMenuRouting {
	/** Keep a path-relative identity so only a same-path copy is precedence-deduped. */
	public static function moduleIdentity(relativePath:String):String {
		var clean = StringTools.replace(StringTools.trim(relativePath == null ? '' : relativePath), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0
			|| clean.indexOf('..') >= 0)
			return '';
		return Path.normalize(clean);
	}

	/** Same module identity means the same relative file in different import roots. */
	public static function sameModuleIdentity(first:String, second:String):Bool {
		var a = moduleIdentity(first);
		var b = moduleIdentity(second);
		return a != '' && a == b;
	}

	/** Decide whether a candidate wins the manifest priority tie-break. */
	public static function candidateWins(candidatePriority:Int, candidatePath:String,
		currentPriority:Int, currentPath:String):Bool {
		if (candidatePriority != currentPriority)
			return candidatePriority < currentPriority;
		if (candidatePath == null)
			return false;
		if (currentPath == null)
			return true;
		return Reflect.compare(candidatePath, currentPath) < 0;
	}

	/** HXC string equality is case-sensitive; preserve the authored level id. */
	public static function levelMatches(authoredLevelId:String, currentLevelId:String):Bool {
		return authoredLevelId != null && authoredLevelId != ''
			&& currentLevelId != null && authoredLevelId == currentLevelId;
	}

	/** Resolve a visible StoryMenu row back to its source week-list index. */
	public static function sourceWeekIndex(visibleIndex:Int, weekNums:Array<Int>):Int {
		return weekNums != null && visibleIndex >= 0 && visibleIndex < weekNums.length
			? weekNums[visibleIndex] : visibleIndex;
	}
}
