package;

import flixel.FlxG;
import flixel.FlxCamera;
import flixel.FlxObject;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxTween.FlxTweenManager;

/** Isolated native cameras and manager exercise the real gameplay event entrypoint. */
@:access(PlayState)
@:access(flixel.FlxCamera)
class RuntimeSmokeLegacyCameraEvents {
	static function check(ok:Bool, message:String):Void if (!ok) throw message;
	static function near(a:Float, b:Float):Bool return Math.abs(a-b) < 0.00001;
	public static function verify(state:PlayState, registry:NightmareVisionLegacyScriptRegistry, api:NightmareVisionScriptInterp):Void {
		var saved:Map<String, Dynamic> = [];
		for (name in ['camGame','camHUD','camFollow','defaultCamZoom','isCameraOnForcedPos','camTween','camHUDAlphaTween','songSpeedTween',
			'curBeat','lastBeatHit','totalBeat','totalShake','timeBeat','gameZ','hudZ','gameShake','hudShake','shakeTime','hscriptStates','boyfriendCameraOffset','girlfriendCameraOffset','opponentCameraOffset','nightmareVisionCameraEvents']) saved.set(name, Reflect.getProperty(state,name));
		var oldPrimary = FlxG.camera;var oldManager = FlxTween.globalManager;var oldPref = state.nightmareVisionPrefs.view.camZooms;
		var oldMain = registry.funkyScripts;var oldHx = registry.hscriptArray;var oldLua = registry.luaArray;var oldEvents = registry.eventScripts;
		var manager = new FlxTweenManager();var game = new CompatCamera();var hud = new FlxCamera();var follow = new FlxObject();
		var observer:NightmareVisionScriptModule = null;var notifications = 0;var chainLog:Array<String> = [];var observingChain = false;
		var restore = function() {
			if (state.nightmareVisionCameraEvents != null) state.nightmareVisionCameraEvents.destroy();
			registry.funkyScripts = oldMain;registry.hscriptArray = oldHx;registry.luaArray = oldLua;registry.eventScripts = oldEvents;
			if (observer != null) observer.destroy();
			for (name in saved.keys()) Reflect.setProperty(state,name,saved.get(name));
			state.nightmareVisionPrefs.view.camZooms = oldPref;FlxG.camera = oldPrimary;FlxTween.globalManager = oldManager;
			manager.destroy();game.destroy();hud.destroy();follow.destroy();
		};
		state.camGame = game;state.camHUD = hud;state.camFollow = follow;FlxG.camera = game;FlxTween.globalManager = manager;
		state.camTween = null;state.camHUDAlphaTween = null;state.nightmareVisionCameraEvents = null;
		state.boyfriendCameraOffset = [0,0];state.girlfriendCameraOffset = [0,0];state.opponentCameraOffset = [0,0];
		registry.funkyScripts = [];registry.hscriptArray = [];registry.luaArray = [];registry.eventScripts = [];
		try {
			observer = NightmareVisionScriptModule.fromSource('__camera_events', 'var defaultCamZoom=-1;function onEvent(n,a,b){record(n);}function onBeatHit(){record("beat:"+curBeat);}', state,null,
				function(i) {var h:NightmareVisionScriptModule=cast i.variables.get('script');h.historicalCalls=true;i.variables.set('record',function(n:String) {
					if (observingChain) chainLog.push(n+':'+state.totalBeat+':'+state.lastBeatHit);
					notifications++;if(n=='HUD Fade' && state.camHUDAlphaTween == null) throw 'Notification preceded owned fade';
				});},function(n,c,e)throw e);
			registry.add(observer);
			state.defaultCamZoom = 0.8;game.zoom = 0.8;hud.zoom = 1;state.nightmareVisionPrefs.view.camZooms = true;
			state.triggerEventNote('Add Camera Zoom','','');
			check(near(game.zoom,.815)&&near(hud.zoom,1.03),'Native additive defaults');
			game.zoom = 1.35;state.triggerEventNote('Add Camera Zoom','1','1');check(near(game.zoom,1.35)&&near(hud.zoom,1.03),'Native source zoom limit');
			game.zoom = 0.8;state.triggerEventNote('Camera Zoom','2','');
			check(near(game.zoom,.8)&&near(state.defaultCamZoom,1.6)&&observer.get('defaultCamZoom')==1.6,'Empty duration publishes default without immediate camera write');
			game.zoom = 0.4;state.triggerEventNote('Camera Zoom','0.5','1,linear');var zoom = state.camTween;
			check(zoom!=null&&near(state.defaultCamZoom,.8),'Native zoom handle');
			state.triggerEventNote('HUD Fade','0','1');var fade = state.camHUDAlphaTween;
			api.execute(new NightmareVisionScriptParser().parseString('if(camTween==null||camHUDAlphaTween==null||game.camTween!=camTween||Reflect.getProperty(game,"camHUDAlphaTween")!=camHUDAlphaTween)throw "native tween aliases";','__camera_aliases'));
			var other:Dynamic = {alpha:1.};var foreign = FlxTween.tween(other,{alpha:0.},1);
			state.nightmareVisionCameraEvents.setActive(false);manager.update(.25);
			check(near(hud.alpha,1)&&other.alpha<1&&!zoom.active&&!fade.active,'Owned pause preserves foreign tween');
			state.nightmareVisionCameraEvents.setActive(true);manager.update(.5);
			check(near(hud.alpha,.5)&&near(game.zoom,.4+.4*Math.sqrt(.75))&&zoom.active&&fade.active,'Native linear fade, circOut zoom and resume');
			state.triggerEventNote('HUD Fade','1','1');check(!fade.active&&state.camHUDAlphaTween!=fade,'Fade replaces only its handle');
			manager.update(1.1);check(near(hud.alpha,1)&&state.camHUDAlphaTween==null&&state.camTween==null,'Native completion clears handles');
			state.triggerEventNote('Set Cam Zoom','0.6','2');check(near(state.defaultCamZoom,.6)&&near(game.zoom,.8),'Set Cam Zoom changes only default');
			state.triggerEventNote('Camera Follow Pos','bad','12');check(state.isCameraOnForcedPos&&follow.x==0&&follow.y==12,'Native follow lock');
			state.triggerEventNote('Camera Follow Pos','','');check(!state.isCameraOnForcedPos,'Native follow release');
			state.triggerEventNote('Set Cam Pos','23,45','bf');check(state.boyfriendCameraOffset[0]==23&&state.boyfriendCameraOffset[1]==45,'Native actor offsets');
			state.triggerEventNote('Game Flash','#FF0000','');check(near(game._fxFlashDuration,.5),'Native flash default');
			state.triggerEventNote('Screen Shake','0.5,0.02,extra','0.2,0.01');check(near(game._fxShakeDuration,.5)&&near(hud._fxShakeDuration,.2),'Native shake accepts source extra fields');
			state.hscriptStates = [];observingChain = true;
			api.execute(new NightmareVisionScriptParser().parseString('gameZ=0.2;hudZ=0.3;totalShake=7;timeBeat=2;game.shakeTime=true;Reflect.setProperty(game,"totalBeat",2);if(game.totalBeat!=2||game.gameZ!=gameZ||PlayState.totalShake!=7)throw "chain aliases";','__chain_aliases'));
			game.zoom = .8;hud.zoom = 1;state.curBeat = 2;state.gameShake = .006;state.hudShake = .008;
			var bpm = Conductor.bpm;
			state.finishHistoricalNightmareBeat();
			check(state.totalBeat==1&&state.totalShake==7&&state.lastBeatHit==2&&observer.get('curBeat')==2,'Native chain counter consumption and published beat');
			check(near(game.zoom,1)&&near(hud.zoom,1.3),'Native chain uses live amplitudes');
			check(near(game._fxShakeDuration,60/bpm),'Native chain shake uses current BPM and interval');
			check(chainLog.join('|')=='Add Camera Zoom:2:2|Screen Shake:1:2|beat:2:1:2','Native event/count/beat publication order: '+chainLog.join('|'));
			chainLog=[];state.curBeat=3;state.finishHistoricalNightmareBeat();check(state.totalBeat==1&&chainLog.join('|')=='beat:3:1:3','Native off-interval beat notification');
			state.triggerEventNote('Camera Zoom Chain','2,3,0.01,0.02','2,1');
			check(near(state.gameZ,.015)&&near(state.hudZ,.03)&&state.totalBeat==2&&state.timeBeat==1&&state.shakeTime,'Native chain setup');
			state.triggerEventNote('Screen Shake Chain','0.05,0.06','9');check(state.totalShake==9&&near(state.gameShake,.05)&&near(state.hudShake,.06),'Native shake-chain state');
			observingChain = false;
			@:privateAccess RuntimeSmokeHarness.emit('legacy_camera_chain_native_verified',{liveBindings:true,beatPublication:true,reentrantDispatcher:true,remainingCount:true,bpmDuration:true,offInterval:true,shakeState:true});
			state.triggerEventNote('HUD Fade','0','2');var retired = state.camHUDAlphaTween;state.nightmareVisionCameraEvents.destroy();state.nightmareVisionCameraEvents = null;
			check(!retired.active&&state.camHUDAlphaTween==null,'Native owner teardown');
			@:privateAccess RuntimeSmokeHarness.emit('legacy_camera_events_native_verified',{events:8,notifications:notifications,sourceDefaults:true,publicTweenHandles:true,ownedPauseResume:true,unrelatedTweenPreserved:true,replacement:true,completion:true,teardown:true});
		} catch(error:Dynamic) {restore();throw error;}
		restore();
	}
}
