"""Structural contract for the retained Psych achievement native fixture."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "tools" / "prepare_psych_achievements_fixture.ps1"
RUNNER = ROOT / "tools" / "run_psych_achievements_native.ps1"
FREEPLAY_SMOKE = ROOT / "source" / "RuntimeSmokeFreeplayState.hx"


class RuntimePsychAchievementsFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = BUILDER.read_text(encoding="utf-8")
        cls.runner = RUNNER.read_text(encoding="utf-8")
        cls.freeplay_smoke = FREEPLAY_SMOKE.read_text(encoding="utf-8")

    def test_builder_creates_a_pinned_psych_source_chart_and_owner_assets(self):
        builder = self.builder
        self.assertIn("[Parameter(Mandatory=$true)][string]$SeedRuntime", builder)
        self.assertIn("[Parameter(Mandatory=$true)][string]$RunId", builder)
        self.assertIn("SeedRuntime must be an explicit absolute path", builder)
        self.assertIn("SeedRuntime must be outside the repository checkout", builder)
        self.assertIn("Refusing to replace an existing fixture output", builder)
        self.assertIn("psych-achievements-fixture-$RunId", builder)
        self.assertIn("5c67ced49e5a98535298a6daa3f8f4ec79ac8399", builder)
        self.assertIn("git -C $psychRoot rev-parse HEAD", builder)
        self.assertIn("$revisionExitCode = $LASTEXITCODE", builder)
        self.assertIn("git -C $psychRoot status --porcelain --untracked-files=no", builder)
        self.assertNotIn("Select-Object -First 1", builder)
        self.assertIn("assets/data/$songFolder/$songFolder.json", builder)
        self.assertIn('"song": "Achievement Runtime Fixture"', builder)
        self.assertIn('"sectionNotes": [[0, 0, 0]]', builder)
        self.assertIn("assets/songs/$songFolder/Inst.ogg", builder)
        self.assertIn('"save": "fixture_progress"', builder)
        self.assertIn('"maxScore": 3', builder)
        self.assertIn('"maxDecimals": 2', builder)
        self.assertIn('"save": "fixture_popup"', builder)
        self.assertIn("assets/images/unknownMod.png", builder)
        self.assertIn("assets/images/achievements/fixture_progress.png", builder)
        self.assertIn("assets/images/achievements/fixture_popup-pixel.png", builder)
        self.assertIn("assets/base_game/shared/images/achievements/week6_nomiss-pixel.png", builder)
        self.assertIn("assets/fonts/vcr.ttf", builder)
        self.assertIn("assets/sounds/confirmMenu.ogg", builder)
        self.assertIn("Templates/spooky/lightning.ogg", builder)
        self.assertIn("[System.IO.FileMode]::CreateNew", builder)
        self.assertIn("readOnlyInputs = $script:readOnlyInputs", builder)
        self.assertIn("sha256 = (Get-FileHash", builder)
        self.assertIn("Read-only fixture input", builder)
        self.assertNotIn("Remove-Item", builder)

    def test_runner_imports_before_smoke_and_requires_all_native_probe_evidence(self):
        runner = self.runner
        import_call = runner.index("Native Psych retained-source import")
        smoke_call = runner.index("Psych achievement native component probe")
        self.assertLess(import_call, smoke_call)
        self.assertIn("[Parameter(Mandatory=$true)][string]$FixtureDir", runner)
        self.assertIn("[Parameter(Mandatory=$true)][string]$RuntimeDir", runner)
        self.assertIn("[Parameter(Mandatory=$true)][string]$BuildGate", runner)
        self.assertIn("cammie-psych-achievements-*", runner)
        self.assertIn("RuntimeDir must be outside the repository checkout", runner)
        self.assertIn("Refusing a non-fresh private runtime with an existing import-cache", runner)
        self.assertIn("BuildGate must stay below the repository tmp directory", runner)
        self.assertIn("--smoke-import-source", runner)
        self.assertIn('--smoke-import-type "Psych"', runner)
        self.assertIn("--smoke-freeplay --smoke-duration-ms 45000", runner)
        self.assertIn("$env:CAMMIE_SMOKE_SAVE_ROOT = $saveRoot.Replace", runner)
        self.assertIn("$env:CAMMIE_PSYCH_ACHIEVEMENTS_SMOKE = '1'", runner)
        self.assertIn("$env:CAMMIE_PSYCH_ACHIEVEMENTS_CAPTURE = $captureStem.Replace", runner)
        self.assertIn("psych_achievements_verified", runner)
        for field in ("hscript", "lua", "reflected", "persistence", "sameOwnerReuse",
                      "otherOwnerCleanup", "popupLifecycle"):
            self.assertIn(f"'{field}'", runner)
        self.assertIn("'-popup.png'", runner)
        self.assertIn("process environment restored", runner)
        self.assertIn("$optionsBefore", runner)
        self.assertIn("$versionBefore", runner)
        self.assertIn("Private options and version restored", runner)
        self.assertNotIn("ownerRoot =", runner)
        self.assertNotIn("ownerRoot:", runner)
        self.assertNotIn("Remove-Item", runner)
        self.assertIn("FlxG.sound.muted = true;", self.freeplay_smoke)

    def test_standard_service_mode_requires_authored_language_inputs_and_real_binders(self):
        probe = (ROOT / 'source/RuntimePsychStandardProbe.hx').read_text(encoding='utf-8')
        for relative in ('assets/shared/data/en-US.lang', 'assets/data/en-US.lang', 'assets/data/fixture-alt.lang'):
            self.assertIn(relative, self.builder)
        self.assertIn('standardServices = [bool]$StandardServices', self.builder)
        self.assertIn('CAMMIE_PSYCH_STANDARD_SMOKE', self.runner)
        self.assertIn('psych_standard_verified', self.runner)
        for field in ('languageReload', 'rpcMarshalling', 'ownerCleanup'):
            self.assertIn("'" + field + "'", self.runner)
        for operation in ('resolvePublishedOwner()', 'new PsychHscriptSourceBindings',
                          'new PsychRuntimeBindings', 'psychLuaNativeClassScope',
                          'FlxG.switchState(FreeplayState.new)', 'DiscordClient.getRequestedSnapshot()'):
            self.assertIn(operation, probe)
        self.assertIn('sourceGameplay:false', probe)


if __name__ == "__main__":
    unittest.main()
