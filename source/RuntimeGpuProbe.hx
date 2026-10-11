package;

#if (sys && lime_opengl)
import lime.app.Application;
import lime.graphics.opengl.GL;
#end

/** Opt-in asynchronous GPU elapsed queries around OpenFL rendering, before presentation. */
class RuntimeGpuProbe {
	#if (sys && lime_opengl)
	static var installed:Bool = false;
	static var initialized:Bool = false;
	static var available:Bool = false;
	static var active:GpuFrameQuery;
	static var slots:Array<GpuFrameQuery> = [];
	static var samples:Array<Array<Float>> = [];
	static var skipped:Int = 0;
	static var lastReport:Float = 0;
	static var serial:Int = 0;
	#end

	public static function install():Void {
		#if (sys && lime_opengl)
		if (installed || Sys.getEnv('CAMMIE_GPU_PROFILE') != '1') return;
		var window = Application.current == null ? null : Application.current.window;
		if (window == null) return;
		installed = true;
		window.onRender.add(beginFrame, false, 10000);
		window.onRender.add(endFrame, false, -10000);
		#end
	}

	#if (sys && lime_opengl)
	static function beginFrame(context:lime.graphics.RenderContext):Void {
		if (!initialized) {
			initialized = true;
			var extensions = GL.getSupportedExtensions();
			var version = Std.string(GL.getParameter(GL.VERSION));
			var desktop = version.indexOf('OpenGL ES') < 0;
			var parsed = ~/^(\d+)\.(\d+)/;
			var core = parsed.match(version) && (Std.parseInt(parsed.matched(1)) > 3
				|| (Std.parseInt(parsed.matched(1)) == 3 && Std.parseInt(parsed.matched(2)) >= 3));
			available = desktop && (core || (extensions != null && extensions.indexOf('GL_ARB_timer_query') >= 0));
			var bits = available ? NativeGpuTimer.initialize() : 0;
			available = available && bits >= 32;
			@:privateAccess RuntimeSmokeHarness.emit('gpu_profile_context', {available:available,
				vendor:GL.getParameter(GL.VENDOR), renderer:GL.getParameter(GL.RENDERER), version:version,
				counterBits:bits, boundary:'OpenFL render submission before presentation',
				width:Application.current.window.width, height:Application.current.window.height});
			if (available) for (_ in 0...16) slots.push({query:NativeGpuTimer.create(), pending:false, songMs:0, serial:0});
			lastReport = haxe.Timer.stamp();
		}
		if (!available) return;
		active = null;
		for (slot in slots) {
			if (slot.pending && NativeGpuTimer.available(slot.query)) {
				samples.push([slot.songMs, NativeGpuTimer.milliseconds(slot.query), slot.serial]);
				slot.pending = false;
			}
			if (!slot.pending && active == null) active = slot;
		}
		var now = haxe.Timer.stamp();
		if (now - lastReport >= 1) {
			@:privateAccess RuntimeSmokeHarness.emit('gpu_frame_batch', {samples:samples, skipped:skipped});
			samples = [];skipped = 0;lastReport = now;
		}
		if (active == null) {skipped++;return;}
		active.songMs = PlayState.instance != null && flixel.FlxG.state == PlayState.instance ? Conductor.songPosition : -1;
		active.serial = serial++;
		NativeGpuTimer.begin(active.query);
	}

	static function endFrame(context:lime.graphics.RenderContext):Void {
		if (active == null) return;
		NativeGpuTimer.end();
		active.pending = true;
		active = null;
	}
	#end
}

#if (sys && lime_opengl)
private typedef GpuFrameQuery = {var query:Int;var pending:Bool;var songMs:Float;var serial:Int;}
#end
