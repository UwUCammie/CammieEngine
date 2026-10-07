"""Retained Psych language publication plans and legacy suppression."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP

from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''import ImportFile as File;
import ImportIO;
import ImportSourceSnapshot;
import PsychAssetProfile.PsychAssetProfileBuild;
import PsychLanguagePublisher;
import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File as RawFile;

class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;

  static function main():Void {
    var config:Dynamic = Json.parse(RawFile.getContent("config.json"));
    var capture = ImportSourceSnapshot.capture(config.sourceRoot, config.cacheRoot,
      "Psych Engine", "0.0.17", {workerCount:1});
    check(capture.status == "complete" && capture.complete,
      "snapshot capture failed: " + capture.error);
    ImportSourceSnapshot.verify(capture.snapshotRoot, capture.snapshotId, null, null, 1);
    var content = Path.join([capture.snapshotRoot, "content"]);
    var selected = Path.join([content, config.rootRelative]);
    var build:PsychAssetProfileBuild = cast config.build;
    var profile = PsychAssetProfile.resolveRetained(content, capture.snapshotId,
      config.rootRelative, "Psych Engine", config.namespace, build);
    if (config.tamperAfterResolve == true)
      RawFile.saveContent(Path.join([selected, config.tamperPath]), "changed-after-snapshot");

    var install = config.install;
    var stage = config.stage;
    var io = ImportIO.begin(install, stage, cast config.masked, true);
    io.setNamespace(selected, "Psych Engine", config.namespace);
    if (config.bindProfile == true)
      io.setAssetProfile(selected, content, capture.snapshotId, config.rootRelative,
        "Psych Engine", config.namespace, profile);
    var owner = "assets/imported_mods/" + config.namespace;
    var requestedOwner = config.destinationRoot == null ? owner : config.destinationRoot;
    var engineArg = config.engineArg == null ? "Psych Engine" : config.engineArg;
    var plan = PsychLanguagePublisher.prepare(selected, engineArg, requestedOwner);
    var published = 0;

    switch (config.mode) {
      case "complete":
        check(profile.complete, "fixture profile should be complete");
        check(plan.profileBound && plan.authoritative && !plan.legacyAllowed,
          "complete retained profile did not become authoritative");
        check(plan.files.length == 1 && plan.files[0].ownerRelative == "data/en-US.lang",
          "complete map did not produce the exact language target");
        check(PsychLanguagePublisher.skipLegacy(plan,
          Path.join([selected, "data/legacy.lang"]), Path.join([owner, "data/legacy.lang"])),
          "complete mapping allowed an unmapped conventional file through legacy fallback");
      case "incomplete":
        check(!profile.complete && plan.profileBound && !plan.authoritative && plan.legacyAllowed,
          "incomplete profile did not preserve the compatibility path");
        check(plan.files.length == 1, "enabled language mapping was not kept additive");
        check(PsychLanguagePublisher.skipLegacy(plan,
          Path.join([selected, "assets/disabled/data/blocked.lang"]),
          Path.join([owner, "data/blocked.lang"])),
          "disabled source leaked into the legacy collector");
        check(PsychLanguagePublisher.skipLegacy(plan,
          Path.join([selected, "assets/uncertain/data/unknown.lang"]),
          Path.join([owner, "uncertain/data/unknown.lang"])),
          "unresolved source leaked into the legacy collector");
        check(!PsychLanguagePublisher.skipLegacy(plan,
          Path.join([selected, "data/legacy.lang"]),
          Path.join([owner, "data/legacy.lang"])),
          "safe legacy compatibility path was suppressed");
      case "cross-extension":
        check(profile.complete && plan.authoritative && plan.files.length == 1,
          "source-filter did not include a non-language source renamed to .lang");
        check(plan.files[0].sourceRelative == "assets/types/data/source.txt"
          && plan.files[0].ownerRelative == "data/converted.lang",
          "cross-extension map did not preserve its authored source and target");
      case "unresolved-collision":
        check(!plan.failed && plan.profileBound && plan.files.length == 0,
          "enabled source was selected despite an unresolved competitor for its owner path");
        check(PsychLanguagePublisher.skipLegacy(plan,
          Path.join([selected, "data/same.lang"]), Path.join([owner, "data/same.lang"])),
          "unresolved owner path was not suppressed from the legacy collector");
      case "prefix-suppression":
        plan.blockedSources.set(Path.join([selected, "data"]), true);
        plan.blockedDestinations.set(Path.join([owner, "shared/data"]), true);
        check(PsychLanguagePublisher.skipLegacy(plan,
          Path.join([selected, "data/nested/fallback.lang"]), Path.join([owner, "data/nested/fallback.lang"])),
          "a deferred source prefix did not suppress a legacy descendant");
        check(PsychLanguagePublisher.skipLegacy(plan,
          Path.join([selected, "other/file.lang"]), Path.join([owner, "shared/data/nested/file.lang"])),
          "a deferred destination prefix did not suppress a legacy descendant");
      case "empty-owner-missing":
        check(plan.failed && plan.blockAllLegacy,
          "an unenumerable mapping to the whole owner root did not protect prior language outputs");
      case "ambiguous", "incomplete-owned", "unknown-owned", "tampered", "wrong-owner",
        "empty-owner-missing":
        check(plan.failed, "uncertain mapping did not stop over a prior managed language output");
        check(plan.files.length == 0 || config.mode == "incomplete-owned",
          "ambiguous or invalid mapping selected an output");
      case "unavailable":
        check(!plan.profileBound && plan.legacyAllowed && plan.files.length == 0,
          "profile-unavailable import changed legacy behavior");
      default:
        throw "unknown publisher fixture mode: " + config.mode;
    }

    PsychLanguagePublisher.publish(plan, function(source:String, destination:String):Void {
      io.copy(source, destination);
      published++;
    });
    if (config.mode == "complete" || config.mode == "cross-extension" || config.mode == "incomplete") {
      check(published == plan.files.length, "planned files were not published through ImportIO");
      for (file in plan.files)
        check(File.getBytes(file.destinationPath).toHex() == RawFile.getBytes(file.sourcePath).toHex(),
          "published language bytes changed: " + file.ownerRelative);
    } else {
      check(published == 0, "failed or unavailable plan unexpectedly wrote mapped files");
    }
    if (config.mode == "ambiguous" || config.mode == "incomplete-owned"
      || config.mode == "unknown-owned" || config.mode == "tampered" || config.mode == "wrong-owner"
      || config.mode == "empty-owner-missing") {
      var prior = Path.join([install, config.priorRelative]);
      check(RawFile.getContent(prior) == "prior-managed-language",
        "previously managed language output changed");
    }
    ImportIO.end();
    RawFile.saveContent("result.json", Json.stringify({
      profileComplete:profile.complete,
      walkStatus:plan.cancelled ? "cancelled" : (plan.failed ? "failed" : "ready"),
      authoritative:plan.authoritative,
      legacyAllowed:plan.legacyAllowed,
      blockAllLegacy:plan.blockAllLegacy,
      failed:plan.failed,
      published:published,
      files:[for (file in plan.files) {
        sourceRelative:file.sourceRelative, ownerRelative:file.ownerRelative,
        candidateOrder:file.candidateOrder, sha256:file.sha256, size:file.size
      }],
      diagnostics:plan.diagnostics
    }));
  }
}'''


COMPLETE_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/translations" rename="assets" />
</project>
'''

INCOMPLETE_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/translations" rename="assets" />
  <assets path="assets/disabled" rename="assets" if="NOT_SELECTED" />
  <assets path="assets/uncertain" rename="assets/uncertain" if="UNKNOWN_FLAG" />
</project>
'''

AMBIGUOUS_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/one" rename="assets" />
  <assets path="assets/two" rename="assets" />
</project>
'''

CROSS_EXTENSION_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/types" rename="assets">
    <image name="data/source.txt" rename="data/converted.lang" />
  </assets>
</project>
'''

UNRESOLVED_COLLISION_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/enabled" rename="assets" />
  <assets path="assets/unresolved" rename="assets" if="UNKNOWN_FLAG" />
</project>
'''

UNKNOWN_SCOPE_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/$UNKNOWN_SOURCE" rename="assets" />
</project>
'''

EMPTY_OWNER_MISSING_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/missing-language-root" rename="assets" />
</project>
'''


def write_bytes(root, relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class PsychLanguagePublisherTest(unittest.TestCase):
    def run_fixture(self, mode, project, files, *, masked=(), tamper_after_resolve=False,
                    bind_profile=True, tamper_path="", destination_root=None, engine_arg=None):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="psych-language-publisher-", dir=TEST_TMP)
        self.addCleanup(temporary.cleanup)
        work = Path(temporary.name)
        source = work / "donor"
        source.mkdir()
        (source / "Project.xml").write_text(project, encoding="utf-8", newline="\n")
        for relative, data in files.items():
            write_bytes(source, relative, data)
        install = work / "install"
        stage = install / "import-cache/staging/session"
        stage.mkdir(parents=True)
        masked_paths = []
        prior_relative = ""
        for relative in masked:
            prior_relative = relative
            prior = install / relative
            prior.parent.mkdir(parents=True, exist_ok=True)
            prior.write_bytes(b"prior-managed-language")
            masked_paths.append(relative)
        build = {"command": "", "flags": [
            {"name": "NOT_SELECTED", "state": "disabled", "provenance": "publisher-fixture"}
        ]}
        config = {
            "mode": mode,
            "sourceRoot": str(source),
            "cacheRoot": str(install / "import-cache/sources"),
            "rootRelative": "",
            "namespace": "psych-language-publisher-fixture",
            "build": build,
            "install": str(install),
            "stage": str(stage),
            "masked": masked_paths,
            "priorRelative": prior_relative,
            "tamperAfterResolve": tamper_after_resolve,
            "tamperPath": tamper_path,
            "bindProfile": bind_profile,
            "destinationRoot": destination_root,
            "engineArg": engine_arg,
        }
        (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
        (work / "config.json").write_text(json.dumps(config), encoding="utf-8", newline="\n")
        tjson = work / "tjson"
        tjson.mkdir()
        (tjson / "TJSON.hx").write_text('''package tjson;
class TJSON {}
enum EncodeStyle { Full; }
class TJSONEncoder {
 public function new() {}
 public function doEncode(value:Dynamic, ?style:String):String return haxe.Json.stringify(value);
 public function encodeValue(value:Dynamic, style:EncodeStyle, depth:Int):String return haxe.Json.stringify(value);
}''', encoding="utf-8", newline="\n")
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main"],
            cwd=work, env=env, text=True, capture_output=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((work / "result.json").read_text(encoding="utf-8"))

    def test_complete_profile_is_authoritative_and_preserves_mapped_bytes(self):
        result = self.run_fixture("complete", COMPLETE_PROJECT, {
            "assets/translations/data/en-US.lang": b'English (US)\r\nmapped: "Exact bytes"\r\n',
            "data/legacy.lang": b'English (US)\nlegacy: "Should not leak"\n',
        }, engine_arg="psych")
        self.assertTrue(result["profileComplete"])
        self.assertTrue(result["authoritative"])
        self.assertFalse(result["legacyAllowed"])
        self.assertEqual(result["published"], 1)
        self.assertEqual(result["files"][0]["ownerRelative"], "data/en-US.lang")

    def test_bound_profile_rejects_a_sibling_owner_destination_before_copy(self):
        result = self.run_fixture("wrong-owner", COMPLETE_PROJECT, {
            "assets/translations/data/en-US.lang": b'English (US)\nmapped: "Must stay scoped"\n',
        }, destination_root="assets/imported_mods/sibling-owner",
            masked=("assets/imported_mods/psych-language-publisher-fixture/data/en-US.lang",))
        self.assertTrue(result["failed"])
        self.assertEqual(result["published"], 0)

    def test_incomplete_profile_adds_enabled_mapping_but_suppresses_disabled_and_unresolved_sources(self):
        result = self.run_fixture("incomplete", INCOMPLETE_PROJECT, {
            "assets/translations/data/en-US.lang": b'English (US)\nmapped: "Retained"\n',
            "assets/disabled/data/blocked.lang": b'English (US)\nblocked: "Disabled"\n',
            "assets/uncertain/data/unknown.lang": b'English (US)\nunknown: "Unresolved"\n',
            "data/legacy.lang": b'English (US)\nlegacy: "Compatibility"\n',
        })
        self.assertFalse(result["profileComplete"])
        self.assertFalse(result["authoritative"])
        self.assertTrue(result["legacyAllowed"])
        self.assertEqual(result["published"], 1)

    def test_non_language_source_renamed_to_lang_is_still_receipt_checked_and_published(self):
        result = self.run_fixture("cross-extension", CROSS_EXTENSION_PROJECT, {
            "assets/types/data/source.txt": b'English (US)\nrenamed: "Mapped"\n',
        })
        self.assertTrue(result["profileComplete"])
        self.assertEqual(result["published"], 1)
        self.assertEqual(result["files"][0]["sourceRelative"], "assets/types/data/source.txt")
        self.assertEqual(result["files"][0]["ownerRelative"], "data/converted.lang")

    def test_enabled_mapping_is_suppressed_when_unresolved_competitor_targets_same_path(self):
        result = self.run_fixture("unresolved-collision", UNRESOLVED_COLLISION_PROJECT, {
            "assets/enabled/data/same.lang": b'English (US)\nenabled: "Known"\n',
            "assets/unresolved/data/same.lang": b'English (US)\nunresolved: "Unknown"\n',
        })
        self.assertFalse(result["failed"])
        self.assertEqual(result["published"], 0)

    def test_legacy_suppression_treats_deferred_paths_as_subtree_prefixes(self):
        result = self.run_fixture("prefix-suppression", COMPLETE_PROJECT, {}, bind_profile=False)
        self.assertEqual(result["published"], 0)

    def test_missing_candidate_mapped_to_assets_root_preserves_prior_language_output(self):
        result = self.run_fixture("empty-owner-missing", EMPTY_OWNER_MISSING_PROJECT, {},
            masked=("assets/imported_mods/psych-language-publisher-fixture/data/en-US.lang",))
        self.assertTrue(result["failed"])
        self.assertEqual(result["published"], 0)

    def test_ambiguous_target_and_unresolved_owned_target_preserve_prior_language_bytes(self):
        collision = self.run_fixture("ambiguous", AMBIGUOUS_PROJECT, {
            "assets/one/data/same.lang": b'English (US)\none: "First"\n',
            "assets/two/data/same.lang": b'English (US)\ntwo: "Second"\n',
        }, masked=("assets/imported_mods/psych-language-publisher-fixture/data/same.lang",))
        self.assertTrue(collision["failed"])
        self.assertEqual(collision["published"], 0)
        unresolved = self.run_fixture("incomplete-owned", INCOMPLETE_PROJECT, {
            "assets/translations/data/en-US.lang": b'English (US)\nmapped: "Retained"\n',
            "assets/disabled/data/blocked.lang": b'English (US)\nblocked: "Disabled"\n',
            "assets/uncertain/data/unknown.lang": b'English (US)\nunknown: "Unresolved"\n',
        }, masked=("assets/imported_mods/psych-language-publisher-fixture/uncertain/data/unknown.lang",))
        self.assertTrue(unresolved["failed"])
        self.assertEqual(unresolved["published"], 0)

    def test_unenumerable_and_changed_snapshot_mappings_fail_closed_for_managed_languages(self):
        unknown = self.run_fixture("unknown-owned", UNKNOWN_SCOPE_PROJECT, {},
            masked=("assets/imported_mods/psych-language-publisher-fixture/data/stale.lang",))
        self.assertTrue(unknown["failed"])
        tampered = self.run_fixture("tampered", COMPLETE_PROJECT, {
            "assets/translations/data/en-US.lang": b'English (US)\nmapped: "Original"\n',
        }, masked=("assets/imported_mods/psych-language-publisher-fixture/data/en-US.lang",),
            tamper_after_resolve=True, tamper_path="assets/translations/data/en-US.lang")
        self.assertTrue(tampered["failed"])
        self.assertEqual(tampered["published"], 0)

    def test_missing_profile_keeps_legacy_path_enabled(self):
        result = self.run_fixture("unavailable", COMPLETE_PROJECT, {
            "assets/translations/data/en-US.lang": b'English (US)\nmapped: "Retained"\n',
        }, bind_profile=False)
        self.assertFalse(result["authoritative"])
        self.assertTrue(result["legacyAllowed"])
        self.assertEqual(result["published"], 0)

    def test_both_psych_import_routes_use_the_shared_plan_and_legacy_suppression(self):
        module_functions = (ROOT / "source/ModuleFunctions.hx").read_text(encoding="utf-8")
        global_pack = (ROOT / "source/PsychGlobalPackImporter.hx").read_text(encoding="utf-8")
        composite = (ROOT / "source/SourceMappedMediaPublisher.hx").read_text(encoding="utf-8")
        self.assertIn("SourceMappedMediaPublisher.prepare(sourceRoot, normalizedEngine", module_functions)
        self.assertIn("SourceMappedMediaPublisher.publish(owner.plan", module_functions)
        self.assertIn("SourceMappedMediaPublisher.languageView(mappedPlan)", module_functions)
        self.assertIn("SourceMappedMediaPublisher.skipLegacyGlobal", module_functions)
        self.assertIn("SourceMappedMediaPublisher.prepare(source, ImportEngine.PSYCH", global_pack)
        self.assertIn("SourceMappedMediaPublisher.publish(mappedPlan", global_pack)
        self.assertIn("SourceMappedMediaPublisher.skipLegacyGlobal", global_pack)
        self.assertIn("SourceMappedAssetPublisher.prepareMany", composite)
        self.assertIn("PsychLanguagePublisher.skipLegacy(languagePlan, sourcePath, destinationPath)", global_pack)


if __name__ == "__main__":
    unittest.main()
