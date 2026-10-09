package;

/** Public historical methods share the same state transaction as event dispatch. */
class NightmareVisionLegacyCharacterBindings {
	public static function install(interp:NightmareVisionScriptInterp,state:Dynamic,stateClass:Dynamic,
		preload:(String,Int)->Void,change:(String,Int)->Void,position:(Character,Bool)->Void,reload:Void->Void):Void {
		var api:Map<String,Dynamic> = ['addCharacterToList'=>preload,'changeCharacter'=>change,'startCharacterPos'=>position,'reloadHealthBarColors'=>reload];
		for(name in api.keys()) {
			var callback=api.get(name);var read=function():Dynamic return callback;
			interp.variables.remove(name);
			interp.bindLiveValue(name,read,null,function()return state);
			interp.sourceClassScope().bindStaticField(state,name,read);
			interp.sourceClassScope().bindStaticField(stateClass,name,read);
		}
	}
}
