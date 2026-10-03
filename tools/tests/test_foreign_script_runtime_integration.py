"""Source-level guards for foreign multi-script/stage runtime wiring.

PlayState depends on Flixel/OpenFL and is intentionally not compiled by the
small interpreter fixtures. These checks pin the integration points while the
pure discovery and translation classes are exercised by their own Haxe tests.
"""

from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ForeignScriptRuntimeIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play_state = (ROOT / "source/PlayState.hx").read_text()

    def test_chart_aware_multi_script_plan_loads_once(self):
        source = self.play_state
        self.assertIn("PsychScriptDiscovery.discover(compatRoot, Song.storageFolder(SONG), SONG, songEvents)", source)
        self.assertIn("CompatScriptManifest.FILE_NAME", source)
        self.assertIn("compatScriptRoots()", source)
        self.assertIn("psychCompatScriptsLoaded", source)
        self.assertIn("loadedCompatScriptPaths", source)
        self.assertIn("entry.scope == PsychScriptDiscovery.STAGE", source)
        self.assertIn("basename.startsWith('modchart.')", source)
        self.assertIn("loadPsychCompatScripts();", source)

    def test_psych_stage_has_runtime_and_static_fallback_paths(self):
        source = self.play_state
        self.assertIn("function loadPsychStageCompat():Bool", source)
        self.assertIn("PsychStageCompat.translateFile(entry.path)", source)
        self.assertIn("makeHaxeState('stage', directory, filename);", source)
        self.assertIn("makeHaxeState('stage', directory, filename, fallback);", source)
        self.assertIn("applyPsychStageJson", source)

    def test_explicit_script_extensions_are_not_double_suffixed(self):
        source = self.play_state
        self.assertIn("lower.endsWith('.hscript') || lower.endsWith('.hxs')", source)
        self.assertIn("lower.endsWith('.lua') && FNFAssets.exists(normalized)", source)
        self.assertIn("lower.endsWith('.hxc') && FNFAssets.exists(normalized)", source)
        self.assertIn("HxcCompat.translate", source)

    def test_hxc_layout_is_selected_by_song_stage_and_character(self):
        source = self.play_state
        self.assertIn("HxcScriptDiscovery.discoverRoot(root, SONG.song)", source)
        self.assertIn("hxcScriptRoots()", source)
        self.assertIn("case 'character': selectedCharacterPaths.indexOf(scriptPath) >= 0", source)
        self.assertIn("loadHxcStageCompat() || loadPsychStageCompat()", source)
        self.assertIn("loadHxcCompatScripts();", source)

    def test_manifest_hxc_state_factory_is_root_scoped(self):
        factory = (ROOT / "source/HxcStateFactory.hx").read_text()
        runtime = (ROOT / "source/HxcImportedRuntime.hx").read_text()
        self.assertIn("CompatScriptManifest.ROOT_PREFIX", factory)
        self.assertIn("HxcScriptDiscovery.discoverRoot(cleanRoot, '')", factory)
        self.assertIn("insideRoot(path, cleanRoot)", factory)
        self.assertIn("unsupported-hxc-state-ambiguous", factory)
        self.assertIn("unsupported-hxc-cross-import-switch", factory)
        self.assertIn("HxcCompatRuntime.stateInit(requested)", factory)
        self.assertIn("CreditsState", factory)
        self.assertIn("SaveDataState", factory)
        self.assertIn("public static function startExitState", factory)
        self.assertIn("public static function stateFactory", factory)
        self.assertIn("public static function openSubStateScoped", factory)
        self.assertIn("new HxcImportedSubState(entry)", factory)
        self.assertIn("new HxcImportedState(entry)", factory)
        self.assertIn("EngineCompat.rewriteScopedAssetPaths(entry.generatedHscript)", runtime)
        self.assertIn("HxcStateAssetScope.paths(entry.root)", runtime)
        self.assertIn("HxcStateFactory.stateInit(entry.root, name)", runtime)
        self.assertIn("HxcStateFactory.stateFactory(entry.root, name, args)", runtime)
        self.assertIn("HxcStateFactory.openSubStateScoped(entry.root, owner, value)", runtime)
        self.assertIn("HxcStateFactory.openSubStateScoped(entry.root, host, value)", runtime)
        self.assertIn("HxcStateFactory.startExitState(entry.root, target)", runtime)
        self.assertIn("hxcStartExitState", runtime)
        self.assertIn("interp.variables.set('CreditsState', CreditsState)", runtime)
        self.assertIn("interp.variables.set('SaveDataState', SaveDataState)", runtime)

    def test_hxc_state_lifecycle_and_safe_navigation_are_native_wrappers(self):
        factory = (ROOT / "source/HxcStateFactory.hx").read_text()
        state = (ROOT / "source/HxcImportedState.hx").read_text()
        substate = (ROOT / "source/HxcImportedSubState.hx").read_text()
        music_state = (ROOT / "source/MusicBeatState.hx").read_text()
        music_substate = (ROOT / "source/MusicBeatSubstate.hx").read_text()
        runtime = (ROOT / "source/HxcImportedRuntime.hx").read_text()
        for source in (state, substate):
            self.assertIn("runtime.create();", source)
            self.assertIn("runtime.update(elapsed);", source)
            self.assertIn("runtime.step(hxcCurrentStep);", source)
            self.assertIn("runtime.beat(hxcCurrentBeat);", source)
            self.assertIn("runtime.destroy();", source)
        self.assertIn("hxcCurrentStep", music_state)
        self.assertIn("hxcCurrentBeat", music_state)
        self.assertIn("hxcCurrentStep", music_substate)
        self.assertIn("hxcCurrentBeat", music_substate)
        self.assertIn("HxcStateFactory.switchState", runtime)

    def test_hxc_state_transition_lowering_is_root_scoped(self):
        compat = (ROOT / "source/HxcCompat.hx").read_text()
        factory = (ROOT / "source/HxcStateFactory.hx").read_text()
        plugin = (ROOT / "source/PluginManager.hx").read_text()
        play_state = (ROOT / "source/PlayState.hx").read_text()
        freeplay_runtime = (ROOT / "source/HxcFreeplayRuntime.hx").read_text()
        for token in (
            "hxcStateFactory(\"$1\", [$2])",
            "hxcStateInit($1)",
            "hxcSubStateInit($1)",
            "hxcOpenSubStateOn(",
            "hxcStartExitState(",
            "lowerStateTransitionFactories",
        ):
            self.assertIn(token, compat)
        self.assertIn("HxcScriptDiscovery.normalizeToken(requested)", factory)
        self.assertIn("return stateInit(root, requested)", factory)
        self.assertIn("targetRoot", factory)
        self.assertIn('interp.variables.set("hxcStateFactory"', plugin)
        self.assertIn('interp.variables.set("hxcStartExitState"', plugin)
        self.assertIn('interp.variables.set("CreditsState", CreditsState)', plugin)
        self.assertIn('interp.variables.set("SaveDataState", SaveDataState)', plugin)
        self.assertIn('HxcStateFactory.stateFactory(\'\', name, args)', plugin)
        self.assertIn('HxcStateFactory.openSubStateScoped(\'\', null, target)', plugin)
        self.assertIn('HxcStateFactory.openSubStateScoped(\'\', host, target)', plugin)
        self.assertIn("HxcStateFactory.startExitState(hxcRoot, target)", play_state)
        self.assertIn("HxcStateFactory.startExitState(scope == null ? '' : scope.root, target)", freeplay_runtime)

    def test_native_vslice_stage_keeps_companion_hxc_in_an_isolated_scope(self):
        source = self.play_state
        self.assertIn("var hxcStageScopes:Array<String> = [];", source)
        self.assertIn("var scope = 'stage-hxc-' + hxcStageScopeIndex++;", source)
        self.assertIn("makeHaxeState(scope, Path.directory(scriptPath) + '/', Path.withoutDirectory(scriptPath));", source)
        self.assertIn("loadHxcStageCompat();", source)
        self.assertIn("function clearHxcStageScopes():Void", source)
        self.assertIn("if (curStage != null && curStage.interp == null)", source)
        self.assertIn("clearHxcStageScopes();", source)

    def test_hxc_stage_duplicate_props_bind_to_native_objects(self):
        source = self.play_state
        self.assertIn("function nativeStagePropBindings():Map<String, Dynamic>", source)
        self.assertIn("function filterHxcStageDuplicateProps(source:String, bindings:Map<String, Dynamic>):String", source)
        self.assertIn("nativeStagePropBindings();", source)
        self.assertIn("interp.variables.set(name, hxcStageBindings.get(name));", source)
        self.assertIn("filterHxcStageDuplicateProps(source, hxcStageBindings)", source)
        self.assertIn("The native converter owns props with a real JSON asset", source)

    def test_hxc_stage_asset_paths_are_manifest_scoped(self):
        source = self.play_state
        compat = (ROOT / "source/EngineCompat.hx").read_text()
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("EngineCompat.rewriteScopedAssetPaths(source)", source)
        self.assertIn("interp.variables.set('hxcPaths'", source)
        self.assertIn("interp.variables.set('hxcAssets'", source)
        self.assertIn("function makeHxcPathsProxy(root:String):Dynamic", source)
        self.assertIn("function makeHxcAssetsProxy():Dynamic", source)
        self.assertIn("FNFAssets.getBitmapData(scoped)", source)
        self.assertIn("Std.isOfType(id, BitmapData)", source)
        self.assertIn("FlxAtlasFrames.fromSparrow(imageValue, metadataValue)", source)
        self.assertIn("mergeVSliceHxcStageAssets", module)
        self.assertIn("selectedSongs:Map<String, SongImport>", module)
        self.assertIn("rewriteScopedAssetPaths", compat)
        self.assertIn("hxcAssets.", compat)

    def test_real_concert_hxc_has_scoped_shader_and_teto_dependencies(self):
        donor = Path("/run/media/cammie/External Storage/FNF-Example-Mods/v-slice/HatsuneMiku-ProjectFunkin-V-Slice")
        script = donor / "scripts/stages/concert.hxc"
        if not script.is_file():
            self.skipTest("V-Slice example donor is not mounted")
        source = script.read_text()
        self.assertIn('Paths.getSparrowAtlas("stage/TB/teto_idle")', source)
        self.assertIn('Assets.getText(Paths.frag("blend"))', source)
        self.assertTrue((donor / "images/stage/TB/teto_idle.png").is_file())
        self.assertTrue((donor / "images/stage/TB/teto_idle.xml").is_file())
        self.assertTrue((donor / "shaders/blend.frag").is_file())
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("hxcStageAssetReferences", module)
        self.assertIn("mergeVSliceHxcStageAsset(sourceRoot, runtimeNamespace, reference, result)", module)

    def test_vslice_import_copies_only_runtime_compatible_foreign_trees(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("mergeVSliceRuntimeAssets(engineRoot.contentRoot", module)
        self.assertIn("['sounds', 'music', 'videos', 'fonts', 'shaders']", module)
        self.assertIn("mergeVSliceEventAssets", module)
        self.assertIn("EngineCompat.eventSpriteDescriptorFromSource", module)
        self.assertIn("HxcEventSpriteDescriptor.serializeCatalog(descriptors)", module)
        self.assertIn("Path.join([runtimeNamespace, HxcEventSpriteDescriptor.CATALOG_FILE])", module)
        self.assertIn("existingImportRelative(images, atlasKey + metadataExtension)", module)
        self.assertIn("mergeVSliceEventFile(imageSource, destinationBase + '.png'", module)
        self.assertIn("mergeCompatScriptTrees", module)
        self.assertIn("assets/imported_mods/<namespace>", module)
        self.assertNotIn("['scripts', 'data', 'songs', 'characters']", module)

    def test_importer_isolates_script_trees_and_repairs_missing_manifests(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("compatScripts.json", module)
        self.assertIn("for (importedSong in importedSongs)", module)
        self.assertIn("writeCompatScriptManifest(importedSong)", module)
        self.assertIn("CompatScriptManifest.destinationRoot(sourceRoot, engine)", module)
        self.assertIn("for (name in compatScriptTreeNames())", module)
        self.assertIn("var destinationRoot = destination;", module)
        self.assertIn("Path.join([destinationRoot, 'scripts', family])", module)
        self.assertNotIn("Path.join(['assets', 'scripts', family])", module)

    def test_manifest_selection_is_scoped_to_the_current_song(self):
        source = self.play_state
        self.assertIn("var manifestPath = currentSongDataPath(CompatScriptManifest.FILE_NAME)", source)
        self.assertIn("function currentSongStorageFolder():String", source)
        self.assertIn("Song.storageFolder(SONG)", source)
        self.assertIn("var roots:Array<String> = ['assets']", source)
        self.assertIn("for (compatRoot in compatScriptRoots())", source)
        self.assertIn("CompatScriptManifest.rootsInPrecedence(manifest)", source)
        self.assertIn("CompatScriptManifest.selectedRoot(manifest)", source)

    def test_importer_records_selected_manifest_owner_for_repairs(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("manifest.selectedRoot = desiredOwner", module)
        self.assertIn("CompatScriptManifest.destinationKey(manifest.selectedRoot)", module)
        self.assertIn("CompatScriptManifest.destinationKey(desiredOwner)", module)

    def test_event_assets_skip_native_fallback_for_manifest_routes(self):
        source = self.play_state
        self.assertIn("function compatForeignScriptRoots():Array<String>", source)
        self.assertIn("ShaderPaths.resolve('vignette', compatForeignScriptRoots(), false)", source)
        self.assertIn("CompatScriptManifest.selectedRoot(getCompatScriptManifest())", source)
        sprite_runtime = source[source.index("function spawnHxcEventSprite("):source.index("function clearHxcVignette(")]
        self.assertNotIn("compatForeignScriptRoots()", sprite_runtime)
        self.assertIn("var roots = hxcScriptRoots();", source)
        self.assertIn("for (root in roots)", source)

    def test_event_sprite_uses_selected_manifest_root_and_astc_decoder_boundary(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        source = self.play_state
        self.assertIn("VSliceAstcAdapter.decodeFile(source, destination)", module)
        self.assertIn("result.errors.push(detail)", module)
        self.assertIn("for (message in mergedRuntime.errors)", module)
        self.assertIn("CompatScriptManifest.selectedRoot(getCompatScriptManifest())", source)
        self.assertIn("HxcStateAssetScope.eventAtlas(root, atlasKey, atlasType", source)
        self.assertIn("EngineCompat.eventSpriteDescriptorFromSource(File.getContent(path))", source)
        self.assertIn("filesRead >= 128", source)
        self.assertNotIn("compatForeignScriptRoots()", source[source.index("function spawnHxcEventSprite("):source.index("function clearHxcVignette(")])
        self.assertNotIn("MarkovEyes.png", source)
        self.assertNotIn("MarkovWindow", source)

    def test_event_descriptor_import_reads_donor_and_writes_only_namespace(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        importer = module[module.index("static function mergeVSliceEventAssets("):module.index(
            "/** Copy one event-owned asset", module.index("static function mergeVSliceEventAssets(")
        )]
        self.assertIn("File.getContent(path)", importer)
        self.assertIn("File.saveContent(catalogPath, catalogContents)", importer)
        self.assertIn("Path.join([runtimeNamespace, HxcEventSpriteDescriptor.CATALOG_FILE])", importer)
        self.assertIn("mergeVSliceEventFile(imageSource, destinationBase + '.png'", importer)
        self.assertIn("mergeVSliceEventFile(metadataSource, destinationBase + metadataExtension", importer)
        self.assertNotIn("File.saveContent(path", importer)
        self.assertNotIn("File.copy(catalogPath", importer)

    def test_event_atlas_scope_has_no_native_or_other_root_fallback(self):
        scope = (ROOT / "source/HxcStateAssetScope.hx").read_text()
        method = scope[scope.index("public static function eventAtlas("):scope.index("/** Resolve a static HXC media key", scope.index("public static function eventAtlas("))]
        self.assertIn("scopedAssetPath(root, 'images/' + clean + '.png')", method)
        self.assertIn("scopedAssetPath(root, 'images/' + clean + (packer ? '.txt' : '.xml'))", method)
        self.assertNotIn("nativeAssetPath", method)
        self.assertNotIn("compatScriptRoots", method)


if __name__ == "__main__":
    unittest.main()
