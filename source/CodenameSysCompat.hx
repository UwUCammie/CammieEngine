package;

/** Narrow Sys adapters that preserve imported-state exit semantics by host scope. */
@:keep
class CodenameSysCompat {
	/** Shared/non-state interpreters return to the native menu instead of exiting the host. */
	public static function facade():Dynamic {
		return {
			exit:function(?_code:Int = 0):Void {
				trace('[codename-state-exit] Imported state returned to the native menu.');
				CodenameModRuntime.exitToNativeMenu();
			}
		};
	}

	/** An active imported state uses Sys.exit as an application quit. The caller
		must already have verified that its host is CodenameImportedState. Tests
		can inject a recorder instead of terminating their Haxe process.
	*/
	public static function importedStateFacade(ownerRoot:String,
		?processExit:Int->Void):Dynamic {
		return {
			exit:function(?code:Int = 0):Void {
				if (!CodenameModRuntime.isActiveOwner(ownerRoot)) {
					trace('[codename-state-exit] Imported state returned to the native menu.');
					CodenameModRuntime.exitToNativeMenu();
					return;
				}
				trace('[codename-state-exit] Active imported state requested application exit.');
				if (processExit != null) processExit(code); else exitProcess(code);
			}
		};
	}

	static function exitProcess(code:Int):Void {
		#if sys
		Sys.exit(code);
		#else
		CodenameModRuntime.exitToNativeMenu();
		#end
	}
}
