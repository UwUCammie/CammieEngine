package;

#if sys
import flixel.FlxG;
import flixel.FlxSprite;
import lime.app.Application;
import openfl.display.BitmapData;
import sys.io.File;

/** Opt-in generated component fixture, never a donor or chart override. */
@:access(RuntimeSmokeHarness)
class RuntimeLegacyAnimateProbe {
	static var started:Bool = false;
	static var renders:Int = 0;
	static var sprites:Array<NightmareVisionLegacyFlxAnimate> = [];
	static var owner:NightmareVisionSpriteOwner;
	static var scope:SourceNativeClassScope;
	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_LEGACY_ANIMATE_SMOKE') == '1';
	static function check(value:Bool, message:String):Void if (!value) throw message;
	static function matrix(x:Float = 0, y:Float = 0):Array<Float>
		return [1,0,0,0,0,1,0,0,0,0,1,0,x,y,0,1];
	public static function tick():Void {
		if (!enabled() || started || RuntimeSmokeHarness.finished) return;
		if (!Std.isOfType(FlxG.state, FreeplayState) || ImportRefreshManager.browseTick().busy) return;
		started = true;
		try {
			check(FlxG.sound.muted && Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null, 'Muted private saves required');
			var bitmap = new BitmapData(64,32,true,0xFFFF0000);
			bitmap.fillRect(new openfl.geom.Rectangle(32,0,32,32), 0xFF00FF00);
			var frames:Array<Dynamic> = [for (i in 0...2) {I:i,DU:1,E:[{ASI:{N:i == 0 ? 'red' : 'green',M3D:matrix()}}]}];
			var manifest = haxe.Json.stringify({AN:{N:'generated',SN:'stage',TL:{L:[{LN:'pixels',FR:frames}]},
				STI:{SI:{SN:'stage',FF:1,LP:'PO',ST:'G',TRP:{x:0,y:0},M3D:matrix(30,20)}}},MD:{FRT:12}});
			var spritemap = haxe.Json.stringify({meta:{image:'pixels.png'},ATLAS:{SPRITES:[
				{SPRITE:{name:'red',x:0,y:0,w:32,h:32,rotated:false}},
				{SPRITE:{name:'green',x:32,y:0,w:32,h:32,rotated:false}}]}});
			var assets:Dynamic = {
				getText:function(id:String):String return switch(id) {
					case 'fixture/Animation.json': manifest;
					case 'fixture/spritemap.json': spritemap;
					default: throw 'Unexpected fixture identity: '+id;
				},
				getBitmapData:function(id:String):BitmapData {
					check(id == 'fixture/pixels.png', 'Unexpected fixture image identity'); return bitmap;
				},
				list:function(type:String):Array<String> return type == 'TEXT'
					? ['fixture/Animation.json','fixture/spritemap.json'] : ['fixture/pixels.png'],
				exists:function(id:String,type:String):Bool return id == 'fixture/spritemap.json' || id == 'fixture/pixels.png'
			};
			owner = new NightmareVisionSpriteOwner(function(path) throw 'Unexpected Sparrow lookup');
			FlxG.state.add(new FlxSprite().makeGraphic(FlxG.width,FlxG.height,0xFF000000));
			for (i in 0...2) {
				var sprite = new NightmareVisionLegacyFlxAnimate(100+i*200,300,'fixture',null,assets,owner,'generated-owner');
				sprite.antialiasing = false; sprite.active = false;
				FlxG.state.add(sprite); sprites.push(sprite);
			}
			check(sprites[0].library != sprites[1].library, 'Instance timelines share mutable library state');
			check(sprites[0].sourceAnim.curFrame == 1, 'Stage first frame was lost');
			sprites[1].sourceAnim.addBySymbol('offset','stage',12,false,20,40);
			sprites[1].sourceAnim.play('offset',true);
			check(sprites[0].sourceAnim.curFrame == 1 && sprites[1].sourceAnim.curFrame == 0, 'Independent source cursors lost');
			scope = new SourceNativeClassScope();
			scope.bindStaticField(sprites[1],'anim',function()return sprites[1].sourceAnim);
			check(scope.reflectFacade().getProperty(sprites[1],'anim') == sprites[1].sourceAnim, 'Native reflection route lost');
			Application.current.window.onRender.add(onRender,false,-1000);
		} catch(error:Dynamic) RuntimeSmokeHarness.fail('legacy-animate',Std.string(error));
	}
	static function onRender(context:lime.graphics.RenderContext):Void {
		if (RuntimeSmokeHarness.finished || ++renders < 4) return;
		Application.current.window.onRender.remove(onRender);
		try {
			var image = Application.current.window.readPixels(); check(image != null,'No framebuffer');
			File.saveBytes('tmp/legacy-animate-native.png', image.encode());
			// Check exact authored transforms in logical screen coordinates. The second
			// sprite must not inherit the atlas stage's (30,20) translation.
			var sx = image.width / FlxG.width; var sy = image.height / FlxG.height;
			var green = image.getPixel(Std.int(140*sx),Std.int(330*sy),lime.graphics.PixelFormat.ARGB32);
			var red = image.getPixel(Std.int(330*sx),Std.int(350*sy),lime.graphics.PixelFormat.ARGB32);
			check(green == 0x00FF00 && red == 0xFF0000, 'Native frame colors/positions differ: '+green+','+red);
			owner.release();
			var rejected = false;
			try sprites[1].sourceAnim.play('offset') catch(_:Dynamic) rejected = true;
			check(rejected, 'Released owner permits captured animation calls');
			for (sprite in sprites) {scope.unbindStaticFields(sprite);FlxG.state.remove(sprite,true);sprite.destroy();}
			scope.release(); sprites = [];
			RuntimeSmokeHarness.emit('legacy_animate_native_verified',{
				generatedAssets:true,receiptImport:false,independentCursors:true,firstFrame:1,
				stageTranslation:[30,20],namedTranslation:[20,40],ownerRelease:true,reflection:true});
			RuntimeSmokeHarness.succeed();
		} catch(error:Dynamic) RuntimeSmokeHarness.fail('legacy-animate-render',Std.string(error));
	}
}
#end
