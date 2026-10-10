package;

/** Source instance creation and mounting over live registries and native services. */
class SourceScriptInstances {
	public static function create(name:String,type:String,args:Array<Dynamic>,registry:()->Dynamic,
		resolve:String->Dynamic,parse:Dynamic->Dynamic,construct:(Dynamic,Array<Dynamic>)->Dynamic,warn:String->Void):Bool {
		if(!Std.isOfType(args,Array))args=[];
		name=StringTools.replace(StringTools.trim(name),'.','');
		if(registry().get(name)!=null) {warn('createInstance: Variable $name is already being used and cannot be replaced!');return false;}
		if(args==null)args=[];
		var resolved=resolve(type);
		if(resolved==null) {warn('createInstance: Class $type not found');return false;}
		var object=construct(resolved,parse(args));
		if(object!=null)registry().set(name,object);
		else warn('createInstance: Failed to create $name, arguments are possibly wrong.');
		return object!=null;
	}
	public static function add(name:String,front:Bool,registry:()->Dynamic,target:()->Dynamic,
		play:()->Dynamic,gameOver:()->Dynamic,anchor:()->Dynamic,warn:String->Void):Void {
		var object:Dynamic=registry().get(name);
		if(object==null) {warn('addInstance: Can\'t add what doesn\'t exist~ ($name)');return;}
		if(front)target().add(object);
		else {
			var active=play();
			if(active==null)throw 'addInstance requires a PlayState for insertion';
			if(!Reflect.getProperty(active, 'isDead'))play().insert(Reflect.getProperty(play(), 'members').indexOf(anchor()),object);
			else SourceScriptSpriteLifecycle.insertGameOver(object,gameOver);
		}
	}
}
