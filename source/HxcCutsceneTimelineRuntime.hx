package;

import HxcCutsceneTimeline.HxcCutsceneAction;
import HxcCutsceneTimeline.HxcCutsceneAsset;
import HxcCutsceneTimeline.HxcCutsceneEvent;
import HxcCutsceneTimeline.HxcCutsceneTime;
import HxcCutsceneTimeline.HxcCutsceneTimelineData;
import HxcCutsceneTimeline.HxcCutsceneTimelineDiagnostic;

/** A native-owned callback for one already validated, data-only action. */
typedef HxcCutsceneTimelineActionHandler = HxcCutsceneAction->Bool;

/** Resolves only an asset declared by the extracted timeline manifest. */
typedef HxcCutsceneTimelineAssetChecker = HxcCutsceneAsset->Bool;

/**
	Deterministic consumer for HxcCutsceneTimelineData.

	This class is deliberately independent from Flixel and HScript.  It owns the
	cutscene clock, event cursor, bounded time conversion, dialogue completion
	delay, cancellation, and one-shot countdown hand-off.  A native host supplies
	the action handler and asset checker; donor objects and donor closures never
	cross this boundary.
*/
class HxcCutsceneTimelineRuntime {
	public static inline var STATE_IDLE:String = 'idle';
	public static inline var STATE_RUNNING:String = 'running';
	public static inline var STATE_WAITING_DIALOGUE:String = 'waiting-dialogue';
	public static inline var STATE_FINISHED:String = 'finished';
	public static inline var STATE_CANCELLED:String = 'cancelled';

	public var timeline(default, null):HxcCutsceneTimelineData;
	public var diagnostics(default, null):Array<HxcCutsceneTimelineDiagnostic>;
	public var elapsed(default, null):Float = 0;
	public var eventIndex(default, null):Int = 0;
	public var dialogueElapsed(default, null):Float = 0;
	public var state(default, null):String = STATE_IDLE;

	/** Set by a native host after construction. */
	public var onAction:HxcCutsceneTimelineActionHandler;
	public var assetAvailable:HxcCutsceneTimelineAssetChecker;
	public var onHandoff:Void->Void;
	public var onCleanup:Void->Void;

	var crochetMilliseconds:Float;
	var eventTimes:Array<Null<Float>> = [];
	var dialogueEndDelay:Null<Float>;
	var dialogueEndRequested:Bool = false;
	var cleanupCalled:Bool = false;
	var handoffCalled:Bool = false;

	/**
		Recognized action kinds emitted by HxcCutsceneTimeline.  Keep this list
		explicit: a newly added extractor action must acquire a native consumer
		instead of silently executing through a dynamic object graph.
	*/
	public static function supportsAction(kind:String):Bool {
		return switch (kind == null ? '' : kind) {
			case 'captureDefaultZoom' | 'dialogueConfig' | 'spriteDefine' | 'spriteAdd'
				| 'spriteRemove' | 'cameraMove' | 'cameraZoom' | 'cameraShake'
				| 'cameraFade' | 'soundPlay' | 'musicPlay' | 'actorAnimation'
				| 'dialogueStart' | 'focusFirstSection' | 'musicFadeIn'
				| 'musicFadeOut' | 'musicFadeOutSkipped' | 'spriteAnimation' | 'visibility'
				| 'handoff' | 'removeOwnedFilter': true;
			default: false;
		};
	}

	public function new(data:HxcCutsceneTimelineData, crochetMs:Float) {
		timeline = data;
		crochetMilliseconds = isFinite(crochetMs) && crochetMs > 0 ? crochetMs : 0;
		diagnostics = [];
		if (timeline == null) {
			diagnose('error', 'invalid-hxc-cutscene-timeline',
				'Native timeline consumer received no data-only timeline.');
			return;
		}
		if (timeline.diagnostics != null)
			diagnostics = timeline.diagnostics.copy();
		if (timeline.version != HxcCutsceneTimeline.VERSION)
			diagnose('error', 'unsupported-hxc-cutscene-timeline-version',
				'Native timeline consumer does not support version ' + timeline.version + '.');

		if (timeline.events == null)
			timeline.events = [];
		if (timeline.events.length == 0)
			diagnose('error', 'invalid-hxc-cutscene-timeline-events',
				'Native timeline consumer requires at least one ordered event.');
		for (event in timeline.events)
			eventTimes.push(resolveTime(event == null ? null : event.at,
				'event timestamp'));
		dialogueEndDelay = resolveTime(timeline.dialogueEndDelay, 'dialogue completion delay');
		validateActions(timeline.initialActions, 'initial');
		for (index in 0...timeline.events.length)
			validateActions(timeline.events[index] == null ? null : timeline.events[index].actions,
				'event[' + index + ']');
		validateActions(timeline.dialogueEnd, 'dialogueEnd');
	}

	/** Start once, dispatching initial actions in source order. */
	public function start():Bool {
		if (state != STATE_IDLE || timeline == null || hasErrors()) {
			if (state == STATE_IDLE && hasErrors())
				failAndHandoff();
			return false;
		}
		state = STATE_RUNNING;
		elapsed = 0;
		eventIndex = 0;
		dialogueElapsed = 0;
		dialogueEndRequested = false;
		if (!dispatchActions(timeline.initialActions))
			return state == STATE_RUNNING || state == STATE_WAITING_DIALOGUE;
		return state == STATE_RUNNING || state == STATE_WAITING_DIALOGUE;
	}

	/**
		Advance the native clock. Events are consumed in the original array order;
		equal timestamps are intentionally not coalesced or re-sorted.
	*/
	public function advance(deltaSeconds:Float):Void {
		if (state != STATE_RUNNING && state != STATE_WAITING_DIALOGUE)
			return;
		var delta = isFinite(deltaSeconds) && deltaSeconds > 0 ? deltaSeconds : 0;
		if (state == STATE_RUNNING) {
			elapsed += delta;
			while (eventIndex < timeline.events.length) {
				var eventAt = eventTimes[eventIndex];
				if (eventAt == null || eventAt > elapsed + 0.000001)
					break;
				var event = timeline.events[eventIndex];
				eventIndex++;
				if (event != null && !dispatchActions(event.actions))
					break;
			}
		}
		if (state == STATE_WAITING_DIALOGUE) {
			dialogueElapsed += delta;
			if (dialogueEndDelay != null && dialogueElapsed + 0.000001 >= dialogueEndDelay)
				finishDialogue();
		}
	}

	/** Called by the native dialogue owner once its text has ended. */
	public function notifyDialogueEnd():Void {
		if (state != STATE_RUNNING && state != STATE_WAITING_DIALOGUE)
			return;
		dialogueEndRequested = true;
		dialogueElapsed = 0;
		state = STATE_WAITING_DIALOGUE;
		if (dialogueEndDelay == null || dialogueEndDelay <= 0)
			finishDialogue();
	}

	/** Complete a sound action's bounded callback after the native sound ends. */
	public function completeAction(action:HxcCutsceneAction):Void {
		if (action == null || action.onComplete == null
			|| (state != STATE_RUNNING && state != STATE_WAITING_DIALOGUE))
			return;
		dispatchActions(action.onComplete);
	}

	/** Cancel timers/actions and safely hand off so PlayState cannot remain stuck. */
	public function cancel(?handoff:Bool = true):Void {
		if (state == STATE_FINISHED || state == STATE_CANCELLED)
			return;
		state = STATE_CANCELLED;
		cleanup();
		if (handoff)
			handoffNow();
	}

	/** Force the bounded dialogue-end path (used by a missing dialogue owner). */
	public function finishNow():Void {
		if (state == STATE_FINISHED || state == STATE_CANCELLED)
			return;
		if (state == STATE_IDLE)
			start();
		if (state == STATE_FINISHED || state == STATE_CANCELLED)
			return;
		dialogueEndRequested = true;
		dialogueElapsed = dialogueEndDelay == null ? 0 : dialogueEndDelay;
		finishDialogue();
	}

	public function isDone():Bool {
		return state == STATE_FINISHED || state == STATE_CANCELLED;
	}

	function finishDialogue():Void {
		if (!dialogueEndRequested || (state != STATE_WAITING_DIALOGUE && state != STATE_RUNNING))
			return;
		dispatchActions(timeline.dialogueEnd);
		if (state != STATE_FINISHED && state != STATE_CANCELLED)
			handoffNow();
	}

	function dispatchActions(actions:Array<HxcCutsceneAction>):Bool {
		if (actions == null)
			return true;
		for (action in actions) {
			if (state == STATE_FINISHED || state == STATE_CANCELLED)
				return false;
			if (!dispatchAction(action))
				continue;
		}
		return true;
	}

	function dispatchAction(action:HxcCutsceneAction):Bool {
		if (action == null) {
			diagnose('warning', 'invalid-hxc-cutscene-action', 'Null action was skipped.');
			return false;
		}
		if (!supportsAction(action.kind)) {
			diagnose('warning', 'unsupported-hxc-cutscene-runtime-action',
				'Native timeline action is not supported: ' + action.kind + '.');
			return false;
		}
		var asset = actionAsset(action);
		if (action.asset != null && StringTools.trim(action.asset) != '' && asset == null)
			return false;
		if (asset != null) {
			if (assetAvailable != null && !assetAvailable(asset)) {
				diagnose('warning', 'missing-hxc-cutscene-asset',
					'Manifest-scoped cutscene asset is unavailable: ' + asset.kind + ':' + asset.key + '.');
				return false;
			}
		}
		if (onAction != null) {
			var handled = false;
			try handled = onAction(action) catch (error:Dynamic) {
				diagnose('warning', 'hxc-cutscene-native-action-error',
					'Native timeline action failed safely: ' + action.kind + ' (' + Std.string(error) + ').');
				return false;
			}
			if (!handled)
				diagnose('info', 'hxc-cutscene-native-action-skipped',
					'Native host skipped action: ' + action.kind + '.');
		}
		return true;
	}

	function actionAsset(action:HxcCutsceneAction):Null<HxcCutsceneAsset> {
		if (action == null || action.asset == null || StringTools.trim(action.asset) == '')
			return null;
		if (timeline == null || timeline.assets == null) {
			diagnose('warning', 'undeclared-hxc-cutscene-asset',
				'Action references an asset outside the extracted manifest: ' + action.asset + '.');
			return null;
		}
		for (asset in timeline.assets)
			if (asset != null && asset.key == action.asset)
				return asset;
		diagnose('warning', 'undeclared-hxc-cutscene-asset',
			'Action references an asset outside the extracted manifest: ' + action.asset + '.');
		return null;
	}

	function validateActions(actions:Array<HxcCutsceneAction>, owner:String):Void {
		if (actions == null)
			return;
		for (action in actions) {
			if (action == null || !supportsAction(action.kind))
				diagnose('error', 'unsupported-hxc-cutscene-runtime-action',
					owner + ' contains unsupported native action: ' + (action == null ? 'null' : action.kind) + '.');
			if (action != null && action.onComplete != null)
				validateActions(action.onComplete, owner + '.' + action.kind + '.onComplete');
		}
	}

	function resolveTime(time:HxcCutsceneTime, label:String):Null<Float> {
		if (time == null) {
			diagnose('error', 'unsupported-hxc-cutscene-time', label + ' is missing.');
			return null;
		}
		var value:Float = switch (time.kind == null ? '' : time.kind) {
			case 'seconds': time.value;
			case 'crochet-multiplier': crochetMilliseconds * time.value / 1000;
			default:
				diagnose('error', 'unsupported-hxc-cutscene-time',
					label + ' uses an unsupported bounded expression: ' + time.kind + '.');
				return null;
		};
		if (!isFinite(value) || value < 0) {
			diagnose('error', 'unsupported-hxc-cutscene-time',
				label + ' is not a finite non-negative bounded time.');
			return null;
		}
		return value;
	}

	function hasErrors():Bool {
		for (entry in diagnostics)
			if (entry != null && entry.severity == 'error')
				return true;
		return false;
	}

	function failAndHandoff():Void {
		state = STATE_CANCELLED;
		cleanup();
		handoffNow();
	}

	function cleanup():Void {
		if (cleanupCalled)
			return;
		cleanupCalled = true;
		if (onCleanup != null)
			try onCleanup() catch (error:Dynamic)
				diagnose('warning', 'hxc-cutscene-cleanup-error',
					'Native timeline cleanup failed safely: ' + Std.string(error) + '.');
	}

	function handoffNow():Void {
		if (handoffCalled)
			return;
		handoffCalled = true;
		state = STATE_FINISHED;
		cleanup();
		if (onHandoff != null)
			try onHandoff() catch (error:Dynamic)
				diagnose('warning', 'hxc-cutscene-handoff-error',
					'Native timeline countdown hand-off failed safely: ' + Std.string(error) + '.');
	}

	function diagnose(severity:String, code:String, message:String):Void {
		var entry:HxcCutsceneTimelineDiagnostic = {severity:severity, code:code, message:message};
		diagnostics.push(entry);
	}

	static function isFinite(value:Float):Bool {
		return !Math.isNaN(value) && value != Math.POSITIVE_INFINITY && value != Math.NEGATIVE_INFINITY;
	}
}
