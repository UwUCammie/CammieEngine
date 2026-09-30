package;

/** Owner- and PlayState-scoped storage for Codename's public module fields.
 * Each interpreter remains isolated for ordinary locals; only fields declared
 * public are connected across the currently active song/stage scopes. */
class CodenamePublicScriptGlobals {
	var values:Map<String, Dynamic> = new Map();
	var fieldOwners:Map<String, Array<String>> = new Map();
	var ownerFields:Map<String, Array<String>> = new Map();
	var scopeOwners:Map<String, Array<String>> = new Map();
	var interpreters:Array<CodenameScriptInterp> = [];

	public function new() {}

	public function attach(interp:CodenameScriptInterp):Void {
		if (interp == null) return;
		if (interpreters.indexOf(interp) < 0) interpreters.push(interp);
		for (name in values.keys()) bind(interp, name);
	}

	public function declare(interp:CodenameScriptInterp, names:Array<String>, scope:String,
		source:String):Void {
		if (scope == null || source == null) return;
		attach(interp);
		var owner = scope + '::' + source;
		var fields = ownerFields.get(owner);
		if (fields == null) {
			fields = [];
			ownerFields.set(owner, fields);
		}
		var scopeEntries = scopeOwners.get(scope);
		if (scopeEntries == null) {
			scopeEntries = [];
			scopeOwners.set(scope, scopeEntries);
		}
		if (scopeEntries.indexOf(owner) < 0) scopeEntries.push(owner);
		if (names == null) return;
		for (name in names) {
			if (name == null || name == '') continue;
			if (fields.indexOf(name) < 0) fields.push(name);
			var owners = fieldOwners.get(name);
			if (owners == null) {
				owners = [];
				fieldOwners.set(name, owners);
			}
			if (owners.indexOf(owner) < 0) {
				if (owners.length > 0)
					trace('[codename-public-var] Multiple active declarations for ' + name
						+ ' (' + owners.join(', ') + ', ' + owner + '); sharing one PlayState-scoped value.');
				owners.push(owner);
			}
			if (!values.exists(name)) values.set(name, null);
			for (active in interpreters) bind(active, name);
		}
	}

	public function releaseScope(scope:String):Void {
		if (scope == null) return;
		var owners = scopeOwners.get(scope);
		if (owners != null) for (owner in owners.copy()) releaseOwnerKey(owner);
		scopeOwners.remove(scope);
	}

	public function releaseOwner(scope:String, source:String):Void {
		if (scope == null || source == null) return;
		releaseOwnerKey(scope + '::' + source);
	}

	function releaseOwnerKey(owner:String):Void {
		var fields = ownerFields.get(owner);
		ownerFields.remove(owner);
		if (fields == null) return;
		for (name in fields) {
			var owners = fieldOwners.get(name);
			if (owners == null) continue;
			owners.remove(owner);
			if (owners.length > 0) continue;
			fieldOwners.remove(name);
			values.remove(name);
			for (interp in interpreters) interp.unbindPublicModuleGlobal(name);
		}
	var scopes = [for (scope in scopeOwners.keys()) scope];
		for (scope in scopes) {
			var ownersForScope = scopeOwners.get(scope);
			if (ownersForScope != null && ownersForScope.indexOf(owner) >= 0) {
				ownersForScope.remove(owner);
				if (ownersForScope.length == 0) scopeOwners.remove(scope);
			}
		}
	}

	public function detach(interp:CodenameScriptInterp):Void {
		if (interp == null) return;
		for (name in values.keys()) interp.unbindPublicModuleGlobal(name);
		interpreters.remove(interp);
	}

	public function clear():Void {
		for (interp in interpreters) for (name in values.keys())
			interp.unbindPublicModuleGlobal(name);
		interpreters.resize(0);
		values.clear();
		fieldOwners.clear();
		ownerFields.clear();
		scopeOwners.clear();
	}

	public function getField(name:String):Dynamic return values.get(name);
	public function hasField(name:String):Bool return values.exists(name);

	/** Codename's `scripts` registry publishes state or script fields to every
	 * active gameplay interpreter. Each published key belongs to its source
	 * script, so the existing scope release path removes it with that script. */
	public function scriptFacade(scope:String, source:String):Dynamic {
		return {
			set:function(name:String, value:Dynamic):Void publish(scope, source, name, value),
			get:function(name:String):Dynamic return getField(name),
			exists:function(name:String):Bool return hasField(name),
			remove:function(name:String):Void releaseField(scope, source, name)
		};
	}

	public function publish(scope:String, source:String, name:String, value:Dynamic):Void {
		if (scope == null || source == null || name == null || name == '') return;
		// Reuse the declaration bookkeeping so multiple active scripts may share
		// a name and the final owner controls when the slot is unbound.
		declare(null, [name], scope, source);
		values.set(name, value);
	}

	function releaseField(scope:String, source:String, name:String):Void {
		if (scope == null || source == null || name == null || name == '') return;
		var owner = scope + '::' + source;
		var fields = ownerFields.get(owner);
		if (fields == null || fields.indexOf(name) < 0) return;
		fields.remove(name);
		var owners = fieldOwners.get(name);
		if (owners != null) {
			owners.remove(owner);
			if (owners.length > 0) return;
			fieldOwners.remove(name);
			values.remove(name);
			for (interp in interpreters) interp.unbindPublicModuleGlobal(name);
		}
		if (fields.length == 0) releaseOwnerKey(owner);
	}

	function bind(interp:CodenameScriptInterp, name:String):Void {
		interp.bindPublicModuleGlobal(name,
			function():Dynamic return values.get(name),
			function(value:Dynamic):Void values.set(name, value));
	}
}
