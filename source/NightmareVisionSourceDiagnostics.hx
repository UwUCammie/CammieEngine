package;

import crowplexus.iris.ErrorSeverity;
import crowplexus.iris.Iris;
import flixel.util.FlxColor;
import haxe.PosInfos;

using StringTools;

/** Owner-bound Iris logging and the source module error path. */
@:keep
class NightmareVisionSourceDiagnostics {
	final ownerRoot:String;
	final coreDirectory:String;
	final writeConsole:String->Void;
	final pending:Array<{message:String, colour:FlxColor}> = [];
	var addDebugText:String->FlxColor->Void;
	var released:Bool = false;

	public function new(ownerRoot:String, coreDirectory:String, ?writeConsole:String->Void) {
		if (ownerRoot == null || coreDirectory == null || !coreDirectory.startsWith(ownerRoot + '/'))
			throw '[nmv-bootstrap-service] Diagnostics paths do not belong to the source owner';
		this.ownerRoot = ownerRoot;
		this.coreDirectory = coreDirectory;
		this.writeConsole = writeConsole == null ? defaultConsoleWrite : writeConsole;
	}

	/** Attach the owner DebugText group and flush errors reported before Init's
	 * DebugText step completed. */
	public function bindDebugText(sink:String->FlxColor->Void):Void {
		ensureAlive();
		if (sink == null) throw '[nmv-bootstrap-service] Missing owner DebugText sink';
		addDebugText = sink;
		for (message in pending) addDebugText(message.message, message.colour);
		pending.resize(0);
	}

	/** Match the donor FunkinScript parse/callback error route: console output
	 * is immediate and the red source message waits for owner DebugText if needed. */
	public function reportError(name:String, callback:String, error:Dynamic):Void {
		if (released) return;
		var label = callback == null || callback == '' ? 'script' : callback;
		var message = label == 'module'
			? '[$name]: PARSING ERROR: ' + Std.string(error)
			: '[$name]: $label ERROR: ' + Std.string(error);
		writeConsole('[ERROR] ' + message);
		addMessage(message, FlxColor.fromRGB(255, 64, 64));
	}

	/** Bind the donor's public Iris logging calls to this owner only. Iris's
	 * process-global methods are never reassigned. */
	public function bindIris(interp:NightmareVisionScriptInterp):Void {
		ensureAlive();
		if (interp == null) throw '[nmv-bootstrap-service] Missing source Iris interpreter';
		var facade:Dynamic = {};
		Reflect.setField(facade, 'warn', Reflect.makeVarArgs(function(args:Array<Dynamic>):Void {
			logIris(interp, args, 'warn');
		}));
		Reflect.setField(facade, 'error', Reflect.makeVarArgs(function(args:Array<Dynamic>):Void {
			logIris(interp, args, 'error');
		}));
		Reflect.setField(facade, 'print', Reflect.makeVarArgs(function(args:Array<Dynamic>):Void {
			logIris(interp, args, 'print');
		}));
		interp.variables.set('Iris', facade);
		interp.bindImport('Iris', facade);
		interp.bindImport('crowplexus.iris.Iris', facade);
		interp.sourceError = function(error:Dynamic, position:PosInfos):Void {
			logIris(interp, [error, position], 'error');
		};
	}

	public function release():Void {
		if (released) return;
		released = true;
		pending.resize(0);
		addDebugText = null;
	}

	function logIris(interp:NightmareVisionScriptInterp, args:Array<Dynamic>, kind:String):Void {
		if (released) return;
		var value:Dynamic = args.length == 0 ? null : args[0];
		var position:PosInfos = args.length > 1 ? cast args[1] : interp.posInfos();
		var message = formatPosition(position, value);
		var severity:ErrorSeverity = switch (kind) {
			case 'warn':
				addMessage(message, FlxColor.YELLOW);
				ErrorSeverity.ERROR;
			case 'error':
				addMessage(message, FlxColor.fromRGB(255, 64, 64));
				ErrorSeverity.NONE;
			default:
				addMessage(message, FlxColor.WHITE);
				ErrorSeverity.NONE;
		};
		// FunkinScript.init uses this unchanged Iris output path after adding
		// owner-colored DebugText, including ERROR severity for warnings.
		Iris.logLevel(severity, value, position);
	}

	function formatPosition(position:PosInfos, value:Dynamic):String {
		var fileName = position == null || position.fileName == null ? 'hscript' : position.fileName;
		if (fileName.startsWith(coreDirectory + '/'))
			fileName = fileName.substr(coreDirectory.length + 1);
		else if (fileName.startsWith(ownerRoot + '/'))
			fileName = fileName.substr(ownerRoot.length + 1);
		var lineNumber = position == null ? 0 : position.lineNumber;
		return '[$fileName:$lineNumber] - ' + Std.string(value);
	}

	function addMessage(message:String, colour:FlxColor):Void {
		if (addDebugText != null) addDebugText(message, colour);
		else pending.push({message:message, colour:colour});
	}

	static function defaultConsoleWrite(message:String):Void {
		#if sys
		Sys.println(message);
		#else
		trace(message);
		#end
	}

	function ensureAlive():Void if (released)
		throw '[nmv-bootstrap-service] Owner diagnostics have been released';
}
