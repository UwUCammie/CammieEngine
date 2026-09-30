from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PSYCH_SOURCE = ROOT.parent / "FNF-Example-Mods/misc/psych_source_code/source/psychlua/FunkinLua.hx"
RESULTS_SCRIPT = ROOT.parent / "FNF-Example-Mods/misc/V-Slice Results Screen (psych engine)/scripts/results.lua"


class PsychScriptMediaCompatTest(unittest.TestCase):
    def test_media_globals_capture_the_validated_calling_owner(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        expected_routes = [
            "compatMakeLuaSpriteForOwner(psychScriptOwner, tag, image, x, y)",
            "compatMakeAnimatedLuaSpriteForOwner(psychScriptOwner, tag, image, x, y, spriteType)",
            "compatPlaySoundForOwner(psychScriptOwner, path, volume, tag, looped)",
            "compatPlayMusicForOwner(psychScriptOwner, path, volume, looped)",
            "compatPrecacheImageForOwner(psychScriptOwner, path, allowGPU)",
            "compatPrecacheSoundForOwner(psychScriptOwner, path)",
            "compatPrecacheMusicForOwner(psychScriptOwner, path)",
        ]
        for route in expected_routes:
            self.assertIn(route, source)
        self.assertIn("PsychOwnerPaths.create(ownerRoot)", source)
        self.assertIn("PsychOwnerAssetPath.ownerReferenceAllowed(ownerRoot, reference)", source)
        self.assertGreaterEqual(source.count("compatPsychOwnerFallbackAllowed(ownerRoot,"), 7)
        paths = (ROOT / "source/PsychOwnerPaths.hx").read_text(encoding="utf-8")
        for atlas_method in ("getAtlas", "getSparrowAtlas", "getPackerAtlas", "getAsepriteAtlas"):
            self.assertIn("'" + atlas_method + "'", paths)

    def test_native_sound_fallback_does_not_search_the_active_song_import(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = source.index("function compatPsychNativeSoundPath(")
        end = source.index("function compatPlayMusic(", start)
        fallback = source[start:end]
        self.assertIn("preferSounds ? 'sounds/' : 'music/'", fallback)
        self.assertIn("preferSounds ? 'music/' : 'sounds/'", fallback)
        self.assertNotIn("selectedRoot", fallback)
        self.assertNotIn("selectedPsychSkinRoot", fallback)

    def test_donor_and_results_script_use_the_supported_paths(self):
        psych = PSYCH_SOURCE.read_text(encoding="utf-8")
        self.assertIn('Lua_helper.add_callback(lua, "precacheImage"', psych)
        self.assertIn('Paths.image(name, allowGPU)', psych)
        self.assertIn('Lua_helper.add_callback(lua, "makeLuaSprite"', psych)
        self.assertIn('Lua_helper.add_callback(lua, "makeAnimatedLuaSprite"', psych)
        self.assertIn('Lua_helper.add_callback(lua, "playSound"', psych)
        self.assertIn('Paths.sound(sound)', psych)
        self.assertIn('Paths.music(sound)', psych)

        results = RESULTS_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("makeLuaSprite(", results)
        self.assertIn("makeAnimatedLuaSprite(", results)
        self.assertIn("playSound(", results)
        self.assertIn("playMusic(", results)


if __name__ == "__main__":
    unittest.main()
