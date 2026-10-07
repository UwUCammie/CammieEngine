package;

import flixel.FlxStrip;
import flixel.util.FlxColor;

/** Minimal source MeshRender behavior on the host's FlxStrip draw path. */
@:keep
@:build(NightmareVisionSpriteMacro.build())
class NightmareVisionMeshRender extends FlxStrip {
	@:keep public var vertex_count(default, null):Int = 0;
	@:keep public var index_count(default, null):Int = 0;

	public function new(x:Float = 0, y:Float = 0, ?color:FlxColor = FlxColor.WHITE) {
		super(x, y);
		makeGraphic(1, 1, color);
	}

	@:keep public inline function build_vertex(x:Float, y:Float, u:Float = 0, v:Float = 0):Int {
		var index = vertex_count;
		var pos = index << 1;
		vertices[pos] = x;
		vertices[pos + 1] = y;
		uvtData[pos] = u;
		uvtData[pos + 1] = v;
		vertex_count++;
		return index;
	}

	@:keep public function add_tri(a:Int, b:Int, c:Int):Void {
		indices[index_count] = a;
		indices[index_count + 1] = b;
		indices[index_count + 2] = c;
		index_count += 3;
	}

	@:keep public function build_tri(ax:Float, ay:Float, bx:Float, by:Float, cx:Float, cy:Float,
		au:Float = 0, av:Float = 0, bu:Float = 0, bv:Float = 0, cu:Float = 0, cv:Float = 0):Void {
		add_tri(build_vertex(ax, ay, au, av), build_vertex(bx, by, bu, bv), build_vertex(cx, cy, cu, cv));
	}

	@:keep public function add_quad(a:Int, b:Int, c:Int, d:Int):Void {
		add_tri(a, b, c);
		add_tri(a, c, d);
	}

	@:keep public function build_quad(ax:Float, ay:Float, bx:Float, by:Float, cx:Float, cy:Float, dx:Float, dy:Float,
		au:Float = 0, av:Float = 0, bu:Float = 0, bv:Float = 0, cu:Float = 0, cv:Float = 0,
		du:Float = 0, dv:Float = 0):Void {
		var b = build_vertex(bx, by, bu, bv);
		var a = build_vertex(ax, ay, au, av);
		var c = build_vertex(cx, cy, cu, cv);
		var d = build_vertex(dx, dy, du, dv);
		add_tri(a, b, c);
		add_tri(a, c, d);
	}

	public function clear():Void {
		vertices.length = 0;
		indices.length = 0;
		uvtData.length = 0;
		colors.length = 0;
		vertex_count = 0;
		index_count = 0;
	}
}
