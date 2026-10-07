package;

#if macro
import haxe.macro.Context;
import haxe.macro.Expr;
import haxe.macro.TypeTools;
import haxe.macro.ExprTools;
#end

/** Targeted source methods only; never annotate the process-wide FlxSprite. */
class NightmareVisionSpriteMacro
{
	public static macro function build():Array<Field>
	{
		var fields = Context.getBuildFields();
		var cls = Context.getLocalClass().get();
		var position = Context.currentPos();
		var mark = ':nightmareVisionSpriteConvenience';
		var ownerName = '__nightmareVisionSpriteOwner';
		var parent = cls.superClass;
		var inherited:Map<String, haxe.macro.Type.ClassField> = [];
		while (parent != null) {
			var type = parent.t.get();
			for (field in type.fields.get()) if (!inherited.exists(field.name)) inherited.set(field.name, field);
			parent = type.superClass;
		}
		function add(field:Field):Void {
			for (current in fields) if (current.name == field.name)
				Context.error('[nightmare-vision-sprite] Target already declares ' + field.name, current.pos);
			if (inherited.exists(field.name)) {
				var existing = inherited.get(field.name);
				if (!existing.meta.has(mark))
					Context.error('[nightmare-vision-sprite] Incompatible inherited method or owner cell: ' + field.name, position);
				switch (field.kind) {
					case FFun(expected):
						switch (TypeTools.follow(existing.type)) {
							case TFun(args, ret):
								if (args.length != expected.args.length || TypeTools.toString(ret) != TypeTools.toString(Context.resolveType(expected.ret, position)))
									Context.error('[nightmare-vision-sprite] Inherited source signature differs: ' + field.name, position);
								for (i in 0...args.length) {
									var argument = expected.args[i];
									if (args[i].opt != (argument.opt == true || argument.value != null)
										|| TypeTools.toString(args[i].t) != TypeTools.toString(Context.resolveType(argument.type, position)))
										Context.error('[nightmare-vision-sprite] Inherited source argument differs: ' + field.name, position);
								}
							default: Context.error('[nightmare-vision-sprite] Inherited source method is not callable: ' + field.name, position);
						}
					case FVar(expected, _):
						if (TypeTools.toString(existing.type) != TypeTools.toString(Context.resolveType(expected, position)))
							Context.error('[nightmare-vision-sprite] Inherited owner cell type differs', position);
					default:
				}
				return;
			}
			field.meta = [{name:':keep', pos:position}, {name:mark, pos:position}];
			fields.push(field);
		}
		add({name:ownerName, access:[APrivate], pos:position,
			kind:FVar(macro:Null<NightmareVisionSpriteOwner>, macro null)});
		var methods = (macro class {
			public function loadFromSheet(path:String, animName:String, fps:Int = 24, looped:Bool = true):flixel.FlxSprite
				return NightmareVisionSpriteMethods.loadFromSheet(this, path, animName, fps, looped);
			public function loadAtlasFrames(frames:flixel.graphics.frames.FlxAtlasFrames):flixel.FlxSprite
				return NightmareVisionSpriteMethods.loadAtlasFrames(this, frames);
			public function makeScaledGraphic(width:Float, height:Float, color:flixel.util.FlxColor = flixel.util.FlxColor.WHITE):flixel.FlxSprite
				return NightmareVisionSpriteMethods.makeScaledGraphic(this, width, height, color);
			public function setScale(x:Float, y:Float, update:Bool = true):flixel.FlxSprite
				return NightmareVisionSpriteMethods.setScale(this, x, y, update);
			public function centerOnObject(object:flixel.FlxObject, axes:flixel.util.FlxAxes = cast 0x11):flixel.FlxSprite
				return NightmareVisionSpriteMethods.centerOnObject(this, object, axes);
		}).fields;
		for (field in methods) add(field);
		var cleanupMark = ':nightmareVisionSpriteCleanup';
		var ownDestroy:Null<Field> = null;
		for (field in fields) if (field.name == 'destroy') ownDestroy = field;
		if (ownDestroy != null) {
			switch (ownDestroy.kind) {
				case FFun(fn):
					if (fn.expr == null) Context.error('[nightmare-vision-sprite] Destroy needs a source body', ownDestroy.pos);
					// Returns in nested functions belong to those callbacks, not this destructor.
					function withReturnCleanup(expr:Expr, cleanupReturns:Bool = true):Expr {
						return switch (expr.expr) {
							case EFunction(kind, callback):
								if (callback.expr != null) callback.expr = withReturnCleanup(callback.expr, false);
								{expr:EFunction(kind, callback), pos:expr.pos};
							case EReturn(value):
								if (!cleanupReturns) {expr:EReturn(value == null ? null : withReturnCleanup(value, false)), pos:expr.pos};
								else if (value == null) macro {NightmareVisionSpriteMethods.clear(this); return;}
								else {
									var call = withReturnCleanup(value);
									macro {$call; NightmareVisionSpriteMethods.clear(this); return;}
								}
							case ECall({expr:EField({expr:EConst(CIdent('super'))}, 'destroy')}, _):
								// Ancestor wrappers may clear their cell on return/throw. The
								// child still owns its full original cleanup body and callbacks.
								macro {
									var __nvBorrowedOwner:Null<NightmareVisionSpriteOwner> = Reflect.field(this, '__nightmareVisionSpriteOwner');
									try {$expr;} catch (__nvParentError:Dynamic) {
										Reflect.setField(this, '__nightmareVisionSpriteOwner', __nvBorrowedOwner);
										throw __nvParentError;
									}
									Reflect.setField(this, '__nightmareVisionSpriteOwner', __nvBorrowedOwner);
								}
								default: ExprTools.map(expr, function(child) return withReturnCleanup(child, cleanupReturns));
							};
					}
					var body = withReturnCleanup(fn.expr);
					fn.expr = macro {
						try {$body;} catch (error:Dynamic) {NightmareVisionSpriteMethods.clear(this); throw error;}
						NightmareVisionSpriteMethods.clear(this);
					};
					if (ownDestroy.meta == null) ownDestroy.meta = [];
					ownDestroy.meta.push({name:cleanupMark, pos:position});
				default: Context.error('[nightmare-vision-sprite] Destroy must be a method', ownDestroy.pos);
			}
		} else if (!inherited.exists('destroy') || !inherited.get('destroy').meta.has(cleanupMark)) {
			var cleanup = (macro class {
				override public function destroy():Void {
					try {super.destroy();} catch (error:Dynamic) {NightmareVisionSpriteMethods.clear(this); throw error;}
					NightmareVisionSpriteMethods.clear(this);
				}
			}).fields[0];
			cleanup.meta = [{name:':keep', pos:position}, {name:cleanupMark, pos:position}];
			fields.push(cleanup);
		}
		return fields;
	}
}
