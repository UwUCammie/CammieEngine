package;

import hscript.ScriptClass;
import hscript.ScriptClassScope;

/** Shared registration and attachment for direct and owner-source Psych stages. */
class PsychStageConstruction {
	final host:Dynamic;
	final context:SourceStageContext;
	var scope:ScriptClassScope;
	var postCreate:Bool = false;
	final initialBackground:Bool;
	var placement:PsychStagePlacement;
	public final stages:Array<Dynamic> = [];
	public final registries:Array<Array<Dynamic>> = [];
	public final adapters:Array<PsychBaseStageCompat> = [];

	public function new(host:Dynamic, ?context:SourceStageContext, initialBackground:Bool = false) {
		this.host = host;
		this.context = context;
		this.initialBackground = initialBackground;
	}

	public static function register(host:Dynamic, stage:Dynamic):Array<Dynamic> {
		if (host == null) return null;
		var registry:Array<Dynamic> = Reflect.getProperty(host, 'stages');
		if (registry == null) {registry = [];Reflect.setProperty(host, 'stages', registry);}
		registry.push(stage);
		return registry;
	}

	public static function createNative(context:SourceStageContext, ?host:Dynamic):PsychBaseStageCompat
		return new PsychBaseStageCompat(host, context, true);

	public function bind(scope:ScriptClassScope, activate:Bool = true):Void {
		if (this.scope != null) {
			if (this.scope != scope) throw '[psych-stage] Construction scope cannot change owners';
			return;
		}
		this.scope = scope;
		// Capture the live scene at construction, not the retained asset owner.
		placement = new PsychStagePlacement(context == null ? host : context.state(), initialBackground && !postCreate);
		if (activate) install();
	}

	function install():Void {
		scope.bindNativeFactory(PsychBaseStageCompat, createOwnedNative);
		scope.bindNativeConstruction(PsychBaseStageCompat, before, after,
			['ID', 'active', 'visible', 'alive', 'exists', 'curStep', 'curDecStep', 'curBeat', 'curDecBeat', 'curSection'], attach);
	}

	/** Keep selected-stage construction local to its call, including nested stages. */
	public function withActive<T>(callback:Void->T):T {
		if (scope == null) throw '[psych-stage] Construction scope is not bound';
		var restore = scope.captureNativeConstruction(PsychBaseStageCompat);
		install();
		try {
			var result = callback();restore();return result;
		} catch (error:Dynamic) {restore();throw error;}
	}

	function createOwnedNative(args:Array<Dynamic>):Dynamic {
		var stage = createNative(context, host);
		stage.attachScriptClassScope(scope);
		stage.attachPlacement(placement);
		adapters.push(stage);
		var target = context == null ? host : context.state();
		if (target != null) {
			stages.push(stage);
			registries.push(Reflect.getProperty(target, 'stages'));
		}
		return stage;
	}

	function before(stage:ScriptClass):Void {
		var registry = register(context == null ? host : context.state(), stage);
		if (registry == null) throw '[psych-stage] Invalid state for the stage added!';
		registries.push(registry);
		stages.push(stage);
	}

	function attach(nativeBase:Dynamic):Void {
		var adapter:PsychBaseStageCompat = cast nativeBase;
		adapters.push(adapter);
		adapter.attachHost(host);
		adapter.attachContext(context);
		adapter.attachScriptClassScope(scope);
		adapter.attachPlacement(placement);
		if (postCreate) adapter.beginPostCreate();
	}

	function after(stage:ScriptClass, nativeBase:Dynamic):Void stage.callFunction('create', []);

	public function beginPostCreate():Void {
		postCreate = true;
		if (placement != null) placement.beginPostCreate();
		for (adapter in adapters) adapter.beginPostCreate();
	}
}
