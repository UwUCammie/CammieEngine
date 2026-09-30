// Based on CodenameCrew/CodenameEngine-Dev at 945fc60afd2c8e000dc2c48d0a3417297ab54026.
// Modified for OpenFL 9.5.2 and owner-aware asset loading by Disappointing Plus.
// Licensed under Apache-2.0; see tools/licenses/CodenameEngine-Dev-LICENSE.txt.
package flx3d;

#if THREE_D_SUPPORT
import away3d.cameras.Camera3D;
import away3d.containers.ObjectContainer3D;
import away3d.entities.Mesh;
import away3d.entities.SegmentSet;
import away3d.entities.TextureProjector;
import away3d.events.Asset3DEvent;
import away3d.events.LoaderEvent;
import away3d.library.Asset3DLibrary;
import away3d.library.Asset3DLibraryBundle;
import away3d.library.assets.Asset3DType;
import away3d.lights.LightBase;
import away3d.loaders.misc.AssetLoaderContext;
import away3d.loaders.misc.AssetLoaderToken;
import away3d.loaders.parsers.*;
import away3d.materials.TextureMaterial;
import away3d.primitives.SkyBox;
import away3d.utils.Cast;
import flx3d.Flx3DUtil;
import haxe.io.Bytes;
import haxe.io.Path;
import openfl.Assets;
import openfl.utils.ByteArray;
import away3d.utils.Utils.expect;
import RuntimeSmokeHarness;
#end

// FlxView3D with helpers for easier updating
class Flx3DView extends FlxView3D {
	#if THREE_D_SUPPORT
	private static var __3DIDS:Int = 0;

	var meshes:Array<Mesh> = [];
	private var destroyed3DAssets:Bool = false;
	var smokeAssetCompleteCount:Int = 0;
	public function new(x:Float = 0, y:Float = 0, width:Int = -1, height:Int = -1) {
		if (!Flx3DUtil.is3DAvailable())
			throw "[Flx3DView] 3D is not available on this platform. Stages in use: " + Flx3DUtil.getUsed3D() + ", Max stages allowed: " + Flx3DUtil.getTotal3D() + ".";
		super(x, y, width, height);
		__cur3DStageID = __3DIDS++;
	}

	/** Read a model through the default OpenFL asset registry. Owner-bound views
	 * override this to enforce the selected import's asset root. */
	public function loadModelBytes(assetPath:String):Dynamic
		return Assets.getBytes(assetPath);

	/** Read a texture through the default OpenFL registry. A BitmapData is also
	 * accepted because Codename Paths.image() returns pixels rather than an ID. */
	public function loadTextureBitmap(texturePath:Dynamic):openfl.display.BitmapData {
		if (Std.isOfType(texturePath, openfl.display.BitmapData))
			return cast texturePath;
		return Assets.getBitmapData(Std.string(texturePath), true);
	}

	/** Callback dispatch point lets an owner-bound view restore its asset scope
	 * while Away3D reports asynchronous loader events. */
	public function invokeModelCallback(callback:Asset3DEvent->Void, event:Asset3DEvent):Void {
		if (callback != null) callback(event);
	}

	/** Preserve the legacy sibling-MTL mapping for ordinary OpenFL asset IDs.
	 * Owner-bound views override this with their scoped dependency resolver. */
	public function mapModelDependencies(context:AssetLoaderContext, assetPath:String,
		modelData:Dynamic):Void {
		var noExt = Path.withoutExtension(assetPath);
		context.mapUrlToData(Path.withoutDirectory(noExt) + '.mtl', noExt + '.mtl');
	}

	public function addModel(assetPath:String, callback:Asset3DEvent->Void, ?texturePath:Dynamic, smoothTexture:Bool = true) {

		if (RuntimeSmokeHarness.enabled()) {
			var runtimeClass = Type.getClass(this);
			RuntimeSmokeHarness.markStep('3d-view-instance:type='
				+ (runtimeClass == null ? 'null' : Type.getClassName(runtimeClass))
				+ ':path=' + assetPath);
		}
		// Keep the unconverted native bytes as Dynamic until the Bytes check.
		// Inferring ByteArrayData here inserts a C++ cast before the null check;
		// owner-backed FNFAssets returns haxe.io.Bytes, which that cast drops.
		var model:Dynamic = loadModelBytes(assetPath);
		if (model == null)
			throw 'Model at ${assetPath} was not found.';
		// Haxe/OpenFL return haxe.io.Bytes from disk, while Away3D's parsers
		// consume OpenFL ByteArrayData (or String for text models). Normalize
		// here so the default and owner-scoped loading paths agree.
		if (Std.isOfType(model, Bytes))
			model = ByteArray.fromBytes(cast model);

		var context = new AssetLoaderContext();
		var noExt = Path.withoutExtension(assetPath);
		trace(noExt);
		mapModelDependencies(context, assetPath, model);

		var material:TextureMaterial = null;
		if (texturePath != null)
			material = new TextureMaterial(Cast.bitmapTexture(loadTextureBitmap(texturePath)), smoothTexture);

		return loadData(model, context, switch(Path.extension(assetPath).toLowerCase()) {
			case "dae": new DAEParser();
			case "md2": new MD2Parser();
			case "md5": new MD5MeshParser();
			case "awd": new AWDParser();
			default:	new OBJParser();
		}, (event:Asset3DEvent) -> {
			if (event.asset != null && event.asset.assetType == Asset3DType.MESH) {
				var mesh:Mesh = cast event.asset;
				if (material != null)
					mesh.material = material;
				meshes.push(mesh);
			}
			invokeModelCallback(callback, event);
		});
	}

	private var __cur3DStageID:Int;
	private var _loaders:Map<Asset3DLibraryBundle, AssetLoaderToken> = [];

	private function loadData(data:Dynamic, context:AssetLoaderContext, parser:ParserBase, onAssetCallback:Asset3DEvent->Void):AssetLoaderToken {
		var token:AssetLoaderToken;

		var lib:Asset3DLibraryBundle;
		lib = Asset3DLibraryBundle.getInstance('Flx3DView-${__cur3DStageID}');
		token = lib.loadData(data, context, null, parser);

		token.addEventListener(Asset3DEvent.ASSET_COMPLETE, (event:Asset3DEvent) -> {
			if (RuntimeSmokeHarness.enabled()) {
				smokeAssetCompleteCount++;
				var type = event.asset == null ? 'null' : event.asset.assetType;
				var name = event.asset == null ? 'null' : event.asset.name;
				RuntimeSmokeHarness.markStep('3d-asset-complete:type=' + type + ':name=' + name
					+ ':count=' + smokeAssetCompleteCount);
			}
			// ! Taken from Loader3D https://github.com/openfl/away3d/blob/master/away3d/loaders/Loader3D.hx#L207-L232
			if (event.type == Asset3DEvent.ASSET_COMPLETE) {
				var obj:ObjectContainer3D = switch (event.asset.assetType) {
					case Asset3DType.LIGHT: expect(event.asset, LightBase);
					case Asset3DType.CONTAINER: expect(event.asset, ObjectContainer3D);
					case Asset3DType.MESH: expect(event.asset, Mesh);
					case Asset3DType.SKYBOX: expect(event.asset, SkyBox);
					case Asset3DType.TEXTURE_PROJECTOR: expect(event.asset, TextureProjector);
					case Asset3DType.CAMERA: expect(event.asset, Camera3D);
					case Asset3DType.SEGMENT_SET: expect(event.asset, SegmentSet);
					default: null;
				}
				if (obj != null && obj.parent == null)
					view.scene.addChild(obj);
			}

			if (onAssetCallback != null)
				onAssetCallback(event);
		});

		token.addEventListener(LoaderEvent.RESOURCE_COMPLETE, (_) -> {
			if (RuntimeSmokeHarness.enabled())
				RuntimeSmokeHarness.markStep('3d-resource-complete:assets=' + smokeAssetCompleteCount);
			trace("Loader Finished...");

		});

		_loaders.set(lib,token);

		return token;
	}

	override function destroy():Void {
		if (destroyed3DAssets) return;
		destroyed3DAssets = true;
		var oldMeshes = meshes;
		meshes = [];
		if (oldMeshes != null)
			for (mesh in oldMeshes)
				if (mesh != null) mesh.dispose();

		var bundle = Asset3DLibraryBundle.getInstance('Flx3DView-${__cur3DStageID}');
		if (bundle != null) bundle.stopAllLoadingSessions();
		@:privateAccess {
			if (bundle != null && bundle._loadingSessions != null) {
				for(load in bundle._loadingSessions) {
					if (load != null) load.dispose();
				}
			}
			Asset3DLibrary._instances.remove('Flx3DView-${__cur3DStageID}');
		}

		super.destroy();
	}

	public function addChild(c)
		view.scene.addChild(c);
	#end
}
