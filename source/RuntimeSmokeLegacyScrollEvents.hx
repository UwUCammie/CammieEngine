package;

import flixel.tweens.FlxTween;
import flixel.tweens.FlxTween.FlxTweenManager;

/** Real historical dispatch and native tween lifetimes on isolated state. */
@:access(PlayState)
class RuntimeSmokeLegacyScrollEvents {
	static function check(ok:Bool,message:String):Void if(!ok)throw message;
	static function near(a:Float,b:Float):Bool return Math.abs(a-b)<0.00001;
	public static function verify(state:PlayState,api:NightmareVisionScriptInterp):Void {
		var saved:Map<String,Dynamic>=[];
		for(name in ['songSpeedType','songSpeedTween','generatedMusic','noteKillOffset','hscriptStates','nightmareVisionCameraEvents','camTween','camHUDAlphaTween'])saved.set(name,Reflect.getProperty(state,name));
		var oldSpeed=PlayState.daScrollSpeed;var oldSong=PlayState.SONG;var oldManager=FlxTween.globalManager;
		var prefs=state.nightmareVisionPrefs.view;var oldSettings=Reflect.field(prefs,'gameplaySettings');
		var settings:Map<String,Dynamic>=['scrolltype'=>'constant','scrollspeed'=>1.5];
		var registry=state.legacyScriptRegistry();var oldMain=registry.funkyScripts;var oldHx=registry.hscriptArray;var oldLua=registry.luaArray;var oldEvents=registry.eventScripts;
		var manager=new FlxTweenManager();var observer:NightmareVisionScriptModule=null;var notifications=0;var nesting=false;
		var restore=function(){
			if(state.nightmareVisionCameraEvents!=null)state.nightmareVisionCameraEvents.destroy();
			for(name in saved.keys())Reflect.setProperty(state,name,saved.get(name));
			PlayState.daScrollSpeed=oldSpeed;PlayState.SONG=oldSong;FlxTween.globalManager=oldManager;
			Reflect.setField(prefs,'gameplaySettings',oldSettings);
			registry.funkyScripts=oldMain;registry.hscriptArray=oldHx;registry.luaArray=oldLua;registry.eventScripts=oldEvents;
			if(observer!=null)observer.destroy();manager.destroy();
		};
		FlxTween.globalManager=manager;state.nightmareVisionCameraEvents=null;state.songSpeedTween=null;state.generatedMusic=false;state.hscriptStates=[];
		PlayState.SONG=cast Reflect.copy(oldSong);PlayState.SONG.speed=2;Reflect.setField(prefs,'gameplaySettings',settings);
		registry.funkyScripts=[];registry.hscriptArray=[];registry.luaArray=[];registry.eventScripts=[];
		try {
			observer=NightmareVisionScriptModule.fromSource('__scroll_events','function onEvent(n,a,b){record();}',state,null,function(i){
				var module:NightmareVisionScriptModule=cast i.variables.get('script');module.historicalCalls=true;
				i.variables.set('record',function(){notifications++;if(nesting){nesting=false;var old=state.songSpeedType;state.songSpeedType='constant';state.triggerEventNote('Change Scroll Speed','99','0');state.songSpeedType=old;}});
			},function(n,c,e)throw e);registry.add(observer);
			state.initializeHistoricalSongSpeed();check(state.songSpeedType=='constant'&&state.songSpeed==2,'Source generation defaults');
			state.triggerEventNote('Change Scroll Speed','2','0');check(state.songSpeed==2&&notifications==0&&state.songSpeedTween==null,'Constant mode exits notifications');
			api.execute(new NightmareVisionScriptParser().parseString('songSpeedType="multiplicative";','__scroll_mode'));
			nesting=true;state.triggerEventNote('Change Scroll Speed','','');check(state.songSpeed==3&&notifications==1,'Defaults and nested constant notification isolation');
			state.triggerEventNote('Change Scroll Speed','2','1');var first=state.songSpeedTween;
			state.triggerEventNote('Change Scroll Speed','3','2');var second=state.songSpeedTween;
			check(first!=second&&first.active&&second.active&&first.duration==1&&second.duration==2,'Concurrent source duration/handles');
			api.execute(new NightmareVisionScriptParser().parseString('if(songSpeedTween!=game.songSpeedTween||songSpeedTween!=PlayState.songSpeedTween||songSpeedTween!=Reflect.getProperty(game,"songSpeedTween"))throw "speed handle aliases";','__scroll_handles'));
			manager.update(0);manager.update(.5);var pausedSpeed=state.songSpeed;var foreign:Dynamic={value:0.};var other=FlxTween.tween(foreign,{value:1.},4);
			state.nightmareVisionCameraEvents.setActive(false);manager.update(.5);check(state.songSpeed==pausedSpeed&&foreign.value>0,'Owned speed pause');
			state.nightmareVisionCameraEvents.setActive(true);manager.update(.5);
			check(state.songSpeedTween==null&&second.active&&near(state.songSpeed,6),'Older completion clears live newer handle');
			manager.update(1.1);check(near(state.songSpeed,9)&&!second.active&&state.songSpeedTween==null,'Newer tween survives old completion');
			state.triggerEventNote('Change Scroll Speed','4','1');var doomed=state.songSpeedTween;state.nightmareVisionCameraEvents.destroy();state.nightmareVisionCameraEvents=null;
			check(!doomed.active&&other.active&&state.songSpeedTween==null,'Owner teardown preserves foreign tween');
			@:privateAccess RuntimeSmokeHarness.emit('legacy_scroll_events_native_verified',{generationDefaults:true,constantExit:true,nestedNotification:true,liveHandles:true,overlap:true,sourceDuration:true,ownedPause:true,completion:true,ownedTeardown:true});
		} catch(error:Dynamic){restore();throw error;}
		restore();
	}
}
