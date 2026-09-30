package;

/** HXC constructor surface for health icons that are configured after creation. */
class HxcHealthIconAdapter extends HealthIcon {
	public function new(char:String = 'bf', isPlayer:Bool = false, ?isnormal:Bool = false,
		?loadAsync:Bool = false, ?ownerSong:String) {
		super(char, isPlayer, isnormal, loadAsync, ownerSong, true);
	}
}
