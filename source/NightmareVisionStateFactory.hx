package;

/**
	Owner-facing operations needed by the source state factory. The host resolves
	redirects against its current config and authorized owner paths, while keeping
	engine states and script wrappers out of this core.
*/
interface INightmareVisionStateFactoryHost {
	/** Map the constructed host class to the source's simple state class name. */
	public function requestedStateName(state:Dynamic):String;
	/** Return the selected config's resolved scripts/states path, or null. */
	public function stateRedirectPath(requestedName:String):Null<String>;
	public function scriptExists(ownerPath:String):Bool;
	/** Construct the owner-scoped wrapper. Its constructor binds before onLoad. */
	public function makeScriptState(ownerPath:String):Dynamic;
	public function destroyState(state:Dynamic):Void;
	public function warnMissingRedirect(requestedName:String, ownerPath:String):Void;
	public function getTransitionOverrides():NightmareVisionStateTransitionOverrides;
	public function setTransitionOverrides(value:NightmareVisionStateTransitionOverrides):Void;
	/** Register a one-shot callback for the next completed state switch. */
	public function afterPostStateSwitch(callback:Void->Void):Void;
}

/** The pair of process transition values temporarily changed by CoolUtil. */
typedef NightmareVisionStateTransitionOverrides = {
	var transitionIn:Dynamic;
	var transitionOut:Dynamic;
}

/** A materialized request and the constructor which resetState must retain. */
typedef NightmareVisionStateFactoryResult = {
	var state:Dynamic;
	var constructor:Null<Void->Dynamic>;
	var redirected:Bool;
}

/**
	Nightmare Vision's constructor-based state redirect core.

	The native host constructs the requested class first, just as FunkinGame does,
	then this factory applies the selected owner's stateRedirects entry. The
	returned constructor is the one the host must retain for resetState.
*/
@:keep
class NightmareVisionStateFactory {
	final host:INightmareVisionStateFactoryHost;
	public var lastConstructor(default, null):Null<Void->Dynamic>;
	public var lastWasRedirected(default, null):Bool = false;

	public function new(host:INightmareVisionStateFactoryHost) {
		if (host == null) throw '[nightmare-vision-state-factory] Missing host';
		this.host = host;
	}

	/** Materialize one requested constructor and resolve its selected-owner redirect. */
	public function construct(request:Null<Void->Dynamic>,
		?resetConstructor:Null<Void->Dynamic>):NightmareVisionStateFactoryResult {
		// Flixel's legacy NextState accepts an instance, then derives a no-arg
		// constructor for reset. Keep that reset factory separate from the initial
		// materialization so a reset never reuses a destroyed instance.
		var retainedRequest = resetConstructor == null ? request : resetConstructor;
		if (request == null) {
			lastConstructor = retainedRequest;
			lastWasRedirected = false;
			return result(null, retainedRequest, false);
		}

		var requestedState = request();
		if (requestedState == null) {
			lastConstructor = retainedRequest;
			lastWasRedirected = false;
			return result(null, retainedRequest, false);
		}

		var requestedName = host.requestedStateName(requestedState);
		if (requestedName == null || StringTools.trim(requestedName) == '') {
			lastConstructor = retainedRequest;
			lastWasRedirected = false;
			return result(requestedState, retainedRequest, false);
		}

		var ownerPath = host.stateRedirectPath(requestedName);
		if (ownerPath == null) {
			lastConstructor = retainedRequest;
			lastWasRedirected = false;
			return result(requestedState, retainedRequest, false);
		}
		if (!host.scriptExists(ownerPath)) {
			host.warnMissingRedirect(requestedName, ownerPath);
			lastConstructor = retainedRequest;
			lastWasRedirected = false;
			return result(requestedState, retainedRequest, false);
		}

		// FunkinGame destroys the requested state before it constructs ScriptedState.
		host.destroyState(requestedState);
		var redirectedConstructor:Void->Dynamic = function():Dynamic {
			return host.makeScriptState(ownerPath);
		};
		// Publish before invoking the wrapper, since its onLoad can request a
		// nested state transition and that later request must remain current.
		lastConstructor = redirectedConstructor;
		lastWasRedirected = true;
		var redirectedState = redirectedConstructor();
		return result(redirectedState, redirectedConstructor, true);
	}

	/** Re-run the exact resolved constructor saved by the most recent request. */
	public function resetState():NightmareVisionStateFactoryResult {
		var constructor = lastConstructor;
		if (constructor == null) return result(null, null, lastWasRedirected);
		var state = constructor();
		return result(state, constructor, lastWasRedirected);
	}

	/**
		Match CoolUtil.switchState: set the temporary pair, request the switch, then
		register restoration of the captured values for postStateSwitch.
	*/
	public function switchWithTransitions(transitionIn:Dynamic, transitionOut:Dynamic,
		switchRequest:Null<Void->Dynamic>):Dynamic {
		if (switchRequest == null) return null;

		var previous = host.getTransitionOverrides();
		host.setTransitionOverrides({transitionIn:transitionIn, transitionOut:transitionOut});
		var state = switchRequest();
		host.afterPostStateSwitch(function():Void {
			host.setTransitionOverrides({
				transitionIn:previous.transitionIn,
				transitionOut:previous.transitionOut
			});
		});
		return state;
	}

	static function result(state:Dynamic, constructor:Null<Void->Dynamic>, redirected:Bool):NightmareVisionStateFactoryResult {
		return {state:state, constructor:constructor, redirected:redirected};
	}
}
