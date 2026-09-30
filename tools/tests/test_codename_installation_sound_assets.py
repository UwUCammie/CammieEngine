"""Selected-owner Codename sound fallback is bounded to its own installation."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameInstallationSoundAssetsTest(unittest.TestCase):
    def test_owner_precedence_installation_fallback_and_rejections(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            installation = base / "installation"
            owner = installation / "mods/fnas"
            owner_local = owner / "sounds/menu/scroll.wav"
            owner_local.parent.mkdir(parents=True)
            owner_local.write_bytes(b"owner wav")
            install_sound = installation / "assets/sounds/menu/scroll.ogg"
            install_sound.parent.mkdir(parents=True)
            install_sound.write_bytes(b"installation ogg")
            (installation / "mods/other/sounds/ignored.ogg").parent.mkdir(parents=True)
            (installation / "mods/other/sounds/ignored.ogg").write_bytes(b"foreign mod")

            ambiguous_a = installation / "assets/sounds/amb/Menu.ogg"
            ambiguous_b = installation / "assets/sounds/amb/menu.ogg"
            ambiguous_a.parent.mkdir(parents=True)
            ambiguous_a.write_bytes(b"a")
            ambiguous_b.write_bytes(b"b")

            outside = base / "outside"
            outside.mkdir()
            (outside / "alert.ogg").write_bytes(b"escape")
            escaped = installation / "assets/sounds/escape"
            escaped.parent.mkdir(parents=True, exist_ok=True)
            try:
                escaped.symlink_to(outside, target_is_directory=True)
            except OSError:
                escaped = None

            loose_owner = base / "loose/fnas"
            loose_owner.mkdir(parents=True)
            (base / "Main.hx").write_text('''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
class Main {
 static function require(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var owner = Sys.args()[0];
  var local = CodenameInstallationSoundAssets.resolve(owner, "menu/scroll");
  require(local.status == "ok" && local.origin == "owner"
    && local.relative == "sounds/menu/scroll.wav"
    && File.getContent(local.source) == "owner wav", "owner files must win as a group before base OGGs");
  FileSystem.deleteFile(Path.join([owner, "sounds/menu/scroll.wav"]));
  var fallback = CodenameInstallationSoundAssets.resolve(owner, "menu/scroll");
  require(fallback.status == "ok" && fallback.origin == "installation"
    && fallback.relative == "sounds/menu/scroll.ogg"
    && File.getContent(fallback.source) == "installation ogg", "installation fallback");
  var explicit = CodenameInstallationSoundAssets.resolve(owner, "menu/scroll.ogg");
  require(explicit.status == "ok" && explicit.relative == "sounds/menu/scroll.ogg", "explicit extension");
  var foreign = CodenameInstallationSoundAssets.resolve(owner, "ignored");
  require(foreign.status == "missing", "must not search sibling mods");
  var ambiguous = CodenameInstallationSoundAssets.resolve(owner, "amb/MENU");
  require(ambiguous.status == "ambiguous" && ambiguous.source == null, "ambiguous case variants must fail closed");
  var unsafe = CodenameInstallationSoundAssets.resolve(owner, "../outside/alert");
  require(unsafe.status == "unsafe", "path traversal must fail closed");
  var escaped = CodenameInstallationSoundAssets.resolve(owner, "escape/alert");
  require(escaped.status == "escape" && escaped.source == null, "symlink escape must fail closed");
  var unsupported = CodenameInstallationSoundAssets.resolve(Sys.args()[1], "menu/scroll");
  require(unsupported.status == "unsupported-layout", "installation fallback requires a mods/<owner> layout");
 }
}''')
            p = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main",
                 str(owner), str(loose_owner)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
