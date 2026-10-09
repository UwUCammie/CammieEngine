package;

import flixel.text.FlxText;

/** Raw event writes and independent tagged objects on a disposable native registry. */
@:access(PlayState)
@:access(GameOverSubstate)
class RuntimeSmokeLegacyPropertyEvent {
	static function check(ok:Bool,message:String):Void if(!ok)throw message;
	public static function verify(state:PlayState,api:NightmareVisionScriptInterp):Void {
		var oldObjects=state.modchartObjects;var oldSprites=state.modchartSprites;var oldTexts=state.modchartTexts;var oldScopes=state.hscriptStates;
		var oldType=state.songSpeedType;var registry=state.legacyScriptRegistry();var oldMain=registry.funkyScripts;var oldHx=registry.hscriptArray;var oldLua=registry.luaArray;var oldEvents=registry.eventScripts;
		var oldDead=state.isDead;var oldGameOver=GameOverSubstate.instance;var oldDadName=state.dad.curCharacter;
		var object=new FlxText(0,0,100,'object');var sprite=new FlxText(0,0,100,'sprite');var label:FlxText=null;var observer:NightmareVisionScriptModule=null;var notifications=0;
		var restore=function(){
			state.modchartObjects=oldObjects;state.modchartSprites=oldSprites;state.modchartTexts=oldTexts;state.hscriptStates=oldScopes;state.songSpeedType=oldType;
			registry.funkyScripts=oldMain;registry.hscriptArray=oldHx;registry.luaArray=oldLua;registry.eventScripts=oldEvents;
			state.isDead=oldDead;GameOverSubstate.instance=oldGameOver;state.dad.curCharacter=oldDadName;
			if(observer!=null)observer.destroy();object.destroy();sprite.destroy();if(label!=null)label.destroy();
		};
		state.modchartObjects=[];state.modchartSprites=[];state.modchartTexts=[];state.hscriptStates=[];
		registry.funkyScripts=[];registry.hscriptArray=[];registry.luaArray=[];registry.eventScripts=[];
		try {
			observer=NightmareVisionScriptModule.fromSource('__property_event','function onEvent(n,a,b){record();}',state,null,function(i){
				var module:NightmareVisionScriptModule=cast i.variables.get('script');module.historicalCalls=true;i.variables.set('record',function(){notifications++;});
			},function(n,c,e)throw e);registry.add(observer);
			state.modchartSprites.set('__property',sprite);label=state.compatMakeLuaText('__property','text');state.modchartObjects.set('__property',object);
			state.triggerEventNote('Set Property','__property.text','object-written');check(object.text=='object-written'&&sprite.text=='sprite'&&label.text=='text','Source object priority');
			state.modchartObjects.remove('__property');state.triggerEventNote('Set Property','__property.text','sprite-written');check(sprite.text=='sprite-written'&&label.text=='text','Source sprite priority');
			state.compatSetTextString('__property','text-helper');check(label.text=='text-helper'&&sprite.text=='sprite-written','Text helper namespace');
			state.modchartSprites.remove('__property');state.triggerEventNote('Set Property','__property.text','false');check(label.text=='false','Source text fallback/raw string');
			api.execute(new NightmareVisionScriptParser().parseString('if(getLuaObject("__property",false)!=null||game.getLuaObject("__property")!=modchartTexts.get("__property")||getLuaObject("camHUD")!=null)throw "source tag lookup";','__property_tags'));
			var tree:Dynamic={inner:{value:'old'},list:[{value:'array'}]};state.modchartObjects.set('__tree',tree);
			state.triggerEventNote('Set Property','__tree.inner.value','1.25');state.triggerEventNote('Set Property','__tree.list[0].value','nested');
			state.triggerEventNote('Set Property','__tree.list[0]','literal');
			check(tree.inner.value=='1.25'&&Std.isOfType(tree.inner.value,String)&&tree.list[0].value=='nested'&&Reflect.field(tree,'list[0]')=='literal','Native raw values and literal final brackets');
			state.triggerEventNote('Set Property','songSpeedType','false');check(state.songSpeedType=='false','Direct state raw value');
			check(state.historicalReadProperty(state,'healthBar')==state.sourceHUDBarAlias('healthBar')&&state.historicalReadProperty(state,'iconP1')==state.sourceHUDIconAlias('iconP1'),'Shared source HUD identity');
			var dead:GameOverSubstate=Type.createEmptyInstance(GameOverSubstate);dead.boyfriend=state.dad;GameOverSubstate.instance=dead;state.isDead=true;
			state.triggerEventNote('Set Property','boyfriend.curCharacter','__property_dead');check(state.dad.curCharacter=='__property_dead'&&state.boyfriend!=state.dad,'Historical game-over root');
			check(notifications==8,'Post-effect notification count: '+notifications);
			@:privateAccess RuntimeSmokeHarness.emit('legacy_property_event_native_verified',{tagPriority:true,textNamespace:true,rawValues:true,nestedIndex:true,literalFinalField:true,sourceHudIdentity:true,gameOverRoot:true,notifications:true});
		} catch(error:Dynamic){restore();throw error;}
		restore();
	}
}
