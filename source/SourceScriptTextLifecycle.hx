package;

/** Shared tagged text transactions over the owning registry and native scenes. */
class SourceScriptTextLifecycle {
	public static function create(tag:String, registry:()->Dynamic, scene:()->Dynamic, make:()->Dynamic, variableRegistry:Bool = false):Dynamic {
		tag = StringTools.replace(tag, '.', '');
		reset(tag, registry, scene, variableRegistry);
		var text = make();
		registry().set(tag, text);
		return text;
	}
	public static function reset(tag:String, registry:()->Dynamic, scene:()->Dynamic, variableRegistry:Bool = false):Void {
		if (variableRegistry) {
			var variables = registry();
			var object:Dynamic = variables.get(tag);
			if (object == null || object.destroy == null) return;
			scene().remove(object, true);
			object.destroy();
			variables.remove(tag);
			return;
		}
		if (!registry().exists(tag)) return;
		var text:Dynamic = registry().get(tag);
		text.kill();
		if (text.wasAdded) scene().remove(text, true);
		text.destroy();
		registry().remove(tag);
	}
	public static function add(tag:String, registry:()->Dynamic, scene:()->Dynamic, variableRegistry:Bool = false):Void {
		if (variableRegistry) {
			var text:Dynamic = registry().get(tag);
			if (text != null) scene().add(text);
			return;
		}
		if (!registry().exists(tag)) return;
		var text:Dynamic = registry().get(tag);
		if (!text.wasAdded) {
			scene().add(text);
			text.wasAdded = true;
		}
	}
	public static function remove(tag:String, destroy:Bool, registry:()->Dynamic, scene:()->Dynamic, variableRegistry:Bool = false):Void {
		if (variableRegistry) {
			var variables = registry();
			var text:Dynamic = variables.get(tag);
			if (text == null) return;
			scene().remove(text, true);
			if (destroy) {
				text.destroy();
				variables.remove(tag);
			}
			return;
		}
		if (!registry().exists(tag)) return;
		var text:Dynamic = registry().get(tag);
		if (destroy) text.kill();
		if (text.wasAdded) {
			scene().remove(text, true);
			text.wasAdded = false;
		}
		if (destroy) {
			text.destroy();
			registry().remove(tag);
		}
	}
}
