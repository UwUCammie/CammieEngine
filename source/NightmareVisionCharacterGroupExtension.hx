package;

/** NMV's CharacterGroup-only operations over the shared Psych group surface.
	The state/bank owns and destroys the cached actors; this extension only
	forwards authored operations and exposes the bank's live members. */
class NightmareVisionCharacterGroupExtension {
	final bankForRole:Void->NightmareVisionCharacterBank;
	final attachCharacter:Dynamic->Dynamic;
	final assignParentReference:Dynamic->Dynamic;
	final fallbackGroup:PsychBaseStageActorGroupCompat;
	final localMap:Map<String, Dynamic> = new Map();
	var parentOverride:Dynamic;
	var hasParentOverride:Bool = false;

	public function new(bankForRole:Void->NightmareVisionCharacterBank,
		group:PsychBaseStageActorGroupCompat, ?attachCharacter:Dynamic->Dynamic,
		?assignParentReference:Dynamic->Dynamic) {
		this.bankForRole = bankForRole;
		this.fallbackGroup = group;
		this.attachCharacter = attachCharacter;
		this.assignParentReference = assignParentReference;
	}

	/** The role is fixed by the group. The optional source-call argument is
	 * accepted for release scripts that pass the role redundantly. */
	public function addToList(name:String, ?_type:Int):Dynamic {
		var bank = bank();
		if (bank == null) throw '[nightmare-vision-character-group] addToList(' + name + ') before the role bank is initialized';
		mergeLocalMap(bank);
		return bank.addToList(name);
	}

	/** Match CharacterGroup.addChar's identity/cache behavior while delegating
	 * placement and state ownership to the owning PlayState. */
	public function addChar(character:Dynamic):Dynamic {
		if (character == null) return null;
		var result = attachCharacter == null ? fallbackGroup.add(character) : attachCharacter(character);
		var name = characterName(character);
		if (name != null) {
			localMap.set(name, character);
			var bank = bank();
			if (bank != null) bank.map.set(name, character);
		}
		return result == null ? character : result;
	}

	public function change(name:String):Dynamic {
		var bank = bank();
		if (bank == null) throw '[nightmare-vision-character-group] change(' + name + ') before the role bank is initialized';
		mergeLocalMap(bank);
		var current = bank.change(name);
		parentOverride = null;
		hasParentOverride = false;
		return current;
	}

	public function parent():Dynamic {
		if (hasParentOverride) return parentOverride;
		var bank = bank();
		return bank == null ? null : bank.parent;
	}

	public function setParent(value:Dynamic):Dynamic {
		if (assignParentReference != null) {
			var result = assignParentReference(value);
			parentOverride = result;
			hasParentOverride = true;
			return result;
		}
		parentOverride = value;
		hasParentOverride = true;
		return value;
	}

	public function map():Map<String, Dynamic> {
		var bank = bank();
		if (bank == null) return localMap;
		mergeLocalMap(bank);
		return bank.map;
	}

	public function cachedMembers():Array<Dynamic> {
		var output:Array<Dynamic> = [];
		for (member in localMap) if (member != null && !output.contains(member)) output.push(member);
		var bank = bank();
		if (bank != null && bank.map != null)
			for (member in bank.map) if (member != null && !output.contains(member)) output.push(member);
		return output;
	}

	function bank():NightmareVisionCharacterBank return bankForRole == null ? null : bankForRole();
	function mergeLocalMap(bank:NightmareVisionCharacterBank):Void
		for (name in localMap.keys()) if (!bank.map.exists(name)) bank.map.set(name, localMap.get(name));

	static function characterName(character:Dynamic):String {
		var name:Dynamic = Reflect.getProperty(character, 'requestedCharacter');
		if (name == null || Std.string(name) == '') name = Reflect.getProperty(character, 'curCharacter');
		return name == null || Std.string(name) == '' ? null : Std.string(name);
	}
}
