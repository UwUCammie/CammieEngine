package;

import haxe.ds.ObjectMap;

/** FlxG adapter that forwards native static/instance fields except `save`,
	which is replaced with the selected owner's save facade. The native delegate
	stays in a host-side identity table and is removed with its save lifetime. */
class NightmareVisionFlxGView {
	static var nativeDelegates:ObjectMap<NightmareVisionFlxGView, Dynamic> = new ObjectMap();
	static var viewsBySave:ObjectMap<NightmareVisionSaveFacade, Array<NightmareVisionFlxGView>> = new ObjectMap();
	public final save:NightmareVisionSaveFacade;

	public function new(nativeFlxG:Dynamic, save:NightmareVisionSaveFacade) {
		if (nativeFlxG == null || save == null)
			throw '[nightmare-vision-save] FlxG view requires the native API and owner save facade';
		this.save = save;
		nativeDelegates.set(this, nativeFlxG);
		var views = viewsBySave.get(save);
		if (views == null) {
			views = [];
			viewsBySave.set(save, views);
		}
		views.push(this);
	}

	public function getField(name:String):Dynamic {
		if (name == null || name == '') return null;
		if (name == 'save') return save;
		return Reflect.getProperty(getNativeDelegate(), name);
	}

	public function setField(name:String, value:Dynamic):Dynamic {
		if (name == 'save')
			throw '[nightmare-vision-save] Refused to replace the owner-scoped FlxG.save view';
		if (name == null || name == '')
			throw '[nightmare-vision-save] Refused an invalid FlxG field';
		Reflect.setProperty(getNativeDelegate(), name, value);
		return value;
	}

	/** Remove host-side native references when the owner save facade is released. */
	public static function releaseForSave(save:NightmareVisionSaveFacade):Void {
		var views = viewsBySave.get(save);
		if (views == null) return;
		for (view in views.copy()) view.release();
		viewsBySave.remove(save);
	}

	public function release():Void {
		nativeDelegates.remove(this);
		var views = viewsBySave.get(save);
		if (views != null) {
			views.remove(this);
			if (views.length == 0) viewsBySave.remove(save);
		}
	}

	function getNativeDelegate():Dynamic {
		var nativeFlxG = nativeDelegates.get(this);
		if (nativeFlxG == null)
			throw '[nightmare-vision-save] FlxG view has been released';
		return nativeFlxG;
	}
}
