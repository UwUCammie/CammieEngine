package;

/** Elapsed-time menu repeat and the selected card's settling motion. */
class FreeplayScrollMotion {
 public static inline var INITIAL_DELAY:Float = 0.28;
 public static inline var REPEAT_RATE:Float = 10;
 public static inline var FAST_RATE:Float = 30;
 public static inline var MAX_FRAME_TIME:Float = 0.1;
 public var offset:Float = 0;
 var direction:Int = 0;
 var delay:Float = 0;
 var repeat:Float = 0;
 public function new() {}
 public function reset():Void { direction = 0; delay = 0; repeat = 0; }
 public function advance(elapsed:Float, up:Bool, down:Bool, fast:Bool):Int {
  var next = up == down ? 0 : (up ? -1 : 1);
  if (next == 0) { reset(); return 0; }
  if (next != direction) { direction = next; delay = INITIAL_DELAY; repeat = 0; return next; }
  // Discard a long stall instead of jumping through a queued backlog.
  var dt = Math.min(MAX_FRAME_TIME, Math.max(0, elapsed));
  if (delay > 0) { var waiting = Math.min(delay, dt); delay -= waiting; dt -= waiting; }
  repeat += dt * (fast ? FAST_RATE : REPEAT_RATE);
  var steps = Std.int(Math.floor(repeat + 0.0000001));
  repeat -= steps;
  return direction * steps;
 }
 public function moved(change:Int):Void { if (change != 0) offset = change < 0 ? 18 : -18; }
 public function settle(elapsed:Float):Bool {
  if (offset == 0) return false;
  offset *= Math.exp(-12 * Math.max(0, elapsed));
  if (Math.abs(offset) < 0.02) offset = 0;
  return true;
 }
}
