package flx3d;

/** Reflectable facade for HScript, whose static class reflection differs from
 * compiled Haxe calls. */
class CodenameFlx3DUtil {
	public static function facade():Dynamic {
		return {
			is3DAvailable: function():Bool return is3DAvailable(),
			getUsed3D: function():Int return getUsed3D(),
			getTotal3D: function():Int return getTotal3D(),
			dispose: function(value:Dynamic):Dynamic return dispose(value)
		};
	}

	static function is3DAvailable():Bool {
		#if THREE_D_SUPPORT
		return Flx3DUtil.is3DAvailable();
		#else
		return false;
		#end
	}

	static function getUsed3D():Int {
		#if THREE_D_SUPPORT
		return Flx3DUtil.getUsed3D();
		#else
		return 0;
		#end
	}

	static function getTotal3D():Int {
		#if THREE_D_SUPPORT
		return Flx3DUtil.getTotal3D();
		#else
		return 0;
		#end
	}

	static function dispose(value:Dynamic):Dynamic {
		#if THREE_D_SUPPORT
		if (value != null) (cast value:away3d.library.assets.IAsset).dispose();
		#end
		return null;
	}
}
