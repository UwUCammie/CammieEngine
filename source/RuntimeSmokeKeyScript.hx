package;

import flixel.FlxG;

/**
	Presses keys at chosen song positions inside a smoke process, the way a
	player would, for songs whose mods ask for one (a dodge on space, for
	example). `--smoke-keys space@22800,space@45000` sends a real key down and
	up through the stage once the song clock has reached each time. It arms
	itself when the song scene is ready, so it works for any smoke run.
**/
@:access(RuntimeSmokeHarness)
class RuntimeSmokeKeyScript {
	static var pending:Array<{key:String, at:Float}> = [];
	static var armed:Bool = false;

	public static function install():Void {
		#if sys
		if (armed || !RuntimeSmokeHarness.enabled()) return;
		var args = Sys.args();
		var index = args.indexOf('--smoke-keys');
		if (index < 0 || index + 1 >= args.length) return;
		armed = true;
		for (entry in args[index + 1].split(',')) {
			var parts = entry.split('@');
			var time = parts.length == 2 ? Std.parseFloat(parts[1]) : Math.NaN;
			if (Math.isFinite(time) && time >= 0) pending.push({key: StringTools.trim(parts[0]), at: time});
		}
		pending.sort(function(a, b) return Reflect.compare(a.at, b.at));
		RuntimeSmokeHarness.emit('smoke_keys_armed', {count: pending.length});
		if (pending.length > 0) FlxG.signals.postUpdate.add(update);
		#end
	}

	static function update():Void {
		#if sys
		if (RuntimeSmokeHarness.finished || pending.length == 0 || !RuntimeSmokeHarness.playStateReady
			|| !Std.isOfType(FlxG.state, PlayState)) return;
		while (pending.length > 0 && Conductor.songPosition >= pending[0].at) {
			var next = pending.shift();
			RuntimeSmokeHarness.simulateKey(next.key);
			RuntimeSmokeHarness.emit('smoke_key', {key: next.key, scheduled: next.at, songPosition: Conductor.songPosition});
		}
		#end
	}
}
