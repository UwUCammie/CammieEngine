package;

import flixel.text.FlxText;

/** Raw event writes and independent tagged objects on a disposable native registry. */
@:access(PlayState)
@:access(GameOverSubstate)
class RuntimeSmokeLegacyPropertyEvent {
	@:keep public static var reflectionFixture:Dynamic;
	static function check(ok:Bool,message:String):Void if(!ok)throw message;
	public static function verify(state:PlayState,api:NightmareVisionScriptInterp):Void {
		var oldObjects=state.modchartObjects;var oldSprites=state.modchartSprites;var oldTexts=state.modchartTexts;var oldScopes=state.hscriptStates;
		var oldNotes=state.notes;var oldPending=state.unspawnNotes;var oldFixture=reflectionFixture;var probeGroup=new flixel.group.FlxGroup.FlxTypedGroup<FlxText>();var groupText=new FlxText(0,0,100,"group");var keptText=new FlxText(0,0,100,"kept");
		var oldType=state.songSpeedType;var registry=state.legacyScriptRegistry();var oldMain=registry.funkyScripts;var oldHx=registry.hscriptArray;var oldLua=registry.luaArray;var oldEvents=registry.eventScripts;
		var oldDead=state.isDead;var oldGameOver=GameOverSubstate.instance;var oldDadName=state.dad.curCharacter;
		var object=new FlxText(0,0,100,'object');var sprite=new FlxText(0,0,100,'sprite');var label:FlxText=null;var observer:NightmareVisionScriptModule=null;var notifications=0;
		var restore=function(){
			state.modchartObjects=oldObjects;state.modchartSprites=oldSprites;state.modchartTexts=oldTexts;state.hscriptStates=oldScopes;state.songSpeedType=oldType;
			registry.funkyScripts=oldMain;registry.hscriptArray=oldHx;registry.luaArray=oldLua;registry.eventScripts=oldEvents;
			state.notes=oldNotes;state.unspawnNotes=oldPending;reflectionFixture=oldFixture;probeGroup.destroy();if(groupText.animation!=null)groupText.destroy();if(keptText.animation!=null)keptText.destroy();
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
			var lua = new LuaCompatInterp();state.seedEngineCompat(lua);
			lua.variables.set('__expectedActor',state.dad);lua.variables.set('__replacementActor',state.boyfriend);
			lua.execute(new hscript.Parser().parseString('if(getProperty("boyfriend")!=__expectedActor)throw "Lua game-over direct root";if(setProperty("boyfriend",__replacementActor)!=true||getProperty("boyfriend")!=__replacementActor)throw "Lua direct write result";if(setProperty("__tree.inner.value",false)!=true||getProperty("__tree.inner.value")!=false)throw "Lua raw boolean";if(setProperty("__tree.list[0].value","lua")!=true||getProperty("__tree.list[0].value")!="lua")throw "Lua nested array";if(setProperty("__tree.list[0]",42)!=true||getProperty("__tree.list[0]")!=42)throw "Lua final array";','__lua_properties'));
			check(tree.list[0]==42&&Reflect.field(tree,'list[0]')=='literal'&&dead.boyfriend==state.boyfriend,'Lua and event final token policies');
			state.isDead=false;
			lua.variables.set('__sourceOpponent',state.nightmareVisionLegacyReceptors.opponent);
			lua.execute(new hscript.Parser().parseString('if(getProperty("opponentStrums")!=__sourceOpponent)throw "Lua source field identity";if(setProperty("opponentStrums",__sourceOpponent)!=true||getProperty("opponentStrums")!=__sourceOpponent)throw "Lua shared field write";if(getProperty("strumLineNotes")==getProperty("strumLineNotes"))throw "Lua flattened field array must be fresh";','__lua_field_properties'));
			state.notes=cast probeGroup;probeGroup.add(groupText);probeGroup.add(keptText);
			var removed=0;probeGroup.memberRemoved.add(function(item){
				if(item==groupText)check(!item.exists&&item.animation!=null,'Native kill/remove/destroy ordering');
				if(item==keptText)check(item.exists&&item.animation!=null,'Native retained member removal');
				removed++;
			});
			reflectionFixture={raw:'original',items:[{value:'first'}]};
			lua.execute(new hscript.Parser().parseString('if(getPropertyFromGroup("notes",0,"text")!="group")throw "native group read";setPropertyFromGroup("notes",0,"text","written");if(getPropertyFromGroup("notes",0,"text")!="written")throw "native group write";removeFromGroup("notes",0);removeFromGroup("notes",0,true);if(setPropertyFromClass("RuntimeSmokeLegacyPropertyEvent","reflectionFixture.items[0].value",false)!=true||getPropertyFromClass("RuntimeSmokeLegacyPropertyEvent","reflectionFixture.items[0].value")!=false)throw "native class raw array";if(getPropertyFromClass("flixel.FlxG","width")<=0)throw "native static property";','__lua_group_properties'));
			lua.variables.set('__game',state);
			lua.execute(new hscript.Parser().parseString('if(getPropertyFromClass("meta.states.PlayState","instance")!=__game)throw "historical class alias";if(getPropertyFromClass("meta.data.Conductor","songPosition")!=getSongPosition())throw "historical conductor alias";','__lua_class_aliases'));
			check(api.resolveSourceImport('meta.data.Conductor')==PlayState.nightmareVisionConductor&&api.resolveSourceImport('meta.data.ClientPrefs')==state.nightmareVisionPrefs.view,'Lua/HScript shared canonical aliases');
			check(removed==2&&probeGroup.length==0&&groupText.animation==null&&keptText.exists,'Native group disposal and retention');
			state.unspawnNotes=cast [groupText,keptText,groupText];
			lua.execute(new hscript.Parser().parseString('removeFromGroup("unspawnNotes",2);','__lua_array_remove'));
			check(state.unspawnNotes.length==2&&(cast state.unspawnNotes[0]:Dynamic)==keptText&&keptText.exists,'Array removal removes first matching member without destroying');
			state.notes=oldNotes;state.unspawnNotes=oldPending;
			@:privateAccess RuntimeSmokeHarness.emit('legacy_lua_group_native_verified',{publicBindings:true,groupReadWrite:true,killRemoveDestroy:true,dontDestroy:true,arrayRemoval:true,classRawWrites:true,nativeStaticRead:true,sharedCanonicalAliases:true});
			RuntimeSmokeLegacyObjectOrder.verify(state,lua);
			RuntimeSmokeLegacyTextLifecycle.verify(state,lua);
			RuntimeSmokeTextProperties.verify(state,lua);
			RuntimeSmokePsychTextLifecycle.verify(state);
			RuntimeSmokePsychSpriteLifecycle.verify(state);
			RuntimeSmokePsychStateRegistry.verify(state);
			RuntimeSmokePsychInstanceArguments.verify(state);
			RuntimeSmokePsychPublicReflection.verify(state);
			lua.variables.clear();
			@:privateAccess RuntimeSmokeHarness.emit('legacy_lua_property_native_verified',{publicBindings:true,rawValues:true,finalArray:true,gameOverDirectRoot:true,setReturn:true,eventPolicyDistinct:true,sharedFieldAliases:true});
			@:privateAccess RuntimeSmokeHarness.emit('legacy_property_event_native_verified',{tagPriority:true,textNamespace:true,rawValues:true,nestedIndex:true,literalFinalField:true,sourceHudIdentity:true,gameOverRoot:true,notifications:true});
		} catch(error:Dynamic){restore();throw error;}
		restore();
	}
}
