package;

using StringTools;

/** Historical state-owned caches over shared native actor, icon, bar and script services. */
@:access(PlayState)
class NightmareVisionLegacyCharacterChanges {
	public static function preload(state:PlayState, name:String, type:Int):Void {
		if (type < 0 || type > 2 || (type == 2 && (state.gf == null || state.gf == state.nightmareVisionHiddenGFPlaceholder))) return;
		if (cache(state,type).exists(name)) return;
		var actor = state.constructNightmareVisionRole(name,type);
		if(type==2) actor.scrollFactor.set(0.95,0.95);
		// Constructors may replace a public cache. Select it again before insertion.
		cache(state,type).set(name,actor);
		state.nightmareVisionCharacterGroup(type).add(actor);
		state.startHistoricalCharacterPos(actor,type==1);
		actor.alpha=0.00001;
		state.loadNightmareVisionCharacter(actor);
	}
	static function cache(state:PlayState,type:Int):Map<String,Character> {
		return type==0 ? state.boyfriendMap : type==1 ? state.dadMap : state.gfMap;
	}
	/** The three source role blocks were the same steps; only the icon side,
	 * the dad-as-GF visibility rule and the published script names differ. */
	public static function change(state:PlayState, name:String, charType:Int){
		if (charType < 0 || charType > 2 || (charType == 2 && (state.gf == null || state.gf == state.nightmareVisionHiddenGFPlaceholder))) {
			state.reloadHistoricalHealthBarColors();
			return;
		}
		if (actor(state, charType).curCharacter != name) {
			var oldChar = actor(state, charType);
			var shiftFocus:Bool = state.focusedChar == oldChar;
			if (!cache(state, charType).exists(name)) {
				state.addNightmareVisionCharacterToList(name, charType);
			}
			// Read the role again: building the actor can run scripts that replace it.
			var wasGf:Bool = charType == 1 && actor(state, charType).curCharacter.startsWith('gf');
			var lastAlpha:Float = actor(state, charType).alpha;
			actor(state, charType).alpha = 0.00001;
			assign(state, charType, cache(state, charType).get(name));
			if (charType == 1) {
				var visibleGf = state.gf != null && state.gf != state.nightmareVisionHiddenGFPlaceholder;
				if (!state.dad.curCharacter.startsWith('gf')) {
					if (wasGf && visibleGf) state.gf.visible = true;
				} else if (visibleGf) state.gf.visible = false;
			}
			actor(state, charType).alpha = lastAlpha;
			if (shiftFocus) state.focusedChar = actor(state, charType);
			if (charType != 2) state.changeHistoricalCharacterIcon(charType == 0, actor(state, charType).healthIcon);
			for (field in state.playFields.members) {
				if (field.owner == oldChar) field.owner = actor(state, charType);
			}
		}
		var scripts = state.legacyScriptRegistry();
		switch (charType) {
			case 0:
				state.setHistoricalCharacterLua('boyfriendName', state.boyfriend.curCharacter);
				scripts.setOnScripts('boyfriend', state.boyfriend);
				scripts.setOnScripts('boyfriendGroup', state.boyfriendGroup);
				scripts.setOnScripts('bfGhost', state.bfGhost);
			case 1:
				state.setHistoricalCharacterLua('dadName', state.dad.curCharacter);
				scripts.setOnScripts('dad', state.dad);
				scripts.setOnScripts('dadGroup', state.dadGroup);
				// The source publishes dadGhost as the dad group.
				scripts.setOnScripts('dadGhost', state.dadGroup);
			default:
				state.setHistoricalCharacterLua('gfName', state.gf.curCharacter);
				scripts.setOnScripts('gf', state.gf);
				scripts.setOnScripts('gfGroup', state.gfGroup);
		}
		state.reloadHistoricalHealthBarColors();
	}

	static function actor(state:PlayState, type:Int):Character {
		return type == 0 ? state.boyfriend : type == 1 ? state.dad : state.gf;
	}

	static function assign(state:PlayState, type:Int, value:Character):Void {
		if (type == 0) state.boyfriend = value;
		else if (type == 1) state.dad = value;
		else state.gf = value;
	}
}
