"""Static-reference planning and native HXC visual-asset scope regressions."""
from haxe_test_support import HAXE_COMMAND

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE"
)
NESTED_ARRAY_DONOR = DONOR / "scripts/songs/libitina.hxc"
HL17_MENU = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "codename/hl17_v3/mods/HL17/data/states/HL17MainMenu.hx"
)
HL17_INTRO = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "codename/hl17_v3/mods/HL17/data/states/IntroState.hx"
)


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain unavailable")
class HxcVisualAssetPlannerTest(unittest.TestCase):
    def run_fixture(self, source: str, *args: str) -> subprocess.CompletedProcess:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-visual-assets-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp", str(ROOT / "source"),
                    "-cp", folder,
                    "-main", "Main", "--interp",
                    *args,
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_literal_paths_are_deduplicated_and_dynamic_paths_are_not_guessed(self):
        result = self.run_fixture(
            r'''class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(
      "Paths.image('mainmenu/PleaseKrillMe');"
      + "Paths.getSparrowAtlas(\"freeplay/freeplayCapsule/takeoverweektypes\");"
      + "Paths.getFrames('main/sonic');"
      + "Paths.image('mainmenu/PleaseKrillMe');"
      + "Paths.image(prefix + 'dynamic');"
      + "Paths.getFrames(prefix + 'dynamic');");
    if (refs.length != 3) throw 'literal reference count: ' + refs.length;
    if (refs[0].kind != 'image' || refs[0].key != 'mainmenu/PleaseKrillMe')
      throw 'image reference was not preserved';
    if (refs[1].kind != 'sparrow'
      || refs[1].key != 'freeplay/freeplayCapsule/takeoverweektypes')
      throw 'atlas reference was not preserved';
    if (refs[2].kind != 'frames' || refs[2].key != 'main/sonic')
      throw 'getFrames reference was not preserved';
    var aliased = HxcAssetPlanner.literalReferences(
      "function createMenuItem(name:String, atlas:String) {"
      + " Paths.getSparrowAtlas(atlas); }"
      + "createMenuItem('costumes', 'mainmenu/PleaseKrillMe');");
    if (aliased.length != 1 || aliased[0].key != 'mainmenu/PleaseKrillMe')
      throw 'one-hop atlas alias was not planned';
    Sys.println('hxc-visual-planner-literals-ok');
  }
}'''
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-visual-planner-literals-ok", result.stdout)

    def test_permanent_texture_cache_uses_image_ownership_for_sound_path_keys(self):
        result = self.run_fixture(
            r'''class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(
      "FunkinMemory.permanentCacheTexture(Paths.sound('mechanics/Sign_Post_Mechanic', 'shared'));"
      + "FunkinMemory.permanentCacheTexture(Paths.sound('mechanics/HP GREMLIN', 'shared'));"
      + "FunkinMemory.permanentCacheTexture(Paths.sound('notes/NOTE_death', 'shared'));"
      + "FunkinSound.playOnce(Paths.sound('mechanics/Sign_Post_Mechanic'));"
      + "FunkinMemory.permanentCacheTexture(Paths.image('ui/prompt', 'shared'));");
    var images:Array<String> = [];
    var sounds:Array<String> = [];
    for (reference in refs) {
      if (reference.kind == 'image') images.push(reference.key);
      if (reference.kind == 'sound') sounds.push(reference.key);
    }
    if (images.length != 4 || images.indexOf('mechanics/Sign_Post_Mechanic') < 0
      || images.indexOf('mechanics/HP GREMLIN') < 0 || images.indexOf('notes/NOTE_death') < 0
      || images.indexOf('ui/prompt') < 0)
      throw 'permanent texture references were not planned as images: ' + images.join(',');
    if (sounds.length != 1 || sounds[0] != 'mechanics/Sign_Post_Mechanic')
      throw 'an independent Paths.sound use was removed with the texture cache: ' + sounds.join(',');
    Sys.println('hxc-permanent-texture-kind-ok');
  }
}'''
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-permanent-texture-kind-ok", result.stdout)

    def test_package_root_file_literals_are_owned_without_guessing_dynamic_paths(self):
        result = self.run_fixture(
            r'''class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(
      "Paths.file('window-icon.png'); Paths.file('assets/menus/title.png');"
      + "Paths.file(prefix + 'dynamic.png'); Paths.file('window-icon.png');");
    if (refs.length != 2 || refs[0].kind != 'file' || refs[0].key != 'window-icon.png'
      || refs[1].kind != 'file' || refs[1].key != 'assets/menus/title.png')
      throw 'bounded package-file references changed: ' + refs.length;
  }
}'''
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hxc_health_icon_ids_are_planned_only_from_literal_icon_slots(self):
        result = self.run_fixture(
            r'''class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(
      "PlayState.instance.iconP2.loadCharacter('our-harmony');"
      + "iconP1.setIcon(\"another-icon\");"
      + "iconP2.loadCharacter('our-harmony');"
      + "iconP2.loadCharacter(dynamicId);"
      + "speaker.loadCharacter('not-a-health-icon-slot');");
    if (refs.length != 2 || refs[0].kind != 'health-icon'
      || refs[0].key != 'our-harmony' || refs[1].key != 'another-icon')
      throw 'literal health icon references were not bounded/deduplicated';
  }
}'''
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(
        (DONOR / "scripts/songs/our-harmony.hxc").is_file()
        and (DONOR / "images/icons/icon-our-harmony.png").is_file()
        and (DONOR / "images/icons/icon-our-harmony.xml").is_file(),
        "mounted V-Slice icon fixture unavailable",
    )
    def test_mounted_hxc_health_icon_resolves_both_files_from_its_selected_root(self):
        script = DONOR / "scripts/songs/our-harmony.hxc"
        before = script.read_bytes()
        fixture = r'''import sys.io.File;
class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(File.getContent(__SCRIPT__));
    var discovered = false;
    for (reference in refs)
      if (reference.kind == 'health-icon' && reference.key == 'our-harmony') discovered = true;
    var mappings = VSliceImporter.hxcHealthIconMappings(__DONOR__, 'our-harmony');
    var png = false;
    var xml = false;
    if (mappings != null) for (mapping in mappings) {
      if (mapping.destination == 'images/icons/icon-our-harmony.png'
        && StringTools.startsWith(mapping.source, __DONOR__)) png = true;
      if (mapping.destination == 'images/icons/icon-our-harmony.xml'
        && StringTools.startsWith(mapping.source, __DONOR__)) xml = true;
    }
    if (!discovered || !png || !xml) throw 'mounted HXC health icon bundle was not owner-scoped';
    Sys.println('hxc-mounted-owner-icon-ok');
  }
}'''.replace("__SCRIPT__", json.dumps(str(script))).replace(
            "__DONOR__", json.dumps(str(DONOR))
        )
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-mounted-owner-icon-ok", result.stdout)
        self.assertEqual(before, script.read_bytes())

    def test_nested_finite_string_templates_preserve_selected_array_relationships(self):
        result = self.run_fixture(
            r'''class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(
      "function createSpeaker(state:String) { Paths.getSparrowAtlas('people/speakers/' + state); }"
      + "createSpeaker('quiet'); createSpeaker('normal');"
      + "var characterNames:Array<String> = ['Alice','Sam'];"
      + "Paths.getSparrowAtlas('cards/' + characterNames[i] + 'Card');"
      + "var resourceGroups:Array<Array<String>> = [['front','left'],['secure','private']];"
      + "function chooseResource(group:String='common') {"
      + " var sources:Array<String> = resourceGroups[group == 'restricted' ? 1 : 0];"
      + " var item = sources[index]; var groupPath = group == 'restricted' ? 'restricted/' : '';"
      + " Paths.getSparrowAtlas('panels/' + groupPath + item); }"
      + "chooseResource(); chooseResource('restricted');"
      + "Paths.image('NOTE_hold_assets');");
    var sawQuiet = false;
    var sawNormal = false;
    var sawPrefix = false;
    var sawAlice = false;
    var sawSam = false;
    var sawFront = false;
    var sawSecure = false;
    var sawWrongPair = false;
    var sawHold = false;
    for (reference in refs) {
      if (reference.key == 'people/speakers/quiet') sawQuiet = true;
      if (reference.key == 'people/speakers/normal') sawNormal = true;
      if (reference.key == 'people/speakers/') sawPrefix = true;
      if (reference.key == 'cards/AliceCard') sawAlice = true;
      if (reference.key == 'cards/SamCard') sawSam = true;
      if (reference.key == 'panels/front') sawFront = true;
      if (reference.key == 'panels/restricted/secure') sawSecure = true;
      if (reference.key == 'panels/restricted/front' || reference.key == 'panels/secure') sawWrongPair = true;
      if (reference.key == 'NOTE_hold_assets') sawHold = true;
    }
    if (!sawQuiet || !sawNormal || sawPrefix || !sawAlice || !sawSam
      || !sawFront || !sawSecure || sawWrongPair || !sawHold) {
      var keys = [];
      for (reference in refs) keys.push(reference.key);
      throw 'finite HXC template expansion was incomplete or over-broad: ' + keys.join(',');
    }
    Sys.println('hxc-visual-planner-related-arrays-ok');
  }
}'''
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-visual-planner-related-arrays-ok", result.stdout)

    def test_constant_foreach_loops_expand_only_bounded_literal_members(self):
        values = ",".join("'item%d'" % index for index in range(130))
        result = self.run_fixture(
            r'''class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(
      "var itemsOrder:Array<String> = ['load','credits','options','quit'];"
      + "function createMenu() { for (item in itemsOrder) {"
      + " Paths.image('main/' + item); Paths.image('main/' + item + '-blur'); } }");
    var keys = [];
    for (reference in refs) keys.push(reference.key);
    for (item in ['load','credits','options','quit']) {
      if (keys.indexOf('main/' + item) < 0 || keys.indexOf('main/' + item + '-blur') < 0)
        throw 'finite foreach path was omitted for ' + item + ': ' + keys.join(',');
    }
    if (keys.indexOf('main/') >= 0 || keys.indexOf('main/-blur') >= 0)
      throw 'foreach emitted an unbound prefix';

    var dynamicRefs = HxcAssetPlanner.literalReferences(
      "function createMenu(runtimeItems:Array<String>) {"
      + " for (item in runtimeItems) { Paths.image('main/' + item); } }");
    if (dynamicRefs.length != 0) throw 'runtime loop values were guessed';

    var oversized = HxcAssetPlanner.literalReferences(
      "var items:Array<String> = [__VALUES__];"
      + "function createMenu() { for (item in items) { Paths.image('bounded/' + item); } }");
    if (oversized.length != 128) throw 'finite loop cap changed: ' + oversized.length;
    Sys.println('hxc-visual-planner-finite-foreach-ok');
  }
}'''.replace("__VALUES__", values)
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-visual-planner-finite-foreach-ok", result.stdout)

    def test_finite_random_integer_audio_paths_expand_with_strict_bounds(self):
        result = self.run_fixture(
            r'''class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(
      "Paths.sound('intro/' + FlxG.random.int(0,12));"
      + "Paths.music(\"menu/\" + FlxG.random.int(2, 3));"
      + "Paths.sound('fixed/click');"
      + "Paths.sound('runtime/' + selectedSound);"
      + "Paths.sound('wide/' + FlxG.random.int(0,128));"
      + "Paths.sound('reversed/' + FlxG.random.int(4,2));"
      + "Paths.sound('variable/' + FlxG.random.int(0, maximum));");
    var keys = [];
    for (reference in refs) keys.push(reference.kind + ':' + reference.key);
    if (refs.length != 16) throw 'bounded audio reference count: ' + keys.join(',');
    for (index in 0...13)
      if (keys.indexOf('sound:intro/' + index) < 0)
        throw 'finite inclusive sound range omitted value ' + index + ': ' + keys.join(',');
    if (keys.indexOf('music:menu/2') < 0 || keys.indexOf('music:menu/3') < 0
      || keys.indexOf('sound:fixed/click') < 0)
      throw 'literal sound or finite music paths were omitted: ' + keys.join(',');
    for (key in ['sound:intro/', 'sound:runtime/', 'sound:wide/0',
      'sound:reversed/4', 'sound:variable/0'])
      if (keys.indexOf(key) >= 0)
        throw 'unknown or over-cap path was guessed: ' + key;
    Sys.println('hxc-finite-audio-paths-ok');
  }
}'''
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-finite-audio-paths-ok", result.stdout)

    @unittest.skipUnless(HL17_INTRO.is_file(), "mounted Codename IntroState fixture unavailable")
    def test_mounted_intro_finite_audio_range_is_planned_without_editing_source(self):
        before = HL17_INTRO.read_bytes()
        fixture = r'''import sys.io.File;
class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(File.getContent(__SOURCE__), true);
    var keys = [];
    for (reference in refs)
      if (reference.kind == 'sound' && StringTools.startsWith(reference.key, 'intro/'))
        keys.push(reference.key);
    if (keys.length != 14 || keys.indexOf('intro/soundFull') < 0)
      throw 'numbered intro range or static intro sound changed: ' + keys.join(',');
    for (index in 0...13)
      if (keys.indexOf('intro/' + index) < 0)
        throw 'finite intro sound path was omitted: ' + index + ' in ' + keys.join(',');
    Sys.println('hxc-mounted-finite-audio-paths-ok');
  }
}'''.replace("__SOURCE__", json.dumps(str(HL17_INTRO)))
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-mounted-finite-audio-paths-ok", result.stdout)
        self.assertEqual(before, HL17_INTRO.read_bytes())

    @unittest.skipUnless(HL17_MENU.is_file(), "mounted HL17 Codename source fixture unavailable")
    def test_mounted_hl17_menu_finite_loop_paths_are_planned(self):
        before = HL17_MENU.read_bytes()
        fixture = r'''import sys.io.File;
class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(File.getContent(__SOURCE__));
    var keys = [];
    for (reference in refs)
      if (reference.kind == 'image') keys.push(reference.key);
    var expected = ['main/bg', 'main/logo', 'main/blure',
      'main/load', 'main/load-blur', 'main/credits', 'main/credits-blur',
      'main/options', 'main/options-blur', 'main/quit', 'main/quit-blur'];
    for (key in expected)
      if (keys.indexOf(key) < 0) throw 'mounted HL17 menu asset omitted: ' + key + ' in ' + keys.join(',');
    if (keys.indexOf('main/') >= 0 || keys.indexOf('main/-blur') >= 0)
      throw 'mounted HL17 menu emitted unbound foreach prefixes';
    Sys.println('hxc-visual-planner-mounted-hl17-ok');
  }
}'''.replace("__SOURCE__", json.dumps(str(HL17_MENU)))
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-visual-planner-mounted-hl17-ok", result.stdout)
        self.assertEqual(before, HL17_MENU.read_bytes())

    @unittest.skipUnless(NESTED_ARRAY_DONOR.is_file(), "mounted nested-array HXC fixture unavailable")
    def test_mounted_nested_array_template_paths_remain_planned(self):
        before = NESTED_ARRAY_DONOR.read_bytes()
        fixture = r'''import sys.io.File;
class Main {
  static function main() {
    var source = File.getContent(__SOURCE__);
    var refs = HxcAssetPlanner.literalReferences(source);
    var expected = [
      'libitina/popups/Binary', 'libitina/popups/Error',
      'libitina/popups/Unauthorized', 'libitina/popups/Unknown',
      'libitina/popups/Unspecified', 'libitina/popupsred/Access',
      'libitina/popupsred/Corrupted'
    ];
    var planned = [];
    for (reference in refs) planned.push(reference.key);
    for (key in expected) {
      var found = false;
      for (reference in refs)
        if (reference.kind == 'sparrow' && reference.key == key) found = true;
      if (!found) throw 'mounted finite template path missing: ' + key + ' in ' + planned.join(',');
    }
    for (reference in refs)
      if (reference.key == 'libitina/popupsred/Binary'
        || reference.key == 'libitina/popups/Access')
        throw 'nested array rows were cross-paired: ' + reference.key;
    Sys.println('hxc-visual-planner-mounted-nested-ok');
  }
}'''.replace('__SOURCE__', json.dumps(str(NESTED_ARRAY_DONOR)))
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('hxc-visual-planner-mounted-nested-ok', result.stdout)
        self.assertEqual(before, NESTED_ARRAY_DONOR.read_bytes())

    def test_synthetic_plan_reads_only_bounded_hxc_families(self):
        with tempfile.TemporaryDirectory(prefix="hxc-visual-donor-", dir=ROOT / "tmp") as folder:
            donor = Path(folder)
            (donor / "scripts/modules").mkdir(parents=True)
            (donor / "images/unreferenced").mkdir(parents=True)
            (donor / "scripts/modules/visual.hxc").write_text(
                "Paths.getSparrowAtlas('mainmenu/PleaseKrillMe');\n"
                "Paths.image('freeplay/freeplayCapsule/takeoverweektypes');\n"
                "Paths.getFrames('main/sonic');"
            , newline='\n')
            # A media file with no HXC reference is intentionally irrelevant to
            # the plan; the importer copies only the references later.
            (donor / "images/unreferenced/never.png").write_bytes(b"not planned")
            source = r'''import haxe.io.Path;
class Main {
  static function main() {
    var plan = HxcAssetPlanner.plan(__DONOR__);
    if (plan.scripts.length != 1 || plan.references.length != 3)
      throw 'bounded plan changed: ' + plan.scripts.length + '/' + plan.references.length;
    var keys = [plan.references[0].key, plan.references[1].key];
    if (keys.indexOf('mainmenu/PleaseKrillMe') < 0
      || keys.indexOf('freeplay/freeplayCapsule/takeoverweektypes') < 0)
      throw 'plan content changed';
    var sawFrames = false;
    for (reference in plan.references)
      if (reference.kind == 'frames' && reference.key == 'main/sonic') sawFrames = true;
    if (!sawFrames) throw 'getFrames was omitted from the bounded HXC plan';
    Sys.println('hxc-visual-planner-root-ok');
  }
}'''.replace('__DONOR__', json.dumps(str(donor)))
            result = self.run_fixture(source)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("hxc-visual-planner-root-ok", result.stdout)

    def test_selected_stage_plan_filters_only_unselected_stage_scripts(self):
        with tempfile.TemporaryDirectory(prefix="hxc-selected-stages-", dir=ROOT / "tmp") as folder:
            donor = Path(folder)
            fixtures = {
                "stages/hall.hxc": "Paths.image('stage/hall-missing');",
                "stages/clubroom.hxc": "Paths.image('stage/clubroom-needed');",
                "scripts/stages/hall.hxc": "Paths.sound('stage-hall-sound');",
                "data/stages/hall.hxc": "Paths.image('stage/data-hall-missing');",
                "scripts/modules/menu.hxc": "Paths.image('menu/needed');",
                "scripts/notes/custom.hxc": "Paths.image('notes/needed');",
                "data/stages/OffName.hxc": "class Renamed extends Stage { function new() { super('clubroom'); } function onCreate() { Paths.image('stage/renamed-needed'); } }",
                "scripts/stages/ActorName.hxc": "class Actor extends MultiSparrowCharacter { function new() { super('actor'); } function onCreate() { Paths.image('actor/needed'); } }",
            }
            for relative, content in fixtures.items():
                path = donor / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')
            source = r'''class Main {
  static function main() {
    var filtered = HxcAssetPlanner.plan(__DONOR__, ['clubroom']);
    var filteredKeys = [];
    for (reference in filtered.references) filteredKeys.push(reference.key);
    if (filtered.scripts.length != 5
      || filteredKeys.indexOf('stage/renamed-needed') < 0
      || filteredKeys.indexOf('actor/needed') < 0
      || filteredKeys.indexOf('stage/clubroom-needed') < 0
      || filteredKeys.indexOf('menu/needed') < 0
      || filteredKeys.indexOf('notes/needed') < 0
      || filteredKeys.indexOf('stage/hall-missing') >= 0
      || filteredKeys.indexOf('stage/data-hall-missing') >= 0
      || filteredKeys.indexOf('stage-hall-sound') >= 0)
      throw 'stage selection filtered the wrong HXC surface: '
        + filtered.scripts.length + '/' + filteredKeys.join(',');
    var all = HxcAssetPlanner.plan(__DONOR__);
    if (all.scripts.length != 8 || all.references.length != 8)
      throw 'default plan must retain every script and reference';
    var none = HxcAssetPlanner.plan(__DONOR__, []);
    var noneKeys = [for (reference in none.references) reference.key];
    if (none.scripts.length != 3 || none.references.length != 3
      || noneKeys.indexOf('actor/needed') < 0
      || noneKeys.indexOf('stage/renamed-needed') >= 0
      || noneKeys.indexOf('stage/clubroom-needed') >= 0)
      throw 'empty stage selection must keep non-stage families only';
    Sys.println('hxc-visual-planner-selected-stages-ok');
  }
}'''.replace("__DONOR__", json.dumps(str(donor)))
            result = self.run_fixture(source)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("hxc-visual-planner-selected-stages-ok", result.stdout)

    def test_native_boundaries_and_manifest_copy_path_are_present(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        main_menu = (ROOT / "source/MainMenuState.hx").read_text()
        freeplay = (ROOT / "source/FreeplayState.hx").read_text()
        scope = (ROOT / "source/HxcStateAssetScope.hx").read_text()
        runtime = (ROOT / "source/HxcFreeplayRuntime.hx").read_text()
        compat_runtime = (ROOT / "source/HxcCompatRuntime.hx").read_text()

        self.assertIn("HxcAssetPlanner.plan(root)", module)
        self.assertIn("HxcAssetPlanner.plan(root, selectedStages)", module)
        self.assertIn("activeReferences.exists(identity)", module)
        self.assertIn("selectedVSliceHxcStages(sourceRoot, scriptSourceRoot, selectedSongs)", module)
        self.assertIn("mergeVSliceHxcStaticAssets", module)
        self.assertIn("VSliceImporter.hxcHealthIconMappings", module)
        self.assertIn("kind == 'health-icon'", module)
        self.assertIn("mergeVSliceHxcStageAsset(sourceRoot, runtimeNamespace", module)
        self.assertIn("CodenameFrameAtlasAssets.plan(sourceRoot, stem)", module)
        self.assertIn("CompatScriptManifest.destinationRoot", module)
        self.assertIn("images/' + stem + '.png", module)
        self.assertIn("images/' + stem + metadataExtension", module)
        self.assertIn("hxcSharedLibraryAlias", module)
        self.assertIn("vSliceLibraryRoots", module)

        self.assertIn("HxcStateAssetScope.sparrowAtlas(assetRoot", main_menu)
        self.assertIn("freeplay basic", main_menu)
        self.assertIn("hxc-asset-fallback", scope)
        self.assertIn("hxcPushAssetScope", freeplay)
        self.assertIn("hxcApplyImportedFreeplayCustomization", freeplay)
        self.assertIn("HxcFreeplayWeekType", freeplay)
        self.assertIn("owner.hxcPushAssetScope(scope.root)", runtime)
        self.assertIn("factoryEntry", compat_runtime)

    @unittest.skipUnless(
        DONOR.is_dir()
        and (DONOR / "scripts/modules/CostumeMenuButtonv2.hxc").is_file()
        and (DONOR / "scripts/modules/FreeplayFixes.hxc").is_file(),
        "mounted TAKEOVER HXC modules unavailable",
    )
    def test_mounted_modules_retain_the_two_literal_visual_references(self):
        costume_path = DONOR / "scripts/modules/CostumeMenuButtonv2.hxc"
        freeplay_path = DONOR / "scripts/modules/FreeplayFixes.hxc"
        before = {costume_path: costume_path.read_bytes(), freeplay_path: freeplay_path.read_bytes()}
        costume = costume_path.read_text(errors="ignore")
        freeplay = freeplay_path.read_text(errors="ignore")
        # CostumeMenuButtonv2 uses a one-hop `atlas` parameter; assert both
        # sides of that static binding are present in the mounted donor.
        self.assertIn("'mainmenu/PleaseKrillMe'", costume)
        self.assertIn("Paths.getSparrowAtlas(atlas)", costume)
        self.assertIn("freeplay/freeplayCapsule/takeoverweektypes", freeplay)
        fixture = r'''class Main {
  static function main() {
    var plan = HxcAssetPlanner.plan(__DONOR__);
    var sawCostume = false;
    var sawWeekType = false;
    for (reference in plan.references) {
      if (reference.key == 'mainmenu/PleaseKrillMe') sawCostume = true;
      if (reference.key == 'freeplay/freeplayCapsule/takeoverweektypes') sawWeekType = true;
    }
    if (!sawCostume || !sawWeekType) throw 'mounted visual references were not planned';
    Sys.println('hxc-visual-planner-mounted-ok');
  }
}'''.replace('__DONOR__', json.dumps(str(DONOR)))
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('hxc-visual-planner-mounted-ok', result.stdout)
        self.assertEqual(before[costume_path], costume_path.read_bytes())
        self.assertEqual(before[freeplay_path], freeplay_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
