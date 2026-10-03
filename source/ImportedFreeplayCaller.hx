package;

/** Keep a directly launched imported Freeplay's caller across its ModifierState
	return, while rejecting an owner switch or a later native category launch. */
class ImportedFreeplayCaller {
	static var ownerRoot:String = '';
	static var scriptPath:String = '';
	static var returnKind:String = '';

	public static function capture(owner:String, script:String):Void {
		clear();
		if (CompatScriptManifest.destinationKey(owner) == '' || script == null
			|| StringTools.trim(script) == '') return;
		ownerRoot = owner;
		scriptPath = script;
		returnKind = 'codename-state';
	}

	/** Capture the package picker as the return target for native Freeplay. */
	public static function capturePackage(owner:String):Void {
		clear();
		if (CompatScriptManifest.destinationKey(owner) == '') return;
		ownerRoot = owner;
		returnKind = 'package-picker';
	}

	public static function keepFor(activeOwner:String, returningFromGameplay:Bool):Void {
		if (returnKind == 'package-picker') {
			// The native Freeplay fallback has no active Codename runtime owner.
			// Keep its picker return token through that menu and its chart roundtrip.
			if (ownerRoot == '' || (activeOwner != null && StringTools.trim(activeOwner) != ''
				&& CompatScriptManifest.destinationKey(activeOwner)
				!= CompatScriptManifest.destinationKey(ownerRoot))) clear();
			return;
		}
		var keep = returningFromGameplay && ownerRoot != ''
			&& CompatScriptManifest.destinationKey(activeOwner)
			== CompatScriptManifest.destinationKey(ownerRoot);
		if (!keep) clear();
	}

	/** Return only an explicitly captured imported Freeplay owner.
	 * A chart's active Codename owner is gameplay context, not a menu filter. */
	public static function ownerForFreeplay(activeOwner:String):String {
		return ownerRoot != '' && returnKind != '' ? ownerRoot : '';
	}

	public static function take(activeOwner:String):Dynamic {
		if (CompatScriptManifest.destinationKey(activeOwner) == ''
			|| CompatScriptManifest.destinationKey(activeOwner)
			!= CompatScriptManifest.destinationKey(ownerRoot) || scriptPath == '') {
			if (returnKind == 'package-picker' && ownerRoot != ''
				&& CompatScriptManifest.destinationKey(activeOwner)
				== CompatScriptManifest.destinationKey(ownerRoot)) {
				var packageRoute:Dynamic = {ownerRoot:ownerRoot, scriptPath:'', returnKind:returnKind};
				clear();
				return packageRoute;
			}
			clear();
			return null;
		}
		var result:Dynamic = {ownerRoot:ownerRoot, scriptPath:scriptPath, returnKind:returnKind};
		clear();
		return result;
	}

	public static function clear():Void {
		ownerRoot = '';
		scriptPath = '';
		returnKind = '';
	}
}
