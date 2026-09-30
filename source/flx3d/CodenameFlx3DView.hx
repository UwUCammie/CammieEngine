package flx3d;

import CodenameFlx3DContext;
import CodenamePaths;
import FNFAssets;
import away3d.events.Asset3DEvent;
import away3d.loaders.misc.AssetLoaderContext;
import haxe.io.Path;
import openfl.display.BitmapData;

/** Codename's Flx3DView with selected-owner model and texture access. */
class CodenameFlx3DView extends Flx3DView {
	final ownerPaths:CodenamePaths;

	public function new(x:Float = 0, y:Float = 0, width:Int = -1, height:Int = -1) {
		ownerPaths = CodenameFlx3DContext.requireOwner();
		super(x, y, width, height);
	}

	override public function loadModelBytes(assetPath:String):Dynamic
		return FNFAssets.getBytes(ownerPaths.getPath(assetPath));

	override public function loadTextureBitmap(texturePath:Dynamic):BitmapData {
		if (Std.isOfType(texturePath, BitmapData))
			return cast texturePath;
		return FNFAssets.getBitmapData(ownerPaths.getPath(Std.string(texturePath)));
	}

	override public function mapModelDependencies(context:AssetLoaderContext,
		assetPath:String, modelData:Dynamic):Void {
		if (Path.extension(assetPath).toLowerCase() == 'obj')
			CodenameFlx3DAssetSource.mapObjDependencies(ownerPaths, context, assetPath, cast modelData);
		else
			super.mapModelDependencies(context, assetPath, modelData);
	}

	override public function invokeModelCallback(callback:Asset3DEvent->Void,
		event:Asset3DEvent):Void {
		if (callback == null) return;
		CodenameFlx3DContext.withOwner(ownerPaths, function():Void callback(event));
	}
}
