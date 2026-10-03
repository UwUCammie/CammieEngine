"""Minimal renderer-free FlxPoint module for extracted Haxe interpreter fixtures."""

from pathlib import Path


def write_flixel_point_stub(classpath: Path) -> None:
    """Write only the FlxPoint surface needed by the shared stage-group facade."""
    point_file = classpath / "flixel" / "math" / "FlxPoint.hx"
    point_file.parent.mkdir(parents=True, exist_ok=True)
    point_file.write_text(
        """package flixel.math;

class FlxPoint {
 public var x:Float;
 public var y:Float;
 public function new(x:Float=0,y:Float=0) { this.x=x; this.y=y; }
 public function set(x:Float=0,y:Float=0):FlxPoint { this.x=x; this.y=y; return this; }
 public function copyFrom(point:FlxPoint):FlxPoint return set(point.x,point.y);
}

class FlxCallbackPoint extends FlxPoint {
 final callback:FlxPoint->Void;
 public function new(setXCallback:FlxPoint->Void, ?setYCallback:FlxPoint->Void,
  ?setXYCallback:FlxPoint->Void) {
  super();
  callback = setXYCallback != null ? setXYCallback : setXCallback;
 }
 override public function set(x:Float=0,y:Float=0):FlxCallbackPoint {
  super.set(x,y);
  if (callback != null) callback(this);
  return this;
 }
}
""",
        encoding="utf-8",
    )
