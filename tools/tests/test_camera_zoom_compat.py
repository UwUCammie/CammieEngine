from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"
TMP.mkdir(exist_ok=True)


class CameraZoomCompatibilityTest(unittest.TestCase):
    def test_camera_smoke_telemetry_is_opt_in_and_covers_resonance_audit_points(self):
        harness = (ROOT / "source/RuntimeSmokeHarness.hx").read_text()
        camera_probe = harness[
            harness.index("\tpublic static function markCameraSnapshot(") : harness.index(
                "\n\t/** Queue only primitive note data", harness.index("\tpublic static function markCameraSnapshot(")
            )
        ]
        self.assertIn("if (!enabled() || finished)", camera_probe)
        self.assertIn("emit('camera_snapshot', payload);", camera_probe)

        source = (ROOT / "source/PlayState.hx").read_text()
        snapshot_start = source.index("\tfunction runtimeSmokeCameraSnapshot(")
        snapshot_end = source.index("\n\tfunction psychStagePoint(", snapshot_start)
        snapshot = source[snapshot_start:snapshot_end]
        for field in (
            "chartEventTimestampMs", "eventTargetZoom", "eventDurationSeconds",
            "cameraZoom", "activeCameraZoom", "defaultCamZoom", "stageDefaultZoom",
            "followTargetX", "followTargetY", "cameraScrollX", "cameraScrollY",
            "cameraCount", "psychCameraCompatibilityActive", "mustHitSection",
            "boyfriendMidX", "boyfriendMidY", "boyfriendPsychInitialFollowCamX",
            "boyfriendPsychCameraContribution", "opponentPsychCameraContribution",
            "girlfriendPsychCameraContribution",
        ):
            self.assertIn(field + ":", snapshot)
        self.assertIn("if (!RuntimeSmokeHarness.enabled() || camGame == null)", snapshot)
        self.assertIn("runtimeSmokeCameraSnapshot('playstate-ready');", source)
        self.assertIn("runtimeSmokeCameraSnapshot('first-bf-focus');", source)
        self.assertIn("runtimeSmokeCameraSnapshot('first-authored-zoom-start'", source)
        self.assertIn("runtimeSmokeCameraSnapshot('first-authored-zoom-complete'", source)
        self.assertIn("var captureFirstZoomCompletion = smokeFirstZoomEventCaptured", source)

    def test_psych_initial_stage_focus_and_flash_preference_helpers(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("Song.currentPsychCharacterRoot();", source)
        self.assertIn("psychCameraRoot != null && StringTools.trim(psychCameraRoot) != ''", source)
        helper_start = source.index("\tpublic static function cameraNoteOffset(")
        helper_end = source.index("\n\tpublic var disableScoreChange", helper_start)
        helpers = source[helper_start:helper_end]
        fixture = """class PsychStageCameraCompatibilityTest {
""" + helpers + """
	static function expectTarget(actual:Array<Float>, expected:Array<Float>, label:String):Void {
		if (actual == null || actual.length != 2 || actual[0] != expected[0] || actual[1] != expected[1])
			throw label + ': ' + actual;
	}
	static function main() {
		var bf = [10.0, 20.0];
		var dad = [30.0, 40.0];
		var gf = [50.0, 60.0];
		expectTarget(psychInitialCameraTarget(true, false, false, bf, dad, gf), bf,
			'player section should initially target BF');
		expectTarget(psychInitialCameraTarget(false, true, false, bf, dad, gf), gf,
			'GF section should initially target GF');
		expectTarget(psychInitialCameraTarget(false, false, true, bf, dad, gf), gf,
			'GF singing should initially target GF');
		expectTarget(psychInitialCameraTarget(false, false, false, bf, dad, gf), dad,
			'opponent section should initially target dad');
		expectTarget(psychInitialCameraTarget(false, true, false, bf, dad, null), dad,
			'missing GF should retain opponent fallback');
		if (!psychFlashCallbackSuppressed(false, true, ' Flash '))
			throw 'disabled preference should suppress the Flash visual callback';
		if (psychFlashCallbackSuppressed(true, true, 'Flash')
			|| psychFlashCallbackSuppressed(false, false, 'Flash')
			|| psychFlashCallbackSuppressed(false, true, 'Camera Flash'))
			throw 'flash preference gate suppressed a callback outside its scope';
	}
}
"""
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            path = Path(folder) / "PsychStageCameraCompatibilityTest.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-main", "PsychStageCameraCompatibilityTest", "--interp"],
                capture_output=True, text=True, cwd=ROOT, timeout=300,
                env={**os.environ, "TMPDIR": str(TMP)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        apply = source[source.index("\tfunction applyPsychStageJson("):source.index("\n\tfunction loadPsychStageCompat(")]
        self.assertLess(apply.index("boyfriend.setPosition"), apply.index("refreshPsychStageCameraTarget();"))
        self.assertLess(apply.index("applyPsychStageCameraOffsets(data);"), apply.index("refreshPsychStageCameraTarget();"))
        self.assertIn("psychStageCameraOpponent = psychStagePoint(data, 'camera_opponent');", source)
        refresh = source[source.index("\tfunction refreshPsychStageCameraTarget("):source.index("\n\tfunction applyPsychStageJson(")]
        self.assertIn("camFollow.setPosition(target[0], target[1]);", refresh)
        self.assertIn("camGame.focusOn(camFollow.getPosition());", refresh)
        self.assertNotIn("defaultCamZoom", refresh)
        self.assertNotIn("setGameCameraZoom", refresh)
        self.assertIn("defaultCamZoom = parsedZoom;", apply)
        self.assertIn("setGameCameraZoom(parsedZoom);", apply)

        follow_start = source.index("\t\tif (generatedMusic && PlayState.SONG.notes[curSection] != null) {")
        follow_end = source.index("\n\t\t\t\t// playerOneTurn/playerTwoTurn mark", follow_start)
        camera_follow = source[follow_start:follow_end]
        self.assertIn("camFollow.setPosition", camera_follow)
        self.assertNotIn("setGameCameraZoom", camera_follow)
        self.assertNotIn("defaultCamZoom =", camera_follow)

        self.assertIn("psychFlashEventScopes.set(scriptScope, true);", source)
        self.assertIn("psychFlashEventScopes.exists(usehaxe)", source)
        self.assertIn("psychFlashEventScopes.clear();", source)

    def test_gameplay_and_hud_decay_use_elapsed_time(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("if (camZooming && !inCutscene)")
        update = source[start:source.index("holdCameraZoomTargets();", start)]
        self.assertEqual(update.count("cameraZoomDecayRetention(elapsed, camZoomDecay)"), 2)
        self.assertNotIn("Math.pow(0.95, camZoomDecay)", update)

    def test_legacy_zoom_multiplier_and_visible_note_offset(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        helper_start = source.index("\tpublic static function cameraNoteOffset(")
        helper_end = source.index("\n\tpublic var disableScoreChange", helper_start)
        helpers = source[helper_start:helper_end]
        fixture = """class CameraZoomCompatibilityTest {
""" + helpers + """
	static function close(a:Float, b:Float):Bool {
		return Math.abs(a - b) < 0.000001;
	}
	static function main() {
		for (fps in [30, 60, 144, 480, 2400]) {
			var zoom = 1.0;
			for (_ in 0...fps * 5)
				zoom = 0.6 + (zoom - 0.6) * cameraZoomDecayRetention(1.0 / fps, 1);
			var expected = 0.6 + 0.4 * Math.pow(0.95, 300);
			if (!close(zoom, expected) || zoom < 0.6)
				throw "zoom return must converge to its target independently of FPS";
		}
		if (cameraZoomDecayRetention(0, 1) != 1 || cameraZoomDecayRetention(1, 0) != 1)
			throw "paused or disabled decay must preserve the current zoom";
		if (!close(legacyStageZoom(2.85, 0.9), 2.565))
			throw "Golden baseline zoom must remain relative to its stage";
		if (!close(legacyStageZoom(2.85, 1.4), 3.99))
			throw "Golden zoom-in multiplier";
		if (!close(legacyCameraZoomDefaultOnStart(0.15, 0.5, 1.5), 0.15))
			throw "a tweened legacy target must not replace the resting zoom before completion";
		if (!close(legacyCameraZoomDefaultOnStart(0.15, 0.5, 0), 0.5))
			throw "an immediate legacy target must become the resting zoom at once";
		if (!close(cameraZoomTarget(0.7, 1.5, 'stage'), 1.05))
			throw "stage-relative cutscene zoom must use the stage baseline";
		if (!close(cameraZoomTarget(0.7, 1.5, 'direct'), 1.5))
			throw "direct camera zoom semantics changed";
		if (!close(cameraZoomDuration(3, 240), 3))
			throw "cinematic zoom duration must stay in seconds";
		if (!close(cameraZoomDuration(null, 240), 0.24))
			throw "chart zoom duration must still convert milliseconds";
		if (!close(cameraNoteOffset(2.85) * 2.85, 25))
			throw "high zoom magnified directional movement";
		if (!close(cameraNoteOffset(0.7), 25))
			throw "low zoom chart movement changed";
		if (!cameraZoomEventIsAbsolute(0.5, 0.5))
			throw "paired legacy target values must be recognized";
		if (cameraZoomEventIsAbsolute(0.06, 0.03))
			throw "small Psych pulses must remain additive";
		if (!close(cameraZoomEventValue(0.9, 0.6, 0.6, true), 0.6))
			throw "legacy intro target must replace, not stack on, the current zoom";
		if (!close(cameraZoomEventValue(0.5, 0.015, 0.03, false), 0.515))
			throw "Psych camera pulse must remain additive";
		var targets = cameraZoomEventTargets(0.9, 1.03, 0.6, 0.6, true);
		if (!close(targets[0], 0.6) || !close(targets[1], 1.03))
			throw "absolute event must target gameplay without scaling the HUD";
		// Simulate the camera update/decay pass overwriting both components.
		// The sustained target must restore the world camera while leaving the
		// independently-owned HUD camera alone.
		if (!close(cameraZoomHoldValue(4, targets[0]), 0.6)
			|| !close(cameraZoomHoldValue(2, null), 2))
			throw "held intro target must survive without capturing the HUD";
		if (!close(cameraZoomHoldValue(0.515, null), 0.515))
			throw "ordinary additive pulses must not acquire a held target";
		var lockedGame = 0.5;
		var lockedHud = 1.0;
		for (target in [0.5, 0.6, 0.7, 0.8, 0.9]) {
			var locked = cameraZoomEventTargets(lockedGame, lockedHud, target, target, true);
			lockedGame = locked[0];
			lockedHud = locked[1];
		}
		if (!close(lockedGame, 0.9) || !close(lockedHud, 1.0))
			throw "Locked intro targets must not accumulate or scale the HUD";
		if (!cameraZoomIntroUsesTargets(0, 10971.428, 0.5, 0.5, 5, 0.5))
			throw "Locked-shaped intro should opt into target semantics";
		if (cameraZoomIntroUsesTargets(13333.333, 13333.333, 0.5, 0.5, 2, 0.9))
			throw "isolated in-song pulses must remain additive";
	}
}
"""
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            path = Path(folder) / "CameraZoomCompatibilityTest.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp",
                    folder,
                    "-main",
                    "CameraZoomCompatibilityTest",
                    "--interp",
                ],
                capture_output=True,
                text=True,
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(TMP)},
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\t\t\tcase 'Legacy Camera Zoom':")
        end = source.index("\n\t\t\tcase 'Set camzoom':", start)
        handler = source[start:end]
        self.assertIn("legacyCameraZoomDefaultOnStart(defaultCamZoom, legacyZoom, legacyDuration)", handler)
        self.assertIn("onComplete: function(_) {", handler)
        self.assertIn("defaultCamZoom = legacyZoom;", handler)
        self.assertIn("runtimeSmokeCameraSnapshot('first-authored-zoom-complete'", handler)

    def test_chaos_cutscene_keeps_donor_zoom_cues(self):
        fixture = ROOT / "assets/images/custom_cutscenes/fleetway.hscript"
        if not fixture.is_file():
            self.skipTest(f"mounted Chaos cutscene fixture unavailable: {fixture}")
        cutscene = fixture.read_text()
        self.assertIn(
            "ZoomCamera({zoom: 1, durationSeconds: 0.9, ease: 'linear', mode: 'direct'});",
            cutscene,
        )
        self.assertIn(
            "ZoomCamera({zoom: 0.7, durationSeconds: 0.4, ease: 'expoIn', mode: 'direct'});",
            cutscene,
        )
        self.assertIn("thechamber.animation.play('a', true);", cutscene)
        self.assertIn("emeraldbeamyellow.visible = true;", cutscene)
        self.assertIn("emeraldbeam.visible = false;", cutscene)
        self.assertIn("new FlxTimer().start(4.5", cutscene)
        self.assertNotIn("FlxTween.tween(FlxG.camera, {zoom: 1.5}", cutscene)

    def test_script_zoom_does_not_stack_with_engine_beat_bump(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        beat_hit = source[source.index("\toverride function beatHit()") :]
        self.assertIn("var scriptChangedZoom = cameraZoomChanged(", beat_hit)
        self.assertIn("!inCutscene && !endingSong && !scriptChangedZoom && camBoomSpeed > 0", beat_hit)
        self.assertIn("!scriptChangedZoom && !nativeCamBoomPulse", beat_hit)
        self.assertIn("&& camZooming && camGame.zoom < 1.35", beat_hit)
        self.assertEqual(beat_hit.count("setAllHaxeVar('curBeat', curBeat);"), 1)

    def test_event_and_custom_character_paths_keep_their_distinct_semantics(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        events = source[source.index("\tfunction fireSongEvent("):source.index("\n\tprivate function generateSong(")]
        self.assertIn("case 'Set camzoom':", events)
        self.assertIn("legacyStageZoom(curStage.defaultZoom, parseF(e.v1))", events)

        camera = source[source.index("\t\tif (camNotes) {"):source.index("\n\t\tif (endingSong)", source.index("\t\tif (camNotes) {"))]
        self.assertIn("final fallbackCamOffset = cameraNoteOffset(defaultCamZoom);", camera)
        self.assertIn("dadcam = [daCam[0], daCam[1]];", camera)
        self.assertIn("bfcam = [daCam[0], daCam[1]];", camera)
        self.assertNotIn("dadcam = [-25, 0]", camera)
        self.assertNotIn("bfcam = [-25, 0]", camera)

    def test_add_camera_zoom_distinguishes_intro_targets_from_pulses(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\t\t\tcase 'Add Camera Zoom':")
        end = source.index("\n\t\t\tcase 'Screen Shake':", start)
        handler = source[start:end]

        # Modding Plus documents this event as additive, while Locked's donor
        # chart has a distinct note-less target sequence.  The handler must
        # route both camera components through the compatibility resolver.
        self.assertIn("cameraZoomEventTargets(currentGameZoom, camHUD.zoom", handler)
        self.assertIn("setGameCameraZoom(resolvedZooms[0]);", handler)
        self.assertIn("camHUD.zoom = resolvedZooms[1];", handler)
        self.assertIn("!isAbsoluteTarget", handler)
        self.assertIn("cameraZoomIntroTargets", handler)
        self.assertNotIn("camZooming = true", handler)

    def test_intro_target_is_reapplied_after_follow_and_decay(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertTrue("camGame = new CompatCamera();" in source,
                        "gameplay must own its compatibility camera")
        self.assertIn("FlxG.cameras.reset(camGame);", source)
        self.assertIn("if (FlxG.camera != null && FlxG.camera != camGame)", source)

        # A HUD-only regression can still pass the target-value tests above:
        # require the engine to bind null-camera world members to camGame and
        # to write the gameplay camera itself when a target is applied.
        self.assertIn("function bindGameplayCameras():Void", source)
        self.assertIn("object.cameras = [camGame];", source)
        game_zoom = source[
            source.index("\tfunction setGameCameraZoom(") : source.index(
                "\n\tfunction holdCameraZoomTargets()", source.index("\tfunction setGameCameraZoom(")
            )
        ]
        self.assertIn("camGame.zoom = zoom;", game_zoom)
        self.assertIn("ensureGameplayCameraBinding();", game_zoom)

        event_start = source.index("\t\tdispatchDueSongEvents();")
        event_pump = source[event_start:source.index("\n\t\t// keep the Image Flash overlay", event_start)]
        self.assertIn("holdCameraZoomTargets();", event_pump)

        decay_start = source.index("\t\tif (camZooming && !inCutscene) {")
        decay_end = source.index("\n\t\tFlxG.watch.addQuick", decay_start)
        self.assertIn("holdCameraZoomTargets();", source[decay_start:decay_end])

    def test_locked_intro_matches_donor_and_normal_pulses_stay_small(self):
        import json

        locked = ROOT / "assets/data/locked/locked.json"
        colorful = ROOT / "assets/data/colorful/colorful.json"
        if not locked.is_file() or not colorful.is_file():
            self.skipTest(f"mounted camera chart fixtures unavailable: {locked}, {colorful}")
        chart = json.loads(locked.read_text())["song"]
        zoom_events = [
            (row[0], event[1], event[2])
            for row in chart["events"]
            for event in row[1]
            if event[0] == "Add Camera Zoom"
        ]
        self.assertEqual(
            zoom_events[:5],
            [
                (0, "0.5", "0.5"),
                (2742.85714285714, "0.6", "0.6"),
                (5485.71428571429, "0.7", "0.7"),
                (8228.57142857143, "0.8", "0.8"),
                (10971.4285714286, "0.9", "0.9"),
            ],
        )
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("detectCameraZoomIntroTargets();", source)
        self.assertIn("cameraZoomIntroUsesTargets(firstAddTime", source)
        # The ordinary donor/Psych spelling is intentionally still visible in
        # the corpus and must not be converted to an absolute target.
        colorful = json.loads(colorful.read_text())["song"]
        first = next(
            event
            for row in colorful["events"]
            for event in row[1]
            if event[0] == "Add Camera Zoom"
        )
        self.assertEqual(first[1:], ["0.060", "0.030"])


if __name__ == "__main__":
    unittest.main()
