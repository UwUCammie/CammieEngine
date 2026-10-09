package;

/** Native animation admission over a disposable cache entry; gameplay is restored. */
@:access(PlayState)
class RuntimeSmokeLegacyCharacterCarry {
	static function check(ok:Bool, message:String):Void if (!ok) throw message;
	public static function verify(state:PlayState):Void {
		var bf = state.boyfriend;var other = state.dad;var group = state.boyfriendGroup;
		var oldParent = group.parent;var oldMap = group.map;var oldHold = state.nightmareVisionHoldLedger;
		var oldHUD = state.playHUD;var oldIconMode = state.sourceHUDIconMode;
		var oldP1 = state.iconP1;var oldP2 = state.iconP2;var oldBar = state.healthBar;
		var owners = [for (field in state.playFields.members) field.owner];
		var snapshots:Array<Map<String,Dynamic>> = [];
		var names = ['__carry_present', '__carry_missing'];
		for (actor in [bf, other]) {
			var saved:Map<String,Dynamic> = [];
			for (key in ['alpha','specialAnim','holdTimer','heyTimer','stunned','animationNotes']) saved.set(key, Reflect.getProperty(actor,key));
			saved.set('name',actor.animation.name);saved.set('frame',actor.animation.curAnim.curFrame);snapshots.push(saved);
		}
		var restore = function() {
			state.boyfriend=bf;group.parent=oldParent;group.map=oldMap;state.nightmareVisionHoldLedger=oldHold;
			state.playHUD=oldHUD;state.sourceHUDIconMode=oldIconMode;state.iconP1=oldP1;state.iconP2=oldP2;state.healthBar=oldBar;
			for(i in 0...owners.length)state.playFields.members[i].owner=owners[i];
			for(i in 0...2){var actor=i==0?bf:other;var saved=snapshots[i];actor.playAnim(saved.get('name'),true,false,saved.get('frame'));
				for(key in saved.keys())if(key!='name'&&key!='frame')Reflect.setProperty(actor,key,saved.get(key));}
			bf.animation.remove(names[0]);bf.animation.remove(names[1]);other.animation.remove(names[0]);
		};
		state.playHUD=null;state.sourceHUDIconMode=0;state.iconP1=null;state.iconP2=null;state.healthBar=null;state.nightmareVisionHoldLedger=null;
		try {
			for(name in names)check(!bf.animation.exists(name)&&!other.animation.exists(name),'Carry fixture alias collision');
			bf.animation.add(names[0],[0,0,0,0],12,false);bf.animation.add(names[1],[0,0,0,0],12,false);
			other.animation.add(names[0],[0,0,0,0],12,false);
			var alias=bf.curCharacter+'__carry_variant';group.map=[alias=>other];
			bf.playAnim(names[0],true,false,3);other.animation.curAnim=null;
			state.changeNightmareVisionCharacterEvent('0',alias);
			check(state.boyfriend==other&&other.animation.name==names[0]&&other.animation.curAnim.curFrame==3,
				'Historical carry into idle controller: '+other.animation.name+':'+(other.animation.curAnim==null?-1:other.animation.curAnim.curFrame));
			state.boyfriend=bf;group.parent=bf;bf.playAnim(names[1],true,false,3);other.playAnim(names[0],true,false,1);
			state.changeNightmareVisionCharacterEvent('0',alias);
			check(state.boyfriend==other&&other.animation.name==names[0]&&other.animation.curAnim.curFrame==1,
				'Missing alias must preserve current replacement frame: '+other.animation.name+':'+other.animation.curAnim.curFrame);
			@:privateAccess RuntimeSmokeHarness.emit('legacy_character_carry_native_verified',{existingAlias:true,emptyController:true,framePreserved:true,missingAliasSkipped:true,cacheEntry:true});
		} catch(error:Dynamic){restore();throw error;}
		restore();
	}
}
