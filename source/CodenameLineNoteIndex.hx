package;

import haxe.ds.ObjectMap;

/** Per-song immutable identity and order index for Codename-authored notes. */
@:keep
class CodenameLineNoteIndex {
	public var byLine:Map<Int, Array<Dynamic>> = new Map();
	public var byObject:ObjectMap<Dynamic, Bool> = new ObjectMap();

	public function new() {}
}
