package;

#if macro
import haxe.macro.Context;
import haxe.macro.Expr;
#end

/** Generate only native super trampolines; runtime ownership is shared. */
class SourceNativeClassAdapterMacro {
	#if macro
	public static function build(animation:Bool = true):Array<Field> {
		var fields = Context.getBuildFields();
		var adapter = macro class NativeClassCallbacks extends flixel.FlxBasic {
			public var sourceLifecycle(default, null):SourceNativeClassLifecycle;
			public function bind(owner:hscript.ScriptClass, scope:hscript.ScriptClassScope):Void {
				if (sourceLifecycle != null) throw '[source-native] Native adapter already has an owner';
				sourceLifecycle = new SourceNativeClassLifecycle(owner, scope, callNativeBase);
			}
			public function scriptOwner():hscript.ScriptClass return sourceLifecycle == null ? null : sourceLifecycle.owner;
			function dispatchSource(name:String, args:Array<Dynamic>):Void {
				// Native constructors can call virtual methods before owner binding.
				if (sourceLifecycle == null) callNativeBase(name, args);
				else sourceLifecycle.dispatch(name, args);
			}
			override public function update(elapsed:Float):Void dispatchSource('update', [elapsed]);
			override public function draw():Void dispatchSource('draw', []);
			override public function kill():Void dispatchSource('kill', []);
			override public function revive():Void dispatchSource('revive', []);
			override public function destroy():Void dispatchSource('destroy', []);
			public function supportsNativeSuper(name:String):Bool return SourceNativeClassLifecycle.hasNativeSuper(name, $v{animation});
			public function callNativeSuper(name:String, args:Array<Dynamic>):Dynamic {
				return sourceLifecycle == null ? callNativeBase(name, args) : sourceLifecycle.callNativeSuper(name, args);
			}
			function callNativeBase(name:String, args:Array<Dynamic>):Dynamic {
				switch (name) {
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
		if (animation) {
			var extra = macro class SpriteAnimationCallback extends flixel.FlxSprite {
				override function updateAnimation(elapsed:Float):Void dispatchSource('updateAnimation', [elapsed]);
			};
			adapter.fields = adapter.fields.concat(extra.fields);
			for (field in adapter.fields) if (field.name == 'callNativeBase') switch (field.kind) {
				case FFun(fn): switch (fn.expr.expr) {
					case EBlock(expressions): switch (expressions[0].expr) {
						case ESwitch(subject, cases, fallback):
							cases.push({values:[macro 'updateAnimation'], guard:null, expr:macro super.updateAnimation(args[0])});
						default:
					}
					default:
				}
				default:
			}
		}
		return fields.concat(adapter.fields);
	}
	#end
}
