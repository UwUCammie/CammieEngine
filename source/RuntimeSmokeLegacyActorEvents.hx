package;

/** Actual actor controllers and event dispatch, restored after the isolated probe. */
@:access(PlayState)
class RuntimeSmokeLegacyActorEvents {
	static function check(ok:Bool, message:String):Void if (!ok) throw message;
	public static function verify(state:PlayState, registry:NightmareVisionLegacyScriptRegistry):Void {
		var oldGF = state.gf;var oldSpeed = state.gfSpeed;var oldStates = state.hscriptStates;
		var oldMain = registry.funkyScripts;var oldHx = registry.hscriptArray;var oldLua = registry.luaArray;var oldEvents = registry.eventScripts;
		var actors = [state.boyfriend, state.dad];var snapshots:Array<Map<String,Dynamic>>=[];var added:Array<{actor:Character,name:String}>=[];
		var observer:NightmareVisionScriptModule = null;var calls:Array<String>=[];
		for (actor in actors) {
			var saved:Map<String,Dynamic>=[];
			for (name in ['specialAnim','heyTimer','idleSuffix','danceIdle','danceEveryNumBeats','stunned','holdTimer','curCharacter']) saved.set(name,Reflect.getProperty(actor,name));
			saved.set('animationName',actor.animation.name);saved.set('animationFrame',actor.animation.curAnim.curFrame);snapshots.push(saved);
			for (name in ['hey','cheer']) if (!actor.animation.exists(name)) {
				actor.animation.add(name,[0],0,false);added.push({actor:actor,name:name});
			}
		}
		var restore = function() {
			registry.funkyScripts=oldMain;registry.hscriptArray=oldHx;registry.luaArray=oldLua;registry.eventScripts=oldEvents;
			if(observer!=null)observer.destroy();state.gf=oldGF;state.gfSpeed=oldSpeed;state.hscriptStates=oldStates;
			for(i in 0...actors.length) {
				var actor=actors[i];var saved=snapshots[i];
				actor.playAnim(saved.get('animationName'),true,false,saved.get('animationFrame'));
				for(name in saved.keys()) if(name!='animationName'&&name!='animationFrame')Reflect.setProperty(actor,name,saved.get(name));
			}
			for(entry in added)entry.actor.animation.remove(entry.name);
		};
		state.hscriptStates=[];registry.funkyScripts=[];registry.hscriptArray=[];registry.luaArray=[];registry.eventScripts=[];
		try {
			observer=NightmareVisionScriptModule.fromSource('__actor_events','function onEvent(n,a,b){record(n);}',state,null,
				function(i){var h:NightmareVisionScriptModule=cast i.variables.get('script');h.historicalCalls=true;i.variables.set('record',function(n:String){
					calls.push(n);if(n=='Play Animation'&&!state.boyfriend.specialAnim)throw 'Actor event notification preceded flags';
				});},function(n,c,e)throw e);
			registry.add(observer);state.gf=state.dad;
			state.triggerEventNote('Play Animation','singLEFT',' 1 ');
			check(state.boyfriend.animation.name=='singLEFT'&&state.boyfriend.specialAnim,'Native numeric animation target');
			state.boyfriend.specialAnim=false;state.dad.specialAnim=false;
			state.triggerEventNote('Hey!',' 0 ','bad');
			check(state.boyfriend.animation.name=='hey'&&state.boyfriend.specialAnim&&state.boyfriend.heyTimer==.6&&!state.dad.specialAnim,'Native Hey target/default duration');
			state.triggerEventNote('Hey!','GF','1.25');
			check(state.dad.animation.name=='cheer'&&state.dad.specialAnim&&state.dad.heyTimer==1.25,'Native GF cheer');
			state.triggerEventNote('Alt Idle Animation','1','');check(state.boyfriend.idleSuffix=='','Native exact suffix reset');
			state.triggerEventNote('Alt Idle Animation','2','-missing');check(state.dad.idleSuffix=='-missing'&&!state.dad.danceIdle,'Native suffix and dance recalculation');
			state.dad.danceEveryNumBeats=2;state.dad.idleSuffix='';state.dad.specialAnim=false;state.dad.stunned=false;state.dad.playAnim('idle',true);
			state.triggerEventNote('Set GF Speed','2','');state.triggerEventNote('Set GF Speed','2','');
			check(state.gfSpeed==2&&state.dad.danceEveryNumBeats==2&&!state.girlfriendDanceDue(2)&&state.girlfriendDanceDue(4),'Native historical repeated speed and cadence');
			state.dad.stunned=true;check(!state.girlfriendDanceDue(4),'Native stunned GF gate');
			check(calls.length==7,'Native actor events notify once');
			@:privateAccess RuntimeSmokeHarness.emit('legacy_actor_events_native_verified',{numericTarget:true,heyTimer:true,specialFlags:true,suffixReset:true,danceRecalculation:true,repeatedSpeed:true,cadence:true,postEffectNotification:true});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
	}
}
