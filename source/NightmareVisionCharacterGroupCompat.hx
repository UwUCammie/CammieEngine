package;

/** NMV group facade adds its CharacterGroup API without widening Psych's
	shared FlxSpriteGroup compatibility class. */
class NightmareVisionCharacterGroupCompat extends PsychBaseStageActorGroupCompat {
	final characterGroup:NightmareVisionCharacterGroupExtension;
	var groupType:Int;
	var checkGF:Bool;

	public function new(stageHost:Dynamic, role:String,
		bankForRole:Void->NightmareVisionCharacterBank,
		?attachCharacter:Dynamic->Dynamic,
		?assignParentReference:Dynamic->Dynamic) {
		super(stageHost, role);
		characterGroup = new NightmareVisionCharacterGroupExtension(bankForRole, this,
			attachCharacter, assignParentReference);
		groupType = role == 'bf' ? 0 : role == 'dad' ? 1 : 2;
		checkGF = role == 'dad';
	}

	public override function additionalMembers():Array<Dynamic> return characterGroup.cachedMembers();
	public var parent(get, set):Dynamic;
	function get_parent():Dynamic {
		var value = characterGroup.parent();
		return value == null ? actor() : value;
	}
	function set_parent(value:Dynamic):Dynamic return characterGroup.setParent(value);
	public var map(get, never):Map<String, Dynamic>;
	function get_map():Map<String, Dynamic> return characterGroup.map();
	public var type(get, set):Int;
	function get_type():Int return groupType;
	function set_type(value:Int):Int return groupType = value;
	public var gfCheck(get, set):Bool;
	function get_gfCheck():Bool return checkGF;
	function set_gfCheck(value:Bool):Bool return checkGF = value;
	public function change(name:String):Dynamic return characterGroup.change(name);
	public function addToList(name:String, ?type:Int):Dynamic return characterGroup.addToList(name, type);
	public function addChar(character:Dynamic):Dynamic return characterGroup.addChar(character);
}
