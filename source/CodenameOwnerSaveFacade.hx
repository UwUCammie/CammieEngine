package;

/** The source-facing subset of FlxG.save that can safely cross an owner
	boundary. `data` is a field-routing object, never the native save record. */
class CodenameOwnerSaveFacade {
	public final data:CodenameOwnerSaveData;

	public function new(ownerRoot:String) {
		data = new CodenameOwnerSaveData(ownerRoot);
	}

	public function flush():Void data.flush();
}
