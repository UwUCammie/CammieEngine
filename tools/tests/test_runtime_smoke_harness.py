"""Source-level coverage for the post-build native runtime smoke gate."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
MATRIX_PATH = ROOT / "tools" / "run_runtime_smoke_matrix.py"
HAXE = ROOT / ".tools" / "haxe" / "haxe"


def load_matrix_module():
    spec = importlib.util.spec_from_file_location("runtime_smoke_matrix", MATRIX_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load runtime smoke matrix module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def extract_haxe_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated Haxe method: {marker}")


class RuntimeSmokeHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = (SOURCE / "RuntimeSmokeHarness.hx").read_text()
        cls.state = (SOURCE / "RuntimeSmokeState.hx").read_text()
        cls.main = (SOURCE / "Main.hx").read_text()
        cls.play_state = (SOURCE / "PlayState.hx").read_text()
        cls.import_harness = (SOURCE / "RuntimeImportSmokeHarness.hx").read_text()
        cls.import_state = (SOURCE / "RuntimeImportSmokeState.hx").read_text()
        cls.matrix = load_matrix_module()

    def test_native_entry_point_is_opt_in_and_playstate_hooks_are_bounded(self):
        self.assertIn("RuntimeSmokeHarness.enabled()", self.main)
        self.assertIn("initialState = RuntimeSmokeState", self.main)
        self.assertIn("RuntimeSmokeHarness.applyRuntimeRoot()", self.main)
        self.assertIn("RuntimeSmokeHarness.markPlayStateStart(SONG)", self.play_state)
        self.assertIn("RuntimeSmokeHarness.markPlayStateReady(SONG)", self.play_state)
        self.assertIn("RuntimeSmokeHarness.tick(elapsed)", self.play_state)
        self.assertIn("Sys.exit(0)", self.harness)
        self.assertIn("Sys.exit(1)", self.harness)
        self.assertIn("--smoke-runtime-root", self.harness)
        self.assertNotIn("OptionsHandler.options =", self.harness + self.state)

    def test_markers_are_machine_readable_and_required_runtime_setup_is_present(self):
        for marker in ("startup", "playstate_start", "playstate_ready", "success", "failure"):
            self.assertIn(f"emit('{marker}'", self.harness)
        for setup in ("PluginManager.init()", "DifficultyManager.init()", "ModifierState.init()", "PlayerSettings.init()"):
            self.assertIn(setup, self.state)
        for flag in ("--smoke-song", "--smoke-chart", "--smoke-difficulty", "--smoke-duration-ms", "--smoke-log"):
            self.assertIn(flag, self.harness)
        self.assertIn("FlxG.autoPause = false", self.state)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_song_end_settle_finishes_after_playstate_handoff_without_faking_handoff(self):
        ready = extract_haxe_method(
            self.harness, "public static function markPlayStateReady("
        )
        self.assertIn(
            "if (config().requireSongEnd || config().requireEndHandoff)", ready
        )
        self.assertIn("installSongEndCompletionWatch();", ready)
        watch = extract_haxe_method(
            self.harness, "static function installSongEndCompletionWatch()"
        )
        self.assertIn("observeSongEndCompletion(Std.isOfType(FlxG.state, PlayState), settled);", watch)
        observe = extract_haxe_method(
            self.harness, "static function observeSongEndCompletion("
        )
        fixture = r'''class FlxG { public static var state:Dynamic; }
class PlayState {}
class Main {
 static var cfg:Dynamic={requireEndHandoff:false};
 static var finished=false;
 static var naturalSongEndObserved=true;
 static var handoffObserved=false;
 static var handoffCount=0;
 static var successCount=0;
 static function config():Dynamic return cfg;
 static function markEndHandoff():Void {
  if (!handoffObserved) {handoffObserved=true;handoffCount++;}
 }
 static function succeed():Void {successCount++;finished=true;}
''' + observe + r'''
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  observeSongEndCompletion(true,true);
  check(successCount==0 && handoffCount==0,"observer completed while PlayState remained active");
  observeSongEndCompletion(false,false);
  check(successCount==0 && handoffCount==0,"completion-only run skipped its settle window or faked handoff");
  observeSongEndCompletion(false,true);
  check(successCount==1 && handoffCount==0,"completion-only return did not succeed cleanly");
  finished=false; handoffObserved=false; cfg.requireEndHandoff=true;
  observeSongEndCompletion(false,false);
  check(successCount==1 && handoffCount==1,"strict run did not record the handoff before settling");
  observeSongEndCompletion(false,true);
  check(successCount==2 && handoffCount==1,"strict run did not succeed after settling exactly one handoff");
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture_path = Path(folder) / "Main.hx"
            fixture_path.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [str(HAXE), "-cp", str(folder), "--interp", "-main", "Main"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_diagnostic_boundaries_cover_countdown_skin_and_ready_handoffs(self):
        countdown = extract_haxe_method(self.play_state,
                                       "public function startCountdown():Void {")
        phases = (
            "countdown:modchart-load-begin",
            "countdown:modchart-load-complete",
            "countdown:psych-scripts-begin",
            "countdown:psych-scripts-complete",
            "countdown:creation-visuals-begin",
            "countdown:creation-visuals-complete",
            "countdown:codename-event-scripts-begin",
            "countdown:codename-event-scripts-complete",
            "countdown:song-loaded-callbacks-begin",
            "countdown:song-loaded-callbacks-complete",
            "countdown:countdownStart-callback-begin",
            "countdown:countdownStart-callback-complete",
            "countdown:startCountdown-callback-begin",
            "countdown:startCountdown-callback-complete",
            "countdown:timer-setup-begin",
            "countdown:timer-setup-complete",
        )
        positions = [countdown.index(phase) for phase in phases]
        self.assertEqual(positions, sorted(positions))
        create_phases = (
            "playstate:create:ui-layout-begin",
            "playstate:create:ui-layout-complete",
            "playstate:create:intro-selection-begin",
            "playstate:create:intro-dispatch-returned",
            "playstate:create:countdown-returned",
            "playstate:create:super-create-begin",
            "playstate:create:super-create-complete",
            "playstate:create:stateChangeEnd-begin",
            "playstate:create:stateChangeEnd-complete",
        )
        create_positions = [self.play_state.index(phase) for phase in create_phases]
        self.assertEqual(create_positions, sorted(create_positions))

        failure = extract_haxe_method(self.harness,
                                      "public static function markNoteGenerationFailure(")
        self.assertIn("setPsychSkinDiagnosticPhase", self.harness)
        self.assertIn("psychSkinPhase", failure)

    def test_player_hit_trace_samples_live_actor_after_hit_route_returns(self):
        self.assertIn("tracePlayerHits:Bool", self.harness)
        self.assertIn("case '--smoke-trace-player-hits'", self.harness)
        self.assertIn("if (config().tracePlayerHits)", self.harness)
        self.assertIn("player1GoodHitSignal.connect", self.harness)
        self.assertIn("pendingPlayerHitProbes.push({", self.harness)
        self.assertIn("pendingPlayerHitProbes = [];", self.harness)
        self.assertIn("flushPlayerHitProbes();", self.harness)
        self.assertIn("emit('player1_good_hit_postroute'", self.harness)
        self.assertNotIn("note: note", self.harness)
        for field in (
            "signalOwner: 'player1'",
            "mustPress: note.mustPress",
            "shouldBeSung: note.shouldBeSung",
            "actorMatchesBoyfriend: actor == gameState.boyfriend",
            "judgementSongPosition: Conductor.songPosition",
            "sampleSongPosition: Conductor.songPosition",
            "animation: current == null ? '' : Reflect.field(current, 'name')",
        ):
            self.assertIn(field, self.harness)

    def test_smoke_practice_ignores_menu_preference_and_cannot_save_scores(self):
        setup = self.play_state.index("// Smoke practice must also work")
        self.assertIn("RuntimeSmokeHarness.config().practice", self.play_state[setup:setup + 250])
        self.assertIn("practiceMode = true;", self.play_state[setup:setup + 250])
        guard = "if (!RuntimeSmokeHarness.enabled() && !demoMode && ModifierState.scoreMultiplier > 0)"
        self.assertEqual(self.play_state.count(guard), 2)

    def test_targeted_freeplay_smoke_continues_through_default_play_modifier(self):
        self.assertIn("freeplay_modifier_start", self.harness)
        self.assertIn("freeplay_modifier_accept_begin", self.harness)
        self.assertIn("Std.isOfType(FlxG.state, ModifierState)", self.harness)
        self.assertIn("ModifierState.modifiers[index].internName", self.harness)
        self.assertIn("modifierSelection.action != 'play'", self.harness)
        self.assertIn("Accepted Freeplay song did not reach PlayState", self.harness)
        self.assertIn("deadline = Sys.time() + config().durationMs / 1000.0;", self.harness)
        # Launching through ModifierState must not mutate either saved options
        # or modifier selections: ENTER is sent only when Play is selected.
        self.assertNotIn("OptionsHandler.options =", self.harness)
        self.assertNotIn("ModifierState.modifiers[index].value =", self.harness)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_modifier_selection_observation_does_not_change_modifier_values(self):
        method = extract_haxe_method(
            self.harness, "static function modifierSelectionObservation():Dynamic")
        fixture = """class ModifierState {
  public static var modifiers:Array<Dynamic> = [
    {internName: 'antijank', value: false},
    {internName: 'play', value: false}
  ];
}
class FlxG { public static var state:Dynamic = {curSelected: 1}; }
class Main {
""" + method + """
  static function main():Void {
    var selected = modifierSelectionObservation();
    if (selected.selection != 1 || selected.action != 'play')
      throw 'default Play action was not observed';
    if (ModifierState.modifiers[1].value)
      throw 'observation changed a modifier value';
    FlxG.state = {curSelected: 0};
    if (modifierSelectionObservation().action == 'play')
      throw 'observation ignored the current selection';
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture_path = Path(folder) / "Main.hx"
            fixture_path.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [str(HAXE), "-cp", str(folder), "--interp", "-main", "Main"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_botplay_smoke_uses_actual_demo_route_without_saved_modifiers(self):
        self.assertIn("case '--smoke-botplay'", self.harness)
        self.assertIn("botplay: false", self.harness)
        self.assertIn("RuntimeSmokeHarness.enabled() && RuntimeSmokeHarness.config().botplay", self.play_state)
        setup = self.play_state.index("RuntimeSmokeHarness.config().botplay")
        self.assertIn("demoMode = true", self.play_state[setup:setup + 150])
        self.assertIn("maxStepCatchUp = 0", self.play_state[setup:setup + 150])

    def test_selected_codename_owner_is_checked_against_chart_manifest(self):
        self.assertIn("case '--smoke-owner-root'", self.harness)
        self.assertIn("ownerRoot: config().ownerRoot", self.harness)
        self.assertIn("CompatScriptManifest.selectedRoot(manifest)", self.state)
        self.assertIn("CodenameModRuntime.activateChartOwner(request.ownerRoot)", self.state)

    def test_gameplay_frame_profiler_is_opt_in_and_records_song_time(self):
        self.assertIn("case '--smoke-frame-stats'", self.harness)
        self.assertIn("frameStats: false", self.harness)
        self.assertIn("if (config().frameStats)\n\t\t\tinstallFrameStats();", self.harness)
        self.assertIn("songPosition: playStateReady ? Conductor.songPosition : null", self.harness)

    def test_character_swap_probe_is_smoke_only_and_measures_elapsed_time(self):
        self.assertIn("emit('character_swap_decode', snapshot);", self.harness)
        for field in ('bitmapCacheHits', 'bitmapCacheMisses', 'bitmapDecodeMs'):
            self.assertIn(field, self.harness + (SOURCE / 'RuntimeDecodeMetrics.hx').read_text())
        self.assertIn('RuntimeSmokeHarness.beginCharacterSwap()', self.play_state)
        self.assertIn('RuntimeSmokeHarness.markCharacterSwap(smokeSwapStartedAt, charTo, charState);',
                      self.play_state)

    def test_matrix_has_six_families_and_all_named_regressions(self):
        cases = self.matrix.SMOKE_MATRIX
        families = {case.family for case in cases[:6]}
        self.assertEqual(
            families,
            {"V-Slice", "Psych Engine", "Kade Engine", "Legacy FNF/Polymod", "Modding Plus", "FPS Plus"},
        )
        expected_representatives = {
            "V-Slice": ("dokidoggle", "dokidoggle", "normal"),
            "Psych Engine": ("resonance", "resonance-hard", "hard"),
            "Kade Engine": ("tutorial", "tutorial", "normal"),
            "Legacy FNF/Polymod": ("thorns", "thorns", "normal"),
            "Modding Plus": ("slaughter", "slaughter", "normal"),
            "FPS Plus": ("ballistic", "ballistic", "normal"),
        }
        actual_representatives = {
            case.family: (case.folder, case.chart, case.difficulty) for case in cases[:6]
        }
        self.assertEqual(actual_representatives, expected_representatives)
        self.assertEqual(set(self.matrix.ENGINE_FAMILY_EVIDENCE), set(expected_representatives))
        for evidence in self.matrix.ENGINE_FAMILY_EVIDENCE.values():
            self.assertIn("/data/", evidence)
            self.assertTrue(evidence.endswith(".json"))
        required = {
            "chaos",
            "inquiry",
            "locked",
            "cycles-wrath",
            "cycles-encore-springless",
            "popipo",
            "fnia-ugh",
        }
        self.assertTrue(required.issubset({case.id for case in cases}))
        expected_named = {
            "chaos": ("chaos", "chaos-hard", "hard"),
            "inquiry": ("inquiry", "inquiry-hard", "hard"),
            "locked": ("locked", "locked-hard", "hard"),
            "cycles-wrath": ("cycles-wrath", "cycles-wrath-hard", "hard"),
            "cycles-encore-springless": (
                "cycles-encore-springless",
                "cycles-encore-springless-encore",
                "encore",
            ),
            "popipo": ("popipo", "popipo-hard", "hard"),
            "fnia-ugh": ("fnia-ugh", "fnia-ugh-hard", "hard"),
        }
        actual_named = {
            case.id: (case.folder, case.chart, case.difficulty)
            for case in cases
            if case.id in expected_named
        }
        self.assertEqual(actual_named, expected_named)
        self.assertEqual(set(self.matrix.NAMED_REGRESSION_EVIDENCE), set(expected_named))
        donor_root = "/run/media/cammie/External Storage/modding-plus-fnf/"
        for evidence in self.matrix.NAMED_REGRESSION_EVIDENCE.values():
            self.assertTrue(evidence.startswith(donor_root))
            self.assertTrue(evidence.endswith(".json"))
        expected_examples = {
            "example-expurgation", "example-wacky-hard", "example-wacky-nightmare",
            "example-rabbit-hole", "example-fantasy-girl-01", "example-vs-freddy",
            "example-ballistic", "example-future-sound", "example-resonance",
            "example-cursed-expurgation",
        }
        self.assertEqual(
            {case.id for case in cases if case.family == "example regression"},
            expected_examples,
        )
        self.assertEqual(set(self.matrix.EXAMPLE_REGRESSION_EVIDENCE), expected_examples)
        mounted_examples = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
        for evidence in self.matrix.EXAMPLE_REGRESSION_EVIDENCE.values():
            self.assertFalse(Path(evidence).is_absolute())
            self.assertTrue(evidence.endswith(".json"))
            if mounted_examples.is_dir():
                self.assertTrue((mounted_examples / evidence).is_file(), evidence)
        self.assertEqual(len(cases), len({case.id for case in cases}))
        for case in cases:
            self.assertTrue(case.folder)
            self.assertTrue(case.chart)
            self.assertGreater(case.timeout_seconds, 0)

    def test_command_uses_project_local_log_and_optional_fixture_root(self):
        case = self.matrix.SMOKE_MATRIX[-1]
        command = self.matrix.build_command(
            Path("/build/Funkin"),
            case,
            3000,
            ROOT / "tmp/runtime-smoke/logs/fnia-ugh.log",
            runtime_root=ROOT / "tmp/runtime-smoke/fixture",
        )
        self.assertEqual(command[0], "/build/Funkin")
        self.assertIn("--smoke-runtime-root", command)
        self.assertIn(str(ROOT / "tmp/runtime-smoke/logs/fnia-ugh.log"), command)
        self.assertNotIn("--build", command)
        readme = (ROOT / "README.md").read_text()
        update_log = (ROOT / "updateLog.txt").read_text()
        for token in (
            "tools/run_runtime_smoke_matrix.py",
            "--runtime-root",
            "--asset-root",
            "tmp/runtime-smoke/logs/",
            "does not build anything automatically",
        ):
            self.assertIn(token, readme)
        self.assertIn("native runtime smoke matrix", update_log)

    def test_native_smoke_launches_only_on_isolated_display(self):
        command = self.matrix.offscreen_command(["/build/Funkin", "--smoke-song", "test"], "/usr/bin/xvfb-run")
        self.assertEqual(command[:4], ["/usr/bin/xvfb-run", "-a", "-s", "-screen 0 1280x720x24"])
        self.assertEqual(command[4:], ["/build/Funkin", "--smoke-song", "test"])
        with patch.object(self.matrix.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "xvfb-run is required"):
                self.matrix.offscreen_command(["/build/Funkin"])

    def test_marker_parser_ignores_traces_but_keeps_json_events(self):
        markers = self.matrix.parse_markers(
            "trace: normal output\n"
            'RUNTIME_SMOKE|{"event":"startup","marker":"runtime-smoke"}\n'
            'RUNTIME_SMOKE|{"event":"success","durationMs":3000}\n'
            "RUNTIME_SMOKE|not-json\n"
        )
        self.assertEqual([marker["event"] for marker in markers], ["startup", "success"])

    def test_strict_diagnostics_rejects_script_errors_after_success(self):
        case = self.matrix.SmokeCase("strict-errors", "test", "strict", "strict")
        output = "\n".join(
            "RUNTIME_SMOKE|" + json.dumps({"event": event})
            for event in ("startup", "playstate_start", "playstate_ready", "success")
        ) + "\nsource/PlayState.hx:42: [codename-script-error] stage.stepHit: missing export\n"

        class FakeProcess:
            returncode = 0

            def __init__(self, *_args, **_kwargs):
                pass

            def communicate(self, timeout=None):
                return output, None

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            binary = base / "Funkin"
            binary.write_bytes(b"placeholder")
            (base / "assets" / "data").mkdir(parents=True)
            (base / "assets" / "data" / "options.json").write_text("{}")
            with patch.object(self.matrix, "LOG_ROOT", base / "logs"), patch.object(
                self.matrix, "offscreen_command", side_effect=lambda command: command
            ), patch.object(self.matrix.subprocess, "Popen", side_effect=FakeProcess):
                result = self.matrix.run_case(binary, case, duration_ms=1000,
                                              strict_diagnostics=True)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["diagnostic_count"], 1)
        self.assertIn("native script diagnostic", result["reason"])
        self.assertEqual(len(self.matrix.runtime_diagnostics(
            "[hxc-unsupported-hxc-module-body] source callback\n"
            "[codename-script-unused-enum-elided] recoverable\n")), 1)
        self.assertEqual(self.matrix.runtime_diagnostics("MissingMod modifier was not found !\n"),
                         ["MissingMod modifier was not found !"])
        self.assertEqual(self.matrix.runtime_diagnostics(
            "source/PlayState.hx:8322: [psych-stage] callback create failed: EInvalidAccess(x)\n"),
            ["source/PlayState.hx:8322: [psych-stage] callback create failed: EInvalidAccess(x)"])
        self.assertEqual(self.matrix.runtime_diagnostics(
            "[psych-stage-video] could not play selected-owner video end.mp4\n"
            "[hxc-video-missing] end.mp4\n"),
            ["[psych-stage-video] could not play selected-owner video end.mp4",
             "[hxc-video-missing] end.mp4"])
        self.assertEqual(self.matrix.runtime_diagnostics(
            'RUNTIME_SMOKE|{"event":"success","message":"hscript error"}\n'
            'source/PlayState.hx:1414: hscript error in compat_song_0.createPost: Null Function Pointer\n'
        ), ['source/PlayState.hx:1414: hscript error in compat_song_0.createPost: Null Function Pointer'])
        self.assertEqual(self.matrix.runtime_diagnostics('Null Function Pointer\nError : Null Function Pointer\n'),
                         ['Null Function Pointer', 'Error : Null Function Pointer'])
        self.assertEqual(self.matrix.runtime_diagnostics('Invalid field:moveCameraSection\n'),
                         ['Invalid field:moveCameraSection'])
        self.assertEqual(self.matrix.runtime_diagnostics(
            '[hscript-null-operand] "+" used a null operand\n'
            '[hscript-null-iterator] for-in used a null value\n'
            'source/HxcWindowCompat.hx:33: [hxc-window] missing icon: assets/dokicon.png\n'),
            ['[hscript-null-operand] "+" used a null operand',
             '[hscript-null-iterator] for-in used a null value',
             'source/HxcWindowCompat.hx:33: [hxc-window] missing icon: assets/dokicon.png'])

    def test_timeout_output_handles_bytes_then_text_without_losing_diagnostics(self):
        class TimedOutProcess:
            returncode = -9

            def communicate(self, timeout=None):
                if timeout is not None:
                    raise subprocess.TimeoutExpired(
                        ["fake-funkin"], timeout, output=b"startup\npartial-\xff\n"
                    )
                return "tail-after-kill\n", None

            def kill(self):
                return None

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            folder_path = Path(folder)
            binary = folder_path / "Funkin"
            binary.write_bytes(b"placeholder")
            (folder_path / "assets" / "data").mkdir(parents=True)
            log_root = folder_path / "logs"
            case = self.matrix.SMOKE_MATRIX[0]
            with patch.object(self.matrix, "LOG_ROOT", log_root), patch.object(
                self.matrix.subprocess, "Popen", return_value=TimedOutProcess()
            ):
                result = self.matrix.run_case(
                    binary,
                    case,
                    duration_ms=3000,
                    timeout_seconds=0.01,
                )

            self.assertTrue(result["timed_out"])
            self.assertEqual(result["returncode"], -9)
            self.assertIn("timeout after 0.01s", result["reason"])
            process_log = (log_root / f"{case.id}.process.log").read_text()
            self.assertEqual(process_log, "startup\npartial-�\ntail-after-kill\n")

    def test_runtime_process_uses_project_local_temp_directory(self):
        runner = MATRIX_PATH.read_text()
        self.assertIn('"TMPDIR": str(overlay_root / "scratch")', runner)

    def test_each_case_uses_default_options_and_private_save_overlay(self):
        case = self.matrix.SMOKE_MATRIX[0]
        markers = "\n".join(
            "RUNTIME_SMOKE|" + json.dumps({"event": event})
            for event in ("startup", "playstate_start", "playstate_ready", "success")
        ) + "\n"
        observations = []

        class FakeProcess:
            returncode = 0

            def __init__(self, command, **kwargs):
                cwd = Path(kwargs["cwd"])
                env = kwargs["env"]
                options = cwd / "assets" / "data" / "options.json"
                observations.append((
                    cwd, options.read_bytes(),
                    (cwd / "assets" / "images").is_symlink(),
                    (cwd / "assets" / "data" / "chart").is_symlink(),
                    (cwd / "assets" / "imported_mods" / "selected" / "stages" / "Haven.lua").is_file()
                    and not (cwd / "assets" / "imported_mods" / "selected" / "stages" / "Haven.lua").is_symlink(),
                    (cwd / "assets" / "imported_mods" / "selected" / "images" / "large.png").is_file()
                    and not (cwd / "assets" / "imported_mods" / "selected" / "images" / "large.png").is_symlink(),
                    (cwd / "assets" / "imported_mods" / "global-provider" / "scripts" / "results.lua").is_file()
                    and not (cwd / "assets" / "imported_mods" / "global-provider" / "scripts" / "results.lua").is_symlink(),
                    {key: env[key] for key in
                     ("XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "TMPDIR")},
                    command,
                ))

            def communicate(self, timeout=None):
                return markers, None

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source = Path(folder) / "source"
            (source / "assets" / "data" / "chart").mkdir(parents=True)
            (source / "assets" / "images").mkdir()
            selected = source / "assets" / "imported_mods" / "selected"
            (selected / "stages").mkdir(parents=True)
            (selected / "images").mkdir()
            (selected / "stages" / "Haven.lua").write_text("function onCreate() end")
            (selected / "images" / "large.png").write_bytes(b"media")
            provider = source / "assets" / "imported_mods" / "global-provider"
            (provider / "scripts").mkdir(parents=True)
            (provider / "scripts" / "results.lua").write_text("function onEndSong() end")
            (source / "assets" / "imported_mods" / "globalResultsProvider.json").write_text(
                json.dumps({"version": 1, "defaultOwner": "assets/imported_mods/global-provider"})
            )
            (source / "assets" / "data" / case.folder).mkdir()
            (source / "assets" / "data" / case.folder / "compatScripts.json").write_text(
                json.dumps({"roots": [{"path": "assets/imported_mods/selected"}]})
            )
            (source / "assets" / "data" / "options.json").write_bytes(b'{"offset":251}')
            binary = source / "Funkin"
            binary.write_bytes(b"placeholder")
            log_root = Path(folder) / "logs"
            with patch.object(self.matrix, "LOG_ROOT", log_root), patch.object(
                self.matrix, "offscreen_command", side_effect=lambda command: command
            ), patch.object(self.matrix.subprocess, "Popen", side_effect=FakeProcess):
                result = self.matrix.run_case(binary, case, duration_ms=3000, runtime_root=source)
            self.assertEqual(result["status"], "passed", result)
            self.assertEqual((source / "assets" / "data" / "options.json").read_bytes(), b'{"offset":251}')
            self.assertFalse(observations[0][0].exists())

        cwd, default_bytes, images_link, chart_link, script_copy, media_copy, provider_copy, private_paths, command = observations[0]
        self.assertEqual(default_bytes, (ROOT / "assets" / "data" / "options.json").read_bytes())
        self.assertTrue(images_link)
        self.assertTrue(chart_link)
        self.assertTrue(script_copy)
        self.assertTrue(media_copy)
        self.assertTrue(provider_copy)
        for path in private_paths.values():
            self.assertEqual(Path(path).parent, cwd)
        self.assertIn("--smoke-runtime-root", command)
        self.assertEqual(command[command.index("--smoke-runtime-root") + 1], str(cwd))

    def test_cross_song_switch_copies_both_owner_scripts(self):
        first = self.matrix.SmokeCase("switch-first", "test", "first", "first")
        second = self.matrix.SmokeCase("switch-second", "test", "second", "second-hard", "hard")
        observations = []

        class FakeProcess:
            returncode = 0

            def __init__(self, command, **kwargs):
                cwd = Path(kwargs["cwd"])
                observations.append((command, [
                    (cwd / "assets" / "imported_mods" / owner / "scripts" / "test.lua").is_file()
                    and not (cwd / "assets" / "imported_mods" / owner / "scripts" / "test.lua").is_symlink()
                    for owner in ("first-owner", "second-owner")]))

            def communicate(self, timeout=None):
                markers = [{"event": "startup"}]
                markers.extend({"event": "visit_selection", "visit": visit,
                    "songFolder": case.folder, "chart": case.chart,
                    "difficulty": case.difficulty} for visit, case in
                    ((1, first), (2, second)))
                markers.extend({"event": event, "visit": visit} for event, visit in (
                    ("playstate_start", 1), ("playstate_ready", 1),
                    ("playstate_destroyed", 1), ("playstate_start", 2),
                    ("playstate_ready", 2)))
                markers.append({"event": "success"})
                return "\n".join("RUNTIME_SMOKE|" + json.dumps(marker)
                    for marker in markers), None

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source = Path(folder) / "source"
            for case, owner in ((first, "first-owner"), (second, "second-owner")):
                data = source / "assets" / "data" / case.folder
                data.mkdir(parents=True)
                (data / "compatScripts.json").write_text(json.dumps({
                    "roots": [{"path": f"assets/imported_mods/{owner}"}]}))
                script = source / "assets" / "imported_mods" / owner / "scripts" / "test.lua"
                script.parent.mkdir(parents=True)
                script.write_text("function onCreate() end")
            binary = source / "Funkin"
            binary.write_bytes(b"placeholder")
            with patch.object(self.matrix, "LOG_ROOT", Path(folder) / "logs"), patch.object(
                self.matrix, "offscreen_command", side_effect=lambda command: command
            ), patch.object(self.matrix.subprocess, "Popen", side_effect=FakeProcess):
                result = self.matrix.run_case(binary, first, duration_ms=3000,
                                              runtime_root=source, next_case=second)
        self.assertEqual(result["status"], "passed", result)
        command, copied = observations[0]
        self.assertEqual(copied, [True, True])
        self.assertEqual(command[command.index("--smoke-next-song") + 1], "second")
        self.assertEqual(command[command.index("--smoke-next-chart") + 1], "second-hard")

    def test_changed_disposable_options_fail_without_touching_source(self):
        case = self.matrix.SMOKE_MATRIX[0]
        overlays = []

        class MutatingProcess:
            returncode = 0

            def __init__(self, command, **kwargs):
                cwd = Path(kwargs["cwd"])
                overlays.append(cwd)
                (cwd / "assets" / "data" / "options.json").write_bytes(b'{"offset":999}')

            def communicate(self, timeout=None):
                return "\n".join(
                    "RUNTIME_SMOKE|" + json.dumps({"event": event})
                    for event in ("startup", "playstate_start", "playstate_ready", "success")
                ), None

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source = Path(folder) / "source"
            (source / "assets" / "data").mkdir(parents=True)
            options = source / "assets" / "data" / "options.json"
            options.write_bytes(b'{"offset":251}')
            binary = source / "Funkin"
            binary.write_bytes(b"placeholder")
            with patch.object(self.matrix, "LOG_ROOT", Path(folder) / "logs"), patch.object(
                self.matrix, "offscreen_command", side_effect=lambda command: command
            ), patch.object(self.matrix.subprocess, "Popen", side_effect=MutatingProcess):
                result = self.matrix.run_case(binary, case, duration_ms=3000)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["options_changed"])
            self.assertEqual(options.read_bytes(), b'{"offset":251}')
            self.assertFalse(overlays[0].exists())

    def test_native_runtime_root_keeps_binary_library_directory(self):
        runner = MATRIX_PATH.read_text()
        self.assertIn('environment["LD_LIBRARY_PATH"]', runner)
        self.assertIn("native_library_root = str(binary.parent)", runner)
        self.assertIn('if not wine and os.name != "nt"', runner)

    def test_private_display_environment_discards_desktop_sessions(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            overlay = Path(folder)
            with patch.dict(os.environ, {
                "DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0",
                "WAYLAND_SOCKET": "9", "XAUTHORITY": "/personal/auth",
                "XDG_RUNTIME_DIR": "/personal/runtime",
            }):
                env = self.matrix._case_environment(Path("/build/Funkin"), overlay, False)
            for key in ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "XAUTHORITY", "XDG_RUNTIME_DIR"):
                self.assertNotIn(key, env)
            self.assertEqual(env["SDL_VIDEODRIVER"], "x11")
            self.assertEqual(env["XDG_DATA_HOME"], str(overlay / "xdg-data"))

    def test_native_import_preparation_uses_full_import_workflow(self):
        self.assertIn("RuntimeImportSmokeHarness.enabled()", self.main)
        self.assertIn("initialState = RuntimeImportSmokeState", self.main)
        self.assertIn("--smoke-import-source", self.import_harness)
        self.assertIn("--smoke-import-type", self.import_harness)
        self.assertIn("--smoke-import-package-name", self.import_harness)
        self.assertIn("ImportWorkflow.beginScan", self.import_state)
        self.assertIn("ImportWorkflow.beginImport", self.import_state)
        self.assertIn("ImportPackageNamePrompt.createOverrides", self.import_state)
        self.assertIn("scanJob.snapshot()", self.import_state)
        self.assertIn("importJob.snapshot()", self.import_state)
        self.assertIn("RUNTIME_IMPORT_SMOKE|", self.import_harness)
        self.assertIn("Sys.exit(0)", self.import_harness)
        self.assertIn("Sys.exit(1)", self.import_harness)
        self.assertIn("FlxG.autoPause = false", self.import_state)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_import_smoke_keeps_bounded_error_details(self):
        method = extract_haxe_method(self.import_harness,
                                     "static function boundedErrors(value:Dynamic):Array<String>")
        fixture = "class Main {\n" + method + "\nstatic function main():Void {\n" + '''
  if (boundedErrors(null).length != 0) throw "null errors";
  var errors:Array<String> = [for (i in 0...23) StringTools.lpad(Std.string(i), "x", 700)];
  var details = boundedErrors(errors);
  if (details.length != 20 || details[0].length != 500
    || details[19].length != 500) throw "bounded error marker";
''' + "}\n}\n"
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "--interp", "-main", "Main"],
                cwd=folder, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_import_harness_compiles_as_a_native_interpreter_fixture(self):
        fixture = """class Main {
  static function main() {
    if (RuntimeImportSmokeHarness.config() != null)
      throw 'unexpected smoke arguments';
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture_path = Path(folder) / "Main.hx"
            fixture_path.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [str(HAXE), "-cp", str(SOURCE), "-cp", str(folder), "--interp", "-main", "Main"],
                cwd=folder,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_import_state_compiles_against_workflow_job_contract(self):
        files = {
            "flixel/FlxG.hx": """package flixel;
class FlxG { public static var autoPause:Bool = true; }
""",
            "flixel/FlxState.hx": """package flixel;
class FlxState {
  public function new() {}
  public function create():Void {}
  public function update(elapsed:Float):Void {}
}
""",
            "ImportWorkflow.hx": """typedef ImportProgress = {
  var complete:Bool; var result:Dynamic; var error:String;
}
class ImportScanJob {
  public function new() {}
  public function snapshot():ImportProgress return {complete:true,result:{},error:null};
  public function isFinished():Bool return true;
  public function cancel():Void {}
}
class ImportImportJob {
  public function new() {}
  public function snapshot():ImportProgress return {complete:true,result:{},error:null};
  public function isFinished():Bool return true;
  public function cancel():Void {}
}
class ImportWorkflow {
  public static function beginScan(source:String, type:String):ImportScanJob return new ImportScanJob();
  public static function beginImport(source:String, scan:Dynamic, type:String, ?names:Map<String,String>):ImportImportJob return new ImportImportJob();
  public static function beginSongScan(source:String, type:String):ImportScanJob return new ImportScanJob();
  public static function beginSongImport(source:String, scan:Dynamic, type:String):ImportImportJob return new ImportImportJob();
}
""",
            "PluginManager.hx": "class PluginManager { public static function init():Void {} }\n",
            "DifficultyManager.hx": "class DifficultyManager { public static function init():Void {} }\n",
            "ModifierState.hx": "class ModifierState { public static function init():Void {} }\n",
            "PlayerSettings.hx": "class PlayerSettings { public static function init():Void {} }\n",
            "ImportPackageNamePrompt.hx": """class ImportPackageNamePrompt {
  public static function collectUnnamedRoots(songs:Array<Dynamic>):Array<Dynamic> return [];
  public static function validName(name:String):Bool return true;
  public static function createOverrides(requests:Array<Dynamic>, names:Array<String>):Map<String,String> return new Map<String,String>();
}
""",
            "CompileMain.hx": "class CompileMain { static function main() { var cls:Class<Dynamic> = RuntimeImportSmokeState; trace(cls); } }\n",
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            for relative, contents in files.items():
                path = Path(folder) / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents, encoding="utf-8")
            result = subprocess.run(
                [str(HAXE), "-cp", str(SOURCE), "-cp", str(folder), "--interp", "-main", "CompileMain"],
                cwd=folder,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
