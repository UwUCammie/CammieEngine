package;

/** A synchronous owner stack used only while a Codename interpreter constructs
 * owner-bound 3D objects. Asynchronous loader callbacks re-enter the captured
 * owner explicitly through CodenameFlx3DView/CodenameFlx3DCamera. */
class CodenameFlx3DContext {
	static var ownerStack:Array<CodenamePaths> = [];

	public static function currentPaths():Null<CodenamePaths>
		return ownerStack.length == 0 ? null : ownerStack[ownerStack.length - 1];

	public static function requireOwner():CodenamePaths {
		var paths = currentPaths();
		if (paths == null)
			throw '[codename-3d] 3D objects must be constructed inside an owner-scoped Codename interpreter';
		return paths;
	}

	/** Narrow interpreter hook around HScript's `new Flx3DView()` dispatch. */
	public static function pushOwner(paths:CodenamePaths):Void {
		if (paths == null) throw '[codename-3d] Missing owner context';
		ownerStack.push(paths);
	}

	public static function popOwner(paths:CodenamePaths):Void {
		if (ownerStack.length == 0)
			throw '[codename-3d] Owner context stack underflow';
		var active = ownerStack.pop();
		if (active != paths)
			throw '[codename-3d] Owner context stack was not restored in order';
	}

	/** Restore the previous owner on both success and exception. Haxe has no
	 * finally clause, so pop explicitly along both exit paths. */
	public static function withOwner<T>(paths:CodenamePaths, action:Void->T):T {
		if (paths == null || action == null)
			throw '[codename-3d] Missing owner context';
		pushOwner(paths);
		var result:Dynamic = null;
		var error:Dynamic = null;
		var failed = false;
		try result = action() catch (caught:Dynamic) {
			failed = true;
			error = caught;
		}
		popOwner(paths);
		if (failed) throw error;
		return cast result;
	}
}
