package;

import flixel.graphics.FlxGraphic;

/**
	Keeps the disk images a song loads alive until the song ends.

	A disk graphic is cached with no use count of its own, so flixel destroys it
	as soon as the last sprite drawing it goes away. Scripts that remove and
	recreate a sprite with the same image (flashes, overlays, popups recreated on
	a beat) then paid a full PNG decode, an atlas rebuild and a texture upload in
	the middle of the song. Psych keeps Paths.image graphics until the state is
	cleared, so holding them for the song matches the engines these scripts were
	written for.

	Each held graphic carries one extra use count. Every hold is released when
	the song ends (Main does that before its cache sweep, so the sweep can still
	free them) and when the asset generation moves, so a reimport or a file
	write never serves an old decode. Ordinary holds are capped by bitmap bytes
	and the oldest go first; images a script precached on purpose are pinned and
	only released with the song.

	Releasing a hold can destroy the graphic, which disposes its texture, so
	releases only happen on the thread that started the song. Loader threads
	just add holds.
**/
class SongGraphicRetention {
	public static inline var DEFAULT_MAX_HELD_BYTES:Float = 512.0 * 1024 * 1024;
	/** Ordinary holds beyond this many bitmap bytes release their oldest
		graphic. A script streaming unique images must not keep all of them.
		Zero turns ordinary holds off; precached images are still pinned. */
	public static var maxHeldBytes:Float = DEFAULT_MAX_HELD_BYTES;

	static var active:Bool = false;
	static var epoch:Int = 0;
	static var held:Map<String, FlxGraphic> = new Map();
	static var heldSize:Map<String, Float> = new Map();
	static var pinned:Map<String, Bool> = new Map();
	// Oldest first. Only unpinned keys, the ones the byte cap may release.
	static var order:Array<String> = [];
	static var unpinnedBytes:Float = 0;
	static var pending:Array<FlxGraphic> = [];
	#if (sys && target.threaded)
	static var lock:sys.thread.Mutex = new sys.thread.Mutex();
	static var owner:sys.thread.Thread;
	#end

	/** Remember the render thread. Main calls this once while it starts up. */
	public static function bindOwnerThread():Void {
		#if (sys && target.threaded)
		owner = sys.thread.Thread.current();
		#end
	}

	/** Start holding graphics for a song. Anything still held is released. */
	public static function begin(epoch:Int):Void {
		end();
		SongGraphicRetention.epoch = epoch;
		active = true;
	}

	/** Release every hold and stop holding new graphics. */
	public static function end():Void {
		enter();
		active = false;
		var released = pending;
		pending = [];
		for (graphic in held) released.push(graphic);
		clearLocked();
		leave();
		for (graphic in released) drop(graphic);
	}

	public static function isActive():Bool return active;

	/** Release the holds taken under an older asset generation. Lookups call
		this before asking the cache, so an image held only by this class is
		decoded again after a file write or an import instead of being served
		from the old decode. Loader threads only queue the release. */
	public static function sync(epoch:Int):Void {
		if (!active || epoch == SongGraphicRetention.epoch)
			return;
		enter();
		if (active && epoch != SongGraphicRetention.epoch) {
			for (graphic in held) pending.push(graphic);
			clearLocked();
			SongGraphicRetention.epoch = epoch;
		}
		var released:Array<FlxGraphic> = null;
		if (pending.length > 0 && onOwnerThread()) {
			released = pending;
			pending = [];
		}
		leave();
		if (released != null)
			for (old in released) drop(old);
	}

	/** Hold `graphic` (cached under `key`) until the song ends. `pin` exempts it
		from the byte cap. Does nothing outside a song. */
	public static function hold(key:String, graphic:FlxGraphic, epoch:Int, pin:Bool = false):Void {
		if (!active || key == null || graphic == null || graphic.isDestroyed || (!pin && maxHeldBytes <= 0))
			return;
		enter();
		if (!active) {
			leave();
			return;
		}
		if (epoch != SongGraphicRetention.epoch) {
			// The disk or the imports changed: none of the old decodes may be
			// handed out again just because a hold kept them.
			for (graphic in held) pending.push(graphic);
			clearLocked();
			SongGraphicRetention.epoch = epoch;
		}
		var current = held.get(key);
		if (current == graphic) {
			if (pin && !pinned.exists(key)) {
				pinned.set(key, true);
				order.remove(key);
				unpinnedBytes -= heldSize.get(key);
			} else if (!pinned.exists(key)) {
				// Recently used images are the last ones the cap releases.
				order.remove(key);
				order.push(key);
			}
		} else {
			if (current != null)
				forgetLocked(key, current);
			graphic.incrementUseCount();
			var size = graphic.width * 4.0 * graphic.height;
			held.set(key, graphic);
			heldSize.set(key, size);
			if (pin)
				pinned.set(key, true);
			else {
				order.push(key);
				unpinnedBytes += size;
			}
			// Never release the graphic that was just asked for.
			while (unpinnedBytes > maxHeldBytes && order.length > 1)
				forgetLocked(order[0], held.get(order[0]));
		}
		var released:Array<FlxGraphic> = null;
		if (pending.length > 0 && onOwnerThread()) {
			released = pending;
			pending = [];
		}
		leave();
		if (released != null)
			for (old in released) drop(old);
	}

	public static function isHeld(key:String):Bool {
		enter();
		var graphic = held.get(key);
		leave();
		return graphic != null && !graphic.isDestroyed;
	}

	public static function isPinned(key:String):Bool {
		enter();
		var result = pinned.exists(key);
		leave();
		return result;
	}

	public static function heldCount():Int {
		enter();
		var count = 0;
		for (_ in held.keys()) count++;
		leave();
		return count;
	}

	public static function heldBytes():Float return unpinnedBytes;

	static function forgetLocked(key:String, graphic:FlxGraphic):Void {
		held.remove(key);
		if (pinned.exists(key))
			pinned.remove(key);
		else if (order.remove(key))
			unpinnedBytes -= heldSize.get(key);
		heldSize.remove(key);
		if (graphic != null)
			pending.push(graphic);
	}

	static function clearLocked():Void {
		held.clear();
		heldSize.clear();
		pinned.clear();
		order.resize(0);
		unpinnedBytes = 0;
	}

	static function drop(graphic:FlxGraphic):Void {
		// A script may have destroyed the graphic itself (FlxG.bitmap.remove,
		// a removeFromCache helper). Its count no longer matters then.
		if (graphic != null && !graphic.isDestroyed)
			graphic.decrementUseCount();
	}

	/** True on the render thread, the only one that may release a graphic or
		upload a texture. */
	public static function onOwnerThread():Bool {
		#if (sys && target.threaded)
		return owner == null || sys.thread.Thread.current() == owner;
		#else
		return true;
		#end
	}

	static inline function enter():Void {
		#if (sys && target.threaded) lock.acquire(); #end
	}

	static inline function leave():Void {
		#if (sys && target.threaded) lock.release(); #end
	}
}
