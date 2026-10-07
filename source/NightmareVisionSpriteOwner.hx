package;

import flixel.graphics.frames.FlxAtlasFrames;

/** Borrowed atlas IO shared by a selected source owner, never a sprite lifetime. */
@:keep
class NightmareVisionSpriteOwner
{
	var loader:Null<String->FlxAtlasFrames>;
	public function new(loader:String->FlxAtlasFrames) this.loader = loader;
	public function rebind(loader:String->FlxAtlasFrames):Void this.loader = loader;
	public function release():Void loader = null;
	public function requireActive():Void
	{
		if (loader == null) throw '[nightmare-vision-sprite] Selected atlas owner has been released';
	}
	public function atlasFrames(path:String):FlxAtlasFrames
	{
		requireActive();
		return loader(path);
	}
}
