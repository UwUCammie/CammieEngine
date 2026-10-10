package;

/** Native verification of owner-scoped source method dispatch. */
class RuntimeSmokeSourceVirtualMethods {
	public static function verify():Void {
		#if sys
		if (Sys.getEnv('CAMMIE_SOURCE_VIRTUAL_METHOD_SMOKE') != '1') return;
		#else
		return;
		#end
		var loaded = CodenameScriptClassLoader.load('tmp/source-virtual-method-probe', ['demo.Child'], new Map(), new Map());
		if (loaded.diagnostics.length != 0) throw loaded.diagnostics;
		try {
			var child:hscript.AbstractScriptClass = loaded.scope.createInstance('demo.Child');
			var output:Array<String> = [];
			output.push(child.run());output.push(child.inheritedCall());
			var captured = child.capture();output.push(captured('captured'));
			output.push(child.explicitSuper('explicit-super'));
			output.push(child.capturedWide());
			output.push(child.local(function(value) return 'local:' + value));
			output.push(child.recover());
			#if sys
			var expected = sys.io.File.getContent('tmp/source-virtual-method-probe/expected.txt');
			if (StringTools.trim(output.join('\n')) != StringTools.trim(expected)) throw 'Source virtual dispatch mismatch: ' + output;
			#end
			@:privateAccess RuntimeSmokeHarness.emit('source_virtual_methods_native_verified', {constructorOverride:true,privateOverride:true,explicitSuper:true,lexicalStatic:true,methodReferences:true,optionalArguments:true,exceptionRecovery:true});
		} catch (error:Dynamic) {loaded.scope.release();throw error;}
		loaded.scope.release();
	}
}
