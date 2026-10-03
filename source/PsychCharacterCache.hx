package;

/** Shared Psych CharacterGroup cache and alpha-transfer behavior.
 * Construction and display ownership stay with the caller because stage
 * placement, scripts, playfield ownership and rendering differ by host. */
class PsychCharacterCache<T> {
	public var map(default, null):Map<String, T> = new Map();
	public var parent(default, null):T;
	final identity:T->String;
	final construct:String->T;
	final activate:T->T->Void;

	public function new(parent:T, identity:T->String, construct:String->T, activate:T->T->Void) {
		this.parent = parent;
		this.identity = identity;
		this.construct = construct;
		this.activate = activate;
		if (parent != null) map.set(identity(parent), parent);
	}

	/** Return an existing actor or construct and cache a hidden one. */
	public function addToList(name:String):T {
		if (map.exists(name)) return map.get(name);
		var actor = construct(name);
		if (actor == null) throw '[psych-character-cache] Cannot construct ' + name;
		Reflect.setProperty(actor, 'alpha', 0.00001);
		// Psych CharacterGroup::addChar keys newly-created actors by their
		// resolved character identity, not blindly by the constructor argument.
		map.set(identity(actor), actor);
		return actor;
	}

	/** Activate a cached actor while carrying the previous actor's alpha. */
	public function change(name:String):T {
		if (parent != null && identity(parent) == name) return parent;
		if (!map.exists(name)) addToList(name);
		var next = map.get(name);
		if (next == null) throw '[psych-character-cache] No cached actor for ' + name;
		var old = parent;
		var alpha:Float = old == null ? 1 : Reflect.getProperty(old, 'alpha');
		if (old != null) Reflect.setProperty(old, 'alpha', 0.0001);
		parent = next;
		Reflect.setProperty(next, 'alpha', alpha);
		activate(old, next);
		return next;
	}

	/** Drop cache references; the owning state removes/destroys its actors. */
	public function release():Void {
		map.clear();
		parent = null;
	}
}
