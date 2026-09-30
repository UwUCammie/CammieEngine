package;

import flixel.system.FlxAssets.FlxShader;
import flixel.addons.display.FlxRuntimeShader;
import flixel.FlxSprite;
import hscript.Interp;
import hscript.ParserEx;
import hscript.InterpEx;
using StringTools;

class ShaderHandler {
	// stuff
	var hscriptStates:Map<String, Interp> = [];
	var exInterp:InterpEx = new InterpEx();
	var haxeSprites:Map<String, FlxSprite> = [];
	function callHscript(func_name:String, args:Array<Dynamic>, usehaxe:String) {
		// if function doesn't exist
		if (!hscriptStates.get(usehaxe).variables.exists(func_name)) {
			trace("Function doesn't exist, silently skipping...");
			return;
		}
		var method = hscriptStates.get(usehaxe).variables.get(func_name);
		switch(args.length) {
			case 0:
				method();
			case 1:
				method(args[0]);
		}
	}
	function callAllHScript(func_name:String, args:Array<Dynamic>) {
		for (key in hscriptStates.keys()) {
			callHscript(func_name, args, key);
		}
	}
	function setHaxeVar(name:String, value:Dynamic, usehaxe:String) {
		hscriptStates.get(usehaxe).variables.set(name,value);
	}
	function getHaxeVar(name:String, usehaxe:String):Dynamic {
		return hscriptStates.get(usehaxe).variables.get(name);
	}
	function setAllHaxeVar(name:String, value:Dynamic) {
		for (key in hscriptStates.keys())
			setHaxeVar(name, value, key);
	}
	function makeHaxeState(usehaxe:String, path:String, filename:String, daShader:Dynamic) {
		trace("opening a haxe state (because we are cool :))");
		var parser = new ParserEx();
		var program = parser.parseString(FNFAssets.getHscript(path + filename));
		var interp = PluginManager.createSimpleInterp();
		// set vars
		interp.variables.set("FlxShader", FlxShader);
		interp.variables.set("shader", daShader);
		interp.variables.set("create", function create() {} );
		interp.variables.set("update", function update(elapsed) {} );
		// stuff
		trace("set stuff");
		interp.execute(program);
		hscriptStates.set(usehaxe,interp);
		trace('executed');
	}


	public function new(shader:String):Void {
		//var frag = FNFAssets.getText("assets/shaders/" + shader + "/shader.frag");
		//makeHaxeState("shader", "assets/shaders/", shader, new CoolRuntimeShader(frag));
		//callAllHScript("new", []);
	}

	public function update(elapsed:Float):Void {
		//callAllHScript("update", [elapsed]);
	}
}

class CoolRuntimeShader extends FlxRuntimeShader {
	//uhhhhhh
	public function new(frag, ?vertex:String) {
		if ((frag is String)) {
			var s:String = frag;
			// old-engine scripts pass RAW GLSL source (lofright's stage
			// grayscale, etc.) - if it looks like shader code, hand it
			// straight through instead of treating it as a shader NAME and
			// trying to read 'assets/shaders/#pragma header...}.frag'
			if (StringTools.ltrim(s).indexOf('#pragma') == 0 || s.indexOf('void main') != -1) {
				super(CodenameShaderSource.normalizeOpenFL(s), vertex == null ? null : CodenameShaderSource.normalizeOpenFL(vertex));
				return;
			}
			var path = ShaderPaths.resolve(s);
			if (path == null) throw 'Shader not found: $s';
			s = FNFAssets.getText(path);
			super(CodenameShaderSource.normalizeOpenFL(s), vertex == null ? null : CodenameShaderSource.normalizeOpenFL(vertex));
			return;
		}
		 super(frag, vertex);
	}

	/**
		Small ScriptedFlxRuntimeShader compatibility surface used by imported HXC
		modules. Keep the bridge explicit: generic donor script methods are not
		reflected into the native shader, while the common Vignette intensity pair
		maps to the native uniform spelling.
	*/
	public function scriptCall(methodName:String, ?args:Array<Dynamic>):Dynamic {
		if (methodName == 'setIntensity') {
			var value:Float = 0;
			if (args != null && args.length > 0 && args[0] != null) {
				var parsed = Std.parseFloat(Std.string(args[0]));
				if (!Math.isNaN(parsed))
					value = parsed;
			}
			setFloat('u_intensity', value);
		}
		return null;
	}

	public function scriptGet(fieldName:String):Dynamic {
		var uniform = fieldName == 'uIntensity' ? 'u_intensity' : fieldName;
		return getFloat(uniform);
	}
}
