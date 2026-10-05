package;

import flixel.FlxCamera;
import flixel.FlxObject;
import flixel.FlxSprite;
import flixel.math.FlxPoint;
import hscript.Interp;
#if (!flash && sys)
import flixel.addons.display.FlxRuntimeShader;
import lime.graphics.opengl.GLProgram;
#end

/**
	Installs the Psych HScript preset surface on one selected source interpreter.
	Callback registration is delegated to a caller-owned, source-scoped bridge.
*/
@:access(PlayState)
class PsychHscriptSourceBindings {
	final host:PlayState;
	final interp:Interp;
	final origin:String;
	final callbackBridge:Dynamic;
	final parentLua:Dynamic;

	public function new(host:PlayState, interp:Interp, origin:String, callbackBridge:Dynamic) {
		this.host = host;
		this.interp = interp;
		this.origin = origin;
		this.callbackBridge = callbackBridge;
		this.parentLua = callbackBridge == null ? null
			: invokeBridge(callbackBridge, 'parentFacade', [origin, interp]);
	}

	public function install():Void {
		var variables = interp.variables;
		variables.set('Type', Type);
		variables.set('Countdown', PsychBaseStageCountdown);
		variables.set('Rating', PsychRatingCompat);
		variables.set('PsychCamera', PsychHscriptCamera);
		variables.set('CustomSubstate', new PsychHscriptCustomSubstateFacade(host));
		variables.set('parentLua', parentLua);
		var selfFactory = callbackBridge == null ? null : Reflect.field(callbackBridge, 'selfFacade');
		if (Reflect.isFunction(selfFactory))
			variables.set('this', Reflect.callMethod(callbackBridge, selfFactory,
				[origin, interp, parentLua]));
		variables.set('game', host);
		variables.set('buildTarget', sourceBuildTarget());
		variables.set('customSubstate', host.compatCustomSubstate);
		variables.set('customSubstateName', host.compatCustomSubstate == null
			? 'unnamed' : host.compatCustomSubstate.customName);

		variables.set('setVar', function(name:String, value:Dynamic):Dynamic {
			return setSharedVar(host.psychScriptVariables, name, value);
		});
		variables.set('getVar', function(name:String):Dynamic {
			return getSharedVar(host.psychScriptVariables, name);
		});
		variables.set('removeVar', function(name:String):Bool {
			return removeSharedVar(host.psychScriptVariables, name);
		});
		variables.set('createGlobalCallback', function(name:String, func:Dynamic):Void {
			registerGlobal(callbackBridge, origin, name, func);
		});
		variables.set('createCallback', function(name:String, func:Dynamic,
			?parent:Dynamic):Void {
			var target = parent == null ? parentLua : parent;
			if (target == null)
				throw 'createCallback ($name): source has no parent Lua callback scope';
			registerLocal(callbackBridge, origin, name, func, target);
		});

		#if (!flash && sys)
		variables.set('ErrorHandledRuntimeShader', PsychHscriptErrorHandledRuntimeShader);
		#end
	}

	static function invokeBridge(bridge:Dynamic, methodName:String, args:Array<Dynamic>):Dynamic {
		if (bridge == null) throw '[psych-hscript] callback bridge is unavailable';
		var method = Reflect.field(bridge, methodName);
		if (!Reflect.isFunction(method))
			throw '[psych-hscript] callback bridge must implement $methodName';
		return Reflect.callMethod(bridge, method, args);
	}

	static function registerLocal(bridge:Dynamic, origin:String, name:String,
		func:Dynamic, parent:Dynamic):Void {
		invokeBridge(bridge, 'registerLocal', [origin, name, func, parent]);
	}

	static function registerGlobal(bridge:Dynamic, origin:String, name:String,
		func:Dynamic):Void {
		invokeBridge(bridge, 'registerGlobal', [origin, name, func]);
	}

	static function setSharedVar(variables:Map<String, Dynamic>, name:String,
		value:Dynamic):Dynamic {
		variables.set(name, value);
		return value;
	}

	static function getSharedVar(variables:Map<String, Dynamic>, name:String):Dynamic {
		return variables.get(name);
	}

	static function removeSharedVar(variables:Map<String, Dynamic>, name:String):Bool {
		return variables.remove(name);
	}

	static function platformBuildTarget(platform:String, x86:Bool = false):String {
		return switch (platform) {
			case 'windows': x86 ? 'windows_x86' : 'windows';
			case 'linux': 'linux';
			case 'mac': 'mac';
			case 'html5': 'browser';
			case 'android': 'android';
			case 'switch': 'switch';
			default: 'unknown';
		};
	}

	static function sourceBuildTarget():String {
		#if windows
			#if x86_BUILD
		return platformBuildTarget('windows', true);
			#else
		return platformBuildTarget('windows');
			#end
		#elseif linux
		return platformBuildTarget('linux');
		#elseif mac
		return platformBuildTarget('mac');
		#elseif html5
		return platformBuildTarget('html5');
		#elseif android
		return platformBuildTarget('android');
		#elseif switch
		return platformBuildTarget('switch');
		#else
		return platformBuildTarget('unknown');
		#end
	}
}

/** Psych camera follow math copied from Psych 1.0.4's backend.PsychCamera. */
class PsychHscriptCamera extends FlxCamera {
	override public function update(elapsed:Float):Void {
		if (target != null) updateFollowDelta(elapsed);
		updateScroll();
		updateFlash(elapsed);
		updateFade(elapsed);
		flashSprite.filters = filtersEnabled ? filters : null;
		updateFlashSpritePosition();
		updateShake(elapsed);
	}

	public function updateFollowDelta(?elapsed:Float = 0):Void {
		if (deadzone == null) {
			target.getMidpoint(_point);
			_point.addPoint(targetOffset);
			_scrollTarget.set(_point.x - width * 0.5, _point.y - height * 0.5);
		} else {
			var targetX:Float = target.x + targetOffset.x;
			var targetY:Float = target.y + targetOffset.y;
			if (style == SCREEN_BY_SCREEN) {
				if (targetX >= viewRight) _scrollTarget.x += viewWidth;
				else if (targetX + target.width < viewLeft) _scrollTarget.x -= viewWidth;
				if (targetY >= viewBottom) _scrollTarget.y += viewHeight;
				else if (targetY + target.height < viewTop) _scrollTarget.y -= viewHeight;
				bindScrollPos(_scrollTarget);
			} else {
				var edge = targetX - deadzone.x;
				if (_scrollTarget.x > edge) _scrollTarget.x = edge;
				edge = targetX + target.width - deadzone.x - deadzone.width;
				if (_scrollTarget.x < edge) _scrollTarget.x = edge;
				edge = targetY - deadzone.y;
				if (_scrollTarget.y > edge) _scrollTarget.y = edge;
				edge = targetY + target.height - deadzone.y - deadzone.height;
				if (_scrollTarget.y < edge) _scrollTarget.y = edge;
			}
			if (Std.isOfType(target, FlxSprite)) {
				if (_lastTargetPosition == null)
					_lastTargetPosition = FlxPoint.get(target.x, target.y);
				_scrollTarget.x += (target.x - _lastTargetPosition.x) * followLead.x;
				_scrollTarget.y += (target.y - _lastTargetPosition.y) * followLead.y;
				_lastTargetPosition.set(target.x, target.y);
			}
		}
		var mult:Float = 1 - Math.exp(-elapsed * followLerp / (1 / 60));
		scroll.x += (_scrollTarget.x - scroll.x) * mult;
		scroll.y += (_scrollTarget.y - scroll.y) * mult;
	}

}

/** Owner-captured static Psych CustomSubstate surface. */
@:access(PlayState)
class PsychHscriptCustomSubstateFacade {
	final owner:PlayState;

	public function new(owner:PlayState) this.owner = owner;

	public var name(get, never):String;
	function get_name():String {
		return owner == null || owner.compatCustomSubstate == null
			? 'unnamed' : owner.compatCustomSubstate.customName;
	}

	public var instance(get, never):PsychCustomSubstate;
	function get_instance():PsychCustomSubstate {
		return owner == null ? null : owner.compatCustomSubstate;
	}

	public function openCustomSubstate(name:String, pauseGame:Bool = false):Void {
		if (owner != null) owner.compatOpenCustomSubstate(name, pauseGame);
	}

	public function closeCustomSubstate():Bool {
		return owner != null && owner.compatCloseCustomSubstate();
	}

	public function insertToCustomSubstate(tag:String, pos:Int = -1):Bool {
		if (owner == null || owner.compatCustomSubstate == null) return false;
		var object = owner.psychScriptVariables.get(tag);
		if (!Std.isOfType(object, FlxObject)) return false;
		if (pos < 0) owner.compatCustomSubstate.add(cast object);
		else owner.compatCustomSubstate.insert(pos, cast object);
		return true;
	}
}

#if (!flash && sys)
/** Source-compatible constructor and compile-error callback without donor crash I/O. */
class PsychHscriptErrorHandledRuntimeShader extends FlxRuntimeShader {
	public var shaderName:String = '';
	public dynamic function onError(error:Dynamic):Void {}

	public function new(?shaderName:String, ?fragmentSource:String, ?vertexSource:String) {
		this.shaderName = shaderName == null ? '' : shaderName;
		super(fragmentSource, vertexSource);
	}

	override function __createGLProgram(vertexSource:String, fragmentSource:String):GLProgram {
		try return super.__createGLProgram(vertexSource, fragmentSource) catch (error:Dynamic) {
			try onError(error) catch (_:Dynamic) {}
			return null;
		}
	}
}
#end
