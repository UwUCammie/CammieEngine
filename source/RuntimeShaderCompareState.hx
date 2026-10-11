package;

import flixel.FlxG;
import flixel.FlxState;
import flixel.FlxSprite;
import flixel.addons.display.FlxRuntimeShader;
import lime.app.Application;

/** Opt-in native pixel comparison with identical textures, uniforms and times. */
class RuntimeShaderCompareState extends FlxState {
	#if sys
	var shaders:Array<FlxRuntimeShader> = [];
	var times:Array<Float> = [0, 1, 10, 80, 175, 230];
	var cases:Array<Dynamic> = [{}];
	var timeUniforms:Array<String> = ['iTime'];
	var settings:Dynamic;
	var index:Int = 0;
	var caseIndex:Int = 0;
	var frames:Int = 0;
	var listener:lime.graphics.RenderContext->Void;
	var output:String;
	#end
	override public function create():Void {
		super.create();
		#if sys
		FlxG.sound.muted = true;
		Application.current.window.resize(1280,720);
		FlxG.mouse.visible = false;
		if (Main.fpsCounter != null) Main.fpsCounter.visible = false;
		output = Sys.getEnv('CAMMIE_SHADER_COMPARE_OUTPUT');
		if (output == null) throw 'Shader comparison requires an explicit output directory';
		if (!sys.FileSystem.exists(output)) sys.FileSystem.createDirectory(output);
		var configPath = Sys.getEnv('CAMMIE_SHADER_COMPARE_CONFIG');
		if (configPath != null) settings = haxe.Json.parse(sys.io.File.getContent(configPath));
		if (settings != null) {
			if (settings.cases != null) cases = cast settings.cases;
			if (settings.times != null) times = cast settings.times;
			if (settings.timeUniforms != null) timeUniforms = cast settings.timeUniforms;
		}
		if (cases.length == 0 || times.length == 0) throw 'Shader comparison requires nonempty cases and times';
		if (Sys.getEnv('CAMMIE_SHADER_OPTIMIZATIONS') != '0') throw 'Reference normalization must disable optimizations';
		var original = CodenameShaderSource.normalizeOpenFL(sys.io.File.getContent(Sys.getEnv('CAMMIE_SHADER_COMPARE')));
		var optimized = settings != null && settings.candidatePath != null
			? sys.io.File.getContent(settings.candidatePath) : ShaderSourceOptimizer.nearestDistance(original);
		if (original == optimized) throw 'No shader reduction matched';
		sys.io.File.saveContent(output + '/reference.frag',original);
		sys.io.File.saveContent(output + '/candidate.frag',optimized);
		var width:Int = settings != null && settings.inputWidth != null ? settings.inputWidth : 3680;
		var height:Int = settings != null && settings.inputHeight != null ? settings.inputHeight : 2920;
		var color:Int = settings != null && settings.inputColor != null ? Std.parseInt(settings.inputColor) : 0xFFFFFFFF;
		for (side in 0...2) {
			var shader = new FlxRuntimeShader(side == 0 ? original : optimized);
			for (entry in [{name:'red_amt',value:0.1},{name:'green_amt',value:0.17},{name:'blue_amt',value:0.3}])
				if (Reflect.hasField(shader.data,entry.name)) shader.setFloat(entry.name,entry.value);
			shaders.push(shader);
			var sprite = new FlxSprite(side * 640, 0).makeGraphic(width,height,color);
			sprite.setGraphicSize(640,720);sprite.updateHitbox();sprite.shader = shader;
			sprite.antialiasing = true;add(sprite);
		}
		applyInputs();
		listener = function(_) {
			if (++frames < 4) return;
			frames = 0;
			for (shader in shaders) if (Reflect.field(shader,'glProgram') == null) throw 'Comparison shader did not compile';
			var prefix = settings == null ? '' : 'case-' + caseIndex + '-';
			sys.io.File.saveBytes(output + '/' + prefix + 'time-' + times[index] + '.png',Application.current.window.readPixels().encode());
			if (++index >= times.length) {index = 0;caseIndex++;}
			if (caseIndex >= cases.length) {
				Application.current.window.onRender.remove(listener);
				sys.io.File.saveContent(output + '/complete.json',haxe.Json.stringify({times:times,cases:cases,width:1280,height:720,reference:'left',candidate:'right'}));
				Sys.exit(0);
			}
			applyInputs();
		};
		Application.current.window.onRender.add(listener,false,-1001);
		#end
	}
	#if sys
	function applyInputs():Void {
		for (shader in shaders) {
			for (input in [settings,cases[caseIndex]]) if (input != null) {
				var floats:Dynamic = Reflect.field(input,'floats');
				if (floats != null) for (name in Reflect.fields(floats)) shader.setFloat(name,Reflect.field(floats,name));
				var ints:Dynamic = Reflect.field(input,'ints');
				if (ints != null) for (name in Reflect.fields(ints)) shader.setInt(name,Reflect.field(ints,name));
			}
			for (name in timeUniforms) if (Reflect.hasField(shader.data,name)) shader.setFloat(name,times[index]);
		}
	}
	#end
}
