package;

/** Refresh authored XML prop names without replacing script-owned variables. */
class CodenameStageBindings {
	var bound:Map<String, Dynamic> = new Map();

	public function new() {}

	public function refresh(variables:Map<String, Dynamic>, elements:Map<String, Dynamic>,
		?isActorAlias:String->Dynamic->Bool):Void {
		var next:Map<String, Dynamic> = new Map();
		for (name in bound.keys()) {
			if (((isActorAlias != null && isActorAlias(name, bound.get(name)))
				|| elements == null || !elements.exists(name) || elements.get(name) == null)
				&& variables.exists(name) && variables.get(name) == bound.get(name))
				variables.remove(name);
		}
		if (elements != null)
			for (name in elements.keys()) {
				if (!~/^[A-Za-z_][A-Za-z0-9_]*$/.match(name)) continue;
				var value = elements.get(name);
				if (value == null) continue;
				// Native stage registration also contains role characters, whereas
				// Codename's stageSprites contains XML props. Preserve live actor
				// aliases without blocking an actual prop with the same name.
				if (isActorAlias != null && isActorAlias(name, value)) continue;
				if (!variables.exists(name) || (bound.exists(name) && variables.get(name) == bound.get(name))) {
					variables.set(name, value);
					next.set(name, value);
				}
			}
		bound = next;
	}
}
