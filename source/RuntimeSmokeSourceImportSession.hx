package;

/** Verify retained owner-class imports on the native target without scene changes. */
class RuntimeSmokeSourceImportSession {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}

	public static function verify():Void {
		#if sys
		if (Sys.getEnv('CAMMIE_SOURCE_IMPORT_SESSION_SMOKE') != '1') return;
		#else
		return;
		#end
		var owner = 'tmp/source-import-session-probe';
		var loader = CodenameScriptClassLoader.open(owner, new Map(), new Map());
		var isolated = CodenameScriptClassLoader.open(owner, new Map(), new Map());
		var cleanup = function() {loader.scope.release();isolated.scope.release();};
		try {
			var first = loader.importClasses(['demo.Counter']);
			check(first.diagnostics.length == 0, 'Native initial class import: ' + first.diagnostics.join('; '));
			var symbol = loader.scope.resolveClassSymbol('demo.Counter');
			var instance = loader.scope.createInstance('demo.Counter');
			check(instance.callFunction('next', []) == 2, 'Native lexical static increment');
			var next = loader.importClasses(['demo.Counter', 'demo.Later']);
			check(next.diagnostics.length == 0 && loader.scope.resolveClassSymbol('demo.Counter') == symbol, 'Native incremental class identity');
			check(loader.scope.createInstance('demo.Later').callFunction('current', []) == 2, 'Native dependency shares static storage');
			var failed = loader.importClasses(['demo.Bad']);
			check(failed.diagnostics.length > 0 && !failed.imports.iterator().hasNext(), 'Native rejected import batch');
			check(loader.scope.findDescriptor('other.Counter') == null && loader.scope.resolveClassSymbol('Counter') == symbol, 'Native dependency/alias rollback');
			check(instance.callFunction('next', []) == 3, 'Native retained instance survives failed imports');
			check(loader.importClasses(['demo.Later']).diagnostics.length == 0, 'Native retry after rejected batch');
			check(isolated.importClasses(['demo.Counter']).diagnostics.length == 0, 'Native independent source scope');
			check(isolated.scope.resolveClassSymbol('demo.Counter') != symbol
				&& isolated.scope.createInstance('demo.Counter').callFunction('current', []) == 1, 'Native isolated static state');
			loader.scope.release();
			var rejected = false;
			try loader.importClasses(['demo.Counter']) catch (_:Dynamic) rejected = true;
			check(rejected, 'Native released session cannot revive');
			@:privateAccess RuntimeSmokeHarness.emit('source_import_session_native_verified', {
				classIdentity:true,lexicalStatics:true,dependencyStatics:true,batchRollback:true,retainedInstance:true,retry:true,isolatedScope:true,release:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
