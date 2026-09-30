package;

/** Codename's StrumLineGroup exposes both members and iteration over its
 * lines. Keep the native source-index array live, including empty slots. */
@:keep
class CodenameStrumLineCollection<T> {
	@:keep public var members(default, null):Array<Null<CodenameInputLine<T>>>;

	public function new(members:Array<Null<CodenameInputLine<T>>>) {
		this.members = members;
	}

	@:keep public function iterator():Iterator<Null<CodenameInputLine<T>>>
		return members.iterator();
}
