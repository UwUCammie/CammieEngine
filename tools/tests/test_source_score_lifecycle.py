"""Exercise the source-owned score callback/display lifecycle in PlayState."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


PSYCH_RUNTIME_BINDINGS = r'''
class LifecyclePsychRuntimeBindings {
    public static function dispatch(host:Dynamic, name:String, args:Array<Dynamic>,
        family:String = 'Scripts', ignoreStops:Bool = false, ?hscriptArgs:Array<Dynamic>):Dynamic {
        host.psychDispatchNames.push(name);
        host.psychDispatchArgs.push(args);
        var callback:Dynamic = host.psychDispatchCallback;
        if (callback != null) {
            var value:Dynamic = Reflect.callMethod(host, callback, [name, args]);
            if (value != null) return value;
        }
        return host.psychDispatchResults.get(name);
    }
}
'''


ENGINE_COMPAT = r'''
class LifecycleEngineCompat {
    public static function anyFunctionStop(values:Array<Dynamic>):Bool {
        for (value in values) if (value == ScriptCallbackResult.STOP) return true;
        return false;
    }
}
'''


NV_SCRIPT_GROUP = r'''
class LifecycleNightmareVisionScriptGroup {
    public static inline var CONTINUE_FUNC = 'NV_CONTINUE';
    public static inline var STOP_FUNC = 'NV_STOP';
}
'''


RUNTIME_SMOKE_HARNESS = r'''
class LifecycleRuntimeSmokeHarness {
    public static function markStep(name:String):Void {}
}
'''


HAXE_INTERP = r'''
package hscript;

import haxe.ds.StringMap;

class Interp {
    public var variables:StringMap<Dynamic> = new StringMap();
    public function new() {}
}
'''


FIXTURE = r'''
import hscript.Interp;

class HudMock {
    public var calls:Array<Array<Dynamic>> = [];
    public var beforeUpdate:Dynamic;
    public function new() {}
    public function onUpdateScore(score:Int, percent:Float, misses:Int, missed:Bool):Void {
        if (beforeUpdate != null) Reflect.callMethod(this, beforeUpdate, [score, percent, misses, missed]);
        calls.push([score, percent, misses, missed]);
    }
}

class SourceScoreLifecycleFixture {
    public var songScore:Int = 731;
    public var misses:Int = 0;
    public var sicks:Int = 1;
    public var goods:Int = 0;
    public var bads:Int = 0;
    public var shits:Int = 0;
    public var accuracy:Float = 100;
    public var totalPlayed:Int = 1;
    public var totalNotesHit:Float = 1;
    public var sourceAcceptedHits:Int = 0;
    public var sourceLedgerActive:Bool = false;
    public var epics:Int = 0;
    public var ratingStuff:Array<Dynamic> = [];
    public var instakillOnMiss:Bool = false;
    public var cpuControlled:Bool = false;
    public var scoreTxt:Dynamic = {text:'old text'};
    public var playHUD:HudMock = new HudMock();
    public var nightmareVisionScripts:Dynamic = null;
    public var selectedRoot:Dynamic = null;

    var psychRatingOverrides:Map<String,Dynamic> = [];
    var psychRatingRecalculating:Bool = false;
    var psychRatingPrevious:Dynamic = null;
    var psychScoreSnapshot:Dynamic = null;
    var psychScoreLastValues:Array<Float> = [];
    var psychHitsAdjustment:Int = 0;
    var hscriptStates:Map<String,Interp> = [];

    public var psychDispatchNames:Array<String> = [];
    public var psychDispatchArgs:Array<Array<Dynamic>> = [];
    public var psychDispatchResults:Map<String,Dynamic> = [];
    public var psychDispatchCallback:Dynamic;
    public var nightmareCalls:Array<String> = [];
    public var nightmareArgs:Array<Array<Dynamic>> = [];
    public var nightmareResults:Map<String,Dynamic> = [];
    public var bopCount:Int = 0;

    public function sourceScoreLedgerActive():Bool return sourceLedgerActive;
    public function sourceRatingHits(_index:Int, fallback:Int):Int return fallback;

    public var ratingPercent(get, never):Float;
    function get_ratingPercent():Float return sourceScoreSnapshot().rating;
    public var ratingName(get, never):String;
    function get_ratingName():String return sourceScoreSnapshot().ratingName;
    public var ratingFC(get, set):String;
    function get_ratingFC():String return sourceScoreSnapshot().ratingFC;
    function set_ratingFC(value:String):String {
        setPsychRatingValue('ratingFC', value);
        return value;
    }

    public function new() {}

__SOURCE_SCORE_SNAPSHOT__

__REFRESH_METHOD__

__SET_RATING_METHOD__

__SOURCE_DISPLAY_OWNED_METHOD__

__FULL_COMBO_METHOD__

__UPDATE_RATING_FC_METHOD__

__UPDATE_SCORE_METHOD__

__UPDATE_SCORE_TEXT_METHOD__

__UPDATE_SCORE_BAR_METHOD__

__RECALCULATE_RATING_METHOD__

__NOTIFY_RATING_METHOD__

    public function selectedPsychSkinRoot():Dynamic return selectedRoot;

    public function callNightmareVision(name:String, ?args:Array<Dynamic>):Dynamic {
        nightmareCalls.push(name);
        nightmareArgs.push(args == null ? [] : args);
        return nightmareResults.get(name);
    }

    public function callHscript(name:String, args:Array<Dynamic>, scope:String,
        optional:Bool = false, ?returns:Array<Dynamic>):Bool return false;

    public function doScoreBop():Void bopCount++;

    static function fail(message:String):Void throw message;
    static function check(value:Bool, message:String):Void if (!value) fail(message);

    static function clearPsychCalls(state:SourceScoreLifecycleFixture):Void {
        state.psychDispatchNames = [];
        state.psychDispatchArgs = [];
    }

    static function expectArgs(args:Array<Dynamic>, expected:Bool, message:String):Void {
        check(args != null && args.length == 1 && args[0] == expected, message);
    }

    static function checkPsychUpdateScoreStopAndSentinels():Void {
        var state = new SourceScoreLifecycleFixture();
        state.psychDispatchResults.set('preUpdateScore', ScriptCallbackResult.STOP);
        state.updateScore(false, true);
        check(state.scoreTxt.text == 'old text', 'exact Psych STOP must gate text refresh');
        check(state.bopCount == 0, 'exact Psych STOP must gate score bop');
        check(state.psychDispatchNames.length == 1
            && state.psychDispatchNames[0] == 'preUpdateScore',
            'exact Psych STOP must gate onUpdateScore');

        for (sentinel in [ScriptCallbackResult.STOP_LUA, ScriptCallbackResult.STOP_HSCRIPT,
                ScriptCallbackResult.STOP_ALL, 'Function_Stop']) {
            state = new SourceScoreLifecycleFixture();
            state.psychDispatchResults.set('preUpdateScore', sentinel);
            state.updateScore(false, true);
            check(StringTools.startsWith(state.scoreTxt.text, 'Score: 731'),
                'non-exact sentinel cancelled score text refresh: ' + sentinel);
            check(state.bopCount == 1, 'non-exact sentinel cancelled score bop: ' + sentinel);
            check(state.psychDispatchNames.length == 2
                && state.psychDispatchNames[0] == 'preUpdateScore'
                && state.psychDispatchNames[1] == 'onUpdateScore',
                'non-exact sentinel cancelled post hook: ' + sentinel);
        }

        state = new SourceScoreLifecycleFixture();
        state.psychDispatchResults.set('preUpdateScore', ScriptCallbackResult.CONTINUE);
        state.updateScore(true, true);
        check(state.psychDispatchNames.length == 2, 'miss update must call pre and post hooks');
        expectArgs(state.psychDispatchArgs[0], true, 'pre hook lost missed argument');
        expectArgs(state.psychDispatchArgs[1], true, 'post hook lost missed argument');
        check(state.bopCount == 0, 'miss update must not bop even when scoreBop is true');
        check(StringTools.startsWith(state.scoreTxt.text, 'Score: 731'),
            'miss update must still refresh the display');
    }

    static function checkNightmareVisionUpdateScoreBar():Void {
        var state = new SourceScoreLifecycleFixture();
        state.nightmareVisionScripts = {};
        state.accuracy = 72.34;
        state.misses = 3;
        state.nightmareResults.set('onUpdateScore', NightmareVisionScriptGroup.STOP_FUNC);
        state.updateScoreBar(true);
        check(state.nightmareCalls.length == 1 && state.nightmareCalls[0] == 'onUpdateScore',
            'Nightmare Vision display gate must run onUpdateScore');
        expectArgs(state.nightmareArgs[0], true, 'Nightmare Vision gate lost missed argument');
        check(state.playHUD.calls.length == 0, 'Nightmare Vision STOP must gate HUD update');
        check(state.psychDispatchNames.length == 0,
            'Nightmare Vision updateScoreBar must not add a Psych preUpdateScore hook');

        state.nightmareCalls = [];
        state.nightmareArgs = [];
        state.nightmareResults.set('onUpdateScore', NightmareVisionScriptGroup.CONTINUE_FUNC);
        state.updateScoreBar(true);
        check(state.nightmareCalls.length == 1 && state.playHUD.calls.length == 1,
            'Nightmare Vision continue must update the HUD once');
        var hudArgs = state.playHUD.calls[0];
        check(hudArgs.length == 4 && hudArgs[0] == 731 && hudArgs[1] == 72.34
            && hudArgs[2] == 3 && hudArgs[3] == true,
            'Nightmare Vision HUD arguments/order changed');
        check(state.psychDispatchNames.length == 0,
            'Nightmare Vision updateScoreBar unexpectedly dispatched a Psych prehook');
    }

    static function checkRatingStopKeepsValuesAndDisplays():Void {
        var state = new SourceScoreLifecycleFixture();
        state.selectedRoot = 'selected Psych source';
        state.accuracy = 85;
        state.psychScoreSnapshot = state.sourceScoreSnapshot();
        var previous = state.psychScoreSnapshot;
        state.accuracy = 55;
        state.misses = 2;
        state.psychDispatchResults.set('onRecalculateRating', ScriptCallbackResult.STOP);
        state.psychDispatchResults.set('preUpdateScore', ScriptCallbackResult.CONTINUE);
        state.psychDispatchCallback = function(name:String, args:Array<Dynamic>):Dynamic {
            if (name == 'onRecalculateRating') {
                state.setPsychRatingValue('ratingName', 'Script Name');
                state.ratingFC = 'Script FC';
                return ScriptCallbackResult.STOP;
            }
            return state.psychDispatchResults.get(name);
        };
        var fullComboCalls = 0;
        state.fullComboFunction = function():Void {
            fullComboCalls++;
            state.ratingFC = 'Default FC';
        };

        state.notifyPsychRatingChange(true, false);
        var mapped = state.sourceScoreSnapshot();
        check(mapped.rating == previous.rating, 'rating STOP did not preserve prior percentage');
        check(mapped.ratingName == 'Script Name', 'rating STOP discarded callback-written name');
        check(mapped.ratingFC == 'Script FC', 'rating STOP discarded callback-written FC label');
        check(fullComboCalls == 0, 'rating STOP must skip the dynamic FC override');
        check(state.psychDispatchNames.length == 3
            && state.psychDispatchNames[0] == 'onRecalculateRating'
            && state.psychDispatchNames[1] == 'preUpdateScore'
            && state.psychDispatchNames[2] == 'onUpdateScore',
            'rating STOP must still run the score display hook');
        expectArgs(state.psychDispatchArgs[1], true, 'display pre hook lost missed argument');
        expectArgs(state.psychDispatchArgs[2], true, 'display post hook lost missed argument');
        check(StringTools.startsWith(state.scoreTxt.text, 'Score: 731 | Misses: 2 | Rating: Script Name'),
            'rating STOP did not render preserved/written rating values');
        check(StringTools.endsWith(state.scoreTxt.text, 'Script FC'),
            'rating STOP display lost the callback-written FC value');
    }

    static function checkPsychDynamicFullComboLifecycle():Void {
        var state = new SourceScoreLifecycleFixture();
        state.selectedRoot = 'selected Psych source';
        state.sourceLedgerActive = true;
        state.ratingStuff = [['Low', 0.5], ['New', 0.8], ['Great', 0.9], ['Perfect', 1.0]];
        state.totalPlayed = 1;
        state.totalNotesHit = 0.4;
        state.psychScoreSnapshot = state.sourceScoreSnapshot();
        state.totalNotesHit = 0.85;

        var calls = 0;
        var observedPercent = -1.0;
        var observedName = '';
        var observedByPostHook = false;
        state.fullComboFunction = function():Void {
            calls++;
            observedPercent = state.ratingPercent;
            observedName = state.ratingName;
            state.ratingFC = 'Custom ' + observedName;
        };
        state.psychDispatchCallback = function(name:String, _args:Array<Dynamic>):Dynamic {
            if (name == 'onUpdateScore')
                observedByPostHook = state.ratingPercent == 0.85
                    && state.ratingName == 'Great' && state.ratingFC == 'Custom Great';
            return null;
        };

        state.RecalculateRating();
        check(calls == 1, 'Psych recalculation must invoke the dynamic fullComboFunction once');
        check(observedPercent == 0.85 && observedName == 'Great',
            'Psych fullComboFunction did not see the recalculated percent and name');
        check(observedByPostHook, 'Psych display post hook ran before the custom FC result was visible');
        check(StringTools.endsWith(state.scoreTxt.text, 'Custom Great'),
            'Psych display did not render the dynamic FC result');

        state = new SourceScoreLifecycleFixture();
        state.selectedRoot = 'selected Psych source';
        state.sourceLedgerActive = true;
        state.totalPlayed = 0;
        state.totalNotesHit = 0;
        state.psychScoreSnapshot = {rating:0.73, ratingName:'Previous', ratingFC:'Previous FC'};
        var emptyCalls = 0;
        var emptyPercent = -1.0;
        var emptyName = '';
        state.fullComboFunction = function():Void {
            emptyCalls++;
            emptyPercent = state.ratingPercent;
            emptyName = state.ratingName;
            state.ratingFC = 'Empty FC';
        };
        state.RecalculateRating();
        check(emptyCalls == 1, 'Psych fullComboFunction must run with zero played notes');
        check(emptyPercent == 0.73 && emptyName == '?',
            'zero-play Psych FC hook must see retained percent and recalculated ? name');
        check(state.ratingFC == 'Empty FC', 'zero-play Psych FC hook result was discarded');
    }

    static function checkNightmareVisionDynamicFullComboLifecycle():Void {
        var state = new SourceScoreLifecycleFixture();
        state.nightmareVisionScripts = {};
        state.sourceLedgerActive = true;
        state.ratingStuff = [
            {name:'Low', percent:0.5}, {name:'New', percent:0.8},
            {name:'Great', percent:0.9}, {name:'Perfect', percent:1.0}
        ];
        state.totalPlayed = 1;
        state.totalNotesHit = 0.4;
        state.psychScoreSnapshot = state.sourceScoreSnapshot();
        state.totalNotesHit = 0.85;

        var calls = 0;
        var observedPercent = -1.0;
        var observedName = '';
        state.updateRatingFC = function():Void {
            calls++;
            observedPercent = state.ratingPercent;
            observedName = state.ratingName;
            state.ratingFC = 'Custom ' + observedName;
        };
        var observedByHud = false;
        state.playHUD.beforeUpdate = function(_score:Int, percent:Float, _misses:Int, _missed:Bool):Void {
            observedByHud = state.ratingPercent == 0.85 && state.ratingName == 'Great'
                && state.ratingFC == 'Custom Great' && percent == 85;
        };
        state.RecalculateRating();
        check(calls == 1, 'NV recalculation must invoke dynamic updateRatingFC once');
        check(observedPercent == 0.85 && observedName == 'Great',
            'NV updateRatingFC did not see the recalculated percent and name');
        check(state.playHUD.calls.length == 1 && observedByHud,
            'NV HUD ran before the custom FC result was visible');

        state = new SourceScoreLifecycleFixture();
        state.nightmareVisionScripts = {};
        state.sourceLedgerActive = true;
        state.ratingStuff = [{name:'Low', percent:0.5}, {name:'Perfect', percent:1.0}];
        state.totalPlayed = 0;
        state.totalNotesHit = 0;
        state.psychScoreSnapshot = {rating:0.73, ratingName:'Previous', ratingFC:'Previous FC'};
        var emptyCalls = 0;
        var emptyPercent = -1.0;
        var emptyName = '';
        state.updateRatingFC = function():Void {
            emptyCalls++;
            emptyPercent = state.ratingPercent;
            emptyName = state.ratingName;
            state.ratingFC = 'Empty NV FC';
        };
        state.RecalculateRating();
        check(emptyCalls == 1, 'NV updateRatingFC must run with zero played notes');
        check(emptyPercent == 0.73 && emptyName == '?',
            'zero-play NV FC hook must see retained percent and recalculated ? name');
        check(state.ratingFC == 'Empty NV FC', 'zero-play NV FC hook result was discarded');

        state = new SourceScoreLifecycleFixture();
        state.nightmareVisionScripts = {};
        state.sourceLedgerActive = true;
        state.ratingStuff = [{name:'Low', percent:0.5}, {name:'Perfect', percent:1.0}];
        state.ratingFC = 'Custom held FC';
        state.psychScoreSnapshot = state.sourceScoreSnapshot();
        state.nightmareResults.set('onRecalculateRating', NightmareVisionScriptGroup.STOP_FUNC);
        state.nightmareResults.set('onUpdateScore', NightmareVisionScriptGroup.CONTINUE_FUNC);
        var stopCalls = 0;
        var stopPreservedByHud = false;
        state.updateRatingFC = function():Void {
            stopCalls++;
            state.ratingFC = 'Wrong FC';
        };
        state.playHUD.beforeUpdate = function(_score:Int, _percent:Float, _misses:Int, _missed:Bool):Void {
            stopPreservedByHud = state.ratingFC == 'Custom held FC';
        };
        state.RecalculateRating();
        check(stopCalls == 0, 'NV exact STOP must skip dynamic updateRatingFC');
        check(state.ratingFC == 'Custom held FC' && stopPreservedByHud,
            'NV exact STOP display did not preserve the existing custom FC');
        check(state.playHUD.calls.length == 1, 'NV exact STOP must still refresh the HUD');
    }

    static function checkDynamicOverrideReentryAndThrowRecovery():Void {
        var state = new SourceScoreLifecycleFixture();
        state.selectedRoot = 'selected Psych source';
        var ratingCalls = 0;
        state.psychDispatchCallback = function(name:String, _args:Array<Dynamic>):Dynamic {
            if (name == 'onRecalculateRating') ratingCalls++;
            return null;
        };
        var overrideCalls = 0;
        state.fullComboFunction = function():Void {
            overrideCalls++;
            state.RecalculateRating();
            state.ratingFC = 'Reentered safely';
        };
        state.RecalculateRating();
        check(ratingCalls == 1 && overrideCalls == 1,
            'RecalculateRating inside an FC override recursed through the lifecycle');
        check(state.ratingFC == 'Reentered safely', 'FC override write was lost after reentry');

        var threw = false;
        state.fullComboFunction = function():Void throw 'expected FC override failure';
        try state.RecalculateRating() catch (_:Dynamic) threw = true;
        check(threw, 'throwing Psych FC override was swallowed');
        check(!state.psychRatingRecalculating, 'throwing Psych FC override left recursion guard set');
        state.fullComboFunction = function():Void state.ratingFC = 'Recovered FC';
        state.RecalculateRating();
        check(state.ratingFC == 'Recovered FC' && !state.psychRatingRecalculating,
            'Psych rating lifecycle did not recover after an FC override threw');
    }

    static function checkNightmareVisionDynamicOverrideReentryAndThrowRecovery():Void {
        var state = new SourceScoreLifecycleFixture();
        state.nightmareVisionScripts = {};
        var overrideCalls = 0;
        state.updateRatingFC = function():Void {
            overrideCalls++;
            state.RecalculateRating();
            state.ratingFC = 'NV Reentered safely';
        };
        state.RecalculateRating();
        check(overrideCalls == 1 && state.nightmareCalls.length == 2,
            'NV RecalculateRating inside updateRatingFC recursed through the lifecycle');
        check(state.ratingFC == 'NV Reentered safely', 'NV FC override write was lost after reentry');

        state = new SourceScoreLifecycleFixture();
        state.nightmareVisionScripts = {};
        var threw = false;
        state.updateRatingFC = function():Void throw 'expected NV FC override failure';
        try state.RecalculateRating() catch (_:Dynamic) threw = true;
        check(threw, 'throwing NV FC override was swallowed');
        check(!state.psychRatingRecalculating, 'throwing NV FC override left recursion guard set');
        state.updateRatingFC = function():Void state.ratingFC = 'NV Recovered FC';
        state.RecalculateRating();
        check(state.ratingFC == 'NV Recovered FC' && !state.psychRatingRecalculating,
            'NV rating lifecycle did not recover after an FC override threw');
    }

    static function main():Void {
        checkPsychUpdateScoreStopAndSentinels();
        checkNightmareVisionUpdateScoreBar();
        checkRatingStopKeepsValuesAndDisplays();
        checkPsychDynamicFullComboLifecycle();
        checkNightmareVisionDynamicFullComboLifecycle();
        checkDynamicOverrideReentryAndThrowRecovery();
        checkNightmareVisionDynamicOverrideReentryAndThrowRecovery();
    }
}
'''


class SourceScoreLifecycleTest(unittest.TestCase):
    def test_source_score_callbacks_and_display_lifecycle(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        methods = {
            "__SOURCE_SCORE_SNAPSHOT__": extract_method(play_state, "function sourceScoreSnapshot("),
            "__REFRESH_METHOD__": extract_method(play_state, "function refreshPsychScoreGlobals("),
            "__SET_RATING_METHOD__": extract_method(play_state, "public function setPsychRatingValue("),
            "__SOURCE_DISPLAY_OWNED_METHOD__": extract_method(play_state, "function sourceScoreDisplayOwned("),
            "__FULL_COMBO_METHOD__": extract_method(play_state, "public dynamic function fullComboFunction("),
            "__UPDATE_RATING_FC_METHOD__": extract_method(play_state, "public dynamic function updateRatingFC("),
            "__UPDATE_SCORE_METHOD__": extract_method(play_state, "public dynamic function updateScore("),
            "__UPDATE_SCORE_TEXT_METHOD__": extract_method(play_state, "public dynamic function updateScoreText("),
            "__UPDATE_SCORE_BAR_METHOD__": extract_method(play_state, "public function updateScoreBar("),
            "__RECALCULATE_RATING_METHOD__": extract_method(play_state, "public function RecalculateRating("),
            "__NOTIFY_RATING_METHOD__": extract_method(play_state, "function notifyPsychRatingChange("),
        }
        fixture = FIXTURE
        for placeholder, method in methods.items():
            fixture = fixture.replace(placeholder, method)
        fixture = fixture.replace("PsychRuntimeBindings.", "LifecyclePsychRuntimeBindings.")
        fixture = fixture.replace("EngineCompat.", "LifecycleEngineCompat.")
        fixture = fixture.replace("NightmareVisionScriptGroup.", "LifecycleNightmareVisionScriptGroup.")
        fixture = fixture.replace("RuntimeSmokeHarness.", "LifecycleRuntimeSmokeHarness.")

        with tempfile.TemporaryDirectory(prefix="source-score-lifecycle-", dir=TEST_TMP) as folder:
            Path(folder, "SourceScoreLifecycleFixture.hx").write_text(fixture, newline="\n")
            Path(folder, "LifecyclePsychRuntimeBindings.hx").write_text(PSYCH_RUNTIME_BINDINGS, newline="\n")
            Path(folder, "LifecycleEngineCompat.hx").write_text(ENGINE_COMPAT, newline="\n")
            Path(folder, "LifecycleNightmareVisionScriptGroup.hx").write_text(NV_SCRIPT_GROUP, newline="\n")
            Path(folder, "LifecycleRuntimeSmokeHarness.hx").write_text(RUNTIME_SMOKE_HARNESS, newline="\n")
            Path(folder, "hscript").mkdir()
            Path(folder, "hscript/Interp.hx").write_text(HAXE_INTERP, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-main", "SourceScoreLifecycleFixture", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_create_initial_score_display_calls_precede_on_create_post(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        loader_start = play_state.index("function makeHaxeState(")
        module_start = play_state.index('startSucceeded = callHscript("start", [SONG.song], usehaxe, true);', loader_start)
        module_post = play_state.index('callHscript("createPost", [], usehaxe, true);', module_start)
        module_guard_start = play_state.rfind("if (selectedPsychSkinRoot() == null", module_start, module_post)
        module_guard = play_state[module_guard_start:module_post]
        self.assertIn("selectedPsychSkinRoot() == null || interp.variables.get('__psychScoreGlobals') != true", module_guard)
        self.assertLess(module_start, module_guard_start)
        self.assertLess(module_guard_start, module_post)

        start = play_state.index("override public function create()")
        end = play_state.index("\n\tfunction customIntro", start)
        create = play_state[start:end]
        intro_start = create.index("RuntimeSmokeHarness.markStep('playstate:create:intro-selection-begin');")
        display_start = create.index("RuntimeSmokeHarness.markStep('playstate:create:intro-dispatch-returned');", intro_start)
        initial_score = create[display_start:create.index("RuntimeSmokeHarness.markStep('playstate:create:countdown-returned');", display_start)]
        on_create_post = create.index("callNightmareVision('onCreatePost', []);", display_start)

        self.assertIn("if (sourceScoreDisplayOwned())", initial_score)
        self.assertEqual(initial_score.count("RecalculateRating(false, false);"), 1)
        self.assertEqual(initial_score.count("if (nightmareVisionScripts != null) updateScoreBar();"), 1)
        self.assertLess(display_start, on_create_post)
        self.assertLess(create.index("startCountdown();", intro_start), display_start)
        psych_post = create.index("if (selectedPsychSkinRoot() != null) PsychRuntimeBindings.dispatch(this, 'onCreatePost', []);")
        nightmare_vision_post = create.index("callNightmareVision('onCreatePost', []);", display_start)
        self.assertLess(display_start, psych_post)
        self.assertLess(psych_post, nightmare_vision_post)
        self.assertLess(nightmare_vision_post, create.index("RuntimeSmokeHarness.markStep('playstate:create:super-create-begin');"))

        notify = extract_method(play_state, "function notifyPsychRatingChange(")
        self.assertEqual(notify.count("updateScoreBar(missed);"), 1)
        self.assertEqual(notify.count("updateScore(missed, scoreBop);"), 1)
        # RecalculateRating -> notify produces one Psych display call. NV's
        # create path adds the explicit second updateScoreBar after that call.
        psych_initial_display_calls = notify.count("updateScore(missed, scoreBop);")
        nightmare_vision_initial_display_calls = notify.count("updateScoreBar(missed);") + initial_score.count(
            "if (nightmareVisionScripts != null) updateScoreBar();"
        )
        self.assertEqual(psych_initial_display_calls, 1)
        self.assertEqual(nightmare_vision_initial_display_calls, 2)
        self.assertIn("if (nightmareVisionScripts != null) updateScoreBar(missed);", notify)
        self.assertIn("else if (selectedPsychSkinRoot() != null) updateScore(missed, scoreBop);", notify)


if __name__ == "__main__":
    unittest.main()
