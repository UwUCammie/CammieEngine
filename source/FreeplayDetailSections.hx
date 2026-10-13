package;

typedef FreeplayDetailSection = {
	var title:String;
	var y:Int;
	var height:Int;
	var color:Int;
}

/** Right-hand Freeplay detail cards for the 720p logical viewport. Every block
 * of detail text sits on one backed card whose accent and heading share a color. */
class FreeplayDetailSections {
	/** Bottom edge shared by the visualizer floor and every bar. */
	public static inline var METER_FLOOR:Int = 166;
	public static inline var GAP:Int = 8;
	public static inline var TRACK_Y:Int = 176;
	public static inline var TRACK_HEIGHT:Int = 120;
	public static inline var DIFFICULTY_Y:Int = TRACK_Y + TRACK_HEIGHT + GAP;
	public static inline var DIFFICULTY_HEIGHT:Int = 200;
	public static inline var SCORE_Y:Int = DIFFICULTY_Y + DIFFICULTY_HEIGHT + GAP;
	public static inline var SCORE_HEIGHT:Int = 132;

	public static function layout():Array<FreeplayDetailSection> return [
		{title:'TRACK', y:TRACK_Y, height:TRACK_HEIGHT, color:0xFFFF66B7},
		{title:'DIFFICULTY', y:DIFFICULTY_Y, height:DIFFICULTY_HEIGHT, color:0xFF80E3D0},
		{title:'YOUR BEST', y:SCORE_Y, height:SCORE_HEIGHT, color:0xFFFFD166},
	];
}
