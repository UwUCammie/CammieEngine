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
	public static function change(state:PlayState, name:String, charType:Int){
		switch(charType) {
			case 0:
				if(state.boyfriend.curCharacter != name) {
					var shiftFocus:Bool = state.focusedChar==state.boyfriend;
					var oldChar = state.boyfriend;
					if(!state.boyfriendMap.exists(name)) {
						state.addNightmareVisionCharacterToList(name, charType);
					}

					var lastAlpha:Float = state.boyfriend.alpha;
					state.boyfriend.alpha = 0.00001;
					state.boyfriend = state.boyfriendMap.get(name);
					state.boyfriend.alpha = lastAlpha;
					if(shiftFocus)state.focusedChar=state.boyfriend;
					state.changeHistoricalCharacterIcon(true, state.boyfriend.healthIcon);
					for(field in state.playFields.members){
						if(field.owner==oldChar)field.owner=state.boyfriend;
					}
				}
				state.setHistoricalCharacterLua('boyfriendName', state.boyfriend.curCharacter);
				state.legacyScriptRegistry().setOnScripts('boyfriend', state.boyfriend);
				state.legacyScriptRegistry().setOnScripts('boyfriendGroup', state.boyfriendGroup);
				state.legacyScriptRegistry().setOnScripts('bfGhost', state.bfGhost);

			case 1:
				if(state.dad.curCharacter != name) {
					var shiftFocus:Bool = state.focusedChar==state.dad;
					var oldChar = state.dad;
					if(!state.dadMap.exists(name)) {
						state.addNightmareVisionCharacterToList(name, charType);
					}

					var wasGf:Bool = state.dad.curCharacter.startsWith('gf');
					var lastAlpha:Float = state.dad.alpha;
					state.dad.alpha = 0.00001;
					state.dad = state.dadMap.get(name);
					if(!state.dad.curCharacter.startsWith('gf')) {
						if(wasGf && state.gf != null && state.gf != state.nightmareVisionHiddenGFPlaceholder) {
							state.gf.visible = true;
						}
					} else if(state.gf != null && state.gf != state.nightmareVisionHiddenGFPlaceholder) {
						state.gf.visible = false;
					}
					if(shiftFocus)state.focusedChar=state.dad;
					state.dad.alpha = lastAlpha;
					state.changeHistoricalCharacterIcon(false, state.dad.healthIcon);
					for (field in state.playFields.members)
					{
						if (field.owner == oldChar)
							field.owner = state.dad;
					}
				}
				state.setHistoricalCharacterLua('dadName', state.dad.curCharacter);
				state.legacyScriptRegistry().setOnScripts('dad', state.dad);
				state.legacyScriptRegistry().setOnScripts('dadGroup', state.dadGroup);
				state.legacyScriptRegistry().setOnScripts('dadGhost', state.dadGroup);

			case 2:
				if(state.gf != null && state.gf != state.nightmareVisionHiddenGFPlaceholder)
				{
					if(state.gf.curCharacter != name)
					{
						var shiftFocus:Bool = state.focusedChar==state.gf;
						var oldChar = state.gf;
						if(!state.gfMap.exists(name))
						{
							state.addNightmareVisionCharacterToList(name, charType);
						}

						var lastAlpha:Float = state.gf.alpha;
						state.gf.alpha = 0.00001;
						state.gf = state.gfMap.get(name);
						state.gf.alpha = lastAlpha;
						if(shiftFocus)state.focusedChar=state.gf;
						for (field in state.playFields.members)
						{
							if (field.owner == oldChar)
								field.owner = state.gf;
						}
					}
					state.setHistoricalCharacterLua('gfName', state.gf.curCharacter);
					state.legacyScriptRegistry().setOnScripts('gf', state.gf);
					state.legacyScriptRegistry().setOnScripts('gfGroup', state.gfGroup);
				}
		}
		state.reloadHistoricalHealthBarColors();
	}
}
