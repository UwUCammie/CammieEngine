package;

import flixel.FlxBasic;

/** Isolated native scene checks, run only by the source-stage smoke harness. */
class RuntimeSmokePsychStagePlacement {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}

	public static function verify():Void {
		var objects:Array<FlxBasic> = [];
		var prop = function():FlxBasic {var value = new FlxBasic();objects.push(value);return value;};
		var scene = function():Dynamic {
			var value:Dynamic = {stages:[], members:[], boyfriend:prop()};
			value.members.push(value.boyfriend);
			value.add = function(object:Dynamic):Dynamic {value.members.push(object);return object;};
			value.insert = function(index:Int, object:Dynamic):Dynamic {value.members.insert(index, object);return object;};
			return value;
		};
		var initial:Dynamic = scene(), foreign:Dynamic = scene();
		var current:Dynamic = initial;
		var context = new SourceStageContext(function() return current, function() return current,
			function(value) return false, function(name) return null);
		var runtime = new PsychCompiledStageRuntime('tmp/source-stage-callback-probe', 'demo.FactoryProbe', foreign, null, null, context);
		var cleanup = function() {runtime.destroy();for (object in objects) object.destroy();};
		try {
			check(runtime.create(), 'Native placement fixture: ' + runtime.diagnostics.join('; '));
			var helper:PsychBaseStageCompat = initial.stages[1];
			var backdrop = prop();helper.add(backdrop);
			check(initial.members[0] == backdrop && initial.members[1] == initial.boyfriend, 'Nested native helper inserts initial scenery before actors');
			current = foreign;
			var otherProp = prop();helper.add(otherProp);
			check(foreign.members[0] == foreign.boyfriend && foreign.members[1] == otherProp, 'Initial phase does not reorder a different scene');
			current = initial;
			var returnedProp = prop();helper.add(returnedProp);
			check(initial.members[1] == returnedProp && initial.members[2] == initial.boyfriend, 'Retained helper preserves construction phase on returning');
			runtime.beginPostCreate();
			var foreground = prop();helper.add(foreground);
			check(initial.members[3] == foreground, 'Retained native helper appends after construction');
			check(runtime.dispatch('stepHit', []), 'Callback-created native stage dispatch');
			var later:PsychBaseStageCompat = initial.stages[2];
			var laterProp = prop();later.add(laterProp);
			check(initial.members[4] == laterProp, 'Callback-created helper shares completed placement phase');
			runtime.destroy();
			check(!helper.exists && !later.exists, 'Both native helpers retain owner cleanup');
			@:privateAccess RuntimeSmokeHarness.emit('psych_stage_placement_native_verified', {
				initialScene:true,nestedNative:true,foreignScene:true,returnToScene:true,retainedHelper:true,callbackHelper:true,ownedCleanup:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
