package;

import flixel.text.FlxText;

/** Disposable scene objects verify ordering without moving authored actors. */
@:access(PlayState)
class RuntimeSmokeLegacyObjectOrder {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState, lua:LuaCompatInterp):Void {
		var first = new FlxText(0, 0, 80, 'order-first');
		var second = new FlxText(0, 0, 80, 'order-second');
		var sceneA = new flixel.FlxState();
		var sceneB = new flixel.FlxState();
		var detached = new FlxText(0, 0, 80, 'order-migrated');
		var original = state.members.copy();
		var cleanup = function() {
			state.remove(first, true);state.remove(second, true);
			state.modchartObjects.remove('__order');state.modchartTexts.remove('__orderText');
			first.destroy();second.destroy();sceneA.destroy();sceneB.destroy();
			if (detached.animation != null) detached.destroy();
		};
		try {
			state.modchartObjects.set('__order', {items:[first, second]});
			state.modchartTexts.set('__orderText', second);
			state.insert(state.members.length, first);state.insert(state.members.length, second);
			lua.variables.set('__orderEnd', state.members.length - 1);
			lua.variables.set('__orderStart', original.length);
			lua.execute(new hscript.Parser().parseString('if(getObjectOrder("__orderText")!=__orderEnd)throw "native text ordering lookup";setObjectOrder("__order.items[1]",__orderStart);if(getObjectOrder("__orderText")!=__orderStart)throw "native nested ordering write";setObjectOrder("__order.items[0]",__orderStart+1);if(getObjectOrder("__order.items[0]")!=__orderStart+1)throw "native ordered insertion";', '__lua_order'));
			check(first.container == state && second.container == state && first.exists && second.exists, 'Ordering preserves native object ownership and lifetime');
			state.remove(first, true);state.remove(second, true);
			check(state.members.length == original.length, 'Ordering restores scene size');
			for (i in 0...original.length) check(state.members[i] == original[i], 'Authored scene order preserved');
			var active:flixel.FlxState = sceneA;
			sceneA.add(detached);
			sceneA.memberRemoved.add(function(item) {if (item == detached) active = sceneB;});
			SourceScriptReflection.setLegacyObjectOrder('tag', 500, function() return active, function(name) return detached, Reflect.getProperty, function() throw 'missing temporary tag');
			check(sceneA.members.indexOf(detached) < 0 && sceneB.members.indexOf(detached) == 0 && detached.container == sceneB && detached.exists, 'Removal callback changes native insertion scene');
			@:privateAccess RuntimeSmokeHarness.emit('legacy_object_order_native_verified', {publicBindings:true,textTag:true,nestedArray:true,nativeOwnership:true,sceneReentry:true,authoredOrderPreserved:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
