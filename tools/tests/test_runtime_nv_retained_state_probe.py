"""Structural contract for the opt-in retained-import native NV state probe."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "source" / "RuntimeNvStateProbe.hx"
RUNNER = ROOT / "tools" / "run_nv_retained_state_native.ps1"
BUILDER = ROOT / "tools" / "prepare_nv_retained_state_fixture.ps1"


class RuntimeNvRetainedStateProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = PROBE.read_text(encoding="utf-8")
        cls.runner = RUNNER.read_text(encoding="utf-8")
        cls.builder = BUILDER.read_text(encoding="utf-8")

    def test_retained_mode_uses_committed_receipt_snapshot_and_public_family_lookup(self):
        self.assertIn("CAMMIE_NV_STATE_RETAINED", self.probe)
        self.assertIn("ImportRefreshTransaction.loadManifest", self.probe)
        self.assertIn("ImportSourceSnapshot.verify(snapshotRoot, snapshotId, null, null, 1)", self.probe)
        self.assertIn("A child verification pool", self.probe)
        self.assertIn("while the game waits for the pool", self.probe)
        self.assertIn("ImportPackageFamilyCatalog.forOwner(alphaRootFromCatalog)", self.probe)
        self.assertIn("manifest.packageFamilyCatalog", self.probe)
        self.assertIn("sourceCore:Reflect.field(retainedEvidence, 'sourceCore')", self.probe)
        self.assertIn("sourceFont:Reflect.field(retainedEvidence, 'sourceFont')", self.probe)
        self.assertIn("findRetainedSourceCore(snapshotRoot, cast snapshotFiles)", self.probe)
        self.assertIn("CompatScriptManifest.selectedRoot(compat)", self.probe)
        self.assertIn("ImportedModDiscovery.ownerForSong(folder, 'assets/data')", self.probe)
        self.assertIn("Path.withoutExtension(parts[3]).toLowerCase() != folder.toLowerCase()", self.probe)
        self.assertIn("path.toLowerCase() != prefix + 'inst.ogg'", self.probe)
        self.assertIn("verifyManifestOutput(install, manifest, owner", self.probe)

    def test_constructed_family_path_is_preserved_and_retained_path_runs_source_init(self):
        self.assertIn("family = [{directory:'alpha',root:a},{directory:'beta',root:b}]", self.probe)
        self.assertIn("NightmareVisionPluginHost.mount(a", self.probe)
        self.assertIn("session.startMeta.skipSplash = splashMode() == 'None'", self.probe)
        self.assertIn("skipSplash:splashMode() == 'None'", self.probe)
        self.assertIn("session.startMeta.skipSplash == (splashMode() == 'None')", self.probe)
        self.assertIn("if (phase == 1 && splashMode() != 'None' && !observeSplash(loads)) return", self.probe)
        self.assertIn("RuntimeSmokeHarness.emit('nv_splash_verified'", self.probe)
        self.assertIn("noLateSwitch:true", self.probe)
        self.assertIn("session.switchState(session.createStateFactory('Init'))", self.probe)
        self.assertIn("session.bootstrapComplete", self.probe)
        self.assertIn("session.mods.selectedRoot() == expectedBetaRoot", self.probe)
        self.assertIn("Reflect.field(parent, 'formatted') == 'retained-state-fixture-easy'", self.probe)
        self.assertIn("checkNativeHostSettingsRestored()", self.probe)
        self.assertIn("Reflect.field(FlxG.keys, 'preventDefaultKeys') == Reflect.field(nativeHostSettings, 'preventDefaultKeys')", self.probe)
        self.assertIn("FlxG.sound.muteKeys == Reflect.field(nativeHostSettings, 'muteKeys')", self.probe)
        self.assertIn("FlxG.mouse.visible == Reflect.field(nativeHostSettings, 'mouseVisible')", self.probe)
        self.assertIn("Source Init changed its 60 Hz update cadence in uncapped host mode", self.probe)

    def test_native_runner_imports_before_state_and_keeps_private_outputs_reviewable(self):
        import_call = self.runner.index("Native retained-source import")
        state_call = self.runner.index("Retained source-state native probe")
        self.assertLess(import_call, state_call)
        self.assertIn("[Parameter(Mandatory=$true)][string]$FixtureDir", self.runner)
        self.assertIn("[Parameter(Mandatory=$true)][string]$RuntimeDir", self.runner)
        self.assertIn("[Parameter(Mandatory=$true)][string]$BuildGate", self.runner)
        self.assertIn("cammie-nv-startup-", self.runner)
        self.assertIn("$runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint", self.runner)
        self.assertIn("BuildGate must stay below the repository tmp directory", self.runner)
        self.assertIn("Join-Path $runtime 'import-cache'", self.runner)
        self.assertIn("--smoke-import-source", self.runner)
        self.assertIn("--smoke-import-type \"Nightmare Vision\"", self.runner)
        self.assertIn("$env:CAMMIE_NV_STATE_RETAINED = '1'", self.runner)
        self.assertIn("$env:CAMMIE_NV_SPLASH_MODE = $SplashMode", self.runner)
        self.assertIn("'CAMMIE_NV_SPLASH_MODE'", self.runner)
        self.assertIn("$retained[0].sourceFont.path -ne 'assets/fonts/consolas.ttf'", self.runner)
        self.assertIn("$fixtureSplashMode -ne $SplashMode", self.runner)
        self.assertIn("$fixtureSplashMode = 'None'", self.runner)
        self.assertIn("'nv_splash_verified'", self.runner)
        self.assertIn("$verified[0].sourceSplash -ne $true", self.runner)
        for proof_field in ("formattedOrLogoVisible", "completed", "disposed", "cleaned", "audioRestored", "noLateSwitch"):
            self.assertIn(f"$splashVerified[0].{proof_field} -ne $true", self.runner)
        self.assertIn("$captures += 'splash'", self.runner)
        self.assertIn("RUNTIME_IMPORT_SMOKE|", self.runner)
        self.assertIn("RUNTIME_SMOKE|", self.runner)
        self.assertIn("Private options and version restored, process environment restored", self.runner)
        self.assertNotIn("Remove-Item", self.runner)

    def test_fixture_builder_is_reproducible_and_create_only(self):
        self.assertIn("[Parameter(Mandatory=$true)][string]$SeedRuntime", self.builder)
        self.assertIn("SeedRuntime must be an explicit absolute path", self.builder)
        self.assertIn("SeedRuntime must be outside the repository checkout", self.builder)
        self.assertIn("Generated fixture output must stay below the repository tmp directory", self.builder)
        self.assertIn("Refusing to replace an existing fixture output", self.builder)
        self.assertIn("fnf_sources/NightmareVision'", self.builder)
        self.assertIn("assets/embeds/fonts/consolas.ttf", self.builder)
        self.assertIn("readOnlySeedInputs = $seedInputs", self.builder)
        self.assertIn("[System.IO.FileMode]::CreateNew", self.builder)
        self.assertIn("content/alpha/assets/songs/retained-state-fixture/data/normal.json", self.builder)
        self.assertIn("content/beta/assets/scripts/states/FixtureTitle.hx", self.builder)
        self.assertIn("content/beta/assets/scripts/states/FixtureDirect.hx", self.builder)
        self.assertIn("content/beta/assets/scripts/states/TitleState.hx", self.builder)
        self.assertIn("State fixture beta", self.builder)
        self.assertIn("new MusicBeatState()", self.builder)
        self.assertIn("new MusicBeatSubstate()", self.builder)
        self.assertIn("new ScriptedState('FixtureDirect')", self.builder)
        self.assertIn("direct-state-load", self.builder)
        self.assertIn("direct-state-destroy", self.builder)
        self.assertIn("__nvFixtureInitDone", self.builder)
        self.assertIn("__probeResetRequested", self.builder)
        self.assertIn("highscore-bound:source", self.builder)
        self.assertNotIn("Remove-Item", self.builder)
        self.assertNotIn("Copy-Item", self.builder)
        self.assertNotIn("WriteAllText", self.builder)

    def test_opt_in_splash_modes_use_hashed_donor_assets_and_default_stays_skipped(self):
        modes = ("None", "Branding", "Video", "SkipBranding", "AbortBranding")
        for mode in modes:
            self.assertIn(f"'{mode}'", self.builder)
            self.assertIn(f"'{mode}'", self.runner)
        self.assertIn("[string]$SplashMode = 'None'", self.builder)
        self.assertIn("[string]$SplashMode = 'None'", self.runner)
        self.assertIn("$allowedSplashModes -ccontains $SplashMode", self.builder)
        self.assertIn("$allowedSplashModes -ccontains $SplashMode", self.runner)
        self.assertIn("assets/game/images/branding/watermarks/NMV.png", self.builder)
        self.assertIn("content/beta/assets/images/branding/watermarks/NMV.png", self.builder)
        self.assertIn("content/beta/assets/sounds/intro.ogg", self.builder)
        self.assertIn("Templates/spooky/lightning.ogg", self.builder)
        self.assertIn("fnf_example_mods/nightmare vision/dsides_r_11_final/content/new-dsides/videos/intro.mp4", self.builder)
        self.assertIn("content/beta/assets/videos/intro.mp4", self.builder)
        self.assertIn("Main.startMeta.skipSplash != Probe.skipSplash", self.builder)
        self.assertIn("splashMode = $SplashMode", self.builder)
        self.assertIn("if ($SplashMode -ne 'None') { $markers += 'nv_splash_verified' }", self.builder)
        self.assertIn("if ($SplashMode -eq 'None')", self.runner)
        self.assertIn("$splashVerified.Count -ne 0", self.runner)


if __name__ == "__main__":
    unittest.main()
