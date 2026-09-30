"""V-Slice base countdown image ids resolve through native UI assets."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class VSliceSharedAssetPathsTest(unittest.TestCase):
    def test_countdown_image_namespace_maps_to_existing_pixel_and_normal_assets(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''class Main {
  static function check(value:Bool, message:String):Void {
    if (!value) throw message;
  }
  static function exists(key:String):Bool
    return sys.FileSystem.exists("assets/images/" + key + ".png");
  static function main():Void {
    var ready = VSliceSharedAssetPaths.imageCandidates("ui/countdown/pixel/ready", "normal");
    var set = VSliceSharedAssetPaths.imageCandidates("shared:ui/countdown/pixel/set.png", "normal");
    var go = VSliceSharedAssetPaths.imageCandidates("default:ui/countdown/pixel/go", "missing-pack");
    check(ready.length > 0 && ready[0] == "custom_ui/ui_packs/normal/ready-pixel",
      "pixel ready did not prefer the configured native pack");
    check(set.length > 0 && set[0] == "custom_ui/ui_packs/normal/set-pixel",
      "shared pixel set id did not normalize");
    check(go.length > 1 && go[1] == "custom_ui/ui_packs/normal/date-pixel",
      "pixel GO did not use the engine's authored date-pixel asset");
    for (candidates in [ready, set, go]) {
      var found = false;
      for (candidate in candidates)
        if (exists(candidate)) found = true;
      check(found, "countdown fallback candidate is absent from the engine assets: " + candidates);
    }

    var normal = VSliceSharedAssetPaths.imageCandidates("ui/countdown/doki/go", "vslice-custom");
    check(normal.length > 1 && normal[0] == "custom_ui/ui_packs/vslice-custom/go"
      && normal[1] == "custom_ui/ui_packs/normal/go",
      "normal countdown did not prefer the active pack before native normal fallback");
    check(VSliceSharedAssetPaths.imageCandidates("images/custom-countdown/ready").length == 0,
      "custom countdown path was silently replaced by native art");
    check(VSliceSharedAssetPaths.imageCandidates("ui/countdown/pixel/other").length == 0,
      "unknown countdown token was mapped to a misleading fallback");
    var unsafePack = VSliceSharedAssetPaths.imageCandidates("ui/countdown/pixel/ready", "../outside");
    check(unsafePack.length > 0 && unsafePack[0].indexOf("..") < 0,
      "unsafe UI pack name entered an asset path");
  }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            folder_path = Path(folder)
            (folder_path / "VSliceSharedAssetPaths.hx").write_text(
                (ROOT / "source/VSliceSharedAssetPaths.hx").read_text()
            )
            (folder_path / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_both_hxc_image_proxies_use_the_shared_vslice_fallback(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        state_scope = (ROOT / "source/HxcStateAssetScope.hx").read_text()
        self.assertIn("VSliceSharedAssetPaths.imageCandidates(key,", play_state)
        self.assertIn("VSliceSharedAssetPaths.imageCandidates(key)", state_scope)
        self.assertIn("hxc-vslice-image-missing", play_state)
        self.assertIn("hxc-vslice-image-missing", state_scope)


if __name__ == "__main__":
    unittest.main()
