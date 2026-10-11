package;

#if macro
import haxe.macro.Context;
import haxe.macro.Expr;
#end

/** Generate only native super trampolines; runtime ownership is shared. */
class SourceNativeClassAdapterMacro {
	#if macro
	public static function build(animation:Bool = true, object:Bool = false, spriteGroup:Bool = false):Array<Field> {
		var fields = Context.getBuildFields();
		// Bind the actual instance before native super() can dispatch virtual hooks.
		for (field in fields) if (field.name == 'new') switch (field.kind) {
			case FFun(fn):
				fn.args.unshift({name:'bindBeforeSuper', opt:true, type:macro : SourceNativeClassAdapter->Void});
				var body = fn.expr;
				fn.expr = macro {if (bindBeforeSuper != null) bindBeforeSuper(this);$body;};
			default:
		}
		var adapter = macro class NativeClassCallbacks extends flixel.FlxBasic {
			public var sourceLifecycle(default, null):SourceNativeClassLifecycle;
			public function bind(owner:hscript.ScriptClass, scope:hscript.ScriptClassScope):Void {
				if (sourceLifecycle != null) throw '[source-native] Native adapter already has an owner';
				sourceLifecycle = new SourceNativeClassLifecycle(owner, scope, callNativeBase);
			}
			public function scriptOwner():hscript.ScriptClass return sourceLifecycle == null ? null : sourceLifecycle.owner;
			function dispatchSource(name:String, args:Array<Dynamic>):Void {
				// Unowned direct adapter construction retains the native implementation.
				if (sourceLifecycle == null) callNativeBase(name, args);
				else sourceLifecycle.dispatch(name, args);
			}
			function dispatchSourceResult(name:String, args:Array<Dynamic>):Dynamic
				return sourceLifecycle == null ? callNativeBase(name, args) : sourceLifecycle.dispatchResult(name, args);
			override function set_visible(value:Bool):Bool return cast dispatchSourceResult('set_visible', [value]);
			override function set_active(value:Bool):Bool return cast dispatchSourceResult('set_active', [value]);
			override function set_exists(value:Bool):Bool return cast dispatchSourceResult('set_exists', [value]);
			override function set_alive(value:Bool):Bool return cast dispatchSourceResult('set_alive', [value]);
			override function get_camera():flixel.FlxCamera return cast dispatchSourceResult('get_camera', []);
			override function set_camera(value:flixel.FlxCamera):flixel.FlxCamera return cast dispatchSourceResult('set_camera', [value]);
			override function get_cameras():Array<flixel.FlxCamera> return cast dispatchSourceResult('get_cameras', []);
			override function set_cameras(value:Array<flixel.FlxCamera>):Array<flixel.FlxCamera> return cast dispatchSourceResult('set_cameras', [value]);
			override public function update(elapsed:Float):Void dispatchSource('update', [elapsed]);
			override public function draw():Void dispatchSource('draw', []);
			override public function kill():Void dispatchSource('kill', []);
			override public function revive():Void dispatchSource('revive', []);
			override public function destroy():Void dispatchSource('destroy', []);
			public function supportsNativeSuper(name:String):Bool return SourceNativeClassLifecycle.hasNativeSuper(name, $v{animation}, $v{animation || object}, $v{spriteGroup});
			public function callNativeSuper(name:String, args:Array<Dynamic>):Dynamic {
				return sourceLifecycle == null ? callNativeBase(name, args) : sourceLifecycle.callNativeSuper(name, args);
			}
			function callNativeBase(name:String, args:Array<Dynamic>):Dynamic {
				switch (name) {
					case 'set_visible': return super.set_visible(args[0]);
					case 'set_active': return super.set_active(args[0]);
					case 'set_exists': return super.set_exists(args[0]);
					case 'set_alive': return super.set_alive(args[0]);
					case 'get_camera': return super.get_camera();
					case 'set_camera': return super.set_camera(args[0]);
					case 'get_cameras': return super.get_cameras();
					case 'set_cameras': return super.set_cameras(args[0]);
					case 'update': super.update(args[0]);
					case 'draw': super.draw();
					case 'kill': super.kill();
					case 'revive': super.revive();
					case 'destroy': super.destroy();
					default: throw '[source-native] Unsupported native super method: ' + name;
				}
				return null;
			}
		};
		var addCallbacks = function(extra:TypeDefinition, nativeCases:Array<Case>):Void {
			adapter.fields = adapter.fields.concat(extra.fields);
			for (field in adapter.fields) if (field.name == 'callNativeBase') switch (field.kind) {
				case FFun(fn): switch (fn.expr.expr) {
					case EBlock(expressions): switch (expressions[0].expr) {
						case ESwitch(subject, cases, fallback):
							for (nativeCase in nativeCases) cases.push(nativeCase);
						default:
					}
					default:
				}
				default:
			}
		};
		if (animation) {
			var extra = macro class SpriteCallbacks extends flixel.FlxSprite {
				override function updateAnimation(elapsed:Float):Void dispatchSource('updateAnimation', [elapsed]);
				override public function drawFrame(force:Bool = false):Void dispatchSource('drawFrame', [force]);
				override public function graphicLoaded():Void dispatchSource('graphicLoaded', []);
				override public function loadGraphic(graphic:flixel.system.FlxAssets.FlxGraphicAsset, animated:Bool = false, frameWidth:Int = 0, frameHeight:Int = 0, unique:Bool = false, ?key:String):flixel.FlxSprite
					return cast dispatchSourceResult('loadGraphic', [graphic, animated, frameWidth, frameHeight, unique, key]);
				override function set_clipRect(rect:flixel.math.FlxRect):flixel.math.FlxRect
					return cast dispatchSourceResult('set_clipRect', [rect]);
				override function set_alpha(value:Float):Float return cast dispatchSourceResult('set_alpha', [value]);
				override public function updateHitbox():Void dispatchSource('updateHitbox', []);
				override function drawSimple(camera:flixel.FlxCamera):Void dispatchSource('drawSimple', [camera]);
				override function drawComplex(camera:flixel.FlxCamera):Void dispatchSource('drawComplex', [camera]);
			};
			addCallbacks(extra, [
				{values:[macro 'updateAnimation'], guard:null, expr:macro super.updateAnimation(args[0])},
				{values:[macro 'drawFrame'], guard:null, expr:macro super.drawFrame(args[0])},
				{values:[macro 'graphicLoaded'], guard:null, expr:macro super.graphicLoaded()},
				{values:[macro 'loadGraphic'], guard:null, expr:macro return super.loadGraphic(args[0], args[1], args[2], args[3], args[4], args[5])},
				{values:[macro 'set_clipRect'], guard:null, expr:macro return super.set_clipRect(args[0])},
				{values:[macro 'set_alpha'], guard:null, expr:macro return super.set_alpha(args[0])},
				{values:[macro 'updateHitbox'], guard:null, expr:macro super.updateHitbox()},
				{values:[macro 'drawSimple'], guard:null, expr:macro super.drawSimple(args[0])},
				{values:[macro 'drawComplex'], guard:null, expr:macro super.drawComplex(args[0])}
			]);
		}
		if (spriteGroup) {
			var extra = macro class GroupInitializationCallback extends flixel.group.FlxSpriteGroup {
				override function initGroup(maxSize:Int):Void dispatchSource('initGroup', [maxSize]);
			};
			addCallbacks(extra, [{values:[macro 'initGroup'], guard:null, expr:macro super.initGroup(args[0])}]);
		}
		if (animation || object) {
			var extra = macro class ObjectInitializationCallback extends flixel.FlxObject {
				override function initVars():Void dispatchSource('initVars', []);
				override function set_x(value:Float):Float return cast dispatchSourceResult('set_x', [value]);
				override function set_y(value:Float):Float return cast dispatchSourceResult('set_y', [value]);
				override function set_width(value:Float):Float return cast dispatchSourceResult('set_width', [value]);
				override function set_height(value:Float):Float return cast dispatchSourceResult('set_height', [value]);
				override function get_width():Float return cast dispatchSourceResult('get_width', []);
				override function get_height():Float return cast dispatchSourceResult('get_height', []);
			};
			addCallbacks(extra, [
				{values:[macro 'initVars'], guard:null, expr:macro super.initVars()},
				{values:[macro 'set_x'], guard:null, expr:macro return super.set_x(args[0])},
				{values:[macro 'set_y'], guard:null, expr:macro return super.set_y(args[0])},
				{values:[macro 'set_width'], guard:null, expr:macro return super.set_width(args[0])},
				{values:[macro 'set_height'], guard:null, expr:macro return super.set_height(args[0])},
				{values:[macro 'get_width'], guard:null, expr:macro return super.get_width()},
				{values:[macro 'get_height'], guard:null, expr:macro return super.get_height()}
			]);
		}
		return fields.concat(adapter.fields);
	}
	#end
}
