package;

/** Modern Psych sprite transactions share native objects and text replacement services. */
class SourceScriptSpriteLifecycle {
	public static function create(tag:String, registry:()->Dynamic, scene:()->Dynamic, make:()->Dynamic, activate:Bool):Void {
		var sprite = SourceScriptTextLifecycle.create(tag, registry, scene, make, true);
		if (activate) Reflect.setProperty(sprite, 'active', true);
	}
	public static function createAnimate(tag:String, registry:()->Dynamic, play:()->Dynamic, make:()->Dynamic):Void {
		tag = StringTools.replace(tag, '.', '');
		var previous:Dynamic = registry().get(tag);
		if (previous != null) {
			previous.kill();
			play().remove(previous);
			previous.destroy();
		}
		var sprite = make();
		registry().set(tag, sprite);
		Reflect.setProperty(sprite, 'active', true);
	}
	public static function add(tag:String, front:Bool, registry:()->Dynamic, scene:()->Dynamic, anchor:()->Dynamic, isDead:()->Bool, gameOver:()->Dynamic):Void {
		var sprite:Dynamic = registry().get(tag);
		if (sprite == null) return;
		var target:Dynamic = scene();
		if (front) target.add(sprite);
		else if (!isDead()) target.insert(target.members.indexOf(anchor()), sprite);
		else gameOver().insert(gameOver().members.indexOf(Reflect.getProperty(gameOver(), 'boyfriend')), sprite);
	}
	public static function remove(tag:String, destroy:Bool, group:String, resolve:String->Dynamic, registry:()->Dynamic, scene:()->Dynamic):Void {
		var sprite:Dynamic = resolve(tag);
		if (sprite == null || sprite.destroy == null) return;
		var target:Dynamic = group == null ? scene() : resolve(group);
		target.remove(sprite, true);
		if (destroy) {
			registry().remove(tag);
			sprite.destroy();
		}
	}
}
