package;

import openfl.system.System;

/** Explicit HScript import aliases for the legacy Flx3D API. Call from
 * CodenameImportBindings.addShared so gameplay and imported-state interpreters
 * share the same owner-aware constructors. */
class CodenameFlx3DBindings {
	public static function addShared(bindings:Map<String, Dynamic>,
		interp:CodenameScriptInterp, paths:CodenamePaths):Void {
		if (bindings == null || interp == null || paths == null)
			throw '[codename-3d] Shared binding context is incomplete';
		bindings.set('flx3d.Flx3DView', flx3d.CodenameFlx3DView);
		bindings.set('flx3d.Flx3DCamera', flx3d.CodenameFlx3DCamera);
		bindings.set('flx3d.FlxView3D', flx3d.FlxView3D);
		bindings.set('flx3d.Flx3DUtil', flx3d.CodenameFlx3DUtil.facade());
		bindings.set('openfl.system.System', systemFacade());
		#if THREE_D_SUPPORT
		bindings.set('away3d.core.base.Geometry', away3d.core.base.Geometry);
		bindings.set('away3d.cameras.lenses.PerspectiveLens', away3d.cameras.lenses.PerspectiveLens);
		#else
		bindings.set('away3d.core.base.Geometry', CodenameUnavailableApi);
		bindings.set('away3d.cameras.lenses.PerspectiveLens', CodenameUnavailableApi);
		#end
	}

	static function systemFacade():Dynamic {
		return {
			gc: function():Void System.gc(),
			totalMemoryNumber: System.totalMemoryNumber
		};
	}
}
