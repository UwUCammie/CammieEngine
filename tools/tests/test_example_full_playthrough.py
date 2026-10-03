"""Guard the full-song gate against stale ownership and missing media."""

import hashlib
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from run_example_full_playthrough import (direct_private_case, input_delivered, preflight,
                                         psych_loaded_chart_mismatches,
                                         process_timeout_for_ready_window, run_row, script_errors,
                                         validate_direct_private_runtime)
from run_runtime_smoke_matrix import SmokeCase
from run_runtime_smoke_matrix import unexplained_error_lines


class ExampleFullPlaythroughTest(unittest.TestCase):
    def test_process_watchdog_covers_native_startup_and_ready_gameplay(self):
        for gameplay_window in (45.0, 75.0, 240.0):
            timeout = process_timeout_for_ready_window(gameplay_window)
            native_startup_watchdog = gameplay_window + 120.0
            self.assertGreaterEqual(timeout - native_startup_watchdog,
                                    gameplay_window + 35.0)

    def test_direct_mode_requires_a_physical_private_runtime(self):
        with self.assertRaisesRegex(ValueError, "below repository tmp"):
            validate_direct_private_runtime(ROOT / "export/release/linux/bin",
                                            ROOT / "export/release/linux/bin/Funkin")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            runtime = Path(scratch)
            binary = runtime / "Funkin"
            binary.write_bytes(b"fixture")
            options = runtime / "assets/data/options.json"
            options.parent.mkdir(parents=True)
            options.write_text("{}", newline='\n')
            validate_direct_private_runtime(runtime, binary)
            (runtime / "outside").symlink_to(ROOT / "export/release/linux/bin", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "links outside"):
                validate_direct_private_runtime(runtime, binary)

    def test_direct_mode_resets_only_private_options_and_saves(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            runtime = Path(scratch)
            options = runtime / "assets/data/options.json"
            options.parent.mkdir(parents=True)
            options.write_text('{"personal":true}', newline='\n')
            private_save = runtime / "xdg-data"
            private_save.mkdir()
            (private_save / "old-save").write_text("fixture", newline='\n')
            case = SmokeCase("private-case", "fixture", "song", "song", "normal")
            with patch('run_example_full_playthrough._run_case_in_overlay',
                       return_value={"status": "passed"}) as launch:
                self.assertEqual(direct_private_case(runtime / "Funkin", case, 1000,
                                                     10, runtime, None, None, (),
                                                     input_trigger="song_end")["status"], "passed")
            self.assertEqual(options.read_bytes(), (ROOT / "assets/data/options.json").read_bytes())
            self.assertFalse((private_save / "old-save").exists())
            self.assertTrue((runtime / "scratch").is_dir())
            self.assertTrue((runtime / "xdg-cache").is_dir())
            self.assertEqual(launch.call_args.args[3:5], (runtime, runtime))
            self.assertEqual(launch.call_args.kwargs["input_trigger"], "song_end")

    def test_script_gate_counts_null_arithmetic_and_missing_owner_icon(self):
        output = ('[hscript-null-operand] "+" used a null operand\n'
                  '[hscript-null-iterator] for-in used a null value\n'
                  'source/HxcWindowCompat.hx:33: [hxc-window] missing icon: assets/dokicon.png\n')
        self.assertEqual(len(script_errors(output)), 3)

    def test_generic_error_gate_ignores_hyphenated_video_adapter_prose(self):
        informational = ('[hxc-hxc-video-module-adapter] playback-error behavior is delegated '
                         'to hxvlc for the host boundary\n')
        actual = ('[hxc-playback-error] playback-error behavior failed: decoder error\n'
                  'Error : Null Object Reference\n')
        self.assertEqual(unexplained_error_lines(informational), [])
        self.assertEqual(unexplained_error_lines(actual), actual.splitlines())
        self.assertEqual(unexplained_error_lines(actual, [actual.splitlines()[0]]),
                         [actual.splitlines()[1]])

    def test_nightmare_vision_unsupported_scripts_cannot_pass_the_script_gate(self):
        warning = '[nightmare-vision-unsupported-script] scope=stage path=data/stages/demo/script.hx'
        self.assertEqual(script_errors(warning, 'Nightmare Vision'), [warning])

    def test_codename_source_character_fallback_is_engine_specific(self):
        fallback = ('[codename-character-source-fallback] Codename source fallback for missing '
                    '"bf-dark" uses DEFAULT_CHARACTER "bf" mapped to native "bf"\n')
        other = '[codename-script-error] another Codename issue\n'
        self.assertEqual(script_errors(fallback), [fallback.strip()])
        self.assertEqual(script_errors(fallback, "Psych Engine"), [fallback.strip()])
        self.assertEqual(script_errors(fallback, "Codename Engine"), [])
        self.assertEqual(script_errors(fallback + other, "Codename Engine"), [other.strip()])
        unavailable = ('[codename-character-fallback-unavailable] missing "bf-dark" has no '
                       'safe DEFAULT_CHARACTER definition\n')
        self.assertEqual(script_errors(unavailable, "Codename Engine"), [unavailable.strip()])

    def test_dialogue_driver_needs_no_key_when_song_starts_first(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            local = Path(scratch)
            process = local / 'tmp/runtime-smoke/logs/0-plain-plain.process.log'
            process.parent.mkdir(parents=True)
            process.write_text('RUNTIME_SMOKE|{"event":"song_start"}\n'
                               'RUNTIME_SMOKE|{"event":"song_end","dispatchedEvents":0,"dueEvents":0,"totalEvents":0}\n', newline='\n')
            song_chart = local / 'assets/data/plain/plain.json'
            song_chart.parent.mkdir(parents=True)
            song_chart.write_text('{"song":{"song":"plain"}}', newline='\n')
            (local / 'Funkin').write_bytes(b'current native binary')
            with patch('run_example_full_playthrough.ROOT', local), \
                 patch('run_example_full_playthrough.preflight', return_value=(song_chart, 8.0, None)), \
                 patch('run_example_full_playthrough.run_case',
                       return_value={'status': 'passed'}) as launch:
                result = run_row({'group': 'Psych Engine', 'package': 'fixture',
                                  'song': 'plain', 'difficulty': 'normal',
                                  'runtimeChartSha256': 'stale inventory hash',
                                  'runtimeOwner': 'assets/imported_mods/fixture'}, 0,
                                 local, local / 'Funkin', 5.0, repeat_key='Return')
            self.assertEqual(result['status'], 'passed')
            self.assertIs(result['dialogueInputDelivered'], False)
            self.assertEqual(launch.call_args.kwargs['timeout_seconds'], 305.0)
            evidence = result['provenance']
            self.assertEqual(evidence['binarySha256'],
                             hashlib.sha256(b'current native binary').hexdigest())
            self.assertEqual(evidence['runtimeChartSha256'],
                             hashlib.sha256(song_chart.read_bytes()).hexdigest())
            self.assertEqual(evidence['runtimeOwner'], 'assets/imported_mods/fixture')
            self.assertEqual(evidence['testMode'], 'accelerated-completion')
            self.assertEqual(evidence['playbackRate'], 5.0)
            self.assertIs(evidence['allDependenciesFingerprinted'], False)
            self.assertIsNone(evidence['compatManifestSha256'])

    def test_psych_gate_checks_loaded_difficulty_before_intro_swaps(self):
        chart = {"player1": "bf-santa", "player2": "testis", "gf": "gf_JUICY"}
        markers = [
            {"event": "playstate_start", "chartPlayer1": "bf", "chartPlayer2": "testis",
             "chartGf": "gf_JUICY"},
            {"event": "character_visual", "role": "player", "requestedCharacter": "bf-santa"},
        ]
        self.assertEqual(psych_loaded_chart_mismatches(chart, markers),
                         ["loaded player1 differs from selected chart: expected 'bf-santa', got 'bf'"])
        markers[0]["chartPlayer1"] = "bf-santa"
        markers[1]["requestedCharacter"] = "bf"
        self.assertEqual(psych_loaded_chart_mismatches(chart, markers), [])
        self.assertIn("chartPlayer1: song == null ? null : Reflect.field(song, 'player1')",
                      (ROOT / "source/RuntimeSmokeHarness.hx").read_text())

    def test_private_intro_input_requires_a_matching_delivery_marker(self):
        self.assertFalse(input_delivered('', 'e'))
        self.assertFalse(input_delivered('OFFSCREEN_INPUT|bad-json\n', 'e'))
        self.assertFalse(input_delivered('OFFSCREEN_INPUT|{"key":"e","delivered":false}\n', 'e'))
        self.assertFalse(input_delivered('OFFSCREEN_INPUT|{"key":"Return","delivered":true}\n', 'e'))
        self.assertTrue(input_delivered('OFFSCREEN_INPUT|{"key":"e","delivered":true}\n', 'e'))
        self.assertFalse(input_delivered(
            'OFFSCREEN_INPUT|{"key":"Return","trigger":"playstate_ready","delivered":true}\n',
            'Return', trigger='song_end'))
        self.assertTrue(input_delivered(
            'OFFSCREEN_INPUT|{"key":"Return","trigger":"song_end","delivered":true}\n',
            'Return', trigger='song_end'))

    def test_dismiss_ending_waits_for_song_end_and_records_native_handoff(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            local = Path(scratch)
            process = local / 'tmp/runtime-smoke/logs/0-plain-plain.process.log'
            process.parent.mkdir(parents=True)
            handoff = {"event": "end_handoff", "state": "VictoryLoopState"}
            process.write_text(
                'RUNTIME_SMOKE|{"event":"song_end","dispatchedEvents":0,'
                '"dueEvents":0,"totalEvents":0}\n'
                + 'RUNTIME_SMOKE|' + json.dumps(handoff) + '\n'
                + 'OFFSCREEN_INPUT|' + json.dumps({"key": "Return", "trigger": "song_end",
                                                   "delivered": True}) + '\n', newline='\n')
            song_chart = local / 'assets/data/plain/plain.json'
            song_chart.parent.mkdir(parents=True)
            song_chart.write_text('{"song":{"song":"plain"}}', newline='\n')
            with patch('run_example_full_playthrough.ROOT', local), \
                 patch('run_example_full_playthrough.preflight', return_value=(song_chart, 8.0, None)), \
                 patch('run_example_full_playthrough.run_case',
                       return_value={'status': 'passed'}) as launch:
                result = run_row({'group': 'fixture', 'package': 'fixture',
                                  'song': 'plain', 'difficulty': 'normal'}, 0,
                                 local, local / 'Funkin', 50.0, dismiss_ending=True)

            self.assertEqual(result['status'], 'passed')
            self.assertEqual(result['endHandoff'], handoff)
            self.assertTrue(result['endingInputDelivered'])
            self.assertEqual(launch.call_args.kwargs['input_key'], 'Return')
            self.assertEqual(launch.call_args.kwargs['input_trigger'], 'song_end')
            self.assertIn('--smoke-require-end-handoff', launch.call_args.kwargs['extra_flags'])
            self.assertIn('--smoke-require-song-end', launch.call_args.kwargs['extra_flags'])

    def test_dismiss_ending_fails_without_one_handoff_and_song_end_trigger(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            local = Path(scratch)
            process = local / 'tmp/runtime-smoke/logs/0-plain-plain.process.log'
            process.parent.mkdir(parents=True)
            process.write_text(
                'RUNTIME_SMOKE|{"event":"song_end","dispatchedEvents":0,'
                '"dueEvents":0,"totalEvents":0}\n'
                'RUNTIME_SMOKE|{"event":"end_handoff","state":"VictoryLoopState"}\n'
                'RUNTIME_SMOKE|{"event":"end_handoff","state":"TitleState"}\n'
                'OFFSCREEN_INPUT|{"key":"Return","trigger":"playstate_ready",'
                '"delivered":true}\n', newline='\n')
            song_chart = local / 'assets/data/plain/plain.json'
            song_chart.parent.mkdir(parents=True)
            song_chart.write_text('{"song":{"song":"plain"}}', newline='\n')
            with patch('run_example_full_playthrough.ROOT', local), \
                 patch('run_example_full_playthrough.preflight', return_value=(song_chart, 8.0, None)), \
                 patch('run_example_full_playthrough.run_case',
                       return_value={'status': 'passed'}):
                result = run_row({'group': 'fixture', 'package': 'fixture',
                                  'song': 'plain', 'difficulty': 'normal'}, 0,
                                 local, local / 'Funkin', 50.0, dismiss_ending=True)

            self.assertEqual(result['status'], 'failed')
            self.assertIn('expected one end_handoff marker', result['reason'])
            self.assertIn('ending Return was not delivered after native song_end', result['reason'])
            self.assertIsNone(result['endHandoff'])

    def test_dialogue_and_ending_use_separate_input_triggers(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            local = Path(scratch)
            process = local / 'tmp/runtime-smoke/logs/0-plain-plain.process.log'
            process.parent.mkdir(parents=True)
            process.write_text(
                'RUNTIME_SMOKE|{"event":"song_start"}\n'
                'RUNTIME_SMOKE|{"event":"song_end","dispatchedEvents":0,"dueEvents":0}\n'
                'RUNTIME_SMOKE|{"event":"end_handoff","state":"FreeplayState"}\n'
                'OFFSCREEN_INPUT|{"key":"Return","trigger":"repeat until song_start","delivered":true}\n'
                'OFFSCREEN_INPUT|{"key":"Return","trigger":"song_end","delivered":true}\n', newline='\n')
            song_chart = local / 'assets/data/plain/plain.json'
            song_chart.parent.mkdir(parents=True)
            song_chart.write_text('{"song":{"song":"plain"}}', newline='\n')
            with patch('run_example_full_playthrough.ROOT', local), \
                 patch('run_example_full_playthrough.preflight', return_value=(song_chart, 8.0, None)), \
                 patch('run_example_full_playthrough.run_case',
                       return_value={'status': 'passed'}) as launch:
                result = run_row({'group': 'fixture', 'package': 'fixture',
                                  'song': 'plain', 'difficulty': 'normal'}, 0,
                                 local, local / 'Funkin', 50.0, repeat_key='Return',
                                 dismiss_ending=True)
            self.assertEqual(result['status'], 'passed')
            self.assertTrue(result['dialogueInputDelivered'])
            self.assertTrue(result['endingInputDelivered'])
            self.assertIsNone(launch.call_args.kwargs['input_key'])
            self.assertEqual(launch.call_args.kwargs['repeat_key'], 'Return')
            self.assertEqual(launch.call_args.kwargs['input_trigger'], 'playstate_ready')
            self.assertEqual(launch.call_args.kwargs['post_key'], 'Return')

    def test_preflight_uses_selected_storage_folder_for_colliding_song_audio(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            root = Path(scratch)
            data = root / "assets/data/example--owner"
            audio = root / "assets/songs/example--owner"
            data.mkdir(parents=True)
            audio.mkdir(parents=True)
            (data / "example--owner-hard.json").write_text(json.dumps({
                "song": {"song": "example", "notes": [{"sectionNotes": [[100, 0, 0]]}]}
            }) + "\x00" * 8, newline='\n')
            (data / "compatScripts.json").write_text(json.dumps({
                "selectedRoot": "assets/imported_mods/owner"}), newline='\n')
            (audio / "example_Inst.ogg").write_bytes(b"fixture")
            row = {
                "runtimeChartPresent": True, "ownerMatched": True,
                "sourceVariantImported": True, "sourceNoteCountMatched": True,
                "runtimeChart": "assets/data/example--owner/example--owner-hard.json",
                "runtimeOwner": "assets/imported_mods/owner", "sourceNoteCount": 1,
            }
            with patch("run_example_full_playthrough._audio_duration", return_value=90.0):
                chart, seconds, error = preflight(row, root)
            self.assertIsNone(error)
            self.assertEqual(chart, data / "example--owner-hard.json")
            self.assertEqual(seconds, 90.0)

    def test_preflight_requires_current_selected_owner_and_real_audio(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            root = Path(scratch)
            data = root / "assets/data/example"
            audio = root / "assets/songs/example"
            data.mkdir(parents=True)
            audio.mkdir(parents=True)
            (data / "example-hard.json").write_text(json.dumps({
                "song": {"song": "example", "notes": [{"sectionNotes": [[100, 0, 0]]}]}
            }), newline='\n')
            (data / "compatScripts.json").write_text(json.dumps({"selectedRoot": "assets/imported_mods/other"}), newline='\n')
            row = {
                "runtimeChartPresent": True, "ownerMatched": True,
                "sourceVariantImported": True, "sourceNoteCountMatched": True,
                "runtimeChart": "assets/data/example/example-hard.json",
                "runtimeOwner": "assets/imported_mods/expected",
                "sourceNoteCount": 1,
            }
            _, _, error = preflight(row, root)
            self.assertIn("selected owner changed", error)
            (data / "compatScripts.json").write_text(json.dumps({"selectedRoot": row["runtimeOwner"]}), newline='\n')
            _, _, error = preflight(row, root)
            self.assertIn("instrumental missing", error)
            row["sourceNoteCount"] = 2
            _, _, error = preflight(row, root)
            self.assertIn("runtime note count changed", error)
            row["sourceNoteCount"] = 1
            (audio / "Inst.ogg").write_bytes(b"fixture")
            with patch("run_example_full_playthrough._audio_duration", return_value=120.0):
                chart, seconds, error = preflight(row, root)
            self.assertIsNone(error)
            self.assertEqual(chart, data / "example-hard.json")
            self.assertEqual(seconds, 120.0)

    def test_preflight_rejects_stale_inventory_before_game_launch(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            row = {"runtimeChartPresent": True, "ownerMatched": True,
                   "sourceVariantImported": True, "sourceNoteCountMatched": False,
                   "runtimeChart": "assets/data/example/example.json"}
            _, _, error = preflight(row, Path(scratch))
            self.assertEqual(error, "inventory does not establish sourceNoteCountMatched")

    def test_vslice_preflight_uses_source_gameplay_rows_and_preserves_raw_inventory(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            root = Path(scratch)
            data = root / "assets/data/example"
            audio = root / "assets/songs/example"
            data.mkdir(parents=True)
            audio.mkdir(parents=True)
            (data / "example.json").write_text(json.dumps({"song": {
                "song": "example", "notes": [{"sectionNotes": [[100, lane, 0]
                                                for lane in range(8)]}]}}), newline='\n')
            (data / "compatScripts.json").write_text(json.dumps({
                "selectedRoot": "assets/imported_mods/owner"}), newline='\n')
            (audio / "Inst.ogg").write_bytes(b"fixture")
            row = {"group": "V-Slice", "runtimeChartPresent": True,
                   "ownerMatched": True, "sourceVariantImported": True,
                   "sourceNoteCount": 16, "sourceNoteCountMatched": False,
                   "sourceGameplayNoteCount": 8,
                   "sourceGameplayNoteCountMatched": True,
                   "runtimeChart": "assets/data/example/example.json",
                   "runtimeOwner": "assets/imported_mods/owner"}
            with patch("run_example_full_playthrough._audio_duration", return_value=42.0):
                chart, seconds, error = preflight(row, root)
            self.assertIsNone(error)
            self.assertEqual(chart, data / "example.json")
            self.assertEqual(seconds, 42.0)
            row["sourceGameplayNoteCountMatched"] = False
            _, _, error = preflight(row, root)
            self.assertEqual(error, "inventory does not establish sourceGameplayNoteCountMatched")

    def test_interpreter_error_fails_a_natural_ending_gate(self):
        output = ('RUNTIME_SMOKE|{"event":"song_end","message":"hscript error in metadata"}\n'
                  'source/PlayState.hx:1301: hscript error in stage.start: EUnknownVariable(front)\n')
        self.assertEqual(script_errors(output),
                         ['source/PlayState.hx:1301: hscript error in stage.start: EUnknownVariable(front)'])
        self.assertEqual(script_errors(
            '[codename-script-unsupported-import] data/events/Change Character.hx:3: '
            'No explicit binding for import funkin.game.Character\n'
            '[codename-script-error] data/stages/phillyTruck.hx.create: Invalid field:uRainColor\n'
        ), [
            '[codename-script-unsupported-import] data/events/Change Character.hx:3: '
            'No explicit binding for import funkin.game.Character',
            '[codename-script-error] data/stages/phillyTruck.hx.create: Invalid field:uRainColor',
        ])
        self.assertEqual(script_errors(
            '[character-resolution] character-registry-entry-missing|0|Character "0" missing\n'
            '[codename-actor-runtime] unsupported-placement:0:0\n'), [
            '[character-resolution] character-registry-entry-missing|0|Character "0" missing',
            '[codename-actor-runtime] unsupported-placement:0:0',
        ])
        self.assertEqual(script_errors(
            '[hxc-unsupported-hxc-callback-body] onPause donor body was not adapted\n'),
            ['[hxc-unsupported-hxc-callback-body] onPause donor body was not adapted'])
        self.assertEqual(script_errors(
            'source/Character.hx:828: [codename-character-construction] nerd: '
            '[codename-asset] Missing scoped asset: owner/images/Nerd.png\n'),
            ['source/Character.hx:828: [codename-character-construction] nerd: '
             '[codename-asset] Missing scoped asset: owner/images/Nerd.png'])
        self.assertEqual(script_errors(
            'source/PlayState.hx:8272: [psych-stage-json-only] Applied owner stage metadata\n'
            'source/PlayState.hx:8316: unavailable imported class dependency backend.WeekData\n'
            '[engine-compat] [unsupported-engine-dependency] compiled stage did not run\n'), [
            'source/PlayState.hx:8272: [psych-stage-json-only] Applied owner stage metadata',
            'source/PlayState.hx:8316: unavailable imported class dependency backend.WeekData',
            '[engine-compat] [unsupported-engine-dependency] compiled stage did not run',
        ])
        self.assertEqual(script_errors(
            'source/PlayState.hx:8346: [psych-stage-runtime] executing owner class\n'
            'source/PlayState.hx:8328: [psych-stage] callback createPost failed: Invalid field:blockHit\n'), [
            'source/PlayState.hx:8328: [psych-stage] callback createPost failed: Invalid field:blockHit',
        ])
        self.assertEqual(script_errors(
            '[psych-stage-video] could not play selected-owner video assets/imported_mods/m/videos/end.mp4\n'
            '[hxc-video-missing] assets/imported_mods/m/videos/end.mp4\n'), [
            '[psych-stage-video] could not play selected-owner video assets/imported_mods/m/videos/end.mp4',
            '[hxc-video-missing] assets/imported_mods/m/videos/end.mp4',
        ])
        self.assertEqual(script_errors('Null Function Pointer\n'), ['Null Function Pointer'])


if __name__ == "__main__":
    unittest.main()
