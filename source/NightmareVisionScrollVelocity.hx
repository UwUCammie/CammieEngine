package;

import nightmarevision.modchart.NightmareVisionModchartTransform;

typedef NightmareVisionSpeedEvent = {
	var position:Float;
	var startTime:Float;
	var songTime:Float;
	var speed:Float;
	@:optional var startSpeed:Float;
}

/** Historical NV visual transport, with source event identity and lazy metadata. */
class NightmareVisionScrollVelocity {
	public static function initial():NightmareVisionSpeedEvent
		return {position:0, startTime:0, songTime:0, speed:1, startSpeed:1};

	public static function select(time:Float, changes:Array<NightmareVisionSpeedEvent>):NightmareVisionSpeedEvent {
		var event = initial();
		for (candidate in changes) {
			if (candidate.startTime <= time && candidate.startTime >= event.startTime) {
				if (candidate.startSpeed == null) candidate.startSpeed = event.speed;
				event = candidate;
			}
		}
		return event;
	}

	public static function position(time:Float, event:NightmareVisionSpeedEvent):Float
		return event.position - NightmareVisionModchartTransform.visualPosition(time, event.songTime, 1) * event.speed;

	public static function sort(a:NightmareVisionSpeedEvent, b:NightmareVisionSpeedEvent):Int
		return a.startTime < b.startTime ? -1 : a.startTime > b.startTime ? 1 : 0;

	public static function push(changes:Array<NightmareVisionSpeedEvent>, name:String, value:String,
		time:Float, songSpeed:Float):Void {
		var parsed = Std.parseFloat(value);
		var speed = name == 'Constant SV' ? (Math.isNaN(parsed) ? songSpeed : songSpeed / parsed)
			: (Math.isNaN(parsed) ? 1 : parsed);
		changes.sort(sort);
		changes.push({position:position(time, select(time, changes)), songTime:time, startTime:time, speed:speed});
	}
}
