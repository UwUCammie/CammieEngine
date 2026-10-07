"""Portable-Haxe tests for three-way shared registry refreshes."""
from haxe_test_support import HAXE_COMMAND

import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
TJSON = ROOT / ".haxelib/tjson/1,4,0"

FIXTURE = r'''import haxe.Json;
import sys.io.File;

class ImportRegistryRefreshFixture {
  static function main():Void {
    var spec:Dynamic = Json.parse(File.getContent(Sys.args()[0]));
    var result = if (spec.mode == "prepare")
      ImportRegistryRefresh.prepare(spec.before, spec.generated, spec.live)
    else if (spec.mode == "seed")
      ImportRegistryRefresh.regenerationSeed(spec.before, spec.generated, spec.live)
    else
      ImportRegistryRefresh.merge(spec.before, spec.generated, spec.live);
    Sys.println(Json.stringify({text: result.text, conflicts: result.conflicts}));
  }
}
'''


class ImportRegistryRefreshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAXE.is_file() or not TJSON.is_dir():
            raise unittest.SkipTest("portable Haxe or pinned TJSON is unavailable")
        cls.native_fixture = None
        if os.name == "nt":
            from windows_native_import_fixture import NativeFixtureUnavailable, get_native_fixture
            try:
                cls.native_fixture = get_native_fixture()
            except NativeFixtureUnavailable:
                cls.native_fixture = None

    def run_merge(self, mode: str, before: str, generated: str, live: str) -> dict:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder_name:
            folder = Path(folder_name)
            output_path = None
            merged_text = None
            if self.native_fixture is not None:
                before_path = folder / "before.json"
                generated_path = folder / "generated.json"
                live_path = folder / "live.json"
                output_path = folder / "merged.json"
                before_path.write_text(before, encoding="utf-8", newline="\n")
                generated_path.write_text(generated, encoding="utf-8", newline="\n")
                live_path.write_text(live, encoding="utf-8", newline="\n")
                command = [str(self.native_fixture.executable), "registry-refresh", mode,
                           str(before_path), str(generated_path), str(live_path), str(output_path)]
                environment = self.native_fixture.environment
            else:
                fixture = folder / "ImportRegistryRefreshFixture.hx"
                fixture.write_text(FIXTURE, encoding="utf-8", newline="\n")
                spec = folder / "registry-case.json"
                spec.write_text(json.dumps({"mode": mode, "before": before,
                                           "generated": generated, "live": live}),
                                encoding="utf-8", newline="\n")
                command = [*HAXE_COMMAND, "-cp", str(folder), "-cp", str(ROOT / "source"),
                           "-cp", str(TJSON), "--run", "ImportRegistryRefreshFixture", str(spec)]
                environment = {**os.environ, "TMPDIR": str(ROOT / "tmp")}
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,
            )
            if output_path is not None:
                merged_text = output_path.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        response = json.loads(result.stdout.strip().splitlines()[-1])
        if merged_text is not None:
            response["text"] = merged_text
        return response

    @staticmethod
    def parsed(text: str) -> dict:
        return json.loads(text)

    def test_prepare_reverts_previous_import_changes_and_keeps_unrelated_live_values(self):
        before = '''{
          // This JSONC baseline predates the package import.
          "songs": {"imported": {"title": "old", "enabled": true}, "local": "base",},
          "list": ["base", "removed",],
          "removeMe": "baseline",
        }'''
        previous = '''{"songs":{"imported":{"title":"new","enabled":true,"added":3},
          "local":"base"},"list":["base"],"removeMe":"baseline"}'''
        live = '''{"songs":{"imported":{"title":"new","enabled":true,"added":3,"user":"keep"},
          "local":"local edit"},"list":["base","user-item"],"removeMe":"baseline","extra":9}'''

        result = self.run_merge("prepare", before, previous, live)

        self.assertEqual(result["conflicts"], [])
        merged = self.parsed(result["text"])
        self.assertEqual(merged["songs"]["imported"], {
            "title": "old", "enabled": True, "user": "keep"})
        self.assertEqual(merged["songs"]["local"], "local edit")
        self.assertEqual(merged["list"], ["base", "removed", "user-item"])
        self.assertEqual(merged["removeMe"], "baseline")
        self.assertEqual(merged["extra"], 9)

    def test_regeneration_seed_resets_owned_edits_and_preserves_other_live_entries(self):
        before = '''{
          "entries": [{"name":"itemA","display":"Original","stable":"base"}],
          "localSetting": "base"
        }'''
        previous = '''{
          "entries": [
            {"name":"itemA","display":"Generated old","stable":"base","ownerField":"old"},
            {"name":"removedOwned","display":"Generated old"}
          ],
          "localSetting": "base"
        }'''
        # The live source already contains the converter's new display text.
        # The seed must still reset it to the source baseline so conversion can
        # run again, while retaining unrelated edits and another owner's row.
        live = '''{
          "entries": [
            {"name":"itemA","display":"Generated current","stable":"base",
             "ownerField":"current","userField":"keep"},
            {"name":"removedOwned","display":"Locally changed"},
            {"name":"userB","display":"Local row"}
          ],
          "localSetting": "local edit",
          "userSetting": true
        }'''

        result = self.run_merge("seed", before, previous, live)

        self.assertEqual(result["conflicts"], [])
        merged = self.parsed(result["text"])
        self.assertEqual(merged["entries"], [
            {"name":"itemA", "display":"Original", "stable":"base", "userField":"keep"},
            {"name":"userB", "display":"Local row"},
        ])
        self.assertEqual(merged["localSetting"], "local edit")
        self.assertTrue(merged["userSetting"])

    def test_regeneration_seed_keeps_foreign_nested_rows_when_removing_owned_container(self):
        before = "[]"
        previous = '''[{"name":"sharedGroup","title":"Generated title","songs":[
          {"name":"ownerSong","version":"Generated old"}
        ]}]'''
        live = '''[{"name":"sharedGroup","title":"Local title","songs":[
          {"name":"ownerSong","version":"Generated current"},
          {"name":"foreignSong","version":"Other owner"}
        ]}]'''

        result = self.run_merge("seed", before, previous, live)

        self.assertEqual(result["conflicts"], [])
        self.assertEqual(self.parsed(result["text"]), [{
            "name": "sharedGroup",
            "songs": [{"name": "foreignSong", "version": "Other owner"}],
        }])

    def test_merge_accepts_already_regenerated_value_but_rejects_a_divergent_edit(self):
        before = '''{"entries":[{"name":"itemA","display":"Original"}]}'''
        previous = '''{"entries":[{"name":"itemA","display":"Generated old"}]}'''
        generated = '''{"entries":[{"name":"itemA","display":"Generated current"}]}'''
        already_regenerated = '''{"entries":[
          {"name":"itemA","display":"Generated current"},
          {"name":"userB","display":"Local row"}
        ]}'''

        accepted = self.run_merge("merge", previous, generated, already_regenerated)

        self.assertEqual(accepted["conflicts"], [])
        self.assertEqual(self.parsed(accepted["text"]), self.parsed(already_regenerated))

        locally_edited = '''{"entries":[
          {"name":"itemA","display":"Manual edit"},
          {"name":"userB","display":"Local row"}
        ]}'''
        rejected = self.run_merge("merge", previous, generated, locally_edited)

        self.assertTrue(any("display" in item for item in rejected["conflicts"]), rejected)
        self.assertEqual(self.parsed(rejected["text"]), self.parsed(locally_edited))

    def test_prepare_preserves_and_reports_edited_imported_values_and_local_deletions(self):
        before = '{"nested":{"changed":"old"},"added":"baseline"}'
        previous = '{"nested":{"changed":"new","addedByImport":"yes"},"added":"baseline"}'
        live = '{"nested":{"changed":"local edit"}}'

        result = self.run_merge("prepare", before, previous, live)

        merged = self.parsed(result["text"])
        self.assertEqual(merged, {"nested": {"changed": "local edit"}})
        self.assertTrue(any("nested.changed" in item for item in result["conflicts"]))
        self.assertTrue(any("nested.addedByImport" in item for item in result["conflicts"]))

    def test_merge_applies_changed_leaves_and_array_appends_while_preserving_local_edits(self):
        before = '''{
          "stage":{"existing":"old","unchanged":true},
          "list":["a","b",],
          "local":"base",
        }'''
        generated = '''{"stage":{"existing":"new","unchanged":true,"introduced":5},
          "list":["a","b","engine"],"local":"base"}'''
        live = '''{"stage":{"existing":"old","unchanged":true,"user":"keep"},
          "list":["a","local-item"],"local":"local edit","other":"preserve"}'''

        result = self.run_merge("merge", before, generated, live)

        self.assertEqual(len(result["conflicts"]), 1)
        self.assertIn("list", result["conflicts"][0])
        merged = self.parsed(result["text"])
        self.assertEqual(merged["stage"], {
            "existing": "new", "unchanged": True, "user": "keep", "introduced": 5})
        self.assertEqual(merged["list"], ["a", "engine", "local-item"])
        self.assertEqual(merged["local"], "local edit")
        self.assertEqual(merged["other"], "preserve")

    def test_merge_conflicts_on_diverged_imported_leaf_and_conservatively_handles_reordered_arrays(self):
        before = '{"setting":"base","order":["a","b","c"]}'
        generated = '{"setting":"generated","order":["b","a","c"]}'
        live = '{"setting":"user edit","order":["a","b","c","local"]}'

        result = self.run_merge("merge", before, generated, live)

        merged = self.parsed(result["text"])
        self.assertEqual(merged, {"setting": "user edit", "order": ["a", "b", "c", "local"]})
        self.assertTrue(any("setting" in item for item in result["conflicts"]))
        self.assertTrue(any("order" in item for item in result["conflicts"]))

    def test_unchanged_live_jsonc_is_returned_byte_for_byte(self):
        text = '{\n  // keep comment\n  "values": ["a",],\n}\n'
        result = self.run_merge("merge", text, text, text)
        self.assertEqual(result["text"], text)
        self.assertEqual(result["conflicts"], [])

    def test_astral_keys_and_values_survive_strict_json_reconciliation(self):
        before = r'''{"base":{"literal-🎵":"Café 🎵","\ud83c\udfb5-key":"literal 🎵",
          "escaped-value":"\ud83c\udfb5"},"groups":[]}'''
        generated = r'''{"base":{"literal-🎵":"Café 🎵","\ud83c\udfb5-key":"literal 🎵",
          "escaped-value":"\ud83c\udfb5"},"groups":[{"name":"🎵"}]}'''

        result = self.run_merge("merge", before, generated, before)

        self.assertEqual(result["conflicts"], [])
        merged = self.parsed(result["text"])
        self.assertEqual(merged["base"]["literal-🎵"], "Café 🎵")
        self.assertEqual(merged["base"]["🎵-key"], "literal 🎵")
        self.assertEqual(merged["base"]["escaped-value"], "🎵")
        self.assertEqual(merged["groups"], [{"name": "🎵"}])

    def test_astral_keys_and_values_survive_jsonc_reconciliation(self):
        before = r'''{
          // literal and escaped astral key/value coverage
          "base":{"literal-🎵":"Café 🎵","\ud83c\udfb5-key":"literal 🎵",
            "escaped-value":"\ud83c\udfb5",},
          "groups":[],
        }
        '''
        generated = r'''{
          // parser accepts comments and trailing commas before serialization
          "base":{"literal-🎵":"Café 🎵","\ud83c\udfb5-key":"literal 🎵",
            "escaped-value":"\ud83c\udfb5",},
          "groups":[{"name":"🎵",}],
        }
        '''

        result = self.run_merge("merge", before, generated, before)

        self.assertEqual(result["conflicts"], [])
        merged = self.parsed(result["text"])
        self.assertEqual(merged["base"]["literal-🎵"], "Café 🎵")
        self.assertEqual(merged["base"]["🎵-key"], "literal 🎵")
        self.assertEqual(merged["base"]["escaped-value"], "🎵")
        self.assertEqual(merged["groups"], [{"name": "🎵"}])

    def test_astral_unchanged_fast_path_and_user_edit_conflict_keep_original_text(self):
        unchanged = r'''{
          // retain this JSONC byte-for-byte
          "base":{"🎵-key":"Café 🎵","escaped":"\ud83c\udfb5"},
          "owned":"old",
        }
        '''
        unchanged_result = self.run_merge("merge", unchanged, unchanged, unchanged)
        self.assertEqual(unchanged_result["text"], unchanged)
        self.assertEqual(unchanged_result["conflicts"], [])

        before = r'''{"base":{"🎵-key":"Café 🎵"},"owned":"old"}'''
        generated = r'''{"base":{"🎵-key":"Café 🎵"},"owned":"new"}'''
        user_edit = r'''{"base":{"🎵-key":"Café 🎵"},"owned":"local edit"}'''
        conflict = self.run_merge("merge", before, generated, user_edit)
        self.assertTrue(any("owned" in item for item in conflict["conflicts"]))
        self.assertEqual(conflict["text"], user_edit)

    def test_merge_keyed_freeplay_arrays_keeps_concurrent_category_and_song_additions(self):
        before = '''[
          {"name":"All","songs":[{"name":"base-song","character":"dad"}]},
          {"name":"Weeks","songs":[]}
        ]'''
        generated = '''[
          {"name":"All","songs":[
            {"name":"base-song","character":"dad"},
            {"name":"engine-song","character":"bf"}]},
          {"name":"Weeks","songs":[]}
        ]'''
        live = '''[
          {"name":"All","songs":[
            {"name":"base-song","character":"dad"},
            {"name":"user-song","character":"gf"}]},
          {"name":"Weeks","songs":[]},
          {"name":"Local category","songs":[]}
        ]'''

        result = self.run_merge("merge", before, generated, live)

        self.assertEqual(result["conflicts"], [])
        merged = self.parsed(result["text"])
        self.assertEqual([entry["name"] for entry in merged], ["All", "Weeks", "Local category"])
        all_songs = next(entry["songs"] for entry in merged if entry["name"] == "All")
        self.assertEqual([entry["name"] for entry in all_songs], ["base-song", "engine-song", "user-song"])

    def test_prepare_keyed_arrays_removes_only_previous_imported_entry(self):
        before = '''[{"name":"All","songs":[{"name":"base-song","character":"dad"}]}]'''
        previous = '''[{"name":"All","songs":[
          {"name":"base-song","character":"dad"},
          {"name":"old-import","character":"bf"}]}]'''
        live = '''[{"name":"All","songs":[
          {"name":"base-song","character":"dad"},
          {"name":"old-import","character":"bf"},
          {"name":"other-import","character":"gf"},
          {"name":"user-song","character":"spooky"}]}]'''

        result = self.run_merge("prepare", before, previous, live)

        self.assertEqual(result["conflicts"], [])
        merged = self.parsed(result["text"])
        songs = merged[0]["songs"]
        self.assertEqual([entry["name"] for entry in songs], ["base-song", "other-import", "user-song"])

    def test_prepare_removes_new_group_contribution_but_keeps_other_owners_children(self):
        before = '[]'
        previous = '''[{"name":"Imported","title":"Imported songs","songs":[
          {"name":"song-a","character":"bf"}]}]'''
        live = '''[{"name":"Imported","title":"Imported songs","songs":[
          {"name":"song-a","character":"bf"},
          {"name":"song-b","character":"gf"}]}]'''

        result = self.run_merge("prepare", before, previous, live)

        self.assertEqual(result["conflicts"], [])
        merged = self.parsed(result["text"])
        self.assertEqual(merged, [{
            "name": "Imported", "title": "Imported songs",
            "songs": [{"name": "song-b", "character": "gf"}],
        }])

    def test_prepare_removes_keyed_array_with_absent_baseline_and_keeps_foreign_nested_row(self):
        before = '{"owners":{"other-owner":"stable"}}'
        previous = '''{"owners":{"other-owner":"stable","import-owner":"v1"},
          "groups":[{"name":"shared-group","title":"Shared","songs":[
            {"name":"imported-song","version":"v1"}]}]}'''
        live = '''{"owners":{"other-owner":"stable","import-owner":"v1"},
          "groups":[{"name":"shared-group","title":"Shared","songs":[
            {"name":"imported-song","version":"v1"},
            {"name":"foreign-song","version":"other owner"}]}]}'''

        result = self.run_merge("prepare", before, previous, live)

        self.assertEqual(result["conflicts"], [])
        merged = self.parsed(result["text"])
        self.assertEqual(merged["owners"], {"other-owner": "stable"})
        self.assertEqual(merged["groups"], [{
            "name": "shared-group", "title": "Shared",
            "songs": [{"name": "foreign-song", "version": "other owner"}],
        }])

    def test_prepare_reports_local_scalar_and_child_edits_in_removed_group(self):
        before = '[]'
        previous = '''[{"name":"Imported","title":"Imported songs","songs":[
          {"name":"song-a","character":"bf"}]}]'''
        edited_lives = [
            ('header scalar', '''[{"name":"Imported","title":"Local title","songs":[
              {"name":"song-a","character":"bf"}]}]''', "title", "Local title"),
            ('child scalar', '''[{"name":"Imported","title":"Imported songs","songs":[
              {"name":"song-a","character":"user-character"}]}]''', "songs", None),
        ]

        for label, live, changed_field, expected_value in edited_lives:
            with self.subTest(edit=label):
                result = self.run_merge("prepare", before, previous, live)
                self.assertTrue(result["conflicts"], result)
                merged = self.parsed(result["text"])
                if changed_field == "title":
                    self.assertEqual(merged[0]["title"], expected_value)
                else:
                    self.assertEqual(merged[0]["songs"][0]["character"], "user-character")

    def test_prepare_conflicts_on_local_child_deletion_even_when_foreign_child_remains(self):
        before = '[]'
        previous = '''[{"name":"Imported","songs":[
          {"name":"song-a","character":"bf"}]}]'''
        live = '''[{"name":"Imported","songs":[
          {"name":"song-b","character":"gf"}]}]'''

        result = self.run_merge("prepare", before, previous, live)

        self.assertTrue(any("locally deleted generated child" in item for item in result["conflicts"]), result)
        merged = self.parsed(result["text"])
        self.assertEqual([song["name"] for song in merged[0]["songs"]], ["song-b"])

    def test_ambiguous_object_array_identity_conflicts_conservatively(self):
        before = '[{"name":"duplicate","value":1},{"name":"duplicate","value":2}]'
        generated = '[{"name":"duplicate","value":1},{"name":"duplicate","value":3}]'
        live = '[{"name":"duplicate","value":1},{"name":"duplicate","value":2},{"name":"local","value":9}]'

        result = self.run_merge("merge", before, generated, live)

        self.assertEqual(self.parsed(result["text"]), self.parsed(live))
        self.assertTrue(any("$" in item for item in result["conflicts"]))


if __name__ == "__main__":
    unittest.main()
