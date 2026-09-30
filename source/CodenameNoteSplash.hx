package;

import flixel.graphics.frames.FlxAtlasFrames;
import flixel.FlxCamera;
import CodenameSplashData.CodenameSplashAnimation;

/** One owner-scoped Codename splash rendered on a native receptor. */
class CodenameNoteSplash extends NoteSplash {
	public var renderable(default, null):Bool = false;

	public function new(data:CodenameSplashData, frames:FlxAtlasFrames,
		animationData:CodenameSplashAnimation, direction:Int,
		receptor:Strumline.StrumNote, lineScale:Float, ?fallbackCameras:Array<FlxCamera>) {
		super(0, 0, direction, 'normal', true);
		if (data == null || frames == null || animationData == null || receptor == null)
			return;

		this.frames = frames;
		this.direction = direction;
		if (animationData.indices != null && animationData.indices.length > 0)
			animation.addByIndices('codenameSplash', animationData.prefix,
				animationData.indices, '', animationData.fps, animationData.loop);
		else
			animation.addByPrefix('codenameSplash', animationData.prefix,
				animationData.fps, animationData.loop);

		var registered = animation.getByName('codenameSplash');
		if (registered == null || registered.frames == null || registered.frames.length == 0)
			return;

		var effectiveScale = data.scale * lineScale;
		if (!Math.isFinite(effectiveScale))
			effectiveScale = data.scale;
		scale.set(effectiveScale, effectiveScale);
		alpha = data.alpha;
		antialiasing = data.antialiasing;
		updateHitbox();
		setPosition(receptor.x + 0.5 * (receptor.width - width) + animationData.x,
			receptor.y + 0.5 * (receptor.height - height) + animationData.y);
		scrollFactor.set(receptor.scrollFactor.x, receptor.scrollFactor.y);
		if (receptor.cameras != null && receptor.cameras.length > 0)
			cameras = receptor.cameras.copy();
		else if (fallbackCameras != null)
			cameras = fallbackCameras.copy();
		animation.play('codenameSplash', true);
		renderable = animation.curAnim != null;
	}
}
