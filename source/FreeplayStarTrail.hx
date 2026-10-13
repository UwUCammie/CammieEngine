package;

/** Pure motion for the card star field. The card is a window onto a larger
 * field of faint spinning stars: they set off from an emitter just beyond the
 * card's right edge that is taller than the card, cross into view already in
 * flight, and fade out before the middle of the card. Each star bends very
 * slightly up or down as it goes. A star crossing the card's edge is cut off
 * by it, so the top, bottom and right edges show partial stars.
 * Nothing varies from run to run: rows and bends come from a fixed scatter
 * that never lines up into steps or a grid. */
class FreeplayStarTrail {
	public static inline var STARS:Int = 320;
	/** Fading copies that follow each star. */
	public static inline var GHOSTS:Int = 2;
	/** Seconds a star lives. */
	public static inline var PERIOD:Float = 1.1;
	public static inline var SIZE:Float = 0.8;
	/** Degrees per second. */
	public static inline var SPIN:Float = 260;
	/** Share of the card width a star travels in its life. */
	public static inline var REACH:Float = 0.47;
	/** Share of the card width the emitter sits beyond the right edge. */
	public static inline var START:Float = 0.03;
	/** Height of the emitter as a share of the card's. */
	public static inline var HEIGHT:Float = 1.6;
	/** Life between a star and each successive tail copy. */
	public static inline var GHOST_STEP:Float = 0.008;
	/** Furthest a star bends off its row by the end of its life, in half card heights. */
	public static inline var ARC:Float = 0.22;
	/** Brightness of a star as it enters. Low, because there are so many. */
	public static inline var GLOW:Float = 0.42;

	/** Life 0..1 of star `n`, which enters exactly PERIOD / STARS after star `n - 1`. */
	public static function life(clock:Float, star:Int):Float {
		var value = clock / PERIOD - star / STARS;
		return value - Math.floor(value);
	}
	/** A fixed scatter of 0..1 values. Evenly stepped rows interlock with the
	 * evenly spaced spawn times into a woven grid once the field is dense, so
	 * rows are mixed instead. Small integers keep every target in agreement. */
	static function scatter(star:Int, salt:Int):Float {
		// Squaring is what scatters: a plain multiply would step evenly again.
		// 46337 is the largest prime whose square still fits a 32-bit integer.
		var mixed = ((star + 1) * 7919 + salt * 1031) % 46337;
		mixed = (mixed * mixed) % 46337;
		mixed = (mixed + salt * 977 + star * 13) % 46337;
		mixed = (mixed * mixed) % 46337;
		return mixed / 46337;
	}
	/** Row of a star, -1 (top of the field) to 1 (bottom). */
	public static function direction(star:Int):Float return scatter(star, 1) * 2 - 1;
	/** Share of the card width travelled, at one steady speed. */
	public static function distance(life:Float):Float return REACH * Math.max(0, Math.min(1, life));
	/** Row a star starts on, as an offset from the card's middle in half card heights. */
	public static function spread(star:Int):Float return direction(star) * HEIGHT;
	/** How far and which way a star bends, -1 (up) to 1 (down). */
	public static function bend(star:Int):Float return scatter(star, 5) * 2 - 1;
	/** Offset from the card's middle at a point in a star's life: its row plus a
	 * gentle arc. Beyond -1..1 it is outside the card and is not drawn. */
	public static function offset(star:Int, life:Float):Float {
		var age = Math.max(0, Math.min(1, life));
		return spread(star) + bend(star) * ARC * age * age;
	}
	/** Pixel size of one star frame. */
	public static inline var FRAME:Int = 18;
	/** Turned copies of the star baked into its sheet. A turning sprite cannot
	 * be cut by a straight edge, so the turn lives in the frames instead. */
	public static inline var TURNS:Int = 24;
	/** How far past the card, in half card heights, a star still shows a part of itself. */
	public static inline var OVERHANG:Float = 0.3;
	/** Whether a star can ever be seen through the card, whole or in part. */
	public static function reachesCard(star:Int):Bool return Math.abs(spread(star)) <= 1 + ARC + OVERHANG;
	/** Frame showing a turn in degrees. A five pointed star repeats every 72. */
	public static function turnFrame(degrees:Float):Int {
		var part = degrees / 72; part -= Math.floor(part);
		return Std.int(part * TURNS) % TURNS;
	}
	/** First frame pixel still inside the window, for a drawn edge at `start`
	 * with each frame pixel `scale` screen pixels wide. */
	public static function clipFrom(start:Float, scale:Float, low:Float):Float
		return scale <= 0 ? FRAME : Math.max(0, Math.min(FRAME, (low - start) / scale));
	/** Frame pixel where the window ends. */
	public static function clipTo(start:Float, scale:Float, high:Float):Float
		return scale <= 0 ? 0 : Math.max(0, Math.min(FRAME, (high - start) / scale));
	/** Whether a sprite at that offset, `margin` half heights tall, stays inside the card. */
	public static function inside(offset:Float, margin:Float = 0):Bool return Math.abs(offset) <= 1 - margin;
	/** Share of the card width a star is past the right edge, negative before it enters. */
	public static function entered(life:Float):Float return distance(life) - START;
	/** Already bright when it crosses the edge, gone by the end of its life. */
	public static function opacity(life:Float):Float {
		if (life <= 0 || life >= 1 || entered(life) < 0) return 0;
		var rest = 1 - life;
		return rest * Math.sqrt(rest) * GLOW;
	}
	/** Stars shrink as they fade. */
	public static function scale(life:Float):Float return SIZE * (1 - 0.4 * Math.max(0, Math.min(1, life)));
	/** Life a tail copy trails its star by. */
	public static function ghostLag(ghost:Int):Float return (ghost + 1) * GHOST_STEP;
	public static function ghostOpacity(life:Float, ghost:Int):Float
		return opacity(life - ghostLag(ghost)) * (1 - (ghost + 1) / (GHOSTS + 1)) * 0.6;
}
