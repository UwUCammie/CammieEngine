package;

/** Identifies character references whose source API can be exposed in any Codename scope. */
interface CodenameCharacterAccess {
	public var codenameSourceId:String;
	public function codenamePlayAnim(name:String, ?force:Null<Bool>, context:Dynamic = null,
		reverse:Bool = false, frame:Int = 0):Void;
	public function codenameTryDance():Void;
}
