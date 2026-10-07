package;

#if sys
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.graphics.FlxGraphic;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.addons.display.FlxRuntimeShader;
import haxe.crypto.Sha256;
import haxe.io.Path;
import lime.app.Application;
import openfl.text.Font;
import sys.FileSystem;
import sys.io.File;
using StringTools;

/** Generated private imports only. Verify publication through actual native loaders. */
@:access(RuntimeSmokeHarness)
class RuntimeMappedMediaProbe {
	static var started:Bool = false;
	static var renders:Int = 0;
	static var sprites:Array<FlxSprite> = [];
	static var nvPaths:NightmareVisionPaths;
	static var evidence:Dynamic;
	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_MAPPED_MEDIA_SMOKE') == '1';
	static function check(value:Bool, message:String):Void if (!value) throw message;
	public static function tick():Void {
		if (!enabled() || started || RuntimeSmokeHarness.finished) return;
		if (!Std.isOfType(FlxG.state, FreeplayState) || ImportRefreshManager.browseTick().busy) return;
		started = true;
		try {
			check(FlxG.sound.muted && Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null,
				'Muted private saves required');
			var request:Dynamic = CoolUtil.parseJson(File.getContent('tmp/mapped-media-request.json'));
			check(request.kind == 'mapped-media-native-v17' || request.kind == 'asset-identities-native-v17',
				'Expected generated native media fixture');
			var psychRoot:String = request.psychRoot;
			var nvRoot:String = request.nvRoot;
			check(psychRoot != nvRoot && psychRoot.startsWith('assets/imported_mods/')
				&& nvRoot.startsWith('assets/imported_mods/'), 'Separate receipt-owned namespaces required');
			for (item in (cast request.files:Array<Dynamic>)) {
				var path:String = item.path;
				check(path.startsWith(psychRoot + '/') || path.startsWith(nvRoot + '/'), 'Expected owner media path');
				check(Sha256.make(File.getBytes(path)).toHex() == item.sha256,
					'Published bytes differ from generated source: ' + path);
			}
			var psych = PsychOwnerPaths.create(psychRoot);
			var graphic:FlxGraphic = Reflect.callMethod(psych, Reflect.field(psych, 'image'), ['mapped-sheet']);
			verifyGraphic(graphic, 'Psych image');
			var atlas:FlxAtlasFrames = Reflect.callMethod(psych, Reflect.field(psych, 'getSparrowAtlas'), ['mapped-sheet']);
			check(atlas != null && atlas.frames.length == 2, 'Psych atlas metadata lost its frames');
			var raw:String = Reflect.callMethod(psych, Reflect.field(psych, 'file'), ['custom/mapped-pixels.bin']);
			verifyBitmap(raw, 'Psych typed custom path');
			var sound:Dynamic = Reflect.callMethod(psych, Reflect.field(psych, 'sound'), ['mapped-sound']);
			var music:Dynamic = Reflect.callMethod(psych, Reflect.field(psych, 'music'), ['mapped-music']);
			check(Std.isOfType(sound, openfl.media.Sound) && Std.isOfType(music, openfl.media.Sound),
				'Psych sound/music did not return source Sound objects');
			check(sound == Reflect.callMethod(psych, Reflect.field(psych, 'sound'), ['mapped-sound']),
				'Psych audio cache did not reuse the decoded owner Sound');
			var decoded = FlxG.sound.load(sound);
			var musicDecoded = FlxG.sound.load(music);
			check(decoded != null && decoded.length > 0 && musicDecoded != null && musicDecoded.length > 0,
				'Psych sound/music could not decode');
			decoded.destroy(); musicDecoded.destroy();
			var font:String = Reflect.callMethod(psych, Reflect.field(psych, 'font'), ['mapped-font.otf']);
			check(Font.fromFile(font) != null, 'Psych font could not decode');
			var fragment:String = Reflect.callMethod(psych, Reflect.field(psych, 'shaderFragment'), ['mapped-shader']);
			var video:String = Reflect.callMethod(psych, Reflect.field(psych, 'video'), ['mapped-video']);
			check(FileSystem.exists(video) && FileSystem.stat(video).size > 100, 'Psych video path was not published');
			addGraphic(graphic, 140, 220, FNFAssets.getText(fragment));
			addAtlas(atlas, 400, 220);

			nvPaths = new NightmareVisionPaths(nvRoot);
			var core = nvPaths.image('mapped-sheet', null, true, false);
			verifyGraphic(core, 'NV core image');
			check(nvPaths.getPath('images/mapped-sheet.png', null, false).startsWith(nvRoot + '/__nmv_core/'),
				'NV core lookup was replaced by a package lookup');
			check(nvPaths.getPath('images/mapped-sheet.png', null, true)
				== nvPaths.getPath('images/mapped-sheet.png', null, false), 'Absent NV override did not resolve core');
			verifyBitmap(nvPaths.getPath('custom/mapped-pixels.bin', null, false), 'NV typed custom core path');
			var coreAtlas = nvPaths.getSparrowAtlas('mapped-sheet', null, true, false);
			check(coreAtlas != null && coreAtlas.frames.length == 2, 'NV core atlas lost its frames');
			check(nvPaths.sound('mapped-sound', null, false).length > 0
				&& nvPaths.music('mapped-music', null, false).length > 0, 'NV core sound/music could not decode');
			check(Font.fromFile(nvPaths.font('mapped-font', false)) != null, 'NV core font could not decode');
			check(FileSystem.exists(nvPaths.video('mapped-video', null, false)), 'NV core video path missing');
			addGraphic(core, 660, 220, FNFAssets.getText(nvPaths.fragment('mapped-shader', false)));
			addAtlas(coreAtlas, 920, 220);
			if (request.identityProbe == true) verifyIdentities(psychRoot, nvRoot);
			evidence = {psychRoot:psychRoot, nvRoot:nvRoot, publishedByteHashes:true,
				images:true, customTypedPaths:true, atlasFrames:2, soundAndMusicDecode:true,
				fontDecode:true, shaderRendering:true, videoPathOnly:true,
				identityAliases:request.identityProbe == true, psychSoundObjects:true};
			Application.current.window.onRender.add(onRender, false, -1000);
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('mapped-media', Std.string(error));
	}

	static function verifyIdentities(psychRoot:String, nvRoot:String):Void {
		var openfl = PsychOwnerOpenFlAssets.create(psychRoot);
		var lime = PsychOwnerLimeAssets.create(psychRoot);
		for (facade in [openfl, lime]) {
			check(Reflect.callMethod(facade, Reflect.field(facade, 'exists'), ['visuals:art-alias', 'IMAGE']),
				'Qualified image identity unavailable');
			check(!Reflect.callMethod(facade, Reflect.field(facade, 'exists'), ['visuals:art-alias', 'FONT']),
				'Qualified image accepted as wrong asset type');
			check(!Reflect.callMethod(facade, Reflect.field(facade, 'hasLibrary'), ['empty-test']),
				'Bare library configuration incorrectly created an AssetLibrary');
			check(!Reflect.callMethod(facade, Reflect.field(facade, 'exists'), ['empty-test:absent', 'IMAGE']),
				'Empty owner library borrowed an unrelated asset');
			var selected:String = Reflect.callMethod(facade, Reflect.field(facade, 'getPath'), ['visuals:picked-art']);
			check(selected == psychRoot + '/images/mapped-sheet.png', 'Last declared identity did not win');
			var text:String = Reflect.callMethod(facade, Reflect.field(facade, 'getText'), ['note-alias']);
			check(text == 'Owner asset identity text\n', 'TEXT identity bytes changed');
			var bytes:Dynamic = Reflect.callMethod(facade, Reflect.field(facade, 'getBytes'), ['bytes-alias']);
			check(bytes != null && Reflect.getProperty(bytes, 'length') == 4, 'BINARY identity missing');
			var listed:Array<String> = Reflect.callMethod(facade, Reflect.field(facade, 'list'), ['IMAGE']);
			check(listed.indexOf('art-alias') >= 0 && listed.indexOf('picked-art') >= 0,
				'Owner identities omitted from typed list');
		}
		var bitmap:openfl.display.BitmapData = Reflect.callMethod(openfl,
			Reflect.field(openfl, 'getBitmapData'), ['visuals:art-alias']);
		check(bitmap != null && bitmap.getPixel32(1, 1) == 0xFF19CC55, 'OpenFL identity pixel altered');
		var facade = new NightmareVisionFunkinAssets(nvPaths);
		check(facade.getContent('note-alias') == 'Owner asset identity text\n', 'NV core TEXT identity missing');
		var coreBitmap = facade.getBitmapData('visuals:art-alias');
		check(coreBitmap != null && coreBitmap.getPixel32(1, 1) == 0xFF19CC55, 'NV identity pixel altered');
		var psych = RuntimeOwnerAssetIdentity.acquire(psychRoot, 'Psych Engine', 'package');
		var core = RuntimeOwnerAssetIdentity.acquire(nvRoot, 'Nightmare Vision', 'core');
		check(psych.bindingState == 'ready' && core.bindingState == 'ready',
			'Native identity index lacks a committed receipt');
		var psychPath = psych.resolveAssetId('visuals:art-alias', 'IMAGE').path;
		var corePath = core.resolveAssetId('visuals:art-alias', 'IMAGE').path;
		check(psychPath.startsWith(psychRoot + '/') && corePath.startsWith(nvRoot + '/__nmv_core/')
			&& psychPath != corePath, 'Logical identity leaked between namespaces');
	}
	static function verifyGraphic(graphic:FlxGraphic, label:String):Void {
		check(graphic != null && graphic.bitmap != null && graphic.width == 64 && graphic.height == 32,
			label + ' dimensions differ');
		check(graphic.bitmap.getPixel32(4, 4) == 0xFF19CC55 && graphic.bitmap.getPixel32(40, 4) == 0xFFFF6633,
			label + ' pixel colors differ');
		check(graphic.bitmap.getPixel32(0, 0) == 0, label + ' transparency differs');
	}
	static function verifyBitmap(path:String, label:String):Void {
		check(path != null && FileSystem.exists(path), label + ' path missing');
		var bitmap = FNFAssets.getBitmapData(path);
		check(bitmap != null && bitmap.width == 64 && bitmap.getPixel32(4, 4) == 0xFF19CC55,
			label + ' decode differs');
	}
	static function addGraphic(graphic:FlxGraphic, x:Float, y:Float, shader:String):Void {
		var sprite = new FlxSprite(x, y).loadGraphic(graphic);
		sprite.scale.set(3, 3); sprite.updateHitbox();
		sprite.shader = new FlxRuntimeShader(shader);
		FlxG.state.add(sprite); sprites.push(sprite);
	}
	static function addAtlas(frames:FlxAtlasFrames, x:Float, y:Float):Void {
		var sprite = new FlxSprite(x, y); sprite.frames = frames;
		sprite.animation.addByPrefix('loop', 'frame', 4, true); sprite.animation.play('loop');
		sprite.scale.set(3, 3); sprite.updateHitbox(); FlxG.state.add(sprite); sprites.push(sprite);
	}
	static function onRender(context:lime.graphics.RenderContext):Void {
		if (RuntimeSmokeHarness.finished || ++renders < 4) return;
		Application.current.window.onRender.remove(onRender);
		try {
			var pixels = Application.current.window.readPixels(); check(pixels != null, 'Missing native mapped media framebuffer');
			for (sprite in sprites) if (sprite.shader != null)
				check(sprite.shader.glProgram != null, 'Mapped shader did not compile during native rendering');
			File.saveBytes('tmp/mapped-media-native.png', pixels.encode());
			for (sprite in sprites) {FlxG.state.remove(sprite, true); sprite.destroy();}
			sprites = [];
			nvPaths.releaseOwnerAssets();
			RuntimeSmokeHarness.emit('mapped_media_native_verified', evidence);
			RuntimeSmokeHarness.succeed();
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('mapped-media-render', Std.string(error));
	}
}
#end
