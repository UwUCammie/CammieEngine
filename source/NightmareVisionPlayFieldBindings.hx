package;

/** Owner-local constructor binding for the Nightmare Vision source PlayField. */
@:keep
class NightmareVisionPlayFieldBindings {
	public static function install(interp:NightmareVisionScriptInterp, owner:String,
		resolve:String->Dynamic):Void {
		if (interp == null || owner == null || resolve == null)
			throw '[nightmare-vision-playfield] Invalid owner constructor binding';

		var classView = new NightmareVisionPlayFieldClassView(owner, resolve);
		interp.variables.set('PlayField', classView);
		interp.bindImport('funkin.objects.note.PlayField', classView);
		interp.bindConstructorFactory(classView,
			function(args:Array<Dynamic>):Dynamic return classView.create(args), null);
	}
}

/** Carries only an owner key and resolver; it never captures a gameplay scene. */
@:keep
class NightmareVisionPlayFieldClassView {
	final owner:String;
	final resolve:String->Dynamic;

	public function new(owner:String, resolve:String->Dynamic) {
		this.owner = owner;
		this.resolve = resolve;
	}

	public function create(args:Array<Dynamic>):Dynamic {
		var host = resolve(owner);
		if (host == null)
			throw '[nightmare-vision-playfield] No active PlayState for owner: ' + owner;
		var factory = Reflect.field(host, 'createNightmareVisionSourceField');
		if (!Reflect.isFunction(factory))
			throw '[nightmare-vision-playfield] Owner has no source field factory: ' + owner;
		return Reflect.callMethod(host, factory, [args]);
	}
}
