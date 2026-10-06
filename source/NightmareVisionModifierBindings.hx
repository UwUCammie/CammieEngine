package;
import nightmarevision.modchart.NightmareVisionModchartVector;
/** Source modifier imports expose the actual adapter types and their methods. */
@:keep
class NightmareVisionModifierBindings {
	public static function install(interp:NightmareVisionScriptInterp, ?owner:String, ?resolve:String->Dynamic):Void {
		var types:Map<String,Dynamic> = ['Modifier'=>NightmareVisionModifier, 'NoteModifier'=>NightmareVisionNoteModifier,
			'SubModifier'=>NightmareVisionSubModifier,'ScriptedModifier'=>NightmareVisionScriptedModifier,
			'ModManager'=>NightmareVisionModManager];
		for(name=>type in types) { interp.variables.set(name,type); interp.bindImport('funkin.game.modchart.'+name,type); }
		if (owner != null && resolve != null) interp.bindConstructorFactory(NightmareVisionModManager, function(args:Array<Dynamic>):Dynamic {
			var host=resolve(owner);
			if(host==null) throw '[nightmare-vision-modifier] No active owner: '+owner;
			var factory=Reflect.field(host,'createNightmareVisionSourceModManager');
			if(!Reflect.isFunction(factory)) throw '[nightmare-vision-modifier] Owner has no modifier manager factory';
			return Reflect.callMethod(host,factory,[args]);
		},null);
		var builtins:Map<String,Dynamic> = [
			'ReverseModifier'=>NightmareVisionReverseModifier,
			'ConfusionModifier'=>NightmareVisionConfusionModifier,
			'PerspectiveModifier'=>NightmareVisionPerspectiveModifier,
			'OpponentModifier'=>NightmareVisionOpponentModifier,
			'FlipModifier'=>NightmareVisionFlipModifier,
			'InvertModifier'=>NightmareVisionInvertModifier,
			'DrunkModifier'=>NightmareVisionDrunkModifier,
			'BeatModifier'=>NightmareVisionBeatModifier,
			'AlphaModifier'=>NightmareVisionAlphaModifier,
			'ReceptorScrollModifier'=>NightmareVisionReceptorScrollModifier,
			'ScaleModifier'=>NightmareVisionScaleModifier,
			'TransformModifier'=>NightmareVisionTransformModifier,
			'InfinitePathModifier'=>NightmareVisionInfinitePathModifier,
			'PathModifier'=>NightmareVisionPathModifier,
			'AccelModifier'=>NightmareVisionAccelModifier,
			'XModifier'=>NightmareVisionXModifier,
			'RotateModifier'=>NightmareVisionRotateModifier,
			'LocalRotateModifier'=>NightmareVisionLocalRotateModifier
		];
		for(name=>type in builtins) { interp.variables.set(name,type); interp.bindImport('funkin.game.modchart.modifiers.'+name,type); }
		var events:Map<String, Dynamic> = [
			'BaseEvent'=>NightmareVisionBaseEvent, 'ModEvent'=>NightmareVisionModEvent,
			'SetEvent'=>NightmareVisionSetEvent, 'EaseEvent'=>NightmareVisionEaseEvent,
			'CallbackEvent'=>NightmareVisionCallbackEvent, 'StepCallbackEvent'=>NightmareVisionStepCallbackEvent
		];
		for (name=>type in events) {
			interp.variables.set(name, type);
			interp.bindImport('funkin.game.modchart.events.' + name, type);
		}
		interp.variables.set('EventTimeline', NightmareVisionEventTimeline);
		interp.bindImport('funkin.game.modchart.EventTimeline', NightmareVisionEventTimeline);
		var kinds:Dynamic={NOTE_MOD:'NOTE_MOD',MISC_MOD:'MISC_MOD'};
		var orders:Dynamic={FIRST:-1000,PRE_REVERSE:-3,REVERSE:-2,POST_REVERSE:-1,DEFAULT:0,LAST:1000};
		interp.variables.set('ModifierType',kinds); interp.variables.set('ModifierOrder',orders);
		interp.bindImport('funkin.game.modchart.Modifier.ModifierType',kinds);
		interp.bindImport('funkin.game.modchart.Modifier.ModifierOrder',orders);
		for(name in Reflect.fields(kinds)) interp.variables.set(name,Reflect.field(kinds,name));
		for(name in Reflect.fields(orders)) interp.variables.set(name,Reflect.field(orders,name));
		interp.variables.set('Vector3',NightmareVisionModchartVector);
		interp.bindImport('funkin.backend.math.Vector3',NightmareVisionModchartVector);
	}
}
