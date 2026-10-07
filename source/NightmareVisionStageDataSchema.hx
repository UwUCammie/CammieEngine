package;

/** Pinned source StageFile, StageObject and animation shapes. */
typedef NightmareVisionStageFile =
{
	var defaultZoom:Float;
	var boyfriend:Array<Float>;
	var girlfriend:Array<Float>;
	var opponent:Array<Float>;
	@:optional var hide_girlfriend:Null<Bool>;
	@:optional var camera_boyfriend:Null<Array<Float>>;
	@:optional var camera_opponent:Null<Array<Float>>;
	@:optional var camera_girlfriend:Null<Array<Float>>;
	@:optional var camera_speed:Null<Float>;
	@:optional var dadZIndex:Null<Int>;
	@:optional var gfZIndex:Null<Int>;
	@:optional var bfZIndex:Null<Int>;
	@:optional var stageObjects:Array<NightmareVisionStageObject>;
}
typedef NightmareVisionStageObject =
{
	@:optional var id:Null<String>;
	@:optional var asset:Null<String>;
	@:optional var position:Array<Float>;
	@:optional var scrollFactor:Array<Float>;
	@:optional var scale:Array<Float>;
	@:optional var alpha:Null<Float>;
	@:optional var flipX:Null<Bool>;
	@:optional var flipY:Null<Bool>;
	@:optional var zIndex:Null<Int>;
	@:optional var angle:Null<Float>;
	@:optional var colour:Null<String>;
	@:optional var blend:Null<String>;
	@:optional var dance_every:Null<Int>;
	@:optional var antialiasing:Null<Bool>;
	@:optional var highQuality:Null<Bool>;
	@:optional var customInstance:Null<String>;
	@:optional var animations:Array<NightmareVisionStageAnimationInfo>;
	@:optional var advancedCalls:Array<{method:String, ?args:Array<Dynamic>}>;
	@:optional var setProperties:Array<{property:String, value:Dynamic}>;
}
typedef NightmareVisionStageAnimationInfo =
{
	var anim:String;
	var name:String;
	var fps:Int;
	var loop:Bool;
	@:optional var indices:Array<Int>;
	var offsets:Array<Int>;
	@:optional var flipX:Null<Bool>;
	@:optional var flipY:Null<Bool>;
}
