"""Receipt-bound Psych Project.xml asset mappings and source data scopes."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP

from pathlib import Path
from haxe_test_support import FixturePath as Path
import hashlib
import json
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import PsychAssetProfile.PsychAssetProfileBuild;
@:access(ImportSourceSnapshot)
class Main {
 static function main():Void {
  var config:Dynamic = haxe.Json.parse(File.getContent("config.json"));
  var engine:String = config.engine == null ? "Psych Engine" : config.engine;
  var capture = ImportSourceSnapshot.capture(config.sourceRoot, config.cacheRoot,
   engine, "0.0.17", {workerCount:1});
  if (capture.status != "complete" || !capture.complete)
   throw "fixture snapshot did not complete: " + capture.error;
  if (config.legacySchema1 == true) {
   var receipt:Dynamic = haxe.Json.parse(File.getContent(capture.receiptPath));
   var directories:Array<String> = cast Reflect.field(receipt, "directories");
   var files:Array<Dynamic> = cast Reflect.field(receipt, "files");
   var exclusions:Array<Dynamic> = cast Reflect.field(receipt, "exclusions");
   var omissions:Array<Dynamic> = cast Reflect.field(receipt, "omissions");
   var incomplete:Array<Dynamic> = cast Reflect.field(receipt, "incompleteReasons");
   Reflect.setField(receipt, "snapshotSchemaVersion", 1);
   var legacyId = ImportSourceSnapshot.receiptSnapshotId(engine, directories, files,
    exclusions, omissions, incomplete, 1);
   Reflect.setField(receipt, "snapshotId", legacyId);
   File.saveContent(capture.receiptPath, haxe.Json.stringify(receipt));
   var legacyRoot = Path.join([Path.directory(capture.snapshotRoot), legacyId]);
   FileSystem.rename(capture.snapshotRoot, legacyRoot);
   capture.snapshotId = legacyId;
   capture.snapshotRoot = legacyRoot;
   capture.receiptPath = Path.join([legacyRoot, "receipt.json"]);
  }
  ImportSourceSnapshot.verify(capture.snapshotRoot, capture.snapshotId, null, null, 1);
  var content = Path.join([capture.snapshotRoot, "content"]);
  var selected = Path.join([content, config.rootRelative]);
  if (config.tamperProject)
   File.saveContent(Path.join([selected, "Project.xml"]), "<project><assets path='changed'/></project>");
  if (config.tamperLanguage)
   File.saveContent(Path.join([selected, "assets/translations/data/en-US.lang"]), "tampered language bytes");
  if (config.tamperMappedNonLanguage)
   File.saveContent(Path.join([selected, "assets/mapped-types/scripts/Effect.hx"]), "tampered script bytes");
  if (config.deleteMappedNonLanguage)
   FileSystem.deleteFile(Path.join([selected, "assets/mapped-types/audio/theme.ogg"]));
  if (config.deleteTypedMapped)
   FileSystem.deleteFile(Path.join([selected, "assets/typed-raw/raw.bin"]));
  if (config.tamperIncludedProject != null)
   File.saveContent(Path.join([selected, config.tamperIncludedProject]), "<project><define name='TAMPERED'/></project>");

  var build:PsychAssetProfileBuild = cast config.build;
  var profile = PsychAssetProfile.resolveRetained(content, capture.snapshotId,
   config.rootRelative, engine, config.namespace, build);
  var resolverCancellation:Dynamic = null;
  if (config.cancelAfter != null) {
   var checks = 0;
   var caught = false;
   try {
    PsychAssetProfile.resolveRetained(content, capture.snapshotId,
     config.rootRelative, engine, config.namespace, build, function() {
      checks++;
      return checks >= Std.int(config.cancelAfter);
     });
   } catch (error:Dynamic) {
    if (Std.isOfType(error, ImportWorkCancelled)) caught = true;
    else throw error;
   }
   resolverCancellation = {caught:caught, checks:checks};
  }
  var events:Array<Dynamic> = [];
  var walk = PsychAssetProfile.walkLanguageFiles(profile, content,
   function(item) events.push(item));
  var mappedEvents:Array<Dynamic> = [];
  var mappedWalk = PsychAssetProfile.walkMappedFiles(profile, content,
   function(item) mappedEvents.push(item));
  var filteredMappedEvents:Array<Dynamic> = [];
  var filteredMappedWalk = PsychAssetProfile.walkMappedFiles(profile, content,
   function(item) filteredMappedEvents.push(item), null, null,
   function(sourceRelative:String, mappedPath:String) return
    StringTools.endsWith(sourceRelative.toLowerCase(), ".lang")
    || StringTools.endsWith(mappedPath.toLowerCase(), ".lang"));
  var typedMappedEvents:Array<Dynamic> = [];
  var typedMappedWalk = PsychAssetProfile.walkMappedFiles(profile, content,
   function(item) typedMappedEvents.push(item), null, null, null,
   function(candidate, sourceRelative:String, mappedPath:String) return candidate.type == "image");
  var cancelledWalk = PsychAssetProfile.walkMappedFiles(profile, content,
   null, null, function() return true);
  var badRoot = PsychAssetProfile.resolveRetained(content, capture.snapshotId,
   "../nested/root", engine, config.namespace, build);
  var unverified = PsychAssetProfile.resolveUnverified(selected, engine,
   config.namespace, build);
  var unverifiedWalk = PsychAssetProfile.walkLanguageFiles(unverified, content,
   function(item) events.push(item));
  File.saveContent("result.json", haxe.Json.stringify({capture:capture,
   profile:profile, walk:walk, events:events, mappedWalk:mappedWalk,
   mappedEvents:mappedEvents, filteredMappedWalk:filteredMappedWalk,
   filteredMappedEvents:filteredMappedEvents, typedMappedWalk:typedMappedWalk,
   typedMappedEvents:typedMappedEvents, cancelledWalk:cancelledWalk, badRoot:badRoot,
   unverified:unverified, unverifiedWalk:unverifiedWalk,
   resolverCancellation:resolverCancellation}));
 }
}'''


PROJECT = '''<?xml version="1.0" encoding="utf-8"?>
<project>
  <define name="TRANSLATIONS_ALLOWED" />
  <section if="TRANSLATIONS_ALLOWED">
    <assets path="assets/translations" rename="assets" exclude="*.ogg" if="web" />
    <assets path="assets/translations" rename="assets" exclude="*.mp3" unless="web" />
    <assets path="assets/translations" rename="assets/alternate" unless="web" />
  </section>
  <section if="officialBuild">
    <define name="BASE_GAME_FILES" />
    <define name="VIDEOS_ALLOWED" if="windows || linux || android || mac" unless="32bits" />
  </section>
  <assets path="assets/videos" if="VIDEOS_ALLOWED" />
  <section if="BASE_GAME_FILES">
    <assets path="assets/base_game" rename="assets" if="BASE_GAME_FILES" />
  </section>
  <assets path="assets/haxedef-only" if="FLAG_ONLY" />
  <assets path="assets/filter-profile" rename="assets/filtered"
    include="special[0-9].lang" exclude="blocked.lang" />
  <assets path="assets/question-filter" rename="assets/question" include="special?.lang" />
  <assets path="assets/prefix-filter" rename="assets/prefix" include="special" />
  <assets path="assets/nested" rename="assets/nested-target" include="ignored*.lang">
    <image name="shared/data/from-child.lang" rename="shared/data/nested.lang"
      include="ignored-child" />
  </assets>
  <assets path="assets/direct-file.bin" rename="assets/direct/renamed.bin" />
  <assets path="assets/nested-typed">
    <asset path="text-source.unknown" rename="text-output.bin" type="text" />
    <asset path="binary-source.unknown" rename="binary-output.dat" type="binary" />
  </assets>
  <assets path="assets/mapped-types" rename="assets/types" />
  <assets path="assets/typed-raw" rename="assets/nonstandard" type="image" />
  <assets path="assets/disabled-tree" rename="assets/disabled" if="false" />
  <assets path="assets/uncertain-tree" rename="assets/uncertain" if="MISSING_FEATURE" />
  <assets path="assets/uncertain-tree" rename="assets/dynamic-filter" include="$MAPPING_FILTER" />
  <assets path="assets/collision-a" rename="assets/collision" />
  <assets path="assets/collision-b" rename="assets/collision" />
  <assets path="assets/collision-source.dat" rename="assets/collision/same.lang" />
  <assets path="assets/collision-target.lang" rename="assets/collision/same.lang" />
  <assets path="assets/escaped&amp;source" rename="assets/escaped&amp;target" />
  <assets path="assets/bundles" rename="assets/bundles" />
  <assets path="example_mods" rename="mods" if="MODS_ALLOWED" />
  <haxedef name="FLAG_ONLY" />
  <haxeflag name="--macro" value="allowPackage('flash')" />
  <macro name="sample.BuildMacro.run()" />
  <include path="extra-project.xml" />
</project>
'''

MISSING_ASSETS_ROOT_PROJECT = '''<?xml version="1.0" encoding="utf-8"?>
<project>
  <assets path="assets/translations" rename="assets" />
</project>
'''


# Focused declaration slice copied from the pinned donor Project.xml. Its
# conditions and renames are kept in donor order; this is not the full file.
PINNED_DONOR_PROJECT_SLICE = '''<?xml version="1.0" encoding="utf-8"?>
<project>
  <define name="MODS_ALLOWED" if="desktop" />
  <define name="TRANSLATIONS_ALLOWED" />
  <section if="officialBuild">
    <define name="TITLE_SCREEN_EASTER_EGG" />
    <define name="BASE_GAME_FILES" />
    <define name="VIDEOS_ALLOWED" if="windows || linux || android || mac" unless="32bits" />
  </section>
  <assets path="assets/fonts" />
  <assets path="assets/shared" exclude="*.ogg" if="web" />
  <assets path="assets/shared" exclude="*.mp3" unless="web" />
  <assets path="assets/embed" exclude="*.ogg" if="web" embed="true" />
  <assets path="assets/embed" exclude="*.mp3" unless="web" embed="true" />
  <assets path="assets/videos" if="VIDEOS_ALLOWED" />
  <assets path="assets/songs" exclude="*.ogg" if="web" />
  <assets path="assets/songs" exclude="*.mp3" unless="web" />
  <assets path="assets/week_assets" rename="assets" exclude="*.ogg" if="web" />
  <assets path="assets/week_assets" rename="assets" exclude="*.mp3" unless="web" />
  <section if="TITLE_SCREEN_EASTER_EGG">
    <assets path="assets/secrets" rename="assets/shared" exclude="*.ogg" if="web" />
    <assets path="assets/secrets" rename="assets/shared" exclude="*.mp3" unless="web" />
  </section>
  <section if="TRANSLATIONS_ALLOWED">
    <assets path="assets/translations" rename="assets" exclude="*.ogg" if="web" />
    <assets path="assets/translations" rename="assets" exclude="*.mp3" unless="web" />
  </section>
  <section if="BASE_GAME_FILES">
    <assets path="assets/base_game" rename="assets" exclude="*.ogg" if="web" />
    <assets path="assets/base_game" rename="assets" exclude="*.mp3" unless="web" />
  </section>
  <section if="MODS_ALLOWED">
    <assets path="example_mods" rename="mods" embed="false" type="template" unless="mac" />
    <assets path="example_mods" rename="mods" embed="false" if="mac" />
    <assets path="list.txt" rename="modsList.txt" />
  </section>
  <assets path="art/readme.txt" rename="do NOT readme.txt" />
  <section if="desktop">
    <assets path="alsoft.txt" rename="plugins/alsoft.ini" type="text" if="windows" />
    <assets path="alsoft.txt" rename="plugins/alsoft.conf" type="text" unless="windows" />
  </section>
</project>
'''


EXPLICIT_BUILD = {
    "target": "windows",
    "command": "",
    "flags": [
        {"name": "web", "state": "disabled", "provenance": "focused-fixture"},
        {"name": "officialBuild", "state": "enabled", "provenance": "focused-fixture"},
        {"name": "windows", "state": "enabled", "provenance": "focused-fixture"},
        {"name": "linux", "state": "disabled", "provenance": "focused-fixture"},
        {"name": "android", "state": "disabled", "provenance": "focused-fixture"},
        {"name": "mac", "state": "disabled", "provenance": "focused-fixture"},
        {"name": "32bits", "state": "disabled", "provenance": "focused-fixture"},
        {"name": "MODS_ALLOWED", "state": "enabled", "provenance": "focused-fixture"},
    ],
}


def write_bytes(root, relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class PsychAssetProfileTest(unittest.TestCase):
    def run_profile(self, build, *, tamper_project=False, tamper_language=False,
                    tamper_mapped_non_language=False, delete_mapped_non_language=False,
                    delete_typed_mapped=False,
                    omit_translation_root=False,
                    tamper_included_project=None, project_files=None,
                    cancel_after=None,
                    legacy_schema1=False,
                    project_text=PROJECT,
                    engine="Psych Engine"):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix="psych-profile-", dir=TEST_TMP)
        self.addCleanup(temp.cleanup)
        work = Path(temp.name)
        source = work / "source"
        selected = source / "nested/root"
        selected.mkdir(parents=True)
        if isinstance(project_text, bytes):
            (selected / "Project.xml").write_bytes(project_text)
        else:
            (selected / "Project.xml").write_text(project_text, encoding="utf-8", newline="\n")
        (source / "other/root").mkdir(parents=True)
        (source / "other/root/Project.xml").write_text(
            '<project><assets path="other-only" /></project>', encoding="utf-8", newline="\n"
        )
        language_files = {
            "assets/translations/data/en-US.lang": b'English (US)\r\nhello: "Root"\r\n',
            "assets/translations/shared/data/en-US.lang": b'English (US)\nhello: "Shared"\n',
            "assets/translations/week1/data/en-US.lang": b'English (US)\nhello: "Level"\n',
            "assets/translations/base_game/week1/data/en-US.lang": b'English (US)\nhello: "Base level"\n',
            "assets/translations/library/alternate/data/en-US.lang": b'English (US)\nhello: "Library"\n',
            "assets/translations/mods/untrusted/data/en-US.lang": b'English (US)\nhello: "Untrusted"\n',
            "assets/translations/data/readme.txt": b'not a language file',
            "assets/filter-profile/data/special7.lang": b'English (US)\nspecial: "Keep"\n',
            "assets/filter-profile/data/specialx.lang": b'English (US)\nspecial: "Wrong"\n',
            "assets/filter-profile/data/blocked.lang": b'English (US)\nspecial: "Blocked"\n',
            "assets/question-filter/data/special.lang": b'English (US)\nquestion: "Optional l"\n',
            "assets/question-filter/data/specia.lang": b'English (US)\nquestion: "No l"\n',
            "assets/question-filter/data/special7.lang": b'English (US)\nquestion: "Not a wildcard"\n',
            "assets/prefix-filter/data/special-case.lang": b'English (US)\nprefix: "Prefix"\n',
            "assets/prefix-filter/data/not-special.lang": b'English (US)\nprefix: "No prefix"\n',
            "assets/nested/shared/data/from-child.lang": b'English (US)\nnested: "Nested asset"\n',
            "assets/nested/child/metadata.bin": b"nested metadata payload",
            "assets/direct-file.bin": b"direct-file-source-bytes",
            "assets/nested-typed/text-source.unknown": b"explicit nested text payload",
            "assets/nested-typed/binary-source.unknown": bytes(range(16)),
            "assets/mapped-types/images/atlas.PNG": b"image-payload",
            "assets/mapped-types/scripts/Effect.hx": b"class Effect {}",
            "assets/mapped-types/audio/theme.ogg": b"audio-payload",
            "assets/mapped-types/files/resource.bundle": b"ordinary-bundle-extension-file",
            "assets/mapped-types/readme.hash": b"excluded-hash",
            "assets/typed-raw/raw.bin": b"typed-image-payload",
            "assets/disabled-tree/disabled.dat": b"disabled-source-bytes",
            "assets/disabled-tree/disabled.lang": b'English (US)\ndisabled: "Phrase"\n',
            "assets/uncertain-tree/uncertain.dat": b"uncertain-source-bytes",
            "assets/uncertain-tree/uncertain.lang": b'English (US)\nuncertain: "Phrase"\n',
            "assets/collision-a/same.dat": b"first-collision-source",
            "assets/collision-b/same.dat": b"second-collision-source",
            "assets/collision-source.dat": b"non-language-collision-source",
            "assets/collision-target.lang": b'English (US)\ncollision: "Phrase"\n',
            "assets/escaped&source/value.dat": b"escaped-path-source",
            "assets/bundles/test.bundle/payload.bin": b"bundle-payload",
        }
        for relative, data in language_files.items():
            if omit_translation_root and relative.startswith("assets/translations/"):
                continue
            write_bytes(selected, relative, data)
        for relative, data in (project_files or {}).items():
            if isinstance(data, bytes):
                write_bytes(selected, relative, data)
            else:
                write_bytes(selected, relative, data.encode("utf-8"))
        config = {
            "sourceRoot": str(source),
            "cacheRoot": str(work / "snapshot-cache"),
            "rootRelative": "nested/root",
            "namespace": "psych-owner-fixture",
            "build": build,
            "engine": engine,
            "tamperProject": tamper_project,
            "tamperLanguage": tamper_language,
            "tamperMappedNonLanguage": tamper_mapped_non_language,
            "deleteMappedNonLanguage": delete_mapped_non_language,
            "deleteTypedMapped": delete_typed_mapped,
            "tamperIncludedProject": tamper_included_project,
            "cancelAfter": cancel_after,
            "legacySchema1": legacy_schema1,
        }
        (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
        (work / "config.json").write_text(json.dumps(config), encoding="utf-8", newline="\n")
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main"],
            cwd=work, env=env, text=True, capture_output=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((work / "result.json").read_text(encoding="utf-8")), language_files

    def test_exact_pinned_psych_and_nightmare_vision_project_bytes_resolve(self):
        pinned = [
            ("Psych Engine", ROOT.parent / "fnf_sources/FNF-PsychEngine/Project.xml",
             "1c5a6e0ac31780686317ad5efb720fdee93f9547d83ca6289d36ba46fc69790b"),
            ("Nightmare Vision", ROOT.parent / "fnf_sources/NightmareVision/Project.xml",
             "96a3e7ae97889f88285613e6cbe8189deb5bb6c916b3808c49a915f8fdf593a8"),
        ]
        for engine, project_path, expected_hash in pinned:
            with self.subTest(engine=engine):
                if not project_path.is_file():
                    self.skipTest(f"pinned {engine} donor Project.xml is unavailable")
                project_bytes = project_path.read_bytes()
                self.assertEqual(hashlib.sha256(project_bytes).hexdigest(), expected_hash)
                result, _ = self.run_profile(EXPLICIT_BUILD, project_text=project_bytes, engine=engine)
                profile = result["profile"]
                self.assertEqual(profile["provenance"], "receipt-bound")
                self.assertEqual(profile["sourceEngine"], engine)
                self.assertEqual(profile["projectSha256"], expected_hash)
                self.assertEqual(result["mappedWalk"]["status"], "incomplete")
                candidates = profile["candidates"]
                if engine == "Psych Engine":
                    self.assertIn(("assets/fonts", "enabled"),
                                  [(row["sourceRelative"], row["state"]) for row in candidates])
                else:
                    self.assertTrue({("assets/embeds", "enabled"), ("assets/game", "enabled")}
                                    <= {(row["sourceRelative"], row["state"]) for row in candidates})

    def test_receipt_bound_mapping_preserves_rename_order_and_lime_filters(self):
        result, _ = self.run_profile(EXPLICIT_BUILD)
        profile = result["profile"]
        self.assertEqual(profile["provenance"], "receipt-bound")
        self.assertEqual(profile["rootRelative"], "nested/root")
        self.assertEqual(profile["namespace"], "psych-owner-fixture")
        self.assertEqual(profile["projectRelative"], "nested/root/Project.xml")
        self.assertEqual(
            profile["projectSha256"],
            hashlib.sha256(PROJECT.encode("utf-8")).hexdigest(),
        )
        self.assertFalse(profile["complete"], "opaque macro/include inputs must prevent a completeness claim")
        self.assertTrue(any(":haxedef name=FLAG_ONLY" in item for item in profile["opaqueBuildInputs"]))

        candidates = profile["candidates"]
        translations = [item for item in candidates if item["sourceRelative"] == "assets/translations"]
        self.assertEqual(
            [(item["state"], item["targetRelative"]) for item in translations],
            [("disabled", "assets"), ("enabled", "assets"), ("enabled", "assets/alternate")],
        )
        videos = next(item for item in candidates if item["sourceRelative"] == "assets/videos")
        base_game = next(item for item in candidates if item["sourceRelative"] == "assets/base_game")
        haxedef_only = next(item for item in candidates if item["sourceRelative"] == "assets/haxedef-only")
        self.assertEqual(videos["state"], "enabled")
        self.assertEqual(base_game["state"], "enabled")
        self.assertEqual(haxedef_only["state"], "unresolved")
        nested = next(item for item in candidates if item["sourceRelative"] ==
                      "assets/nested/shared/data/from-child.lang")
        self.assertEqual(nested["state"], "enabled")
        self.assertEqual(nested["targetRelative"], "assets/nested-target/shared/data/nested.lang")
        self.assertEqual(nested["type"], "image")

        events = result["events"]
        root_translation = "assets/translations/shared/data/en-US.lang"
        mapped_duplicates = [item for item in events if item["sourceRelative"] == root_translation]
        self.assertEqual([item["mappedPath"] for item in mapped_duplicates], [
            "assets/shared/data/en-US.lang", "assets/alternate/shared/data/en-US.lang"
        ])
        self.assertEqual([item["ownerRelative"] for item in mapped_duplicates], [
            "shared/data/en-US.lang", "alternate/shared/data/en-US.lang"
        ])
        self.assertTrue(any(item["mappedPath"] == "assets/base_game/week1/data/en-US.lang" for item in events))
        self.assertTrue(any(item["mappedPath"] == "assets/week1/data/en-US.lang" for item in events))
        self.assertTrue(any(item["mappedPath"] == "assets/library/alternate/data/en-US.lang" for item in events))
        self.assertTrue(any(item["mappedPath"] == "assets/filtered/data/special7.lang" for item in events))
        self.assertFalse(any("specialx.lang" in item["mappedPath"] for item in events))
        self.assertFalse(any("blocked.lang" in item["mappedPath"] for item in events))
        self.assertTrue(any(item["mappedPath"] == "assets/question/data/special.lang" for item in events))
        self.assertTrue(any(item["mappedPath"] == "assets/question/data/specia.lang" for item in events))
        self.assertFalse(any(item["mappedPath"] == "assets/question/data/special7.lang" for item in events))
        self.assertTrue(any(item["mappedPath"] == "assets/prefix/data/special-case.lang" for item in events))
        self.assertFalse(any(item["mappedPath"] == "assets/prefix/data/not-special.lang" for item in events))
        self.assertTrue(any(item["mappedPath"] == "assets/nested-target/shared/data/nested.lang" for item in events))
        self.assertFalse(any("Untrusted" in item["sourceRelative"] or "/mods/" in item["sourceRelative"] for item in events))

        mapped_walk = result["mappedWalk"]
        mapped = result["mappedEvents"]
        self.assertEqual(mapped_walk["status"], "incomplete")
        self.assertTrue(any(row["sourceRelative"] == "assets/direct-file.bin"
                            and row["mappedPath"] == "assets/direct/renamed.bin" for row in mapped))
        self.assertTrue(any(row["sourceRelative"] == "assets/nested-typed/text-source.unknown"
                            and row["mappedPath"] == "assets/nested-typed/text-output.bin"
                            and row["type"] == "text" for row in mapped),
                        "nested Lime type='text' was not retained for the asset identity resolver")
        self.assertTrue(any(row["sourceRelative"] == "assets/nested-typed/binary-source.unknown"
                            and row["mappedPath"] == "assets/nested-typed/binary-output.dat"
                            and row["type"] == "binary" for row in mapped),
                        "nested Lime type='binary' was not retained for the asset identity resolver")
        self.assertTrue(any(row["sourceRelative"] == "assets/mapped-types/images/atlas.PNG"
                            and row["mappedPath"] == "assets/types/images/atlas.PNG" for row in mapped))
        self.assertTrue(any(row["sourceRelative"] == "assets/mapped-types/scripts/Effect.hx"
                            for row in mapped))
        self.assertTrue(any(row["sourceRelative"] == "assets/mapped-types/audio/theme.ogg"
                            for row in mapped))
        self.assertTrue(any(row["sourceRelative"] == "assets/mapped-types/files/resource.bundle"
                            for row in mapped))
        self.assertTrue(any(row["sourceRelative"] == "assets/escaped&source/value.dat"
                            and row["mappedPath"] == "assets/escaped&target/value.dat" for row in mapped))
        self.assertFalse(any(row["sourceRelative"].endswith("readme.hash") for row in mapped))
        self.assertIn("assets/uncertain-tree/uncertain.dat", mapped_walk["deferredSourcePaths"])
        self.assertIn("uncertain/uncertain.dat", mapped_walk["deferredOwnerPaths"])
        self.assertIn("assets/disabled-tree/disabled.dat", mapped_walk["disabledSourcePaths"])
        self.assertIn("disabled/disabled.dat", mapped_walk["disabledOwnerPaths"])
        self.assertIn("bundles/test.bundle", mapped_walk["deferredOwnerPaths"])
        self.assertTrue(mapped_walk["deferredScopeUnknown"])
        self.assertTrue(any(item["code"] == "candidate-scope-unknown"
                            for item in mapped_walk["diagnostics"]))
        self.assertEqual(mapped_walk["ambiguousOwnerPaths"], ["collision/same.dat", "collision/same.lang"])
        projections = mapped_walk["projections"]
        self.assertTrue(any(row["kind"] == "deferred"
                            and row["sourceRelative"] == "assets/uncertain-tree/uncertain.dat"
                            and row["ownerRelative"] == "uncertain/uncertain.dat"
                            and row["candidate"]["sourceRelative"] == "assets/uncertain-tree"
                            for row in projections))
        self.assertTrue(any(row["kind"] == "disabled"
                            and row["sourceRelative"] == "assets/disabled-tree/disabled.dat"
                            and row["candidate"]["state"] == "disabled"
                            for row in projections))
        self.assertEqual(sum(1 for row in projections if row["kind"] == "ambiguous"
                             and row["ownerRelative"] == "collision/same.lang"), 2)
        filtered_walk = result["filteredMappedWalk"]
        filtered = result["filteredMappedEvents"]
        self.assertTrue(all(row["sourceRelative"].lower().endswith(".lang")
                            or row["mappedPath"].lower().endswith(".lang") for row in filtered))
        self.assertIn("assets/uncertain-tree/uncertain.lang", filtered_walk["deferredSourcePaths"])
        self.assertNotIn("assets/uncertain-tree/uncertain.dat", filtered_walk["deferredSourcePaths"])
        self.assertIn("assets/disabled-tree/disabled.lang", filtered_walk["disabledSourcePaths"])
        self.assertNotIn("assets/disabled-tree/disabled.dat", filtered_walk["disabledSourcePaths"])
        self.assertIn("assets/collision-source.dat", [row["sourceRelative"] for row in filtered])
        self.assertIn("collision/same.lang", filtered_walk["ambiguousOwnerPaths"])
        self.assertEqual(result["cancelledWalk"]["status"], "cancelled")
        for row in mapped:
            data = Path(row["sourcePath"]).read_bytes()
            self.assertEqual(row["size"], len(data))
            self.assertEqual(row["sha256"], hashlib.sha256(data).hexdigest())

    def test_schema_one_snapshot_receipt_remains_receipt_bound(self):
        result, _ = self.run_profile(EXPLICIT_BUILD, legacy_schema1=True)
        self.assertEqual(result["capture"]["status"], "complete")
        self.assertEqual(result["profile"]["provenance"], "receipt-bound")
        self.assertEqual(result["profile"]["snapshotId"], result["capture"]["snapshotId"])

    def test_lime_asset_ids_follow_file_directory_and_nested_name_rules(self):
        project = '''<project>
  <assets path="assets/id-file.dat" rename="assets/identity/renamed.dat" id="logical/file-id" />
  <assets path="assets/id-directory" rename="assets/identity/directory" id="ignored-directory-id" />
  <assets path="assets/id-nested" rename="assets/identity/nested">
    <image name="icons/named.png" rename="icons/target.png" />
    <image path="icons/path.png" rename="icons/path-target.png" id="logical/path-id" />
  </assets>
</project>'''
        result, _ = self.run_profile(
            {"flags": [], "flagsComplete": True, "command": ""},
            project_text=project,
            project_files={
                "assets/id-file.dat": b"single-file",
                "assets/id-directory/child.dat": b"directory-child",
                "assets/id-nested/icons/named.png": b"nested-name",
                "assets/id-nested/icons/path.png": b"nested-path",
            },
        )
        profile = result["profile"]
        candidates = {row["sourceRelative"]: row for row in profile["candidates"]}
        self.assertEqual(candidates["assets/id-file.dat"]["assetId"], "logical/file-id")
        self.assertTrue(candidates["assets/id-file.dat"]["assetIdOverride"])
        self.assertFalse(candidates["assets/id-directory"]["assetIdOverride"])

        events = {row["sourceRelative"]: row for row in result["mappedEvents"]}
        single = events["assets/id-file.dat"]
        self.assertEqual(single["mappedPath"], "assets/identity/renamed.dat")
        self.assertEqual(single["assetId"], "logical/file-id")
        self.assertTrue(single["assetIdOverride"])

        directory_child = events["assets/id-directory/child.dat"]
        self.assertEqual(directory_child["mappedPath"], "assets/identity/directory/child.dat")
        self.assertEqual(directory_child["assetId"], directory_child["mappedPath"])
        self.assertFalse(directory_child["assetIdOverride"])

        nested_name = events["assets/id-nested/icons/named.png"]
        self.assertEqual(nested_name["mappedPath"], "assets/identity/nested/icons/target.png")
        self.assertEqual(nested_name["assetId"], "icons/named.png")
        self.assertTrue(nested_name["assetIdOverride"])

        nested_id = events["assets/id-nested/icons/path.png"]
        self.assertEqual(nested_id["mappedPath"], "assets/identity/nested/icons/path-target.png")
        self.assertEqual(nested_id["assetId"], "logical/path-id")
        self.assertTrue(nested_id["assetIdOverride"])

    def test_lime_library_load_attributes_capture_preload_embed_and_disabled_handlers(self):
        project = '''<project>
  <library name="warm" preload="true" embed="false" />
  <library name="lazy" preload="false" embed="true" />
  <library name="inactive-handler" handler="custom.Reader" if="false" />
  <assets path="assets/warm" library="warm" embed="false" />
  <assets path="assets/lazy" library="lazy" embed="false" />
</project>'''
        result, _ = self.run_profile(
            {"target": "html5", "flags": [], "flagsComplete": True, "command": ""},
            project_text=project,
            project_files={
                "assets/warm/one.txt": b"warm payload",
                "assets/lazy/two.txt": b"lazy payload",
            },
        )
        profile = result["profile"]
        self.assertTrue(profile["complete"], profile["diagnostics"])
        self.assertTrue(profile["librariesComplete"], profile["libraries"])
        libraries = {item["name"]: item for item in profile["libraries"]}
        self.assertEqual(set(libraries), {"warm", "lazy"},
                         "a disabled library handler must have no parser side effect")
        self.assertEqual(libraries["warm"]["preloadState"], "known")
        self.assertTrue(libraries["warm"]["preload"])
        self.assertFalse(libraries["warm"]["embed"])
        self.assertEqual(libraries["warm"]["embedState"], "known")
        self.assertFalse(libraries["lazy"]["preload"])
        self.assertTrue(libraries["lazy"]["embed"])
        self.assertEqual(libraries["lazy"]["generateState"], "known")
        self.assertFalse(libraries["lazy"]["generate"])
        self.assertEqual(libraries["lazy"]["prefix"], "")
        self.assertEqual({item["library"] for item in profile["candidates"]}, {"warm", "lazy"})

    def test_lime_library_unresolved_preload_is_not_defaulted(self):
        project = '''<project>
  <library name="lazy" preload="${UNKNOWN_PRELOAD}" />
  <assets path="assets/lazy" library="lazy" embed="false" />
</project>'''
        result, _ = self.run_profile(
            {"target": "html5", "flags": [], "flagsComplete": False, "command": ""},
            project_text=project,
            project_files={"assets/lazy/two.txt": b"lazy payload"},
        )
        self.assertFalse(result["profile"]["complete"], result["profile"]["libraries"])
        declaration = result["profile"]["libraries"][0]
        self.assertEqual(declaration["preloadState"], "unresolved")
        self.assertTrue(result["profile"]["librariesComplete"],
                        "known library identity remains separate from its unresolved preload value")

    def test_source_filter_skips_hashing_non_language_mapped_assets(self):
        result, _ = self.run_profile(EXPLICIT_BUILD, tamper_mapped_non_language=True)
        generic_codes = {item["code"] for item in result["mappedWalk"]["diagnostics"]}
        filtered_codes = {item["code"] for item in result["filteredMappedWalk"]["diagnostics"]}
        self.assertIn("mapped-file-hash-mismatch", generic_codes)
        self.assertNotIn("mapped-file-hash-mismatch", filtered_codes)
        self.assertIn("assets/mapped-types/scripts/Effect.hx",
                      result["mappedWalk"]["deferredSourcePaths"])
        self.assertTrue(all(row["sourceRelative"].lower().endswith(".lang")
                            or row["mappedPath"].lower().endswith(".lang")
                            for row in result["filteredMappedEvents"]))

    def test_candidate_filter_selects_typed_assets_at_arbitrary_targets(self):
        result, _ = self.run_profile(EXPLICIT_BUILD)
        typed = result["typedMappedEvents"]
        self.assertTrue(any(row["sourceRelative"] == "assets/typed-raw/raw.bin"
                            and row["mappedPath"] == "assets/nonstandard/raw.bin"
                            and row["type"] == "image" for row in typed))
        self.assertFalse(any(row["sourceRelative"].startswith("assets/mapped-types/")
                             for row in typed))
        self.assertNotIn("mapped-file-not-visited",
                         {row["code"] for row in result["typedMappedWalk"]["diagnostics"]})

    def test_missing_receipt_mapped_file_gets_deferred_projection(self):
        result, _ = self.run_profile(EXPLICIT_BUILD, delete_mapped_non_language=True)
        self.assertIn("mapped-file-not-visited",
                      {item["code"] for item in result["mappedWalk"]["diagnostics"]})
        self.assertIn("assets/mapped-types/audio/theme.ogg",
                      result["mappedWalk"]["deferredSourcePaths"])
        self.assertIn("types/audio/theme.ogg", result["mappedWalk"]["deferredOwnerPaths"])
        self.assertNotIn("assets/mapped-types/audio/theme.ogg",
                         result["filteredMappedWalk"]["deferredSourcePaths"])

    def test_missing_typed_media_file_keeps_candidate_projection(self):
        result, _ = self.run_profile(EXPLICIT_BUILD, delete_typed_mapped=True)
        projection = next(row for row in result["typedMappedWalk"]["projections"]
                          if row["sourceRelative"] == "assets/typed-raw/raw.bin")
        self.assertEqual(projection["kind"], "deferred")
        self.assertEqual(projection["ownerRelative"], "nonstandard/raw.bin")
        self.assertEqual(projection["candidate"]["type"], "image")

    def test_unresolved_target_variable_does_not_become_literal_owner_path(self):
        result, _ = self.run_profile(EXPLICIT_BUILD,
            project_text='<project><assets path="assets/typed-symbolic" '
            'rename="assets/${UNKNOWN_TARGET}" type="image" /></project>',
            project_files={"assets/typed-symbolic/icon.png": b"typed-image-bytes"})
        projection = next(row for row in result["typedMappedWalk"]["projections"]
                          if row["candidate"]["sourceRelative"] == "assets/typed-symbolic")
        self.assertEqual(projection["kind"], "deferred")
        self.assertIsNone(projection["ownerRelative"])
        self.assertTrue(result["typedMappedWalk"]["deferredScopeUnknown"])

    def test_missing_assets_root_mapping_marks_the_full_owner_scope_unknown(self):
        result, _ = self.run_profile(EXPLICIT_BUILD,
            project_text=MISSING_ASSETS_ROOT_PROJECT, omit_translation_root=True)
        walk = result["mappedWalk"]
        self.assertTrue(result["profile"]["complete"])
        self.assertEqual(walk["status"], "incomplete")
        self.assertIn("assets/translations", walk["deferredSourcePaths"])
        self.assertEqual(walk["deferredOwnerPaths"], [])
        self.assertTrue(walk["deferredScopeUnknown"])

    def test_local_project_includes_are_inline_bounded_and_add_only(self):
        project = '''<project>
  <define name="KEEP" value="parent" />
  <include path="fragments" />
  <assets path="${NEW_PATH}" rename="assets/after" />
  <assets path="assets/bare" if="FALSE_TEXT" />
  <assets path="assets/literal" if="${FALSE_TEXT}" />
</project>'''
        project_files = {
            "fragments/include.lime": '''<project>
  <set name="KEEP" value="child" />
  <define name="NEW_PATH" value="assets/from-child" />
  <define name="FALSE_TEXT" value="false" />
  <assets path="assets/included" />
  <include path="nested" />
</project>''',
            "fragments/nested/include.nmml": '''<project>
  <assets path="assets/nested" />
</project>''',
            # Lime chooses include.lime ahead of both other directory variants.
            "fragments/include.nmml": '<project><assets path="assets/wrong-nmml" /></project>',
            "fragments/include.xml": '<project><assets path="assets/wrong-xml" /></project>',
        }
        result, _ = self.run_profile(
            {"target": "fixture", "flags": [], "values": [], "flagsComplete": True, "command": ""},
            project_text=project, project_files=project_files)
        profile = result["profile"]
        self.assertEqual(profile["version"], 4)
        self.assertTrue(profile["complete"], profile["diagnostics"])
        self.assertEqual(
            [(row["sourceRelative"], row["targetRelative"], row["state"])
             for row in profile["candidates"]],
            [
                ("fragments/assets/included", "assets/included", "enabled"),
                ("fragments/nested/assets/nested", "assets/nested", "enabled"),
                ("assets/from-child", "assets/after", "enabled"),
                ("assets/bare", "assets/bare", "enabled"),
                ("assets/literal", "assets/literal", "disabled"),
            ],
        )
        inputs = profile["inputFiles"]
        self.assertEqual([row["path"] for row in inputs], [
            "nested/root/Project.xml",
            "nested/root/fragments/include.lime",
            "nested/root/fragments/nested/include.nmml",
        ])
        self.assertEqual([row["parentInclude"] for row in inputs], [
            None, "nested/root/Project.xml", "nested/root/fragments/include.lime",
        ])
        self.assertEqual([row["order"] for row in inputs], [0, 1, 2])
        for row in inputs:
            data = (Path(result["capture"]["snapshotRoot"]) / "content" / row["path"]).read_bytes()
            self.assertEqual(row["size"], len(data))
            self.assertEqual(row["sha256"], hashlib.sha256(data).hexdigest())
        self.assertRegex(profile["contextFingerprint"], r"^[0-9a-f]{64}$")
        self.assertEqual({row["name"]: row["value"] for row in profile["values"]}, {
            "FALSE_TEXT": "false", "KEEP": "parent", "NEW_PATH": "assets/from-child",
        })

    def test_explicit_project_values_resolve_asset_include_and_context_identity(self):
        project = '''<project>
  <include path="${PROJECT_FRAGMENT}" />
  <assets path="${ASSET_SOURCE}" rename="assets/mapped" />
</project>'''
        project_files = {
            "fragments/selected.xml": '<project><assets path="assets/included" /></project>',
        }
        build = {"target": "fixture", "flags": [], "values": [
            {"name": "PROJECT_FRAGMENT", "value": "fragments/selected.xml", "provenance": "fixture-build"},
            {"name": "ASSET_SOURCE", "value": "assets/selected", "provenance": "fixture-build"},
        ], "flagsComplete": True, "command": ""}
        result, _ = self.run_profile(build, project_text=project, project_files=project_files)
        profile = result["profile"]
        self.assertTrue(profile["complete"], profile["diagnostics"])
        self.assertEqual({row["name"]: row["value"] for row in profile["buildValues"]}, {
            row["name"]: row["value"] for row in build["values"]
        })
        self.assertEqual({row["name"]: row["value"] for row in profile["values"]}, {
            "ASSET_SOURCE": "assets/selected",
            "PROJECT_FRAGMENT": "fragments/selected.xml",
        })
        self.assertEqual([(row["sourceRelative"], row["targetRelative"])
                          for row in profile["candidates"]], [
                              ("fragments/assets/included", "assets/included"),
                              ("assets/selected", "assets/mapped"),
                          ])
        changed, _ = self.run_profile({**build, "values": [
            {"name": "PROJECT_FRAGMENT", "value": "fragments/other.xml", "provenance": "fixture-build"},
            build["values"][1],
        ]}, project_text=project, project_files=project_files)
        self.assertNotEqual(profile["contextFingerprint"], changed["profile"]["contextFingerprint"])

    def test_explicit_lime_command_is_distinct_from_flag_completeness_and_empty_command(self):
        project = '<project><assets path="assets/command" if="compile" /></project>'
        unknown, _ = self.run_profile({"flags": [], "flagsComplete": True}, project_text=project)
        explicit_none, _ = self.run_profile({"flags": [], "flagsComplete": True, "command": ""},
            project_text=project)
        explicit_command, _ = self.run_profile({"flags": [
            {"name": "compile", "state": "disabled"},
        ], "flagsComplete": True, "command": "compile"}, project_text=project)

        self.assertIsNone(unknown["profile"]["buildCommand"])
        self.assertEqual(unknown["profile"]["candidates"][0]["state"], "unresolved")
        self.assertEqual(explicit_none["profile"]["buildCommand"], "")
        self.assertEqual(explicit_none["profile"]["candidates"][0]["state"], "disabled")
        self.assertEqual(explicit_command["profile"]["buildCommand"], "compile")
        self.assertEqual(explicit_command["profile"]["candidates"][0]["state"], "enabled")
        self.assertEqual(len({unknown["profile"]["contextFingerprint"],
                              explicit_none["profile"]["contextFingerprint"],
                              explicit_command["profile"]["contextFingerprint"]}), 3)

    def test_include_source_paths_are_relative_to_containing_project_and_merge_add_only(self):
        project = '''<project>
  <define name="ROOT_TARGET" value="assets" />
  <include path="${PROJECT_FILE}" />
  <assets path="assets/translations" rename="${ROOT_TARGET}/after" />
</project>'''
        included = '''<project>
  <define name="ROOT_TARGET" value="assets/child-override" />
  <assets path="../assets/translations" rename="${ROOT_TARGET}/included" />
</project>'''
        build = {"target": "fixture", "flags": [], "flagsComplete": True, "command": "", "values": [
            {"name": "PROJECT_FILE", "value": "proj/include.xml", "provenance": "fixture-build"},
            {"name": "DISPLAY", "value": "Café 🎵", "provenance": "fixture-build"},
        ]}
        result, _ = self.run_profile(build, project_text=project,
            project_files={"proj/include.xml": included})
        profile = result["profile"]
        self.assertTrue(profile["complete"], profile["diagnostics"])
        self.assertEqual([(row["sourceRelative"], row["targetRelative"])
                          for row in profile["candidates"]], [
                              ("assets/translations", "assets/child-override/included"),
                              ("assets/translations", "assets/after"),
                          ])
        effective = {row["name"]: row["value"] for row in profile["values"]}
        self.assertEqual(effective["ROOT_TARGET"], "assets")
        self.assertEqual(effective["DISPLAY"], "Café 🎵")
        self.assertEqual([row["path"] for row in profile["inputFiles"]], [
            "nested/root/Project.xml", "nested/root/proj/include.xml",
        ])

    def test_missing_local_include_obeys_noerror_attribute_presence(self):
        optional, _ = self.run_profile({"flags": [], "flagsComplete": True, "command": ""}, project_text='''<project>
  <include path="missing.xml" noerror="false" />
  <assets path="assets/optional" if="KNOWN_ABSENT" />
</project>''')
        optional_profile = optional["profile"]
        self.assertTrue(optional_profile["complete"], optional_profile["diagnostics"])
        self.assertTrue(optional_profile["flagsComplete"])
        self.assertFalse(optional_profile["mappingScopeUnknown"])
        self.assertFalse(optional["mappedWalk"]["deferredScopeUnknown"])
        self.assertEqual([row["path"] for row in optional_profile["inputFiles"]], [
            "nested/root/Project.xml",
        ])
        self.assertEqual(optional_profile["candidates"][0]["state"], "disabled")

        required, _ = self.run_profile({"flags": [], "flagsComplete": True, "command": ""}, project_text='''<project>
  <include path="missing.xml" />
  <assets path="assets/required" if="KNOWN_ABSENT" />
</project>''')
        required_profile = required["profile"]
        self.assertFalse(required_profile["complete"])
        self.assertFalse(required_profile["flagsComplete"])
        self.assertTrue(required_profile["mappingScopeUnknown"])
        self.assertTrue(required["mappedWalk"]["deferredScopeUnknown"])
        self.assertEqual(required_profile["candidates"][0]["state"], "unresolved")
        self.assertIn("project-include-missing", "\n".join(required_profile["diagnostics"]))

    def test_local_include_accepts_lime_extension_wrapper(self):
        result, _ = self.run_profile({"flags": [], "flagsComplete": True, "command": ""}, project_text='''<project>
  <include path="fragment.xml" />
</project>''', project_files={
            "fragment.xml": '''<extension>
  <assets path="assets/from-extension" />
</extension>''',
        })
        profile = result["profile"]
        self.assertTrue(profile["complete"], profile["diagnostics"])
        self.assertEqual([(row["sourceRelative"], row["state"])
                          for row in profile["candidates"]], [
                              ("assets/from-extension", "enabled"),
                          ])

    def test_resolver_cancellation_survives_nested_include_catch(self):
        project = '<project><include path="child.xml" /></project>'
        child = "<extension>" + "".join(
            f'<assets path="assets/item-{index}" />' for index in range(20)
        ) + "</extension>"
        result, _ = self.run_profile({"flags": [], "flagsComplete": True, "command": ""},
            project_text=project, project_files={"child.xml": child}, cancel_after=11)
        self.assertIsNotNone(result["resolverCancellation"])
        self.assertTrue(result["resolverCancellation"]["caught"], result["resolverCancellation"])
        self.assertGreaterEqual(result["resolverCancellation"]["checks"], 11)

    def test_project_asset_metadata_interpolates_and_disabled_assets_stay_side_effect_free(self):
        project = '''<project>
  <assets path="${ASSET_SOURCE}" rename="assets/resolved" type="${ASSET_TYPE}"
    embed="${ASSET_EMBED}" library="${ASSET_LIBRARY}" />
  <assets path="assets/unknown-type" type="${MISSING_TYPE}" />
  <assets path="assets/unknown-embed" embed="${MISSING_EMBED}" />
  <assets path="assets/unknown-library" library="${MISSING_LIBRARY}" />
  <assets path="assets/nested" type="${BASE_TYPE}" embed="${BASE_EMBED}"
    library="${BASE_LIBRARY}">
    <asset name="child" type="${CHILD_TYPE}" embed="${CHILD_EMBED}"
      library="${CHILD_LIBRARY}" />
  </assets>
  <assets path="assets/disabled" type="${MISSING_TYPE}" embed="${MISSING_EMBED}"
    library="${MISSING_LIBRARY}" include="${MISSING_FILTER}" if="false" />
  <import path="${MISSING_IMPORT}" if="false" />
</project>'''
        build = {"flags": [], "flagsComplete": False, "values": [
            {"name": "ASSET_SOURCE", "value": "assets/source"},
            {"name": "ASSET_TYPE", "value": "image"},
            {"name": "ASSET_EMBED", "value": "true"},
            {"name": "ASSET_LIBRARY", "value": "fixture"},
            {"name": "BASE_TYPE", "value": "binary"},
            {"name": "BASE_EMBED", "value": "false"},
            {"name": "BASE_LIBRARY", "value": "base"},
            {"name": "CHILD_TYPE", "value": "font"},
            {"name": "CHILD_EMBED", "value": "true"},
            {"name": "CHILD_LIBRARY", "value": "child"},
        ]}
        result, _ = self.run_profile(build, project_text=project)
        profile = result["profile"]
        self.assertFalse(profile["complete"])
        candidates = {row["sourceRelative"]: row for row in profile["candidates"]}
        resolved = candidates["assets/source"]
        self.assertEqual((resolved["type"], resolved["embed"], resolved["library"], resolved["state"]),
                         ("image", "true", "fixture", "enabled"))
        nested = candidates["assets/nested/child"]
        self.assertEqual((nested["type"], nested["embed"], nested["library"], nested["state"]),
                         ("font", "true", "child", "enabled"))
        nested_event = next(row for row in result["mappedEvents"]
                            if row["mappedPath"] == "assets/nested/child/metadata.bin")
        self.assertEqual((nested_event["type"], nested_event["embed"], nested_event["library"]),
                         ("font", "true", "child"))
        for suffix in ("unknown-type", "unknown-embed", "unknown-library"):
            self.assertEqual(candidates["assets/" + suffix]["state"], "unresolved")
        self.assertEqual(candidates["assets/disabled"]["state"], "disabled")
        self.assertFalse(any("MISSING_FILTER" in item or "MISSING_IMPORT" in item
                             for item in profile["diagnostics"]))

    def test_only_setenv_interpolates_assignment_names(self):
        build = {"flags": [], "flagsComplete": True, "command": "", "values": [
            {"name": "DYNAMIC_NAME", "value": "EXPANDED_NAME"},
        ]}
        literal, _ = self.run_profile(build, project_text='''<project>
  <set name="${DYNAMIC_NAME}" value="from-set" />
  <assets path="assets/set-name" if="EXPANDED_NAME" />
</project>''')
        literal_profile = literal["profile"]
        self.assertEqual(literal_profile["candidates"][0]["state"], "unresolved")
        self.assertFalse(literal_profile["complete"])

        interpolated, _ = self.run_profile(build, project_text='''<project>
  <setenv name="${DYNAMIC_NAME}" value="from-setenv" />
  <assets path="assets/setenv-name" if="EXPANDED_NAME" />
</project>''')
        interp_profile = interpolated["profile"]
        self.assertEqual(interp_profile["candidates"][0]["state"], "enabled")
        self.assertEqual({row["name"]: row["value"] for row in interp_profile["values"]}[
            "EXPANDED_NAME"], "from-setenv")

    def test_define_and_removal_names_remain_literal(self):
        result, _ = self.run_profile({"flags": [], "flagsComplete": True, "command": "", "values": [
            {"name": "DYNAMIC_NAME", "value": "EXPANDED_NAME"},
            {"name": "DYNAMIC_OTHER", "value": "OTHER_NAME"},
        ]}, project_text='''<project>
  <define name="${DYNAMIC_NAME}" value="from-define" />
  <assets path="assets/define-name" if="EXPANDED_NAME" />
  <unset name="${DYNAMIC_NAME}" />
  <assets path="assets/unset-name" if="EXPANDED_NAME" />
  <undefine name="${DYNAMIC_OTHER}" />
  <assets path="assets/undefine-name" if="OTHER_NAME" />
</project>''')
        profile = result["profile"]
        states = {row["sourceRelative"]: row["state"] for row in profile["candidates"]}
        self.assertEqual(states, {
            "assets/define-name": "unresolved",
            "assets/unset-name": "unresolved",
            "assets/undefine-name": "unresolved",
        })
        self.assertFalse(profile["complete"])

    def test_unknown_include_branch_is_unresolved_and_does_not_merge_defines(self):
        project = '''<project>
  <include path="optional.xml" if="UNKNOWN_FEATURE" />
  <assets path="assets/after" if="FROM_OPTIONAL" />
</project>'''
        project_files = {
            "optional.xml": '''<project>
  <define name="FROM_OPTIONAL" />
  <assets path="assets/optional" />
</project>''',
        }
        result, _ = self.run_profile({"target": "fixture", "flagsComplete": True, "command": "",
            "flags": [{"name": "UNKNOWN_FEATURE", "state": "unresolved"}]},
            project_text=project, project_files=project_files)
        profile = result["profile"]
        self.assertFalse(profile["complete"])
        self.assertEqual([(row["sourceRelative"], row["state"])
                          for row in profile["candidates"]], [
                              ("assets/optional", "unresolved"),
                              ("assets/after", "unresolved"),
                          ])
        self.assertTrue(any("unresolved-project-condition" in item
                            for item in profile["diagnostics"]))

    def test_project_context_definition_order_value_unknown_and_complete_absence(self):
        project = '''<project>
  <define name="VALUE_KNOWN" value="${UNCAPTURED_VALUE}" />
  <assets path="assets/presence" if="VALUE_KNOWN" />
  <assets path="assets/string" if="${VALUE_KNOWN}" />
  <define name="RESET_ME" />
  <assets path="assets/before-reset" if="RESET_ME" />
  <undefine name="RESET_ME" />
  <assets path="assets/after-reset" if="RESET_ME" />
  <setenv name="ENV_PRESENT" />
  <assets path="assets/setenv" if="ENV_PRESENT" />
  <haxedef name="COMPILER_ONLY" />
  <assets path="assets/haxedef" if="COMPILER_ONLY" />
</project>'''
        result, _ = self.run_profile({"flags": [
            {"name": "UNCAPTURED_VALUE", "state": "unresolved"},
        ], "flagsComplete": True, "command": ""}, project_text=project)
        profile = result["profile"]
        candidates = {row["sourceRelative"]: row["state"] for row in profile["candidates"]}
        self.assertEqual(candidates, {
            "assets/presence": "enabled",
            "assets/string": "unresolved",
            "assets/before-reset": "enabled",
            "assets/after-reset": "disabled",
            "assets/setenv": "enabled",
            "assets/haxedef": "disabled",
        })
        self.assertFalse(profile["complete"])
        self.assertTrue(any("undefine-haxedef RESET_ME" in item
                            for item in profile["opaqueBuildInputs"]))
        self.assertNotIn("COMPILER_ONLY", {row["name"] for row in profile["values"]})

    def test_combined_include_file_depth_and_node_limits_are_reported(self):
        root = [f'<include path="part-{index}.xml" />' for index in range(64)]
        project_files = {f"part-{index}.xml": "<project />" for index in range(64)}
        file_limit, _ = self.run_profile({"flags": [], "flagsComplete": True, "command": ""},
            project_text="<project>" + "".join(root) + "</project>", project_files=project_files)
        self.assertFalse(file_limit["profile"]["complete"])
        self.assertIn("project-include-file-limit",
                      "\n".join(file_limit["profile"]["diagnostics"]))
        self.assertEqual(len(file_limit["profile"]["inputFiles"]), 64)

        chain_files = {}
        for index in range(40):
            target = f'<include path="chain-{index + 1}.xml" />' if index < 39 else ""
            chain_files[f"chain-{index}.xml"] = f"<project>{target}</project>"
        depth_limit, _ = self.run_profile({"flags": [], "flagsComplete": True, "command": ""},
            project_text='<project><include path="chain-0.xml" /></project>',
            project_files=chain_files)
        self.assertFalse(depth_limit["profile"]["complete"])
        self.assertIn("project-include-depth-limit",
                      "\n".join(depth_limit["profile"]["diagnostics"]))

        node_child = "<project>" + "<ignored/>" * 8400 + "</project>"
        node_root = '<project><include path="nodes.xml" />' + "<ignored/>" * 8400 + "</project>"
        node_limit, _ = self.run_profile({"flags": [], "flagsComplete": True, "command": ""},
            project_text=node_root, project_files={"nodes.xml": node_child})
        self.assertFalse(node_limit["profile"]["complete"])
        self.assertIn("project-xml-node-limit",
                      "\n".join(node_limit["profile"]["diagnostics"]))

    def test_disabled_include_is_not_opened_and_repeated_include_replays_with_parent_context(self):
        disabled, _ = self.run_profile({"flags": []}, project_text=
            '<project><include path="missing" if="false" /><assets path="assets/ok" /></project>')
        self.assertTrue(disabled["profile"]["complete"], disabled["profile"]["diagnostics"])
        self.assertEqual(disabled["profile"]["inputFiles"], [
            {"path": "nested/root/Project.xml", "size": len(
                b'<project><include path="missing" if="false" /><assets path="assets/ok" /></project>'),
             "sha256": hashlib.sha256(
                 b'<project><include path="missing" if="false" /><assets path="assets/ok" /></project>'
             ).hexdigest(), "parentInclude": None, "order": 0},
        ])

        repeated = '''<project>
  <set name="TARGET" value="assets/first" />
  <include path="parts/common.xml" />
  <set name="TARGET" value="assets/second" />
  <include path="parts/../parts/common.xml" />
</project>'''
        repeat_result, _ = self.run_profile({"flags": [], "flagsComplete": True, "command": ""}, project_text=repeated,
            project_files={"parts/common.xml": '<project><assets path="assets/source" rename="${TARGET}/language" /></project>'})
        repeat_profile = repeat_result["profile"]
        self.assertTrue(repeat_profile["complete"], repeat_profile["diagnostics"])
        self.assertEqual([(row["sourceRelative"], row["targetRelative"])
                          for row in repeat_profile["candidates"]], [
                              ("parts/assets/source", "assets/first/language"),
                              ("parts/assets/source", "assets/second/language"),
                          ])
        self.assertEqual([row["path"] for row in repeat_profile["inputFiles"]], [
            "nested/root/Project.xml", "nested/root/parts/common.xml", "nested/root/parts/common.xml",
        ])

    def test_include_cycles_escapes_receipt_failures_and_value_conflicts_fail_closed(self):
        cycle_result, _ = self.run_profile({"flags": []}, project_text=
            '<project><include path="one.xml" /></project>', project_files={
                "one.xml": '<project><include path="./one.xml" /></project>',
            })
        self.assertFalse(cycle_result["profile"]["complete"])
        self.assertIn("include-cycle", "\n".join(cycle_result["profile"]["diagnostics"]))

        escape_result, _ = self.run_profile({"flags": []}, project_text=
            '<project><include path="../../other/root/Project.xml" /></project>')
        self.assertFalse(escape_result["profile"]["complete"])
        self.assertIn("unsafe-project-include", "\n".join(escape_result["profile"]["diagnostics"]))

        tampered, _ = self.run_profile({"flags": []}, project_text=
            '<project><include path="child.xml" /></project>',
            project_files={"child.xml": '<project><assets path="assets/child" /></project>'},
            tamper_included_project="child.xml")
        self.assertEqual(tampered["profile"]["provenance"], "invalid")
        self.assertIn("project-include-hash-mismatch", "\n".join(tampered["profile"]["diagnostics"]))

        conflict, _ = self.run_profile({"flags": [
            {"name": "ASSET_SOURCE", "state": "unresolved"},
        ], "values": [{"name": "ASSET_SOURCE", "value": "assets/source"}]},
            project_text='<project><assets path="${ASSET_SOURCE}" /></project>')
        self.assertEqual(conflict["profile"]["provenance"], "invalid")
        self.assertIn("build-context-value-conflict", "\n".join(conflict["profile"]["diagnostics"]))

    def test_lime_library_declarations_keep_empty_names_and_uncertainty(self):
        project = '''<project>
  <library name="EmptyLibrary" />
  <library id="ExplicitId" path="native/libsample.a" />
  <library name="DisabledLibrary" if="OFF" />
  <library name="${UNKNOWN_LIBRARY}" />
  <library type="sample" handler="ExampleHandler" />
  <assets path="assets/identity" library="asset-partition" />
</project>'''
        result, _ = self.run_profile({
            "flags": [{"name": "OFF", "state": "disabled", "provenance": "fixture"}],
            "flagsComplete": False, "command": "",
        }, project_text=project, project_files={"assets/identity/example.txt": b"identity"})
        profile = result["profile"]
        libraries = profile["libraries"]
        self.assertEqual([(row["name"], row["state"], row["sourcePath"]) for row in libraries], [
            ("EmptyLibrary", "enabled", ""),
            ("ExplicitId", "enabled", "native/libsample.a"),
            ("DisabledLibrary", "disabled", ""),
            ("${UNKNOWN_LIBRARY}", "unresolved", ""),
        ])
        self.assertFalse(profile["librariesComplete"], "unknown names and dynamic handlers must not claim a complete library table")
        self.assertFalse(profile["complete"])
        self.assertEqual(profile["candidates"][0]["library"], "asset-partition")
        self.assertTrue(any("unresolved-library-handler" in item for item in profile["diagnostics"]))

    def test_target_label_does_not_resolve_missing_build_flags(self):
        result, _ = self.run_profile({"target": "windows", "flags": []})
        profile = result["profile"]
        self.assertEqual(profile["buildTarget"], "windows")
        self.assertEqual(profile["flags"], [])
        candidates = {item["sourceRelative"]: item for item in profile["candidates"]}
        self.assertEqual(candidates["assets/videos"]["state"], "unresolved")
        self.assertEqual(candidates["assets/base_game"]["state"], "unresolved")
        self.assertEqual(candidates["assets/translations"]["state"], "unresolved")
        self.assertFalse(profile["complete"])

    def test_pinned_donor_declaration_order_across_known_contexts(self):
        pairs = [
            ("assets/fonts", "assets/fonts"),
            ("assets/shared", "assets/shared"),
            ("assets/shared", "assets/shared"),
            ("assets/embed", "assets/embed"),
            ("assets/embed", "assets/embed"),
            ("assets/videos", "assets/videos"),
            ("assets/songs", "assets/songs"),
            ("assets/songs", "assets/songs"),
            ("assets/week_assets", "assets"),
            ("assets/week_assets", "assets"),
            ("assets/secrets", "assets/shared"),
            ("assets/secrets", "assets/shared"),
            ("assets/translations", "assets"),
            ("assets/translations", "assets"),
            ("assets/base_game", "assets"),
            ("assets/base_game", "assets"),
            ("example_mods", "mods"),
            ("example_mods", "mods"),
            ("list.txt", "modsList.txt"),
            ("art/readme.txt", "do NOT readme.txt"),
            ("alsoft.txt", "plugins/alsoft.ini"),
            ("alsoft.txt", "plugins/alsoft.conf"),
        ]

        def build(target, **states):
            return {"target": target, "flags": [
                {"name": name, "state": state, "provenance": "matrix-input"}
                for name, state in states.items()
            ], "flagsComplete": True, "command": ""}

        contexts = [
            ("Windows official 64-bit", build("windows", windows="enabled", linux="disabled",
                android="disabled", mac="disabled", **{"32bits": "disabled"}, web="disabled",
                desktop="enabled", officialBuild="enabled", html5="disabled", mobile="disabled"),
             ["enabled", "disabled", "enabled", "disabled", "enabled", "enabled", "disabled",
              "enabled", "disabled", "enabled", "disabled", "enabled", "disabled", "enabled",
              "disabled", "enabled", "enabled", "disabled", "enabled", "enabled", "enabled", "disabled"]),
            ("Windows nonofficial 64-bit", build("windows", windows="enabled", linux="disabled",
                android="disabled", mac="disabled", **{"32bits": "disabled"}, web="disabled",
                desktop="enabled", officialBuild="disabled", BASE_GAME_FILES="disabled",
                TITLE_SCREEN_EASTER_EGG="disabled", VIDEOS_ALLOWED="disabled",
                MODS_ALLOWED="disabled", html5="disabled", mobile="disabled"),
             ["enabled", "disabled", "enabled", "disabled", "enabled", "disabled", "disabled",
              "enabled", "disabled", "enabled", "disabled", "disabled", "disabled", "enabled",
              "disabled", "disabled", "enabled", "disabled", "enabled", "enabled", "enabled", "disabled"]),
            ("web", build("html5", web="enabled", desktop="disabled", windows="disabled",
                linux="disabled", android="disabled", mac="disabled", officialBuild="disabled",
                **{"32bits": "disabled"}, BASE_GAME_FILES="disabled",
                TITLE_SCREEN_EASTER_EGG="disabled", VIDEOS_ALLOWED="disabled",
                MODS_ALLOWED="disabled", html5="enabled", mobile="disabled"),
             ["enabled", "enabled", "disabled", "enabled", "disabled", "disabled", "enabled",
              "disabled", "enabled", "disabled", "disabled", "disabled", "enabled", "disabled",
              "disabled", "disabled", "disabled", "disabled", "disabled", "enabled", "disabled", "disabled"]),
        ]

        for label, context, states in contexts:
            with self.subTest(context=label):
                result, _ = self.run_profile(context, project_text=PINNED_DONOR_PROJECT_SLICE)
                profile = result["profile"]
                self.assertTrue(profile["complete"], profile["diagnostics"])
                candidates = profile["candidates"]
                self.assertEqual([(item["sourceRelative"], item["targetRelative"])
                                  for item in candidates], pairs)
                self.assertEqual([item["state"] for item in candidates], states)
                self.assertEqual(result["walk"]["files"], 5)
                self.assertEqual([item["ownerRelative"] for item in result["events"]], [
                    "data/en-US.lang", "base_game/week1/data/en-US.lang",
                    "library/alternate/data/en-US.lang", "shared/data/en-US.lang",
                    "week1/data/en-US.lang",
                ])

        missing, _ = self.run_profile({"target": "windows", "flags": []},
                                      project_text=PINNED_DONOR_PROJECT_SLICE)
        self.assertFalse(missing["profile"]["complete"])
        self.assertEqual(missing["profile"]["buildTarget"], "windows")
        self.assertEqual([item["state"] for item in missing["profile"]["candidates"]], [
            "enabled", "unresolved", "unresolved", "unresolved", "unresolved", "unresolved",
            "unresolved", "unresolved", "unresolved", "unresolved", "unresolved", "unresolved",
            "unresolved", "unresolved", "unresolved", "unresolved", "unresolved", "unresolved",
            "unresolved", "enabled", "unresolved", "unresolved",
        ])
        self.assertEqual(missing["events"], [])

    def test_receipt_binding_rejects_project_tampering_and_unverified_walks(self):
        result, _ = self.run_profile(EXPLICIT_BUILD, tamper_project=True)
        self.assertEqual(result["profile"]["provenance"], "invalid")
        self.assertTrue(any("project-hash-mismatch" in item for item in result["profile"]["diagnostics"]))
        self.assertEqual(result["badRoot"]["provenance"], "invalid")
        self.assertTrue(any("invalid-root-relative" in item for item in result["badRoot"]["diagnostics"]))
        self.assertEqual(result["unverified"]["provenance"], "legacy-unverified")
        self.assertEqual(result["unverifiedWalk"]["status"], "incomplete")
        self.assertEqual(result["unverifiedWalk"]["files"], 0)

    def test_language_bytes_are_rechecked_against_the_snapshot_receipt(self):
        result, _ = self.run_profile(EXPLICIT_BUILD, tamper_language=True)
        self.assertEqual(result["profile"]["provenance"], "receipt-bound")
        self.assertEqual(result["walk"]["status"], "incomplete")
        self.assertTrue(any(item["code"] == "language-file-hash-mismatch"
                            for item in result["walk"]["diagnostics"]))
        self.assertFalse(any(item["sourceRelative"] == "assets/translations/data/en-US.lang"
                             for item in result["events"]))


if __name__ == "__main__":
    unittest.main()
