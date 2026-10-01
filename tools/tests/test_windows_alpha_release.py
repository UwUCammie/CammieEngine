"""Windows x64 alpha release packaging and workflow contracts."""

from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SCRIPT = ROOT / "tools/package_windows_release.py"
SPEC = importlib.util.spec_from_file_location("windows_release_package", PACKAGE_SCRIPT)
PACKAGE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PACKAGE)


def write(path: Path, data: bytes = b"fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class WindowsAlphaReleaseTest(unittest.TestCase):
    def make_package_fixture(self, root: Path) -> tuple[Path, Path]:
        runtime = root / "runtime"
        repo = root / "repo"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        write(runtime / "Funkin.exe", b"exe")
        write(runtime / "CammieUpdateHelper.exe", b"update helper")
        write(runtime / "RELEASE_TAG", b"previous-release\n")
        write(runtime / "updateLog.txt", b"stale runtime notes")
        write(runtime / "lime.ndll", b"runtime native library")
        write(runtime / "libvlc.dll", b"VLC library")
        write(runtime / "libvlccore.dll", b"VLC core library")
        write(runtime / "libunwind.dll", b"runtime dll")
        write(runtime / "plugins/plugins.dat", b"VLC plugin index")
        write(runtime / "plugins/codec/libdemo_plugin.dll", b"VLC plugin")
        write(runtime / "manifest/libvlc.json", b"generated VLC library manifest")
        write(runtime / "manifest/default.json", b"generated Lime asset manifest")
        write(runtime / "assets/data/song/chart.json", b"chart")
        write(runtime / "assets/data/private-flat-song/chart.json", b"untracked local chart")
        write(runtime / "assets/data/options.json", b'{"personal":true}')
        write(runtime / "assets/imported_mods/bundled-vslice-results/pack.json", b'{"runsGlobally":true}')
        write(runtime / "assets/imported_mods/bundled-vslice-results/scripts/results.lua", b"onEndSong = function() end")
        write(runtime / "assets/imported_mods/bundled-vslice-results/images/results.png", b"bundled results image")
        write(runtime / "tools/astcenc.exe", b"decoder")
        write(runtime / "tools/astcenc-LICENSE.txt", b"runtime decoder license")
        for name in (
            "LICENSE",
            "NOTICE",
            "tools/licenses/astcenc-LICENSE.txt",
            "tools/licenses/CodenameEngine-Dev-LICENSE.txt",
        ):
            write(repo / name, name.encode())
        write(repo / "README.md", b"build documentation")
        write(repo / "USER-README.txt", b"user documentation")
        write(repo / "updateLog.txt", b"release notes")
        write(repo / "CHANGELOG.md", b"history")
        write(repo / "assets/data/options.json", b'{"fpsCap":60,"normalizeSongAudio":false}')
        write(repo / "assets/data/song/chart.json", b"tracked chart")
        write(repo / "assets/imported_mods/bundled-vslice-results/pack.json", b'{"runsGlobally":true}')
        write(repo / "assets/imported_mods/bundled-vslice-results/scripts/results.lua", b"onEndSong = function() end")
        write(repo / "assets/imported_mods/bundled-vslice-results/images/results.png", b"bundled results image")
        write(repo / "example_mods/readme.txt", b"tracked bundled example")
        subprocess.run(["git", "-C", str(repo), "add", "-f", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                        "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
        return runtime, repo

    def test_package_contains_runtime_not_personal_options_or_imports(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            root = Path(temp)
            runtime, repo = self.make_package_fixture(root)
            output = root / "dist"
            archive, checksum = PACKAGE.make_package(runtime, output, "alpha-test.1", repo)

            with zipfile.ZipFile(archive) as package:
                names = set(package.namelist())
                prefix = "CammieEngine-windows-x64/"
                self.assertIn(prefix + "Funkin.exe", names)
                self.assertIn(prefix + "CammieUpdateHelper.exe", names)
                self.assertIn(prefix + "lime.ndll", names)
                self.assertIn(prefix + "libunwind.dll", names)
                self.assertIn(prefix + "libvlc.dll", names)
                self.assertIn(prefix + "libvlccore.dll", names)
                self.assertIn(prefix + "plugins/plugins.dat", names)
                self.assertIn(prefix + "plugins/codec/libdemo_plugin.dll", names)
                self.assertIn(prefix + "manifest/libvlc.json", names)
                self.assertIn(prefix + "manifest/default.json", names)
                self.assertIn(prefix + "tools/astcenc.exe", names)
                self.assertIn(prefix + "tools/astcenc-LICENSE.txt", names)
                self.assertIn(prefix + "assets/data/song/chart.json", names)
                self.assertEqual(package.read(prefix + "RELEASE_TAG"), b"alpha-test.1\n")
                self.assertEqual(package.read(prefix + "updateLog.txt"), b"release notes")
                self.assertIn(prefix + "assets/imported_mods/bundled-vslice-results/pack.json", names)
                self.assertIn(prefix + "assets/imported_mods/bundled-vslice-results/scripts/results.lua", names)
                self.assertIn(prefix + "assets/imported_mods/bundled-vslice-results/images/results.png", names)
                self.assertFalse(any("private-flat-song" in name for name in names))
                self.assertEqual(
                    package.read(prefix + "assets/data/options.json"),
                    b'{"fpsCap":60,"normalizeSongAudio":false}',
                    "the package must carry the committed seed, never the runtime copy",
                )
                self.assertIn(prefix + "START-HERE.txt", names)
                self.assertIn(prefix + "LICENSE", names)
                self.assertIn(prefix + "NOTICE", names)
                self.assertIn(prefix + "licenses/CodenameEngine-Dev-LICENSE.txt", names)
                self.assertIn(prefix + "docs/BUILD-README.md", names)
                self.assertIn("Extract this ZIP", package.read(prefix + "START-HERE.txt").decode())

            expected = sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(checksum.read_text(encoding="ascii"), f"{expected}  {archive.name}\n")
            self.assertTrue(archive.name.startswith("CammieEngine-alpha-test.1-windows-x64"))

    def test_package_requires_runtime_and_license_inputs(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            root = Path(temp)
            runtime = root / "runtime"
            runtime.mkdir()
            with self.assertRaisesRegex(ValueError, "Funkin.exe"):
                PACKAGE.make_package(runtime, root / "dist", "alpha-test", ROOT)

            runtime, repo = self.make_package_fixture(root / "second")
            for missing in ("CammieUpdateHelper.exe", "lime.ndll", "libvlccore.dll"):
                (runtime / missing).unlink()
                with self.assertRaisesRegex(ValueError, missing.replace(".", r"\.")):
                    PACKAGE.make_package(runtime, root / f"dist-missing-{missing}", "alpha-test", repo)
                write(runtime / missing, b"restored fixture library")
            bundled_script = runtime / "assets/imported_mods/bundled-vslice-results/scripts/results.lua"
            bundled_script.unlink()
            with self.assertRaisesRegex(ValueError, "bundled-vslice-results/scripts/results.lua"):
                PACKAGE.make_package(runtime, root / "dist-missing-results", "alpha-test", repo)
            write(bundled_script, b"onEndSong = function() end")
            (repo / "tools/licenses/CodenameEngine-Dev-LICENSE.txt").unlink()
            with self.assertRaisesRegex(ValueError, "required release notice"):
                PACKAGE.make_package(runtime, root / "dist2", "alpha-test", repo)

    def test_case_only_runtime_mirrors_are_safe_for_windows_updater(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            root = Path(temp)
            runtime, repo = self.make_package_fixture(root)
            first = "assets/songs/Example/Inst.ogg"
            second = "assets/songs/example/Inst.ogg"
            write(runtime / first, b"same audio")
            write(runtime / second, b"same audio")
            write(repo / first, b"same audio")
            subprocess.run(["git", "-C", str(repo), "add", first], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                            "user.email=fixture@example.invalid", "commit", "-qm", "mirror"], check=True)
            archive, _ = PACKAGE.make_package(runtime, root / "dist", "alpha-test", repo)
            with zipfile.ZipFile(archive) as package:
                names = [name.casefold() for name in package.namelist()]
                self.assertEqual(len(names), len(set(names)))
                self.assertEqual(sum(name.endswith("assets/songs/example/inst.ogg") for name in names), 1)

            write(repo / second, b"different audio")
            subprocess.run(["git", "-C", str(repo), "add", second], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                            "user.email=fixture@example.invalid", "commit", "-qm", "conflict"], check=True)
            write(runtime / second, b"different audio")
            with self.assertRaisesRegex(ValueError, "conflicting Windows paths"):
                PACKAGE.make_package(runtime, root / "bad-dist", "alpha-test", repo)

    def test_excludes_owner_import_trees_without_modifying_them(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            root = Path(temp)
            runtime, repo = self.make_package_fixture(root)
            write(runtime / "assets/imported_mods/owner/owner.json", b"local owner")
            write(runtime / "assets/imported_mods/globalResultsProvider.json", b"personal provider")
            archive, _ = PACKAGE.make_package(runtime, root / "dist", "alpha-test", repo)
            with zipfile.ZipFile(archive) as package:
                names = package.namelist()
                self.assertFalse(any("/imported_mods/owner/" in name for name in names))
                self.assertFalse(any(name.endswith("globalResultsProvider.json") for name in names))
            self.assertEqual((runtime / "assets/imported_mods/owner/owner.json").read_bytes(), b"local owner")

    def test_refuses_modified_bundled_results_media(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            root = Path(temp)
            runtime, repo = self.make_package_fixture(root)
            write(runtime / "assets/imported_mods/bundled-vslice-results/images/results.png", b"changed locally")
            with self.assertRaisesRegex(ValueError, "bundled results asset differs"):
                PACKAGE.make_package(runtime, root / "dist", "alpha-test", repo)

    def test_canonical_windows_build_has_linux_shared_pins_and_patches(self):
        batch = (ROOT / "run.bat").read_text(encoding="utf-8")
        for required in (
            '"4.3.6"',
            "call :ensure_lib funkin-modchart 1.2.5",
            "tools\\patch_hxcpp_large_free.py",
            "tools\\install_codename_3d.py",
            "tools\\patch_openfl_context3d_readback.py",
            "tools\\patch_openfl_shader_version.py",
            "tools\\patch_hscript_ex_owner_scope.py",
            "tools\\patch_funkin_modchart_uv.py",
            ":ensure_asset_scaffolding",
            ":build_update_helper",
        ):
            self.assertIn(required, batch)

    def test_one_command_linux_cross_release_includes_results_source(self):
        script = ROOT / "build-windows-release.sh"
        subprocess.run(["bash", "-n", str(script)], check=True)
        help_result = subprocess.run([str(script), "--help"], check=True,
                                     capture_output=True, text=True)
        self.assertIn("Windows x64", help_result.stdout)
        content = script.read_text(encoding="utf-8")
        for required in (
            "./run.sh setup",
            ".tools/llvm-mingw/bin/x86_64-w64-mingw32-clang++",
            "./build.sh windows",
            "tools/package_windows_release.py",
            "bundled-vslice-results",
        ):
            self.assertIn(required, content)
        project = (ROOT / "Project.xml").read_text(encoding="utf-8")
        self.assertIn('assets/imported_mods/bundled-vslice-results', project)

    def test_no_github_actions_windows_rebuild(self):
        self.assertFalse((ROOT / ".github/workflows/windows-alpha.yml").exists())
        self.assertFalse((ROOT / ".github/workflows/build.yml").exists())
        self.assertFalse((ROOT / ".github/workflows/FunkyMainMenu.yml").exists())
        self.assertFalse((ROOT / ".github/workflows/win64.yml").exists())


if __name__ == "__main__":
    unittest.main()
