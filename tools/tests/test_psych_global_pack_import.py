"""Ownership and provider selection for chart-free Psych global packs."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class PsychGlobalPackImportTest(unittest.TestCase):
    def test_scoped_import_receipt_provider_and_song_rejection(self):
        with tempfile.TemporaryDirectory(prefix="psych-global-pack-", dir=ROOT / "tmp") as folder:
            work = Path(folder)
            donor_a = work / "misc" / "V-Slice Results Screen (psych engine)"
            donor_b = work / "other-pack"
            chart_donor = work / "pack-with-chart"
            for donor in (donor_a, donor_b, chart_donor):
                (donor / "scripts").mkdir(parents=True)
                (donor / "pack.json").write_text(
                    '{"name":"Shared display name","runsGlobally":true}', encoding="utf-8"
                )
                (donor / "pack.png").write_text("pack-cover", encoding="utf-8")
                (donor / "scripts" / "results.lua").write_text("return 'owned script'", encoding="utf-8")
                (donor / "images").mkdir()
                (donor / "images" / "screen.png").write_text("image-a", encoding="utf-8")
                (donor / "sounds").mkdir()
                (donor / "sounds" / "confirm.ogg").write_text("sound-a", encoding="utf-8")
                (donor / "data").mkdir()
                (donor / "data" / "settings.json").write_text(
                    '{"allowResultsAnimation":{"value":true}}', encoding="utf-8"
                )
            (donor_a / "shared/images").mkdir(parents=True)
            (donor_a / "shared/images/atlas.png").write_text("shared-image", encoding="utf-8")
            (donor_a / "songs/demo").mkdir(parents=True)
            (donor_a / "songs/demo/Inst.ogg").write_text("unused-audio", encoding="utf-8")
            (donor_b / "images" / "screen.png").write_text("image-b", encoding="utf-8")
            bundled = work / "assets/imported_mods/bundled-vslice-results"
            (bundled / "scripts").mkdir(parents=True)
            (bundled / "pack.json").write_text(
                '{"name":"Bundled default","runsGlobally":true}', encoding="utf-8"
            )
            (bundled / "scripts/results.lua").write_text("bundled results", encoding="utf-8")
            (chart_donor / "data" / "fixture").mkdir(parents=True)
            (chart_donor / "data" / "fixture" / "fixture-hard.json").write_text(
                '{"song":{"notes":[],"bpm":120}}', encoding="utf-8"
            )

            (work / "Main.hx").write_text(r'''import sys.FileSystem;
import sys.io.File;
class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function main():Void {
    var donorA = Sys.args()[0];
    var donorB = Sys.args()[1];
    var chartDonor = Sys.args()[2];
    FileSystem.createDirectory('assets/data');
    File.saveContent('assets/data/options.json', 'personal-options-sentinel');
    check(PsychGlobalPackImporter.defaultProvider() == PsychGlobalPackImporter.BUNDLED_PROVIDER_ROOT,
      'packaged results did not provide the clean-install default');
    check(PsychGlobalPackImporter.isEligible(donorA), 'generic global pack was not eligible');
    check(!PsychGlobalPackImporter.isEligible(chartDonor), 'chart-bearing pack was eligible');
    var first = PsychGlobalPackImporter.importPack(donorA);
    check(first.eligible && first.imported && first.failed == 0, 'first import failed: ' + first.errors.join('; '));
    var ownerA = first.ownerRoot;
    check(ownerA == PsychGlobalPackImporter.ownerForSource(donorA), 'owner path was not stable');
    check(File.getContent(ownerA + '/scripts/results.lua') == "return 'owned script'", 'script missing');
    check(File.getContent(ownerA + '/pack.png') == 'pack-cover', 'pack cover missing');
    check(File.getContent(ownerA + '/images/screen.png') == 'image-a', 'image missing');
    check(File.getContent(ownerA + '/sounds/confirm.ogg') == 'sound-a', 'sound missing');
    check(File.getContent(ownerA + '/shared/images/atlas.png') == 'shared-image', 'shared media missing');
    check(!FileSystem.exists(ownerA + '/songs'), 'song audio tree was copied');
    check(File.getContent(ownerA + '/data/settings.json').indexOf('allowResultsAnimation') >= 0,
      'pack settings missing');
    check(File.getContent('assets/data/options.json') == 'personal-options-sentinel',
      'personal options were mutated');
    check(PsychGlobalPackImporter.defaultProvider() == ownerA, 'first provider was not selected');
    check(File.getContent(ownerA + '/' + PsychGlobalPackImporter.RECEIPT_NAME).indexOf(ownerA) >= 0,
      'owner receipt missing');

    File.saveContent(ownerA + '/images/screen.png', 'user-owner-override');
    File.saveContent(donorA + '/images/screen.png', 'changed-donor-image');
    var receiptBefore = File.getContent(ownerA + '/' + PsychGlobalPackImporter.RECEIPT_NAME);
    var repeat = PsychGlobalPackImporter.importPack(donorA);
    check(repeat.imported && repeat.failed == 0 && repeat.ownerRoot == ownerA, 'repeat import failed');
    check(File.getContent(ownerA + '/' + PsychGlobalPackImporter.RECEIPT_NAME) == receiptBefore,
      'valid owner receipt was rewritten');
    check(File.getContent(ownerA + '/images/screen.png') == 'user-owner-override',
      'existing owner file was replaced');
    check(File.getContent(donorA + '/images/screen.png') == 'changed-donor-image', 'donor was changed');

    var second = PsychGlobalPackImporter.importPack(donorB);
    check(second.imported && second.ownerRoot != ownerA, 'distinct source roots shared an owner');
    check(File.getContent(second.ownerRoot + '/images/screen.png') == 'image-b', 'second owner media missing');
    check(PsychGlobalPackImporter.defaultProvider() == ownerA, 'later import silently changed the default');
    check(PsychGlobalPackImporter.selectDefaultProvider(second.ownerRoot), 'valid provider selection failed');
    check(PsychGlobalPackImporter.defaultProvider() == second.ownerRoot, 'provider config did not select owner B');
    File.saveContent(PsychGlobalPackImporter.PROVIDER_CONFIG, '{invalid');
    check(PsychGlobalPackImporter.defaultProvider() == PsychGlobalPackImporter.BUNDLED_PROVIDER_ROOT,
      'invalid user selection did not fall back to packaged results');
    check(!PsychGlobalPackImporter.selectDefaultProvider('assets/imported_mods/../data'),
      'unsafe owner selection was accepted');
    check(!PsychGlobalPackImporter.selectDefaultProvider('assets/imported_mods/not-imported'),
      'owner without receipt was selected');
    check(File.getContent('assets/data/options.json') == 'personal-options-sentinel',
      'provider selection mutated personal options');

    var rejected = PsychGlobalPackImporter.importPack(chartDonor);
    check(!rejected.eligible && !rejected.imported && rejected.ownerRoot == '',
      'chart-bearing global pack was imported');
  }
}''', encoding="utf-8")
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main",
                 str(donor_a), str(donor_b), str(chart_donor)],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_workflow_routes_chart_free_psych_packs_to_the_scoped_importer(self):
        workflow = (ROOT / "source/ImportWorkflow.hx").read_text(encoding="utf-8")
        settings = (ROOT / "source/ImportSettingsState.hx").read_text(encoding="utf-8")
        self.assertIn("PsychGlobalPackImporter.isEligible(descriptor.root, descriptor.contentRoot)", workflow)
        self.assertIn("imported = importChartFreePsychGlobalPacks()", workflow)
        self.assertIn("PsychGlobalPackImporter.importPack(root.root, root.contentRoot)", workflow)
        self.assertIn("scanResult.globalPacksToImport > 0", settings)


if __name__ == "__main__":
    unittest.main()
