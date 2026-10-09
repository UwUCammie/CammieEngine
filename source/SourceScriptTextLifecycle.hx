package;

/** Shared tagged text transactions over the owning registry and native scenes. */
class SourceScriptTextLifecycle {
	public static function create(tag:String, registry:()->Dynamic, scene:()->Dynamic, make:()->Dynamic):Dynamic {
		tag = StringTools.replace(tag, '.', '');
		reset(tag, registry, scene);
		var text = make();
		registry().set(tag, text);
		return text;
	}
	public static function reset(tag:String, registry:()->Dynamic, scene:()->Dynamic):Void {
		if (!registry().exists(tag)) return;
		var text:Dynamic = registry().get(tag);
		text.kill();
		if (text.wasAdded) scene().remove(text, true);
		text.destroy();
		registry().remove(tag);
	}
	public static function add(tag:String, registry:()->Dynamic, scene:()->Dynamic):Void {
		if (!registry().exists(tag)) return;
		var text:Dynamic = registry().get(tag);
		if (!text.wasAdded) {
			scene().add(text);
			text.wasAdded = true;
		}
	}
	public static function remove(tag:String, destroy:Bool, registry:()->Dynamic, scene:()->Dynamic):Void {
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
