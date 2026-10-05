"""Minimal standalone field dependencies; exercise the pinned real signal code."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def write_nv_field_sprite_stubs(work):
    (work / 'flixel/util').mkdir(parents=True, exist_ok=True)
    (work / 'flixel').mkdir(parents=True, exist_ok=True)
    (work / 'flixel/FlxSprite.hx').write_text('''package flixel;
class FlxSprite {
 public var x:Float=0; public var y:Float=0; public var width:Float=0; public var height:Float=0;
 public var color:Int=0; public var alpha:Float=1; public var exists:Bool=true;
 public var visible:Bool=true; public var alive:Bool=true; public var destroyed:Bool=false;
 public var scrollFactor:FixtureScrollFactor;
 public function new() scrollFactor=new FixtureScrollFactor();
 public function makeGraphic(width:Int,height:Int,color:Int):FlxSprite {
  this.width=width;this.height=height;this.color=color;return this;
 }
 public function destroy():Void destroyed=true;
}
class FixtureScrollFactor {public function new(){} public function set(x:Float=1,y:Float=1):Void {}}
''', newline='\n')
    (work / 'flixel/util/FlxColor.hx').write_text('''package flixel.util;
class FlxColor {public static inline var WHITE:Int=0xFFFFFF;public static inline var BLACK:Int=0x000000;}
''', newline='\n')


def write_nv_field_dependencies(work):
    (work / 'flixel/util').mkdir(parents=True, exist_ok=True)
    write_nv_field_sprite_stubs(work)
    (work / 'flixel/util/FlxSignal.hx').write_text(
        (ROOT / '.haxelib/flixel/6,1,2/flixel/util/FlxSignal.hx').read_text(), newline='\n')
    (work / 'flixel/util/FlxDestroyUtil.hx').write_text('''package flixel.util;
class FlxDestroyUtil {
 public static function destroyArray<T:IFlxDestroyable>(items:Array<T>):Array<T> {
  if(items!=null) {for(item in items)if(item!=null)item.destroy();items.resize(0);} return null;
 }
}
interface IFlxDestroyable {public function destroy():Void;}
''', newline='\n')
    (work / 'NightmareVisionNoteSkin.hx').write_text(
        'class NightmareVisionNoteSkin {public function new() {}}', newline='\n')
