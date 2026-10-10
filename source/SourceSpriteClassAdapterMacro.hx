package;

#if macro
import haxe.macro.Context;
import haxe.macro.Expr;
#end

/** Generate only native super trampolines; runtime ownership is shared. */
class SourceSpriteClassAdapterMacro {
	#if macro
	public static function build():Array<Field> {
		var fields = Context.getBuildFields();
		var adapter = macro class NativeSpriteCallbacks extends flixel.FlxSprite {
			public var sourceLifecycle(default, null):SourceSpriteClassLifecycle;
			public function bind(owner:hscript.ScriptClass, scope:hscript.ScriptClassScope):Void {
				if (sourceLifecycle != null) throw '[source-sprite] Native adapter already has an owner';
				sourceLifecycle = new SourceSpriteClassLifecycle(owner, scope, callNativeBase);
			}
			public function scriptOwner():hscript.ScriptClass return sourceLifecycle == null ? null : sourceLifecycle.owner;
			function dispatchSource(name:String, args:Array<Dynamic>):Void {
				// Native constructors can call virtual methods before owner binding.
				if (sourceLifecycle == null) callNativeBase(name, args);
				else sourceLifecycle.dispatch(name, args);
			}
			override public function update(elapsed:Float):Void dispatchSource('update', [elapsed]);
			override public function draw():Void dispatchSource('draw', []);
			override function updateAnimation(elapsed:Float):Void dispatchSource('updateAnimation', [elapsed]);
			override public function kill():Void dispatchSource('kill', []);
			override public function revive():Void dispatchSource('revive', []);
			override public function destroy():Void dispatchSource('destroy', []);
			public function callNativeSuper(name:String, args:Array<Dynamic>):Dynamic {
				return sourceLifecycle == null ? callNativeBase(name, args) : sourceLifecycle.callNativeSuper(name, args);
			}
			function callNativeBase(name:String, args:Array<Dynamic>):Dynamic {
				switch (name) {
					case 'update': super.update(args[0]);
					case 'draw': super.draw();
					case 'updateAnimation': super.updateAnimation(args[0]);
					case 'kill': super.kill();
					case 'revive': super.revive();
					case 'destroy': super.destroy();
					default: throw '[source-sprite] Unsupported native super method: ' + name;
				}
				return null;
			}
		};
		return fields.concat(adapter.fields);
	}
	#end
}
