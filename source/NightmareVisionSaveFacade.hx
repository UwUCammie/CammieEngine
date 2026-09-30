package;

/** Owner-scoped FlxG.save surface for Nightmare Vision scripts. */
class NightmareVisionSaveFacade {
	public final data:NightmareVisionSaveData;
	var released:Bool = false;

	public function new(ownerRoot:String, storage:Dynamic) {
		data = new NightmareVisionSaveData(ownerRoot, storage);
	}

	public function flush():Void {
		if (released) throw '[nightmare-vision-save] This save facade has been released';
		data.flush();
	}

	public function release():Void {
		if (released) return;
		released = true;
		NightmareVisionFlxGView.releaseForSave(this);
		data.release();
	}
}
