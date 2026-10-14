package;

/**
 * Per-owner contexts that live as long as one primary owner session: a context
 * is reused (and pointed at the newest owner view) while the session lasts, and
 * every context is released when another primary owner takes over. The Psych and
 * Nightmare Vision alphabet registries are two uses of it.
 */
class SourceOwnerContextRegistry<T> {
	var primaryRoot:Null<String>;
	final contexts:Map<String, T> = new Map();
	final releaseContext:T->Void;
	final sessionChanged:Null<Void->Void>;

	public function new(releaseContext:T->Void, ?sessionChanged:Void->Void) {
		this.releaseContext = releaseContext;
		this.sessionChanged = sessionChanged;
	}

	/** Switch the primary owner. An empty root and no root are the same "no
	 * owner" session, so switching between them releases nothing. */
	public function enterSession(root:Null<String>):Void {
		if (root == '') root = null;
		if (root == primaryRoot) return;
		for (context in contexts) releaseContext(context);
		contexts.clear();
		if (sessionChanged != null) sessionChanged();
		primaryRoot = root;
	}

	/** The context for `root`, made with `create` the first time and passed to
	 * `rebind` on every later request in the same session. */
	public function get(root:String, create:Void->T, rebind:T->Void):T {
		var context = contexts.get(root);
		if (context == null) {
			context = create();
			contexts.set(root, context);
		} else rebind(context);
		return context;
	}

	public function existing(root:String):Null<T> return contexts.get(root);
}
