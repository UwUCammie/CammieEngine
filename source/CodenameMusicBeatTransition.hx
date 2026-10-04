package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxState;
import flixel.FlxSubState;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween;
import flixel.util.FlxColor;

/** Shared native host for Codename's `funkin.backend.MusicBeatTransition`.
	The static script selector is keyed by the active Codename owner; each run
	gets an owner-scoped interpreter and scene list. Ordinary native states keep
	Flixel's existing transition flow unless that selected owner configured a
	transition script.
*/
class CodenameMusicBeatTransition extends MusicBeatSubstate {
	/** The source class has one static selector. Store it by owner so switching
		imports can never reuse another mod's callback path.
	*/
	public static var script(get, set):String;
	static var incomingStateOwner:String = '';
	static final incomingSong = new CodenameTransitionSongLease();
	static var incomingStateHandler:FlxState->Void;

	static function watchIncomingState(ownerRoot:String):Void {
		clearIncomingStateWatch();
		incomingStateOwner = ownerRoot;
		incomingStateHandler = function(nextState:FlxState):Void {
			var isMusicBeatState = Std.isOfType(nextState, MusicBeatState);
			var isLoadingWrapper = Std.isOfType(nextState, LoadingState);
			if (!CodenameTransitionScope.shouldAbandonIncoming(isMusicBeatState,
				isLoadingWrapper)) return;
			var owner = incomingStateOwner;
			clearIncomingStateWatch();
			abandonIncoming(owner);
		};
		FlxG.signals.preStateCreate.add(incomingStateHandler);
	}

	static function clearIncomingStateWatch(?ownerRoot:String):Void {
		if (incomingStateHandler == null) return;
		if (ownerRoot != null && ownerRoot != ''
			&& !CodenameTransitionScope.sameOwner(incomingStateOwner, ownerRoot)) return;
		FlxG.signals.preStateCreate.remove(incomingStateHandler);
		incomingStateHandler = null;
		incomingStateOwner = '';
	}

	static function get_script():String {
		var owner = currentOwnerRoot();
		return CodenameTransitionScope.script(owner);
	}
	static function set_script(value:String):String {
		var owner = currentOwnerRoot();
		if (owner == null || owner == '') {
			trace('[codename-transition] Ignored script selection without an active owner.');
			return value;
		}
		return CodenameTransitionScope.setScript(owner, value);
	}

	public var transitionTween:FlxTween;
	public var transitionCamera:CodenameTransitionCamera;
	public var newState:FlxState;
	/** Script-facing target captured before Flixel starts the outgoing outro.
		The native host keeps `newState` null for callback-based state switches. */
	public var scriptNewState:FlxState;
	public var transOut:Bool = false;
	public var allowSkip:Bool = true;
	public var blackSpr:FlxSprite;
	public var transitionSprite:FlxSprite;
	public var ownerRoot(default, null):String;
	public var sourceSong(default, null):CodenameSongView;
	public var scriptPath(default, null):String;
	public var parentDisabler(default, null):CodenameParentDisabler;

	var hostState:FlxState;
	var outroComplete:Void->Void;
	var runtime:CodenameMusicBeatTransitionRuntime;
	var nextFrameSkip:Bool = false;
	var finishing:Bool = false;
	var switchingState:Bool = false;
	var destroyedTransition:Bool = false;
	var smokeUpdateFrames:Int = 0;
	var stateHandoff:Bool = false;

	public function new(?newState:FlxState, ?ownerRoot:String, ?transOut:Null<Bool>,
		?outroComplete:Void->Void, ?scriptPathOverride:String) {
		super();
		this.newState = newState;
		this.scriptNewState = newState;
		this.ownerRoot = ownerRoot == null ? currentOwnerRoot() : ownerRoot;
		this.transOut = transOut == null ? newState != null : transOut;
		this.outroComplete = outroComplete;
		stateHandoff = newState != null || outroComplete != null;
		scriptPath = scriptPathOverride == null
			? CodenameTransitionScope.script(this.ownerRoot) : scriptPathOverride;
	}

	/** Prefer the active chart's installed Codename owner. The explicit
		Imported Mods session remains the fallback for menu and state scripts. */
	public static function currentOwnerRoot():String {
		var chartOwner = '';
		var play = PlayState.instance;
		if (play != null && FlxG.state == play)
			chartOwner = play.codenameTransitionOwnerRoot();
		return CodenameTransitionScope.resolveOwner(chartOwner,
			CodenameModRuntime.activeRoot());
	}

	static function ownerForState(host:FlxState):String {
		var play = PlayState.instance;
		if (play != null && host == play) {
			var chartOwner = play.codenameTransitionOwnerRoot();
			if (chartOwner != null && chartOwner != '') return chartOwner;
		}
		return CodenameModRuntime.activeRoot();
	}

	/** Resolve the same owner context for transition callbacks and handoffs. */
	public static function canRunOwner(ownerRoot:String):Bool {
		var chartOwner = '';
		var play = PlayState.instance;
		if (play != null && FlxG.state == play)
			chartOwner = play.codenameTransitionOwnerRoot();
		return CodenameTransitionScope.canRunOwner(ownerRoot, chartOwner,
			CodenameModRuntime.activeRoot());
	}

	/** LoadingState owns several engine-level routes that call native FlxG
		directly instead of the imported interpreter facade. Capture their
		destination for the active owner's outgoing script, but leave the native
		Flixel switch callback and target semantics intact. */
	public static function switchStateForCurrentOwner(target:FlxState):Bool {
		var owner = currentOwnerRoot();
		if (target == null || owner == '' || !canRunOwner(owner)
			|| CodenameTransitionScope.script(owner) == '') return false;
		CodenameTransitionScope.queueStateTarget(owner, target);
		try CodenameRequestedStateCompat.switchToKnownTarget(target,
			function():Void FlxG.switchState(target)) catch (error:Dynamic) {
			CodenameTransitionScope.clearPendingStateTarget(owner);
			throw error;
		}
		CodenameTransitionScope.clearPendingStateTarget(owner);
		return true;
	}

	/** Codename MusicBeatState.startTransition equivalent. */
	public static function openForOwner(ownerRoot:String, target:Dynamic,
		skipSubStates:Bool = false, ?outroComplete:Void->Void,
		?transOut:Null<Bool>, ?scriptStateTarget:Dynamic,
		?scriptPathOverride:String, ?sourceSong:CodenameSongView):Bool {
		if (!canRunOwner(ownerRoot)) return false;
		var path = scriptPathOverride == null
			? CodenameTransitionScope.script(ownerRoot) : scriptPathOverride;
		if (path == null || path == '') return false;
		if (target != null && !Std.isOfType(target, FlxState)) {
			trace('[codename-transition] Refused a non-FlxState transition target.');
			return false;
		}
		if (scriptStateTarget != null && !Std.isOfType(scriptStateTarget, FlxState)) {
			trace('[codename-transition] Refused a non-FlxState script target.');
			return false;
		}
		var current = FlxG.state;
		if (!Std.isOfType(current, MusicBeatState)) return false;
		var state:MusicBeatState = cast current;
		if (containsTransition(state.subState)) return false;

		var next:FlxState = target == null ? null : cast target;
		var isOut = transOut == null ? outroComplete != null || next != null : transOut;
		var transition = new CodenameMusicBeatTransition(next, ownerRoot, isOut,
			outroComplete, scriptPathOverride);
		transition.sourceSong = sourceSong;
		if (scriptStateTarget != null) transition.scriptNewState = cast scriptStateTarget;
		transition.hostState = state;
		var host:FlxState = state;
		if (!skipSubStates) {
			var candidate = state.subState;
			var found:FlxState = null;
			while (candidate != null) {
				if (Std.isOfType(candidate, CodenameMusicBeatTransition)) {
					found = null;
					break;
				}
				if (Std.isOfType(candidate, MusicBeatSubstate)
					&& Reflect.field(candidate, 'canOpenCustomTransition') == true) found = candidate;
				host = candidate;
				candidate = candidate.subState;
			}
			if (found != null) {
				host = found;
			} else host = state;
		}
		transition.hostState = host;
		host.openSubState(transition);
		return true;
	}

	/** Open a selected outgoing transition over a lifecycle-created substate.
		The target may still be queued by Flixel, so attach directly to that host. */
	public static function openLifecycleSubstate(ownerRoot:String,
		target:MusicBeatSubstate, transOut:Bool):Bool {
		if (target == null || !CodenameTransitionScope.canRun(ownerRoot,
			currentOwnerRoot()) || !canRunOwner(ownerRoot)) return false;
		var current = FlxG.state;
		if (!Std.isOfType(current, MusicBeatState) || containsTransition(target.subState)) return false;
		var transition = new CodenameMusicBeatTransition(null, ownerRoot, transOut, null);
		transition.hostState = cast current;
		target.openSubState(transition);
		return true;
	}

	/** The pause close hook chooses the incoming script before native resume. */
	public static function openLifecycleResume(ownerRoot:String):Bool {
		if (!canRunOwner(ownerRoot)) return false;
		var incomingScript = CodenameTransitionScope.consumeLifecycleResumeScript(ownerRoot);
		if (incomingScript == null || incomingScript == '') return false;
		return openForOwner(ownerRoot, null, false, null, false, null, incomingScript);
	}

	/** Outgoing FlxG.switchState bridge for this fork's startOutro lifecycle. */
	public static function startOwnerOutro(host:MusicBeatState, onOutroComplete:Void->Void):Bool {
		var owner = host == null ? '' : ownerForState(host);
		if (owner == null || owner == '' || !canRunOwner(owner)
			|| CodenameTransitionScope.script(owner) == '') return false;
		var scriptTarget = CodenameTransitionScope.takeStateTarget(owner);
		var completeKnownOutro = onOutroComplete;
		if (scriptTarget != null && onOutroComplete != null)
			completeKnownOutro = function():Void {
				onOutroComplete();
				CodenameRequestedStateCompat.bindKnownTargetRequest(scriptTarget);
			};
		var started = openForOwner(owner, null, false, completeKnownOutro, null, scriptTarget);
		if (started) {
			host.persistentUpdate = false;
			host.persistentDraw = true;
			return true;
		}
		return false;
	}

	/** FlxG.switchState re-enters startOutro when finish hands off an explicit
		Codename target. Let that one handoff continue without opening a second
		transition or running a native FlxTransitionableState outro.
	*/
	public static function completeTransitionSwitch(host:MusicBeatState,
		onOutroComplete:Void->Void):Bool {
		if (host == null || !findSwitchingTransition(host.subState)) return false;
		onOutroComplete();
		return true;
	}

	/** Consume the one incoming half scheduled by a completed custom outro. */
	public static function startPendingIncoming(host:MusicBeatState):Bool {
		if (host == null) return false;
		var owner = CodenameTransitionScope.pendingIncomingOwner();
		if (owner == null || owner == '') {
			var staleOwner = incomingStateOwner;
			if (staleOwner != '') abandonIncoming(staleOwner);
			else clearIncomingStateWatch();
			return false;
		}
		var path = CodenameTransitionScope.script(owner);
		if (path == '') {
			abandonIncoming(owner);
			return false;
		}
		var songView = incomingSong.take(owner, PlayState.SONG);
		if (!openForOwner(owner, null, false, null, null, null, null, songView)) {
			abandonIncoming(owner);
			return false;
		}
		clearIncomingStateWatch(owner);
		CodenameTransitionScope.consumeIncoming(owner);
		return true;
	}

	/** Release a failed or impossible incoming half without leaving a global
		owner that could leak into later menus or unrelated charts. */
	public static function abandonIncoming(ownerRoot:String):Void {
		incomingSong.clear(ownerRoot);
		clearIncomingStateWatch(ownerRoot);
		CodenameTransitionScope.abandonIncoming(ownerRoot);
		if (!CodenameModRuntime.isActiveOwner(ownerRoot)
			&& !CodenameTransitionScope.canRunOwner(ownerRoot, currentOwnerRoot(), ''))
			CodenameTransitionScope.clearOwner(ownerRoot);
	}

	public static function clearOwner(ownerRoot:String):Void {
		incomingSong.clear(ownerRoot);
		clearIncomingStateWatch(ownerRoot);
		CodenameTransitionScope.clearOwner(ownerRoot);
	}

	/** Release chart-selected transition state after gameplay leaves its owner.
		The outgoing state-switch pair keeps its selector until the incoming half
		finishes; an explicitly active Codename session owns its selector itself. */
	public static function releaseChartOwner(ownerRoot:String):Void {
		if (ownerRoot == null || ownerRoot == ''
			|| CodenameModRuntime.isActiveOwner(ownerRoot)
			|| CodenameTransitionScope.hasStateHandoff(ownerRoot)) return;
		clearOwner(ownerRoot);
	}

	static function containsTransition(state:FlxState):Bool {
		var current = state;
		while (current != null) {
			if (Std.isOfType(current, CodenameMusicBeatTransition)) return true;
			current = current.subState;
		}
		return false;
	}

	static function findSwitchingTransition(state:FlxState):Bool {
		var current = state;
		while (current != null) {
			if (Std.isOfType(current, CodenameMusicBeatTransition)
				&& (cast current:CodenameMusicBeatTransition).switchingState) return true;
			current = current.subState;
		}
		return false;
	}

	override public function create():Void {
		CodenameStateSmokeTrace.mark('transition-target', ownerRoot, scriptPath,
			[CodenameStateSmokeTrace.field('transOut', transOut),
				CodenameStateSmokeTrace.field('hostTarget', CodenameStateSmokeTrace.stateName(newState)),
				CodenameStateSmokeTrace.field('scriptTarget', CodenameStateSmokeTrace.stateName(scriptNewState)),
				CodenameStateSmokeTrace.field('callbackHandoff', outroComplete != null)]);
		if (transOut) {
			parentDisabler = new CodenameParentDisabler();
			add(parentDisabler);
		}

		transitionCamera = new CodenameTransitionCamera();
		transitionCamera.bgColor = FlxColor.TRANSPARENT;
		FlxG.cameras.add(transitionCamera, false);
		cameras = [transitionCamera];

		var event = new CodenameMusicBeatTransitionEvent(transOut, scriptNewState);
		if (canRunOwner(ownerRoot) && scriptPath != '') {
			runtime = new CodenameMusicBeatTransitionRuntime(this, ownerRoot, scriptPath);
			runtime.create(event);
		}
		if (event.cancelled) {
			super.create();
			return;
		}

		add(blackSpr = new FlxSprite(0, transOut ? -transitionCamera.height : transitionCamera.height)
			.makeGraphic(1, 1, FlxColor.WHITE));
		blackSpr.color = FlxColor.BLACK;
		var paths = new CodenamePaths(ownerRoot);
		try {
			transitionSprite = new FlxSprite().loadGraphic(paths.image('menus/transitionSpr'));
			add(transitionSprite);
		} catch (_:Dynamic) {
			// Codename's default art is core-owned. Never fall through to the
			// native/global asset namespace for an imported transition.
		}
		resizeDefaultSprites();
		transitionCamera.scroll.y = transitionCamera.height;
		transitionTween = FlxTween.tween(transitionCamera.scroll,
			{y: -transitionCamera.height}, SceneTransitionTiming.sceneDuration(2 / 3), {
				ease: FlxEase.sineOut,
				onComplete: function(_) finish()
			});

		super.create();
		if (runtime != null) runtime.postCreate(event);
	}

	override public function update(elapsed:Float):Void {
		if (RuntimeSmokeHarness.enabled()
			&& (smokeUpdateFrames++ == 0 || smokeUpdateFrames == 60
				|| smokeUpdateFrames == 120 || smokeUpdateFrames == 240))
			RuntimeSmokeHarness.markStep('transition-update:' + smokeUpdateFrames
				+ ':elapsed=' + Std.string(elapsed) + ':out=' + Std.string(transOut)
				+ ':' + (runtime == null ? 'no-runtime' : runtime.debugStatus()));
		if (runtime != null) runtime.update(elapsed);
		super.update(elapsed);
		if (nextFrameSkip) {
			var event = new CodenameMusicBeatTransitionEvent();
			if (runtime != null) runtime.skip(event);
			if (!event.cancelled) finish();
			return;
		}
		if (allowSkip && hostState != null && !hostState.persistentUpdate
			&& FlxG.keys != null && FlxG.keys.pressed.SHIFT) {
			if (newState != null) {
				nextFrameSkip = true;
				hostState.persistentDraw = false;
			} else {
				var event = new CodenameMusicBeatTransitionEvent();
				if (runtime != null) runtime.skip(event);
				if (!event.cancelled) finish();
			}
		}
		if (runtime != null) runtime.postUpdate(elapsed);
	}

	override public function onResize(width:Int, height:Int):Void {
		super.onResize(width, height);
		resizeDefaultSprites();
		if (runtime != null) runtime.resize(new CodenameMusicBeatTransitionEvent(transOut, scriptNewState));
	}

	public function resizeDefaultSprites():Void {
		if (transitionCamera == null) return;
		if (blackSpr != null) {
			blackSpr.scale.set(transitionCamera.width, transitionCamera.height);
			blackSpr.updateHitbox();
		}
		if (transitionSprite != null) {
			transitionSprite.setGraphicSize(transitionCamera.width, transitionCamera.height);
			transitionSprite.updateHitbox();
		}
	}

	public function finish():Void {
		if (finishing || destroyedTransition) return;
		if (RuntimeSmokeHarness.enabled()) RuntimeSmokeHarness.markStep('transition-finish:'
			+ Std.string(transOut) + ':' + (runtime == null ? 'no-runtime' : runtime.debugStatus()));
		var event = new CodenameMusicBeatTransitionEvent(transOut, scriptNewState);
		if (runtime != null) runtime.finish(event);
		if (event.cancelled) {
			if (scriptNewState != null)
				CodenameRequestedStateCompat.clearKnownTarget(scriptNewState);
			return;
		}
		if (runtime != null) runtime.captureStaticVariables();
		finishing = true;
		if (transOut) {
			CodenameTransitionScope.markOutgoingFinished(ownerRoot, stateHandoff, scriptPath);
			if (stateHandoff) {
				incomingSong.clear();
				var play = PlayState.instance;
				if (play != null && FlxG.state == play
					&& CodenameTransitionScope.sameOwner(play.codenameTransitionOwnerRoot(), ownerRoot)) {
					var view = play.codenameSongView();
					if (view != null) incomingSong.capture(ownerRoot, PlayState.SONG, view.getField('meta'));
				}
				watchIncomingState(ownerRoot);
			}
		}
		// A pause/game-over transition closes over a still-live state. Restore its
		// captured cameras, tweens, timers and sounds when this overlay is removed.
		// Only discard those references when the transition is handing off states.
		if (parentDisabler != null && (newState != null || outroComplete != null))
			parentDisabler.reset();
		if (newState != null) {
			switchingState = true;
			CodenameRequestedStateCompat.switchToKnownTarget(newState,
				function():Void FlxG.switchState(newState));
			switchingState = false;
		} else if (outroComplete != null) {
			outroComplete();
		}
		close();
		if (runtime != null) runtime.postFinish();
		if (!transOut && CodenameTransitionScope.hasStateHandoff(ownerRoot)) {
			CodenameTransitionScope.completeIncoming(ownerRoot);
			var chartStillOwnsSelector = CodenameTransitionScope.canRunOwner(ownerRoot,
				currentOwnerRoot(), '');
			if (!CodenameModRuntime.isActiveOwner(ownerRoot) && !chartStillOwnsSelector)
				clearOwner(ownerRoot);
		}
	}

	/** The upstream type's constructor is also used directly by a few scripts.
		This helper chooses the current native MusicBeatState as its host.
	*/
	public function open():Bool {
		var current = FlxG.state;
		if (!Std.isOfType(current, MusicBeatState)) return false;
		hostState = cast current;
		hostState.openSubState(this);
		return true;
	}

	override public function destroy():Void {
		if (destroyedTransition) return;
		destroyedTransition = true;
		if (!finishing && scriptNewState != null)
			CodenameRequestedStateCompat.clearKnownTarget(scriptNewState);
		if (runtime != null) {
			runtime.destroy();
			runtime = null;
		}
		if (transitionTween != null) {
			transitionTween.cancel();
			transitionTween = null;
		}
		if (transitionCamera != null) {
			if (FlxG.cameras.list.indexOf(transitionCamera) >= 0)
				FlxG.cameras.remove(transitionCamera, true);
			transitionCamera = null;
		}
		parentDisabler = null;
		sourceSong = null;
		super.destroy();
	}
}
